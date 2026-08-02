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


# --- the rate plan is a term of the CONTRACT ----------------------------------

def _engagement(client_id="C", tax_year=2025, **kw):
    from satc.models.work import Engagement

    return Engagement(client_id=client_id, tax_year=tax_year, **kw)


def test_the_agreed_rate_plan_survives_persistence(tmp_path):
    """It is agreed once, on the contract — so it has to still be there next year.

    Deciding it per-invoice meant re-deciding it every time and never being able
    to answer "what is this client on?" without reading old invoices.
    """
    from satc.models.mart import DataMart
    from satc.persistence import SATCStore

    mart = DataMart()
    mart.engagements = [_engagement(rate_plan_key="household",
                                    rate_plan_basis="single income, two children")]
    with SATCStore(tmp_path) as store:
        store.save_mart(mart)

    with SATCStore(tmp_path) as store:
        back = store.load_mart().engagements
    assert len(back) == 1
    assert back[0].rate_plan_key == "household"
    assert back[0].rate_plan_basis == "single income, two children"


def test_a_reduced_plan_with_no_basis_loads_and_is_visible_as_such(tmp_path):
    """History must ALWAYS load. The refusal belongs at invoice-issue time,
    where it already lives — a store that raised here would make the record
    unreadable exactly when the owner needs to see what went wrong."""
    from satc.models.mart import DataMart
    from satc.models.work import rate_plan_for
    from satc.persistence import SATCStore

    mart = DataMart()
    mart.engagements = [_engagement(rate_plan_key="hardship", rate_plan_basis="")]
    with SATCStore(tmp_path) as store:
        store.save_mart(mart)

    with SATCStore(tmp_path) as store:
        back = store.load_mart().engagements          # no raise

    on_file = rate_plan_for(back, client_id="C", tax_year=2025)
    assert on_file.plan_key == "hardship"
    assert on_file.is_agreed
    assert on_file.basis_missing                       # VISIBLE, not fatal
    assert "no basis is recorded" in on_file.why()


def test_the_default_is_reported_as_a_fallback_not_as_a_decision():
    """Principle 2: an unanswered question is not an answer. A client nobody has
    priced and a client explicitly put on standard read the same as bare strings."""
    from satc.models.work import rate_plan_for

    nobody_decided = rate_plan_for([], client_id="C", tax_year=2025)
    decided = rate_plan_for([_engagement(rate_plan_key="standard")],
                            client_id="C", tax_year=2025)

    assert nobody_decided.plan_key == decided.plan_key == "standard"
    assert nobody_decided.is_fallback and not nobody_decided.is_agreed
    assert decided.is_agreed and not decided.is_fallback
    assert nobody_decided.why() != decided.why()
    assert "No rate plan agreed" in nobody_decided.why()
    assert "agreed on the 2025 engagement" in decided.why()


def test_an_engagement_for_another_year_is_not_this_years_agreement():
    """The contract is per (client, year). Last year's household rate is not
    this year's — means change, and honouring a lapsed term silently is how a
    discount becomes permanent by accident."""
    from satc.models.work import rate_plan_for

    prior = [_engagement(tax_year=2024, rate_plan_key="hardship",
                         rate_plan_basis="job loss")]
    assert rate_plan_for(prior, client_id="C", tax_year=2025).is_fallback
    assert rate_plan_for(prior, client_id="C", tax_year=2024).is_agreed
    assert rate_plan_for(prior, client_id="OTHER", tax_year=2024).is_fallback


def test_a_blank_plan_key_is_an_empty_slot_not_the_standard_rate():
    """A row that predates the field carries NULL, which is silence. Reading
    silence as "standard" would invent a value nobody recorded."""
    from satc.models.work import rate_plan_for

    on_file = rate_plan_for([_engagement(rate_plan_key="")],
                            client_id="C", tax_year=2025)
    assert on_file.plan_key == "standard"       # what applies meanwhile
    assert on_file.is_fallback                  # but nobody agreed it
    assert not on_file.basis_missing            # nothing to be missing yet


