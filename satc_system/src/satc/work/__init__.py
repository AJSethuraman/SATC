"""WORK — where a job stands, and what can actually be picked up.

The stage is DERIVED, never set. See :mod:`satc.work.stage` for why.
"""

from satc.work.stage import (
    REVIEW_CATEGORIES,
    StageView,
    derive_stage,
    stage_matches_record,
)

__all__ = [
    "REVIEW_CATEGORIES",
    "StageView",
    "derive_stage",
    "stage_matches_record",
]
