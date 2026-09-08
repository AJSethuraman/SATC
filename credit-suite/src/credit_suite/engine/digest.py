"""The run digest: per-entity latest-period values, statuses and flag counts.

The engine output the Watchlist parity tests and the monitoring email read. It
is deliberately a plain dict rather than a class -- it is serialised to JSON on
stdout as the runner's status, and a shape that survives ``json.dumps`` is the
shape a downstream reader can rely on.

Staleness is first-class here: a stale entity's status is forced to STALE and it
counts toward no alert KPI and no median. That is not cosmetic. A bank that
merged away keeps returning its final quarter forever, and letting it sit in the
peer median drags the whole comparison toward a figure nobody is reporting any
more.

**A documented divergence, stated rather than hidden:** the workbook's own
``MEDIAN()`` rows *include* stale entities, because a spreadsheet formula cannot
see runtime staleness. The digest median excludes them. The two therefore differ
on a peer set containing a stale bank, and that difference is real and explained
in each monitor's ``_readme`` rather than quietly reconciled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from credit_suite.engine import staleness
from credit_suite.engine.config import Config, EntityRow
from credit_suite.engine.metrics import Registry, metric_value
from credit_suite.engine.metrics import balance_field
from credit_suite.engine.thresholds import (ALERT, NOT_APPLICABLE, OK, STALE,
                                            WATCH, status_for)


@dataclass
class EntityContext:
    """What an annotator gets to look at. Read-only by convention."""

    entity: EntityRow
    periods: Sequence[Tuple[str, Dict[str, Optional[float]]]]
    latest_fields: Dict[str, Optional[float]]
    roster_row: Dict[str, Any]
    stale: bool
    cfg: Config


#: A source-supplied note producer. Notes are what make a blank auditable --
#: "this is null because the form is only filed by $1B+ reporters" is the
#: difference between a gap and a mystery.
Annotator = Callable[[EntityContext], List[str]]


def metric_status(registry: Registry, metric_id: str, fields, threshold) -> str:
    """OK / WATCH / ALERT for a value; for a blank, WHICH blank.

    ``N/A`` when the book the metric stands on is zero or missing -- a bank
    with no card book has nothing to check, and until 5 September 2026 that
    read ``OK`` (#259). ``""`` when there is a book but no number (a field the
    form does not carry for this bank). The Watchlist helper formulas draw
    the same three-way split, so the digest and the workbook agree.
    """
    value = metric_value(registry, metric_id, fields)
    if value is not None:
        return status_for(value, threshold)
    balance = balance_field(registry, metric_id)
    if balance and not fields.get(balance):
        return NOT_APPLICABLE
    return ""


def compute_digest(cfg: Config, registry: Registry,
                   landed: Dict[int, Tuple[EntityRow, Sequence]],
                   roster: Dict[str, dict],
                   annotators: Sequence[Annotator] = (),
                   headline_metric: Optional[str] = None) -> dict:
    """Build the digest for one run."""
    spec = cfg.spec

    latest_period: Dict[int, Optional[str]] = {}
    for slot, (_entity, periods) in landed.items():
        latest_period[slot] = next(
            (p for p, values in periods
             if any(v is not None for v in values.values())), None)
    set_max = max((p for p in latest_period.values() if p), default=None)

    entities: List[dict] = []
    for slot in sorted(landed):
        entity, periods = landed[slot]
        latest_fields = dict(periods[0][1]) if periods else {}
        last = latest_period[slot]
        stale = staleness.is_stale(last, set_max, cfg.stale_multiplier,
                                   spec.period_days)

        metrics: Dict[str, dict] = {}
        alert_n = watch_n = 0
        for series in cfg.series:
            value = metric_value(registry, series.id, latest_fields)
            status = metric_status(registry, series.id, latest_fields,
                                   cfg.thresholds.get(series.id))
            metrics[series.id] = {"value": value, "status": status,
                                  "dimension": series.category}
            # These counts mirror the Watchlist COUNTIF columns exactly, so
            # they are computed for every landed entity including stale ones.
            # Staleness excludes at the top-level KPIs below, not here.
            if status == ALERT:
                alert_n += 1
            elif status == WATCH:
                watch_n += 1

        context = EntityContext(entity=entity, periods=periods,
                                latest_fields=latest_fields,
                                roster_row=roster.get(entity.key) or {},
                                stale=stale, cfg=cfg)
        notes: List[str] = []
        for annotate in annotators:
            notes.extend(annotate(context))
        if stale and spec.stale_note:
            notes.append(spec.stale_note.format(
                multiplier=("%g" % cfg.stale_multiplier)))

        entities.append({
            "slot": slot, "id_prefix": "s%02d" % slot, "key": entity.key,
            "name": entity.name, "group": entity.group,
            "entity_key": entity.entity_key, "asof_period": last,
            "stale": stale,
            "status": (STALE if stale else
                       ALERT if alert_n > 0 else
                       WATCH if watch_n > 0 else OK),
            "alert_count": alert_n, "watch_count": watch_n,
            "headline": metrics.get(headline_metric, {}).get("value")
            if headline_metric else None,
            "metrics": metrics, "notes": notes,
        })

    medians: Dict[str, Optional[float]] = {}
    for series in cfg.series:
        values = sorted(e["metrics"][series.id]["value"] for e in entities
                        if not e["stale"]
                        and e["metrics"][series.id]["value"] is not None)
        if not values:
            medians[series.id] = None
        else:
            n = len(values)
            medians[series.id] = (values[n // 2] if n % 2 else
                                  (values[n // 2 - 1] + values[n // 2]) / 2.0)

    return {"entities": entities, "medians": medians, "set_max_period": set_max}
