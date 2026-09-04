"""Unit tests for the data path (BUILD SPEC phase 1 & 2 tests).

Run: python3 -m pytest tests/ -q     (or: python3 tests/test_runner.py)
"""
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

from credit_suite.sources.fred import runner as R
from credit_suite.sources.fred import series_seed as S


# --------------------------------------------------------------------------
# Fixtures: tiny known frames
# --------------------------------------------------------------------------
def q_series(values, start="2020-03-31"):
    idx = pd.date_range(start=start, periods=len(values), freq="QE")
    return pd.Series(values, index=idx, dtype="float64")


def m_series(values, start="2020-01-31"):
    idx = pd.date_range(start=start, periods=len(values), freq="ME")
    return pd.Series(values, index=idx, dtype="float64")


# --------------------------------------------------------------------------
# Transforms (sec 3) -- pure, deterministic
# --------------------------------------------------------------------------
def test_level_passthrough():
    s = q_series([1.0, 2.0, 3.0])
    out = R.t_level(s, "quarterly")
    assert list(out) == [1.0, 2.0, 3.0]


def test_yoy_pct_quarterly_uses_4_periods():
    # 5 quarters: the 5th is +10% over the 1st.
    s = q_series([100, 101, 102, 103, 110])
    out = R.t_yoy_pct(s, "quarterly")
    assert math.isnan(out.iloc[0])           # no base 4 periods back
    assert out.iloc[4] == pytest.approx(10.0)


def test_yoy_pct_monthly_uses_12_periods():
    vals = [100 + i for i in range(13)]       # 13 months, last = 112
    s = m_series(vals)
    out = R.t_yoy_pct(s, "monthly")
    assert out.iloc[12] == pytest.approx(12.0)   # 112 vs 100
    assert all(math.isnan(x) for x in out.iloc[:12])


def test_missing_value_stays_missing():
    # A transform must never invent data; NaN in -> NaN out.
    s = q_series([100, np.nan, 102, 103, 110])
    out = R.t_yoy_pct(s, "quarterly")
    assert math.isnan(out.iloc[1])


def test_zscore_8q_needs_full_window_and_flags_a_jump():
    # VARYING warm-up (not flat) so the full-window requirement is actually
    # load-bearing: with min_periods relaxed to 1 the early points would yield
    # finite z's, so `all NaN` below genuinely detects that regression.
    base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    s = q_series(base + [20.0])                 # 9th point spikes well above trailing mean
    out = R.t_zscore_8q(s, "quarterly")
    assert all(math.isnan(x) for x in out.iloc[:7])   # < 8 observations -> NaN
    assert not math.isnan(out.iloc[7])                # 8th point: first full window
    assert out.iloc[8] > 1.0                          # spike -> high z-score


def test_zscore_flat_window_nan_nonflat_finite():
    # Flat window (std 0) -> NaN, never inf. NOTE: the explicit
    # `std.replace(0.0, NaN)` guard is belt-and-suspenders -- in this rolling
    # form the point is always inside its own window, so a flat window also has a
    # zero numerator (0/0 = NaN) and the guard cannot be independently killed by
    # a rolling-input mutation. What IS load-bearing here is the non-flat side:
    # a jump after a flat run must yield a FINITE z (the std>0 path works), so we
    # don't blanket-NaN real signal.
    flat = R.t_zscore_8q(q_series([2.0] * 9), "quarterly")
    assert math.isnan(flat.iloc[8])
    assert not any(math.isinf(x) for x in flat.dropna())
    jump = R.t_zscore_8q(q_series([2.0] * 8 + [5.0]), "quarterly")
    assert math.isfinite(jump.iloc[8]) and jump.iloc[8] > 1.0


def test_index_to_pct_equals_yoy_on_index():
    s = q_series([100, 100, 100, 100, 105])
    a = R.t_index_to_pct(s, "quarterly")
    b = R.t_yoy_pct(s, "quarterly")
    pd.testing.assert_series_equal(a, b)


