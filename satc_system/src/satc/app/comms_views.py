"""Client-communication drafts screen (Flask blueprint).

Pick a client and one of the templates in ``configs/comms/``; the screen renders
a DRAFT prefilled from what the practice already holds on that client — the
year, the items their engagement asked for, what's still outstanding in the
document register, the result on their return, the fee on file.

**Nothing is sent from here.** There is no SMTP anywhere in this path. The screen
hands the preparer finished text to copy into their own mail client (or, on a
machine with desktop Outlook, pops a compose window via the same helper the
organizer and delivery screens already use). A human always presses send.

Thin by design: gathering records from :data:`~satc.app.state.STATE` and reading
the form is all that happens here. The merging, the prefill rules, and the
"never invent a value" marker all live in :mod:`satc.comms`.

Routes:
  GET  /comms                 - template picker + rendered draft
  POST /comms                 - re-render with the preparer's typed-in values
  POST /comms/outlook         - hand the current draft to a desktop Outlook draft
"""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from satc.app.state import STATE
from satc.comms import build_context, library, render
from satc.obligations.policy import policy as firm_policy

bp = Blueprint("comms", __name__)

# Form fields that aren't merge values (so everything else can be swept up as one).
_FILL_PREFIX = "fill_"

# The templates whose fee slot means WHAT WE AGREED rather than what we billed.
#
# ``fee_amount_text`` is one merge name for two different facts. Everywhere else
# it is the amount on a bill — money already owed for work already done, which
# :func:`_latest_invoice` resolves with some care. On a letter a client SIGNS it
# is the fee this engagement agreed, and only the engagement can say that.
# See :func:`_context`, which drops the one before the other gets its turn.
_STATES_TERMS = frozenset({"engagement_letter"})


def _int_or_none(raw: str):
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() else None


def _newest_engagement(client_id: str, year: int | None = None):
    """The engagement this letter is ABOUT, or the newest if no year is named.

    Year first, and it is not a nicety. This used to take whichever job came
    back first — which is whichever was SAVED last — so entering a late
    prior-year engagement made every current-year letter quote the prior year's
    terms. The mismatch note downstream would then fire on the right client and
    the wrong pair of years, and the wording that landed still looked like an
    agreement.
    """
    mine = [e for e in STATE.jobs() if e.client_id == client_id]
    if year is not None:
        same_year = [e for e in mine if getattr(e, "tax_year", None) == year]
        if same_year:
            return same_year[0]
    return mine[0] if mine else None


def _workflow_name(engagement) -> str:
    """The engagement's workflow display name — ``""`` when it can't be resolved."""
    key = getattr(engagement, "workflow_key", "")
    if not key:
        return ""
    try:
        from satc.intake.workflows import load_workflow
        return load_workflow(key).name
    except Exception:  # noqa: BLE001 - a missing workflow just means no prefill
        return ""


def _fee_record(client_id: str, tax_year: int | None):
    """The engagement/fee row for this client — preferring the matching year."""
    rows = [e for e in STATE.mart.engagements if e.client_id == client_id]
    if tax_year is not None:
        return next((e for e in rows if e.tax_year == tax_year), None)
    return rows[-1] if rows else None


def _situation(client_id: str, values: dict) -> str:
    """A short description of this client, for choosing between wordings.

    Deliberately facts the engine already established — entity type, what is on
    file — never a judgement. The model's job is to match a situation to a
    pre-written sentence, not to characterise the client.
    """
    pc = STATE.public_client(client_id)
    bits = [f"client {STATE.name(client_id)}"]
    if pc is not None and pc.entity_type:
        bits.append(f"entity type {pc.entity_type}")
    if values.get("tax_year"):
        bits.append(f"tax year {values['tax_year']}")
    if values.get("engagement_name"):
        bits.append(f"engagement: {values['engagement_name']}")
    docs = {d.doc_type for d in STATE.received_documents() if d.client_id == client_id}
    if docs:
        bits.append("documents on file: " + ", ".join(sorted(docs)[:6]))
    return "; ".join(bits)


class WrongInvoice(Exception):
    """The draft was asked for an invoice this client does not have.

    Its own exception rather than a ``None`` return, because the two outcomes
    must not be confused: "nobody named an invoice" falls back to the newest
    one, and "somebody named an invoice that is not this client's" must not
    fall back to anything at all.
    """


