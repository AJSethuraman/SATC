"""Invoicing and payment screens (Flask blueprint) — raise a bill, record money in.

The billing engine (:mod:`satc.billing`) has been complete for a while and was
reachable only from Python, which meant the owner could not actually raise an
invoice. This is that screen, and nothing more: it gathers the owner's picks,
hands them to the engine, and shows what the engine says back.

Three things this module deliberately does NOT do:

* **It does not compute money.** Every figure on every page comes off an
  :class:`~satc.billing.invoice.Invoice` — ``standard_total``,
  ``discount_total``, ``total``, ``summary_block()``. A total formatted in Jinja
  from a number this file worked out would be a second opinion about a client's
  bill, and two opinions is one too many.
* **It does not phrase a refusal.** When ``issue()`` refuses a reduced plan with
  no recorded basis, that sentence — the one that explains why improvisation
  looks arbitrary when two clients compare notes — is what the owner reads. The
  view catches the error and renders its message; it never rewrites it, and it
  never lets it become a stack trace (principle 10).
* **It does not send.** Issuing fixes an invoice and writes it to the store. The
  covering email is still a separate, human act on the comms screen, and the
  print page is something the owner prints (principle 9).

A DRAFT LIVES IN THE SESSION. Half a bill is not a fact about the practice, so
it does not belong in the store; only ``issue()`` writes durably. The invoice
number is derived from what is already stored at the moment of issue, never held
in the draft, so two half-finished drafts can never be given the same number
(principle 8).

PAID IS NOT A FLAG. These screens used to write ``invoice.paid_on`` straight off
a form, which made "paid" something the owner asserted rather than something the
ledger computed. An assertion cannot tell a part payment from a settled bill,
cannot notice the same deposit entered twice, and cannot say WHEN the balance
actually cleared. So every payment screen here records a
:class:`~satc.billing.payment.Payment` — money arriving is the fact — and
``paid_on`` is brought into line from the ledger afterwards (principle 11b).

Routes:
  GET  /invoices                  - every invoice, plus what each client is into us for
  GET  /invoices/new              - build one from the catalogue
  POST /invoices/new              - set the header, add a line, drop a line, discard
  POST /invoices/<id>/issue       - fix it and write it down (or show why it refused)
  POST /invoices/<id>/paid        - record a payment against this invoice
  GET  /invoices/<id>             - the invoice as the client reads it, and its ledger
  GET  /invoices/<id>/print       - the same thing, printable, with nothing to click
  GET  /payments                  - the ledger, and the tray of unattributed money
  POST /payments/record           - money that did not arrive through an invoice screen
  POST /payments/<id>/match       - attribute one, off the shortlist reconciliation offered
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from satc.app.state import STATE, acting_actor
from satc.app.today_views import working_tax_year
from satc.billing import (
    BillingError,
    Invoice,
    billed_to_date,
    by_category,
    default_plan_key,
    next_invoice_number,
    plans,
    service,
)
from satc.billing.payment import (
    MatchBasis,
    Method,
    Payment,
    accept_choice,
    apply_to_invoice,
    merge,
    outstanding,
    overpaid_by,
    paid_on_invoice,
    reconcile,
    settled_on,
)
from satc.config import ConfigError
from satc.models.actor import ActorRefused, require_human
from satc.models.work import rate_plan_for

bp = Blueprint("billing", __name__)

# The half-built invoice, kept per browser session. See the module docstring:
# a draft is not yet a fact about the practice.
_DRAFT = "invoice_draft"

# The number THIS session last issued. Held only so a re-submitted issue form
# can be recognised as the same request arriving twice; see
# ``_is_the_same_invoice``.
_LAST_ISSUED = "invoice_last_issued"

# What a refusal from this file tells the owner to do instead. The actor gate is
# unreachable from a live browser request by construction, so this only ever
# fires from a script or a future tool path — and those get told where the
# decision actually lives.
_ISSUE_INSTEAD = ("open Invoices in the local app and issue it there — an invoice "
                  "is the practice's own act and a person has to make it")

# The earliest year this practice could be billing for. A tax year is not free
# text: ``billed_to_date`` groups by it, so a year that is merely *accepted*
# rather than *checked* puts the invoice in a different season's running total,
# where nobody looking for it will find it.
_EARLIEST_TAX_YEAR = 2000

# How each way of arriving reads on screen. The engine hands back a KEY from a
# finite set and this looks up the words — the same rule the model answers to
# (principle 6a), applied to the view so no screen can invent a sixth method.
_METHOD_LABEL = {
    Method.CARD: "Card",
    Method.CHECK: "Check",
    Method.TRANSFER: "Bank transfer",
    Method.CASH: "Cash",
    Method.OTHER: "Other",
}

# WHY we believe a payment belongs to an invoice, in the owner's words. These
# must not read alike: a payment the reference NAMED and a payment a model
# picked are different facts, and a screen that renders both as "matched" throws
# away the only thing that tells them apart a year later.
_HOW_MATCHED = {
    MatchBasis.REFERENCE: "The payment named the invoice",
    MatchBasis.SOLE_AMOUNT: "The only open invoice that amount could clear",
    MatchBasis.CHOSEN_BY_HUMAN: "You picked the invoice",
    MatchBasis.CHOSEN_BY_MODEL: "A model picked the invoice — worth a look",
    MatchBasis.UNMATCHED: "Not attributed to an invoice yet",
}


# --- the ledger ---------------------------------------------------------------
#
# Everything below goes through the store's payment seam —
# ``save_payments(payments)`` / ``load_payments(client_id="")`` — and never
# through ``invoice.paid_on``. Money arriving is recorded once; the paid state
# is recomputed from it (principle 11b).


def _ledger(client_id: str = "") -> list[Payment]:
    """Every payment recorded — for one client, or the whole book."""
    return list(STATE.store.load_payments(client_id))


def _record(payments) -> list[Payment]:
    """Fold payments into the ledger, and say which ones were actually NEW.

    The same deposit pasted twice, or a form re-submitted, lands on the same
    ``payment_id`` and is dropped rather than counted twice (principle 8). The
    return value is what makes that visible: the caller can tell the owner
    "already recorded" instead of silently doing nothing.
    """
    _, added = merge(_ledger(), payments)
    if added:
        STATE.store.save_payments(added)
    return added


def _settle(invoice: Invoice, ledger) -> Invoice:
    """Bring an invoice's ``paid_on`` into line with the ledger, and store it.

    ``paid_on`` is a cached SUMMARY of the payments, kept because the queue, the
    overdue check and the client's copy all read it. It is never the fact — a
    part payment leaves it None and the invoice correctly still owed.
    """
    before = invoice.paid_on
    apply_to_invoice(invoice, ledger)

    # NEVER ERASE A PRE-LEDGER PAID DATE. An invoice settled before payments
    # were recorded facts carries paid_on and no rows. Record a PART payment
    # against it and the ledger's answer is "not settled" — so this used to
    # overwrite a real record of full payment with None, and the client's copy
    # silently stopped saying "paid in full".
    #
    # Two records disagree, and neither is a stale flag: one is coarse, one is
    # detailed, and only a human knows which is right. So the coarse one is KEPT
    # and the disagreement is surfaced (principles 2 and 5) rather than resolved
    # by whichever code ran last.
    if before is not None and invoice.paid_on is None:
        invoice.paid_on = before
        return invoice

    if invoice.paid_on != before:
        STATE.store.save_invoices([invoice])
    return invoice


def _records_disagree(invoice: Invoice, ledger) -> str:
    """The sentence to show when the flag and the ledger cannot both be right."""
    if invoice.paid_on is None:
        return ""
    owed = outstanding(invoice, ledger)
    if owed <= 0:
        return ""
    return (f"Two records of this invoice disagree. It is marked paid on "
            f"{invoice.paid_on:%B %d, %Y} — a record made before payments were "
            f"itemised — but the payments now on the ledger leave "
            f"${owed:,.2f} outstanding. SATC will not pick between them: if the "
            f"older record is right, the missing payments have not been entered; "
            f"if the ledger is right, this was never settled in full.")


def _in_step(invoices, ledger) -> list[Invoice]:
    """Every invoice whose paid state the ledger can answer, brought into line.

    This is ``apply_all`` with one thing held back. ``apply_to_invoice`` sets
    ``paid_on`` to whatever the ledger says, and what an EMPTY ledger says is
    None — so running it across the book quietly erases the paid date of any
    invoice settled before payments were recorded facts. That is the pre-ledger
    record described below, and it is a fact, not a stale flag. An invoice the
    ledger has never heard of is therefore left exactly as it was found.

    The corrected flag is written back rather than only computed for the page,
    because ``paid_on`` is what the queue and the overdue check read, and a
    summary that is right on one screen and stale on the next is worse than no
    summary. Idempotent: nothing is written when nothing moved (principle 8).
    """
    known = {p.invoice_id for p in ledger if p.invoice_id}
    for invoice in invoices:
        if invoice.invoice_id in known:
            _settle(invoice, ledger)
    return list(invoices)


# --- what KIND of record says an invoice is paid ------------------------------
#
# Two different facts can answer "was this paid", and they are not the same fact.
#
#   LEDGER      Payments are recorded against it. How much arrived, when the
#               balance cleared, whether they overpaid — every figure is
#               COMPUTED, and the invoice can be asked any of those questions.
#
#   PRE-LEDGER  ``paid_on`` is set and no payment is recorded against it. This
#               is the flag the old screens wrote, before money arriving was a
#               fact of its own. It says THE BILL WAS SETTLED, ON THAT DAY, and
#               it cannot say how much arrived, in how many parts, or by what
#               rail. Coarse — but recorded, and the practice has nothing else.
#
# Recomputing the second from an empty ledger is how an invoice paid two years
# ago came back fully unpaid on its own page while the printed copy silently
# dropped "Paid in full": data loss, in the client's favour, on the one piece of
# paper that must never be wrong. So the coarse record is KEPT — and every
# screen says which of the two it is showing, because a summary and a
# computation that read identically are indistinguishable exactly when it
# matters (principle 4's rule about two kinds of thing, pointed at money).
#
# Where the ledger has anything at all to say, it wins: it is the finer record,
# and principle 11b is not negotiable once the facts exist.

LEDGER = "ledger"
PRE_LEDGER = "pre_ledger"
NOTHING = "nothing"

# How each reads on screen. A key from a finite set, words looked up here — the
# same rule the method picker answers to.
RECORD_LABEL = {
    LEDGER: "computed from the payment ledger",
    PRE_LEDGER: "recorded before the payment ledger existed",
    NOTHING: "nothing recorded",
}

_ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class _Money:
    """What is known about one invoice's money, and HOW it is known.

    Built once per invoice and handed to the templates whole, so the list, the
    invoice page and the printed copy cannot answer the same question
    differently — which is precisely what happened while each screen reached
    for whichever of ``paid_on`` and the ledger was nearest.
    """

    record: str
    paid: Decimal
    owed: Decimal
    over: Decimal
    settled: date | None
    payments: tuple

    @property
    def from_ledger(self) -> bool:
        return self.record == LEDGER

    @property
    def pre_ledger(self) -> bool:
        return self.record == PRE_LEDGER

    @property
    def is_settled(self) -> bool:
        """Nothing is owed AND something is actually recorded as having paid it.

        A nil invoice owes nothing either; that is not the same as settled, and
        the free-plan branch on the invoice page is what says so."""
        return self.owed == 0 and self.record != NOTHING

    @property
    def part_paid(self) -> bool:
        return self.owed > 0 and self.paid > 0

    @property
    def how_we_know(self) -> str:
        return RECORD_LABEL[self.record]


def _money_state(invoice: Invoice, ledger) -> _Money:
    """The paid state of one invoice, and which kind of record it rests on.

    The single place any screen asks. Ledger first, because it is the finer
    record; the coarse flag only answers where the ledger is silent about this
    invoice, and it is returned LABELLED rather than laundered into a figure
    that looks computed.

    This is the same rule ``actions.propose.balance_owed`` already applies when
    it decides whether to chase — ledger where the ledger has anything to say,
    ``paid_on`` as the fallback and never as a veto. Deliberately identical: the
    queue not chasing an invoice while the invoice screen shows it unpaid is the
    same fact answered two ways, and two answers is one too many.
    """
    mine = tuple(sorted((p for p in ledger if p.invoice_id == invoice.invoice_id),
                        key=lambda p: (p.received_on, p.payment_id), reverse=True))
    if mine:
        apply_to_invoice(invoice, ledger)
        return _Money(record=LEDGER, paid=paid_on_invoice(invoice, ledger),
                      owed=outstanding(invoice, ledger),
                      over=overpaid_by(invoice, ledger),
                      settled=settled_on(invoice, ledger), payments=mine)
    if invoice.paid_on is not None:
        # The flag is read, never recomputed — and never overwritten. What it
        # says is "this bill was settled on this day", which is the meaning the
        # screens that wrote it gave it and the meaning ``billed_to_date`` has
        # always read out of it. Taking the total as the amount is reading that
        # record, not inventing one; what would be an invention is presenting it
        # as though the ledger had produced it, which is why nothing renders it
        # without ``how_we_know`` alongside.
        return _Money(record=PRE_LEDGER, paid=invoice.total, owed=_ZERO,
                      over=_ZERO, settled=invoice.paid_on, payments=())
    return _Money(record=NOTHING, paid=_ZERO, owed=outstanding(invoice, ledger),
                  over=_ZERO, settled=None, payments=())


def _reconcilable(invoices, ledger) -> list[Invoice]:
    """The invoices reconciliation is allowed to consider.

    ``_open_for`` in the engine asks whether an invoice is settled, and that is
    a LEDGER question: an invoice recorded paid before the ledger existed has no
    payments against it, so it reads as wide open and gets put forward as a
    candidate for the next deposit that walks in. Offering to attribute money to
    a bill already recorded as settled is how one fee ends up collected twice on
    paper, so the coarse record is honoured and those invoices are not offered.

    Held back from the CANDIDATE LIST only. They stay on every screen, and
    nothing here hides a payment.
    """
    return [i for i in invoices if not _money_state(i, ledger).pre_ledger]


def _sum(amounts) -> Decimal:
    """Add money that is already money.

    Every figure fed in here came out of ``_money()`` in the engine, so it is
    already exact to the cent and this cannot round anything — which is the only
    reason a view is allowed to add at all. It never derives an amount; it
    totals ones the engine struck.
    """
    return sum(amounts, _ZERO)


# --- the draft ----------------------------------------------------------------

def _draft() -> dict:
    """The session's half-built invoice (an empty dict when there isn't one)."""
    return session.get(_DRAFT) or {}


def _save_draft(draft: dict) -> None:
    session[_DRAFT] = draft
    session.modified = True


def _working_year() -> int:
    """The tax year the practice is on — the same one Today works from.

    Shared rather than re-derived so the two screens cannot disagree about which
    year the owner is in the middle of (principle 3: computed, never stored).
    """
    rows = list(STATE.received_documents()) + list(STATE.requested_items())
    return working_tax_year(rows, date.today())


def _next_number() -> str:
    """The number this draft would be issued under, derived from what exists."""
    return next_invoice_number(STATE.store.load_invoices(), year=date.today().year)


def _invoice_from(draft: dict, *, invoice_id: str) -> Invoice:
    """Rebuild the engine's Invoice from the session draft.

    Every line goes back through :meth:`Invoice.add`, so the draft cannot hold a
    line the engine would not accept — a quantity on a fixed-price service, say.
    Raises whatever the engine raises; the callers turn that into a message.
    """
    inv = Invoice(
        invoice_id=invoice_id,
        client_id=draft.get("client_id", ""),
        tax_year=int(draft.get("tax_year") or _working_year()),
        plan_key=draft.get("plan_key") or default_plan_key(),
        plan_basis=draft.get("plan_basis", ""))
    for row in draft.get("lines", []):
        override = (row.get("rate_override") or "").strip()
        inv.add(row.get("service_code", ""),
                quantity=row.get("quantity") or "1",
                note=row.get("note", ""),
                rate_override=Decimal(override) if override else None)
    return inv


def _priced(invoice: Invoice) -> Invoice:
    """The same invoice, having proved it can state its own money.

    Building a line and pricing it are two different moments: a rate or a
    quantity that is not a real number survives ``add`` and only raises when
    ``quantize`` is reached, which in a template is a 500 rather than a
    sentence. Taking the totals here moves that moment inside a ``try``.
    """
    _ = (invoice.standard_total, invoice.discount_total, invoice.total)
    return invoice


# --- reading the form ---------------------------------------------------------

def _a_tax_year(raw: str) -> tuple[int | None, str]:
    """Parse the tax year, refusing rather than quietly using the working one.

    Substituting the working year for anything unreadable is the failure this
    screen can least afford: the owner reads back the year they typed nowhere,
    the invoice files itself under a season they did not choose, and the running
    total that is supposed to save them reconstructing the year from memory is
    the thing that is wrong (principles 1 and 5).
    """
    text = (raw or "").strip()
    if not text:
        return _working_year(), ""
    latest = date.today().year + 1
    if not (text.isdigit() and _EARLIEST_TAX_YEAR <= int(text) <= latest):
        return None, (f"{text!r} is not a tax year. Write four digits between "
                      f"{_EARLIEST_TAX_YEAR} and {latest} — what a client has been "
                      f"billed to date is grouped by this, so a year that is nearly "
                      f"right puts the invoice somewhere nobody will look for it.")
    return int(text), ""


def _plan_on_file(client_id: str, tax_year: int):
    """What this client is on for the year, and whether anybody actually decided.

    The invoice screen must not present the practice default as though it were
    an agreement. :func:`~satc.models.work.rate_plan_for` answers for every
    client, including one nobody has priced, and says WHICH it is doing — that
    distinction is the whole reason the screen asks it instead of reaching for
    ``default_plan_key()`` (principle 2: an unanswered question is not an answer).
    """
    return rate_plan_for(STATE.mart.engagements, client_id=client_id,
                         tax_year=tax_year)


def _set_header(draft: dict, form) -> str:
    """Who the invoice is for, which year, and what they pay relative to standard.

    Everything is read and checked BEFORE anything is written to the draft: a
    refused year must leave the year that was already there alone, rather than
    half-applying the form it just declined.
    """
    year, problem = _a_tax_year(form.get("tax_year", ""))
    if problem:
        return problem
    client_id = (form.get("client_id") or "").strip()
    key = (form.get("plan_key") or "").strip() or default_plan_key()
    basis = " ".join((form.get("plan_basis") or "").split())

    # The plan picker was drawn for whoever was selected when the page was
    # rendered. If the owner has now changed the client and left the picker
    # alone, what it shows was never a decision about THIS client — so take the
    # plan their engagement actually agreed rather than carrying the previous
    # client's across. ``plan_shown`` is what the picker was rendered with, so
    # "the owner touched it" is a recorded fact rather than a guess.
    if key == (form.get("plan_shown") or "").strip() \
            and client_id != (draft.get("client_id") or ""):
        on_file = _plan_on_file(client_id, year)
        key = on_file.plan_key
        basis = basis or on_file.basis

    if key not in plans():
        return (f"There is no rate plan called {key!r}. Pick one of: "
                f"{', '.join(sorted(plans()))}.")
    draft["client_id"] = client_id
    draft["tax_year"] = year
    draft["plan_key"] = key
    draft["plan_basis"] = basis
    _save_draft(draft)
    return ""


_NOT_AN_AMOUNT = ("Write what the work was worth as a plain number, like 400 or "
                  "400.00 — or leave it blank to bill the catalogue rate.")


def _an_override(raw: str, code: str, note: str) -> tuple[Decimal | None, str]:
    """Parse ``rate_override``, and hold it to the same rule a reduced plan is.

    An override changes what the work was WORTH, which is an honest thing to
    record — but only in one direction without saying why. Billing above the
    catalogue is the work genuinely being worth more, and the client can see the
    number they are being asked for. Billing BELOW it is a discount by another
    name: it shows up nowhere in ``shows_a_discount``, nowhere in
    ``plan_basis``, and reaches the client as nothing but a smaller number. That
    is exactly the improvisation the engine refuses on a reduced plan, so it is
    refused here on the same terms and recorded in the same way — as a reason,
    written down, on the line itself.
    """
    text = (raw or "").strip()
    if not text:
        return None, ""
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None, f"{text!r} is not an amount. {_NOT_AN_AMOUNT}"
    # Decimal() is happy to hand back NaN and Infinity. Money is not: they pass
    # every guard written as a comparison (NaN fails them all) and then blow up
    # in `quantize` when a total is finally taken — which is a 500 on a page,
    # not a refusal.
    if not amount.is_finite():
        return None, f"{text!r} is not an amount. {_NOT_AN_AMOUNT}"
    if amount < 0:
        return None, (f"{amount:,.2f} is not something a client can be billed. A "
                      f"negative invoice is not a credit note — if money is owed "
                      f"back, that is a separate act, not a line on this bill.")

    standard = service(code).standard_rate      # ConfigError for an unknown code
    if amount < standard and not note:
        return None, (f"Billing this at {amount:,.2f} when it is worth {standard:,.2f} "
                      f"is a reduction, and it needs a recorded reason before it can "
                      f"go on the invoice. Write on the line why the work was worth "
                      f"less — a reduced rate with no basis is improvisation, and "
                      f"improvisation is what looks arbitrary when two clients "
                      f"compare notes.")
    return amount, ""


def _a_quantity(raw: str) -> tuple[str, str]:
    """Parse ``quantity`` far enough to know it is a number at all.

    How many is too many, and what is fixed-price, stay the engine's business.
    This only catches the values ``Decimal`` accepts and arithmetic then chokes
    on, so the owner reads a sentence instead of ``[<class
    'decimal.InvalidOperation'>]``.
    """
    text = (raw or "1").strip() or "1"
    try:
        qty = Decimal(text)
    except InvalidOperation:
        qty = None
    if qty is None or not qty.is_finite():
        return "", (f"{text!r} is not a quantity. Write how many as a plain number, "
                    f"like 1 or 2 — three rentals is three Schedule Es.")
    return text, ""


def _add_line(draft: dict, form) -> str:
    """Put one catalogue service on the draft, or say why it can't go on.

    The service arrives as a CODE picked from the catalogue — there is no field
    anywhere on this screen that types a service name, for the same reason the
    model isn't allowed to (principle 6a: choose from the finite set).
    """
    code = (form.get("service_code") or "").strip()
    if not code:
        return "Pick a service from the catalogue before adding a line."

    note = " ".join((form.get("note") or "").split())
    quantity, problem = _a_quantity(form.get("quantity", ""))
    if problem:
        return problem
    try:
        override, problem = _an_override(form.get("rate_override", ""), code, note)
    except ConfigError as exc:
        return str(exc)
    if problem:
        return problem

    row = {"service_code": code, "quantity": quantity, "note": note,
           "rate_override": str(override) if override is not None else ""}

    # Validate by ASKING THE ENGINE, on a throwaway copy. The rules about
    # quantities and fixed-price services live in exactly one place, and it
    # isn't here. The totals are TAKEN, not just built: a line can assemble
    # cleanly and still be unformattable, and a draft that cannot be rendered
    # must never reach the session — the only Discard button in the app is on
    # the page it would break.
    trial = dict(draft)
    trial["lines"] = list(draft.get("lines", [])) + [row]
    try:
        _priced(_invoice_from(trial, invoice_id="draft"))
    except (BillingError, ConfigError, InvalidOperation, ValueError) as exc:
        return str(exc)
    _save_draft(trial)
    return ""


def _drop_line(draft: dict, form) -> str:
    """Take a line back off the draft. Nothing durable has happened yet."""
    raw = (form.get("line_no") or "").strip()
    lines = list(draft.get("lines", []))
    if not raw.isdigit() or int(raw) >= len(lines):
        return "That line is no longer on this draft."
    lines.pop(int(raw))
    draft["lines"] = lines
    _save_draft(draft)
    return ""


def _a_date(raw: str, *, fallback: date) -> tuple[date | None, str]:
    """Parse a date field, refusing rather than quietly using today."""
    text = (raw or "").strip()
    if not text:
        return fallback, ""
    try:
        return date.fromisoformat(text), ""
    except ValueError:
        return None, (f"{text!r} is not a date. Write it as YYYY-MM-DD "
                      f"(for example {fallback.isoformat()}).")


def _an_arrival_date(raw: str, *, today: date,
                     invoice: Invoice | None = None) -> tuple[date | None, str]:
    """The day money arrived — and it has to be a day that has happened.

    THIS GUARD HAS TO BE SYMMETRICAL, and for a while it was not. A payment
    dated before its invoice was refused, while the same mistyped year in the
    other direction sailed through: ``received_on=2062-03-01`` settled the
    invoice, took it off the chase, and printed "Paid in full March 01, 2062" on
    the copy the client receives. A date in the future is not a payment, it is a
    typo or an expectation, and neither is a fact about money that has arrived
    (principle 2).

    It also has to be on EVERY path. The invoice page had the backwards half of
    it; the Payments screen — where a cheque in the post is recorded, with no
    invoice to compare against — had no date guard at all in either direction.
    So the rule lives here, once, and both callers ask it.
    """
    received_on, problem = _a_date(raw, fallback=today)
    if problem:
        return None, problem
    if received_on > today:
        return None, (f"{received_on:%B %d, %Y} has not happened yet, so no money "
                      f"arrived on it. Check the year on the deposit — a date in "
                      f"the future settles the invoice, takes it off the chase, "
                      f"and prints a thank-you dated {received_on:%Y} on the copy "
                      f"the client reads.")
    if invoice is not None and invoice.issued_on and received_on < invoice.issued_on:
        # Money cannot have arrived against a bill that did not exist yet. The
        # old screen took the date on trust, so a mistyped year filed a payment
        # decades before the work — and nothing downstream could tell.
        return None, (f"{received_on:%B %d, %Y} is before invoice "
                      f"{invoice.invoice_id} was issued on "
                      f"{invoice.issued_on:%B %d, %Y}. Money cannot have arrived "
                      f"against a bill that did not exist yet — check the date on "
                      f"the deposit, or record it against the invoice it paid.")
    return received_on, ""


_NOT_AN_ARRIVAL = ("Write what arrived as a plain number of dollars, like 450 "
                   "or 187.50.")


def _an_amount(raw: str) -> tuple[Decimal | None, str]:
    """Parse what arrived, refusing rather than assuming the balance.

    Filling a blank in with the outstanding balance would be the screen deciding
    how much the client paid (principle 1). The form shows the balance as a
    starting figure the owner can see and change; a field actually left empty is
    an unanswered question, and it is refused.
    """
    text = (raw or "").strip().lstrip("$").replace(",", "").strip()
    if not text:
        return None, (f"How much arrived? {_NOT_AN_ARRIVAL} A payment with no "
                      f"amount is not a fact about the practice.")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None, f"{(raw or '').strip()!r} is not an amount. {_NOT_AN_ARRIVAL}"
    # Decimal() hands back NaN and Infinity happily, and every guard written as
    # a comparison passes NaN. Finiteness is asked first, as it is on a rate.
    if not amount.is_finite():
        return None, f"{(raw or '').strip()!r} is not an amount. {_NOT_AN_ARRIVAL}"
    if amount <= 0:
        return None, (f"{amount:,.2f} is not money arriving. A refund or a "
                      f"correction is its own act, not a negative row on the "
                      f"payment ledger — every total in the practice sums this.")
    return amount, ""


def _a_method(raw: str) -> tuple[Method | None, str]:
    """Read the method off the picker, and refuse anything not in the set.

    There is no field anywhere on these screens that types how money arrived,
    for the same reason there is none that types a service name: the set is
    finite and the engine owns it (principle 6a).
    """
    try:
        return Method((raw or "").strip().lower()), ""
    except ValueError:
        return None, (f"{(raw or '').strip()!r} is not a way money arrives. Pick "
                      f"one of: {', '.join(_METHOD_LABEL[m] for m in Method)}.")


# --- the screens --------------------------------------------------------------

def _build_screen(*, error: str = "", note: str = ""):
    """Render the build screen from whatever the draft currently holds."""
    draft = _draft()
    invoice = None
    try:
        invoice = _priced(_invoice_from(draft, invoice_id=_next_number()))
    except (BillingError, ConfigError, InvalidOperation, ValueError) as exc:
        # A draft the engine will no longer accept — a service removed from the
        # catalogue under it, say, or a row left in a cookie by an older build
        # that let one through. Say so and offer the way out, rather than
        # rendering half an invoice: this page carries the only Discard button,
        # so a draft that 500s it locks the owner out of invoicing entirely.
        invoice = None
        error = error or (f"{exc} This draft can't be shown as it stands — "
                          f"discard it and start again.")

    year = int(draft.get("tax_year") or _working_year())
    return render_template(
        "invoice_build.html", title="New invoice",
        draft=draft, invoice=invoice, catalogue=by_category(), plans=plans(),
        clients=STATE.client_choices(), tax_year=year,
        on_file=_plan_on_file((draft.get("client_id") or "").strip(), year),
        today=date.today(), error=error, note=note)


@bp.route("/invoices")
def invoices():
    """Every invoice the practice has raised, and what each client is into us for.

    THE HEADLINE MONEY SCREEN, and the last one still answering from the flag.
    Both halves of it did: the status column read ``invoice.is_paid``, and the
    running total counted a whole invoice as paid the moment ``paid_on`` was
    non-empty. Neither could see a part payment, and neither could see a payment
    recorded anywhere other than an invoice's own page — so a deposit written
    through the store seam left the invoice reading Overdue while the money sat
    on the ledger next to it.
    """
    today = date.today()
    year = _working_year()
    ledger = _ledger()
    rows = sorted(_in_step(STATE.store.load_invoices(), ledger),
                  key=lambda i: (i.issued_on or date.min, i.invoice_id), reverse=True)
    listed = [{"invoice": inv, "money": _money_state(inv, ledger)} for inv in rows]
    # Only clients with something billed IN THAT YEAR get a row. Building the
    # row set from every client who has ever been invoiced puts a line of zeros
    # against someone whose work was last season — and "Outstanding 0.00" next
    # to a client who does owe money, in another year, is worse than no row at
    # all (principle 13).
    billed_this_year = sorted({i.client_id for i in rows
                               if i.tax_year == year and i.is_issued})
    running = [_running_total(rows, ledger, client_id=cid, tax_year=year)
               for cid in billed_this_year]
    draft = _draft()
    return render_template(
        "invoices.html", title="Invoices", listed=listed, running=running,
        tax_year=year, today=today,
        draft=draft, draft_lines=len(draft.get("lines", [])))


def _running_total(invoices, ledger, *, client_id: str, tax_year: int) -> dict:
    """What one client has been billed this season, and what has actually landed.

    What was BILLED is the engine's own ``billed_to_date``. What has been PAID
    is not taken from it: that figure is summed off ``paid_on``, so a client who
    has paid 300 of a 450 invoice counts as having paid nothing, and one whose
    payment came in through the tray counts as having paid nothing either. Both
    are answered here off the ledger, invoice by invoice, and the count of
    invoices resting on the coarse pre-ledger record travels with the row so the
    screen can say the total is not all of one kind.
    """
    billed = billed_to_date(invoices, client_id=client_id, tax_year=tax_year)
    mine = [i for i in invoices if i.client_id == client_id
            and i.tax_year == tax_year and i.is_issued]
    states = [_money_state(i, ledger) for i in mine]
    return {
        "client_id": client_id,
        "name": STATE.name(client_id),
        "invoices": billed["invoices"],
        "standard_value": billed["standard_value"],
        "charged": billed["charged"],
        "paid": _sum(s.paid for s in states),
        "outstanding": _sum(s.owed for s in states),
        "pre_ledger": sum(1 for s in states if s.pre_ledger),
    }


@bp.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    """Build a draft: pick the client, pick the plan, add lines from the catalogue."""
    if request.method != "POST":
        return _build_screen()

    draft = _draft()
    action = (request.form.get("action") or "").strip()
    if action == "discard":
        session.pop(_DRAFT, None)
        session.modified = True
        return _build_screen(note="Draft discarded. Nothing was ever written down.")
    if action == "header":
        return _build_screen(error=_set_header(draft, request.form))
    if action == "add":
        return _build_screen(error=_add_line(draft, request.form))
    if action == "drop":
        return _build_screen(error=_drop_line(draft, request.form))
    return _build_screen(error="That button did nothing SATC recognises. "
                               "Set the client, add a line, or issue the invoice.")


@bp.route("/invoices/<invoice_id>/issue", methods=["POST"])
def issue(invoice_id: str):
    """Fix the draft and write it down — or show, on the page, why it refused.

    The refusal is the product here. A reduced plan with no recorded basis stops
    at this line, and the owner reads the engine's own sentence about it.
    """
    stored = STATE.store.load_invoices()
    draft = _draft()
    taken = next((i for i in stored if i.invoice_id == invoice_id), None)
    if taken is not None and _is_the_same_invoice(taken, draft):
        # Already issued under that number — a double-submitted form or a back
        # button. "Already exists as requested" is success (principle 8).
        return redirect(url_for("billing.view", invoice_id=invoice_id))
    # Otherwise the number in the URL is stale and now belongs to somebody else.
    # It is not a conflict to report: the number was never part of what the
    # owner asked for, only of when the page was rendered. Fall through and
    # number this invoice from what exists NOW (principle 8: the id derives from
    # what the thing is, not from when the form was drawn).

    if not draft.get("lines"):
        return _build_screen(error="There is nothing on this draft yet. Add what the "
                                   "client received, then issue it.")
    if not (draft.get("client_id") or "").strip():
        return _build_screen(error="Choose which client this invoice is for. An invoice "
                                   "addressed to nobody can't be sent or reconciled.")

    issued_on, problem = _a_date(request.form.get("issued_on", ""), fallback=date.today())
    if problem:
        return _build_screen(error=problem)
    raw_days = (request.form.get("due_in_days") or "30").strip()
    if not raw_days.isdigit():
        return _build_screen(error=f"{raw_days!r} is not a number of days. Payment terms "
                                   f"are a whole number of days, like 30.")

    try:
        require_human(acting_actor(), "issue an invoice", instead=_ISSUE_INSTEAD)
        invoice = _invoice_from(draft, invoice_id=next_invoice_number(
            stored, year=(issued_on or date.today()).year))
        invoice.issue(on=issued_on, due_in_days=int(raw_days))
    except (BillingError, ActorRefused, ConfigError, ValueError) as exc:
        return _build_screen(error=str(exc))

    STATE.store.save_invoices([invoice])
    session.pop(_DRAFT, None)
    # Remember what THIS session issued. The draft is gone, so a re-submitted
    # form has nothing left to compare against; this is what lets the second
    # arrival be recognised as the same request rather than as a stranger
    # asking about a number that happens to be taken.
    session[_LAST_ISSUED] = invoice.invoice_id
    session.modified = True
    return redirect(url_for("billing.view", invoice_id=invoice.invoice_id))


@bp.route("/invoices/<invoice_id>/paid", methods=["POST"])
def mark_paid(invoice_id: str):
    """Record money arriving against this invoice — a fact, not a flag.

    What used to happen here was ``invoice.paid_on = whatever the form said``,
    which accepted a 1999 date on a 2026 invoice, silently overwrote itself on a
    second submit, and could not represent half the bill arriving at all. A
    payment is written to the ledger instead, and ``paid_on`` is recomputed from
    it: a part payment leaves the invoice unpaid and still owed (principle 11b).
    """
    invoice = _find(invoice_id)
    problem = ""
    try:
        require_human(acting_actor(), "record a payment", instead=_ISSUE_INSTEAD)
    except ActorRefused as exc:
        problem = str(exc)
    if not problem and not invoice.is_issued:
        problem = (f"Invoice {invoice.invoice_id} has not been issued, so there is "
                   f"nothing to have been paid. Issue it first.")

    amount, trouble = _an_amount(request.form.get("amount", ""))
    problem = problem or trouble
    received_on, trouble = _an_arrival_date(request.form.get("received_on", ""),
                                            today=date.today(), invoice=invoice)
    problem = problem or trouble
    method, trouble = _a_method(request.form.get("method", ""))
    problem = problem or trouble
    if problem:
        return _view_screen(invoice, error=problem)

    payment = Payment(
        client_id=invoice.client_id, amount=amount, received_on=received_on,
        method=method,
        reference=" ".join((request.form.get("reference") or "").split()),
        invoice_id=invoice.invoice_id,
        # Recorded on this invoice's own page: the owner said which invoice it
        # was, and the ledger keeps that as the reason rather than pretending
        # something reconciled it.
        basis=MatchBasis.CHOSEN_BY_HUMAN)

    added = _record([payment])
    ledger = _ledger(invoice.client_id)
    _settle(invoice, ledger)
    clash = _records_disagree(invoice, ledger)
    if clash:
        return _view_screen(invoice, note=clash)
    if not added:
        return _view_screen(invoice, note=(
            f"Already on the ledger: {amount:,.2f} by "
            f"{_METHOD_LABEL[method].lower()} on {received_on:%B %d, %Y}. "
            f"Nothing was counted twice."))
    return redirect(url_for("billing.view", invoice_id=invoice.invoice_id))


@bp.route("/invoices/<invoice_id>")
def view(invoice_id: str):
    """The invoice as the client reads it — the engine's own words, not ours."""
    return _view_screen(_find(invoice_id))


