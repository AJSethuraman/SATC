"""Quoting a live engagement again, and the six ways it could go wrong quietly.

An engagement was priced exactly once -- in `intake.finish`, at the moment it
was created -- and nineteen commands later, not one of them could add a
chargeable line to work that already existed. A client who rang in March to say
they had bought a rental had to be re-interviewed as a second engagement, or
have a figure typed onto an invoice by hand.

The risk in fixing that is not that the arithmetic is wrong. `pricing.py` does
the arithmetic and is tested where it lives. The risk is everything AROUND the
number: a price that moves with nothing saying why, a scope line left standing
on a signed letter that the new answers contradict, a second estimate a client
cannot tell from the first. Each test below is one of those.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engagements  # noqa: E402
import intake  # noqa: E402
import interview as iv  # noqa: E402
import invoicing  # noqa: E402
import pricing  # noqa: E402
import requote  # noqa: E402
import tins  # noqa: E402

ANSWERS = ROOT / "samples" / "interview-answers.json"


@pytest.fixture
def live(tmp_path):
    """One priced engagement on disk, the way `interview` leaves it."""
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    out = intake.finish(answers, store=tmp_path, today=date(2027, 2, 3))
    assert out.created, out.reason
    return out.ref, tmp_path


def k1s(n: int) -> dict:
    """Both answers that state one fact about the K-1s.

    The count is what the estimate's K-1 line is billed from; the additional
    forms line is the same fact in the preparer's own words, printed two
    inches above it. `requote` refuses to move one without the other, so a
    test that moves one is testing the refusal, not the re-quote.
    """
    return {"count_k1s": n, "additional_forms": [f"{n} K-1s as reported"]}


# ── which answers can move the money ──────────────────────────────────────

def test_the_movers_are_read_out_of_the_schedule_not_listed_by_hand():
    """A list of price-moving answers kept in Python would go stale the first
    time somebody added a counted line to the registry, and nothing would say
    so -- the re-quote would simply stop offering the question."""
    moving = pricing.answers_that_move_money()
    assert {"count_states", "count_k1s", "federal_form"} <= set(moving)

    invented = {"per_unit": {"moorings": {"count_from": "count_moorings"}}}
    assert "count_moorings" in pricing.answers_that_move_money(invented)


def test_a_gate_that_reads_the_schedules_names_the_answer_behind_it():
    """`federal_schedules` carries no count and feeds nothing, so
    `interview.billable_counts` never mentions it -- and it selects the 1040
    package, the largest single number on most estimates."""
    assert "federal_schedules" in pricing.answers_that_move_money()
    gated = {"base": {"1040": {"tiers": {"x": {"gate": {"schedules_any": ["E1"]}}}}}}
    assert "federal_schedules" in pricing.answers_that_move_money(gated)


def test_a_price_that_turns_on_a_question_nobody_asks_is_refused(monkeypatch):
    """Not a soft skip. A schedule pricing on an answer the interview does not
    collect is a price nobody can change, and it would look like a re-quote
    that simply never moved."""
    monkeypatch.setattr(pricing, "answers_that_move_money",
                        lambda *a, **k: ["count_states", "count_unicorns"])
    with pytest.raises(requote.RequoteError, match="count_unicorns"):
        requote.questions()


def test_only_the_questions_this_client_was_actually_asked(live):
    """Nineteen answers move money across the schedule and no client is asked
    all nineteen. Offering `count_owners` on a 1040 invites a preparer to set
    it, where the schedule reads it for two entity forms and ignores it here --
    a control that appears to do something and does nothing."""
    ref, store = live
    answers = requote._answers(ref, store)
    assert answers["federal_form"] == "1040"
    shown = {q["id"] for q in requote.questions(answers)}
    assert "count_states" in shown
    assert "count_owners" not in shown, "an individual has no owner K-1s"
    assert shown < {q["id"] for q in requote.questions()}


# ── the plan writes nothing ───────────────────────────────────────────────

def test_planning_a_re_quote_touches_no_file(live):
    ref, store = live
    before = json.loads((store / ref / "record.json").read_text(encoding="utf-8"))
    quote = requote.plan(ref, k1s(6), store=store)
    assert quote.moves_money
    after = json.loads((store / ref / "record.json").read_text(encoding="utf-8"))
    assert before == after, "the plan wrote to the record"
    assert not (store / ref / "revisions.json").exists()


def test_the_plan_names_every_line_that_moved_and_the_difference(live):
    ref, store = live
    quote = requote.plan(ref, k1s(4), store=store)
    moved = {mv.service: mv for mv in quote.moved}
    assert "Schedule K-1 received" in moved
    assert moved["Schedule K-1 received"].kind == "added"
    assert quote.difference.endswith("more")
    assert quote.before_total != quote.after_total


def test_a_typo_in_a_question_name_is_refused_not_ignored(live):
    """`--set count_state=3` silently changing nothing would report "the total
    does not change", and be believed."""
    ref, store = live
    with pytest.raises(requote.RequoteError, match="count_state"):
        requote.plan(ref, {"count_state": 3}, store=store)


