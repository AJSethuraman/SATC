"""The engine: what it refuses, what it catches, and what it lets through.

The outcome that matters is `wrongly_absorbed` — an answer that was wrong, that
the engine could not fault, and that would therefore have reached a client with
nobody the wiser. Every other outcome costs a little time. That one costs the
reason to trust all the others, so it is tested hardest and reported first.
"""
from __future__ import annotations

import socket

import pytest

import engine
import record
from conftest import DESKS, NetworkUsed
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
                          citation="ASC 360-10"), desk, question="a question")
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


# ── who escalated, which is the only thing the escalation column can mean ────

def _secondary_desk(tmp_path):
    """A desk whose one source is interpretive, so the engine escalates.

    Built here rather than reused, because every other desk in this suite rests
    on binding authority and the whole point of this case is that it does not.
    """
    d = tmp_path / "interp"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · Somebody's reading of the rule\n\n"
        "**Tier:** secondary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-05\n\n"
        "**Citation prefix:** GUIDE\n\n"
        "**Why:** a work of the United States Government, public domain.\n",
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** GUIDE 1\n\n"
        "**Answer:** treat it as a reconciling item\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## GUIDE 1\n\n**Source:** S1 · **Checked:** 2026-09-05\n\n"
        "> the guide's reading\n\n"
        "## GUIDE 2\n\n**Source:** S1 · **Checked:** 2026-09-05\n\n"
        "> another paragraph\n",
        encoding="utf-8")
    return record.load(d)


def test_a_confident_answer_on_interpretive_authority_is_escalated_by_the_engine(tmp_path):
    """It reached the right conclusion and cited real authority. The engine
    escalated it anyway, because a secondary source is somebody's reading and
    the choice belongs to the firm — the desk did not decline, it was stopped."""
    desk = _secondary_desk(tmp_path)
    p = desk.problems[0]
    r = engine.grade(Answer(position=p.answer, citation=p.citation), p, desk)
    assert r.outcome is engine.Outcome.ESCALATED
    assert r.escalated_by == engine.ENGINE
    assert r.reason == "authority_permits_choice"


def test_a_desk_that_declines_is_recorded_as_the_one_that_declined(tmp_path):
    """The same cell, the opposite meaning. Without this distinction a desk
    built to exercise escalation measures its own record's tiers rather than
    whether the brain knew it did not know."""
    desk = _secondary_desk(tmp_path)
    p = desk.problems[0]
    r = engine.grade(Answer(position="", escalated=True,
                            reason="authority_permits_choice"), p, desk)
    assert r.outcome is engine.Outcome.ESCALATED
    assert r.escalated_by == engine.DESK


def test_the_two_escalations_are_distinguishable_at_all(tmp_path):
    """The assertion the two tests above exist to make jointly: same outcome,
    same reason, and still tellable apart."""
    desk = _secondary_desk(tmp_path)
    p = desk.problems[0]
    stopped = engine.grade(Answer(position=p.answer, citation=p.citation), p, desk)
    declined = engine.grade(Answer(position="", escalated=True,
                                   reason="authority_permits_choice"), p, desk)
    assert stopped.outcome is declined.outcome
    assert stopped.reason == declined.reason
    assert stopped.escalated_by != declined.escalated_by


def test_nothing_but_an_escalation_records_who_escalated(fixed_assets, problem):
    """An empty label on a correct answer must not read as "the engine did it"."""
    r = engine.grade(Answer(position=problem.answer, citation=problem.citation),
                     problem, fixed_assets)
    assert r.outcome is engine.Outcome.CORRECT
    assert r.escalated_by == ""


# ── the reason set had nothing for a missing FACT ────────────────────────────

def test_a_desk_can_say_the_rule_is_clear_and_the_facts_are_not(fixed_assets, problem):
    """The firm, 5 September 2026, on an agent that called a client's J.Crew
    purchases personal: "no matter what, its answer was wrong."

    The lookup was not the error — knowing J.Crew sells clothing is real evidence
    about WHAT WAS BOUGHT. The error was going from "sells clothing" to "personal
    expense" without reaching the test, which asks whether an item is "especially
    required by his profession and does not merely take the place of articles
    required in civilian life" and contains no vendor test at all.

    What the firm does instead: "i could even flag it to ask the client." That
    outcome was inexpressible — every other reason in the set is about the
    authority, and none about the facts the authority asks for.
    """
    r = grade(Answer(position="", escalated=True,
                     reason="facts_not_established",
                     working="the rule is 1.262-1(b)(8); ask what was bought"),
              problem, fixed_assets)
    assert r.outcome is Outcome.ESCALATED
    assert r.reason == "facts_not_established"
    assert r.escalated_by == "desk", "the desk declined; the engine did not stop it"


def test_every_reason_but_one_is_about_authority_rather_than_facts():
    """The gap, asserted so it cannot quietly reopen.

    `facts_not_established` is the only reason in the set that is about what the
    rule asks for rather than about the rule. If it is removed, or if the set
    grows another facts-shaped reason without anyone noticing, this says so.
    """
    about_facts = {"facts_not_established"}
    assert about_facts <= set(REASONS), (
        "the set has nothing for a rule that is clear and a fact that is missing; "
        "a desk in that position can only guess or blame the record")
    about_authority = set(REASONS) - about_facts - {"model_gave_up"}
    assert all(
        w in r for r in about_authority
        for w in ("authority", "citation", "source", "position")
        if w in r), "unreachable; the loop below is the real assertion"
    for r in about_authority:
        assert any(w in r for w in ("authority", "citation", "source", "position")), (
            f"{r!r} is neither about the authority nor named as being about the "
            f"facts; the set's two halves have to stay legible")


