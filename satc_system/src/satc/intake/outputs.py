"""Client-communications output generators — request emails + printable checklists.

A Python port of the standalone checklist app's ``outputs.js``, retargeted onto
SATC's intake data model:

  * A plain-text *client request email* listing the client-facing asks grouped by
    category, each line using the precise ``client_request_text`` for the task.
  * A printable *client request* HTML document (client-facing tasks only).
  * A printable *internal checklist* HTML document (risk flags, intake answers, and
    every task grouped by category with internal instructions + completion status).

Workflow display names and intake-question labels come from
:func:`satc.intake.workflows.load_workflow`. All functions tolerate missing/None
fields so a half-populated engagement still renders.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from satc.intake.workflows import load_workflow
from satc.models.intake import IntakeEngagement, IntakeTask

# Month abbreviations, mirroring the JS ``{ month: 'short' }`` formatter.
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_AUDIENCE_LABELS = {"client": "Client", "internal": "Internal"}


# ---------------------------------------------------------------------------
# Small helpers (direct ports of the JS utilities)
# ---------------------------------------------------------------------------

def client_facing_tasks(tasks: list[IntakeTask] | None) -> list[IntakeTask]:
    """Only the tasks that speak to the client (``audience == "client"``)."""
    return [t for t in (tasks or []) if getattr(t, "audience", None) == "client"]


def group_tasks_by_category(
    tasks: list[IntakeTask] | None,
) -> list[tuple[str, list[IntakeTask]]]:
    """Group tasks by category, preserving first-seen category order."""
    groups: list[tuple[str, list[IntakeTask]]] = []
    index: dict[str, int] = {}
    for task in tasks or []:
        category = getattr(task, "category", "") or "General"
        if category not in index:
            index[category] = len(groups)
            groups.append((category, []))
        groups[index[category]][1].append(task)
    return groups


def format_output_date(d: date | None) -> str:
    """Format a date as e.g. ``"Apr 15, 2026"``; ``""`` for ``None``."""
    if d is None:
        return ""
    try:
        return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"
    except (AttributeError, IndexError, TypeError):
        return ""


def format_answer(value: Any) -> str:
    """Render a yes/no intake answer for display."""
    if value == "yes":
        return "Yes"
    if value == "no":
        return "No"
    return "No answer"


def escape_html(value: Any) -> str:
    """Escape ``& < > " '`` for safe interpolation into HTML."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


# ---------------------------------------------------------------------------
# Shared engagement accessors
# ---------------------------------------------------------------------------

def _load_workflow_safe(workflow_key: str) -> Any:
    """Load the workflow definition; ``None`` if it cannot be resolved."""
    if not workflow_key:
        return None
    try:
        return load_workflow(workflow_key)
    except Exception:
        return None


def _workflow_name(engagement: IntakeEngagement, workflow: Any) -> str:
    if workflow is not None and getattr(workflow, "name", ""):
        return workflow.name
    return getattr(engagement, "workflow_key", "") or "engagement"


def _display_label(engagement: IntakeEngagement, client_name: str | None) -> str:
    """A name to address the client by: explicit name, else the client id."""
    if client_name:
        return client_name
    return getattr(engagement, "client_id", "") or "Client"


# ---------------------------------------------------------------------------
# Plain-text client request email
# ---------------------------------------------------------------------------

