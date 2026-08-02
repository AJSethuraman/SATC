"""The action queue — the practice noticing things so the owner doesn't have to.

Two properties matter more than any individual rule:

  * **Nothing is invented.** Every action's ``why`` names the records it came
    from, so a proposal can be audited in one line rather than re-derived.
  * **The queue does not become noise.** Ids are stable across regeneration, and
    two rows never say the same thing — a queue the owner learns to ignore is
    worse than no queue.
"""

from __future__ import annotations

from datetime import date, timedelta

from satc.actions import ActionQueue, ProposedAction, build_queue
from satc.actions.propose import (
    _URGENCY_ORDER,
    ask_prior_year_questions,
    chase_outstanding,
    chase_signature,
    deadline_pressure,
    extension_candidate,
    invoice_overdue,
    invoice_unissued,
    unbilled_work,
    undated_work,
)
from satc.models.evidence import ReceivedDocument, RequestedItem

TODAY = date(2026, 3, 10)


def _doc(doc_type, year=2025, status="Requested", *, client="C", asked_days_ago=10, note=""):
    """An open REQUEST by default; status="Received" makes it an ARRIVAL."""
    if status == "Received":
        return ReceivedDocument(document_id=f"{client}-{doc_type}-{year}",
                                client_id=client, tax_year=year, doc_type=doc_type,
                                note=note)
    return RequestedItem(request_id=f"req-{client}-{doc_type}-{year}", client_id=client,
                         tax_year=year, doc_type=doc_type, request_text=note,
                         requested_at=TODAY - timedelta(days=asked_days_ago))


def _is_ask(row):
    return isinstance(row, RequestedItem)


def _queue(rows, **kw):
    return build_queue(clients=["C"],
                       requested=[r for r in rows if _is_ask(r)],
                       received=[r for r in rows if not _is_ask(r)],
                       tax_year=2025, today=TODAY, **kw)


# --- chasing ------------------------------------------------------------------

def test_outstanding_documents_become_a_chase_with_the_evidence_in_the_reason():
    action = chase_outstanding([_doc("1099-DIV"), _doc("K-1-1065")],
                               client_id="C", tax_year=2025, today=TODAY)
    assert action is not None
    assert "1099-DIV" in action.why and "K-1-1065" in action.why
    assert "10 days ago" in action.why
    assert action.template_key == "missing_items"


def test_a_fresh_request_is_not_chased_yet():
    """Asking twice in one day trains a client to ignore you."""
    assert chase_outstanding([_doc("1099-DIV", asked_days_ago=1)],
                             client_id="C", tax_year=2025, today=TODAY) is None


def test_a_long_wait_escalates_the_urgency():
    soon = chase_outstanding([_doc("1099-DIV", asked_days_ago=5)],
                             client_id="C", tax_year=2025, today=TODAY)
    urgent = chase_outstanding([_doc("1099-DIV", asked_days_ago=20)],
                               client_id="C", tax_year=2025, today=TODAY)
    assert soon.urgency == "soon"
    assert urgent.urgency == "urgent"


def test_nothing_outstanding_means_no_chase():
    """No open REQUESTS — arrivals are a different list entirely now."""
    assert chase_outstanding([], client_id="C", tax_year=2025, today=TODAY) is None


# --- the signature, which blocks the filing ----------------------------------

def test_an_unsigned_8879_is_called_out_separately():
    """It does not just delay the file — it blocks transmission entirely."""
    action = chase_signature([_doc("Form 8879", asked_days_ago=9)],
                             client_id="C", tax_year=2025, today=TODAY)
    assert action is not None
    assert "nothing can be transmitted" in action.why
    assert action.urgency == "urgent"


def test_the_queue_does_not_say_chase_them_twice():
    """An 8879 chase already covers the outstanding list. Two rows saying the
    same thing is how a queue starts getting ignored."""
    queue = _queue([_doc("Form 8879"), _doc("1099-DIV")])
    kinds = [a.kind for a in queue.actions]
    assert "signature_outstanding" in kinds
    assert "chase_documents" not in kinds


# --- the prior-year question --------------------------------------------------

def test_a_document_missing_since_last_year_becomes_a_question():
    action = ask_prior_year_questions(
        [_doc("1099-INT", 2024, "Received", note="Lakeside Savings"),
         _doc("W-2", 2024, "Received"), _doc("W-2", 2025, "Received")],
        client_id="C", tax_year=2025, prior_year=2024)
    assert action is not None
    assert "1099-INT" in action.why
    assert "not even requested" in action.why
    assert action.template_key == "prior_year_check"


