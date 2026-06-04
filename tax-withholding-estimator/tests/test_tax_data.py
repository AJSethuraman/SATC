"""Tests for tax-table loading."""

from __future__ import annotations

from decimal import Decimal

from twe.tax_data import available_years, load_tax_tables


def test_2025_is_available():
    assert 2025 in available_years()


def test_load_2025_values():
    tables, notes = load_tax_tables(2025)
    assert tables.tax_year == 2025
    assert notes == []
    assert tables.standard_deduction("single") == Decimal("15000")
    assert tables.standard_deduction("married_jointly") == Decimal("30000")
    assert tables.ss_wage_base == Decimal("176100")
    zero_top, fifteen_top = tables.capital_gains_thresholds("single")
    assert zero_top == Decimal("48350")
    assert fifteen_top == Decimal("533400")


def test_brackets_top_is_unbounded():
    tables, _ = load_tax_tables(2025)
    brackets = tables.ordinary_brackets("single")
    assert brackets[-1].up_to is None
    assert brackets[-1].rate == Decimal("0.37")


def test_none_year_uses_latest():
    tables, notes = load_tax_tables(None)
    assert tables.tax_year == available_years()[-1]
    assert any("latest available" in n for n in notes)


def test_missing_year_falls_back():
    tables, notes = load_tax_tables(1990)
    assert tables.tax_year == available_years()[-1]
    assert any("not bundled" in n for n in notes)
