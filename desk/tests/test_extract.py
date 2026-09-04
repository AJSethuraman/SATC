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

import re
import sys

import pytest

from conftest import DESKS, ROOT

sys.path.insert(0, str(ROOT / "tools"))
import extract_ecfr as ex          # noqa: E402

XML = ROOT / "tools" / "fixtures" / "1.263a-3.xml"


# ── ambiguity is never resolved into a guess ─────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("A owns a machine. Therefore, A must capitalize the amount paid.",
     "must capitalize"),
    ("A owns a machine. Therefore, A must be capitalized under (x).",
     "must capitalize"),
    ("A owns a machine. Accordingly, A is not required to capitalize it.",
     "not required to capitalize"),
    ("A owns a machine. Thus, the amounts are not required to be capitalized.",
     "not required to capitalize"),
])
def test_each_spelling_the_regulation_uses_is_read(text, expected):
    """Four framings, two answers. Knowing only two of the four is how an example
    concluding "must be capitalized" came to be recorded as NOT required to."""
    _, _, verdict = ex.split_conclusion(text)
    assert verdict == expected


def test_an_example_stating_both_conclusions_is_left_out_not_guessed():
    """The real § 1.263(a)-3(l)(3) Example 4 shape: a cleanup that is not an
    adaptation, and regrading that must be capitalized. Recording either one as
    THE answer scores a correct response as `wrongly_absorbed`."""
    both = ("B pays two amounts. Therefore, B is not required to capitalize the "
            "cleanup under paragraph (x). Accordingly, the regrading must be "
            "capitalized under paragraph (y).")
    facts, _, why = ex.split_conclusion(both)
    assert facts is None
    assert why == "states more than one conclusion"


def test_a_conclusion_must_be_announced_not_merely_mentioned():
    """The verbs appear all over the regulation -- in the rule being recited and
    in the taxpayer's own prior treatment. Only the sentence that ANNOUNCES the
    outcome decides it, which is what the connective marks."""
    facts, _, why = ex.split_conclusion(
        "C properly capitalizes its costs. Under paragraph (x) a taxpayer must "
        "capitalize an improvement. C pays an amount for work.")
    assert facts is None
    assert why == "states no conclusion this desk can score"


def test_an_example_stating_no_conclusion_is_left_out():
    facts, _, why = ex.split_conclusion("C owns a building. C pays for work.")
    assert facts is None
    assert why == "states no conclusion this desk can score"


def test_the_leak_vocabulary_can_never_be_narrower_than_the_classifier():
    """THE ONE CHECK THAT IS NOT CIRCULAR. Every earlier leak test asked the
    splitter's own vocabulary whether the splitter had leaked, so a phrasing the
    splitter did not know was invisible to both -- which is exactly how "must be
    capitalized" survived into a fact pattern after the leak was called fixed.

    `LEAKS` is deliberately wider than `CLASSIFY`, and this asserts the
    containment holds for every phrase the classifier can match. Erring wide
    costs an example; erring narrow costs the scoreboard its meaning."""
    for answer, rx in ex.CLASSIFY:
        sample = f"Therefore, the amount {rx.pattern}"
        probe = {
            r"\bmust capitaliz\w*": "Therefore, A must capitalize it.",
            r"\bmust be capitaliz\w*": "Therefore, it must be capitalized.",
            r"\bnot required to capitaliz\w*": "Therefore, A is not required to capitalize it.",
            r"\bnot required to be capitaliz\w*": "Therefore, it is not required to be capitalized.",
        }[rx.pattern]
        assert rx.search(probe), f"probe does not exercise {rx.pattern}"
        assert ex.LEAKS.search(probe), (
            f"{rx.pattern!r} is scorable but not treated as a leak: a fact "
            f"pattern could keep it and every leak check would pass"
        )


@pytest.mark.parametrize("text", [
    "Assume the same facts as in Example 1, except that...",
    "Assume the same facts as Example 25, except that...",
    "The same facts as Example 3 apply.",
    "The facts are the same as in Example 30, except that...",
])
def test_an_example_leaning_on_one_not_shown_is_left_out(text):
    """Three spellings. A filter written for only "same facts as in Example"
    missed a real case on this extractor's first run, because the regulation also
    says "same facts as Example" without the *in* -- and one written for both
    still missed "The facts are the same as in Example 30"."""
    assert ex.DEPENDENT.search(text)


def test_no_problem_in_the_record_leans_on_an_example_not_shown():
    """Asserted over what SHIPPED, not over the filter.

    The parametrized test above interrogates `DEPENDENT` directly, so deleting a
    spelling from it left every test green while a problem referring to facts
    nobody can see stayed in the denominator -- the helper checked, the caller
    unchecked, for the third time in this plugin's short life.
    """
    import record
    desk = record.load(DESKS / "fixed-assets")
    assert desk.problems, "no problems loaded; this would pass vacuously"
    leaning = [p.id for p in desk.problems
               if ex.DEPENDENT.search(p.facts)
               or re.search(r"(?:in|as) Example \d", p.facts)]
    assert not leaning, (
        f"{len(leaning)} problems rest on facts the desk was never given: "
        f"{leaning}"
    )


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
    leaking = [p.id for p in desk.problems if ex.LEAKS.search(p.facts)]
    assert not leaking, (
        f"{len(leaking)} problems state their own answer in the facts: {leaking}"
    )


def test_an_inseparable_conclusion_is_left_out_rather_than_leaked():
    """When the conclusion cannot be lifted out of the fact pattern, the example
    is lost and counted -- never shipped with the answer still in it."""
    # One sentence, carrying both the facts and the conclusion: nothing survives
    # the split, so there is no fact pattern to hand anybody.
    facts, _, why = ex.split_conclusion(
        "Therefore, X must capitalize the amount paid to replace the roof.")
    assert facts is None
    assert why == "conclusion cannot be separated from the facts"
    # And `build` routes that outcome into the counted exclusions rather than
    # letting the example through with empty facts.
    monkey = lambda _t: (None, None, "conclusion cannot be separated from the facts")
    real, ex.split_conclusion = ex.split_conclusion, monkey
    try:
        _, kept, dropped, _, _ = ex.build(XML, DESKS / "fixed-assets",
                                          today="2026-09-04")
    finally:
        ex.split_conclusion = real
    assert kept == [], "every example should have been lost to the split"
    assert any(why == "conclusion cannot be separated from the facts"
               for _, why in dropped), "the exclusion was not counted by name"
