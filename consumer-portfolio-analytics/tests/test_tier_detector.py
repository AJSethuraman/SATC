"""Tier detector and degrade-function tests."""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    F_CREDIT_LIMIT,
    F_ORIGINAL_TERM_MONTHS,
    F_REMAINING_TERM_MONTHS,
    PANEL_REQUIREMENT,
    TIER1_ONLY_FIELDS,
    TIER2_ONLY_FIELDS,
)
from ucpa.generator import degrade_to_tier
from ucpa.products import CreditCardModule
from ucpa.tier_detector import detect_tier, is_monthly_panel

MODULE = CreditCardModule()


def test_full_tape_detected_tier2(small_tape: pd.DataFrame) -> None:
    result = detect_tier(small_tape, MODULE)
    assert result.detected_tier == 2
    assert result.is_panel
    assert result.missing_for_tier0 == []
    assert result.missing_for_next_tier == []


def test_degrade_to_tier1(small_tape: pd.DataFrame) -> None:
    t1 = degrade_to_tier(small_tape, 1)
    assert not (set(t1.columns) & TIER2_ONLY_FIELDS)
    result = detect_tier(t1, MODULE)
    assert result.detected_tier == 1
    assert result.is_panel
    # Missing-for-Tier-2 excludes term fields (not applicable to cards).
    expected = sorted(
        TIER2_ONLY_FIELDS - {F_ORIGINAL_TERM_MONTHS, F_REMAINING_TERM_MONTHS}
    )
    assert result.missing_for_next_tier == expected


def test_degrade_to_tier0_snapshot(small_tape: pd.DataFrame) -> None:
    t0 = degrade_to_tier(small_tape, 0)
    assert not (set(t0.columns) & (TIER1_ONLY_FIELDS | TIER2_ONLY_FIELDS))
    # One row per account: a snapshot, not a panel.
    assert t0.groupby("account_id").size().max() == 1
    assert not is_monthly_panel(t0)
    result = detect_tier(t0, MODULE)
    assert result.detected_tier == 0
    assert result.missing_for_tier0 == []
    assert PANEL_REQUIREMENT in result.missing_for_next_tier
    assert F_CREDIT_LIMIT in result.missing_for_next_tier


def test_degrade_does_not_mutate_input(small_tape: pd.DataFrame) -> None:
    before = small_tape.copy()
    degrade_to_tier(small_tape, 0)
    pd.testing.assert_frame_equal(small_tape, before)


def test_below_tier0_reported(small_tape: pd.DataFrame) -> None:
    broken = small_tape.drop(columns=["charge_off_flag"])
    result = detect_tier(broken, MODULE)
    assert result.detected_tier == 0
    assert result.missing_for_tier0 == ["charge_off_flag"]


def test_all_null_column_counts_as_missing(small_tape: pd.DataFrame) -> None:
    tape = small_tape.copy()
    tape["score_band"] = pd.NA
    result = detect_tier(tape, MODULE)
    assert result.detected_tier == 0  # Tier 1 needs a populated score band
    assert "score_band" in result.missing_for_next_tier