# ── the record afterwards ─────────────────────────────────────────────────

def test_the_signed_letter_keeps_its_date_and_the_estimate_gets_a_new_one(live):
    """Two sheets in a drawer showing different totals under the same date is
    a question nobody can answer next February -- and re-dating the engagement
    letter re-dates an instrument the client has already signed."""
    ref, store = live
    was = engagements.load(ref, store)
    quote = requote.plan(ref, k1s(4), store=store,
                         today=date(2027, 5, 9))
    requote.apply(quote, "two more K-1s arrived", store=store,
                  today=date(2027, 5, 9))
    now = engagements.load(ref, store)
    assert now["LetterDate"] == was["LetterDate"] == "February 3, 2027"
    assert now["EstimateDate"] == "May 9, 2027"


def test_a_field_the_new_answers_no_longer_supply_is_removed(live):
    """A MERGE IS NOT ENOUGH, and this is the case that proves it.

    Layering the new fields over the old leaves behind every field the answers
    stopped supplying. `compose` skips a question whose answer is now empty --
    it emits nothing rather than an empty string -- so a merge keeps the OLD
    value, and the letter goes on naming a prior firm the client has just told
    us they never had.

    Written against a field the recomposition genuinely drops. The first
    version of this test used `LocalReturns`, which `compose` rebuilds from a
    key that is still present, so it passed with the clearing removed
    entirely: a test that could not fail, guarding the one thing here most
    likely to be got wrong.
    """
    ref, store = live
    was = engagements.load(ref, store)
    assert was["PriorFirmName"] == "Halloran & Reeve CPAs"

    quote = requote.plan(ref, {"prior_firm": "no", "prior_firm_name": ""},
                         store=store)
    assert "PriorFirmName" not in quote.record, (
        "the letter still names a prior firm the client says they never had"
    )
    assert quote.record["PriorFirm"] is False

    # And nothing OUTSIDE what the interview supplies is disturbed: the
    # recomposition does not know what a lifecycle event or a close-out put on
    # the record, and guessing is how a record loses something.
    assert quote.record["EngagementRef"] == was["EngagementRef"]
    assert quote.record["_season"] == was["_season"]


def test_the_scope_moving_is_reported_separately_from_the_price(live):
    """The price is the headline; the scope is what gets missed, and it is on
    a letter the client has already signed."""
    ref, store = live
    quote = requote.plan(ref, {"count_states": 3, "states": ["Ohio", "Michigan",
                                                            "Indiana"]},
                         store=store)
    moved = {c.question for c in quote.scope_moved}
    assert "StateReturns" in moved
    assert any("engagement letter" in note for note in quote.notes)


def test_a_re_quote_that_moves_no_scope_says_so(live):
    """Sorting a shoebox is billed and describes nothing on the letter, which
    is the common case: the figure moves and the signed pack still reads
    correctly."""
    ref, store = live
    quote = requote.plan(ref, {"count_sorting": 2}, store=store)
    assert quote.moves_money and not quote.scope_moved
    assert any("still reads correctly" in note for note in quote.notes)


# ── what `apply` refuses ──────────────────────────────────────────────────

def test_a_re_quote_with_no_reason_is_refused(live):
    """The number moved and in a year nobody remembers why. The gate's
    override log takes a reason for the same reason, and this is the money."""
    ref, store = live
    quote = requote.plan(ref, k1s(4), store=store)
    with pytest.raises(requote.RequoteError, match="reason"):
        requote.apply(quote, "   ", store=store)
    assert not (store / ref / "revisions.json").exists()
    assert engagements.load(ref, store)["EstimateTotal"] == quote.before_total


def test_a_re_quote_that_changes_nothing_is_refused(live):
    """A revision log full of no-ops is a log nobody reads, and a second
    estimate identical to the first confuses a client for no reason."""
    ref, store = live
    same = requote._answers(ref, store)["count_k1s"]
    quote = requote.plan(ref, {"count_k1s": same}, store=store)
    assert not quote.changes_anything
    with pytest.raises(requote.RequoteError, match="nothing"):
        requote.apply(quote, "no change at all", store=store)


