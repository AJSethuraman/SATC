"""THE LADDER: charter §§3-4, enforced.

Each test here is written to FAIL if the behaviour it names is removed —
mutation-tested by hand (doctrine rule 10, RULES FOR YOU): comment out the
gate check in ``ladder._build_rung`` and watch ``test_the_precondition_gate_*``
tests go red before restoring it. See the session report for the actual run.

Approvals are built through the REAL recording functions in
``satc.autonomy.approval`` (``record_approval`` / ``record_correction``)
rather than constructed by hand, so these tests also exercise the real hash
comparison an approval or correction has to pass — a test fixture that could
never actually be produced by the recording functions would prove nothing
about the ladder that reads them.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timedelta

import pytest

from satc.autonomy.approval import Approval, record_approval, record_correction
from satc.autonomy.ladder import AutonomyPolicy, load_autonomy_policy, rung_for, streaks
from satc.autonomy.preconditions import (
    ALL_PRECONDITIONS,
    gate_status,
    record_precondition,
)
from satc.models.actor import Actor

OWNER = Actor.owner()
# A policy built by hand rather than loaded from configs/firm_policy.yaml, so
# these tests do not silently drift if the practice reclassifies a template —
# routine=5, money_or_deadline=10, cadence=90, with two templates explicitly
# marked routine for the happy-path tests below.
DEFAULT_POLICY = AutonomyPolicy(routine_templates=frozenset({"status_update", "birthday"}))


def _approve(template_key: str, client_id: str, on: date) -> Approval:
    """A clean send: what went out is exactly what SATC rendered."""
    return record_approval(actor=OWNER, template_key=template_key, client_id=client_id,
                           rendered_text=f"draft for {template_key}/{client_id}", decided_on=on)


def _correct(template_key: str, client_id: str, on: date, reason: str) -> Approval:
    """An edited send, with one of the five reason codes."""
    return record_correction(actor=OWNER, template_key=template_key, client_id=client_id,
                             rendered_text=f"draft for {template_key}/{client_id}",
                             sent_text=f"draft for {template_key}/{client_id}, but corrected",
                             reason=reason, decided_on=on)


def _clean_gate(as_of: date):
    """All three preconditions confirmed today — the gate holds."""
    return [record_precondition(actor=OWNER, key=k, confirmed_on=as_of) for k in ALL_PRECONDITIONS]


def _lapsed_gate(as_of: date, cadence_days: int):
    """All three confirmed once, long enough ago that the cadence has passed."""
    stale = as_of - timedelta(days=cadence_days + 30)
    return [record_precondition(actor=OWNER, key=k, confirmed_on=stale) for k in ALL_PRECONDITIONS]


# --- the streak accrues and resets -------------------------------------------

def test_a_streak_accrues_to_earned_then_a_correction_resets_it_to_zero():
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [_approve("status_update", "C-1", today + timedelta(days=i))
                for i in range(DEFAULT_POLICY.routine_n)]

    rung = rung_for(("status_update", "C-1"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert rung.state == "earned"
    assert rung.streak == DEFAULT_POLICY.routine_n
    assert rung.needed == DEFAULT_POLICY.routine_n
    assert rung.blocked_reason == ""

    approvals.append(_correct("status_update", "C-1",
                              today + timedelta(days=DEFAULT_POLICY.routine_n + 1),
                              reason="wrong_judgment"))
    demoted = rung_for(("status_update", "C-1"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert demoted.state == "draft_only"
    assert demoted.streak == 0
    assert "the call was wrong" in demoted.why       # REASON_CODES["wrong_judgment"]


# --- consecutive means consecutive FOR THAT PAIR, not close in time ----------

def test_a_gap_in_time_does_not_break_the_streak():
    """A client emailed twice a year still reaches rung 5 in three years —
    that is the correct amount of evidence, not a bug (charter §4)."""
    gate = _clean_gate(date(2029, 1, 1))
    approvals = [
        _approve("birthday", "C-2", date(2026, 3, 1)),
        _approve("birthday", "C-2", date(2027, 3, 1)),   # a year later
        _approve("birthday", "C-2", date(2028, 3, 1)),   # another year
        _approve("birthday", "C-2", date(2028, 12, 1)),
        _approve("birthday", "C-2", date(2029, 1, 1)),
    ]
    rung = rung_for(("birthday", "C-2"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=date(2029, 1, 1))
    assert rung.state == "earned"
    assert rung.streak == 5


# --- an unclassified template is the STRICTER rung ---------------------------

def test_an_unclassified_template_needs_ten_not_five():
    """Not on the routine list and not on the money_or_deadline list either —
    charter §4: nobody having classified it is treated as the stricter case."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [_approve("some_new_template", "C-3", today + timedelta(days=i))
                for i in range(5)]

    at_five = rung_for(("some_new_template", "C-3"), approvals,
                       policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert at_five.needed == 10
    assert at_five.state == "draft_only"          # 5 of 10 is not earned

    approvals += [_approve("some_new_template", "C-3", today + timedelta(days=5 + i))
                 for i in range(5)]
    at_ten = rung_for(("some_new_template", "C-3"), approvals,
                      policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert at_ten.state == "earned"
    assert at_ten.streak == 10


# --- demotion: wrong_fact spreads, the other four codes do not ---------------

def test_a_wrong_fact_correction_demotes_every_pair_on_that_template():
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = (
        [_approve("missing_items", "CLIENT-A", today + timedelta(days=i)) for i in range(3)]
        + [_approve("missing_items", "CLIENT-B", today + timedelta(days=i)) for i in range(3)]
    )
    # The correction lands on CLIENT-A's copy, after both have accrued.
    approvals.append(_correct("missing_items", "CLIENT-A", today + timedelta(days=10),
                              reason="wrong_fact"))

    a = rung_for(("missing_items", "CLIENT-A"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    b = rung_for(("missing_items", "CLIENT-B"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert a.streak == 0
    assert b.streak == 0, "a wrong_fact correction on one client must reset every client on this template"
    assert "wrong-fact" in b.why or "wrong fact" in b.why


def test_a_non_wrong_fact_correction_demotes_only_the_corrected_pair():
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = (
        [_approve("missing_items", "CLIENT-A", today + timedelta(days=i)) for i in range(3)]
        + [_approve("missing_items", "CLIENT-B", today + timedelta(days=i)) for i in range(3)]
    )
    for reason in ("wrong_judgment", "should_not_have_flagged", "gave_up", "missing_capability"):
        corrected = approvals + [_correct("missing_items", "CLIENT-A",
                                          today + timedelta(days=10), reason=reason)]
        a = rung_for(("missing_items", "CLIENT-A"), corrected, policy=DEFAULT_POLICY, preconditions=gate, today=today)
        b = rung_for(("missing_items", "CLIENT-B"), corrected, policy=DEFAULT_POLICY, preconditions=gate, today=today)
        assert a.streak == 0, reason
        assert b.streak == 3, f"{reason} must not touch a sibling pair, only wrong_fact does"


# --- the streak is walked in TIME order, never input-list order --------------
#
# _compute's docstring is explicit: it has to be ONE walk, in true time order,
# because a wrong_fact correction reaching into a sibling pair "lands at the
# moment it actually happened" and not wherever the caller's list happened to
# put it. A store load has no guaranteed row order, so if _compute ever trusted
# list order instead of sorting via all_approvals(), a shuffled load would
# silently produce a different streak than a sorted one for the exact same
# facts.

def test_streak_reflects_true_time_order_not_the_order_events_were_handed_in():
    """True chronological order is approve, approve, correct — the correction
    happened LAST and must win, resetting the streak to zero. Handing the same
    three events to rung_for in a different list order must not change that."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    d1, d2, d3 = today, today + timedelta(days=1), today + timedelta(days=2)

    approve1 = _approve("status_update", "C-20", d1)
    approve2 = _approve("status_update", "C-20", d2)
    correct3 = _correct("status_update", "C-20", d3, reason="wrong_judgment")

    # Fed out of chronological order: the correction (truly last) sits in the
    # middle of the list.
    shuffled = [approve1, correct3, approve2]

    rung = rung_for(("status_update", "C-20"), shuffled, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today)
    assert rung.streak == 0, "the correction happened last in TIME and must win"
    assert rung.state == "draft_only"


def test_wrong_fact_sibling_reset_lands_at_the_moment_it_happened_not_list_order():
    """B approves, A's wrong_fact correction resets both A and B (B was already
    on record at that moment), and THEN B approves again — a fresh streak of 1
    that happened after the reset. The answer must not depend on what order the
    caller's list put these rows in."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    d1, d2, d3, d4 = (today, today + timedelta(days=1),
                      today + timedelta(days=2), today + timedelta(days=3))

    a_approve = _approve("missing_items", "CLIENT-A", d1)
    b_approve1 = _approve("missing_items", "CLIENT-B", d2)
    a_correct = _correct("missing_items", "CLIENT-A", d3, reason="wrong_fact")
    b_approve2 = _approve("missing_items", "CLIENT-B", d4)   # truly AFTER the reset

    # List order deliberately scrambled relative to decided_on order.
    shuffled = [a_approve, b_approve2, b_approve1, a_correct]

    b_rung = rung_for(("missing_items", "CLIENT-B"), shuffled, policy=DEFAULT_POLICY,
                      preconditions=gate, today=today)
    assert b_rung.streak == 1, (
        "an approval that truly happened after the wrong_fact correction must "
        "still count fresh, regardless of the order the caller supplied the rows in")


def test_a_same_day_correction_and_approval_are_ordered_by_the_clock():
    """The other half of time order, and the one the record USED to get wrong.

    Both tests above put every decision on its own day, so ``decided_on``
    alone answers them and the ``recorded_at`` tiebreak could vanish without
    either noticing. Two decisions about one pair on ONE day are ordered by
    the moment the owner clicked — nothing else in the record can say which
    came last, and it used to be settled by whichever draft's SHA-256 sorted
    higher.

    Asserted in both directions on purpose: a hash tiebreak returns the same
    order whichever way round the clocks are set, so one of these two has to
    fail if the clock stops being consulted."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    day = today + timedelta(days=1)
    morning = datetime(2026, 1, 2, 9, 0)
    afternoon = datetime(2026, 1, 2, 15, 0)

    approve = _approve("status_update", "C-21", day)
    correct = _correct("status_update", "C-21", day, reason="wrong_judgment")

    corrected_last = rung_for(
        ("status_update", "C-21"),
        [dataclasses.replace(approve, recorded_at=morning),
         dataclasses.replace(correct, recorded_at=afternoon)],
        policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert corrected_last.streak == 0, "the correction was keyed in last; it must win"

    approved_last = rung_for(
        ("status_update", "C-21"),
        [dataclasses.replace(approve, recorded_at=afternoon),
         dataclasses.replace(correct, recorded_at=morning)],
        policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert approved_last.streak == 1, (
        "same two decisions, same day, clocks the other way round — the "
        "approval was keyed in last and accrues on top of the correction")


def test_the_ladder_reads_the_bytes_not_the_reason_column():
    """``Approval.outcome`` is a hash comparison (charter §4) and the ladder
    has to ASK it rather than look at ``reason`` itself. A row that carries a
    reason code but whose sent text is byte-identical to what SATC rendered is
    an approval — the draft went out unchanged, whatever a column says — and
    it accrues. Every fixture in this file gets its reason from the recording
    function that also set the hashes, so nothing here would otherwise notice
    the ladder grading itself from the label."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [_approve("status_update", "C-22", today + timedelta(days=i))
                 for i in range(3)]
    approvals[1] = dataclasses.replace(approvals[1], reason="wrong_fact")

    rung = rung_for(("status_update", "C-22"), approvals, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today)
    assert rung.streak == 3, (
        "a reason column on a row whose bytes match is not a correction — "
        "the outcome is the hash comparison, never the label")


def test_the_corrected_pair_is_told_it_was_corrected_not_swept_up_as_a_sibling():
    """The wrong_fact sweep reaches every OTHER pair on the template, and the
    pair that was actually corrected keeps its own sentence with the reason
    code the owner picked. Both land on streak zero, so a test that checked
    only the number cannot tell them apart — and telling the owner their draft
    was "reset by a wrong-fact correction on their own draft" answers a
    question nobody asked (principle 10)."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = (
        [_approve("missing_items", "CLIENT-A", today + timedelta(days=i)) for i in range(3)]
        + [_approve("missing_items", "CLIENT-B", today + timedelta(days=i)) for i in range(3)]
        + [_correct("missing_items", "CLIENT-A", today + timedelta(days=10),
                    reason="wrong_fact")]
    )
    a = rung_for(("missing_items", "CLIENT-A"), approvals, policy=DEFAULT_POLICY,
                 preconditions=gate, today=today)
    assert a.streak == 0
    assert "it stated something untrue" in a.why, (
        "the corrected pair must read as its own correction, with its reason code")
    assert "reset by a wrong-fact correction" not in a.why


# --- the precondition gate is a HARD gate -------------------------------------

def test_the_precondition_gate_holds_every_pair_at_zero_however_clean_the_record():
    """No precondition ever recorded at all: charter §3 — the ladder refuses to
    accrue ANYTHING, no matter how many clean approvals sit on file."""
    today = date(2026, 1, 1)
    approvals = [_approve("status_update", "C-4", today + timedelta(days=i))
                for i in range(DEFAULT_POLICY.routine_n)]     # would be "earned" if ungated

    rung = rung_for(("status_update", "C-4"), approvals, policy=DEFAULT_POLICY, preconditions=[])
    assert rung.state == "draft_only"
    assert rung.streak == 0
    assert rung.blocked_reason, "must name the reason, not just refuse silently"
    assert "never recorded" in rung.blocked_reason


def test_a_lapsed_reconfirmation_freezes_accrual_without_demoting():
    """Recorded once, long enough ago to have gone stale: charter §3 — freezes,
    does not wipe the record. The streak must still be VISIBLE, just capped
    below earned."""
    today = date(2026, 6, 1)
    gate = _lapsed_gate(today, DEFAULT_POLICY.precondition_cadence_days)
    # Enough clean approvals that, ungated, this pair would already be earned.
    approvals = [_approve("status_update", "C-5", today - timedelta(days=DEFAULT_POLICY.routine_n - i))
                for i in range(DEFAULT_POLICY.routine_n)]

    rung = rung_for(("status_update", "C-5"), approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert rung.state == "draft_only", "frozen means it cannot cross into earned"
    assert rung.streak == DEFAULT_POLICY.routine_n, "demotes nothing — the real count must still show"
    assert rung.blocked_reason
    assert "lapsed" in rung.blocked_reason


def test_streaks_lists_every_pair_the_record_has_seen():
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [
        _approve("welcome", "C-6", today),
        _approve("welcome", "C-7", today),
        _correct("welcome", "C-8", today, reason="gave_up"),
    ]
    rungs = streaks(approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    pairs = {r.pair for r in rungs}
    assert pairs == {("welcome", "C-6"), ("welcome", "C-7"), ("welcome", "C-8")}


def test_streaks_is_ordered_by_pair_not_by_when_each_pair_first_appeared():
    """``streaks``' own claim: ordered by (template_key, client_id) so the
    screen is stable run to run rather than shuffling with whatever order the
    store happened to load rows in — "a queue that reorders itself for no
    reason is noise" (principle 13). The test above compares a SET, which
    cannot see order at all, and the pairs below are deliberately introduced
    in an order that is not their sorted one."""
    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [
        _approve("welcome", "C-33", today),
        _approve("birthday", "C-31", today + timedelta(days=1)),
        _approve("welcome", "C-30", today + timedelta(days=2)),
        _approve("birthday", "C-32", today + timedelta(days=3)),
    ]
    rungs = streaks(approvals, policy=DEFAULT_POLICY, preconditions=gate, today=today)
    assert [r.pair for r in rungs] == [
        ("birthday", "C-31"), ("birthday", "C-32"),
        ("welcome", "C-30"), ("welcome", "C-33")]


# --- N is firm policy: a config edit changes the answer, no code change -----

def test_changing_a_threshold_in_a_temp_config_changes_the_answer(tmp_path):
    (tmp_path / "firm_policy.yaml").write_text(
        "autonomy:\n"
        "  thresholds:\n"
        "    routine: 2\n"
        "    money_or_deadline: 3\n"
        "  precondition_reconfirm_days: 30\n"
        "  templates:\n"
        "    routine:\n"
        "      - welcome\n",
        encoding="utf-8")
    strict_policy = load_autonomy_policy(tmp_path)
    assert strict_policy.threshold_for("welcome") == 2

    (tmp_path / "firm_policy.yaml").write_text(
        "autonomy:\n"
        "  thresholds:\n"
        "    routine: 9\n"
        "    money_or_deadline: 12\n"
        "  precondition_reconfirm_days: 30\n"
        "  templates:\n"
        "    routine:\n"
        "      - welcome\n",
        encoding="utf-8")
    loose_policy = load_autonomy_policy(tmp_path)
    assert loose_policy.threshold_for("welcome") == 9

    today = date(2026, 1, 1)
    gate = _clean_gate(today)
    approvals = [_approve("welcome", "C-9", today + timedelta(days=i)) for i in range(3)]

    with_strict = rung_for(("welcome", "C-9"), approvals, policy=strict_policy, preconditions=gate, today=today)
    with_loose = rung_for(("welcome", "C-9"), approvals, policy=loose_policy, preconditions=gate, today=today)
    assert with_strict.state == "earned"          # 3 of 2
    assert with_loose.state == "draft_only"        # 3 of 9
    assert with_strict.needed == 2 and with_loose.needed == 9


def test_a_template_listed_under_both_routine_and_money_or_deadline_is_refused(tmp_path):
    from satc.config import ConfigError

    (tmp_path / "firm_policy.yaml").write_text(
        "autonomy:\n"
        "  templates:\n"
        "    routine:\n"
        "      - welcome\n"
        "    money_or_deadline:\n"
        "      - welcome\n",
        encoding="utf-8")
    with pytest.raises(ConfigError):
        load_autonomy_policy(tmp_path)


def test_a_firm_policy_file_that_is_not_a_policy_is_refused_not_defaulted(tmp_path):
    """The other side of the test below, and the line between them is
    principle 5. NO file means "no preferences recorded yet" and documents
    itself as the strict defaults. A file that IS there and cannot be read as
    a policy is a different fact entirely: handing back defaults would run the
    ladder on thresholds nobody chose while a broken config sat on disk with
    nothing said about it."""
    from satc.config import ConfigError

    (tmp_path / "firm_policy.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_autonomy_policy(tmp_path)

    (tmp_path / "firm_policy.yaml").write_text(
        "autonomy:\n  - not a mapping either\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_autonomy_policy(tmp_path)


def test_a_missing_config_file_falls_back_to_the_strict_built_in_defaults(tmp_path):
    """An empty directory (no firm_policy.yaml at all) must not crash the
    ladder — it reads as the strictest defaults, never as an error that takes
    the whole screen down (principle 5's "refuse rather than default" is about
    guessing an ANSWER; falling back to the documented strict default here is
    not a guess, it is what the loader promises when nothing is on file)."""
    policy = load_autonomy_policy(tmp_path)
    assert policy.routine_n == 5
    assert policy.money_or_deadline_n == 10
    assert policy.threshold_for("anything") == 10


def test_the_real_firm_policy_yaml_classifies_all_eighteen_templates():
    """Guards the config edit itself: every template the comms library knows
    about must land on exactly one side of routine/money_or_deadline, so
    nothing is silently defaulting to the strict rung by accident."""
    from satc.comms.library import load_library

    policy = load_autonomy_policy()
    keys = set(load_library().keys())
    classified = policy.routine_templates | policy.money_or_deadline_templates
    assert keys, "the comms library must not be empty"
    assert keys <= classified, keys - classified
    assert not (policy.routine_templates & policy.money_or_deadline_templates)


# --- a lapse must not take away what was already earned ----------------------
#
# Charter §3 makes two promises that pull different ways: a lapse "freezes
# accrual" AND "demotes nothing". Implementing either alone is wrong, and both
# wrong answers were written before this test existed — one discarded the
# evidence, the other knocked an earned pair back to draft_only.

def test_a_pair_earned_before_the_lapse_stays_earned():
    """Demoting on a paperwork lapse is exactly what the charter says would
    train the owner to resent the gate."""
    today = date(2026, 6, 1)
    cadence = DEFAULT_POLICY.precondition_cadence_days

    # Confirmed once, long ago: the freeze lands cadence days after that.
    gate = _lapsed_gate(today, cadence)
    frozen_from = gate_status(gate, cadence_days=cadence, today=today).frozen_since
    assert frozen_from is not None, "a lapsed gate must say WHEN accrual stopped"

    # A full streak completed BEFORE the freeze.
    approvals = [_approve("status_update", "C-9", frozen_from - timedelta(days=n + 1))
                 for n in reversed(range(DEFAULT_POLICY.routine_n))]

    rung = rung_for(("status_update", "C-9"), approvals, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today)
    assert rung.state == "earned", (
        "a lapsed confirmation demoted a pair that had already crossed")
    assert "before the freeze" in rung.why
    assert rung.blocked_reason, "it should still say the gate is stale"


def test_approvals_after_the_freeze_still_count_as_evidence():
    """The other half. Five clean approvals during a stale confirmation really
    did happen (principle 2) — wiping them is a demotion in substance, whatever
    it is labelled. They show; they just cannot carry the pair across."""
    today = date(2026, 6, 1)
    gate = _lapsed_gate(today, DEFAULT_POLICY.precondition_cadence_days)
    approvals = [_approve("status_update", "C-10", today - timedelta(days=n + 1))
                 for n in reversed(range(DEFAULT_POLICY.routine_n))]

    rung = rung_for(("status_update", "C-10"), approvals, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today)
    assert rung.streak == DEFAULT_POLICY.routine_n, "the evidence was discarded"
    assert rung.state == "draft_only", "it crossed while the gate was stale"


def test_an_approval_on_the_last_day_the_gate_still_held_counts_toward_earned():
    """The boundary itself, which both tests above step around.

    ``frozen_since`` is ``last_confirmed + cadence``, and ``gate_status``
    still reports the gate as HOLDING on that day — it goes stale the day
    after (``(as_of - confirmed).days > cadence_days``). So an approval
    decided ON ``frozen_since`` happened while the practice genuinely met the
    bar, and it has to count: ``PreconditionGate.frozen_since``'s own
    docstring says "approvals after this day do not count, and everything up
    to it stands". Discarding it demotes a pair that had crossed, over a
    paperwork lapse — exactly the thing charter §3 forbids."""
    today = date(2026, 6, 1)
    cadence = DEFAULT_POLICY.precondition_cadence_days
    gate = _lapsed_gate(today, cadence)
    frozen_from = gate_status(gate, cadence_days=cadence, today=today).frozen_since
    assert frozen_from is not None
    # Said out loud, because the whole test rests on it: on frozen_from the
    # gate had not lapsed yet.
    assert gate_status(gate, cadence_days=cadence, today=frozen_from).holds
    assert not gate_status(gate, cadence_days=cadence,
                           today=frozen_from + timedelta(days=1)).holds

    n = DEFAULT_POLICY.routine_n
    approvals = [_approve("status_update", "C-13", frozen_from - timedelta(days=n - 1 - i))
                 for i in range(n)]
    assert approvals[-1].decided_on == frozen_from, "the last one lands on the boundary"

    rung = rung_for(("status_update", "C-13"), approvals, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today)
    assert rung.state == "earned", (
        "the pair completed its streak on the last day the gate still held, "
        "and the lapse afterwards must not take that away")


def test_streaks_does_not_promote_a_pair_that_only_crossed_during_the_freeze():
    """``rung_for`` is not the only door onto this answer. ``streaks()``
    renders the whole screen and computes ``earned_before`` by its own second
    walk — every lapse test above goes through ``rung_for``, so that walk
    could stop being cut off at the freeze and nothing would notice."""
    today = date(2026, 6, 1)
    gate = _lapsed_gate(today, DEFAULT_POLICY.precondition_cadence_days)
    pair = ("status_update", "C-14")
    approvals = [_approve(*pair, today - timedelta(days=n + 1))
                 for n in reversed(range(DEFAULT_POLICY.routine_n))]

    rung = {r.pair: r for r in streaks(approvals, policy=DEFAULT_POLICY,
                                       preconditions=gate, today=today)}[pair]
    assert rung.streak == DEFAULT_POLICY.routine_n, "the evidence still shows"
    assert rung.state == "draft_only", (
        "every one of these approvals landed after the freeze — none of them "
        "may carry the pair across")


def test_the_freeze_date_is_what_separates_the_two():
    """Mutation check — principle 12. If frozen_since stopped being computed,
    'earned before the freeze' and 'earned during it' become the same question
    and one of the two tests above starts lying."""
    today = date(2026, 6, 1)
    cadence = DEFAULT_POLICY.precondition_cadence_days
    lapsed = gate_status(_lapsed_gate(today, cadence), cadence_days=cadence, today=today)
    clean = gate_status(_clean_gate(today), cadence_days=cadence, today=today)

    assert lapsed.frozen_since is not None
    assert clean.frozen_since is None, "nothing is frozen when the gate holds"
    assert lapsed.frozen_since < today


# --- the four things the reviewers found, pinned ------------------------------

def test_an_off_ladder_capability_cannot_accrue_at_all():
    """Charter §2 calls these "not a rung; not a rung that exists" — and nothing
    enforced it, so any string was a valid template_key and a capability that
    must never graduate could quietly build a streak."""
    from satc.autonomy.approval import ApprovalError

    for key in ("efile_the_return", "sign_8879", "charge_the_card", "delete_client"):
        with pytest.raises(ApprovalError) as refusal:
            record_approval(actor=Actor.owner(), template_key=key, client_id="CL-1",
                            rendered_text="x", decided_on=date(2026, 3, 1))
        assert "permanently off the autonomy ladder" in str(refusal.value)
        # BOTH doors — a correction is a fact about a pair too.
        with pytest.raises(ApprovalError):
            record_correction(actor=Actor.owner(), template_key=key, client_id="CL-1",
                              rendered_text="x", sent_text="y", reason="wrong_fact",
                              decided_on=date(2026, 3, 1))


def test_every_shipped_template_is_still_allowed():
    """Guards against over-fixing. 'signature_request' ASKS a client to sign and
    is an ordinary letter; banning it would leave the ladder with nothing on it."""
    from satc.autonomy.approval import scope_refusal
    from satc.comms import library

    refused = [k for k in library().keys() if scope_refusal(k)]
    assert not refused, f"legitimate templates refused: {refused}"


def test_a_missed_trap_actually_demotes_the_templates_it_holds():
    """Charter §7. DrillResult.demotions was read in exactly one place in the
    whole codebase — a print statement in the CLI — so the digest reported a
    demotion that never happened."""
    import dataclasses

    from satc.autonomy.traps import run_drill, templates_held

    today = date(2026, 6, 1)
    gate = _clean_gate(today)
    approvals = [_approve("invoice_cover", "C-11", today - timedelta(days=n + 1))
                 for n in reversed(range(DEFAULT_POLICY.money_or_deadline_n))]

    clean = run_drill(today=today)
    earned = rung_for(("invoice_cover", "C-11"), approvals, policy=DEFAULT_POLICY,
                      preconditions=gate, today=today, held=templates_held(clean))
    assert earned.state == "earned"

    missed = dataclasses.replace(
        clean,
        traps=tuple(dataclasses.replace(t, passed=False)
                    if "invoice_cover" in t.holds else t for t in clean.traps))
    held = rung_for(("invoice_cover", "C-11"), approvals, policy=DEFAULT_POLICY,
                    preconditions=gate, today=today, held=templates_held(missed))
    assert held.state == "draft_only", "a trap miss demoted nothing"
    assert "missed last night" in held.why


def test_no_drill_on_file_holds_everything():
    """"Nobody ran it" is the strongest version of "could not run", and charter
    §7 says that counts as a miss. A scoreboard reading a silent night as a
    clean one is the failure the rule exists to prevent."""
    from satc.autonomy.traps import HOLD_EVERYTHING, templates_held

    assert templates_held(None) == HOLD_EVERYTHING

    today = date(2026, 6, 1)
    approvals = [_approve("welcome", "C-12", today - timedelta(days=n + 1))
                 for n in reversed(range(DEFAULT_POLICY.routine_n))]
    rung = rung_for(("welcome", "C-12"), approvals, policy=DEFAULT_POLICY,
                    preconditions=_clean_gate(today), today=today,
                    held=templates_held(None))
    assert rung.state == "draft_only"


def test_a_precondition_ticked_today_does_not_hold_for_last_march():
    """A record that improves the past is not a record."""
    from satc.autonomy.preconditions import gate_status

    ticked_now = _clean_gate(date(2026, 8, 7))
    past = gate_status(ticked_now, cadence_days=90, today=date(2026, 3, 20))
    assert not past.holds
    assert past.missing, "a confirmation recorded later must not cover an earlier day"
