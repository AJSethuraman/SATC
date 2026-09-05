"""The front door, which was a promise in a refusal message until it was built.

`routing.refusal_naming_the_desk` has always told a stopped agent to "Ask <desk>
with ask_desk, then come back with the citation." There was no `ask_desk`. Seven
desks, an engine, a measured gate, and nothing a caller could invoke — the record
complete and unreachable. These tests are about the door, not the record.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import dataclasses

import ask
import engine
import positions
import record
from conftest import DESKS


def test_the_tool_the_refusal_message_names_exists():
    """The one that would have caught it. A refusal that instructs a caller to
    use a tool nobody wrote is a dead end wearing a next step's clothes."""
    import routing
    msg = routing.refusal_naming_the_desk(
        "is a brewery tab a business meal?", routing.registry(DESKS))
    assert "ask_desk" in msg, "fixture no longer proves it"
    assert callable(ask.consult) and callable(ask.answer)


def test_a_question_comes_back_with_what_it_may_be_answered_from():
    hits = ask.consult("is a brewery tab a business meal?", DESKS)
    assert [d for d, _ in hits] == ["meals-and-entertainment"]
    text = hits[0][1]
    assert "## The authority" in text and "26 CFR 1.274" in text


def test_silence_is_a_result():
    """A question touching no desk comes back empty — not routed to the nearest
    one. A router that always answers is one whose answer means nothing."""
    assert ask.consult("what time is the train", DESKS) == []


def test_the_brief_never_carries_the_answer_key():
    """`PROBLEMS.md` is the key. A desk scored against problems its answerer
    could read measures transcription, not knowledge."""
    desk = record.load(DESKS / "cash-and-bank")
    text = ask.brief("does the client hold materials at year end?", desk)
    for p in desk.problems:
        assert p.facts not in text, f"{p.id}'s facts reached the answerer"
        assert f"**Answer:** {p.answer}" not in text


def test_the_brief_never_carries_a_proposal():
    """A PROPOSED position is one agent's suggestion nobody has said yes to.
    Showing it would let a guess become the next agent's premise, which is the
    whole failure the two-store split exists to prevent.

    NAMED DESKS USED TO BE THE FIXTURE, AND RATIFICATION BROKE IT. This asserted
    over `capitalization-and-de-minimis` and `vehicle-expense`; on 5 September
    2026 the firm ratified every vehicle proposal and the test failed for saying
    a desk "no longer proves it" -- the record moving as designed, reported as a
    defect. So the fixture is now built here, and the record is checked as well
    as rather than instead of.
    """
    built = dataclasses.replace(
        record.load(DESKS / "cash-and-bank"),
        positions=(positions.Position(
            id="POSX", title="a proposal nobody has said yes to",
            citation="IRS Pub. 583 (12/2024), \"Reconciling the checking account\""
                     " -- what the statement did not yet include",
            recorded="2026-09-05",
            position="THIS SENTENCE MUST NEVER REACH AN ANSWERER"),))
    assert all(q.proposed for q in built.positions), "the fixture is not a proposal"
    assert "THIS SENTENCE MUST NEVER REACH AN ANSWERER" not in ask.brief("cheque", built)

    # And the same over whatever the record actually holds today, which may be
    # nothing -- ratification is the point, so an empty sweep is not a failure.
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        text = ask.brief("what is our capitalisation threshold?", desk)
        for q in desk.positions:
            if q.proposed:
                assert q.position not in text, f"{d.name}/{q.id} reached the answerer"


def test_the_firms_own_positions_do_reach_the_answerer():
    """The other half. A ratified position is the firm's word and real
    authority — on a `human_only` source it is the desk's ENTIRE knowledge."""
    desk = record.load(DESKS / "cash-and-bank")
    ratified = [q for q in desk.positions if not q.proposed]
    assert ratified, "fixture no longer proves it"
    text = ask.brief("is an uncleared cheque a reconciling item?", desk)
    assert all(q.position in text for q in ratified)


def test_an_answer_goes_through_the_production_path():
    desk = record.load(DESKS / "cash-and-bank")
    cb4 = next(p for p in desk.problems if p.id == "CB4")

    good = ask.answer(cb4.facts, "cash-and-bank", position=cb4.answer,
                      citation=cb4.citation, desks=DESKS, keep=False)
    assert not isinstance(good, engine.Refusal)

    timing = next(c for c in desk.answered_by if "did not yet include" in c)
    bad = ask.answer(cb4.facts, "cash-and-bank",
                     position="a reconciling item, no entry in the books",
                     citation=timing, desks=DESKS, keep=False)
    assert isinstance(bad, engine.Refusal)
    assert bad.reason == "citation_does_not_support"


def test_an_escalation_is_a_first_class_answer():
    out = ask.answer("what did the client buy at the hardware store?",
                     "cash-and-bank", escalate="facts_not_established",
                     desks=DESKS, keep=False)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "facts_not_established"


