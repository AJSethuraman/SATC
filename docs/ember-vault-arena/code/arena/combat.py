from __future__ import annotations

"""Combat resolution — a PURE planning module.

``combat`` decides: hit/miss, damage, which wild-swing face, which bystander,
which room reaction, who takes what, what is collateral, who gets credit.

``engine`` decides nothing about combat.  It applies the returned effects in
order, computes before/after ``changes`` pairs, emits events, and applies score
deltas.

Layering: this module imports only ``dataclasses``, ``typing`` and
``arena.items`` (itself a leaf).  Importing engine/storage/providers/rng here is
a layering violation — combat never rolls its own dice, it is handed a ``roll``
callable and returns data.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from . import grid, items


COMBAT_TABLE_VERSION = "ember-vault-0.2/combat-1"

TOHIT_DIE = 20
DAMAGE_DIE = 6
WILD_SWING_DIE = 6
DC_BASE = 10
MINIMUM_DAMAGE = 1
BYSTANDER_DAMAGE = 2  # flat; ignores armor and guard
EMPTY_HANDED_SELF_DAMAGE = 1
MONSTER_HIT_POINTS_PER_ROUND_CAP = 3

# Monsters share the d20 to-hit and the d6 damage formula, but a monster miss is
# just a miss.  Every wild-swing face is agent-shaped: "you wear it" needs an
# inventory monsters do not have, "a bystander wears it" would let monsters chip
# other monsters and deflate the agents' +1/hit economy, and a room reaction that
# drops loot would reward agents for a monster's failure.  Wild Swing is a risk
# tax on AGENT aggression.  Accepted cost: monsters can now MISS, which they
# could not in v0.1 — rebalance the monster templates, not this rule.
MONSTERS_ROLL_WILD_SWING = False

GUARDIAN_IDS: frozenset[str] = frozenset({"ironwood_guardian", "ossuary_guardian"})
WARDEN_ID = "crown_warden"

GUARDIAN_FINISHING_BLOW_POINTS = 3
WARDEN_FINISHING_BLOW_POINTS = 5


# ---------------------------------------------------------------------------
# passives
# ---------------------------------------------------------------------------


def effective_power(
    base_power: int, inventory: Sequence[str]
) -> tuple[int, tuple[dict[str, Any], ...]]:
    """SINGLE SOURCE OF TRUTH for attack power.

    ``rules.visible_observation`` publishes the same disclosures, so the combat
    math and the observation's disclosure obligation can never disagree.
    """
    disclosures = tuple(
        entry
        for entry in items.passive_disclosures(inventory)
        if entry["stat"] == "power"
    )
    return base_power + items.passive_power_bonus(inventory), disclosures


def effective_armor(
    base_armor: int, inventory: Sequence[str]
) -> tuple[int, tuple[dict[str, Any], ...]]:
    disclosures = tuple(
        entry
        for entry in items.passive_disclosures(inventory)
        if entry["stat"] == "armor"
    )
    return base_armor + items.passive_armor_bonus(inventory), disclosures


# ---------------------------------------------------------------------------
# frozen projections
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Combatant:
    id: str
    name: str
    kind: str  # "agent" | "monster"
    room: str
    hp: int
    max_hp: int
    power: int  # BASE power, before passives
    armor: int  # BASE armor, before passives
    guard: int
    inventory: tuple[str, ...]
    alive: bool


def combatant_from_agent(agent: Mapping[str, Any]) -> Combatant:
    return Combatant(
        id=agent["id"],
        name=agent["name"],
        kind="agent",
        room=agent["room"],
        hp=agent["hp"],
        max_hp=agent["max_hp"],
        power=agent["power"],
        # Cover is armour you get from the floor: standing behind a fallen
        # pillar raises the DC to hit you exactly like worn plate would.
        armor=agent["armor"] + grid.cover_bonus(agent["room"], agent.get("tile") or []),
        guard=agent.get("guard", 0),
        inventory=tuple(agent.get("inventory", ())),
        alive=agent.get("status") == "active" and agent["hp"] > 0,
    )


def combatant_from_monster(monster: Mapping[str, Any]) -> Combatant:
    return Combatant(
        id=monster["id"],
        name=monster["name"],
        kind="monster",
        room=monster["room"],
        hp=monster["hp"],
        max_hp=monster["max_hp"],
        power=monster["power"],
        armor=monster["armor"],
        guard=monster.get("guard", 0),
        inventory=(),
        alive=monster["hp"] > 0,
    )


@dataclass(frozen=True)
class ToHit:
    label: str
    roll: int
    base_power: int
    passives: tuple[dict[str, Any], ...]
    effective_power: int
    total: int
    dc_base: int
    dc_armor: int
    dc_guard: int
    dc: int
    hit: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "roll": self.roll,
            "base_power": self.base_power,
            "passives": [dict(entry) for entry in self.passives],
            "effective_power": self.effective_power,
            "total": self.total,
            "dc": {
                "base": self.dc_base,
                "armor": self.dc_armor,
                "guard": self.dc_guard,
                "value": self.dc,
            },
            "hit": self.hit,
        }


@dataclass(frozen=True)
class DamageCalc:
    label: str
    roll: int
    effective_power: int
    target_armor: int
    target_guard: int
    raw: int
    amount: int
    minimum_applied: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "roll": self.roll,
            "effective_power": self.effective_power,
            "target_armor": self.target_armor,
            "target_guard": self.target_guard,
            "raw": self.raw,
            "amount": self.amount,
            "minimum_applied": self.minimum_applied,
        }


# ---------------------------------------------------------------------------
# the Wild Swing table — reweighting means editing `faces` and nothing else
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WildSwingFace:
    face_id: str
    faces: tuple[int, ...]  # <-- THE ONLY THING YOU EDIT TO REWEIGHT
    title: str
    flavor: str


WILD_SWING_TABLE: tuple[WildSwingFace, ...] = (
    WildSwingFace(
        "you_wear_it",
        (1, 2),
        "YOU WEAR IT",
        "The swing goes wide and something of yours goes with it.",
    ),
    WildSwingFace(
        "bystander_wears_it",
        (3, 4),
        "A BYSTANDER WEARS IT",
        "The blow travels. Somebody who was not part of this pays for it.",
    ),
    WildSwingFace(
        "room_wears_it",
        (5, 6),
        "THE ROOM WEARS IT",
        "The room takes the hit, and the room answers.",
    ),
)

_FACE_INDEX: dict[int, WildSwingFace] = {}


@dataclass(frozen=True)
class RoomReaction:
    room_id: str
    reaction_id: str
    flavor: str
    effect_kind: str  # strip_guard|reveal_item|attacker_damage|burst_damage|none
    item_id: str | None = None
    amount: int = 0
    max_uses: int = 0  # 0 == unlimited


# Deterministic, one per room, consuming ZERO randomness.  ironwood_gate and
# ossuary_gate are REQUIRED to differ in both flavor and effect_kind.
ROOM_REACTIONS: dict[str, RoomReaction] = {
    "threshold": RoomReaction(
        "threshold",
        "threshold_sluice",
        "Rain sluices off the threshold stone and shoves {target} off its brace.",
        "strip_guard",
    ),
    "ironwood_gate": RoomReaction(
        "ironwood_gate",
        "ironwood_splinter_shear",
        "The swing shears a blade of ironwood off the gate; it clatters to the floor.",
        "reveal_item",
        item_id="ironwood_splinter",
        max_uses=1,
    ),
    "ossuary_gate": RoomReaction(
        "ossuary_gate",
        "ossuary_ribfall",
        "The bone-rack sloughs; a rib of ash-bone lodges in {attacker}'s guard arm.",
        "attacker_damage",
        amount=1,
    ),
    "vault": RoomReaction(
        "vault",
        "ember_glass_flare",
        "The ember-glass flares and the heat lashes everything near the plinth.",
        "burst_damage",
        amount=1,
    ),
    "egress": RoomReaction(
        "egress",
        "egress_windfall",
        "Wind off the egress arch takes the blow and gives nothing back.",
        "none",
    ),
}

DEFAULT_ROOM_REACTION = ROOM_REACTIONS["egress"]


def wild_swing_face(roll: int) -> WildSwingFace:
    return _FACE_INDEX[roll]


def validate_tables() -> None:
    """Runs at import. The faces must partition 1..WILD_SWING_DIE exactly."""
    seen: dict[int, str] = {}
    face_ids: set[str] = set()
    for face in WILD_SWING_TABLE:
        if face.face_id in face_ids:
            raise ValueError(f"duplicate wild swing face_id: {face.face_id}")
        face_ids.add(face.face_id)
        for value in face.faces:
            if value in seen:
                raise ValueError(
                    f"wild swing face {value} claimed by both "
                    f"{seen[value]} and {face.face_id}"
                )
            seen[value] = face.face_id
    expected = set(range(1, WILD_SWING_DIE + 1))
    if set(seen) != expected:
        raise ValueError(
            f"wild swing table must partition {sorted(expected)}, got {sorted(seen)}"
        )
    for room_id, reaction in ROOM_REACTIONS.items():
        if reaction.room_id != room_id:
            raise ValueError(f"room reaction key/room_id mismatch for {room_id}")
        if reaction.effect_kind == "reveal_item":
            if not items.is_known_item(reaction.item_id):
                raise ValueError(
                    f"room reaction {reaction.reaction_id} reveals unknown item "
                    f"{reaction.item_id}"
                )
    _FACE_INDEX.clear()
    _FACE_INDEX.update({value: _face_by_id(face_id) for value, face_id in seen.items()})


def _face_by_id(face_id: str) -> WildSwingFace:
    for face in WILD_SWING_TABLE:
        if face.face_id == face_id:
            return face
    raise KeyError(face_id)


validate_tables()


# ---------------------------------------------------------------------------
# effects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Effect:
    """One ordered instruction for the engine.

    ``collateral=True`` ALWAYS implies ``credited_to is None``: any kill produced
    by such an effect scores zero for everybody.  These two fields are the only
    signals the engine consults when deciding whether to score.
    """

    kind: str  # damage|drop_item|strip_guard|reveal_item|none
    event_type: str
    phase: str  # agent|monster|referee
    actor_id: str | None = None
    target_id: str | None = None
    target_kind: str | None = None  # agent|monster|room|item
    amount: int = 0
    item_id: str | None = None
    room_id: str | None = None
    collateral: bool = False
    credited_to: str | None = None
    cause: str = ""
    accident: bool = False
    public_text: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "event_type": self.event_type,
            "phase": self.phase,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "target_kind": self.target_kind,
            "amount": self.amount,
            "item_id": self.item_id,
            "room_id": self.room_id,
            "collateral": self.collateral,
            "credited_to": self.credited_to,
            "cause": self.cause,
            "accident": self.accident,
            "public_text": self.public_text,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class BystanderPick:
    candidates: tuple[str, ...]
    chosen_id: str | None
    label: str | None
    roll: int | None
    index: int | None
    forced: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidates": list(self.candidates),
            "bystander_id": self.chosen_id,
            "selection": {
                "label": self.label,
                "roll": self.roll,
                "index": self.index,
                "forced": self.forced,
            },
        }


@dataclass(frozen=True)
class WildSwingOutcome:
    label: str
    roll: int
    face: WildSwingFace
    resolved_as: str
    fell_through: bool
    bystander: BystanderPick | None
    reaction: RoomReaction | None
    reaction_applied: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "roll": self.roll,
            "face_id": self.face.face_id,
            "title": self.face.title,
            "faces": list(self.face.faces),
            "resolved_as": self.resolved_as,
            "fell_through": self.fell_through,
        }


@dataclass(frozen=True)
class AttackResolution:
    attacker_id: str
    attacker_kind: str
    target_id: str
    target_kind: str
    room_id: str
    round_no: int
    outcome: str  # hit|miss
    tohit: ToHit
    damage: DamageCalc | None
    wild_swing: WildSwingOutcome | None
    effects: tuple[Effect, ...]
    table_version: str = COMBAT_TABLE_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "attacker_id": self.attacker_id,
            "attacker_kind": self.attacker_kind,
            "target_id": self.target_id,
            "target_kind": self.target_kind,
            "room": self.room_id,
            "round": self.round_no,
            "outcome": self.outcome,
            "tohit": self.tohit.as_dict(),
            "damage": self.damage.as_dict() if self.damage else None,
            "wild_swing": self.wild_swing.as_dict() if self.wild_swing else None,
            "combat_table_version": self.table_version,
        }


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------


def resolve_attack(
    *,
    round_no: int,
    attacker: Combatant,
    target: Combatant,
    room_id: str,
    room_occupants: Sequence[Combatant],
    room_reaction_uses: Mapping[str, int] | None = None,
    roll: Callable[[int, str], int],
) -> AttackResolution:
    """Plan one attack. Consumes rolls in a fixed order and nothing else.

    RNG order (and nothing may be interleaved, or replay diverges):
      1. tohit:r{r}:{attacker}:{target}                d20, always, first
      2a. HIT  -> damage:r{r}:{attacker}:{target}      d6
      2b. MISS -> wildswing:r{r}:{attacker}:{target}   d6  (agents only)
      3.  MISS + bystander face + >=2 candidates ->
              wildswing_bystander:r{r}:{attacker}:{target}  d(len(candidates))

    Room reactions consume ZERO randomness.  A single bystander candidate
    consumes NO roll (``HashRNG.roll`` raises for sides < 2).  Stale targets must
    be filtered by the caller BEFORE this function is entered — it always rolls.
    """
    uses = dict(room_reaction_uses or {})
    suffix = f"r{round_no}:{attacker.id}:{target.id}"

    eff_power, power_passives = effective_power(attacker.power, attacker.inventory)
    target_armor, _ = effective_armor(target.armor, target.inventory)
    tohit_roll = roll(TOHIT_DIE, f"tohit:{suffix}")
    dc = DC_BASE + target_armor + target.guard
    total = tohit_roll + eff_power
    # No natural-20 auto-hit and no natural-1 auto-miss. Do not add crits: the
    # d20 swing is already wide enough at these DCs.
    tohit = ToHit(
        label=f"tohit:{suffix}",
        roll=tohit_roll,
        base_power=attacker.power,
        passives=power_passives,
        effective_power=eff_power,
        total=total,
        dc_base=DC_BASE,
        dc_armor=target_armor,
        dc_guard=target.guard,
        dc=dc,
        hit=total >= dc,
    )

    if tohit.hit:
        damage = _damage_calc(
            roll=roll(DAMAGE_DIE, f"damage:{suffix}"),
            label=f"damage:{suffix}",
            eff_power=eff_power,
            target_armor=target_armor,
            target_guard=target.guard,
        )
        effects = (
            Effect(
                kind="damage",
                event_type="attack_hit",
                phase=attacker.kind,
                actor_id=attacker.id,
                target_id=target.id,
                target_kind=target.kind,
                amount=damage.amount,
                room_id=room_id,
                collateral=False,
                credited_to=attacker.id,
                cause="attack",
                public_text=(
                    f"{attacker.name} hits {target.name} for {damage.amount}."
                ),
                payload={
                    "outcome": "hit",
                    "attacker_kind": attacker.kind,
                    "target_kind": target.kind,
                    "room": room_id,
                    "tohit": tohit.as_dict(),
                    "damage": damage.as_dict(),
                    "combat_table_version": COMBAT_TABLE_VERSION,
                },
            ),
        )
        resolution = AttackResolution(
            attacker_id=attacker.id,
            attacker_kind=attacker.kind,
            target_id=target.id,
            target_kind=target.kind,
            room_id=room_id,
            round_no=round_no,
            outcome="hit",
            tohit=tohit,
            damage=damage,
            wild_swing=None,
            effects=effects,
        )
        _assert_single_damage_per_body(resolution)
        return resolution

    # ---- miss -------------------------------------------------------------
    if attacker.kind == "monster" and not MONSTERS_ROLL_WILD_SWING:
        effects = (
            Effect(
                kind="none",
                event_type="attack_miss",
                phase=attacker.kind,
                actor_id=attacker.id,
                target_id=target.id,
                target_kind=target.kind,
                room_id=room_id,
                cause="attack",
                public_text=f"{attacker.name} lunges at {target.name} and misses.",
                payload={
                    "outcome": "miss",
                    "attacker_kind": attacker.kind,
                    "target_kind": target.kind,
                    "room": room_id,
                    "tohit": tohit.as_dict(),
                    "wild_swing": None,
                    "reason": "monsters_do_not_wild_swing",
                    "combat_table_version": COMBAT_TABLE_VERSION,
                },
            ),
        )
        resolution = AttackResolution(
            attacker_id=attacker.id,
            attacker_kind=attacker.kind,
            target_id=target.id,
            target_kind=target.kind,
            room_id=room_id,
            round_no=round_no,
            outcome="miss",
            tohit=tohit,
            damage=None,
            wild_swing=None,
            effects=effects,
        )
        _assert_single_damage_per_body(resolution)
        return resolution

    swing_roll = roll(WILD_SWING_DIE, f"wildswing:{suffix}")
    face = wild_swing_face(swing_roll)
    effects_list: list[Effect] = []
    bystander: BystanderPick | None = None
    reaction: RoomReaction | None = None
    reaction_applied = False
    resolved_as = face.face_id
    fell_through = False

    if face.face_id == "you_wear_it":
        effects_list.extend(_you_wear_it(attacker, room_id, face))
    elif face.face_id == "bystander_wears_it":
        candidates = tuple(
            sorted(
                body.id
                for body in room_occupants
                if body.alive
                and body.hp > 0
                and body.id != attacker.id
                and body.id != target.id
            )
        )
        if candidates:
            if len(candidates) == 1:
                bystander = BystanderPick(
                    candidates=candidates,
                    chosen_id=candidates[0],
                    label=None,
                    roll=None,
                    index=0,
                    forced=True,
                )
            else:
                label = f"wildswing_bystander:{suffix}"
                pick_roll = roll(len(candidates), label)
                bystander = BystanderPick(
                    candidates=candidates,
                    chosen_id=candidates[pick_roll - 1],
                    label=label,
                    roll=pick_roll,
                    index=pick_roll - 1,
                    forced=False,
                )
            chosen = _by_id(room_occupants, bystander.chosen_id)
            effects_list.append(
                Effect(
                    kind="damage",
                    event_type="wild_swing_bystander",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=bystander.chosen_id,
                    target_kind=chosen.kind if chosen else None,
                    amount=BYSTANDER_DAMAGE,
                    room_id=room_id,
                    collateral=True,
                    credited_to=None,
                    cause="wild_swing_bystander",
                    accident=True,
                    public_text=(
                        f"{attacker.name}'s wild swing catches "
                        f"{chosen.name if chosen else bystander.chosen_id} "
                        f"for {BYSTANDER_DAMAGE}."
                    ),
                    payload={
                        "face_id": face.face_id,
                        **bystander.as_dict(),
                        "bystander_kind": chosen.kind if chosen else None,
                        "amount": BYSTANDER_DAMAGE,
                        "ignores_armor": True,
                        "ignores_guard": True,
                        "combat_table_version": COMBAT_TABLE_VERSION,
                    },
                )
            )
        else:
            fell_through = True
            resolved_as = "room_wears_it"
            bystander = BystanderPick(
                candidates=(), chosen_id=None, label=None, roll=None,
                index=None, forced=False,
            )
            effects_list.append(
                Effect(
                    kind="none",
                    event_type="wild_swing_no_bystander",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=None,
                    room_id=room_id,
                    cause="wild_swing_bystander",
                    public_text=(
                        f"{attacker.name}'s wild swing finds nobody else to blame."
                    ),
                    payload={
                        "face_id": face.face_id,
                        "candidates": [],
                        "fallback": "room_wears_it",
                        "combat_table_version": COMBAT_TABLE_VERSION,
                    },
                )
            )
            reaction, reaction_applied, room_effects = _room_wears_it(
                attacker, target, room_id, room_occupants, uses, face, fell_through=True
            )
            effects_list.extend(room_effects)
    else:  # room_wears_it
        reaction, reaction_applied, room_effects = _room_wears_it(
            attacker, target, room_id, room_occupants, uses, face, fell_through=False
        )
        effects_list.extend(room_effects)

    wild_swing = WildSwingOutcome(
        label=f"wildswing:{suffix}",
        roll=swing_roll,
        face=face,
        resolved_as=resolved_as,
        fell_through=fell_through,
        bystander=bystander,
        reaction=reaction,
        reaction_applied=reaction_applied,
    )
    miss_effect = Effect(
        kind="none",
        event_type="attack_miss",
        phase=attacker.kind,
        actor_id=attacker.id,
        target_id=target.id,
        target_kind=target.kind,
        room_id=room_id,
        cause="attack",
        public_text=(
            f"{attacker.name} swings at {target.name}, misses, and the arena "
            f"takes it personally."
        ),
        payload={
            "outcome": "miss",
            "attacker_kind": attacker.kind,
            "target_kind": target.kind,
            "room": room_id,
            "tohit": tohit.as_dict(),
            "wild_swing": wild_swing.as_dict(),
            "combat_table_version": COMBAT_TABLE_VERSION,
        },
    )
    resolution = AttackResolution(
        attacker_id=attacker.id,
        attacker_kind=attacker.kind,
        target_id=target.id,
        target_kind=target.kind,
        room_id=room_id,
        round_no=round_no,
        outcome="miss",
        tohit=tohit,
        damage=None,
        wild_swing=wild_swing,
        effects=tuple([miss_effect] + effects_list),
    )
    _assert_single_damage_per_body(resolution)
    return resolution


def _damage_calc(
    *, roll: int, label: str, eff_power: int, target_armor: int, target_guard: int
) -> DamageCalc:
    # Guard counts TWICE on purpose: once raising the to-hit DC and once
    # mitigating damage. That is what makes spending a turn on guard worth it
    # across a 12-round match. Do not "fix" it.
    raw = roll + eff_power - (target_armor + target_guard)
    return DamageCalc(
        label=label,
        roll=roll,
        effective_power=eff_power,
        target_armor=target_armor,
        target_guard=target_guard,
        raw=raw,
        amount=max(MINIMUM_DAMAGE, raw),
        minimum_applied=raw < MINIMUM_DAMAGE,
    )


def _you_wear_it(
    attacker: Combatant, room_id: str, face: WildSwingFace
) -> list[Effect]:
    droppable = items.droppable_item_ids(attacker.inventory)
    if droppable:
        item_id = droppable[0]  # deterministic: first in sorted inventory
        return [
            Effect(
                kind="drop_item",
                event_type="wild_swing_self_drop",
                phase="referee",
                actor_id=attacker.id,
                target_id=item_id,
                target_kind="item",
                item_id=item_id,
                room_id=room_id,
                collateral=False,
                credited_to=None,
                cause="wild_swing_self",
                accident=True,
                public_text=(
                    f"{attacker.name} loses grip on the "
                    f"{items.item_name(item_id)}."
                ),
                payload={
                    "face_id": face.face_id,
                    "selection": "first_in_sorted_inventory",
                    "inventory_before": sorted(attacker.inventory),
                    "item": items.describe_item(item_id),
                    "crown_transfer": item_id == items.CROWN_ID,
                    "combat_table_version": COMBAT_TABLE_VERSION,
                },
            )
        ]
    return [
        Effect(
            kind="damage",
            event_type="wild_swing_self_damage",
            phase="referee",
            actor_id=attacker.id,
            target_id=attacker.id,
            target_kind=attacker.kind,
            amount=EMPTY_HANDED_SELF_DAMAGE,
            room_id=room_id,
            collateral=True,
            credited_to=None,
            cause="wild_swing_self",
            accident=True,
            public_text=f"{attacker.name} wrenches something, empty-handed.",
            payload={
                "face_id": face.face_id,
                "reason": "empty_handed",
                "amount": EMPTY_HANDED_SELF_DAMAGE,
                "combat_table_version": COMBAT_TABLE_VERSION,
            },
        )
    ]


def _room_wears_it(
    attacker: Combatant,
    target: Combatant,
    room_id: str,
    room_occupants: Sequence[Combatant],
    uses: Mapping[str, int],
    face: WildSwingFace,
    *,
    fell_through: bool,
) -> tuple[RoomReaction, bool, list[Effect]]:
    reaction = ROOM_REACTIONS.get(room_id, DEFAULT_ROOM_REACTION)
    flavor = reaction.flavor.format(attacker=attacker.name, target=target.name)
    base_payload = {
        "face_id": "room_wears_it",
        "room": room_id,
        "reaction_id": reaction.reaction_id,
        "flavor": flavor,
        "effect_kind": reaction.effect_kind,
        "fell_through": fell_through,
        "combat_table_version": COMBAT_TABLE_VERSION,
    }

    if reaction.effect_kind == "strip_guard":
        # FINDING: stripping the ATTACKER's guard is dead code — guard is zeroed
        # for everyone at round start and only set by the guard action or the
        # invalid-action fallback, both of which preclude attacking that round.
        # So this strips the INTENDED TARGET's guard, which is a real effect.
        return (
            reaction,
            True,
            [
                Effect(
                    kind="strip_guard",
                    event_type="wild_swing_room_reaction",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=target.id,
                    target_kind=target.kind,
                    room_id=room_id,
                    collateral=False,
                    credited_to=None,
                    cause="room_reaction",
                    public_text=flavor,
                    payload={**base_payload, "target_id": target.id, "applied": True},
                )
            ],
        )

    if reaction.effect_kind == "reveal_item":
        exhausted = (
            reaction.max_uses > 0 and uses.get(room_id, 0) >= reaction.max_uses
        )
        if exhausted:
            return (
                reaction,
                False,
                [
                    Effect(
                        kind="none",
                        event_type="wild_swing_room_reaction",
                        phase="referee",
                        actor_id=attacker.id,
                        target_id=room_id,
                        target_kind="room",
                        room_id=room_id,
                        cause="room_reaction",
                        public_text=(
                            f"The {room_id.replace('_', ' ')} has nothing left to shed."
                        ),
                        payload={
                            **base_payload,
                            "effect_kind": "none",
                            "applied": False,
                            "exhausted": True,
                        },
                    )
                ],
            )
        return (
            reaction,
            True,
            [
                Effect(
                    kind="reveal_item",
                    event_type="wild_swing_room_reaction",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=room_id,
                    target_kind="room",
                    item_id=reaction.item_id,
                    room_id=room_id,
                    collateral=False,
                    credited_to=None,
                    cause="room_reaction",
                    public_text=flavor,
                    payload={
                        **base_payload,
                        "applied": True,
                        "effect": {"item": items.describe_item(reaction.item_id or "")},
                    },
                )
            ],
        )

    if reaction.effect_kind == "attacker_damage":
        return (
            reaction,
            True,
            [
                Effect(
                    kind="damage",
                    event_type="wild_swing_room_reaction",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=attacker.id,
                    target_kind=attacker.kind,
                    amount=reaction.amount,
                    room_id=room_id,
                    collateral=True,
                    credited_to=None,
                    cause="room_reaction",
                    accident=True,
                    public_text=flavor,
                    payload={**base_payload, "applied": True, "amount": reaction.amount},
                )
            ],
        )

    if reaction.effect_kind == "burst_damage":
        victims = sorted(
            body.id
            for body in room_occupants
            if body.alive and body.hp > 0 and body.id != attacker.id
        )
        effects = []
        for victim_id in victims:
            victim = _by_id(room_occupants, victim_id)
            effects.append(
                Effect(
                    kind="damage",
                    event_type="wild_swing_room_reaction",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=victim_id,
                    target_kind=victim.kind if victim else None,
                    amount=reaction.amount,
                    room_id=room_id,
                    collateral=True,
                    credited_to=None,
                    cause="room_reaction",
                    accident=True,
                    public_text=flavor,
                    payload={
                        **base_payload,
                        "applied": True,
                        "amount": reaction.amount,
                        "victims": victims,
                    },
                )
            )
        if effects:
            return reaction, True, effects
        return (
            reaction,
            False,
            [
                Effect(
                    kind="none",
                    event_type="wild_swing_room_reaction",
                    phase="referee",
                    actor_id=attacker.id,
                    target_id=room_id,
                    target_kind="room",
                    room_id=room_id,
                    cause="room_reaction",
                    public_text=flavor,
                    payload={**base_payload, "applied": False, "victims": []},
                )
            ],
        )

    return (
        reaction,
        False,
        [
            Effect(
                kind="none",
                event_type="wild_swing_room_reaction",
                phase="referee",
                actor_id=attacker.id,
                target_id=room_id,
                target_kind="room",
                room_id=room_id,
                cause="room_reaction",
                public_text=flavor,
                payload={**base_payload, "applied": False},
            )
        ],
    )


def _by_id(bodies: Sequence[Combatant], body_id: str | None) -> Combatant | None:
    for body in bodies:
        if body.id == body_id:
            return body
    return None


def _assert_single_damage_per_body(resolution: AttackResolution) -> None:
    """No body may take two damage effects in one resolution.

    Holds because a hit never rolls Wild Swing and the bystander candidate list
    excludes both the attacker and the intended target.
    """
    seen: set[str] = set()
    for effect in resolution.effects:
        if effect.kind != "damage" or effect.target_id is None:
            continue
        if effect.target_id in seen:
            raise AssertionError(
                f"{effect.target_id} takes two damage effects in one resolution"
            )
        seen.add(effect.target_id)


# ---------------------------------------------------------------------------
# monster tactics (deterministic; the v0.1 LLM call is gone)
# ---------------------------------------------------------------------------


def choose_monster_target(
    *,
    round_no: int,
    monster: Combatant,
    candidates: Sequence[Combatant],
    roll: Callable[[int, str], int],
) -> str:
    """Lowest HP wins; ties broken by a seeded roll over stable-sorted ids.

    A single tied id consumes NO roll.  Raises on an empty candidate list — the
    engine must skip monsters with no living agents in the room.
    """
    living = [body for body in candidates if body.alive and body.hp > 0]
    if not living:
        raise ValueError(f"{monster.id} has no living targets")
    lowest = min(body.hp for body in living)
    tied = sorted(body.id for body in living if body.hp == lowest)
    if len(tied) == 1:
        return tied[0]
    index = roll(len(tied), f"monster_target:r{round_no}:{monster.id}") - 1
    return tied[index]


def monster_hit_score(hits_this_round_before: int) -> int:
    """+1 per successful hit on a monster, capped at 3 per agent per round."""
    return 1 if hits_this_round_before < MONSTER_HIT_POINTS_PER_ROUND_CAP else 0


def finishing_blow_points(monster_id: str) -> int:
    if monster_id == WARDEN_ID:
        return WARDEN_FINISHING_BLOW_POINTS
    if monster_id in GUARDIAN_IDS:
        return GUARDIAN_FINISHING_BLOW_POINTS
    return 0
