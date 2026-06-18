"""Workflow engine — load workflow configs and generate engagement task lists.

A faithful Python port of the checklist app's rules engine:

  * conditional task inclusion (``all`` / ``any`` / ``equals`` / ...),
  * date math relative to a single due date (``days_before_due``),
  * risk-flag generation from affirmative answers and linked entities,
  * relationship-aware tasks (K-1 reminders between a person and the S-corp /
    partnership they own),
  * regeneration that PRESERVES completion state + notes by ``template_id`` when
    intake answers change — re-running the interview never wipes progress.

Workflow definitions live in ``configs/workflows/*.yaml`` so the domain knowledge
is config, not code (mirroring SATC's extraction/classification configs).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from satc.config import CONFIG_ROOT, ConfigError, _load_yaml
from satc.ids import opaque_id
from satc.models.intake import (
    IntakeEngagement,
    IntakeTask,
    TaskTemplate,
    WorkflowDef,
    WorkflowQuestion,
)

_WORKFLOW_DIR = "workflows"

# Which workflows are offered for each client type (drives the intake UI).
WORKFLOW_KEYS_BY_CLIENT_TYPE: dict[str, list[str]] = {
    "person": ["personal_1040_core", "personal_schedule_c", "personal_rental_schedule_e"],
    "business": ["business_monthly_bookkeeping", "business_year_end_cleanup",
                 "business_scorp_tax", "business_partnership_tax"],
}


# ---------------------------------------------------------------------------
# Loading workflow configs
# ---------------------------------------------------------------------------

def _workflow_path(key: str, config_root: Path | None) -> Path:
    return (config_root or CONFIG_ROOT) / _WORKFLOW_DIR / f"{key}.yaml"


def load_workflow(key: str, config_root: Path | None = None) -> WorkflowDef:
    """Load one workflow definition from ``configs/workflows/<key>.yaml``."""
    data = _load_yaml(_workflow_path(key, config_root))
    questions = [WorkflowQuestion(
        id=q["id"], label=q.get("label", q["id"]),
        type=str(q.get("type", "boolean")), risk_flag=q.get("risk_flag") or "",
    ) for q in data.get("questions", [])]
    tasks = [TaskTemplate(
        template_id=t["template_id"], title=t["title"],
        category=t.get("category", "General"), audience=t.get("audience", "internal"),
        days_before_due=int(t.get("days_before_due", 0)), condition=t.get("condition"),
        client_request_text=t.get("client_request_text", ""),
        accepted_alternatives=t.get("accepted_alternatives", ""),
        why_needed=t.get("why_needed", ""),
        internal_instructions=t.get("internal_instructions", ""),
        doc_type=t.get("doc_type", "") or t["title"],
    ) for t in data.get("tasks", [])]
    return WorkflowDef(
        key=data.get("key", key), name=data["name"], description=data.get("description", ""),
        engagement_type=data.get("engagement_type", key), client_type=data.get("client_type", ""),
        questions=questions, tasks=tasks,
    )


def list_workflows(config_root: Path | None = None) -> list[WorkflowDef]:
    """Load every workflow config found on disk."""
    root = (config_root or CONFIG_ROOT) / _WORKFLOW_DIR
    if not root.is_dir():
        return []
    return [load_workflow(p.stem, config_root) for p in sorted(root.glob("*.yaml"))]


def workflows_for_client_type(client_type: str, config_root: Path | None = None) -> list[WorkflowDef]:
    """Workflows offered for a person or business (keeps personal/entity work apart)."""
    keys = WORKFLOW_KEYS_BY_CLIENT_TYPE.get(client_type, [])
    out: list[WorkflowDef] = []
    for key in keys:
        try:
            out.append(load_workflow(key, config_root))
        except ConfigError:
            continue
    return out


# ---------------------------------------------------------------------------
# Rules engine
# ---------------------------------------------------------------------------

def evaluate_condition(condition: dict[str, Any] | None, answers: dict[str, Any]) -> bool:
    """Evaluate a task's inclusion condition against the intake answers."""
    if not condition:
        return True
    if "all" in condition:
        return all(evaluate_condition(c, answers) for c in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(c, answers) for c in condition["any"])

    value = answers.get(condition.get("question_id"))
    if "equals" in condition:
        return value == condition["equals"]
    if "not_equals" in condition:
        return value != condition["not_equals"]
    if "includes" in condition:
        needle = condition["includes"]
        return needle in value if isinstance(value, (list, tuple)) else needle in str(value or "")
    if "greater_than" in condition:
        return _num(value) > _num(condition["greater_than"])
    if "less_than" in condition:
        return _num(value) < _num(condition["less_than"])
    return True


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_truthy(value: Any) -> bool:
    return value in (True, "yes", "true") or _num(value) > 0


