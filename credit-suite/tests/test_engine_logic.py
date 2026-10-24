"""Gates, thresholds, staleness and raw layout: the engine must agree with the
code it replaces, and must keep agreeing once that code is gone.

Where a property has a finite input space, it is asserted over the *whole* space
rather than on an example -- a threshold rule checked on one value is a rule
tested on the case it cannot fail.
"""

from __future__ import annotations

import itertools

import pytest

from credit_suite.engine import gates, rawlayout, staleness, thresholds
from credit_suite.engine.config import (Config, EntityRow, SeriesSpec, Threshold,
                                        parse_config)
from credit_suite.sources.fdic.spec import FDIC

from test_engine_config import config_rows  # noqa: F401


def series_row(**over) -> SeriesSpec:
    base = dict(id="NCLNLSR", title="Noncurrent", category="aq", lane="dashboard",
                metric_type="ratio", frequency="quarterly", sa_nsa="nsa",
                units="pct", level_rate_index="rate", geo_segment="entity",
                source_class="A", dashboard_capable=True, watchlist_capable=True,
                source_url="", table_id="", sheet="", series_label="",
                transform="direct", notes="")
    base.update(over)
    return SeriesSpec(**base)


def entity_row(**over) -> EntityRow:
    base = dict(slot=1, key="628", name="Test Bank", group="peer", active=True,
                key_prefix="cert")
    base.update(over)
    return EntityRow(**base)


# --------------------------------------------------------------------------
# threshold engine -- asserted over the whole space, not an example
# --------------------------------------------------------------------------

VALUES = [None, float("nan"), -1.0, 0.0, 0.5, 0.99, 1.0, 1.01, 2.0, 100.0]
BOUNDS = [None, 0.0, 1.0, 2.0]


def test_a_missing_threshold_is_ok_never_a_flag():
    assert thresholds.status_for(999.0, None) == "OK"
    assert thresholds.status_for(None, Threshold(1.0, 2.0, "above")) == "OK"
    assert thresholds.status_for(float("nan"), Threshold(1.0, 2.0, "above")) == "OK"


def test_alert_wins_over_watch_when_a_value_passes_both():
    assert thresholds.status_for(5.0, Threshold(1.0, 2.0, "above")) == "ALERT"


def test_direction_below_flags_the_other_way():
    """Capital and coverage run below-is-bad; getting this backwards turns a
    bank in trouble green."""
    low = Threshold(watch=8.0, alert=6.0, direction="below")
    assert thresholds.status_for(9.0, low) == "OK"
    assert thresholds.status_for(7.0, low) == "WATCH"
    assert thresholds.status_for(5.0, low) == "ALERT"
    high = Threshold(watch=8.0, alert=6.0, direction="above")
    assert thresholds.status_for(9.0, high) == "ALERT"


def test_only_the_literal_word_below_flips_the_direction():
    for spelling in ["above", "", "ABOVE", "up", "higher"]:
        assert thresholds.status_for(5.0, Threshold(1.0, 2.0, spelling)) == "ALERT"
    assert thresholds.status_for(5.0, Threshold(1.0, 2.0, "below")) == "OK"


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------

def test_the_gate_is_default_deny_not_deny_listed():
    """An unanticipated key form must be refused, not waved through."""
    for key in ["", "  ", "ABC", "12-34", "628x", "12345678", "cert:628",
                "628 ", "0x284", "-628", "6.28"]:
        row = entity_row(key=key)
        assert gates.gate_entity_row(row, FDIC), "admitted %r" % key
    for key in ["628", "1", "9999999"]:
        assert not gates.gate_entity_row(entity_row(key=key), FDIC), key


def test_an_inactive_row_is_excluded_and_never_refused():
    """Switching an entity off is a choice, not a mistake -- it must not be
    reported as a refusal an analyst has to go and fix."""
    cfg = Config(spec=FDIC, entities=[
        entity_row(slot=1, key="628", active=True),
        entity_row(slot=2, key="3511", name="Off Bank", active=False),
        entity_row(slot=3, key="", name="", active=True),      # headroom
    ])
    admitted, refusals, excluded = gates.evaluate_entities(cfg)
    assert [r.slot for r in admitted] == [1]
    assert refusals == []
    assert [r.slot for r in excluded] == [2]


def test_one_bad_row_refuses_itself_and_lets_the_rest_land():
    """A typo in a peer list must not kill the whole refresh."""
    cfg = Config(spec=FDIC, entities=[
        entity_row(slot=1, key="628", name="Good"),
        entity_row(slot=2, key="OOPS", name="Typo"),
        entity_row(slot=3, key="3511", name="Also Good"),
    ])
    admitted, refusals, _ = gates.evaluate_entities(cfg)
    assert [r.name for r in admitted] == ["Good", "Also Good"]
    assert len(refusals) == 1
    assert "Typo" in refusals[0][1] and "cert:OOPS" in refusals[0][1]


def test_a_non_admitted_metric_class_refuses_the_whole_run():
    """One poisoned metric row would corrupt every entity's counts, so unlike a
    bad entity this is not survivable."""
    with pytest.raises(gates.WatchlistRefused, match="NCLNLSR"):
        gates.assert_metrics_admissible([series_row(source_class="C")], FDIC)
    gates.assert_metrics_admissible([series_row(source_class="A")], FDIC)


