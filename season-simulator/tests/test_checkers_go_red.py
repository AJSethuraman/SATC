"""Every checker goes red on a planted violation (principle 12).

`docs/DESIGN-PRINCIPLES.md:224`: a check that has never failed is not evidence.
Each test below builds the smallest snapshot that breaks one rule, using the
real record classes of the two projects, and asserts the checker reports it.
Where it is cheap, the same snapshot with the violation removed must come back
clean -- so a checker that always fires is caught too.

The record shapes come from satc_system's own tests
(`tests/test_work_queue.py:28-70`), imported rather than copied.
"""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from season_sim import clock, paths
from season_sim import invariants as I
from season_sim.observe import Snapshot

_spec = importlib.util.spec_from_file_location(
    "satc_test_work_queue_shapes", paths.SATC_ROOT / "tests" / "test_work_queue.py")
WQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(WQ)

from satc.actions.propose import ProposedAction  # noqa: E402
from satc.intake.chasing import Sweep, Waiting  # noqa: E402
from satc.models.evidence import RequestedItem  # noqa: E402
from satc.obligations.profile import ObligationInstance  # noqa: E402
from satc.work.queue import BlockedItem, Board, Factor, QueuePolicy, WorkItem  # noqa: E402
from satc.work.stage import StageView  # noqa: E402

DAY = date(2027, 4, 20)


# ── builders ─────────────────────────────────────────────────────────────────

def snap(**kw) -> Snapshot:
    s = Snapshot(day=kw.pop("day", DAY))
    s.tax_year = 2026
    s.board = Board(workable=(), not_workable=(), policy=QueuePolicy())
    s.sweep = Sweep(rows=[], requests=0)
    s.agent = {"actions": []}
    s.cd_board = ([], [])
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def action(kind="chase_documents", cid="C1", urgency="soon", why="evidence", due=None,
           title="t", subject="2026", evidence=()):
    return ProposedAction(action_id=f"{kind}/{cid}/{subject}", kind=kind, client_id=cid,
                          title=title, why=why, urgency=urgency, due=due, evidence=evidence)


def duty(cid="C1", *, due=date(2027, 4, 15), statutory=date(2027, 4, 15), form="1040",
         extended=date(2027, 10, 15), documents_due=date(2027, 3, 1), assumed=()):
    return ObligationInstance(
        obligation_key=f"{cid}/file/{form}/US/2026", client_id=cid, rule_key="form_1040",
        kind="file", form=form, jurisdiction="US", period_key="2026", statutory_due=statutory,
        due=due, extended_due=extended, documents_due=documents_due,
        from_assumed_facts=tuple(assumed))


def item(cid="C1", doc="W-2", *, asked=DAY - timedelta(days=20), blocking="non_blocking",
         status="outstanding", year=2026):
    return RequestedItem(request_id=f"R-{cid}-{doc}", client_id=cid, tax_year=year,
                         doc_type=doc, blocking=blocking, status=status, requested_at=asked)


class FakeTracked:
    def __init__(self, sim_id, ref, satc_client, form="1040", **kw):
        self.sim = SimpleNamespace(sim_id=sim_id, ref=ref, form=form, satc_workflows=["x"],
                                   prior_ref="", amended_ref="")
        self.satc_client = satc_client
        self.engaged_on = "2027-01-10"
        self.invoice = kw.get("invoice", "")
        self.jobs = kw.get("jobs", {})


class FakeFirm:
    def __init__(self, tracked=(), gate_refusals=(), probes=(), store=""):
        self.t = {tr.sim.sim_id: tr for tr in tracked}
        self.gate_refusals = list(gate_refusals)
        self.probes = list(probes)
        self.cd = SimpleNamespace(store=store)

    def by_satc(self):
        return {tr.satc_client: tr for tr in self.t.values()}

    def by_ref(self):
        return {tr.sim.ref: tr for tr in self.t.values()}

    def by_job(self):
        return {j: tr for tr in self.t.values() for j in tr.jobs.values()}


def ctx(*tracked, billing="satc", **firm_kw):
    return I.Ctx(FakeFirm(tracked, **firm_kw), tax_year=2026, billing_door=billing)


def red(code, s, c=None) -> list:
    hits, _n = I.REGISTRY[code].fn(s, c or I.Ctx(None))
    return hits


# ── A. calendar ──────────────────────────────────────────────────────────────

def test_A1_a_due_date_before_the_statute_goes_red():
    early = duty(due=date(2027, 4, 14))
    assert red("A1", snap(obligations=[early]))
    assert not red("A1", snap(obligations=[duty()]))


