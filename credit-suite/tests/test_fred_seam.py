"""FRED speaks the contract's seam now, and the translation loses nothing.

FRED predates TEMPLATE_CONTRACT section 6 and speaks pandas. Rather than rewrite
its providers underneath a parity check whose whole job is to prove nothing
changed, the adapter TRANSLATES: `fetch_series` emits NormalizedRows, and `run`
rebuilds the Series from them. So the contract seam is genuinely on the data
path, not bolted to the side.

That only counts if the round trip is lossless, which is what these assert --
over every seeded series, not a sample.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest

from credit_suite.engine.provider import NormalizedRow
from credit_suite.sources.fred import runner as R
from credit_suite.sources.fred import series_seed as S

ASOF = date(2026, 3, 1)


@pytest.fixture(scope="module")
def cfg():
    rows = ([["[SERIES]"], S.HEADER]
            + [[r[h] for h in S.HEADER] for r in S.all_series()])
    return R.parse_config(rows)


@pytest.fixture(scope="module")
def demo():
    return R.DemoProvider(asof=ASOF,
                          freq_by_id={s["series_id"]: s["frequency"]
                                      for s in S.all_series()})


def test_the_adapter_answers_the_contracts_seam(cfg, demo):
    spec = cfg.series[0]
    rows = demo.fetch_series(spec)
    assert rows and all(isinstance(r, NormalizedRow) for r in rows)
    first = rows[0]
    assert first.id == spec.series_id
    assert first.geo_segment == spec.geo_segment
    assert first.source_class == "A"
    assert first.units == spec.units
    assert len(first.period) == 10 and first.period[4] == "-"


def test_the_round_trip_is_lossless_for_every_seeded_series(cfg, demo):
    """Series -> NormalizedRows -> Series, for all of them. If this drifts by a
    float, the parity golden lights up 22,000 cells later; better to say which
    series and which observation."""
    checked = 0
    for spec in cfg.series:
        if spec.is_dead:
            continue
        original = demo.fetch(spec.series_id)
        restored = R.rows_to_series(demo.fetch_series(spec))

        assert len(restored) == len(original), spec.series_id
        assert list(restored.index) == list(original.index), spec.series_id
        for stamp in original.index:
            a, b = original[stamp], restored[stamp]
            if pd.isna(a):
                assert pd.isna(b), "%s %s: NaN became %r" % (spec.series_id,
                                                             stamp, b)
            else:
                assert a == b, "%s %s" % (spec.series_id, stamp)
        checked += 1
    assert checked > 100, "only %d series compared" % checked


def test_a_missing_observation_survives_as_missing_not_as_zero(cfg):
    """FRED's missing marker is '.', and the whole reason it is coerced is that
    a gap must stay a gap. Zero is a rate; blank is not."""
    spec = cfg.series[0]
    index = pd.to_datetime(["2026-01-31", "2026-02-28", "2026-03-31"])
    series = pd.Series([1.5, float("nan"), 2.5], index=index, dtype="float64")

    rows = R.series_to_rows(series, spec)
    assert [r.value for r in rows] == [1.5, None, 2.5]

    restored = R.rows_to_series(rows)
    assert restored.iloc[0] == 1.5
    assert math.isnan(restored.iloc[1]), "the gap came back as a number"
    assert restored.iloc[2] == 2.5


def test_rows_carry_iso_periods_a_reviewer_can_read(cfg):
    spec = cfg.series[0]
    series = pd.Series([1.0], index=pd.to_datetime(["2026-03-31"]),
                       dtype="float64")
    assert R.series_to_rows(series, spec)[0].period == "2026-03-31"


def test_an_empty_series_round_trips_to_an_empty_series(cfg):
    spec = cfg.series[0]
    assert R.series_to_rows(pd.Series(dtype="float64"), spec) == []
    assert R.rows_to_series([]).empty


def test_rows_come_back_sorted_oldest_first(cfg):
    """Every offset formula in the workbook assumes an order; rebuilding one out
    of order would move every value by a row."""
    spec = cfg.series[0]
    rows = [
        NormalizedRow(id=spec.series_id, period="2026-03-31", value=3.0,
                      geo_segment="", source_class="A", units=""),
        NormalizedRow(id=spec.series_id, period="2025-03-31", value=1.0,
                      geo_segment="", source_class="A", units=""),
        NormalizedRow(id=spec.series_id, period="2025-09-30", value=2.0,
                      geo_segment="", source_class="A", units=""),
    ]
    restored = R.rows_to_series(rows)
    assert list(restored.values) == [1.0, 2.0, 3.0]


def test_the_run_path_actually_goes_through_the_seam():
    """Guards the guard. If `run` reverted to calling the pandas `fetch`
    directly, every test above would still pass while the contract seam became
    decoration."""
    source = open(R.__file__, encoding="utf-8").read()
    assert "provider.fetch_series(spec)" in source, \
        "run() no longer fetches through the contract seam"
    assert "rows_to_series(provider.fetch_series(spec))" in source


def test_fred_no_longer_defines_its_own_normalized_row():
    """FRED must use the engine's row type, not a second one that happens to
    have the same fields -- two definitions that must agree will not."""
    source = open(R.__file__, encoding="utf-8").read()
    assert "class NormalizedRow" not in source
    assert "from credit_suite.engine.provider import NormalizedRow" in source
