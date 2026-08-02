"""Tests for the interview fan-out (:mod:`satc.intake.fanout`).

The claim under test is that ONE call turns interview answers into everything
that follows for an engagement — the tasks, the document requests, the
statutory deadline with its citation, the obligation key the work queue orders
on, the quote, and the facts the engagement letter needs — so that no downstream
screen re-derives any of it and disagrees.

Every test here fails without the behaviour it names; the mutation runs are
recorded in the report for this change (principle 12).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import dataclasses

import pytest

from satc.config import ConfigError
from satc.intake.fanout import ENTITY_TYPE_BY_WORKFLOW, duty_rule_for, fan_out
from satc.intake.workflows import load_workflow
from satc.models.work import Engagement

TODAY = date(2026, 1, 15)
YEAR = 2025
CLIENT = "SATC-004000"

# The rental branch of the 1040 interview. One answer that must produce a task,
# a document request AND a quote line — the whole point of the module.
INVESTMENTS = {"newSatcClient": "no", "brokerageActivity": "yes"}


def a_plan(answers=None, **kw):
    workflow = load_workflow(kw.pop("workflow_key", "personal_1040_core"))
    kw.setdefault("client_id", CLIENT)
    kw.setdefault("tax_year", YEAR)
    kw.setdefault("today", TODAY)
    return fan_out(workflow, answers if answers is not None else {}, **kw)


def agreed_plan(client_id=CLIENT, tax_year=YEAR, key="standard", basis="agreed at intake"):
    """A billing contract on file, so the quote is not on a fallback plan."""
    return [Engagement(client_id=client_id, tax_year=tax_year,
                       rate_plan_key=key, rate_plan_basis=basis)]


# ---------------------------------------------------------------------------
# One answer, one call, three consequences
# ---------------------------------------------------------------------------

def test_one_answer_produces_its_task_its_request_and_its_quote_line():
    plan = a_plan(INVESTMENTS, engagements=agreed_plan())

    task = next((t for t in plan.tasks
                 if t.template_id == "personal-1040-brokerage-crypto-documents"), None)
    assert task is not None, "the brokerage answer must generate its task"

    request = next((r for r in plan.requests if r.task_id == task.task_id), None)
    assert request is not None, "the same answer must open its document request"
    assert request.doc_type == "Brokerage 1099 / crypto exports"

    codes = [line.service_code for line in plan.quote.lines]
    assert "schedule_d" in codes, "the same answer must put its price on the quote"

    # And the three agree about WHY they exist: the task, the request and the
    # line all trace to the one answer.
    assert task.request_id == request.request_id


def test_an_unanswered_branch_produces_nothing_anywhere():
    """An explicit "no" is not an unanswered question — neither generates work."""
    plan = a_plan({"newSatcClient": "no", "brokerageActivity": "no"},
                  engagements=agreed_plan())
    assert not [t for t in plan.tasks
                if t.template_id == "personal-1040-brokerage-crypto-documents"]
    assert "schedule_d" not in [line.service_code for line in plan.quote.lines]


# ---------------------------------------------------------------------------
# (1) The deadline is COMPUTED from a cited rule, never keyed in
# ---------------------------------------------------------------------------

def test_the_deadline_is_the_computed_statutory_one_and_carries_its_citation():
    plan = a_plan(INVESTMENTS)

    # 2025 individual return: the 15th day of the 4th month after year end.
    # April 15 2026 is a Wednesday, so no §7503 shift applies.
    assert plan.duty.statutory_due == date(2026, 4, 15)
    assert plan.due_date == date(2026, 4, 15)
    assert plan.job.due_date == plan.duty.due

    assert "IRC §6072(a)" in plan.citation
    assert plan.duty.rule_key == "form_1040"


def test_the_deadline_shifts_off_a_weekend_because_it_is_computed_not_stored():
    """2027's April 15 is a Thursday; 2021's was fine — 2022's April 15 was a
    Friday but Emancipation Day pushed it. Use a year that genuinely moves."""
    plan = a_plan(INVESTMENTS, tax_year=2016)
    # April 15 2017 is a Saturday; IRC §7503 moves the act to the next business
    # day. A stored constant would still say the 15th.
    assert plan.duty.statutory_due == date(2017, 4, 15)
    assert plan.duty.due > plan.duty.statutory_due
    assert plan.duty.shift_reason


def test_no_passed_in_due_date_can_drive_the_engagement():
    """fan_out has no due_date parameter at all — that is the fix."""
    with pytest.raises(TypeError):
        a_plan(INVESTMENTS, due_date=date(2026, 12, 25))


def test_the_task_dates_hang_off_the_computed_deadline():
    plan = a_plan(INVESTMENTS)
    task = next(t for t in plan.tasks
                if t.template_id == "personal-1040-upload-w2-1099-core")
    assert (plan.duty.due - task.suggested_date).days == 21


def test_a_business_workflow_lands_on_its_own_duty_not_the_individual_one():
    plan = a_plan({}, workflow_key="business_scorp_tax")
    assert plan.duty.rule_key == "form_1120s"
    assert plan.duty.statutory_due == date(2026, 3, 15)
    assert plan.duty.due == date(2026, 3, 16)   # Mar 15 2026 is a Sunday
    assert plan.duty.form == "1120S"
    assert plan.job.due_date == date(2026, 3, 16)


# ---------------------------------------------------------------------------
# (1b) An unsourced jurisdiction REFUSES, by name
# ---------------------------------------------------------------------------

def test_a_jurisdiction_with_no_sourced_rules_refuses_and_names_it():
    with pytest.raises(ConfigError) as excinfo:
        a_plan(INVESTMENTS, jurisdiction="OH")
    message = str(excinfo.value)
    assert "'OH'" in message
    assert "will not fall back to the federal calendar" in message
    assert "configs/obligations/oh.yaml" in message


def test_a_sourced_state_computes_its_own_deadline():
    """Massachusetts is on file, so it answers — with the MA rule, not the
    federal one. This is the counterpart that proves the refusal above is a
    refusal and not a blanket inability to do states."""
    plan = a_plan(INVESTMENTS, jurisdiction="MA")
    assert plan.duty.rule_key == "ma_form_1"
    assert plan.duty.jurisdiction == "MA"
    assert "MA" in plan.obligation_key


def test_the_clients_recorded_entity_type_beats_the_workflow_table():
    """A recorded fact about the taxpayer outranks which button the owner
    clicked. A partnership run through the 1040 workflow must not get an
    April 15 date off a table (principle 2)."""
    plan = a_plan({}, entity_type="PARTNERSHIP", entity_type_basis="agency_notice")
    assert plan.duty.rule_key == "form_1065"
    assert plan.duty.due == date(2026, 3, 16)          # Mar 15 2026 is a Sunday
    assert "/1065/" in plan.obligation_key


def test_an_entity_type_no_cited_rule_covers_refuses_by_name():
    with pytest.raises(ConfigError) as excinfo:
        a_plan({}, entity_type="SOLEPROP", entity_type_basis="prior_filing")
    assert "SOLEPROP" in str(excinfo.value)
    assert "configs/obligations/us.yaml" in str(excinfo.value)


# ---------------------------------------------------------------------------
# (1c) A GUESSED entity type never acquires a citation
# ---------------------------------------------------------------------------
#
# The importer defaults an unknown business to SCORP ("most common small-
# business default"). Whether an entity is an S corporation is assigned by the
# IRS in writing, so that value is a guess — and a guess that reaches here
# would not shift a date, it would invent a whole filing duty, key it, and merge
# it into the client's obligation set where nothing can clear it.

def test_an_unsourced_entity_type_cannot_buy_a_citation():
    """The reproduction: a business the importer guessed SCORP, run through the
    individual interview, used to come back with a March 15 1120-S deadline and
    IRC §6072(b) behind it — recorded, apparently, as fact."""
    with pytest.raises(ConfigError) as excinfo:
        a_plan({}, entity_type="SCORP")                # no basis: nobody said so
    message = str(excinfo.value)
    assert "SCORP" in message
    assert "no record of how it knows" in message.lower()
    assert "assigned by the IRS in writing" in message
    # Principle 10: the refusal names what would have been right.
    assert "2553" in message and "CP261" in message


def test_creating_a_business_with_no_stated_entity_type_refuses(tmp_path):
    """The other end of the same rope. The vault used to record SCORP for a
    business nobody typed a type for, and everything downstream then read it as
    a fact about the taxpayer."""
    from satc.intake.service import create_business_client
    from satc.persistence import SATCStore

    store = SATCStore(tmp_path)
    with pytest.raises(ValueError) as excinfo:
        create_business_client(store, legal_name="Riverbend Holdings",
                               entity_type="", ein="12-3456789")
    assert "assigned by the IRS in writing" in str(excinfo.value)
    assert "PARTNERSHIP" in str(excinfo.value)      # names the real options
    assert not store.load_mart().public_clients, "nothing may be recorded on a refusal"


def test_an_unsourced_entity_type_that_only_agrees_with_the_owners_choice_is_harmless():
    """It contradicts nothing and decides nothing — the workflow the owner chose
    already says what is being prepared, and that is a human act rather than a
    table's opinion about what an entity IS."""
    plan = a_plan({}, workflow_key="business_scorp_tax", entity_type="SCORP")
    assert plan.duty.rule_key == "form_1120s"


