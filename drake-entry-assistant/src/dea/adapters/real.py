"""Conservative real Drake adapter stub.

This module intentionally refuses live execution until a separately approved
implementation is completed.
"""

from __future__ import annotations

from dataclasses import dataclass

from dea.logging_utils import action_step_to_log_record
from dea.models import ActionPlan, ActionStep, ExecutionResult, ScreenMap


@dataclass(slots=True)
class RealDrakeAdapter:
    """Stub adapter that refuses unsafe or unimplemented live execution."""

    live_enabled: bool = False
    name: str = "real-drake-stub"

    def focus_app(self) -> None:
        """Placeholder for future window focus checks."""
        return None

    def open_screen(self, screen_code: str) -> None:
        """Placeholder for future screen navigation checks."""
        del screen_code
        return None

    def verify_screen(self, screen: ScreenMap) -> None:
        """Placeholder for future screen marker checks."""
        del screen
        return None

    def enter_field(self, field_locator: str, value: str) -> None:
        """Placeholder for future field entry behavior."""
        del field_locator
        del value
        return None

    def handle_unexpected_state(self) -> None:
        """Placeholder for future unexpected-state handlers."""
        return None

    def execute_action_plan(
        self,
        action_plan: ActionPlan,
        screen_maps: dict[str, ScreenMap],
    ) -> ExecutionResult:
        """Refuse execution in all current modes for safety.

        - If ``live_enabled`` is False, execution is blocked as disabled.
        - If ``live_enabled`` is True, execution is still blocked because real
          Drake automation is not implemented yet.
        """
        del screen_maps

        message = (
            "Live Drake mode is disabled. Re-run with --live-drake to acknowledge the guard."
            if not self.live_enabled
            else "Live Drake execution is not implemented yet; refusing execution for safety."
        )

        step = action_plan.steps[0] if action_plan.steps else ActionStep(
            action="OPEN_SCREEN",
            screen="",
            field="",
            value="",
            masked_value="",
            source_sheet=None,
            source_cell=None,
            support_status="SUPPORTED",
        )
        record = action_step_to_log_record(
            step,
            client_id=action_plan.client_id,
            tax_year=action_plan.tax_year,
            mode="live_execute",
            status="FAILED_SCREEN_CHECK",
            error_message=message,
        )
        return ExecutionResult(success=False, records=[record], error_message=message)
