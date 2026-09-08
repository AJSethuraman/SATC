"""An escalation a person can resolve must say what to ask them.

THE FIRM, 8 SEPTEMBER 2026, reading a refusal with no question in it:

    "why does it need client context though - i thought we are making it ask
     follow up questions for appropriate context?"

They were right, and the reason list had said so since it was written:
`facts_not_established` carries the annotation *"the rule is clear; what was
bought is not. ASK."*

WHAT WAS ACTUALLY WIRED. `Refusal.ask` existed from 5 September and was set at
SIX sites — every one of them a refusal the ENGINE detects: a position's
declared fact absent, a client rule recorded, the wrong body of authority. On an
ESCALATION, where the DESK is the thing that noticed, there was nowhere to put a
question: `Answer` had no `ask` field and `ask.answer` had no `ask` parameter.
Every escalation ever produced came back with `ask=''`.

WHAT IT COST, AND IT IS NOT SUBTLE. Asked about a forklift on 8 September, a
desk worked out exactly what it needed — the invoice amount, whether the client
elects the de minimis safe harbour, whether it has an applicable financial
statement — and wrote all three into the PROSE of `working`, because no field
would carry them. A caller cannot act on a paragraph. Read from outside, that
looked like *"the desk needs a client-context store before it can answer
anything"*, and a session reported exactly that to the firm. It was wrong. The
desk did not need a store. It needed to be able to ask.
"""
import pytest

import ask
import engine

FORKLIFT = "we bought a forklift. is the invoice price deducted or capitalized?"
WORKING = ("1.263(a)-2(d)(1) opens 'Except as provided in 1.162-3 ... and in "
           "1.263(a)-1(f)', and this desk holds neither exception's facts.")
FOLLOW_UP = ("What was the invoice amount, and does the client have an "
             "applicable financial statement? Under the threshold that applies, "
             "the de minimis safe harbour may reach it.")


def _escalate(reason, **kw):
    return ask.answer(FORKLIFT, "fixed-assets", escalate=reason,
                      working=WORKING, keep=False, **kw)


# ------------------------------------------------------- it refuses to stall

@pytest.mark.parametrize("reason", engine.MUST_ASK)
def test_an_escalation_a_person_can_resolve_needs_a_question(reason):
    with pytest.raises(engine.EngineError, match="without a follow-up question"):
        _escalate(reason)


@pytest.mark.parametrize("reason", engine.MUST_ASK)
def test_and_whitespace_is_not_a_question(reason):
    with pytest.raises(engine.EngineError):
        _escalate(reason, ask="   \n  ")


def test_the_error_says_what_to_do_about_it():
    """A gate that refuses without naming the fix teaches nothing."""
    with pytest.raises(engine.EngineError) as e:
        _escalate("facts_not_established")
    said = str(e.value)
    assert "`ask=`" in said
    assert "PERSON can resolve" in said


# ------------------------------------------------ and not where nobody can help

def test_a_search_task_is_not_forced_to_invent_a_question():
    """`authority_absent` is a claim about the RECORD — there is nobody to ask,
    and requiring a question here would produce one written to satisfy a check.
    The firm would answer it and learn nothing."""
    out = _escalate("authority_absent")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent"


def test_the_must_ask_set_is_small_and_deliberate():
    """THE DENOMINATOR. Requiring it on every reason would make the field noise."""
    assert set(engine.MUST_ASK) == {
        "facts_not_established", "context_not_on_file", "document_not_requested"}
    assert len(engine.MUST_ASK) < len(engine.REASONS) / 3


# ------------------------------------------------------- what the caller gets

def test_the_question_reaches_the_caller():
    out = _escalate("facts_not_established", ask=FOLLOW_UP)
    assert isinstance(out, engine.Refusal)
    assert out.ask == FOLLOW_UP


def test_and_is_printed_where_a_person_will_read_it():
    shown = str(_escalate("facts_not_established", ask=FOLLOW_UP))
    assert FOLLOW_UP in shown
    assert "It asks:" in shown


def test_the_verdict_still_leads_and_the_reasoning_still_comes_back():
    """The follow-up is added to the refusal, not instead of the rest of it."""
    out = _escalate("facts_not_established", ask=FOLLOW_UP)
    shown = str(out)
    assert shown.splitlines()[0].startswith("THE DESK DID NOT ANSWER")
    assert WORKING in shown
    assert shown.index(WORKING) < shown.index(FOLLOW_UP)


def test_an_authority_absent_escalation_may_still_carry_one():
    """Not required is not forbidden — a searcher can say what would help."""
    out = _escalate("authority_absent", ask="Does the firm hold an ASC licence?")
    assert out.ask == "Does the firm hold an ASC licence?"


# --------------------------------------------------- the answering contract

def test_the_harness_prompt_demands_a_real_question():
    """The tool's prompt is what an answering model actually reads. A field the
    engine requires and the prompt never mentions is a gate that fires on every
    honest attempt."""
    from tools import ask_the_desks
    prompt = "\n".join(ask_the_desks.brief_lines()) if hasattr(
        ask_the_desks, "brief_lines") else ""
    if not prompt:                       # the prompt is assembled inline
        import inspect
        prompt = inspect.getsource(ask_the_desks)
    assert '"ask"' in prompt
    assert "MUST fill in `ask`" in prompt
    assert "more information needed" in prompt, (
        "the prompt does not say what a USELESS question looks like, and that "
        "is the one it will otherwise produce")


def test_a_stale_answer_set_is_a_row_and_not_a_crash():
    """THIRTEEN ANSWERS, ONE WRITTEN UNDER AN OLDER CONTRACT. `serve_answers`
    put every answer straight through `serve`, so one `EngineError` killed the
    run and reported none of the twelve that were fine.

    Found replaying `runs/reasked-2026-09-07-evening`, recorded before `ask`
    existed. That file is a RECORD of what the desks did; backfilling questions
    into it would be inventing evidence."""
    import json
    from pathlib import Path
    from tools import ask_the_desks
    real = Path(__file__).resolve().parents[1] / "runs" / \
        "reasked-2026-09-07-evening" / "answers.json"
    stale = [a for a in json.loads(real.read_text(encoding="utf-8"))
             if a.get("escalated") and a.get("reason") in engine.MUST_ASK
             and not a.get("ask")]
    assert stale, "the historical run no longer contains a pre-contract answer"