def test_a_recorded_entity_type_still_decides_the_duty():
    """The counterpart that proves the refusal is a refusal and not an inability
    to use a client record at all."""
    plan = a_plan({}, workflow_key="business_scorp_tax",
                  entity_type="PARTNERSHIP", entity_type_basis="stated_by_client")
    assert plan.duty.rule_key == "form_1065"


def test_an_assumed_default_is_not_a_basis():
    """`assumed_default` is the ProfileFact basis that means "nothing told us".
    It is a label for a guess, not a licence for one."""
    with pytest.raises(ConfigError):
        a_plan({}, entity_type="SCORP", entity_type_basis="assumed_default")


def test_a_guessed_entity_type_cannot_be_smuggled_in_through_the_client_record(tmp_path):
    """End to end, through the real importer, the real store and the real door.

    ``add_client_smart(name='Riverbend Holdings', entity_type='')`` records
    SCORP in the mart although nobody said so. The mart cannot say where that
    value came from, so the engagement refuses rather than deriving a 1120-S
    deadline from it."""
    from satc.intake import importer
    from satc.intake.service import commit_import, create_engagement_from_intake
    from satc.persistence import SATCStore

    store = SATCStore(tmp_path)
    parsed = importer.parse_one(name="Riverbend Holdings", tin="12-3456789",
                                entity_type="")
    assert parsed.entity_type == "SCORP", "the importer still guesses (upstream fix)"
    cid = commit_import(store, [parsed], include_duplicates=True)[0]

    with pytest.raises(ConfigError) as excinfo:
        create_engagement_from_intake(
            store, client_id=cid, workflow_key="personal_1040_core",
            tax_year=YEAR, answers={}, today=TODAY)
    assert "SCORP" in str(excinfo.value)
    assert not store.load_jobs(), "nothing may be written on a refused derivation"


