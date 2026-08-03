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

import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from satc.config import CONFIG_ROOT, ConfigError, _load_yaml
from satc.ids import opaque_id
from satc.models.intake import (
    TaskTemplate,
    WorkflowDef,
    WorkflowQuestion,
)
from satc.models.work import Job, Task

_WORKFLOW_DIR = "workflows"

# The intake question that gates the NEW-vs-RETURNING branch. It is asked first,
# outside the question table, and its answer ("yes" = new) drives prior-year asks.
NEW_CLIENT_GATE = "newSatcClient"

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
    path = _workflow_path(key, config_root)
    data = _load_yaml(path)
    validate_conditions(data, path)
    questions = [WorkflowQuestion(
        id=q["id"], label=q.get("label", q["id"]),
        type=str(q.get("type", "boolean")), risk_flag=q.get("risk_flag") or "",
        change_label=q.get("change_label") or "",
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
    wf = WorkflowDef(
        key=data.get("key", key), name=data["name"], description=data.get("description", ""),
        engagement_type=data.get("engagement_type", key), client_type=data.get("client_type", ""),
        questions=questions, tasks=tasks,
    )
    if _OVERRIDE_PROVIDER is not None:        # apply the practice's in-app edits
        try:
            overrides = _OVERRIDE_PROVIDER(wf.key)
        except Exception:  # noqa: BLE001 - never let a bad override break loading
            overrides = None
        if overrides:
            apply_overrides(wf, overrides)
    return wf


# ---------------------------------------------------------------------------
# Practice customization — overrides layered on top of the built-in workflows
# ---------------------------------------------------------------------------

# A callable (workflow_key) -> override dict | None, set by the app from the store.
_OVERRIDE_PROVIDER = None


def set_override_provider(provider) -> None:
    """Register where per-workflow overrides come from (e.g. the SQLite store)."""
    global _OVERRIDE_PROVIDER
    _OVERRIDE_PROVIDER = provider


def apply_overrides(wf: WorkflowDef, ov: dict) -> None:
    """Mutate a workflow in place with the practice's edits.

    Override shape (all keys optional)::

        {"name": "...",
         "questions": {"<id>": {"label": "...", "risk_flag": "...", "disabled": true}},
         "tasks": {"<template_id>": {"client_request_text": "...", "category": "...",
                                     "why_needed": "...", "doc_type": "...", "disabled": true}},
         "added_questions": [{"id": "...", "label": "...", "risk_flag": "...",
                              "request": {"title": "...", "category": "...",
                                          "client_request_text": "...", "doc_type": "...",
                                          "days_before_due": 14}}]}
    """
    if ov.get("name"):
        wf.name = ov["name"]

    q_edits = ov.get("questions", {})
    kept_q: list[WorkflowQuestion] = []
    for q in wf.questions:
        edit = q_edits.get(q.id, {})
        if edit.get("disabled"):
            continue
        q.label = edit.get("label", q.label)
        if "risk_flag" in edit:
            q.risk_flag = edit["risk_flag"] or ""
        kept_q.append(q)
    wf.questions = kept_q

    t_edits = ov.get("tasks", {})
    kept_t: list[TaskTemplate] = []
    for t in wf.tasks:
        edit = t_edits.get(t.template_id, {})
        if edit.get("disabled"):
            continue
        t.client_request_text = edit.get("client_request_text", t.client_request_text)
        t.category = edit.get("category", t.category)
        t.why_needed = edit.get("why_needed", t.why_needed)
        t.doc_type = edit.get("doc_type", t.doc_type)
        kept_t.append(t)
    wf.tasks = kept_t

    for added in ov.get("added_questions", []):
        qid = str(added.get("id", "")).strip()
        if not qid:
            continue
        wf.questions.append(WorkflowQuestion(
            id=qid, label=added.get("label", qid), risk_flag=added.get("risk_flag") or ""))
        req = added.get("request") or {}
        wf.tasks.append(TaskTemplate(
            template_id=f"custom-{qid}", title=req.get("title", added.get("label", qid)),
            category=req.get("category", "Custom"), audience="client",
            days_before_due=int(req.get("days_before_due", 14)),
            condition={"question_id": qid, "equals": "yes"},
            client_request_text=req.get("client_request_text", ""),
            doc_type=req.get("doc_type", "") or req.get("title", qid)))


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
# The condition grammar — one file, one validation, both blocks
# ---------------------------------------------------------------------------

# The whole grammar, as :func:`evaluate_condition` actually implements it.
# Written down because a workflow file is hand-edited and the engine is SILENT
# about a word it does not recognise: an unreadable test falls off the end of
# the ladder and reads as True.
CONDITION_OPERATORS = ("equals", "not_equals", "includes", "greater_than", "less_than")
CONDITION_BRANCHES = ("all", "any")

# The two blocks that gate on this grammar, and what a gate the engine cannot
# read would do in each. The words differ because the damage differs — a task
# that goes unconditional is a document every client is chased for, a service
# that goes unconditional is money on every quote — and principle 10 wants the
# reader's own sentence, not a generic one.
_GATED_BLOCKS = {
    "tasks": {
        "unconditional": "leave condition: out to generate it for every client",
        "always_true": ("so {name} would be generated for EVERY client — a "
                        "conditional ask silently turned into one nobody chose"),
    },
    "services": {
        "unconditional": "leave condition: out to price it on every engagement",
        "always_true": ("so {name} would be on every quote with a reason that "
                        "is not true of the client reading it"),
    },
}


def check_condition(node: Any, *, asked: set[str], block: str, name: str,
                    path: Path) -> None:
    """Refuse a gate the engine would silently misread.

    Two typos matter here and both are quiet. A ``question_id`` this workflow
    does not ask consults nothing, so the leaf reads as an unanswered question
    forever — an ask that can never fire, or a ``not_equals`` leaf that used to
    always fire. A misspelled OPERATOR is worse still: :func:`evaluate_condition`
    falls off the end of its ladder and returns ``True``, so the gate is open for
    everybody.

    A workflow file is meant to be hand-edited, so a typo is an ordinary event
    rather than an exceptional one, and an ordinary event that silently generates
    work — or prices it — is the kind of quiet this system is built not to have.
    Principles 5 and 10: refuse it, and name the file, the entry and the fix.
    """
    words = _GATED_BLOCKS[block]
    where = f"{name!r} in the {block}: block"
    if node is None or node == {}:
        return                                   # no gate at all: applies always
    if not isinstance(node, dict):
        raise ConfigError(
            f"{path.name} gates {where} on {node!r}, which is not a condition. "
            f"Write a mapping like {{question_id: movedStates, equals: \"yes\"}}, "
            f"or {words['unconditional']}.")

    branches = [key for key in CONDITION_BRANCHES if key in node]
    if branches:
        extra = sorted(set(node) - set(branches))
        if len(branches) > 1 or extra:
            raise ConfigError(
                f"{path.name} gates {where} on a condition combining "
                f"{', '.join(sorted(branches) + extra)}. A condition is EITHER one "
                f"'all:'/'any:' branch OR one question test — the engine reads the "
                f"branch and ignores everything beside it, which is a gate nobody "
                f"reviewing this file would predict.")
        children = node[branches[0]]
        if not isinstance(children, list) or not children:
            raise ConfigError(
                f"{path.name} gates {where} on an empty {branches[0]!r}. List the "
                f"conditions it combines, or {words['unconditional']}.")
        for child in children:
            check_condition(child, asked=asked, block=block, name=name, path=path)
        return

    qid = str(node.get("question_id", "")).strip()
    if not qid:
        raise ConfigError(
            f"{path.name} gates {where} on {node!r}, which names no question_id. "
            f"Name a question from this workflow's questions: block.")
    if qid not in asked:
        raise ConfigError(
            f"{path.name} gates {where} on question {qid!r}, which this workflow "
            f"does not ask. It asks: {', '.join(sorted(asked)) or 'nothing'}. "
            f"Correct the spelling in the {block}: block, or add the question to "
            f"questions: — a gate on a question nobody is asked is answered by "
            f"silence, and silence is not an answer.")
    used = [op for op in CONDITION_OPERATORS if op in node]
    if len(used) != 1:
        seen = sorted(set(node) - {"question_id"})
        raise ConfigError(
            f"{path.name} tests {qid!r} for {where} with "
            f"{', '.join(seen) if seen else 'no comparison at all'}, which the "
            f"engine does not understand. Use exactly one of: "
            f"{', '.join(CONDITION_OPERATORS)}. A test it cannot read is TRUE for "
            f"everybody, {words['always_true'].format(name=repr(name))}.")


def validate_conditions(data: dict[str, Any], path: Path) -> None:
    """Check EVERY gate in a workflow file — ``tasks:`` and ``services:`` alike.

    This lived in :func:`~satc.billing.quote.load_service_map` and so guarded the
    ``services:`` block only. The SAME typo in a ``tasks:`` condition in the SAME
    hand-edited file was accepted in silence, and a mistyped operator turns a
    conditional task UNCONDITIONAL — the document request goes to every client.
    A guard on one of two paths through one file is not a guard.

    So it lives here, where both readers pass: :func:`load_workflow` reads the
    file for what to ask and chase, ``load_service_map`` reads it for what the
    answers cost, and either door validates the whole file.

    Read from the RAW data rather than a loaded :class:`WorkflowDef`, because the
    typo being caught lives in the file: a question the practice has disabled
    through an override is a different conversation from one never written down.
    """
    asked = {str(q.get("id", "")).strip() for q in (data.get("questions") or [])
             if isinstance(q, dict)} - {""}
    for block, id_key, unnamed in (("tasks", "template_id", "(a task with no template_id)"),
                                   ("services", "service", "(a service with no code)")):
        for entry in data.get(block) or []:
            if not isinstance(entry, dict):
                # The SHAPE of an entry is the loader's complaint, and each
                # loader says something better about its own block than a
                # condition checker could.
                continue
            check_condition(entry.get("condition"), asked=asked, block=block,
                            name=str(entry.get(id_key, "")).strip() or unnamed,
                            path=path)


# ---------------------------------------------------------------------------
# Rules engine
# ---------------------------------------------------------------------------

def answered(value: Any) -> bool:
    """Whether the interview holds an answer at all.

    ``None`` is a question never asked and ``""`` is one the form submitted
    empty — :func:`_normalize_answers` produces the second for every question a
    client skipped. Neither is a fact about the client.
    """
    return value is not None and str(value).strip() != ""


def _evaluate(condition: dict[str, Any] | None, answers: dict[str, Any], *,
              strict: bool) -> bool:
    """The condition ladder. ``strict`` says what an UNANSWERED leaf does.

    ``strict=True`` is the engine's answer to "does this apply": silence
    satisfies nothing. ``strict=False`` is the old reading, kept only so
    :func:`condition_holds_by_silence` can tell the two apart — it is not a
    semantics any caller should act on.
    """
    if not condition:
        return True
    if "all" in condition:
        return all(_evaluate(c, answers, strict=strict) for c in condition["all"])
    if "any" in condition:
        return any(_evaluate(c, answers, strict=strict) for c in condition["any"])

    value = answers.get(condition.get("question_id"))
    if strict and not answered(value):
        # Principle 2. An unanswered question is not an answer, and it is not an
        # answer in EITHER direction: `not_equals: "no"` was satisfied by silence,
        # so a client was asked for a document because they had NOT said
        # something. `less_than: 100` was too, because a missing answer numbered
        # zero. Nobody has said anything, so nothing has been decided.
        return False
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


def evaluate_condition(condition: dict[str, Any] | None, answers: dict[str, Any]) -> bool:
    """Does this gate apply to this client, on what the client has actually said?

    Silence satisfies nothing. Every caller that DOES something on the strength
    of a gate — generating a task, minting a document request, putting money on
    a quote — reads this one, so no path can be walked through by leaving the
    interview blank.
    """
    return _evaluate(condition, answers, strict=True)


def condition_holds_by_silence(condition: dict[str, Any] | None,
                               answers: dict[str, Any]) -> bool:
    """True when a gate is satisfied ONLY because a question is unanswered.

    Not a second opinion about whether the gate applies — the answer to that is
    still no. It is the third state between yes and no: nobody has said. A
    caller that must not ACT on silence ignores it; a caller that must not
    silently DROP what the silence is hiding — the quote, where a $145 service
    vanishing from an estimate is principle 1 in the other direction — shows it,
    unpriced, naming the question still to answer.
    """
    return (_evaluate(condition, answers, strict=False)
            and not _evaluate(condition, answers, strict=True))


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

def task_id_for(job_id: str, template_id: str) -> str:
    """A task's id, derived from WHAT IT IS: this template, on this job.

    Principle 8. A uuid minted per call meant re-running the interview without
    the previous task rows in hand produced a whole new set of ids for the same
    work — so anything holding a task id (a RequestedItem, a note, an audit
    row) pointed at a task that no longer existed. Same job, same template,
    same id, on every machine and every run.

    Falls back to a uuid only for a template with no id at all, which the
    config loader does not produce.
    """
    if not template_id:
        return opaque_id("task")
    blob = f"{job_id}|{template_id}".encode("utf-8")
    return f"task-{hashlib.sha256(blob).hexdigest()[:16]}"


def _make_task(job_id: str, template: TaskTemplate, due_date: date | str, *,
               existing: Task | None, relationship_generated: bool = False) -> Task:
    return Task(
        task_id=(existing.task_id if existing
                 else task_id_for(job_id, template.template_id)),
        job_id=job_id,
        template_id=template.template_id,
        title=template.title,
        category=template.category,
        audience=template.audience,
        client_request_text=template.client_request_text,
        accepted_alternatives=template.accepted_alternatives,
        why_needed=template.why_needed,
        internal_instructions=template.internal_instructions,
        suggested_date=calculate_suggested_date(due_date, template.days_before_due),
        status=existing.status if existing else "not_started",
        notes=existing.notes if existing else "",
        relationship_generated=relationship_generated,
        request_id=existing.request_id if existing else "",
    )


def _build_workflow_tasks(workflow: WorkflowDef, job_id: str, due_date: date | str,
                          answers: dict[str, str], existing: dict[str, Task]) -> list[Task]:
    return [_make_task(job_id, t, due_date, existing=existing.get(t.template_id))
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
                     period_key: str = "", linked_clients: list[Any] | None = None,
                     relationships: list[Any] | None = None,
                     existing_engagements: list[Any] | None = None,
                     existing_tasks: list[Task] | None = None,
                     job_id: str | None = None,
                     created_at: str = "", now: str | None = None) -> Job:
    """Generate a full engagement: conditional tasks + relationship tasks + risk flags."""
    from datetime import datetime, timezone

    stamp = now or datetime.now(timezone.utc).isoformat()
    eng_id = job_id or opaque_id("engagement")
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
    return Job(
        job_id=eng_id, client_id=client_id, workflow_key=workflow.key,
        engagement_type=workflow.engagement_type, tax_year=tax_year, period_key=period_key,
        due_date=due, intake_answers=normalized, risk_flags=flags,
        created_at=created_at or stamp, updated_at=stamp, tasks=tasks)


def regenerate_engagement(engagement: Job, workflow: WorkflowDef, *,
                          answers: dict[str, Any] | None = None,
                          due_date: date | str | None = None, **context: Any) -> Job:
    """Rebuild an engagement after intake answers change, preserving task progress."""
    return build_engagement(
        workflow,
        client_id=engagement.client_id,
        due_date=due_date or engagement.due_date,
        answers=answers if answers is not None else engagement.intake_answers,
        tax_year=context.get("tax_year", engagement.tax_year),
        period_key=context.get("period_key", engagement.period_key),
        linked_clients=context.get("linked_clients"),
        relationships=context.get("relationships"),
        existing_engagements=context.get("existing_engagements"),
        existing_tasks=engagement.tasks,
        job_id=engagement.job_id,
        created_at=engagement.created_at)
