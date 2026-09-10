"""The engine: what it refuses, what it catches, and what it lets through.

The outcome that matters is `wrongly_absorbed` — an answer that was wrong, that
the engine could not fault, and that would therefore have reached a client with
nobody the wiser. Every other outcome costs a little time. That one costs the
reason to trust all the others, so it is tested hardest and reported first.
"""
from __future__ import annotations

import re
import socket

import pytest

import engine
import record
from conftest import CORPUS, NetworkUsed
from engine import (Answer, EngineError, Outcome, REASONS, Refusal, Served, grade, report,
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
    """A Big 4 guide's reading must never be handed over in a regulation's voice.

    THE CLAIM IS UNCHANGED AND THE MECHANISM IS NOT, since 6 September 2026.
    The firm answered "Serve it, marked" on the fourth docket, so where no rule
    reaches — and this desk holds no binding source at all — the guide's reading
    is served with `binding=False` and a caveat naming it as the Service's
    stated position rather than settled law. Refusing it protected nobody: it
    sent the same question back to the firm every time it was asked, which is
    what they asked to stop.

    What may never happen is the guide being served in a REGULATION's voice, and
    that is now asserted directly rather than implied by a refusal.
    """
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
        "## GUIDE 1\n\n**Source:** S1 · **Checked:** 2026-09-04 · **Kind:** rule\n\n> a reading\n",
        encoding="utf-8")
    desk = record.load(d)
    r = grade(Answer(position="must capitalize", citation="GUIDE 1"),
              desk.problems[0], desk)
    assert r.outcome is Outcome.CORRECT

    out = serve(Answer(position="must capitalize", citation="GUIDE 1"), desk,
                question="f")
    assert isinstance(out, Served)
    # THE VOICE IS THE ASSERTION. It is served, and it is not served as a rule.
    assert out.binding is False
    assert "not the rule" in out.caveat


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
            "## ASC 360-10\n\n**Source:** S1 · **Checked:** 2026-09-04 · **Kind:** rule\n\n"
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
        "## GUIDE 1\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n"
        "> the guide's reading\n\n"
        "## GUIDE 2\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n"
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
    # IT IS GRADED NOW, WHICH IS THE POINT. A problem that could only ever
    # escalate was a problem no brain was ever tested on, and an escalation
    # reads as a success on this scoreboard.
    assert r.outcome is engine.Outcome.CORRECT

    out = engine.serve(Answer(position=p.answer, citation=p.citation), desk,
                       question=p.facts)
    assert isinstance(out, engine.Served)
    assert out.binding is False, "a secondary source served as though it settled it"
    assert "not the rule" in out.caveat and out.tier in out.caveat


def _mixed_desk(tmp_path):
    """A desk holding BOTH a rule and a publication about it, declared.

    This is the shape the guidance fallback must not open: the regulation says
    one thing, the plain-English page says another, and a model that finds the
    page easier to read must not be allowed to answer from it. The record has a
    live example — § 1.263(a)-1 says $500, the IRS tangible-property page says
    $2,500, and the tie-out confirmed both on 6 September 2026.
    """
    d = tmp_path / "mixed"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · The regulation\n\n"
        "**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-06\n\n"
        "**Citation prefix:** REG\n\n**Why:** public domain.\n\n---\n\n"
        "## S2 · The plain-English page about it\n\n"
        "**Tier:** secondary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-06\n\n"
        "**Citation prefix:** PAGE\n\n**Why:** public domain.\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## mixed · a desk with a rule and a summary of it\n\n"
        "**Answered from S1:** threshold\n\n"
        "**Answered from S2:** threshold\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** PAGE 1\n\n**Answer:** $2,500\n\n"
        "**Facts:** what is the threshold?\n", encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## REG 1\n\n**Source:** S1 · **Checked:** 2026-09-06 · **Kind:** rule\n\n> $500\n\n"
        "## PAGE 1\n\n**Source:** S2 · **Checked:** 2026-09-06 · **Kind:** rule\n\n> $2,500\n",
        encoding="utf-8")
    return record.load(d)