def _requested_invoice(client_id: str, invoice_id: str):
    """The ONE invoice this draft is about, or a refusal.

    The Today queue titles a row "Invoice 2026-9001 unpaid" and hands that
    number over in the link. If this resolved anything else, the client would
    read a covering note quoting a different number and a different amount than
    the row asserted — principle 1, reaching a client.

    So an id that is not on file, or belongs to somebody else, REFUSES
    (principle 5). Falling back to the newest bill here is the confident wrong
    answer: a covering email quoting the wrong bill is worse than no draft, and
    unlike a missing draft nobody would ever notice it.
    """
    found = next((i for i in STATE.store.load_invoices()
                  if str(i.invoice_id) == invoice_id), None)
    if found is None:
        raise WrongInvoice(
            f"No invoice {invoice_id} is on file, so there is nothing to draft a "
            f"covering note about. Open the invoice from the billing screen and "
            f"check the number.")
    if found.client_id != client_id:
        raise WrongInvoice(
            f"Invoice {invoice_id} does not belong to {STATE.name(client_id)}. "
            f"Drafting from it would quote another client's bill, so nothing has "
            f"been prefilled. Pick the right client, or the right invoice.")
    return found


def _latest_invoice(client_id: str, tax_year: int | None, invoice_id: str = ""):
    """The invoice a covering email is about.

    With an explicit ``invoice_id`` — which is what a Today row hands over —
    that number is the fact the row already asserted, and nothing else will do;
    see :func:`_requested_invoice`. With none, the newest ISSUED invoice for the
    year, which is all a preparer arriving cold at ``/comms`` has said.
    """
    if invoice_id:
        return _requested_invoice(client_id, invoice_id)
    issued = [i for i in STATE.store.load_invoices(client_id)
              if i.is_issued and (tax_year is None or i.tax_year == tax_year)]
    return max(issued, key=lambda i: (i.issued_on, i.invoice_id)) if issued else None


def _agreed_terms(engagement, year: int | None, *, template_key: str,
                  notes: list[str]) -> dict[str, str]:
    """What THIS engagement agreed — the layer that stops every letter being one letter.

    ``build_context`` knows the client, the firm and the dates; it cannot know
    what anybody promised, so the scope and the fee came from standing wording
    that reads the same for a $450 return and a $5,500 partnership. These facts
    are derived from the interview answers behind the job — the origin fact —
    and RECOMPUTED rather than read off a stored copy (principle 3).

    Three ways this answers "nothing", and only one of them is a problem:

    * No engagement on file at all. The draft is for a client we have not
      quoted, standing wording is the honest thing to offer, and the screen
      already marks it as machine-drafted.
    * An engagement for a DIFFERENT YEAR. Terms belong to the year that agreed
      them, so last year's scope may not be restated as this year's. On a letter
      that states terms this is worth saying out loud, because the wording that
      lands instead looks exactly like an agreement.
    * The facts would not derive. Named with the refusal, because falling back
      to standing wording silently is how the letter stops being this client's.
    """
    if engagement is None:
        return {}

    if year is not None and getattr(engagement, "tax_year", None) != year:
        if template_key in _STATES_TERMS:
            notes.append(
                f"The newest engagement on file for {STATE.name(engagement.client_id)} "
                f"is for {engagement.tax_year}, not {year} — a different year's "
                f"engagement agreed different terms, so nothing below is taken from "
                f"it. Generate the {year} engagement from intake, or draft the "
                f"letter for {engagement.tax_year}.")
        return {}

    from satc.intake.service import letter_facts_for_job

    try:
        return letter_facts_for_job(STATE.store, engagement)
    except Exception as refused:  # noqa: BLE001 - a config refusal must not 500 a draft
        # A comms screen is not where a config refusal should take the app down.
        # It is also not where standing wording should quietly stand in for what
        # an engagement agreed: the facts stay ABSENT, so every slot they would
        # have filled renders `[[ ... : fill in ]]`, and the refusal is shown
        # with the step that clears it (principles 1 and 10).
        notes.append(
            f"SATC could not work out what this engagement agreed, so the scope and "
            f"fee below are not taken from it. {refused}")
        return {}


