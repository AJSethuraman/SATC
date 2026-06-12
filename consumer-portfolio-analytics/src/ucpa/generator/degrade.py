"""Degrade a Tier 2 tape to Tier 1 or Tier 0 field availability.

Simulates lower-maturity clients so the tier detector and the engine's
data-gap reporting can be exercised end to end:

* **Tier 1**: drop all Tier 2 columns; the monthly panel and standard
  monitoring fields remain.
* **Tier 0**: additionally drop the Tier 1 columns and collapse the panel
  to a snapshot -- each account's last observed row, which is how a
  minimal servicing-system extract typically looks (open accounts as of
  the extract date, charged-off accounts at their write-off month).
"""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    TIER1_ONLY_FIELDS,
    TIER2_ONLY_FIELDS,
)


def degrade_to_tier(tape: pd.DataFrame, tier: int) -> pd.DataFrame:
    """Strip ``tape`` down to the field availability of ``tier``.

    Args:
        tape: A tape at Tier 2 (or higher availability than the target).
        tier: Target tier: 2 returns a copy unchanged, 1 drops Tier 2
            fields, 0 also drops Tier 1 fields and collapses to a snapshot.

    Returns:
        A new DataFrame; the input is never mutated.
    """
    if tier not in (0, 1, 2):
        raise ValueError(f"tier must be 0, 1 or 2, got {tier!r}")
    if tier == 2:
        return tape.copy()

    out = tape.drop(columns=[c for c in TIER2_ONLY_FIELDS if c in tape.columns])
    if tier == 1:
        return out

    out = out.drop(columns=[c for c in TIER1_ONLY_FIELDS if c in out.columns])
    last_idx = (
        out.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort")
        .groupby(F_ACCOUNT_ID, sort=True)
        .tail(1)
        .index
    )
    return out.loc[sorted(last_idx)].reset_index(drop=True)
