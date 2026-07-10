"""Deterministic synthetic FRED data for offline / demo runs.

Lets ``python redflag_monitor.py --demo`` produce a full workbook with no API
key or network, and gives the disposition-persistence acceptance test (run
twice) something to run against. The numbers are plausible but invented.

``DemoFredClient`` is duck-compatible with :class:`fred.FredClient`: it exposes
``fetch_observations(series_id)`` returning ascending observations, including
``"."``-style gaps for ``TERMCBCCALLNS`` so section 7.1 is exercised.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from redflag_monitor.config import Signal
from redflag_monitor.fred import Observation

# Plausible base levels per series.
_BASE = {
    "DFF": 4.33, "DGS10": 4.20, "DGS2": 4.05, "T10Y2Y": -0.30, "SOFR": 4.30,
    "UNRATE": 4.0, "CPIAUCSL": 300.0, "UMCSENT": 70.0, "PSAVERT": 4.5, "TDSP": 11.3,
    "DRCCLACBS": 3.0, "CORCCACBS": 4.5, "DRCLACBS": 2.5, "TERMCBCCALLNS": 21.5,
}
# Deterministic last-step deltas engineered to breach a few thresholds so the
# demo workbook shows both flagged and unflagged rows.
_FINAL_DELTA = {
    "DGS10": 0.60,    # abs_change >= 0.50 -> flag
    "UNRATE": 0.30,   # abs_change >= 0.20, up -> flag
    "DFF": 0.05,      # below 0.25 -> no flag
}


def _periods(frequency: str, today: date) -> list[date]:
    """Generate enough ascending period dates to cover yoy comparisons."""
    if frequency == "daily":
        return [today - timedelta(days=i) for i in range(420)][::-1]
    if frequency == "monthly":
        out = []
        y, m = today.year - 3, today.month
        for _ in range(36):
            out.append(date(y, m, 1))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return out
    # quarterly
    out = []
    q_months = [1, 4, 7, 10]
    y = today.year - 4
    for _ in range(20):
        for qm in q_months:
            out.append(date(y, qm, 1))
        y += 1
    return [d for d in out if d <= today][-16:]


def _value(series_id: str, idx: int, total: int) -> float:
    base = _BASE.get(series_id, 5.0)
    # Gentle deterministic drift + small wave; CPI rises like a price index.
    if series_id == "CPIAUCSL":
        return round(base + idx * 0.8, 3)
    wave = 0.15 * math.sin(idx / 4.0)
    # Gentle drift bounded to ~+/-0.2 regardless of series length.
    drift = 0.4 * (idx / max(total - 1, 1) - 0.5)
    return round(base + wave + drift, 4)


class DemoFredClient:
    """Synthetic, duck-compatible stand-in for :class:`fred.FredClient`."""

    def __init__(self, signals: list[Signal], today: date | None = None) -> None:
        self._freq = {s.series_id: s.native_frequency for s in signals}
        self._today = today or date.today()

    def fetch_observations(self, series_id: str) -> list[Observation]:
        frequency = self._freq.get(series_id, "monthly")
        periods = _periods(frequency, self._today)
        total = len(periods)
        observations: list[Observation] = []
        for idx, period in enumerate(periods):
            value: float | None = _value(series_id, idx, total)
            # TERMCBCCALLNS is labeled monthly but only populates ~quarterly.
            if series_id == "TERMCBCCALLNS" and period.month not in (3, 6, 9, 12):
                value = None
            observations.append(Observation(period=period.isoformat(), value=value))

        # Apply engineered final-step delta to the last valid observation.
        delta = _FINAL_DELTA.get(series_id)
        if delta is not None and observations:
            last = observations[-1]
            if last.value is not None:
                observations[-1] = Observation(period=last.period, value=round(last.value + delta, 4))
        return observations
