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
    UNAVAILABLE,
    Evidence,
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


def _nim_proxy_trend(ctx: SignalContext) -> SignalOutcome | None:
    return _trend_outcome(
        ctx, "nim_proxy", lambda v: pct(v, 2), noun="the net-interest-margin proxy",
        caveat="Proxy: NII over average TOTAL assets (true NIM uses average earning "
        "assets, rarely in face XBRL). Level is understated; trend is the signal.",
    )


def _npl_trend(ctx: SignalContext) -> SignalOutcome | None:
    outcome = _trend_outcome(
        ctx, "nonperforming_loans", money, falling_is_bad=False,
        noun="nonaccrual loans",
        caveat="Tag transition at CECL adoption (~2020) hurts comparability; level "
        "needs loan-book context (Phase 4).",
    )
    return outcome


def _charge_offs_trend(ctx: SignalContext) -> SignalOutcome | None:
    return _trend_outcome(
        ctx, "charge_offs", money, falling_is_bad=False, noun="charge-offs",
        caveat="Gross vs net differs by tag; many filers disclose charge-offs only "
        "in credit-quality tables this version does not parse.",
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


# --- Context-based signals (market / peers / disclosure language) -----------------

_NONCANON = "Non-canonical price source (Stooq); context only, never a prediction."


def _valuation_context(ctx: SignalContext) -> SignalOutcome | None:
    market = ctx.extras["market"]
    parts = []
    if market.pe is not None:
        parts.append(f"P/E {market.pe:.1f}")
    if market.ps is not None:
        parts.append(f"P/S {market.ps:.1f}")
    if not parts:
        return None
    return SignalOutcome(
        value_text=" · ".join(parts),
        numeric_value=market.pe if market.pe is not None else market.ps,
        direction="stable",
        score=0,  # deliberately unscored: cheap/expensive needs peer context
        interpretation=(
            f"At {market.price:.2f} ({market.price_date}), trailing multiples are "
            f"{' and '.join(parts)}. Whether that is cheap or expensive requires "
            "peer/history context — reported without a score by design."
        ),
        confidence="low",
        caveat=_NONCANON + " Trailing fundamentals; shares are weighted-average diluted.",
        evidence=[Evidence(kind="url", reference="stooq.com",
                           description="Daily close (non-canonical) x as-filed fundamentals")],
    )


def _momentum_context(ctx: SignalContext) -> SignalOutcome | None:
    market = ctx.extras["market"]
    if market.momentum_12_1 is None:
        return None
    momentum = market.momentum_12_1
    direction = "improving" if momentum > 0.05 else "deteriorating" if momentum < -0.05 else "stable"
    vol_text = f"; 60-day annualized volatility {pct(market.volatility_60d, 0)}" \
        if market.volatility_60d is not None else ""
    return SignalOutcome(
        value_text=pct(momentum),
        numeric_value=momentum,
        direction=direction,
        score={"improving": 1, "deteriorating": -1}.get(direction, 0),
        interpretation=(
            f"12-1 month price momentum is {pct(momentum)}{vol_text}. Descriptive "
            "market context — momentum here is unvalidated for this universe."
        ),
        confidence="low",
        caveat=_NONCANON,
        evidence=[Evidence(kind="url", reference="stooq.com",
                           description="12-1 momentum from daily closes (non-canonical)")],
    )


def _industry_relative(ctx: SignalContext) -> SignalOutcome | None:
    peers = ctx.extras["peers"]
    if not peers.percentiles:
        return None
    readable = {
        "operating_margin": "operating margin", "gross_margin": "gross margin",
        "debt_to_assets": "debt/assets", "accrual_proxy": "accruals",
        "free_cash_flow": "FCF", "revenue": "revenue",
        "nim_proxy": "NIM proxy", "deposits": "deposits",
    }
    parts = [
        f"{readable.get(k, k)} p{v:.0f}" for k, v in sorted(peers.percentiles.items())
    ]
    return SignalOutcome(
        value_text=", ".join(parts),
        numeric_value=None,
        direction="stable",
        score=0,
        interpretation=(
            f"Percentiles vs the {peers.n_peers} same-bucket compan"
            f"{'y' if peers.n_peers == 1 else 'ies'} in your local database "
            f"({', '.join(peers.peer_tickers)}). This is your fetched universe, "
            "not the market — treat as rough orientation only."
        ),
        confidence="low",
        caveat="Local-universe percentiles; a market-wide peer mapping is Phase 4.",
        evidence=[Evidence(kind="fact", reference=", ".join(peers.peer_tickers),
                           description="Same-SIC-bucket companies in local DB")],
    )


def _disclosure_risk_language(ctx: SignalContext) -> SignalOutcome | None:
    metrics = ctx.extras["risk_language"]
    rates = metrics.rates_per_1000
    value_parts = [f"{k[:5]} {v:.1f}/1k" for k, v in sorted(rates.items())]
    direction, score = "stable", 0
    notes = []
    if metrics.novelty_vs_prior is not None:
        value_parts.append(f"novelty {metrics.novelty_vs_prior:.0%}")
        if metrics.novelty_vs_prior > 0.5:
            direction, score = "deteriorating", -1
            notes.append(
                f"about {metrics.novelty_vs_prior:.0%} of risk-factor language is new "
                "vs the prior 10-K — read what changed before concluding"
            )
        else:
            notes.append(
                f"risk-factor language is {1 - metrics.novelty_vs_prior:.0%} similar "
                "to the prior 10-K (largely boilerplate carryover)"
            )
        unc_delta = metrics.rate_delta("uncertainty")
        if unc_delta is not None and unc_delta > 1.0:
            direction, score = "deteriorating", min(score, -1)
            notes.append("uncertainty-word rate rose vs the prior 10-K")
    else:
        notes.append("no prior 10-K sections stored, so change metrics are unavailable")
    return SignalOutcome(
        value_text=" · ".join(value_parts),
        numeric_value=metrics.novelty_vs_prior,
        direction=direction,
        score=score,
        interpretation="Evidence suggests " + "; ".join(notes) + ".",
        confidence="low",
        caveat=(
            "Rule-based word rates over heuristically extracted sections, using a "
            "curated subset of finance word lists — directional at best. "
            f"Based on {metrics.word_count:,} words; chunks "
            f"{metrics.current_chunk_ids[0]}…"
        ),
        evidence=[Evidence(kind="section", reference=", ".join(metrics.current_chunk_ids[:3]),
                           description="Risk Factors chunks (current 10-K)")]
        + ([Evidence(kind="section", reference=", ".join(metrics.prior_chunk_ids[:3]),
                     description="Risk Factors chunks (prior 10-K)")]
           if metrics.prior_chunk_ids else []),
    )


# --- Valuation / quality / forensic signals (require the composed "valuation") --

# The composed ValuationResult is built once per current-view report (see
# features/context.build_all_extras) and passed through as extras["valuation"].
# required_extras=("valuation",) makes every signal below report UNAVAILABLE when
# it is absent — which is exactly the case in point-in-time history replay, where
# extras are not reconstructed. That keeps the fundamental-only screens
# (Piotroski/Altman/Beneish/Montier) consistent with the other extras-gated
# signals rather than leaking present-day context into a past as-of view.

_VAL_SCENARIO = ("Scenario estimate from explicit, editable DCF assumptions — "
                 "not a price target.")
_SCREEN_CAVEAT = ("Statistical/accounting SCREEN for research triage — NOT an "
                  "accusation of fraud, a verdict, or advice. Read the filings.")
_VAL_REPLAY_HINT = ("Built only for the current view; unavailable in point-in-time "
                    "history replay (prices/peers as-of cannot be reconstructed yet).")


def _valuation(ctx: SignalContext):
    return ctx.extras["valuation"]  # gated non-None by required_extras


def _factor(ctx: SignalContext, key: str):
    quality = _valuation(ctx).quality
    return quality.factors.get(key) if quality is not None else None


def _factor_evidence(fr) -> Evidence:
    return Evidence(
        kind="fact",
        reference=", ".join(fr.input_accessions[-3:]) if fr.input_accessions else "",
        description=f"{fr.label}: {fr.formula}",
    )


def _factor_unavailable(fr, label: str) -> SignalOutcome:
    if fr is not None and fr.reason:
        reason = fr.reason
    else:
        reason = f"{label} could not be computed from the mapped fundamentals."
    return SignalOutcome(status=UNAVAILABLE, interpretation=reason)


def _intrinsic_margin_of_safety(ctx: SignalContext) -> SignalOutcome | None:
    val = _valuation(ctx)
    mos = val.margin_of_safety
    if mos is None:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                "Margin of safety needs BOTH an intrinsic DCF value and a current "
                "price; one or both is unavailable (no price data, or the DCF was "
                "not computable for this filer)."
            ),
        )
    direction = "improving" if mos > 0.3 else "deteriorating" if mos < -0.3 else "stable"
    score = 1 if mos > 0.3 else -1 if mos < -0.3 else 0
    fv = val.fair_value_per_share
    side = "above" if mos >= 0 else "below"
    return SignalOutcome(
        value_text=pct(mos),
        numeric_value=mos,
        direction=direction,
        score=score,
        interpretation=(
            f"The DCF fair value ({money(fv)}/share) sits {pct(abs(mos))} {side} the "
            f"current price — margin of safety {pct(mos)}. A scenario, not a target."
        ),
        confidence="low",
        caveat=_VAL_SCENARIO,
        evidence=[Evidence(kind="fact", reference=val.engine_version,
                           description="Two-stage DCF vs non-canonical market price")],
    )


