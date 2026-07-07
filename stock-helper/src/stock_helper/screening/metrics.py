"""Universe rows: the standardizable raw figures for one company, pulled from a
single ``compute_valuation`` result.

This module NEVER re-derives a ratio. It reads the composed ``ValuationResult``
and copies out the handful of already-computed, cross-sectionally comparable
figures the screener standardizes. Anything the valuation could not compute is
carried as ``None`` (never 0) so a missing input can never masquerade as a bad
(or good) score downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlmodel import Session, select

from stock_helper.core.logging import get_logger
from stock_helper.features.context import build_market_context
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.storage.models import Company, SecurityIdentifier
from stock_helper.storage.queries import load_series
from stock_helper.valuation import OK
from stock_helper.valuation.compose import compute_valuation
from stock_helper.valuation.types import ValuationResult

log = get_logger(__name__)

# The standardizable metric keys, in a stable order. Each maps to an
# already-computed figure on the ValuationResult (see ``_metrics_from_result``).
VALUE_METRICS = ("fair_value_gap", "earnings_yield", "fcf_yield", "ev_ebit", "p_b")
QUALITY_METRICS = ("piotroski_f", "gross_profitability", "roic", "roe")
DISTRESS_METRICS = ("altman_z", "beneish_m", "accruals")
STANDARDIZABLE = VALUE_METRICS + QUALITY_METRICS + DISTRESS_METRICS


@dataclass
class UniverseRow:
    """One company's standardizable inputs for the cross-sectional screener.

    ``metrics`` holds raw (un-standardized) figures keyed by the metric names in
    :data:`STANDARDIZABLE`; any figure the valuation could not compute is
    ``None`` (never 0). ``flags`` carries the qualitative screens that travel
    with the company (Beneish manipulation flag, Altman distress zone, distress
    model agreement, stress-scanner keys) so the engine can raise outlier flags
    without recomputing anything."""

    ticker: str
    company_id: int | None
    name: str
    bucket: str
    sic: str | None
    market_cap: float | None
    metrics: dict[str, float | None] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


def _factor_value(quality: Any, key: str) -> float | None:
    """Value of a QualityFactors factor, only when it computed cleanly (status
    OK). A NOT_APPLICABLE / UNAVAILABLE factor contributes ``None``."""
    if quality is None:
        return None
    fr = quality.factors.get(key)
    if fr is None or fr.status != OK or fr.value is None:
        return None
    return fr.value


def _roic(quality: Any) -> float | None:
    """ROIC from the Magic Formula factor's detail (EBIT / invested capital).
    ``None`` when the Magic Formula could not be computed (e.g. no EV)."""
    if quality is None:
        return None
    fr = quality.factors.get("magic_formula")
    if fr is None or fr.status != OK:
        return None
    roic = fr.detail.get("roic")
    return float(roic) if roic is not None else None


def _multiple_value(val: ValuationResult, key: str) -> float | None:
    m = val.multiples.get(key)
    return m.value if m is not None else None


def _metrics_from_result(val: ValuationResult) -> dict[str, float | None]:
    """Copy the standardizable figures out of a ValuationResult. No arithmetic
    happens here beyond selecting an already-computed field."""
    q = val.quality
    return {
        "fair_value_gap": val.margin_of_safety,  # (fair - price)/fair; None w/o price
        "earnings_yield": _multiple_value(val, "earnings_yield"),
        "fcf_yield": _multiple_value(val, "fcf_yield"),
        "ev_ebit": _multiple_value(val, "ev_ebit"),
        "p_b": _multiple_value(val, "p_b"),
        "piotroski_f": _factor_value(q, "piotroski_f"),
        "gross_profitability": _factor_value(q, "gross_profitability"),
        "roic": _roic(q),
        "roe": _factor_value(q, "roe"),
        "altman_z": _factor_value(q, "altman_z"),
        "beneish_m": val.beneish.m_score if val.beneish is not None else None,
        "accruals": _factor_value(q, "accruals_quality"),
    }


def _flags_from_result(val: ValuationResult) -> list[str]:
    """Qualitative screens that ride along with the company. Reuses the flags the
    valuation already raised and adds distress-model agreement from the quality
    panel (the corroboration signal, not any single score)."""
    flags = list(val.flags)  # incl. beneish_manipulation_flag, altman_distress, stress keys
    q = val.quality
    if q is not None and q.distress_panel.get("models_agree"):
        flags.append("distress_models_agree")
    return sorted(set(flags))


def _identifier_for(session: Session, company: Company) -> SecurityIdentifier | None:
    return session.exec(
        select(SecurityIdentifier).where(SecurityIdentifier.company_id == company.id)
    ).first()


def build_universe_row(
    session: Session,
    company: Company,
    *,
    settings=None,
    as_of: date | None = None,
) -> UniverseRow | None:
    """Assemble one UniverseRow for ``company`` by reusing the full valuation
    pipeline (load_series -> derived metrics -> market context -> compute_valuation).

    Returns ``None`` when the company has no identifier or no stored facts (there
    is nothing to standardize). Market context is skipped for point-in-time
    (``as_of``) views, mirroring the ``value`` command — the fundamental figures
    (Piotroski, Altman, Beneish, accruals, ROE) still compute without a price."""
    identifier = _identifier_for(session, company)
    if identifier is None:
        return None
    ticker = identifier.ticker.upper()

    series = load_series(session, company, as_of=as_of)
    if not series:
        return None
    derived = compute_derived_metrics(series)
    market = None if as_of else build_market_context(ticker, series, settings)
    try:
        val = compute_valuation(
            session, company, ticker, series, derived, market, settings, as_of
        )
    except Exception as exc:  # one bad name must not sink the whole screen
        log.debug("valuation failed ticker=%s err=%s", ticker, exc)
        return None

    market_cap = market.market_cap if market is not None else None
    return UniverseRow(
        ticker=ticker,
        company_id=company.id,
        name=company.name,
        bucket=company.industry_bucket,
        sic=company.sic,
        market_cap=market_cap,
        metrics=_metrics_from_result(val),
        flags=_flags_from_result(val),
    )


def build_universe_rows(
    session: Session,
    *,
    tickers: list[str] | None = None,
    settings=None,
    as_of: date | None = None,
) -> list[UniverseRow]:
    """Build a UniverseRow for every company with stored data (optionally
    filtered to ``tickers``). Companies that yield no row are skipped."""
    wanted = {t.upper() for t in tickers} if tickers else None
    rows: list[UniverseRow] = []
    for company in session.exec(select(Company)).all():
        if wanted is not None:
            identifier = _identifier_for(session, company)
            if identifier is None or identifier.ticker.upper() not in wanted:
                continue
        row = build_universe_row(session, company, settings=settings, as_of=as_of)
        if row is not None:
            rows.append(row)
    return rows
