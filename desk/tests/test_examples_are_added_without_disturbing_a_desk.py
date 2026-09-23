"""`tools/add_examples.py` may only add. Everything else it must refuse.

WHY IT EXISTS AT ALL. `extract_ecfr.py` BUILDS a desk -- extracted authority and
`PROBLEMS.md`, which is the answer key. Exactly one file in this record was ever
written by it. Every other desk was assembled by hand, with problems a person
chose, so re-running the builder over one would overwrite that curation and print
"wrote 16 problems" while doing it.

So the additive tool exists, and its whole value is what it will not do. These
tests are about the refusals rather than the writing: a tool that adds authority
to a record is only safe while it cannot quietly change the rest of it.

NOTHING HERE REACHES THE NETWORK. `gather` fetches, and this desk's conftest
replaces the socket layer, so every refusal tested below is one that fires BEFORE
the fetch -- which is also the right place for all of them: a source we may not
copy from should never have been requested in the first place.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import add_examples                                          # noqa: E402
import record                                                # noqa: E402
from conftest import CORPUS                                  # noqa: E402

CAP = CORPUS


def _desk_with_source(**changes):
    """The corpus with one field of S1 altered."""
    import dataclasses
    desk = record.load(CAP)
    s1 = dataclasses.replace(desk.source("S1"), **changes)
    return dataclasses.replace(
        desk, sources=tuple(s1 if s.id == "S1" else s for s in desk.sources))


# ── the refusals, each before any fetch ──────────────────────────────────────

def test_a_source_we_may_not_fetch_is_refused():
    for access in ("human_only", "signed_in_browser", "headless_browser"):
        with pytest.raises(add_examples.Refused, match="not ours to fetch"):
            add_examples.gather(_desk_with_source(access=access), "S1", "2026-09-07")


def test_a_source_we_may_not_copy_from_is_refused():
    """`license_check` is the default and it stores nothing. A licence the firm
    holds may permit an internal copy, which is why this is a fact about the
    source rather than one policy over all of them."""
    for may in ("license_check", "citation_only"):
        with pytest.raises(add_examples.Refused, match="not ours to copy"):
            add_examples.gather(_desk_with_source(may_store=may), "S1", "2026-09-07")


def test_a_source_that_is_not_an_ecfr_section_is_refused():
    """The parser here reads eCFR's XML shape. An IRS publication is HTML and
    would parse to nothing, or worse to something."""
    with pytest.raises(add_examples.Refused, match="not an eCFR section"):
        add_examples.gather(_desk_with_source(url="https://www.irs.gov/publications/p583"),
                            "S1", "2026-09-07")


def test_the_date_must_be_a_date_and_is_never_defaulted():
    """The builder's rule, and for its reason: `checked` is a fact about the
    FETCH. Defaulted to the clock, a rebuild would restamp an old snapshot as
    freshly verified and silence the one signal designed to catch it."""
    with pytest.raises(ValueError):
        add_examples.add(CAP, "S1", "the seventh")


# ── it finds the right file, by reading rather than by convention ────────────

def test_the_source_s_own_file_is_found_by_reading_it(tmp_path):
    """The seven desks spelled these `S1.md`, `S1-treas-reg-1-274-12.md` and
    `treas-reg-1-263a-3.md`. A naming convention six records each have to
    remember is not a convention.

    THE THREE SPELLINGS ARE GONE AND THE PROPERTY IS NOT. `dec-kill` left one
    `extracted/authority.md`, so pointing this at the corpus would prove that a
    file called `authority.md` can be found — which is the naming convention
    back, and passing by luck. The three shapes are CONSTRUCTED instead, which
    is what the test always meant: the file is found by reading which source its
    passages name, whatever it is called.
    """
    for spelling in ("S1.md", "S1-treas-reg-1-274-12.md", "zzz-anything.md"):
        d = tmp_path / spelling
        (d / "extracted").mkdir(parents=True)
        (d / "extracted" / spelling).write_text(
            "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-07 · "
            "**Kind:** rule\n\n> a rule\n", encoding="utf-8")
        # AND A DECOY THAT SORTS FIRST, so "the first file" cannot pass.
        (d / "extracted" / "aaa-other.md").write_text(
            "## 26 CFR 9\n\n**Source:** S2 · **Checked:** 2026-09-07 · "
            "**Kind:** rule\n\n> another rule\n", encoding="utf-8")
        assert add_examples._file_holding(d, "S1").name == spelling

    # And on the real record, where there is now exactly one.
    assert add_examples._file_holding(CAP, "S1").name == "authority.md"


def test_a_source_held_in_no_file_is_refused_rather_than_guessed():
    with pytest.raises(add_examples.Refused, match="held in 0 files"):
        add_examples._file_holding(CAP, "S99")


# ── what it wrote, in the record it wrote it to ──────────────────────────────

def test_every_added_example_is_marked_and_cited_under_its_own_source():
    """Read off the committed record. An example filed under the wrong source
    would pass the desk's own load and be cited to another regulation."""
    for d in [CORPUS]:
        desk = record.load(d)
        for p in desk.passages:
            if p.kind != record.EXAMPLE:
                continue
            src = desk.source(p.source_id)
            assert record.from_source(p.citation, src.citation_prefix), (
                f"{d.name}: {p.citation!r} is filed under {src.id}, whose "
                f"citations begin {src.citation_prefix!r}")
            assert src.may_store == "full_text", (
                f"{d.name}: {p.citation!r} stores text from a source that does "
                f"not permit it")


def test_an_added_example_is_not_beneath_its_lead_in_as_a_paragraph():
    """`under()` must not read `(a)(1)(v) Example 1` as a finer PARAGRAPH of
    `(a)(1)(v)`. If it did, `unsupported.py` would file a model citing the
    example as a near miss on the rule, and the engine's containment logic
    would treat a worked example as a sub-rule of the paragraph it illustrates.
    """
    desk = record.load(CORPUS)
    example = "26 CFR 1.6041-1(a)(1)(v) Example 1"
    assert desk.passage(example).kind == record.EXAMPLE
    assert not record.under(example, "26 CFR 1.6041-1(a)(1)(v)")
    assert record.under("26 CFR 1.6041-1(a)(1)(v)", "26 CFR 1.6041-1(a)(1)")
