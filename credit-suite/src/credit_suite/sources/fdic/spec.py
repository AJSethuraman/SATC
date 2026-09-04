"""What the engine needs to know about FDIC, as data rather than as code."""

from __future__ import annotations

from credit_suite.engine.config import EntityDialect, MonitorSpec

#: Default-deny: only a literal FDIC certificate key passes. Aggregates,
#: name-only rows and unanticipated key forms are refused -- promoting a
#: holding-company/RSSD key is a spec change, not a config edit.
FDIC_ENTITY = EntityDialect(
    key_column="cert",
    key_prefix="cert",
    key_pattern=r"^cert:[0-9]{1,7}$",
    section="PEERS",
    lookup_hint="run --lookup",
)

#: The refusal prose, verbatim from the monitor this engine replaces. It is
#: quoted rather than paraphrased because a refusal is rendered into the
#: Watchlist tab where an analyst reads it, and because a differential test
#: asserts the engine's message is byte-identical to the one it replaced.
_ENTITY_NOTE = (
    "Only CERT-keyed FDIC institutions can be monitored as counterparties;"
    " aggregates, holding companies and name-only rows cannot. Find the"
    ' CERT with: python runner.py --lookup "{name}".'
)

_METRIC_NOTE = (
    "This template admits only the public FDIC BankFind adapter"
    " (Class A); any other class requires its own review before"
    " admission."
)

_GATE2 = (
    "Gate2: source_class is not {admitted} -- this template's only "
    "admitted class is the keyless public FDIC adapter; "
    "any other class (including a future licensed swap) "
    "requires its own review before admission."
)

FDIC = MonitorSpec(
    name="fdic",
    raw_tab="Raw_FDIC",
    entity=FDIC_ENTITY,
    raw_slots_default=16,        # quarters kept per bank, newest-first
    entity_slots_default=40,     # BUILT peer capacity
    pack_version="1.1",
    admitted_source_classes=frozenset({"A"}),
    period_days=92,              # generous quarter length for staleness math
    rebuild_command="python make_workbook.py --peer-slots",
    entity_noun="bank",
    entity_refusal_note=_ENTITY_NOTE,
    metric_refusal_note=_METRIC_NOTE,
    gate2_reason=_GATE2,
)