def test_A2_engines_that_disagree_go_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    rec = {"_return_type": "individual", "TaxYear": 2026}
    assert red("A2", snap(obligations=[duty(due=date(2027, 4, 16))],
                          cd_records={"2027-0001": rec}), c)
    assert not red("A2", snap(obligations=[duty()], cd_records={"2027-0001": rec}), c)


def test_A3_a_wrong_materials_deadline_goes_red(monkeypatch):
    import settings
    real = settings.firm_fields
    monkeypatch.setattr(settings, "firm_fields",
                        lambda season, rt: {**real(season, rt), "MaterialsDeadline": "March 1, 2027"})
    assert red("A3", snap())


# ── B. Today ─────────────────────────────────────────────────────────────────

def test_B1_two_chase_rows_for_one_client_go_red():
    q = [action("chase_documents"), action("signature_outstanding")]
    assert red("B1", snap(queue=q))
    assert not red("B1", snap(queue=q[:1]))


def test_B2_an_empty_why_goes_red():
    assert red("B2", snap(queue=[action(why="  ")]))


def test_B3_out_of_order_rows_and_a_screen_that_disagrees_go_red():
    q = [action(urgency="soon", cid="C1"), action(urgency="overdue", cid="C2")]
    assert red("B3", snap(queue=q, screen_ids=[a.action_id for a in q]))
    ok = [q[1], q[0]]
    assert red("B3", snap(queue=ok, screen_ids=[ok[1].action_id, ok[0].action_id]))
    assert not red("B3", snap(queue=ok, screen_ids=[a.action_id for a in ok]))


def test_B4_a_queue_that_changes_on_rebuild_goes_red():
    q = [action()]
    assert red("B4", snap(queue=q, queue_again=["something-else"]))
    assert not red("B4", snap(queue=q, queue_again=[q[0].action_id]))


def test_B5_a_read_that_writes_goes_red():
    assert red("B5", snap(hash_before="a", hash_after="b", changed_files=["x/satc_data/m.db"]))
    assert not red("B5", snap(hash_before="a", hash_after="a"))


def test_B6_a_client_waiting_and_not_chased_goes_red():
    assert red("B6", snap(requested=[item()]))
    assert not red("B6", snap(requested=[item()], queue=[action()]))


def test_B7_a_misjudged_urgency_goes_red():
    late = action("deadline_approaching", urgency="soon", due=DAY - timedelta(days=5))
    assert red("B7", snap(queue=[late]))
    assert not red("B7", snap(queue=[replace(late, urgency="overdue")]))


def test_B8_overdue_against_an_extended_return_goes_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    row = action("deadline_approaching", urgency="overdue", due=date(2027, 4, 15))
    assert red("B8", snap(queue=[row], cd_events={"2027-0001": ["extension"]}), c)
    assert not red("B8", snap(queue=[row], cd_events={"2027-0001": []}), c)


def test_B9_an_assumption_that_is_not_stated_goes_red():
    d = duty(assumed=("runs_payroll",))
    row = action("deadline_approaching", evidence=(d.obligation_key,), why="due soon")
    assert red("B9", snap(queue=[row], obligations=[d]))


def test_B10_an_extension_row_that_claims_a_decision_goes_red():
    row = action("extension_candidate", why="The extension has been filed.")
    assert red("B10", snap(queue=[row]))


def test_B11_a_client_with_nothing_this_year_and_no_invite_goes_red():
    job = WQ.a_job("J-9", client_id="C9", tax_year=2025)
    assert red("B11", snap(clients=["C9"], jobs=[job]))
    invite = action("interview_invite", cid="C9")
    assert not red("B11", snap(clients=["C9"], jobs=[job], queue=[invite]))


def test_B12_an_agent_that_sees_other_rows_goes_red():
    q = [action(title="Chase 1")]
    assert red("B12", snap(queue=q, agent={"actions": [{"what": "Other", "urgency": "soon"}]}))
    assert not red("B12", snap(queue=q, agent={"actions": [{"what": "Chase 1", "urgency": "soon"}]}))


def test_B13_asking_a_returning_client_for_a_new_client_document_goes_red():
    job = WQ.a_job("J-1", client_id="C1", tax_year=2026)
    job.intake_answers = {"newSatcClient": "no"}
    row = action("prior_year_question", evidence=("Prior-year return",))
    assert red("B13", snap(queue=[row], jobs=[job]))


# ── C. Work ──────────────────────────────────────────────────────────────────

