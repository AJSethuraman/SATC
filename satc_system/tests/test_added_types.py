"""The six common forms the classifier did not know.

Measured on the adversarial corpus, 30 August 2026: a mortgage-interest 1098, a
1099-G state refund and an SSA-1099 all came back **Unclassified**. That is a
SAFE failure -- the classifier never guessed -- but not a harmless one: the file
lands in a folder, no request is closed, and nothing chases it. The packet reads
short for a reason nobody can see.

All six are added with ``key: null``, the established pattern for "a real
document we recognise but do not read figures off". They can close a request and
be filed by type; nothing tries to extract from them, because there is no
extraction map and inventing one would be guessing at box numbers.

1099-B earns its place twice over: it is the third form inside every consolidated
brokerage statement, so adding it also completes the "Several forms:" verdict
that previously named only DIV and INT.
"""

from __future__ import annotations

import pytest

from satc.ingest.classify import load_classifier


@pytest.mark.parametrize("label,text", [
    ("1098", "Form 1098\nMortgage Interest Statement\n"
             "RECIPIENT'S/LENDER'S name: Third Federal\n"
             "1 Mortgage interest received from payer(s)  11,402.19"),
    ("1099-G", "Form 1099-G\nCertain Government Payments\n"
               "Ohio Department of Taxation\n"
               "2 State or local income tax refunds  412.00"),
    ("SSA-1099", "SSA-1099  SOCIAL SECURITY BENEFIT STATEMENT\n2026\n"
                 "Box 5. Net Benefits for 2026   18,240.00"),
    ("1099-B", "Form 1099-B\nProceeds From Broker and Barter Exchange Transactions\n"
               "1d Proceeds  41,200.00"),
    ("1099-MISC", "Form 1099-MISC\nMiscellaneous Information\n"
                  "1 Rents  14,400.00"),
    ("W-2G", "Form W-2G\nCertain Gambling Winnings\n"
             "1 Reportable winnings  2,500.00"),
])
def test_the_form_is_recognised(label, text):
    got = load_classifier().classify_text(text)
    assert got is not None, f"{label} still unclassified"
    assert got.label == label, got


@pytest.mark.parametrize("label", ["1098", "1099-G", "SSA-1099", "1099-B",
                                   "1099-MISC", "W-2G"])
def test_none_of_them_claims_to_be_extractable(label):
    """No extraction map exists for these, and inventing one would be guessing
    at box numbers. They are filed, not read."""
    c = load_classifier()
    dt = next(d for d in c.doc_types if d.label == label)
    assert dt.key is None, f"{label} claims an extraction map it does not have"


def test_1098_is_not_confused_with_1098_t():
    """Tuition and mortgage interest are both "1098" and are not the same form."""
    tuition = ("Form 1098-T\nTuition Statement\n"
               "1 Payments received for qualified tuition  8,400.00")
    assert load_classifier().classify_text(tuition).label == "1098-T"


def test_a_consolidated_1099_now_names_the_1099_b_as_well():
    """The half of the money bug that adding types closes.

    Before 1099-B existed as a type the verdict read "Several forms: 1099-INT,
    1099-DIV" -- correct as far as it went, and silent about the proceeds that
    drive a Schedule D.
    """
    text = ("2026 CONSOLIDATED FORMS 1099\nCharles Schwab & Co., Inc.\n"
            "Summary of Form 1099-DIV     Total ordinary dividends  1,204.00\n"
            "Summary of Form 1099-INT     Interest income  88.10\n"
            "Summary of Form 1099-B       Proceeds from broker transactions  41,200.00")
    got = load_classifier().classify_text(text)
    assert got.multi, got
    assert "1099-B" in got.forms, got.forms
