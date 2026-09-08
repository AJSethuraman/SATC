"""The engine's `_config` parser, pinned against the shipped workbook.

Until 5 September 2026 this file also carried twenty differential tests that
ran the engine beside the legacy FDIC runner and compared them field by
field. The legacy runner was deleted by the migration (#166), so every one of
those tests skipped on every run -- twenty permanent skips that read like an
environment limit and hid any new skip among them. The firm's answer on the
docket was "delete them"; the engine-versus-legacy agreement they proved is
preserved by the Slice-0 parity goldens, which is what `check_parity.py`
measures. What survives here are the hardcoded-value tests -- see the note on
``test_thresholds_are_numeric_typed`` for why they are not merely a copy of
the differential ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pytest

from credit_suite.engine import config as engine_config
from credit_suite.parity import repo_root
from credit_suite.sources.fdic.spec import FDIC

WORKBOOK = repo_root() / "fdic-peer-monitor" / "Bank_Peer_Monitor.xlsm"


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
# the hardcoded-value tests
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
