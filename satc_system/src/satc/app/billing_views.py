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


# --- reading the form ---------------------------------------------------------

def _set_header(draft: dict, form) -> str:
    """Who the invoice is for, which year, and what they pay relative to standard."""
    draft["client_id"] = (form.get("client_id") or "").strip()
    year = (form.get("tax_year") or "").strip()
    draft["tax_year"] = int(year) if year.isdigit() else _working_year()
    key = (form.get("plan_key") or "").strip() or default_plan_key()
    if key not in plans():
        return (f"There is no rate plan called {key!r}. Pick one of: "
                f"{', '.join(sorted(plans()))}.")
    draft["plan_key"] = key
    draft["plan_basis"] = " ".join((form.get("plan_basis") or "").split())
    _save_draft(draft)
    return ""


def _add_line(draft: dict, form) -> str:
    """Put one catalogue service on the draft, or say why it can't go on.

    The service arrives as a CODE picked from the catalogue — there is no field
    anywhere on this screen that types a service name, for the same reason the
    model isn't allowed to (principle 6a: choose from the finite set).
    """
    code = (form.get("service_code") or "").strip()
    if not code:
        return "Pick a service from the catalogue before adding a line."

    override = (form.get("rate_override") or "").strip()
    if override:
        try:
            Decimal(override)
        except InvalidOperation:
            return (f"{override!r} is not an amount. Write what the work was worth "
                    f"as a plain number, like 400 or 400.00 — or leave it blank to "
                    f"bill the catalogue rate.")

    row = {"service_code": code,
           "quantity": (form.get("quantity") or "1").strip() or "1",
           "note": " ".join((form.get("note") or "").split()),
           "rate_override": override}

    # Validate by ASKING THE ENGINE, on a throwaway copy. The rules about
    # quantities and fixed-price services live in exactly one place, and it
    # isn't here.
    trial = dict(draft)
    trial["lines"] = list(draft.get("lines", [])) + [row]
    try:
        _invoice_from(trial, invoice_id="draft")
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
        invoice = _invoice_from(draft, invoice_id=_next_number())
    except (BillingError, ConfigError, InvalidOperation, ValueError) as exc:
        # A draft the engine will no longer accept — a service removed from the
        # catalogue under it, say. Say so and offer the way out, rather than
        # rendering half an invoice.
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
    running = [(cid, STATE.name(cid), billed_to_date(rows, client_id=cid, tax_year=year))
               for cid in sorted({i.client_id for i in rows})]
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
    if any(i.invoice_id == invoice_id for i in stored):
        # Already issued under that number — a double-submitted form or a back
        # button. "Already exists as requested" is success (principle 8).
        return redirect(url_for("billing.view", invoice_id=invoice_id))

    draft = _draft()
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
