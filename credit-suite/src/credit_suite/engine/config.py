"""The `_config` tab: the knob panel, and the only source of truth for a run.

Parsed identically for every monitor (TEMPLATE_CONTRACT section 3): `[SETTINGS]`
key/value, `[THRESHOLDS]` as `id|watch|alert|direction`, `[SERIES]` as the
19-column dictionary, and the `[PEERS]`/`[FOOTPRINT]` entity slot table of
section 13.

What differs between monitors is not the *parsing* -- it is the vocabulary: FDIC
keys entities on an FDIC certificate, EDGAR on a CIK, the county monitors on a
FIPS code. That difference is data, so it is carried in :class:`MonitorSpec`,
which a source hands to the engine. The engine never imports a source.

Threshold cells stay numeric all the way through (carried lesson L8): a band
written as text makes Excel's ``number >= text`` silently FALSE, which downgrades
every ALERT to WATCH with no error anywhere. :func:`validate_thresholds` refuses
a band that is present but not a number rather than coercing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Sequence

#: The 19-column `[SERIES]` dictionary header (contract section 3).
SERIES_HEADER: List[str] = [
    "id", "title", "category", "lane", "metric_type", "frequency", "sa_nsa",
    "units", "level_rate_index", "geo_segment", "source_class",
    "dashboard_capable", "watchlist_capable", "source_url", "table_id", "sheet",
    "series_label", "transform", "notes",
]

#: The entity slot table's header (contract section 13). The second column is
#: named by the monitor's dialect -- ``cert`` for FDIC, ``cik`` for EDGAR.
ENTITY_HEADER_TAIL: List[str] = ["name", "group", "active"]


@dataclass(frozen=True)
class EntityDialect:
    """How one monitor names, spells and validates its entity join key.

    ``key_pattern`` is a default-deny whitelist, never a denylist: an
    unanticipated key form is refused rather than admitted (contract section 7).
    Promoting a new key form is a spec change, not a config edit.
    """

    key_column: str          # the entity-table column holding the key
    key_prefix: str          # the join-key prefix: "cert" -> "cert:628"
    key_pattern: str         # the whitelist regex the gate applies
    section: str = "PEERS"   # [PEERS] or [FOOTPRINT]
    lookup_hint: str = "run --lookup"

    def entity_key(self, key: str) -> str:
        return "%s:%s" % (self.key_prefix, key)

    def admits(self, entity_key: str) -> bool:
        return re.match(self.key_pattern, entity_key) is not None

    @property
    def header(self) -> List[str]:
        return ["slot", self.key_column, *ENTITY_HEADER_TAIL]


@dataclass(frozen=True)
class MonitorSpec:
    """Everything about a monitor the engine needs but must not assume.

    One of these per source. It is data -- the whole point of the consolidation
    is that adding a source writes one of these plus an adapter, and edits no
    engine code.
    """

    name: str
    raw_tab: str
    entity: EntityDialect
    raw_slots_default: int
    entity_slots_default: int
    pack_version: str
    #: Source classes admitted to the gated lane. Class C (licensed) is never
    #: admitted until a contract exists.
    admitted_source_classes: FrozenSet[str] = frozenset({"A"})
    #: Nominal length of one period, in days -- the staleness yardstick. 92 for
    #: a quarterly Call Report source, 31 for a monthly series.
    period_days: int = 92
    #: Rebuild command quoted back when the entity list exceeds built capacity.
    rebuild_command: str = "make_workbook.py"
    #: What one entity is called in prose: "bank", "filer", "county".
    entity_noun: str = "entity"
    #: The domain sentence closing an entity refusal. ``{name}`` and ``{hint}``
    #: are filled in. A message about FDIC certificates would be nonsense in the
    #: EDGAR monitor, so the voice belongs to the source, not the engine.
    entity_refusal_note: str = ""
    #: The domain sentence closing a metric refusal.
    metric_refusal_note: str = ""
    #: Gate 2's reason text -- which classes this monitor admits, and why.
    gate2_reason: str = ""


@dataclass
class SeriesSpec:
    """One `[SERIES]` row: the metric dictionary entry."""

    id: str
    title: str
    category: str
    lane: str
    metric_type: str
    frequency: str
    sa_nsa: str
    units: str
    level_rate_index: str
    geo_segment: str
    source_class: str
    dashboard_capable: bool
    watchlist_capable: bool
    source_url: str
    table_id: str
    sheet: str
    series_label: str
    transform: str
    notes: str


@dataclass
class EntityRow:
    """One entity slot line. An empty row (slot number only) is provisioned
    headroom the user fills in by hand -- capacity is built, occupancy is
    config."""

    slot: Optional[int]
    key: str                # normalized; "" when blank
    name: str
    group: str
    active: bool
    key_prefix: str = "cert"

    @property
    def has_entity(self) -> bool:
        return bool(self.key or self.name)

    @property
    def entity_key(self) -> str:
        return "%s:%s" % (self.key_prefix, self.key)


@dataclass
class Threshold:
    watch: Optional[float]
    alert: Optional[float]
    direction: str          # "above" | "below"


@dataclass
class Config:
    spec: Optional[MonitorSpec] = None
    settings: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, Threshold] = field(default_factory=dict)
    series: List[SeriesSpec] = field(default_factory=list)
    entities: List[EntityRow] = field(default_factory=list)

    def setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    @property
    def raw_slots(self) -> int:
        default = self.spec.raw_slots_default if self.spec else 16
        return int(float(self.settings.get("raw_slots", default)))

    @property
    def entity_slots(self) -> int:
        """The BUILT slot capacity. Informational here -- the raw-layout check
        (slot header labels) is the hard guard against a stale value."""
        default = self.spec.entity_slots_default if self.spec else 40
        key = "peer_slots" if "peer_slots" in self.settings else "entity_slots"
        return int(float(self.settings.get(key, default)))

    @property
    def stale_multiplier(self) -> float:
        value = as_float(self.settings.get("stale_multiplier", "2.0"))
        return 2.0 if value is None else value

    @property
    def demo_mode(self) -> bool:
        return as_bool(self.settings.get("demo_mode", ""))


# --------------------------------------------------------------------------
# cell coercion
# --------------------------------------------------------------------------

def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t")


def as_float(value: Any) -> Optional[float]:
    try:
        text = str(value).strip()
        return float(text) if text != "" else None
    except (TypeError, ValueError):
        return None


def norm_key(value: Any) -> str:
    """An entity-key cell -> a plain string.

    Excel hands numeric cells over as int/float (628 or 628.0). Text is left as
    typed so a malformed value ('ABC', '12-34') reaches the gate and is refused,
    never silently coerced into something that looks valid.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def norm_slot(value: Any) -> Optional[int]:
    try:
        text = str(value).strip()
        return int(float(text)) if text != "" else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# the parser
