"""Tests for PII masking helpers."""

from __future__ import annotations

from decimal import Decimal

from dea.masking import mask_ein, mask_ssn, mask_value


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def test_mask_ssn_handles_unformatted_and_formatted_inputs() -> None:
    unformatted = _id_from_parts("123", "45", "6789")
    formatted = "-".join(["123", "45", "6789"])

    assert mask_ssn(unformatted) == "***-**-6789"
    assert mask_ssn(formatted) == "***-**-6789"


def test_mask_ein_handles_unformatted_and_formatted_inputs() -> None:
    unformatted = _id_from_parts("12", "345", "6789")
    formatted = "-".join(["12", "3456789"])

    assert mask_ein(unformatted) == "**-***6789"
    assert mask_ein(formatted) == "**-***6789"


def test_mask_identifier_returns_empty_for_none_or_blank() -> None:
    assert mask_ssn(None) == ""
    assert mask_ssn("   ") == ""
    assert mask_ein(None) == ""
    assert mask_ein("\t") == ""


def test_short_malformed_identifiers_do_not_expose_input() -> None:
    short_value = "12"

    assert mask_ssn(short_value) == "***-**-****"
    assert mask_ein(short_value) == "**-*******"
    assert short_value not in mask_ssn(short_value)
    assert short_value not in mask_ein(short_value)


def test_mask_value_masks_ssn_and_ein_fields() -> None:
    ssn_value = _id_from_parts("123", "45", "6789")
    ein_value = _id_from_parts("12", "345", "6789")

    assert mask_value("taxpayer.ssn", ssn_value) == "***-**-6789"
    assert mask_value("w2.employer.ein", ein_value) == "**-***6789"


def test_mask_value_leaves_non_sensitive_values_readable() -> None:
    assert mask_value("taxpayer.first_name", "Alex") == "Alex"
    assert mask_value("w2.box_1_wages", Decimal("72000.00")) == "72000.00"
    assert mask_value("notes", None) == ""
