"""Learned paystub template ("training") tests."""

from __future__ import annotations

from satc.ingest.paystub_templates import (
    TemplateLibrary,
    apply_template,
    fingerprint,
    learn,
)
from satc.ingest.readers.paystub import (
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
)

STUB_A = ("Employer: Acme Corp\nPayroll by ADP\n"
          "Gross Pay            2,500.00    30,000.00\n"
          "Federal Income Tax     300.00     3,600.00\n"
          "Pay Frequency: Bi-Weekly\n")
# Same employer/layout, different pay period (different numbers).
STUB_B = ("Employer: Acme Corp\nPayroll by ADP\n"
          "Gross Pay            2,500.00    32,500.00\n"
          "Federal Income Tax     310.00     3,910.00\n"
          "Pay Frequency: Bi-Weekly\n")

CONFIRMED_A = {
    LABEL_GROSS_CURRENT: "2500.00", LABEL_GROSS_YTD: "30000.00",
    LABEL_FED_WH_CURRENT: "300.00", LABEL_FED_WH_YTD: "3600.00",
    LABEL_PAY_FREQUENCY: "biweekly",
}


def test_fingerprint_detects_provider_employer_layout():
    fp = fingerprint(STUB_A)
    assert fp.provider == "ADP"
    assert "acme" in fp.employer
    # Same layout, different dollar values -> same signature.
    assert fp.layout and fingerprint(STUB_B).layout == fp.layout


def test_learn_then_apply_reads_a_new_stub():
    template = learn(STUB_A, CONFIRMED_A)
    lf = apply_template(template, STUB_B).labeled_fields
    assert lf[LABEL_GROSS_CURRENT] == "2500.00"
    assert lf[LABEL_GROSS_YTD] == "32500.00"      # YTD column, B's value
    assert lf[LABEL_FED_WH_CURRENT] == "310.00"
    assert lf[LABEL_FED_WH_YTD] == "3910.00"
    assert not apply_template(template, STUB_B).uncertain_labels  # learned => trusted


def test_library_save_and_match(tmp_path):
    lib = TemplateLibrary(path=tmp_path / "templates.json")
    lib.save(learn(STUB_A, CONFIRMED_A))
    assert lib.match(STUB_B) is not None                  # same layout recognized
    assert lib.match("Net Pay   12.34\nMisc   1.00\n") is None  # unrelated layout
