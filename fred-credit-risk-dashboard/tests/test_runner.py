"""Unit tests for the data path (BUILD SPEC phase 1 & 2 tests).

Run: python3 -m pytest tests/ -q     (or: python3 tests/test_runner.py)
"""
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runner as R
import series_seed as S


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
    base = [2.0] * 8
    s = q_series(base + [5.0])                 # 9th point spikes well above trailing mean
    out = R.t_zscore_8q(s, "quarterly")
    assert all(math.isnan(x) for x in out.iloc[:7])   # < 8 periods -> NaN
    assert out.iloc[8] > 1.0                          # spike -> high z-score


def test_zscore_flat_series_is_nan_not_inf():
    s = q_series([2.0] * 9)                    # zero std -> guard against div-by-zero
    out = R.t_zscore_8q(s, "quarterly")
    assert math.isnan(out.iloc[8])


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


# --------------------------------------------------------------------------
# Provider adapter: the FRED-specific path coerces through coerce_series.
# Mocked so it runs without a key or network (the seam stays isolated).
# --------------------------------------------------------------------------
def test_fredprovider_coerces_dot_to_nan(monkeypatch):
    import types

    class FakeFred:
        def __init__(self, api_key=None):
            pass

        def get_series(self, sid):
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

        def get_series(self, sid):
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
