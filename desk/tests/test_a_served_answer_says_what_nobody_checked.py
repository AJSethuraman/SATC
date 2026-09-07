"""Every field on a served answer is about the SOURCE. None is about the answer.

THE INCIDENT, 7 September 2026, found by a session testing the installed plugin
on the Forge rather than by anyone building it. It aimed five traps at
`fixed-assets` — the largest desk, and the one carrying no ratified positions at
all — and FOUR SERVED. The sharpest cited § 1.263(a)-2(d)(1), whose own text
opens *"a taxpayer must capitalize amounts paid to acquire or produce a unit of
real or personal property"*, and concluded **"deducted, not capitalized"**. The
literal negation of its own citation, served `tier=primary`, `binding=True`, no
caveat.

WHY EVERY CHECK PASSED AND WAS RIGHT TO. `tier` is the regulation's standing.
`binding` says the firm declared that source as authority that binds — not that
this answer binds. `checked_subject` is word overlap between the question and
the desk's subjects. `checked` is when somebody last confirmed the PASSAGE
against its publisher. Together they read to an accountant as *"this was
checked"*, and the one thing they think was checked is the one thing that was
not. The tester's words: *"Served carries no field for 'did anyone check that
this paragraph says this?'"*

AND THE SKILL ALREADY SAID SO, WHICH WAS NOT ENOUGH. `ask-desk` carries the
sentence *"what it does not verify is that the conclusion follows"* — in prose,
at the top, read once by the agent and long gone by the time an answer is
rendered onward to a person. A warning that does not travel with the thing it
warns about is a warning nobody reads.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import record                                               # noqa: E402

TRAP_Q = "is the invoice price of a forklift deducted or capitalized?"
TRAP_CITE = "26 CFR 1.263(a)-2(d)(1)"


@pytest.fixture(scope="module")
def trap():
    """The tester's sharpest trap, served. It STILL serves — that is the point.
    Nothing here claims to have made it refuse; the domain guard cannot reach
    it, because a tax question cited to a tax regulation is in the right body of
    authority and simply says the opposite of what was claimed."""
    out = ask.answer(TRAP_Q, "fixed-assets",
                     position="deducted, not capitalized",
                     citation=TRAP_CITE, model="the trap", keep=False)
    assert isinstance(out, engine.Served), (
        "the trap now refuses — good, but this file's premise has moved and its "
        "docstring is describing something that no longer happens")
    return out


def test_the_answer_says_nobody_checked_the_conclusion(trap):
    assert trap.unchecked, "a served answer carries no such statement"
    assert "Nobody checked that this paragraph says this" in trap.unchecked


def test_it_names_what_WAS_checked_but_briefly(trap):
    """A REVERSAL, RECORDED RATHER THAN QUIETLY APPLIED.

    This test used to require the sentence to inventory THREE checks — that the
    citation resolves, that the source answers this subject, and the source's
    tier — on the reasoning that a bare disclaimer trains a reader to skip it.

    The Forge disagreed after handing three of these to an accountant mid-close:
    *"at one answer it lands; at the fortieth of a close, the eye slides off the
    capitals and the reader stops reading the part that varies. The
    load-bearing content is the first clause plus 'read the passage below'; the
    middle inventory of what was checked is the part I would actually cut."*

    They did the work; they win. Both concerns are real and the compromise is
    that ONE clause still names what was checked, so the sentence is not a bare
    disclaimer — and the tier and the source are printed beside the citation
    anyway, so the inventory was saying it twice."""
    assert "citation resolves" in trap.unchecked
    assert "source is one this desk uses here" in trap.unchecked


def test_the_cited_paragraph_travels_with_the_answer(trap):
    """Until a judge exists the reader IS the check, and they cannot perform it
    on a citation they have to go and look up. Making them fetch it is what
    turns the review nominal."""
    assert trap.passage, "the answer arrives without the words it rests on"
    assert "must capitalize" in trap.passage


def test_the_answer_therefore_refutes_itself_on_sight(trap):
    """THE WHOLE POINT, asserted as the property rather than trusted. Printed
    together, position and passage contradict each other in two lines. Printed
    apart, the same answer reads as settled law."""
    assert "deducted, not capitalized" in trap.position
    assert "must capitalize" in trap.passage


def test_it_cannot_be_left_off(trap):
    """Computed inside `serve`, never passed in — so no caller can omit it and
    no code path can produce a Served without it."""
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for prob in desk.problems:
            out = engine.serve(
                engine.Answer(position=prob.answer, citation=prob.citation),
                desk, question=prob.facts)
            if isinstance(out, engine.Served):
                assert out.unchecked, f"{prob.id} on {d.name} served without it"
                assert out.passage or out.position, (
                    f"{prob.id} on {d.name} served with neither passage nor "
                    f"position — nothing for a reader to check against")


def test_binding_is_described_as_a_property_of_the_source(trap):
    """`binding` is the field most likely to be misread, and it is not renamed —
    ten call sites to fix a READING problem is the wrong tool. Instead the
    sentence beside it says what it means."""
    assert "only that the citation resolves and the source is one this desk " \
           "uses here" in trap.unchecked, (
        "the sentence no longer distinguishes checking the SOURCE from "
        "checking the conclusion, which is the misreading it exists to stop")


def test_a_non_binding_answer_says_so_in_the_same_sentence():
    """The other branch, so the wording cannot quietly assert "binding" on an
    answer that does not bind."""
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank",
                     position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert isinstance(out, engine.Served)
    assert "does not bind" in out.unchecked or out.binding, (
        "a non-binding source served with binding language")


def test_the_skill_tells_the_agent_to_pass_both_on():
    """The object carrying it is half. An agent that renders `position` and
    `citation` and drops the rest has undone the whole thing, so the skill has
    to say so where the agent reads what to do with an answer."""
    skill = (HERE / "skills" / "ask-desk" / "SKILL.md").read_text(encoding="utf-8")
    flat = " ".join(skill.split())
    assert "out.unchecked" in flat and "out.passage" in flat, (
        "the skill never shows the agent printing them")
    assert "MUST pass both on" in flat
    assert "not boilerplate to trim" in flat


def test_a_position_backed_answer_has_something_to_read():
    """FOUND BY RUNNING THE ROUND TRIP, not by a test.

    The first version read `passage.text`, and a ratified position has none —
    it carries the firm's own WORDS in `.position`. So the cash desk served
    "Read the passage." with nothing underneath it: a disclaimer pointing at an
    empty string, which is worse than no disclaimer because it looks discharged.

    On a `human_only` source the firm's words ARE the desk's entire knowledge of
    the authority, so they are both the right thing to show and the only thing
    there is.
    """
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank", position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert isinstance(out, engine.Served)
    assert out.passage, "served 'read this' with nothing to read"


def test_nothing_anywhere_serves_an_empty_thing_to_read():
    """The property, over every recorded answer on every desk — because the
    empty one was found by eye on three examples, and eye-checks do not scale."""
    empty = []
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for prob in desk.problems:
            out = engine.serve(
                engine.Answer(position=prob.answer, citation=prob.citation),
                desk, question=prob.facts)
            if isinstance(out, engine.Served) and not out.passage.strip():
                empty.append(f"{prob.id} on {d.name}")
    assert not empty, (
        "these serve a 'read it yourself' pointing at nothing: " + ", ".join(empty))


def test_a_ratified_answer_does_not_claim_nobody_checked_it():
    """ALSO FOUND BY RUNNING IT. The firm DID check a position-backed answer —
    they ratified that conclusion for that citation, and `_check` refuses any
    restatement, so the words served are theirs. Saying "nobody checked" there
    is a lie in the safe direction, and a disclaimer that cries wolf on the
    safest answers teaches a reader to skip it on the dangerous ones."""
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank", position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert "Nobody checked that this paragraph says this" not in out.unchecked
    assert "THE FIRM RATIFIED THIS CONCLUSION" in out.unchecked
    assert "fits these particular facts" in out.unchecked, (
        "claims the answer is checked without naming what still is not")


def test_an_unratified_answer_still_gets_the_hard_sentence(trap):
    """And the split must not become a way for the dangerous case to get the
    gentle wording."""
    assert "Nobody checked that this paragraph says this" in trap.unchecked
    assert "THE FIRM RATIFIED" not in trap.unchecked


# ── what the Forge found when it closed a set of books on 0.7.2 ──────────────


def test_a_ratified_answer_shows_the_AUTHORITY_not_itself():
    """THE DEFECT I INTRODUCED FIXING THE LAST ONE.

    `serve` resolves through `authority_for`, which on a ratified citation
    returns the POSITION — and a Position has no `.text`. The first fix fell
    back to `.position`, so the field echoed the answer:

        an entry in the books            <- position
        > an entry in the books          <- "the words it rests on"

    The Forge tester: *"the whole argument for `passage` is 'so the reader can
    check the conclusion against the words it rests on' — and here the words it
    rests on are the Pub. 583 text, which is not shown. The one case where the
    reader is told a human already decided is the case where the underlying
    authority becomes invisible."* The text was reachable the whole time.
    """
    cite = ('IRS Pub. 583 (12/2024), "Reconciling the checking account" '
            '— what the books are updated for')
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank", position="an entry in the books",
                     citation=cite, model="m", keep=False)
    assert isinstance(out, engine.Served)
    assert out.passage != out.position, "the passage is the answer restated"
    assert "reconcil" in out.passage.lower(), (
        "the passage is not the publication's own text")
    # And the desk really does hold it, so the fallback is never reached here.
    desk = record.load(HERE / "desks" / "cash-and-bank")
    assert desk.passage(cite).text in out.passage


def test_a_citation_only_source_still_falls_back_to_the_firms_words():
    """The fallback is not removed, only demoted. On a `human_only` source a
    position genuinely IS the desk's whole knowledge of the authority, and
    there is nothing else to put in front of a reader."""
    import inspect
    src = inspect.getsource(engine.serve.__wrapped__
                            if hasattr(engine.serve, "__wrapped__")
                            else engine.serve)
    assert 'getattr(passage, "position", "")' in src, (
        "the citation-only fallback was removed; a human_only desk now serves "
        "nothing to read")


def test_an_escalation_hands_back_the_askers_own_reasoning():
    """It went only to the queue. The Forge, closing books: *"the one answer
    where the agent has the most to say hands the caller the least… Meanwhile
    `showed_by_source` — pure instrumentation — does come back. That is exactly
    backwards for a human reader."*"""
    out = ask.answer("does a widget purchase become an asset?", "fixed-assets",
                     escalate="authority_absent",
                     working="the desk holds the improvement rules and nothing "
                             "on what a widget is",
                     model="m", keep=False)
    assert isinstance(out, engine.Refusal)
    assert "improvement rules" in out.working, (
        "the reasoning reaches the queue and not the caller")


