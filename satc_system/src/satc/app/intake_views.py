"""Client-intake & engagement screens (Flask blueprint).

Registered by :func:`satc.app.server.create_app`. Routes here drive the
new-client / interview flow and the engagement (requested-vs-received) view,
backed by :data:`satc.app.state.STATE`.

Screens (built out by the UI workstream):
  GET  /clients/new                  - choose person/business, create a client
  POST /clients/new                  - create the client, jump into intake
  GET  /intake/new                   - pick a client + workflow, answer the interview
  POST /intake/new                   - generate the engagement (opens Requested docs)
  GET  /engagements                  - list generated engagements
  GET  /engagements/<id>             - tasks grouped by category, risk flags, requests
  POST /engagements/<id>/tasks/<tid> - toggle a task complete
  GET  /engagements/<id>/email       - plain-text client request email
  GET  /engagements/<id>/print       - printable client request list
  GET  /engagements/<id>/print-internal - printable internal checklist
"""

from __future__ import annotations

import dataclasses
import json

from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from satc.app.state import STATE
from satc.intake.workflows import NEW_CLIENT_GATE

bp = Blueprint("intake", __name__)

# Filing statuses offered when capturing/confirming a client's situation.
FILING_STATUSES = [
    "Single",
    "Married filing jointly",
    "Married filing separately",
    "Head of household",
    "Qualifying surviving spouse",
]


def _public_client(client_id: str):
    """Look up a PublicClient by id (the de-identified projection)."""
    return next((c for c in STATE.mart.public_clients if c.client_id == client_id), None)


def _client_type(public_client) -> str:
    """Map an entity_type onto the workflow catalog's person/business split."""
    if public_client is None:
        return "person"
    return "business" if public_client.entity_type != "INDIVIDUAL" else "person"


@bp.route("/engagements")
def engagements():
    return render_template("engagements.html", title="Engagements",
                           engagements=STATE.intake_engagements())


@bp.route("/clients/new", methods=["GET", "POST"])
def new_client():
    if request.method == "POST":
        kind = request.form.get("kind", "person")
        if kind == "business":
            cid = STATE.create_business_client(
                legal_name=request.form.get("legal_name", "").strip(),
                entity_type=request.form.get("entity_type", "SCORP"),
                ein=request.form.get("ein", "").strip(),
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
            )
        else:
            cid = STATE.create_person_client(
                first_name=request.form.get("first_name", "").strip(),
                last_name=request.form.get("last_name", "").strip(),
                ssn=request.form.get("ssn", "").strip(),
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
            )
        return redirect(url_for("intake.client_start", client_id=cid))
    return render_template("client_new.html", title="New client")


@bp.route("/clients/import", methods=["GET", "POST"], endpoint="import_clients")
def import_clients():
    """Bulk import (CSV / spreadsheet / Drake export) with a preview step."""
    from satc.intake.importer import CSV_TEMPLATE

    if request.method == "POST":
        text = ""
        upload = request.files.get("file")
        if upload is not None and upload.filename:
            text = upload.read().decode("utf-8", errors="ignore")
        if not text.strip():
            text = request.form.get("pasted", "")

        parsed = STATE.preview_client_import(csv_text=text)
        parsed_json = json.dumps([dataclasses.asdict(p) for p in parsed])
        new_count = sum(1 for p in parsed if p.status == "new")
        dup_count = sum(1 for p in parsed if p.status == "duplicate")
        review_count = sum(1 for p in parsed if p.status == "review")
        create_count = sum(1 for p in parsed if p.status != "duplicate")
        return render_template(
            "client_import_preview.html", title="Import clients",
            parsed=parsed, parsed_json=parsed_json,
            new_count=new_count, dup_count=dup_count, review_count=review_count,
            create_count=create_count)

    return render_template("client_import.html", title="Import clients",
                           csv_template=CSV_TEMPLATE)


