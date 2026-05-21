"""Base adapter interfaces.

Adapters expose a common contract for executing adapter-agnostic action plans
against a target system (real or simulated).
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence


class EntryAdapter(Protocol):
    """Protocol for action-plan execution backends."""

    name: str

    def connect(self) -> None:
        """Prepare adapter resources for a run."""

    def execute_actions(self, actions: Sequence[dict[str, Any]]) -> None:
        """Execute normalized action steps."""

    def close(self) -> None:
        """Release adapter resources."""