# --------------------------------------------------------------------------
# `.` -> NaN coercion (sec 2) -- never to 0
# --------------------------------------------------------------------------
def test_coerce_dot_to_nan_never_zero():
    raw = pd.Series(["1.5", ".", "2.0", "."],
                    index=pd.to_datetime(["2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]))
    out = R.coerce_series(raw)
    assert out.iloc[0] == 1.5
    assert math.isnan(out.iloc[1])
    assert math.isnan(out.iloc[3])
    assert (out.fillna(-999) != 0).all()      # missing is NaN, not 0


def test_coerce_keeps_datetimeindex_sorted():
    raw = pd.Series([2.0, 1.0],
                    index=pd.to_datetime(["2020-06-30", "2020-03-31"]))
    out = R.coerce_series(raw)
    assert isinstance(out.index, pd.DatetimeIndex)
    assert list(out.index) == sorted(out.index)


# --------------------------------------------------------------------------
# Watchlist boundary validator (sec 0.1) -- the hard gate
# --------------------------------------------------------------------------
def _spec(**kw):
    base = dict(series_id="X", title="t", category="hpi_state", lane="price",
                metric_type="price", frequency="quarterly", sa_nsa="NSA", units="index",
                level_rate_index="index", geo_segment="state:CA", dashboard_capable=False,
                watchlist_capable=True, transform="yoy_pct", alert_rule="none", notes="")
    base.update(kw)
    return R.SeriesSpec(**base)


def test_validator_accepts_state_hpi():
    R.validate_watchlist([_spec()])           # must not raise


def test_validator_refuses_delinquency_in_watchlist():
    bad = _spec(series_id="DRCCLACBS", category="credit_card", lane="consumer",
                geo_segment="national", metric_type="delinquency")
    with pytest.raises(R.WatchlistBoundaryError) as ei:
        R.validate_watchlist([bad])
    assert "DRCCLACBS" in str(ei.value)        # error must name the series


def test_validator_refuses_national_price_series():
    # A national HPI (USSTHPI) must not be watchlist-capable.
    bad = _spec(series_id="USSTHPI", category="hpi_national", geo_segment="national")
    with pytest.raises(R.WatchlistBoundaryError) as ei:
        R.validate_watchlist([bad])
    assert "USSTHPI" in str(ei.value)


def test_validator_refuses_cre_price_even_though_price_lane():
    bad = _spec(series_id="COMREPUSQ159N", category="cre_price", geo_segment="national")
    with pytest.raises(R.WatchlistBoundaryError):
        R.validate_watchlist([bad])


# --------------------------------------------------------------------------
# Transform misuse guard: index_to_pct never on a dollar-level series (sec 3)
# --------------------------------------------------------------------------
def test_index_to_pct_rejected_on_dollar_level():
    bad = _spec(series_id="BOGZ1FL075035503Q", category="cre_price", watchlist_capable=False,
                lane="price", level_rate_index="level", transform="index_to_pct",
                geo_segment="national")
    with pytest.raises(R.TransformMisuseError) as ei:
        R.validate_transforms([bad])
    assert "BOGZ1FL075035503Q" in str(ei.value)


def test_level_allowed_on_dollar_level():
    ok = _spec(series_id="BOGZ1FL075035503Q", watchlist_capable=False, lane="price",
               level_rate_index="level", transform="level", category="cre_price",
               geo_segment="national")
    R.validate_transforms([ok])                # must not raise


# --------------------------------------------------------------------------
# The shipped seed itself must pass both gates
# --------------------------------------------------------------------------
def _seed_specs():
    cfg = R.parse_config([S.HEADER] and _seed_rows())
    return cfg.series


def _seed_rows():
    rows = [["[SERIES]"], S.HEADER]
    for r in S.all_series():
        rows.append([r[h] for h in S.HEADER])
    return rows


def test_seed_passes_watchlist_gate():
    R.validate_watchlist(_seed_specs())


def test_seed_passes_transform_gate():
    R.validate_transforms(_seed_specs())


def test_seed_watchlist_only_hpi():
    specs = _seed_specs()
    wl = R.watchlist_series(specs)
    assert len(wl) == 89                        # 51 states + 18 metros + 20 case-shiller
    assert all(s.category in R._HPI_CATEGORIES for s in wl)
    assert all(s.lane == "price" for s in wl)


def test_dead_series_excluded_from_pull():
    specs = _seed_specs()
    dead = [s for s in specs if s.is_dead]
    assert any(s.series_id == "FODSP" for s in dead)


# --------------------------------------------------------------------------
# Config parsing round-trip (sec 4 -- the knob panel)
# --------------------------------------------------------------------------
def test_parse_config_sections():
    rows = [
        ["[SETTINGS]"], ["key", "value"], ["fred_api_key", ""], ["raw_slots", "100"],
        ["demo_mode", "FALSE"],
        ["[THRESHOLDS]"], ["key", "value"], ["zscore_band", "1.0"], ["sloos_band", "20"],
        ["[SERIES]"], S.HEADER,
        [v for v in (S.all_series()[0][h] for h in S.HEADER)],
        ["[CBSA_EXTENSIONS]"], ["cbsa", "name", "series_id"], ["35620", "New York", "ATNHPIUS35620Q"],
    ]
    cfg = R.parse_config(rows)
    assert cfg.raw_slots == 100
    assert cfg.zscore_band == 1.0
    assert cfg.sloos_band == 20.0
    assert len(cfg.series) == 1
    assert len(cfg.cbsa_extensions) == 1


# --------------------------------------------------------------------------
# Stale-series check (sec 2)
# --------------------------------------------------------------------------
def test_stale_detection():
    from datetime import date
    asof = date(2026, 3, 31)
    fresh = date(2026, 2, 28)
    old = date(2024, 1, 1)
    assert not R.is_stale(fresh, "monthly", asof, 2.0)
    assert R.is_stale(old, "quarterly", asof, 2.0)
    assert R.is_stale(None, "quarterly", asof, 2.0)


# --------------------------------------------------------------------------
# Demo provider is deterministic (sec 0.5 -- one input, one output)
# --------------------------------------------------------------------------
def test_demo_provider_deterministic():
    p1, p2 = R.DemoProvider(), R.DemoProvider()
    a, b = p1.fetch("CORCCACBS"), p2.fetch("CORCCACBS")
    pd.testing.assert_series_equal(a, b)
    assert a.isna().any()                       # exercises the missing-value path


def test_demo_provider_spaces_dates_by_declared_frequency():
    from datetime import date
    p = R.DemoProvider(asof=date(2026, 3, 1),
                       freq_by_id={"HPIPONM226S": "monthly", "USSTHPI": "quarterly"})
    m = p.fetch("HPIPONM226S").sort_index()
    q = p.fetch("USSTHPI").sort_index()
    m_gap = (m.index[-1] - m.index[-2]).days
    q_gap = (q.index[-1] - q.index[-2]).days
    assert 26 <= m_gap <= 35, f"monthly series spaced {m_gap}d (should be ~1 month)"
    assert 85 <= q_gap <= 100, f"quarterly series spaced {q_gap}d (should be ~1 quarter)"


# --------------------------------------------------------------------------
# Provider adapter: the FRED-specific path coerces through coerce_series.
# Mocked so it runs without a key or network (the seam stays isolated).
# --------------------------------------------------------------------------
def test_fredprovider_coerces_dot_to_nan(monkeypatch):
    import types

    class FakeFred:
        def __init__(self, api_key=None):
            pass

        def get_series(self, sid, **kwargs):
            return pd.Series(["2.0", ".", "3.0"],
                             index=pd.to_datetime(["2020-03-31", "2020-06-30", "2020-09-30"]))

        def get_series_info(self, sid):
            return {"observation_end": "2020-09-30"}

    fake_module = types.ModuleType("fredapi")
    fake_module.Fred = FakeFred
    monkeypatch.setitem(sys.modules, "fredapi", fake_module)
    p = R.FredProvider("dummy-key")
    s = p.fetch("CORCCACBS")
    assert s.iloc[0] == 2.0
    assert math.isnan(s.iloc[1])               # '.' -> NaN, not 0
    assert p.last_observation_date("CORCCACBS").isoformat() == "2020-09-30"


# --------------------------------------------------------------------------
# Self-citation / vintage (BUILD SPEC audit trail)
# --------------------------------------------------------------------------
def test_fred_series_url():
    assert R.fred_series_url("CORCCACBS") == "https://fred.stlouisfed.org/series/CORCCACBS"


def test_block_meta_carries_units_transform_and_vintage():
    from datetime import date
    spec = _spec(series_id="CORCCACBS", units="percent", frequency="quarterly",
                 transform="zscore_8q")
    meta = R.block_meta(spec, vintage=date(2026, 3, 1))
    assert "units=percent" in meta
    assert "transform=zscore_8q" in meta
    assert "vintage=2026-03-01" in meta       # pull-date stamp, distinct from obs dates


def test_fredprovider_pins_realtime_when_vintage_set(monkeypatch):
    import types
    seen = {}

    class FakeFred:
        def __init__(self, api_key=None):
            pass

        def get_series(self, sid, **kwargs):
            seen.update(kwargs)
            return pd.Series([1.0], index=pd.to_datetime(["2020-03-31"]))

    fake = types.ModuleType("fredapi")
    fake.Fred = FakeFred
    monkeypatch.setitem(sys.modules, "fredapi", fake)
    # No pin -> no realtime kwargs (latest release).
    R.FredProvider("k", min_interval=0).fetch("X")
    assert "realtime_end" not in seen
    # Pin -> realtime_start/end passed so FRED returns that vintage.
    seen.clear()
    R.FredProvider("k", min_interval=0, realtime_end="2026-03-01").fetch("X")
    assert seen.get("realtime_start") == "2026-03-01"
    assert seen.get("realtime_end") == "2026-03-01"


def test_is_rate_limit_detection():
    assert R._is_rate_limit(Exception("429 Too Many Requests"))
    assert R._is_rate_limit(Exception("Exceeded Rate Limit"))
    assert not R._is_rate_limit(Exception("404 series not found"))


def test_fredprovider_retries_on_rate_limit(monkeypatch):
    import types
    calls = {"n": 0}

    class FakeFred:
        def __init__(self, api_key=None):
            pass

        def get_series(self, sid, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:                       # first call rate-limited
                raise ValueError("429 Too Many Requests. Exceeded Rate Limit.")
            return pd.Series([1.0], index=pd.to_datetime(["2020-03-31"]))

    fake = types.ModuleType("fredapi")
    fake.Fred = FakeFred
    monkeypatch.setitem(sys.modules, "fredapi", fake)
    monkeypatch.setattr(R.time, "sleep", lambda *_: None)   # don't actually wait
    p = R.FredProvider("k", min_interval=0, max_retries=2)
    s = p.fetch("X")
    assert calls["n"] == 2                            # retried once, then succeeded
    assert s.iloc[0] == 1.0


# --------------------------------------------------------------------------
# Threshold validation gate (a bad band must fail loudly, not silently flag
# everything in Python / blank the whole column in Excel)
# --------------------------------------------------------------------------
def _thresh_cfg(z="1.0", sloos="20"):
    return R.parse_config([["[THRESHOLDS]"], ["key", "value"],
                           ["zscore_band", z], ["sloos_band", sloos]])


def test_parse_config_bad_threshold_is_nan_not_zero():
    # The old code silently coerced garbage -> 0.0 (flags on everything). Now NaN.
    cfg = _thresh_cfg(z="garbage")
    assert math.isnan(cfg.thresholds["zscore_band"])
    assert cfg.raw_thresholds["zscore_band"] == "garbage"


def test_validate_thresholds_rejects_non_numeric():
    cfg = _thresh_cfg(z="garbage")
    series = [_spec(alert_rule="zscore", watchlist_capable=False,
                    category="credit_card", lane="consumer", geo_segment="national")]
    with pytest.raises(R.ThresholdConfigError) as ei:
        R.validate_thresholds(cfg, series)
    assert "zscore_band" in str(ei.value)


def test_validate_thresholds_rejects_blank():
    cfg = _thresh_cfg(sloos="")
    series = [_spec(alert_rule="sloos_level", watchlist_capable=False,
                    category="sloos", lane="commercial", geo_segment="national")]
    with pytest.raises(R.ThresholdConfigError) as ei:
        R.validate_thresholds(cfg, series)
    assert "sloos_band" in str(ei.value)


def test_validate_thresholds_rejects_nonpositive():
    for bad in ("0", "-1.5"):
        cfg = _thresh_cfg(z=bad)
        series = [_spec(alert_rule="zscore", watchlist_capable=False,
                        category="credit_card", lane="consumer", geo_segment="national")]
        with pytest.raises(R.ThresholdConfigError):
            R.validate_thresholds(cfg, series)


def test_validate_thresholds_ignores_unreferenced_band():
    # A bad band nobody's alert_rule reads must NOT block the run.
    cfg = _thresh_cfg(sloos="garbage")            # sloos bad, but...
    series = [_spec(alert_rule="zscore", watchlist_capable=False,       # ...only zscore used
                    category="credit_card", lane="consumer", geo_segment="national")]
    R.validate_thresholds(cfg, series)            # must not raise


def test_validate_thresholds_accepts_shipped_seed():
    R.validate_thresholds(_thresh_cfg(), _seed_specs())   # must not raise


# --------------------------------------------------------------------------
# evaluate_alert -- BOTH branches (the sloos_level branch had zero coverage)
# --------------------------------------------------------------------------
def test_evaluate_alert_sloos_level_fires_on_or_above_band():
    cfg = _thresh_cfg(sloos="20")
    spec = _spec(alert_rule="sloos_level", transform="level", watchlist_capable=False,
                 category="sloos", lane="commercial", geo_segment="national")
    assert R.evaluate_alert(spec, q_series([10, 12, 15, 18, 25]), cfg)["rule"] == "sloos_level"
    assert R.evaluate_alert(spec, q_series([10, 12, 15, 18, 20]), cfg) is not None   # == band, >=
    assert R.evaluate_alert(spec, q_series([10, 12, 15, 18, 19.9]), cfg) is None     # below band


def test_evaluate_alert_zscore_fires_on_or_above_band():
    cfg = _thresh_cfg(z="1.0")
    spec = _spec(alert_rule="zscore", transform="zscore_8q", watchlist_capable=False,
                 category="credit_card", lane="consumer", geo_segment="national")
    hot = q_series([2.0] * 8 + [10.0])          # big jump -> high z
    calm = q_series([2.0, 2.01, 2.0, 2.02, 2.0, 2.01, 2.0, 2.02, 2.01])
    assert R.evaluate_alert(spec, hot, cfg)["rule"] == "zscore"
    assert R.evaluate_alert(spec, calm, cfg) is None


# --------------------------------------------------------------------------
# A total-fetch failure must NOT read as success (never trust the exit code)
# --------------------------------------------------------------------------
def test_run_succeeded_flags_zero_pull():
    assert R.run_succeeded({"series_pullable": 10, "series_pulled": 5}) is True
    assert R.run_succeeded({"series_pullable": 10, "series_pulled": 0}) is False   # total failure
    assert R.run_succeeded({"series_pullable": 0, "series_pulled": 0}) is True     # nothing to pull


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
