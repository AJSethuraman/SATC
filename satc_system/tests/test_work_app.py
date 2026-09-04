"""The WORK screen — "what can I sit down and do right now", and in what order.

The pure rules are guarded elsewhere: the stage derivation in ``test_stage.py``
and the ordering in the queue module's own tests. This file guards the thin
view, and specifically the ways a queue SCREEN goes wrong even when the rule
behind it is right:

* it re-sorts what the ranking rule gave it, so the screen and the rule disagree
  and nothing notices;
* it shows a blocked job as though it could be picked up;
* it renders an empty box when nothing is workable, instead of saying that
  everything is blocked on somebody else — which in March is the answer;
* it presents a job whose tasks are all ticked as finished, when the practice
  holds no record that it ever went to the client;
* it silently drops what it did not rank.

Everything goes through the real ``create_app()`` and, except where a known
order is needed, through the real ``satc.work.queue``. A fixture that
hand-registered the blueprint would keep passing after the wiring was dropped.
"""

from __future__ import annotations

import ast
from datetime import date, timedelta
from pathlib import Path

import pytest

from satc.app import work_views
from satc.app.server import create_app
from satc.app.state import STATE
from satc.models.evidence import RequestedItem
from satc.models.readiness import assess
from satc.models.work import Job, Task
from satc.work import derive_stage

TODAY = date(2026, 3, 10)


# --- fixtures for the records the screen reads -------------------------------

def a_task(title, *, category="Data entry", status="not_started",
           audience="internal", blocked_by=(), job_id="J-1") -> Task:
    return Task(task_id=f"{job_id}-{title}", job_id=job_id, template_id=title,
                title=title, category=category, status=status,
                audience=audience, blocked_by=tuple(blocked_by))


def a_job(*tasks, job_id="J-1", client_id="CL-1", tax_year=2025,
          engagement_type="1040 individual return", stage="not_started") -> Job:
    job = Job(job_id=job_id, client_id=client_id, workflow_key="form_1040",
              engagement_type=engagement_type, tax_year=tax_year,
              tasks=list(tasks))
    job.stage = stage
    for task in job.tasks:
        task.job_id = job_id
    return job


def an_open_item(doc_type, *, client_id="CL-1", tax_year=2025,
                 blocking="blocking", requested_at=None) -> RequestedItem:
    return RequestedItem(request_id=f"R-{client_id}-{doc_type}", client_id=client_id,
                         tax_year=tax_year, doc_type=doc_type, blocking=blocking,
                         requested_at=requested_at)


# --- wiring ------------------------------------------------------------------

@pytest.fixture()
def client():
    app = create_app()
    if "work.work" not in app.view_functions:
        pytest.skip(
            "create_app() does not register the work blueprint yet. Add "
            "`app.register_blueprint(work_bp)` in satc/app/server.py and these run.")
    return app.test_client()


@pytest.fixture()
def practice(monkeypatch):
    """Put a known set of jobs and requests in front of the screen.

    Patches the STORE, not the view helpers, so ``STATE.jobs()`` and
    ``STATE.engagement()`` run for real — the job page resolves an id exactly
    the way it does in the app. The queue itself is left alone: what these tests
    render is what ``satc.work.queue`` actually returns.
    """
    def install(jobs=(), requested=()):
        monkeypatch.setattr(STATE.store, "load_jobs", lambda: list(jobs))
        monkeypatch.setattr(STATE, "requested_items", lambda: list(requested))
        monkeypatch.setattr(STATE, "received_documents", lambda: [])
    return install


def body_of(resp) -> str:
    assert resp.status_code == 200, resp.status_code
    return resp.data.decode("utf-8")


# --- the queue renders -------------------------------------------------------

def test_the_queue_shows_the_client_the_stage_the_reason_and_the_next_step(
        client, practice):
    practice(jobs=[a_job(a_task("Enter W-2"), client_id="CL-ALPHA")])

    page = body_of(client.get("/work"))
    assert "CL-ALPHA" in page
    assert "1040 individual return" in page
    assert "prep ready" in page                       # the DERIVED stage
    assert "Ready to start" in page                   # the queue's one-line reason
    assert "Start the prep." in page                  # the next step


