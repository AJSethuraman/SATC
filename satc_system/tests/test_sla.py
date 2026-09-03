"""A promise is not a deadline, and a promise nobody can measure is not a metric.

Two failures this guards against, and they pull in opposite directions.

The first is a screen where "we said two business days" sits next to "the return
is due" in the same typeface. One of those the owner can change over coffee; the
other carries a penalty. Everything derived from ``configs/firm_policy.yaml``
therefore says so, and the loader refuses a promise that tries to cite an
authority — the mirror image of the statutory loader, which refuses a rule that
does not.

The second is the more tempting one: a compliance number built on a plausible
substitute. SATC records no delivery, no inbound message and no moment at which
the documents went complete, so most of these promises cannot be measured at
all. The right answer is a refusal that NAMES the missing fact. A green tick
derived from "the last task was ticked" would be indistinguishable from a
measured one, and that is how a metric becomes a lie.
"""

import tempfile
from contextlib import contextmanager
from datetime import date, datetime

import pytest

from satc.config import ConfigError
from satc.ids import return_key
from satc.models.filing import Filing
from satc.obligations.profile import ObligationInstance
from satc.persistence import SATCStore
from satc.work import sla as sla_mod
from satc.work.sla import (
    FACTS,
    clocks_for,
    compliance,
    compliance_for,
    load_slas,
    measurable_slas,
    promised_by,
    unmeasurable_promises,
)

# A promise whose clock has BOTH ends recorded, so met/missed can be reached at
# all. Uses the real fact keys — a made-up one is refused at load, deliberately.
MEASURABLE = """
slas:
  fix_a_reject:
    label: Fixing a rejected return
    days: {days}
    business_days: {business}
    starts_when: efile_rejected
    ends_when: efile_retransmitted
"""


@pytest.fixture
def policy(tmp_path, monkeypatch):
    """A firm policy file the test owns, wired in where the app reads from."""
    path = tmp_path / "firm_policy.yaml"
    monkeypatch.setattr(sla_mod, "policy_file", lambda *a, **k: path)
    sla_mod.forget_slas()
    yield path
    sla_mod.forget_slas()


def write(path, *, days=2, business="true"):
    path.write_text(MEASURABLE.format(days=days, business=business),
                    encoding="utf-8")


# --- business-day arithmetic ------------------------------------------------


def test_business_days_step_over_a_weekend_and_a_federal_holiday(policy):
    """Friday + 2 business days, with Memorial Day on the Monday.

    2026: Fri 22 May, then Sat/Sun, then Mon 25 May is Memorial Day. So the
    first business day is Tue 26 and the second is Wed 27. A naive +2 would
    answer Sunday 24 May, which is a promise nobody can keep.
    """
    write(policy, days=2)
    promise = promised_by("fix_a_reject", started_on=date(2026, 5, 22),
                          today=date(2026, 5, 22))
    assert promise is not None
    assert promise.promised_date == date(2026, 5, 27)
    assert promise.duration == "2 business days"


def test_a_holiday_observed_on_a_friday_still_moves_the_promise(policy):
    """Independence Day 2026 falls on a Saturday, observed Friday 3 July.

    Thursday 2 July + 1 business day is therefore Monday 6 July, not Friday.
    This is the case a hand-rolled "skip Sat and Sun" rule gets wrong, which is
    why there is exactly one weekend rule in this system and it is not here.
    """
    write(policy, days=1)
    promise = promised_by("fix_a_reject", started_on=date(2026, 7, 2),
                          today=date(2026, 7, 2))
    assert promise.promised_date == date(2026, 7, 6)


def test_a_calendar_day_promise_is_not_quietly_moved_off_the_weekend(policy):
    """§7503 shifts acts with legal consequence. A promise has none.

    Shifting it would hand the practice two days it never offered the client.
    The owner who writes ``business_days: false`` gets calendar days, Sunday
    included.
    """
    write(policy, days=2, business="false")
    promise = promised_by("fix_a_reject", started_on=date(2026, 5, 22),
                          today=date(2026, 5, 22))
    assert promise.promised_date == date(2026, 5, 24), (
        "A calendar-day promise landed on a business day — the weekend rule "
        "leaked into firm policy.")
    assert promise.duration == "2 calendar days"


