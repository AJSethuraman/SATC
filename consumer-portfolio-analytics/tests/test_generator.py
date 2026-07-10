"""Generator tests: determinism, correlated deterioration, FRED calibration."""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    F_ORIGINAL_TERM_MONTHS,
    F_REMAINING_TERM_MONTHS,
    TIER0_FIELDS,
    TIER1_ONLY_FIELDS,
    TIER2_ONLY_FIELDS,
)
from ucpa.generator import CardGeneratorConfig, generate_card_portfolio
from ucpa.metrics.common import active_rows, charge_off_events, monthly_outstanding

from conftest import SMALL_CONFIG


def test_same_seed_identical_tape(small_tape: pd.DataFrame) -> None:
    again = generate_card_portfolio(SMALL_CONFIG)
    pd.testing.assert_frame_equal(small_tape, again)


def test_different_seed_differs(small_tape: pd.DataFrame) -> None:
    other = generate_card_portfolio(
        CardGeneratorConfig(
            n_accounts=500, n_months=36, origination_window_months=30, seed=7
        )
    )
    assert not small_tape.equals(other)


def test_full_tier2_schema(small_tape: pd.DataFrame) -> None:
    for field in TIER0_FIELDS | TIER1_ONLY_FIELDS | TIER2_ONLY_FIELDS:
        assert field in small_tape.columns, field
    # Term fields exist in the schema but are NA: not applicable to revolving.
    assert small_tape[F_ORIGINAL_TERM_MONTHS].isna().all()
    assert small_tape[F_REMAINING_TERM_MONTHS].isna().all()


def test_longitudinal_panel_shape(small_tape: pd.DataFrame) -> None:
    per_account = small_tape.groupby("account_id")[["as_of_date"]].nunique()["as_of_date"]
    assert (per_account > 1).mean() > 0.95  # nearly all accounts observed monthly
    dup = small_tape.duplicated(subset=["account_id", "as_of_date"])
    assert not dup.any()  # exactly one row per account per month


def test_correlated_deterioration_by_score_band(small_tape: pd.DataFrame) -> None:
    """Weaker bands must roll to delinquency at higher rates."""
    act = active_rows(small_tape)
    ever_dq = (
        act.assign(dq=act["delinquency_bucket"] != "CURRENT")
        .groupby("account_id")
        .agg(band=("score_band", "first"), dq=("dq", "max"))
    )
    rates = ever_dq.groupby("band")["dq"].mean()
    assert rates["SUBPRIME"] > rates["NEAR_PRIME"] > rates["PRIME"] > rates["SUPER_PRIME"]


def test_correlated_deterioration_by_vintage() -> None:
    """Weak 2023 vintages must out-lose strong 2021 vintages at equal MOB."""
    tape = generate_card_portfolio()  # default calibrated config
    events = charge_off_events(tape)
    events["mob"] = (
        pd.PeriodIndex(events["co_date"], freq="M")
        - pd.PeriodIndex(events["origination_date"], freq="M")
    ).map(lambda d: d.n)
    events["year"] = events["origination_date"].dt.year

    first = tape.sort_values(["account_id", "as_of_date"]).groupby("account_id").first()
    first["year"] = first["origination_date"].dt.year
    denom = first.groupby("year")["orig_credit_limit"].sum()

    # Compare cumulative loss through MOB 18 (both cohorts fully observed).
    cum18 = (
        events[events["mob"] <= 18].groupby("year")["co_amount"].sum() / denom
    ).fillna(0.0)
    assert cum18[2023] > cum18[2021] * 1.3


def test_calibration_to_fred_industry_aggregates() -> None:
    """Default tape must land on FRED DRCCLACBS / CORCCACBS-style figures.

    Targets documented in ucpa.generator.card_generator: 30+ DPD balance
    rate ~3.0% (DRCCLACBS), annualized gross charge-off rate ~4.0-4.5%
    (CORCCACBS), recoveries ~15-20% of gross charge-offs.
    """
    tape = generate_card_portfolio()
    act = active_rows(tape)
    last = act[act["as_of_date"] == act["as_of_date"].max()]
    dq_bal = last.loc[
        last["delinquency_bucket"].isin(["DPD30", "DPD60", "DPD90", "DPD120"]), "balance"
    ].sum()
    dq90_bal = last.loc[
        last["delinquency_bucket"].isin(["DPD90", "DPD120"]), "balance"
    ].sum()
    rate30 = dq_bal / last["balance"].sum()
    rate90 = dq90_bal / last["balance"].sum()

    out = monthly_outstanding(tape)
    events = charge_off_events(tape)
    co_by_month = events.groupby("co_date")["co_amount"].sum().reindex(out.index).fillna(0.0)
    gross_t12 = co_by_month.tail(12).sum() / out.tail(12).mean()
    rec = tape.groupby("as_of_date")["recovery_amount"].sum().reindex(out.index).fillna(0.0)
    rec_share = rec.tail(12).sum() / co_by_month.tail(12).sum()

    assert 0.025 <= rate30 <= 0.038, rate30  # FRED DRCCLACBS ~3.0-3.2%
    assert 0.004 <= rate90 <= 0.018, rate90
    assert 0.032 <= gross_t12 <= 0.052, gross_t12  # FRED CORCCACBS ~3.6-4.7%
    assert 0.10 <= rec_share <= 0.25, rec_share  # industry recovery rule of thumb


def test_charge_off_convention(small_tape: pd.DataFrame) -> None:
    """CO-month row carries the write-off amount; later rows carry zero."""
    events = charge_off_events(small_tape)
    assert (events["co_amount"] > 0).all()
    co_rows = small_tape[small_tape["charge_off_flag"] == 1]
    later = co_rows.merge(events, on="account_id")
    later = later[later["as_of_date"] > later["co_date"]]
    assert (later["balance"] == 0.0).all()