@bp.route("/clients/import/confirm", methods=["POST"], endpoint="import_clients_confirm")
def import_clients_confirm():
    """Commit the previewed rows carried over as hidden JSON."""
    from satc.intake.importer import ParsedClient

    raw = request.form.get("parsed_json", "[]")
    try:
        rows = json.loads(raw)
    except (ValueError, TypeError):
        rows = []
    parsed = [ParsedClient(**d) for d in rows]
    include_duplicates = bool(request.form.get("include_duplicates"))
    STATE.commit_client_import(parsed, include_duplicates=include_duplicates)
    return redirect(url_for("intake.engagements"))


@bp.route("/clients/quick-add", methods=["POST"], endpoint="quick_add_client")
def quick_add_client():
    """Smart single-add, then flow straight into the interview."""
    client_id, _parsed = STATE.add_client_smart(
        name=request.form.get("name", ""),
        tin=request.form.get("tin", ""),
        entity_type=request.form.get("entity_type", ""),
        email=request.form.get("email", ""),
        phone=request.form.get("phone", ""),
        state=request.form.get("state", ""),
    )
    return redirect(url_for("intake.client_start", client_id=client_id))


def _int_or_none(raw: str):
    raw = (raw or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _prior_summary(client_id: str) -> dict:
    """A compact "what we already know" summary for a returning client."""
    returns = sorted((r for r in STATE.returns() if r.client_id == client_id),
                     key=lambda r: r.tax_year, reverse=True)
    prior = STATE.prior_engagement(client_id)
    requested: list[str] = []
    if prior is not None:
        for t in prior.tasks:
            if t.audience == "client" and t.category not in requested:
                requested.append(t.category)
    return {
        "returns": [(r.tax_year, r.return_type, r.status) for r in returns[:4]],
        "prior_year": prior.tax_year if prior else None,
        "requested_categories": requested,
    }


@bp.route("/clients/<client_id>/start", endpoint="client_start")
def client_start(client_id: str):
    """After a client exists, choose HOW to take them in — separate from creating them.

    Three intake modes: scan their documents, interview them manually, or email
    them an organizer to fill out themselves.
    """
    public_client = _public_client(client_id)
    if public_client is None:
        return redirect(url_for("intake.engagements"))
    return render_template(
        "client_start.html", title="New client", client_id=client_id,
        public_client=public_client, client_type=_client_type(public_client),
        returning=STATE.is_returning(client_id), filing_status=STATE.filing_status(client_id))


@bp.route("/intake/new", methods=["GET", "POST"])
def new_engagement():
    if request.method == "POST":
        client_id = request.form.get("client", "")
        workflow_key = request.form.get("workflow_key", "")
        due_date = request.form.get("due_date", "")
        mode = request.form.get("mode", "new")
        tax_year = _int_or_none(request.form.get("tax_year", ""))

        from satc.intake.workflows import load_workflow

        workflow = load_workflow(workflow_key)
        answers = {}
        for q in workflow.questions:
            if q.id == NEW_CLIENT_GATE:
                continue                       # set from the new/returning gate below
            val = request.form.get(f"q_{q.id}")
            if val is not None:
                answers[q.id] = val
        answers[NEW_CLIENT_GATE] = "yes" if mode == "new" else "no"

        filing_status = request.form.get("filing_status", "").strip()
        if filing_status:
            STATE.set_filing_status(client_id, filing_status)

        eng = STATE.create_engagement(
            client_id=client_id, workflow_key=workflow_key, due_date=due_date,
            answers=answers, tax_year=tax_year)
        return redirect(url_for("intake.engagement_detail", engagement_id=eng.engagement_id))

    client_id = request.args.get("client", "")
    public_client = _public_client(client_id)
    client_type = _client_type(public_client)
    workflows = STATE.workflow_catalog().get(client_type, [])

    workflow_key = request.args.get("workflow", "")
    workflow = None
    mode = request.args.get("mode", "")
    prefill: dict[str, str] = {}
    prior = None
    if workflow_key:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)
        if not mode:                           # auto-detect, preparer can flip it
            mode = "returning" if STATE.is_returning(client_id) else "new"
        prior = STATE.prior_engagement(client_id, workflow_key)
        if mode == "returning" and prior is not None:
            prefill = dict(prior.intake_answers or {})

    returning = mode == "returning"
    return render_template(
        "intake_new.html", title="Intake",
        client_id=client_id, public_client=public_client, client_type=client_type,
        workflows=workflows, workflow=workflow, mode=mode, returning=returning,
        prefill=prefill, prior=prior,
        prior_summary=_prior_summary(client_id) if returning else {},
        filing_statuses=FILING_STATUSES, filing_status=STATE.filing_status(client_id),
        gate_question=NEW_CLIENT_GATE)


