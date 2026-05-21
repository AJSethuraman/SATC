"""Fake adapter used for local development and deterministic testing.

This adapter does not automate Drake or any real UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dea.logging_utils import action_step_to_log_record
from dea.models import ActionPlan, ActionStep, ExecutionResult, ScreenMap


class FakeAdapterError(RuntimeError):
    """Raised when simulated adapter operations fail."""


@dataclass(slots=True)
class FakeDrakeAdapter:
    """Simulation-only adapter with explicit stop conditions."""

    app_available: bool = True
    missing_screens: set[str] = field(default_factory=set)
    missing_fields: set[str] = field(default_factory=set)
    unexpected_popup: bool = False

    name: str = "fake-drake"

    def focus_app(self) -> None:
        if not self.app_available:
            raise FakeAdapterError("Application is not available")

    def open_screen(self, screen_code: str) -> None:
        if not self.app_available:
            raise FakeAdapterError("Application is not available")
        if screen_code in self.missing_screens:
            raise FakeAdapterError(f"Screen not found: {screen_code}")

    def verify_screen(self, screen: ScreenMap) -> None:
        if screen.screen_code in self.missing_screens:
            raise FakeAdapterError(f"Screen markers missing for {screen.screen_code}")
        if self.unexpected_popup:
            self.handle_unexpected_state()

    def enter_field(self, field_locator: str, value: str) -> None:
        del value
        if field_locator in self.missing_fields:
            raise FakeAdapterError(f"Field not available: {field_locator}")

    def handle_unexpected_state(self) -> None:
        raise FakeAdapterError("Unexpected popup or state detected")

    def _lookup_screen_map(self, screen_code: str, screen_maps: dict[str, ScreenMap]) -> ScreenMap | None:
        for screen_map in screen_maps.values():
            if screen_map.screen_code == screen_code:
                return screen_map
        return None

    def _failure_result(
        self,
        step: ActionStep,
        *,
        status: str,
        error_message: str,
        plan: ActionPlan,
        mode: str,
        records: list,
    ) -> ExecutionResult:
        records.append(
            action_step_to_log_record(
                step,
                client_id=plan.client_id,
                tax_year=plan.tax_year,
                mode=mode,
                status=status,
                error_message=error_message,
            )
        )
        return ExecutionResult(success=False, records=records, error_message=error_message)

    def execute_action_plan(
        self,
        action_plan: ActionPlan,
        screen_maps: dict[str, ScreenMap],
    ) -> ExecutionResult:
        records = []
        mode = "fake_execute"

        if not self.app_available:
            first = action_plan.steps[0] if action_plan.steps else ActionStep(
                action="OPEN_SCREEN",
                screen="",
                field="",
                value="",
                masked_value="",
                source_sheet=None,
                source_cell=None,
                support_status="SUPPORTED",
            )
            return self._failure_result(
                first,
                status="FAILED_SCREEN_CHECK",
                error_message="Application is not available",
                plan=action_plan,
                mode=mode,
                records=records,
            )

        try:
            self.focus_app()
        except FakeAdapterError as exc:
            first = action_plan.steps[0] if action_plan.steps else ActionStep(
                action="OPEN_SCREEN",
                screen="",
                field="",
                value="",
                masked_value="",
                source_sheet=None,
                source_cell=None,
                support_status="SUPPORTED",
            )
            return self._failure_result(
                first,
                status="FAILED_SCREEN_CHECK",
                error_message=str(exc),
                plan=action_plan,
                mode=mode,
                records=records,
            )

        current_screen_map: ScreenMap | None = None
        for step in action_plan.steps:
            if self.unexpected_popup:
                return self._failure_result(
                    step,
                    status="FAILED_SCREEN_CHECK",
                    error_message="Unexpected popup or state detected",
                    plan=action_plan,
                    mode=mode,
                    records=records,
                )

            if step.action == "OPEN_SCREEN":
                try:
                    self.open_screen(step.screen)
                    current_screen_map = self._lookup_screen_map(step.screen, screen_maps)
                    if current_screen_map is None:
                        raise FakeAdapterError(f"No screen map found for code {step.screen}")
                    self.verify_screen(current_screen_map)
                except FakeAdapterError as exc:
                    return self._failure_result(
                        step,
                        status="FAILED_SCREEN_CHECK",
                        error_message=str(exc),
                        plan=action_plan,
                        mode=mode,
                        records=records,
                    )
                records.append(
                    action_step_to_log_record(
                        step,
                        client_id=action_plan.client_id,
                        tax_year=action_plan.tax_year,
                        mode=mode,
                        status="ENTERED",
                    )
                )
                continue

            if step.action == "ENTER_FIELD":
                if current_screen_map is None:
                    return self._failure_result(
                        step,
                        status="FAILED_SCREEN_CHECK",
                        error_message="No active screen before field entry",
                        plan=action_plan,
                        mode=mode,
                        records=records,
                    )
                locator = step.field_locator or step.field
                try:
                    self.enter_field(locator, step.value)
                    # Also allow failure simulation by logical field path key.
                    self.enter_field(step.field, step.value)
                except FakeAdapterError as exc:
                    return self._failure_result(
                        step,
                        status="FAILED_FIELD_ENTRY",
                        error_message=str(exc),
                        plan=action_plan,
                        mode=mode,
                        records=records,
                    )
                records.append(
                    action_step_to_log_record(
                        step,
                        client_id=action_plan.client_id,
                        tax_year=action_plan.tax_year,
                        mode=mode,
                        status="ENTERED",
                    )
                )
                continue

            records.append(
                action_step_to_log_record(
                    step,
                    client_id=action_plan.client_id,
                    tax_year=action_plan.tax_year,
                    mode=mode,
                )
            )

        return ExecutionResult(success=True, records=records, error_message=None)
