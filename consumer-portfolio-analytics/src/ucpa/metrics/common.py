"""Shared deterministic helpers for metric computations.

Every helper is a pure function of the input tape; no randomness, no I/O.
"""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    BUCKET_CO,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_CHARGE_OFF_FLAG,
    F_CREDIT_LIMIT,
    F_DELINQUENCY_BUCKET,
    F_ORIG_CREDIT_LIMIT,
    F_ORIGINATION_DATE,
)


def active_rows(tape: pd.DataFrame) -> pd.DataFrame:
    """Rows for open (not charged-off) accounts."""
    return tape[tape[F_DELINQUENCY_BUCKET] != BUCKET_CO]


def latest_snapshot(tape: pd.DataFrame) -> pd.DataFrame:
    """Active rows at the latest as-of month in the tape."""
    act = active_rows(tape)
    if act.empty:
        return act
    return act[act[F_AS_OF_DATE] == act[F_AS_OF_DATE].max()]


def charge_off_events(tape: pd.DataFrame) -> pd.DataFrame:
    """One row per charged-off account: the first month the flag is set.

    By tape convention the balance in that month is the amount written off.

    Returns:
        DataFrame with columns ``account_id``, ``co_date``, ``co_amount``,
        ``origination_date``, sorted by account_id.
    """
    flagged = tape[tape[F_CHARGE_OFF_FLAG] == 1]
    if flagged.empty:
        return pd.DataFrame(
            columns=[F_ACCOUNT_ID, "co_date", "co_amount", F_ORIGINATION_DATE]
        )
    first = (
        flagged.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort")
        .groupby(F_ACCOUNT_ID, sort=True, as_index=False)
        .first()
    )
    return first[[F_ACCOUNT_ID, F_AS_OF_DATE, F_BALANCE, F_ORIGINATION_DATE]].rename(
        columns={F_AS_OF_DATE: "co_date", F_BALANCE: "co_amount"}
    )


def monthly_outstanding(tape: pd.DataFrame) -> pd.Series:
    """Total active (non-charged-off) balance by as-of month, sorted."""
    act = active_rows(tape)
    return act.groupby(F_AS_OF_DATE, sort=True)[F_BALANCE].sum()


def account_origination_limit(tape: pd.DataFrame) -> pd.Series:
    """Per-account credit limit at origination, indexed by account_id.

    Uses ``orig_credit_limit`` when available (Tier 2), otherwise the first
    observed ``credit_limit`` (Tier 1 approximation).
    """
    sorted_tape = tape.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort")
    first = sorted_tape.groupby(F_ACCOUNT_ID, sort=True).first()
    if F_ORIG_CREDIT_LIMIT in tape.columns and tape[F_ORIG_CREDIT_LIMIT].notna().any():
        return first[F_ORIG_CREDIT_LIMIT]
    return first[F_CREDIT_LIMIT]


def months_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    """Whole calendar months from ``earlier`` to ``later`` (month-on-book)."""
    lp = pd.PeriodIndex(later, freq="M")
    ep = pd.PeriodIndex(earlier, freq="M")
    return pd.Series((lp - ep).map(lambda d: d.n), index=later.index)