@bp.route("/invoices/<invoice_id>/print")
def print_invoice(invoice_id: str):
    """The same invoice with nothing to click — for paper or a PDF print."""
    from satc.comms import library

    invoice = _find(invoice_id)
    # The client's copy tells the truth about their balance, so it reads the
    # ledger too. A sheet that says PAID IN FULL because a flag was set, when
    # half the bill is still outstanding, is the one piece of paper that must
    # never be wrong — and the mirror of that is the sheet that says nothing at
    # all about a bill the practice has recorded as settled, which is what a
    # pre-ledger invoice printed until ``_money_state`` started keeping it.
    #
    # This sheet carries the FACT and not the provenance. Which of the practice's
    # two kinds of record a payment date came off is an internal distinction and
    # belongs on the owner's screens; to the client, "paid in full on the 4th of
    # March" means exactly one thing either way.
    ledger = _ledger(invoice.client_id)
    money = _money_state(_in_step([invoice], ledger)[0], ledger)
    # The letterhead comes from the practice's own config, not from a string in
    # a template — the firm's name is a recorded fact like any other.
    return render_template("invoice_print.html", invoice=invoice,
                           client_name=STATE.name(invoice.client_id),
                           money=money, paid=money.paid, owed=money.owed,
                           over=money.over,
                           firm=library().firm_values(), today=date.today())