def _reverse_dcf_implied_growth(ctx: SignalContext) -> SignalOutcome | None:
    val = _valuation(ctx)
    ig = val.implied_growth
    if ig is None:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                "Reverse-DCF implied growth needs a current price and a positive FCF "
                "base; not available here (no price data or non-positive FCF)."
            ),
        )
    return SignalOutcome(
        value_text=pct(ig),
        numeric_value=ig,
        direction="stable",
        score=0,  # unscored by design: achievability is a judgment call
        interpretation=(
            f"At the current price the market is implying roughly {pct(ig)} annual "
            "free-cash-flow growth over the explicit stage. Whether that is "
            "achievable is a judgment call — reported without a score by design."
        ),
        confidence="low",
        caveat=_VAL_SCENARIO,
        evidence=[Evidence(kind="fact", reference=val.engine_version,
                           description="Reverse-DCF growth solved from current price")],
    )


def _relative_valuation(ctx: SignalContext) -> SignalOutcome | None:
    val = _valuation(ctx)
    prs = val.peer_relative
    scored = [(k, pr) for k, pr in prs.items()
              if getattr(pr, "upside_pct", None) is not None]
    if not scored:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                "Peer-relative valuation needs a current price and >=3 same-bucket "
                "peers sharing the same multiples in your local database; not "
                "available here."
            ),
        )
    upsides = [pr.upside_pct for _, pr in scored]
    mean_up = sum(upsides) / len(upsides)
    direction = "improving" if mean_up > 0.25 else "deteriorating" if mean_up < -0.25 else "stable"
    score = 1 if mean_up > 0.25 else -1 if mean_up < -0.25 else 0
    parts = ", ".join(f"{k} {pct(pr.upside_pct)}" for k, pr in sorted(scored))
    n_peers = max((pr.n_peers for _, pr in scored), default=0)
    return SignalOutcome(
        value_text=pct(mean_up),
        numeric_value=mean_up,
        direction=direction,
        score=score,
        interpretation=(
            f"Averaged across {len(scored)} peer-median multiples ({parts}), the "
            f"implied value is {pct(mean_up)} vs the current price. Local "
            f"fetched-universe peers only (n={n_peers}) — orientation, not a target."
        ),
        confidence="low",
        caveat="Peer set is whoever you have fetched in the same SIC bucket, not the market.",
        evidence=[Evidence(kind="fact", reference=val.engine_version,
                           description="Robust peer-median multiples over the local universe")],
    )


