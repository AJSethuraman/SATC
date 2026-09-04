"""The engine: what it refuses, what it catches, and what it lets through.

The outcome that matters is `wrongly_absorbed` — an answer that was wrong, that
the engine could not fault, and that would therefore have reached a client with
nobody the wiser. Every other outcome costs a little time. That one costs the
reason to trust all the others, so it is tested hardest and reported first.
"""
from __future__ import annotations

import socket

import pytest

import record
from conftest import NetworkUsed
from engine import (Answer, EngineError, Outcome, REASONS, grade, report,
                    serve, tally)





# ── the guard on the guard ────────────────────────────────────────────────────

def test_the_no_network_guard_can_actually_fail():
    """Prove the autouse fixture bites. Without this, "offline" is a comment."""
    with pytest.raises(NetworkUsed):
        socket.socket()


# ── the two outcomes that look alike and are not ──────────────────────────────

def test_a_right_answer_with_authority_that_holds_is_correct(fixed_assets, problem):
    r = grade(Answer(position=problem.answer, citation=problem.citation), problem, fixed_assets)
    assert r.outcome is Outcome.CORRECT
    assert not r.costly


def test_a_wrong_answer_the_engine_cannot_fault_is_wrongly_absorbed(
        fixed_assets, problem, wrong_position):
    """The citation resolves, the source binds, and the answer is still wrong.

    Nothing in the engine can catch this, which is exactly why it is counted
    separately: in production it ships.
    """
    r = grade(
        Answer(position=wrong_position, citation=problem.citation),
        problem, fixed_assets)
    assert r.outcome is Outcome.WRONGLY_ABSORBED
    assert r.costly, "this is the only outcome that costs anything"
    assert problem.answer in r.detail, "the report must say what the authority concluded"


def test_wrong_but_caught_is_not_counted_as_wrongly_absorbed(
        fixed_assets, problem, wrong_position):
    """A wrong answer whose citation does not resolve was stopped, not shipped.

    Folding these two together would hide the number the firm actually reads.
    """
    r = grade(
        Answer(position=wrong_position, citation="26 CFR 9.9-9"),
        problem, fixed_assets)
    assert r.outcome is Outcome.WRONG_CAUGHT
    assert not r.costly


# ── refusal is code, not prose ────────────────────────────────────────────────

def test_an_uncited_answer_is_never_correct_even_when_it_is_right(
        fixed_assets, problem):
    """The one that matters. A right answer with no authority is still refused.

    If this ever returns CORRECT, "cite authority or refuse" has quietly become
    advice again — which is what rule 6 measured at 100%, 4%, 0% of runs.
    """
    r = grade(Answer(position=problem.answer, citation=""), problem, fixed_assets)
    assert r.outcome is not Outcome.CORRECT
    assert r.outcome is Outcome.WRONG_CAUGHT
    assert r.reason == "no_citation"


def test_a_refusal_names_the_next_step(fixed_assets, problem):
    """On a small model a bare "no" ends the run; a refusal that names the next
    step self-corrects it (LOCAL-LLM-PATTERN rule 3)."""
    r = grade(Answer(position="x", citation="26 CFR 9.9-9"), problem, fixed_assets)
    assert r.detail, "a refusal with no next step teaches nothing"
    assert "escalate" in r.detail or "add it" in r.detail


def test_a_citation_the_desk_does_not_hold_is_authority_absent(
        fixed_assets, problem):
    r = grade(Answer(position="x", citation="26 CFR 9.9-9"), problem, fixed_assets)
    assert r.reason == "authority_absent"


# ── escalation is a success, and it carries a reason from a closed set ────────

def test_an_escalation_is_recorded_as_a_success_with_its_reason(
        fixed_assets, problem):
    r = grade(
        Answer(position="", escalated=True, reason="authority_permits_choice"),
        problem, fixed_assets)
    assert r.outcome is Outcome.ESCALATED
    assert r.reason == "authority_permits_choice"
    assert not r.costly, "an escalation is the desk knowing it does not know"


def test_an_escalation_reason_outside_the_closed_set_is_an_error(
        fixed_assets, problem):
    """An open reason set becomes prose, and prose cannot be counted."""
    with pytest.raises(EngineError, match="not one of"):
        grade(Answer(position="", escalated=True, reason="dunno"),
              problem, fixed_assets)


def test_our_block_and_their_refusal_are_different_reasons():
    """They were one reason, and collapsing them produced a real defect: the
    single prescribed fix was "grant the domain", met by a case where the domain
    was already granted. Different senders, different fixes."""
    assert "source_blocked_by_us" in REASONS
    assert "source_refuses_us" in REASONS


def test_only_one_reason_is_not_fixable():
    """A question the rules genuinely leave open is a position, and positions are
    the firm's. Everything else is a work item."""
    assert "authority_permits_choice" in REASONS


# ── tier gates the answer ─────────────────────────────────────────────────────

