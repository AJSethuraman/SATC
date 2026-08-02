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


def _int_or_none(raw: str):
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() else None


def _newest_engagement(client_id: str):
    """The client's most recent generated engagement, or ``None``."""
    return next((e for e in STATE.jobs() if e.client_id == client_id), None)


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


def _latest_invoice(client_id: str, tax_year: int | None):
    """The newest ISSUED invoice for this client — what a covering email is about."""
    issued = [i for i in STATE.store.load_invoices(client_id)
              if i.is_issued and (tax_year is None or i.tax_year == tax_year)]
    return max(issued, key=lambda i: (i.issued_on, i.invoice_id)) if issued else None


def _context(client_id: str, tax_year: int | None) -> dict[str, str]:
    """Assemble the merge values for a client from everything on file."""
    lib = library()
    engagement = _newest_engagement(client_id)
    year = tax_year if tax_year is not None else getattr(engagement, "tax_year", None)
    return build_context(
        client_id=client_id,
        client_name=STATE.name(client_id),
        public_client=STATE.public_client(client_id),
        returns=[r for r in STATE.returns() if r.client_id == client_id],
        requested=[r for r in STATE.requested_items() if r.client_id == client_id],
        received=[d for d in STATE.received_documents() if d.client_id == client_id],
        engagement=engagement,
        fee_record=_fee_record(client_id, year),
        invoice=_latest_invoice(client_id, year),
        engagement_name=_workflow_name(engagement),
        standing_text=firm_policy().standing_text,
        tax_year=tax_year,
        # The prior year is always one back from whichever year this comms is
        # about — that comparison is what surfaces a document that stopped
        # arriving, which no amount of tick-and-tie can find.
        prior_year=(year - 1) if year else None,
        firm_values=lib.firm_values(),
    )


def _fills(form) -> dict[str, str]:
    """The preparer's typed-in values for the slots no stored fact can supply."""
    return {k[len(_FILL_PREFIX):]: v for k, v in form.items()
            if k.startswith(_FILL_PREFIX) and (v or "").strip()}


def _render_screen(*, client_id: str, template_key: str, tax_year: int | None,
                   fills: dict[str, str], notes: list[str] | None = None):
    lib = library()
    template = lib.template(template_key) if template_key in lib.keys() else None

    draft = None
    values: dict[str, str] = {}
    preparer_fields: list = []
    model_drafted: list[str] = []
    if template is not None and client_id:
        values = _context(client_id, tax_year)
        values.update(fills)
        draft = render(template, values, library=lib)

        # Anything still unfilled that is WORDING rather than a fact gets
        # written by the local model, so the draft arrives finished. Facts are
        # never composed — they stay visibly marked. See satc.agent.compose.
        composable = [n for n in draft.unfilled
                      if (p := lib.placeholder(n)) is not None and p.model_drafted]
        if composable:
            from satc.agent.compose import compose_slots

            written = compose_slots(
                composable, client_name=STATE.name(client_id),
                tax_year=values.get("tax_year", ""),
                engagement_name=values.get("engagement_name", ""))
            if written:
                values.update(written)
                model_drafted = sorted(written)
                draft = render(template, values, library=lib)

        preparer_fields = lib.preparer_fields(template)

    return render_template(
        "comms.html", title="Client comms",
        stages=lib.by_stage(), template=template, draft=draft,
        clients=STATE.client_choices(), client_id=client_id,
        client_email=STATE.client_email(client_id) if client_id else "",
        tax_year=tax_year or "", fills=fills,
        preparer_fields=preparer_fields,
        model_drafted=[lib.placeholder(n).label if lib.placeholder(n) else n
                       for n in model_drafted],
        prefilled=[(lib.placeholder(n).label if lib.placeholder(n) else n)
                   for n in (draft.filled if draft else []) if not n.startswith("firm_")],
        unfilled_labels=[(lib.placeholder(n).label if lib.placeholder(n) else n, n)
                         for n in (draft.unfilled if draft else [])],
        notes=notes or [])


@bp.route("/comms", methods=["GET", "POST"])
def comms():
    src = request.form if request.method == "POST" else request.args
    return _render_screen(
        client_id=(src.get("client") or "").strip(),
        template_key=(src.get("template") or "").strip(),
        tax_year=_int_or_none(src.get("tax_year", "")),
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
    values = _context(client_id, tax_year)
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
                         tax_year=tax_year or ""),
        attachment_url="", attachment_name="")


@bp.route("/clients/<client_id>/comms")
def client_comms(client_id: str):
    """Jump into the comms screen for one client (linked from their page)."""
    return redirect(url_for("comms.comms", client=client_id,
                            template=request.args.get("template", "")))
