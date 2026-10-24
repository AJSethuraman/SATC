"""One income-side phrase reaches a domain, and the ordinary nouns do not.

THE MEASURED INCIDENT, and only it. On the fourth question of the first live
close, 8 September 2026 — asked because the firm challenged Forge-Occam with two
words, *"Did you ask the desk?"*, about the largest figure in the books — the
desk reported ONE pair:

    "is an unexplained bank deposit taxable income?"  -> federal-tax (on `taxable`)
    "are unidentified deposits gross receipts?"       -> NOTHING

`taxable` was already in the vocabulary. `gross receipts` was not. So
`gross receipts` is added and that is the whole of the fix.

THE FIRST VERSION OF THIS FILE IS THE REASON THE SECOND EXISTS. It invented five
more sentences around that pair — *"is this deposit revenue?"*, *"is a customer
refund income to us?"*, *"are loan proceeds receipts?"*, *"is an owner
contribution income?"* — asserted that all of them must reach a domain, and the
vocabulary was widened by NINETEEN words until they passed. A review of that
commit measured what it cost: six plain bookkeeping questions all classified
`federal-tax`, with no straddle flagged, including *"does that go on the income
statement?"*.

**A test built from imagined phrasings is a specification nobody agreed to.**
The code obliged it, and the result pointed a balance-sheet question at IRS
authority — six hours after the firm said the opposite.

SO THE INVENTED SENTENCES ARE GONE, and their reaching nothing is now asserted
as CORRECT rather than treated as a hole. *"Is this deposit revenue?"* genuinely
straddles book and tax; no vocabulary can place it and guessing is the original
defect. `ask.consult_or_file` files a question that reaches no domain and the
firm is notified, which is what makes this narrow list safe.
"""
from __future__ import annotations

import domains


def _domain(q):
    v = domains.classify(q)
    return v.domain.name if v.domain else None


def test_the_pair_the_desk_actually_reported():
    assert _domain("is an unexplained bank deposit taxable income?") == "federal-tax"
    assert _domain("are unidentified deposits gross receipts?") == "federal-tax", (
        "the exact rephrasing the desk used to isolate the hole")


def test_the_phrase_is_matched_as_a_phrase_and_not_as_its_words():
    """`receipts` alone must not fire — the meals desk declares it meaning the
    paper you keep, which is the sense collision on the docket as M1."""
    assert _domain("did you keep the receipts?") is None


#: Plain bookkeeping. No tax treatment is being asked in any of them, and the
#: nineteen-word list answered every one from federal tax.
BOOK_ONLY = [
    "Should loan proceeds be recorded as revenue?",
    "how do we record sales in the books?",
    "which account does the customer refund go to?",
    "do we recognise revenue when the invoice is raised?",
    "does that go on the income statement?",
    "where does a shareholder contribution get posted?",
]


def test_the_ordinary_nouns_of_the_income_side_do_not_claim_a_book_question():
    wrong = [q for q in BOOK_ONLY if _domain(q) == "federal-tax"]
    assert not wrong, (
        "federal-tax has claimed a pure bookkeeping question, which is the "
        "failure DOMAINS.md exists to stop: " + "; ".join(wrong))


def test_expense_still_claims_a_book_question_and_that_is_recorded_not_fixed():
    """THE ONE THAT SURVIVED THE NARROWING, and it is not from that commit.

    *"is the owner draw recorded as an expense?"* still reaches `federal-tax`,
    firing on `expense` — which predates the income-side widening and is one of
    the words the deduction side is built on. It is the same generic-noun
    problem, in a word that cannot simply be dropped: removing `expense` guts
    the domain that has been working for weeks.

    Asserted as it stands rather than quietly fixed or quietly ignored, so the
    residue is visible and the firm decides. If `expense` is later qualified,
    this goes red and should be rewritten, not deleted.
    """
    assert _domain("is the owner draw recorded as an expense?") == "federal-tax"
