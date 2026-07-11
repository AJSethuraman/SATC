"""Impure orchestrator: assemble one ValuationResult for a company.

Calls the pure calc modules (dcf, multiples, factors, forensics) and the two
DB-backed pieces (peer-relative multiples over the local same-bucket universe).
Intrinsic DCF and the fundamental factor/forensic scores are computed even
when there is no price (point-in-time replay or price data off) — only the
price-dependent parts (EV, market multiples, margin of safety, reverse-DCF)
require a MarketContext. Research aid, not advice.
"""

from typing import Any

from sqlmodel import Session, select

from stock_helper.connectors.prices import fetch_daily_prices
from stock_helper.core.config import get_settings
from stock_helper.core.logging import get_logger
from stock_helper.features.context import MarketContext, build_market_context
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import is_financial
from stock_helper.normalization.facts import MetricSeries
from stock_helper.storage.models import Company, SecurityIdentifier
from stock_helper.storage.queries import load_series
from stock_helper.valuation import VALUATION_VERSION
from stock_helper.valuation.cost_of_capital import compute_cost_of_capital, estimate_beta
from stock_helper.valuation.dcf import reverse_dcf, run_valuation, sensitivity
from stock_helper.valuation.economic_profit import compute_economic_profit
from stock_helper.valuation.factors import compute_quality_factors
from stock_helper.valuation.forensics import (
    compute_beneish_m_score,
    compute_montier_c_score,
    compute_stress_report,
)
from stock_helper.valuation.monte_carlo import run_monte_carlo_from_dcf
from stock_helper.valuation.multiples import (
    compute_enterprise_value,
    compute_multiples,
    peer_relative_valuation,
)
from stock_helper.valuation.residual_income import run_residual_income
from stock_helper.valuation.types import Assumptions, ValuationResult

log = get_logger(__name__)

# Multiple key -> the company underlying figure peer-relative valuation needs.
# Equity multiples take a per-share figure; EV multiples take the aggregate.
_EV_MULTIPLE_KEYS = ("ev_ebit", "ev_ebitda", "ev_sales")


def _latest(series: dict[str, MetricSeries], key: str) -> float | None:
    s = series.get(key)
    return s.latest.value if s else None


def net_claims_senior_to_equity(series: dict[str, MetricSeries]) -> float:
    """Total debt + preferred + minority - cash. This (not just net debt) is what
    an EV-multiple-implied enterprise value must be reduced by to reach common
    equity — the reviewer's fix so peer-implied prices don't overstate equity for
    issuers with preferred/minority interests.

    total_debt is summed from raw debt components (it lives only in the derived
    layer, not the raw series passed here)."""
    total_debt = sum(
        _latest(series, k) or 0.0
        for k in ("long_term_debt", "short_term_debt", "short_term_borrowings")
    )
    cash = _latest(series, "cash") or 0.0
    preferred = _latest(series, "preferred_equity") or 0.0
    minority = _latest(series, "minority_interest") or 0.0
    return total_debt + preferred + minority - cash


def _per_share(series: dict[str, MetricSeries], key: str, shares: float | None) -> float | None:
    v = _latest(series, key)
    if v is None or not shares or shares <= 0:
        return None
    return v / shares


def _company_metrics_for_peers(
    series: dict[str, MetricSeries], shares: float | None, price: float | None
) -> dict[str, float]:
    """Underlying figure per multiple key: per-share for equity multiples,
    aggregate for EV multiples."""
    metrics: dict[str, float] = {}

    def put(key: str, value: float | None) -> None:
        if value is not None:
            metrics[key] = value

    put("pe", _per_share(series, "net_income", shares))
    put("p_b", _per_share(series, "equity", shares))
    put("p_tbv", _per_share(series, "tangible_book", shares))
    put("p_fcf", _per_share(series, "free_cash_flow", shares))
    put("ev_ebit", _latest(series, "operating_income"))
    put("ev_ebitda", _latest(series, "ebitda"))
    put("ev_sales", _latest(series, "revenue"))
    if price is not None:
        metrics["price"] = price
    return metrics


