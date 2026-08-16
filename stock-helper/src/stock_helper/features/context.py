"""Optional signal context computed outside the core engine.

Three builders, each returning None when its inputs are unavailable (the
engine then reports the dependent signals as UNAVAILABLE with a hint):

- market:  momentum / volatility / valuation from the NON-CANONICAL price
  source. Gated by ENABLE_PRICE_DATA; every consumer repeats the caveat.
- peers:   percentile of this company's key metrics among same-bucket
  companies in the LOCAL database (only what you've fetched — labeled as such).
- risk_language: rule-based disclosure metrics over extracted risk-factor
  sections (see parsing/text_metrics.py).

None of this is used in point-in-time history replay — reconstructing "prices
as of" or "peers as of" honestly needs Phase 7 infrastructure, so historical
runs simply mark these signals unavailable rather than leak current data.
"""

import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from sqlmodel import Session, select

from stock_helper.connectors.prices import fetch_daily_prices
from stock_helper.core.config import Settings, get_settings
from stock_helper.features.metrics import DerivedMetric, compute_derived_metrics
from stock_helper.normalization.facts import MetricSeries
from stock_helper.parsing.text_metrics import RiskLanguageMetrics, compute_risk_language
from stock_helper.storage.models import Company, Filing, FilingSection
from stock_helper.storage.queries import load_series

TRADING_DAYS_PER_YEAR = 252


# --- Market context -------------------------------------------------------------

@dataclass
class MarketContext:
    """Price-derived context. NON-CANONICAL source; never a performance claim."""

    price: float
    price_date: date
    momentum_12_1: float | None  # 12-month return skipping the most recent month
    volatility_60d: float | None  # annualized stdev of daily returns, last 60 sessions
    market_cap: float | None  # price x shares (single basis; see shares/shares_source)
    pe: float | None  # market_cap / latest net income (None if NI <= 0)
    ps: float | None  # market_cap / latest revenue
    shares: float | None = None  # THE share count used everywhere downstream (EV, multiples)
    shares_source: str = ""  # "shares_outstanding" (point-in-time) or "diluted_shares" (wtd avg)
    source_label: str = "Stooq daily CSV (non-canonical price data)"


def _latest_share_count(series: dict[str, MetricSeries]) -> tuple[float | None, str]:
    """One share basis for the whole valuation stack: point-in-time shares
    outstanding when available (latest scalar), else weighted-avg diluted."""
    so = series.get("shares_outstanding")
    if so and so.latest.value > 0:
        return so.latest.value, "shares_outstanding"
    diluted = series.get("diluted_shares")
    if diluted and diluted.latest.value > 0:
        return diluted.latest.value, "diluted_shares"
    return None, ""


def compute_market_context(
    prices: pd.DataFrame, series: dict[str, MetricSeries]
) -> MarketContext | None:
    frame = prices.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    if frame.empty:
        return None
    closes = frame["Close"].astype(float)
    price = float(closes.iloc[-1])
    price_date = pd.to_datetime(frame["Date"].iloc[-1]).date()

    momentum = None
    if len(closes) > TRADING_DAYS_PER_YEAR:
        # Classic 12-1: t-252 → t-21, skipping the most recent month (short-term
        # reversal). Descriptive context only — nothing here is a prediction.
        start, end = float(closes.iloc[-TRADING_DAYS_PER_YEAR]), float(closes.iloc[-21])
        if start > 0:
            momentum = end / start - 1.0

    volatility = None
    if len(closes) > 61:
        daily = closes.pct_change().iloc[-60:]
        volatility = float(daily.std()) * math.sqrt(TRADING_DAYS_PER_YEAR)

    market_cap = pe = ps = None
    shares, shares_source = _latest_share_count(series)
    if shares:
        market_cap = price * shares
        ni = series.get("net_income")
        if ni and ni.latest.value > 0:
            pe = market_cap / ni.latest.value
        revenue = series.get("revenue")
        if revenue and revenue.latest.value > 0:
            ps = market_cap / revenue.latest.value

    return MarketContext(
        price=price, price_date=price_date, momentum_12_1=momentum,
        volatility_60d=volatility, market_cap=market_cap, pe=pe, ps=ps,
        shares=shares, shares_source=shares_source,
    )


def build_market_context(
    ticker: str, series: dict[str, MetricSeries], settings: Settings | None = None
) -> MarketContext | None:
    settings = settings or get_settings()
    if not settings.enable_price_data:
        return None
    prices = fetch_daily_prices(ticker, settings)
    if prices is None:
        return None
    return compute_market_context(prices, series)


