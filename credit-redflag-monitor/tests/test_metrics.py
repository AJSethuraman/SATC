"""Metric engine: threshold branches and direction logic (spec section 5)."""

from __future__ import annotations

from redflag_monitor.config import Signal
from redflag_monitor.fred import Observation
from redflag_monitor.metrics import evaluate


def _signal(threshold_type, value, direction="both", frequency="monthly"):
    return Signal(
        series_id="X",
        label="X",
        category="Macro",
        source="FRED",
        native_frequency=frequency,
        threshold_type=threshold_type,
        threshold_value=value,
        direction_that_matters=direction,
        active=True,
    )


def _obs(*pairs):
    return [Observation(period=d, value=v) for d, v in pairs]


def _monthly(values, start_year=2024):
    """Build monthly observations starting Jan of start_year."""
    out = []
    y, m = start_year, 1
    for v in values:
        out.append(Observation(period=f"{y}-{m:02d}-01", value=v))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


# --- abs_change --------------------------------------------------------------


def test_abs_change_flags_when_breached():
    r = evaluate(_signal("abs_change", 0.20, "up"), _obs(("2024-01-01", 4.0), ("2024-02-01", 4.3)))
    assert r.auto_flag is True
    assert round(r.delta_abs, 4) == 0.3


def test_abs_change_below_threshold_not_flagged():
    r = evaluate(_signal("abs_change", 0.20, "up"), _obs(("2024-01-01", 4.0), ("2024-02-01", 4.1)))
    assert r.auto_flag is False


def test_abs_change_wrong_direction_not_flagged():
    # Move is down by 0.3 but the team only cares about up moves.
    r = evaluate(_signal("abs_change", 0.20, "up"), _obs(("2024-01-01", 4.3), ("2024-02-01", 4.0)))
    assert r.auto_flag is False


def test_abs_change_both_direction_flags_either_way():
    down = evaluate(_signal("abs_change", 0.20, "both"), _obs(("2024-01-01", 4.3), ("2024-02-01", 4.0)))
    assert down.auto_flag is True


# --- pct_change --------------------------------------------------------------


def test_pct_change_flag():
    # -10% move, direction down.
    r = evaluate(_signal("pct_change", 10.0, "down"), _obs(("2024-01-01", 80.0), ("2024-02-01", 72.0)))
    assert r.auto_flag is True
    assert round(r.delta_pct, 2) == -10.0


def test_pct_change_just_under_threshold():
    r = evaluate(_signal("pct_change", 10.0, "down"), _obs(("2024-01-01", 80.0), ("2024-02-01", 73.0)))
    assert r.auto_flag is False


# --- level_above / level_below ----------------------------------------------


def test_level_below_inversion_flag():
    r = evaluate(_signal("level_below", 0.0, "down"), _obs(("2024-01-01", 0.2), ("2024-02-01", -0.3)))
    assert r.auto_flag is True


def test_level_below_not_breached():
    r = evaluate(_signal("level_below", 0.0, "down"), _obs(("2024-01-01", 0.2), ("2024-02-01", 0.1)))
    assert r.auto_flag is False


def test_level_above_flag():
    r = evaluate(_signal("level_above", 5.0, "up"), _obs(("2024-01-01", 4.0), ("2024-02-01", 5.5)))
    assert r.auto_flag is True


# --- yoy_change --------------------------------------------------------------


def test_yoy_change_uses_year_ago_observation():
    # 13 monthly points; current vs ~12 months prior.
    values = [300 + i * 0.8 for i in range(13)]  # +0.8/mo -> ~+9.6 yoy
    r = evaluate(_signal("yoy_change", 1.0, "up"), _monthly(values))
    assert r.auto_flag is True
    # prior should be the year-ago (first) reading, not the immediately-prior month.
    assert r.prior == 300.0
    assert round(r.delta_abs, 2) == round(values[-1] - 300.0, 2)


def test_yoy_change_no_year_ago_data_not_flagged():
    r = evaluate(_signal("yoy_change", 1.0, "up"), _obs(("2024-01-01", 300.0), ("2024-02-01", 305.0)))
    assert r.auto_flag is False


# --- edge cases --------------------------------------------------------------


def test_no_valid_observations_returns_error():
    r = evaluate(_signal("abs_change", 0.2), _obs(("2024-01-01", None)))
    assert r.error is not None
    assert r.auto_flag is False


def test_single_observation_no_prior():
    r = evaluate(_signal("abs_change", 0.2), _obs(("2024-01-01", 4.0)))
    assert r.current == 4.0
    assert r.prior is None
    assert r.auto_flag is False


def test_missing_values_dropped_before_current_prior():
    # Trailing "." must not become "current" (spec section 7.1).
    obs = _obs(("2024-01-01", 4.0), ("2024-02-01", 4.5), ("2024-03-01", None))
    r = evaluate(_signal("abs_change", 0.2, "up"), obs)
    assert r.as_of == "2024-02-01"
    assert r.current == 4.5


def test_pct_change_guards_zero_prior():
    r = evaluate(_signal("pct_change", 10.0, "both"), _obs(("2024-01-01", 0.0), ("2024-02-01", 5.0)))
    assert r.delta_pct is None
    assert r.auto_flag is False


def test_threshold_display():
    r = evaluate(_signal("abs_change", 0.25, "both"), _obs(("2024-01-01", 4.0), ("2024-02-01", 4.1)))
    assert r.threshold_display == "abs_change 0.25 (both)"