def _gather_peer_multiples(
    session: Session,
    company: Company,
    settings,
) -> dict[str, list[float]]:
    """Observed multiple values across same-bucket companies in the LOCAL DB.
    Best-effort: peers without price/data simply contribute nothing."""
    peers = session.exec(
        select(Company).where(
            Company.industry_bucket == company.industry_bucket,
            Company.id != company.id,
        )
    ).all()
    by_key: dict[str, list[float]] = {}
    for peer in peers:
        identifier = session.exec(
            select(SecurityIdentifier).where(SecurityIdentifier.company_id == peer.id)
        ).first()
        if identifier is None:
            continue
        p_series = load_series(session, peer)
        p_derived = compute_derived_metrics(p_series)
        p_market = build_market_context(identifier.ticker, p_series, settings)
        if p_market is None:
            continue
        ev = compute_enterprise_value(p_series, p_derived, p_market)
        mults = compute_multiples(p_series, p_derived, p_market, ev, bucket=peer.industry_bucket)
        for key, m in mults.items():
            if m.value is not None and m.value > 0:
                by_key.setdefault(key, []).append(m.value)
    return by_key


def _risk_free_rate(settings) -> float:
    """Risk-free rate from FRED (10-yr Treasury) when a key is configured, else
    the documented config fallback — the CAPM discount rate is never blocked on
    a missing key, only made more approximate (with a caveat)."""
    try:
        from stock_helper.connectors.fred import FredClient

        rf = FredClient(settings).risk_free_rate()
        if rf is not None:
            return rf
    except Exception as exc:
        log.debug("FRED risk-free fetch failed err=%s", exc)
    return settings.risk_free_default


def _estimate_beta(ticker: str, settings) -> float | None:
    """Beta from an OLS regression of the stock's daily returns on the market
    (SPY, non-canonical). None on any failure -> CAPM falls back to beta 1.0."""
    try:
        import pandas as pd

        stock = fetch_daily_prices(ticker, settings)
        index = fetch_daily_prices("SPY", settings)
        if stock is None or index is None:
            return None
        s = stock[["Date", "Close"]].rename(columns={"Close": "s"})
        m = index[["Date", "Close"]].rename(columns={"Close": "m"})
        merged = pd.merge(s, m, on="Date").sort_values("Date")
        merged["sr"] = merged["s"].pct_change()
        merged["mr"] = merged["m"].pct_change()
        merged = merged.dropna()
        if len(merged) < 60:
            return None
        return estimate_beta(merged["sr"].tolist(), merged["mr"].tolist())
    except Exception as exc:
        log.debug("beta estimation failed ticker=%s err=%s", ticker, exc)
        return None