def test_authority_that_only_interprets_escalates_rather_than_answers(
        tmp_path, problem):
    """A Big 4 guide's reading must never be handed over in a regulation's voice."""
    d = tmp_path / "secondary-only"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · An interpretive guide\n\n"
        "**Tier:** secondary · **Access:** public_fetch · "
        "**May store:** citation_only · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** GUIDE\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** GUIDE 1\n\n**Answer:** must capitalize\n\n"
        "**Facts:** f\n", encoding="utf-8")
    (d / "extracted" / "g.md").write_text(
        "## GUIDE 1\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n> a reading\n",
        encoding="utf-8")
    desk = record.load(d)
    r = grade(Answer(position="must capitalize", citation="GUIDE 1"),
              desk.problems[0], desk)
    assert r.outcome is Outcome.ESCALATED
    assert r.reason == "authority_permits_choice"


# ── the denominator is reported so the costly number is read first ────────────

def test_the_report_puts_wrongly_absorbed_first_and_states_zero(
        fixed_assets, problem):
    results = [grade(Answer(position=problem.answer, citation=problem.citation),
                     problem, fixed_assets)]
    text = report(results)
    lines = [l.strip() for l in text.splitlines()]
    assert lines[0].startswith("1 graded")
    assert lines[1].startswith("wrongly_absorbed"), (
        "the number that costs something must be read before the ones that do not"
    )
    assert lines[1].endswith("0"), "zero is stated, not omitted"


def test_the_tally_counts_every_outcome_even_the_absent_ones(
        fixed_assets, problem):
    counts = tally([grade(Answer(position=problem.answer, citation=problem.citation),
                          problem, fixed_assets)])
    assert set(counts) == {o.value for o in Outcome}
    assert counts["correct"] == 1
    assert counts["wrongly_absorbed"] == 0


def test_outcomes_are_never_summed_into_one_figure():
    """`report` must not emit a percentage or a score. A single number hides the
    only one that matters."""
    assert "%" not in report([])


# ── the comparison must not be generous ───────────────────────────────────────

def test_case_and_surrounding_space_do_not_change_the_verdict(
        fixed_assets, problem):
    r = grade(Answer(position=f"  {problem.answer.upper()}  ", citation=problem.citation),
              problem, fixed_assets)
    assert r.outcome is Outcome.CORRECT


def test_a_near_miss_is_not_treated_as_a_match(fixed_assets, problem):
    """A looser comparison would quietly turn wrong answers into right ones —
    the one direction this code must never fail in."""
    r = grade(Answer(position=problem.answer + " partially", citation=problem.citation),
              problem, fixed_assets)
    assert r.outcome is Outcome.WRONGLY_ABSORBED


# ── a ratified position is the firm's word, and the engine holds it to that ────

def _human_only_desk(tmp_path, *, position="not required to capitalize",
                     passage_text=None):
    """A desk whose only authority on a citation is what the firm wrote.

    This is the `human_only` shape: a source the engine may never read, where a
    ratified position is the desk's entire knowledge of it. `passage_text` adds
    a stored passage on the SAME citation, which is the case where the two kinds
    of authority compete.
    """
    d = tmp_path / "positions-desk"
    (d / "extracted").mkdir(parents=True)
    (d / "positions").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source we may not read\n\n"
        "**Tier:** tertiary · **Access:** human_only · "
        "**May store:** license_check · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 360-10\n\n"
        "**Answer:** not required to capitalize\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · What we do here\n\n"
        "**Citation:** ASC 360-10 · **Recorded:** 2026-09-04\n\n"
        f"**Position:** {position}\n\n"
        "**Ratified:** the firm, 4 September 2026\n", encoding="utf-8")
    if passage_text is not None:
        (d / "extracted" / "p.md").write_text(
            "## ASC 360-10\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n"
            f"> {passage_text}\n", encoding="utf-8")
    import record
    return record.load(d)


def test_citing_the_firms_position_and_answering_the_opposite_is_caught(tmp_path):
    """The one path that exists because a human decided did not check the human's
    decision: the branch approved on the citation alone, so a model could cite a
    real position, hand back the opposite conclusion, and have `serve()` return
    it as the firm's own answer."""
    desk = _human_only_desk(tmp_path, position="not required to capitalize")
    r = grade(Answer(position="must capitalize", citation="ASC 360-10"),
              desk.problems[0], desk)
    assert r.outcome is Outcome.WRONG_CAUGHT
    assert r.reason == "contradicts_ratified_position"


def test_agreeing_with_the_position_serves_the_firms_own_wording(tmp_path):
    """Not the model's restatement of it, however close. The engine disposes."""
    desk = _human_only_desk(tmp_path, position="not required to capitalize")
    served = serve(Answer(position="  NOT REQUIRED TO CAPITALIZE  ",
                          citation="ASC 360-10"), desk)
    assert served, f"a matching position should serve: {served}"
    assert served.position == "not required to capitalize"


def test_a_ratified_position_outranks_a_passage_on_the_same_citation(tmp_path):
    """The passage lookup used to win unconditionally, so a non-binding source
    with a position on it escalated as `authority_permits_choice` -- the very
    escalation that creates a position -- with the answer already in the record."""
    desk = _human_only_desk(tmp_path, position="not required to capitalize",
                            passage_text="somebody's reading of the standard")
    assert desk.passage("ASC 360-10") is not None, "fixture must have both"
    r = grade(Answer(position="not required to capitalize", citation="ASC 360-10"),
              desk.problems[0], desk)
    assert r.outcome is Outcome.CORRECT, (
        f"the firm had spoken and the desk refused anyway: {r.reason} {r.detail}")