# --- money arriving, and which invoice it was for ------------------------------

@bp.route("/payments")
def payments():
    """Every payment recorded, and the ones still looking for an invoice."""
    return _payments_screen()


def _payments_screen(*, error: str = "", note: str = ""):
    """The reconciliation screen.

    Two halves, deliberately separate. What is ATTRIBUTED shows how it was
    attributed, because a payment the reference named and one a model picked are
    different facts. What is not attributed goes in a TRAY, and each row is put
    back through :func:`~satc.billing.payment.reconcile` on every load — the
    ladder is re-run rather than cached, so an invoice issued this morning
    changes what yesterday's orphan deposit can be.
    """
    ledger = _ledger()
    # ``paid_on`` is only a summary, so reconcile against invoices brought into
    # line with the ledger first — otherwise a stale flag decides which invoices
    # count as open, and the ladder answers the wrong question.
    invoices = _in_step(STATE.store.load_invoices(), ledger)
    on_file = {i.invoice_id for i in invoices}
    newest = sorted(ledger, key=lambda p: (p.received_on, p.payment_id), reverse=True)

    # An attribution can outlive the invoice it points at. The store keeps such
    # a row loadable on purpose — a payment attributed to nothing is exactly the
    # kind of thing the owner has to be shown — but the screen was rendering it
    # as an ordinary row with a working link, and the link went to a 404. What
    # is wrong with the row travels WITH the row (principle 13).
    matched = [{"payment": p, "name": STATE.name(p.client_id),
                "on_file": p.invoice_id in on_file}
               for p in newest if p.is_matched]
    tray = []
    for payment in (p for p in newest if not p.is_matched):
        match = reconcile(payment, _reconcilable(invoices, ledger), ledger)
        tray.append({
            "payment": payment, "name": STATE.name(payment.client_id),
            "match": match,
            # Only the invoices reconciliation actually offered. The template
            # renders these and nothing else, and ``accept_choice`` refuses
            # anything outside the same list on the way back in.
            "candidates": [i for i in invoices if i.invoice_id in match.candidates],
        })

    return render_template(
        "payments.html", title="Payments", matched=matched, tray=tray,
        clients=STATE.client_choices(), methods=list(Method),
        method_label=_METHOD_LABEL, how_matched=_HOW_MATCHED,
        today=date.today(), error=error, note=note)