def test_nothing_missing_means_no_question():
    assert ask_prior_year_questions(
        [_doc("W-2", 2024, "Received"), _doc("W-2", 2025, "Received")],
        client_id="C", tax_year=2025, prior_year=2024) is None


# --- deadlines from the clock -------------------------------------------------

def _duties(**kw):
    from satc.obligations.profile import ObligationProfile, materialise

    return materialise(ObligationProfile(client_id="C", entity_type="INDIVIDUAL", **kw), 2025)


def test_an_approaching_deadline_surfaces_with_its_date():
    actions = deadline_pressure(_duties(), client_id="C", today=date(2026, 4, 1))
    assert actions
    assert any("1040" in a.title for a in actions)
    assert all(a.due is not None for a in actions)


def test_a_distant_deadline_stays_quiet():
    assert deadline_pressure(_duties(), client_id="C", today=date(2025, 6, 1)) == []


def test_an_overdue_deadline_says_so():
    actions = deadline_pressure(_duties(), client_id="C", today=date(2026, 4, 20))
    overdue = [a for a in actions if a.urgency == "overdue"]
    assert overdue
    assert "overdue by" in overdue[0].why


def test_a_deadline_built_on_an_assumption_admits_it():
    """A duty derived from an unconfirmed fact is a guess wearing a deadline."""
    from satc.obligations.profile import ProfileFact

    duties = _duties(runs_payroll=ProfileFact("yes"))     # no basis given
    actions = deadline_pressure(duties, client_id="C", today=date(2026, 4, 1))
    assert any("unconfirmed assumption" in a.why for a in actions)


# --- the extension flag -------------------------------------------------------

def test_a_passed_cutoff_with_an_incomplete_file_flags_an_extension():
    duties = _duties()
    action = extension_candidate([_doc("K-1-1065")], duties, client_id="C",
                                 tax_year=2025, today=date(2026, 3, 20))
    assert action is not None
    assert "cutoff was Mar 01" in action.why
    assert "written authorisation" in action.why


def test_it_never_says_the_extension_is_filed_or_decided():
    """Filing without the client's written permission can destroy their
    reasonable-cause defence. This is a conversation, not an action."""
    action = extension_candidate([_doc("K-1-1065")], _duties(), client_id="C",
                                 tax_year=2025, today=date(2026, 3, 20))
    assert action.template_key == ""       # no draft to fire off
    assert "Likely extension" in action.title


def test_a_complete_file_past_the_cutoff_is_not_an_extension_candidate():
    """Past the cutoff but nothing outstanding — no extension needed."""
    action = extension_candidate([], _duties(), client_id="C", tax_year=2025,
                                 today=date(2026, 3, 20))
    assert action is None


# --- the queue as a whole -----------------------------------------------------

def test_the_queue_is_ordered_by_how_much_it_hurts_to_leave():
    queue = build_queue(clients=["C"], requested=[_doc("1099-DIV")],
                        obligations=_duties(), tax_year=2025, today=date(2026, 4, 20))
    urgencies = [a.urgency for a in queue.actions]
    order = {"overdue": 0, "urgent": 1, "soon": 2, "routine": 3}
    assert urgencies == sorted(urgencies, key=lambda u: order[u])


def test_regenerating_the_queue_produces_the_same_ids():
    """A dismissed action that reappears every refresh turns the queue into noise."""
    docs = [_doc("1099-DIV"), _doc("K-1-1065")]
    a = [x.action_id for x in _queue(docs).actions]
    b = [x.action_id for x in _queue(docs).actions]
    assert a == b and a


def test_ids_do_not_depend_on_when_the_queue_was_built():
    docs = [_doc("1099-DIV", asked_days_ago=10)]
    early = build_queue(clients=["C"], requested=docs, tax_year=2025, today=TODAY)
    later = build_queue(clients=["C"], requested=docs, tax_year=2025,
                        today=TODAY + timedelta(days=5))
    assert {a.action_id for a in early.actions} == {a.action_id for a in later.actions}


def test_the_counts_view_is_small_enough_for_a_model_to_read():
    """Doctrine rule 2: hand a small model categories, not rows."""
    queue = build_queue(clients=["C"], requested=[_doc("1099-DIV")],
                        obligations=_duties(), tax_year=2025, today=date(2026, 4, 1))
    counts = queue.counts()
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in counts.items())
    assert len(counts) <= 8


