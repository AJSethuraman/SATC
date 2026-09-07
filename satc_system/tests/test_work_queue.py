"""The queue answers "what can I pick up now, and which one first".

Two things are being guarded here and they pull in opposite directions. One is
that the ORDER is useful — a near deadline beats a distant one, a stale file
beats a fresh one, and the same inputs always give the same order. The other is
that the order is only ever a SUGGESTION built out of the owner's own
preferences: it never assigns anything, it never invents a deadline to rank on,
and every row can be argued with because every row says what it is made of.
"""

from datetime import date, datetime, timedelta

import pytest

from satc.config import ConfigError
from satc.models.evidence import RequestedItem
from satc.models.work import Completion, Job, Task
from satc.work.queue import (
    DEFAULT_WEIGHTS,
    FACTOR_KEYS,
    QueuePolicy,
    board,
    load_queue_policy,
    not_workable,
    workable,
)

TODAY = date(2026, 3, 10)


# --- fixtures in the shape the practice actually records ---------------------

def a_task(title, *, job_id="J-1", status="not_started", category="Data entry",
           audience="internal", blocked_by=(), completed_at=None) -> Task:
    return Task(task_id=f"{job_id}/{title}", job_id=job_id, template_id=title,
                title=title, category=category, status=status, audience=audience,
                blocked_by=tuple(blocked_by),
                completion=(Completion(by=None, at=completed_at)  # type: ignore[arg-type]
                            if completed_at else None))


def a_job(job_id="J-1", *tasks, client_id="CL-1", obligation_key="",
          updated=None, tax_year=2025, due_date=None) -> Job:
    stamp = (updated or TODAY).isoformat()
    return Job(job_id=job_id, client_id=client_id, workflow_key="form_1040",
               obligation_key=obligation_key, engagement_type="1040",
               tax_year=tax_year, due_date=due_date, created_at=stamp,
               updated_at=stamp, tasks=[t for t in tasks])


class Duty:
    """The shape of a materialised obligation — dates computed from cited rules.

    A stand-in rather than the real :class:`ObligationInstance` so the test says
    what the queue actually READS off a duty: a key, a form, a due date, and
    whether the duty rests on an unconfirmed assumption. Nothing else.
    """

    def __init__(self, obligation_key, due, *, form="1040", is_assumed=False):
        self.obligation_key = obligation_key
        self.due = due
        self.form = form
        self.is_assumed = is_assumed

    def days_until(self, today, *, extended=False):
        return (self.due - today).days


def an_open_item(doc_type, *, client_id="CL-1", blocking="blocking",
                 requested_at=None) -> RequestedItem:
    return RequestedItem(request_id=f"R-{client_id}-{doc_type}", client_id=client_id,
                         tax_year=2025, doc_type=doc_type, blocking=blocking,
                         requested_at=requested_at)


FLAT = QueuePolicy(weights={k: 0.0 for k in FACTOR_KEYS}, configured=True)


def only(factor: str, **kw) -> QueuePolicy:
    """A policy where exactly one factor pulls — isolates what is being tested."""
    weights = {k: (1.0 if k == factor else 0.0) for k in FACTOR_KEYS}
    return QueuePolicy(weights=weights, configured=True, **kw)


# --- a blocked job is never workable -----------------------------------------

def test_a_job_blocked_on_a_client_never_appears_as_workable():
    """The whole premise: in March the constraint is other people, so a file
    waiting on a W-2 is not work, however much of it is done."""
    blocked = a_job("J-BLOCKED", a_task("Enter W-2", job_id="J-BLOCKED",
                                        status="in_progress"))
    open_now = a_job("J-OPEN", a_task("Enter W-2", job_id="J-OPEN"),
                     client_id="CL-2")
    jobs = [blocked, open_now]
    requested = [an_open_item("W-2", client_id="CL-1")]

    picked = workable(jobs, requested=requested, today=TODAY, tax_year=2025)
    assert [i.job_id for i in picked] == ["J-OPEN"]