def test_the_order_on_screen_is_the_order_the_query_returned(client, practice,
                                                             monkeypatch):
    """A template that re-sorts makes the screen disagree with the ranking rule,
    and there is nothing else in the app that would ever notice.

    The order handed over here is neither alphabetical nor by job id, so any
    plausible re-sort produces a different page.
    """
    from satc.work.queue import Board, QueuePolicy, WorkItem

    jobs = {cid: a_job(a_task("A"), job_id=f"J-{cid}", client_id=cid)
            for cid in ("CL-ALPHA", "CL-BRAVO", "CL-CHARLIE")}
    order = ["CL-CHARLIE", "CL-ALPHA", "CL-BRAVO"]
    items = tuple(
        WorkItem(job=jobs[cid],
                 view=derive_stage(jobs[cid], readiness=assess(
                     (), client_id=cid, tax_year=2025), today=TODAY),
                 rank=position, score=10.0 - position, factors=(),
                 why=f"{cid} ranked {position}.")
        for position, cid in enumerate(order, start=1))

    practice(jobs=list(jobs.values()))
    monkeypatch.setattr(work_views, "_board", lambda *a, **kw: Board(
        workable=items, not_workable=(), policy=QueuePolicy()))

    page = body_of(client.get("/work"))
    positions = [page.index(cid) for cid in order]
    assert positions == sorted(positions), "the screen re-ordered the queue"
    # The rank column is the QUEUE's rank, not the row number the template
    # counted. Re-sorted rows would carry their ranks with them and show 2,1,3.
    ranks = [page.index(f'<td class="mono">{n}</td>') for n in (1, 2, 3)]
    assert ranks == sorted(ranks), "the rank shown is not the rank ranked"


def test_a_blocked_job_is_in_the_waiting_section_and_not_the_workable_one(
        client, practice):
    practice(jobs=[a_job(a_task("Enter W-2"), job_id="J-BLOCKED",
                         client_id="CL-BLOCKED")],
             requested=[an_open_item("W-2", client_id="CL-BLOCKED")])

    page = body_of(client.get("/work"))
    # The blocked half is split by WHO is blocking — a job waiting on a client
    # and a job waiting on the owner to record delivery are different problems
    # and must not share a heading.
    workable_half, waiting_half = page.split("Waiting on clients", 1)
    assert "CL-BLOCKED" not in workable_half, "a job waiting on a W-2 is not workable"
    assert "CL-BLOCKED" in waiting_half
    assert "W-2" in waiting_half
    assert "waiting on documents" in waiting_half


def test_an_empty_queue_says_why_it_is_empty(client, practice):
    """A blank panel and "everything is blocked on a client" are opposite facts
    about a practice, and in March it is always the second one."""
    practice(jobs=[a_job(a_task("Enter W-2"), job_id=f"J-{n}", client_id=f"CL-{n}")
                   for n in range(3)],
             requested=[an_open_item("W-2", client_id=f"CL-{n}") for n in range(3)])

    page = body_of(client.get("/work"))
    assert "3 files are waiting on clients" in page       # the count, from the engine
    assert "chasing is this morning" in page              # and the next step
    # Principle 13: the headline and the panel must not say the same thing.
    assert page.count("3 files are waiting on clients") == 1


def test_an_empty_practice_says_there_is_nothing_to_rank(client, practice):
    practice(jobs=[])
    page = body_of(client.get("/work"))
    assert "Nothing on file to rank." in page         # not the engine's "Nothing open."
    assert "No jobs are on file at all" in page
    assert "Generate one from a client" in page       # ...engagement (apostrophe escaped)


def test_jobs_from_another_year_are_said_out_loud_not_silently_dropped(
        client, practice):
    """The queue ranks one year. A screen that shows nothing while eleven jobs
    sit on file is lying by omission (principle 1)."""
    practice(jobs=[a_job(a_task("A"), job_id="J-OLD", client_id="CL-OLD",
                         tax_year=2019)],
             requested=[an_open_item("W-2", client_id="CL-NOW", tax_year=2025)])

    page = body_of(client.get("/work"))
    assert "for another tax year" in page
    assert "No job on file is for 2025" in page       # and why the queue is empty
    assert "CL-OLD" not in page


def test_an_undecidable_stage_is_labelled_rather_than_presented_as_finished(
        client, practice):
    """Every task ticked is not "delivered". The practice records no fact for
    the step that matters most, so the screen says so."""
    practice(jobs=[a_job(a_task("Enter W-2", status="done"),
                         a_task("Check the return", category="Review", status="done"),
                         job_id="J-DONE", client_id="CL-DONE")])

    page = body_of(client.get("/work"))
    assert "Not known to be delivered" in page
    assert "no record that" in page