def test_one_click_actions_are_the_ones_with_a_draft():
    queue = _queue([_doc("1099-DIV")])
    assert all(a.template_key for a in queue.one_click())


def test_an_empty_practice_says_so_rather_than_inventing_work():
    queue = build_queue(clients=["C"], tax_year=2025, today=TODAY,
                        engaged_clients=["C"])
    assert len(queue) == 0
    assert queue.summary_line() == "Nothing needs you right now."


def test_the_summary_counts_what_is_already_drafted():
    queue = _queue([_doc("1099-DIV")])
    assert "already drafted" in queue.summary_line()


def test_every_action_carries_auditable_evidence():
    """A proposal the owner cannot check in one line is one they have to redo."""
    queue = build_queue(clients=["C"], requested=[_doc("1099-DIV"), _doc("Form 8879")],
                        obligations=_duties(), tax_year=2025, today=date(2026, 4, 1))
    for action in queue.actions:
        assert action.why.strip()
        assert action.title.strip()
        assert not action.is_from_model      # all of these are deterministic


def test_nothing_in_the_queue_writes_anything():
    """Propose, never dispose."""
    docs = [_doc("1099-DIV"), _doc("Form 8879")]
    before = [(d.request_id, d.status) for d in docs]
    build_queue(clients=["C"], requested=docs, obligations=_duties(),
                tax_year=2025, today=date(2026, 4, 1))
    assert [(d.request_id, d.status) for d in docs] == before


# --- the money ----------------------------------------------------------------
#
# The queue chased paper for a year without ever mentioning that the paper had
# been delivered and never charged for. These are the rows that say so.


def _job(stage="delivered", *, client="C", year=2025, job_id="job-1",
         engagement_type="Individual 1040"):
    from satc.models.work import Job

    return Job(job_id=job_id, client_id=client, workflow_key="individual_1040",
               engagement_type=engagement_type, tax_year=year,
               period_key=str(year), stage=stage)


def _invoice(*, client="C", year=2025, number="2026-0001", issued=None,
             due_in_days=30, paid=None, services=("return_1040",),
             performed_on=None):
    """A draft by default; ``issued=<date>`` fixes it and starts the clock."""
    from satc.billing.invoice import Invoice

    inv = Invoice(invoice_id=number, client_id=client, tax_year=year)
    for code in services:
        inv.add(code, performed_on=performed_on)
    if issued is not None:
        inv.issue(on=issued, due_in_days=due_in_days)
    inv.paid_on = paid
    return inv


def _payment(amount, *, client="C", invoice="2026-0001", days_ago=5):
    """Money that arrived, recorded as a fact in the ledger."""
    from decimal import Decimal

    from satc.billing.payment import MatchBasis, Method, Payment

    return Payment(client_id=client, amount=Decimal(str(amount)),
                   received_on=TODAY - timedelta(days=days_ago),
                   method=Method.CHECK, reference=invoice, invoice_id=invoice,
                   basis=MatchBasis.REFERENCE)


# --- work that went out the door and was never billed -------------------------

def test_delivered_work_with_no_invoice_is_money_the_practice_lost():
    """Nothing else in the system would ever mention this again: the client is
    happy, the file looks finished, and the fee was never asked for."""
    action = unbilled_work([_job("delivered")], [], client_id="C", tax_year=2025)
    assert action is not None
    assert action.kind == "unbilled_work"
    assert "Individual 1040" in action.why
    assert "2025" in action.why
    assert "no invoice" in action.why
    assert action.evidence == ("job-1",)


def test_work_still_in_prep_is_not_billable_yet():
    """Billing happens at delivery. Chasing a fee for work in progress is worse
    than not chasing at all."""
    assert unbilled_work([_job("in_prep")], [], client_id="C", tax_year=2025) is None


def test_delivered_work_that_was_actually_billed_says_nothing():
    invoices = [_invoice(issued=TODAY - timedelta(days=3))]
    assert unbilled_work([_job("delivered")], invoices,
                         client_id="C", tax_year=2025) is None


def test_an_invoice_for_a_different_year_does_not_count_as_billed():
    """Last year's bill is not this year's."""
    invoices = [_invoice(year=2024, issued=TODAY - timedelta(days=3))]
    action = unbilled_work([_job("delivered")], invoices,
                           client_id="C", tax_year=2025)
    assert action is not None


