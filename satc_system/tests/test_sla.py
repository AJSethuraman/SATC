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

from datetime import date

import pytest

from satc.config import ConfigError
from satc.obligations.profile import ObligationInstance
from satc.work import sla as sla_mod
from satc.work.sla import (
    FACTS,
    compliance,
    load_slas,
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
    """Not yet is not a verdict. An unanswered question is not an answer."""
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     today=date(2026, 3, 4))
    assert out.status == "open"
    assert not out.is_met and not out.is_missed


def test_a_measurable_promise_past_its_date_with_nothing_recorded_is_missed(policy):
    """Only reachable when the closing fact CAN be recorded.

    Then silence is a real answer about this item — we can see retransmissions,
    and there isn't one. Where the closing fact cannot be recorded at all, the
    gate above this one refuses instead, and that is the difference between a
    statement about a client and a statement about the codebase.
    """
    write(policy, days=2)
    out = compliance("fix_a_reject", started_on=date(2026, 3, 3),
                     today=date(2026, 3, 20))
    assert out.status == "missed"
    assert "nothing records when the fixed return went back out" in out.why


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


def test_no_delivery_fact_is_invented_from_a_finished_task_list():
    """satc.work.stage refuses to conclude delivery; this must not undo that."""
    assert not FACTS["return_delivered"].is_recorded
    assert "a finished task list is not a delivery" in \
        FACTS["return_delivered"].would_need


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