def test_the_start_day_itself_does_not_count(policy):
    """A notice keyed on Tuesday with a one-day promise is answered Wednesday."""
    write(policy, days=1)
    promise = promised_by("fix_a_reject", started_on=date(2026, 3, 3),
                          today=date(2026, 3, 3))
    assert promise.promised_date == date(2026, 3, 4)


# --- kept, and not kept -----------------------------------------------------


def test_a_promise_closed_by_its_date_is_met(policy):
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     closed_on=date(2026, 3, 4), today=date(2026, 3, 10))
    assert out.status == "met"
    assert out.is_met and not out.is_missed
    assert "2026-03-05" in out.why  # the date we promised, on the line


def test_a_promise_closed_after_its_date_is_missed(policy):
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     closed_on=date(2026, 3, 9), today=date(2026, 3, 10))
    assert out.status == "missed"
    assert "4 days later" in out.why
    assert "apology" in out.why, (
        "A missed promise is an apology. If this ever reads like a penalty, the "
        "screen has stopped telling law and preference apart.")


def test_a_promise_still_running_is_neither_met_nor_missed(policy):
    """Not yet is not a verdict. An unanswered question is not an answer.

    ``closed_on=None`` says we looked and it has not happened yet — which is
    what makes "still running" an answer rather than a shrug.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     closed_on=None, today=date(2026, 3, 4))
    assert out.status == "open"
    assert not out.is_met and not out.is_missed


def test_a_measurable_promise_past_its_date_with_nothing_recorded_is_missed(policy):
    """Only reachable when the closing fact CAN be recorded AND was looked for.

    Then silence is a real answer about this item — we can see retransmissions,
    and there isn't one. Where the closing fact cannot be recorded at all, the
    gate above this one refuses instead, and that is the difference between a
    statement about a client and a statement about the codebase. And where
    nobody looked, ``closed_on`` is not passed at all and the verdict is
    withheld — see the trap tests below.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     closed_on=None, today=date(2026, 3, 20))
    assert out.status == "missed"
    assert "nothing records when the fixed return went back out" in out.why


# --- the argument you cannot forget -----------------------------------------


def test_forgetting_the_stop_fact_is_not_a_promise_broken(policy):
    """THE TRAP. An omitted ``closed_on`` used to read as "there was no stop".

    The only promise this practice can measure was reported MISSED on a return
    that had been retransmitted the next morning, because the one caller
    resolved the clock's start and never its stop. A compliance API where
    forgetting an argument silently produces the accusing answer is a trap, and
    the answer it produces is a lie about the practice, not about the client.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     today=date(2026, 3, 20))

    assert out.status == "unresolved", (
        "An unresolved stop was reported as a promise broken. Nobody looked — "
        "that is a statement about the caller, not about the client.")
    assert not out.is_met and not out.is_missed and not out.is_resolved
    assert out.missing_fact == "", (
        "Nothing is known to be missing here. Naming a missing fact turns "
        "'nobody looked' into 'there is nothing to find'.")
    # Principle 10: the refusal names both next steps, and they are different.
    assert "clocks_for" in out.why
    assert "closed_on=None to say you looked" in out.why


def test_the_promise_still_lands_on_the_calendar_when_the_stop_is_unresolved(policy):
    """What is withheld is the VERDICT, not the date.

    The start is a recorded fact, so the day we owed the client is real and
    blanking it would be its own invention (principle 1).
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     today=date(2026, 3, 20))
    assert out.promise is not None
    assert out.promise.promised_date == date(2026, 3, 5)


def test_saying_none_is_a_claim_about_having_looked_and_none_is_not_the_default(policy):
    """The two spellings must not agree, or the distinction is decoration.

    ``None`` means "I read the records and there is no retransmission"; the
    default means "I never read them". Same date, same day, opposite answers.
    """
    write(policy, days=2)
    args = dict(started_on=date(2026, 3, 3), today=date(2026, 3, 20))
    assert compliance("fix_a_reject", closed_on=None, **args).status == "missed"
    assert compliance("fix_a_reject", **args).status == "unresolved"


# --- refusing, by name ------------------------------------------------------


