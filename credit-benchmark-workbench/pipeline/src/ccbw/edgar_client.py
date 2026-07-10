"""HTTP client for SEC EDGAR XBRL APIs.

All endpoints are free and keyless but require a descriptive User-Agent
header; requests without one are blocked. SEC's published fair-access limit
is 10 requests/second -- the client enforces a minimum interval between
requests and retries transient failures with exponential backoff.

An optional on-disk cache makes large pulls polite and resumable: a re-run
after a partial failure only re-fetches what is missing.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import requests


class EdgarError(RuntimeError):
    """Raised when an EDGAR request fails after retries."""


class EdgarClient:
    DATA_BASE = "https://data.sec.gov"
    WWW_BASE = "https://www.sec.gov"

    def __init__(
        self,
        user_agent: str,
        min_interval: float = 0.12,
        max_retries: int = 4,
        cache_dir: Optional[str] = None,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        if not user_agent or "@" not in user_agent:
            raise ValueError(
                "SEC requires a descriptive User-Agent including a contact "
                'email, e.g. "Jane Doe jane@example.com"'
            )
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = session or requests.Session()
        self._last_request_ts = 0.0

    # ------------------------------------------------------------------ #
    # Core fetch with rate limiting, retries, and caching
    # ------------------------------------------------------------------ #

    def _cache_path(self, url: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        digest = hashlib.sha256(url.encode()).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get_json(self, url: str, use_cache: bool = True) -> Any:
        cache_path = self._cache_path(url)
        if use_cache and cache_path and cache_path.exists():
            with open(cache_path) as fh:
                return json.load(fh)

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                resp = self._session.get(
                    url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept-Encoding": "gzip, deflate",
                    },
                    timeout=self.timeout,
                )
                self._last_request_ts = time.monotonic()
                if resp.status_code == 200:
                    data = resp.json()
                    if cache_path:
                        tmp = cache_path.with_suffix(".tmp")
                        with open(tmp, "w") as fh:
                            json.dump(data, fh)
                        tmp.replace(cache_path)
                    return data
                if resp.status_code == 404:
                    raise EdgarError(f"404 not found: {url}")
                # 403 usually means a missing/blocked User-Agent; 429/5xx are
                # transient -- both are worth a backoff retry.
                last_err = EdgarError(f"HTTP {resp.status_code} for {url}")
            except (requests.ConnectionError, requests.Timeout) as exc:
                self._last_request_ts = time.monotonic()
                last_err = exc
            if attempt < self.max_retries:
                time.sleep(min(2.0 ** attempt, 16.0))
        raise EdgarError(f"failed after {self.max_retries + 1} attempts: {last_err}")

    # ------------------------------------------------------------------ #
    # Endpoints
    # ------------------------------------------------------------------ #

    @staticmethod
    def cik10(cik: int | str) -> str:
        """Zero-pad a CIK to the 10 digits the XBRL endpoints require."""
        return str(int(cik)).zfill(10)

    def company_tickers(self) -> dict:
        """Bulk ticker -> CIK map."""
        return self.get_json(f"{self.WWW_BASE}/files/company_tickers.json")

    def company_facts(self, cik: int | str) -> dict:
        """Every XBRL fact a company ever filed, in one call."""
        return self.get_json(
            f"{self.DATA_BASE}/api/xbrl/companyfacts/CIK{self.cik10(cik)}.json"
        )

    def company_concept(self, cik: int | str, tag: str, taxonomy: str = "us-gaap") -> dict:
        """Full history of one tag for one company."""
        return self.get_json(
            f"{self.DATA_BASE}/api/xbrl/companyconcept/CIK{self.cik10(cik)}"
            f"/{taxonomy}/{tag}.json"
        )

    def frame(self, tag: str, unit: str, period: str, taxonomy: str = "us-gaap") -> dict:
        """One fact across all reporting companies for one period.

        ``period`` examples: ``CY2023`` (annual duration), ``CY2024Q1``
        (quarterly duration), ``CY2024Q1I`` (instantaneous / balance sheet).
        """
        return self.get_json(
            f"{self.DATA_BASE}/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json"
        )