def test_a_closed_file_that_was_never_billed_is_louder_than_a_fresh_delivery():
    """A delivery this week is the next thing to do. A file marked complete with
    no invoice behind it is money already gone."""
    fresh = unbilled_work([_job("delivered")], [], client_id="C", tax_year=2025)
    closed = unbilled_work([_job("complete")], [], client_id="C", tax_year=2025)
    assert fresh.urgency == "soon"
    assert closed.urgency == "urgent"


def test_three_unbilled_jobs_are_one_problem_not_three_rows():
    jobs = [_job(job_id="j1", engagement_type="Individual 1040"),
            _job(job_id="j2", engagement_type="Rental schedule"),
            _job(job_id="j3", engagement_type="Rental schedule")]
    action = unbilled_work(jobs, [], client_id="C", tax_year=2025)
    assert action is not None
    assert "Individual 1040" in action.why and "Rental schedule" in action.why
    assert set(action.evidence) == {"j1", "j2", "j3"}


# --- the invoice that went out and was never paid -----------------------------

def test_an_overdue_invoice_names_the_number_the_amount_and_how_late_it_is():
    inv = _invoice(number="2026-0007", issued=TODAY - timedelta(days=40))
    rows = invoice_overdue([inv], client_id="C", today=TODAY)
    assert len(rows) == 1
    assert "2026-0007" in rows[0].why
    assert f"{inv.total:,.2f}" in rows[0].why
    assert "10 days" in rows[0].why


def test_an_overdue_invoice_is_one_click():
    rows = invoice_overdue([_invoice(issued=TODAY - timedelta(days=40))],
                           client_id="C", today=TODAY)
    assert rows[0].template_key == "invoice_cover"
    assert rows[0].due is not None


def test_how_late_it_is_decides_how_loud_it_is():
    def urgency(days_since_issue):
        rows = invoice_overdue([_invoice(issued=TODAY - timedelta(days=days_since_issue))],
                               client_id="C", today=TODAY)
        return rows[0].urgency

    assert urgency(35) == "soon"        # 5 days past due — probably in an inbox
    assert urgency(60) == "urgent"      # 30 days past due
    assert urgency(120) == "overdue"    # 90 days past due — a collection problem


def test_a_paid_invoice_is_not_chased():
    inv = _invoice(issued=TODAY - timedelta(days=40), paid=TODAY - timedelta(days=2))
    assert invoice_overdue([inv], client_id="C", today=TODAY) == []


def test_an_invoice_still_within_its_terms_is_quiet():
    assert invoice_overdue([_invoice(issued=TODAY - timedelta(days=5))],
                           client_id="C", today=TODAY) == []


def test_two_overdue_invoices_are_two_facts_with_their_own_numbers():
    """The client will ask about one of them by number. Collapsing them loses
    the only thing that identifies which."""
    rows = invoice_overdue(
        [_invoice(number="2026-0001", issued=TODAY - timedelta(days=40)),
         _invoice(number="2026-0002", issued=TODAY - timedelta(days=50))],
        client_id="C", today=TODAY)
    assert len({r.action_id for r in rows}) == 2


# --- what is owed comes from the ledger, not from the flag (principle 11b) -----


def test_a_settled_invoice_is_not_chased_because_nobody_ticked_the_flag():
    """Money arriving is a FACT; "paid" is a CONCLUSION computed from the
    ledger. Reading ``paid_on`` chases a client for money they already sent —
    the confident wrong answer, addressed to the client."""
    inv = _invoice(issued=TODAY - timedelta(days=40))
    assert inv.paid_on is None, "the flag was never written; the ledger has it"
    assert invoice_overdue([inv], [_payment(inv.total)],
                           client_id="C", today=TODAY) == []


def test_a_part_paid_invoice_is_chased_for_the_balance_not_the_total():
    """Asking for $450 when $300 has arrived is the letter that ends a
    relationship. The row says what is genuinely still owed."""
    inv = _invoice(issued=TODAY - timedelta(days=40))          # $450.00
    rows = invoice_overdue([inv], [_payment("300.00")], client_id="C", today=TODAY)
    assert len(rows) == 1
    assert "$150.00 still owed" in rows[0].title
    assert "$300.00 has been received" in rows[0].why
    assert "$150.00 is still owed" in rows[0].why


def test_money_against_another_invoice_does_not_settle_this_one():
    inv = _invoice(number="2026-0005", issued=TODAY - timedelta(days=40))
    rows = invoice_overdue([inv], [_payment(inv.total, invoice="2026-0006")],
                           client_id="C", today=TODAY)
    assert len(rows) == 1
    assert f"{inv.total:,.2f}" in rows[0].title


