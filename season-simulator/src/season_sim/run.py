"""One season, in one worker process: guard, import, drive, read, check, write.

This module is the ONLY one that imports satc_system or client-documents at the
top of a function, and it does so only after `guard.pin_environment` has chosen
every path. `STATE` is a process singleton and cannot be re-pointed, so one
worker runs exactly one seed; `__main__` launches the workers.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import date
from pathlib import Path

from season_sim import clock, guard, paths


def _env(repo_sha: str) -> dict:
    import hashlib
    cfg = {
        "firm_policy.yaml": paths.SATC_ROOT / "configs" / "firm_policy.yaml",
        "federal.yaml": paths.SATC_ROOT / "configs" / "obligations" / "federal.yaml",
        "firm-settings.yaml": paths.CD / "registry" / "firm-settings.yaml",
        "fee-schedule.yaml": paths.CD / "registry" / "fee-schedule.yaml",
        "scenario.yaml": paths.PROJECT / "scenario.yaml",
    }
    return {"repo_sha": repo_sha, "python": platform.python_version(),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED", "(unset)"),
            "config_sha256": {k: hashlib.sha256(v.read_bytes()).hexdigest()[:16]
                              for k, v in cfg.items()}}


class Season:
    def __init__(self, *, seed: int, run_dir: Path, out_dir: Path, clients: int | None = None,
                 until: date | None = None, days_mode: str = "all", mutation: str = "",
                 only_clients: set[str] | None = None, checks: set[str] | None = None,
                 repo_sha: str = "", billing_door: str | None = None, pages: bool = True):
        self.seed = seed
        self.iso = guard.pin_environment(run_dir, paths.REPO)
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.clients_n = clients
        self.until = until
        self.days_mode = days_mode
        self.mutation = mutation
        self.only_clients = only_clients
        self.checks = checks
        self.repo_sha = repo_sha
        self.billing_door = billing_door
        self.pages = pages
        self.calls: list = []

    # -- set up ---------------------------------------------------------------
    def boot(self):
        paths.put_projects_on_path()
        clock.seed_uuid4(self.seed)
        import yaml  # noqa: F401  (import before client-documents' shadows are in play)
        from satc.app.server import create_app
        from satc.app.state import STATE
        from satc.persistence.store import resolve_dir
        import cli  # noqa: F401
        import exercise  # noqa: F401
        self.shadowed = paths.assert_no_shadowing()
        self.banned = guard.install_bans()
        if Path(resolve_dir()).resolve() != self.iso.satc_data.resolve() or \
                Path(STATE.store.dir).resolve() != self.iso.satc_data.resolve():
            raise guard.SimRefused(f"satc store resolved to {STATE.store.dir}, not the run dir")
        self.STATE = STATE
        self.app = create_app()
        from season_sim.doors_cd import CdDoors
        from season_sim.doors_satc import SatcDoors
        self.satc = SatcDoors(self.app, self.calls)
        self.cd = CdDoors(self.iso, self.calls)
        if self.mutation:
            from season_sim import mutations
            self.mutated = mutations.apply(self.mutation)

    def run(self) -> dict:
        t_start = time.perf_counter()
        self.boot()           # FIRST: nothing below may import satc before the guard ran

        from season_sim import world as world_mod
        from season_sim.findings import Ledger, dumps
        from season_sim.firm import Firm
        from season_sim.invariants import Ctx, run_all
        from season_sim.observations import Observations, what_if_extension_ack
        from season_sim.observe import Observer
        sc = world_mod.load_scenario()
        w = world_mod.build(self.seed, scenario=sc, clients=self.clients_n,
                            billing_door=self.billing_door)
        if self.only_clients:
            w = w.restricted(self.only_clients)
        (self.out_dir / "world.json").write_text(w.to_json(), encoding="utf-8")

        start = date.fromisoformat(str(sc["season"]["start"]))
        end = self.until or date.fromisoformat(str(sc["season"]["end"]))
        tax_year = int(sc["season"]["tax_year"])

        # Day 0: the real door clears AppState's four 2024 demo clients.
        with clock.frozen(date(tax_year, 1, 2)):
            self.STATE.clear_sample_data()
            if self.STATE.has_sample_data():
                raise guard.SimRefused("the demo clients survived clear_sample_data()")

        firm = Firm(w, sc, self.satc, self.cd, self.STATE, self.calls)
        with_history = any(c.returning for c in w.clients)
        if with_history:
            firm.history()

        ctx = Ctx(firm, tax_year=tax_year, billing_door=w.billing_door)
        ledger = Ledger()
        obs = Observations(tax_year)
        observer = Observer(self)
        audits: list[dict] = []
        timings: list[dict] = []
        last_snap = None
        checkpoints = {date(2027, 1, 4), date(2027, 1, 15), date(2027, 2, 1), date(2027, 2, 15),
                       date(2027, 3, 2), date(2027, 3, 16), date(2027, 4, 1), date(2027, 4, 9),
                       date(2027, 4, 16), date(2027, 5, 3), date(2027, 7, 1), date(2027, 9, 1),
                       date(2027, 10, 1), date(2027, 10, 15)}
        audit_days = {date(2027, m, 1) for m in range(1, 11)} | {date(2027, 4, 16)}

        for d in clock.days(start, end):
            reading = self.days_mode == "all" or d in checkpoints or d == end
            with clock.frozen(d):
                if clock.is_weekday(d):
                    firm.act(d)
                if not reading:
                    continue
                t0 = time.perf_counter()
                snap = observer.read(d, pages=self.pages)
                ctx.refresh()
                results = run_all(snap, ctx, only=self.checks)
                ledger.add_day(d.isoformat(), results)
                obs.day(snap, ctx)
                ctx.prev_day = d.isoformat()
                last_snap = snap
                timings.append({"day": d.isoformat(), **snap.timings,
                                "total": round(time.perf_counter() - t0, 3)})
            if reading and (d in audit_days or d == end) and (not self.checks or "K1" in self.checks):
                audits.append(self.clock_audit(d, ledger, ctx))

        # What-if (H3), labelled: never written anywhere.
        what_if = {}
        delivered = [tr for tr in firm.t.values() if tr.delivered_on and tr.main_job]
        if delivered:
            job = self.STATE.engagement(delivered[0].main_job)
            if job is not None:
                what_if = what_if_extension_ack(job)
                what_if["sim"] = delivered[0].sim.sim_id

        with clock.frozen(end):
            observations = obs.finish(last_snap, ctx, firm) if last_snap else {}
        run_level = self.run_level()
        env = _env(self.repo_sha)
        records = ledger.records(seed=self.seed, env=env, clients=len(w.clients))
        (self.out_dir / "findings.jsonl").write_text(dumps(records), encoding="utf-8")

        summary = {
            "seed": self.seed, "clients": len(w.clients), "billing_door": w.billing_door,
            "days": (end - start).days + 1, "days_read": len(timings),
            "window": [start.isoformat(), end.isoformat()], "mutation": self.mutation,
            "mutated": list(getattr(self, "mutated", ()) or ()),
            "invariants": {code: {"examined": ledger.examined.get(code, 0),
                                  "days_checked": ledger.days_checked.get(code, 0),
                                  "days_with_subjects": ledger.days_with_subjects.get(code, 0),
                                  "findings": sum(1 for r in records if r["invariant"] == code)}
                           for code in sorted(ledger.days_checked)},
            "checker_crashes": ledger.crashes[:20],
            "door_calls": self._call_counts(),
            "clock_audit": audits,
            "what_if_H3": what_if,
            "observations": observations,
            "run_level": run_level,
            "shadowed_modules": [Path(p).name for p in self.shadowed],
            "banned": self.banned,
            "archetypes": {c.sim_id: c.archetype for c in w.clients},
            "outcomes": {tr.sim.sim_id: {
                "archetype": tr.sim.archetype, "form": tr.sim.form, "ref": tr.sim.ref,
                "engaged": tr.engaged_on, "delivered": tr.delivered_on,
                "extended": tr.extended_on, "disengaged": tr.disengaged_on,
                "filed": tr.filed_on, "invoice": tr.invoice, "paid": tr.paid_on,
                "payment_recorded": tr.payment_recorded} for tr in firm.t.values()},
            "env": env,
        }
        (self.out_dir / "summary.json").write_text(
            json.dumps(summary, indent=1, sort_keys=True, default=str), encoding="utf-8")
        (self.out_dir / "timings.json").write_text(json.dumps({
            "wall_seconds": round(time.perf_counter() - t_start, 1), "per_day": timings}),
            encoding="utf-8")
        self.STATE.store.close()
        return summary

    def _call_counts(self) -> dict:
        from collections import Counter
        c = Counter()
        bad = Counter()
        for call in self.calls:
            key = call.target.split(" ")[0] + " " + (call.args.get("argv", [""])[0]
                                                     if call.door == "cli" else
                                                     "/".join(call.target.split("/")[:2]))
            c[key] += 1
            if call.door == "cli" and call.status not in (0, "0"):
                bad[key] += 1
            if call.door == "http" and call.status not in (200, 302):
                bad[key] += 1
        return {"total": sum(c.values()), "by_door": dict(sorted(c.items())),
                "not_ok": dict(sorted(bad.items()))}

    # -- the clock-leak audit ---------------------------------------------------
    def clock_audit(self, d: date, ledger, ctx) -> dict:
        """Every read, twice: clock frozen on the day, then clock on a sentinel
        (2031-06-15) with `today=` passed explicitly. A difference is a clock
        read that `today=` does not reach."""
        import deadlines
        import engagements
        import signing
        from satc.actions import build_queue
        from satc.app.today_views import _obligations, working_tax_year
        from satc.intake.chasing import waiting
        from satc.work.queue import board
        from season_sim.invariants import Hit

        store = Path(self.cd.store)

        def reads() -> dict:
            st = self.STATE
            req, rec = list(st.requested_items()), list(st.received_documents())
            year = working_tax_year(rec + req, d)
            jobs = st.jobs()
            q = build_queue(clients=[c for c, _ in st.client_choices()], requested=req,
                            received=rec, obligations=_obligations(year),
                            engaged_clients=[j.client_id for j in jobs], jobs=jobs,
                            invoices=st.store.load_invoices(), payments=st.store.load_payments(),
                            tax_year=year, today=d)
            b = board(jobs, requested=req, obligations=_obligations(year), today=d, tax_year=year)
            sw = waiting(st.store, today=d)
            recs = [(r["ref"], engagements.load(r["ref"], store)) for r in engagements.listing(store)]
            due, unplaced = deadlines.board(recs, today=d)
            sw2 = signing.waiting(store, today=d)
            _c, season_out = self.cd.season(d.isoformat())
            return {
                "satc.actions.build_queue(today=D)": [f"{a.action_id}:{a.urgency}" for a in q.actions],
                "satc.work.queue.board(today=D)": [f"{w.job_id}:{w.score:.6f}" for w in b.workable]
                + [x.job_id for x in b.not_workable],
                "satc.intake.chasing.waiting(today=D)": [f"{r.request_id}:{r.waiting_days(d)}"
                                                         for r in sw.rows],
                "deadlines.board(today=D)": [f"{x.ref}:{x.when}:{x.kind}:{x.days}" for x in due]
                + [f"unplaced:{u}" for u in unplaced],
                "signing.waiting(today=D)": [f"{w.ref}:{w.overdue}" for w in sw2],
                "cli season --today D": season_out,
            }

        with clock.frozen(d):
            right = reads()
        with clock.frozen(clock.SENTINEL):
            wrong = reads()
        leaks = clock.leaks(right, wrong)
        hits = []
        if "cli season --today D" in leaks:
            a = right["cli season --today D"].splitlines()
            b = wrong["cli season --today D"].splitlines()
            diff = next((f"clock on the day: {x!r} | clock on {clock.SENTINEL}: {y!r}"
                         for x, y in zip(a, b) if x != y), f"{len(a)} vs {len(b)} lines")
            hits.append(Hit("-", f"cli season --today {d} printed differently when the machine "
                                 f"clock was wrong. First difference: {diff}",
                            "identical output: --today D alone decides the answer",
                            "cli season",
                            {"door": "cli", "target": "cli.main(['season', '--today', D, '--store', S])",
                             "clock": f"frozen@{clock.SENTINEL}T14:00Z vs frozen@{d}T14:00Z",
                             "today_arg": d.isoformat()}))
        if not self.checks or "K1" in self.checks:
            ledger.add_day(d.isoformat(), {"K1": (hits, 1)})
        return {"day": d.isoformat(), "reads": sorted(right), "leaks": leaks,
                "sizes": {k: len(v) for k, v in right.items()}}

    def run_level(self) -> dict:
        out = {}
        out["banned_call_attempts"] = 0          # any attempt raises SimRefused and ends the run
        out["env_pinned_at_end"] = all(os.environ.get(k) == v for k, v in {
            "SATC_DATA_DIR": str(self.iso.satc_data),
            "SATC_ENGAGEMENTS": str(self.iso.engagements), "SATC_ROLE": "owner",
            "SATC_OLLAMA": "0"}.items())
        from satc.persistence.store import resolve_dir
        out["store_is_run_dir"] = Path(resolve_dir()).resolve() == self.iso.satc_data.resolve()
        out["cd_default_store_untouched"] = not (paths.CD / "engagements").exists()
        out["cd_out_untouched"] = not (paths.CD / "out").exists()
        return out
