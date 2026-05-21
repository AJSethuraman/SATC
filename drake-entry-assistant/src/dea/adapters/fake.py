"""Fake adapter used for local development and testing.

This adapter does not automate Drake. It records requested actions and can be
used to test orchestration boundaries safely.
"""

from __future__ import annotations

from typing import Any, Sequence


class FakeDrakeAdapter:
    """No-op adapter that records actions instead of automating a UI."""

    name = "fake-drake"

    def __init__(self) -> None:
        self.connected = False
        self.actions_executed: list[dict[str, Any]] = []

    def connect(self) -> None:
        """Mark adapter as connected."""
        self.connected = True

    def execute_actions(self, actions: Sequence[dict[str, Any]]) -> None:
        """Record actions for inspection."""
        self.actions_executed.extend(actions)

    def close(self) -> None:
        """Mark adapter as disconnected."""
        self.connected = False