def _piotroski_f(ctx: SignalContext) -> SignalOutcome | None:
    fr = _factor(ctx, "piotroski_f")
    if fr is None or fr.status != OK or fr.value is None:
        return _factor_unavailable(fr, "Piotroski F-score")
    score9 = fr.value
    quality_word = "strong" if score9 >= 7 else "weak" if score9 <= 3 else "middling"
    direction = "improving" if score9 >= 7 else "deteriorating" if score9 <= 3 else "stable"
    band = 1 if score9 >= 7 else -1 if score9 <= 3 else 0
    return SignalOutcome(
        value_text=f"{score9:.0f}/9",
        numeric_value=score9,
        direction=direction,
        score=band,
        interpretation=(
            f"Piotroski F-score is {score9:.0f}/9 — {quality_word} fundamental strength "
            "on nine binary accounting tests (profitability, leverage, efficiency)."
        ),
        confidence="medium",
        caveat="; ".join(fr.caveats) or "Nine-test accounting screen; not predictive.",
        evidence=[_factor_evidence(fr)],
    )


def _altman_distress(ctx: SignalContext) -> SignalOutcome | None:
    fr = _factor(ctx, "altman_z")
    if fr is None or fr.status != OK or fr.value is None:
        return _factor_unavailable(fr, "Altman distress score")
    zone = fr.detail.get("zone", "")
    model = fr.detail.get("model", "")
    direction = {"safe": "improving", "grey": "stable",
                 "distress": "deteriorating"}.get(zone, "stable")
    score = {"safe": 1, "grey": 0, "distress": -1}.get(zone, 0)
    return SignalOutcome(
        value_text=f"{fr.value:.2f} ({zone})",
        numeric_value=fr.value,
        direction=direction,
        score=score,
        interpretation=(
            f"Altman {model} score is {fr.value:.2f}, in the '{zone}' zone. "
            "A distress SCREEN, not a bankruptcy prediction."
        ),
        confidence="medium",
        caveat=_SCREEN_CAVEAT + (" " + "; ".join(fr.caveats) if fr.caveats else ""),
        evidence=[_factor_evidence(fr)],
    )


