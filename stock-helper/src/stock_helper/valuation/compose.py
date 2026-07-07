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

from stock_helper.core.logging import get_logger
from stock_helper.features.context import MarketContext, build_market_context
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import is_financial
from stock_helper.normalization.facts import MetricSeries
from stock_helper.storage.models import Company, SecurityIdentifier
from stock_helper.storage.queries import load_series
from stock_helper.valuation import VALUATION_VERSION
from stock_helper.valuation.dcf import reverse_dcf, run_valuation, sensitivity
from stock_helper.valuation.factors import compute_quality_factors
from stock_helper.valuation.forensics import (
    compute_beneish_m_score,
    compute_montier_c_score,
    compute_stress_report,
)
from stock_helper.valuation.multiples import (
    compute_enterprise_value,
    compute_multiples,
    peer_relative_valuation,
)
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
    assumptions = Assumptions()
    price = market.price if market else None
    price_date = market.price_date if market else None
    caveats: list[str] = []
    flags: list[str] = []

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
        fair_value_per_share=fair_value,
        margin_of_safety=mos,
        implied_growth=reverse.implied_growth if reverse else None,
        metric_set=quality.metric_set if quality else "",
        flags=sorted(set(flags)),
        caveats=caveats,
        engine_version=VALUATION_VERSION,
    )
