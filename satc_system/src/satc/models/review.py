"""Shared review/answer schema (reused across every checklist in the system).

Per-item dropdown + note: ``Done / Exception / N/A / Note``.
  * Exception drives the open-items / missing-docs rollup.
  * N/A is excluded from completion %.
  * Note surfaces in a separate review view.

This is the same convention used by the CRR reference architecture and is applied
uniformly to diligence checklists (esp. §8867 EITC), documents-received
checklists, and per-section workpaper sign-offs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal

ReviewStatus = Literal["Done", "Exception", "N/A", "Note"]

# The canonical dropdown order shown in the workbook data-validation list.
REVIEW_CHOICES: Final[tuple[str, ...]] = ("", "Done", "Exception", "N/A", "Note")

# Statuses that count toward "ready to file" completion.
_COMPLETING: Final = frozenset({"Done"})
_EXCLUDED: Final = frozenset({"N/A"})


@dataclass(slots=True)
class ReviewItem:
    """One checklist line: a question/assertion the preparer signs off on."""

    item_id: str
    section: str
    label: str
    status: ReviewStatus | str = ""       # "" = not yet reviewed
    note: str = ""
    # When True, an Exception here blocks "ready to file" (e.g. §8867 items).
    gating: bool = False


def completion_pct(items: list[ReviewItem]) -> float:
    """Percent complete, excluding N/A items from the denominator."""
    denominator = [it for it in items if it.status not in _EXCLUDED]
    if not denominator:
        return 100.0
    done = [it for it in denominator if it.status in _COMPLETING]
    return round(100.0 * len(done) / len(denominator), 1)


def open_exceptions(items: list[ReviewItem]) -> list[ReviewItem]:
    """Items flagged as Exception — these roll up to the open-items tracker."""
    return [it for it in items if it.status == "Exception"]


@dataclass(slots=True)
class Checklist:
    """A named group of review items (e.g. a §8867 due-diligence checklist)."""

    checklist_id: str
    title: str
    items: list[ReviewItem] = field(default_factory=list)

    def completion_pct(self) -> float:
        return completion_pct(self.items)

    def open_exceptions(self) -> list[ReviewItem]:
        return open_exceptions(self.items)
