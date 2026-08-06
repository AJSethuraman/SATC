"""The fact the autonomy ladder counts (docs/AUTONOMY-CHARTER.md §11).

Today the Today queue's dismissal is browser session state — no actor, no
date, gone when the cookie clears. These tests guard the record that replaces
it: what was rendered, what the owner says they sent, who decided, and — the
whole point of the exercise — that the outcome is a HASH COMPARISON the system
cannot be talked out of, never a label trusted from whichever function built
the row.
"""

from datetime import date

import pytest

from satc.autonomy.approval import (
    Approval,
    ApprovalError,
    REASON_CODES,
    all_approvals,
    approvals_for,
    hash_text,
    merge,
    record_approval,
    record_correction,
)
from satc.models.actor import Actor, ActorRefused
from satc.persistence import SATCStore

OWNER = Actor.owner()
DAY = date(2026, 3, 20)
RENDERED = "Subject: Your organizer is ready\n\nHi there, please see attached."


def approved(*, actor=OWNER, decided_on=DAY, **kw) -> Approval:
    args = dict(template_key="organizer_request", client_id="CL-1",
               rendered_text=RENDERED, decided_on=decided_on)
    args.update(kw)
    return record_approval(actor=actor, **args)


def corrected(*, actor=OWNER, decided_on=DAY, reason="wrong_fact",
             sent_text=None, **kw) -> Approval:
    args = dict(template_key="organizer_request", client_id="CL-1",
               rendered_text=RENDERED,
               sent_text=sent_text or (RENDERED + " (edited)"),
               reason=reason, decided_on=decided_on)
    args.update(kw)
    return record_correction(actor=actor, **args)


# --- the core distinction: a hash comparison, not a judgement ---------------

def test_identical_rendered_and_sent_hashes_are_an_approval():
    a = approved()
    assert a.outcome == "approval"
    assert a.rendered_hash == a.sent_hash
    assert a.reason == ""


def test_a_one_character_difference_is_a_correction():
    rendered = "Please send your W-2 by March 1."
    sent = "Please send your W-2 by March 2."   # one digit changed
    c = record_correction(actor=OWNER, template_key="doc_request", client_id="CL-1",
                          rendered_text=rendered, sent_text=sent, reason="wrong_fact",
                          decided_on=DAY)
    assert c.outcome == "correction"
    assert c.rendered_hash != c.sent_hash


def test_outcome_is_computed_from_hashes_not_from_which_function_was_called():
    """The system does not grade its own homework (charter §4). Build the two
    records directly and check the property agrees with the bytes, not the
    constructor that happened to be used."""
    same_text = Approval(template_key="t", client_id="CL-1", decided_on=DAY,
                         decided_by=OWNER.handle, rendered_hash=hash_text("x"),
                         sent_hash=hash_text("x"))
    assert same_text.outcome == "approval"
    different_text = Approval(template_key="t", client_id="CL-1", decided_on=DAY,
                              decided_by=OWNER.handle, rendered_hash=hash_text("x"),
                              sent_hash=hash_text("y"), reason="wrong_judgment")
    assert different_text.outcome == "correction"


def test_record_approval_refuses_to_paper_over_an_actual_edit():
    """Calling record_approval does not manufacture an approval when the text
    given as 'sent' disagrees with what was rendered — that is a correction,
    and needs a reason record_approval has no way to collect."""
    with pytest.raises(ApprovalError) as exc:
        approved(sent_text=RENDERED + " extra")
    assert "record_correction" in str(exc.value)


def test_record_correction_refuses_when_nothing_actually_changed():
    with pytest.raises(ApprovalError) as exc:
        corrected(sent_text=RENDERED)
    assert "record_approval" in str(exc.value)


# --- the actor gate ----------------------------------------------------------

def test_a_model_cannot_record_that_the_owner_approved_a_draft():
    with pytest.raises(ActorRefused):
        approved(actor=Actor.model("SATC-Assistant"))


def test_a_model_cannot_record_a_correction_either():
    with pytest.raises(ActorRefused):
        corrected(actor=Actor.model("SATC-Assistant"))


# --- the finite five reason codes --------------------------------------------

def test_every_charter_reason_code_is_accepted():
    assert set(REASON_CODES) == {
        "wrong_fact", "wrong_judgment", "should_not_have_flagged",
        "gave_up", "missing_capability",
    }
    for code in REASON_CODES:
        c = corrected(reason=code)
        assert c.reason == code


def test_a_reason_outside_the_five_is_refused_by_name():
    with pytest.raises(ApprovalError) as exc:
        corrected(reason="looked_fine_to_me")
    message = str(exc.value)
    assert "looked_fine_to_me" in message
    for code in REASON_CODES:
        assert code in message