def test_every_kind_of_refusal_carries_it_not_just_escalations():
    """Set once where all refusals pass through, so a refusal added later
    cannot quietly drop it."""
    out = ask.answer("what do I do with a $10 service charge?", "cash-and-bank",
                     position="something else entirely",
                     citation="26 CFR 1.999-9(z)",
                     working="my reasoning, which the caller needs",
                     model="m", keep=False)
    assert isinstance(out, engine.Refusal)
    assert out.working == "my reasoning, which the caller needs"


def test_the_unchecked_sentence_is_short_enough_to_survive_repetition():
    """*"At one answer it lands; at the fortieth of a close, the eye slides off
    the capitals."* The middle inventory of what WAS checked is cut — it is a
    property of the source and already printed beside the citation."""
    out = ask.answer("is the invoice price of a forklift deducted or capitalized?",
                     "fixed-assets", position="deducted, not capitalized",
                     citation="26 CFR 1.263(a)-2(d)(1)", model="m", keep=False)
    assert len(out.unchecked.split()) <= 32, (
        f"{len(out.unchecked.split())} words; it will be skimmed by the fortieth")
    assert "Nobody checked that this paragraph says this" in out.unchecked
    assert "Read the passage below" in out.unchecked


def test_the_skills_first_line_does_not_need_an_environment_variable():
    """`CLAUDE_PLUGIN_ROOT` is set when the skill is INVOKED and unset in a
    plain shell, so the documented first line of first use raised KeyError for
    a session that pasted it. Executed rather than pattern-matched — a snippet
    that only LOOKS right is what shipped.

    AND THE FIRST FIX FOR THAT RAISED SOMETHING ELSE. On a machine with no
    plugin installed — CI is one — `os.listdir` on the missing cache threw a
    bare `FileNotFoundError` naming a path, which tells a reader nothing about
    what to do. Caught by this test going red in CI, which is the test working.

    So the assertion is not "it always succeeds", which is false: without the
    plugin there is genuinely no desk to ask. It is that BOTH outcomes are
    useful — it imports, or it says what is missing and how to get it.
    """
    import re
    import subprocess
    import sys as _sys
    import tempfile

    skill = (HERE / "skills" / "ask-desk" / "SKILL.md").read_text(encoding="utf-8")
    block = re.search(r"```python\n(import os, sys\n.*?)```", skill, re.S).group(1)
    snippet = block.split("import ask")[0] + "print(sys.path[0])"
    base = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}

    # 1 · where the plugin IS installed, it must resolve and say where.
    here = subprocess.run([_sys.executable, "-c", snippet],
                          capture_output=True, text=True, env=base)
    if here.returncode:
        assert "no desk plugin at" in here.stdout + here.stderr, (
            f"raised something unreadable:\n{here.stderr}")
    else:
        assert here.stdout.strip(), "resolved silently to nothing"

    # 2 · where it is NOT, it must refuse in words a reader can act on —
    #     never a traceback about a missing directory.
    away = subprocess.run([_sys.executable, "-c", snippet], capture_output=True,
                          text=True, env=dict(base, HOME=tempfile.mkdtemp()))
    out = away.stdout + away.stderr
    assert "Traceback" not in out, f"bare traceback on a clean machine:\n{out}"
    assert "no desk plugin at" in out and "claude plugin" in out, (
        f"does not say what is missing or how to get it:\n{out}")



def test_the_skill_warns_that_the_tool_may_serve_a_stale_copy():
    """A session invoked the skill and the tool served SKILL.md from a cache
    three releases old — a file with no mention of the fields the release exists
    to deliver. It would have been followed correctly and produced the old
    output, and nothing said so at the point it bit."""
    flat = " ".join((HERE / "skills" / "ask-desk" / "SKILL.md")
                    .read_text(encoding="utf-8").split())
    assert "three releases stale" in flat or "releases stale" in flat
    assert "/reload-plugins" in flat
