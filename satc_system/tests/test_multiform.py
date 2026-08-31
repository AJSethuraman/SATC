"""A document that is several forms must not answer as one of them.

Measured on an adversarial corpus, 30 August 2026. A consolidated brokerage 1099
-- one page carrying 1099-DIV, 1099-INT and 1099-B summaries, which is what every
Schwab/Fidelity/Vanguard client sends -- classified as **1099-INT**, alone, at
MEDIUM. Then:

    matching.matches("1099-INT", "Core income documents", <the bundle>)  -> True
    reconcile_received(...)                                             -> closes the task

So the request went to Received, the task completed, and the 1099-B proceeds --
$41,200 in the measured case -- were never asked for again. The packet reported
COMPLETE while a whole Schedule D was missing. That is a straight line from a
classifier nicety to a wrong return.

The classifier already had a notion for "I am unsure between two types": it
downgrades to MEDIUM. That is the wrong notion here. A consolidated 1099 is not
an uncertain single form, it is a certain several -- and those are different
facts. Conflating them is the same shape of bug as the reader ladder conflating
"no text to read" with "we could not read the text".
"""

from __future__ import annotations

import pytest

from satc.ingest.classify import load_classifier

CONSOLIDATED = """
2026 CONSOLIDATED FORMS 1099
Charles Schwab & Co., Inc.
Summary of Form 1099-DIV     Total ordinary dividends  1,204.00
Summary of Form 1099-INT     Interest income  88.10
Summary of Form 1099-B       Proceeds from broker transactions  41,200.00
"""

PLAIN_1099INT = """
Form 1099-INT
Interest Income
PAYER'S name: Heartland Bank
1 Interest income   412.55
"""


def test_a_consolidated_1099_is_reported_as_several_forms():
    c = load_classifier()
    got = c.classify_text(CONSOLIDATED)
    assert got is not None
    assert got.multi, f"expected several forms, got a single {got.label!r}"
    assert len(got.forms) >= 2, got


def test_it_names_the_forms_it_found():
    c = load_classifier()
    got = c.classify_text(CONSOLIDATED)
    found = set(got.forms)
    assert {"1099-DIV", "1099-INT"} <= found, found


def test_a_several_forms_verdict_carries_no_extraction_key():
    """Extracting a 3-form page with one form's map would mis-key every value.

    Asserted on the MECHANISM (`key is None`) rather than on `extractable`,
    because extractable is derived from it: a test that only checked the derived
    property would stay green if the mechanism were removed.
    """
    c = load_classifier()
    got = c.classify_text(CONSOLIDATED)
    assert got.key is None, got
    assert not got.extractable


def test_an_ordinary_single_form_is_untouched():
    c = load_classifier()
    got = c.classify_text(PLAIN_1099INT)
    assert got is not None
    assert got.label == "1099-INT"
    assert not got.multi
    assert got.forms == ()
    assert got.extractable


def test_the_verdict_says_so_in_words_a_preparer_reads():
    c = load_classifier()
    got = c.classify_text(CONSOLIDATED)
    assert "several" in got.label.lower() or "several" in got.evidence.lower(), got


# -- and the reason it matters: the request must stay open --------------------

def test_a_several_forms_document_cannot_close_a_request():
    """The whole point. A partial answer must not satisfy a bundle."""
    from satc.intake import matching

    c = load_classifier()
    got = c.classify_text(CONSOLIDATED)
    bundle = "Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B and any brokerage statements"

    # The old failure: the single label it picked sailed through matching.
    assert matching.matches("1099-INT", "Core income documents", bundle) is True

    # And the multi-form verdict must not -- refused at the seam, so a second
    # caller cannot reintroduce it. Note the composite label DOES contain the
    # form names and so would otherwise intersect the bundle's families.
    assert matching.is_multi(got.label)
    assert matching.matches(got.label, "Core income documents", bundle) is False, \
        f"{got.label!r} would still close the request"


# -- the false positive my own first fix introduced ---------------------------

MENTIONS_ANOTHER = """
Form W-2  Wage and Tax Statement
Employer: Buckeye Manufacturing LLC
1 Wages, tips, other compensation  64,500.00
Attach 1099-R if tax was withheld.
"""


def test_a_form_that_merely_mentions_another_is_still_one_form():
    """Found in my own first draft of this fix, before it shipped.

    The first rule was "any other type that clears its own threshold is a second
    form". On the real keyword weights a W-2 mentioning 1099-R scores 27 vs 9 --
    the 1099-R clears the floor of 6 easily -- so a plain W-2, one of the
    commonest documents there is, came back as "Several forms: W-2, 1099-R" and
    would then have closed no request at all.

    A form the document is ABOUT scores comparably to the winner (0.89-0.94 in
    the measured consolidated cases). A form it refers to does not (0.33).
    """
    c = load_classifier()
    got = c.classify_text(MENTIONS_ANOTHER)
    assert got.label == "W-2", got
    assert not got.multi, f"a passing mention made this multi-form: {got.forms}"
    assert got.extractable
