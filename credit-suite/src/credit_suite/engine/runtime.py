"""One refresh, against the closed workbook.

The order of operations here is the design, not an implementation detail:

1. **Every hard gate runs before any fetch.** A refused config must cost nothing
   and change nothing -- refusing after writing half a workbook is worse than
   not refusing at all.
2. **Every slot is blanked before anything is written.** This is what makes a
   run a *stateless rebuild*: a deactivated, refused or failed entity shows
   empty under the fresh timestamp, never last run's figures wearing this run's
   date. It also validates the workbook's raw layout before a single request
   goes out.
3. **A per-entity fetch failure blanks that slot and continues.** One bank's
   outage must not cost the analyst the other eleven.
4. **Zero pulls where pulls were expected is a failure**, not a quiet success.
   Without that check a total outage exits 0 over a workbook of blanks, which
   reads as "nothing is wrong".
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from credit_suite.engine import gates, metrics as metrics_mod, rawlayout
from credit_suite.engine.config import Config, EntityRow
from credit_suite.engine.digest import Annotator, compute_digest
from credit_suite.engine.metrics import Registry
from credit_suite.engine.provider import (FieldSpec, Provider, make_field_spec)
from credit_suite.engine.workbook import OpenpyxlBackend


def run_refresh(backend: OpenpyxlBackend, cfg: Config, provider: Provider,
                registry: Registry, fields: Sequence[str],
                field_units: Dict[str, str], asof: date, mode: str,
                annotators: Sequence[Annotator] = (),
                headline_metric: Optional[str] = None,
                secret: Optional[str] = None) -> dict:
    """Gate, blank, fetch, land, digest. Returns the status dict.

    The caller supplies the already-opened backend and the already-made
    provider, so tests can inject either without the engine knowing how a
    source builds them.
    """
    spec = cfg.spec

    # 1. Hard gates, all of them, before any fetch.
    metrics_mod.validate_metrics(cfg.series, registry, fields)
    gates.assert_metrics_admissible(cfg.series, spec)
    gates.validate_entity_capacity(cfg)
    admitted, refusals, excluded = gates.evaluate_entities(cfg)

    # 2. Stateless rebuild: blank every slot 1..capacity first. This also
    #    checks the built layout against what _config now describes.
    for slot in range(1, cfg.entity_slots + 1):
        backend.clear_slot_block(rawlayout.slot_block(slot, cfg.raw_slots))

    errors: List[str] = []
    landed: Dict[int, Tuple[EntityRow, list]] = {}
    try:
        provider.prime([row.key for row in admitted], asof,
                       names={row.key: row.name for row in admitted})
    except Exception as exc:                      # noqa: BLE001 -- reported, not raised
        errors.append("bulk fetch: %s" % exc)
    else:
        for row in admitted:
            try:
                field_rows = {
                    fname: provider.fetch_series(
                        make_field_spec(row, fname, field_units), secret)
                    for fname in fields
                }
                periods = rawlayout.assemble_periods(field_rows, cfg.raw_slots,
                                                     fields)
            except Exception as exc:              # noqa: BLE001
                errors.append("s%02d %s: %s" % (row.slot, row.entity_key, exc))
                continue
            backend.write_slot_block(
                rawlayout.slot_block(row.slot, cfg.raw_slots), row, periods)
            landed[row.slot] = (row, periods)

    digest = compute_digest(cfg, registry, landed, provider.roster,
                            annotators, headline_metric)
    fresh = [e for e in digest["entities"] if not e["stale"]]

    return {
        "timestamp": asof.isoformat(),
        "mode": mode,
        "pack_version": spec.pack_version,
        "entity_slots": cfg.entity_slots,
        "entities_active": len(admitted) + len(refusals),
        "entities_landed": len(landed),
        "entities_excluded": len(excluded),
        # Staleness excludes an entity from every alert KPI.
        "alert_entities": sum(1 for e in fresh if e["status"] == "ALERT"),
        "watch_entities": sum(1 for e in fresh if e["status"] == "WATCH"),
        "stale_entities": sum(1 for e in digest["entities"] if e["stale"]),
        "alert_flags": sum(e["alert_count"] for e in fresh),
        "watch_flags": sum(e["watch_count"] for e in fresh),
        "vintage": provider.vintage,
        "digest": digest,
        "watchlist_refusals": [message for _, message in refusals],
        "watchlist_admitted": ["s%02d %s" % (r.slot, r.entity_key)
                               for r in admitted],
        "errors": errors[:25],
    }


def run_succeeded(status: dict) -> bool:
    """False when entities were expected to land and none did.

    Per-entity fetch failures are collected rather than raised, so without this
    a total outage would exit 0 over a workbook of blanks under a fresh
    timestamp -- which reads as "checked, nothing wrong". Carried from the FRED
    hardening and promoted into the engine so every monitor gets it.
    """
    expected = status.get("entities_active", 0)
    return not (expected > 0 and status.get("entities_landed", 0) == 0)


#: The runner CLI's exit codes (TEMPLATE_CONTRACT section 4).
EXIT_OK = 0
EXIT_RUN_ERROR = 1
EXIT_GATE_ERROR = 2
EXIT_MISSING_SECRET = 3
EXIT_NOTHING_PULLED = 4