# --- identity: same decision twice is once, different decisions are two ----

def test_recording_the_same_decision_twice_is_recorded_once():
    ledger, added = merge([], [approved()])
    assert len(added) == 1
    ledger, added = merge(ledger, [approved()])
    assert added == []
    assert len(ledger) == 1


def test_two_genuinely_different_decisions_are_two():
    """Different clients, different days, different content — none of these
    collide, and all of them must survive in the ledger."""
    same_pair_diff_day = approved(decided_on=date(2026, 4, 1))
    ledger, added = merge([], [approved(), same_pair_diff_day,
                                approved(client_id="CL-2"),
                                corrected()])
    assert len(added) == 4
    assert len({a.approval_id for a in ledger}) == 4


def test_reclassifying_the_same_correction_replaces_it_not_duplicates_it():
    """Same template, client, day, rendered/sent text — only the reason
    differs. That is the owner correcting the RECORD, not a second decision,
    because who decided and why they call it that are not part of WHICH
    decision it is (mirrors PriceChange.change_id excluding the author)."""
    first = corrected(reason="wrong_fact")
    second = corrected(reason="wrong_judgment")
    assert first.approval_id == second.approval_id


def test_a_sequence_bump_makes_two_identical_decisions_distinguishable():
    """The payment.py pattern: nothing recorded can tell two decisions apart,
    so a human confirming it really is a second one is what separates them."""
    first = approved()
    second = first.as_another_one([first])
    assert second.approval_id != first.approval_id
    assert second.sequence == 1


# --- required fields ----------------------------------------------------------

def test_an_approval_must_name_a_template():
    with pytest.raises(ApprovalError):
        approved(template_key="")


def test_an_approval_must_name_a_client():
    with pytest.raises(ApprovalError):
        approved(client_id="")


# --- reading the record back --------------------------------------------------

def test_approvals_for_returns_only_that_pair_oldest_first():
    later = approved(decided_on=date(2026, 5, 1))
    earlier = approved(decided_on=date(2026, 1, 5))
    other_client = approved(client_id="CL-9")
    other_template = approved(template_key="notice_response")
    mine = approvals_for([later, earlier, other_client, other_template],
                         ("organizer_request", "CL-1"))
    assert [a.decided_on for a in mine] == [date(2026, 1, 5), date(2026, 5, 1)]


def test_all_approvals_is_oldest_first():
    late = approved(decided_on=date(2026, 6, 1))
    early = corrected(decided_on=date(2026, 2, 1))
    ordered = all_approvals([late, early])
    assert ordered[0] is early
    assert ordered[1] is late


# --- persistence: round trip, and history that outlives its template -------

def test_round_trip_preserves_outcome_and_reason(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    an_approval = approved()
    a_correction = corrected(client_id="CL-2", reason="missing_capability",
                             note="client asked for something SATC can't draft")
    store.save_approvals([an_approval, a_correction])
    store.close()

    reopened = SATCStore(tmp_path)
    by_id = {a.approval_id: a for a in reopened.load_approvals()}
    reloaded_approval = by_id[an_approval.approval_id]
    reloaded_correction = by_id[a_correction.approval_id]

    assert reloaded_approval.outcome == "approval"
    assert reloaded_approval.reason == ""
    assert reloaded_correction.outcome == "correction"
    assert reloaded_correction.reason == "missing_capability"
    assert reloaded_correction.note == "client asked for something SATC can't draft"
    assert reloaded_correction.decided_by == OWNER.handle
    reopened.close()


def test_recording_the_same_decision_twice_survives_a_restart_as_one_row(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    store.save_approvals([approved()])
    store.save_approvals([approved()])   # same decision, saved again
    store.close()

    reopened = SATCStore(tmp_path)
    assert len(reopened.load_approvals(client_id="CL-1")) == 1
    reopened.close()


def test_an_approval_for_a_deleted_template_still_loads(tmp_path):
    """History is a fact about something that happened. The refusal against an
    unknown template belongs at record_approval/record_correction time, not
    at load time — the config it once named is free to disappear."""
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    long_gone = approved(template_key="template_retired_last_season")
    store.save_approvals([long_gone])
    store.close()

    reopened = SATCStore(tmp_path)
    reloaded = {a.approval_id: a for a in reopened.load_approvals()}
    assert reloaded[long_gone.approval_id].template_key == "template_retired_last_season"
    reopened.close()


def test_deleting_a_client_removes_their_approvals(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    store.save_approvals([approved(client_id="CL-1")])
    store.delete_client("CL-1")
    assert store.load_approvals(client_id="CL-1") == []
    store.close()
