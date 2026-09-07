"""A number written in prose is a claim, and it goes stale silently.

THE PATTERN THIS REPOSITORY KEEPS RE-LEARNING. The docket announced twenty-two
matters in fixed text and would have lied about it on the first ratification. Its
`<title>` said "Nine Open" over a page whose headline said thirteen. Both were
caught, both by tests that DERIVE the figure and compare. This is the same guard
for the one number quoted furthest from where it is computed: the size of the
stored corpus.

MEASURED, 6 SEPTEMBER 2026. Removing two worked examples from the rewards desk
took the corpus from 533 passages to 531, and eight files went on saying 533 —
`ask.py`'s opening paragraph, `proving.py`'s docstring, the exhibit generator, the
docket generator in two places. Every one of them is prose a person reads to find
out what this thing is, and every one of them was quietly wrong the moment the
record changed.

THE PUBLISHED EXHIBITS ARE EXEMPT, AND THAT IS NOT A LOOPHOLE. A file under
`tie-outs/` is a DATED ARTIFACT: it records what was fetched, and what was true,
on the day it says. Editing one to agree with today's record would be falsifying
the evidence it exists to be — the opposite of the discipline it was written for.
When the record moves, the exhibits are RE-RUN and re-dated, never patched.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402

#: "533 passages", "533 stored passages", "531 of 533 passages". Three digits,
#: because a two-digit count is almost always a per-desk figure and a per-desk
#: figure is legitimately quoted in that desk's own files.
_QUOTED = re.compile(r"\b(\d{3})(?:\s+of\s+(\d{3}))?\s+(?:stored\s+)?passages\b")

#: Directories whose contents are dated evidence rather than description.
_DATED = ("tie-outs", "runs", "docs")


def _corpus_size() -> int:
    return sum(len(record.load(d).passages)
               for d in sorted(DESKS.iterdir())
               if (d / "SOURCES.md").is_file())


def _files():
    for path in sorted(HERE.rglob("*")):
        if path.suffix not in (".py", ".md") or not path.is_file():
            continue
        rel = path.relative_to(HERE)
        if rel.parts and rel.parts[0] in _DATED:
            continue
        if "__pycache__" in rel.parts or rel.name == pathlib.Path(__file__).name:
            continue
        yield rel, path


def test_no_file_quotes_a_corpus_size_the_record_does_not_have():
    live = _corpus_size()
    wrong = []
    for rel, path in _files():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in _QUOTED.finditer(line):
                # In "531 of 533", the DENOMINATOR is the corpus size and the
                # numerator is a verdict count, which this cannot check.
                total = int(match.group(2) or match.group(1))
                if total != live:
                    wrong.append(f"{rel}:{line_no} says {match.group(0)!r}; "
                                 f"the record holds {live}")
    assert not wrong, (
        f"the stored corpus is {live} passages and these say otherwise. A figure "
        f"in prose is a claim, and it is the first thing a reader believes:\n  "
        + "\n  ".join(wrong))


def test_the_check_can_actually_find_a_figure():
    """A sweep that matches nothing passes over anything. This proves the
    pattern finds the shapes the repository actually writes."""
    for text, expect in (("all 533 passages, once", "533"),
                         ("Seven desks, 533 stored passages, an engine", "533"),
                         ("531 of 533 passages are now proven", "533"),
                         ("47 stored passages, 19 problems", None)):
        found = _QUOTED.search(text)
        if expect is None:
            assert found is None or (found.group(2) or found.group(1)) != expect
        else:
            assert found, text
            assert (found.group(2) or found.group(1)) == expect, text


def test_the_dated_evidence_is_left_alone():
    """The exemption, asserted rather than assumed. If `tie-outs/` ever stopped
    existing, this test would silently be exempting nothing and the docstring
    above would be describing a rule that guards no files."""
    exhibits = list((HERE / "tie-outs").glob("*.pdf"))
    assert exhibits, "no exhibits under tie-outs/; the exemption guards nothing"
    # AND EACH ONE CARRIES ITS RUN DATE IN ITS NAME, which is what makes it
    # evidence rather than a description that went stale.
    for pdf in exhibits:
        assert re.search(r"\d{4}-\d{2}-\d{2}", pdf.name), (
            f"{pdf.name} carries no run date; an exhibit without one cannot be "
            f"told apart from a stale claim, which is the whole exemption")
