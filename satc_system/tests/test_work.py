"""The work spine: Engagement (contract) / Job (instance) / Task (unit).

Two things this file exists to pin:

  * A task status enum can say things a boolean cannot — blocked, waiting on the
    client, waived with a reason. Those are not shades of "not done"; they
    decide whether the job can advance.
  * ``selectattr('completed')`` over a STATUS STRING counts every task as done,
    because any non-empty string is truthy. That is a 200 with a wrong number —
    worse than a crash — and it is why counting lives on the model.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from satc.models.actor import Actor, ActorRefused
from satc.models.work import Job, Task, WorkError, complete, waive

MODEL = Actor.model("qwen3:8b")


def _task(title="W-2", status="not_started", **kw):
    return Task(task_id=f"t-{title}", job_id="J1", template_id=f"tpl-{title}",
                title=title, status=status, **kw)


def _job(*tasks):
    return Job(job_id="J1", client_id="C", workflow_key="personal_1040_core",
               tax_year=2025, tasks=list(tasks))


# --- what a boolean could not say ---------------------------------------------

def test_the_states_a_boolean_collapsed_are_now_distinct():
    """blocked / waiting-on-client / waived / cancelled were all "not done"."""
    states = ["not_started", "in_progress", "waiting_on_client", "blocked",
              "awaiting_review", "done", "waived", "cancelled"]
    signatures = {(s, _task(status=s).is_open, _task(status=s).is_done,
                   _task(status=s).is_settled) for s in states}
    assert len(signatures) == len(states)


def test_a_waived_task_is_settled_but_not_done():
    """Counting a waiver as done flatters the number."""
    t = _task(status="waived")
    assert t.is_settled
    assert not t.is_done
    assert not t.is_open


def test_a_blocked_task_is_still_open():
    t = _task(status="blocked")
    assert t.is_open and not t.is_settled


# --- counting happens on the model, never in a template -----------------------

def test_done_count_ignores_waived_and_cancelled():
    job = _job(_task("W-2", "done"), _task("1099", "waived"),
               _task("K-1", "cancelled"), _task("8879", "blocked"))
    assert job.done_count() == 1
    assert job.settled_count() == 3
    assert job.progress() == (3, 4)


def test_a_truthiness_count_would_have_been_wrong():
    """The bug the template used to have, demonstrated.

    Jinja's selectattr('status') keeps every task whose status is truthy — and
    every status string is truthy — so the old counter would report 4 of 4 done
    on a job where one task is done.
    """
    job = _job(_task("W-2", "done"), _task("1099", "not_started"),
               _task("K-1", "blocked"), _task("8879", "waiting_on_client"))
    truthy_count = len([t for t in job.tasks if t.status])
    assert truthy_count == 4          # what selectattr would have counted
    assert job.done_count() == 1      # what is actually true


# --- overdue is now expressible ----------------------------------------------

def test_a_task_with_a_real_due_date_can_be_overdue():
    """Previously there was only a derived hint, so nothing was ever overdue."""
    t = _task(due_date=date(2026, 3, 1))
    assert t.is_overdue(date(2026, 4, 1))
    assert not t.is_overdue(date(2026, 2, 1))


def test_a_settled_task_is_never_overdue():
    t = _task(status="done", due_date=date(2026, 3, 1))
    assert not t.is_overdue(date(2026, 4, 1))


def test_a_job_reports_its_overdue_tasks():
    job = _job(_task("W-2", due_date=date(2026, 3, 1)),
               _task("1099", "done", due_date=date(2026, 3, 1)))
    overdue = job.overdue_tasks(date(2026, 4, 1))
    assert [t.title for t in overdue] == ["W-2"]


# --- completion records what was actually done --------------------------------

def test_completing_a_task_records_who_and_what_they_did():
    """"Marked reviewed without documenting what was performed" is a named
    junior failure mode. A tick that records nothing is indistinguishable from
    a tick someone applied to clear a screen."""
    t = complete(_task(), actor=Actor.owner(), procedure="traced to W-2 box 1",
                 now=datetime(2026, 3, 1, 10, 0))
    assert t.is_done
    assert t.completion.by.is_human
    assert t.completion.procedure == "traced to W-2 box 1"


def test_a_model_cannot_complete_a_task():
    with pytest.raises(ActorRefused):
        complete(_task(), actor=MODEL)


def test_waiving_without_a_reason_is_refused():
    with pytest.raises(WorkError, match="without a reason"):
        waive(_task(), actor=Actor.owner(), reason="  ")


def test_a_waiver_keeps_its_reason_and_who_decided():
    t = waive(_task(), actor=Actor.owner(), reason="no rental this year")
    assert t.status == "waived"
    assert t.waived_reason == "no rental this year"
    assert t.completion.by.is_human


def test_a_model_cannot_waive_a_task():
    with pytest.raises(ActorRefused):
        waive(_task(), actor=MODEL, reason="looks unnecessary")


# --- the vocabulary is unambiguous now ----------------------------------------

def test_engagement_and_job_are_different_things():
    """They previously shared the word "engagement", so every conversation
    about "the engagement" was ambiguous."""
    from satc.models.work import Engagement

    contract = Engagement(client_id="C", tax_year=2025)
    work = _job()
    assert contract.client_id == work.client_id
    assert not hasattr(contract, "tasks")      # a contract has no tasks
    assert not hasattr(work, "fee_amount")     # a job has no fee


def test_a_job_knows_which_duty_it_discharges():
    job = Job(job_id="J1", client_id="C", workflow_key="w",
              obligation_key="C/file/1040/US/2025", period_key="2025")
    assert job.obligation_key.endswith("2025")
    assert job.period_key == "2025"


# --- round trip ---------------------------------------------------------------

def test_a_task_survives_persistence_with_its_status_and_completion():
    import tempfile

    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        job = _job(complete(_task("W-2"), actor=Actor.owner(),
                            procedure="traced to source",
                            now=datetime(2026, 3, 1, 10, 0)),
                   waive(_task("Rental"), actor=Actor.owner(),
                         reason="sold the property in 2024"))
        job.tasks[0].due_date = date(2026, 4, 15)
        store.save_job(job)

        reloaded = {t.template_id: t for j in store.load_jobs() for t in j.tasks}
        w2 = reloaded["tpl-W-2"]
        assert w2.status == "done"
        assert w2.due_date == date(2026, 4, 15)
        assert w2.completion.procedure == "traced to source"
        assert w2.completion.by.is_human

        rental = reloaded["tpl-Rental"]
        assert rental.status == "waived"
        assert rental.waived_reason == "sold the property in 2024"