def test_answers_that_now_flag_work_the_firm_does_not_take_stop_it(live):
    """A HARD NO arriving mid-engagement is not a pricing question. The
    engagement is already live, so what is needed is the disengagement letter,
    and the message says so rather than quoting the work."""
    ref, store = live
    schema = iv.load_schema()
    flag = next((q, o) for _, q in iv.all_questions(schema)
                for o in (q.get("options") or []) if o.get("hard_no"))
    q, option = flag
    value = [option["value"]] if q["type"] == "multi" else option["value"]
    quote = requote.plan(ref, {q["id"]: value}, store=store)
    assert not quote.ok
    assert "disengagement" in " ".join(quote.blockers)
    with pytest.raises(requote.RequoteError):
        requote.apply(quote, "a real reason", store=store)


def test_a_tin_typed_into_a_re_quote_never_reaches_disk(live):
    """`save_answers` is the guard and this proves the re-quote goes through
    it. An engagement's `interview.json` lives in OneDrive and is read back
    every season."""
    ref, store = live
    schema = iv.load_schema()
    free = next(q for _, q in iv.all_questions(schema)
                if q["type"] in ("text", "textarea") and not q.get("internal"))
    quote = requote.plan(ref, k1s(4), store=store)
    quote.answers[free["id"]] = "prior return showed 000-12-3456"
    with pytest.raises(tins.TinRefused):
        requote.apply(quote, "two more K-1s arrived", store=store)
    assert not (store / ref / "revisions.json").exists(), (
        "the revision was logged for a write that was refused"
    )


# ── the log ───────────────────────────────────────────────────────────────

def test_every_re_quote_is_logged_with_what_moved_and_why(live):
    ref, store = live
    for count, why in ((4, "two more K-1s arrived in April"),
                       (6, "the estate issued two more in June")):
        quote = requote.plan(ref, k1s(count), store=store)
        requote.apply(quote, why, store=store)
    log = requote.revisions(ref, store)
    assert len(log) == 2, "the log was overwritten rather than appended to"
    assert [e["reason"] for e in log] == [
        "two more K-1s arrived in April", "the estate issued two more in June"]
    assert log[0]["now"] == log[1]["was"], "the log does not join up"
    assert {a["question"] for a in log[1]["answers"]} == {
        "count_k1s", "additional_forms"}
    k1 = next(a for a in log[1]["answers"] if a["question"] == "count_k1s")
    assert (k1["from"], k1["to"]) == ("4", "6")


def test_a_corrupt_log_is_kept_beside_the_new_one(live):
    """A log you can edit is not evidence, and a log you can silently destroy
    is worse. Same rule as `engagements.record_override`."""
    ref, store = live
    (store / ref / "revisions.json").write_text("{not json", encoding="utf-8")
    quote = requote.plan(ref, k1s(4), store=store)
    requote.apply(quote, "two more K-1s arrived", store=store)
    assert (store / ref / "revisions.corrupt").exists()
    assert requote.revisions(ref, store)[0]["unreadable"]


# ── downstream ────────────────────────────────────────────────────────────

def test_the_next_invoice_bills_the_new_figure_and_cites_the_new_estimate(live):
    """The estimate becomes the invoice; that is `invoicing`'s whole reason to
    exist. A bill raised after a re-quote that still pointed at February's
    sheet would be citing a document the client no longer holds."""
    ref, store = live
    quote = requote.plan(ref, k1s(6), store=store,
                         today=date(2027, 5, 9))
    requote.apply(quote, "four more K-1s arrived", store=store,
                  today=date(2027, 5, 9))
    record = engagements.load(ref, store)
    bill = invoicing.build(record, number="2027-0001", billed="May 2027",
                           today=date(2027, 5, 20))
    assert bill["EstimateTotal"] == quote.after_total
    assert bill["EstimateDate"] == "May 9, 2027"
    assert bill["Subtotal"] == quote.after_total, (
        "the invoice billed something the estimate does not say"
    )


def test_an_engagement_priced_before_the_estimate_had_its_own_date(live):
    """Every record already on disk carries only `LetterDate`. A render that
    refused on one written last week would be this change breaking real
    work."""
    import cli

    ref, store = live
    record = engagements.load(ref, store)
    del record["EstimateDate"]
    engagements.save(record, ref, store)
    built = cli.build_record(engagements.load(ref, store))
    assert built["EstimateDate"] == built["LetterDate"]


def test_an_engagement_with_no_saved_interview_says_what_to_do(live):
    ref, store = live
    (store / ref / "interview.json").unlink()
    with pytest.raises(requote.RequoteError, match="no saved interview"):
        requote.plan(ref, k1s(4), store=store)


