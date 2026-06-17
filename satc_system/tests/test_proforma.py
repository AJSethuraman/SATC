"""Tests for the data mart roll-forward/proforma and prior-vs-current comparison."""

from __future__ import annotations

from decimal import Decimal

from satc.fixtures import synthetic_mart
from satc.proforma import compare_years, flagged, roll_forward


def test_comparison_flags_swing_drop_and_dependents():
    mart = synthetic_mart()
    rows = compare_years(mart, client_id="SATC-001000", return_type="1040",
                         jurisdiction="US", prior_year=2023, current_year=2024)
    by_line = {(r.schedule, r.line_code): r for r in rows}

    # A 1099-INT present in 2023 and missing in 2024 must be flagged DROPPED.
    dropped = by_line[("SCH_B", "old_bank_int")]
    assert "DROPPED" in dropped.flag and dropped.severity == "flag"

    # Ordinary dividends appear new in 2024.
    new = by_line[("SCH_B", "dividends_ord")]
    assert "NEW" in new.flag

    # Dependents dropped 3 -> 2.
    deps = by_line[("1040", "dependents")]
    assert "DEPENDENTS" in deps.flag and deps.severity == "flag"

    # Interest fell 2,500 -> 1,200 (>10% and material) -> SWING flag.
    interest = by_line[("SCH_B", "interest")]
    assert "SWING" in interest.flag

    assert len(flagged(rows)) >= 3


def test_rollforward_carries_open_items_and_basis_into_next_year():
    mart = synthetic_mart()
    seeds = roll_forward(mart, from_year=2024, to_year=2025)

    s1000 = seeds["SATC-001000"]
    kinds = {cf.kind for cf in s1000.carryforwards}
    # Capital loss, charitable and state overpayment all carry into 2025.
    assert {"CAP_LOSS_LT", "CHARITABLE", "STATE_OVERPAYMENT_APPLIED"} <= kinds
    assert s1000.to_year == 2025

    # The S-corp's ending stock basis becomes next year's beginning basis.
    s2000 = seeds["SATC-002000"]
    assert s2000.owner_basis_beginning[0].beginning_balance == Decimal("8200")
    assert s2000.owner_basis_beginning[0].tax_year == 2025

    # The C-corp NOL carries forward.
    assert any(cf.kind == "NOL" for cf in seeds["SATC-004000"].carryforwards)