def test_the_not_workable_list_names_what_each_one_is_waiting_on():
    """An empty workable list is not an answer. "Waiting on a W-2, asked 20 days
    ago" is."""
    jobs = [a_job("J-1", a_task("Enter W-2"))]
    requested = [an_open_item("W-2", requested_at=TODAY - timedelta(days=20))]

    stuck = not_workable(jobs, requested=requested, today=TODAY, tax_year=2025)
    assert len(stuck) == 1
    assert stuck[0].waiting_on == ("W-2",)
    assert "W-2" in stuck[0].why
    assert stuck[0].longest_wait_days == 20
    assert "20 days ago" in stuck[0].why
    assert stuck[0].next_step


def test_the_two_halves_never_overlap_and_never_lose_a_job():
    jobs = [a_job("J-1", a_task("Enter W-2")),
            a_job("J-2", a_task("Enter W-2", job_id="J-2"), client_id="CL-2"),
            a_job("J-3", client_id="CL-3")]           # no tasks — nothing planned
    requested = [an_open_item("W-2", client_id="CL-1")]
    view = board(jobs, requested=requested, today=TODAY, tax_year=2025)

    ids = [i.job_id for i in view.workable] + [b.job_id for b in view.not_workable]
    assert sorted(ids) == ["J-1", "J-2", "J-3"]
    assert len(set(ids)) == 3


def test_an_empty_queue_says_why_it_is_empty():
    jobs = [a_job(f"J-{n}", a_task("Enter W-2", job_id=f"J-{n}")) for n in range(1, 15)]
    requested = [an_open_item("W-2")]
    line = board(jobs, requested=requested, today=TODAY, tax_year=2025).summary_line()
    assert "Nothing to pick up" in line
    assert "14 files" in line


# --- the ordering itself -----------------------------------------------------

def test_a_closer_statutory_deadline_ranks_first():
    near = a_job("J-NEAR", a_task("Prep", job_id="J-NEAR"), obligation_key="K-NEAR")
    far = a_job("J-FAR", a_task("Prep", job_id="J-FAR"), obligation_key="K-FAR",
                client_id="CL-2")
    duties = [Duty("K-NEAR", TODAY + timedelta(days=5)),
              Duty("K-FAR", TODAY + timedelta(days=40))]

    picked = workable([far, near], obligations=duties, today=TODAY, tax_year=2025,
                      policy=only("deadline"))
    assert [i.job_id for i in picked] == ["J-NEAR", "J-FAR"]
    assert picked[0].rank == 1 and picked[1].rank == 2


def test_an_overdue_deadline_outranks_one_due_today():
    """Ids chosen so alphabetical order is the WRONG answer — otherwise a
    version that scored both the same would pass on the tiebreak alone."""
    late = a_job("J-B-LATE", a_task("Prep", job_id="J-B-LATE"), obligation_key="K-LATE")
    today_due = a_job("J-A-TODAY", a_task("Prep", job_id="J-A-TODAY"),
                      obligation_key="K-TODAY", client_id="CL-2")
    duties = [Duty("K-LATE", TODAY - timedelta(days=12)), Duty("K-TODAY", TODAY)]

    picked = workable([today_due, late], obligations=duties, today=TODAY,
                      tax_year=2025, policy=only("deadline"))
    assert [i.job_id for i in picked] == ["J-B-LATE", "J-A-TODAY"]
    assert picked[0].score > picked[1].score
    assert "12 days overdue" in picked[0].why


def test_a_deadline_past_the_horizon_stops_pulling_but_is_still_named():
    """Beyond the horizon the factor says nothing — it must not go NEGATIVE and
    push a distant-deadline job below one with no deadline at all."""
    job = a_job("J-1", a_task("Prep"), obligation_key="K-1")
    duty = Duty("K-1", TODAY + timedelta(days=200))
    item = workable([job], obligations=[duty], today=TODAY, tax_year=2025,
                    policy=only("deadline"))[0]
    deadline = next(f for f in item.factors if f.key == "deadline")
    assert deadline.known is True
    assert deadline.score == 0.0
    assert item.score == 0.0
    assert "Sep 26" in deadline.detail


