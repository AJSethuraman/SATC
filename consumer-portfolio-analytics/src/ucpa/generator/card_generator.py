"""Seeded synthetic credit-card portfolio generator (Tier 2 panel).

Produces a longitudinal monthly panel -- one row per account per month --
with full Tier 2 fields, suitable for exercising every layer of the engine.
All randomness flows through a single ``numpy.random.Generator`` seeded from
``CardGeneratorConfig.seed``; the same config always yields a byte-identical
tape.  No network access, no wall-clock dependence, no LLM involvement.

Correlated deterioration
------------------------
Deterioration is driven by three multiplicative factors on the monthly
current->30DPD entry hazard, so vintage curves and migration matrices look
like real card books rather than noise:

* **Score band** -- subprime accounts enter delinquency at ~15-20x the
  super-prime rate (``BASE_ENTRY_PROB``).
* **Origination vintage** -- ``VINTAGE_FACTORS`` makes 2022-2023 vintages
  materially weaker than 2020-2021 vintages, mirroring the post-pandemic
  underwriting-loosening underperformance documented in the New York Fed's
  Household Debt and Credit reports and industry vintage commentary.
* **Months-on-book seasoning** -- the hazard ramps up over the first ~8
  months, peaks around MOB 12-24, and decays modestly thereafter (classic
  card seasoning curve shape).

Roll-forward severity through the delinquency buckets also scales mildly
with band and vintage, so weaker cohorts both enter delinquency more often
and cure less often.

Calibration targets (documented per the calibration requirement)
----------------------------------------------------------------
The default configuration is tuned so the portfolio's mature-period
aggregates land on published industry figures:

* **30+ DPD delinquency rate (% of balances)** ~ 3.0%.
  Source: FRED series ``DRCCLACBS`` (Delinquency Rate on Credit Card Loans,
  All Commercial Banks), ~3.05% in Q1 2025 and ~3.2% average over 2024.
  Default config produces ~3.1-3.3%; calibration test band: 2.5% - 3.8%.
* **Annualized gross charge-off rate (% of balances)** ~ 4.0-4.5%.
  Source: FRED series ``CORCCACBS`` (Charge-Off Rate on Credit Card Loans,
  All Commercial Banks), ~3.6-4.2% over 2023 rising to ~4.4-4.7% over
  2024 - Q1 2025.  Default config produces ~3.7-4.1%; calibration test
  band: 3.2% - 5.2%.
* **Recoveries** ~ 15-20% of gross charge-offs (industry rule of thumb for
  card recovery rates), so the net charge-off rate runs ~0.6-0.9pp below
  gross.
* Vintage mix and the weak-2022/2023-cohort pattern follow the New York
  Fed Household Debt and Credit report narrative (rising card delinquency
  driven by recent vintages and high-utilization borrowers).

These are *targets for synthetic realism*, asserted as ranges in
``tests/test_generator.py``; the tape remains fully synthetic and seeded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ucpa.data_model import (
    BUCKET_ORDER,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_CHARGE_OFF_FLAG,
    F_CREDIT_LIMIT,
    F_CURRENT_SCORE,
    F_DELINQUENCY_BUCKET,
    F_ORIG_CREDIT_LIMIT,
    F_ORIG_SCORE,
    F_ORIGINAL_TERM_MONTHS,
    F_ORIGINATION_DATE,
    F_PAYMENT_STATUS,
    F_PRODUCT_TYPE,
    F_RECOVERY_AMOUNT,
    F_REMAINING_TERM_MONTHS,
    F_SCORE_BAND,
    F_UTILIZATION,
    PRODUCT_CREDIT_CARD,
    SCORE_BAND_RANGES,
    SCORE_BANDS,
)

# --- Band-level behavior parameters (index order matches SCORE_BANDS) -------
#: Portfolio origination mix by band: super-prime, prime, near-prime, subprime.
BAND_MIX: tuple[float, ...] = (0.25, 0.45, 0.18, 0.12)
#: Base monthly probability of rolling CURRENT -> DPD30, by band, before
#: vintage/seasoning/idiosyncratic multipliers. Tuned to FRED targets above.
BASE_ENTRY_PROB: tuple[float, ...] = (0.0015, 0.0046, 0.0119, 0.0255)
#: Mean credit limit by band (lognormal draw around these).
MEAN_LIMIT: tuple[float, ...] = (15000.0, 9000.0, 5000.0, 2500.0)
#: Long-run target utilization by band when current.
TARGET_UTIL: tuple[float, ...] = (0.10, 0.22, 0.42, 0.60)
#: Multiplier on roll-forward probabilities within delinquency, by band.
ROLL_FWD_MULT: tuple[float, ...] = (0.80, 0.92, 1.06, 1.18)

#: Origination-vintage quality factor on the entry hazard, by calendar year.
#: <1 = better than average, >1 = worse. The weak 2022-2023 cohorts mirror
#: the post-pandemic vintage underperformance in NY Fed HHDC reporting.
VINTAGE_FACTORS: dict[int, float] = {
    2019: 0.85,
    2020: 0.75,
    2021: 0.90,
    2022: 1.20,
    2023: 1.35,
    2024: 1.15,
    2025: 1.05,
}

#: Conditional one-month (cure-to-current, roll-forward) base probabilities
#: from each delinquency bucket DPD30..DPD120; the residual is "stay".
#: The DPD120 roll-forward target is charge-off (~180 DPD timing).
BASE_CURE: tuple[float, ...] = (0.50, 0.20, 0.05, 0.02)
BASE_ROLL: tuple[float, ...] = (0.31, 0.54, 0.68, 0.78)

#: Recovery schedule: collections arrive months 3-12 after charge-off with
#: geometrically decaying weights (factor 0.85), summing to 1.0.
_REC_RAW = 0.85 ** np.arange(10)
RECOVERY_WEIGHTS: np.ndarray = _REC_RAW / _REC_RAW.sum()
RECOVERY_START_LAG = 3
RECOVERY_MONTHS = 10


@dataclass(frozen=True)
class CardGeneratorConfig:
    """Configuration for the synthetic card generator.

    Attributes:
        n_accounts: Number of accounts to originate.
        panel_start: First as-of month, ``"YYYY-MM"``.
        n_months: Panel length in months.
        seed: RNG seed; same config + seed => byte-identical tape.
        origination_window_months: Originations are drawn uniformly over the
            first this-many panel months, so every vintage is observed from
            month-on-book zero and the newest vintage still has history.
        entry_scale: Global multiplier on the current->DPD30 hazard
            (the primary calibration knob for FRED DRCCLACBS/CORCCACBS).
        mean_recovery_rate: Mean lifetime recoveries as a share of the
            charged-off balance (industry card recoveries run ~15-20%).
    """

    n_accounts: int = 4000
    panel_start: str = "2021-01"
    n_months: int = 54
    seed: int = 42
    origination_window_months: int = 48
    entry_scale: float = 1.0
    mean_recovery_rate: float = 0.17


def _seasoning(mob: np.ndarray) -> np.ndarray:
    """Months-on-book multiplier on the entry hazard.

    Ramps ~linearly to 1.0 by MOB 8, peaks ~1.18 around MOB 12-24 via a
    Gaussian hump centered at MOB 16, then decays toward 0.85 by ~MOB 54.
    """
    ramp = np.clip(mob / 8.0, 0.0, 1.0)
    hump = 1.0 + 0.18 * np.exp(-((mob - 16.0) ** 2) / 72.0)
    tail = 1.0 - 0.15 * np.clip((mob - 30.0) / 24.0, 0.0, 1.0)
    return ramp * hump * tail


def generate_card_portfolio(config: CardGeneratorConfig | None = None) -> pd.DataFrame:
    """Generate a Tier 2 longitudinal synthetic credit-card tape.

    Args:
        config: Generator configuration; defaults to the calibrated defaults.

    Returns:
        DataFrame with one row per account per observed month, carrying the
        full Tier 2 field set (term fields are NA -- not applicable to
        revolving cards), sorted by (account_id, as_of_date).
    """
    cfg = config or CardGeneratorConfig()
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_accounts
    months = pd.period_range(cfg.panel_start, periods=cfg.n_months, freq="M")
    month_starts = months.to_timestamp()  # month-start Timestamps

    # ---------------- static account attributes ----------------
    orig_window = min(cfg.origination_window_months, cfg.n_months)
    orig_idx = rng.integers(0, orig_window, size=n)
    band_idx = rng.choice(len(SCORE_BANDS), size=n, p=BAND_MIX)

    band_lo = np.array([SCORE_BAND_RANGES[b][0] for b in SCORE_BANDS])
    band_hi = np.array([SCORE_BAND_RANGES[b][1] for b in SCORE_BANDS])
    orig_score = rng.integers(band_lo[band_idx], band_hi[band_idx] + 1)

    mean_limit = np.array(MEAN_LIMIT)[band_idx]
    limit = np.round(
        np.maximum(rng.lognormal(np.log(mean_limit) - 0.125, 0.5, size=n), 500.0), -2
    )
    orig_limit = limit.copy()

    # Idiosyncratic risk multiplier (lognormal, mean ~1.06).
    risk_mult = rng.lognormal(0.0, 0.35, size=n)
    target_util = np.clip(
        np.array(TARGET_UTIL)[band_idx] + rng.normal(0.0, 0.12, size=n), 0.01, 0.92
    )
    # A band-dependent share of borrowers run near-maxed-out lines even while
    # current (heavier near-limit tail observed in real card books and in the
    # NY Fed HHDC high-utilization-borrower commentary).
    maxed_share = np.array([0.04, 0.08, 0.15, 0.25])[band_idx]
    maxed = rng.random(n) < maxed_share
    target_util = np.where(
        maxed, np.clip(rng.normal(0.96, 0.03, size=n), 0.85, 1.0), target_util
    )
    recovery_rate = np.clip(
        rng.normal(cfg.mean_recovery_rate, 0.05, size=n), 0.05, 0.35
    )

    orig_year = month_starts[orig_idx].year.to_numpy()
    vintage_f = np.array([VINTAGE_FACTORS.get(int(y), 1.0) for y in orig_year])
    band_roll = np.array(ROLL_FWD_MULT)[band_idx]
    roll_sev = np.clip(band_roll * vintage_f**0.25, 0.6, 1.45)

    # ---------------- dynamic state ----------------
    # state: -1 pre-origination, 0 CURRENT, 1..4 DPD30..DPD120, 5 charged off
    state = np.full(n, -1, dtype=np.int64)
    util = np.zeros(n)
    balance = np.zeros(n)
    score = orig_score.astype(np.float64).copy()
    co_month = np.full(n, -10**6, dtype=np.int64)  # panel index of charge-off
    co_amount = np.zeros(n)

    bucket_labels = np.array(BUCKET_ORDER)
    chunks: list[dict[str, np.ndarray]] = []

    for t in range(cfg.n_months):
        # Fixed-size draws every month keep the RNG call sequence stable.
        u_entry = rng.random(n)
        u_roll = rng.random(n)
        u_split = rng.random(n)
        util_noise = rng.normal(0.0, 1.0, size=n)
        u_line = rng.random(n)
        u_pay = rng.random(n)
        u_score = rng.random(n)

        # Originations this month start CURRENT.
        state[orig_idx == t] = 0

        live = state >= 0
        mob = np.where(live, t - orig_idx, 0)
        prev_state = state.copy()
        prev_balance = balance.copy()

        # ---- delinquency-state transitions (skip accounts originated now) ----
        seasoned = live & (mob > 0)

        cur = seasoned & (prev_state == 0)
        p_entry = np.clip(
            np.asarray(BASE_ENTRY_PROB)[band_idx]
            * vintage_f
            * _seasoning(mob.astype(float))
            * risk_mult
            * cfg.entry_scale,
            0.0,
            0.60,
        )
        state[cur & (u_entry < p_entry)] = 1

        for b in range(1, 5):  # DPD30..DPD120
            in_b = seasoned & (prev_state == b)
            if not in_b.any():
                continue
            roll_p = np.clip(BASE_ROLL[b - 1] * roll_sev, 0.05, 0.95)
            cure_p = np.clip(BASE_CURE[b - 1] / roll_sev, 0.01, 1.0 - roll_p)
            roll_to = state.copy()
            roll_to[in_b & (u_roll < cure_p)] = 0  # full cure to current
            stay_lo = cure_p
            stay_hi = 1.0 - roll_p
            stays = in_b & (u_roll >= stay_lo) & (u_roll < stay_hi)
            # A share of "stays" in DPD60+ are partial cures (one bucket back).
            if b >= 2:
                partial = stays & (u_split < 0.30)
                roll_to[partial] = b - 1
                roll_to[stays & ~partial] = b
            else:
                roll_to[stays] = b
            roll_to[in_b & (u_roll >= stay_hi)] = b + 1  # roll forward
            state = np.where(in_b, roll_to, state)

        newly_co = (state == 5) & (prev_state == 4)
        co_month[newly_co] = t
        co_amount[newly_co] = np.round(prev_balance[newly_co] * 1.03, 2)

        # ---- line management (Tier 2 line-change history) ----
        active = live & (state < 5)
        inc = (
            active
            & (state == 0)
            & (mob >= 12)
            & (band_idx <= 2)  # super-prime/prime/near-prime only
            & (util > 0.30)
            & (u_line < 0.010)
        )
        limit[inc] = np.round(limit[inc] * 1.18, -2)
        dec = active & (state >= 2) & (u_line > 0.96)
        limit[dec] = np.maximum(np.round(limit[dec] * 0.70, -2), prev_balance[dec])

        # ---- utilization & balance ----
        ramp = 0.35 + 0.65 * np.clip(mob / 6.0, 0.0, 1.0)
        eff_target = np.where(state >= 1, np.maximum(target_util, 0.88), target_util * ramp)
        new_util = np.clip(0.75 * util + 0.25 * eff_target + 0.02 * util_noise, 0.0, 1.15)
        just_orig = orig_idx == t
        new_util = np.where(just_orig, np.clip(target_util * 0.35, 0.0, 1.0), new_util)
        util = np.where(active, new_util, util)
        balance = np.where(active, np.round(util * limit, 2), 0.0)
        balance[newly_co] = co_amount[newly_co]
        util = np.where(newly_co, np.round(co_amount / limit, 4), util)

        # ---- refreshed score drift ----
        worsened = state > prev_state
        cured = (state == 0) & (prev_state >= 1)
        drift = np.where(
            worsened,
            -22.0 - 10.0 * u_score,
            np.where(cured, 5.0, np.where((state == 0) & (u_score < 0.30), 1.0, 0.0)),
        )
        score = np.clip(np.where(live, score + drift, score), 300.0, 850.0)

        # ---- payment status ----
        pay = np.full(n, "NO_PAY", dtype=object)
        cur_now = active & (state == 0)
        pay[cur_now & (u_pay < 0.22)] = "FULL_PAY"
        pay[cur_now & (u_pay >= 0.22) & (u_pay < 0.85)] = "MIN_PAY"
        pay[cur_now & (u_pay >= 0.85)] = "PARTIAL_PAY"
        d30 = active & (state == 1)
        pay[d30 & (u_pay < 0.35)] = "PARTIAL_PAY"

        # ---- recoveries on charged-off accounts ----
        lag = t - co_month
        recovering = (state == 5) & (lag >= RECOVERY_START_LAG) & (
            lag < RECOVERY_START_LAG + RECOVERY_MONTHS
        )
        recovery = np.zeros(n)
        if recovering.any():
            w = RECOVERY_WEIGHTS[lag[recovering] - RECOVERY_START_LAG]
            recovery[recovering] = np.round(co_amount[recovering] * recovery_rate[recovering] * w, 2)

        # ---- emit rows: active accounts + CO accounts inside recovery window ----
        post_co = (state == 5) & (lag >= 0) & (lag < RECOVERY_START_LAG + RECOVERY_MONTHS)
        emit = active | post_co
        idx = np.flatnonzero(emit)
        emit_balance = np.where(newly_co[idx], co_amount[idx], np.where(state[idx] == 5, 0.0, balance[idx]))
        chunks.append(
            {
                "acct": idx,
                "month_idx": np.full(idx.size, t),
                "state": state[idx],
                "balance": emit_balance,
                "limit": limit[idx],
                "util": np.where(state[idx] == 5, 0.0, np.round(util[idx], 4)),
                "score": score[idx].astype(np.int64),
                "pay": pay[idx],
                "recovery": recovery[idx],
            }
        )

    # ---------------- assemble DataFrame ----------------
    acct = np.concatenate([c["acct"] for c in chunks])
    month_idx = np.concatenate([c["month_idx"] for c in chunks])
    state_col = np.concatenate([c["state"] for c in chunks])

    df = pd.DataFrame(
        {
            F_ACCOUNT_ID: np.char.add("CC", np.char.zfill(acct.astype(str), 6)),
            F_PRODUCT_TYPE: PRODUCT_CREDIT_CARD,
            F_ORIGINATION_DATE: month_starts[orig_idx[acct]],
            F_AS_OF_DATE: month_starts[month_idx],
            F_BALANCE: np.concatenate([c["balance"] for c in chunks]),
            F_DELINQUENCY_BUCKET: bucket_labels[state_col],
            F_CHARGE_OFF_FLAG: (state_col == 5).astype(np.int64),
            F_CREDIT_LIMIT: np.concatenate([c["limit"] for c in chunks]),
            F_SCORE_BAND: np.array(SCORE_BANDS, dtype=object)[band_idx[acct]],
            F_PAYMENT_STATUS: np.concatenate([c["pay"] for c in chunks]),
            F_ORIG_SCORE: orig_score[acct],
            F_CURRENT_SCORE: np.concatenate([c["score"] for c in chunks]),
            F_UTILIZATION: np.concatenate([c["util"] for c in chunks]),
            F_ORIG_CREDIT_LIMIT: orig_limit[acct],
            F_RECOVERY_AMOUNT: np.concatenate([c["recovery"] for c in chunks]),
            F_ORIGINAL_TERM_MONTHS: pd.array([pd.NA] * acct.size, dtype="Int64"),
            F_REMAINING_TERM_MONTHS: pd.array([pd.NA] * acct.size, dtype="Int64"),
        }
    )
    df = df.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort").reset_index(drop=True)
    df[F_DELINQUENCY_BUCKET] = df[F_DELINQUENCY_BUCKET].astype(str)
    return df