def calculate_suggested_date(due_date: date | str, days_before_due: int) -> date:
    """A task's suggested date: ``days_before_due`` days ahead of the due date."""
    if isinstance(due_date, str):
        if not due_date.strip():
            raise ValueError("A valid due date is required.")
        due_date = date.fromisoformat(due_date)
    return due_date - timedelta(days=int(days_before_due))


def _normalize_answers(workflow: WorkflowDef, answers: dict[str, Any]) -> dict[str, str]:
    """Keep only the workflow's own questions; default missing answers to ''."""
    return {q.id: answers.get(q.id, "") for q in workflow.questions}


def generate_risk_flags(workflow: WorkflowDef, answers: dict[str, Any], *,
                        linked_clients: list[Any] | None = None,
                        relationships: list[Any] | None = None) -> list[str]:
    """Risk flags from affirmative risk questions plus linked-entity heuristics."""
    flags: list[str] = []

    def add(flag: str) -> None:
        if flag and flag not in flags:
            flags.append(flag)

    for q in workflow.questions:
        if q.risk_flag and _is_truthy(answers.get(q.id)):
            add(q.risk_flag)

    if workflow.key == "personal_1040_core":
        for client in (linked_clients or []):
            treatment = getattr(client, "tax_treatment", "")
            if treatment == "sCorp":
                add("S-corp shareholder basis review")
            elif treatment == "partnership":
                add("Partnership K-1 receipt review")

    if workflow.key in ("business_scorp_tax", "business_partnership_tax"):
        if any(getattr(r, "relationship_type", "") in ("owner", "shareholder", "partner")
               for r in (relationships or [])):
            add("Linked owner K-1 delivery")

    return flags


# ---------------------------------------------------------------------------
# Task + engagement construction
# ---------------------------------------------------------------------------

def _make_task(engagement_id: str, template: TaskTemplate, due_date: date | str, *,
               existing: IntakeTask | None, relationship_generated: bool = False) -> IntakeTask:
    return IntakeTask(
        task_id=existing.task_id if existing else opaque_id("task"),
        engagement_id=engagement_id,
        template_id=template.template_id,
        title=template.title,
        category=template.category,
        audience=template.audience,
        client_request_text=template.client_request_text,
        accepted_alternatives=template.accepted_alternatives,
        why_needed=template.why_needed,
        internal_instructions=template.internal_instructions,
        suggested_date=calculate_suggested_date(due_date, template.days_before_due),
        completed=existing.completed if existing else False,
        notes=existing.notes if existing else "",
        relationship_generated=relationship_generated,
        document_id=existing.document_id if existing else "",
    )


def _build_workflow_tasks(workflow: WorkflowDef, engagement_id: str, due_date: date | str,
                          answers: dict[str, str], existing: dict[str, IntakeTask]) -> list[IntakeTask]:
    return [_make_task(engagement_id, t, due_date, existing=existing.get(t.template_id))
            for t in workflow.tasks if evaluate_condition(t.condition, answers)]