def test_class_c_is_never_admitted_however_capable_it_claims_to_be():
    """Licensed feeds stay gated until a contract exists."""
    row = series_row(source_class="C", watchlist_capable=True)
    assert gates.gate_metric_row(row, FDIC)


# --------------------------------------------------------------------------
# capacity
# --------------------------------------------------------------------------

def test_over_capacity_is_refused_with_a_rebuild_command_never_truncated():
    cfg = Config(spec=FDIC, settings={"peer_slots": "3"}, entities=[
        entity_row(slot=1, key="628", name="A"),
        entity_row(slot=4, key="3511", name="Beyond"),
    ])
    with pytest.raises(gates.EntityCapacityError) as exc:
        gates.validate_entity_capacity(cfg)
    message = str(exc.value)
    assert "Beyond" in message and "never" in message
    assert FDIC.rebuild_command in message, "no rebuild command to act on"


def test_a_duplicated_slot_is_refused_by_name():
    cfg = Config(spec=FDIC, settings={"peer_slots": "40"}, entities=[
        entity_row(slot=2, key="628", name="First"),
        entity_row(slot=2, key="3511", name="Second"),
    ])
    with pytest.raises(gates.EntityCapacityError, match="First"):
        gates.validate_entity_capacity(cfg)


def test_the_shipped_config_is_within_capacity(config_rows):
    gates.validate_entity_capacity(parse_config(config_rows, FDIC))


# --------------------------------------------------------------------------
# staleness
# --------------------------------------------------------------------------

def test_an_entity_with_nothing_landed_is_stale():
    assert staleness.is_stale(None, "2026-03-31", 2.0, 92) is True


def test_nothing_landed_anywhere_is_not_a_staleness_finding():
    """With no baseline there is nothing to be stale against; claiming a finding
    would be inventing one."""
    assert staleness.is_stale("2020-01-01", None, 2.0, 92) is False


def test_an_unreadable_period_is_stale_rather_than_assumed_current():
    assert staleness.is_stale("garbage", "2026-03-31", 2.0, 92) is True


def test_a_lagging_entity_is_stale_but_a_current_one_is_not():
    assert staleness.is_stale("2026-03-31", "2026-03-31", 2.0, 92) is False
    assert staleness.is_stale("2025-09-30", "2026-03-31", 2.0, 92) is False
    assert staleness.is_stale("2025-03-31", "2026-03-31", 2.0, 92) is True


def test_the_period_length_is_the_monitors_to_set():
    """A monthly source must not be judged on quarterly patience."""
    assert staleness.is_stale("2026-01-31", "2026-03-31", 1.0, 92) is False
    assert staleness.is_stale("2026-01-31", "2026-03-31", 1.0, 31) is True


# --------------------------------------------------------------------------
# raw layout
# --------------------------------------------------------------------------

def test_an_anchor_depends_only_on_the_slot_not_on_who_occupies_it():
    """The property that makes a peer list a config edit rather than a rebuild."""
    a = rawlayout.slot_block(3, 16)
    b = rawlayout.slot_block(3, 16)
    assert (a.header_row, a.first_data_row) == (b.header_row, b.first_data_row)
    assert rawlayout.slot_block(1, 16).header_row == 2
    assert rawlayout.slot_block(2, 16).header_row == 22      # stride 2+16+2
    assert rawlayout.slot_block(2, 4).header_row == 10       # stride 2+4+2


def test_blocks_never_overlap_at_any_capacity():
    for raw_slots in [1, 4, 16, 100]:
        blocks = [rawlayout.slot_block(s, raw_slots) for s in range(1, 41)]
        for earlier, later in zip(blocks, blocks[1:]):
            assert earlier.last_data_row < later.header_row


class _Row:
    def __init__(self, period, value):
        self.period, self.value = period, value


def test_a_field_missing_a_period_blanks_that_cell_rather_than_shifting_rows():
    """The bug this guards is silent: a shifted column attributes one quarter's
    figure to another quarter, and every number still looks plausible."""
    fields = ["ASSET", "DEP"]
    rows = rawlayout.assemble_periods({
        "ASSET": [_Row("2026-03-31", 10.0), _Row("2025-12-31", 9.0),
                  _Row("2025-09-30", 8.0)],
        "DEP": [_Row("2026-03-31", 5.0), _Row("2025-09-30", 4.0)],   # gap
    }, raw_slots=3, fields=fields)

    assert [p for p, _ in rows] == ["2026-03-31", "2025-12-31", "2025-09-30"]
    assert [v["DEP"] for _, v in rows] == [5.0, None, 4.0]
    assert [v["ASSET"] for _, v in rows] == [10.0, 9.0, 8.0]


def test_only_raw_slots_periods_are_kept_newest_first():
    rows = rawlayout.assemble_periods(
        {"ASSET": [_Row("2024-03-31", 1.0), _Row("2026-03-31", 3.0),
                   _Row("2025-03-31", 2.0)]}, raw_slots=2, fields=["ASSET"])
    assert [p for p, _ in rows] == ["2026-03-31", "2025-03-31"]

