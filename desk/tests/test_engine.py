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
from engine import (Answer, EngineError, Outcome, REASONS, Refusal, grade, report,
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


#: The reasons that are about something OTHER than the authority, and what
#: resolves each. The set is meant to stay legible in exactly these groups: a
#: reason that fits none of them has been added without anyone deciding which
#: kind of problem it names, and it is the kind that decides who has to move.
NOT_ABOUT_AUTHORITY = {
    "facts_not_established": "ask the client",
    "document_not_requested": "obtain a document nobody requested",
}


def test_every_reason_is_legibly_about_authority_facts_or_a_document():
    """The gap, asserted so it cannot quietly reopen — and it has widened once.

    It read "every reason but one", because `facts_not_established` was the only
    entry about what the rule asks for rather than about the rule. On 5 September
    2026 the firm named a third kind: "there should be something telling us to
    get like loan statements and stuff to make sure we understand the deal."
    A document that exists and was never requested is not the same problem as a
    fact nobody knows — one is answered by asking a person, the other by
    obtaining a thing — and filing them together sends eight of forty-three real
    questions to the wrong queue.

    So the assertion is no longer "one exception". It is that every reason falls
    in a named group, and that adding one forces a decision about which.
    """
    assert set(NOT_ABOUT_AUTHORITY) <= set(REASONS), (
        "a named non-authority reason has been dropped from the engine; the "
        "desk in that position can only guess or blame the record")
    about_authority = set(REASONS) - set(NOT_ABOUT_AUTHORITY) - {"model_gave_up"}
    for r in about_authority:
        assert any(w in r for w in ("authority", "citation", "source", "position")), (
            f"{r!r} is about neither the authority nor anything named in "
            f"NOT_ABOUT_AUTHORITY. Say which kind of problem it is: the groups "
            f"decide who has to move, and a reason in none of them decides "
            f"nothing")


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


# ── #266: the declared mapping, which is exact and therefore blocks ──────────

def test_the_forge_answer_is_refused_by_serve_and_not_only_by_grade():
    """THE POINT OF #266, and the path with a client on the end of it.

    qwen3:8b answered four bank-reconciliation questions by citing
    § 1.446-1(a)(4) — accounting records — by explicit "extension". `grade()`
    caught all four on `passage.citation != problem.citation`, a check it can
    only make because it holds an answer key. `serve()` holds none and returned
    the accounting conclusion stamped `tier='primary'`, so the scoreboard
    reported `wrongly_absorbed = 0` while the shipping path let four through.
    """
    desk = record.load(DESKS / "cash-and-bank")
    p = next(q for q in desk.problems if q.id == "CB2")
    cited = next(x.citation for x in desk.passages
                 if x.citation.startswith("26 CFR 1.446-1(a)(4)"))

    out = serve(Answer(position=p.answer, citation=cited), desk,
                question=p.facts)
    assert isinstance(out, Refusal)
    assert out.reason == "citation_does_not_support"
    assert "S2" in out.detail and "S1" in out.detail, (
        "the refusal must name what the desk declared and what was cited, so "
        "the record says how to fix itself")

    right = serve(Answer(position=p.answer, citation=p.citation), desk,
                  question=p.facts)
    assert not isinstance(right, Refusal), "the correct citation must survive"
    assert right.checked_subject


def test_the_declared_mapping_refuses_nothing_that_is_right():
    """The cost, pinned. Word overlap refused 4 of the 16 fixed-assets problems
    answered with their OWN recorded citation (#266). A declared mapping refuses
    none, on either desk, because it compares a citation's SOURCE against what
    the firm said answers that subject rather than guessing from vocabulary."""
    for name in ("fixed-assets", "cash-and-bank"):
        desk = record.load(DESKS / name)
        refused = [p.id for p in desk.problems
                   if engine.cited_off_source(
                       Answer(position=p.answer, citation=p.citation),
                       desk, p.facts)[0]]
        assert refused == [], (
            f"{name}: {refused} answered with their own recorded citation and "
            f"were refused. Either the declaration is wrong or the gate is.")


def test_it_refuses_only_when_it_could_look():
    """"I could not check" and "I checked and it is fine" must never be the
    same answer. A question touching no declared subject gives the gate nothing
    to compare, so it passes — and `checked_subject` records that it did."""
    desk = record.load(DESKS / "cash-and-bank")
    p = desk.problems[0]
    cited = next(x.citation for x in desk.passages
                 if x.citation.startswith("26 CFR"))

    astray, _ = engine.cited_off_source(
        Answer(position=p.answer, citation=cited), desk, "what time is the train")
    assert not astray, "nothing was asked about, so nothing could be refused"

    out = serve(Answer(position=p.answer, citation=p.citation), desk,
                question="what time is the train")
    assert not isinstance(out, Refusal)
    assert not out.checked_subject, "it could not look, and must say so"


def test_a_mapping_to_a_source_that_does_not_exist_fails_the_load(tmp_path):
    """A subject answered from a source SOURCES.md never defines would refuse
    every citation for that subject, forever, and read as a strict desk."""
    d = tmp_path / "broken"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-05\n\n"
        "**Citation prefix:** 26 CFR\n\n**Why:** public domain.\n",
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05\n\n> a rule\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## broken · A desk\n\n**Answered from S9:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match=r"\['S9'\]"):
        record.load(d)


def test_the_subjects_are_the_mapping_and_not_a_second_list():
    """`fires_on` is the union of what each source answers. There is no separate
    list to forget to update, which is how two lists of the same thing drift."""
    for name in ("fixed-assets", "cash-and-bank"):
        desk = record.load(DESKS / name)
        declared = {t for terms in desk.answered_from.values() for t in terms}
        assert set(desk.fires_on) == declared
        assert len(desk.fires_on) == len(set(desk.fires_on)), "a subject twice"


def _overlapping_desk(tmp_path, *, prefixes, passage_citation, passage_source,
                      answers_from):
    """A desk written by hand so the gate's SOURCE RESOLUTION can be exercised.

    The two real desks cannot show this: their prefixes do not overlap and every
    stored citation starts with one, so a gate that re-infers the source from a
    prefix and a gate that uses the resolved one agree on every row.
    """
    d = tmp_path / "overlap"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text("".join(
        f"## {sid} · Source {sid}\n\n"
        f"**Tier:** primary · **Access:** public_fetch · "
        f"**May store:** full_text · **Checked:** 2026-09-05\n\n"
        f"**Citation prefix:** {pref}\n\n**Why:** public domain.\n\n"
        for sid, pref in prefixes), encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        f"## P1 · a widget question\n\n**Citation:** {passage_citation}\n\n"
        f"**Answer:** yes\n\n**Facts:** how do widgets work\n", encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        f"## {passage_citation}\n\n**Source:** {passage_source} · "
        f"**Checked:** 2026-09-05\n\n> a rule about widgets\n", encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        f"## overlap · A desk\n\n**Answered from {answers_from}:** widgets\n",
        encoding="utf-8")
    return record.load(d)


def test_the_gate_reads_the_resolved_source_not_the_first_matching_prefix(tmp_path):
    """S1's prefix is `G` and S2's is `G 1`, so `G 1.1` matches BOTH — and the
    first match is S1. Re-inferring the source from the citation named S1,
    refused an answer the desk is declared to give from S2, and did it on a
    passage whose `source_id` says S2 in the record. One fact, resolved twice,
    two answers."""
    desk = _overlapping_desk(
        tmp_path, prefixes=(("S1", "G"), ("S2", "G 1")),
        passage_citation="G 1.1", passage_source="S2", answers_from="S2")

    astray, why = engine.cited_off_source(
        Answer(position="yes", citation="G 1.1"), desk, "how do widgets work")
    assert not astray, f"a right answer from the declared source was refused: {why}"


def test_a_citation_matching_no_prefix_does_not_slip_past_the_gate(tmp_path):
    """The same defect wearing the other face, and the worse one. A stored
    passage carries its source by id, so its citation need not begin with any
    prefix — and prefix matching then named NO source, which the gate read as
    "I could not look" and passed. `serve()` stamps that `checked_subject=True`.
    A gate that opens when it cannot identify the source is worse than none."""
    desk = _overlapping_desk(
        tmp_path, prefixes=(("S1", "G"), ("S2", "H")),
        passage_citation="Z 9", passage_source="S1", answers_from="S2")

    astray, why = engine.cited_off_source(
        Answer(position="yes", citation="Z 9"), desk, "how do widgets work")
    assert astray, "S1 does not answer widgets; the citation came from S1"
    assert "S1" in why and "S2" in why


# `test_serve_still_cannot_tell_two_positions_from_one_source_apart` STOOD HERE
# and was deleted on 5 September 2026, on its own instructions. It pinned the
# half of Codex's #264 finding that the passage split did not close -- `serve()`
# returning the timing position for CB4's facts -- and said: "if this now
# refuses, the limit has been closed -- delete this test and say which change
# closed it." The per-citation narrowing closed it. Its replacement is
# `test_the_wrong_paragraph_of_the_right_source_is_refused` below, which asserts
# the refusal this one asserted the absence of.


def test_the_wrong_paragraph_of_the_right_source_is_refused():
    """THE HOLE THIS CLOSES, and it was pinned open in a test above until now.

    A source-level mapping cannot separate two rules living in one source, and
    the cash desk holds exactly that pair: the timing rule and the correction
    rule are both Publication 583, with opposite answers. Handed CB4's facts —
    a service charge nobody entered — together with the TIMING citation,
    `serve()` returned "a reconciling item, no entry in the books" and stamped
    it `checked_subject=True`. Right source, wrong paragraph, opposite treatment.
    """
    desk = record.load(DESKS / "cash-and-bank")
    cb4 = next(p for p in desk.problems if p.id == "CB4")
    timing = next(c for c in desk.answered_by if "did not yet include" in c)

    out = serve(Answer(position="a reconciling item, no entry in the books",
                       citation=timing), desk, question=cb4.facts)
    assert isinstance(out, Refusal)
    assert out.reason == "citation_does_not_support"
    assert "what the books are updated for" in out.detail, (
        "the refusal must name the paragraph that DOES answer it, or the record "
        "does not say how to fix itself")

    right = serve(Answer(position=cb4.answer, citation=cb4.citation), desk,
                  question=cb4.facts)
    assert not isinstance(right, Refusal), "the correct citation must survive"


def test_the_narrowing_costs_nothing_on_any_desk():
    """WHAT "BUILD AND MEASURE IT" MEANT. The shape this extends was chosen on a
    measurement — word overlap refused 4 of 16 right answers on `fixed-assets`
    and was rejected for it — so this one earns its place the same way: every
    problem on every desk, answered with its OWN recorded citation and its OWN
    recorded answer, and the gate must refuse none of them.

    98 problems, 0 refused, 5 September 2026.
    """
    refused = []
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        refused += [f"{d.name}/{p.id}" for p in desk.problems
                    if engine.cited_off_source(
                        Answer(position=p.answer, citation=p.citation),
                        desk, p.facts)[0]]
    assert refused == [], (
        f"{refused} answered with their own recorded citation and were refused. "
        f"Either the narrowing is wrong or the declaration is.")


def test_a_desk_that_declares_no_narrowing_is_unaffected():
    """The property that makes this safe to add at all: it only ever removes.
    A desk declaring none of these lines behaves exactly as it did, so the cost
    can only be paid by a desk that opted in."""
    plain = [d.name for d in sorted(DESKS.iterdir())
             if (d / "SOURCES.md").is_file() and not record.load(d).answered_by]
    assert plain, "no desk left to prove it on"
    assert "cash-and-bank" not in plain, "the desk that opted in must be excluded"


def test_a_narrowing_may_not_introduce_a_subject(tmp_path):
    """It NARROWS what a source already answers. A term appearing only on a
    per-citation line would widen `fires_on` through a back door — and the union
    of the source lines is `fires_on` precisely so there is no second list."""
    d = tmp_path / "widen"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-05\n\n"
        "**Citation prefix:** 26 CFR\n\n**Why:** public domain.\n",
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05\n\n> a rule\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## widen · A desk\n\n**Answered from S1:** widgets\n\n"
        "**Answered by `26 CFR 1`:** widgets, sprockets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="cannot introduce a subject"):
        record.load(d)


def test_a_narrowing_to_a_citation_the_desk_lacks_fails_the_load(tmp_path):
    """It would refuse every answer for those subjects, forever, and read as a
    strict desk — the same failure the source-level check was given."""
    d = tmp_path / "ghost"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-05\n\n"
        "**Citation prefix:** 26 CFR\n\n**Why:** public domain.\n",
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05\n\n> a rule\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## ghost · A desk\n\n**Answered from S1:** widgets\n\n"
        "**Answered by `26 CFR 999`:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="holds no passage or position"):
        record.load(d)
