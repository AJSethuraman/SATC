"""The v0.1 signal registry. Every signal is documented in SIGNAL_DEFINITIONS.md.

Evaluators are small pure functions over derived metrics. They return None when
there are not enough periods (engine reports INSUFFICIENT_DATA). Interpretations
use "evidence suggests" language on purpose — descriptive, never predictive.
"""

from stock_helper.core.format import arrow_series, money, pct, ratio, shares
from stock_helper.features.metrics import trend_direction, yoy_change
from stock_helper.industry.sic_buckets import BANKING, FINANCIAL_BUCKETS
from stock_helper.signals.base import (
    OK,
    SignalContext,
    SignalDef,
    SignalOutcome,
    metric_evidence,
)

_FINANCIALS = frozenset(FINANCIAL_BUCKETS)
_BANK_ONLY = frozenset({BANKING})


def _confidence_by_history(n_points: int) -> str:
    return "high" if n_points >= 3 else "medium"


def _trend_outcome(
    ctx: SignalContext,
    metric_key: str,
    formatter,
    *,
    falling_is_bad: bool = True,
    caveat: str = "",
    noun: str = "",
) -> SignalOutcome | None:
    metric = ctx.derived[metric_key]
    values = metric.last_n(3)
    if len(values) < 2:
        return None
    movement = trend_direction(values)
    if falling_is_bad:
        direction = movement
    else:  # raw movement up is bad (e.g. leverage rising)
        direction = {"improving": "deteriorating", "deteriorating": "improving"}.get(
            movement, movement
        )
    score = {"improving": 1, "deteriorating": -1}.get(direction, 0)
    noun = noun or metric.label.lower()
    phrases = {
        "improving": f"Evidence suggests {noun} has been improving over recent fiscal years.",
        "deteriorating": f"Evidence suggests {noun} has been deteriorating over recent fiscal years.",
        "stable": f"Evidence suggests {noun} has been broadly stable over recent fiscal years.",
        "mixed": f"{noun.capitalize()} has been mixed over recent fiscal years — no clear trend.",
    }
    return SignalOutcome(
        status=OK,
        value_text=arrow_series(values, formatter),
        numeric_value=values[-1],
        direction=direction,
        score=score,
        interpretation=phrases[direction],
        confidence=_confidence_by_history(len(metric.points)),
        caveat=caveat,
        evidence=[metric_evidence(metric)],
    )


# --- Growth ------------------------------------------------------------------

