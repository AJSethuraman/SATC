"""Tests for the dated, versioned tax-law crosswalk."""

from __future__ import annotations

from satc.crosswalk import CrosswalkLibrary


def _lib() -> CrosswalkLibrary:
    return CrosswalkLibrary().load()


def test_all_primary_jurisdictions_present_for_2024():
    avail = set(_lib().available())
    for juris in ("US", "OH", "MI", "MA"):
        assert (2024, juris) in avail


def test_federal_2024_values_in_force():
    us = _lib().resolve(2024, "US")
    assert us.value("standard_deduction")["mfj"] == 29200
    assert us.value("sec179_limit") == 1220000
    assert us.value("ss_wage_base") == 168600
    assert us.gaps() == []  # 2024 fully in force


def test_versioning_resolves_different_year_values():
    lib = _lib()
    assert lib.resolve(2024, "US").value("standard_deduction")["single"] == 14600
    assert lib.resolve(2025, "US").value("standard_deduction")["single"] == 15000


def test_tcja_sunset_fixture_flags_gaps_not_guesses():
    us26 = _lib().resolve(2026, "US")
    # The sunset fixture must NOT invent a 2026 standard deduction.
    assert us26.param("standard_deduction").is_pending
    # QBI deduction sunsets -> recorded as a gap, not a number.
    assert us26.param("qbi_threshold").is_gap
    # But published COLA items (401k) are in force.
    assert us26.value("retirement_401k_elective_deferral") == 24500
    # Several gaps should be reported.
    assert len(us26.gaps()) >= 5


def test_missing_year_returns_pending_param():
    us = _lib().resolve(2024, "US")
    p = us.param("does_not_exist")
    assert p.is_pending
    assert "pending" in p.pending_reason.lower()


def test_state_regimes_distinct():
    lib = _lib()
    assert lib.resolve(2024, "MI").value("flat_rate") == 0.0425
    assert lib.resolve(2024, "MA").value("part_b_rate") == 0.05
    assert lib.resolve(2024, "OH").value("brackets_nonbusiness")[0]["rate"] == 0.0