@bp.route("/engagements/<engagement_id>", endpoint="engagement_detail")
def engagement_detail(engagement_id: str):
    eng = STATE.engagement(engagement_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))

    # Group tasks by category, preserving first-seen order.
    groups: list[tuple[str, list]] = []
    index: dict[str, int] = {}
    for task in eng.tasks:
        category = task.category or "General"
        if category not in index:
            index[category] = len(groups)
            groups.append((category, []))
        groups[index[category]][1].append(task)

    # Status of any document linked to a client request (Requested/Received badge).
    doc_status = {d.document_id: d.status for d in STATE.documents()}

    client_tasks = [t for t in eng.tasks if t.audience == "client"]
    internal_tasks = [t for t in eng.tasks if t.audience != "client"]

    received = sum(1 for t in client_tasks
                   if (t.document_id and doc_status.get(t.document_id) == "Received") or t.completed)
    total_requests = len(client_tasks)

    return render_template(
        "engagement_detail.html", title="Engagements",
        eng=eng, groups=groups, doc_status=doc_status,
        client_tasks=client_tasks, internal_tasks=internal_tasks,
        received=received, total_requests=total_requests)


@bp.route("/engagements/<engagement_id>/tasks/<task_id>", methods=["POST"])
def toggle_task(engagement_id: str, task_id: str):
    eng = STATE.engagement(engagement_id)
    current = False
    if eng is not None:
        for task in eng.tasks:
            if task.task_id == task_id:
                current = task.completed
                break
    STATE.set_task_completed(task_id, not current)
    return redirect(url_for("intake.engagement_detail", engagement_id=engagement_id))


