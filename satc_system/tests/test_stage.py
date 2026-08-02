"""The job stage is a conclusion, not a field somebody sets.

The failure this guards against is the one the old PipelineStatus had: a stored
status that was true when it was written and wrong by the time anybody read it.
"""

from datetime import date

from satc.models.evidence import RequestedItem
from satc.models.readiness import assess
from satc.models.work import Job, Task
from satc.work import derive_stage

TODAY = date(2026, 3, 10)


def a_task(title, *, category="Data entry", status="not_started",
           audience="internal", blocked_by=()) -> Task:
    return Task(task_id=f"T-{title}", job_id="J-1", template_id=title,
                title=title, category=category, status=status,
                audience=audience, blocked_by=tuple(blocked_by))


def a_job(*tasks) -> Job:
    return Job(job_id="J-1", client_id="CL-1", workflow_key="form_1040",
               engagement_type="1040", tax_year=2025, tasks=list(tasks))


def readiness_with(*items):
    return assess(items, client_id="CL-1", tax_year=2025)


def an_open_item(doc_type, blocking="blocking") -> RequestedItem:
    return RequestedItem(request_id=f"R-{doc_type}", client_id="CL-1",
                         tax_year=2025, doc_type=doc_type, blocking=blocking)


# --- blocked on the client beats everything else -----------------------------

def test_a_missing_blocking_document_holds_the_job_regardless_of_task_progress():
    """The optimistic reading is what lets a return sit until April."""
    job = a_job(a_task("Enter W-2", status="done"),
                a_task("Enter 1099", status="in_progress"))
    view = derive_stage(job, readiness=readiness_with(an_open_item("W-2")))
    assert view.stage == "waiting_on_documents"
    assert "W-2" in view.blocked_by
    assert view.next_step
    assert not view.is_workable


def test_a_non_blocking_document_does_not_hold_the_job():
    """The three-way split earns its keep here: a charity receipt is useful,
    not load-bearing."""
    job = a_job(a_task("Enter W-2"))
    view = derive_stage(job, readiness=readiness_with(
        an_open_item("Charity receipts", blocking="non_blocking")))
    assert view.stage == "prep_ready"
    assert view.is_workable


# --- the ordinary progression ------------------------------------------------

def test_everything_in_hand_and_nothing_started_is_prep_ready():
    view = derive_stage(a_job(a_task("Enter W-2")), readiness=readiness_with())
    assert view.stage == "prep_ready"
    assert view.is_workable


def test_work_under_way_is_in_prep():
    job = a_job(a_task("Enter W-2", status="in_progress"), a_task("Enter 1099"))
    view = derive_stage(job, readiness=readiness_with())
    assert view.stage == "in_prep"


def test_preparing_done_with_review_outstanding_is_in_review():
    job = a_job(a_task("Enter W-2", status="done"),
                a_task("Check the return", category="Review"))
    view = derive_stage(job, readiness=readiness_with())
    assert view.stage == "in_review"
    assert "Check the return" in view.blocked_by


def test_a_waived_task_does_not_hold_the_job_open():
    """Waived is settled — with a reason. That is the whole point of the state."""
    job = a_job(a_task("Enter W-2", status="done"),
                a_task("Foreign accounts", status="waived"))
    assert derive_stage(job, readiness=readiness_with()).stage == "ready_to_deliver"


def test_a_job_with_no_tasks_says_so_and_names_the_next_step():
    view = derive_stage(a_job(), readiness=readiness_with())
    assert view.stage == "not_started"
    assert "interview" in view.next_step


# --- what it refuses to conclude ---------------------------------------------

def test_a_finished_task_list_is_not_delivery():
    """The one inference worth refusing. 'All the boxes are ticked' and 'the
    return went to the client' are different facts, and the practice records
    only the first."""
    job = a_job(a_task("Enter W-2", status="done"),
                a_task("Check the return", category="Review", status="done"))
    view = derive_stage(job, readiness=readiness_with())
    assert view.stage == "ready_to_deliver"
    assert view.stage != "delivered"
    assert view.undecidable
    assert "guess" in view.next_step


def test_nothing_derives_delivered_or_complete_from_anything():
    """Mutation check — principle 12. If a clause were ever added that inferred
    delivery, this is what would catch it."""
    shapes = [
        a_job(),
        a_job(a_task("A", status="done")),
        a_job(a_task("A", status="done"), a_task("B", category="Review", status="done")),
        a_job(a_task("A", status="waived"), a_task("B", status="cancelled")),
    ]
    for job in shapes:
        for ready in (None, readiness_with()):
            assert derive_stage(job, readiness=ready).stage not in ("delivered", "complete")


# --- blocked inside the job --------------------------------------------------

def test_a_task_waiting_on_another_task_is_named():
    job = a_job(a_task("Reconcile", status="done"),
                a_task("Depreciation", blocked_by=("Reconcile",)))
    view = derive_stage(job, readiness=readiness_with())
    assert view.blocked_by == ("Depreciation",)
    assert "earlier work" in view.why


# --- the stored field is only ever a cache -----------------------------------

def test_the_stored_stage_is_not_consulted():
    """A job carrying stage='complete' with a missing W-2 is waiting on
    documents, whatever the field says. This is the invariant that stops a
    stored status from going stale and being believed."""
    job = a_job(a_task("Enter W-2"))
    job.stage = "complete"
    view = derive_stage(job, readiness=readiness_with(an_open_item("W-2")))
    assert view.stage == "waiting_on_documents"
