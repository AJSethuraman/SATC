"""The daily read pass: what every screen and every engine says, on one day.

Everything here READS. It calls the real routes (through the test client) and
keeps what each route handed its template -- the queue /today built, the board
/work built, the stage a job page derived -- so the checks read the route, not
a copy of it. It also recomputes each with the arguments the route is known to
pass; that copy is used only to count the days it disagreed with the route (a
run-level guard on the simulator's own fidelity). The agent door and
client-documents' engines, which have no screen here, are called directly.

B5 in the brief -- "reads write nothing" -- is measured here: both SQLite files
and the whole engagements tree are hashed before and after the pass.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

BADGE = re.compile(r'<p><span class="badge">([^<]+)</span>')


@dataclass
class Snapshot:
    day: date
    tax_year: int = 0
    clients: list = field(default_factory=list)          # [client_id]
    entity: dict = field(default_factory=dict)           # client_id -> entity_type
    requested: list = field(default_factory=list)
    received: list = field(default_factory=list)
    jobs: list = field(default_factory=list)
    obligations: list = field(default_factory=list)
    invoices: list = field(default_factory=list)
    payments: list = field(default_factory=list)
    deliverables: dict = field(default_factory=dict)     # job_id -> delivery | None
    engagement_refs: dict = field(default_factory=dict)  # ref -> [client_id]
    queue: list = field(default_factory=list)            # what GET /today rendered, ProposedAction
    queue_again: list = field(default_factory=list)      # ids from a second GET /today (B4)
    today_year: object = None                            # the year GET /today worked on
    screen_ids: list = field(default_factory=list)       # /today, in page order
    screen_status: int = 0
    agent: dict = field(default_factory=dict)
    board: object = None                                 # what GET /work rendered
    work_refusal: str = ""
    copy_mismatch: dict = field(default_factory=dict)    # simulator's copy vs the route, per screen
    work_screen_ids: list = field(default_factory=list)
    page_stage: dict = field(default_factory=dict)       # job_id -> badge text
    page_view: dict = field(default_factory=dict)        # job_id -> StageView GET /work/<id> rendered
    sweep: object = None
    cd_refs: list = field(default_factory=list)
    cd_records: dict = field(default_factory=dict)
    cd_unreadable: list = field(default_factory=list)
    cd_board: tuple = ((), ())
    cd_season_out: str = ""
    cd_waiting: list = field(default_factory=list)
    cd_standing: dict = field(default_factory=dict)
    cd_may_file: dict = field(default_factory=dict)
    cd_stages: dict = field(default_factory=dict)
    cd_events: dict = field(default_factory=dict)
    cd_closed: dict = field(default_factory=dict)
    cd_interviews: set = field(default_factory=set)
    cd_invoices: dict = field(default_factory=dict)      # ref -> [invoice dict]
    cd_sweep_count: int = 0
    hash_before: str = ""
    hash_after: str = ""
    changed_files: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)


def tree_hash(paths: list[Path]) -> tuple[str, dict]:
    files = {}
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        items = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for p in items:
            try:
                files[str(p)] = hashlib.sha1(p.read_bytes()).hexdigest()
            except OSError:
                files[str(p)] = "unreadable"
    h = hashlib.sha1("\n".join(f"{k}={v}" for k, v in sorted(files.items())).encode()).hexdigest()
    return h, files


class Observer:
    def __init__(self, sim):
        self.sim = sim
        self.STATE = sim.STATE
        self.satc = sim.satc
        self.cd = sim.cd

    def _watched(self) -> list[Path]:
        data = Path(self.STATE.store.dir)
        return [p for p in data.glob("*.db")] + [Path(self.cd.store)]

    def read(self, d: date, *, pages: bool = True) -> Snapshot:
        s = Snapshot(day=d)
        t0 = time.perf_counter()
        s.hash_before, before = tree_hash(self._watched())
        self._satc(s, pages=pages)
        t1 = time.perf_counter()
        self._cd(s)
        t2 = time.perf_counter()
        s.hash_after, after = tree_hash(self._watched())
        s.changed_files = sorted(k for k in set(before) | set(after)
                                 if before.get(k) != after.get(k))
        s.timings = {"satc": round(t1 - t0, 3), "cd": round(t2 - t1, 3)}
        return s

    # -- satc_system --------------------------------------------------------
    def _satc(self, s: Snapshot, *, pages: bool) -> None:
        from satc.actions import build_queue
        from satc.agent import tools as agent_tools
        from satc.app import work_views
        from satc.app.today_views import _obligations, working_tax_year
        from satc.intake.chasing import waiting
        from satc.work.queue import board
        from satc.work.stage import derive_stage

        st = self.STATE
        d = s.day
        s.requested = list(st.requested_items())
        s.received = list(st.received_documents())
        copy_year = working_tax_year(s.received + s.requested, d)
        call, ids, ctx = self.satc.today()
        s.screen_ids, s.screen_status = ids, call.status
        routed = ctx.get("queue")
        s.queue = list(routed.actions) if routed is not None else []
        s.today_year = ctx.get("tax_year")
        # The year the checks judge against is the one /today worked on.
        s.tax_year = int(s.today_year) if s.today_year is not None else copy_year
        choices = st.client_choices()
        s.clients = [cid for cid, _ in choices]
        s.entity = {pc.client_id: pc.entity_type for pc in st.mart.public_clients}
        s.jobs = st.jobs()
        s.obligations = _obligations(s.tax_year)
        s.invoices = st.store.load_invoices()
        s.payments = st.store.load_payments()
        for e in st.mart.engagements:
            if e.engagement_ref:
                s.engagement_refs.setdefault(e.engagement_ref, []).append(e.client_id)

        # THE ROUTES' OWN ANSWERS. Today's queue and the Work board are what
        # /today and /work handed their templates (Flask's template_rendered
        # signal), not a recomputation with arguments copied from the routes: a
        # route that changed what it passes the engine must change what the
        # checks see. The copy is still computed, as a FIDELITY check on the
        # simulator itself -- every day it disagrees with the route is counted
        # and reported as a run-level guard, never silently used.
        def copy_queue():
            return build_queue(
                clients=[cid for cid, _ in st.client_choices()],
                requested=s.requested, received=s.received, obligations=s.obligations,
                engaged_clients=[j.client_id for j in s.jobs], jobs=s.jobs,
                invoices=s.invoices, payments=s.payments, tax_year=s.tax_year, today=d)

        _again_call, _ids, again = self.satc.today()          # B4: the same day, the same queue
        s.queue_again = [a.action_id for a in again["queue"].actions] if again.get("queue") else []
        s.copy_mismatch["today"] = ([a.action_id for a in copy_queue().actions]
                                    != [a.action_id for a in s.queue]
                                    or s.today_year != copy_year)
        s.agent = agent_tools.today(st)

        _call, s.work_screen_ids, wctx = self.satc.work()
        s.board = wctx.get("board")
        copy_board = board(s.jobs, requested=s.requested, obligations=s.obligations,
                           today=d, tax_year=s.tax_year)
        if s.board is None:                  # the route refused to rank; say so, never substitute
            s.work_refusal = wctx.get("refusal", "(no board rendered)")
            s.board = type(copy_board)(workable=(), not_workable=(), policy=copy_board.policy)
        s.copy_mismatch["work"] = (
            [(w.job_id, w.view.stage) for w in copy_board.workable]
            + [(b.job_id, b.view.stage) for b in copy_board.not_workable]
            != [(w.job_id, w.view.stage) for w in s.board.workable]
            + [(b.job_id, b.view.stage) for b in s.board.not_workable])

        page_mismatch = False
        for job in s.jobs:
            delivery, filings = work_views._delivery_and_filings(job)
            s.deliverables[job.job_id] = delivery
            if job.tax_year is not None and int(job.tax_year) != s.tax_year:
                continue
            readiness = work_views._readiness(job, s.requested, s.tax_year)
            copy_view = derive_stage(job, readiness=readiness, today=d,
                                     delivery=delivery, filings=filings)
            if pages:
                _c, body, jctx = self.satc.rendered(f"/work/{job.job_id}")
                m = BADGE.search(body)
                s.page_stage[job.job_id] = m.group(1).strip() if m else ""
                view = jctx.get("view")
                s.page_view[job.job_id] = view if view is not None else copy_view
                page_mismatch = page_mismatch or view is None or view.stage != copy_view.stage
            else:
                s.page_view[job.job_id] = copy_view
        s.copy_mismatch["job_page"] = page_mismatch
        s.sweep = waiting(st.store, today=d)

    # -- client-documents ---------------------------------------------------
    def _cd(self, s: Snapshot) -> None:
        import closeout
        import cli
        import deadlines
        import engagements
        import invoicing
        import lifecycle
        import packaging
        import signing
        import stages

        store = Path(self.cd.store)
        d = s.day
        s.cd_refs = [r["ref"] for r in engagements.listing(store)]
        records = []
        for ref in s.cd_refs:
            try:
                rec = engagements.load(ref, store)
            except Exception:                                  # noqa: BLE001
                s.cd_unreadable.append(ref)
                continue
            s.cd_records[ref] = rec
            records.append((ref, rec))
        s.cd_board = deadlines.board(records, today=d)
        _call, s.cd_season_out = self.cd.season(d.isoformat())
        s.cd_waiting = signing.waiting(store, today=d)
        for ref, rec in s.cd_records.items():
            try:
                docs = packaging.documents_for(rec)
            except Exception:                                  # noqa: BLE001
                docs = None
            saved = lifecycle.load_saved(ref, "delivery", store) or {}
            deadline = (saved.get("answers") or {}).get("signature_deadline", "")
            if docs is not None:
                s.cd_standing[ref] = signing.standing(ref, rec, docs, cli.TEMPLATE_DIR,
                                                      store=store, deadline=deadline, today=d)
                s.cd_may_file[ref] = signing.may_file(ref, rec, docs, cli.TEMPLATE_DIR,
                                                      store=store, deadline=deadline, today=d)
            s.cd_stages[ref] = stages.reached(ref, store)
            s.cd_events[ref] = lifecycle.events_on(ref, store)
            s.cd_closed[ref] = closeout.load_filed(ref, store)
            s.cd_invoices[ref] = invoicing.issued_for(store, ref)
            if (store / ref / "interview.json").exists():
                s.cd_interviews.add(ref)
        s.cd_sweep_count = len(closeout.sweep(store))