def test_guidance_may_not_be_served_where_the_desk_holds_the_rule(tmp_path):
    """The condition the whole fallback rests on, on the shape that motivates it.

    Without it, "serve guidance where no rule reaches" becomes "serve guidance",
    and a model dodges a regulation by citing the summary of it. The refusal
    names what it is: the desk holds binding authority for what was asked."""
    desk = _mixed_desk(tmp_path)
    out = engine.serve(Answer(position="$2,500", citation="PAGE 1"), desk,
                       question="what is the threshold?")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_permits_choice"
    assert "holds binding authority" in out.detail
    # AND THE RULE ITSELF STILL SERVES, so this is a narrowing and not a wall.
    ok = engine.serve(Answer(position="$500", citation="REG 1"), desk,
                      question="what is the threshold?")
    assert isinstance(ok, engine.Served) and ok.binding is True


def test_a_desk_that_cannot_tell_whether_a_rule_reaches_refuses(tmp_path):
    """The middle case, and it fails toward the firm rather than toward an
    answer. A desk holding binding sources but declaring no mapping cannot say
    whether a rule reaches this question — and "I could not check" must never
    read the same as "I checked and it is fine"."""
    d = tmp_path / "unmapped"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · The regulation\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-06\n\n"
        "**Citation prefix:** REG\n\n**Why:** public domain.\n\n---\n\n"
        "## S2 · A page\n\n**Tier:** secondary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-06\n\n"
        "**Citation prefix:** PAGE\n\n**Why:** public domain.\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** PAGE 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## REG 1\n\n**Source:** S1 · **Checked:** 2026-09-06 · **Kind:** rule\n\n> rule\n\n"
        "## PAGE 1\n\n**Source:** S2 · **Checked:** 2026-09-06 · **Kind:** rule\n\n> reading\n",
        encoding="utf-8")
    out = engine.serve(Answer(position="a", citation="PAGE 1"), record.load(d),
                       question="f")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_permits_choice"


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
    # ON A DESK THAT STILL REFUSES. `_secondary_desk` holds no rule at all, so
    # since 6 September 2026 the engine serves it marked rather than stopping
    # it — and the distinction this test is about only exists where it stops.
    desk = _mixed_desk(tmp_path)
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


#: A FOURTH KIND, added 8 September 2026 with `not_judged` (#346), and it is a
#: different question from every group below: those name what is MISSING and who
#: has to go and get it — a client, a document, our own engagement file. This
#: names something the CALLER did not do. Nothing is missing from the record,
#: nothing is missing from the file, and the desk's answer is complete; a second
#: reader was required by that desk's own declaration and none was supplied.
#:
#: It is separated rather than folded in because the groups exist to decide who
#: has to move, and here it is neither the client, nor the preparer, nor the
#: firm — it is whoever wired the caller. And it is the one refusal `ask.answer`
#: does not file in `unsupported/`, for the same reason: that queue says the
#: record is missing something, and the record is complete.
CALLER_CONTRACT = {
    "not_judged": "supply a second reader's judgment, from a party other than "
                  "the one that answered",
}

