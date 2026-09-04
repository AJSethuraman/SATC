"""The adapter's deterministic parts: what the prompt carries, what it refuses.

No model runs here and no score is asserted. What IS asserted is the gate that
sits between the record and the brain, because a leak check nothing exercises
is a promise -- and the first record's leak was called fixed twice before a
test caught it.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter

import pytest

import engine
import record
import scoreboard
from conftest import DESKS, ROOT
from engine import Answer

sys.path.insert(0, str(ROOT / "tools"))
import scoreboard_run as sr        # noqa: E402

DESK = DESKS / "fixed-assets"


def _scratch(tmp_path, *, extra_passage: str = ""):
    """A one-problem desk whose authority is a rule, plus whatever is added."""
    d = tmp_path / "desk"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · Reg\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** 26 CFR 1.263(a)-3\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · Big job\n\n**Citation:** 26 CFR 1.263(a)-3(k)(1)(vi)\n\n"
        "**Answer:** must capitalize\n\n"
        "**Facts:** K owns a building. K pays an amount to replace the entire "
        "roof, including the decking, insulation and membrane. The old roof "
        "had leaked for years.\n", encoding="utf-8")
    (d / "extracted" / "reg.md").write_text(
        "## 26 CFR 1.263(a)-3(k)(1)(vi)\n\n**Source:** S1 · **Checked:** "
        "2026-09-04\n\n> Is for the replacement of a major component. Text of "
        "the rule follows.\n" + extra_passage, encoding="utf-8")
    return record.load(d)


def test_the_prompt_shows_the_rules_and_the_facts_once():
    desk = record.load(DESK)
    for p in desk.problems:
        prompt = sr.build_prompt(p, desk)
        assert "26 CFR 1.263(a)-3(k)(1)(vi) — Is for the replacement" in prompt
        assert prompt.count(p.facts) == 1
        assert p.title not in prompt


def test_a_worked_example_stored_as_authority_is_refused_at_the_prompt(tmp_path):
    """The leak at its new boundary, as a mechanism. Store the problem's own
    example beside the rules and the prompt refuses to be built."""
    clean = _scratch(tmp_path)
    assert "K owns a building" in sr.build_prompt(clean.problems[0], clean)
    leaking = _scratch(
        tmp_path / "b",
        extra_passage="\n---\n\n## 26 CFR 1.263(a)-3(k)(7) Example 14\n\n"
                      "**Source:** S1 · **Checked:** 2026-09-04\n\n"
                      "> K owns a building. K pays an amount to replace the "
                      "entire roof, including the decking, insulation and "
                      "membrane. Therefore, K must capitalize it.\n")
    with pytest.raises(sr.Leak, match="fact pattern of P1"):
        sr.build_prompt(leaking.problems[0], leaking)


def test_the_two_shapes_and_nothing_else():
    desk = record.load(DESK)
    index = sr.build_prompt(desk.problems[0], desk, shape="index")
    text = sr.build_prompt(desk.problems[0], desk, shape="text")
    rule = desk.passage("26 CFR 1.263(a)-3(j)(1)")
    assert rule.text in text and rule.text not in index
    assert len(index) < len(text) / 3, "the index shape is not short"
    with pytest.raises(ValueError, match="shape"):
        sr.build_prompt(desk.problems[0], desk, shape="everything")


def test_the_constant_control_reports_the_citation_baseline():
    desk = record.load(DESK)
    c = sr.constant_control(desk)
    citation, n = Counter(p.citation for p in desk.problems).most_common(1)[0]
    assert (c["citation"], c["cites"], c["of"]) == (citation, n, len(desk.problems))
    assert c["through_the_engine"]["correct"] == 0, "a constant answer cites nothing"


def test_a_reply_that_is_not_json_is_graded_as_it_came_back():
    a = sr.parse_reply("I think it must be capitalized.")
    assert a.citation == "" and not a.escalated
    a = sr.parse_reply('{"position": "x", "citation": "c", "escalated": true, '
                       '"reason": "because"}')
    assert not a.escalated and a.citation == "c", "an unknown reason is an answer"


def test_the_script_records_what_was_shown_beside_the_baselines(tmp_path):
    """End to end through `_main` on a copy of the desk, with a replay file
    standing in for a brain: the record must say which shape of the authority
    the brain saw and what a constant citation would have matched."""
    copy = tmp_path / "fixed-assets"
    shutil.copytree(DESK, copy, ignore=shutil.ignore_patterns("runs", "unsupported"))
    desk = record.load(copy)
    replies = tmp_path / "replies.json"
    replies.write_text(json.dumps({
        p.id: json.dumps({"position": p.answer, "citation": p.citation,
                          "escalated": False, "reason": "", "working": "w"})
        for p in desk.problems}), encoding="utf-8")
    out = tmp_path / "out"
    rc = sr._main(["--desk", str(copy), "--skip-forge", "--out", str(out),
                   "--frontier-replies", str(replies), "--corpus", "index"])
    assert rc == 0
    board = (out / "SCOREBOARD.txt").read_text(encoding="utf-8")
    assert (f"AUTHORITY SHOWN: {len(desk.passages)} stored paragraphs as "
            f"'index', for {len(desk.problems)} problems.") in board
    citation, n = Counter(p.citation for p in desk.problems).most_common(1)[0]
    assert f"citing {citation!r} every time matches {n} of {len(desk.problems)}" in board
    outcomes = json.loads((out / "outcomes.json").read_text(encoding="utf-8"))
    assert outcomes["frontier"]["counts"]["correct"] == len(desk.problems)


# ── containment is measured, and never scored ────────────────────────────────

def test_a_finer_path_under_the_governing_rule_is_counted_apart():
    """Seven problems key to `(j)` because that is what the regulation's own
    conclusion names. A desk answering "betterment, (j)(1)(iii)" has reached the
    right rule by a finer path, and the engine refuses it — correctly, since
    `_check` is shared with `serve()` and anything accepting a near-miss here
    hands one to a client.

    So it is reported rather than forgiven, and reported OUTSIDE the four
    outcomes: containment admits 14 of 172 paths under `(j)` and exactly 1 under
    `(k)(1)(vi)`, so scoring by it would grade seven problems fourteen times more
    leniently than one for no reason but the regulation's prose.
    """
    desk = record.load(DESK)
    coarse = next((p for p in desk.problems if p.citation.endswith("-3(j)")), None)
    assert coarse is not None, "fixture has no coarsely-keyed problem"
    finer = coarse.citation + "(1)(iii)"

    answers = {p.id: Answer(position=p.answer, citation=p.citation)
               for p in desk.problems}
    answers[coarse.id] = Answer(position=coarse.answer, citation=finer)
    run = scoreboard.run(desk, lambda p: answers[p.id], model="probe")
    d = sr.diagnostic(desk, run, answers)

    assert d["citation_within_governing_rule"] == 1, d
    assert d["citation_matched"] == len(desk.problems) - 1, d
    assert d["citation_off_index"] == 0, "a real subparagraph is in the index"

    # And it stays out of every total the scoreboard reports.
    counts = run.counts
    assert sum(counts.values()) == len(desk.problems)
    assert counts["correct"] == len(desk.problems) - 1, (
        "a finer path was scored as correct; the engine must still refuse it")


def test_wrongly_absorbed_is_reachable_at_all():
    """The one outcome that costs anything, proved reachable rather than assumed.

    `grade()` refuses a wrong citation BEFORE comparing the conclusion, so on a
    run where citations are the weak part this number is structurally suppressed
    — the first scoreboard reported 0 on both rows and said so: the trap was not
    sprung, not proved unsprungable. Loosening the gate would expose it; proving
    it directly costs nothing and loosens nothing.
    """
    desk = record.load(DESK)
    p = desk.problems[0]
    other = next(q.answer for q in desk.problems if q.answer != p.answer)

    caught = engine.grade(Answer(position=other, citation=p.citation), p, desk)
    assert caught.outcome is engine.Outcome.WRONGLY_ABSORBED, (
        f"a wrong conclusion behind a citation that HELD graded {caught.outcome}; "
        f"the costly outcome cannot be reached and every 0 reported for it is "
        f"meaningless"
    )
    # The control: same wrong conclusion, wrong citation — caught earlier, so the
    # suppression this test exists to characterise is real and not imagined.
    wrong_cite = next(q.citation for q in desk.problems if q.citation != p.citation)
    assert engine.grade(Answer(position=other, citation=wrong_cite), p, desk
                        ).outcome is engine.Outcome.WRONG_CAUGHT
