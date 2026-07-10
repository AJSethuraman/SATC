"""Tier detector: classify an input tape as Tier 0 / 1 / 2.

A field "counts" as present when the column exists and contains at least one
non-null value.  Tier 1 additionally requires the tape to be a longitudinal
monthly panel (at least one account observed in more than one as-of month);
a single-snapshot extract caps the client at Tier 0 regardless of columns.

The detector is product-aware: it asks the product module which fields each
tier requires, so fields that do not apply to a product (e.g. loan term for
revolving cards) never gate detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ucpa.data_model import F_ACCOUNT_ID, F_AS_OF_DATE, PANEL_REQUIREMENT
from ucpa.products.base import ProductModule


@dataclass
class TierDetectionResult:
    """Outcome of tier detection on one tape.

    Attributes:
        detected_tier: 0, 1 or 2 -- the highest tier whose requirements
            (and all lower tiers' requirements) the tape satisfies.
        is_panel: True when the tape is a monthly longitudinal panel.
        field_presence: Per-field availability over all tiered fields.
        missing_for_tier0: Tier 0 fields absent from the tape.  Non-empty
            means the tape fails the minimum data standard; detection still
            reports tier 0 but the engine will block most metrics.
        missing_for_next_tier: What the client must add to reach the next
            tier (field names, plus the panel-structure marker if needed).
            Empty when already at Tier 2.
        n_accounts / n_rows / n_months: Tape shape diagnostics.
    """

    detected_tier: int
    is_panel: bool
    field_presence: dict[str, bool]
    missing_for_tier0: list[str] = field(default_factory=list)
    missing_for_next_tier: list[str] = field(default_factory=list)
    n_accounts: int = 0
    n_rows: int = 0
    n_months: int = 0


def field_present(tape: pd.DataFrame, name: str) -> bool:
    """True when ``name`` exists as a column with at least one non-null value."""
    return name in tape.columns and bool(tape[name].notna().any())


def is_monthly_panel(tape: pd.DataFrame) -> bool:
    """True when at least one account is observed in more than one as-of month."""
    if F_ACCOUNT_ID not in tape.columns or F_AS_OF_DATE not in tape.columns:
        return False
    if tape[F_AS_OF_DATE].nunique() < 2:
        return False
    per_account = tape.groupby(F_ACCOUNT_ID, sort=False)[F_AS_OF_DATE].nunique()
    return bool((per_account > 1).any())


def detect_tier(tape: pd.DataFrame, module: ProductModule) -> TierDetectionResult:
    """Classify ``tape`` against ``module``'s tiered data model.

    Args:
        tape: Account-level tape (panel or snapshot).
        module: Product module supplying per-tier field requirements.

    Returns:
        A :class:`TierDetectionResult` with the detected tier and a
        structured list of what is missing for the next tier.
    """
    tiers = module.tier_fields()
    presence: dict[str, bool] = {}
    for tier in (0, 1, 2):
        for f in sorted(tiers[tier]):
            presence[f] = field_present(tape, f)

    panel = is_monthly_panel(tape)

    missing0 = sorted(f for f in tiers[0] if not presence[f])
    missing1_fields = sorted(f for f in tiers[1] if not presence[f])
    missing2_fields = sorted(f for f in tiers[2] if not presence[f])

    # Tier 1 = all Tier 0 + Tier 1 fields present AND longitudinal panel.
    meets_tier1 = not missing0 and not missing1_fields and panel
    meets_tier2 = meets_tier1 and not missing2_fields

    if meets_tier2:
        detected, missing_next = 2, []
    elif meets_tier1:
        detected, missing_next = 1, missing2_fields
    else:
        detected = 0
        missing_next = missing1_fields + ([] if panel else [PANEL_REQUIREMENT])

    n_accounts = int(tape[F_ACCOUNT_ID].nunique()) if F_ACCOUNT_ID in tape.columns else 0
    n_months = int(tape[F_AS_OF_DATE].nunique()) if F_AS_OF_DATE in tape.columns else 0

    return TierDetectionResult(
        detected_tier=detected,
        is_panel=panel,
        field_presence=presence,
        missing_for_tier0=missing0,
        missing_for_next_tier=missing_next,
        n_accounts=n_accounts,
        n_rows=int(len(tape)),
        n_months=n_months,
    )
