"""CLIENT INTAKE & ENGAGEMENT WORKFLOWS — the front of the funnel.

Where the document pipeline answers "what are the numbers?", this layer answers
"who is the client, what's their situation, and what do we need from them?" It is
ported from the standalone "Workflow Task Checklists" app into SATC's data model:

  * A reusable client index (people + businesses) with RELATIONSHIPS between them
    (spouse, owner, shareholder, partner, ...). Identities live in the vault; the
    relationship graph (by ``client_id``) is non-sensitive and lives in the mart.
  * Engagement WORKFLOWS (1040 core, Schedule C, rental, bookkeeping, S-corp, ...)
    defined as CONFIG (``configs/workflows/*.yaml``). Each carries intake questions
    and conditional tasks with precise client-facing request text.
  * Generated ENGAGEMENTS: answering the intake questions produces a task list,
    relationship-aware reminders (e.g. "track expected K-1 from the S-corp you
    own"), and risk flags. Every client-facing task becomes a ``Requested``
    document so the document pipeline can later mark it ``Received`` — closing the
    loop between "what we asked for" and "what came in".

These dataclasses are SQL-shaped like the rest of :mod:`satc.models`. Free-form
maps (intake answers, risk flags) serialize to JSON text in the store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

# Who a task speaks to. Client-facing tasks drive document requests + client comms;
# internal tasks drive the preparer's own checklist.
TaskAudience = Literal["internal", "client"]

# Relationship kinds in the client graph (ported from the checklist app).
RELATIONSHIP_TYPES = (
    "spouse", "dependent", "owner", "shareholder", "partner",
    "officer", "authorizedContact", "payrollContact", "bookkeeper",
)


# ---------------------------------------------------------------------------
# Workflow definitions (loaded from config — the domain knowledge)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class WorkflowQuestion:
    """One intake question. ``risk_flag`` is raised when answered affirmatively."""

    id: str
    label: str
    type: str = "boolean"          # "boolean" / "yesNo" — answers are "yes"/"no"
    risk_flag: str = ""


@dataclass(slots=True)
class TaskTemplate:
    """A conditional task within a workflow.

    ``condition`` (optional) gates inclusion against the intake answers. For
    client-facing tasks, ``client_request_text`` is the exact ask sent to the
    client and ``doc_type`` is what an arriving document must match to satisfy it.
    """

    template_id: str
    title: str
    category: str = "General"
    audience: TaskAudience = "internal"
    days_before_due: int = 0
    condition: dict[str, Any] | None = None
    client_request_text: str = ""
    accepted_alternatives: str = ""
    why_needed: str = ""
    internal_instructions: str = ""
    doc_type: str = ""             # for received-matching; defaults to title


@dataclass(slots=True)
class WorkflowDef:
    """A whole engagement workflow, loaded from ``configs/workflows/<key>.yaml``."""

    key: str
    name: str
    description: str = ""
    engagement_type: str = ""
    client_type: str = ""          # "person" | "business" | "" (any)
    questions: list[WorkflowQuestion] = field(default_factory=list)
    tasks: list[TaskTemplate] = field(default_factory=list)

    def question(self, qid: str) -> WorkflowQuestion | None:
        return next((q for q in self.questions if q.id == qid), None)


# ---------------------------------------------------------------------------
# Persisted records (one per SQL table)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Relationship:
    """An edge in the client graph. PK = ``rel_id``. Keyed by client_id (non-PII)."""

    rel_id: str
    from_client_id: str
    to_client_id: str
    relationship_type: str
    ownership_pct: str = ""
    is_primary: bool = False
    note: str = ""


@dataclass(slots=True)
class IntakeTask:
    """A generated task on an engagement. PK = ``task_id``.

    A client-facing task is linked to the ``Requested`` document it created via
    ``document_id``; when that document is later received, the task completes.
    """

    task_id: str
    engagement_id: str
    template_id: str
    title: str
    category: str = "General"
    audience: TaskAudience = "internal"
    client_request_text: str = ""
    accepted_alternatives: str = ""
    why_needed: str = ""
    internal_instructions: str = ""
    suggested_date: date | None = None
    completed: bool = False
    notes: str = ""
    relationship_generated: bool = False
    document_id: str = ""          # links a client request to its DocumentRecord


@dataclass(slots=True)
class IntakeEngagement:
    """A generated engagement (a workflow instance). PK = ``engagement_id``."""

    engagement_id: str
    client_id: str
    workflow_key: str
    engagement_type: str = ""
    tax_year: int | None = None
    period_end: str = ""
    due_date: date | None = None
    intake_answers: dict[str, str] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    tasks: list[IntakeTask] = field(default_factory=list)
