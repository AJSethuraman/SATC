"""The engine, bound to FDIC's spec.

The engine's functions are generic: ``slot_block`` needs a capacity,
``field_col`` needs a field list, ``parse_config`` needs a MonitorSpec. This
module supplies FDIC's answers once, so the FDIC layout and runner can call them
without repeating "for FDIC" at every call site -- and so there is exactly one
place where a wrong binding could be made.

It is deliberately thin. Nothing here decides anything; it only says which
monitor is asking. If a function in here starts containing logic, that logic
belongs either in the engine (if every source needs it) or in the adapter (if
only FDIC does).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from credit_suite.engine import gates as _gates
from credit_suite.engine import metrics as _metrics
from credit_suite.engine import rawlayout as _rawlayout
from credit_suite.engine import staleness as _staleness
from credit_suite.engine.config import Config, EntityRow, SeriesSpec, Threshold
from credit_suite.engine.config import parse_config as _parse_config
from credit_suite.engine.provider import FieldSpec, NormalizedRow
from credit_suite.engine.provider import make_field_spec as _make_field_spec
from credit_suite.engine.thresholds import status_for  # noqa: F401  (re-export)
from credit_suite.sources.fdic import fields as _fields
from credit_suite.sources.fdic.spec import FDIC

# --- the constants the layout reads -------------------------------------
SPEC = FDIC
RAW_TAB = FDIC.raw_tab
RAW_FIELDS = _fields.RAW_FIELDS
PCT_FIELDS = _fields.PCT_FIELDS
FIELD_UNITS = _fields.FIELD_UNITS
PACK_RATIOS = _fields.PACK_RATIOS
PACK_DIRECT = _fields.PACK_DIRECT
METRICS = _fields.REGISTRY
LOANBOOK_CLASS = _fields.LOANBOOK_CLASS
CONSUMER_CLASSES = _fields.CONSUMER_CLASSES
COMMERCIAL_CLASSES = _fields.COMMERCIAL_CLASSES
PACK_VERSION = FDIC.pack_version
RAW_SLOTS_DEFAULT = FDIC.raw_slots_default
PEER_SLOTS_DEFAULT = FDIC.entity_slots_default

#: Status-panel placement. Dashboard_LoanBook is wider than the others (its
#: banner merge runs past column L), so its panel lives further right.
STATUS_COL = 12                                   # column L
STATUS_COL_BY_TAB = {"Dashboard_LoanBook": 24}    # column X
DASH_TABS = ("Dashboard_AssetQuality", "Dashboard_Capital_Earnings",
             "Dashboard_Funding_Concentration", "Dashboard_LoanBook")

# Re-exported types the layout annotates with.
PeerRow = EntityRow
WatchlistRefused = _gates.WatchlistRefused
PeerCapacityError = _gates.EntityCapacityError
MetricError = _metrics.MetricError
SlotBlock = _rawlayout.SlotBlock
slot_label = _rawlayout.slot_label


def parse_config(rows) -> Config:
    return _parse_config(rows, FDIC)


def slot_block(slot: int, raw_slots: int = FDIC.raw_slots_default):
    return _rawlayout.slot_block(slot, raw_slots)


def field_col(fname: str) -> int:
    return _rawlayout.field_col(fname, RAW_FIELDS)


def assemble_quarters(field_rows, raw_slots: int):
    return _rawlayout.assemble_periods(field_rows, raw_slots, RAW_FIELDS)


def make_field_spec(row: EntityRow, fname: str) -> FieldSpec:
    return _make_field_spec(row, fname, FIELD_UNITS)


def metric_value(metric_id: str, values) -> Optional[float]:
    return _metrics.metric_value(METRICS, metric_id, values)


def validate_metrics(series: Sequence[SeriesSpec]) -> None:
    _metrics.validate_metrics(series, METRICS, RAW_FIELDS)


def validate_peer_capacity(cfg: Config) -> None:
    _gates.validate_entity_capacity(cfg)


def assert_entity_gates(cfg: Config) -> None:
    _gates.assert_entity_gates(cfg)


def assert_metrics_admissible(series: Sequence[SeriesSpec]) -> None:
    _gates.assert_metrics_admissible(series, FDIC)


def evaluate_peers(cfg: Config):
    return _gates.evaluate_entities(cfg)


def gate_peer_row(row: EntityRow) -> List[str]:
    return _gates.gate_entity_row(row, FDIC)


def gate_metric_row(series: SeriesSpec) -> List[str]:
    return _gates.gate_metric_row(series, FDIC)


def peer_refusal_message(row: EntityRow, reasons) -> str:
    return _gates.entity_refusal_message(row, reasons, FDIC)


def metric_refusal_message(series: SeriesSpec, reasons) -> str:
    return _gates.metric_refusal_message(series, reasons, FDIC)


def is_stale_bank(last_period, set_max_period, stale_multiplier) -> bool:
    return _staleness.is_stale(last_period, set_max_period, stale_multiplier,
                               FDIC.period_days)


# --- the adapter's names, so a caller has one FDIC front door ------------
import time  # noqa: E402  (re-exported: tests patch time.sleep through here)

from credit_suite.engine.provider import ClassCStubProvider, Provider  # noqa: E402,F401
from credit_suite.sources.fdic.adapter import (FdicDemoProvider,  # noqa: E402,F401
                                               FdicProvider, make_provider)
from credit_suite.sources.fdic.fields import (d_brodepr, d_creconr,  # noqa: E402,F401
                                              d_lndepr, d_pd3089r, d_texas,
                                              d_unrlzcapr)

#: The join-key whitelist, spelled out for callers that assert on the pattern.
ENTITY_KEY_PATTERN = FDIC.entity.key_pattern


def __getattr__(name: str):
    """Lazily expose the runner's entry points.

    ``runner`` imports this module, so importing it at the top would be a
    cycle. Everything here is a front door for callers, not a dependency of
    anything in the engine.
    """
    if name in ("run", "main", "read_provenance_rows", "facsimile_url",
                "bankfind_url", "status_lines", "ANNOTATORS", "build_parser"):
        from credit_suite.sources.fdic import runner as _runner
        return getattr(_runner, name)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


def assemble(base_xlsx: str, out_xlsm: str, macro_bas: str = None) -> str:
    """Wrap FDIC's base .xlsx into the macro-enabled .xlsm."""
    import os

    from credit_suite.engine import package

    macro_bas = macro_bas or os.path.join(os.path.dirname(__file__), "macro.bas")
    return package.assemble(base_xlsx, out_xlsm, macro_bas, "PeerMonitor")
