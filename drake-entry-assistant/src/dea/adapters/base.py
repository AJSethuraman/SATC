"""Base adapter interfaces for action-plan execution backends."""

from __future__ import annotations

from typing import Protocol

from dea.models import ActionPlan, ExecutionResult, ScreenMap


class EntryAdapter(Protocol):
    """Protocol for adapter execution backends."""

    name: str

    def focus_app(self) -> None:
        """Bring target app into focus (or simulate that behavior)."""

    def open_screen(self, screen_code: str) -> None:
        """Open a target screen by screen code."""

    def verify_screen(self, screen: ScreenMap) -> None:
        """Verify expected screen markers are present."""

    def enter_field(self, field_locator: str, value: str) -> None:
        """Enter a field value using a provided locator description."""

    def handle_unexpected_state(self) -> None:
        """Handle and raise on unexpected application states."""

    def execute_action_plan(
        self,
        action_plan: ActionPlan,
        screen_maps: dict[str, ScreenMap],
    ) -> ExecutionResult:
        """Execute an action plan and return structured execution records."""
