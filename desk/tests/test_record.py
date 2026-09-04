"""The record refuses to be half-read.

Every test here has a mutation twin: it changes the record so the check must go
red, and asserts that it does. Seven of this operation's check bugs produced
false passes, and a check that has only ever passed is not evidence.
"""
from __future__ import annotations

import sys

import pytest

import record
from conftest import DESKS, ROOT


# ── it loads at all ───────────────────────────────────────────────────────────

def test_fixed_assets_desk_loads(fixed_assets):
    assert fixed_assets.name == "fixed-assets"
    assert fixed_assets.sources, "a desk with no authority cannot answer anything"
    assert fixed_assets.problems, "a desk that cannot be scored is a claim"


def test_every_problem_cites_authority_the_desk_actually_holds(fixed_assets):
    """The scoreboard is worthless if its own answers cite nothing."""
    for p in fixed_assets.problems:
        assert fixed_assets.passage(p.citation) is not None, (
            f"problem {p.id} cites {p.citation!r}, which is not in extracted/"
        )


def test_stored_text_is_verbatim_from_the_authority(fixed_assets):
    """Every passage must state the conclusion its problem attributes to it.

    Matched through the classifier's spellings rather than against the answer
    string, because `answer` is a canonical LABEL covering four framings: the
    regulation writes "not required to be capitalized" where the label reads
    "not required to capitalize". Asserting the label literally passed only while
    the classifier knew two spellings, and it was that same two-spelling reading
    that recorded a wrong answer for § 1.263(a)-3(l)(3) Example 4.

    Over every problem, not `problems[0]` -- regenerating the set has already
    moved a different example into that slot once.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import extract_ecfr as ex
    assert fixed_assets.problems, "no problems; this would pass vacuously"
    for p in fixed_assets.problems:
        passage = fixed_assets.passage(p.citation)
        assert passage is not None, f"problem {p.id} has no stored authority"
        spellings = [rx for answer, rx in ex.CLASSIFY if answer == p.answer]
        assert spellings, f"{p.answer!r} is not an answer the classifier states"
        assert any(rx.search(passage.text) for rx in spellings), (
            f"problem {p.id} claims {p.answer!r}, and the stored authority for "
            f"{p.citation} says no such thing — one of the two is wrong"
        )


# ── it raises rather than defaulting ──────────────────────────────────────────

BASE = """## S1 · A source

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-04

**Citation prefix:** 26 CFR 1.263(a)-3
"""


def test_a_good_source_block_parses():
    """The control. Without it, every test below could pass for the wrong reason."""
    assert record.parse_sources(BASE)[0].tier == "primary"


@pytest.mark.parametrize("find,replace,expect", [
    ("**Tier:** primary", "**Tier:** important", "tier"),
    ("**Access:** public_fetch", "**Access:** curl", "access"),
    ("**May store:** full_text", "**May store:** sure", "may_store"),
    ("**Checked:** 2026-09-04", "**Checked:** last tuesday", "checked"),
])
def test_a_value_outside_the_vocabulary_is_an_error(find, replace, expect):
    with pytest.raises(record.RecordError, match=expect):
        record.parse_sources(BASE.replace(find, replace))


@pytest.mark.parametrize("line,label", [
    ("**Citation prefix:** 26 CFR 1.263(a)-3\n", "Citation prefix"),
])
def test_a_missing_required_field_is_an_error(line, label):
    with pytest.raises(record.RecordError, match=label):
        record.parse_sources(BASE.replace(line, ""))


def test_an_empty_record_is_an_error_not_an_empty_desk():
    with pytest.raises(record.RecordError, match="no sources"):
        record.parse_sources("# nothing here\n")
    with pytest.raises(record.RecordError, match="no problems"):
        record.parse_problems("# nothing here\n")


def test_a_passage_citing_an_unrecorded_source_is_an_error(tmp_path):
    """Authority with no recorded source cannot be verified, so it is refused."""
    d = tmp_path / "orphan"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** c\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "x.md").write_text(
        "## 26 CFR 1.263(a)-3(k)(7) Example 3\n\n"
        "**Source:** S9 · **Checked:** 2026-09-04\n\n> text\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="S9"):
        record.load(d)


def test_a_missing_desk_is_an_error(tmp_path):
    with pytest.raises(record.RecordError, match="no desk"):
        record.load(tmp_path / "nope")


def test_a_desk_without_problems_is_an_error(tmp_path):
    """A desk that cannot be scored is a claim, so it does not load."""
    d = tmp_path / "unscored"
    d.mkdir()
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    with pytest.raises(record.RecordError, match="PROBLEMS"):
        record.load(d)


# ── the vocabulary is closed on purpose ───────────────────────────────────────

def test_human_only_is_a_recognised_access_value():
    """FASB ASC needs it: a source the engine may cite and must never read."""
    assert "human_only" in record.ACCESS


def test_license_check_stores_nothing_by_being_the_strictest_default():
    assert record.MAY_STORE[-1] == "license_check"


def test_only_primary_authority_is_binding():
    """Tier 2 or 3 alone is somebody's reading, which is a position for the firm."""
    src = record.parse_sources(BASE)[0]
    assert src.binding
    for tier in ("secondary", "tertiary"):
        weaker = record.parse_sources(BASE.replace("primary", tier))[0]
        assert not weaker.binding