def test_a_reason_outside_the_closed_set_is_still_refused(fixed_assets, problem):
    """The control. Adding one reason must not have opened the set."""
    with pytest.raises(EngineError, match="not one of"):
        grade(Answer(position="", escalated=True, reason="ask_the_client"),
              problem, fixed_assets)


# ── #266: serve() could not judge a citation because it never saw the question ─

def test_serving_requires_the_question(fixed_assets, problem):
    """The signature change IS the fix.

    Without the question this function could verify that the cited authority
    exists and binds, and nothing whatever about whether it had anything to do
    with what was asked. On 5 September 2026 it served four bank-reconciliation
    answers citing a rule about accounting records, stamped `tier='primary'`.
    `grade()` caught them only because it holds an answer key; there is no key
    here and never will be, so the question is what stands in for one.
    """
    with pytest.raises(TypeError, match="question"):
        serve(Answer(position=problem.answer, citation=problem.citation),
              fixed_assets)


def test_a_served_answer_says_whether_its_subject_could_be_checked():
    """"I could not look" and "I looked and it is fine" were the same answer.

    `tier='primary'` was the whole story a caller got, and it reads as *this is
    solid* when all that was verified is that the authority exists and binds.
    """
    desk = record.load(DESKS / "cash-and-bank")
    p = desk.problems[0]

    on = serve(Answer(position=p.answer, citation=p.citation), desk,
               question=p.facts)
    assert on.checked_subject, "the question touches this desk's subjects"

    off = serve(Answer(position=p.answer, citation=p.citation), desk,
                question="what time is the train")
    assert not off.checked_subject, (
        "nothing in that question touches a subject, so nothing could be "
        "compared — and that must not read as a clean check")


def test_most_fixed_assets_problems_touch_none_of_the_desks_own_subjects():
    """THE THIRD REASON WORD OVERLAP CANNOT DO THIS JOB, and a finding in its
    own right.

    Nine of the sixteen fixed-assets problems mention not one of that desk's
    twenty-four declared subjects. So the subject gate could only ever judge
    seven of them — and it got four of those seven wrong.

    The cause is that `fires_on` describes how a QUESTION arrives ("should I
    capitalize this?") while the problems are the regulation's own worked
    examples, phrased as fact patterns ("A owns a building..."). Two different
    registers, and nobody had compared them.

    It also means routing would not reach this desk for nine of its own
    problems. Whether that matters depends on whether a person's question reads
    like a regulation example — but it is a fact about the record that was
    unmeasured until #266 forced the question.
    """
    touches = engine._canon_touches()
    desk = record.load(DESKS / "fixed-assets")
    silent = [p.id for p in desk.problems
              if not any(touches(p.facts, s) for s in desk.fires_on)]
    assert silent == ["P3", "P6", "P7", "P8", "P9", "P10", "P12", "P13", "P14"], (
        f"the set moved to {silent}; re-measure before trusting any check that "
        f"compares a question to this desk's subjects")

    cash = record.load(DESKS / "cash-and-bank")
    assert not [p.id for p in cash.problems
                if not any(touches(p.facts, s) for s in cash.fires_on)], (
        "every cash problem touches a subject — its facts were composed, and "
        "that is exactly why it cannot stand in for the measurement above")


def test_the_forge_answer_is_what_off_subject_catches(fixed_assets):
    """The regression fixture is a real answer a real model produced.

    qwen3:8b, cash desk, 5 September 2026: four bank-reconciliation questions
    answered by citing § 1.446-1(a)(4) — accounting records — by explicit
    "extension". Real, resolvable, primary, and served.
    """
    desk = record.load(DESKS / "cash-and-bank")
    p = next(q for q in desk.problems if q.id == "CB2")
    cited = next(x.citation for x in desk.passages
                 if x.citation.startswith("26 CFR 1.446-1(a)(4)"))

    astray, why = engine.off_subject(
        Answer(position=p.answer, citation=cited), desk, p.facts)
    assert astray and "shares no subject" in why

    right, _ = engine.off_subject(
        Answer(position=p.answer, citation=p.citation), desk, p.facts)
    assert not right, "the correct citation must survive it"


def test_off_subject_is_measured_and_the_cost_is_pinned_here():
    """WHY IT IS NOT WIRED INTO `_check`, as a number rather than an opinion.

    Blocking on it would refuse a quarter of the fixed-assets problems answered
    with their OWN recorded citation — P4 and P5 (the question says only "unit
    of property"; § 1.263(a)-3(j) does not use the phrase) and P15 and P16 (the
    question triggers only `263` and `263(a)`, which are routing hooks for a
    section number, not subjects any authority text repeats).

    Comparing against the DESK's subjects instead of the QUESTION's drops that
    to zero and stops catching the Forge answer, which mentions "cash". Word
    overlap over-refuses or under-catches; neither is exact enough to block on,
    and `guards.py` draws the line exactly there.

    This test exists so the cost cannot be forgotten and the gate cannot be
    switched on without someone watching this number move.
    """
    desk = record.load(DESKS / "fixed-assets")
    refused = [p.id for p in desk.problems
               if engine.off_subject(
                   Answer(position=p.answer, citation=p.citation),
                   desk, p.facts)[0]]
    assert refused == ["P4", "P5", "P15", "P16"], (
        f"the measured false-refusal set moved to {refused}. That is a finding "
        f"either way: the gate got better, or the record changed under it. "
        f"Re-measure before wiring it in."
    )
    assert not any(
        engine.off_subject(Answer(position=p.answer, citation=p.citation),
                           desk, p.facts)[0]
        for p in record.load(DESKS / "cash-and-bank").problems
    ), "no cash-desk problem is falsely refused; the cost is on fixed-assets"