# --- Peer context ----------------------------------------------------------------

PEER_METRICS = (
    "operating_margin", "gross_margin", "debt_to_assets", "accrual_proxy",
    "free_cash_flow", "revenue", "nim_proxy", "deposits",
)


@dataclass
class PeerContext:
    """Company vs same-bucket companies in the LOCAL database.

    This is not a market-wide peer universe — it is whoever has been fetched.
    n_peers is displayed everywhere so the tiny sample is never hidden."""

    bucket: str
    n_peers: int  # excluding the company itself
    peer_tickers: list[str]
    percentiles: dict[str, float] = field(default_factory=dict)  # metric -> 0..100


def percentile_rank(value: float, peer_values: list[float]) -> float:
    """Share of peer values <= value, in percent (ties count as <=)."""
    if not peer_values:
        return 50.0
    below_or_equal = sum(1 for v in peer_values if v <= value)
    return below_or_equal / len(peer_values) * 100


def build_peer_context(
    session: Session, company: Company, derived: dict[str, DerivedMetric]
) -> PeerContext | None:
    peers = session.exec(
        select(Company).where(
            Company.industry_bucket == company.industry_bucket,
            Company.id != company.id,
        )
    ).all()
    if not peers:
        return None
    from stock_helper.storage.models import SecurityIdentifier

    peer_derived: dict[str, dict[str, DerivedMetric]] = {}
    peer_tickers: list[str] = []
    for peer in peers:
        identifier = session.exec(
            select(SecurityIdentifier).where(SecurityIdentifier.company_id == peer.id)
        ).first()
        peer_tickers.append(identifier.ticker if identifier else f"CIK{peer.cik}")
        peer_derived[str(peer.id)] = compute_derived_metrics(load_series(session, peer))

    percentiles: dict[str, float] = {}
    for metric_key in PEER_METRICS:
        mine = derived.get(metric_key)
        if mine is None or mine.latest is None:
            continue
        peer_values = [
            d[metric_key].latest
            for d in peer_derived.values()
            if metric_key in d and d[metric_key].latest is not None
        ]
        if len(peer_values) < 2:  # a 1-peer percentile is noise, skip
            continue
        percentiles[metric_key] = percentile_rank(mine.latest, peer_values)

    return PeerContext(
        bucket=company.industry_bucket,
        n_peers=len(peers),
        peer_tickers=sorted(peer_tickers),
        percentiles=percentiles,
    )


# --- Risk-language context ---------------------------------------------------------

def build_risk_language_context(
    session: Session, company: Company
) -> RiskLanguageMetrics | None:
    """Risk-factor language metrics from the two most recent 10-Ks with
    extracted sections (needs `fetch-sec --with-documents`)."""
    filings = session.exec(
        select(Filing)
        .where(Filing.company_id == company.id, Filing.form == "10-K")
        .order_by(Filing.filed_date.desc())  # type: ignore[attr-defined]
        .limit(2)
    ).all()

    def risk_chunks(filing: Filing) -> list[FilingSection]:
        return session.exec(
            select(FilingSection)
            .where(
                FilingSection.filing_id == filing.id,
                FilingSection.section_name == "risk_factors",
            )
            .order_by(FilingSection.chunk_index)  # type: ignore[arg-type]
        ).all()

    current = risk_chunks(filings[0]) if filings else []
    prior = risk_chunks(filings[1]) if len(filings) > 1 else []
    return compute_risk_language(current, prior or None)


def build_all_extras(
    session: Session,
    company: Company,
    ticker: str,
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    settings: Settings | None = None,
) -> dict[str, object]:
    """Everything the current-view report/UI can feed the signal engine.
    Values are None when unavailable — the engine reports that honestly.

    Only ever called for the CURRENT view (``as_of is None``); point-in-time
    replay cannot honestly reconstruct prices/peers, so the caller skips it."""
    market = build_market_context(ticker, series, settings)
    # ``compute_valuation`` is imported lazily: valuation.compose imports this
    # module at top level, so a top-level import here would form a cycle. It
    # never raises (fundamental parts compute without a price; price-derived
    # pieces are simply omitted when ``market`` is None).
    from stock_helper.valuation.compose import compute_valuation

    return {
        "market": market,
        "peers": build_peer_context(session, company, derived),
        "risk_language": build_risk_language_context(session, company),
        "valuation": compute_valuation(
            session, company, ticker, series, derived, market, settings
        ),
    }