# --------------------------------------------------------------------------

def parse_config(rows: Sequence[Sequence], spec: MonitorSpec) -> Config:
    """Parse the `_config` sheet (a list of row value-lists).

    Section order in the sheet is irrelevant and unknown sections are ignored,
    so a monitor may carry an extra section without the engine caring. Lines
    starting ``#`` are in-sheet comments and are never data.
    """
    cfg = Config(spec=spec)
    dialect = spec.entity
    section: Optional[str] = None
    series_header: Optional[List[str]] = None
    thr_header: Optional[List[str]] = None
    entity_header: Optional[List[str]] = None

    for raw in rows:
        first = ("" if not raw or raw[0] is None else str(raw[0])).strip()
        if first.startswith("[") and first.endswith("]"):
            section = first.strip("[]").strip().upper()
            series_header = thr_header = entity_header = None
            continue
        if not first or first.startswith("#"):
            continue

        if section == "SETTINGS":
            if first.lower() in ("key", "name"):
                continue
            value = "" if len(raw) < 2 or raw[1] is None else raw[1]
            cfg.settings[first] = str(value).strip()

        elif section == "THRESHOLDS":
            if thr_header is None and first.lower() == "id":
                thr_header = [str(c).strip().lower() for c in raw]
                continue
            cells = {h: ("" if i >= len(raw) or raw[i] is None else raw[i])
                     for i, h in enumerate(thr_header or
                                           ["id", "watch", "alert", "direction"])}
            cfg.thresholds[first] = Threshold(
                watch=as_float(cells.get("watch")),
                alert=as_float(cells.get("alert")),
                direction=str(cells.get("direction", "above")).strip().lower()
                or "above")

        elif section == dialect.section:
            if entity_header is None and first.lower() == "slot":
                entity_header = [str(c).strip().lower() for c in raw]
                continue
            cells = {h: (None if i >= len(raw) else raw[i])
                     for i, h in enumerate(entity_header or dialect.header)}
            cfg.entities.append(EntityRow(
                slot=norm_slot(cells.get("slot")),
                key=norm_key(cells.get(dialect.key_column)),
                name=("" if cells.get("name") is None
                      else str(cells.get("name")).strip()),
                group=("" if cells.get("group") is None
                       else str(cells.get("group")).strip().lower()),
                active=as_bool(cells.get("active")),
                key_prefix=dialect.key_prefix))

        elif section == "SERIES":
            if series_header is None:
                series_header = [str(c).strip() for c in raw]
                continue
            cells = {h: ("" if i >= len(raw) or raw[i] is None else raw[i])
                     for i, h in enumerate(series_header)}

            def text(key: str, default: str = "") -> str:
                return str(cells.get(key, default)).strip()

            cfg.series.append(SeriesSpec(
                id=text("id"),
                title=text("title"),
                category=text("category"),
                lane=text("lane").lower(),
                metric_type=text("metric_type"),
                frequency=text("frequency"),
                sa_nsa=text("sa_nsa"),
                units=text("units"),
                level_rate_index=text("level_rate_index").lower(),
                geo_segment=text("geo_segment"),
                source_class=text("source_class").upper(),
                dashboard_capable=as_bool(cells.get("dashboard_capable", "")),
                watchlist_capable=as_bool(cells.get("watchlist_capable", "")),
                source_url=text("source_url"),
                table_id=text("table_id"),
                sheet=text("sheet"),
                series_label=text("series_label"),
                transform=text("transform", "direct").lower(),
                notes=text("notes")))
    return cfg


class ThresholdConfigError(ValueError):
    """A threshold band an alert rule reads is not a usable number.

    Carried lesson L8. Refusing is the whole point: a text-typed band makes
    Excel's ``number >= text`` silently FALSE, so every ALERT quietly becomes a
    WATCH and nothing anywhere reports a problem.
    """


def validate_thresholds(cfg: Config) -> None:
    """Refuse a band that some series actually reads and that is not a number.

    Only bands in play are checked. An absent band is a different thing from a
    broken one -- absent means "this metric has no watch level", which is a
    legitimate state that :func:`status_for` already handles.
    """
    for series in cfg.series:
        threshold = cfg.thresholds.get(series.id)
        if threshold is None:
            continue
        for level in ("watch", "alert"):
            raw = getattr(threshold, level)
            if raw is None:
                continue
            if isinstance(raw, float) and raw != raw:
                raise ThresholdConfigError(
                    "%s: %s band is not a number (NaN). A non-numeric band "
                    "makes Excel's comparison silently FALSE (L8); fix the "
                    "_config cell rather than letting it downgrade the flag."
                    % (series.id, level))