def test_a_workflow_with_no_filing_duty_has_no_deadline_rather_than_a_wrong_one():
    """Bookkeeping files nothing, so no statute has an opinion about when it is
    due. That is a true ANSWER about the engagement, not a failure to compute
    one — and it must not cost the owner the workflow.

    Refusing it outright (the first attempt at this) made two of the four
    workflows the app offers a business client unreachable, which is a worse
    failure than the deadline it was preventing.
    """
    from satc.intake.fanout import NO_FILING_DUTY, NoFilingDuty, duty_for

    workflow = load_workflow("business_monthly_bookkeeping")
    assert workflow.key in NO_FILING_DUTY
    assert workflow.key not in ENTITY_TYPE_BY_WORKFLOW

    with pytest.raises(NoFilingDuty):
        duty_rule_for(workflow)
    assert duty_for(workflow, client_id=CLIENT, tax_year=YEAR) is None


def test_a_workflow_in_neither_list_refuses_rather_than_becoming_service_work():
    """Absence must not mean "files nothing". A filing workflow somebody forgot
    to register would otherwise lose its deadline silently."""
    from satc.intake.fanout import NO_FILING_DUTY, duty_rule_for as _drf

    workflow = load_workflow("personal_1040_core")
    unknown = dataclasses.replace(workflow, key="brand_new_workflow")
    assert unknown.key not in ENTITY_TYPE_BY_WORKFLOW
    assert unknown.key not in NO_FILING_DUTY

    with pytest.raises(ConfigError) as excinfo:
        _drf(unknown)
    assert "does not know whether" in str(excinfo.value)
    assert "NO_FILING_DUTY" in str(excinfo.value)      # names both next steps
    assert "ENTITY_TYPE_BY_WORKFLOW" in str(excinfo.value)