def _relationship_templates(workflow_key: str, *, linked_clients: list[Any],
                            relationships: list[Any], tax_year: Any,
                            existing_engagements: list[Any]) -> list[TaskTemplate]:
    """Relationship-aware reminder templates (K-1 flow between linked entities)."""
    templates: list[TaskTemplate] = []

    if workflow_key == "personal_1040_core":
        for client in linked_clients:
            if getattr(client, "client_type", "") != "business":
                continue
            name = getattr(client, "display_name", getattr(client, "client_id", "linked entity"))
            treatment = getattr(client, "tax_treatment", "")
            cid = getattr(client, "client_id", name)
            if treatment in ("sCorp", "partnership"):
                kind = "S-corp" if treatment == "sCorp" else "partnership"
                templates.append(TaskTemplate(
                    template_id=f"relationship-personal-1040-k1-{cid}",
                    title=f"Track expected K-1 from {name}",
                    category="Linked client reminders", audience="internal", days_before_due=10,
                    internal_instructions=f"Confirm final {kind} K-1 is received from {name}."))
            if treatment == "sCorp":
                templates.append(TaskTemplate(
                    template_id=f"relationship-personal-1040-7203-{cid}",
                    title=f"Review shareholder basis support for {name}",
                    category="Linked client reminders", audience="internal", days_before_due=9,
                    internal_instructions=f"Review whether Form 7203/shareholder basis support is "
                                          f"needed for {name}."))
            elif treatment == "partnership":
                templates.append(TaskTemplate(
                    template_id=f"relationship-personal-1040-partnership-k1-{cid}",
                    title=f"Confirm partnership K-1 reporting for {name}",
                    category="Linked client reminders", audience="internal", days_before_due=9,
                    internal_instructions=f"Confirm partnership K-1 state and passive activity "
                                          f"details for {name}."))

    if workflow_key in ("business_scorp_tax", "business_partnership_tax"):
        owner_ids = {r.from_client_id for r in relationships
                     if getattr(r, "relationship_type", "") in ("owner", "shareholder", "partner")}
        owner_ids |= {r.to_client_id for r in relationships
                      if getattr(r, "relationship_type", "") in ("owner", "shareholder", "partner")}
        for owner in linked_clients:
            cid = getattr(owner, "client_id", "")
            if getattr(owner, "client_type", "") != "person" or cid not in owner_ids:
                continue
            name = getattr(owner, "display_name", cid)
            feeds = any(getattr(e, "client_id", "") == cid
                        and getattr(e, "engagement_type", "") == "personal1040Core"
                        and str(getattr(e, "tax_year", "")) == str(tax_year or "")
                        for e in existing_engagements)
            templates.append(TaskTemplate(
                template_id=f"relationship-business-deliver-k1-{cid}",
                title=f"Deliver final K-1 to {name}",
                category="Linked owner reminders", audience="internal", days_before_due=5,
                internal_instructions=(f"Feeds linked personal return for {name}. Deliver final K-1 "
                                       "and mark owner follow-up complete." if feeds else
                                       f"Deliver final K-1 to {name} and note whether a linked "
                                       "personal return is needed.")))
    return templates


def build_engagement(workflow: WorkflowDef, *, client_id: str, due_date: date | str,
                     answers: dict[str, Any] | None = None, tax_year: int | None = None,
                     period_end: str = "", linked_clients: list[Any] | None = None,
                     relationships: list[Any] | None = None,
                     existing_engagements: list[Any] | None = None,
                     existing_tasks: list[IntakeTask] | None = None,
                     engagement_id: str | None = None,
                     created_at: str = "", now: str | None = None) -> IntakeEngagement:
    """Generate a full engagement: conditional tasks + relationship tasks + risk flags."""
    from datetime import datetime, timezone

    stamp = now or datetime.now(timezone.utc).isoformat()
    eng_id = engagement_id or opaque_id("engagement")
    normalized = _normalize_answers(workflow, answers or {})
    existing_by_template = {t.template_id: t for t in (existing_tasks or []) if t.template_id}

    tasks = _build_workflow_tasks(workflow, eng_id, due_date, normalized, existing_by_template)
    for tmpl in _relationship_templates(
            workflow.key, linked_clients=linked_clients or [], relationships=relationships or [],
            tax_year=tax_year, existing_engagements=existing_engagements or []):
        tasks.append(_make_task(eng_id, tmpl, due_date,
                                existing=existing_by_template.get(tmpl.template_id),
                                relationship_generated=True))

    flags = generate_risk_flags(workflow, normalized,
                                linked_clients=linked_clients, relationships=relationships)
    due = date.fromisoformat(due_date) if isinstance(due_date, str) else due_date
    return IntakeEngagement(
        engagement_id=eng_id, client_id=client_id, workflow_key=workflow.key,
        engagement_type=workflow.engagement_type, tax_year=tax_year, period_end=period_end,
        due_date=due, intake_answers=normalized, risk_flags=flags,
        created_at=created_at or stamp, updated_at=stamp, tasks=tasks)


def regenerate_engagement(engagement: IntakeEngagement, workflow: WorkflowDef, *,
                          answers: dict[str, Any] | None = None,
                          due_date: date | str | None = None, **context: Any) -> IntakeEngagement:
    """Rebuild an engagement after intake answers change, preserving task progress."""
    return build_engagement(
        workflow,
        client_id=engagement.client_id,
        due_date=due_date or engagement.due_date,
        answers=answers if answers is not None else engagement.intake_answers,
        tax_year=context.get("tax_year", engagement.tax_year),
        period_end=context.get("period_end", engagement.period_end),
        linked_clients=context.get("linked_clients"),
        relationships=context.get("relationships"),
        existing_engagements=context.get("existing_engagements"),
        existing_tasks=engagement.tasks,
        engagement_id=engagement.engagement_id,
        created_at=engagement.created_at)