@bp.route("/payments/record", methods=["POST"])
def record_payment():
    """Money that did not come in through an invoice screen.

    A cheque in the post, a transfer against nothing in particular. It is
    recorded UNMATCHED on purpose: the tray then reconciles it in the open,
    where the owner can read what the ladder concluded and why, rather than this
    form quietly picking an invoice for it (principle 5).
    """
    problem = ""
    try:
        require_human(acting_actor(), "record a payment", instead=_ISSUE_INSTEAD)
    except ActorRefused as exc:
        problem = str(exc)

    client_id = (request.form.get("client_id") or "").strip()
    if not problem and not client_id:
        problem = ("Whose money is this? A payment belonging to nobody can never "
                   "be reconciled against an invoice, and it distorts every "
                   "client total that sums the ledger.")
    amount, trouble = _an_amount(request.form.get("amount", ""))
    problem = problem or trouble
    # No invoice to compare against here — this is money that arrived against
    # nothing in particular. The half of the guard that does not need one still
    # applies: a day that has not happened is not a day money arrived on.
    received_on, trouble = _an_arrival_date(request.form.get("received_on", ""),
                                            today=date.today())
    problem = problem or trouble
    method, trouble = _a_method(request.form.get("method", ""))
    problem = problem or trouble
    if problem:
        return _payments_screen(error=problem)

    payment = Payment(
        client_id=client_id, amount=amount, received_on=received_on,
        method=method,
        reference=" ".join((request.form.get("reference") or "").split()),
        note=" ".join((request.form.get("note") or "").split()))
    if not _record([payment]):
        return _payments_screen(note=(
            f"Already on the ledger: {amount:,.2f} by "
            f"{_METHOD_LABEL[method].lower()} on {received_on:%B %d, %Y}. "
            f"Nothing was counted twice."))
    return redirect(url_for("billing.payments"))