def test_a_stale_file_outranks_a_fresh_one():
    """The quietly-slipping detector. Both are workable; one has had nothing
    recorded against it for a fortnight."""
    stale = a_job("J-STALE", a_task("Prep", job_id="J-STALE"),
                  updated=TODAY - timedelta(days=21))
    fresh = a_job("J-FRESH", a_task("Prep", job_id="J-FRESH"), client_id="CL-2",
                  updated=TODAY)

    picked = workable([fresh, stale], today=TODAY, tax_year=2025, policy=only("idle"))
    assert [i.job_id for i in picked] == ["J-STALE", "J-FRESH"]
    assert "21 days" in picked[0].why


def test_a_finished_task_counts_as_movement_so_the_job_is_not_called_stale():
    """"How long has it sat" is measured off facts the practice actually holds —
    when the record was written, and when work was finished."""
    old_record = TODAY - timedelta(days=30)
    # Ids ordered so that a version blind to the completion would tie both jobs
    # at "30 days stale" and hand J-A-WORKED the top slot on the tiebreak.
    worked = a_job("J-A-WORKED",
                   a_task("Prep", job_id="J-A-WORKED", status="done",
                          completed_at=datetime(2026, 3, 9, 14, 0)),
                   a_task("Review", job_id="J-A-WORKED", category="Review"),
                   updated=old_record)
    untouched = a_job("J-B-COLD", a_task("Prep", job_id="J-B-COLD"),
                      a_task("Review", job_id="J-B-COLD", category="Review"),
                      client_id="CL-2", updated=old_record)

    picked = workable([worked, untouched], today=TODAY, tax_year=2025,
                      policy=only("idle"))
    assert [i.job_id for i in picked] == ["J-B-COLD", "J-A-WORKED"]
    assert picked[0].score > picked[1].score
    assert "1 day" in picked[1].why


def test_work_that_unblocks_other_work_outranks_flat_work():
    leverage = a_job("J-LEVER",
                     a_task("Reconcile", job_id="J-LEVER"),
                     a_task("Depreciation", job_id="J-LEVER",
                            blocked_by=("Reconcile",)),
                     a_task("Sch E", job_id="J-LEVER", blocked_by=("Reconcile",)))
    flat = a_job("J-FLAT", a_task("Prep", job_id="J-FLAT"),
                 a_task("Prep 2", job_id="J-FLAT"),
                 a_task("Prep 3", job_id="J-FLAT"), client_id="CL-2")

    picked = workable([flat, leverage], today=TODAY, tax_year=2025,
                      policy=only("unblocks"))
    assert [i.job_id for i in picked] == ["J-LEVER", "J-FLAT"]
    assert "frees 2 blocked tasks" in picked[0].why


def test_the_job_with_least_left_on_it_ranks_first_as_a_quick_win():
    nearly = a_job("J-NEARLY", a_task("Prep", job_id="J-NEARLY", status="done"),
                   a_task("Review", job_id="J-NEARLY", category="Review"))
    heavy = a_job("J-HEAVY", *[a_task(f"Prep {n}", job_id="J-HEAVY") for n in range(5)],
                  client_id="CL-2")

    picked = workable([heavy, nearly], today=TODAY, tax_year=2025,
                      policy=only("quick_win"))
    assert [i.job_id for i in picked] == ["J-NEARLY", "J-HEAVY"]
    assert "1 task left" in picked[0].why


# --- stable, total, deterministic --------------------------------------------

def test_the_same_inputs_give_the_same_order_whatever_order_they_arrive_in():
    jobs = [a_job(f"J-{n}", a_task("Prep", job_id=f"J-{n}"), client_id=f"CL-{n}",
                  obligation_key=f"K-{n}", updated=TODAY - timedelta(days=n))
            for n in range(1, 8)]
    duties = [Duty(f"K-{n}", TODAY + timedelta(days=n * 3)) for n in range(1, 8)]

    forward = [i.job_id for i in workable(jobs, obligations=duties, today=TODAY,
                                          tax_year=2025, policy=only("deadline"))]
    backward = [i.job_id for i in workable(list(reversed(jobs)), obligations=duties,
                                           today=TODAY, tax_year=2025,
                                           policy=only("deadline"))]
    again = [i.job_id for i in workable(jobs, obligations=duties, today=TODAY,
                                        tax_year=2025, policy=only("deadline"))]
    assert forward == backward == again


