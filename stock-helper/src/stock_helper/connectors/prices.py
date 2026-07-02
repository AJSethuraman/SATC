"""Optional daily price connector (Stooq). NON-CANONICAL market data.

Free CSV endpoint, no key. No corporate-action or survivorship guarantees —
used only for context charts, never for signals in v0.1, and always labeled
"non-canonical" wherever it is displayed. Disabled unless ENABLE_PRICE_DATA=true.
"""

import io
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd

from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger

log = get_logger(__name__)

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
PRICE_SOURCE_LABEL = "Stooq daily CSV (non-canonical price data)"
_CACHE_TTL = timedelta(hours=24)


def fetch_daily_prices(ticker: str, settings: Settings | None = None) -> pd.DataFrame | None:
    """Return a Date/Close (+OHLCV) DataFrame, or None if disabled/unavailable."""
    settings = settings or get_settings()
    if not settings.enable_price_data:
        return None
    cache = settings.price_cache_dir / f"{ticker.lower()}.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        age = datetime.now(UTC).timestamp() - cache.stat().st_mtime
        if age < _CACHE_TTL.total_seconds():
            return pd.read_csv(cache, parse_dates=["Date"])
    url = STOOQ_URL.format(symbol=ticker.lower())
    try:
        response = httpx.get(url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
        frame = pd.read_csv(io.StringIO(response.text), parse_dates=["Date"])
    except Exception as exc:  # any failure just means "no price chart"
        log.warning("price fetch failed ticker=%s err=%s", ticker, exc)
        return None
    if "Close" not in frame.columns or frame.empty:
        log.warning("price data empty/unexpected ticker=%s", ticker)
        return None
    frame.to_csv(cache, index=False)
    return frame
