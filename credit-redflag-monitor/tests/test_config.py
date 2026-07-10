"""Signal Dictionary loading and validation."""

from __future__ import annotations

import pytest

from redflag_monitor.config import (
    ConfigError,
    active_signals,
    load_signals_from_csv,
    signal_from_mapping,
    signals_from_rows,
)
from redflag_monitor.seed import seed_signals


def _row(**overrides):
    base = {
        "series_id": "DGS10",
        "label": "10-Yr Treasury",
        "category": "Rate",
        "source": "FRED",
        "native_frequency": "daily",
        "threshold_type": "abs_change",
        "threshold_value": "0.5",
        "direction_that_matters": "both",
        "active": "Y",
        "notes": "term funding",
    }
    base.update(overrides)
    return base


def test_signal_from_mapping_happy_path():
    signal = signal_from_mapping(_row())
    assert signal.series_id == "DGS10"
    assert signal.threshold_value == 0.5
    assert signal.active is True


def test_active_parsing_variants():
    assert signal_from_mapping(_row(active="N")).active is False
    assert signal_from_mapping(_row(active="yes")).active is True
    assert signal_from_mapping(_row(active="")).active is False


def test_case_insensitive_headers():
    raw = {k.upper(): v for k, v in _row().items()}
    assert signal_from_mapping(raw).series_id == "DGS10"


def test_invalid_category_rejected():
    with pytest.raises(ConfigError):
        signal_from_mapping(_row(category="Bogus"))


def test_invalid_threshold_type_rejected():
    with pytest.raises(ConfigError):
        signal_from_mapping(_row(threshold_type="magic"))


def test_non_numeric_threshold_rejected():
    with pytest.raises(ConfigError):
        signal_from_mapping(_row(threshold_value="lots"))


def test_blank_rows_skipped_and_duplicates_rejected():
    rows = [_row(), {"series_id": ""}, _row()]
    with pytest.raises(ConfigError, match="duplicate"):
        signals_from_rows(rows)


def test_signals_from_rows_skips_trailing_blanks():
    rows = [_row(), {"series_id": "  ", "label": ""}]
    signals = signals_from_rows(rows)
    assert len(signals) == 1


def test_active_signals_filter():
    rows = [_row(series_id="A"), _row(series_id="B", active="N")]
    assert [s.series_id for s in active_signals(signals_from_rows(rows))] == ["A"]


def test_seed_round_trips_through_validation():
    seeds = seed_signals()
    revalidated = signals_from_rows([s.as_row() for s in seeds])
    assert len(revalidated) == len(seeds) == 14


def test_load_signals_from_csv(tmp_path):
    csv_path = tmp_path / "dict.csv"
    csv_path.write_text(
        "series_id,label,category,source,native_frequency,threshold_type,"
        "threshold_value,direction_that_matters,active,notes\n"
        "DFF,Fed Funds,Rate,FRED,daily,abs_change,0.25,both,Y,policy\n",
        encoding="utf-8",
    )
    signals = load_signals_from_csv(csv_path)
    assert signals[0].series_id == "DFF"