# ---------------------------------------------------------------------------
# (2) obligation_key is set, and matches the duty
# ---------------------------------------------------------------------------

def test_the_job_records_the_obligation_key_of_the_duty_it_discharges():
    plan = a_plan(INVESTMENTS)
    assert plan.job.obligation_key, "build_engagement alone leaves this empty"
    assert plan.job.obligation_key == plan.duty.obligation_key
    assert plan.job.obligation_key == f"{CLIENT}/file/1040/US/{YEAR}"
    assert plan.job.period_key == str(YEAR)


def test_the_obligation_key_matches_the_one_materialise_would_build():
    """The queue joins jobs to duties on this key. Two spellings of it is two
    rows that never meet."""
    from satc.obligations.profile import obligation_key

    plan = a_plan(INVESTMENTS)
    assert plan.job.obligation_key == obligation_key(
        CLIENT, "file", "1040", "US", str(YEAR))


def test_the_queue_can_find_the_duty_behind_a_fanned_out_job():
    """The end the fix exists for: deadline pressure ranks a real job."""
    from satc.work.queue import board

    # A workflow with internal work on it, so the job reaches the workable half
    # at all — the deadline is what is under test, not the stage machine.
    plan = a_plan({}, workflow_key="personal_rental_schedule_e")
    result = board([plan.job], obligations=[plan.duty], today=TODAY)
    assert result.workable, "the job must reach the workable half of the board"
    item = result.workable[0]
    assert item.deadline_known and item.deadline == plan.duty.due, \
        "the board must resolve the job's deadline from its obligation_key"

    # Mutation guard: strip the key — which is the state build_engagement leaves
    # every job in — and the board can no longer find the duty at all.
    plan.job.obligation_key = ""
    blind = board([plan.job], obligations=[plan.duty], today=TODAY)
    assert not blind.workable[0].deadline_known


# ---------------------------------------------------------------------------
# (3) The engagement letter is fed — and invents nothing
# ---------------------------------------------------------------------------

def test_the_letter_facts_carry_the_derived_scope_deadline_and_asks():
    plan = a_plan(INVESTMENTS, engagements=agreed_plan())
    facts = plan.letter_facts

    assert facts["tax_year"] == str(YEAR)
    assert facts["due_date"] == "April 15, 2026"
    assert "Your federal individual tax return" in facts["scope_of_services"]
    assert "Upload Forms W-2" in facts["requested_items"]


def test_the_letter_states_no_fee_when_nobody_agreed_a_rate_plan():
    """No engagement on file means the practice default applies as a FALLBACK —
    nobody decided what this client pays, so the letter must not say."""
    plan = a_plan(INVESTMENTS)             # no engagements passed
    assert plan.quote.plan_is_fallback
    assert "fee_terms" not in plan.letter_facts
    assert "fee_amount_text" not in plan.letter_facts


def test_the_letter_states_no_bare_amount_while_work_is_unpriced():
    """personal_1040_core prices state returns at `quantity: unknown`, so the
    total is not the whole price. The honest sentence is offered; the bare
    number is not."""
    plan = a_plan(INVESTMENTS, engagements=agreed_plan())
    assert plan.quote.unpriced
    assert "fee_terms" in plan.letter_facts
    assert "fee_amount_text" not in plan.letter_facts
    assert "does not include" in plan.letter_facts["fee_terms"]


def test_a_letter_fact_the_practice_lacks_is_absent_so_the_draft_marks_it():
    """The contract with RenderedDraft: absent, never blank, never guessed."""
    from satc.comms.render import render
    from satc.comms.library import library

    plan = a_plan(INVESTMENTS)             # fallback plan -> no fee is a fact
    assert all(str(v).strip() for v in plan.letter_facts.values()), \
        "a blank value would render as an empty gap instead of a marker"

    draft = render(library().template("engagement_letter"), plan.letter_facts,
                   library=library())
    assert "fee_terms" in draft.unfilled
    assert "[[ Fee terms: fill in ]]" in draft.body
    assert "scope_of_services" in draft.filled


