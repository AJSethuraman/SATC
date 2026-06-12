"""Credit-card product module: the Phase 1 reference implementation.

This module is the template that personal/installment and student loans
will follow in Phase 2: it declares the product's tier field model and
wires the full deterministic metric battery to its data requirements and
configurable threshold checks.
"""

from __future__ import annotations

from ucpa.data_model import (
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_CHARGE_OFF_FLAG,
    F_CREDIT_LIMIT,
    F_DELINQUENCY_BUCKET,
    F_ORIGINAL_TERM_MONTHS,
    F_ORIGINATION_DATE,
    F_RECOVERY_AMOUNT,
    F_REMAINING_TERM_MONTHS,
    F_SCORE_BAND,
    PRODUCT_CREDIT_CARD,
)
from ucpa.metrics.charge_offs import compute_charge_off_rates, compute_recovery_trends
from ucpa.metrics.concentration import compute_concentration
from ucpa.metrics.delinquency import compute_delinquency_distribution
from ucpa.metrics.migration import compute_migration_matrix
from ucpa.metrics.time_series import compute_portfolio_time_series
from ucpa.metrics.utilization import compute_line_management, compute_utilization_distribution
from ucpa.metrics.vintage import compute_vintage_curves
from ucpa.products.base import MetricSpec, ProductModule, ThresholdCheck

_T0 = (
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_ORIGINATION_DATE,
    F_BALANCE,
    F_DELINQUENCY_BUCKET,
    F_CHARGE_OFF_FLAG,
)