def _beneish_manipulation(ctx: SignalContext) -> SignalOutcome | None:
    beneish = _valuation(ctx).beneish
    if beneish is None or beneish.m_score is None:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                "Beneish M-score needs two clean consecutive fiscal years of the full "
                "input set with non-degenerate denominators; not available for this filer."
            ),
        )
    m = beneish.m_score
    score = -1 if beneish.flag else 0
    direction = "deteriorating" if beneish.flag else "stable"
    tail = (
        ", above the -1.78 screen threshold — the accrual/growth profile RESEMBLES "
        "that of known manipulators (a screen, not a conclusion)."
        if beneish.flag else ", below the -1.78 screen threshold."
    )
    return SignalOutcome(
        value_text=f"{m:.2f}",
        numeric_value=m,
        direction=direction,
        score=score,
        interpretation=f"Beneish M-score is {m:.2f}{tail}",
        confidence="low",
        caveat=_SCREEN_CAVEAT + (" " + beneish.caveats[0] if beneish.caveats else ""),
        evidence=[Evidence(
            kind="fact",
            reference=", ".join(beneish.input_accessions[-3:]) if beneish.input_accessions else "",
            description="Beneish 8-factor M-score (two consecutive fiscal years)")],
    )


def _montier_c(ctx: SignalContext) -> SignalOutcome | None:
    fr = _factor(ctx, "montier_c")
    if fr is None or fr.status != OK or fr.value is None:
        # The current valuation engine does not compute a Montier C-score; the
        # signal is wired to light up automatically once a factor named
        # ``montier_c`` appears in the quality bundle.
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                "Montier C-score (six-flag earnings-manipulation checklist) is not "
                "produced by the current valuation engine — nothing to report yet."
            ),
        )
    c = fr.value
    score = -1 if c >= 4 else 0
    direction = "deteriorating" if c >= 4 else "stable"
    return SignalOutcome(
        value_text=f"{c:.0f}/6",
        numeric_value=c,
        direction=direction,
        score=score,
        interpretation=(
            f"Montier C-score is {c:.0f}/6 manipulation flags — a SCREEN, not a verdict."
        ),
        confidence="low",
        caveat=_SCREEN_CAVEAT,
        evidence=[_factor_evidence(fr)],
    )