def test_the_letter_facts_never_carry_a_pii_bearing_value():
    plan = a_plan(INVESTMENTS, engagements=agreed_plan())
    blob = "\n".join(plan.letter_facts.values())
    assert CLIENT in blob                      # the opaque handle is fine
    # No TIN-shaped run anywhere. The fan-out is fed a client_id and answers,
    # never the vault, so this asserts the seam stays that way.
    assert not re.search(r"\b\d{3}-?\d{2}-?\d{4}\b", blob)


# ---------------------------------------------------------------------------
# (8) Re-running the interview is safe
# ---------------------------------------------------------------------------

def test_re_running_with_the_same_answers_changes_nothing():
    first = a_plan(INVESTMENTS, engagements=agreed_plan())
    second = a_plan(INVESTMENTS, engagements=agreed_plan(),
                    existing_tasks=first.tasks)

    assert second.job.job_id == first.job.job_id
    assert [t.task_id for t in second.tasks] == [t.task_id for t in first.tasks]
    assert [t.template_id for t in second.tasks] == [t.template_id for t in first.tasks]
    assert second.job.obligation_key == first.job.obligation_key
    assert second.due_date == first.due_date
    assert second.out_of_scope == ()
    # The asks already open are not opened a second time.
    assert second.requests == ()


def test_ids_do_not_depend_on_when_the_run_happened():
    """Even with no previous tasks in hand, a re-run lands on the same ids."""
    first = a_plan(INVESTMENTS)
    second = a_plan(INVESTMENTS)
    assert second.job.job_id == first.job.job_id
    assert [t.task_id for t in second.tasks] == [t.task_id for t in first.tasks]
    assert [r.request_id for r in second.requests] == \
           [r.request_id for r in first.requests]


def test_a_changed_answer_preserves_work_in_flight_and_says_what_left_scope():
    first = a_plan({"newSatcClient": "no", "marketplaceInsurance": "yes"})
    marketplace = next(t for t in first.tasks
                       if t.template_id == "personal-1040-marketplace-1095a")
    marketplace.status = "in_progress"
    marketplace.notes = "1095-A chased, half reconciled"

    # They say no to Marketplace coverage this year.
    second = a_plan({"newSatcClient": "no", "marketplaceInsurance": "no"},
                    existing_tasks=first.tasks)

    gone = [o for o in second.out_of_scope
            if o.template_id == "personal-1040-marketplace-1095a"]
    assert len(gone) == 1, "the removal must be reported, not silent"
    assert gone[0].had_progress and gone[0].retained
    assert "no longer in scope" in gone[0].why
    assert gone[0].why.strip(), "every queue row carries its own evidence"

    kept = next((t for t in second.tasks if t.template_id ==
                 "personal-1040-marketplace-1095a"), None)
    assert kept is not None, "work already started is never silently deleted"
    assert kept.status == "in_progress"
    assert kept.notes == "1095-A chased, half reconciled"


def test_work_that_left_scope_is_not_asked_of_the_client_in_the_same_breath():
    """One call must not say two things about one engagement.

    The retained task goes back onto the job so the owner can still see and
    cancel it — and it used to go into the letter's ``requested_items`` with
    it, so the plan said "out of scope" and the letter said "please send us
    your Form 1095-A", to the one person who cannot see the plan."""
    first = a_plan({"newSatcClient": "no", "marketplaceInsurance": "yes"},
                   engagements=agreed_plan())
    assert "1095-A" in first.letter_facts["requested_items"]

    second = a_plan({"newSatcClient": "no", "marketplaceInsurance": "no"},
                    engagements=agreed_plan(), existing_tasks=first.tasks)

    assert [o.template_id for o in second.out_of_scope] == \
           ["personal-1040-marketplace-1095a"]
    assert any(t.template_id == "personal-1040-marketplace-1095a"
               for t in second.tasks), "still on the job, so it can be cancelled"
    assert "1095-A" not in second.letter_facts["requested_items"], \
        "the letter must not ask for a document the same plan calls out of scope"


