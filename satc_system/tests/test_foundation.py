"""Tests for stable keys, masking, and the identity-vault / data-mart split."""

from __future__ import annotations

import pytest

from satc.ids import (
    parse_return_key,
    return_key,
    validate_client_id,
    normalize_jurisdiction,
)
from satc.masking import last4, mask_ein, mask_ssn
from satc.models.identity import IdentityRecord, VaultAddress


def test_return_key_roundtrip():
    rk = return_key("SATC-001000", 2024, "1040", "oh")
    assert parse_return_key(rk) == ("SATC-001000", 2024, "1040", "OH")


def test_return_key_rejects_unknown_type():
    with pytest.raises(ValueError):
        return_key("SATC-001000", 2024, "1041", "US")


def test_jurisdiction_normalization():
    assert normalize_jurisdiction("federal") == "US"
    assert normalize_jurisdiction("fed") == "US"
    assert normalize_jurisdiction("mi") == "MI"


def test_client_id_convention():
    assert validate_client_id("SATC-001000")
    assert not validate_client_id("jane smith")


def test_masking_last4():
    assert mask_ssn("400-55-1234") == "***-**-1234"
    assert mask_ein("12-3456789") == "**-***6789"
    assert last4("400551234") == "1234"


def test_vault_to_public_strips_pii():
    rec = IdentityRecord(
        client_id="SATC-001000",
        entity_type="INDIVIDUAL",
        legal_name="Jane Q Synthetic",
        tin="400-55-1234",
        addresses=[VaultAddress(line1="1 Maple St", city="Columbus", state="OH", zip="43004")],
    )
    pub = rec.to_public()
    # The public projection must not expose the legal name or full TIN anywhere.
    assert "Synthetic" not in pub.display_label
    assert pub.tin_masked == "***-**-1234"
    assert pub.tin_last4 == "1234"
    assert pub.default_return_type == "1040"
    assert pub.home_state == "OH"
