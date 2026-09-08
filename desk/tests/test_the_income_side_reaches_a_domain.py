"""The gate fires on the examiner's word and not the bookkeeper's.

FOUND ON THE FOURTH QUESTION OF THE FIRST CLOSE, 8 September 2026 — asked only
because the firm challenged Forge-Occam with two words, *"Did you ask the
desk?"*, about the largest figure in the books. It had classified unidentified
deposits as a client question and never tested that judgement.

`domain: None`, for the third time that night, on a question that asks WHETHER
SOMETHING IS GROSS RECEIPTS. The desk was careful that this is NOT the
past-participle hole — it could see that test in the checkout — but a different
hole in the same wall:

    "the NOUNS of the income side are missing where the verbs of the deduction
     side are present"

`taxable` is in the vocabulary. `gross receipts` is not. **The gate switches on
for the word an examiner would use and stays off for the word a bookkeeper
would use.** One rephrasing isolates it exactly:

    "is an unexplained bank deposit taxable income?"  -> federal-tax
    "are unidentified deposits gross receipts?"       -> NOTHING

WHY IT IS NOT COSMETIC. With no domain the wrong-body-of-authority gate does not
run, and the income side is exactly where book and tax diverge hardest: a
deposit is not gross receipts by virtue of being a deposit, and booking one to
sales overstates the income and the tax.
"""
from __future__ import annotations

import domains

#: Written the way a bookkeeper writes them, not the way a regulation does.
INCOME_SIDE = [
    "are unidentified deposits gross receipts?",
    "is this deposit revenue?",
    "does that count as gross income?",
    "is a customer refund income to us?",
    "are loan proceeds receipts?",
    "is an owner contribution income?",
]


def _domain(q):
    return domains.classify(q).domain


def test_the_income_side_reaches_a_domain():
    silent = [q for q in INCOME_SIDE if not _domain(q)]
    assert not silent, (
        "the income side of a close reaches no domain, so the wrong-body gate "
        "is not watching where book and tax diverge hardest: " + "; ".join(silent))


def test_the_pair_that_isolated_it():
    """The examiner's word already worked; the bookkeeper's did not."""
    assert _domain("is an unexplained bank deposit taxable income?")
    assert _domain("are unidentified deposits gross receipts?"), (
        "the exact rephrasing the desk used to isolate the hole")