def test_the_rank_is_shown_as_a_preference_and_not_as_law(client, practice):
    """Principle 4. The weights are something the owner changes over coffee;
    the deadline is a statute. They must not read the same on screen."""
    practice(jobs=[a_job(a_task("Enter W-2"), client_id="CL-ALPHA")])

    page = body_of(client.get("/work"))
    assert "The order is firm policy, not law" in page
    assert "configs/firm_policy.yaml" in page
    assert "no statutory deadline on file" in page     # never a stand-in date


def test_a_missing_ranking_rule_is_a_sentence_and_not_a_500(client, practice,
                                                            monkeypatch):
    """Refuse rather than default (principle 5): an arbitrary order looks
    exactly like a considered one."""
    practice(jobs=[a_job(a_task("Enter W-2"), client_id="CL-ALPHA")])

    def boom(*a, **kw):
        raise ImportError("No module named 'satc.work.queue'")
    monkeypatch.setattr(work_views, "_board", boom)

    page = body_of(client.get("/work"))
    assert "will not order this queue" in page
    assert "satc.work.queue" in page
    assert "Workable now" not in page, "nothing may be listed in no particular order"


def test_a_typo_in_the_ordering_policy_is_shown_not_crashed_on(client, practice,
                                                               monkeypatch):
    """The weights are hand-edited firm policy, so a typo in them is an ordinary
    event. The loader's message already names the file and the fix; ranking on
    SATC's defaults instead would silently ignore what the owner wrote."""
    from satc.config import ConfigError

    practice(jobs=[a_job(a_task("Enter W-2"), client_id="CL-ALPHA")])

    def bad(*a, **kw):
        raise ConfigError("queue.weights names factors SATC does not compute: "
                          "deadlien. Correct the spelling in firm_policy.yaml.")
    monkeypatch.setattr(work_views, "_board", bad)

    page = body_of(client.get("/work"))
    assert "deadlien" in page
    assert "Correct the spelling in firm_policy.yaml" in page
    assert "Workable now" not in page


# --- one job -----------------------------------------------------------------

def test_the_job_page_shows_the_stage_the_tasks_and_what_is_outstanding(
        client, practice):
    job = a_job(a_task("Reconcile", status="done"),
                a_task("Depreciation", blocked_by=("Reconcile",)),
                job_id="J-ONE", client_id="CL-ONE")
    # Relative to the real clock: the screen asks the calendar what today is, so
    # a fixed date here would rot the moment the suite ran on another day.
    practice(jobs=[job],
             requested=[an_open_item("K-1", client_id="CL-ONE",
                                     blocking="expected_late",
                                     requested_at=date.today() - timedelta(days=37))])

    page = body_of(client.get("/work/J-ONE"))
    assert "Depreciation" in page
    # What it is blocked ON, and not merely the fact that a task by that name
    # exists — "Reconcile" appears as a row title either way, so the assertion
    # has to reach the cell that names the dependency.
    assert '<span class="flag">Reconcile</span>' in page
    assert "K-1" in page
    assert "blocks filing, not prep" in page
    assert "37 days" in page                          # computed, never stored
    assert "in prep" in page


def test_a_request_with_no_date_on_file_is_marked_not_blanked(client, practice):
    """Principle 1: a date the practice does not hold is visible, never blank."""
    practice(jobs=[a_job(a_task("Enter W-2"), job_id="J-NODATE",
                         client_id="CL-NODATE")],
             requested=[an_open_item("1099-INT", client_id="CL-NODATE",
                                     blocking="non_blocking")])

    page = body_of(client.get("/work/J-NODATE"))
    assert "no request date on file" in page


def test_the_job_page_reports_the_derived_stage_not_the_stored_one(client, practice):
    """A job carrying stage='complete' with a missing W-2 is waiting on
    documents, whatever the field says."""
    practice(jobs=[a_job(a_task("Enter W-2"), job_id="J-STALE",
                         client_id="CL-STALE", stage="complete")],
             requested=[an_open_item("W-2", client_id="CL-STALE")])

    page = body_of(client.get("/work/J-STALE"))
    assert "waiting on documents" in page
    assert "That field is a cache" in page


