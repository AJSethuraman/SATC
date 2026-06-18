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

from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    request,
    url_for,
)

from satc.app.state import STATE

bp = Blueprint("intake", __name__)


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
        return redirect(url_for("intake.new_engagement", client=cid))
    return render_template("client_new.html", title="New client")


@bp.route("/intake/new", methods=["GET", "POST"])
def new_engagement():
    if request.method == "POST":
        client_id = request.form.get("client", "")
        workflow_key = request.form.get("workflow_key", "")
        due_date = request.form.get("due_date", "")
        tax_year_raw = request.form.get("tax_year", "").strip()
        try:
            tax_year = int(tax_year_raw) if tax_year_raw else None
        except ValueError:
            tax_year = None

        from satc.intake.workflows import load_workflow

        workflow = load_workflow(workflow_key)
        answers = {}
        for q in workflow.questions:
            val = request.form.get(f"q_{q.id}")
            if val is not None:
                answers[q.id] = val

        eng = STATE.create_engagement(
            client_id=client_id, workflow_key=workflow_key, due_date=due_date,
            answers=answers, tax_year=tax_year or None)
        return redirect(url_for("intake.engagement_detail", engagement_id=eng.engagement_id))

    client_id = request.args.get("client", "")
    public_client = _public_client(client_id)
    client_type = _client_type(public_client)
    workflows = STATE.workflow_catalog().get(client_type, [])

    workflow_key = request.args.get("workflow", "")
    workflow = None
    if workflow_key:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)

    return render_template(
        "intake_new.html", title="Intake",
        client_id=client_id, public_client=public_client, client_type=client_type,
        workflows=workflows, workflow=workflow)


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