def test_a_start_fact_nobody_records_refuses_and_names_it():
    """The one that matters most. Nothing records when documents went complete.

    Not "met", not "missed", not zero — a refusal that says which fact is
    missing and what would settle it.
    """
    out = compliance("return_turnaround", started_on=date(2026, 3, 3),
                     closed_on=date(2026, 3, 4), today=date(2026, 3, 10))
    assert out.status == "unmeasurable"
    assert not out.is_met and not out.is_missed
    assert out.missing_fact == "documents_complete"
    assert out.why.startswith("SATC cannot tell you whether this was met:")
    assert "when the documents went complete" in out.why
    assert "went complete on" in out.why  # names what would settle it


def test_a_stop_fact_nobody_records_refuses_even_when_the_start_is_recorded():
    """A notice arriving IS recorded. Our answer going out is not.

    Half a clock is not a clock, and the refusal has to name the half that is
    missing or the owner goes looking in the wrong place.
    """
    out = compliance("notice_turnaround", started_on=date(2026, 3, 3),
                     today=date(2026, 3, 30))
    assert out.status == "unmeasurable"
    assert out.missing_fact == "notice_response_sent"
    assert "when our response to the notice went out" in out.why


def test_delivery_is_now_a_recorded_fact_and_still_does_not_make_a_metric():
    """The entry that flipped, and the half-clock it must not become.

    ``satc.models.deliverable`` is persisted and reads back per client, so *when
    the return went to the client* is a recorded fact at last — this module's
    map of what SATC can see has to say so, or it lies in the other direction.

    And it changes nothing about ``return_turnaround``, which is the point worth
    guarding. That promise STARTS at ``documents_complete``, which is recorded
    nowhere, and half a clock measures nothing. The tempting move once one end
    lands is to start it from something adjacent — the job's creation, the last
    task ticked — and report a number. The refusal must still name the START.
    """
    assert FACTS["return_delivered"].is_recorded, (
        "delivery is persisted and readable; claiming otherwise is the same "
        "lie as claiming a fact SATC does not hold, pointed the other way")
    assert "Deliverable" in FACTS["return_delivered"].recorded_as

    out = compliance("return_turnaround", started_on=date(2026, 3, 3),
                     closed_on=date(2026, 3, 20), today=date(2026, 3, 30))
    assert out.status == "unmeasurable"
    assert out.missing_fact == "documents_complete", (
        "one end of the clock landing turned the other end into a metric")
    assert "return_turnaround" not in measurable_slas()


def test_a_recordable_start_that_is_blank_says_where_it_would_go(policy):
    """A different gap needs a different next step.

    "Nothing in SATC records this" is a codebase gap. "Nothing was recorded on
    this one" is a data gap on a single item, and the fix is to go and key it.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=None, today=date(2026, 3, 10))
    assert out.status == "unmeasurable"
    assert out.missing_fact == "efile_rejected"
    assert "Filing.ack_date" in out.why


def test_a_clock_that_stopped_before_it_started_refuses(policy):
    """Two dates that cannot both be right, and the wrong answer flatters us.

    A stop before its start always looks fast, so the failure mode of believing
    it is a promise reported as kept on the strength of a typo.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 10),
                     closed_on=date(2026, 3, 3), today=date(2026, 3, 20))
    assert out.status == "unmeasurable", (
        "A retransmission dated before its own rejection was reported as a "
        "promise kept.")
    assert "One of those two dates is wrong" in out.why


def test_the_two_names_for_the_promise_date_cannot_disagree(policy):
    """``.by`` is what the plan screen reads; ``promised_date`` is canonical."""
    write(policy, days=2)
    promise = promised_by("fix_a_reject", started_on=date(2026, 5, 22),
                          today=date(2026, 5, 22))
    assert promise.by == promise.promised_date == date(2026, 5, 27)


def test_promised_by_returns_nothing_rather_than_guessing_a_start(policy):
    write(policy, days=2)
    assert promised_by("fix_a_reject", started_on=None,
                       today=date(2026, 3, 10)) is None


def test_an_unknown_promise_refuses_and_names_the_ones_that_exist(policy):
    write(policy, days=2)
    with pytest.raises(ConfigError) as exc:
        compliance("same_day_everything", started_on=date(2026, 3, 3),
                   today=date(2026, 3, 3))
    assert "same_day_everything" in str(exc.value)
    assert "fix_a_reject" in str(exc.value), (
        "A refusal that does not name what IS on file ends the run.")


