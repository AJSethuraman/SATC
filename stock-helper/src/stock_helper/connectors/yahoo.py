"""Optional daily price connector (Yahoo Finance). NON-CANONICAL market data.

Yahoo's public chart JSON endpoint is free, needs no API key, and — unlike
Stooq's CSV — has no tight per-IP daily cap and much wider coverage, which makes
it the better default for a hundreds-of-names universe and for the backtest.

It is still NON-CANONICAL: no survivorship guarantee (delisted tickers are
absent), Yahoo can change or throttle the endpoint at will, and values are
adjusted closes (dividends/splits), not audited prices. Every price-derived
output stays labeled non-canonical, and any failure returns None so callers
degrade to intrinsic-only rather than fabricating a number.

The parser (:func:`parse_yahoo_chart`) is pure and unit-tested against a saved
fixture so its correctness does not depend on network access.
"""

import httpx
import pandas as pd

from stock_helper.core.logging import get_logger

log = get_logger(__name__)

# range=10y gives enough history for a multi-year walk-forward; interval=1d.
YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range}&interval=1d"
)

# Yahoo returns 401/429 to clients with no browser-like User-Agent.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def parse_yahoo_chart(payload: dict) -> pd.DataFrame | None:
    """Turn a Yahoo v8 chart JSON payload into a Date/OHLC/Close/Volume frame.

    ``Close`` is the **adjusted** close when Yahoo provides it (correct for
    splits/dividends, which is what beta and the backtest need); the latest
    adjusted close equals the raw close, so valuation's "current price" is
    unaffected. Rows with a null close are dropped. Returns None when the
    payload carries an error, has no result, or yields no usable rows.
    """
    if not isinstance(payload, dict):
        return None
    chart = payload.get("chart") or {}
    if chart.get("error"):
        return None
    results = chart.get("result") or []
    if not results:
        return None
    result = results[0]
    timestamps = result.get("timestamp") or []
    if not timestamps:
        return None
    indicators = result.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    adj = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    close = quote.get("close") or []
    # Prefer adjusted close; fall back to raw close where adjclose is missing.
    if adj is None:
        adj = close
    dates = pd.to_datetime(timestamps, unit="s").normalize()
    frame = pd.DataFrame(
        {
            "Date": dates,
            "Open": quote.get("open") or [None] * len(timestamps),
            "High": quote.get("high") or [None] * len(timestamps),
            "Low": quote.get("low") or [None] * len(timestamps),
            "Close": [a if a is not None else c for a, c in zip(adj, close, strict=False)],
            "Volume": quote.get("volume") or [None] * len(timestamps),
        }
    )
    frame = frame.dropna(subset=["Close"]).reset_index(drop=True)
    if frame.empty:
        return None
    return frame


def fetch_yahoo_daily(symbol: str, *, range_: str = "10y") -> pd.DataFrame | None:
    """Fetch a daily price frame for ``symbol`` from Yahoo, or None on any error.

    ``symbol`` is used as-is (e.g. ``AAPL``, ``BRK-B``, ``SPY``) — Yahoo's class-B
    convention already matches the SEC ticker convention this app stores.
    """
    url = YAHOO_CHART_URL.format(symbol=symbol.upper(), range=range_)
    try:
        response = httpx.get(url, timeout=20.0, follow_redirects=True, headers=_HEADERS)
        response.raise_for_status()
        frame = parse_yahoo_chart(response.json())
    except Exception as exc:  # any failure just means "no price from Yahoo"
        log.warning("yahoo price fetch failed ticker=%s err=%s", symbol, exc)
        return None
    if frame is None:
        log.warning("yahoo price data empty/unexpected ticker=%s", symbol)
    return frame