def test_a_task_that_left_scope_opens_no_new_document_request():
    """A retained client task with no request of its own must not acquire one.

    The requests are opened from the tasks the ANSWERS produced; work the
    answers removed is not work to chase. This one has progress but was never
    asked for, so nothing in the register covers it — and nothing should."""
    first = a_plan({"newSatcClient": "no", "marketplaceInsurance": "yes"})
    marketplace = next(t for t in first.tasks
                       if t.template_id == "personal-1040-marketplace-1095a")
    marketplace.status = "in_progress"
    marketplace.request_id = ""          # never actually asked

    second = a_plan({"newSatcClient": "no", "marketplaceInsurance": "no"},
                    existing_tasks=first.tasks)

    assert marketplace.template_id in {o.template_id for o in second.out_of_scope}
    assert not [r for r in second.requests if "1095" in str(r.doc_type)], \
        "no request may be opened for work these answers took out of scope"
    assert not marketplace.request_id, "and the task must not be marked as asked"


def test_a_settled_out_of_scope_task_is_kept_but_stops_being_reported():
    """Principle 13: the action a row asks for must clear the row.

    A completed task with a satisfied request has nothing outstanding — no work
    to finish, no ask to close, nothing to cancel. Reporting it on run 2, 3 and
    4 for ever is the row that teaches the owner to scroll past the one that
    mattered. It stays ON the job; what it stops doing is asking."""
    first = a_plan({"newSatcClient": "no", "educationExpenses": "yes"})
    tuition = next(t for t in first.tasks
                   if t.template_id == "personal-1040-education-1098t")
    assert tuition.request_id

    dropped = {"newSatcClient": "no", "educationExpenses": "no"}
    second = a_plan(dropped, existing_tasks=first.tasks,
                    open_request_ids={tuition.request_id})
    assert [o.template_id for o in second.out_of_scope] == \
           ["personal-1040-education-1098t"], "while the ask is open, it is reported"

    # The owner does exactly what the row asks: the document arrives, the
    # request closes, the task completes.
    tuition.status = "done"
    third = a_plan(dropped, existing_tasks=second.tasks, open_request_ids=set())
    fourth = a_plan(dropped, existing_tasks=third.tasks, open_request_ids=set())

    assert third.out_of_scope == (), "a row nothing can clear is worse than no row"
    assert fourth.out_of_scope == ()
    assert any(t.template_id == "personal-1040-education-1098t" for t in third.tasks), \
        "still on the job — the finished work is not deleted, only unreported"


def test_a_cancelled_task_stops_being_reported_without_the_register():
    """The same guarantee for a caller that does not hold the document register.

    ``reconcile_received`` completes the task when the request is satisfied, so
    a settled task is a settled ask — that is a reading of a recorded fact, not
    a guess about one."""
    first = a_plan({"newSatcClient": "no", "educationExpenses": "yes"})
    tuition = next(t for t in first.tasks
                   if t.template_id == "personal-1040-education-1098t")

    dropped = {"newSatcClient": "no", "educationExpenses": "no"}
    assert a_plan(dropped, existing_tasks=first.tasks).out_of_scope

    tuition.status = "cancelled"         # the owner acted on the row
    again = a_plan(dropped, existing_tasks=first.tasks)
    assert again.out_of_scope == ()
    assert any(t.template_id == "personal-1040-education-1098t" for t in again.tasks)


def test_an_untouched_internal_task_that_leaves_scope_is_dropped_but_reported():
    """Nothing is at stake: no status, no note, and nobody was ever asked for
    anything. It goes — but it is still named, so a changed answer never
    removes work silently."""
    template = "rental-review-short-term-rental-activity"
    first = a_plan({"shortTermRentalActivity": "yes"},
                   workflow_key="personal_rental_schedule_e")
    assert any(t.template_id == template for t in first.tasks)

    second = a_plan({"shortTermRentalActivity": "no"},
                    workflow_key="personal_rental_schedule_e",
                    existing_tasks=first.tasks)

    gone = [o for o in second.out_of_scope if o.template_id == template]
    assert len(gone) == 1
    assert not gone[0].had_progress and not gone[0].retained
    assert "nobody had started it" in gone[0].why
    assert not [t for t in second.tasks if t.template_id == template]