#: The reasons that are about something OTHER than the authority, and what
#: resolves each. The set is meant to stay legible in exactly these groups: a
#: reason that fits none of them has been added without anyone deciding which
#: kind of problem it names, and it is the kind that decides who has to move.
NOT_ABOUT_AUTHORITY = {
    "facts_not_established": "ask the client",
    "document_not_requested": "obtain a document nobody requested",
    # The third of the same family, and it is resolved by NEITHER of the above:
    # the fact should already be in our own engagement record, so the answer is
    # to look there and, when it is not there, to notice that the intake missed
    # it. The firm, 5 September 2026: "if they're missing that piece of
    # information, something was just missing from the file."
    "context_not_on_file": "read our own file, and fix the intake that skipped it",
    # The fourth and fifth, asked for by the firm on 6 September 2026. Both are
    # about the FILE rather than the authority, and they are separated because
    # a different person fixes each.
    "client_rule_governs": "read the rule the firm already recorded for this client",
    # AND THIS ONE IS NOT FIXED BY READING ANYTHING. There is nowhere to read.
    # The firm: "if the follow up has no answer we know there's a legit hole to
    # fix because the accountant or firm never assigned it up front ... What if
    # this mattered only sometimes and we never even made a field for it."
    "no_field_for_this_fact": "decide, as a firm, whether this fact is recorded at all",
    # AND THE SIXTH IS ABOUT THE SECOND READING, NOT ABOUT THE RECORD. A judge
    # handed the paragraph and the conclusion quoted words the paragraph does
    # not contain, so the judgment is void -- which says nothing at all about
    # whether the authority is any good. Filing it as an authority problem would
    # put a defect in the reading into the queue that reads out what the RECORD
    # is missing, and that queue is how the firm decides what to go and find.
    "judgment_not_in_the_passage": "re-judge, quoting the passage that is there",
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
    assert set(CALLER_CONTRACT) <= set(REASONS), (
        "a named caller-contract reason has been dropped from the engine")
    assert not (set(CALLER_CONTRACT) & set(NOT_ABOUT_AUTHORITY)), (
        "a reason cannot be in two groups; the groups decide who has to move")
    assert set(NOT_ABOUT_AUTHORITY) <= set(REASONS), (
        "a named non-authority reason has been dropped from the engine; the "
        "desk in that position can only guess or blame the record")
    about_authority = (set(REASONS) - set(NOT_ABOUT_AUTHORITY)
                       - set(CALLER_CONTRACT) - {"model_gave_up"})
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
    desk = record.load(CORPUS)
    p = desk.problems[0]

    on = serve(Answer(position=p.answer, citation=p.citation), desk,
               question=p.facts)
    assert on.checked_subject, "the question touches this desk's subjects"

    off = serve(Answer(position=p.answer, citation=p.citation), desk,
                question="what time is the train")
    assert not off.checked_subject, (
        "nothing in that question touches a subject, so nothing could be "
        "compared — and that must not read as a clean check")


def test_no_desks_problems_are_invisible_to_its_own_subjects():
    """THIS TEST USED TO PIN NINE, and closing that is what it was for.

    It read `test_most_fixed_assets_problems_touch_none_of_the_desks_own_subjects`
    and asserted the exact nine — because nine of `fixed-assets`' sixteen
    problems mentioned not one of its twenty-four declared subjects, so the
    subject gate could judge only seven of them and got four of those wrong.

    The cause, once looked at: the subjects were the REGULATION'S vocabulary and
    the problems are the SITUATION'S. It declared `betterment`, `restoration`,
    `adaptation`, `unit of property` — the words § 1.263(a)-3 uses to name its
    tests — and none of the words it uses to name the things the tests are about.
    `building` appears 117 times in the authority that desk holds and was not a
    subject of it.

    Fixed 5 September 2026 by declaring what the authority itself names, measured
    both ways: nine blind became zero, and the candidates pulled in nothing from
    any other desk once `plumbing` was dropped — every problem it reached was
    about a plumbing COMPANY rather than a plumbing SYSTEM.

    So the assertion is now the general one, across every desk. A problem its own
    desk's subjects cannot see is a row `serve()` reports `checked_subject=False`
    on: the gate that exists to catch a wrong citation never runs for it.
    """
    touches = engine._canon_touches()
    blind = {}
    for d in [CORPUS]:
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        silent = [p.id for p in desk.problems
                  if not any(touches(p.facts, s) for s in desk.fires_on)]
        if silent:
            blind[d.name] = silent
    assert blind == {}, (
        f"{blind} touch none of their own desk's subjects. `serve()` cannot "
        f"check the subject on those rows and says so — declare what the "
        f"authority itself names, and measure what the new subjects pull in "
        f"from other desks before keeping them.")


def test_the_forge_answer_is_what_off_subject_catches(fixed_assets):
    """The regression fixture is a real answer a real model produced.

    qwen3:8b, cash desk, 5 September 2026: four bank-reconciliation questions
    answered by citing § 1.446-1(a)(4) — accounting records — by explicit
    "extension". Real, resolvable, primary, and served.
    """
    desk = record.load(CORPUS)
    p = next(q for q in desk.problems if q.id == "CB2")
    cited = next(x.citation for x in desk.passages
                 if x.citation.startswith("26 CFR 1.446-1(a)(4)"))

    astray, why = engine.off_subject(
        Answer(position=p.answer, citation=cited), desk, p.facts)
    assert astray and "shares no subject" in why

    right, _ = engine.off_subject(
        Answer(position=p.answer, citation=p.citation), desk, p.facts)
    assert not right, "the correct citation must survive it"


#: THE FALSE REFUSALS THIS GATE WOULD PRODUCE IF ANYBODY WIRED IT IN.
#:
#: MEASURED 5 SEPTEMBER 2026 on `fixed-assets` alone: 12 of that desk's 16
#: problems. RE-MEASURED 10 SEPTEMBER 2026 over the ONE CORPUS: **36 of 98**,
#: and the denominator changed with the record, so the two rates are what
#: compare — 75% then, 37% now.
#:
#: THE RATE FELL AND THE GATE DID NOT IMPROVE. Word overlap refuses when the
#: citation's text shares none of the question's declared subjects. One corpus
#: means every question is measured against the union of seven vocabularies, so
#: more questions touch SOMETHING and fewer are refused outright — the gate is
#: being handed a bigger dictionary, not better judgement. Whole desks are still
#: refused entire: every vehicle problem but four, seven of eight meals ones.
#:
#: Kept public, tested and unused, with the cost pinned, so nobody wires it in
#: without watching this list.
OFF_SUBJECT = [
    "CD8", "TP3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P12", "P13",
    "P14", "P15", "P16", "M2", "M3", "M6", "M7", "M8", "M11", "M13", "PB1",
    "PB6", "IR4", "IR5", "VE1", "VE2", "VE3", "VE4", "VE5", "VE6", "VE7",
    "VE8", "VE9", "VE10", "VE11",
]


def test_off_subject_is_measured_and_the_cost_is_pinned_here():
    """WHY IT IS NOT WIRED INTO `_check`, as a number rather than an opinion —
    AND THE NUMBER GOT WORSE WHEN THE RECORD GOT BETTER, which is the strongest
    thing anyone has said against this gate.

    It was 4 of 16: P4 and P5 (the question says only "unit of property", which
    § 1.263(a)-3(j) does not use) and P15 and P16 (only `263` and `263(a)` fire,
    and those are routing hooks for a section number, not subjects any authority
    text repeats). Nine other problems could not be judged at all, because they
    touched none of that desk's subjects — the gate simply passed on them.

    On 5 September 2026 those nine were fixed, by declaring the words the
    regulation itself uses for the things it governs (`building` appears 117
    times in the stored authority and was not a subject). The nine became
    judgeable, and word overlap got **all nine of them wrong**:

        before the subjects were fixed     4 of 16 refused
        after                             12 of 16 refused

    So it is not merely imprecise. **It degrades as the record improves** — every
    subject added correctly gives it another right answer to refuse. A gate whose
    cost rises when the thing it guards gets better is one that measures
    vocabulary rather than meaning, and `guards.py` draws the line exactly there.

    Kept public, tested and unused, with the cost pinned, so nobody wires it in
    without watching this number.
    """
    desk = record.load(CORPUS)
    refused = [p.id for p in desk.problems
               if engine.off_subject(
                   Answer(position=p.answer, citation=p.citation),
                   desk, p.facts)[0]]
    assert refused == OFF_SUBJECT, (
        f"the measured false-refusal set moved to {refused}. That is a finding "
        f"either way: the gate got better, or the record changed under it. "
        f"Re-measure before wiring it in."
    )
    # AND IT IS NOT UNIFORM, which is the half that says it measures vocabulary
    # rather than meaning. Every one of the eight bank-reconciliation problems
    # passes — their questions say `bank` and the paragraph says `bank` — while
    # eleven of the fifteen vehicle ones are refused on their own citation.
    assert not [p.id for p in desk.problems if p.id.startswith("CB")
                and engine.off_subject(
                    Answer(position=p.answer, citation=p.citation),
                    desk, p.facts)[0]], (
        "the bank problems were the class this gate got right; if they are "
        "refused now the measurement above is describing something else")


# ── #266: the declared mapping, which is exact and therefore blocks ──────────

def test_the_forge_answer_is_now_served_with_the_warning_and_the_judge_is_the_gate():
    """#266 REVERSED ON THE SOURCE-LEVEL HALF, 8 September 2026. Read this.

    WHAT IT USED TO ASSERT. qwen3:8b answered four bank-reconciliation questions
    by citing § 1.446-1(a)(4) — accounting records — by explicit "extension".
    `grade()` caught all four on the answer key; `serve()` holds none and let
    them out stamped `tier='primary'`. So the declared source map was allowed to
    BLOCK, and this test pinned that.

    WHY IT NO LONGER DOES, and the firm decided it:

        "it is difficult to have multiple desks that are so silo'd when we can
         have an agent tie things out and provide suggestions"
        "We currently do not need to test against ollama. Stop trying to. This
         can be a Claude code only thing ... Ollama is end game"

    Two supports were removed at once. The block's own justification was that
    `serve()` "had no key and no equivalent of `grade()`'s citation check" —
    #346 built the judge, a second reader on the paragraph and the conclusion,
    on every answer. And every measurement behind it is `qwen3:8b`, which is not
    a model this repository targets any more.

    WHAT IT COST, over all 98 recorded problems, asked whether it would refuse
    each desk's OWN recorded citation:

        phrased as the full fact pattern (~50 words)    0 of 98
        phrased as its title (~8 words)                10 of 98

    All ten are this source-level check; the per-citation narrowing costs zero
    in both. It measures how many declared keywords the asker typed. And
    `PROBLEMS.md` is written in the verbose style, which is the style that
    scores zero — so the suite could never see it. Confirmed live the same day:
    "How is the depreciation worked out?" refused § 1.263(a)-2(d)(1), the
    acquisition rule, on a thing that had been bought.

    WHAT STANDS BEHIND THE ANSWER NOW, AND WHAT IS NOT PROVEN HERE. The judge.
    This suite CANNOT run it — it needs a model call, and that is the point of
    Forge-Desk. **So this test asserts the warning is carried, and it does NOT
    assert that anything catches the qwen3 answer.** If the judge turns out not
    to refuse it, that is a real regression and this docstring is where to
    start. The per-citation half still blocks, and
    `test_the_wrong_paragraph_of_the_right_source_is_refused` proves it.
    """
    desk = record.load(CORPUS)
    p = next(q for q in desk.problems if q.id == "CB2")
    cited = next(x.citation for x in desk.passages
                 if x.citation.startswith("26 CFR 1.446-1(a)(4)"))

    out = serve(Answer(position=p.answer, citation=cited), desk,
                question=p.facts)
    assert not isinstance(out, Refusal), (
        "the source-level map advises now; only the per-citation narrowing "
        "still refuses")
    assert out.off_source, "served with the doubt dropped entirely"
    # S5 AND S4, WHICH WERE S2 AND S1 UNTIL 10 SEPTEMBER 2026. `dec-kill`
    # merged seven records that each numbered their own sources from S1, so
    # every id moved; the SOURCES they name did not. S5 is Publication 583,
    # which the record declares for `bank`; S4 is § 1.446-1, which it does not.
    assert "S5" in out.off_source and "S4" in out.off_source, (
        "the warning must name what the desk declared and what was cited, so "
        "the record still says how to fix itself")
    assert str(out).index(out.off_source) < str(out).index(out.position), (
        "the warning must be read before the conclusion, not after it")

    right = serve(Answer(position=p.answer, citation=p.citation), desk,
                  question=p.facts)
    assert not isinstance(right, Refusal), "the correct citation must survive"
    assert not right.off_source, "a declared citation carries no warning"
    assert right.checked_subject


def test_the_declared_mapping_refuses_nothing_that_is_right():
    """The cost, pinned. Word overlap refused 4 of the 16 fixed-assets problems
    answered with their OWN recorded citation (#266). A declared mapping refuses
    none, on either desk, because it compares a citation's SOURCE against what
    the firm said answers that subject rather than guessing from vocabulary."""
    desk = record.load(CORPUS)
    refused = [p.id for p in desk.problems
               if engine.cited_off_source(
                   Answer(position=p.answer, citation=p.citation),
                   desk, p.facts)[0]]
    assert refused == [], (
        f"{refused} answered with their own recorded citation and were "
        f"refused. Either the declaration is wrong or the gate is.")


def test_it_refuses_only_when_it_could_look():
    """"I could not check" and "I checked and it is fine" must never be the
    same answer. A question touching no declared subject gives the gate nothing
    to compare, so it passes — and `checked_subject` records that it did."""
    desk = record.load(CORPUS)
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
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n> a rule\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## broken · A desk\n\n**Answered from S9:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match=r"\['S9'\]"):
        record.load(d)


def test_the_subjects_are_the_mapping_and_not_a_second_list():
    """`fires_on` is the union of what each source answers. There is no separate
    list to forget to update, which is how two lists of the same thing drift."""
    desk = record.load(CORPUS)
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
        f"**Checked:** 2026-09-05 · **Kind:** rule\n\n> a rule about widgets\n",
        encoding="utf-8")
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
    desk = record.load(CORPUS)
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
    for d in [CORPUS]:
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


