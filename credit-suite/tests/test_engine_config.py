"""The engine's `_config` parser must agree with the one it replaces.

Hand-written expectations would prove the parser agrees with what I *believed*
the legacy parser did. These tests run both implementations over the real
shipped `_config` tab and compare them field by field, which proves agreement
with what it actually does -- the only version that matters, because parity is
measured against the workbook the legacy code produced.

The differential tests are scaffolding with a known end: they are skipped once
the legacy module is deleted (issue #165 removes it), and the hardcoded-value
tests below them are what survives. Both are here on purpose -- see the note on
``test_thresholds_are_numeric_typed`` for why the surviving ones are not merely
a copy of the differential ones.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import openpyxl
import pytest

from credit_suite.engine import config as engine_config
from credit_suite.parity import repo_root
from credit_suite.sources.fdic.spec import FDIC

LEGACY_RUNNER = repo_root() / "fdic-peer-monitor" / "runner.py"
WORKBOOK = repo_root() / "fdic-peer-monitor" / "Bank_Peer_Monitor.xlsm"


_LEGACY_CACHE = {}


def _load_legacy():
    """Import the legacy FDIC runner under its own name, once.

    Two things this has to get right. Its folder must be importable for the
    duration, because it imports `series_seed` and friends as top-level
    modules. And the module must be in ``sys.modules`` *before* it executes:
    ``@dataclass`` resolves its annotations through
    ``sys.modules[cls.__module__]``, so a module that is not registered yet
    blows up on its first dataclass.
    """
    if "module" in _LEGACY_CACHE:
        return _LEGACY_CACHE["module"]

    folder = str(LEGACY_RUNNER.parent)
    added = folder not in sys.path
    if added:
        sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location("legacy_fdic_runner",
                                                      LEGACY_RUNNER)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[spec.name]
            raise
    finally:
        if added:
            sys.path.remove(folder)
    _LEGACY_CACHE["module"] = module
    return module


legacy = pytest.mark.skipif(not LEGACY_RUNNER.is_file(),
                            reason="legacy FDIC runner deleted by the migration")


@pytest.fixture(scope="module")
def config_rows():
    wb = openpyxl.load_workbook(WORKBOOK, keep_vba=True, read_only=True)
    try:
        return [list(row) for row in wb["_config"].iter_rows(values_only=True)]
    finally:
        wb.close()


@pytest.fixture(scope="module")
def parsed(config_rows):
    return engine_config.parse_config(config_rows, FDIC)


# --------------------------------------------------------------------------
# differential: the engine agrees with the code it replaces
# --------------------------------------------------------------------------

@legacy
def test_settings_match_the_legacy_parser(config_rows, parsed):
    assert parsed.settings == _load_legacy().parse_config(config_rows).settings


@legacy
def test_every_threshold_matches_the_legacy_parser(config_rows, parsed):
    old = _load_legacy().parse_config(config_rows).thresholds
    assert set(parsed.thresholds) == set(old)
    assert old, "no thresholds parsed at all -- the comparison proves nothing"
    for key, want in old.items():
        got = parsed.thresholds[key]
        assert (got.watch, got.alert, got.direction) == \
               (want.watch, want.alert, want.direction), key


@legacy
def test_every_series_field_matches_the_legacy_parser(config_rows, parsed):
    old = _load_legacy().parse_config(config_rows).series
    assert len(parsed.series) == len(old)
    assert old, "no series parsed at all -- the comparison proves nothing"
    for want, got in zip(old, parsed.series):
        for name in engine_config.SERIES_HEADER:
            assert getattr(got, name) == getattr(want, name), \
                "%s.%s" % (want.id, name)


@legacy
def test_every_entity_row_matches_the_legacy_peer_row(config_rows, parsed):
    old = _load_legacy().parse_config(config_rows).peers
    assert len(parsed.entities) == len(old)
    assert old, "no peers parsed at all -- the comparison proves nothing"
    for want, got in zip(old, parsed.entities):
        assert (got.slot, got.key, got.name, got.group, got.active) == \
               (want.slot, want.cert, want.name, want.group, want.active)
        assert got.entity_key == want.entity_key
        assert got.has_entity == want.has_bank


@legacy
def test_derived_settings_match_the_legacy_parser(config_rows, parsed):
    old = _load_legacy().parse_config(config_rows)
    assert parsed.raw_slots == old.raw_slots
    assert parsed.entity_slots == old.peer_slots
    assert parsed.stale_multiplier == old.stale_multiplier


# --------------------------------------------------------------------------
# what survives the legacy module's deletion
# --------------------------------------------------------------------------

def test_the_shipped_config_parses_to_something_worth_comparing(parsed):
    """Report the denominator. A parser that returned nothing would satisfy
    every differential test above by agreeing about nothing."""
    assert len(parsed.series) == 53
    assert len(parsed.entities) == 40
    assert sum(1 for e in parsed.entities if e.has_entity) == 12
    assert len(parsed.thresholds) == 53
    assert parsed.raw_slots == 16 and parsed.entity_slots == 40


def test_thresholds_are_numeric_typed(parsed):
    """Carried lesson L8, asserted on the real shipped config.

    Not a duplicate of the differential threshold test: that one proves the two
    parsers agree, and they would still agree if BOTH read a text-typed band.
    This one asserts the property itself.
    """
    for metric, threshold in parsed.thresholds.items():
        for level in ("watch", "alert"):
            value = getattr(threshold, level)
            assert value is None or isinstance(value, float), \
                "%s %s band is %r, not a number" % (metric, level, value)
            assert value is None or value == value, "%s %s is NaN" % (metric, level)


def test_a_comment_line_is_never_data(parsed):
    assert not any(e.key.startswith("#") or e.name.startswith("#")
                   for e in parsed.entities)
    assert not any(s.id.startswith("#") for s in parsed.series)
    assert not any(k.startswith("#") for k in parsed.settings)


def test_a_blank_slot_is_headroom_not_an_entity(parsed):
    blanks = [e for e in parsed.entities if not e.has_entity]
    assert blanks, "no provisioned headroom at all"
    for row in blanks:
        assert row.slot is not None, "headroom must still carry its slot number"
        assert row.entity_key == "cert:", "a blank slot must not fake a key"


def test_a_malformed_key_reaches_the_gate_rather_than_being_coerced():
    """A key the parser 'fixed' is a key the gate cannot refuse."""
    rows = [["[PEERS]"], ["slot", "cert", "name", "group", "active"],
            [1, "12-34", "Odd Bank", "peer", "TRUE"],
            [2, "ABC", "Text Bank", "peer", "TRUE"],
            [3, 628.0, "Numeric Bank", "peer", "TRUE"]]
    entities = engine_config.parse_config(rows, FDIC).entities
    assert [e.key for e in entities] == ["12-34", "ABC", "628"]
    assert not FDIC.entity.admits(entities[0].entity_key)
    assert not FDIC.entity.admits(entities[1].entity_key)
    assert FDIC.entity.admits(entities[2].entity_key)


def test_a_nan_band_an_alert_rule_reads_is_refused_not_coerced():
    """L8 at the gate: refuse rather than let a broken band downgrade a flag."""
    rows = [["[THRESHOLDS]"], ["id", "watch", "alert", "direction"],
            ["NCLNLSR", float("nan"), 2.0, "above"],
            ["[SERIES]"], engine_config.SERIES_HEADER,
            ["NCLNLSR", "Noncurrent", "aq", "dashboard", "ratio", "quarterly",
             "nsa", "pct", "rate", "entity", "A", "TRUE", "TRUE", "", "", "",
             "", "direct", ""]]
    cfg = engine_config.parse_config(rows, FDIC)
    with pytest.raises(engine_config.ThresholdConfigError, match="NCLNLSR"):
        engine_config.validate_thresholds(cfg)


def test_a_sound_config_passes_the_threshold_gate(parsed):
    engine_config.validate_thresholds(parsed)
