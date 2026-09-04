"""The extractor, and the rule that the count cannot lie.

A problem set that quietly omits what it could not parse reports a denominator
that means nothing. `docs/SOFTWARE-TENETS.md` opens on exactly that failure: a
proof artifact once declared 190 documents fine when every one of them was
unreadable.

So nothing is dropped silently, ambiguity is never resolved into a guess, and the
number `PROBLEMS.md` prints about itself is asserted against the file's actual
contents.
"""
from __future__ import annotations

import sys

import pytest

from conftest import DESKS, ROOT

sys.path.insert(0, str(ROOT / "tools"))
import extract_ecfr as ex          # noqa: E402

XML = ROOT / "tools" / "fixtures" / "1.263a-3.xml"


# ── ambiguity is never resolved into a guess ─────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Therefore, A must capitalize the amount paid.", "must capitalize"),
    ("A is not required to capitalize the amount.", "not required to capitalize"),
])
def test_a_single_stated_conclusion_is_read(text, expected):
    assert ex.classify(text) == expected


def test_an_example_stating_both_conclusions_is_left_out_not_guessed():
    """"...not required to capitalize under (x), but must capitalize under (y)"
    is the case a looser matcher turns into a confident wrong answer."""
    both = ("B is not required to capitalize the amounts under paragraph (x), "
            "but must capitalize the amounts under paragraph (y).")
    assert ex.classify(both) is None


def test_an_example_stating_no_conclusion_is_left_out():
    assert ex.classify("C owns a building. C pays an amount for work.") is None


@pytest.mark.parametrize("text", [
    "Assume the same facts as in Example 1, except that...",
    "Assume the same facts as Example 25, except that...",
    "The same facts as Example 3 apply.",
])
def test_an_example_leaning_on_one_not_shown_is_left_out(text):
    """Both spellings. A filter written for only "same facts as in Example"
    missed a real case on this extractor's first run, because the regulation
    also says "same facts as Example" without the *in*."""
    assert ex.DEPENDENT.search(text)


# ── the denominator is real ──────────────────────────────────────────────────

def test_every_example_is_either_kept_or_counted_as_dropped():
    all_ex, kept, dropped, _, _ = ex.build(XML, DESKS / "fixed-assets",
                                           today="2026-09-04")
    assert len(kept) + len(dropped) == len(all_ex), "an example vanished"
    assert all(why for _, why in dropped), "something was dropped with no reason"


def test_the_extraction_is_reproducible_from_the_committed_source():
    """The record can be rebuilt without a network. If eCFR is down, or the
    section is amended, this still runs and the diff shows what moved."""
    _, kept, _, problems, passages = ex.build(XML, DESKS / "fixed-assets",
                                              today="2026-09-04")
    assert len(problems) == len(passages) == len(kept)
    assert problems, "the fixture produced nothing; it is not the section"


def test_problems_md_cannot_lie_about_its_own_count():
    """The document states a denominator. This asserts it against reality.

    A count in prose and a count in the file are two claims with nothing
    comparing them, which is the shape of nearly every real bug here.
    """
    import re

    import record
    desk = record.load(DESKS / "fixed-assets")
    text = (DESKS / "fixed-assets" / "PROBLEMS.md").read_text(encoding="utf-8")

    stated = {m.group(1): int(m.group(2)) for m in
              re.finditer(r"\| ([^|]+?) \| \*\*(\d+)\*\* \|", text)}
    assert stated, "PROBLEMS.md no longer states its counts"
    assert stated["Usable as problems"] == len(desk.problems), (
        f"PROBLEMS.md says {stated['Usable as problems']} usable problems; the "
        f"file actually contains {len(desk.problems)}"
    )
    assert stated["Examples in the section"] == (
        stated["Usable as problems"] + stated["Left out"]), (
        "the stated counts do not add up"
    )


def test_every_exclusion_reason_is_named_in_the_document():
    all_ex, kept, dropped, _, _ = ex.build(XML, DESKS / "fixed-assets",
                                           today="2026-09-04")
    text = (DESKS / "fixed-assets" / "PROBLEMS.md").read_text(encoding="utf-8")
    for _, why in dropped:
        assert why in text, f"examples were dropped for {why!r} and it is not stated"


def test_the_facts_are_verbatim_from_the_source_not_retyped():
    """The extractor reads the regulation's own EXAMPLE elements, so a problem's
    facts are the authority's words by construction.

    Checked sentence by sentence rather than whole, because the conclusion is now
    withheld: the facts are a SUBSET of the example's sentences, and every one of
    them still has to appear in the section exactly as the section wrote it.
    """
    import record
    desk = record.load(DESKS / "fixed-assets")
    _, kept, _, _, _ = ex.build(XML, DESKS / "fixed-assets", today="2026-09-04")
    from_source = "\n".join(e["text"] for e, _ in kept)
    for p in desk.problems:
        for sentence in ex._SENTENCE.split(p.facts):
            assert sentence in from_source, (
                f"problem {p.id} contains {sentence!r}, which the section does not"
            )


def test_no_problem_hands_the_model_its_own_answer():
    """The whole scoreboard rests on this. A problem whose facts state the
    conclusion measures whether a model can copy a sentence.

    Asserted over the COMMITTED record, not over a fresh build, because the file
    a scoreboard run reads is the file on disk -- a check that only ever sees
    what `build` just returned would pass against a leaking `PROBLEMS.md`.
    """
    import record
    desk = record.load(DESKS / "fixed-assets")
    assert desk.problems, "no problems loaded; this check would pass vacuously"
    leaking = [p.id for p in desk.problems if ex.states_conclusion(p.facts)]
    assert not leaking, (
        f"{len(leaking)} problems state their own answer in the facts: {leaking}"
    )


def test_an_inseparable_conclusion_is_left_out_rather_than_leaked():
    """When the conclusion cannot be lifted out of the fact pattern, the example
    is lost and counted -- never shipped with the answer still in it."""
    # One sentence, carrying both the facts and the conclusion: nothing survives
    # the split, so there is no fact pattern to hand anybody.
    assert ex.split_conclusion(
        "X paid to replace the roof and must capitalize the amount."
    ) == ("", "")
    # And `build` routes that outcome into the counted exclusions rather than
    # letting the example through with empty facts.
    monkey = lambda _text: ("", "")
    real, ex.split_conclusion = ex.split_conclusion, monkey
    try:
        _, kept, dropped, _, _ = ex.build(XML, DESKS / "fixed-assets",
                                          today="2026-09-04")
    finally:
        ex.split_conclusion = real
    assert kept == [], "every example should have been lost to the split"
    assert any(why == "conclusion cannot be separated from the fact pattern"
               for _, why in dropped), "the exclusion was not counted by name"
