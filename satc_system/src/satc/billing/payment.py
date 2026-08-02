"""Money arriving, and working out which invoice it was for.

An invoice's ``paid_on`` is one flag, and a flag cannot answer the questions a
practice actually has: *did they pay all of it?*, *when did the balance clear?*,
*have I already recorded this deposit?* So payments are **recorded facts** and
the paid state is **computed from them** — principles 2 and 3. The ledger is the
truth; the flag is a summary of it.

RECONCILIATION IS A LADDER, and the model is on the bottom rung only.

    1. The payment names the invoice and the amount reconciles.
       Nobody decides anything. This is nearly all card volume, because the pay
       link is per-invoice and carries the number with it.

    2. No reference, but the amount matches exactly ONE open invoice.
       Still nobody decides. One candidate is not a judgment call.

    3. Several candidates, or none that match exactly.
       NOW a human or a model picks — from the list of open invoices, which is
       finite and short. It returns an INVOICE ID, never an amount, and
       ``accept_choice`` refuses an id that was not among the candidates it was
       offered. Principle 6a: the model chooses from the same list the human
       gets, and the engine checks the answer.

What no rung does is move money. SATC records that money arrived; it never
collects it. Collection lives in the Invoicer project, which is internet-facing
and already carries Stripe. This machine holds the identity vault and stays off
the public network — principle 11 is not worth trading for a webhook endpoint.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from satc.billing.catalogue import _money
from satc.billing.invoice import BillingError, Invoice


class Method(str, Enum):
    """How the money arrived. Affects how much we can trust the reference."""

    CARD = "card"
    CHECK = "check"
    TRANSFER = "transfer"
    CASH = "cash"
    OTHER = "other"


class MatchBasis(str, Enum):
    """WHY we believe this payment belongs to this invoice.

    Kept on the payment because "how do we know" outlives "what we concluded" —
    principle 2. A year later, a match made by a model and a match made by the
    reference number are not the same fact, and the ledger should say which.
    """

    REFERENCE = "reference"          # rung 1 — it told us
    SOLE_AMOUNT = "sole_amount"      # rung 2 — only one it could be
    CHOSEN_BY_HUMAN = "chosen_by_human"
    CHOSEN_BY_MODEL = "chosen_by_model"
    UNMATCHED = "unmatched"

    @property
    def is_automatic(self) -> bool:
        return self in (MatchBasis.REFERENCE, MatchBasis.SOLE_AMOUNT)


def payment_id(*, client_id: str, amount: Decimal, received_on: date,
               method: Method | str, reference: str) -> str:
    """An id derived from what the payment IS, never from when we imported it.

    This is the whole defence against double-counting. Re-import the same bank
    export, replay the same webhook, paste the same deposit twice — it lands on
    the same id and merges instead of becoming a second payment. Principle 8.
    """
    raw = "|".join([
        client_id.strip().lower(),
        f"{_money(amount):.2f}",
        received_on.isoformat(),
        str(getattr(method, "value", method)),
        " ".join(reference.split()).lower(),
    ])
    return "pay_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Payment:
    """Money that arrived. A fact, not a decision."""

    client_id: str
    amount: Decimal
    received_on: date
    method: Method = Method.OTHER
    reference: str = ""
    """Whatever the rail gave us — a cheque number, a Stripe session, a memo
    line. Rung 1 reads the invoice number out of this when it is there."""

    invoice_id: str = ""
    basis: MatchBasis = MatchBasis.UNMATCHED
    note: str = ""

    @property
    def payment_id(self) -> str:
        return payment_id(client_id=self.client_id, amount=self.amount,
                          received_on=self.received_on, method=self.method,
                          reference=self.reference)

    @property
    def is_matched(self) -> bool:
        return bool(self.invoice_id) and self.basis is not MatchBasis.UNMATCHED

    def against(self, invoice_id: str, basis: MatchBasis) -> "Payment":
        """The same payment, now attributed. Frozen, so this returns a new one."""
        return Payment(client_id=self.client_id, amount=self.amount,
                       received_on=self.received_on, method=self.method,
                       reference=self.reference, invoice_id=invoice_id,
                       basis=basis, note=self.note)


# --- what an invoice is actually owed --------------------------------------

def paid_on_invoice(invoice: Invoice, payments) -> Decimal:
    """Sum of payments attributed to this invoice."""
    return _money(sum((p.amount for p in payments
                       if p.invoice_id == invoice.invoice_id), Decimal(0)))


def outstanding(invoice: Invoice, payments) -> Decimal:
    """What is still owed. Never negative — an overpayment is a credit, not a
    debt owed back to us, and pretending otherwise would corrupt every total
    that sums this."""
    balance = _money(invoice.total - paid_on_invoice(invoice, payments))
    return balance if balance > 0 else Decimal("0.00")


def overpaid_by(invoice: Invoice, payments) -> Decimal:
    """Anything paid beyond the total. Surfaced rather than swallowed — a
    client who overpaid is owed a conversation."""
    excess = _money(paid_on_invoice(invoice, payments) - invoice.total)
    return excess if excess > 0 else Decimal("0.00")


def is_settled(invoice: Invoice, payments) -> bool:
    return outstanding(invoice, payments) == 0


def settled_on(invoice: Invoice, payments) -> date | None:
    """The date the balance reached zero — the LAST payment that mattered.

    Computed, not stored. A part-payment in March and the rest in June means
    this invoice was settled in June, and no flag set in March can say that.
    """
    mine = sorted((p for p in payments if p.invoice_id == invoice.invoice_id),
                  key=lambda p: p.received_on)
    running = Decimal(0)
    for payment in mine:
        running = _money(running + payment.amount)
        if running >= invoice.total:
            return payment.received_on
    return None


# --- the ladder -------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Match:
    """What reconciliation concluded, and what it wants next."""

    basis: MatchBasis
    invoice_id: str = ""
    candidates: tuple[str, ...] = ()
    """The open invoices this could be. On rung 3 this is exactly the list a
    human or a model is allowed to pick from — nothing else is a valid answer."""

    why: str = ""

    @property
    def is_resolved(self) -> bool:
        return bool(self.invoice_id)

    @property
    def needs_a_decision(self) -> bool:
        return not self.is_resolved and bool(self.candidates)


def _open_for(client_id: str, invoices, payments) -> list[Invoice]:
    """Issued, not yet settled, belonging to this client."""
    return [inv for inv in invoices
            if inv.client_id == client_id and inv.is_issued
            and not is_settled(inv, payments)]


def reconcile(payment: Payment, invoices, payments=()) -> Match:
    """Work out which invoice a payment belongs to, deterministically.

    Returns a resolved Match on rungs 1 and 2. On rung 3 it returns the
    CANDIDATES and stops — deciding is somebody else's job, and this function
    will not guess between them. Principle 5.
    """
    candidates = _open_for(payment.client_id, invoices, payments)

    if not candidates:
        return Match(basis=MatchBasis.UNMATCHED, why=(
            f"No open invoice for {payment.client_id}. Either this is for an "
            f"invoice not yet issued, or it belongs to a different client."))

    # Rung 1 — the payment names an invoice, and the amount reconciles.
    named = [inv for inv in candidates
             if inv.invoice_id and inv.invoice_id in payment.reference]
    if len(named) == 1:
        invoice = named[0]
        owed = outstanding(invoice, payments)
        if payment.amount <= owed or payment.amount == invoice.total:
            return Match(basis=MatchBasis.REFERENCE, invoice_id=invoice.invoice_id,
                         why=f"Reference names invoice {invoice.invoice_id}.")
        # It named an invoice but paid more than is owed on it. Do NOT silently
        # spill the excess onto another invoice; that is how money ends up
        # attributed to work the client never agreed to.
        return Match(basis=MatchBasis.UNMATCHED,
                     candidates=tuple(i.invoice_id for i in candidates),
                     why=(f"Reference names {invoice.invoice_id}, but "
                          f"${payment.amount:,.2f} is more than the ${owed:,.2f} "
                          f"outstanding on it."))

    # Rung 2 — no reference, but only one open invoice matches the amount.
    exact = [inv for inv in candidates if outstanding(inv, payments) == payment.amount]
    if len(exact) == 1:
        invoice = exact[0]
        return Match(basis=MatchBasis.SOLE_AMOUNT, invoice_id=invoice.invoice_id,
                     why=(f"${payment.amount:,.2f} is the exact balance of "
                          f"{invoice.invoice_id}, and the only one it matches."))

    # Rung 3 — genuinely ambiguous. Hand over the shortlist, decide nothing.
    ids = tuple(inv.invoice_id for inv in candidates)
    if exact:
        why = (f"${payment.amount:,.2f} is the exact balance of {len(exact)} open "
               f"invoices. Which one did they mean?")
    else:
        why = (f"${payment.amount:,.2f} does not clear any single open invoice — "
               f"likely a part payment. Which invoice is it against?")
    return Match(basis=MatchBasis.UNMATCHED, candidates=ids, why=why)


def accept_choice(payment: Payment, invoice_id: str, match: Match, *,
                  by_model: bool) -> Payment:
    """Attribute a payment to an invoice somebody picked off the shortlist.

    The gate: the id must be one of the candidates that were OFFERED. A model
    that answers with an invoice it was not shown — a hallucinated number, a
    different client's invoice, last year's — is refused here rather than
    believed. This is what "the engine disposes" means when the model's job was
    to choose a row.
    """
    if not match.candidates:
        raise BillingError(
            "There was nothing to choose between. Reconcile the payment first, "
            "and only ask for a decision when it returns candidates.")
    if invoice_id not in match.candidates:
        raise BillingError(
            f"{invoice_id!r} was not one of the open invoices offered "
            f"({', '.join(match.candidates)}). A payment can only be attributed "
            f"to an invoice that is actually open for this client.")
    basis = MatchBasis.CHOSEN_BY_MODEL if by_model else MatchBasis.CHOSEN_BY_HUMAN
    return payment.against(invoice_id, basis)


def apply_to_invoice(invoice: Invoice, payments) -> Invoice:
    """Bring the invoice's ``paid_on`` into line with the ledger.

    The ledger is the truth; ``paid_on`` is a cached summary of it, kept
    because the queue, the overdue check and every existing screen read it. A
    part-paid invoice stays UNPAID here — it is still owed, and an overdue
    chase for the balance is the correct thing to surface.

    Idempotent: running it twice, or on an invoice already in step, changes
    nothing. Principle 8.
    """
    settled = settled_on(invoice, payments)
    if invoice.paid_on != settled:
        invoice.paid_on = settled
    return invoice


def apply_all(invoices, payments) -> list[Invoice]:
    """The same, across the book. Cheap enough to run on every page load, which
    is the point — a summary that can drift is a summary nobody can trust."""
    return [apply_to_invoice(inv, payments) for inv in invoices]


def merge(existing, arriving) -> tuple[list[Payment], list[Payment]]:
    """Fold new payments into the ledger, ignoring ones already recorded.

    Returns ``(ledger, newly_added)``. Re-importing the same bank export is a
    no-op rather than a duplicate, because the id is derived from the payment
    itself. Principle 8: "already recorded" is success, not a conflict.
    """
    ledger = list(existing)
    seen = {p.payment_id for p in ledger}
    added: list[Payment] = []
    for payment in arriving:
        if payment.payment_id in seen:
            continue
        seen.add(payment.payment_id)
        ledger.append(payment)
        added.append(payment)
    return ledger, added