def test_identical_jobs_break_their_tie_on_job_id_not_on_input_order():
    """A total order, not merely a stable sort. Two jobs with nothing to choose
    between them must still come out the same way every time."""
    same = [a_job("J-B", a_task("Prep", job_id="J-B"), client_id="CL-2"),
            a_job("J-A", a_task("Prep", job_id="J-A"), client_id="CL-1"),
            a_job("J-C", a_task("Prep", job_id="J-C"), client_id="CL-3")]
    for arrangement in (same, list(reversed(same)), [same[1], same[2], same[0]]):
        picked = workable(arrangement, today=TODAY, tax_year=2025)
        assert [i.job_id for i in picked] == ["J-A", "J-B", "J-C"]


# --- never invent a deadline --------------------------------------------------

def test_a_job_with_no_obligation_on_file_is_ranked_without_a_deadline_invented():
    job = a_job("J-ADHOC", a_task("Answer the notice", job_id="J-ADHOC"))
    picked = workable([job], today=TODAY, tax_year=2025)

    assert len(picked) == 1
    item = picked[0]
    assert item.deadline is None
    assert item.deadline_known is False
    assert item.rank == 1                       # still ranked, on what IS known
    assert "no statutory deadline on file" in item.why
    deadline = next(f for f in item.factors if f.key == "deadline")
    assert deadline.known is False and deadline.contribution == 0.0


def test_a_hand_typed_due_date_on_the_job_is_not_treated_as_a_deadline():
    """Job.due_date is a date somebody keyed into a form. Scoring it as though
    it came from a cited rule is exactly how law and preference blur."""
    typed = a_job("J-TYPED", a_task("Prep", job_id="J-TYPED"),
                  due_date=TODAY + timedelta(days=1))
    nothing = a_job("J-NONE", a_task("Prep", job_id="J-NONE"), client_id="CL-2")

    picked = workable([typed, nothing], today=TODAY, tax_year=2025,
                      policy=only("deadline"))
    assert all(not i.deadline_known and i.deadline is None for i in picked)
    assert all(i.score == 0.0 for i in picked)


def test_a_deadline_resting_on_an_assumption_says_so():
    job = a_job("J-1", a_task("File the 941"), obligation_key="K-941")
    duty = Duty("K-941", TODAY + timedelta(days=4), form="941", is_assumed=True)
    item = workable([job], obligations=[duty], today=TODAY, tax_year=2025)[0]
    assert "unconfirmed assumption" in item.why


# --- the ordering is preference, and changing it changes the order -----------

def test_changing_a_weight_in_the_config_changes_the_order(tmp_path):
    """Written to a temp config, never to the shipped one. If this ever passes
    with the weights ignored, the config is decoration."""
    urgent_but_heavy = a_job("J-URGENT",
                             *[a_task(f"Prep {n}", job_id="J-URGENT") for n in range(6)],
                             obligation_key="K-URGENT")
    slack_but_tiny = a_job("J-TINY", a_task("Prep", job_id="J-TINY"),
                           obligation_key="K-TINY", client_id="CL-2")
    duties = [Duty("K-URGENT", TODAY + timedelta(days=2)),
              Duty("K-TINY", TODAY + timedelta(days=40))]

    def policy_from(text: str) -> QueuePolicy:
        (tmp_path / "firm_policy.yaml").write_text(text, encoding="utf-8")
        return load_queue_policy(tmp_path)

    deadline_first = policy_from(
        "queue:\n  horizon_days: 45\n  weights:\n"
        "    deadline: 1.0\n    idle: 0.0\n    unblocks: 0.0\n    quick_win: 0.1\n")
    quick_first = policy_from(
        "queue:\n  horizon_days: 45\n  weights:\n"
        "    deadline: 0.1\n    idle: 0.0\n    unblocks: 0.0\n    quick_win: 1.0\n")

    jobs = [urgent_but_heavy, slack_but_tiny]
    assert [i.job_id for i in workable(jobs, obligations=duties, today=TODAY,
                                       tax_year=2025, policy=deadline_first)] \
        == ["J-URGENT", "J-TINY"]
    assert [i.job_id for i in workable(jobs, obligations=duties, today=TODAY,
                                       tax_year=2025, policy=quick_first)] \
        == ["J-TINY", "J-URGENT"]


