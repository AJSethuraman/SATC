"""The front door, which was a promise in a refusal message until it was built.

`routing.refusal_naming_the_desk` has always told a stopped agent to "Ask <desk>
with ask_desk, then come back with the citation." There was no `ask_desk`. Seven
desks, an engine, a measured gate, and nothing a caller could invoke — the record
complete and unreachable. These tests are about the door, not the record.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import dataclasses

import ask
import engine
import positions
import record
import conftest                                             # noqa: E402
from conftest import CORPUS

HERE = Path(__file__).resolve().parents[1]


def test_the_front_door_the_skills_name_exists():
    """The one that would have caught it. An instruction that tells a caller to
    use a tool nobody wrote is a dead end wearing a next step's clothes.

    IT USED TO CHECK A ROUTING MESSAGE. `routing.refusal_naming_the_desk` built
    the string "Ask <desk> with ask_desk" and this asserted the string mentioned
    the tool. `dec-kill` deleted routing, and with it the only thing that ever
    named a desk — so the check moves to where the instruction actually lives
    now, which is the skills an agent reads at runtime. A skill naming a
    function that does not exist is the same defect one layer up.
    """
    named = set()
    for f in sorted((HERE / "skills").rglob("SKILL.md")):
        for m in re.finditer(r"\bask\.(\w+)\(", f.read_text(encoding="utf-8")):
            named.add(m.group(1))
    assert named, "no skill names a front-door call, so this proves nothing"
    for name in sorted(named):
        assert callable(getattr(ask, name, None)), (
            f"a skill tells an agent to call ask.{name}(), and there is no such "
            f"callable — that is `ask_desk` again")
    assert callable(ask.consult) and callable(ask.answer)


def test_a_question_comes_back_with_what_it_may_be_answered_from():
    """ONE CORPUS, ONE BRIEF. This asserted a list of desk names until
    10 September 2026; `dec-kill` left nothing to name."""
    text = ask.consult("is a brewery tab a business meal?")
    assert "## The authority" in text and "26 CFR 1.274" in text


def test_silence_is_a_result():
    """A question touching no desk comes back empty — not routed to the nearest
    one. A router that always answers is one whose answer means nothing."""
    assert ask.consult("zzqx vvbbnn") == ""


def test_the_brief_never_carries_the_answer_key():
    """`PROBLEMS.md` is the key, and the GRADING brief is where that matters.

    WHAT ONE CORPUS MADE VISIBLE, 10 September 2026. This asserted over
    `cash-and-bank`, whose four problems happen not to be drawn from passages it
    holds, and it passed. Over one corpus it fails immediately: CD1's facts ARE
    the text of `26 CFR 1.263(a)-1(f)(7) Example 1`, which the corpus holds,
    because six of the seven records draw their problems from the worked
    examples of the regulation they store.

    So the property was never true of a record holding both — it was true of the
    one desk this test happened to pick. The answer key is IN the corpus by
    construction, and `brief_for_grading` is the thing that exists to keep it
    away from anything being scored (`runs/2026-09-04/SCOREBOARD.md`: the first
    corpus stored the 21 examples it also graded on, and a frontier model solved
    the set as a matching puzzle rather than by reasoning).

    ASSERTED ON BOTH HALVES, because a one-sided version would pass if
    `rules_only` started dropping everything: the grading brief must not carry a
    problem's facts, AND the answering brief must still carry real authority.
    """
    desk = record.load(CORPUS)
    graded = ask.brief_for_grading("does the client hold materials at year end?",
                                   desk)
    for p in desk.problems:
        assert p.facts not in graded, f"{p.id}'s facts reached a graded answerer"
        assert f"**Answer:** {p.answer}" not in graded

    # The answering brief is a different question and still holds authority.
    answering = ask.brief("does the client hold materials at year end?", desk)
    assert "## The authority" in answering and len(answering) > len(graded)

    # AND THE PROBLEM'S OWN ANSWER LINE NEVER APPEARS ANYWHERE. A worked example
    # states its conclusion in the regulation's words; `**Answer:**` is OURS,
    # and it reaching an answerer would be the record handing over its key.
    for p in desk.problems:
        assert f"**Answer:** {p.answer}" not in answering


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
        record.load(CORPUS),
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
    desk = record.load(CORPUS)
    text = ask.brief("what is our capitalisation threshold?", desk)
    for q in desk.positions:
        if q.proposed:
            assert q.position not in text, f"{q.id} reached the answerer"


def test_the_firms_own_positions_do_reach_the_answerer():
    """The other half. A ratified position is the firm's word and real
    authority — on a `human_only` source it is the desk's ENTIRE knowledge."""
    desk = record.load(CORPUS)
    ratified = [q for q in desk.positions if not q.proposed]
    assert ratified, "fixture no longer proves it"
    text = ask.brief("is an uncleared cheque a reconciling item?", desk)
    assert all(q.position in text for q in ratified)


