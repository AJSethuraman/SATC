from __future__ import annotations

"""Item registry — the single source of truth for every item in the arena.

One entry per item id carries BOTH the human-readable ``effect`` string that is
shown to models verbatim AND the mechanical hooks the resolver reads.  Nothing
outside this module may hard-code an item literal (the v0.1
``1 if "veteran_blade" in inventory else 0`` in ``engine._attack`` was exactly
the disclosure gap this registry closes).

Invariant: every non-default mechanical hook is either surfaced by
``passive_disclosures`` or named in the ``effect`` string.  No silent hooks.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence


ITEM_SCHEMA_VERSION = "ember-vault-items-0.2"

CROWN_ID = "ember_crown"


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    effect: str  # human-readable, shown to models VERBATIM
    consumed_on_use: bool
    # --- mechanical hooks: read ONLY by the resolver, never re-derived there ---
    passive_power: int = 0
    passive_armor: int = 0
    heal: int = 0
    usable: bool = False  # is `use` a legal verb for this item?
    droppable: bool = True  # eligible for the wild-swing "YOU WEAR IT" drop
    is_crown: bool = False
    value: int = 0  # treasure value, read by the treasure_hoarder objective


_REGISTRY: dict[str, ItemDef] = {
    "ember_crown": ItemDef(
        id="ember_crown",
        name="Ember Crown",
        effect=(
            "Objective. While you carry it you gain +2 at the end of every full "
            "round (attunement). At attunement 2 or more you may move to egress "
            "and win the match outright. ANY transfer resets attunement to 0. It "
            "cannot be used. WARNING: it sorts first alphabetically, so a wild "
            "swing that makes you drop an item always drops the Crown."
        ),
        consumed_on_use=False,
        usable=False,
        droppable=True,
        is_crown=True,
        value=25,
    ),
    "healing_tonic": ItemDef(
        id="healing_tonic",
        name="Healing Tonic",
        effect="Use: restore 5 HP, up to your maximum. Consumed on use.",
        consumed_on_use=True,
        heal=5,
        usable=True,
        droppable=True,
        value=5,
    ),
    "ironwood_splinter": ItemDef(
        id="ironwood_splinter",
        name="Ironwood Splinter",
        effect="Use: restore 2 HP, up to your maximum. Consumed on use.",
        consumed_on_use=True,
        heal=2,
        usable=True,
        droppable=True,
        value=3,
    ),
    "veteran_blade": ItemDef(
        id="veteran_blade",
        name="Veteran Blade",
        effect=(
            "Passive: +1 Power on every attack you make. Never consumed. "
            "Can be dropped."
        ),
        consumed_on_use=False,
        passive_power=1,
        usable=False,
        droppable=True,
        value=8,
    ),
}

ITEM_REGISTRY: Mapping[str, ItemDef] = MappingProxyType(_REGISTRY)

# Stat hooks that must appear in ``passive_disclosures``. Keeping the mapping
# here (rather than in the disclosure function) is what makes the completeness
# test a loop over the registry instead of a hand-written list.
PASSIVE_STAT_FIELDS: tuple[tuple[str, str], ...] = (
    ("passive_power", "power"),
    ("passive_armor", "armor"),
)


def is_known_item(item_id: str | None) -> bool:
    return isinstance(item_id, str) and item_id in ITEM_REGISTRY


def item_def(item_id: str) -> ItemDef:
    return ITEM_REGISTRY[item_id]


def item_name(item_id: str) -> str:
    definition = ITEM_REGISTRY.get(item_id)
    return definition.name if definition else item_id


def describe_item(item_id: str) -> dict[str, Any]:
    """THE ONLY item shape allowed in an observation. Exactly four keys."""
    definition = item_def(item_id)
    return {
        "id": definition.id,
        "name": definition.name,
        "effect": definition.effect,
        "consumed_on_use": definition.consumed_on_use,
    }


def describe_items(item_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Order-preserving; duplicates preserved (two tonics render twice)."""
    return [describe_item(item_id) for item_id in item_ids]


def passive_power_bonus(inventory: Sequence[str]) -> int:
    return sum(item_def(item_id).passive_power for item_id in _distinct(inventory))


def passive_armor_bonus(inventory: Sequence[str]) -> int:
    return sum(item_def(item_id).passive_armor for item_id in _distinct(inventory))


def usable_item_ids(inventory: Sequence[str]) -> list[str]:
    """Sorted and DEDUPED — two tonics enumerate one `use healing_tonic`."""
    return sorted({item_id for item_id in _known(inventory) if item_def(item_id).usable})


def droppable_item_ids(inventory: Sequence[str]) -> list[str]:
    """Sorted, duplicates preserved: the wild-swing drop takes index 0."""
    return sorted(item_id for item_id in _known(inventory) if item_def(item_id).droppable)


def heal_amount(item_id: str) -> int:
    return item_def(item_id).heal


def consumed_on_use(item_id: str) -> bool:
    return item_def(item_id).consumed_on_use


def item_value(item_id: str) -> int:
    definition = ITEM_REGISTRY.get(item_id)
    return definition.value if definition else 0


def loot_value(inventory: Sequence[str]) -> int:
    return sum(item_value(item_id) for item_id in inventory)


def passive_disclosures(inventory: Sequence[str]) -> list[dict[str, Any]]:
    """One entry per (DISTINCT item, non-zero stat hook).

    Passives do NOT stack: two Veteran Blades are +1 Power, not +2, so nobody
    can hoard a stat.  Disclosure follows the same de-duplication, which keeps
    the observation's reconciliation invariant exact:
    ``power_effective == power_base + sum(delta for power disclosures)``.
    Sorted by (stat, source_id) for a stable observation.
    """
    entries: list[dict[str, Any]] = []
    for item_id in _distinct(inventory):
        definition = item_def(item_id)
        for field, stat in PASSIVE_STAT_FIELDS:
            delta = getattr(definition, field)
            if not delta:
                continue
            entries.append(
                {
                    "source_kind": "item",
                    "source_id": definition.id,
                    "source_name": definition.name,
                    "stat": stat,
                    "delta": delta,
                    "text": (
                        f"{definition.name} grants "
                        f"{delta:+d} {stat.capitalize()}."
                    ),
                }
            )
    entries.sort(key=lambda entry: (entry["stat"], entry["source_id"]))
    return entries


def _known(inventory: Sequence[str]) -> list[str]:
    """Unknown ids can only arrive from a corrupted state; ignore them here so
    observation building can never raise mid-match."""
    return [item_id for item_id in inventory if item_id in ITEM_REGISTRY]


def _distinct(inventory: Sequence[str]) -> list[str]:
    """Sorted and deduped — canonical order, and duplicates never double-count."""
    return sorted(set(_known(inventory)))
