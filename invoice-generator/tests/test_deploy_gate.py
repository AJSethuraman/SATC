"""The deploy gate is configuration, and configuration rots silently.

Invoicer takes real client card payments. Render's own auto-deploy watches
main and fires on the push, in parallel with CI and without waiting for it --
so before the gate existed, a merge that broke the suite reached production
before anyone knew.

Nothing about that gate is exercised by running the app, which is exactly why
it needs a test: someone flips ``autoDeploy`` back to ``true`` to unstick a
deploy at midnight, and eighteen months later nobody remembers the gate was
ever there. These assertions are the memory.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[2]
RENDER = REPO / "render.yaml"
WORKFLOW = REPO / ".github" / "workflows" / "deploy-invoicer.yml"
TESTS_WORKFLOW = REPO / ".github" / "workflows" / "test.yml"


def _load(path: Path) -> dict:
    assert path.exists(), f"{path.relative_to(REPO)} is missing"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(doc: dict) -> dict:
    # PyYAML reads a bare `on:` key as the boolean True, because YAML 1.1 says
    # so and GitHub Actions does not care. Accept either.
    return doc.get("on", doc.get(True)) or {}


def test_render_does_not_deploy_on_its_own() -> None:
    web = next(
        s for s in _load(RENDER)["services"] if s.get("name") == "invoicer"
    )
    assert web.get("autoDeploy") is False, (
        "render.yaml has autoDeploy on for the invoicer service. That hands the "
        "deploy decision back to Render, which does not wait for CI, on an app "
        "that takes client card payments."
    )


def test_a_gated_deploy_workflow_exists() -> None:
    doc = _load(WORKFLOW)
    run = _triggers(doc).get("workflow_run")
    assert run, "deploy-invoicer.yml no longer waits on another workflow"

    assert "Tests" in (run.get("workflows") or []), (
        "the deploy no longer keys off the Tests workflow"
    )
    assert run.get("branches") == ["main"], (
        "the deploy should only follow Tests on main"
    )

    guard = doc["jobs"]["deploy"].get("if", "")
    assert "workflow_run.conclusion == 'success'" in guard, (
        "the deploy job no longer requires Tests to have SUCCEEDED. `completed` "
        "is not `success` -- a failed run is also a completed one."
    )


def test_the_workflow_it_waits_for_is_the_one_that_runs_the_tests() -> None:
    """A gate pointed at a workflow that no longer exists is not a gate."""
    tests = _load(TESTS_WORKFLOW)
    assert tests.get("name") == "Tests", (
        "test.yml was renamed; deploy-invoicer.yml still waits on 'Tests' and "
        "will now wait forever, which reads exactly like a deploy that never "
        "happened for no reason."
    )

    projects = [
        job["project"]
        for job in tests["jobs"]["pytest"]["strategy"]["matrix"]["include"]
    ]
    assert "invoice-generator" in projects, (
        "the Tests workflow no longer runs invoice-generator's suite, so gating "
        "the deploy on it proves nothing about the app being deployed."
    )


def test_a_missing_deploy_hook_fails_loudly() -> None:
    """A deploy step that quietly does nothing and reports success is the bug
    class this repo's software tenets are about."""
    body = WORKFLOW.read_text(encoding="utf-8")
    step = body.split("Ask Render to deploy", 1)[1]
    assert re.search(r'if \[ -z "\$HOOK" \]', step), (
        "nothing checks that RENDER_DEPLOY_HOOK_URL is actually set"
    )
    guard = step.split("exit 1", 1)[0]
    assert "::error::" in guard and "exit 1" in step, (
        "a missing deploy hook has to fail the run. Warning and carrying on "
        "means green checks and an app that was never deployed."
    )


def test_the_manual_override_has_to_be_meant_and_explained() -> None:
    doc = _load(WORKFLOW)
    inputs = _triggers(doc)["workflow_dispatch"]["inputs"]
    assert inputs["confirm"]["required"] is True
    assert inputs["reason"]["required"] is True, (
        "an override without a recorded reason is just a second, quieter way to "
        "deploy past a red suite"
    )

    body = WORKFLOW.read_text(encoding="utf-8")
    assert 'if [ "$CONFIRM" != "DEPLOY" ]' in body, (
        "the confirmation input is collected but never checked"
    )
    assert "GITHUB_STEP_SUMMARY" in body, (
        "the override reason is collected but never written anywhere anyone "
        "will read it"
    )


def test_success_means_the_app_answered_not_that_render_took_the_call() -> None:
    """`200 from the deploy hook` means "request accepted", not "app serving"."""
    body = WORKFLOW.read_text(encoding="utf-8")
    assert "/api/health" in body, (
        "nothing verifies the deployed app actually came back up"
    )
