"""WORK — what can I sit down and do right now.

A tax practice in March is not a to-do list, it is a QUEUE WITH CONSTRAINTS.
Almost everything is blocked on somebody else — a missing 1099, a review, a
signature — so the scarce resource is not hours, it is UNBLOCKED WORK. This
screen answers the question that follows from that: *what can I pick up right
now, and which one first*. It deliberately does not answer "what needs doing",
because in March the answer is "everything" and that is not usable.

Thin by design, like :mod:`satc.app.today_views`. The ORDER comes from
:mod:`satc.work.queue`; the STAGE comes from :func:`satc.work.derive_stage`;
this module gathers records and hands them over. No rule about what is workable,
and no rule about what ranks above what, lives in this file — a ranking rule
hidden in a view is a ranking rule nothing tests.

**It proposes; it never disposes** (principle 9). It assigns nothing, starts
nothing, reserves nothing, and advances nothing. It says "this one first, and
why". Every action on it is a click the owner makes — which is also why the rank
is rendered as a suggestion: the ordering weights are FIRM POLICY, not law, and
the screen says which is which (principle 4).

Routes:
  GET /work            - the queue, then (clearly secondary) what is NOT workable
  GET /work/<job_id>   - one job: its derived stage, its tasks, its documents
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, render_template

from satc.app.state import STATE
# Both borrowed rather than re-derived. A second copy of "which year is the
# practice working on" or of "materialise every client's duties" would drift
# from Today's copy, and the two screens would then quietly disagree about what
# is overdue.
from satc.app.today_views import _obligations, working_tax_year
from satc.config import ConfigError
from satc.models.readiness import assess
from satc.work import derive_stage, stage_matches_record

bp = Blueprint("work", __name__)


def _board(jobs, *, requested, obligations, today: date, tax_year: int):
    """Ask :mod:`satc.work.queue` for both halves. The screen holds no opinion.

    ``board`` and not ``workable`` because the two halves have to agree: derived
    twice they could disagree about a single job, and a job in neither list — or
    in both — is the failure nobody would notice.

    Imported inside the call rather than at module scope on purpose: the app
    must still start, and every other screen must still render, if the ordering
    rule is not installed. A missing one then becomes a sentence the owner can
    read (principle 10) instead of a stack trace on the front door.
    """
    from satc.work.queue import board

    return board(jobs, requested=requested, obligations=obligations,
                 today=today, tax_year=tax_year)


def _readiness(job, requested, tax_year: int):
    """What this job's client still owes us, for the year the job is about."""
    return assess(requested, client_id=job.client_id,
                  tax_year=job.tax_year if job.tax_year is not None else tax_year)


def empty_queue_note(board, *, jobs, tax_year: int) -> str:
    """Why the queue is empty, and what to do about it — never a blank panel.

    "Nothing to do" and "everything is blocked on somebody else" are opposite
    facts about a practice, and in March it is always the second one.

    Deliberately does NOT repeat :meth:`Board.summary_line`, which is already
    the headline. The headline carries the COUNT; this carries the next step.
    Principle 13: two things on a screen never say the same thing, or the owner
    learns to read neither.
    """
    if not board.not_workable:
        if not jobs:
            return ("No jobs are on file at all, so there is nothing to rank. "
                    "Generate one from a client's engagement.")
        return (f"No job on file is for {tax_year}, so nothing was ranked. Check "
                f"the year on the jobs in Engagements.")
    return ("Every job on file is blocked on somebody else. What each one is "
            "waiting on is listed below — chasing is this morning's work, not "
            "preparing.")


def headline_for(board) -> str:
    """The one line at the top. The engine's count, or an honest silence.

    ``summary_line`` answers "Nothing open." for a practice with no jobs at
    all, which is true and useless as a headline; the panel underneath names
    the next step, so the top line only has to stop pretending there is a queue.
    """
    if board.workable or board.not_workable:
        return board.summary_line()
    return "Nothing on file to rank."


@bp.route("/work")
def work():
    """The queue. Workable jobs in the order the ranking rule returned them."""
    as_of = date.today()
    requested = STATE.requested_items()
    year = working_tax_year(list(STATE.received_documents()) + list(requested), as_of)
    jobs = STATE.jobs()

    board = None
    refusal = ""
    try:
        board = _board(jobs, requested=requested, obligations=_obligations(year),
                       today=as_of, tax_year=year)
    except ImportError as exc:
        # Refuse rather than default (principle 5). Ranking these jobs here
        # would be a second ordering rule nobody tests, and listing them
        # unordered would quietly answer "which one first" with "whichever" —
        # an arbitrary order looks exactly like a considered one.
        refusal = (
            f"SATC cannot order this queue: the ranking rule "
            f"(satc.work.queue) is not installed — {exc}. Nothing is shown "
            f"rather than a list in no particular order. Install it, or work "
            f"from Today until it is there.")
    except ConfigError as bad_policy:
        # The ordering weights are hand-edited firm policy, so a typo in them is
        # an ordinary event rather than a crash. The loader's message already
        # names the file and the fix (principle 10), so it is shown verbatim.
        # Falling back to SATC's defaults instead would quietly ignore what the
        # owner wrote and rank the week on numbers nobody chose.
        refusal = str(bad_policy)

    # Jobs the board never saw, because they belong to another tax year. Said
    # out loud: an empty screen that is hiding eleven jobs is a lie of omission.
    shown = 0 if board is None else len(board.workable) + len(board.not_workable)
    return render_template(
        "workable.html", title="Work", board=board, refusal=refusal,
        tax_year=year, as_of=as_of, other_years=max(len(jobs) - shown, 0),
        headline=("What you can pick up right now" if board is None
                  else headline_for(board)),
        empty_note=("" if board is None
                    else empty_queue_note(board, jobs=jobs, tax_year=year)),
        names={cid: name for cid, name in STATE.client_choices()})


@bp.route("/work/<job_id>")
def job_detail(job_id: str):
    """One job: where it stands, what is blocked on what, and what is missing."""
    as_of = date.today()
    found = STATE.engagement(job_id)
    if found is None:
        # A 404 that names the next step, not a 500 and not a blank page. A job
        # id only ever reaches the owner through a link, so a stale bookmark or
        # a regenerated job is the usual cause, and the queue is where to go back to.
        return render_template(
            "job.html", title="Work", job=None, job_id=job_id,
            refusal=(f"No job {job_id!r} is on file. A job id only ever comes "
                     f"from a link, so this one has most likely been discarded "
                     f"or regenerated — open the work queue and pick it there."),
            names={}), 404

    requested = STATE.requested_items()
    year = working_tax_year(list(STATE.received_documents()) + list(requested), as_of)
    readiness = _readiness(found, requested, year)
    view = derive_stage(found, readiness=readiness, today=as_of)

    return render_template(
        "job.html", title="Work", job=found, job_id=job_id, refusal="",
        view=view, readiness=readiness, as_of=as_of,
        # The stored stage is a cache and is shown ONLY as a disagreement. It is
        # never what this screen reports, and a drifted one is worth seeing —
        # that drift is what made the old status field untrustworthy.
        stale_cache=not stage_matches_record(found, view),
        names={cid: name for cid, name in STATE.client_choices()})