def _view(stage):
    return StageView(stage=stage, why="w")


def _work(job, stage="prep_ready", score=0.5, factors=None, deadline=None):
    factors = factors or tuple(Factor(k, k, 0.0, 1.0, "", True) for k in
                               ("deadline", "idle", "unblocks", "quick_win"))
    return WorkItem(job=job, view=_view(stage), rank=1, score=score, factors=factors,
                    why="w", deadline=deadline, deadline_known=deadline is not None)


def _board(work=(), stuck=()):
    return Board(workable=tuple(work), not_workable=tuple(stuck), policy=QueuePolicy())


def test_C1_a_job_missing_from_the_board_goes_red():
    job = WQ.a_job("J-1", tax_year=2026)
    assert red("C1", snap(jobs=[job]))
    assert not red("C1", snap(jobs=[job], board=_board([_work(job)])))


def test_C2_a_finished_job_offered_as_workable_goes_red():
    job = WQ.a_job("J-1", tax_year=2026)
    assert red("C2", snap(board=_board([_work(job, stage="ready_to_deliver")])))


def test_C3_delivered_with_no_record_goes_red():
    assert red("C3", snap(page_view={"J-1": _view("delivered")}, deliverables={"J-1": None}))


def test_C4_a_blocked_job_not_shown_waiting_goes_red():
    job = WQ.a_job("J-1", client_id="C1", tax_year=2026)
    s = snap(requested=[item(blocking="blocking")], board=_board([_work(job)]))
    assert red("C4", s)


def test_C5_board_and_page_that_disagree_go_red():
    job = WQ.a_job("J-1", tax_year=2026)
    s = snap(board=_board(stuck=[BlockedItem(job=job, view=_view("not_started"),
                                             waiting_on=(), why="w")]),
             page_view={"J-1": _view("delivered")}, page_stage={"J-1": "delivered"})
    assert red("C5", s)


def test_C6_a_board_out_of_score_order_goes_red():
    a, b = WQ.a_job("J-a", tax_year=2026), WQ.a_job("J-b", tax_year=2026)
    assert red("C6", snap(board=_board([_work(a, score=0.1), _work(b, score=0.9)])))


def test_C7_a_dominated_job_ranked_first_goes_red():
    weak = tuple(Factor(k, k, 0.1, 1.0, "", True) for k in ("deadline", "idle", "unblocks", "quick_win"))
    strong = tuple(Factor(k, k, 0.9, 1.0, "", True) for k in ("deadline", "idle", "unblocks", "quick_win"))
    a, b = WQ.a_job("J-a", tax_year=2026), WQ.a_job("J-b", tax_year=2026)
    assert red("C7", snap(board=_board([_work(a, factors=weak), _work(b, factors=strong)])))


def test_C8_a_deadline_factor_that_lies_about_knowing_goes_red():
    job = WQ.a_job("J-1", tax_year=2026, obligation_key="nothing-on-file")
    assert red("C8", snap(board=_board([_work(job)])))


def test_C9_an_extended_job_ranked_on_the_original_date_goes_red():
    job = WQ.a_job("J-1", client_id="C1", tax_year=2026)
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    s = snap(board=_board([_work(job, deadline=date(2027, 4, 15))]),
             cd_events={"2027-0001": ["extension"]})
    assert red("C9", s, c)


# ── D. chase lists ───────────────────────────────────────────────────────────

def _waiting(cid="C1", since=DAY - timedelta(days=4)):
    return Waiting(client_id=cid, client=cid, request_id=f"R-{cid}", doc_type="W-2",
                   asked_for="W-2", tax_year=2026, since=since)


def test_D1_a_sweep_that_does_not_add_up_goes_red():
    assert red("D1", snap(requested=[item()], sweep=Sweep(rows=[], requests=1)))
    assert not red("D1", snap(requested=[item()], sweep=Sweep(rows=[_waiting()], requests=1)))


def test_D2_a_sweep_out_of_order_or_listing_today_goes_red():
    rows = [_waiting("C1", DAY - timedelta(days=2)), _waiting("C2", DAY - timedelta(days=9))]
    assert red("D2", snap(sweep=Sweep(rows=rows, requests=2)))
    assert red("D2", snap(sweep=Sweep(rows=[_waiting(since=DAY)], requests=1)))


def _standing(ref, missing=(), overdue=False):
    lines = [SimpleNamespace(document=d, field=f) for d, f in missing]
    return SimpleNamespace(ref=ref, missing=lines, overdue=overdue, expected=lines,
                           waiting_days=lambda today=None: 3)


