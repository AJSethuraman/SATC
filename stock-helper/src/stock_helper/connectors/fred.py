"""FRED risk-free-rate connector, mirroring the SecClient acquisition pattern.

No business logic lives here — only acquisition. The latest observation of a
FRED series (default DGS10, the 10-yr Treasury constant-maturity yield) is
fetched and cached as a JSON envelope under data/raw/fred/ with the URL and
retrieval timestamp, so pulls are auditable and re-parseable without re-hitting
FRED. ``transport`` is injectable for offline tests (httpx.MockTransport).

FRED reports DGS10 in *percent* (e.g. "4.20" == 4.20%). ``risk_free_rate``
returns it as a DECIMAL FRACTION (0.042) so downstream cost-of-capital math is
unit-consistent. Missing observations are marked "." by FRED and yield None.
Without an API key (settings.fred_api_key / env FRED_API_KEY) the client is
inert and returns None — the caller falls back to settings.risk_free_default.
"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger

log = get_logger(__name__)

FRED_OBSERVATIONS_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id={series_id}&api_key={api_key}&file_type=json"
    "&sort_order=desc&limit=1"
)
DEFAULT_SERIES_ID = "DGS10"  # 10-yr Treasury constant maturity (percent)
FRED_MISSING_MARKER = "."  # FRED's marker for a missing observation


class FredClient:
    """Disk-cached GET client for the FRED observations endpoint.

    Inert (all methods return None) when no API key is configured.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings or get_settings()
        self.api_key = self.settings.fred_api_key.strip().strip('"')
        self.cache_dir = self.settings.raw_fred_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=self.settings.sec_cache_ttl_hours)
        self._client = httpx.Client(
            headers={"Accept-Encoding": "gzip, deflate"},
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

    # -- caching -----------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        # The API key is a secret; keep it out of cache filenames.
        keyless = re.sub(r"api_key=[^&]*", "api_key=REDACTED", url)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", keyless.split("://", 1)[-1])[:120]
        digest = hashlib.sha1(keyless.encode()).hexdigest()[:10]
        return self.cache_dir / f"{slug}.{digest}.json"

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text())
            retrieved = datetime.fromisoformat(envelope["retrieved_at"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
        if self.ttl.total_seconds() > 0 and datetime.now(UTC) - retrieved < self.ttl:
            return envelope["body"]
        return None

    def _write_cache(self, url: str, body: str) -> None:
        # Store the redacted URL in the envelope so the secret never lands on disk.
        keyless = re.sub(r"api_key=[^&]*", "api_key=REDACTED", url)
        envelope = {
            "url": keyless,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "body": body,
        }
        self._cache_path(url).write_text(json.dumps(envelope))

    # -- requests ----------------------------------------------------------

    def get_json(self, url: str) -> Any:
        cached = self._read_cache(url)
        if cached is not None:
            log.debug("cache hit url=%s", re.sub(r"api_key=[^&]*", "api_key=REDACTED", url))
            return json.loads(cached)
        log.info("GET %s", re.sub(r"api_key=[^&]*", "api_key=REDACTED", url))
        response = self._client.get(url)
        response.raise_for_status()
        self._write_cache(url, response.text)
        return json.loads(response.text)

    # -- FRED endpoints ----------------------------------------------------

    def risk_free_rate(self, series_id: str = DEFAULT_SERIES_ID) -> float | None:
        """Latest ``series_id`` observation as a decimal fraction, or None.

        Returns None when: no API key is configured, the request fails, no
        observations come back, or the latest value is FRED's missing marker
        (".") or otherwise unparseable. DGS10 is a percent yield, so the value
        is divided by 100 (4.20 -> 0.042).
        """
        if not self.api_key:
            log.debug("FRED_API_KEY not configured; risk_free_rate -> None")
            return None
        url = FRED_OBSERVATIONS_URL.format(series_id=series_id, api_key=self.api_key)
        try:
            payload = self.get_json(url)
        except Exception as exc:  # any failure just means "no risk-free rate"
            log.warning("FRED fetch failed series=%s err=%s", series_id, exc)
            return None
        observations = payload.get("observations") if isinstance(payload, dict) else None
        if not observations:
            return None
        raw = observations[0].get("value")
        if raw is None or raw == FRED_MISSING_MARKER:
            return None
        try:
            return float(raw) / 100.0
        except (TypeError, ValueError):
            return None

    def close(self) -> None:
        self._client.close()
