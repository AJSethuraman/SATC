"""The watchlist gate: default-deny, three gates, all required.

TEMPLATE_CONTRACT section 7, and non-negotiable. A value only reaches the gated
lane if its series is watchlist-capable, its source class is admitted for that
lane, AND its entity key matches the monitor's explicit join-key whitelist.

Two properties are load-bearing and easy to lose in a refactor:

* **Default-deny, not deny-listed.** An unanticipated key form is refused, not
  admitted. A denylist fails open; this fails closed.
* **Refusals are series-named and interpolated from the real config row**, so a
  refusal tells the analyst which line to fix rather than that something,
  somewhere, was rejected.

The domain sentence at the end of each refusal is the monitor's, not the
engine's -- a message about FDIC certificates would be nonsense in the EDGAR
monitor. The engine composes the structure; :class:`MonitorSpec` supplies the
voice.

Metric rows and entity rows are refused differently, on purpose. A non-admitted
*metric* poisons every entity's counts, so it refuses the whole run. A bad
*entity* row refuses only itself: one typo in a peer list must not kill the
refresh, so that slot is blanked and named while the rest still lands.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from credit_suite.engine.config import Config, EntityRow, MonitorSpec, SeriesSpec


class WatchlistRefused(Exception):
    """A hard gate refused. Carries the interpolated, row-named message."""


class EntityCapacityError(Exception):
    """More entities than BUILT slots.

    Refused with the rebuild command. The runner never truncates an entity
    list -- silently monitoring fewer banks than the analyst listed is the
    failure mode this exists to prevent.
    """


def entity_refusal_message(row: EntityRow, reasons: Sequence[str],
                           spec: MonitorSpec) -> str:
    return (
        'WATCHLIST REFUSED: %s slot %s "%s" has %s="%s", active=%s. %s %s'
        % (spec.entity.section.lower().rstrip("s"), row.slot,
           row.name or "(unnamed)", spec.entity.key_column, row.key,
           "TRUE" if row.active else "FALSE", " ".join(reasons),
           spec.entity_refusal_note.format(
               name=row.name or "<%s name>" % spec.entity_noun,
               hint=spec.entity.lookup_hint))
    ).rstrip()


def metric_refusal_message(series: SeriesSpec, reasons: Sequence[str],
                           spec: MonitorSpec) -> str:
    return (
        'WATCHLIST REFUSED: series "%s" has source_class="%s", '
        'watchlist_capable=%s. %s %s'
        % (series.id, series.source_class,
           "TRUE" if series.watchlist_capable else "FALSE",
           " ".join(reasons), spec.metric_refusal_note)
    ).rstrip()


def gate_entity_row(row: EntityRow, spec: MonitorSpec) -> List[str]:
    """Failed-gate reasons for an active entity row. Empty list == admitted."""
    reasons: List[str] = []
    if not spec.entity.admits(row.entity_key):
        reasons.append(
            "Gate3: entity key '%s' does not match the join-key whitelist "
            "pattern %s (default-deny; a blank or malformed %s cannot be "
            "fetched)." % (row.entity_key, spec.entity.key_pattern,
                           spec.entity.key_column.upper()))
    return reasons


def gate_metric_row(series: SeriesSpec, spec: MonitorSpec) -> List[str]:
    reasons: List[str] = []
    if not series.watchlist_capable:
        reasons.append("Gate1: watchlist_capable is not TRUE.")
    if series.source_class not in spec.admitted_source_classes:
        reasons.append(spec.gate2_reason.format(
            admitted="/".join(sorted(spec.admitted_source_classes))))
    return reasons


def assert_metrics_admissible(series: Sequence[SeriesSpec],
                              spec: MonitorSpec) -> None:
    """Hard gate at build time AND at run start -- defence in depth behind gate 2."""
    for row in series:
        reasons = gate_metric_row(row, spec)
        if reasons:
            raise WatchlistRefused(metric_refusal_message(row, reasons, spec))


def evaluate_entities(cfg: Config) -> Tuple[List[EntityRow],
                                            List[Tuple[EntityRow, str]],
                                            List[EntityRow]]:
    """Apply the default-deny gates to every entity row carrying an entity.

    Returns ``(admitted, refusals, excluded)``. Admitted rows are fetched and
    landed; refused slots are never fetched and are blanked, with the message
    rendered; excluded is the ``active=FALSE`` list -- blanked, not refused,
    because switching an entity off is a choice rather than a mistake.
    """
    admitted: List[EntityRow] = []
    refusals: List[Tuple[EntityRow, str]] = []
    excluded: List[EntityRow] = []
    spec = cfg.spec
    for row in cfg.entities:
        if not row.has_entity:
            continue                       # provisioned empty slot
        if not row.active:
            excluded.append(row)           # gate 1: exclusion, not refusal
            continue
        reasons = gate_entity_row(row, spec)
        if reasons:
            refusals.append((row, entity_refusal_message(row, reasons, spec)))
        else:
            admitted.append(row)
    return admitted, refusals, excluded


def assert_entity_gates(cfg: Config) -> None:
    """Build-time hard gate backing the runtime gates.

    A bad metric row or a bad seed entity cannot even be built into the lane.
    At run time the per-entity gate refuses-and-continues instead.
    """
    assert_metrics_admissible(cfg.series, cfg.spec)
    _, refusals, _ = evaluate_entities(cfg)
    if refusals:
        raise WatchlistRefused(refusals[0][1])


def validate_entity_capacity(cfg: Config) -> None:
    """Every entity-carrying row needs a unique slot inside the BUILT capacity.

    Over capacity is refused with the exact rebuild command, never truncated.
    """
    cap = cfg.entity_slots
    spec = cfg.spec
    occupied = [row for row in cfg.entities if row.has_entity]
    seen: Dict[int, EntityRow] = {}
    bad: List[EntityRow] = []
    for row in occupied:
        if row.slot is None or row.slot < 1 or row.slot > cap:
            bad.append(row)
        elif row.slot in seen:
            raise EntityCapacityError(
                '[%s] slot %s is listed twice ("%s" and "%s"); slots must be '
                "unique -- fix the [%s] table."
                % (spec.entity.section, row.slot, seen[row.slot].name,
                   row.name, spec.entity.section))
        else:
            seen[row.slot] = row
    if bad:
        need = max(len(occupied), max((row.slot or 0) for row in occupied))
        names = ", ".join('"%s" (slot %s)' % (row.name or row.key, row.slot)
                          for row in bad)
        target = max(need, cap + 1)
        raise EntityCapacityError(
            "[%s] lists more entities than the workbook was built for: %s "
            "outside the built capacity of %d slots. The runner never "
            "truncates an entity list -- rebuild with %s %d."
            % (spec.entity.section, names, cap, spec.rebuild_command, target))