@bp.route("/payments/<payment_id>/match", methods=["POST"])
def match_payment(payment_id: str):
    """Attribute a payment — to what reconciliation found, or to a choice off
    the shortlist it offered.

    The ladder is re-run here rather than trusted from the page that drew the
    form, because the page may be minutes old. On rungs 1 and 2 nothing from the
    form is read at all: the reference named the invoice, or only one invoice
    that amount could clear was open, and neither is a decision anybody makes.
    On rung 3 the id goes through :func:`accept_choice`, which refuses anything
    that was not among the candidates — the engine checks the answer, and a
    posted invoice belonging to another client bounces off it (principle 6).
    """
    ledger = _ledger()
    payment = next((p for p in ledger if p.payment_id == payment_id), None)
    if payment is None:
        abort(404, description=(
            f"No payment {payment_id} on the ledger. Payments are recorded on "
            f"an invoice's own page or on the Payments screen — if this one has "
            f"never been recorded, record it there first."))

    invoices = _in_step(STATE.store.load_invoices(), ledger)
    match = reconcile(payment, _reconcilable(invoices, ledger), ledger)
    try:
        require_human(acting_actor(), "attribute a payment", instead=_ISSUE_INSTEAD)
        if match.is_resolved:
            attributed = payment.against(match.invoice_id, match.basis)
        else:
            attributed = accept_choice(
                payment, (request.form.get("invoice_id") or "").strip(),
                match, by_model=False)
    except (BillingError, ActorRefused) as exc:
        return _payments_screen(error=str(exc))

    # The id derives from the payment itself, so attributing it REPLACES the
    # unattributed row rather than adding a second one (principle 8).
    STATE.store.save_payments([attributed])
    fresh = _ledger(attributed.client_id)
    for invoice in STATE.store.load_invoices(attributed.client_id):
        if invoice.invoice_id == attributed.invoice_id:
            _settle(invoice, fresh)
    return redirect(url_for("billing.payments"))