def compute_valuation(
    session: Session,
    company: Company,
    ticker: str,
    series: dict[str, MetricSeries],
    derived: dict,  # metric key -> DerivedMetric
    market: MarketContext | None,
    settings=None,
    as_of=None,
) -> ValuationResult:
    """Full valuation packet for one company. Never returns None: fundamental
    (intrinsic + factors + forensics) results compute without a price; only
    price-derived pieces are omitted when ``market`` is None."""
    bucket = company.industry_bucket
    price = market.price if market else None
    price_date = market.price_date if market else None
    caveats: list[str] = []
    flags: list[str] = []

    # --- cost of capital: replace the flat-9% discount rate with a defensible
    # CAPM cost of equity (risk-free from FRED or a config fallback, beta from
    # the price series when available, an explicit ERP assumption). The DCF then
    # discounts at Ke; the assumptions are all carried for the UI to show. -----
    settings = settings or get_settings()
    risk_free = _risk_free_rate(settings)
    beta = _estimate_beta(ticker, settings) if market else None
    coc = compute_cost_of_capital(
        series, derived, market,
        risk_free=risk_free, beta=beta, erp=settings.equity_risk_premium,
    )
    # Use Ke as the discount rate, but never let it fall to/under terminal growth
    # (that would make the perpetuity blow up); keep a floor above it.
    ke = coc.ke
    base_assumptions = Assumptions()
    discount = max(ke, base_assumptions.terminal_growth + 0.02)
    assumptions = Assumptions(discount_rate=discount)

    # --- intrinsic (works without price; shares from series if no market) ------
    dcf = run_valuation(series, derived, bucket, market, assumptions)
    reverse = reverse_dcf(series, derived, bucket, market, assumptions) if market else None

    sens = None
    if dcf.status == "OK" and dcf.base_fcf is not None and not is_financial(bucket):
        base_inputs = {
            "fcf_0": dcf.base_fcf,
            "stage1_growth": dcf.stage1_growth if dcf.stage1_growth is not None else 0.05,
            "stage1_years": dcf.stage1_years or assumptions.stage1_years,
            "discount_rate": dcf.discount_rate or assumptions.discount_rate,
            "terminal_growth": dcf.terminal_growth or assumptions.terminal_growth,
            "shares": dcf.shares,
            "net_debt": dcf.net_debt,
            "fcf_basis": dcf.fcf_basis,
        }
        try:
            sens = sensitivity(base_inputs)
        except Exception as exc:  # sensitivity is a nicety, never fatal
            log.debug("sensitivity failed ticker=%s err=%s", ticker, exc)

    # --- relative (needs price) -----------------------------------------------
    ev = compute_enterprise_value(series, derived, market) if market else None
    multiples = compute_multiples(series, derived, market, ev, bucket=bucket) if market else {}

    peer_relative: dict[str, Any] = {}
    if market and multiples:
        shares = market.shares
        try:
            peer_multiples = _gather_peer_multiples(session, company, settings)
            if peer_multiples:
                peer_relative = peer_relative_valuation(
                    multiples,
                    peer_multiples,
                    company_metrics=_company_metrics_for_peers(series, shares, price),
                    net_debt=net_claims_senior_to_equity(series),
                    shares=shares,
                )
        except Exception as exc:
            log.debug("peer-relative failed ticker=%s err=%s", ticker, exc)

    # --- quality + forensics (fundamentals only) ------------------------------
    quality = compute_quality_factors(series, derived, bucket, company.sic, market, ev)
    beneish = compute_beneish_m_score(series)
    stress = compute_stress_report(series, derived, market)
    # Bridge: Montier C-Score lives in the forensics module; surface it as a
    # quality factor so the montier_c signal and the report render it (the two
    # were built in parallel and didn't share this key).
    montier = compute_montier_c_score(series, derived)
    if quality is not None and montier is not None:
        quality.factors["montier_c"] = montier

    # --- residual income (book-anchored; works where DCF is weak / for banks) --
    residual = run_residual_income(series, derived, market, cost_of_equity=ke, bucket=bucket)

    # --- economic profit (ROIC - WACC): does the company create value? ---------
    magic = quality.factors.get("magic_formula") if quality else None
    roic = magic.detail.get("roic") if magic and getattr(magic, "detail", None) else None
    economic_profit = compute_economic_profit(roic, coc.wacc)

    # --- Monte Carlo: uncertainty fan around the DCF (input uncertainty only) --
    monte_carlo = None
    if dcf.status == "OK" and not is_financial(bucket):
        monte_carlo = run_monte_carlo_from_dcf(dcf, derived, price=price)

    # --- headline + flags ------------------------------------------------------
    fair_value = dcf.fair_value_per_share
    mos = dcf.margin_of_safety
    if beneish and beneish.flag:
        flags.append("beneish_manipulation_flag")
    for key, _reason, _value in (stress.stress_flags if stress else []):
        flags.append(key)
    altman = quality.factors.get("altman_z") if quality else None
    if altman and getattr(altman, "detail", None) and altman.detail.get("zone") == "distress":
        flags.append("altman_distress")

    caveats.append(
        "Valuations are scenario estimates from explicit assumptions, not price "
        "targets. Forensic/stress flags are research screens, never accusations."
    )
    if market:
        caveats.append(f"Price-derived figures use {market.source_label}.")

    return ValuationResult(
        ticker=ticker,
        bucket=bucket,
        as_of=as_of,
        price=price,
        price_date=price_date,
        dcf=dcf,
        reverse=reverse,
        sensitivity=sens,
        enterprise_value=ev,
        multiples=multiples,
        peer_relative=peer_relative,
        self_history={},  # historical per-fiscal-year price join deferred (see FE2)
        quality=quality,
        beneish=beneish,
        stress=stress,
        cost_of_capital=coc,
        residual_income=residual,
        economic_profit=economic_profit,
        monte_carlo=monte_carlo,
        fair_value_per_share=fair_value,
        margin_of_safety=mos,
        implied_growth=reverse.implied_growth if reverse else None,
        metric_set=quality.metric_set if quality else "",
        flags=sorted(set(flags)),
        caveats=caveats,
        engine_version=VALUATION_VERSION,
    )
