"""Payments: the ledger, the reconciliation ladder, and the gate on rung 3."""

from datetime import date
from decimal import Decimal

import pytest

from satc.billing.invoice import BillingError, Invoice
from satc.billing.payment import (
    MatchBasis,
    Method,
    Payment,
    accept_choice,
    is_settled,
    merge,
    outstanding,
    overpaid_by,
    reconcile,
    settled_on,
)

ISSUED = date(2026, 4, 1)


def an_invoice(number: str, client: str = "CL-1", *, services=("return_1040",)) -> Invoice:
    inv = Invoice(invoice_id=number, client_id=client, tax_year=2025)
    for code in services:
        inv.add(code)
    return inv.issue(on=ISSUED)


def a_payment(amount, client="CL-1", *, reference="", when=date(2026, 4, 10),
              method=Method.CHECK) -> Payment:
    return Payment(client_id=client, amount=Decimal(str(amount)), received_on=when,
                   method=method, reference=reference)


# --- the ledger -------------------------------------------------------------

def test_a_part_payment_leaves_a_balance():
    inv = an_invoice("2026-0001")          # return_1040 = 450
    part = a_payment("200.00").against("2026-0001", MatchBasis.REFERENCE)
    assert outstanding(inv, [part]) == Decimal("250.00")
    assert not is_settled(inv, [part])


def test_the_settled_date_is_the_payment_that_cleared_it_not_the_first():
    inv = an_invoice("2026-0001")
    first = a_payment("200.00", when=date(2026, 4, 10)).against("2026-0001", MatchBasis.REFERENCE)
    rest = a_payment("250.00", when=date(2026, 6, 2)).against("2026-0001", MatchBasis.REFERENCE)
    assert settled_on(inv, [first, rest]) == date(2026, 6, 2)
    assert is_settled(inv, [first, rest])


def test_an_overpayment_is_surfaced_not_swallowed():
    inv = an_invoice("2026-0001")
    over = a_payment("500.00").against("2026-0001", MatchBasis.REFERENCE)
    # Outstanding never goes negative — a credit is not a debt we owe ourselves.
    assert outstanding(inv, [over]) == Decimal("0.00")
    assert overpaid_by(inv, [over]) == Decimal("50.00")


def test_the_same_deposit_recorded_twice_is_recorded_once():
    """The whole reason ids are derived from the payment itself."""
    one = a_payment("450.00", reference="check 1041")
    ledger, added = merge([], [one])
    assert len(added) == 1
    ledger, added = merge(ledger, [a_payment("450.00", reference="check 1041")])
    assert added == []
    assert len(ledger) == 1


def test_two_genuinely_different_payments_are_not_merged():
    ledger, _ = merge([], [a_payment("450.00", reference="check 1041"),
                           a_payment("450.00", reference="check 1042")])
    assert len(ledger) == 2


# --- rung 1: it told us -----------------------------------------------------

def test_a_referenced_payment_matches_with_nobody_deciding():
    inv = an_invoice("2026-0007")
    match = reconcile(a_payment("450.00", reference="Invoice 2026-0007"), [inv])
    assert match.basis is MatchBasis.REFERENCE
    assert match.invoice_id == "2026-0007"
    assert match.basis.is_automatic


def test_a_reference_that_overpays_that_invoice_does_not_spill_onto_another():
    """Attributing the excess elsewhere would credit work nobody agreed to."""
    small = an_invoice("2026-0007")                                  # 450
    other = an_invoice("2026-0008", services=("return_1040", "schedule_c"))
    match = reconcile(a_payment("725.00", reference="re 2026-0007"), [small, other])
    assert not match.is_resolved
    assert match.needs_a_decision
    assert "more than" in match.why


# --- rung 2: only one it could be ------------------------------------------

def test_an_unreferenced_payment_matching_one_balance_needs_no_judgment():
    inv = an_invoice("2026-0001")
    other = an_invoice("2026-0002", services=("return_1065",))       # 1250
    match = reconcile(a_payment("450.00"), [inv, other])
    assert match.basis is MatchBasis.SOLE_AMOUNT
    assert match.invoice_id == "2026-0001"


def test_a_settled_invoice_is_not_a_candidate():
    settled = an_invoice("2026-0001")
    paid = a_payment("450.00").against("2026-0001", MatchBasis.REFERENCE)
    twin = an_invoice("2026-0002")                                   # same amount
    match = reconcile(a_payment("450.00", when=date(2026, 5, 1)), [settled, twin], [paid])
    assert match.invoice_id == "2026-0002"


# --- rung 3: somebody has to choose ----------------------------------------

def test_two_identical_balances_are_not_guessed_between():
    a, b = an_invoice("2026-0001"), an_invoice("2026-0002")
    match = reconcile(a_payment("450.00"), [a, b])
    assert not match.is_resolved
    assert set(match.candidates) == {"2026-0001", "2026-0002"}
    assert match.why


def test_a_part_payment_with_no_reference_asks_rather_than_assumes():
    inv = an_invoice("2026-0001")
    match = reconcile(a_payment("100.00"), [inv])
    assert not match.is_resolved
    assert match.candidates == ("2026-0001",)
    assert "part payment" in match.why


def test_no_open_invoice_says_so_and_names_the_next_step():
    match = reconcile(a_payment("450.00", client="CL-9"), [an_invoice("2026-0001")])
    assert not match.is_resolved
    assert match.candidates == ()
    assert "not yet issued" in match.why


# --- the gate on rung 3 -----------------------------------------------------

def test_a_choice_from_the_shortlist_is_accepted_and_records_who_chose():
    a, b = an_invoice("2026-0001"), an_invoice("2026-0002")
    payment = a_payment("450.00")
    match = reconcile(payment, [a, b])
    chosen = accept_choice(payment, "2026-0002", match, by_model=True)
    assert chosen.invoice_id == "2026-0002"
    assert chosen.basis is MatchBasis.CHOSEN_BY_MODEL
    assert not chosen.basis.is_automatic       # provenance survives the decision


def test_an_invoice_that_was_never_offered_is_refused():
    """The model gets the same list the human does, and nothing else counts."""
    a, b = an_invoice("2026-0001"), an_invoice("2026-0002")
    payment = a_payment("450.00")
    match = reconcile(payment, [a, b])
    with pytest.raises(BillingError) as refusal:
        accept_choice(payment, "2026-9999", match, by_model=True)
    assert "2026-9999" in str(refusal.value)
    assert "2026-0001" in str(refusal.value)   # the refusal names the real options


def test_choosing_when_nothing_was_ambiguous_is_refused():
    inv = an_invoice("2026-0001")
    payment = a_payment("450.00", reference="2026-0001")
    match = reconcile(payment, [inv])          # resolved on rung 1
    with pytest.raises(BillingError):
        accept_choice(payment, "2026-0001", match, by_model=True)


def test_the_gate_would_actually_fail_if_it_stopped_checking():
    """Mutation check — principle 12.

    If ``accept_choice`` dropped its membership test, this is the call that
    would start succeeding. Asserting the refusal here means the test above is
    load-bearing rather than decorative.
    """
    payment = a_payment("450.00")
    match = reconcile(payment, [an_invoice("2026-0001"), an_invoice("2026-0002")])
    assert "2026-9999" not in match.candidates
    with pytest.raises(BillingError):
        accept_choice(payment, "2026-9999", match, by_model=False)
