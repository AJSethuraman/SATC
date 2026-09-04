"""One test per finding from the Codex review of 4 September 2026.

All six were real. The suite was green through every one of them, which is the
useful part: 42 mutations had been confirmed red and none of them probed these
paths, because a mutation can only break code you thought to write.

Kept in one file, named for where they came from, so the next person can see
what an outside reader found that the author's own checks did not.
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

import _canon
import record
import staleness
from conftest import DESKS, ROOT
from engine import Answer, Outcome, grade, serve

sys.path.insert(0, str(ROOT / "tools"))
import extract_ecfr as ex          # noqa: E402

XML = ROOT / "tools" / "fixtures" / "1.263a-3.xml"


# ── P1 · an example's later paragraphs were dropped ──────────────────────────

def test_every_child_of_an_example_is_read_not_just_pspace():
    """`<P>` is a SIBLING of `<PSPACE>` inside `<EXAMPLE>`, not a child of it.

    Collecting only PSPACE dropped the (ii) paragraph — usually where the
    conclusion lives — so examples arrived with their facts intact and their
    answer missing, and were counted as stating no conclusion. The denominator
    shrank silently.

    (The review named nested `<P>` inside `<PSPACE>`; there are none. The
    mechanism was wrong and the consequence exactly right.)
    """
    root = ET.parse(XML).getroot()
    with_siblings = [e for e in root.findall(".//EXAMPLE") if e.findall("P")]
    assert with_siblings, "fixture no longer has multi-paragraph examples"

    found = {e["title"]: e["text"] for e in ex.examples(XML)}
    e = with_siblings[0]
    tail = " ".join("".join(e.findall("P")[-1].itertext()).split())
    title = "".join(e.find("HED").itertext()).strip().split(". ", 1)[-1]
    assert title in found, "example not extracted at all"
    assert tail[:60] in found[title], (
        "the example's later paragraph was dropped; its conclusion lives there"
    )


def test_reading_every_paragraph_recovers_problems_that_were_being_dropped():
    _, kept, dropped, _, _ = ex.build(XML, DESKS / "fixed-assets",
                                      today="2026-09-04")
    assert len(kept) >= 34, (
        f"only {len(kept)} problems usable; reading every paragraph of each "
        f"example should yield at least 34"
    )


# ── P1 · the citation must support the graded problem ───────────────────────

def test_the_right_answer_from_the_wrong_paragraph_is_not_correct(fixed_assets):
    """The finding that mattered most: it inflated the scoreboard.

    An answer giving the right conclusion while citing any other primary
    passage in the desk was scored CORRECT — so a model could reach the verdict
    from a paragraph about something else. The engine's own docstring already
    claimed to distinguish "a citation that resolves" from "the right one"; the
    claim was written and not implemented.
    """
    p = next(x for x in fixed_assets.problems if x.answer == "must capitalize")
    other = next(x for x in fixed_assets.problems if x.citation != p.citation)
    r = grade(Answer(position=p.answer, citation=other.citation), p, fixed_assets)
    assert r.outcome is not Outcome.CORRECT
    assert r.reason == "citation_does_not_support"
    assert p.citation in r.detail, "the refusal must name what the question turns on"


def test_the_right_answer_from_the_right_paragraph_still_passes(fixed_assets):
    """The control. Without it the fix above could pass by refusing everything."""
    p = fixed_assets.problems[0]
    assert grade(Answer(position=p.answer, citation=p.citation), p,
                 fixed_assets).outcome is Outcome.CORRECT


# ── P2 · staleness counted one entry twice ──────────────────────────────────

def test_an_undated_and_aged_passage_is_counted_once(tmp_path):
    """It landed in `unchecked` and then fell through into `aged`, so `total`
    overstated the denominator — in the one module whose job is to not do that."""
    d = tmp_path / "d"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · s\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** X\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** X 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## X 1\n\n**Source:** S1 · **Checked:** 2000-01-01\n\n> t\n",
        encoding="utf-8")
    r = staleness.check(record.load(d), lambda s: None, today="2026-09-06")
    assert r.total == 1, f"one passage reported as {r.total} entries"
    assert len(r.unchecked) == 1 and r.aged == []
    assert "days old" in r.unchecked[0].detail, "the age is still worth saying"


# ── P2 · installed canon versions sorted as text ────────────────────────────

def test_canon_versions_are_ordered_numerically_not_alphabetically():
    """Sorted as text, "1.9.0" beats "1.10.0" and the OLDER canon loads."""
    from pathlib import Path
    order = sorted([Path("1.9.0"), Path("1.10.0"), Path("1.4.0")],
                   key=_canon._version, reverse=True)
    assert [p.name for p in order] == ["1.10.0", "1.9.0", "1.4.0"]


def test_an_unexpected_directory_name_does_not_break_the_search():
    from pathlib import Path
    assert _canon._version(Path("not-a-version"))  # must not raise


# ── P2 · the documented command wrote nothing ───────────────────────────────

def test_the_extract_command_actually_writes_what_it_computed(tmp_path):
    """It computed both collections, printed counts, and exited 0 having written
    nothing — so the "reproducible regeneration" path regenerated nothing."""
    d = tmp_path / "desk"
    (d / "extracted").mkdir(parents=True)
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "extract_ecfr.py"), str(XML), str(d)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (d / "PROBLEMS.md").is_file(), "PROBLEMS.md was not written"
    written = list((d / "extracted").glob("*.md"))
    assert written, "no authority was written"
    assert "wrote" in r.stdout, "the command should say what it wrote"


# ── P2 · ratified positions were never loaded ───────────────────────────────

def test_a_ratified_position_is_loaded_and_answers(tmp_path):
    """For a `human_only` source a position is the desk's ENTIRE knowledge.

    Unloaded, every citation backed only by a position refused as
    `authority_absent`, making the advertised path unusable — and that path is
    the only way FASB ASC can ever be reached.
    """
    d = tmp_path / "d"
    (d / "positions").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A licensed source\n\n**Tier:** primary · **Access:** human_only · "
        "**May store:** citation_only · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 360-10-35-4\n\n"
        "**Answer:** capitalise it\n\n**Facts:** f\n", encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · Roof replacement\n\n"
        "**Citation:** ASC 360-10-35-4 · **Recorded:** 2026-09-04\n\n"
        "**Position:** capitalise it\n\n**Ratified:** PR #999\n", encoding="utf-8")
    desk = record.load(d)
    assert len(desk.positions) == 1
    out = serve(Answer(position="capitalise it", citation="ASC 360-10-35-4"), desk)
    assert not isinstance(out, type(serve(Answer(position="x"), desk))) or True
    from engine import Refusal, Served
    assert isinstance(out, Served), f"a ratified position must answer, got {out}"


def test_an_unratified_position_does_not_answer(tmp_path):
    """A proposal in an open pull request is not yet the firm's word. Serving it
    would record an answer they never gave."""
    from engine import Refusal
    d = tmp_path / "d"
    (d / "positions").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · s\n\n**Tier:** primary · **Access:** human_only · "
        "**May store:** citation_only · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · x\n\n**Citation:** ASC 1 · **Recorded:** 2026-09-04\n\n"
        "**Position:** a\n", encoding="utf-8")          # no Ratified line
    desk = record.load(d)
    assert desk.positions[0].proposed
    assert isinstance(serve(Answer(position="a", citation="ASC 1"), desk), Refusal)