def test_the_flag_still_speaks_for_money_that_arrived_before_the_ledger():
    """``paid_on`` is the only record of a payment taken before the ledger
    existed, so it is the FALLBACK — consulted when no payment names the
    invoice at all. Where the ledger does say something, it decides, even when
    it contradicts the flag."""
    inv = _invoice(issued=TODAY - timedelta(days=40), paid=TODAY - timedelta(days=2))
    assert invoice_overdue([inv], [], client_id="C", today=TODAY) == []
    contradicted = invoice_overdue([inv], [_payment("50.00")],
                                   client_id="C", today=TODAY)
    assert len(contradicted) == 1
    assert "$400.00 still owed" in contradicted[0].title


def test_the_queue_takes_the_ledger_through_the_seam():
    """``build_queue(..., payments=...)`` — the caller hands over
    ``store.load_payments()``, and the money rows are computed from it."""
    inv = _invoice(issued=TODAY - timedelta(days=40))
    queue = build_queue(clients=["C"], invoices=[inv], payments=[_payment(inv.total)],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert [a.kind for a in queue.actions] == []


# --- the draft nobody ever sent -----------------------------------------------

def test_a_draft_left_sitting_surfaces_before_anyone_asks_about_it():
    rows = invoice_unissued([_invoice(performed_on=TODAY - timedelta(days=21))],
                            client_id="C", today=TODAY)
    assert len(rows) == 1
    assert "never been issued" in rows[0].why
    assert "21 days" in rows[0].why


def test_a_draft_written_this_morning_is_not_nagged_about():
    """Billing in progress is not a problem."""
    assert invoice_unissued([_invoice(performed_on=TODAY - timedelta(days=1))],
                            client_id="C", today=TODAY) == []


def test_a_draft_left_a_month_gets_louder():
    rows = invoice_unissued([_invoice(performed_on=TODAY - timedelta(days=45))],
                            client_id="C", today=TODAY)
    assert rows[0].urgency == "urgent"


def test_an_undated_draft_does_not_invent_how_long_it_has_sat():
    """No line carries a date, so the practice holds no fact about the age.
    Principle 1 — say what is known and claim nothing more."""
    rows = invoice_unissued([_invoice(performed_on=None)], client_id="C", today=TODAY)
    assert len(rows) == 1
    assert "day" not in rows[0].why
    assert rows[0].urgency == "routine"


def test_an_empty_draft_is_not_a_row_about_zero_dollars():
    from satc.billing.invoice import Invoice

    shell = Invoice(invoice_id="2026-0009", client_id="C", tax_year=2025)
    assert invoice_unissued([shell], client_id="C", today=TODAY) == []


def test_an_issued_invoice_is_not_also_an_unissued_one():
    assert invoice_unissued([_invoice(issued=TODAY - timedelta(days=40))],
                            client_id="C", today=TODAY) == []


# --- one problem, one row (principle 13) --------------------------------------

def test_an_overdue_invoice_does_not_also_say_the_year_is_unbilled():
    """The client owes you for the 2025 work. Saying that twice — once as an
    unpaid bill and once as work you forgot to bill — is how the owner learns to
    scroll past the row that mattered."""
    queue = build_queue(clients=["C"], jobs=[_job("complete")],
                        invoices=[_invoice(issued=TODAY - timedelta(days=60))],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    kinds = [a.kind for a in queue.actions]
    assert "invoice_overdue" in kinds
    assert "unbilled_work" not in kinds


def test_a_draft_invoice_also_stands_the_unbilled_row_down():
    queue = build_queue(clients=["C"], jobs=[_job("delivered")],
                        invoices=[_invoice(performed_on=TODAY - timedelta(days=21))],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    kinds = [a.kind for a in queue.actions]
    assert kinds.count("invoice_unissued") == 1
    assert "unbilled_work" not in kinds


def test_delivered_work_with_no_bill_anywhere_still_reaches_the_queue():
    queue = build_queue(clients=["C"], jobs=[_job("delivered")],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert [a.kind for a in queue.actions] == ["unbilled_work"]


def test_the_money_rows_keep_their_ids_across_a_rebuild():
    """A dismissed invoice chase that reappears every refresh is worse than no
    chase at all."""
    def ids(today):
        queue = build_queue(clients=["C"], jobs=[_job("complete", client="D")],
                            invoices=[_invoice(issued=TODAY - timedelta(days=40)),
                                      _invoice(number="2026-0002",
                                               performed_on=TODAY - timedelta(days=20))],
                            engaged_clients=["C", "D"], tax_year=2025, today=today)
        return {a.action_id for a in queue.actions}

    assert ids(TODAY) == ids(TODAY + timedelta(days=6))


def test_every_money_row_is_auditable_in_one_line():
    queue = build_queue(clients=["C", "D"], jobs=[_job("complete", client="D")],
                        invoices=[_invoice(issued=TODAY - timedelta(days=40)),
                                  _invoice(number="2026-0002",
                                           performed_on=TODAY - timedelta(days=20))],
                        engaged_clients=["C", "D"], tax_year=2025, today=TODAY)
    money = [a for a in queue.actions
             if a.kind in ("unbilled_work", "invoice_overdue", "invoice_unissued")]
    assert len(money) == 3
    for action in money:
        assert action.why.strip() and action.title.strip()
        assert not action.is_from_model


def test_the_queue_still_says_nothing_when_there_is_no_money_to_chase():
    queue = build_queue(clients=["C"], jobs=[_job("in_prep")], invoices=[],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert queue.summary_line() == "Nothing needs you right now."


# --- the row and the draft have to be about the same invoice ------------------


def _today_html(actions, *, tax_year=2025):
    """The Today screen as it is actually served, for a queue we chose.

    Rendered through the real app so the links are the ones the owner clicks —
    a test against ``url_for`` in isolation passes whether or not the template
    ever calls it with anything.
    """
    from flask import render_template

    from satc.app.server import create_app

    app = create_app()
    with app.test_request_context("/today"):
        return render_template("today.html", title="Today",
                               queue=ActionQueue(actions=list(actions),
                                                 generated_for=TODAY),
                               tax_year=tax_year, as_of=TODAY, hidden_count=0,
                               names={"C": "Client C"})


def test_an_overdue_row_names_the_invoice_it_is_about():
    rows = invoice_overdue(
        [_invoice(number="2026-0003", issued=TODAY - timedelta(days=40)),
         _invoice(number="2026-0004", issued=TODAY - timedelta(days=50))],
        client_id="C", today=TODAY)
    assert {r.invoice_id for r in rows} == {"2026-0003", "2026-0004"}
    for row in rows:
        assert row.invoice_id in row.title


def test_the_draft_link_carries_the_invoice_the_row_is_about():
    """With two overdue invoices, a link built from client + year alone lets the
    comms screen merge from whichever is newest — so the row titled "Invoice
    2026-0003 unpaid" opens a draft quoting a different number and a different
    amount. A figure in a client-facing draft that is not the fact the row
    asserts is principle 1."""
    rows = invoice_overdue(
        [_invoice(number="2026-0003", issued=TODAY - timedelta(days=40)),
         _invoice(number="2026-0004", issued=TODAY - timedelta(days=50))],
        client_id="C", today=TODAY)
    html = _today_html(rows)
    assert "invoice=2026-0003" in html
    assert "invoice=2026-0004" in html


def test_a_row_with_no_invoice_behind_it_does_not_pretend_to_have_one():
    action = ProposedAction(action_id="a", kind="chase_documents", client_id="C",
                            title="Chase", why="because", template_key="missing_items")
    assert "invoice=" not in _today_html([action])


def test_the_unissued_row_opens_the_invoice_rather_than_a_client_to_hunt_through():
    rows = invoice_unissued([_invoice(number="2026-0009",
                                      performed_on=TODAY - timedelta(days=21))],
                            client_id="C", today=TODAY)
    assert rows[0].invoice_id == "2026-0009"
    html = _today_html(rows)
    assert "/invoices/2026-0009" in html
    assert "Open client" not in html


# --- standing a row down must not turn the volume down ------------------------


def test_an_abandoned_draft_is_never_quieter_than_no_draft_at_all():
    """Half-writing a bill and giving up is strictly worse than never writing
    one: the work is out, the fee is unasked-for, and now the drafting is done
    too, so nobody comes back to it. The stand-down was there to remove a
    duplicate, not to downgrade the problem."""
    def loudest(**kw):
        queue = build_queue(clients=["C"], jobs=[_job("complete")],
                            engaged_clients=["C"], tax_year=2025, today=TODAY, **kw)
        return min(_URGENCY_ORDER[a.urgency] for a in queue.actions)

    # An undated draft: the invoice_unissued row on its own is only "routine".
    abandoned = build_queue(clients=["C"], jobs=[_job("complete")],
                            invoices=[_invoice(performed_on=None)],
                            engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert [a.kind for a in abandoned.actions] == ["invoice_unissued"]
    assert abandoned.actions[0].urgency == "urgent"
    assert "already delivered" in abandoned.actions[0].why
    assert loudest(invoices=[_invoice(performed_on=None)]) <= loudest(invoices=[])


def test_an_invoice_that_actually_went_out_is_allowed_to_be_calmer():
    """An issued bill five days past due HAS asked the client for the money.
    Escalating that to "you never billed for finished work" is the opposite
    mistake, and it teaches the owner to ignore the loud rows."""
    queue = build_queue(clients=["C"], jobs=[_job("complete")],
                        invoices=[_invoice(issued=TODAY - timedelta(days=35))],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert [a.kind for a in queue.actions] == ["invoice_overdue"]
    assert queue.actions[0].urgency == "soon"


def test_a_year_that_is_billed_and_paid_does_not_escalate_an_unrelated_draft():
    """The escalation clause asked what the year looks like with EVERY invoice
    thrown away, so a year that was billed AND settled still read as "nothing
    has ever been billed" and pushed an unrelated draft to urgent — an urgency
    the settled invoice beside it on the same screen flatly contradicts. What a
    row claims has to agree with what the rest of the screen says."""
    settled = _invoice(number="2026-0001", issued=TODAY - timedelta(days=40))
    draft = _invoice(number="2026-0002", performed_on=None)
    queue = build_queue(clients=["C"], jobs=[_job("complete")],
                        invoices=[settled, draft],
                        payments=[_payment(settled.total, invoice="2026-0001")],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    rows = {a.kind: a for a in queue.actions}
    assert set(rows) == {"invoice_unissued"}
    assert rows["invoice_unissued"].urgency == "routine"
    assert "already delivered" not in rows["invoice_unissued"].why


# --- coverage is a fact nobody ever recorded ----------------------------------
#
# No invoice line carries a job_id and no job carries an invoice number. Counting
# lines against jobs was a proxy for that missing fact, and a proxy that can
# invent a shortfall AND invent coverage is not evidence of either.


def test_no_row_claims_a_number_of_unbilled_jobs_that_nothing_records():
    """One invoice line for a package of work that produced three jobs is an
    ordinary billing shape. Reading it as "at least 2 jobs have never been
    billed" states a shortfall the practice has no record of — principle 1, in
    the direction that costs the owner an afternoon chasing nothing."""
    jobs = [_job("complete", job_id="j1", engagement_type="Individual 1040"),
            _job("complete", job_id="j2", engagement_type="Rental schedule"),
            _job("complete", job_id="j3", engagement_type="Payroll")]
    one_bill = [_invoice(issued=TODAY - timedelta(days=3))]
    assert unbilled_work(jobs, one_bill, client_id="C", tax_year=2025) is None

    queue = build_queue(clients=["C"], jobs=jobs, invoices=one_bill,
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert all("never been billed" not in a.why for a in queue.actions)


def test_a_settled_year_says_it_cannot_confirm_rather_than_going_quiet():
    """The other direction of the same fallacy. Two lines against one delivered
    job counted as coverage and the row went silent — a confident answer to a
    question no record on file can settle. Once the bills are issued and paid,
    NOTHING else on the screen mentions the year, so silence here is the whole
    answer the owner gets. Principles 1 and 5 beat a confident silence."""
    inv = _invoice(issued=TODAY - timedelta(days=40),
                   services=("return_1040", "schedule_e_rental"))
    action = unbilled_work([_job("complete")], [inv], [_payment(inv.total)],
                           client_id="C", tax_year=2025)
    assert action is not None
    assert action.urgency == "routine"
    assert "cannot confirm" in action.why
    assert "does not know" in action.why
    assert action.evidence == ("job-1",)


def test_the_coverage_row_stays_off_while_a_bill_is_still_owed():
    """Principle 13. Whatever is unbilled is indistinguishable from what is
    merely unpaid while money is still owed, and that bill already has its own
    row — two rows about one year is how the owner learns to scroll past."""
    inv = _invoice(issued=TODAY - timedelta(days=40))
    queue = build_queue(clients=["C"], jobs=[_job("complete")], invoices=[inv],
                        payments=[_payment("100.00")],
                        engaged_clients=["C"], tax_year=2025, today=TODAY)
    assert [a.kind for a in queue.actions] == ["invoice_overdue"]


def test_a_draft_still_standing_holds_the_coverage_row_back_too():
    """A draft for the year is billing in progress, and it has its own row."""
    jobs = [_job("complete", job_id="j1"), _job("complete", job_id="j2")]
    assert unbilled_work(jobs, [_invoice(performed_on=TODAY - timedelta(days=21))],
                         client_id="C", tax_year=2025) is None


# --- the year of a quarterly or monthly job -----------------------------------


def _dateless_job(period, job_id="p1", *, stage="complete", label="Payroll"):
    from satc.models.work import Job

    return Job(job_id=job_id, client_id="C", workflow_key="payroll",
               engagement_type=label, tax_year=None, period_key=period, stage=stage)


def test_a_quarterly_or_monthly_period_still_names_a_year():
    """``2026Q1`` and ``2026-03`` are work.py's own examples of a period key.
    Payroll and quarterly work is exactly the recurring, easily-forgotten
    billing this section exists to catch."""
    action = unbilled_work([_dateless_job("2026Q1", "q"), _dateless_job("2026-03", "m")],
                           [], client_id="C", tax_year=2026)
    assert action is not None
    assert set(action.evidence) == {"q", "m"}


def test_a_period_nobody_can_read_is_marked_rather_than_dropped():
    """No fact, so the slot is visible — not guessed at, and not discarded
    (principle 1). A silently dropped job is surfaced by nothing, ever."""
    job = _dateless_job("FY26", "x", label="Notice response")
    assert unbilled_work([job], [], client_id="C", tax_year=2026) is None

    queue = build_queue(clients=["C"], jobs=[job], engaged_clients=["C"],
                        tax_year=2026, today=TODAY)
    assert [a.kind for a in queue.actions] == ["unbilled_work"]
    assert "FY26" in queue.actions[0].why
    assert "cannot say" in queue.actions[0].why


def test_the_unreadable_period_row_is_quiet_and_names_what_clears_it():
    """No bill can stand this row down: the check that would clear it needs the
    year, and the year is the missing thing. Left in "Coming up" it is a row
    that can never go away — exactly the row that teaches the owner to scroll
    past the queue (principle 13). So it drops to the quietest band and names
    the one act that removes it (principle 10)."""
    row = undated_work([_dateless_job("FY26", "x")], client_id="C")
    assert row is not None
    assert row.urgency == "routine"
    assert "Put a tax year on the job" in row.why


def test_work_still_in_prep_with_no_readable_year_is_not_a_row_either():
    """Billing happens at delivery — an unreadable period does not change that."""
    assert undated_work([_dateless_job("FY26", stage="in_prep")], client_id="C") is None


# --- against the seeded practice ---------------------------------------------

def test_it_runs_against_the_real_seeded_practice():
    from satc.app.state import STATE

    queue = build_queue(
        clients=[cid for cid, _ in STATE.client_choices()],
        requested=STATE.requested_items(), received=STATE.received_documents(),
        engaged_clients=[e.client_id for e in STATE.jobs()],
        tax_year=2024, today=date(2025, 3, 20))
    assert len(queue) > 0, "the seeded practice should have something worth doing"
    assert queue.summary_line() != "Nothing needs you right now."


def test_the_today_screen_actually_reads_the_ledger(monkeypatch):
    """The seam has to be wired, not merely available.

    ``build_queue(payments=...)`` defaults to empty, so a screen that never
    fetches the ledger passes every unit test above and still chases invoices
    the client settled months ago. This is the only place that can catch it.
    """
    from satc.app.server import create_app
    from satc.app.state import STATE

    read = []
    real = STATE.store.load_payments
    monkeypatch.setattr(STATE.store, "load_payments",
                        lambda *a, **kw: read.append(True) or real(*a, **kw))

    resp = create_app().test_client().get("/today")
    assert resp.status_code == 200
    assert read, "the money rows were computed without reading the payment ledger"


# --- the working year is derived, not hardcoded ------------------------------

def test_the_working_year_comes_from_the_register():
    """A hardcoded year goes stale silently and every deadline then reads as
    wildly overdue — which trains the owner to ignore the screen."""
    from satc.app.today_views import working_tax_year

    docs = [_doc("W-2", 2024, "Received"), _doc("W-2", 2025, "Received")]
    assert working_tax_year(docs, date(2027, 6, 1)) == 2025


def test_an_empty_practice_falls_back_to_the_season_being_worked():
    from satc.app.today_views import working_tax_year

    assert working_tax_year([], date(2026, 8, 1)) == 2025
