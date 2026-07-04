"""Validate the ported workflow YAML configs and the engagement engine.

These tests exercise every workflow config on disk (the reference
``personal_1040_core`` plus the seven ported workflows) and assert they load
cleanly, satisfy the schema contract, and drive ``build_engagement`` without
raising.
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.intake.workflows import build_engagement, list_workflows

EXPECTED_WORKFLOW_COUNT = 8


@pytest.fixture(scope="module")
def workflows():
    return list_workflows()


def test_eight_workflows_total(workflows):
    assert len(workflows) == EXPECTED_WORKFLOW_COUNT


def test_every_workflow_is_well_formed(workflows):
    for wf in workflows:
        assert wf.name, f"{wf.key} is missing a name"
        assert len(wf.questions) >= 1, f"{wf.key} has no questions"
        assert len(wf.tasks) >= 1, f"{wf.key} has no tasks"
        for task in wf.tasks:
            assert task.template_id, f"{wf.key} has a task with no template_id"
            assert task.title, f"{wf.key}/{task.template_id} has no title"


def test_template_ids_unique_within_each_workflow(workflows):
    for wf in workflows:
        ids = [t.template_id for t in wf.tasks]
        assert len(ids) == len(set(ids)), f"{wf.key} has duplicate template_ids"


def test_build_engagement_with_all_yes(workflows):
    for wf in workflows:
        answers = {q.id: "yes" for q in wf.questions}
        engagement = build_engagement(
            wf,
            client_id="client-test",
            due_date=date(2026, 4, 15),
            answers=answers,
            tax_year=2025,
        )
        assert engagement.tasks, f"{wf.key} produced no tasks with all-yes answers"
        # Every conditional task should fire when every answer is "yes", so the
        # generated engagement must include at least as many tasks as templates.
        assert len(engagement.tasks) == len(wf.tasks), (
            f"{wf.key} expected {len(wf.tasks)} tasks, got {len(engagement.tasks)}"
        )
