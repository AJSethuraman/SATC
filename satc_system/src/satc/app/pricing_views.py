"""Prices — what the practice charges, and a record of every time it moved.

Rates and discounts have always been a YAML edit. That is not a gap this screen
closes by moving them into the database; it is the design, and this screen is a
door onto it. Two decisions shape everything below, and both belong to
:mod:`satc.billing.editor` — this file is the thin view over them.

**THE FILE IS STILL THE TRUTH.** These forms edit
``configs/billing/services.yaml`` and ``configs/billing/rate_plans.yaml``. They
do not write an override that layers on top. The questionnaire editor works that
way, but it is wrong here: an override quietly beats a hand edit, so the owner
changes the file, nothing happens, and nothing on any screen says why. Hand
editing stays exactly as supported as it was before this screen existed, and the
screen says so out loud — and, because :func:`~satc.billing.history.reconcile_files`
runs on every load, a hand edit made at midnight is IN the record by morning,
attributed to nobody rather than to the app.

**THE EDIT IS SURGICAL.** In these two files the comments are the reasoning, so
re-serialising them would be valid YAML and a real regression. The editor finds
the line and changes the value; this screen never writes a byte of YAML itself.

WHAT THIS SCREEN OWES THE OWNER:

* **The refusal is the product.** Every rule about what a price may be lives in
  the editor and the catalogue loader — not here. This file's whole contribution
  to a bad value is to catch the refusal and put it on the page as a sentence,
  with what was typed still in the box. A second copy of those rules here would
  be a second copy to drift, and two opinions about a price is one too many.
* **It says what a change will and will not do**, and the two halves of that
  answer are currently different. See ``_WHAT_A_RATE_DOES`` — a service rate is
  frozen onto the invoice line when the line is raised, and a plan's discount is
  not. That asymmetry is a defect in the invoice engine, not in this screen, and
  this screen states it rather than hiding it.
* **A change can say why.** Offered, never required — an unexplained change is
  still a fact, and refusing to record it for want of a reason would lose the
  fact as well as the reason (principle 2).
* **When each price last moved**, and where nothing is recorded it says nothing
  is recorded rather than showing a date it does not have (principle 1).

Routes:
  GET  /pricing            every rate and every discount, editable in place
  POST /pricing/rate       change one service's standard rate
  POST /pricing/discount   change one plan's discount
  GET  /pricing/history    every change, newest first, filterable — and what a
                           rate was on a given day
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, render_template, request

from satc.app.state import STATE, acting_actor
from satc.billing import catalogue, editor, history
from satc.billing.invoice import BillingError
from satc.config import ConfigError
from satc.models.actor import ActorRefused, require_human

bp = Blueprint("pricing", __name__)

# What a refusal from this file tells the owner to do instead. The actor gate is
# unreachable from a live browser request by construction, so this only fires
# from a script or a future tool path — and those get told where the decision
# actually lives. A price is firm policy, and firm policy is the owner's.
_INSTEAD = ("open Prices in the local app and change it there — what the "
            "practice charges is the owner's own decision, and the record of it "
            "has to name the person who made it")

# WHAT A CHANGE REACHES, in the owner's words. These are not reassurance; they
# were read off the engine, and they do not agree with each other.
#
#   A SERVICE RATE is safe. ``InvoiceLine.standard_rate`` is written onto the
#   line by ``Invoice.add``, and ``standard_total`` sums
#   ``line.standard_rate * line.quantity``. Nothing on an issued invoice reads
#   the catalogue again. Verified, and pinned by
#   ``test_an_issued_invoice_does_not_move_when_the_rate_behind_it_changes``.
#
#   A PLAN DISCOUNT IS NOT. ``Invoice.rate_plan`` is a property calling
#   ``plan(self.plan_key)`` on every access, so ``discount_total`` and ``total``
#   are recomputed from whatever ``rate_plans.yaml`` says NOW. Move a discount
#   and every issued invoice on that plan reprices — including the copy the
#   client is holding and the billed-to-date figures. That is a defect in the
#   invoice engine (the percentage should be stamped onto the invoice the way
#   the rate is stamped onto the line) and it is not this screen's to fix. What
#   this screen can do is refuse to let the owner find out the hard way.
_WHAT_A_RATE_DOES = (
    "Changing a rate does not re-price anything already issued. An invoice line "
    "stores the rate it was raised at, so a bill sent last March keeps the "
    "figures on the copy the client is holding. The new rate applies to the next "
    "invoice you build.")

_WHAT_A_DISCOUNT_DOES = (
    "Changing a discount does NOT move invoices already issued. An invoice now "
    "records the percentage it was raised at, the same way each line records the "
    "rate it was raised at, so last season's invoices stay exactly as they were "
    "sent — on the client's copy, in the register and in the billed-to-date "
    "figures. Drafts you have not issued yet DO follow the new number, which is "
    "usually what you want: nobody has agreed them with anybody.")

# This screen said the opposite for one afternoon, and it was true when it said
# it: an issued invoice re-read the live discount every time it was rendered, so
# moving the household rate from 25% to 30% restated what a client had already
# paid. The warning was honest and the behaviour was wrong; the engine was fixed
# rather than the sentence softened.


def _a_reason(raw: str) -> str:
    """The optional why. Collapsed like every other free-text field in the app."""
    return " ".join((raw or "").split())


# --- the record ---------------------------------------------------------------

def _newest_first(changes) -> list:
    """The record reads backwards from now.

    ``history`` hands its rows back oldest first, which is the right order for
    replaying what happened to a price and the wrong order for a screen: the
    change the owner is looking for is nearly always the one they just made.
    """
    return list(reversed(list(changes)))


def _last_changed() -> dict:
    """The newest recorded change against each service code and plan key.

    Read ONCE and indexed, not asked per row. This page draws every service and
    every plan, so a per-row query would be a per-row read of the same record —
    the cost ``default_plan_key`` shares a cache to avoid.

    A subject absent from this map has no recorded change, which is a different
    fact from "changed a long time ago", and the template renders it differently.
    """
    newest: dict = {}
    for change in _newest_first(history.all_changes(STATE.store)):
        newest.setdefault(change.subject, change)
    return newest


def _catch_up() -> list:
    """Fold in any price the owner changed in the file since SATC last looked.

    This is what keeps hand editing honest rather than merely permitted. Without
    it the record would be COMPLETE LOOKING and wrong — and a gap in a record
    reads exactly like nothing having happened. The rows it writes carry no
    author and a date pinned to an interval, because that is genuinely all that
    is known (principles 1 and 2).

    Usually returns nothing, because usually nothing has moved. A ``ConfigError``
    is left to escape to the caller, which turns it into the sentence the owner
    needs in order to fix the file — this is the screen they would come to.
    """
    return history.reconcile_files(STATE.store)


# --- the screen ---------------------------------------------------------------

def _pricing_screen(*, error: str = "", note: str = "", entered: dict | None = None):
    """Draw the whole price list, or say why it cannot be drawn.

    ``entered`` is what the owner typed into the field that was just refused. It
    goes back in the box on purpose: a refusal that also wipes the value makes
    the owner retype it in order to read the complaint, and the third time that
    happens they stop reading the complaint.
    """
    entered = entered or {}
    services_file = str(editor.price_file("services"))
    plans_file = str(editor.price_file("plans"))
    try:
        outside = _catch_up()
        groups = catalogue.by_category()
        plans = list(catalogue.plans().values())
        default_plan = catalogue.default_plan_key()
        stamps = {"services": editor.file_stamp("services"),
                  "plans": editor.file_stamp("plans")}
    except ConfigError as exc:
        # The billing config does not currently load. Refusing to draw the price
        # list is the honest answer — half a list, holding only the services that
        # happened to parse, is a page the owner would trust. The loader's own
        # sentence names the file and the line (principles 5 and 10).
        return render_template(
            "pricing.html", title="Prices", groups=[], plans=[], default_plan="",
            last={}, entered={}, stamps={},
            services_file=services_file, plans_file=plans_file,
            what_a_rate_does=_WHAT_A_RATE_DOES,
            what_a_discount_does=_WHAT_A_DISCOUNT_DOES,
            error=error or str(exc), note="", outside=[])

    return render_template(
        "pricing.html", title="Prices", groups=groups, plans=plans,
        default_plan=default_plan, last=_last_changed(), entered=entered,
        stamps=stamps, services_file=services_file, plans_file=plans_file,
        what_a_rate_does=_WHAT_A_RATE_DOES,
        what_a_discount_does=_WHAT_A_DISCOUNT_DOES,
        error=error, note=note, outside=outside)


@bp.route("/pricing")
def pricing():
    """What the practice charges — every rate and every discount, editable here."""
    return _pricing_screen()


def _change_one(*, which: str, subject: str, raw: str, why: str, stamp: str,
                apply, kind: str, field: str, epilogue: str):
    """The shared body of both POSTs: gate, edit the file, then record it.

    THE ORDER IS THE WHOLE THING. The actor is checked before anything is
    written, because a write that then fails to be recorded is a price change
    with no author. The file is written before the history row, because the file
    is the source of truth and ``record_change`` refuses a row that disagrees
    with it — the record describes the file's movements and never leads them.
    """
    mine = {subject: raw} if subject else {}
    if not subject:
        return _pricing_screen(error=(
            f"That form did not say which {which} to change. Change a price from "
            f"the box on its own row."))
    try:
        require_human(acting_actor(), "change what the practice charges",
                      instead=_INSTEAD)
        # ``expected_stamp`` is what the file looked like when this page was
        # drawn. A tab left open over lunch while the YAML was hand-edited
        # submits a stale form, and without this the edit would silently throw
        # the hand edit away — the exact failure the whole no-overrides decision
        # was taken to avoid. Blank only when the form predates the field.
        edit = apply(subject, raw, expected_stamp=stamp or None)
    except (ActorRefused, ConfigError) as exc:
        # The editor's and the loader's own refusals, verbatim: an unknown code,
        # a value the file cannot hold, a file that would no longer load, a
        # change made in another window. They name the thing and the next step
        # better than a rewrite of them would (principle 10).
        return _pricing_screen(error=str(exc), entered=mine)

    if not edit.is_change:
        # The file already said this. Not an error and not history — the file was
        # not rewritten, so recording a row saying 450 became 450 would be a row
        # that renders identically forever, in a record whose worth a year later
        # is that every row in it is a change (principles 8 and 13).
        return _pricing_screen(note=edit.summary())

    try:
        history.record_change(
            STATE.store, kind=kind, subject=subject, field=field,
            old_value=edit.old, new_value=edit.new, actor=acting_actor(),
            note=why)
    except (BillingError, ConfigError, ActorRefused) as exc:
        # The price HAS changed and the record has not. Saying so is the only
        # honest option: swallowing it would leave the owner believing a change
        # they can see on the page is written down, and reversing the file to
        # match would be this screen deciding to undo a change the owner asked
        # for and the engine accepted (principle 9).
        return _pricing_screen(error=(
            f"{edit.summary()} — the file was changed. The change was NOT added "
            f"to the price history: {exc}"))

    return _pricing_screen(note=f"{edit.summary()} Written to {edit.file}. {epilogue}")


@bp.route("/pricing/rate", methods=["POST"])
def set_rate():
    """Change one service's standard rate, in the file, on one line."""
    return _change_one(
        which="service",
        subject=(request.form.get("code") or "").strip(),
        raw=request.form.get("rate", ""),
        why=_a_reason(request.form.get("why", "")),
        stamp=(request.form.get("stamp") or "").strip(),
        apply=editor.set_rate,
        kind=history.SERVICE, field=history.STANDARD_RATE,
        epilogue=_WHAT_A_RATE_DOES)


