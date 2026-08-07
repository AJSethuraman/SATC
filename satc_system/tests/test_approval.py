"""The fact the autonomy ladder counts (docs/AUTONOMY-CHARTER.md §11).

Today the Today queue's dismissal is browser session state — no actor, no
date, gone when the cookie clears. These tests guard the record that replaces
it: what was rendered, what the owner says they sent, who decided, and — the
whole point of the exercise — that the outcome is a HASH COMPARISON the system
cannot be talked out of, never a label trusted from whichever function built
the row.
"""

import dataclasses
from datetime import date, datetime

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


def test_hash_text_is_sensitive_to_leading_and_trailing_whitespace():
    """The module docstring's own claim: hash_text is deliberately NOT
    stripped. Stripping would launder away exactly the edits — a trailing
    space, leading whitespace from a mail client's quoting — this record
    exists to catch (charter §4: 'a changed comma is a correction')."""
    assert hash_text("Please see attached.") != hash_text(" Please see attached. ")
    assert hash_text("Please see attached.") != hash_text("Please see attached. ")


def test_a_whitespace_only_edit_is_still_a_correction():
    rendered = "Please see attached."
    sent = rendered + " "   # trailing space, nothing else changed
    c = record_correction(actor=OWNER, template_key="doc_request", client_id="CL-1",
                          rendered_text=rendered, sent_text=sent, reason="wrong_judgment",
                          decided_on=DAY)
    assert c.outcome == "correction"
    assert c.rendered_hash != c.sent_hash


def test_hash_text_is_case_sensitive():
    """The same docstring's other named claim: NOT case-folded either. An
    owner who changed "Dear Robert" to "Dear ROBERT", or lower-cased a
    shouted subject line, looked at the draft and decided it was wrong."""
    assert hash_text("Please see attached.") != hash_text("please see attached.")
    assert hash_text("PLEASE SEE ATTACHED.") != hash_text("Please see attached.")


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


def test_the_outcome_follows_the_bytes_even_when_the_reason_field_disagrees():
    """The sharper version of the test above, which cannot tell the two apart.

    Both rows there carry a reason that AGREES with their hashes, so an
    ``outcome`` that read ``reason`` instead of the two hashes would answer
    both correctly and the check would report success forever (principle 12).
    These two rows disagree on purpose — a reason column filled in on a row
    whose bytes are identical, and an edit recorded with no reason at all,
    both of which a store can hand back. ``outcome`` reads the bytes; the
    reason field gets no vote."""
    labelled_a_correction = Approval(
        template_key="t", client_id="CL-1", decided_on=DAY, decided_by=OWNER.handle,
        rendered_hash=hash_text("x"), sent_hash=hash_text("x"), reason="wrong_fact")
    assert labelled_a_correction.outcome == "approval"
    assert not labelled_a_correction.is_correction

    labelled_nothing = Approval(
        template_key="t", client_id="CL-1", decided_on=DAY, decided_by=OWNER.handle,
        rendered_hash=hash_text("x"), sent_hash=hash_text("y"))
    assert labelled_nothing.outcome == "correction"
    assert labelled_nothing.is_correction


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


def test_the_same_decision_twice_in_one_batch_is_still_recorded_once():
    """Idempotence is not only about a row already sitting on the ledger.
    A re-import of an export that contains the decision twice, or a double
    post that arrives as one batch, never touches the ``existing`` side at
    all — and the test above cannot see that case, because its duplicate
    always arrives in a second call."""
    ledger, added = merge([], [approved(), approved()])
    assert len(added) == 1
    assert len(ledger) == 1


def test_merge_leaves_the_ledger_it_was_given_alone():
    """``merge`` hands back a NEW ledger. Growing the caller's own list as a
    side effect is how "load it, merge into it, then decide whether to save"
    becomes a record that changed before anybody decided to change it."""
    existing = [approved()]
    ledger, added = merge(existing, [approved(client_id="CL-2")])
    assert len(added) == 1
    assert len(ledger) == 2
    assert len(existing) == 1, "merge mutated the list it was handed"


def test_approval_id_depends_on_which_template_it_is():
    """The pair is (template_key, client_id) — charter §4. Two approvals that
    agree on client, day, and both hashes but differ ONLY in template_key are
    different decisions and must not collide on id."""
    welcome = approved(template_key="welcome_letter")
    invoice = approved(template_key="invoice_cover")
    assert welcome.client_id == invoice.client_id
    assert welcome.decided_on == invoice.decided_on
    assert welcome.rendered_hash == invoice.rendered_hash
    assert welcome.sent_hash == invoice.sent_hash
    assert welcome.approval_id != invoice.approval_id