def _is_the_same_invoice(taken: Invoice, draft: dict) -> bool:
    """Is the invoice already under that number the very thing being asked for?

    "Already exists as requested" is only success when the existing thing IS the
    thing requested. The number comes off ``_next_number()`` when the build page
    is DRAWN, so a tab left open carries a number that may since have been
    issued to another client. Redirecting there would tell the owner that this
    client's invoice had been raised, while nothing was written for them at all
    and the draft sat in the session looking unsaved.
    """
    if not draft.get("lines"):
        # Nothing is being asked for. That is the SAME request only when this
        # session is the one that issued it and the draft was cleared by that
        # success. A browser that has never issued anything — a fresh session, a
        # pasted URL — posting a number that happens to be taken is asking about
        # somebody else's invoice, and redirecting there would hand one client's
        # bill to a session that was never given it (principle 11).
        return session.get(_LAST_ISSUED) == taken.invoice_id
    if taken.client_id != (draft.get("client_id") or "").strip():
        return False
    try:
        proposed = _invoice_from(draft, invoice_id=taken.invoice_id)
    except (BillingError, ConfigError, InvalidOperation, ValueError):
        return False
    if (proposed.plan_key, proposed.tax_year) != (taken.plan_key, taken.tax_year):
        return False
    shape = [(ln.service_code, ln.quantity, ln.standard_rate) for ln in proposed.lines]
    return shape == [(ln.service_code, ln.quantity, ln.standard_rate)
                     for ln in taken.lines]