@bp.route("/pricing/discount", methods=["POST"])
def set_discount():
    """Change one rate plan's discount, in the file, on one line."""
    return _change_one(
        which="rate plan",
        subject=(request.form.get("key") or "").strip(),
        raw=request.form.get("discount_pct", ""),
        why=_a_reason(request.form.get("why", "")),
        stamp=(request.form.get("stamp") or "").strip(),
        apply=editor.set_discount,
        kind=history.RATE_PLAN, field=history.DISCOUNT_PCT,
        epilogue=_WHAT_A_DISCOUNT_DOES)


@bp.route("/pricing/history")
def price_history():
    """Every price change this practice has made, newest first.

    The whole point of keeping it. A rate that has been 450 since 2024 and a rate
    that moved three times last spring are different facts about the practice,
    and neither is legible from the current price list alone.
    """
    subject = (request.args.get("service") or "").strip()

    # What the filter can be set to is drawn from the RECORD as well as from the
    # catalogue. A service deleted from services.yaml still has changes behind
    # it, and a filter that could not select it would make those rows
    # unreachable — the record outlives the price it is about.
    try:
        names = {code: svc.name for code, svc in catalogue.services().items()}
        names.update({key: rp.name for key, rp in catalogue.plans().items()})
        trouble = ""
    except ConfigError as exc:
        # The history is a fact of its own and does not depend on today's config
        # parsing. Losing the whole record because a rate was mistyped this
        # morning would be the record failing on the day it is most needed — and
        # this is the screen somebody is on while fixing it.
        names, trouble = {}, str(exc)

    rows = _newest_first(history.changes_for(STATE.store, subject) if subject
                         else history.all_changes(STATE.store))
    choices = sorted({c.subject for c in history.all_changes(STATE.store)} | set(names),
                     key=lambda t: (names.get(t, "").lower() or "zzz", t))

    asked, answer, when_problem = (request.args.get("on") or "").strip(), None, ""
    if subject and asked:
        # The question the record exists to answer, asked out loud. ``rate_on``
        # refuses a date it cannot answer for rather than extrapolating today's
        # number backwards, so this is a straight pass-through: the basis travels
        # with the number because the number gets quoted to a client.
        try:
            answer = history.rate_on(STATE.store, subject, date.fromisoformat(asked))
        except ValueError:
            when_problem = (f"{asked!r} is not a date. Write it as YYYY-MM-DD "
                            f"(for example {date.today().isoformat()}).")

    return render_template(
        "price_history.html", title="Price history", rows=rows, names=names,
        choices=choices, target=subject, kind_discount=history.RATE_PLAN,
        asked=asked, answer=answer, when_problem=when_problem,
        begins=history.record_begins(STATE.store), error=trouble)
