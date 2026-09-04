"""Staleness reports; it never gates. And it never calls a gap fresh.

A permanently-red check is worse than no check: after the third day nobody reads
it, and the next genuine failure hides behind it. This repository already had to
sideline one for exactly that reason.
"""
from __future__ import annotations

import pytest

import record
import staleness

BASE = ("## S1 · A source\n\n"
        "**Tier:** primary · **Access:** {access} · "
        "**May store:** full_text · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** X\n")


def desk(tmp_path, *, access="public_fetch", checked="2026-09-04", passage=True):
    d = tmp_path / "d"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE.format(access=access), encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** X 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    if passage:
        (d / "extracted" / "a.md").write_text(
            f"## X 1\n\n**Source:** S1 · **Checked:** {checked}\n\n> text\n",
            encoding="utf-8")
    return record.load(d)


def test_an_amendment_after_the_checked_date_is_flagged(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: "2026-09-05",
                        today="2026-09-06")
    assert len(r.amended) == 1
    assert "amended 2026-09-05" in r.amended[0].detail


def test_an_amendment_before_the_checked_date_is_not_flagged(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: "2026-01-01",
                        today="2026-09-06")
    assert r.amended == []
    assert r.fresh == 1


def test_age_is_a_separate_signal_from_amendment(tmp_path):
    """A source can change in ways no timestamp captures."""
    r = staleness.check(desk(tmp_path, checked="2020-01-01"),
                        lambda s: "2019-01-01", today="2026-09-06")
    assert r.amended == []
    assert len(r.aged) == 1


def test_a_source_that_could_not_be_reached_is_unchecked_not_fresh(tmp_path):
    """A clean result over a source nobody could open is the false pass this
    whole operation keeps being bitten by."""
    def boom(src):
        raise RuntimeError("403 from its own edge")

    r = staleness.check(desk(tmp_path), boom, today="2026-09-06")
    assert r.fresh == 0
    assert len(r.unchecked) == 1
    assert "403" in r.unchecked[0].detail


def test_a_human_only_source_is_reported_unchecked_and_never_fetched(tmp_path):
    """The engine never reaches for it, so only a person can confirm it."""
    called = []
    r = staleness.check(desk(tmp_path, access="human_only"),
                        lambda s: called.append(s) or "2026-09-05",
                        today="2026-09-06")
    assert called == [], "human_only must not be fetched even to check freshness"
    assert len(r.unchecked) == 1
    assert r.unchecked[0].why == "human_only"


def test_a_source_publishing_no_date_is_unchecked_not_fresh(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: None, today="2026-09-06")
    assert r.fresh == 0
    assert len(r.unchecked) == 1


def test_the_report_states_the_gap_in_its_own_list(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: None, today="2026-09-06")
    text = r.render()
    assert "NOT CHECKED: 1" in text, "a silent gap is not a finding"


def test_the_report_says_none_rather_than_omitting_an_empty_gap(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: "2026-01-01", today="2026-09-06")
    assert "NOT CHECKED: 0" in r.render()
    assert "(none)" in r.render(), (
        "a line that disappears when clean teaches a reader that its absence "
        "means nothing was checked"
    )


def test_findings_come_before_the_clean_count(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: "2026-09-05", today="2026-09-06")
    text = r.render()
    assert text.index("amended since checked") < text.index("fresh:")


def test_staleness_never_raises_on_a_finding(tmp_path):
    """It reports. Making it red would train people to ignore red."""
    r = staleness.check(desk(tmp_path, checked="2000-01-01"),
                        lambda s: "2026-09-05", today="2026-09-06")
    assert r.amended or r.aged
    assert isinstance(r.render(), str)


def test_every_entry_lands_in_exactly_one_bucket(tmp_path):
    r = staleness.check(desk(tmp_path), lambda s: "2026-01-01", today="2026-09-06")
    assert r.total == 1, "an entry was double-counted or vanished"


def test_a_source_is_asked_once_however_many_passages_cite_it(fixed_assets):
    """Called inside the passage loop, the shipped desk made one request per
    passage -- 31 identical calls to one government site. Beyond the rate limit
    it made the report non-deterministic: a call that failed where an earlier one
    succeeded put two passages of the SAME source in different buckets."""
    calls = []

    def amended_on(src):
        calls.append(src.id)
        return "2020-01-01"

    staleness.check(fixed_assets, amended_on, today="2026-09-04")
    assert len(fixed_assets.passages) > 1, "fixture cannot show the difference"
    assert calls == sorted(set(calls)), (
        f"asked {len(calls)} times for {len(set(calls))} sources: {calls[:5]}..."
    )


def test_a_desk_answering_only_through_positions_is_still_reported(tmp_path):
    """A `human_only` source has no stored text, so a desk built on one has NO
    passages -- and the loop ran zero times, reporting "0 entries checked" while
    the engine served those positions daily. Silence that reads as a clean bill
    is worse than no report at all."""
    d = tmp_path / "positions-only"
    (d / "positions").mkdir(parents=True)
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source we may not read\n\n"
        "**Tier:** tertiary · **Access:** human_only · "
        "**May store:** license_check · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 360-10\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · What we do here\n\n"
        "**Citation:** ASC 360-10 · **Recorded:** 2020-01-01\n\n"
        "**Position:** must capitalize\n\n"
        "**Ratified:** the firm, 1 January 2020\n", encoding="utf-8")
    desk = record.load(d)
    assert not desk.passages, "fixture must have no stored text"

    rep = staleness.check(desk, lambda src: "2026-01-01", today="2026-09-04")
    assert rep.total == 1, f"reported {rep.total} entries for a desk with one"
    assert any(f.citation == "ASC 360-10" for f in rep.unchecked), (
        f"the only authority this desk has went unmentioned: {rep.render()}"
    )
