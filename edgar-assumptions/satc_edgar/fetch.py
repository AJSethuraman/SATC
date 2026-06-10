"""EDGAR REST fetch layer with throttling and a deterministic local cache.

Endpoints used (all free, no API key required):
  * company tickers : https://www.sec.gov/files/company_tickers.json
  * submissions     : https://data.sec.gov/submissions/CIK{cik10}.json
  * company facts   : https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json

SEC requires a descriptive ``User-Agent`` with a real contact and asks
clients to stay under ~10 requests/second; both are enforced here.

Reproducibility: every fetched payload is written to the cache together with
the date it was first pulled (recorded in ``_cache_meta.json``). Re-runs read
from cache and reuse the ORIGINAL pull date, so a run is byte-identical and
its EDGAR data vintage is stable regardless of when it is re-executed.
"""

from __future__ import annotations

import datetime as _dt
import gzip
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

META_FILENAME = "_cache_meta.json"


def cik10(cik: int | str) -> str:
    """Zero-pad a CIK to the 10-digit form EDGAR uses in paths."""
    return str(int(cik)).zfill(10)


class EdgarClient:
    """Throttled, cached EDGAR client.

    Parameters
    ----------
    user_agent:
        Required by SEC. Should include a real contact (name/app + email).
    cache_dir:
        Directory for cached JSON payloads and the cache metadata manifest.
    min_interval:
        Minimum seconds between live HTTP requests (throttle). Default 0.15s
        keeps us comfortably under the ~10 req/s ceiling.
    offline:
        If True, never hit the network; cache misses raise ``CacheMiss``.
    """

    def __init__(
        self,
        user_agent: str,
        cache_dir: str = ".edgar_cache",
        min_interval: float = 0.15,
        offline: bool = False,
        logger=None,
        max_retries: int = 4,
    ) -> None:
        if not user_agent or "@" not in user_agent:
            raise ValueError(
                "A descriptive User-Agent containing a real contact email is "
                "required by SEC EDGAR (e.g. 'My Co Research jane@example.com')."
            )
        self.user_agent = user_agent
        self.cache_dir = cache_dir
        self.min_interval = float(min_interval)
        self.offline = offline
        self.max_retries = int(max_retries)
        self._last_request = 0.0
        self._log = logger or (lambda msg: None)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._meta_path = os.path.join(self.cache_dir, META_FILENAME)
        self._meta: Dict[str, str] = self._load_meta()
        # Dates (ISO) of every cache entry actually read/written this run; used
        # to report the EDGAR data vintage deterministically.
        self.used_vintages: set[str] = set()

    # -- cache metadata ----------------------------------------------------
    def _load_meta(self) -> Dict[str, str]:
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                return {}
        return {}

    def _save_meta(self) -> None:
        with open(self._meta_path, "w", encoding="utf-8") as fh:
            json.dump(self._meta, fh, indent=2, sort_keys=True)

    def _cache_path(self, key: str) -> str:
        safe = key.replace("/", "_")
        return os.path.join(self.cache_dir, safe)

    # -- HTTP --------------------------------------------------------------
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def _http_get(self, url: str) -> bytes:
        backoff = 2.0
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            self._throttle()
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return raw
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code in (403, 404):
                    # Not transient — surface immediately.
                    raise
                if exc.code in (429, 503):
                    self._log(f"  rate-limited ({exc.code}) on {url}; backoff {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
                self._log(f"  network error on {url}: {exc}; backoff {backoff}s")
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError(f"GET failed after {self.max_retries} attempts: {url} ({last_err})")

    # -- cached JSON fetch -------------------------------------------------
    def get_json(self, url: str, key: str) -> Optional[Dict[str, Any]]:
        """Return parsed JSON for ``url``, using/refreshing the local cache.

        Returns ``None`` for a 404 (e.g. a CIK with no XBRL facts). The pull
        date is recorded on first fetch and reused on subsequent runs.
        """
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            if self._meta.get(key):
                self.used_vintages.add(self._meta[key])
            if content == "":  # cached 404 sentinel
                return None
            return json.loads(content)

        if self.offline:
            raise CacheMiss(f"offline and not cached: {key}")

        try:
            raw = self._http_get(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # Cache the miss so we don't re-hit EDGAR for it.
                self._write_cache(key, "")
                return None
            raise
        text = raw.decode("utf-8")
        # Validate it parses before caching.
        data = json.loads(text)
        self._write_cache(key, text)
        return data

    def _write_cache(self, key: str, text: str) -> None:
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        today = _dt.date.today().isoformat()
        self._meta[key] = today
        self.used_vintages.add(today)
        self._save_meta()

    # -- typed helpers -----------------------------------------------------
    def get_company_tickers(self) -> Dict[str, Any]:
        return self.get_json(TICKERS_URL, "company_tickers.json") or {}

    def get_submissions(self, cik: int | str) -> Optional[Dict[str, Any]]:
        c = cik10(cik)
        return self.get_json(SUBMISSIONS_URL.format(cik10=c), f"submissions_CIK{c}.json")

    def get_companyfacts(self, cik: int | str) -> Optional[Dict[str, Any]]:
        c = cik10(cik)
        return self.get_json(COMPANYFACTS_URL.format(cik10=c), f"companyfacts_CIK{c}.json")

    def vintage_range(self) -> str:
        """Human-readable EDGAR data vintage from cache entries used this run."""
        if not self.used_vintages:
            return "unknown"
        lo = min(self.used_vintages)
        hi = max(self.used_vintages)
        return lo if lo == hi else f"{lo}..{hi}"


class CacheMiss(Exception):
    """Raised when offline mode is on and a resource is not cached."""


def list_ciks(tickers_payload: Dict[str, Any]) -> List[int]:
    """Extract a sorted, de-duplicated list of CIKs from company_tickers.json.

    The payload is a dict keyed by stringified row index, each value carrying
    ``cik_str``, ``ticker`` and ``title``.
    """
    ciks: set[int] = set()
    for row in tickers_payload.values():
        if isinstance(row, dict) and "cik_str" in row:
            try:
                ciks.add(int(row["cik_str"]))
            except (TypeError, ValueError):
                continue
    return sorted(ciks)


def ticker_for_cik(tickers_payload: Dict[str, Any]) -> Dict[int, str]:
    """Map CIK -> primary ticker (first seen, deterministic by row order)."""
    out: Dict[int, str] = {}
    for key in sorted(tickers_payload.keys(), key=lambda k: int(k) if k.isdigit() else k):
        row = tickers_payload[key]
        if isinstance(row, dict) and "cik_str" in row:
            try:
                cik = int(row["cik_str"])
            except (TypeError, ValueError):
                continue
            if cik not in out:
                out[cik] = str(row.get("ticker", "")).upper()
    return out