def test_an_ask_already_sent_to_the_client_is_never_dropped():
    """A client task carries an open row in the document register. Dropping it
    would strand a request nobody can ever close (principle 13)."""
    first = a_plan({"newSatcClient": "no", "educationExpenses": "yes"})
    asked = next(t for t in first.tasks
                 if t.template_id == "personal-1040-education-1098t")
    assert asked.status == "not_started" and asked.request_id

    second = a_plan({"newSatcClient": "no", "educationExpenses": "no"},
                    existing_tasks=first.tasks)

    gone = [o for o in second.out_of_scope
            if o.template_id == "personal-1040-education-1098t"]
    assert len(gone) == 1 and gone[0].retained
    assert "already been asked" in gone[0].why
    assert any(t.template_id == "personal-1040-education-1098t"
               for t in second.tasks)


def test_a_newly_true_answer_adds_its_work_without_disturbing_the_rest():
    first = a_plan({"newSatcClient": "no"})
    before = {t.template_id for t in first.tasks}

    second = a_plan({"newSatcClient": "no", "educationExpenses": "yes"},
                    existing_tasks=first.tasks)
    after = {t.template_id for t in second.tasks}

    assert after - before == {"personal-1040-education-1098t"}
    assert second.out_of_scope == ()
    # Only the NEW ask opens a request; the standing ones already have theirs.
    assert [r.doc_type for r in second.requests] == ["1098-T"]


# ---------------------------------------------------------------------------
# Requests: what blocks comes from the duty's own cited rule
# ---------------------------------------------------------------------------

def test_what_blocks_comes_from_the_duty_that_was_computed():
    plan = a_plan({"newSatcClient": "no"})
    core = next(r for r in plan.requests if r.doc_type == "Core income documents")
    # Not on the 1040 rule's blocking list (W-2 / W-2G / 1099-R) by that name.
    assert core.blocking == "non_blocking"
    assert plan.duty.blocking_docs == ("W-2", "W-2G", "1099-R")
    assert all(r.requested_at == TODAY for r in plan.requests)
    assert all(r.tax_year == YEAR for r in plan.requests)


def test_a_partnership_engagement_uses_the_partnership_rules_blocking_list():
    plan = a_plan({}, workflow_key="business_partnership_tax")
    assert plan.duty.rule_key == "form_1065"
    assert plan.duty.blocking_docs == ()


# ---------------------------------------------------------------------------
# The quote seam
# ---------------------------------------------------------------------------

def test_a_quote_that_cannot_be_produced_is_named_never_silently_zero(monkeypatch):
    import satc.billing.quote as quote_module

    def refuse(*args, **kwargs):
        raise ConfigError("the rate plan catalogue is broken")

    monkeypatch.setattr(quote_module, "quote_for", refuse)
    plan = a_plan(INVESTMENTS)
    assert plan.quote is None
    assert "No quote" in plan.quote_unavailable
    assert "fee_terms" not in plan.letter_facts
    assert "scope_of_services" not in plan.letter_facts
    assert plan.tasks, "a broken price must not stop the interview producing work"


def test_the_quote_is_always_an_estimate():
    plan = a_plan(INVESTMENTS, engagements=agreed_plan())
    assert plan.quote.is_estimate is True
    assert isinstance(plan.quote.total, Decimal)


# ---------------------------------------------------------------------------
# The persisting seam
# ---------------------------------------------------------------------------

def test_create_engagement_from_intake_persists_once_and_is_re_runnable(tmp_path):
    from satc.intake.service import create_engagement_from_intake, create_person_client
    from satc.persistence import SATCStore

    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id=CLIENT)

    first = create_engagement_from_intake(
        store, client_id=cid, workflow_key="personal_1040_core", tax_year=YEAR,
        answers=INVESTMENTS, today=TODAY)
    opened = len(store.load_mart().requested_items)
    assert opened == len(first.requests) > 0

    again = create_engagement_from_intake(
        store, client_id=cid, workflow_key="personal_1040_core", tax_year=YEAR,
        answers=INVESTMENTS, today=TODAY)

    assert again.job.job_id == first.job.job_id
    assert len(store.load_jobs()) == 1, "re-running must not mint a second job"
    assert len(store.load_mart().requested_items) == opened, \
        "re-running must not ask the client for the same document twice"

    stored = store.load_jobs()[0]
    assert stored.obligation_key == first.duty.obligation_key
    assert stored.due_date == date(2026, 4, 15)