def test_two_different_templates_same_client_same_day_both_survive_merge():
    """The real-world consequence of losing template_key from the id: two
    decisions about the same client on the same day, one about the welcome
    letter and one about the invoice cover, would collapse to a single id and
    merge() would silently drop one of them."""
    welcome = approved(template_key="welcome_letter")
    invoice = approved(template_key="invoice_cover")
    ledger, added = merge([], [welcome, invoice])
    assert len(added) == 2, "a second template's decision must not be treated as a duplicate"
    assert len({a.approval_id for a in ledger}) == 2


def test_approval_id_depends_on_what_satc_actually_rendered():
    """``rendered_hash`` is part of WHICH decision this is, not decoration on
    it. Two corrections on the same day for the same pair, each edited down to
    the same final wording from a DIFFERENT draft, are two decisions about two
    drafts — and the sent text alone cannot tell them apart."""
    first = corrected(rendered_text="Draft A, before the merge field was fixed",
                      sent_text="What actually went out")
    second = corrected(rendered_text="Draft B, after it was fixed",
                       sent_text="What actually went out")
    assert first.sent_hash == second.sent_hash
    assert first.rendered_hash != second.rendered_hash
    assert first.approval_id != second.approval_id


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


# BOTH DOORS, not one. ``record_correction`` is a second write path onto the
# same ledger, and the scope refusal above is already tested through both —
# these two required fields were only ever tested through ``record_approval``,
# so a pair with no template or no client could still be created by the other
# door and the ladder would key a streak on ("", "").

def test_a_correction_must_name_a_template():
    with pytest.raises(ApprovalError):
        corrected(template_key="")


def test_a_correction_must_name_a_client():
    with pytest.raises(ApprovalError):
        corrected(client_id="")


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


def test_two_same_day_decisions_are_ordered_by_when_they_were_recorded():
    """``all_approvals``' own headline claim: WITHIN a day the order is
    ``recorded_at``, and it used to be a SHA-256.

    Asserting one arrangement proves nothing — a tiebreak that had quietly
    fallen back to ``approval_id`` would still return SOME order and could
    happen to return that one. So the same two decisions are ordered twice,
    swapping only which was keyed in first. A hash-based tiebreak gives the
    identical answer both times, so one of these two assertions must fail."""
    morning = datetime(2026, 3, 20, 9, 0)
    afternoon = datetime(2026, 3, 20, 15, 0)
    an_approval = approved()
    a_correction = corrected()
    assert an_approval.decided_on == a_correction.decided_on == DAY

    approval_first = all_approvals([
        dataclasses.replace(an_approval, recorded_at=morning),
        dataclasses.replace(a_correction, recorded_at=afternoon)])
    assert [a.outcome for a in approval_first] == ["approval", "correction"]

    correction_first = all_approvals([
        dataclasses.replace(an_approval, recorded_at=afternoon),
        dataclasses.replace(a_correction, recorded_at=morning)])
    assert [a.outcome for a in correction_first] == ["correction", "approval"]


def test_the_day_a_decision_was_made_outranks_when_it_was_keyed_in():
    """The other way the same ordering can break. ``recorded_at`` settles
    ties WITHIN a day; it does not overrule the day itself. A March decision
    typed up this afternoon still belongs before a June one typed up this
    morning — the ledger is a timeline of decisions, not of data entry."""
    march = dataclasses.replace(approved(decided_on=date(2026, 3, 1)),
                                recorded_at=datetime(2026, 7, 1, 15, 0))
    june = dataclasses.replace(approved(decided_on=date(2026, 6, 1)),
                               recorded_at=datetime(2026, 7, 1, 9, 0))
    assert [a.decided_on for a in all_approvals([june, march])] == [
        date(2026, 3, 1), date(2026, 6, 1)]


def test_a_row_with_no_recorded_at_sorts_first_within_its_day():
    """"We do not know when" is the only honest place for a row written
    before the column existed — earliest within its day, never latest, so an
    undated row cannot silently overrule a decision that IS timestamped."""
    undated = dataclasses.replace(approved(), recorded_at=None)
    timestamped = dataclasses.replace(corrected(), recorded_at=datetime(2026, 3, 20, 0, 1))
    assert all_approvals([timestamped, undated])[0] is undated


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


def test_two_templates_for_one_client_on_one_day_survive_a_restart(tmp_path):
    """The OTHER path for the same invariant, and the one that loses the row
    for good. ``merge()`` merely skips a colliding id; the store's approvals
    table is keyed on ``approval_id`` with INSERT OR REPLACE, so an id that
    did not name the template would overwrite the other decision on disk and
    nothing would ever report it missing."""
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    store.save_approvals([approved(template_key="welcome_letter"),
                          approved(template_key="invoice_cover")])
    store.close()

    reopened = SATCStore(tmp_path)
    keys = sorted(a.template_key for a in reopened.load_approvals(client_id="CL-1"))
    assert keys == ["invoice_cover", "welcome_letter"]
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