def _distress_panel_agreement(ctx: SignalContext) -> SignalOutcome | None:
    val = _valuation(ctx)
    quality = val.quality
    panel: list[tuple[str, bool]] = []  # (name, flagged)

    alt = quality.factors.get("altman_z") if quality is not None else None
    if alt is not None and alt.status == OK and alt.value is not None:
        panel.append(("Altman", alt.detail.get("zone") == "distress"))
    # Ohlson O / Zmijewski light up automatically if a future engine adds them.
    for key, name in (("ohlson_o", "Ohlson O"), ("zmijewski", "Zmijewski")):
        fr = quality.factors.get(key) if quality is not None else None
        if fr is not None and fr.status == OK and fr.value is not None:
            flagged = fr.detail.get("zone") == "distress" or bool(fr.detail.get("flag"))
            panel.append((name, flagged))
    beneish = val.beneish
    if beneish is not None and beneish.m_score is not None:
        panel.append(("Beneish", bool(beneish.flag)))
    stress = val.stress
    if stress is not None:
        panel.append(("Stress-scan", stress.flag_count > 0))

    if not panel:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation="No distress or forensic screen could be computed for this filer.",
        )
    flagged_names = [name for name, hit in panel if hit]
    n, k = len(panel), len(flagged_names)
    names = ", ".join(name for name, _ in panel)
    score = -1 if (k > 0 and k * 2 >= n) else 0  # majority of the panel agrees
    direction = "deteriorating" if score < 0 else "stable"
    tail = f": {', '.join(flagged_names)}" if flagged_names else ""
    return SignalOutcome(
        value_text=f"{k}/{n} screens flag",
        numeric_value=float(k),
        direction=direction,
        score=score,
        interpretation=(
            f"{k} of {n} independent distress/forensic screens ({names}) are currently "
            f"raising a flag{tail}. Agreement across independent SCREENS is worth a "
            "closer read, but none is a verdict."
        ),
        confidence="low",
        caveat=_SCREEN_CAVEAT,
        evidence=[Evidence(kind="fact", reference=val.engine_version,
                           description="Panel of independent distress/forensic screens")],
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
    SignalDef(
        key="nim_proxy_trend", name="NIM proxy trend", category="Banking",
        description="Net interest income over average total assets (proxy), 3y direction.",
        formula="net_interest_income / avg(total_assets)",
        applicable_buckets=_BANK_ONLY,
        required_metrics=("nim_proxy",), evaluator=_nim_proxy_trend,
        unavailable_hint="NII tag (InterestIncomeExpenseNet) not found in this filer's XBRL.",
    ),
    SignalDef(
        key="npl_trend", name="Nonaccrual loans trend", category="Banking",
        description="Direction of nonaccrual/nonperforming loans.",
        formula="FinancingReceivableNonaccrualStatus (as filed)",
        applicable_buckets=_BANK_ONLY,
        required_metrics=("nonperforming_loans",), evaluator=_npl_trend,
        unavailable_hint="Often disclosed only in credit-quality tables, not face XBRL.",
    ),
    SignalDef(
        key="charge_offs_trend", name="Charge-offs trend", category="Banking",
        description="Direction of gross charge-offs.",
        formula="FinancingReceivableAllowanceForCreditLossesWriteOffs (as filed)",
        applicable_buckets=_BANK_ONLY,
        required_metrics=("charge_offs",), evaluator=_charge_offs_trend,
        unavailable_hint="Often disclosed only in credit-quality tables, not face XBRL.",
    ),
    # --- Context-based (market / peers / disclosure text) ---
    SignalDef(
        key="valuation_context", name="Valuation (trailing P/E, P/S)", category="Valuation",
        description="Trailing multiples from non-canonical prices. Unscored by design.",
        formula="price x diluted_shares / {net_income, revenue}",
        required_extras=("market",), evaluator=_valuation_context,
        unavailable_hint="Enable ENABLE_PRICE_DATA=true for non-canonical price context "
        "(also unavailable in point-in-time history replay).",
    ),
    SignalDef(
        key="momentum_12_1", name="Market momentum (12-1)", category="Market",
        description="12-month price return skipping the most recent month, plus volatility.",
        formula="close[t-21] / close[t-252] - 1",
        required_extras=("market",), evaluator=_momentum_context,
        unavailable_hint="Enable ENABLE_PRICE_DATA=true for non-canonical price context "
        "(also unavailable in point-in-time history replay).",
    ),
    SignalDef(
        key="disclosure_risk_language", name="Disclosure / risk language", category="Disclosure",
        description="Word-rate tone and year-over-year novelty of Risk Factors.",
        formula="curated word rates per 1000 words; 1 - shingle Jaccard vs prior 10-K",
        required_extras=("risk_language",), evaluator=_disclosure_risk_language,
        unavailable_hint="Run fetch-sec TICKER --with-documents to extract filing sections.",
    ),
    SignalDef(
        key="industry_relative_context", name="Industry-relative percentiles", category="Context",
        description="Key metrics vs same-bucket companies in the local database.",
        formula="percentile rank among locally fetched same-bucket companies",
        required_extras=("peers",), evaluator=_industry_relative,
        unavailable_hint="Fetch more same-industry tickers to build a local peer set.",
    ),
    # --- Valuation (composed DCF / multiples / peer-relative) ---
    SignalDef(
        key="intrinsic_margin_of_safety", name="Intrinsic margin of safety",
        category="Valuation",
        description="DCF fair value vs current price. >+30% supportive, <-30% a flag.",
        formula="(fair_value_per_share - price) / fair_value_per_share",
        excluded_buckets=_FINANCIALS,
        required_extras=("valuation",), evaluator=_intrinsic_margin_of_safety,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="reverse_dcf_implied_growth", name="Reverse-DCF implied growth",
        category="Valuation",
        description="Stage-1 FCF growth the current price already implies. Unscored by design.",
        formula="growth g s.t. DCF(g) == price x shares",
        required_extras=("valuation",), evaluator=_reverse_dcf_implied_growth,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="relative_valuation", name="Relative valuation (peer-median)",
        category="Valuation",
        description="Mean implied upside across peer-median multiples. Bands +-25%.",
        formula="mean over multiples of (peer_median_implied_price / price - 1)",
        required_extras=("valuation",), evaluator=_relative_valuation,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    # --- Quality / distress / forensic screens ---
    SignalDef(
        key="piotroski_f", name="Piotroski F-score", category="Quality",
        description="Nine binary fundamental-strength tests, 0-9. >=7 strong, <=3 weak.",
        formula="sum of 9 binary tests (profitability, leverage, efficiency)",
        excluded_buckets=_FINANCIALS,
        required_extras=("valuation",), evaluator=_piotroski_f,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="altman_distress", name="Altman distress score", category="Quality",
        description="Altman Z / Z'' distress score and zone (safe/grey/distress).",
        formula="Z (manufacturer, market-based) or Z'' (book-based) by SIC + data",
        excluded_buckets=_FINANCIALS,
        required_extras=("valuation",), evaluator=_altman_distress,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="beneish_manipulation", name="Beneish M-score (manipulation screen)",
        category="Forensic",
        description="Eight-factor earnings-manipulation SCREEN. M > -1.78 = resemblance flag.",
        formula="M = -4.84 + 0.920*DSRI + ... + 4.679*TATA - 0.327*LVGI",
        required_extras=("valuation",), evaluator=_beneish_manipulation,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="montier_c", name="Montier C-score (manipulation screen)",
        category="Forensic",
        description="Six-flag earnings-manipulation checklist SCREEN (when computed).",
        formula="count of 6 Montier manipulation flags",
        excluded_buckets=_FINANCIALS,
        required_extras=("valuation",), evaluator=_montier_c,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    SignalDef(
        key="distress_panel_agreement", name="Distress panel agreement",
        category="Forensic",
        description="How many independent distress/forensic screens currently flag.",
        formula="count of flagged screens among {Altman, Beneish, stress-scan, ...}",
        required_extras=("valuation",), evaluator=_distress_panel_agreement,
        unavailable_hint=_VAL_REPLAY_HINT,
    ),
    # --- Declared placeholders (implemented later; shown honestly as such) ---
    SignalDef(
        key="cet1_placeholder", name="CET1 ratio", category="Banking",
        description="Regulatory capital ratio.",
        applicable_buckets=_BANK_ONLY,
        implemented=False, placeholder_reason="Phase 4 — frequently not in face XBRL; "
        "needs filing-table parsing.",
    ),
]
