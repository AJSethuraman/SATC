"""Tests for the client-intake workflow engine (:mod:`satc.intake.workflows`).

Ported from the standalone checklist app's ``test/workflows.test.js``: the rules
engine (conditional inclusion, date math), config loading, relationship-aware
K-1 reminders, risk flags, and regeneration that preserves task progress.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from satc.intake.workflows import (
    build_engagement,
    calculate_suggested_date,
    evaluate_condition,
    list_workflows,
    load_workflow,
    regenerate_engagement,
    workflows_for_client_type,
)


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------

def test_evaluate_condition_none_is_always_true():
    assert evaluate_condition(None, {}) is True
    assert evaluate_condition({}, {"anything": "value"}) is True


def test_evaluate_condition_equals_match_and_mismatch():
    cond = {"question_id": "newSatcClient", "equals": "yes"}
    assert evaluate_condition(cond, {"newSatcClient": "yes"}) is True
    assert evaluate_condition(cond, {"newSatcClient": "no"}) is False
    # Missing answer (defaults to None) is not equal to "yes".
    assert evaluate_condition(cond, {}) is False


def test_evaluate_condition_not_equals():
    cond = {"question_id": "filingStatus", "not_equals": "single"}
    assert evaluate_condition(cond, {"filingStatus": "married"}) is True
    assert evaluate_condition(cond, {"filingStatus": "single"}) is False


def test_evaluate_condition_any():
    cond = {"any": [
        {"question_id": "a", "equals": "yes"},
        {"question_id": "b", "equals": "yes"},
    ]}
    assert evaluate_condition(cond, {"a": "no", "b": "yes"}) is True
    assert evaluate_condition(cond, {"a": "yes", "b": "no"}) is True
    assert evaluate_condition(cond, {"a": "no", "b": "no"}) is False


def test_evaluate_condition_all():
    cond = {"all": [
        {"question_id": "a", "equals": "yes"},
        {"question_id": "b", "equals": "yes"},
    ]}
    assert evaluate_condition(cond, {"a": "yes", "b": "yes"}) is True
    assert evaluate_condition(cond, {"a": "yes", "b": "no"}) is False
    assert evaluate_condition(cond, {"a": "no", "b": "no"}) is False


def test_evaluate_condition_includes():
    # Membership in a list answer.
    cond = {"question_id": "states", "includes": "CA"}
    assert evaluate_condition(cond, {"states": ["CA", "NY"]}) is True
    assert evaluate_condition(cond, {"states": ["NY", "TX"]}) is False
    # Substring of a string answer.
    cond_str = {"question_id": "note", "includes": "crypto"}
    assert evaluate_condition(cond_str, {"note": "has crypto activity"}) is True
    assert evaluate_condition(cond_str, {"note": "nothing notable"}) is False


def test_evaluate_condition_greater_than():
    cond = {"question_id": "income", "greater_than": 100}
    assert evaluate_condition(cond, {"income": 150}) is True
    assert evaluate_condition(cond, {"income": "150"}) is True
    assert evaluate_condition(cond, {"income": 50}) is False
    assert evaluate_condition(cond, {"income": 100}) is False  # strict


def test_evaluate_condition_less_than():
    cond = {"question_id": "income", "less_than": 100}
    assert evaluate_condition(cond, {"income": 50}) is True
    assert evaluate_condition(cond, {"income": "50"}) is True
    assert evaluate_condition(cond, {"income": 150}) is False
    assert evaluate_condition(cond, {"income": 100}) is False  # strict


# ---------------------------------------------------------------------------
# calculate_suggested_date
# ---------------------------------------------------------------------------

def test_calculate_suggested_date_subtracts_days_from_iso_string():
    assert calculate_suggested_date("2026-04-15", 10) == date(2026, 4, 5)


def test_calculate_suggested_date_accepts_a_date_object():
    assert calculate_suggested_date(date(2026, 4, 15), 10) == date(2026, 4, 5)


def test_calculate_suggested_date_zero_offset_is_the_due_date():
    assert calculate_suggested_date("2026-04-15", 0) == date(2026, 4, 15)


def test_calculate_suggested_date_empty_string_raises():
    with pytest.raises(ValueError):
        calculate_suggested_date("", 10)
    with pytest.raises(ValueError):
        calculate_suggested_date("   ", 10)


# ---------------------------------------------------------------------------
# Loading workflow configs
# ---------------------------------------------------------------------------

def test_load_workflow_personal_1040_core():
    wf = load_workflow("personal_1040_core")
    assert wf.key == "personal_1040_core"
    assert wf.client_type == "person"
    assert wf.questions, "workflow should define intake questions"
    assert wf.tasks, "workflow should define tasks"
    # The reference config carries the well-known prior-year-return task.
    assert any(t.template_id == "personal-1040-request-prior-year-returns" for t in wf.tasks)


def test_list_workflows_returns_several():
    workflows = list_workflows()
    assert len(workflows) >= 3
    keys = {w.key for w in workflows}
    assert "personal_1040_core" in keys


def test_workflows_for_client_type_person_excludes_business():
    person_workflows = workflows_for_client_type("person")
    assert person_workflows, "expected person workflows"
    keys = [w.key for w in person_workflows]
    assert keys == ["personal_1040_core", "personal_schedule_c", "personal_rental_schedule_e"]
    # No business-typed workflow leaks into the person list.
    assert all(w.client_type != "business" for w in person_workflows)


# ---------------------------------------------------------------------------
# build_engagement — conditional gating + risk flags
# ---------------------------------------------------------------------------

def _template_ids(engagement):
    return {t.template_id for t in engagement.tasks}


def test_conditional_task_present_when_answer_matches():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-1", due_date="2026-04-15",
                           answers={"newSatcClient": "yes"})
    assert "personal-1040-request-prior-year-returns" in _template_ids(eng)


def test_conditional_task_absent_when_answer_does_not_match():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-1", due_date="2026-04-15",
                           answers={"newSatcClient": "no"})
    assert "personal-1040-request-prior-year-returns" not in _template_ids(eng)


def test_risk_flag_raised_for_marketplace_insurance():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-1", due_date="2026-04-15",
                           answers={"marketplaceInsurance": "yes"})
    assert "Marketplace Form 1095-A required" in eng.risk_flags


def test_no_risk_flag_when_question_not_affirmative():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-1", due_date="2026-04-15",
                           answers={"marketplaceInsurance": "no"})
    assert "Marketplace Form 1095-A required" not in eng.risk_flags


# ---------------------------------------------------------------------------
# build_engagement — relationship-aware K-1 reminders
# ---------------------------------------------------------------------------

def test_relationship_task_for_linked_scorp_is_internal_and_relationship_generated():
    wf = load_workflow("personal_1040_core")
    scorp = SimpleNamespace(client_id="SATC-BIZ", client_type="business",
                            display_name="Acme S Corp", tax_treatment="sCorp")
    eng = build_engagement(wf, client_id="SATC-PERSON", due_date="2026-04-15",
                           answers={}, linked_clients=[scorp])

    matches = [t for t in eng.tasks if t.title == "Track expected K-1 from Acme S Corp"]
    assert len(matches) == 1, "exactly one K-1 tracking task expected"
    task = matches[0]
    assert task.relationship_generated is True
    assert task.audience == "internal"
    # Linking an S-corp also raises the shareholder-basis risk flag.
    assert "S-corp shareholder basis review" in eng.risk_flags


def test_no_relationship_task_without_linked_clients():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-PERSON", due_date="2026-04-15", answers={})
    assert not any(t.relationship_generated for t in eng.tasks)


# ---------------------------------------------------------------------------
# regenerate_engagement — preserves progress by template_id
# ---------------------------------------------------------------------------

def test_regenerate_preserves_completion_and_task_id():
    wf = load_workflow("personal_1040_core")
    answers = {"newSatcClient": "yes"}
    eng = build_engagement(wf, client_id="SATC-PERSON", due_date="2026-04-15", answers=answers)

    tracked = eng.tasks[0]
    tracked.completed = True
    tracked.notes = "Already uploaded."
    preserved_template = tracked.template_id
    preserved_task_id = tracked.task_id

    regenerated = regenerate_engagement(eng, wf, answers=answers)

    survivors = [t for t in regenerated.tasks if t.template_id == preserved_template]
    assert len(survivors) == 1
    survivor = survivors[0]
    assert survivor.completed is True
    assert survivor.notes == "Already uploaded."
    # The stable identity (task_id) is carried across regeneration.
    assert survivor.task_id == preserved_task_id
    # The engagement id is preserved too (it is the same engagement, re-derived).
    assert regenerated.engagement_id == eng.engagement_id


def test_regenerate_adds_newly_gated_task_uncompleted():
    wf = load_workflow("personal_1040_core")
    eng = build_engagement(wf, client_id="SATC-PERSON", due_date="2026-04-15",
                           answers={"newSatcClient": "no"})
    assert "personal-1040-request-prior-year-returns" not in _template_ids(eng)

    regenerated = regenerate_engagement(eng, wf, answers={"newSatcClient": "yes"})
    new_tasks = [t for t in regenerated.tasks
                 if t.template_id == "personal-1040-request-prior-year-returns"]
    assert len(new_tasks) == 1
    assert new_tasks[0].completed is False
    assert new_tasks[0].notes == ""
