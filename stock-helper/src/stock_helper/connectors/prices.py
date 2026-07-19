"""Optional daily price connector. NON-CANONICAL market data.

Two free, keyless sources: **Yahoo Finance** (default — no tight daily cap, wide
coverage, best for a large universe + backtest) and **Stooq** (fallback). Prices
are used for market multiples, margin of safety, beta, and the backtest; they are
always labeled "non-canonical" and carry no survivorship or corporate-action
guarantee. Disabled unless ENABLE_PRICE_DATA=true. Any failure returns None so
callers degrade to intrinsic-only rather than fabricating a number.

Source order is controlled by ``settings.price_source``:
``auto`` (Yahoo → Stooq, default), ``yahoo``, or ``stooq``.
"""

import io
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd

from stock_helper.connectors.yahoo import fetch_yahoo_daily
from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger

log = get_logger(__name__)

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
PRICE_SOURCE_LABEL = "Yahoo Finance / Stooq daily (non-canonical price data)"
_CACHE_TTL = timedelta(hours=24)

# Stooq's CSV endpoint returns 404 (an HTML stub) to clients that send no
# browser-like User-Agent, so httpx's default "python-httpx/..." is rejected.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


def _fetch_stooq(ticker: str) -> pd.DataFrame | None:
    """Fetch a daily frame from Stooq's CSV endpoint, or None on any error."""
    url = STOOQ_URL.format(symbol=ticker.lower())
    try:
        response = httpx.get(url, timeout=20.0, follow_redirects=True, headers=_HEADERS)
        response.raise_for_status()
        text = response.text
        # Stooq answers HTTP 200 with a plain-text "No data" / HTML stub when a
        # symbol is unknown or the per-IP daily cap is hit; that has no "Date"
        # header, so guard before handing it to the parser.
        if not text.lstrip().lower().startswith("date"):
            log.warning("stooq price unavailable ticker=%s (%s)",
                        ticker, text.strip()[:80])
            return None
        frame = pd.read_csv(io.StringIO(text), parse_dates=["Date"])
    except Exception as exc:
        log.warning("stooq price fetch failed ticker=%s err=%s", ticker, exc)
        return None
    if "Close" not in frame.columns or frame.empty:
        return None
    return frame


def _sources_for(settings: Settings):
    """Ordered list of (name, fetch_fn) price sources per settings.price_source."""
    src = (getattr(settings, "price_source", "auto") or "auto").lower()
    yahoo = ("yahoo", fetch_yahoo_daily)
    stooq = ("stooq", _fetch_stooq)
    if src == "yahoo":
        return [yahoo]
    if src == "stooq":
        return [stooq]
    return [yahoo, stooq]  # auto


def fetch_daily_prices(ticker: str, settings: Settings | None = None) -> pd.DataFrame | None:
    """Return a Date/Close (+OHLCV) DataFrame, or None if disabled/unavailable.

    Tries each configured source in order (Yahoo then Stooq by default) and
    caches the first success as CSV for ``_CACHE_TTL``. Column shape is stable
    across sources: at minimum ``Date`` and ``Close``, which every consumer uses.
    """
    settings = settings or get_settings()
    if not settings.enable_price_data:
        return None
    cache = settings.price_cache_dir / f"{ticker.lower()}.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        age = datetime.now(UTC).timestamp() - cache.stat().st_mtime
        if age < _CACHE_TTL.total_seconds():
            return pd.read_csv(cache, parse_dates=["Date"])

    for name, fetch in _sources_for(settings):
        frame = fetch(ticker)
        if frame is not None and "Close" in frame.columns and not frame.empty:
            frame.to_csv(cache, index=False)
            log.info("price fetched ticker=%s source=%s rows=%d", ticker, name, len(frame))
            return frame
    log.warning("price data unavailable ticker=%s (all sources failed)", ticker)
    return None