def _revenue_growth(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["revenue"]
    growth = yoy_change([v for _, v in metric.points])
    if growth is None:
        return None
    direction = "improving" if growth > 0.02 else "deteriorating" if growth < -0.02 else "stable"
    return SignalOutcome(
        value_text=pct(growth),
        numeric_value=growth,
        direction=direction,
        score={"improving": 1, "deteriorating": -1}.get(direction, 0),
        interpretation=(
            f"Evidence suggests revenue {'grew' if growth >= 0 else 'declined'} "
            f"{pct(abs(growth))} year over year in the latest fiscal year."
        ),
        confidence=_confidence_by_history(len(metric.points)),
        caveat="As-filed revenue; acquisitions/divestitures are not stripped out.",
        evidence=[metric_evidence(metric)],
    )


# --- Profitability -----------------------------------------------------------

def _operating_margin_trend(ctx: SignalContext) -> SignalOutcome | None:
    return _trend_outcome(
        ctx, "operating_margin", lambda v: pct(v),
        caveat="One-time items are not stripped; check MD&A before concluding.",
        noun="operating margin",
    )


def _gross_margin_trend(ctx: SignalContext) -> SignalOutcome | None:
    return _trend_outcome(
        ctx, "gross_margin", lambda v: pct(v),
        caveat="Some filers do not tag cost of revenue consistently across years.",
        noun="gross margin",
    )


# --- Cash flow / quality ------------------------------------------------------

def _fcf_trend(ctx: SignalContext) -> SignalOutcome | None:
    outcome = _trend_outcome(
        ctx, "free_cash_flow", money,
        caveat="FCF = OCF minus PP&E capex only; excludes acquisitions and is lumpy by nature.",
        noun="free cash flow",
    )
    if outcome and outcome.numeric_value is not None and outcome.numeric_value < 0:
        outcome.score = min(outcome.score or 0, -1)
        outcome.interpretation += " Latest-year free cash flow is negative."
    return outcome


def _ocf_vs_net_income(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["ocf_to_net_income"]
    value = metric.latest
    if value is None:
        return None
    unstable = abs(value) > 10
    if value >= 1.0:
        direction, score = "improving", 1
        reading = "operating cash flow fully covers reported net income — supportive of earnings quality"
    elif value >= 0.8:
        direction, score = "stable", 0
        reading = "operating cash flow is broadly in line with reported net income"
    else:
        direction, score = "deteriorating", -1
        reading = "operating cash flow lags reported net income — a soft earnings-quality flag"
    return SignalOutcome(
        value_text=ratio(value),
        numeric_value=value,
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading} (latest fiscal year).",
        confidence="low" if unstable else _confidence_by_history(len(metric.points)),
        caveat="Ratio is unstable when net income is near zero." if unstable
        else "Single-year snapshot; look at several years before concluding.",
        evidence=[metric_evidence(metric)],
    )


def _accrual_proxy(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["accrual_proxy"]
    value = metric.latest
    if value is None:
        return None
    if value <= 0:
        direction, score = "improving", 1
        reading = "cash earnings exceed accrual earnings (negative accruals)"
    elif value <= 0.05:
        direction, score = "stable", 0
        reading = "accruals are modest relative to assets"
    elif value <= 0.10:
        direction, score = "deteriorating", -1
        reading = "accruals are elevated relative to assets"
    else:
        direction, score = "deteriorating", -2
        reading = "accruals are high relative to assets — an earnings-quality flag"
    return SignalOutcome(
        value_text=pct(value),
        numeric_value=value,
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading}.",
        confidence="medium",
        caveat="Cash-flow-approach proxy only; a balance-sheet accrual measure is planned (Phase 3 v2).",
        evidence=[metric_evidence(metric)],
    )


# --- Leverage / liquidity -----------------------------------------------------

def _debt_to_assets(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["debt_to_assets"]
    values = metric.last_n(3)
    if not values:
        return None
    latest = values[-1]
    movement = trend_direction(values) if len(values) >= 2 else "stable"
    direction = {"improving": "deteriorating", "deteriorating": "improving"}.get(movement, movement)
    score = {"improving": 1, "deteriorating": -1}.get(direction, 0)
    if latest > 0.5:
        score = min(score, -1)
    return SignalOutcome(
        value_text=arrow_series(values, lambda v: pct(v)),
        numeric_value=latest,
        direction=direction,
        score=score,
        interpretation=(
            f"Total debt is {pct(latest)} of assets"
            + (", a comparatively high level" if latest > 0.5 else "")
            + (f"; the ratio has been {'falling' if direction == 'improving' else 'rising' if direction == 'deteriorating' else 'steady'}."
               if len(values) >= 2 else ".")
        ),
        confidence=_confidence_by_history(len(metric.points)),
        caveat="Tagged debt only; operating leases and off-balance-sheet items may be excluded.",
        evidence=[metric_evidence(metric)],
    )


def _interest_coverage(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["interest_coverage"]
    value = metric.latest
    if value is None:
        return None
    if value < 0:
        direction, score, reading = "deteriorating", -2, "operating income is negative — coverage is not meaningful and leverage risk is elevated"
    elif value < 2:
        direction, score, reading = "deteriorating", -2, "operating income covers interest less than 2x — a leverage flag"
    elif value <= 8:
        direction, score, reading = "stable", 0, f"operating income covers interest about {value:.1f}x"
    else:
        direction, score, reading = "improving", 1, f"operating income covers interest comfortably ({value:.1f}x)"
    return SignalOutcome(
        value_text=f"{value:.1f}x",
        numeric_value=value,
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading}.",
        confidence="medium",
        caveat="InterestExpense tagging is inconsistent across filers; treat the level as approximate.",
        evidence=[metric_evidence(metric)],
    )


def _current_ratio(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["current_ratio"]
    value = metric.latest
    if value is None:
        return None
    if value < 1.0:
        direction, score, reading = "deteriorating", -1, "current liabilities exceed current assets"
    elif value <= 1.5:
        direction, score, reading = "stable", 0, "short-term liquidity looks adequate"
    else:
        direction, score, reading = "improving", 1, "short-term liquidity looks comfortable"
    return SignalOutcome(
        value_text=ratio(value),
        numeric_value=value,
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading} (current ratio {value:.2f}).",
        confidence="medium",
        caveat="Meaningful only for filers with classified balance sheets.",
        evidence=[metric_evidence(metric)],
    )


def _cash_trend(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["cash"]
    values = metric.last_n(3)
    if len(values) < 2:
        return None
    outcome = _trend_outcome(ctx, "cash", money, noun="the cash balance",
                             caveat="Ignores short-term investments and undrawn credit facilities.")
    growth = yoy_change(values)
    if outcome and growth is not None and growth < -0.30:
        outcome.score = min(outcome.score or 0, -1)
        outcome.interpretation += f" Cash declined {pct(abs(growth))} in the latest year."
    return outcome


# --- Capital / dilution ---------------------------------------------------------

def _share_dilution(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["diluted_shares"]
    growth = yoy_change([v for _, v in metric.points])
    if growth is None:
        return None
    if growth > 0.02:
        direction, score, reading = "deteriorating", -1, f"diluted share count rose {pct(growth)} — shareholders were diluted"
    elif growth < -0.01:
        direction, score, reading = "improving", 1, f"diluted share count fell {pct(abs(growth))} — consistent with net buybacks"
    else:
        direction, score, reading = "stable", 0, "diluted share count was roughly flat"
    return SignalOutcome(
        value_text=arrow_series(metric.last_n(3), shares),
        numeric_value=growth,
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading} year over year.",
        confidence=_confidence_by_history(len(metric.points)),
        caveat="Weighted-average diluted shares as filed; splits appear as filed values.",
        evidence=[metric_evidence(metric)],
    )


def _buyback_activity(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["buybacks"]
    values = metric.last_n(3)
    if not values:
        return None
    latest = values[-1]
    active = latest > 0
    return SignalOutcome(
        value_text=arrow_series(values, money),
        numeric_value=latest,
        direction="improving" if active else "stable",
        score=1 if active else 0,
        interpretation=(
            f"Evidence suggests the company repurchased {money(latest)} of stock in the latest fiscal year."
            if active else "No share repurchases reported in the latest fiscal year."
        ),
        confidence="high",
        caveat="Gross repurchases; issuance (e.g. stock compensation) is not netted here — see the dilution signal.",
        evidence=[metric_evidence(metric)],
    )


# --- Banking-specific -----------------------------------------------------------

def _deposits_trend(ctx: SignalContext) -> SignalOutcome | None:
    return _trend_outcome(
        ctx, "deposits", money, noun="total deposits",
        caveat="Face XBRL deposits only; interest-bearing vs non-interest-bearing mix is not visible.",
    )


def _credit_loss_allowance(ctx: SignalContext) -> SignalOutcome | None:
    metric = ctx.derived["credit_loss_allowance"]
    values = metric.last_n(3)
    if not values:
        return None
    growth = yoy_change(values)
    if growth is not None and growth > 0.20:
        direction, score = "deteriorating", -1
        reading = f"the credit-loss allowance rose {pct(growth)} year over year — reserves are building"
    elif growth is not None and growth < -0.10:
        direction, score = "improving", 0
        reading = f"the credit-loss allowance fell {pct(abs(growth))} year over year — reserve releases"
    else:
        direction, score = "stable", 0
        reading = "the credit-loss allowance was broadly stable"
    return SignalOutcome(
        value_text=arrow_series(values, money),
        numeric_value=values[-1],
        direction=direction,
        score=score,
        interpretation=f"Evidence suggests {reading}.",
        confidence="medium",
        caveat="CECL adoption (~2020) and tag transitions hurt year-over-year comparability. "
        "Allowance level alone says nothing without loan growth context (Phase 4).",
        evidence=[metric_evidence(metric)],
    )


# --- Registry --------------------------------------------------------------------

REGISTRY: list[SignalDef] = [
    SignalDef(
        key="revenue_growth_yoy", name="Revenue growth (YoY)", category="Growth",
        description="Latest fiscal-year revenue vs prior year.",
        formula="revenue[t] / revenue[t-1] - 1",
        excluded_buckets=frozenset({BANKING}),
        required_metrics=("revenue",), evaluator=_revenue_growth,
    ),
    SignalDef(
        key="operating_margin_trend", name="Operating margin trend", category="Profitability",
        description="Direction of operating margin over up to 3 fiscal years.",
        formula="operating_income / revenue",
        excluded_buckets=_FINANCIALS,
        required_metrics=("operating_margin",), evaluator=_operating_margin_trend,
    ),
    SignalDef(
        key="gross_margin_trend", name="Gross margin trend", category="Profitability",
        description="Direction of gross margin over up to 3 fiscal years.",
        formula="(revenue - cost_of_revenue) / revenue",
        excluded_buckets=_FINANCIALS,
        required_metrics=("gross_margin",), evaluator=_gross_margin_trend,
    ),
    SignalDef(
        key="fcf_trend", name="Free cash flow trend", category="Cash flow",
        description="Direction of FCF (OCF - capex) over up to 3 fiscal years.",
        formula="operating_cash_flow - capex",
        excluded_buckets=_FINANCIALS,
        required_metrics=("free_cash_flow",), evaluator=_fcf_trend,
    ),
    SignalDef(
        key="ocf_vs_net_income", name="OCF vs net income", category="Quality",
        description="Does operating cash flow back reported earnings?",
        formula="operating_cash_flow / net_income",
        excluded_buckets=_FINANCIALS,
        required_metrics=("ocf_to_net_income",), evaluator=_ocf_vs_net_income,
    ),
    SignalDef(
        key="accrual_proxy", name="Accrual quality proxy", category="Quality",
        description="Accruals relative to assets (cash-flow approach).",
        formula="(net_income - operating_cash_flow) / total_assets",
        excluded_buckets=_FINANCIALS,
        required_metrics=("accrual_proxy",), evaluator=_accrual_proxy,
    ),
    SignalDef(
        key="debt_to_assets", name="Debt / assets", category="Leverage",
        description="Tagged debt as a share of total assets, level and direction.",
        formula="(long_term_debt + short_term_debt) / total_assets",
        excluded_buckets=_FINANCIALS,
        required_metrics=("debt_to_assets",), evaluator=_debt_to_assets,
    ),
    SignalDef(
        key="interest_coverage", name="Interest coverage", category="Leverage",
        description="Operating income over interest expense (latest year).",
        formula="operating_income / interest_expense",
        excluded_buckets=_FINANCIALS,
        required_metrics=("interest_coverage",), evaluator=_interest_coverage,
    ),
    SignalDef(
        key="current_ratio", name="Current ratio", category="Liquidity",
        description="Current assets over current liabilities (latest year).",
        formula="current_assets / current_liabilities",
        excluded_buckets=_FINANCIALS,
        required_metrics=("current_ratio",), evaluator=_current_ratio,
    ),
    SignalDef(
        key="share_dilution", name="Share count dilution", category="Quality",
        description="Year-over-year change in weighted-average diluted shares.",
        formula="diluted_shares[t] / diluted_shares[t-1] - 1",
        required_metrics=("diluted_shares",), evaluator=_share_dilution,
    ),
    SignalDef(
        key="buyback_activity", name="Buyback activity", category="Capital return",
        description="Reported share repurchases in recent fiscal years.",
        formula="PaymentsForRepurchaseOfCommonStock (as filed)",
        required_metrics=("buybacks",), evaluator=_buyback_activity,
    ),
    SignalDef(
        key="cash_trend", name="Cash balance trend", category="Liquidity",
        description="Direction of cash & equivalents over up to 3 fiscal years.",
        formula="CashAndCashEquivalents (as filed)",
        required_metrics=("cash",), evaluator=_cash_trend,
    ),
    SignalDef(
        key="deposits_trend", name="Deposits trend", category="Banking",
        description="Direction of total deposits over up to 3 fiscal years.",
        formula="Deposits (as filed)",
        applicable_buckets=_BANK_ONLY,
        required_metrics=("deposits",), evaluator=_deposits_trend,
    ),
    SignalDef(
        key="credit_loss_allowance", name="Credit-loss allowance", category="Banking",
        description="Level and change of the allowance for credit losses.",
        formula="FinancingReceivableAllowanceForCreditLosses (as filed)",
        applicable_buckets=_BANK_ONLY,
        required_metrics=("credit_loss_allowance",), evaluator=_credit_loss_allowance,
    ),
    # --- Declared placeholders (implemented later; shown honestly as such) ---
    SignalDef(
        key="valuation_placeholder", name="Valuation (P/E, EV/EBIT…)", category="Valuation",
        description="Valuation ratios need trustworthy price × share alignment.",
        implemented=False, placeholder_reason="Phase 5 — requires canonical price data.",
    ),
    SignalDef(
        key="momentum_placeholder", name="Market momentum (12-1)", category="Market",
        description="Momentum needs canonical price history.",
        implemented=False, placeholder_reason="Phase 5 — requires canonical price data.",
    ),
    SignalDef(
        key="disclosure_risk_language", name="Disclosure / risk language", category="Disclosure",
        description="Risk-factor novelty and MD&A tone change.",
        implemented=False, placeholder_reason="Phase 2/3 — requires robust filing text features.",
    ),
    SignalDef(
        key="nim_placeholder", name="Net interest margin (NIM)", category="Banking",
        description="Needs interest income/expense and average earning assets.",
        applicable_buckets=_BANK_ONLY,
        implemented=False, placeholder_reason="Phase 4 — bank metric library.",
    ),
    SignalDef(
        key="charge_offs_placeholder", name="Net charge-offs / NPLs", category="Banking",
        description="Charge-off and nonperforming-loan ratios.",
        applicable_buckets=_BANK_ONLY,
        implemented=False, placeholder_reason="Phase 4 — often table-only disclosure; needs filing-table parsing.",
    ),
    SignalDef(
        key="cet1_placeholder", name="CET1 ratio", category="Banking",
        description="Regulatory capital ratio.",
        applicable_buckets=_BANK_ONLY,
        implemented=False, placeholder_reason="Phase 4 — frequently not in face XBRL.",
    ),
    SignalDef(
        key="industry_relative_placeholder", name="Industry-relative percentiles", category="Context",
        description="Metrics vs sector distributions.",
        implemented=False, placeholder_reason="Phase 4 — needs a wider fetched universe.",
    ),
]
