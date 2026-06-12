"""Deterministic, rule-based observations derived from computed metrics.

This layer mechanically turns the metric battery's numbers into templated,
auditable statements of fact -- "summary thoughts" a reviewer would
otherwise read off the tables by hand.  Every observation is produced by a
fixed rule (identified by ``rule_id``) over the computed summaries and
tables: same review in, same observations out, golden-tested like every
other number.

Boundary with the findings document: observations state *what the numbers
show* (levels, trends, rankings, linkages between metrics).  They never
state analytical opinions, root causes, or conclusions -- that remains the
human analyst's job, and the findings template labels these accordingly.

Severity taxonomy (ordered): ``INFO`` (neutral fact), ``NOTABLE``
(magnitude worth attention or a WATCH-level threshold), ``ELEVATED``
(material adverse magnitude or a breached threshold).  Where an observation
covers a summary value that also has a configured threshold, the severity
is at least as high as the threshold outcome, so the two layers can never
contradict each other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from ucpa.metrics.results import ReviewResult

SEV_INFO = "INFO"
SEV_NOTABLE = "NOTABLE"
SEV_ELEVATED = "ELEVATED"
_SEV_ORDER = {SEV_INFO: 0, SEV_NOTABLE: 1, SEV_ELEVATED: 2}


@dataclass(frozen=True)
class Observation:
    """One deterministic, rule-generated statement of fact.

    Attributes:
        rule_id: Stable identifier of the rule that produced the text.
        category: Reporting area (e.g. ``delinquency``, ``vintage``).
        severity: ``INFO`` / ``NOTABLE`` / ``ELEVATED``.
        text: The templated statement, with the underlying numbers embedded.
    """

    rule_id: str
    category: str
    severity: str
    text: str


def _pct(x: float, dp: int = 2) -> str:
    return f"{x:.{dp}%}"


def _pp(x: float) -> str:
    """Format a rate delta in percentage points with an explicit sign."""
    return f"{x * 100.0:+.2f}pp"


def _max_sev(*sevs: str) -> str:
    return max(sevs, key=lambda s: _SEV_ORDER[s])


def _threshold_severity(review: ReviewResult, *summary_keys: str) -> str:
    """Severity implied by the threshold layer for the given summary keys."""
    sev = SEV_INFO
    for e in review.exceptions:
        if e.summary_key in summary_keys:
            sev = _max_sev(sev, SEV_ELEVATED if e.severity == "EXCEPTION" else SEV_NOTABLE)
    return sev


def _summary(review: ReviewResult, metric: str) -> Optional[dict]:
    result = review.result_for(metric)
    if result is None or result.status == "blocked":
        return None
    return result.summary


def _value(review: ReviewResult, metric: str, key: str) -> Optional[float]:
    s = _summary(review, metric)
    if s is None:
        return None
    v = s.get(key)
    return float(v) if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------------------
# Rules. Each returns a list (possibly empty) of observations; rules skip
# silently when the metrics they read were blocked by data gaps.
# ---------------------------------------------------------------------------
def _rule_dq_level(review: ReviewResult) -> list[Observation]:
    s = _summary(review, "delinquency_distribution")
    if s is None or s.get("dpd30plus_balance_rate") is None:
        return []
    as_of = s.get("as_of")
    as_of_txt = as_of.strftime("%Y-%m") if isinstance(as_of, pd.Timestamp) else str(as_of)
    sev = _threshold_severity(review, "dpd30plus_balance_rate", "dpd90plus_balance_rate")
    return [
        Observation(
            "OBS-DQ-01",
            "delinquency",
            sev,
            f"As of {as_of_txt}, {_pct(s['dpd30plus_balance_rate'])} of open balances are 30+ "
            f"days past due ({_pct(s['dpd90plus_balance_rate'])} are 90+), across "
            f"{s['total_accounts']:,} open accounts and ${s['total_balance']:,.0f}.",
        )
    ]


def _rule_dq_trend(review: ReviewResult) -> list[Observation]:
    delta = _value(review, "portfolio_time_series", "dpd30plus_yoy_delta")
    if delta is None:
        return []
    if delta > 0:
        direction = "higher than"
        sev = SEV_ELEVATED if delta > 0.005 else (SEV_NOTABLE if delta > 0.001 else SEV_INFO)
    else:
        direction = "lower than" if delta < 0 else "unchanged from"
        sev = SEV_INFO
    sev = _max_sev(sev, _threshold_severity(review, "dpd30plus_yoy_delta"))
    return [
        Observation(
            "OBS-DQ-02",
            "delinquency",
            sev,
            f"The 30+ DPD balance rate is {_pp(delta)} {direction} twelve months ago.",
        )
    ]


def _rule_co_trend(review: ReviewResult) -> list[Observation]:
    out: list[Observation] = []
    gross = _value(review, "charge_off_rates", "gross_co_rate_t12")
    net = _value(review, "charge_off_rates", "net_co_rate_t12")
    if gross is not None:
        sev = _threshold_severity(review, "gross_co_rate_t12", "net_co_rate_t12")
        net_txt = f" ({_pct(net)} net of recoveries)" if net is not None else ""
        out.append(
            Observation(
                "OBS-CO-01",
                "charge_offs",
                sev,
                f"The trailing-12-month annualized gross charge-off rate is {_pct(gross)}{net_txt}.",
            )
        )
    delta = _value(review, "portfolio_time_series", "gross_co_rate_yoy_delta")
    if delta is not None:
        if delta > 0:
            sev = SEV_ELEVATED if delta > 0.005 else (SEV_NOTABLE if delta > 0.001 else SEV_INFO)
            direction = "above"
        else:
            sev, direction = SEV_INFO, "below"
        sev = _max_sev(sev, _threshold_severity(review, "gross_co_rate_yoy_delta"))
        out.append(
            Observation(
                "OBS-CO-02",
                "charge_offs",
                sev,
                f"The trailing-12-month charge-off rate runs {_pp(delta)} "
                f"{direction} the same window one year earlier.",
            )
        )
    return out


def _rule_growth(review: ReviewResult) -> list[Observation]:
    growth = _value(review, "portfolio_time_series", "balance_growth_12m")
    if growth is None:
        return []
    sev = _max_sev(
        SEV_NOTABLE if growth > 0.25 else SEV_INFO,
        _threshold_severity(review, "balance_growth_12m"),
    )
    suffix = (
        " Delinquency and charge-off rates are measured against this growing denominator."
        if growth > 0.25
        else ""
    )
    return [
        Observation(
            "OBS-TS-01",
            "time_series",
            sev,
            f"Open balances changed {_pct(growth, 1)} over the last twelve months.{suffix}",
        )
    ]


def _rule_roll_trend(review: ReviewResult) -> list[Observation]:
    result = review.result_for("migration_matrix")
    if result is None or result.status == "blocked" or "trend" not in result.tables:
        return []
    trend = result.tables["trend"]
    if len(trend) < 12:
        return []
    last6 = float(trend["current_to_dpd30"].tail(6).mean())
    prior6 = float(trend["current_to_dpd30"].iloc[-12:-6].mean())
    if prior6 <= 0 or last6 < 0.001:  # too thin to compare meaningfully
        return []
    ratio = last6 / prior6
    if ratio >= 1.5:
        sev = SEV_ELEVATED
    elif ratio >= 1.25:
        sev = SEV_NOTABLE
    else:
        sev = SEV_INFO
    direction = "up from" if ratio > 1 else "down from" if ratio < 1 else "level with"
    return [
        Observation(
            "OBS-MIG-01",
            "roll_rates",
            sev,
            f"The current->30DPD dollar roll rate averaged {_pct(last6)} over the last six "
            f"months, {direction} {_pct(prior6)} over the prior six.",
        )
    ]


def _rule_cure(review: ReviewResult) -> list[Observation]:
    cure = _value(review, "migration_matrix", "dpd30_cure_rate")
    if cure is None:
        return []
    sev = _threshold_severity(review, "dpd30_cure_rate")
    return [
        Observation(
            "OBS-MIG-02",
            "roll_rates",
            sev,
            f"{_pct(cure)} of 30DPD dollars cure to current month over month; "
            f"{_pct(_value(review, 'migration_matrix', 'dpd30_to_dpd60') or 0.0)} roll forward to 60DPD.",
        )
    ]


def _rule_vintage(review: ReviewResult) -> list[Observation]:
    result = review.result_for("vintage_curves")
    if result is None or result.status == "blocked":
        return []
    out: list[Observation] = []
    summary = result.summary
    cohort_summary = result.tables.get("cohort_summary")
    worst = summary.get("worst_cohort_mob12")
    worst_loss = summary.get("max_cum_loss_mob12")
    if worst is not None and worst_loss is not None and cohort_summary is not None:
        measurable = cohort_summary["cum_loss_mob12"].dropna()
        if len(measurable) >= 2:
            median = float(measurable.median())
            ratio = (float(worst_loss) / median) if median > 0 else float("inf")
            sev = SEV_ELEVATED if ratio >= 2.0 else (SEV_NOTABLE if ratio >= 1.5 else SEV_INFO)
            sev = _max_sev(sev, _threshold_severity(review, "max_cum_loss_mob12"))
            out.append(
                Observation(
                    "OBS-VIN-01",
                    "vintage",
                    sev,
                    f"Cohort {worst} shows the highest MOB-12 cumulative loss at "
                    f"{_pct(float(worst_loss))}, versus a median of {_pct(median)} across "
                    f"{len(measurable)} measurable cohorts.",
                )
            )
    ratio = summary.get("recent_vs_seasoned_mob12_ratio")
    if ratio is not None:
        ratio = float(ratio)
        if ratio > 1.0:
            sev = SEV_ELEVATED if ratio >= 1.5 else SEV_NOTABLE
            comparison = f"{ratio:.2f}x the seasoned-cohort average"
        else:
            sev = SEV_INFO
            comparison = f"{ratio:.2f}x (at or below) the seasoned-cohort average"
        sev = _max_sev(sev, _threshold_severity(review, "recent_vs_seasoned_mob12_ratio"))
        out.append(
            Observation(
                "OBS-VIN-02",
                "vintage",
                sev,
                f"The four most recent measurable quarterly cohorts are losing {comparison} "
                f"at month-on-book 12.",
            )
        )
    return out


def _rule_mix(review: ReviewResult) -> list[Observation]:
    below_prime = _value(review, "concentration", "below_prime_balance_share")
    subprime = _value(review, "concentration", "subprime_balance_share")
    if below_prime is None or subprime is None:
        return []
    sev = _threshold_severity(
        review, "below_prime_balance_share", "subprime_balance_share", "max_vintage_year_share"
    )
    return [
        Observation(
            "OBS-CON-01",
            "concentration",
            sev,
            f"{_pct(below_prime)} of open balances sit below prime "
            f"({_pct(subprime)} subprime).",
        )
    ]


def _rule_utilization(review: ReviewResult) -> list[Observation]:
    high = _value(review, "utilization_distribution", "high_util_balance_share")
    port = _value(review, "utilization_distribution", "portfolio_utilization")
    if high is None or port is None:
        return []
    sev = _max_sev(
        SEV_NOTABLE if high > 0.20 else SEV_INFO,
        _threshold_severity(review, "high_util_balance_share", "portfolio_utilization"),
    )
    return [
        Observation(
            "OBS-UTL-01",
            "utilization",
            sev,
            f"{_pct(high)} of open balances sit on accounts at or above 90% utilization; "
            f"portfolio-level utilization is {_pct(port)}.",
        )
    ]


def _rule_line_management(review: ReviewResult) -> list[Observation]:
    s = _summary(review, "line_management")
    if s is None or s.get("exposure_added_total") is None:
        return []
    sev = _threshold_severity(review, "increase_share_below_prime", "increases_gone_bad_rate")
    return [
        Observation(
            "OBS-LIN-01",
            "line_management",
            sev,
            f"{s['line_increase_events']:,} line increases added ${s['exposure_added_total']:,.0f} "
            f"of exposure over the panel; {_pct(float(s['increase_share_below_prime']))} of the "
            f"increase dollars went to below-prime accounts, and "
            f"{_pct(float(s['increases_gone_bad_rate']))} of measurable increases hit 30+ DPD "
            f"within six months.",
        )
    ]


def _rule_recoveries(review: ReviewResult) -> list[Observation]:
    t12 = _value(review, "recovery_trends", "recovery_rate_t12")
    if t12 is None:
        return []
    sev = _threshold_severity(review, "recovery_rate_t12")
    return [
        Observation(
            "OBS-REC-01",
            "recoveries",
            sev,
            f"Trailing-12-month recoveries equal {_pct(t12)} of trailing-12-month gross "
            f"charge-offs.",
        )
    ]


def _rule_data_maturity(review: ReviewResult) -> list[Observation]:
    det = review.tier_detection
    n_gaps = len(review.gaps)
    if n_gaps:
        sev = SEV_NOTABLE
        tail = (
            f"{n_gaps} analytic(s) are blocked or limited by missing data -- "
            "see the data-maturity gap assessment."
        )
    else:
        sev = SEV_INFO
        tail = "the tape supports the full metric battery."
    return [
        Observation(
            "OBS-DAT-01",
            "data_maturity",
            sev,
            f"The tape was detected at Tier {det.detected_tier} "
            f"({'monthly panel' if det.is_panel else 'snapshot'}); {tail}",
        )
    ]


_RULES = (
    _rule_dq_level,
    _rule_dq_trend,
    _rule_roll_trend,
    _rule_cure,
    _rule_co_trend,
    _rule_recoveries,
    _rule_vintage,
    _rule_mix,
    _rule_utilization,
    _rule_line_management,
    _rule_growth,
    _rule_data_maturity,
)


def derive_observations(review: ReviewResult) -> list[Observation]:
    """Run every observation rule over ``review``, in fixed report order."""
    out: list[Observation] = []
    for rule in _RULES:
        out.extend(rule(review))
    return out
