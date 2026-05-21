"""Action-plan output helpers for masked dry-run artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from dea.models import ActionPlan


def write_action_plan_json(action_plan: ActionPlan, path: str | Path) -> None:
    """Write a masked JSON representation of an action plan.

    Raw entry values are intentionally excluded.
    """
    output = Path(path)
    payload = {
        "client_id": action_plan.client_id,
        "tax_year": action_plan.tax_year,
        "steps": [
            {
                "action": step.action,
                "screen": step.screen,
                "field": step.field,
                "masked_value": step.masked_value,
                "source_sheet": step.source_sheet,
                "source_cell": step.source_cell,
                "support_status": step.support_status,
                "field_locator": step.field_locator,
            }
            for step in action_plan.steps
        ],
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_action_plans_json(action_plans: list[ActionPlan], path: str | Path) -> None:
    """Write one masked JSON artifact containing multiple client action plans."""
    output = Path(path)
    payload = {
        "plans": [
            {
                "client_id": plan.client_id,
                "tax_year": plan.tax_year,
                "steps": [
                    {
                        "action": step.action,
                        "screen": step.screen,
                        "field": step.field,
                        "masked_value": step.masked_value,
                        "source_sheet": step.source_sheet,
                        "source_cell": step.source_cell,
                        "support_status": step.support_status,
                        "field_locator": step.field_locator,
                    }
                    for step in plan.steps
                ],
            }
            for plan in action_plans
        ]
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
