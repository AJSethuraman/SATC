"""Point-in-time signal history: replay the scorecard at past dates.

For each as-of date (by default, the day each 10-K/10-Q was filed — the moments
new fundamental information arrived), rebuild the canonical series as it was
knowable then, run the signal engine, and persist SignalHistory rows.

Outcome labels (ForwardReturn) are optional and EXPLORATORY: they use the
non-canonical price source (Stooq), ignore trading costs, and carry no
survivorship guarantees. They exist so signal behavior can be *inspected*
against subsequent price moves — they are not a backtest and support no
performance claim. Real validation (walk-forward, cost model, multiple-testing
controls) is Phase 7 — see ROADMAP.md.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pandas as pd
from sqlmodel import Session, select

from stock_helper.connectors.prices import fetch_daily_prices
from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.signals.base import SIGNALS_VERSION
from stock_helper.signals.engine import EvaluatedSignal, evaluate_signals
from stock_helper.storage.models import Company, Filing, ForwardReturn, SignalHistory
from stock_helper.storage.queries import find_company, load_series

log = get_logger(__name__)

DEFAULT_HORIZONS = (20, 60, 120)  # trading days

OUTCOME_CAVEAT = (
    "Forward returns are exploratory: non-canonical prices (Stooq), no cost model, "
    "no survivorship guarantees. Not a backtest; no performance claim."
)


@dataclass
class HistoryPoint:
    as_of: date
    signals: list[EvaluatedSignal]
    outcomes: dict[int, "OutcomeLabel"] = field(default_factory=dict)


@dataclass(frozen=True)
class OutcomeLabel:
    horizon_days: int
    entry_date: date
    exit_date: date
    ret: float  # simple return over the horizon


def default_history_dates(
    session: Session,
    company: Company,
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    """As-of dates where fundamental information changed: the filed dates of
    stored 10-K/10-Q filings (facts filed that day count as knowable that
    evening — decisions simulated off them must use the *next* session, which
    is exactly how forward-return entry dates are computed)."""
    query = select(Filing.filed_date).where(
        Filing.company_id == company.id,
        Filing.form.in_(["10-K", "10-Q"]),  # type: ignore[attr-defined]
    )
    dates = sorted({d for d in session.exec(query).all() if d is not None})
    if start is not None:
        dates = [d for d in dates if d >= start]
    if end is not None:
        dates = [d for d in dates if d <= end]
    return dates


def build_signal_history(
    session: Session,
    ticker: str,
    start: date | None = None,
    end: date | None = None,
    settings: Settings | None = None,
    with_outcomes: bool = False,
) -> list[HistoryPoint]:
    """Replay signals at each history date and persist SignalHistory rows.

    Re-running replaces this ticker's previous history (engine may have
    changed), keeping the table idempotent per (ticker, engine run).
    """
    settings = settings or get_settings()
    ticker = ticker.upper()
    company = find_company(session, ticker)
    dates = default_history_dates(session, company, start, end)
    now = datetime.now(UTC)

    for old in session.exec(
        select(SignalHistory).where(SignalHistory.company_id == company.id)
    ).all():
        session.delete(old)

    points: list[HistoryPoint] = []
    for as_of in dates:
        series = load_series(session, company, as_of=as_of)
        derived = compute_derived_metrics(series)
        signals = evaluate_signals(company.industry_bucket, derived)
        points.append(HistoryPoint(as_of=as_of, signals=signals))
        for evaluated in signals:
            outcome = evaluated.outcome
            session.add(
                SignalHistory(
                    company_id=company.id,
                    ticker=ticker,
                    as_of_date=as_of,
                    signal_key=evaluated.definition.key,
                    category=evaluated.definition.category,
                    status=outcome.status,
                    direction=outcome.direction,
                    score=outcome.score,
                    numeric_value=outcome.numeric_value,
                    value_text=outcome.value_text,
                    confidence=outcome.confidence,
                    engine_version=SIGNALS_VERSION,
                    created_at=now,
                )
            )

    if with_outcomes:
        _attach_outcomes(session, company, ticker, points, settings, now)

    session.commit()
    log.info("signal history ticker=%s dates=%d outcomes=%s", ticker, len(points), with_outcomes)
    return points


def forward_returns(
    prices: pd.DataFrame,
    as_of: date,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> dict[int, OutcomeLabel]:
    """Simple close-to-close returns starting the first trading day AFTER as_of.

    Entering at the next session (not the as-of day itself) avoids the
    lookahead of trading on information the same day it was filed. Horizons
    with insufficient future data are omitted, never extrapolated.
    """
    frame = prices.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    dates = pd.to_datetime(frame["Date"]).dt.date
    future = frame[dates > as_of].reset_index(drop=True)
    if future.empty:
        return {}
    entry_close = float(future.loc[0, "Close"])
    entry_date = pd.to_datetime(future.loc[0, "Date"]).date()
    if entry_close == 0:
        return {}
    out: dict[int, OutcomeLabel] = {}
    for horizon in horizons:
        if horizon >= len(future):
            continue
        exit_close = float(future.loc[horizon, "Close"])
        out[horizon] = OutcomeLabel(
            horizon_days=horizon,
            entry_date=entry_date,
            exit_date=pd.to_datetime(future.loc[horizon, "Date"]).date(),
            ret=exit_close / entry_close - 1.0,
        )
    return out


def _attach_outcomes(
    session: Session,
    company: Company,
    ticker: str,
    points: list[HistoryPoint],
    settings: Settings,
    now: datetime,
) -> None:
    prices = fetch_daily_prices(ticker, settings)
    if prices is None:
        log.warning(
            "outcomes requested but price data unavailable ticker=%s "
            "(is ENABLE_PRICE_DATA=true?)", ticker,
        )
        return
    for old in session.exec(
        select(ForwardReturn).where(ForwardReturn.company_id == company.id)
    ).all():
        session.delete(old)
    for point in points:
        labels = forward_returns(prices, point.as_of)
        point.outcomes = labels
        for label in labels.values():
            session.add(
                ForwardReturn(
                    company_id=company.id,
                    ticker=ticker,
                    as_of_date=point.as_of,
                    horizon_days=label.horizon_days,
                    entry_date=label.entry_date,
                    exit_date=label.exit_date,
                    ret=label.ret,
                    retrieved_at=now,
                )
            )
