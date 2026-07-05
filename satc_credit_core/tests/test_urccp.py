"""The shared URCCP resolver: floors hold, tightening allowed, loosening refused."""

import pytest

from satc_credit_core import URCCP_FLOORS, URCCPError, resolve_classification_dpd
from satc_credit_core import pii


def test_floors_are_the_interagency_standard():
    assert URCCP_FLOORS["closed_end"] == {"substandard_from_dpd": 90, "loss_from_dpd": 120}
    assert URCCP_FLOORS["open_end"] == {"substandard_from_dpd": 90, "loss_from_dpd": 180}


def test_default_resolves_to_the_floor():
    assert resolve_classification_dpd("closed_end") == {
        "substandard_from_dpd": 90, "loss_from_dpd": 120}
    assert resolve_classification_dpd("open_end") == {
        "substandard_from_dpd": 90, "loss_from_dpd": 180}


def test_bank_policy_may_tighten():
    # Charge off a closed-end loan at 90 instead of 120 — stricter, allowed.
    got = resolve_classification_dpd("closed_end", {"loss_from_dpd": 90})
    assert got["loss_from_dpd"] == 90


def test_loosening_is_refused():
    with pytest.raises(URCCPError, match="LOOSEN"):
        resolve_classification_dpd("closed_end", {"loss_from_dpd": 180})


def test_non_boundary_override_refused():
    with pytest.raises(URCCPError, match="boundary"):
        resolve_classification_dpd("open_end", {"substandard_from_dpd": 45})


def test_unknown_type_refused():
    with pytest.raises(URCCPError, match="unknown"):
        resolve_classification_dpd("revolving_widget")


def test_pii_scan_flags_tin_shapes():
    assert pii.find_tin("borrower 123-45-6789 here")      # SSN
    assert pii.find_tin("ein 12-3456789")                 # EIN
    assert not pii.find_tin("loan L-001 balance 100000")  # clean
    with pytest.raises(AssertionError):
        pii.assert_no_tin("ssn 123-45-6789")