def test_D3_an_unsigned_engagement_left_off_the_list_goes_red():
    st = _standing("2027-0001", [("Form 8879", "TaxpayerName")])
    assert red("D3", snap(cd_standing={"2027-0001": st}, cd_waiting=[]))
    assert not red("D3", snap(cd_standing={"2027-0001": st}, cd_waiting=[st]))


def test_D4_a_disengaged_engagement_still_chased_goes_red():
    st = _standing("2027-0001", [("Form 8879", "TaxpayerName")])
    assert red("D4", snap(cd_waiting=[st], cd_events={"2027-0001": ["disengagement"]}))
    assert not red("D4", snap(cd_waiting=[st], cd_events={"2027-0001": []}))


# ── E. season board ──────────────────────────────────────────────────────────

def _due(ref, when, kind="filing", days=-3):
    import deadlines
    return deadlines.Due(ref=ref, client="Testclient", return_type="individual_1040",
                         when=when, what="return due", kind=kind, days=days)


def test_E1_an_engagement_that_vanishes_from_the_board_goes_red():
    assert red("E1", snap(cd_records={"2027-0001": {}}, cd_board=([], [])))
    assert not red("E1", snap(cd_records={"2027-0001": {}}, cd_board=([], ["2027-0001"])))


def test_E2_a_board_out_of_order_goes_red():
    rows = [_due("2027-0002", date(2027, 4, 15)), _due("2027-0001", date(2027, 3, 15))]
    assert red("E2", snap(cd_board=(rows, [])))


def test_E3_a_placed_row_with_no_readable_year_goes_red():
    assert red("E3", snap(cd_board=([_due("2027-0001", date(2027, 4, 15))], []),
                          cd_records={"2027-0001": {"_return_type": "individual", "TaxYear": 0}}))


def test_E4_a_season_command_that_prints_another_board_goes_red():
    rows = [_due("2027-0001", date(2027, 4, 15))]
    out = f"1 engagement(s) read, {DAY.isoformat()}\n\n  nothing due in that window.\n"
    assert red("E4", snap(cd_board=(rows, []), cd_refs=["2027-0001"], cd_season_out=out))


def test_E5_an_amended_return_overdue_at_original_dates_goes_red(tmp_path):
    ref = "2027-0101"
    (tmp_path / ref).mkdir()
    (tmp_path / ref / "interview.json").write_text('{"return_basis": "amended"}', "utf-8")
    c = I.Ctx(FakeFirm(store=str(tmp_path)))
    s = snap(cd_board=([_due(ref, date(2026, 4, 15), days=-300)], []), cd_records={ref: {}})
    assert red("E5", s, c)


def test_E6_a_closed_engagement_still_overdue_goes_red():
    s = snap(cd_board=([_due("2027-0001", date(2027, 4, 15))], []),
             cd_closed={"2027-0001": {"filed_form": "1040"}})
    assert red("E6", s)
    assert not red("E6", snap(cd_board=([_due("2027-0001", date(2027, 4, 15))], [])))


def test_E7_an_extended_engagement_at_the_original_date_goes_red():
    s = snap(cd_board=([_due("2027-0001", date(2027, 4, 15))], []),
             cd_events={"2027-0001": ["extension"]})
    assert red("E7", s)


# ── F. gates ─────────────────────────────────────────────────────────────────

def test_F1_a_clear_gate_with_a_missing_authorization_goes_red():
    st = _standing("2027-0001", [("Form 8879", "TaxpayerName")])
    s = snap(cd_standing={"2027-0001": st},
             cd_may_file={"2027-0001": SimpleNamespace(clear=True)})
    assert red("F1", s)
    s.cd_may_file["2027-0001"] = SimpleNamespace(clear=False)
    assert not red("F1", s)


def test_F2_paid_without_billed_goes_red():
    steps = [SimpleNamespace(key="billed", reached=False), SimpleNamespace(key="paid", reached=True)]
    assert red("F2", snap(cd_stages={"2027-0001": steps}))


def test_F3_a_close_out_sweep_that_skips_goes_red():
    assert red("F3", snap(cd_interviews={"2027-0001", "2027-0002"}, cd_sweep_count=1))


# ── G. across the stores ─────────────────────────────────────────────────────

def test_G1_a_ref_no_satc_engagement_carries_goes_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    assert red("G1", snap(cd_records={"2027-0001": {}}, engagement_refs={}), c)
    assert not red("G1", snap(cd_records={"2027-0001": {}},
                              engagement_refs={"2027-0001": ["C1"]}), c)


