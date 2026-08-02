"""Where a job actually stands — DERIVED from facts, never set by hand.

``Job.stage`` had no producer, and that was the design telling us something
rather than a gap to fill with a setter. Look at what the stages are:

    waiting_on_documents   a blocking request is still outstanding
    prep_ready             everything blocking is in hand, nothing started
    in_prep                internal work is under way
    in_review              the preparing is settled, the review is not
    ready_to_deliver       every internal task is settled

Each of those is a CONCLUSION from facts the practice already records. Stored,
the field lies the moment a document arrives — which is exactly what the old
``PipelineStatus`` did, and principle 3 exists because of it. So this module
computes it, and the stored field is only ever a cache of what this says.

WHAT IT WILL NOT CONCLUDE. ``delivered`` and ``complete`` are not derivable
today: the practice records no fact for "the 8879 went out" or "the return was
accepted", and inferring delivery from "all the tasks are ticked" would be a
guess about the one step that matters most. So this refuses those two stages and
NAMES what would settle it (principles 1, 5 and 10). When a Deliverable entity
exists, it becomes another clause here rather than a new source of truth.

WHY IT MATTERS. In March almost everything is blocked on somebody else, so the
scarce thing is not hours — it is UNBLOCKED WORK. Deriving the stage is what
connects the document pipeline to the work model: a document arrives, a request
is satisfied, a task settles, the job moves, and what is workable changes. That
chain, and not a status field, is the staff-accountant behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from satc.models.readiness import Readiness
from satc.models.work import Job, JobStage, Task

# Which task categories mean "somebody is checking the work". FIRM POLICY, not
# law — a practice that calls it "Second look" changes this, and nothing about
# the derivation cares. Kept here rather than in configs/ because it is a
# vocabulary question about this codebase's own task templates, not a date the
# owner sets; if it ever becomes a preference worth editing, it moves to
# firm_policy.yaml with the rest.
REVIEW_CATEGORIES = frozenset({"review", "quality review", "second review"})


def _is_review(task: Task) -> bool:
    return task.category.strip().lower() in REVIEW_CATEGORIES


@dataclass(frozen=True, slots=True)
class StageView:
    """What stage a job is at, why, and what would move it on."""

    stage: JobStage
    why: str
    """One line, in the owner's language, naming the evidence."""

    blocked_by: tuple[str, ...] = ()
    """What is holding it up — document types, or task titles."""

    next_step: str = ""
    """What would move this job forward. Empty when it is already moving."""

    undecidable: bool = False
    """True when the practice holds no fact that could settle the question.

    Distinct from "not there yet": principle 2, an unanswered question is not
    an answer. A job whose tasks are all done is NOT known to be delivered."""

    @property
    def is_workable(self) -> bool:
        """Can somebody sit down and DO this right now?

        ``ready_to_deliver`` is deliberately excluded. There is no preparing
        left on it — the only thing outstanding is recording that it went to the
        client, which is a different act. Counting it as workable put a job with
        nothing left to do at the top of the queue, permanently, above real prep
        work: it scored as the smallest job on the board and nothing the practice
        can record would ever move it. That is precisely the row principle 13
        warns about, the one that teaches the owner to scroll past the queue.
        """
        return self.stage in ("prep_ready", "in_prep", "in_review")

    @property
    def is_abandoned(self) -> bool:
        """Every task cancelled — the job was called off, not finished."""
        return self.stage == "not_started" and self.undecidable

    @property
    def is_waiting(self) -> bool:
        return self.stage == "waiting_on_documents"


def derive_stage(job: Job, *, readiness: Readiness | None = None,
                 today: date | None = None) -> StageView:
    """Work out where this job stands from what the practice actually knows.

    Order matters: the most blocking condition wins, because a job with a
    missing W-2 is waiting on documents no matter how many internal tasks have
    been ticked. Reporting the furthest-along true statement would be the
    optimistic reading, and the optimistic reading is what lets a return sit.
    """
    del today  # reserved: overdue tasks do not change the STAGE, only urgency

    internal = [t for t in job.tasks if t.audience == "internal"]
    prep = [t for t in internal if not _is_review(t)]
    review = [t for t in internal if _is_review(t)]

    # 1. Blocked on the client. Nothing internal changes this.
    if readiness is not None and not readiness.can_start_prep:
        waiting = tuple(i.doc_type for i in readiness.blocking_open)
        return StageView(
            stage="waiting_on_documents",
            why=readiness.why_not_prep(),
            blocked_by=waiting,
            next_step=f"Chase {', '.join(waiting)}." if waiting else "")

    # 2. Blocked on another task inside the job.
    blocked = [t for t in internal if t.is_open and t.blocked_by]
    startable = [t for t in internal if t.is_open and not t.blocked_by]
    if blocked and not startable and internal:
        return StageView(
            stage="in_prep",
            why=(f"{len(blocked)} task{'s' if len(blocked) != 1 else ''} waiting "
                 f"on earlier work in this job."),
            blocked_by=tuple(t.title for t in blocked),
            next_step="Finish what they depend on.")

    # 3. Nothing recorded yet at all.
    if not internal:
        return StageView(
            stage="not_started", why="No work planned on this job yet.",
            next_step="Run the interview to generate its tasks.")

    if all(t.is_settled for t in internal):
        # "Settled" covers done, waived AND cancelled — and a job whose tasks
        # were all CANCELLED was called off, not finished. Reading that as ready
        # to deliver proposed abandoned work for billing as though it had been
        # done, which is the worst direction for this mistake to run.
        if not any(t.is_done for t in internal):
            return StageView(
                stage="not_started",
                why="Every task on this job was cancelled or waived — nothing "
                    "was actually performed.",
                next_step=("Confirm this job was called off. If work really was "
                           "done, it is not recorded anywhere, and nothing "
                           "downstream — billing included — can see it."),
                undecidable=True)

        # Everything internal is done — but "done preparing" is not "delivered",
        # and the practice records no fact that could tell them apart.
        return StageView(
            stage="ready_to_deliver",
            why="Every task on this job is settled.",
            next_step=("There is no record that this went to the client. Record "
                       "it — SATC cannot tell delivery from a finished task "
                       "list, and will not guess at the step that matters most."),
            undecidable=True)

    if review and all(t.is_settled for t in prep):
        open_review = [t for t in review if t.is_open]
        return StageView(
            stage="in_review",
            why=(f"Preparing is finished; {len(open_review)} review "
                 f"task{'s' if len(open_review) != 1 else ''} outstanding."),
            blocked_by=tuple(t.title for t in open_review),
            next_step="Review it.")

    started = [t for t in internal if t.status != "not_started"]
    if started:
        open_now = [t for t in internal if t.is_open]
        return StageView(
            stage="in_prep",
            why=(f"{len(started)} of {len(internal)} tasks under way, "
                 f"{len(open_now)} still open."),
            blocked_by=tuple(t.title for t in open_now[:3]),
            next_step="Keep going.")

    # 4. Everything blocking is in hand and nobody has started.
    return StageView(
        stage="prep_ready",
        why=("Everything needed is in hand and nothing has been started."
             if readiness is not None
             else "Nothing has been started. (No document check on file.)"),
        next_step="Start the prep.")


def stage_matches_record(job: Job, view: StageView) -> bool:
    """Whether the STORED stage agrees with what the facts say.

    A disagreement is not an error to raise — it is the ordinary state of a
    cache after a document arrives. It is worth SHOWING, because a stored stage
    that has drifted is the exact thing that made the old status field
    untrustworthy.
    """
    return job.stage == view.stage
