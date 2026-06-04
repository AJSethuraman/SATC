"""Tests for input model construction and coercion."""

from __future__ import annotations

from decimal import Decimal

import pytest

from twe.models import EstimatorInput, to_decimal


def test_from_dict_minimal():
    inp = EstimatorInput.from_dict({
        "filing_status": "single",
        "paystub": {"pay_frequency": "weekly", "gross_pay_per_period": 1000},
    })
    assert inp.filing_status == "single"
    assert inp.paystub.gross_pay_per_period == Decimal("1000")
    assert inp.paystub.periods_per_year == 52


def test_from_dict_coerces_and_typed():
    inp = EstimatorInput.from_dict({
        "filing_status": "married_jointly",
        "paystub": {
            "pay_frequency": "biweekly",
            "gross_pay_per_period": "3200.50",
            "pay_periods_remaining": 10,
        },
        "other_income": {"interest": 100.10},
        "target_refund": 500,
    })
    assert inp.paystub.gross_pay_per_period == Decimal("3200.50")
    assert inp.paystub.pay_periods_remaining == 10
    assert inp.other_income.interest == Decimal("100.10")
    assert inp.target_refund == Decimal("500")


def test_from_dict_missing_filing_status():
    with pytest.raises(ValueError, match="filing_status is required"):
        EstimatorInput.from_dict({"paystub": {"pay_frequency": "weekly"}})


def test_from_dict_rejects_unknown_top_level_key():
    with pytest.raises(ValueError, match="unknown input keys"):
        EstimatorInput.from_dict({
            "filing_status": "single",
            "paystub": {"pay_frequency": "weekly"},
            "bogus": 1,
        })


def test_from_dict_rejects_unknown_nested_key():
    with pytest.raises(ValueError, match="unknown keys for OtherIncome"):
        EstimatorInput.from_dict({
            "filing_status": "single",
            "paystub": {"pay_frequency": "weekly"},
            "other_income": {"lottery": 5},
        })


def test_to_decimal_handles_none_and_float():
    assert to_decimal(None) == Decimal("0")
    assert to_decimal(0.1) == Decimal("0.1")  # str routing avoids float noise


def test_taxable_pay_per_period():
    inp = EstimatorInput.from_dict({
        "filing_status": "single",
        "paystub": {
            "pay_frequency": "monthly",
            "gross_pay_per_period": 5000,
            "retirement_pretax_per_period": 500,
            "other_pretax_per_period": 200,
        },
    })
    assert inp.paystub.taxable_pay_per_period == Decimal("4300")