@bp.route("/engagements/<engagement_id>/email")
def engagement_email(engagement_id: str):
    eng = STATE.engagement(engagement_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_client_request_email
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_client_request_email(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/plain")


@bp.route("/engagements/<engagement_id>/email/outlook", methods=["POST"],
          endpoint="engagement_email_outlook")
def engagement_email_outlook(engagement_id: str):
    """Pop a ready-to-send Outlook draft of the client request email."""
    eng = STATE.engagement(engagement_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    from satc.intake.email_draft import mailto_url, open_outlook_draft
    from satc.intake.outputs import build_request_email

    to = STATE.client_email(eng.client_id)
    subject, body = build_request_email(eng, client_name=STATE.name(eng.client_id))
    result = open_outlook_draft(to=to, subject=subject, body=body)
    return render_template(
        "draft_result.html", title="Engagements", result=result, what="request email",
        to=to, subject=subject, body=body,
        mailto=mailto_url(to=to, subject=subject, body=body),
        back_url=url_for("intake.engagement_detail", engagement_id=engagement_id),
        attachment_url="", attachment_name="")


# -- intake mode (c): email the client an organizer to fill out --------------

def _organizer_path(client_id: str, workflow_key: str):
    from pathlib import Path
    folder = Path(STATE.store.dir) / "organizers"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{client_id}_{workflow_key}_organizer.pdf"


def _write_organizer(client_id: str, workflow_key: str, *, returning: bool,
                     tax_year: int | None = None):
    """Generate the organizer PDF for a client+workflow and return (workflow, path)."""
    from satc.intake.outputs import generate_intake_organizer_pdf
    from satc.intake.workflows import load_workflow

    workflow = load_workflow(workflow_key)
    prior = STATE.prior_engagement(client_id, workflow_key)
    prefill = dict(prior.intake_answers) if (returning and prior is not None) else {}
    pdf = generate_intake_organizer_pdf(
        workflow, client_name=STATE.name(client_id), tax_year=tax_year, returning=returning,
        prefill=prefill, filing_status=STATE.filing_status(client_id))
    path = _organizer_path(client_id, workflow_key)
    path.write_bytes(pdf)
    return workflow, path


@bp.route("/intake/organizer", endpoint="organizer")
def organizer():
    """Pick a workflow, then preview/send the client a fillable organizer."""
    client_id = request.args.get("client", "")
    public_client = _public_client(client_id)
    if public_client is None:
        return redirect(url_for("intake.engagements"))
    client_type = _client_type(public_client)
    workflow_key = request.args.get("workflow", "")
    returning = STATE.is_returning(client_id)

    workflow = None
    if workflow_key:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)
    return render_template(
        "organizer.html", title="Intake", client_id=client_id, public_client=public_client,
        returning=returning, workflow=workflow,
        workflows=None if workflow else STATE.workflow_catalog().get(client_type, []),
        client_email=STATE.client_email(client_id), mode="returning" if returning else "new")


@bp.route("/intake/organizer.pdf", endpoint="organizer_pdf")
def organizer_pdf():
    client_id = request.args.get("client", "")
    workflow_key = request.args.get("workflow", "")
    if not (client_id and workflow_key) or _public_client(client_id) is None:
        return redirect(url_for("intake.engagements"))
    returning = request.args.get("mode", "") == "returning" or (
        not request.args.get("mode") and STATE.is_returning(client_id))
    _wf, path = _write_organizer(client_id, workflow_key, returning=returning,
                                 tax_year=_int_or_none(request.args.get("tax_year", "")))
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name="tax_organizer.pdf")


@bp.route("/intake/organizer/email", methods=["POST"], endpoint="organizer_email")
def organizer_email():
    client_id = request.form.get("client", "")
    workflow_key = request.form.get("workflow_key", "")
    if not (client_id and workflow_key) or _public_client(client_id) is None:
        return redirect(url_for("intake.engagements"))
    returning = request.form.get("mode", "") == "returning"
    tax_year = _int_or_none(request.form.get("tax_year", ""))

    from satc.intake.email_draft import mailto_url, open_outlook_draft
    from satc.intake.outputs import build_organizer_email

    workflow, path = _write_organizer(client_id, workflow_key, returning=returning, tax_year=tax_year)
    subject, body = build_organizer_email(
        client_name=STATE.name(client_id), workflow=workflow, tax_year=tax_year, returning=returning)
    to = STATE.client_email(client_id)
    result = open_outlook_draft(to=to, subject=subject, body=body, attachments=[str(path)])
    return render_template(
        "draft_result.html", title="Intake", result=result, what="organizer email",
        to=to, subject=subject, body=body,
        mailto=mailto_url(to=to, subject=subject, body=body),
        back_url=url_for("intake.organizer", client=client_id, workflow=workflow_key),
        attachment_url=url_for("intake.organizer_pdf", client=client_id, workflow=workflow_key,
                               mode="returning" if returning else "new"),
        attachment_name="tax_organizer.pdf")


@bp.route("/engagements/<engagement_id>/print")
def engagement_print(engagement_id: str):
    eng = STATE.engagement(engagement_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_client_request_print_html
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_client_request_print_html(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/html")


@bp.route("/engagements/<engagement_id>/print-internal")
def engagement_print_internal(engagement_id: str):
    eng = STATE.engagement(engagement_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_internal_checklist_print_html
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_internal_checklist_print_html(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/html")
