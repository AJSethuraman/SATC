"""Observations: what the season looked like where no rule says what it should be.

NOTHING HERE IS A FAILURE, and the report never calls one a failure. An
observation is a measured fact with no recorded threshold behind it -- "jobs sat
fourteen days untouched" is the firm's own `stale_after_days: 14`
(`firm_policy.yaml:71-74`) used as a yardstick, not a rule anyone broke.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta


class Observations:
    def __init__(self, tax_year: int):
        self.tax_year = tax_year
        self.wrong_year_days: list[dict] = []
        self.chase_gap = Counter()                 # client -> days /documents lists, Today silent
        self.signature_rows = 0
        self.rows_by_kind_month: dict[str, Counter] = defaultdict(Counter)
        self.work_empty_ready: list[dict] = []     # days nothing workable while prep-ready files exist
        self.work_top: list[dict] = []
        self.ready_to_deliver_days = Counter()     # job -> days at ready_to_deliver
        self.stale = Counter()                     # job -> days idle >= 14 while open
        self.stale_by_stage = Counter()            # stage -> job-days idle >= 14
        self.stage_days: dict[str, Counter] = defaultdict(Counter)
        self.blocking_classes = Counter()
        self.toggled_without_completion = set()
        self.g7_signed_in_cd = set()
        self.not_workable_reasons = Counter()
        self.first_2026_request: str = ""
        self.days = 0

    def day(self, snap, ctx) -> None:
        self.days += 1
        d = snap.day
        month = d.strftime("%Y-%m")
        for a in snap.queue:
            self.rows_by_kind_month[month][a.kind] += 1
            if a.kind == "signature_outstanding":
                self.signature_rows += 1
        if snap.tax_year != self.tax_year:
            overdue = sum(1 for a in snap.queue if a.urgency == "overdue")
            self.wrong_year_days.append({"day": d.isoformat(), "working_year": snap.tax_year,
                                         "overdue_rows": overdue, "rows": len(snap.queue)})
        elif not self.first_2026_request:
            self.first_2026_request = d.isoformat()

        # Today (3 days) vs /documents (1 day), per client.
        chased = {a.client_id for a in snap.queue
                  if a.kind in ("chase_documents", "signature_outstanding")}
        for row in snap.sweep.rows:
            if row.client_id not in chased and row.tax_year == snap.tax_year:
                self.chase_gap[ctx.sim_for_client(row.client_id)] += 1

        # The Work queue against "a real March".
        work = list(snap.board.workable)
        stuck = list(snap.board.not_workable)
        for b in stuck:
            self.not_workable_reasons[b.view.stage] += 1
        for item in work + stuck:
            self.stage_days[item.view.stage][ctx.sim_for_job(item.job_id)] += 1
            if item.view.stage == "ready_to_deliver":
                self.ready_to_deliver_days[item.job.workflow_key] += 1
        ready_files = []
        for tr in (ctx.firm.t.values() if ctx.firm else ()):
            if tr.prep_started and not tr.delivered_on:
                ready_files.append(tr.sim.sim_id)
        if not work and ready_files:
            self.work_empty_ready.append({"day": d.isoformat(), "in_prep": len(ready_files)})
        if d.day == 1 or d.isoformat() in ("2027-03-15", "2027-04-15"):
            self.work_top.append({
                "day": d.isoformat(), "workable": len(work), "not_workable": len(stuck),
                "top": [{"rank": w.rank, "sim": ctx.sim_for_job(w.job_id),
                         "workflow": w.job.workflow_key, "score": round(w.score, 3),
                         "why": w.why} for w in work[:3]]})

        from satc.work.queue import _last_movement
        for item in work + stuck:
            moved = _last_movement(item.job)
            delivered = snap.deliverables.get(item.job_id) is not None
            if moved and not delivered and (d - moved).days >= 14:
                self.stale[ctx.sim_for_job(item.job_id)] += 1
                self.stale_by_stage[item.view.stage] += 1

        for j in snap.jobs:
            for t in j.tasks:
                if t.status == "done" and t.completion is None:
                    self.toggled_without_completion.add((ctx.sim_for_job(j.job_id), t.task_id))

        import signing
        auth = signing._authorization_names()
        current = {tr.sim.ref for tr in (ctx.firm.t.values() if ctx.firm else ())}
        for ref, st in snap.cd_standing.items():
            if ref in current and st.expected and not [m for m in st.missing if m.document in auth] \
                    and any(ln.document in auth for ln in st.expected):
                self.g7_signed_in_cd.add(ref)

    def finish(self, snap, ctx, firm) -> dict:
        from satc.work import sla

        blocking = Counter()
        for r in snap.requested:
            if r.tax_year == self.tax_year:
                blocking[f"{r.doc_type} -> {r.blocking}"] += 1

        k1 = []
        for tr in firm.t.values():
            if tr.sim.archetype != "k1_gated":
                continue
            partner = firm.t.get(tr.sim.partnership or "")
            k1.append({"sim": tr.sim.sim_id, "partnership": tr.sim.partnership,
                       "partnership_delivered": partner.delivered_on if partner else "",
                       "return_delivered": tr.delivered_on, "extended": tr.extended_on,
                       "lag_days": ((date.fromisoformat(tr.delivered_on)
                                     - date.fromisoformat(partner.delivered_on)).days
                                    if tr.delivered_on and partner and partner.delivered_on
                                    else None)})

        try:
            measurable = sorted(sla.measurable_slas())
        except Exception as exc:                          # noqa: BLE001
            measurable = [f"(could not read: {exc})"]
        try:
            unmeasurable = [f"{getattr(p, 'kind', '')}: {getattr(p, 'missing_fact', '') or getattr(p, 'why', '')}"[:160]
                            for p in sla.unmeasurable_promises()]
        except Exception as exc:                          # noqa: BLE001
            unmeasurable = [f"(could not read: {exc})"]
        filings = firm.STATE.filings()

        facts = Counter(f["kind"] + ": " + f["detail"].split(";")[-1].strip()
                        for f in firm.facts)

        # The alert thresholds the firm wrote (firm_policy.yaml:43-44), loaded by
        # obligations/policy.py:96-97, against the defaults Today's deadline rows
        # actually use (propose.deadline_pressure / _urgency_from_days). Nothing
        # outside policy.py reads the two policy values.
        import inspect

        from satc.actions.propose import _urgency_from_days, deadline_pressure
        from satc.obligations.policy import load_policy
        try:
            pol = load_policy()
            alerts = {"firm_policy.yaml alerts": {"approaching_days": pol.approaching_days,
                                                  "urgent_days": pol.urgent_days},
                      "what Today uses": {
                          "deadline_pressure soon_days": inspect.signature(
                              deadline_pressure).parameters["soon_days"].default,
                          "_urgency_from_days urgent": inspect.signature(
                              _urgency_from_days).parameters["urgent"].default}}
        except Exception as exc:                          # noqa: BLE001
            alerts = {"could not read": str(exc)}

        # Payments, by what could record them.
        paid = [tr for tr in firm.t.values() if tr.paid_on]
        by_style = Counter(tr.sim.pay_style for tr in firm.t.values() if tr.invoice)
        recorded = Counter(tr.payment_recorded or "not yet due" for tr in firm.t.values()
                           if tr.invoice)
        checks = [p for p in firm.unrecordable_payments if p["by"] == "check"]
        refusals = [dict(r, sim=tr.sim.sim_id) for tr in firm.t.values() for r in tr.refusals]
        return {
            "working_year_before_2026": {
                "days": len(self.wrong_year_days), "first_2026_day": self.first_2026_request,
                "overdue_rows_on_those_days": [w["overdue_rows"] for w in self.wrong_year_days],
                "sample": self.wrong_year_days[:3]},
            "today_vs_documents_threshold": {
                "client_days_listed_on_documents_but_not_chased_on_today": sum(self.chase_gap.values()),
                "clients": len(self.chase_gap)},
            "signature_outstanding_rows_all_season": self.signature_rows,
            "today_rows_by_month": {m: dict(c) for m, c in sorted(self.rows_by_kind_month.items())},
            "work_queue": {
                "days_nothing_workable_while_returns_in_prep": len(self.work_empty_ready),
                "not_workable_stage_days": dict(self.not_workable_reasons),
                "stage_job_days": {k: sum(v.values()) for k, v in self.stage_days.items()},
                "monthly_top": self.work_top},
            "ready_to_deliver_job_days_never_proposed": sum(self.ready_to_deliver_days.values()),
            "ready_to_deliver_job_days_by_workflow": dict(self.ready_to_deliver_days),
            "stale_14_days_job_days_by_stage": dict(self.stale_by_stage),
            "delivered_vs_closed_out": {
                "delivered": sum(1 for tr in firm.t.values() if tr.delivered_on),
                "closed_out_as_filed": sum(1 for tr in firm.t.values() if tr.filed_on),
                "payments_made_with_no_door": len(firm.unrecordable_payments),
                "of_which_checks": len(checks),
                "of_which_cards": len(firm.unrecordable_payments) - len(checks)},
            # What was L4. It never observed the product (it counted the checks the
            # scenario scripted), and the gap is already written down, so it is an
            # observation with its record cited, not a failing check.
            "check_payments_no_command_records": {
                "count": len(checks), "sims": sorted({p["sim"] for p in checks}),
                "gate_says": "client-documents/signing.py:564-570 ('a bill paid another way "
                             "is recorded by hand')",
                "already_recorded": "docs/OPERATING-PROCEDURES.md:382-385 ('Judgement, not "
                                    "procedure: a bill paid another way ... marking it by hand "
                                    "is a decision about money that belongs to a person')",
                "settlement_writer": "record_settlement's only caller is cli.py:900 (Square)"},
            "billed_clients_by_payment_style": dict(by_style),
            "payment_recorded": dict(recorded),
            "clients_who_paid_by_season_end": len(paid),
            "alert_thresholds": alerts,
            "stale_14_days_job_days": sum(self.stale.values()),
            "stale_jobs_top": self.stale.most_common(5),
            "request_blocking_classes": dict(blocking),
            "tasks_done_with_no_completion_record": len(self.toggled_without_completion),
            "current_year_e_file_authorizations_fully_signed_in_client_documents": len(self.g7_signed_in_cd),
            "satc_filings_on_file": len(filings),
            "slas": {"measurable": measurable, "unmeasurable": unmeasurable},
            "k1_dependency": k1,
            "facts_with_no_door": dict(facts),
            "refused_door_calls": len(refusals),
            "refusals_sample": refusals[:12],
        }


def what_if_extension_ack(job) -> dict:
    """H3, in a LABELLED what-if: no door records a Filing (D8), so this asks the
    pure function what it would say if one with ack 'a' (extension accepted) were
    on file. Nothing is written."""
    from satc.models.filing import Filing
    from satc.work.stage import derive_stage

    filing = Filing(filing_id="what-if", return_key=f"{job.client_id}-{job.tax_year}-1040",
                    client_id=job.client_id, ack_code="a", ack_date=date(2027, 4, 15),
                    note="WHAT-IF: never written; no door records a Filing (D8)")
    kw = {"ack_code": "a", "ack_date": "2027-04-15"}
    view = derive_stage(job, filings=[filing])
    return {"ran": True, "filing": {k: str(v) for k, v in kw.items()},
            "stage": view.stage, "why": view.why,
            "is_accepted": getattr(filing, "is_accepted", None)}
