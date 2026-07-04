"""SEC EDGAR HTTP client: fair-access compliant, throttled, disk-cached.

No business logic lives here — only acquisition. Cached responses are stored as
JSON envelopes under data/raw/sec/ with the URL and retrieval timestamp, so raw
pulls are auditable and re-parseable without re-hitting SEC.
"""

import hashlib
import json
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from stock_helper.core.config import Settings, get_settings
from stock_helper.core.logging import get_logger

log = get_logger(__name__)

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
ARCHIVES_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}"
FILING_INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{accession}-index.htm"

# SEC guidance caps automated traffic at 10 req/s; we stay well below.
_MIN_REQUEST_INTERVAL_S = 0.17


class TickerNotFoundError(LookupError):
    pass


class SecClient:
    """Throttled, cached GET client for SEC endpoints.

    ``transport`` is injectable for offline tests (httpx.MockTransport).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.settings = settings or get_settings()
        user_agent = self.settings.require_sec_user_agent()
        self.cache_dir = self.settings.raw_sec_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=self.settings.sec_cache_ttl_hours)
        self._last_request_at = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

    # -- caching -----------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1])[:120]
        digest = hashlib.sha1(url.encode()).hexdigest()[:10]
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

    def _write_cache(self, url: str, body: str) -> datetime:
        retrieved_at = datetime.now(UTC)
        envelope = {"url": url, "retrieved_at": retrieved_at.isoformat(), "body": body}
        self._cache_path(url).write_text(json.dumps(envelope))
        return retrieved_at

    # -- requests ----------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL_S:
            time.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
        self._last_request_at = time.monotonic()

    def get_text(self, url: str) -> str:
        cached = self._read_cache(url)
        if cached is not None:
            log.debug("cache hit url=%s", url)
            return cached
        self._throttle()
        log.info("GET %s", url)
        response = self._client.get(url)
        response.raise_for_status()
        self._write_cache(url, response.text)
        return response.text

    def get_json(self, url: str) -> Any:
        return json.loads(self.get_text(url))

    # -- SEC endpoints -----------------------------------------------------

    def load_ticker_map(self) -> dict[str, dict]:
        """ticker (upper) -> {"cik": int, "title": str}. Current filers only —
        NOT a historical security master (see DATA_SOURCES.md)."""
        raw = self.get_json(TICKER_MAP_URL)
        return {
            entry["ticker"].upper(): {"cik": int(entry["cik_str"]), "title": entry["title"]}
            for entry in raw.values()
        }

    def ticker_to_cik(self, ticker: str) -> int:
        entry = self.load_ticker_map().get(ticker.upper())
        if entry is None:
            raise TickerNotFoundError(
                f"Ticker {ticker!r} not found in SEC company_tickers.json "
                "(U.S. EDGAR filers only)."
            )
        return entry["cik"]

    def fetch_submissions(self, cik: int) -> dict:
        return self.get_json(SUBMISSIONS_URL.format(cik=cik))

    def fetch_company_facts(self, cik: int) -> dict:
        return self.get_json(COMPANY_FACTS_URL.format(cik=cik))

    def fetch_archive_document(self, cik: int, accession: str, filename: str) -> str:
        url = archive_document_url(cik, accession, filename)
        return self.get_text(url)

    def close(self) -> None:
        self._client.close()


def archive_document_url(cik: int, accession: str, filename: str) -> str:
    return ARCHIVES_DOC_URL.format(
        cik=cik, accession_nodash=accession.replace("-", ""), filename=filename
    )


def filing_index_url(cik: int, accession: str) -> str:
    return FILING_INDEX_URL.format(
        cik=cik, accession_nodash=accession.replace("-", ""), accession=accession
    )
