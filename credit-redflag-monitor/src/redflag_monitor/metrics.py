"""Metric engine: clean -> derive current/prior -> threshold -> auto-flag.

Pure deterministic logic, fully unit-testable. The branch taken is driven
entirely by the signal's ``threshold_type`` (spec section 7.4), so retuning or
adding a signal never requires a code change.

All flagging is threshold logic. No judgment, no AI -- the human disposition
columns live in the workbook, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from redflag_monitor.config import Signal
from redflag_monitor.fred import Observation, valid_observations

# Tolerance (days) when matching the year-ago observation for yoy_change.
_YOY_WINDOW_DAYS = 75


@dataclass(frozen=True)
class MetricResult:
    """Outcome of evaluating one signal against its threshold."""

    signal: Signal
    current: float | None = None
    as_of: str | None = None
    prior: float | None = None
    prior_period: str | None = None
    delta_abs: float | None = None
    delta_pct: float | None = None
    auto_flag: bool = False
    error: str | None = None

    @property
    def threshold_display(self) -> str:
        """Human-readable threshold for the workbook, e.g. ``abs_change >= 0.25``."""
        s = self.signal
        return f"{s.threshold_type} {_fmt(s.threshold_value)} ({s.direction_that_matters})"


def _fmt(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _passes_direction(direction: str, delta: float) -> bool:
    """Whether a signed change is in the direction the team cares about."""
    if direction == "both":
        return True  # any move qualifies; the magnitude test gates the flag
    if direction == "up":
        return delta > 0
    if direction == "down":
        return delta < 0
    return False


def _find_year_ago(observations: list[Observation], target_period: str) -> Observation | None:
    """Return the valid observation closest to one year before ``target_period``.

    Used for ``yoy_change`` on noisy/seasonal series. Matches within
    :data:`_YOY_WINDOW_DAYS` of the year-ago date so a monthly series lands on
    the same month and a quarterly series on the same quarter.
    """
    target = datetime.strptime(target_period, "%Y-%m-%d").date()
    # date one year earlier (handle Feb 29 by clamping)
    try:
        anchor = target.replace(year=target.year - 1)
    except ValueError:
        anchor = target.replace(year=target.year - 1, day=28)

    best: Observation | None = None
    best_gap = None
    for obs in observations:
        gap = abs((obs.period_date - anchor).days)
        if gap <= _YOY_WINDOW_DAYS and (best_gap is None or gap < best_gap):
            best, best_gap = obs, gap
    return best


def evaluate(signal: Signal, observations: list[Observation]) -> MetricResult:
    """Evaluate one signal against its threshold.

    ``observations`` may include missing (``"."`` -> ``None``) rows; they are
    dropped first (spec section 7.1). The current reading is the last valid
    observation; the prior depends on the threshold type.
    """
    valid = valid_observations(observations)
    if not valid:
        return MetricResult(signal=signal, error="no valid observations")

    current_obs = valid[-1]
    current = current_obs.value
    assert current is not None  # valid_observations guarantees this

    # Select the comparison ("prior") observation.
    if signal.threshold_type == "yoy_change":
        prior_obs = _find_year_ago(valid, current_obs.period)
    else:
        prior_obs = valid[-2] if len(valid) >= 2 else None

    prior = prior_obs.value if prior_obs else None
    prior_period = prior_obs.period if prior_obs else None

    delta_abs = None
    delta_pct = None
    if prior is not None:
        delta_abs = current - prior
        if prior != 0:
            delta_pct = (current - prior) / abs(prior) * 100.0

    auto_flag = _apply_threshold(signal, current, delta_abs, delta_pct)

    return MetricResult(
        signal=signal,
        current=current,
        as_of=current_obs.period,
        prior=prior,
        prior_period=prior_period,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        auto_flag=auto_flag,
    )


def _apply_threshold(
    signal: Signal,
    current: float,
    delta_abs: float | None,
    delta_pct: float | None,
) -> bool:
    """The deterministic threshold branch (spec section 5)."""
    t = signal.threshold_type
    value = signal.threshold_value
    direction = signal.direction_that_matters

    if t == "level_above":
        return current >= value
    if t == "level_below":
        return current <= value

    if t == "abs_change":
        if delta_abs is None:
            return False
        return abs(delta_abs) >= value and _passes_direction(direction, delta_abs)

    if t == "yoy_change":
        # Year-ago comparison reuses delta_abs (prior == year-ago observation).
        if delta_abs is None:
            return False
        return abs(delta_abs) >= value and _passes_direction(direction, delta_abs)

    if t == "pct_change":
        if delta_pct is None or delta_abs is None:
            return False
        return abs(delta_pct) >= value and _passes_direction(direction, delta_abs)

    return False