def test_every_rank_is_flagged_as_firm_policy_rather_than_law():
    jobs = [a_job("J-1", a_task("Prep"))]
    view = board(jobs, today=TODAY, tax_year=2025)
    assert view.ordering_is_firm_policy
    assert view.policy.is_firm_policy
    assert all(i.ordering_is_firm_policy for i in view.workable)


# --- the policy loader: preference, so no citation required ------------------

def test_the_policy_loader_asks_for_no_citation(tmp_path):
    """The mirror image of the statutory loader, which refuses an uncited rule.
    Nothing in firm policy has an authority behind it, so nothing may be
    demanded of it."""
    (tmp_path / "firm_policy.yaml").write_text(
        "queue:\n  weights:\n    deadline: 2.0\n", encoding="utf-8")
    pol = load_queue_policy(tmp_path)
    assert pol.configured and pol.is_firm_policy
    assert pol.weight("deadline") == 2.0


def test_no_preference_on_file_is_not_the_same_as_a_preference(tmp_path):
    (tmp_path / "firm_policy.yaml").write_text("cutoffs: {}\n", encoding="utf-8")
    pol = load_queue_policy(tmp_path)
    assert pol.configured is False
    assert dict(pol.weights) == DEFAULT_WEIGHTS


def test_a_factor_the_config_did_not_mention_is_flagged_as_defaulted(tmp_path):
    (tmp_path / "firm_policy.yaml").write_text(
        "queue:\n  weights:\n    deadline: 1.0\n", encoding="utf-8")
    pol = load_queue_policy(tmp_path)
    assert pol.configured is True
    assert set(pol.defaulted_weights) == {"idle", "unblocks", "quick_win"}