def test_an_answer_goes_through_the_production_path():
    desk = record.load(CORPUS)
    cb4 = next(p for p in desk.problems if p.id == "CB4")

    good = conftest.answer_judged(cb4.facts,  position=cb4.answer,
                      citation=cb4.citation, corpus=CORPUS, keep=False)
    assert not isinstance(good, engine.Refusal)

    timing = next(c for c in desk.answered_by if "did not yet include" in c)
    bad = conftest.answer_judged(cb4.facts, 
                     position="a reconciling item, no entry in the books",
                     citation=timing, corpus=CORPUS, keep=False)
    assert isinstance(bad, engine.Refusal)
    assert bad.reason == "citation_does_not_support"


def test_an_escalation_is_a_first_class_answer():
    out = conftest.answer_judged("what did the client buy at the hardware store?",
                      escalate="facts_not_established",
                     ask="What was the charge for? The statement line alone "
                         "does not say whether it is a bank fee or a payment.",
                     corpus=CORPUS, keep=False)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "facts_not_established"


def test_a_refusal_is_kept_with_its_reasoning(tmp_path):
    """A refusal is a finding, and the queue is the only thing that says what
    the record is missing. Thrown away, the finding is destroyed."""
    import shutil
    desks = tmp_path / "corpus"

    shutil.copytree(CORPUS, desks)

    out = conftest.answer_judged("is a brewery tab a business meal?", 
                     position="fully deductible", citation="26 CFR 9.9-9",
                     model="a test", corpus=desks)
    assert isinstance(out, engine.Refusal)

    queue = desks / "unsupported" / "asked.md"
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

    desks = tmp_path / "corpus"


    shutil.copytree(CORPUS, desks)
    conftest.answer_judged("what did the client buy at the hardware store?", 
               position="x", citation="26 CFR 9.9-9",
               working="the rule turns on what was bought and nobody has said",
               model="a test", corpus=desks)
    kept = unsupported.parse(
        (desks / "unsupported" / "asked.md")
        .read_text(encoding="utf-8"))
    assert kept[0].working == "the rule turns on what was bought and nobody has said"


def test_an_escalations_reasoning_survives_too(tmp_path):
    """The other branch, which is the one a well-behaved desk uses most."""
    import shutil
    import unsupported

    desks = tmp_path / "corpus"


    shutil.copytree(CORPUS, desks)
    conftest.answer_judged("whose vehicle is it?", 
               escalate="facts_not_established",
               ask="What was the charge for?",
               working="nothing on this desk reaches vehicle ownership",
               corpus=desks)
    kept = unsupported.parse(
        (desks / "unsupported" / "asked.md")
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

    text = (Path(__file__).resolve().parents[1] / "skills" / "be-the-desk"
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
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-05 · **Kind:** rule\n\n> a rule\n",
        encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · A proposal\n\n**Citation:** 26 CFR 2 · "
        "**Recorded:** 2026-09-05\n\n**Position:** something\n", encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## proposed-only · A desk\n\n**Answered from S1:** widgets\n\n"
        "**Answered by `26 CFR 2`:** widgets\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="holds no passage or position"):
        record.load(d)