# ── the sheet may not argue with itself ───────────────────────────────────
#
# `count_k1s` is what the "Schedule K-1 received" line is billed from.
# `additional_forms` is the same fact in the preparer's own words, printed two
# inches above it on the same estimate. Nothing joined them until August 2026,
# and a re-quote is the moment the gap opens, because the count is exactly what
# a re-quote moves.

def test_moving_the_count_and_not_the_sentence_is_refused(live):
    ref, store = live
    assert engagements.load(ref, store)["AdditionalForms"] == \
        "Two K-1s as reported"
    quote = requote.plan(ref, {"count_k1s": 5}, store=store)
    assert not quote.ok
    said = " ".join(quote.blockers)
    assert "Two K-1s" in said and "5 are billed" in said
    assert "Anything else filed alongside?" in said, (
        "it must name the question to change, in the interview's own words"
    )


def test_moving_both_together_is_the_way_through(live):
    ref, store = live
    quote = requote.plan(ref, {"count_k1s": 5,
                               "additional_forms": ["Five K-1s as reported"]},
                         store=store)
    assert quote.ok, quote.blockers
    assert any(c.question == "AdditionalForms" for c in quote.scope_moved)
    requote.apply(quote, "the estate issued three more", store=store)
    assert engagements.load(ref, store)["AdditionalForms"] == \
        "Five K-1s as reported"


def test_the_scope_answers_are_offered_beside_the_counted_ones(live):
    """The remedy has to be on the same screen as the refusal. Offering the
    count without the sentence is offering half of one fact."""
    ref, store = live
    shown = {q["id"] for q in requote.questions(requote._answers(ref, store))}
    assert {"count_k1s", "additional_forms", "states", "localities"} <= shown
    assert "tax_year" not in shown, (
        "changing which year an engagement is for is a different engagement"
    )


def test_a_gap_that_was_already_there_stops_nothing(live):
    """BLOCKING ON THE GAP HOWEVER IT GOT THERE TRAPPED A PREPARER. An
    engagement that already disagreed with itself refused every re-quote --
    including one changing something else entirely, and including the one that
    would have fixed it."""
    ref, store = live
    # Made the way it really arises: the count moved and the sentence did not.
    answers = requote._answers(ref, store)
    answers["count_k1s"] = 4
    engagements.save_answers(answers, ref, store)
    record = {**engagements.load(ref, store),
              **intake.compose_record(answers, today=date(2027, 2, 3)),
              **pricing.price(answers)}
    record["LetterDate"] = "February 3, 2027"
    engagements.save(record, ref, store)
    assert record["AdditionalForms"] == "Two K-1s as reported"

    quote = requote.plan(ref, {"count_states": 3,
                               "states": ["Ohio", "Michigan", "Indiana"]},
                         store=store)
    assert quote.ok, quote.blockers
    assert any("already said" in note for note in quote.notes), (
        "it stops nothing, but it is on the sheet and has to be said"
    )
    requote.apply(quote, "a second state came up", store=store)


def test_the_count_and_the_named_list_move_together_or_not_at_all(live):
    """THE SAME SHAPE, ON THE PAIR WHERE IT CAN BE COUNTED EXACTLY.
    `count_states` decides what the estimate bills; `states` becomes the scope
    line on the estimate AND on the engagement letter. Found by reading a
    revised estimate out of `exercise.py`: it billed three state returns under
    a scope line that still read "State: Ohio"."""
    ref, store = live
    blocked = requote.plan(ref, {"count_states": 3}, store=store)
    assert not blocked.ok
    said = " ".join(blocked.blockers)
    assert "1 state return " in said and "3 are billed" in said, said
    assert "Which states, and on what basis?" in said

    ok = requote.plan(ref, {"count_states": 3,
                            "states": ["Ohio", "Michigan", "Indiana"]},
                      store=store)
    assert ok.ok, ok.blockers
    assert any(c.question == "StateReturns" for c in ok.scope_moved)


def test_the_pairs_all_agree_on_the_answers_this_repo_ships(live):
    """MEASURED BEFORE IT WAS ALLOWED TO BLOCK ANYTHING. A guard that cries
    wolf gets muted, and then it is worse than nothing."""
    ref, store = live
    assert not requote._list_gaps(requote._answers(ref, store))


def test_a_line_that_states_no_number_is_not_a_disagreement(live):
    """"K-1s as reported" claims no count. A check that goes red where no
    answer exists is one people stop reading."""
    ref, store = live
    quote = requote.plan(ref, {"count_k1s": 5,
                               "additional_forms": ["K-1s as reported"]},
                         store=store)
    assert quote.ok, quote.blockers
