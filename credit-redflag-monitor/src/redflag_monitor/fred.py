"""FRED fetcher with robust missing-value handling (spec section 7.1).

FRED returns ``"."`` for missing periods. Several "monthly"-labeled series
(notably ``TERMCBCCALLNS``) actually populate only quarterly, with ``"."`` in
the gap months. We always parse ``"."`` to ``None`` and let callers take the
last two *valid* observations as current/prior -- never a naive "last row."

Network access is isolated in :class:`FredClient._request` so the parser and
the metric engine can be unit-tested against canned payloads with no network.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

import requests

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
MISSING = "."


class FredError(Exception):
    """Raised on FRED transport errors or malformed responses."""


@dataclass(frozen=True)
class Observation:
    """A single FRED observation.

    ``value`` is ``None`` for missing (``"."``) periods. ``period`` is the
    observation date (the value's vintage in the time series).
    """

    period: str  # ISO date string, e.g. "2024-03-01"
    value: float | None

    @property
    def is_valid(self) -> bool:
        return self.value is not None

    @property
    def period_date(self) -> date:
        return datetime.strptime(self.period, "%Y-%m-%d").date()


def parse_observations(payload: dict[str, Any]) -> list[Observation]:
    """Parse a FRED observations JSON payload into ascending observations.

    Missing values (``"."`` or blank) become ``None``. Rows are sorted by
    period ascending so ``[-1]`` is always the most recent.
    """
    raw = payload.get("observations")
    if raw is None:
        raise FredError("FRED payload missing 'observations'")

    parsed: list[Observation] = []
    for row in raw:
        period = str(row.get("date", "")).strip()
        if not period:
            continue
        text = str(row.get("value", MISSING)).strip()
        if text in (MISSING, ""):
            value: float | None = None
        else:
            try:
                value = float(text)
            except ValueError:
                value = None
        parsed.append(Observation(period=period, value=value))

    parsed.sort(key=lambda obs: obs.period)
    return parsed


def valid_observations(observations: list[Observation]) -> list[Observation]:
    """Drop missing (``"."``) rows -- the first step before current/prior."""
    return [obs for obs in observations if obs.is_valid]


class FredClient:
    """Thin client over the FRED REST observations endpoint.

    Parameters
    ----------
    api_key:
        FRED API key. Defaults to the ``FRED_API_KEY`` environment variable.
        Never hardcode a key (spec section 3).
    start:
        Optional ISO ``observation_start``. Defaults to a few years back so
        ``yoy_change`` signals have a year-ago reading available.
    requester:
        Injectable callable for tests; defaults to :func:`requests.get`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        start: str | None = None,
        timeout: float = 30.0,
        requester: Callable[..., requests.Response] | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("FRED_API_KEY", "")
        if not self.api_key:
            raise FredError(
                "FRED API key not provided. Set the FRED_API_KEY environment "
                "variable (free key at fredaccount.stlouisfed.org/apikeys)."
            )
        self.start = start or self._default_start()
        self.timeout = timeout
        self._requester = requester or requests.get

    @staticmethod
    def _default_start() -> str:
        # Three years of history covers yoy on monthly/quarterly series while
        # keeping daily payloads modest.
        today = date.today()
        return f"{today.year - 3}-{today.month:02d}-{today.day:02d}"

    def _request(self, series_id: str) -> dict[str, Any]:
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": self.start,
            "sort_order": "asc",
        }
        try:
            response = self._requester(
                FRED_OBSERVATIONS_URL, params=params, timeout=self.timeout
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            raise FredError(f"FRED request failed for {series_id}: {exc}") from exc

        if response.status_code != 200:
            raise FredError(
                f"FRED returned HTTP {response.status_code} for {series_id}: "
                f"{response.text[:200]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise FredError(f"FRED returned non-JSON for {series_id}") from exc

    def fetch_observations(self, series_id: str) -> list[Observation]:
        """Fetch and parse all observations for a series (ascending)."""
        return parse_observations(self._request(series_id))