def test_human_only_sources_are_not_readable():
    src = record.parse_sources(BASE.replace("public_fetch", "human_only"))[0]
    assert not src.readable, "human_only is the absence of a fetch, not a stricter one"


def test_a_position_whose_citation_matches_no_source_is_refused_at_load(tmp_path):
    """It loaded clean and raised EngineError the first time anybody asked that
    exact question -- a record that reads as valid and detonates on use."""
    d = tmp_path / "typo"
    (d / "positions").mkdir(parents=True)
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** tertiary · **Access:** human_only · "
        "**May store:** license_check · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 360\n\n**Answer:** must capitalize\n\n"
        "**Facts:** f\n", encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · A position with a mistyped citation\n\n"
        "**Citation:** ACS 360-10 · **Recorded:** 2026-09-04\n\n"
        "**Position:** must capitalize\n\n"
        "**Ratified:** the firm, 4 September 2026\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="matches 0 recorded sources"):
        record.load(d)


def test_a_date_that_is_not_a_day_on_the_calendar_is_refused(tmp_path):
    """`2026-02-31` matched the shape regex, loaded clean, and then crashed
    `staleness.check` at `date.fromisoformat`. This parser's promise is that a
    malformed record fails while being READ; stopping at the digit layout keeps
    half of it."""
    with pytest.raises(record.RecordError, match="not a day on the calendar"):
        record.parse_sources(BASE.replace("2026-09-04", "2026-02-31"))
    # And a real leap day still loads, so the check is not just "reject 31".
    assert record.parse_sources(BASE.replace("2026-09-04", "2024-02-29"))


def test_the_same_source_id_defined_twice_is_refused(tmp_path):
    """A set hid the duplicate and `Desk.source()` takes the first match, so a
    passage's tier, access policy and storage permission changed by REORDERING
    two blocks -- with every test green, because the id was "known" either way."""
    d = tmp_path / "dup"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        BASE + "\n" + BASE.replace("**Tier:** primary", "**Tier:** tertiary"),
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1.263(a)-3(a)\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1.263(a)-3(a)\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n"
        "> text\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="more than once"):
        record.load(d)


def test_the_same_citation_stored_twice_is_refused(tmp_path):
    """Two extracted files defining one citation both load and `Desk.passage()`
    takes the first. Files are read sorted, so RENAMING one changes the source,
    tier and checked date behind an answer -- and a tier change can turn a served
    answer into `authority_permits_choice` with nothing in the diff to show it."""
    d = tmp_path / "twice"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1.263(a)-3(a)\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    body = ("## 26 CFR 1.263(a)-3(a)\n\n**Source:** S1 · "
            "**Checked:** 2026-09-04\n\n> text\n")
    (d / "extracted" / "a.md").write_text(body, encoding="utf-8")
    (d / "extracted" / "b.md").write_text(body, encoding="utf-8")
    with pytest.raises(record.RecordError, match="stored more than once"):
        record.load(d)