def generate_client_request_email(
    engagement: IntakeEngagement,
    *,
    client_name: str | None = None,
    firm_name: str = "SAT-C LLP",
) -> str:
    """Build the plain-text client request email.

    Lists the client-facing tasks grouped by category, each line drawn from the
    task's ``client_request_text`` (falling back to its title) plus the suggested
    date. Internal-only details are never included.
    """
    workflow = _load_workflow_safe(getattr(engagement, "workflow_key", ""))
    workflow_name = _workflow_name(engagement, workflow)
    label = _display_label(engagement, client_name)
    due_date = format_output_date(getattr(engagement, "due_date", None))

    client_tasks = client_facing_tasks(getattr(engagement, "tasks", None))
    grouped = group_tasks_by_category(client_tasks)

    lines: list[str] = [
        f"Subject: Requested items for {label} - {workflow_name}",
        "",
        f"Hello {label},",
        "",
        (
            f"I hope you are well. {firm_name} is preparing your {workflow_name} "
            f"checklist due {due_date}. Please provide or review the following "
            f"client-facing items when convenient."
        ),
        "",
    ]

    if not grouped:
        lines += [
            "There are no client-facing requests for this checklist right now.",
            "",
        ]

    for category, category_tasks in grouped:
        lines.append(category)
        for task in category_tasks:
            text = getattr(task, "client_request_text", "") or getattr(task, "title", "")
            suggested = format_output_date(getattr(task, "suggested_date", None))
            lines.append(f"- {text} (suggested by {suggested})")
        lines.append("")

    lines += [
        "If you have questions about any item, please reply here and we will be "
        "happy to help.",
        "",
        "Thank you,",
        firm_name,
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Printable HTML documents
# ---------------------------------------------------------------------------

def _render_task_list(
    tasks: list[IntakeTask] | None, *, include_internal_details: bool = False
) -> str:
    parts: list[str] = []
    for category, category_tasks in group_tasks_by_category(tasks):
        items: list[str] = []
        for task in category_tasks:
            title = getattr(task, "title", "")
            request_text = getattr(task, "client_request_text", "") or title
            display = title if include_internal_details else request_text
            suggested = format_output_date(getattr(task, "suggested_date", None))

            details = [f"<span>Suggested: {suggested}</span>"]
            if include_internal_details:
                audience = getattr(task, "audience", "") or ""
                audience_label = _AUDIENCE_LABELS.get(audience, audience or "Internal")
                status = "Complete" if getattr(task, "completed", False) else "Open"
                details.append(f"<span>Audience: {escape_html(audience_label)}</span>")
                details.append(f"<span>Status: {status}</span>")

            extra = ""
            if include_internal_details:
                instructions = getattr(task, "internal_instructions", "")
                notes = getattr(task, "notes", "")
                if instructions:
                    extra += (
                        f'\n                    <p class="notes">Internal '
                        f"instructions: {escape_html(instructions)}</p>"
                    )
                if notes:
                    extra += (
                        f'\n                    <p class="notes">Notes: '
                        f"{escape_html(notes)}</p>"
                    )

            items.append(
                "\n                  <li>"
                f'\n                    <div class="task-title">{escape_html(display)}</div>'
                '\n                    <div class="task-details">'
                f"\n                      {''.join(details)}"
                "\n                    </div>"
                f"{extra}"
                "\n                  </li>"
            )

        parts.append(
            '\n        <section class="print-category">'
            f"\n          <h2>{escape_html(category)}</h2>"
            "\n          <ol>"
            f"            {''.join(items)}"
            "\n          </ol>"
            "\n        </section>"
        )
    return "".join(parts)


def _render_risk_flags(engagement: IntakeEngagement) -> str:
    flags = getattr(engagement, "risk_flags", None) or []
    if not flags:
        return "<p>No risk flags generated.</p>"
    items = "".join(f"<li>{escape_html(flag)}</li>" for flag in flags)
    return f"<ul>{items}</ul>"


def _render_intake_answers(engagement: IntakeEngagement, workflow: Any) -> str:
    answers = getattr(engagement, "intake_answers", None) or {}
    questions = getattr(workflow, "questions", None) or [] if workflow else []
    if not questions:
        return "<p>No intake questions for this workflow.</p>"

    rows = "".join(
        "\n            <div>"
        f"\n              <dt>{escape_html(getattr(q, 'label', '') or getattr(q, 'id', ''))}</dt>"
        f"\n              <dd>{format_answer(answers.get(getattr(q, 'id', '')))}</dd>"
        "\n            </div>"
        for q in questions
    )
    return f'\n    <dl class="intake-list">{rows}\n    </dl>\n  '


def _build_print_document(*, title: str, intro: str, body: str) -> str:
    return f"""<!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <title>{escape_html(title)}</title>
        <style>
          body {{ color: #1f2933; font-family: Arial, sans-serif; line-height: 1.5; margin: 32px; }}
          h1 {{ margin-bottom: 4px; }}
          h2 {{ border-bottom: 1px solid #cfd8e3; font-size: 1.05rem; margin-top: 28px; padding-bottom: 6px; }}
          ol {{ padding-left: 24px; }}
          li {{ margin-bottom: 14px; }}
          .meta, .task-details, .notes {{ color: #536574; font-size: 0.92rem; }}
          .task-details {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 3px; }}
          .task-title {{ font-weight: 700; }}
          .intake-list {{ display: grid; gap: 8px; }}
          .intake-list div {{ border-bottom: 1px solid #e3e9ef; padding-bottom: 8px; }}
          .intake-list dt {{ color: #536574; font-weight: 700; }}
          .intake-list dd {{ margin: 2px 0 0; }}
          @media print {{ body {{ margin: 20mm; }} button {{ display: none; }} }}
        </style>
      </head>
      <body>
        <h1>{escape_html(title)}</h1>
        <p class="meta">{escape_html(intro)}</p>
        {body}
      </body>
    </html>"""


def generate_client_request_print_html(
    engagement: IntakeEngagement, *, client_name: str | None = None
) -> str:
    """Printable HTML of the client-facing requests only."""
    workflow = _load_workflow_safe(getattr(engagement, "workflow_key", ""))
    workflow_name = _workflow_name(engagement, workflow)
    label = _display_label(engagement, client_name)
    due_date = format_output_date(getattr(engagement, "due_date", None))

    title = f"Client request list - {label}"
    intro = f"{workflow_name} • Due {due_date} • SAT-C LLP"

    tasks = client_facing_tasks(getattr(engagement, "tasks", None))
    body = (
        _render_task_list(tasks)
        if tasks
        else "<p>There are no client-facing requests for this checklist right now.</p>"
    )
    return _build_print_document(title=title, intro=intro, body=body)


def generate_internal_checklist_print_html(
    engagement: IntakeEngagement, *, client_name: str | None = None
) -> str:
    """Printable internal checklist: risk flags, intake answers, all tasks."""
    workflow = _load_workflow_safe(getattr(engagement, "workflow_key", ""))
    workflow_name = _workflow_name(engagement, workflow)
    label = _display_label(engagement, client_name)
    due_date = format_output_date(getattr(engagement, "due_date", None))

    title = f"Internal checklist - {label}"
    intro = f"{workflow_name} • Due {due_date}"

    body = f"""
    <section>
      <h2>Risk flags</h2>
      {_render_risk_flags(engagement)}
    </section>
    <section>
      <h2>Intake answers</h2>
      {_render_intake_answers(engagement, workflow)}
    </section>
    <section>
      <h2>Tasks</h2>
      {_render_task_list(getattr(engagement, "tasks", None), include_internal_details=True)}
    </section>
  """
    return _build_print_document(title=title, intro=intro, body=body)