def test_an_engagement_born_with_no_plan_recorded_is_not_an_agreement():
    """The shape that actually occurs in production, which nothing else covers.

    Every other test here hands ``rate_plan_key=`` in explicitly, or passes no
    engagement at all. Neither is what the code does: it builds
    ``Engagement(client_id=..., tax_year=...)`` and lets the field default
    stand. While that default was ``"standard"``, every engagement in the
    system was born carrying an explicit agreement to pay full rate, so
    ``is_fallback`` — which consumers surface as "nobody has priced this
    client" — could only ever be true for legacy NULL rows. Principle 2: an
    unanswered question is not an answer.
    """
    from satc.models.work import Engagement, rate_plan_for

    born = Engagement(client_id="C", tax_year=2025)      # no plan argument
    assert born.rate_plan_key == "", (
        "The empty slot has to read as silence. A default plan key is an "
        "agreement nobody made.")

    on_file = rate_plan_for([born], client_id="C", tax_year=2025)
    assert on_file.is_fallback and not on_file.is_agreed
    assert "No rate plan agreed" in on_file.why()


def test_no_client_in_the_shipped_fixtures_arrives_already_priced():
    """The reproduction, against the real fixtures rather than a hand-built one.

    Nobody sat down and priced SATC-001000. If the demo data says somebody did,
    the flag is worthless everywhere it is shown.
    """
    from satc.fixtures.synthetic import synthetic_mart
    from satc.models.work import rate_plan_for

    engagements = synthetic_mart().engagements
    assert engagements                                   # the fixture still has some
    on_file = [rate_plan_for(engagements, client_id=e.client_id, tax_year=e.tax_year)
               for e in engagements]
    assert all(r.is_fallback for r in on_file), (
        "A fixture client whose price nobody chose must read as unpriced: "
        + "; ".join(f"{r.client_id} {r.why()}" for r in on_file if r.is_agreed))


# --- the catalogue is hand-edited, so a plan key can go stale ------------------

def test_an_engagement_on_a_retired_plan_still_loads_and_says_so(tmp_path):
    """Renaming a plan in the YAML must not make last year's contract unreadable.

    The store goes out of its way to keep history loading; resolving the key
    through ``plan()`` put the raise back one layer up. Resolving it to the
    default instead would be worse — that invents an agreement (principle 1) —
    so the stale key is carried through, flagged, and named.
    """
    from satc.models.mart import DataMart
    from satc.models.work import rate_plan_for
    from satc.persistence import SATCStore

    mart = DataMart()
    mart.engagements = [_engagement(rate_plan_key="legacy_rate",
                                    rate_plan_basis="agreed back in 2019")]
    with SATCStore(tmp_path) as store:
        store.save_mart(mart)
    with SATCStore(tmp_path) as store:
        back = store.load_mart().engagements              # no raise

    on_file = rate_plan_for(back, client_id="C", tax_year=2025)
    assert on_file.plan_key == "legacy_rate"              # NOT quietly 'standard'
    assert on_file.plan_missing
    assert on_file.is_agreed and not on_file.is_fallback  # somebody did decide
    assert "no longer in the rate plan catalogue" in on_file.why()


def test_a_plan_the_catalogue_still_has_is_not_flagged_as_missing():
    """The other direction of the same switch — so `plan_missing` means something."""
    from satc.models.work import rate_plan_for

    assert not rate_plan_for([_engagement(rate_plan_key="hardship")],
                             client_id="C", tax_year=2025).plan_missing
    assert not rate_plan_for([], client_id="C", tax_year=2025).plan_missing


def test_pricing_a_screenful_of_clients_reads_the_yaml_once(monkeypatch):
    """The fallback answer is one line long and is needed once per unpriced
    client. Parsing rate_plans.yaml per row cost milliseconds a client and let
    two reads inside one request see different versions of the file."""
    from satc.billing import catalogue
    from satc.models.work import rate_plan_for

    reads: list = []
    real_load = catalogue._load
    monkeypatch.setattr(catalogue, "_load",
                        lambda p: (reads.append(p), real_load(p))[1])
    catalogue.forget_prices()
    try:
        for n in range(50):
            assert rate_plan_for([], client_id=f"C{n}", tax_year=2025).is_fallback
    finally:
        catalogue.forget_prices()

    assert len(reads) <= 2, (
        f"rate_plans.yaml was parsed {len(reads)} times for 50 clients — "
        f"the mtime cache exists so it is parsed once.")


def test_a_full_rate_plan_needs_no_basis_to_be_complete():
    """`requires_basis` is the catalogue's rule, not this helper's. Standard is
    the default; asking for a reason to charge full price is noise."""
    from satc.models.work import rate_plan_for

    on_file = rate_plan_for([_engagement(rate_plan_key="standard")],
                            client_id="C", tax_year=2025)
    assert not on_file.requires_basis
    assert not on_file.basis_missing