def _context(client_id: str, tax_year: int | None, invoice_id: str = "", *,
             template_key: str = "",
             notes: list[str] | None = None) -> dict[str, str]:
    """Assemble the merge values for a client from everything on file."""
    lib = library()
    engagement = _newest_engagement(client_id, tax_year)
    year = tax_year if tax_year is not None else getattr(engagement, "tax_year", None)
    values = build_context(
        client_id=client_id,
        client_name=STATE.name(client_id),
        public_client=STATE.public_client(client_id),
        returns=[r for r in STATE.returns() if r.client_id == client_id],
        requested=[r for r in STATE.requested_items() if r.client_id == client_id],
        received=[d for d in STATE.received_documents() if d.client_id == client_id],
        engagement=engagement,
        fee_record=_fee_record(client_id, year),
        invoice=_latest_invoice(client_id, year, invoice_id),
        engagement_name=_workflow_name(engagement),
        standing_text=firm_policy().standing_text,
        tax_year=tax_year,
        # The prior year is always one back from whichever year this comms is
        # about — that comparison is what surfaces a document that stopped
        # arriving, which no amount of tick-and-tie can find.
        prior_year=(year - 1) if year else None,
        firm_values=lib.firm_values(),
    )

    # -- what this engagement agreed, LAYERED OVER the generic prefill --------
    #
    # In that order on purpose. The generic context still supplies the client,
    # the firm and the dates; a fact derived from the answers outranks wording
    # that reads the same for everybody, because this engagement does not.
    notes = notes if notes is not None else []

    if template_key in _STATES_TERMS:
        # A LETTER THAT STATES TERMS TAKES ITS FEE FROM THE TERMS, OR FROM
        # NOTHING. ``build_context`` fills this same name from an ISSUED INVOICE
        # total: a bill for work already done, standing in the slot where a
        # client reads what they agreed to pay — a number they will hold the
        # practice to, on the one document they sign.
        #
        # Dropped BEFORE the engagement gets its turn, and dropped whether or
        # not the engagement can answer. `[[ Fee: fill in ]]` is a question; the
        # wrong number is not a question, and nobody would ever query it.
        values.pop("fee_amount_text", None)

    facts = _agreed_terms(engagement, year, template_key=template_key, notes=notes)
    if facts:
        # The plan's ask list is the generic one MINUS the work these answers
        # took out of scope. Dropped first so that "nothing is in scope to ask
        # for" renders as a visible blank rather than falling back to a list
        # that asks the client for a document the same plan calls out of scope
        # — a contradiction only the client, who cannot see the plan, would read.
        values.pop("requested_items", None)
        values.update(facts)
    return values


def _fills(form) -> dict[str, str]:
    """The preparer's typed-in values for the slots no stored fact can supply."""
    return {k[len(_FILL_PREFIX):]: v for k, v in form.items()
            if k.startswith(_FILL_PREFIX) and (v or "").strip()}


def _render_screen(*, client_id: str, template_key: str, tax_year: int | None,
                   fills: dict[str, str], invoice_id: str = "",
                   notes: list[str] | None = None):
    lib = library()
    template = lib.template(template_key) if template_key in lib.keys() else None

    draft = None
    values: dict[str, str] = {}
    preparer_fields: list = []
    model_drafted: list[str] = []
    notes = list(notes or [])
    if template is not None and client_id:
        try:
            values = _context(client_id, tax_year, invoice_id,
                              template_key=template_key, notes=notes)
        except WrongInvoice as refused:
            # The whole screen stands down, template included, so there is
            # nothing here to copy. Rendering a draft anyway would mean
            # rendering it from some OTHER invoice — the exact failure being
            # refused. The note says which invoice, and what to do instead.
            template, values, notes = None, {}, notes + [str(refused)]

    if template is not None and client_id:
        values.update(fills)
        draft = render(template, values, library=lib)

        # Anything still unfilled that is WORDING rather than a fact gets
        # written by the local model, so the draft arrives finished. Facts are
        # never chosen for — they stay visibly marked. See comms/wording.py.
        composable = [n for n in draft.unfilled
                      if (p := lib.placeholder(n)) is not None and p.model_drafted]
        if composable:
            from satc.comms.wording import choose

            # The model picks between sentences the PRACTICE wrote; it never
            # writes prose. Same limited choices a human has from a dropdown —
            # the output space is what is in configs/comms/wording.yaml, and
            # nothing else can reach a client.
            picked = choose(composable, context=_situation(client_id, values))
            if picked:
                values.update({name: c.text for name, c in picked.items()})
                model_drafted = sorted(n for n, c in picked.items() if c.chosen_by_model)
                draft = render(template, values, library=lib)

        preparer_fields = lib.preparer_fields(template)

    return render_template(
        "comms.html", title="Client comms",
        stages=lib.by_stage(), template=template, draft=draft,
        clients=STATE.client_choices(), client_id=client_id,
        client_email=STATE.client_email(client_id) if client_id else "",
        tax_year=tax_year or "", fills=fills,
        preparer_fields=preparer_fields, invoice_id=invoice_id,
        model_drafted=[lib.placeholder(n).label if lib.placeholder(n) else n
                       for n in model_drafted],
        prefilled=[(lib.placeholder(n).label if lib.placeholder(n) else n)
                   for n in (draft.filled if draft else []) if not n.startswith("firm_")],
        unfilled_labels=[(lib.placeholder(n).label if lib.placeholder(n) else n, n)
                         for n in (draft.unfilled if draft else [])],
        notes=notes)