def test_G2_a_price_that_differs_from_the_estimate_goes_red(tmp_path, monkeypatch):
    ref = "2027-0001"
    (tmp_path / ref).mkdir()
    (tmp_path / ref / "record.json").write_text('{"EstimateTotal": "$100.00"}', "utf-8")
    monkeypatch.setenv("SATC_ENGAGEMENTS", str(tmp_path))
    c = ctx(FakeTracked("SIM-001", ref, "C1"))
    assert red("G2", snap(cd_records={ref: {"EstimateTotal": "$325.00"}}), c)
    assert not red("G2", snap(cd_records={ref: {"EstimateTotal": "$100.00"}}), c)


def test_G4_a_cutoff_that_is_not_the_date_the_client_was_told_goes_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    assert red("G4", snap(obligations=[duty(documents_due=date(2027, 3, 1))]), c)
    assert not red("G4", snap(obligations=[duty(documents_due=date(2027, 3, 25))]), c)


def test_G5_a_chase_for_a_closed_engagement_goes_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    assert red("G5", snap(queue=[action()], cd_closed={"2027-0001": {"x": 1}}), c)


def test_G6_a_filing_past_an_unpaid_satc_bill_goes_red():
    inv = SimpleNamespace(invoice_id="2027-0001", total=100, is_paid=False, client_id="C1",
                          tax_year=2026)
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1", invoice="2027-0001"))
    s = snap(invoices=[inv], payments=[], cd_closed={"2027-0001": {"x": 1}}, cd_invoices={})
    assert red("G6", s, c)


def test_G6_the_other_door_goes_red_too():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1", invoice="2027-0001"),
            billing="client_documents")
    s = snap(invoices=[], cd_invoices={"2027-0001": [{"InvoiceNumber": "2027-0001"}]})
    assert red("G6", s, c)


def test_G8_an_extension_flag_inside_the_told_date_goes_red():
    c = ctx(FakeTracked("SIM-001", "2027-0001", "C1"))
    row = action("extension_candidate")
    assert red("G8", snap(day=date(2027, 3, 10), queue=[row]), c)
    assert not red("G8", snap(day=date(2027, 3, 26), queue=[row]), c)


# ── L. door outcomes; K. clock ───────────────────────────────────────────────

def _refusal(prefix):
    return {"day": DAY.isoformat(), "sim": "SIM-001", "ref": "2027-0001", "kind": "extension",
            "call": {"door": "cli"},
            "output": f"REFUSED BY THE PRE-SEND GATE.\n    {prefix} [x]: nope\n"}


def test_L1_a_compliance_refusal_goes_red_and_is_not_repeated():
    c = ctx(gate_refusals=[_refusal("compliance")])
    assert red("L1", snap(), c)
    c.prev_day = DAY.isoformat()                    # already reported on an earlier read
    assert not red("L1", snap(), c)


def test_L3_a_package_disagreement_refusal_goes_red():
    assert red("L3", snap(), ctx(gate_refusals=[_refusal("agrees")]))
    assert not red("L3", snap(), ctx(gate_refusals=[_refusal("compliance")]))


def test_L2_following_every_instruction_and_billing_twice_goes_red():
    probe = {"day": DAY.isoformat(), "sim": "SIM-001", "ref": "2027-0001", "estimate": "$100.00",
             "lines": [("return_1040", "100.00", "n"), ("return_state", "100.00", "n")],
             "draft_total": "200.00", "call": {"door": "http"}}
    assert red("L2", snap(), ctx(probes=[probe]))
    assert not red("L2", snap(), ctx(probes=[dict(probe, draft_total="100.00")]))


def test_K1_the_clock_audit_reports_a_read_that_moved():
    right = {"cli season --today D": "a", "other": [1]}
    assert clock.leaks(right, {"cli season --today D": "b", "other": [1]}) == ["cli season --today D"]
    assert clock.leaks(right, dict(right)) == []


def test_every_registered_invariant_has_a_red_test_here():
    here = Path(__file__).read_text(encoding="utf-8")
    missing = [code for code in I.REGISTRY if f"def test_{code}_" not in here]
    assert not missing, f"no planted-violation test for {missing}"


@pytest.mark.parametrize("code", sorted(I.REGISTRY))
def test_every_invariant_names_its_rule_and_source(code):
    inv = I.REGISTRY[code]
    assert inv.rule.strip() and inv.sources
    assert inv.kind in ("failure", "cross_store", "known", "recorded_deferral")
