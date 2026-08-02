"""Invoicing screens (Flask blueprint) — raise a bill, see what the client sees.

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

Routes:
  GET  /invoices                  - every invoice, plus what each client is into us for
  GET  /invoices/new              - build one from the catalogue
  POST /invoices/new              - set the header, add a line, drop a line, discard
  POST /invoices/<id>/issue       - fix it and write it down (or show why it refused)
  POST /invoices/<id>/paid        - record that the money arrived
  GET  /invoices/<id>             - the invoice as the client reads it
  GET  /invoices/<id>/print       - the same thing, printable, with nothing to click
"""

from __future__ import annotations

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
from satc.config import ConfigError
from satc.models.actor import ActorRefused, require_human

bp = Blueprint("billing", __name__)

# The half-built invoice, kept per browser session. See the module docstring:
# a draft is not yet a fact about the practice.
_DRAFT = "invoice_draft"

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


def _set_header(draft: dict, form) -> str:
    """Who the invoice is for, which year, and what they pay relative to standard.

    Everything is read and checked BEFORE anything is written to the draft: a
    refused year must leave the year that was already there alone, rather than
    half-applying the form it just declined.
    """
    year, problem = _a_tax_year(form.get("tax_year", ""))
    if problem:
        return problem
    key = (form.get("plan_key") or "").strip() or default_plan_key()
    if key not in plans():
        return (f"There is no rate plan called {key!r}. Pick one of: "
                f"{', '.join(sorted(plans()))}.")
    draft["client_id"] = (form.get("client_id") or "").strip()
    draft["tax_year"] = year
    draft["plan_key"] = key
    draft["plan_basis"] = " ".join((form.get("plan_basis") or "").split())
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

    return render_template(
        "invoice_build.html", title="New invoice",
        draft=draft, invoice=invoice, catalogue=by_category(), plans=plans(),
        clients=STATE.client_choices(), tax_year=draft.get("tax_year") or _working_year(),
        today=date.today(), error=error, note=note)


@bp.route("/invoices")
def invoices():
    """Every invoice the practice has raised, and what each client is into us for."""
    today = date.today()
    year = _working_year()
    rows = sorted(STATE.store.load_invoices(),
                  key=lambda i: (i.issued_on or date.min, i.invoice_id), reverse=True)
    # Only clients with something billed IN THAT YEAR get a row. Building the
    # row set from every client who has ever been invoiced puts a line of zeros
    # against someone whose work was last season — and "Outstanding 0.00" next
    # to a client who does owe money, in another year, is worse than no row at
    # all (principle 13).
    billed_this_year = sorted({i.client_id for i in rows
                               if i.tax_year == year and i.is_issued})
    running = [(cid, STATE.name(cid), billed_to_date(rows, client_id=cid, tax_year=year))
               for cid in billed_this_year]
    draft = _draft()
    return render_template(
        "invoices.html", title="Invoices", invoices=rows, running=running,
        tax_year=year, today=today,
        draft=draft, draft_lines=len(draft.get("lines", [])))


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
    session.modified = True
    return redirect(url_for("billing.view", invoice_id=invoice.invoice_id))


@bp.route("/invoices/<invoice_id>/paid", methods=["POST"])
def mark_paid(invoice_id: str):
    """Record that the money arrived, on the day it arrived."""
    invoice = _find(invoice_id)
    paid_on, problem = _a_date(request.form.get("paid_on", ""), fallback=date.today())
    if not problem:
        try:
            require_human(acting_actor(), "record a payment", instead=_ISSUE_INSTEAD)
        except ActorRefused as exc:
            problem = str(exc)
    if not problem and not invoice.is_issued:
        problem = (f"Invoice {invoice.invoice_id} has not been issued, so there is "
                   f"nothing to have been paid. Issue it first.")
    if problem:
        return _view_screen(invoice, error=problem)

    invoice.paid_on = paid_on
    STATE.store.save_invoices([invoice])
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
    # The letterhead comes from the practice's own config, not from a string in
    # a template — the firm's name is a recorded fact like any other.
    return render_template("invoice_print.html", invoice=invoice,
                           client_name=STATE.name(invoice.client_id),
                           firm=library().firm_values(), today=date.today())


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
        # Nothing is being asked for: the draft was cleared by the issue that
        # succeeded, and this is that same submit arriving twice.
        return True
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


def _view_screen(invoice: Invoice, *, error: str = ""):
    return render_template(
        "invoice_view.html", title=f"Invoice {invoice.invoice_id}",
        invoice=invoice, client_name=STATE.name(invoice.client_id),
        today=date.today(), error=error)