def test_a_promise_with_no_promises_on_file_names_the_file(policy):
    policy.write_text("cutoffs: {}\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        compliance("first_response", started_on=None, today=date(2026, 3, 3))
    assert "firm_policy.yaml" in str(exc.value)


# --- the config is the answer ----------------------------------------------


def test_editing_the_duration_changes_the_answer_with_no_code_change(policy):
    """The owner moves a promise in YAML and the next answer moves with it.

    A duration that needs a restart is a duration the owner will believe they
    changed. Same reasoning as the price catalogue, and the same mtime cache.
    """
    write(policy, days=2)
    args = dict(started_on=date(2026, 3, 3), closed_on=date(2026, 3, 9),
                today=date(2026, 3, 10))
    assert compliance("fix_a_reject", **args).status == "missed"

    write(policy, days=10)
    assert compliance("fix_a_reject", **args).status == "met", (
        "A promise edited in the config did not take effect — the owner would "
        "be measured against a number that is no longer in the file.")


def test_a_promise_that_does_not_say_business_days_is_refused(policy):
    """Two business days and two calendar days are different promises."""
    policy.write_text("""
slas:
  fix_a_reject:
    days: 2
    starts_when: efile_rejected
    ends_when: efile_retransmitted
""", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_slas()
    assert "business_days" in str(exc.value)


def test_a_clock_end_that_does_not_exist_is_refused_at_load(policy):
    policy.write_text("""
slas:
  fix_a_reject:
    days: 2
    business_days: true
    starts_when: the_phone_rang
    ends_when: efile_retransmitted
""", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_slas()
    assert "the_phone_rang" in str(exc.value)
    assert "efile_rejected" in str(exc.value)  # names the ones that exist


def test_a_promise_of_no_days_is_refused(policy):
    write(policy, days=0)
    with pytest.raises(ConfigError) as exc:
        load_slas()
    assert "at least 1" in str(exc.value)


# --- law and firm policy never look alike -----------------------------------


def test_a_promise_that_cites_an_authority_is_refused(policy):
    """The mirror image of the statutory loader, which refuses an UNcited rule.

    A citation here means somebody believes there is an authority behind the
    date — and if there is, it is not a promise and it does not belong in this
    file.
    """
    policy.write_text("""
slas:
  notify_after_reject:
    days: 1
    business_days: false
    starts_when: efile_rejected
    ends_when: efile_retransmitted
    citation: "IRS Pub 1345"
""", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_slas()
    assert "configs/obligations/" in str(exc.value), (
        "A refusal has to name where the thing actually belongs.")


def test_nothing_derived_from_firm_policy_can_pass_as_a_statutory_date(policy):
    """Structurally, not by convention.

    An obligation carries a computed ``statutory_due`` and a citation behind it.
    A promise carries neither, carries ``is_firm_policy``, and does not even
    share a field name — so a template written for one renders nothing for the
    other rather than rendering a promise as law.
    """
    write(policy, days=2)
    promise = promised_by("fix_a_reject", started_on=date(2026, 3, 3),
                          today=date(2026, 3, 3))
    outcome = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                         today=date(2026, 3, 3))

    assert promise.is_firm_policy is True
    assert outcome.is_firm_policy is True

    # Every field on an obligation that carries a DATE with authority behind
    # it. A promise answering to any of these names is one template edit away
    # from being rendered as law.
    statutory_dates = {f for f in ObligationInstance.__slots__ if "due" in f}
    assert "statutory_due" in statutory_dates  # the set is really populated

    for derived in (promise, outcome):
        for banned in ("citation", "source", "authority", *statutory_dates):
            assert not hasattr(derived, banned), (
                f"{type(derived).__name__} exposes {banned!r} — a promise that "
                f"answers to a statutory field name will be rendered as one.")

    for sentence in (promise.why(), outcome.why):
        low = sentence.lower()
        assert "deadline" not in low and "statutory" not in low
    assert "not a filing date" in promise.why()


# --- the promises actually shipped ------------------------------------------


def test_the_shipped_policy_offers_a_starting_set_the_owner_can_edit():
    on_file = load_slas()
    for expected in ("first_response", "notice_turnaround", "return_turnaround",
                     "signature_acknowledged"):
        assert expected in on_file, f"{expected} is not on file"
    assert all(d.days >= 1 and d.label for d in on_file.values())


def test_most_of_what_the_practice_promises_cannot_be_measured_today():
    """The honest report, asserted so it cannot rot into a silent green board.

    If a future change records delivery or inbound messages, this test fails and
    the right response is to celebrate and update the list — not to add a proxy.
    """
    waiting = {o.kind: o.missing_fact for o in unmeasurable_promises()}
    assert waiting == {
        "first_response": "client_message_received",
        "notice_turnaround": "notice_response_sent",
        "return_turnaround": "documents_complete",
        "signature_acknowledged": "authorization_signed",
    }
    assert all(o.why for o in unmeasurable_promises())


def test_the_one_measurable_promise_answers_for_real():
    """Both ends keyed off Drake and recorded, so this one is a real number."""
    out = compliance("efile_reject_turnaround", started_on=date(2026, 3, 3),
                     closed_on=date(2026, 3, 4), today=date(2026, 3, 10))
    assert out.status == "met"


# --- reading the clock out of the records ------------------------------------
#
# These go through the REAL store rather than a list of hand-built objects. The
# bug they guard was invisible in memory: it needed a client with a history —
# several returns, several years, an old rejection that had long since been
# fixed — which is what a store has and a fixture list does not.

CID = "SATC-001000"
RK_2025 = return_key(CID, 2025, "1040", "US")
RK_2023 = return_key(CID, 2023, "1065", "US")


def _filing(rk, *, ack="", attempt=1, ack_date=None, sent=None):
    return Filing(filing_id=f"F-{rk}-{attempt}", return_key=rk, client_id=CID,
                  transmitted_at=sent, ack_code=ack, ack_date=ack_date,
                  attempt=attempt)


@contextmanager
def _stored(*filings):
    """A real SATCStore holding these filings, read back the way the app reads."""
    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        store.save_filings(list(filings))
        yield store.load_filings()


def test_recording_the_retransmission_clears_the_promise():
    """Principle 13, and the row that could never be cleared.

    A rejection older than the promise window used to make the plan say
    "missed" forever — and NOTHING the practice could record would clear it,
    because the only thing that would (the retransmission) was never read. A
    row the owner cannot clear by doing the work is a row they learn to scroll
    past, which costs more than never having shown it.
    """
    rejected_on = date(2026, 3, 10)
    with _stored(
            _filing(RK_2025, ack="R", ack_date=rejected_on, attempt=1,
                    sent=datetime(2026, 3, 9, 16, 0)),
            _filing(RK_2025, ack="A", ack_date=date(2026, 3, 12), attempt=2,
                    sent=datetime(2026, 3, 11, 9, 30))) as filings:
        clocks = clocks_for("efile_reject_turnaround", filings=filings,
                            client_id=CID)

        assert len(clocks) == 1
        assert clocks[0].closed_on == date(2026, 3, 11), (
            "The retransmission was never read, so the clock had no stop.")
        assert not clocks[0].is_open

        out = compliance_for("efile_reject_turnaround", clocks[0],
                             today=date(2026, 8, 2))
        assert out.status == "met", (
            "The return was fixed and back out the next morning, months ago, "
            "and the practice was still being told it broke this promise.")
        assert out.subject == RK_2025


def test_a_rejection_with_no_retransmission_is_still_owed():
    """The other half — otherwise the fix above is just a way to never say no."""
    with _stored(_filing(RK_2025, ack="R", ack_date=date(2026, 3, 10),
                         sent=datetime(2026, 3, 9, 16, 0))) as filings:
        clock, = clocks_for("efile_reject_turnaround", filings=filings,
                            client_id=CID)
        assert clock.closed_on is None and clock.is_open
        assert compliance_for("efile_reject_turnaround", clock,
                              today=date(2026, 8, 2)).status == "missed"


def test_a_rejection_in_another_tax_year_is_not_this_years_promise():
    """Cross-year leak. The clock was read off every filing the client ever had.

    The 2023 partnership's rejection is a fact about the 2023 partnership. Shown
    against the 2025 1040 it is a promise this engagement never made, dated from
    a job that closed two years ago.
    """
    with _stored(
            _filing(RK_2023, ack="R", ack_date=date(2024, 4, 2),
                    sent=datetime(2024, 4, 1, 10, 0)),
            _filing(RK_2025, ack="A", ack_date=date(2026, 3, 1),
                    sent=datetime(2026, 2, 28, 10, 0))) as filings:
        this_year = clocks_for("efile_reject_turnaround", filings=filings,
                               client_id=CID, tax_year=2025)
        assert this_year == (), (
            "A rejection on the 2023 1065 became a broken promise on the 2025 "
            "1040 — a different return, in a different year.")

        # And the 2023 one is not swallowed: it is still answerable, in its year.
        old, = clocks_for("efile_reject_turnaround", filings=filings,
                          client_id=CID, tax_year=2023)
        assert old.subject == RK_2023 and old.tax_year == 2023


def test_two_returns_in_one_year_keep_their_own_clocks():
    """Cross-RETURN leak, which no year filter catches.

    Taking the max ack_date across a client's filings answers about whichever
    return was rejected last, under the label of whichever one you asked about.
    """
    federal = return_key(CID, 2025, "1040", "US")
    ohio = return_key(CID, 2025, "1040", "OH")
    with _stored(
            _filing(federal, ack="R", ack_date=date(2026, 3, 2),
                    sent=datetime(2026, 3, 1, 10, 0)),
            _filing(federal, ack="A", ack_date=date(2026, 3, 4), attempt=2,
                    sent=datetime(2026, 3, 3, 10, 0)),
            _filing(ohio, ack="R", ack_date=date(2026, 4, 20),
                    sent=datetime(2026, 4, 19, 10, 0))) as filings:
        clocks = {c.subject: c for c in clocks_for(
            "efile_reject_turnaround", filings=filings, client_id=CID,
            tax_year=2025)}

        assert clocks[federal].started_on == date(2026, 3, 2)
        assert clocks[federal].closed_on == date(2026, 3, 3)
        assert clocks[ohio].started_on == date(2026, 4, 20), (
            "The Ohio clock started from the federal rejection.")
        assert clocks[ohio].closed_on is None


def test_an_earlier_rejection_already_fixed_does_not_reopen():
    """Attempt 3 is the promise we owe. Attempt 1 was kept and is history."""
    with _stored(
            _filing(RK_2025, ack="R", ack_date=date(2026, 3, 2), attempt=1,
                    sent=datetime(2026, 3, 1, 10, 0)),
            _filing(RK_2025, ack="R", ack_date=date(2026, 3, 3), attempt=2,
                    sent=datetime(2026, 3, 3, 8, 0)),
            _filing(RK_2025, ack="A", ack_date=date(2026, 3, 6), attempt=3,
                    sent=datetime(2026, 3, 4, 8, 0))) as filings:
        clock, = clocks_for("efile_reject_turnaround", filings=filings,
                            client_id=CID)
        assert clock.started_on == date(2026, 3, 3)
        assert clock.closed_on == date(2026, 3, 4)


def test_a_return_never_rejected_owes_nothing_and_says_nothing():
    """No promise was made, so there is no row. Silence is right here."""
    with _stored(_filing(RK_2025, ack="A", ack_date=date(2026, 3, 4),
                         sent=datetime(2026, 3, 3, 10, 0))) as filings:
        assert clocks_for("efile_reject_turnaround", filings=filings,
                          client_id=CID) == ()


def test_another_clients_rejection_is_never_this_clients_promise():
    other = return_key("SATC-002000", 2025, "1040", "US")
    stray = Filing(filing_id="F-X", return_key=other, client_id="SATC-002000",
                   ack_code="R", ack_date=date(2026, 3, 10),
                   transmitted_at=datetime(2026, 3, 9, 10, 0))
    with _stored(stray) as filings:
        assert clocks_for("efile_reject_turnaround", filings=filings,
                          client_id=CID) == ()


def test_a_clock_nothing_records_refuses_rather_than_reading_as_nothing_owed():
    """An empty tuple would render as a clean board (principle 5)."""
    with pytest.raises(ConfigError) as exc:
        clocks_for("return_turnaround", filings=[])
    assert "unmeasurable_promises()" in str(exc.value)
    assert "once per job" in str(exc.value)


# --- said once, not once per engagement --------------------------------------


def test_the_per_item_list_carries_no_row_that_is_the_same_on_every_screen():
    """Principle 13. Four byte-identical refusals appeared on every plan.

    They are RIGHT — SATC genuinely cannot measure a promise whose start fact
    nobody records, and saying so beats a green tick from a proxy. But they say
    the same thing for every client, every workflow, every week, and a row that
    can never change is one the owner learns to skip. So they are said ONCE, as
    a capability the build lacks, and the per-item list carries only rows that
    move when somebody keys something.
    """
    per_item = measurable_slas()
    per_practice = {o.kind for o in unmeasurable_promises()}

    assert set(per_item) == {"efile_reject_turnaround"}
    assert per_practice == {"first_response", "notice_turnaround",
                            "return_turnaround", "signature_acknowledged"}

    # Neither list loses a promise, and neither says a thing twice.
    assert set(per_item) | per_practice == set(load_slas())
    assert not set(per_item) & per_practice

    for spec in per_item.values():
        out = compliance(spec.key, started_on=None, today=date(2026, 8, 2))
        assert out.status != "unmeasurable" or out.missing_fact, (
            "A per-item row refused for a reason that is not about this item.")


def test_the_structural_refusals_are_kept_and_each_names_its_own_gap():
    """Losing the noise must not lose the honesty — or four different missing
    capabilities collapse into one shrug."""
    rows = unmeasurable_promises()
    assert len({r.missing_fact for r in rows}) == len(rows), (
        "Two rows said the same thing, which is the noise this was meant to cut.")
    for row in rows:
        assert row.why.startswith("SATC cannot tell you whether this was met:")
        assert FACTS[row.missing_fact].would_need in row.why  # the next step


# --- the scope that must not be optional -------------------------------------

def test_another_clients_rejection_is_never_this_clients_promise():
    """The cross-year leak was fixed and the cross-CLIENT one left open on the
    adjacent line — the year scoped unconditionally, the client only
    ``if client_id``. A filter that can be switched off by an empty string
    eventually is, by a caller with nothing to pass."""
    from satc.config import ConfigError
    from satc.work.sla import clocks_for

    from satc.models.filing import Filing

    def _F(client_id, return_key, ack_code, ack_date):
        # The REAL Filing: is_rejected is derived from the ack code, and a stand-in
        # that only carries the attributes this test happens to read would pass
        # whether or not the resolver looks at the right ones.
        return Filing(filing_id=f"F-{client_id}-{ack_date}", return_key=return_key,
                      client_id=client_id, ack_code=ack_code, ack_date=ack_date)

    theirs = _F("SATC-AAA", "SATC-AAA|2025|1040|US", "R", date(2026, 1, 5))

    # Asking with no client is REFUSED rather than answered with everybody's.
    with pytest.raises(ConfigError) as refusal:
        clocks_for("efile_reject_turnaround", filings=[theirs], client_id="",
                   tax_year=2025)
    assert "one client" in str(refusal.value)

    # And a different client sees nothing of theirs.
    mine = clocks_for("efile_reject_turnaround", filings=[theirs],
                      client_id="SATC-BBB", tax_year=2025)
    assert not mine


def test_the_client_scope_would_actually_fail_if_it_were_dropped():
    """Mutation check — principle 12. Every other promise test hardcodes one
    client, so the filter was untested in both directions and a mutation that
    removed it left the suite green."""
    from satc.work.sla import clocks_for

    from satc.models.filing import Filing

    def _F(client_id, return_key, ack_code, ack_date):
        # The REAL Filing: is_rejected is derived from the ack code, and a stand-in
        # that only carries the attributes this test happens to read would pass
        # whether or not the resolver looks at the right ones.
        return Filing(filing_id=f"F-{client_id}-{ack_date}", return_key=return_key,
                      client_id=client_id, ack_code=ack_code, ack_date=ack_date)

    both = [_F("SATC-AAA", "SATC-AAA|2025|1040|US", "R", date(2026, 1, 5)),
            _F("SATC-BBB", "SATC-BBB|2025|1040|US", "R", date(2026, 1, 6))]
    for who in ("SATC-AAA", "SATC-BBB"):
        clocks = clocks_for("efile_reject_turnaround", filings=both,
                            client_id=who, tax_year=2025)
        assert len(clocks) == 1, "one client's rejections only"