def _find(invoice_id: str) -> Invoice:
    """The stored invoice, or a 404 that names the next step."""
    found = next((i for i in STATE.store.load_invoices()
                  if i.invoice_id == invoice_id), None)
    if found is None:
        abort(404, description=(
            f"No invoice numbered {invoice_id}. Only issued invoices are written "
            f"down — an unfinished draft lives in this browser session and is "
            f"still on the New invoice screen."))
    return found


def _view_screen(invoice: Invoice, *, error: str = "", note: str = ""):
    """The invoice, and the record its paid state rests on.

    Every figure here comes off :mod:`satc.billing.payment` — what has been
    paid, what is still owed, whether the client OVERPAID. The last one is
    surfaced rather than swallowed: money beyond the total is owed a
    conversation, and an invoice screen that just says "paid" is where that
    conversation stops happening.

    And it says WHICH KIND of record it is reading. An invoice settled before
    the ledger existed used to read here as never having been paid at all,
    because the page recomputed it from an empty ledger and believed the answer.
    """
    ledger = _ledger(invoice.client_id)
    money = _money_state(_in_step([invoice], ledger)[0], ledger)
    return render_template(
        "invoice_view.html", title=f"Invoice {invoice.invoice_id}",
        invoice=invoice, client_name=STATE.name(invoice.client_id),
        money=money, payments=money.payments,
        methods=list(Method), method_label=_METHOD_LABEL,
        how_matched=_HOW_MATCHED,
        paid=money.paid, owed=money.owed, over=money.over, settled=money.settled,
        today=date.today(), error=error, note=note)
