"""Point-in-time panel assembly: the IMPURE seam between the database + price
cache and the pure walk-forward :mod:`stock_helper.backtest.engine`.

This is the module most exposed to the two cardinal sins of a backtest, so both
are handled explicitly and commented at the point of enforcement:

- **LOOKAHEAD** — using information that was not knowable at the rebalance date.
  Guarded three ways: fundamentals are loaded strictly ``as_of=date`` (later
  filings, including restatements, are excluded by ``load_series``); the entry
  price is the last close ON OR BEFORE the date (a point-in-time
  ``MarketContext`` truncated to that date); and the forward return is only ever
  used as the *label* — it never feeds a signal value.

- **SURVIVORSHIP** — the free Stooq price source only carries names that still
  trade, so a company that was delisted (often after distress) simply has no
  future price. Such a name yields ``forward_return() is None`` and is EXCLUDED
  from the cross-section. That exclusion is not silent here: every dropped
  name-date is COUNTED (``dropped_no_price``) and DISCLOSED in the result
  caveats, because omitting failures inflates every backtest and hides exactly
  the distress the survivor set can't see.

Nothing in this module is a performance claim. It is an educational replay over
NON-CANONICAL, survivorship-biased data.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

import pandas as pd
from sqlmodel import Session, select

from stock_helper.backtest.engine import (
    BacktestResult,
    Panel,
    RebalanceObs,
    walk_forward,
)
from stock_helper.connectors.prices import fetch_daily_prices
from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger
from stock_helper.features.context import MarketContext, compute_market_context
from stock_helper.features.metrics import DerivedMetric, compute_derived_metrics
from stock_helper.normalization.facts import MetricSeries
from stock_helper.storage.models import Company, SecurityIdentifier
from stock_helper.storage.queries import load_series
from stock_helper.valuation.factors import compute_piotroski_f_score
from stock_helper.valuation.multiples import compute_enterprise_value, compute_multiples
from stock_helper.valuation.stats import mad, median, robust_zscore

log = get_logger(__name__)

# A signal function scores ONE company on POINT-IN-TIME data, oriented so that a
# HIGHER number is MORE attractive. It returns None whenever its inputs are
# missing or degenerate (never a fabricated number) — those names simply drop
# out of the cross-section rather than pollute the ranking.
SignalFn = Callable[
    [dict[str, MetricSeries], dict[str, DerivedMetric], MarketContext | None, str],
    float | None,
]


# --------------------------------------------------------------------------- #
# Signal functions (reuse existing calc cores; never recompute ratios by hand)
# --------------------------------------------------------------------------- #


def _multiple_value(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
    key: str,
) -> float | None:
    """One market multiple/yield from the pure multiples core, or None.

    Requires a (point-in-time) MarketContext; without a price the enterprise
    value and market cap are unknowable, so the yield is None (UNAVAILABLE),
    never guessed."""
    if market is None:
        return None
    ev = compute_enterprise_value(series, derived, market)
    mults = compute_multiples(series, derived, market, ev, bucket=bucket)
    m = mults.get(key)
    return m.value if (m is not None and m.value is not None) else None


def sig_earnings_yield(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
) -> float | None:
    """Earnings yield (EBIT / enterprise value). Higher = cheaper = attractive."""
    return _multiple_value(series, derived, market, bucket, "earnings_yield")


def sig_fcf_yield(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
) -> float | None:
    """Free-cash-flow yield (FCF / market cap). Higher = cheaper = attractive."""
    return _multiple_value(series, derived, market, bucket, "fcf_yield")


def sig_piotroski_f(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
) -> float | None:
    """Piotroski F-score (0-9). Higher = stronger fundamentals = attractive.

    Pure-fundamental (no price needed), so it is computable at any as-of date
    with two years of statements — which makes it the cleanest probe of the
    survivorship hole (a delisted name still scores, then drops for lack of a
    forward price)."""
    fr = compute_piotroski_f_score(series)
    return fr.value if (fr is not None and fr.value is not None) else None


def sig_value_composite(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
) -> float | None:
    """Mean of a few cheap-yield metrics, oriented higher = cheaper = attractive.

    The components (earnings yield = EBIT/EV, FCF yield = FCF/market cap) are
    deliberately both return-scaled yields, so a plain mean combines them on a
    comparable scale without a cross-section to standardize against — a
    single-name signal function has no peer set of its own. (Cross-sectional
    robust-z standardization of value metrics is exactly what
    ``screening.engine`` does across a universe; here the pure walk-forward
    scores signals by RANK, so a monotone within-name blend is what's needed.)
    Needs at least two present components, else None."""
    parts = [
        _multiple_value(series, derived, market, bucket, "earnings_yield"),
        _multiple_value(series, derived, market, bucket, "fcf_yield"),
    ]
    vals = [v for v in parts if v is not None]
    if len(vals) < 2:
        return None
    return sum(vals) / len(vals)


# Quality metrics whose HIGHER latest value (vs the company's own history) reads
# as stronger. All are pure-fundamental derived metrics carrying a multi-year
# history, so each can be robust-z'd against its own past — no price required.
_QUALITY_METRICS = ("roe", "operating_margin", "gross_margin", "ocf_to_net_income")
_MIN_HISTORY = 4  # median/MAD need a few points to define a scale (matches multiples._MIN_HISTORY)


def sig_quality_composite(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    bucket: str,
) -> float | None:
    """Mean robust-z of a few quality metrics vs the company's OWN history.

    For each quality metric with >= 4 historical points, standardize the latest
    value with a robust z-score (median / scaled MAD, from ``valuation.stats``)
    against that metric's own point-in-time history, then average the available
    z-scores. Higher = improving/strong quality relative to the company's track
    record = attractive. Needs at least two computable components, else None.
    Uses only ``derived`` histories (all as-of), so it is price-free and
    lookahead-free."""
    zs: list[float] = []
    for key in _QUALITY_METRICS:
        dm = derived.get(key)
        if dm is None or dm.latest is None:
            continue
        history = [v for _, v in dm.points]
        if len(history) < _MIN_HISTORY:
            continue
        z = robust_zscore(dm.latest, median(history), mad(history))
        if z is not None:
            zs.append(z)
    if len(zs) < 2:
        return None
    return sum(zs) / len(zs)


SIGNAL_FUNCTIONS: dict[str, SignalFn] = {
    "earnings_yield": sig_earnings_yield,
    "fcf_yield": sig_fcf_yield,
    "piotroski_f": sig_piotroski_f,
    "value_composite": sig_value_composite,
    "quality_composite": sig_quality_composite,
}


# --------------------------------------------------------------------------- #
# Forward-return label (the survivorship hole)
# --------------------------------------------------------------------------- #


def forward_return(
    prices: pd.DataFrame | None, entry_date: date, horizon_days: int
) -> float | None:
    """Simple close-to-close return: ENTER the first trading day STRICTLY AFTER
    ``entry_date`` (never the same day — that would trade on same-day-filed
    information), EXIT ``horizon_days`` trading sessions later.

    Returns None when the price frame is missing/empty, the entry close is
    unusable (<= 0), or the exit session does not exist (a delisted or
    short-history name). That None is the survivorship hole: the name is simply
    excluded, which :func:`build_panel` COUNTS as ``dropped_no_price`` and
    discloses. This is the LABEL only — it must never be fed into a signal."""
    if prices is None or prices.empty or "Close" not in prices.columns:
        return None
    frame = prices.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    session_dates = pd.to_datetime(frame["Date"]).dt.date
    future = frame[session_dates > entry_date].reset_index(drop=True)
    if future.empty:
        return None
    entry_close = float(future.loc[0, "Close"])
    if entry_close <= 0 or horizon_days >= len(future):
        return None
    exit_close = float(future.loc[horizon_days, "Close"])
    return exit_close / entry_close - 1.0


# --------------------------------------------------------------------------- #
# Point-in-time market context (entry price known by the rebalance date)
# --------------------------------------------------------------------------- #


def _point_in_time_market(
    prices: pd.DataFrame | None,
    series: dict[str, MetricSeries],
    as_of: date,
) -> MarketContext | None:
    """A MarketContext using only prices ON OR BEFORE ``as_of``.

    ``compute_market_context`` takes the LAST close of the frame as the price, so
    truncating to ``Date <= as_of`` makes that the last close knowable on the
    rebalance date (trailing momentum/volatility windows are likewise all past).
    Share count comes from the as-of ``series``. Returns None when no price is
    knowable by ``as_of`` (or price data is disabled)."""
    if prices is None or prices.empty or "Close" not in prices.columns:
        return None
    frame = prices.dropna(subset=["Close"]).copy()
    as_dates = pd.to_datetime(frame["Date"]).dt.date
    frame = frame[as_dates <= as_of]
    if frame.empty:
        return None
    return compute_market_context(frame, series)


# --------------------------------------------------------------------------- #
# Universe resolution
# --------------------------------------------------------------------------- #


def _resolve_universe(
    session: Session, tickers: list[str] | None
) -> list[tuple[Company, str]]:
    """(Company, ticker) pairs to score. ``tickers=None`` -> every company in the
    local DB that has a ticker; a list restricts to those tickers."""
    idents = session.exec(select(SecurityIdentifier)).all()
    if tickers is not None:
        wanted = {t.upper() for t in tickers}
        idents = [i for i in idents if i.ticker.upper() in wanted]
    out: list[tuple[Company, str]] = []
    seen: set[int] = set()
    for ident in idents:
        if ident.company_id in seen:
            continue
        company = session.get(Company, ident.company_id)
        if company is None:
            continue
        seen.add(ident.company_id)
        out.append((company, ident.ticker.upper()))
    return out


# --------------------------------------------------------------------------- #
# Panel assembly
# --------------------------------------------------------------------------- #


def build_panel(
    session: Session,
    *,
    signal_name: str,
    dates: list[date],
    horizon_days: int,
    settings: Settings | None = None,
    tickers: list[str] | None = None,
) -> tuple[Panel, dict]:
    """Assemble a walk-forward :data:`Panel` plus a survivorship-diagnostics dict.

    For each rebalance ``date`` and each company:

    1. ``load_series(as_of=date)`` — fundamentals STRICTLY as knowable that day
       (later filings and restatements excluded). [anti-lookahead]
    2. ``compute_derived_metrics`` on that point-in-time series.
    3. A point-in-time ``MarketContext`` whose price is the last close ON OR
       BEFORE ``date``. [anti-lookahead]
    4. The signal value on the above (never on a current-view series).
    5. ``forward_return`` from ``date`` — the LABEL, computed independently and
       never fed back into the signal. [anti-lookahead]

    A name is included only when its signal is computable AND a forward price
    exists. A name with a signal but NO forward price is dropped and counted in
    ``dropped_no_price`` (survivorship exposure). Diagnostics returned:
    ``{n_dates, names_per_date_avg, dropped_no_price, signal_name, horizon_days}``.
    """
    settings = settings or get_settings()
    signal_fn = SIGNAL_FUNCTIONS.get(signal_name)
    if signal_fn is None:
        raise ValueError(
            f"unknown signal {signal_name!r}; choices: {sorted(SIGNAL_FUNCTIONS)}"
        )

    universe = _resolve_universe(session, tickers)

    # Fetch each ticker's price frame once (cached CSV); reused across all dates.
    price_cache: dict[str, pd.DataFrame | None] = {}

    def prices_for(ticker: str) -> pd.DataFrame | None:
        if ticker not in price_cache:
            price_cache[ticker] = fetch_daily_prices(ticker, settings)
        return price_cache[ticker]

    panel: Panel = []
    dropped_no_price = 0
    names_per_date: list[int] = []

    for as_of in sorted(dates):
        signals: dict[str, float] = {}
        forward_returns_map: dict[str, float] = {}
        for company, ticker in universe:
            # [anti-lookahead] fundamentals strictly as-of the rebalance date.
            series = load_series(session, company, as_of=as_of)
            if not series:
                continue
            derived = compute_derived_metrics(series)
            prices = prices_for(ticker)
            # [anti-lookahead] entry price is the last close on/before as_of.
            market = _point_in_time_market(prices, series, as_of)

            signal_value = signal_fn(series, derived, market, company.industry_bucket)
            if signal_value is None:
                continue  # not computable -> excluded (NOT a survivorship drop)

            # [anti-lookahead] the forward return is the label; it enters the day
            # AFTER as_of and never influences signal_value above.
            fret = forward_return(prices, as_of, horizon_days)
            if fret is None:
                # Had a signal but no forward price: delisted / short-history.
                # Excluded AND counted — this is the survivorship exposure.
                dropped_no_price += 1
                continue

            signals[ticker] = float(signal_value)
            forward_returns_map[ticker] = float(fret)

        names_per_date.append(len(signals))
        if signals:
            panel.append(
                RebalanceObs(
                    as_of=as_of, signals=signals, forward_returns=forward_returns_map
                )
            )

    diagnostics = {
        "n_dates": len(panel),
        "names_per_date_avg": (
            sum(names_per_date) / len(names_per_date) if names_per_date else 0.0
        ),
        "dropped_no_price": dropped_no_price,
        "signal_name": signal_name,
        "horizon_days": horizon_days,
    }
    log.info(
        "panel signal=%s dates=%d names_avg=%.2f dropped_no_price=%d",
        signal_name,
        diagnostics["n_dates"],
        diagnostics["names_per_date_avg"],
        dropped_no_price,
    )
    return panel, diagnostics


def _rebalance_dates(start: date, end: date, step_days: int) -> list[date]:
    """Rebalance dates from ``start`` to ``end`` inclusive, every ``step_days``
    calendar days."""
    if step_days <= 0:
        raise ValueError("step_days must be positive")
    out: list[date] = []
    current = start
    while current <= end:
        out.append(current)
        current = current + timedelta(days=step_days)
    return out


def run_backtest(
    session: Session,
    *,
    signal_name: str,
    start: date,
    end: date,
    step_days: int,
    horizon_days: int,
    settings: Settings | None = None,
    n_trials: int = 1,
) -> BacktestResult:
    """End-to-end: generate rebalance dates, build the point-in-time panel, run
    the pure walk-forward engine, and MERGE the survivorship diagnostics into the
    result's caveats.

    ``n_trials`` feeds the engine's deflated-Sharpe multiple-testing penalty (set
    it to the number of signals/parameterizations you actually tried, so a lucky
    winner among many is discounted). The result is educational, survivorship-
    limited, and NOT a performance claim — the merged caveats say so explicitly."""
    settings = settings or get_settings()
    dates = _rebalance_dates(start, end, step_days)
    panel, diagnostics = build_panel(
        session,
        signal_name=signal_name,
        dates=dates,
        horizon_days=horizon_days,
        settings=settings,
    )
    result = walk_forward(panel, horizon_days=horizon_days, n_trials=n_trials)

    # --- Honesty is load-bearing: fold survivorship exposure into the caveats. --
    dropped = diagnostics["dropped_no_price"]
    kept = sum(len(obs.forward_returns) for obs in panel)
    total_name_dates = dropped + kept
    result.caveats.append(
        f"{dropped} of {total_name_dates} name-dates dropped for missing forward "
        f"price — survivorship exposure (delisted/short-history names are silently "
        f"absent from the free price source, which INFLATES results and hides distress)."
    )
    result.caveats.append(
        f"Educational point-in-time replay of signal {signal_name!r} over "
        f"{diagnostics['n_dates']} rebalance date(s), avg "
        f"{diagnostics['names_per_date_avg']:.1f} names/date; NOT a performance claim."
    )
    return result
