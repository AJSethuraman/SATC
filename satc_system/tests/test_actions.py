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

from satc.actions import ProposedAction, build_queue
from satc.actions.propose import (
    ask_prior_year_questions,
    chase_outstanding,
    chase_signature,
    deadline_pressure,
    extension_candidate,
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