def test_a_state_engagement_does_not_overwrite_the_federal_one(tmp_path):
    """Two jurisdictions are two duties, two deadlines and two jobs.

    The job id derives from what the job IS, and which jurisdiction's return it
    prepares is part of that. Without it both engagements derived the same id,
    the state one inherited the federal one's tasks, and saving it overwrote the
    federal row — one client, one workflow, one year, one job, two duties."""
    from satc.intake.service import create_engagement_from_intake, create_person_client
    from satc.persistence import SATCStore

    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id=CLIENT)

    federal = create_engagement_from_intake(
        store, client_id=cid, workflow_key="personal_1040_core", tax_year=YEAR,
        answers=INVESTMENTS, today=TODAY)
    state = create_engagement_from_intake(
        store, client_id=cid, workflow_key="personal_1040_core", tax_year=YEAR,
        answers=INVESTMENTS, today=TODAY, jurisdiction="MA")

    assert state.job.job_id != federal.job.job_id
    assert state.duty.rule_key == "ma_form_1" and federal.duty.rule_key == "form_1040"
    assert len(store.load_jobs()) == 2, "the state return must not eat the federal one"
    assert {j.obligation_key for j in store.load_jobs()} == \
           {federal.duty.obligation_key, state.duty.obligation_key}

    # And each is still idempotent on its own terms (principle 8).
    again = create_engagement_from_intake(
        store, client_id=cid, workflow_key="personal_1040_core", tax_year=YEAR,
        answers=INVESTMENTS, today=TODAY, jurisdiction="MA")
    assert again.job.job_id == state.job.job_id
    assert len(store.load_jobs()) == 2


# ---------------------------------------------------------------------------
# (3b) The letter facts reach the letter
# ---------------------------------------------------------------------------

def _priced_practice(tmp_path, workflow_key="personal_schedule_c"):
    """A store holding one client, one agreed rate plan, and one engagement."""
    from satc.intake.service import create_engagement_from_intake, create_person_client
    from satc.persistence import SATCStore

    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id=CLIENT)
    mart = store.load_mart()
    mart.engagements.extend(agreed_plan(client_id=cid))
    store.save_mart(mart)
    create_engagement_from_intake(
        store, client_id=cid, workflow_key=workflow_key, tax_year=YEAR,
        answers={"newSatcClient": "no"}, today=TODAY)
    return store, cid, store.load_jobs()[0]


def test_the_engagement_letter_renders_from_the_engagements_own_facts(tmp_path):
    """The seam the comms path is missing, exercised end to end.

    ``build_context`` says who the client is; the plan says what was agreed.
    Layered in that order the letter arrives finished, with the scope and the
    fee this engagement actually implies rather than standing wording."""
    from satc.comms import build_context, library, render
    from satc.intake.service import letter_facts_for_job

    store, cid, job = _priced_practice(tmp_path)
    public = next(p for p in store.load_mart().public_clients if p.client_id == cid)

    lib = library()
    values = build_context(client_id=cid, client_name=store.names()[cid],
                           public_client=public, engagement=job, tax_year=YEAR,
                           firm_values=lib.firm_values())
    assert "scope_of_services" not in values, "state alone cannot say what was agreed"
    values.update(letter_facts_for_job(store, job, today=TODAY))

    draft = render(lib.template("engagement_letter"), values, library=lib)
    assert "scope_of_services" in draft.filled and "fee_terms" in draft.filled
    assert "Self-employment income and expenses" in draft.body, \
        "the scope in the letter is the scope these answers priced"
    assert "not a bill" in draft.body, "a quote in a letter must read as a quote"
    assert draft.unfilled == [], "nothing in this letter is left for the owner to invent"
    assert not re.search(r"\b\d{3}-?\d{2}-?\d{4}\b", draft.body)


def test_a_quoted_total_cannot_be_read_as_a_bill(tmp_path):
    """``fee_amount_text`` is filled from an ISSUED INVOICE TOTAL by
    ``build_context``. A quote landing in the same slot is an estimate standing
    exactly where a bill stood, so the marker travels with the value rather than
    with whoever merged the dictionaries."""
    from satc.intake.service import letter_facts_for_job

    store, _cid, job = _priced_practice(tmp_path)
    facts = letter_facts_for_job(store, job, today=TODAY)
    assert facts["fee_amount_text"].startswith("$")
    assert "estimate" in facts["fee_amount_text"]
    assert "not a bill" in facts["fee_amount_text"]