def test_a_refusal_is_kept_with_its_reasoning(tmp_path):
    """A refusal is a finding, and the queue is the only thing that says what
    the record is missing. Thrown away, the finding is destroyed."""
    import shutil
    desks = tmp_path / "desks"
    shutil.copytree(DESKS / "cash-and-bank", desks / "cash-and-bank")

    out = ask.answer("is a brewery tab a business meal?", "cash-and-bank",
                     position="fully deductible", citation="26 CFR 9.9-9",
                     model="a test", desks=desks)
    assert isinstance(out, engine.Refusal)

    queue = desks / "cash-and-bank" / "unsupported" / "asked.md"
    assert queue.is_file(), "the refusal was dropped"
    import unsupported
    kept = unsupported.parse(queue.read_text(encoding="utf-8"))
    assert len(kept) == 1
    assert "brewery" in kept[0].question
    assert kept[0].failed_because == "authority_absent"


def test_keeping_is_the_default_and_the_default_is_the_point(tmp_path):
    """`keep=False` exists for measuring. Defaulting it off would make every
    caller who forgot it silently destroy the findings."""
    import inspect
    assert inspect.signature(ask.answer).parameters["keep"].default is True


# ── what Codex found on #272, each pinned ────────────────────────────────────

def test_the_callers_reasoning_survives_into_the_queue(tmp_path):
    """IT DID NOT. `answer()` took `working` and never passed it to `Answer`, so
    every entry filed through the front door arrived blank — while the skill
    beside it demands a real one, because the reasoning is the only thing that
    says what authority is missing. A queue of blank refusals is a count, and a
    count is the thing this was built not to be."""
    import shutil
    import unsupported

    desks = tmp_path / "desks"
    shutil.copytree(DESKS / "cash-and-bank", desks / "cash-and-bank")
    ask.answer("what did the client buy at the hardware store?", "cash-and-bank",
               position="x", citation="26 CFR 9.9-9",
               working="the rule turns on what was bought and nobody has said",
               model="a test", desks=desks)
    kept = unsupported.parse(
        (desks / "cash-and-bank" / "unsupported" / "asked.md")
        .read_text(encoding="utf-8"))
    assert kept[0].working == "the rule turns on what was bought and nobody has said"


def test_an_escalations_reasoning_survives_too(tmp_path):
    """The other branch, which is the one a well-behaved desk uses most."""
    import shutil
    import unsupported

    desks = tmp_path / "desks"
    shutil.copytree(DESKS / "cash-and-bank", desks / "cash-and-bank")
    ask.answer("whose vehicle is it?", "cash-and-bank",
               escalate="facts_not_established",
               working="nothing on this desk reaches vehicle ownership",
               desks=desks)
    kept = unsupported.parse(
        (desks / "cash-and-bank" / "unsupported" / "asked.md")
        .read_text(encoding="utf-8"))
    assert kept[0].working == "nothing on this desk reaches vehicle ownership"


def test_the_skill_reaches_the_module_from_the_installed_plugin():
    """A skill runs inside whatever repository the caller is working in, and
    `desk` is installed elsewhere — so a bare `import ask` raises
    ModuleNotFoundError on the first line of the first use. Which is the same
    failure as `ask_desk` not existing: a front door that opens onto a wall.

    THE PROSE IS NOT THE CODE, which this test learned by passing on the wrong
    one: it searched the whole file for `import ask` and found the sentence
    warning against it, several lines above the fix. What a caller runs is the
    fenced block, so that is what is checked.
    """
    import re

    text = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
            / "SKILL.md").read_text(encoding="utf-8")
    blocks = [b for b in re.findall(r"```python\n(.*?)```", text, re.S)
              if re.search(r"^import ask$", b, re.M)]
    assert blocks, "the skill no longer shows the import; show the real one"
    for b in blocks:
        assert b.index("CLAUDE_PLUGIN_ROOT") < b.index("import ask"), (
            "a runnable block imports `ask` without first putting the plugin "
            "root on the path; it fails immediately for every caller that is "
            "not this repository")


def test_a_narrowing_may_not_rest_on_a_position_nobody_ratified(tmp_path):
    """`Desk.position()` excludes proposals. Counting one as held let a desk
    load whose narrowed subject then refused everything — the designated
    citation as `authority_absent`, every other as `citation_does_not_support`.
    A dead subject that reads as a strict desk."""
    d = tmp_path / "proposed-only"
    (d / "extracted").mkdir(parents=True)
    (d / "positions").mkdir(parents=True)
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
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · A proposal\n\n**Citation:** 26 CFR 2 · "
        "**Recorded:** 2026-09-05\n\n**Position:** something\n", encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## proposed-only · A desk\n\n**Answered from S1:** widgets\n\n"
        "**Answered by `26 CFR 2`:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="holds no passage or position"):
        record.load(d)