def test_a_record_that_declares_no_narrowing_is_unaffected(tmp_path):
    """The property that makes this safe to add at all: it only ever removes.
    A record declaring none of these lines behaves exactly as it did, so the
    cost can only be paid by one that opted in.

    IT USED TO PICK A DESK THAT HAPPENED NOT TO HAVE OPTED IN, and `dec-kill`
    took that away: there is one record now and it declares two narrowings, so
    there is no un-narrowed one left on disk to point at. A property proved on
    whichever desk happened to satisfy it was always the weaker version — it
    goes green the day the last such desk opts in, having checked nothing. So
    the case is CONSTRUCTED: the real corpus with its `Answered by` lines
    removed, and every problem must serve exactly as it does with them.
    """
    import shutil

    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    f = dst / "SUBJECTS.md"
    text = f.read_text(encoding="utf-8")
    assert "**Answered by " in text, "the fixture's premise moved"
    f.write_text(re.sub(r"^\*\*Answered by .*?(?=\n\n|\n\*\*|\Z)", "", text,
                        flags=re.M | re.S), encoding="utf-8")

    narrowed, plain = record.load(CORPUS), record.load(dst)
    assert narrowed.answered_by and not plain.answered_by, (
        "the fixture did not actually opt out")

    for p in narrowed.problems:
        a = Answer(position=p.answer, citation=p.citation)
        assert (engine.cited_off_source(a, plain, p.facts)[0]
                == engine.cited_off_source(a, narrowed, p.facts)[0]), (
            f"{p.id} is judged differently with the narrowing removed, and the "
            f"narrowing may only ever REMOVE a citation from a subject it was "
            f"already declared for")


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
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n> a rule\n",
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
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n> a rule\n",
        encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## ghost · A desk\n\n**Answered from S1:** widgets\n\n"
        "**Answered by `26 CFR 999`:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="holds no passage or position"):
        record.load(d)
