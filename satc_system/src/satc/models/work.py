"""WORK — the engagement (a contract), the job (an instance), the task (a unit).

Three words that were previously two, one of which meant two things.
``EngagementRecord`` (fee + letter status) and ``IntakeEngagement`` (a workflow
instance with tasks) were unrelated concepts sharing the word "engagement", so
every conversation about "the engagement" was ambiguous. And ``IntakeTask``
carried ``completed: bool`` — while the document it pointed at had five states.

Now:

* **Engagement** — the CONTRACT. Scope, fee, letter status, document cutoff.
  One per client per year. Slow-moving.
* **Job** — an INSTANCE of work discharging one obligation, running a workflow
  from config. This is what has a stage and a due date.
* **Task** — one unit of assignable work inside a job.

The distinction that matters most is on Task. A boolean can express "done" and
"not done", and a practice needs at least: blocked on something else, waiting on
the client, waived because it does not apply this year, and cancelled. Those are
not shades of "not done" — they are different facts, and the difference decides
whether the job can advance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from satc.models.actor import Actor

TaskStatus = Literal[
    "not_started",
    "in_progress",
    "waiting_on_client",   # we have asked; the ball is with them
    "blocked",             # something else must finish first
    "awaiting_review",
    "done",
    "waived",              # does not apply this year — WITH a reason
    "cancelled",
]

# States in which a task no longer holds anything up.
_SETTLED = {"done", "waived", "cancelled"}

TaskAudience = Literal["internal", "client"]

JobStage = Literal[
    "not_started",
    "waiting_on_documents",
    "prep_ready",
    "in_prep",
    "in_review",
    "ready_to_deliver",
    "delivered",
    "complete",
]
"""The INTERNAL stage — what the owner does next.

Deliberately not the client-facing status and deliberately not the filing truth
(Drake's ACK letter). Three authorities, three fields; collapsing them is what
made the old PipelineStatus say "Filed" at transmission, which IRS Pub 1345
contradicts — a return is not filed until the IRS acknowledges it.
"""


@dataclass(slots=True)
class Completion:
    """How a task was finished — never a bare checkbox.

    ``procedure`` exists because "marked reviewed without documenting what was
    actually performed" is a named junior failure mode. A tick that records
    nothing is indistinguishable from a tick someone applied to clear a screen.
    """

    by: Actor
    at: datetime
    procedure: str = ""


@dataclass(slots=True)
class Task:
    """One unit of assignable work inside a job. PK = ``task_id``."""

    task_id: str
    job_id: str
    template_id: str
    """Preserved across regeneration, so re-running the interview keeps progress."""

    title: str
    category: str = "General"
    audience: TaskAudience = "internal"
    status: TaskStatus = "not_started"
    client_request_text: str = ""
    accepted_alternatives: str = ""
    why_needed: str = ""
    internal_instructions: str = ""

    due_date: date | None = None
    """The REAL date this is due. Distinct from the derived hint below —
    previously there was only the hint, so nothing was ever actually overdue."""

    suggested_date: date | None = None
    blocked_by: tuple[str, ...] = ()
    waived_reason: str = ""
    follow_up_round: int = 0
    """Which chase this is. A second request must not read like the first."""

    escalated_at: date | None = None
    request_id: str = ""
    """The RequestedItem this task opened, when it is a client ask."""

    completion: Completion | None = None
    notes: str = ""
    relationship_generated: bool = False

    @property
    def is_settled(self) -> bool:
        """Whether this task is no longer holding anything up."""
        return self.status in _SETTLED

    @property
    def is_open(self) -> bool:
        return not self.is_settled

    @property
    def is_done(self) -> bool:
        """Genuinely finished — NOT waived or cancelled.

        Kept separate from :attr:`is_settled` because a progress count that
        treats "waived" as "done" flatters the number.
        """
        return self.status == "done"

    def is_overdue(self, today: date) -> bool:
        return self.is_open and self.due_date is not None and self.due_date < today


class WorkError(Exception):
    """A work item was asked to enter a state it may not."""


def complete(task: Task, *, actor: Actor, procedure: str = "",
             now: datetime | None = None) -> Task:
    """Finish a task, recording who and what they actually did."""
    from satc.models.actor import require_human

    require_human(actor, "complete a task",
                  instead="propose it as done and let the owner confirm")
    task.status = "done"
    task.completion = Completion(by=actor, at=now or datetime.now(), procedure=procedure)
    return task


def waive(task: Task, *, actor: Actor, reason: str,
          now: datetime | None = None) -> Task:
    """Set a task aside as not applicable — with a reason, always.

    The same refusal as :func:`~satc.models.evidence.mark_not_applicable`, for
    the same reason: a waived task with no reason is indistinguishable from one
    someone clicked past.
    """
    from satc.models.actor import require_human

    require_human(actor, "waive a task")
    if not (reason or "").strip():
        raise WorkError(
            f"Cannot waive {task.title!r} without a reason. Record why it does not "
            f"apply — that note is what makes the skip defensible later.")
    task.status = "waived"
    task.waived_reason = reason.strip()
    task.completion = Completion(by=actor, at=now or datetime.now(),
                                 procedure=f"waived: {reason.strip()}")
    return task


@dataclass(slots=True)
class Job:
    """A work instance discharging one obligation. PK = ``job_id``.

    Was ``IntakeEngagement``. Renamed because it is not the contract — it is one
    run of work against one duty, and a client can have several in a year.
    """

    job_id: str
    client_id: str
    workflow_key: str
    obligation_key: str = ""
    """Which duty this job discharges. Empty for ad-hoc work with no statutory
    deadline behind it (a notice response, a one-off question)."""

    period_key: str = ""
    """``2025``, ``2026Q1``, ``2026-03`` — the recurrence anchor, and the thing
    that makes regeneration idempotent."""

    engagement_type: str = ""
    tax_year: int | None = None
    due_date: date | None = None
    stage: JobStage = "not_started"
    intake_answers: dict[str, str] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    tasks: list[Task] = field(default_factory=list)

    # -- derived ----------------------------------------------------------

    def client_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.audience == "client"]

    def open_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.is_open]

    def done_count(self) -> int:
        """Genuinely finished tasks.

        Computed here rather than in a template. ``selectattr('completed')``
        over a STATUS string counts every task as done, because any non-empty
        string is truthy — a 200 with a wrong number, which is the worst kind
        of failure and the one the old templates would have hit silently.
        """
        return sum(1 for t in self.tasks if t.is_done)

    def settled_count(self) -> int:
        return sum(1 for t in self.tasks if t.is_settled)

    def progress(self) -> tuple[int, int]:
        """(settled, total) — what a progress bar should show."""
        return self.settled_count(), len(self.tasks)

    def overdue_tasks(self, today: date) -> list[Task]:
        return [t for t in self.tasks if t.is_overdue(today)]

    def is_blocked(self) -> bool:
        return any(t.status == "blocked" for t in self.tasks)


@dataclass(slots=True)
class Engagement:
    """The CONTRACT with a client for a period. PK = (client_id, tax_year).

    Was ``EngagementRecord``. Deliberately unchanged in shape: it has exactly
    one producer (the fixtures) and two readers, so widening it now would add
    columns nothing writes. Renamed only, so that "engagement" means one thing.
    """

    client_id: str
    tax_year: int
    engagement_letter_status: str = "Not sent"   # Not sent / Sent / Signed
    fee_amount: Any = None
    invoiced: bool = False
    paid: bool = False
    preparer_id: str = ""
    note: str = ""