class CreditCardModule(ProductModule):
    """Asset-quality battery for revolving credit-card portfolios."""

    product_type = PRODUCT_CREDIT_CARD

    def not_applicable_fields(self) -> frozenset[str]:
        """Term fields do not apply to revolving credit."""
        return frozenset({F_ORIGINAL_TERM_MONTHS, F_REMAINING_TERM_MONTHS})

    def metric_specs(self) -> tuple[MetricSpec, ...]:
        cc = "credit_card"
        return (
            MetricSpec(
                name="delinquency_distribution",
                description=(
                    "Open-account balance and account distribution across "
                    "current/30/60/90/120+ delinquency buckets at the latest month."
                ),
                min_tier=0,
                required_fields=_T0,
                requires_panel=False,
                compute=compute_delinquency_distribution,
                checks=(
                    ThresholdCheck(f"{cc}.delinquency.max_dpd30plus_balance_rate", "dpd30plus_balance_rate", "max", "30+ DPD balance rate"),
                    ThresholdCheck(f"{cc}.delinquency.max_dpd90plus_balance_rate", "dpd90plus_balance_rate", "max", "90+ DPD balance rate"),
                ),
            ),
            MetricSpec(
                name="portfolio_time_series",
                description=(
                    "Consolidated monthly time series of balances, bucket mix, "
                    "originations, charge-offs, recoveries and utilization, with "
                    "year-over-year deterioration headlines."
                ),
                min_tier=1,
                required_fields=_T0,
                requires_panel=True,
                compute=compute_portfolio_time_series,
                checks=(
                    ThresholdCheck(f"{cc}.time_series.max_dpd30plus_yoy_delta", "dpd30plus_yoy_delta", "max", "30+ DPD rate YoY change (pp)"),
                    ThresholdCheck(f"{cc}.time_series.max_gross_co_rate_yoy_delta", "gross_co_rate_yoy_delta", "max", "Gross CO rate (T12) YoY change (pp)"),
                    ThresholdCheck(f"{cc}.time_series.max_balance_growth_12m", "balance_growth_12m", "max", "Open-balance growth over 12 months"),
                ),
            ),
            MetricSpec(
                name="migration_matrix",
                description=(
                    "Average month-over-month roll-rate / migration matrix between "
                    "delinquency buckets (account- and balance-weighted)."
                ),
                min_tier=1,
                required_fields=_T0,
                requires_panel=True,
                compute=compute_migration_matrix,
                checks=(
                    ThresholdCheck(f"{cc}.roll_rates.max_current_to_dpd30", "current_to_dpd30", "max", "Current -> 30DPD monthly roll rate ($)"),
                    ThresholdCheck(f"{cc}.roll_rates.max_dpd30_to_dpd60", "dpd30_to_dpd60", "max", "30DPD -> 60DPD monthly roll rate ($)"),
                    ThresholdCheck(f"{cc}.roll_rates.min_dpd30_cure_rate", "dpd30_cure_rate", "min", "30DPD cure rate ($)"),
                ),
            ),
            MetricSpec(
                name="vintage_curves",
                description=(
                    "Cumulative gross charge-off curves by origination quarter and "
                    "months-on-book, denominated on the cohort's original credit line."
                ),
                min_tier=1,
                required_fields=_T0 + (F_CREDIT_LIMIT,),
                requires_panel=True,
                compute=compute_vintage_curves,
                checks=(
                    ThresholdCheck(f"{cc}.vintage.max_cum_loss_mob12", "max_cum_loss_mob12", "max", "Worst-cohort cumulative loss at MOB 12"),
                    ThresholdCheck(f"{cc}.vintage.max_recent_vs_seasoned_mob12_ratio", "recent_vs_seasoned_mob12_ratio", "max", "Recent vs seasoned vintage loss ratio (MOB 12)", format="num"),
                ),
            ),
            MetricSpec(
                name="concentration",
                description=(
                    "Balance concentration by score band, origination vintage year, "
                    "and credit-line size, with HHI per dimension."
                ),
                min_tier=0,
                required_fields=_T0,
                requires_panel=False,
                compute=compute_concentration,
                checks=(
                    ThresholdCheck(f"{cc}.concentration.max_subprime_balance_share", "subprime_balance_share", "max", "Subprime balance share"),
                    ThresholdCheck(f"{cc}.concentration.max_below_prime_balance_share", "below_prime_balance_share", "max", "Below-prime (near-prime + subprime) balance share"),
                    ThresholdCheck(f"{cc}.concentration.max_vintage_year_share", "max_vintage_year_share", "max", "Largest single-vintage-year balance share"),
                    ThresholdCheck(f"{cc}.concentration.max_score_band_hhi", "score_band_hhi", "max", "Score-band HHI", format="num"),
                ),
            ),
            MetricSpec(
                name="charge_off_rates",
                description=(
                    "Annualized trailing-12-month gross and net charge-off rates "
                    "over average open balances, with the monthly series."
                ),
                min_tier=1,
                required_fields=_T0,
                requires_panel=True,
                compute=compute_charge_off_rates,
                checks=(
                    ThresholdCheck(f"{cc}.charge_offs.max_gross_co_rate_t12", "gross_co_rate_t12", "max", "Gross charge-off rate (T12, annualized)"),
                    ThresholdCheck(f"{cc}.charge_offs.max_net_co_rate_t12", "net_co_rate_t12", "max", "Net charge-off rate (T12, annualized)"),
                ),
            ),
            MetricSpec(
                name="recovery_trends",
                description="Post-charge-off recovery dollars and recovery rates over time.",
                min_tier=2,
                required_fields=_T0 + (F_RECOVERY_AMOUNT,),
                requires_panel=True,
                compute=compute_recovery_trends,
                checks=(
                    ThresholdCheck(f"{cc}.recoveries.min_recovery_rate_t12", "recovery_rate_t12", "min", "Recovery rate (T12 recoveries / T12 gross COs)"),
                ),
            ),
            MetricSpec(
                name="utilization_distribution",
                description=(
                    "Utilization distribution, high-utilization exposure, and total "
                    "open-to-buy at the latest month."
                ),
                min_tier=1,
                required_fields=_T0 + (F_CREDIT_LIMIT,),
                requires_panel=False,
                compute=compute_utilization_distribution,
                checks=(
                    ThresholdCheck(f"{cc}.utilization.max_portfolio_utilization", "portfolio_utilization", "max", "Portfolio (dollar-weighted) utilization"),
                    ThresholdCheck(f"{cc}.utilization.max_high_util_balance_share", "high_util_balance_share", "max", "Balance share on accounts >90% utilized"),
                ),
            ),
            MetricSpec(
                name="line_management",
                description=(
                    "Credit-line increase activity, exposure added, and subsequent "
                    "delinquency performance of increased lines."
                ),
                min_tier=2,
                required_fields=_T0 + (F_CREDIT_LIMIT, F_SCORE_BAND),
                requires_panel=True,
                compute=compute_line_management,
                checks=(
                    ThresholdCheck(f"{cc}.line_management.max_increase_share_below_prime", "increase_share_below_prime", "max", "Line-increase dollars to below-prime accounts"),
                    ThresholdCheck(f"{cc}.line_management.max_increases_gone_bad_rate", "increases_gone_bad_rate", "max", "Line increases 30+ DPD within 6 months"),
                ),
            ),
        )
