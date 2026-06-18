"""Questionnaire (workflow) customization screens — Flask blueprint.

Lets the practice tailor the interviews from inside the app: reword questions and
document requests, turn items off, and add their own yes/no question with the
document it should request. Edits are saved as overrides on top of the built-in
workflows (never editing the shipped config), via :data:`satc.app.state.STATE`.

Routes (under this blueprint, name "workflows"):
  GET  /workflows                 - list workflows, link to edit each
  GET  /workflows/<key>/edit      - the editor form
  POST /workflows/<key>/edit      - save the override
  POST /workflows/<key>/reset     - clear the override (back to built-in)
"""

from __future__ import annotations

import re

from flask import Blueprint, redirect, render_template, request, url_for

from satc.app.state import STATE

bp = Blueprint("workflows", __name__)


def _slugify(text: str) -> str:
    """Lowercase, alphanumeric + hyphen id synthesized from a question label."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "question"


@bp.route("/workflows")
def workflows_index():
    workflows = STATE.all_workflows()
    edited = {wf.key: bool(STATE.workflow_override(wf.key)) for wf in workflows}
    return render_template("workflows_index.html", title="Questionnaires",
                           workflows=workflows, edited=edited)


@bp.route("/workflows/<key>/edit")
def edit_workflow(key: str):
    wf = next((w for w in STATE.all_workflows() if w.key == key), None)
    if wf is None:
        return redirect(url_for("workflows.workflows_index"))
    base = STATE.base_workflow(key)
    override = STATE.workflow_override(key)
    disabled_q = {qid for qid, e in override.get("questions", {}).items() if e.get("disabled")}
    disabled_t = {tid for tid, e in override.get("tasks", {}).items() if e.get("disabled")}
    # Live values keyed for prefill (live workflow already drops disabled items).
    live_q = {q.id: q for q in wf.questions}
    live_t = {t.template_id: t for t in wf.tasks}
    client_tasks = [t for t in base.tasks if t.audience == "client"]
    return render_template(
        "workflow_edit.html", title="Questionnaires", wf=wf, base=base,
        client_tasks=client_tasks, live_q=live_q, live_t=live_t,
        disabled_q=disabled_q, disabled_t=disabled_t,
        added_questions=override.get("added_questions", []))


@bp.route("/workflows/<key>/edit", methods=["POST"])
def save_workflow(key: str):
    base = STATE.base_workflow(key)
    override = STATE.workflow_override(key)
    form = request.form
    data: dict = {}

    # -- workflow name (only if changed from the built-in) ----------------
    wf_name = form.get("wf_name", "").strip()
    if wf_name and wf_name != base.name:
        data["name"] = wf_name

    # -- existing questions ----------------------------------------------
    questions: dict[str, dict] = {}
    for q in base.questions:
        edit: dict = {}
        label = form.get(f"q_{q.id}_label", "").strip()
        if label and label != q.label:
            edit["label"] = label
        risk = form.get(f"q_{q.id}_risk", "").strip()
        if risk != (q.risk_flag or ""):
            edit["risk_flag"] = risk
        if form.get(f"q_{q.id}_disabled"):
            edit["disabled"] = True
        if edit:
            questions[q.id] = edit
    if questions:
        data["questions"] = questions

    # -- existing tasks (client-facing requests) -------------------------
    tasks: dict[str, dict] = {}
    for t in base.tasks:
        if t.audience != "client":
            continue
        edit = {}
        text = form.get(f"t_{t.template_id}_text", "").strip()
        if text and text != t.client_request_text:
            edit["client_request_text"] = text
        category = form.get(f"t_{t.template_id}_category", "").strip()
        if category and category != t.category:
            edit["category"] = category
        if form.get(f"t_{t.template_id}_disabled"):
            edit["disabled"] = True
        if edit:
            tasks[t.template_id] = edit
    if tasks:
        data["tasks"] = tasks

    # -- added custom question (append to any already saved) -------------
    added = list(override.get("added_questions", []))
    new_label = form.get("new_q_label", "").strip()
    if new_label:
        qid = _slugify(new_label)
        new_risk = form.get("new_q_risk", "").strip()
        req_text = form.get("new_q_request_text", "").strip()
        doc_type = form.get("new_q_doc_type", "").strip()
        added.append({
            "id": qid,
            "label": new_label,
            "risk_flag": new_risk,
            "request": {
                "title": new_label,
                "category": "Custom",
                "client_request_text": req_text,
                "doc_type": doc_type,
                "days_before_due": 14,
            },
        })
    if added:
        data["added_questions"] = added

    STATE.save_workflow_override(key, data)
    return redirect(url_for("workflows.edit_workflow", key=key))


@bp.route("/workflows/<key>/reset", methods=["POST"])
def reset_workflow(key: str):
    STATE.save_workflow_override(key, {})
    return redirect(url_for("workflows.edit_workflow", key=key))
