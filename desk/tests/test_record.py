"""The record refuses to be half-read.

Every test here has a mutation twin: it changes the record so the check must go
red, and asserts that it does. Seven of this operation's check bugs produced
false passes, and a check that has only ever passed is not evidence.
"""
from __future__ import annotations

import pytest

import record
from conftest import DESKS


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
    """The passage must contain the conclusion the problem claims it states."""
    p = fixed_assets.problems[0]
    passage = fixed_assets.passage(p.citation)
    assert p.answer.casefold() in passage.text.casefold(), (
        "the stored authority does not contain the conclusion the problem "
        "attributes to it — one of the two was transcribed wrong"
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
