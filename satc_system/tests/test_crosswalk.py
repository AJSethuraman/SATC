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
    """Two years, two answers -- which is all this test is about.

    2025 read 15000 until 6 September 2026. That was Rev. Proc. 2024-40's
    figure, superseded for TY2025 itself by P.L. 119-21 (OBBBA) in July 2025 and
    corrected here. The number changed; what this test asserts did not, and the
    two years still differ, which is the property being checked.

    The figures themselves are proved against the IRS in
    `test_the_2025_tables_are_enacted_law.py`, not here.
    """
    lib = _lib()
    assert lib.resolve(2024, "US").value("standard_deduction")["single"] == 14600
    assert lib.resolve(2025, "US").value("standard_deduction")["single"] == 15750


def test_2026_holds_enacted_law_and_its_one_gap_stays_a_gap():
    """2026.yaml was a TCJA-sunset fixture until 17 October 2026 and now holds
    the law as enacted (Rev. Proc. 2025-32). What it still does not hold is
    recorded as pending rather than guessed -- the property the old fixture
    existed to test."""
    us26 = _lib().resolve(2026, "US")
    assert us26.value("standard_deduction")["single"] == 16100
    assert us26.value("retirement_401k_elective_deferral") == 24500
    assert us26.param("mileage_business").is_pending
    assert [p.name for p in us26.gaps()] == ["mileage_business"]


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