def test_an_unknown_job_id_is_a_404_and_not_a_500(client, practice):
    practice(jobs=[])
    resp = client.get("/work/J-NOT-A-JOB")
    assert resp.status_code == 404
    page = resp.data.decode("utf-8")
    assert "J-NOT-A-JOB" in page
    assert "open the work queue" in page              # principle 10: name the step


# --- it proposes; it never disposes ------------------------------------------

# Recording a delivery is the one write this blueprint may do, and it is not
# the kind principle 9 forbids: it writes down something the OWNER did, rather
# than doing anything itself. SATC still sends nothing.
_MAY_WRITE = {"work.record_delivered"}


def test_the_work_queue_can_only_be_read(client):
    """Principle 9. A queue that ORDERS is proposing; one that assigns, starts
    or reserves is disposing. The queue and the job view stay read-only, and the
    view may not call anything that assigns or starts work."""
    app = create_app()
    rules = [r for r in app.url_map.iter_rules() if r.endpoint.startswith("work.")]
    assert rules, "the work blueprint is not registered"
    for rule in rules:
        if rule.endpoint in _MAY_WRITE:
            continue
        assert rule.methods <= {"GET", "HEAD", "OPTIONS"}, f"{rule.endpoint} accepts writes"

    banned = {"set_task_completed", "save_task", "save_mart", "save_requested_items",
              "create_engagement", "close_request", "post_confirmed", "complete",
              "waive", "run_intake", "delete_client", "confirm_field", "auto_confirm"}
    tree = ast.parse(Path(work_views.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            assert name not in banned, f"work_views calls {name} — that is disposing"


# --- the order really does come from the queue module ------------------------

def test_the_order_comes_from_satc_work_queue_and_nowhere_else():
    """The screen holds no ranking of its own. This pins the seam to the real
    module, so a view that quietly grew its own sort would fail here."""
    from satc.work import queue

    seen = {}

    def spy(jobs, *, requested, obligations, today, tax_year):
        seen.update(jobs=jobs, requested=requested, obligations=obligations,
                    today=today, tax_year=tax_year)
        return "the board"

    original = queue.board
    queue.board = spy
    try:
        out = work_views._board([1, 2], requested=["r"], obligations=["o"],
                                today=TODAY, tax_year=2025)
    finally:
        queue.board = original

    assert out == "the board"
    assert seen == {"jobs": [1, 2], "requested": ["r"], "obligations": ["o"],
                    "today": TODAY, "tax_year": 2025}


# --- recording that work went out --------------------------------------------

def test_recording_a_delivery_needs_a_human_and_writes_only_that(client, practice):
    """It records that the OWNER sent something. SATC sends nothing — an AST
    scan proves this blueprint has no send path at all."""
    import ast as _ast
    from pathlib import Path as _Path

    from satc.app import work_views as _wv

    source = _Path(_wv.__file__).read_text(encoding="utf-8")
    tree = _ast.parse(source)

    # AST, not a substring scan. A docstring that SAYS "SATC has no SMTP" is
    # the point of the file, and a text search flags it — a check that fires on
    # its own explanation is a check nobody keeps.
    imported = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, _ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "smtplib" not in imported, "work_views imports smtplib"

    names = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
             for n in _ast.walk(tree) if isinstance(n, _ast.Call)}
    assert "record_delivery" in names, "the route must go through the guarded helper"
    assert "acting_actor" in names, (
        "the actor must be DERIVED from the request, never taken off the form")


def test_a_delivery_dated_in_the_future_is_refused(client, practice):
    """The mirror of the payment guard. A mistyped year passes every naive check
    and then anchors a promise nobody can have kept yet."""
    practice(jobs=[a_job(a_task("Enter W-2"), job_id="J-DLV", client_id="CL-DLV")])
    resp = client.post("/work/J-DLV/delivered", data={
        "kind": "return_for_review", "return_key": "CL-DLV-2024-1040",
        "delivered_on": "2062-03-01", "channel": "portal"})
    assert resp.status_code == 200, "a refusal is a page, not a redirect"
    assert "in the future" in body_of(resp)


def test_a_delivery_that_does_not_say_which_return_is_refused(client, practice):
    practice(jobs=[a_job(a_task("Enter W-2"), job_id="J-DLV2", client_id="CL-DLV2")])
    resp = client.post("/work/J-DLV2/delivered", data={
        "kind": "return_for_review", "return_key": "",
        "delivered_on": "2026-04-02", "channel": "portal"})
    assert "WHICH return" in body_of(resp)