@bp.route("/comms", methods=["GET", "POST"])
def comms():
    src = request.form if request.method == "POST" else request.args
    return _render_screen(
        client_id=(src.get("client") or "").strip(),
        template_key=(src.get("template") or "").strip(),
        tax_year=_int_or_none(src.get("tax_year", "")),
        # request.values, not src: a Today row arrives as a GET with ?invoice=,
        # and the screen's own re-render posts it back as a form field. Either
        # way it is the number the row already put in front of the owner.
        invoice_id=(request.values.get("invoice") or "").strip(),
        fills=_fills(request.form) if request.method == "POST" else {})


@bp.route("/comms/outlook", methods=["POST"])
def comms_outlook():
    """Hand the rendered draft to the desktop mail client — still unsent."""
    client_id = (request.form.get("client") or "").strip()
    template_key = (request.form.get("template") or "").strip()
    lib = library()
    if not client_id or template_key not in lib.keys():
        return redirect(url_for("comms.comms"))

    tax_year = _int_or_none(request.form.get("tax_year", ""))
    invoice_id = (request.values.get("invoice") or "").strip()
    try:
        # THE SAME SEAM, NOT A SECOND ONE. Both doors into a draft go through
        # `_context`, so the fee an engagement letter states comes from the
        # engagement on this path too. The notes it collects are advice about
        # what could not be derived, and this route hands back a finished
        # compose window rather than a screen that could show them — the draft
        # itself still carries every `[[ ... : fill in ]]` they refer to.
        values = _context(client_id, tax_year, invoice_id,
                          template_key=template_key)
    except WrongInvoice as refused:
        # This route opens a compose window aimed at the client. Handing it a
        # draft built from a DIFFERENT invoice is the one outcome worse than
        # handing it nothing, so it goes back to the screen with the refusal.
        return _render_screen(client_id=client_id, template_key=template_key,
                              tax_year=tax_year, fills=_fills(request.form),
                              invoice_id=invoice_id, notes=[str(refused)])
    values.update(_fills(request.form))
    template = lib.template(template_key)
    draft = render(template, values, library=lib)

    from satc.intake.email_draft import mailto_url, open_outlook_draft

    to = STATE.client_email(client_id)
    result = open_outlook_draft(to=to, subject=draft.subject, body=draft.body)
    return render_template(
        "draft_result.html", title="Client comms", result=result, what=draft.name.lower(),
        to=to, subject=draft.subject, body=draft.body,
        mailto=mailto_url(to=to, subject=draft.subject, body=draft.body),
        back_url=url_for("comms.comms", client=client_id, template=template_key,
                         tax_year=tax_year or "", invoice=invoice_id or None),
        attachment_url="", attachment_name="")


@bp.route("/clients/<client_id>/comms")
def client_comms(client_id: str):
    """Jump into the comms screen for one client (linked from their page)."""
    return redirect(url_for("comms.comms", client=client_id,
                            template=request.args.get("template", "")))