@pytest.mark.parametrize("body, expected", [
    ("queue:\n  weights:\n    deadlien: 1.0\n", "deadlien"),
    ("queue:\n  weights:\n    deadline: -1.0\n", "negative"),
    ("queue:\n  weights:\n    deadline: soon\n", "must be a number"),
    ("queue:\n  horizon_days: 0\n  weights:\n    deadline: 1.0\n", "at least 1 day"),
    ("queue:\n  weights:\n    deadline: 0\n    idle: 0\n    unblocks: 0\n"
     "    quick_win: 0\n", "nothing to order on"),
])
def test_a_config_that_cannot_mean_what_it_says_is_refused_and_names_the_fix(
        tmp_path, body, expected):
    (tmp_path / "firm_policy.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ConfigError) as err:
        load_queue_policy(tmp_path)
    assert expected in str(err.value)
    assert "firm_policy.yaml" in str(err.value)


def test_the_shipped_policy_actually_loads_and_is_configured():
    """Principle 12's other half — a config nothing reads is a config that
    breaks silently."""
    pol = load_queue_policy()
    assert pol.configured is True
    assert pol.defaulted_weights == ()
    assert pol.weight("deadline") > 0


# --- it proposes, it does not dispose ----------------------------------------

def test_ranking_writes_nothing_and_starts_nothing():
    """No assignment, no status change, and the stale stage cache is left
    exactly as it was found."""
    job = a_job("J-1", a_task("Prep"), a_task("Review", category="Review"))
    job.stage = "complete"
    before = (job.stage, [(t.task_id, t.status, t.completion) for t in job.tasks])

    items = workable([job], today=TODAY, tax_year=2025)

    assert (job.stage, [(t.task_id, t.status, t.completion) for t in job.tasks]) == before
    assert not any(hasattr(items[0], attr)
                   for attr in ("assigned_to", "assignee", "started_at", "reserved_by"))


def test_the_stored_stage_is_not_what_decides_workability():
    """A job carrying stage='complete' with a missing W-2 is waiting, whatever
    the field says."""
    job = a_job("J-1", a_task("Prep"))
    job.stage = "complete"
    assert workable([job], requested=[an_open_item("W-2")], today=TODAY,
                    tax_year=2025) == []
    assert [b.job_id for b in not_workable([job], requested=[an_open_item("W-2")],
                                           today=TODAY, tax_year=2025)] == ["J-1"]


# --- every row can be argued with --------------------------------------------

def test_every_row_carries_its_evidence_in_one_line():
    jobs = [a_job("J-1", a_task("Prep"), obligation_key="K-1",
                  updated=TODAY - timedelta(days=9)),
            a_job("J-2", a_task("Prep", job_id="J-2"),
                  a_task("Later", job_id="J-2", blocked_by=("Prep",)),
                  client_id="CL-2")]
    duties = [Duty("K-1", TODAY + timedelta(days=6))]
    view = board(jobs, obligations=duties, today=TODAY, tax_year=2025)

    for item in view.workable:
        assert item.why.strip()
        assert "\n" not in item.why
        assert any(ch.isdigit() for ch in item.why), item.why
    for stuck in view.not_workable:
        assert stuck.why.strip()


def test_two_rows_do_not_say_the_same_thing():
    """Principle 13. A queue whose rows are interchangeable is one the owner
    learns to scroll past."""
    jobs = [a_job("J-1", a_task("Prep"), obligation_key="K-1",
                  updated=TODAY - timedelta(days=3)),
            a_job("J-2", a_task("Prep", job_id="J-2"), a_task("Prep 2", job_id="J-2"),
                  obligation_key="K-2", client_id="CL-2",
                  updated=TODAY - timedelta(days=17))]
    duties = [Duty("K-1", TODAY + timedelta(days=6)),
              Duty("K-2", TODAY + timedelta(days=30), form="1065")]
    reasons = [i.why for i in workable(jobs, obligations=duties, today=TODAY,
                                       tax_year=2025)]
    assert len(set(reasons)) == len(reasons)


def test_a_factor_carries_the_weight_that_moved_it():
    """The rank has to be auditable to the number that produced it, or the
    owner cannot tell a preference they set from one they inherited."""
    job = a_job("J-1", a_task("Prep"), obligation_key="K-1")
    duty = Duty("K-1", TODAY + timedelta(days=5))
    item = workable([job], obligations=[duty], today=TODAY, tax_year=2025,
                    policy=only("deadline"))[0]
    deadline = next(f for f in item.factors if f.key == "deadline")
    assert deadline.weight == 1.0
    assert deadline.contribution == pytest.approx(deadline.score * 1.0)
    assert item.score == pytest.approx(deadline.contribution)
    assert {f.key for f in item.factors} == set(FACTOR_KEYS)


def test_with_every_weight_off_nothing_is_dropped_and_the_order_stays_total():
    """A flat policy must still produce a usable, repeatable list — the queue
    degrades to alphabetical, it does not become random or empty."""
    jobs = [a_job("J-3", a_task("Prep", job_id="J-3"), client_id="CL-3"),
            a_job("J-1", a_task("Prep", job_id="J-1")),
            a_job("J-2", a_task("Prep", job_id="J-2"), client_id="CL-2")]
    picked = workable(jobs, today=TODAY, tax_year=2025, policy=FLAT)
    assert [i.job_id for i in picked] == ["J-1", "J-2", "J-3"]
    assert all(i.why.strip() for i in picked)


# --- the year filter ----------------------------------------------------------

def test_asking_for_one_year_does_not_return_another():
    jobs = [a_job("J-2025", a_task("Prep", job_id="J-2025"), tax_year=2025),
            a_job("J-2024", a_task("Prep", job_id="J-2024"), tax_year=2024,
                  client_id="CL-2")]
    assert [i.job_id for i in workable(jobs, today=TODAY, tax_year=2025)] == ["J-2025"]
