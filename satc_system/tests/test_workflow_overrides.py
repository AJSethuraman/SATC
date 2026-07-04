"""Tests for the in-app questionnaire override engine
(:mod:`satc.intake.workflows` overrides + :class:`SATCStore` persistence).

The practice can customize a built-in workflow without touching the YAML configs:
rename it, relabel/disable questions, edit/disable tasks, and bolt on extra
"if yes, request this" questions. ``apply_overrides`` mutates a loaded workflow in
place; ``set_override_provider`` wires a lookup (typically the store) so
``load_workflow`` layers the practice's edits on automatically.

The override provider is GLOBAL module state. Every test that touches it goes
through the ``reset_override_provider`` fixture so a failure cannot leak the
provider into the rest of the suite.
"""

from __future__ import annotations

import pytest

from satc.intake import workflows
from satc.intake.workflows import (
    apply_overrides,
    load_workflow,
    set_override_provider,
)
from satc.persistence import SATCStore

# A stable question/task id pair that lives in the base personal_1040_core config.
_QID = "newSatcClient"
_TID = "personal-1040-upload-w2-1099-core"


@pytest.fixture
def reset_override_provider():
    """Ensure the global override provider is cleared after the test, win or lose."""
    try:
        yield
    finally:
        set_override_provider(None)


# ---------------------------------------------------------------------------
# apply_overrides — directly on a loaded base workflow (no provider set)
# ---------------------------------------------------------------------------

def test_override_renames_workflow():
    wf = load_workflow("personal_1040_core")
    assert wf.name != "X"
    apply_overrides(wf, {"name": "X"})
    assert wf.name == "X"


def test_override_relabels_question():
    wf = load_workflow("personal_1040_core")
    apply_overrides(wf, {"questions": {_QID: {"label": "new"}}})
    relabeled = {q.id: q.label for q in wf.questions}
    assert relabeled[_QID] == "new"


def test_override_disables_question_removes_it():
    wf = load_workflow("personal_1040_core")
    assert any(q.id == _QID for q in wf.questions)
    apply_overrides(wf, {"questions": {_QID: {"disabled": True}}})
    assert all(q.id != _QID for q in wf.questions)


def test_override_edits_task_request_text():
    wf = load_workflow("personal_1040_core")
    apply_overrides(wf, {"tasks": {_TID: {"client_request_text": "new text"}}})
    task = next(t for t in wf.tasks if t.template_id == _TID)
    assert task.client_request_text == "new text"


def test_override_disables_task_removes_it():
    wf = load_workflow("personal_1040_core")
    assert any(t.template_id == _TID for t in wf.tasks)
    apply_overrides(wf, {"tasks": {_TID: {"disabled": True}}})
    assert all(t.template_id != _TID for t in wf.tasks)


def test_override_added_question_creates_question_and_conditional_task():
    wf = load_workflow("personal_1040_core")
    apply_overrides(wf, {"added_questions": [{
        "id": "gamblingActivity",
        "label": "Gambling or lottery winnings?",
        "request": {"title": "Form W-2G", "client_request_text": "Upload W-2G."},
    }]})

    added_q = next((q for q in wf.questions if q.id == "gamblingActivity"), None)
    assert added_q is not None
    assert added_q.label == "Gambling or lottery winnings?"

    added_t = next((t for t in wf.tasks if t.template_id == "custom-gamblingActivity"), None)
    assert added_t is not None
    assert added_t.condition == {"question_id": "gamblingActivity", "equals": "yes"}
    assert added_t.client_request_text == "Upload W-2G."


# ---------------------------------------------------------------------------
# provider wiring — load_workflow applies overrides automatically
# ---------------------------------------------------------------------------

def test_provider_overrides_only_matching_workflow(reset_override_provider):
    set_override_provider(
        lambda key: {"name": "Renamed by practice"} if key == "personal_1040_core" else None)

    overridden = load_workflow("personal_1040_core")
    assert overridden.name == "Renamed by practice"

    # A different workflow key is untouched by the provider.
    other = load_workflow("personal_schedule_c")
    assert other.name != "Renamed by practice"


def test_provider_reset_restores_base_workflow(reset_override_provider):
    set_override_provider(lambda key: {"name": "Temporary"})
    assert load_workflow("personal_1040_core").name == "Temporary"

    set_override_provider(None)
    assert load_workflow("personal_1040_core").name == "Personal 1040 core"


# ---------------------------------------------------------------------------
# store round-trip — save / load / list overrides
# ---------------------------------------------------------------------------

def test_store_workflow_override_round_trip(tmp_path):
    store = SATCStore(tmp_path)
    store.save_workflow_override("personal_1040_core", {"name": "Z"})

    assert store.load_workflow_override("personal_1040_core") == {"name": "Z"}
    assert "personal_1040_core" in store.workflow_override_keys()
    # Unknown keys return None rather than raising.
    assert store.load_workflow_override("does_not_exist") is None


# ---------------------------------------------------------------------------
# end-to-end — the store IS the provider
# ---------------------------------------------------------------------------

def test_store_as_provider_applies_and_clears(tmp_path, reset_override_provider):
    store = SATCStore(tmp_path)
    store.save_workflow_override("personal_1040_core", {"name": "From store"})

    set_override_provider(store.load_workflow_override)
    assert load_workflow("personal_1040_core").name == "From store"

    # Saving an empty override clears the customization (empty dict -> no edits).
    store.save_workflow_override("personal_1040_core", {})
    assert load_workflow("personal_1040_core").name == "Personal 1040 core"
