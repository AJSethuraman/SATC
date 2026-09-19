from __future__ import annotations

"""Typed contracts: the brain a player submits and the action a model returns.

Versioned from the first commit of the rebuild (PRD §5.41). The ruleset version
stays at ember-vault-0.2 until M3 changes the rules; the ACTION and MANIFEST
schema versions move here, now, because a stored match is only replayable by a
reader that knows the shape of what was stored.

agent-action-1.2 (PRD §5.14, §5.19, §5.42):
  action + target/destination/item/tile as before, plus ``give``;
  speech is an object {mode: say|whisper|silent, to, text<=300};
  note is {objective<=120, reads<=4 of {who, stance, why<=60}};
  fallback is the second choice: the five action slots, or null;
  deal is an offer or an accept, or null (opened 18 Sep 2026, M3): an offer
  names who it is to and one of truce (rounds 1-6), share_item (item,
  by_round) or escort (destination, by_round); an accept names an open
  offer's id. The referee records deals and their breaks and enforces nothing.
  Until 1.2 a non-null deal was refused with the reason, which was the honest
  version of "not built yet".
  reasoning_summary and memory_write are gone; the note replaced both.
"""

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any


RULESET_VERSION = "ember-vault-0.5"
ACTION_SCHEMA_VERSION = "agent-action-1.2"
MANIFEST_SCHEMA_VERSION = "agent-manifest-1.0"

BUILDS: dict[str, dict[str, int]] = {
    "vanguard": {"max_hp": 15, "power": 3, "armor": 2, "speed": 0, "search": 0},
    "scout": {"max_hp": 11, "power": 2, "armor": 1, "speed": 3, "search": 2},
    "mystic": {"max_hp": 11, "power": 3, "armor": 1, "speed": 1, "search": 1},
    "scoundrel": {"max_hp": 12, "power": 2, "armor": 1, "speed": 2, "search": 1},
}

# A talker (PRD §5.25): a house side character on the same contract with a
# restricted legal set. It has a body, so it has numbers, modest ones; it
# cannot score, carry the Crown, search or win.
TALKER_STATS: dict[str, int] = {"max_hp": 10, "power": 1, "armor": 1, "speed": 1, "search": 0}
TALKER_ACTIONS = frozenset({"move", "give", "guard"})
TALKERS_MAX = 3

OBJECTIVES = {
    "monster_hunter",
    "lorekeeper",
    "oathbreaker",
    "treasure_hoarder",
}

# "step" is intra-room tactical movement to a tile; "move" remains room-to-room
# transit. "give" hands one carried item to another body in the same room.
ACTIONS = {
    "move", "step", "attack", "guard", "search", "interact", "take", "use", "rest",
    "give",
}

KINDS = {"character", "talker"}
BRAIN_SECTIONS = ("voice", "wants", "treats", "never")
BRAIN_CAP = 2_000            # total characters across the four sections
SPEECH_MODES = {"say", "whisper", "silent"}
SPEECH_CAP = 300
NOTE_OBJECTIVE_CAP = 120
NOTE_READS_MAX = 4
NOTE_WHY_CAP = 60
STANCES = {"trust", "distrust", "unknown"}
DEAL_KINDS = {"offer", "accept"}
DEAL_TYPES = {"truce", "share_item", "escort"}
TRUCE_ROUNDS_MIN = 1
TRUCE_ROUNDS_MAX = 6
ID_PATTERN = r"[A-Za-z0-9_-]+"


class ValidationError(ValueError):
    pass


def _bounded_text(value: Any, field_name: str, maximum: int, minimum: int = 0) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    value = value.strip()
    if len(value) < minimum or len(value) > maximum:
        raise ValidationError(f"{field_name} must be {minimum}..{maximum} characters")
    return value


def _id(value: Any, field_name: str, maximum: int = 40, minimum: int = 3) -> str:
    text = _bounded_text(value, field_name, maximum, minimum)
    if not re.fullmatch(ID_PATTERN, text):
        raise ValidationError(f"{field_name} may contain only letters, numbers, _ and -")
    return text


def default_objective(agent_id: str) -> str:
    """A secret objective chosen from the id when the brain names none: the
    same brain always gets the same one, and nothing about a match seed leaks
    into it."""
    digest = hashlib.sha256(f"objective:{agent_id}".encode("utf-8")).hexdigest()
    ordered = sorted(OBJECTIVES)
    return ordered[int(digest[:8], 16) % len(ordered)]


@dataclass(frozen=True)
class AgentManifest:
    """A brain (kind=character) or a house side character (kind=talker).

    Characters carry the four player-written sections and a build. Talkers
    carry an agenda, what they know and what they hold; they have no build and
    cannot win. Talkers are validated here and refused by the engine until M3
    builds their legal set (PRD §5.25).
    """

    id: str
    name: str
    build: str
    secret_objective: str
    voice: str
    wants: str
    treats: str
    never: str
    kind: str = "character"
    agenda: str = ""
    knows: tuple[str, ...] = ()
    holds: tuple[str, ...] = ()
    start: str | None = None

    _CHARACTER_FIELDS = frozenset(
        {"id", "name", "build", "secret_objective", "kind", *BRAIN_SECTIONS}
    )
    _TALKER_FIELDS = frozenset(
        {"id", "name", "kind", "voice", "agenda", "knows", "holds", "start"}
    )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AgentManifest":
        if not isinstance(raw, dict):
            raise ValidationError("agent manifest must be an object")
        kind = _bounded_text(raw.get("kind", "character"), "kind", 16, 1).lower()
        if kind not in KINDS:
            raise ValidationError(f"kind must be one of {sorted(KINDS)}")
        allowed = cls._CHARACTER_FIELDS if kind == "character" else cls._TALKER_FIELDS
        unknown = set(raw) - allowed
        if unknown:
            raise ValidationError(f"unknown manifest fields for a {kind}: {sorted(unknown)}")
        agent_id = _id(raw.get("id"), "id")
        name = _bounded_text(raw.get("name"), "name", 40, 2)
        if kind == "talker":
            return cls(
                id=agent_id, name=name, build="", secret_objective="",
                voice=_bounded_text(raw.get("voice"), "voice", 1_000, 1),
                wants="", treats="", never="", kind="talker",
                agenda=_bounded_text(raw.get("agenda"), "agenda", 1_000, 1),
                knows=tuple(_bounded_text(k, "knows[]", 200, 1) for k in (raw.get("knows") or ())),
                holds=tuple(_id(h, "holds[]", 64, 1) for h in (raw.get("holds") or ())),
                start=None if raw.get("start") is None else _id(raw.get("start"), "start", 32, 1),
            )
        build = _bounded_text(raw.get("build"), "build", 32, 1).lower()
        if build not in BUILDS:
            raise ValidationError(f"build must be one of {sorted(BUILDS)}")
        objective_raw = raw.get("secret_objective")
        if objective_raw is None or objective_raw == "":
            objective = default_objective(agent_id)
        else:
            objective = _bounded_text(objective_raw, "secret_objective", 32, 1).lower()
            if objective not in OBJECTIVES:
                raise ValidationError(f"secret_objective must be one of {sorted(OBJECTIVES)}")
        sections = {s: _bounded_text(raw.get(s), s, BRAIN_CAP, 1) for s in BRAIN_SECTIONS}
        total = sum(len(v) for v in sections.values())
        if total > BRAIN_CAP:
            longest = max(sections, key=lambda s: len(sections[s]))
            raise ValidationError(
                f"brain is {total} characters across its four sections; the cap is "
                f"{BRAIN_CAP}. Over by {total - BRAIN_CAP}; the longest section is "
                f"'{longest}' at {len(sections[longest])}."
            )
        return cls(
            id=agent_id, name=name, build=build, secret_objective=objective,
            voice=sections["voice"], wants=sections["wants"],
            treats=sections["treats"], never=sections["never"], kind="character",
        )

    @property
    def brain_text(self) -> str:
        return "\n\n".join(f"{s.upper()}: {getattr(self, s)}" for s in BRAIN_SECTIONS)

    def public_dict(self, reveal_secret: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id, "name": self.name, "kind": self.kind, "build": self.build,
        }
        if reveal_secret:
            result.update({s: getattr(self, s) for s in BRAIN_SECTIONS})
            result["secret_objective"] = self.secret_objective
            if self.kind == "talker":
                result.update({"agenda": self.agenda, "knows": list(self.knows),
                               "holds": list(self.holds), "start": self.start})
        return result

    def as_dict(self) -> dict[str, Any]:
        if self.kind == "talker":
            return {
                "id": self.id, "name": self.name, "kind": "talker", "voice": self.voice,
                "agenda": self.agenda, "knows": list(self.knows), "holds": list(self.holds),
                "start": self.start,
            }
        return {
            "id": self.id, "name": self.name, "kind": "character", "build": self.build,
            "secret_objective": self.secret_objective,
            **{s: getattr(self, s) for s in BRAIN_SECTIONS},
        }

    # July callers read these three; keep them readable so the seam holds.
    @property
    def system_prompt(self) -> str:
        return self.brain_text

    @property
    def personality(self) -> str:
        return self.voice

    @property
    def strategy(self) -> str:
        return self.wants


@dataclass(frozen=True)
class Speech:
    mode: str = "silent"
    to: str | None = None
    text: str = ""

    @classmethod
    def from_raw(cls, raw: Any) -> "Speech":
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise ValidationError("speech must be an object {mode, to, text}")
        unknown = set(raw) - {"mode", "to", "text"}
        if unknown:
            raise ValidationError(f"unknown speech fields: {sorted(unknown)}")
        mode = _bounded_text(raw.get("mode", "silent"), "speech.mode", 16, 1).lower()
        if mode not in SPEECH_MODES:
            raise ValidationError(f"speech.mode must be one of {sorted(SPEECH_MODES)}")
        text = _bounded_text(raw.get("text", ""), "speech.text", SPEECH_CAP)
        to = raw.get("to")
        if mode == "whisper":
            if to is None:
                raise ValidationError("a whisper needs speech.to")
            to = _id(to, "speech.to", 64, 1)
        elif to not in (None, ""):
            raise ValidationError(f"speech.to is only for a whisper, not a {mode}")
        else:
            to = None
        if mode == "silent" and text:
            raise ValidationError("silent speech carries no text")
        if mode != "silent" and not text:
            raise ValidationError(f"a {mode} needs speech.text")
        return cls(mode=mode, to=to, text=text)

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "to": self.to, "text": self.text}


@dataclass(frozen=True)
class Read:
    who: str
    stance: str
    why: str

    def as_dict(self) -> dict[str, Any]:
        return {"who": self.who, "stance": self.stance, "why": self.why}


@dataclass(frozen=True)
class Note:
    """The private note: the only model-written memory. Rewritten every turn,
    carried forward, shown to the audience the moment it is written, never to a
    rival (PRD §5.23-24)."""

    objective: str = ""
    reads: tuple[Read, ...] = ()

    @classmethod
    def from_raw(cls, raw: Any) -> "Note":
        if not isinstance(raw, dict):
            raise ValidationError("note must be an object {objective, reads}")
        unknown = set(raw) - {"objective", "reads"}
        if unknown:
            raise ValidationError(f"unknown note fields: {sorted(unknown)}")
        objective = _bounded_text(raw.get("objective", ""), "note.objective", NOTE_OBJECTIVE_CAP)
        reads_raw = raw.get("reads", [])
        if not isinstance(reads_raw, list):
            raise ValidationError("note.reads must be a list")
        if len(reads_raw) > NOTE_READS_MAX:
            raise ValidationError(f"note.reads holds at most {NOTE_READS_MAX} entries")
        reads = []
        for entry in reads_raw:
            if not isinstance(entry, dict) or set(entry) - {"who", "stance", "why"}:
                raise ValidationError("each read is {who, stance, why}")
            stance = _bounded_text(entry.get("stance", "unknown"), "read.stance", 16, 1).lower()
            if stance not in STANCES:
                raise ValidationError(f"read.stance must be one of {sorted(STANCES)}")
            reads.append(Read(
                who=_id(entry.get("who"), "read.who", 64, 1),
                stance=stance,
                why=_bounded_text(entry.get("why", ""), "read.why", NOTE_WHY_CAP),
            ))
        return cls(objective=objective, reads=tuple(reads))

    def as_dict(self) -> dict[str, Any]:
        return {"objective": self.objective, "reads": [r.as_dict() for r in self.reads]}


def _optional_text(raw: dict[str, Any], field_name: str, maximum: int, prefix: str = "") -> str | None:
    value = raw.get(field_name)
    if value is None:
        return None
    return _bounded_text(value, prefix + field_name, maximum)


def _parse_tile(tile_raw: Any, label: str = "tile") -> tuple[int, int] | None:
    if tile_raw is None:
        return None
    if (
        not isinstance(tile_raw, (list, tuple))
        or len(tile_raw) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in tile_raw)
    ):
        raise ValidationError(f"{label} must be [x, y] integers")
    if not all(0 <= v < 32 for v in tile_raw):
        raise ValidationError(f"{label} coordinates out of range")
    return (int(tile_raw[0]), int(tile_raw[1]))


@dataclass(frozen=True)
class Deal:
    """An offer or an accept (PRD §5.19), flat: every slot is present and the
    ones that do not belong to the kind and type are null. The referee
    records it, never enforces it, and a bad one is lost with the reason."""

    kind: str
    to: str | None = None
    type: str | None = None
    rounds: int | None = None
    item: str | None = None
    destination: str | None = None
    by_round: int | None = None
    offer_id: str | None = None

    _SLOTS = ("kind", "to", "type", "rounds", "item", "destination", "by_round", "offer_id")
    _NEEDS = {"truce": ("rounds",), "share_item": ("item", "by_round"), "escort": ("destination", "by_round")}

    @classmethod
    def from_raw(cls, raw: Any) -> "Deal | None":
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ValidationError("deal must be an object or null")
        unknown = set(raw) - set(cls._SLOTS)
        if unknown:
            raise ValidationError(f"unknown deal fields: {sorted(unknown)}")
        kind = _bounded_text(raw.get("kind"), "deal.kind", 8, 1).lower()
        if kind not in DEAL_KINDS:
            raise ValidationError(f"deal.kind must be one of {sorted(DEAL_KINDS)}")

        def integer(name: str, low: int, high: int) -> int | None:
            value = raw.get(name)
            if value is None:
                return None
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                raise ValidationError(f"deal.{name} must be an integer from {low} to {high}")
            return value

        def ident(name: str) -> str | None:
            return None if raw.get(name) is None else _id(raw.get(name), f"deal.{name}", 64, 1)

        to, item, offer_id = ident("to"), ident("item"), ident("offer_id")
        type_ = None if raw.get("type") is None else _bounded_text(raw.get("type"), "deal.type", 16, 1).lower()
        rounds = integer("rounds", TRUCE_ROUNDS_MIN, TRUCE_ROUNDS_MAX)
        destination = _optional_text(raw, "destination", 32, "deal.")
        by_round = integer("by_round", 1, 9_999)
        if kind == "offer":
            if not to:
                raise ValidationError("deal.to names who the offer is made to")
            if type_ not in DEAL_TYPES:
                raise ValidationError(f"deal.type must be one of {sorted(DEAL_TYPES)}")
            if offer_id is not None:
                raise ValidationError("deal.offer_id belongs to an accept, not an offer")
            needs = cls._NEEDS[type_]
            for slot in ("rounds", "item", "destination", "by_round"):
                present = raw.get(slot) is not None
                if slot in needs and not present:
                    raise ValidationError(f"a {type_} offer needs deal.{slot}")
                if slot not in needs and present:
                    raise ValidationError(f"deal.{slot} does not belong to a {type_} offer")
        else:
            if not offer_id:
                raise ValidationError("deal.offer_id names the open offer you accept")
            for slot in ("to", "type", "rounds", "item", "destination", "by_round"):
                if raw.get(slot) is not None:
                    raise ValidationError(f"deal.{slot} does not belong to an accept")
        return cls(kind=kind, to=to, type=type_, rounds=rounds, item=item, destination=destination,
                   by_round=by_round, offer_id=offer_id)

    def as_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self._SLOTS}


@dataclass(frozen=True)
class SecondChoice:
    """The brain's second choice (PRD §5.42, ruled 18 Sep 2026, docket D11):
    the five action slots and nothing else, used by the referee only when the
    first choice is stale at resolution -- someone took the item, lit the
    seal, killed the target or stood on the tile first. A stale second choice
    is a stale turn; there is no third."""

    action: str
    target: str | None = None
    destination: str | None = None
    item: str | None = None
    tile: tuple[int, int] | None = None

    _SLOTS = ("action", "target", "destination", "item", "tile")

    @classmethod
    def from_raw(cls, raw: Any) -> "SecondChoice | None":
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ValidationError("fallback must be an object or null")
        unknown = set(raw) - set(cls._SLOTS)
        if unknown:
            raise ValidationError(f"unknown fallback fields: {sorted(unknown)}")
        action = _bounded_text(raw.get("action"), "fallback.action", 20, 1).lower()
        if action not in ACTIONS:
            raise ValidationError(f"fallback.action must be one of {sorted(ACTIONS)}")
        return cls(
            action=action,
            target=_optional_text(raw, "target", 64, "fallback."),
            destination=_optional_text(raw, "destination", 32, "fallback."),
            item=_optional_text(raw, "item", 64, "fallback."),
            tile=_parse_tile(raw.get("tile"), "fallback.tile"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"action": self.action, "target": self.target, "destination": self.destination,
                "item": self.item, "tile": list(self.tile) if self.tile else None}


@dataclass(frozen=True)
class AgentAction:
    action: str
    target: str | None = None
    destination: str | None = None
    item: str | None = None
    tile: tuple[int, int] | None = None
    speech: Speech = field(default_factory=Speech)
    note: Note = field(default_factory=Note)
    deal: Deal | None = None
    fallback: SecondChoice | None = None

    _FIELDS = frozenset({
        "action", "target", "destination", "item", "tile", "speech", "note", "deal", "fallback",
    })

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AgentAction":
        if not isinstance(raw, dict):
            raise ValidationError("action output must be an object")
        unknown = set(raw) - cls._FIELDS
        if unknown:
            raise ValidationError(f"unknown action fields: {sorted(unknown)}")
        action = _bounded_text(raw.get("action"), "action", 20, 1).lower()
        if action not in ACTIONS:
            raise ValidationError(f"action must be one of {sorted(ACTIONS)}")

        def optional(field_name: str, maximum: int) -> str | None:
            value = raw.get(field_name)
            if value is None:
                return None
            return _bounded_text(value, field_name, maximum)

        tile_raw = raw.get("tile")
        tile: tuple[int, int] | None = None
        if tile_raw is not None:
            if (
                not isinstance(tile_raw, (list, tuple))
                or len(tile_raw) != 2
                or not all(isinstance(v, int) and not isinstance(v, bool) for v in tile_raw)
            ):
                raise ValidationError("tile must be [x, y] integers")
            if not all(0 <= v < 32 for v in tile_raw):
                raise ValidationError("tile coordinates out of range")
            tile = (int(tile_raw[0]), int(tile_raw[1]))

        if "note" not in raw:
            raise ValidationError("note is required: {objective, reads}")
        return cls(
            action=action,
            target=optional("target", 64),
            destination=optional("destination", 32),
            item=optional("item", 64),
            tile=tile,
            speech=Speech.from_raw(raw.get("speech")),
            note=Note.from_raw(raw.get("note")),
            deal=Deal.from_raw(raw.get("deal")),
            fallback=SecondChoice.from_raw(raw.get("fallback")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "destination": self.destination,
            "item": self.item,
            "tile": list(self.tile) if self.tile else None,
            "speech": self.speech.as_dict(),
            "note": self.note.as_dict(),
            "deal": self.deal.as_dict() if self.deal else None,
            "fallback": self.fallback.as_dict() if self.fallback else None,
        }

    def second(self) -> "AgentAction | None":
        """The second choice as a resolvable action: the five slots from the
        fallback, the speech and the deal already spent, the note unchanged."""
        if not self.fallback:
            return None
        return AgentAction(
            action=self.fallback.action, target=self.fallback.target, destination=self.fallback.destination,
            item=self.fallback.item, tile=self.fallback.tile,
            speech=Speech(), note=self.note, deal=None, fallback=None,
        )


def action_json_schema() -> dict[str, Any]:
    """The output contract as JSON Schema draft-07 -- the draft the Agent SDK
    validates against, and one the Messages API accepts. Generated from the
    same constants the validator uses so the two cannot drift (tenet S8);
    ``schemas/agent-action.schema.json`` is the pinned copy and a test compares."""
    ident = {"type": "string", "pattern": f"^{ID_PATTERN}$", "maxLength": 64}
    nullable_ident = {"type": ["string", "null"], "maxLength": 64}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://ember-vault-arena.local/schemas/{ACTION_SCHEMA_VERSION}.json",
        "title": "Agent Action",
        "description": ACTION_SCHEMA_VERSION,
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "target", "destination", "item", "tile", "speech", "note", "deal", "fallback"],
        "properties": {
            "action": {"type": "string", "enum": sorted(ACTIONS)},
            "target": nullable_ident,
            "destination": {"type": ["string", "null"], "maxLength": 32},
            "item": nullable_ident,
            "tile": {
                "type": ["array", "null"],
                "items": {"type": "integer", "minimum": 0, "maximum": 31},
                "minItems": 2, "maxItems": 2,
            },
            "speech": {
                "type": "object",
                "additionalProperties": False,
                "required": ["mode", "to", "text"],
                "properties": {
                    "mode": {"type": "string", "enum": sorted(SPEECH_MODES)},
                    "to": nullable_ident,
                    "text": {"type": "string", "maxLength": SPEECH_CAP},
                },
            },
            "note": {
                "type": "object",
                "additionalProperties": False,
                "required": ["objective", "reads"],
                "properties": {
                    "objective": {"type": "string", "maxLength": NOTE_OBJECTIVE_CAP},
                    "reads": {
                        "type": "array",
                        "maxItems": NOTE_READS_MAX,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["who", "stance", "why"],
                            "properties": {
                                "who": ident,
                                "stance": {"type": "string", "enum": sorted(STANCES)},
                                "why": {"type": "string", "maxLength": NOTE_WHY_CAP},
                            },
                        },
                    },
                },
            },
            "deal": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "required": ["kind", "to", "type", "rounds", "item", "destination", "by_round", "offer_id"],
                "properties": {
                    "kind": {"type": "string", "enum": sorted(DEAL_KINDS)},
                    "to": nullable_ident,
                    "type": {"type": ["string", "null"], "enum": sorted(DEAL_TYPES) + [None]},
                    "rounds": {"type": ["integer", "null"], "minimum": TRUCE_ROUNDS_MIN, "maximum": TRUCE_ROUNDS_MAX},
                    "item": nullable_ident,
                    "destination": {"type": ["string", "null"], "maxLength": 32},
                    "by_round": {"type": ["integer", "null"], "minimum": 1},
                    "offer_id": nullable_ident,
                },
            },
            "fallback": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "required": ["action", "target", "destination", "item", "tile"],
                "properties": {
                    "action": {"type": "string", "enum": sorted(ACTIONS)},
                    "target": nullable_ident,
                    "destination": {"type": ["string", "null"], "maxLength": 32},
                    "item": nullable_ident,
                    "tile": {
                        "type": ["array", "null"],
                        "items": {"type": "integer", "minimum": 0, "maximum": 31},
                        "minItems": 2, "maxItems": 2,
                    },
                },
            },
        },
    }


def manifest_json_schema() -> dict[str, Any]:
    section = {"type": "string", "minLength": 1, "maxLength": BRAIN_CAP}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://ember-vault-arena.local/schemas/{MANIFEST_SCHEMA_VERSION}.json",
        "title": "Agent Manifest",
        "description": (
            f"{MANIFEST_SCHEMA_VERSION}. A character's four sections together must "
            f"total at most {BRAIN_CAP} characters; that cap is enforced by the "
            f"loader, since JSON Schema cannot sum lengths."
        ),
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "build", *BRAIN_SECTIONS],
                "properties": {
                    "id": {"type": "string", "pattern": f"^{ID_PATTERN}$", "minLength": 3, "maxLength": 40},
                    "name": {"type": "string", "minLength": 2, "maxLength": 40},
                    "kind": {"type": "string", "enum": ["character"]},
                    "build": {"type": "string", "enum": sorted(BUILDS)},
                    "secret_objective": {"type": ["string", "null"], "enum": [*sorted(OBJECTIVES), None]},
                    **{s: section for s in BRAIN_SECTIONS},
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "kind", "voice", "agenda"],
                "properties": {
                    "id": {"type": "string", "pattern": f"^{ID_PATTERN}$", "minLength": 3, "maxLength": 40},
                    "name": {"type": "string", "minLength": 2, "maxLength": 40},
                    "kind": {"type": "string", "enum": ["talker"]},
                    "voice": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "agenda": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "knows": {"type": "array", "items": {"type": "string", "maxLength": 200}},
                    "holds": {"type": "array", "items": {"type": "string", "maxLength": 64}},
                    "start": {"type": ["string", "null"], "maxLength": 32},
                },
            },
        ],
    }


@dataclass(frozen=True)
class ProviderResult:
    """What came back across the provider seam, with everything the match log
    records about the call (PRD §5.31). The first five fields are July's and
    stay positional so July's tests keep constructing it."""

    raw_output: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    latency_ms: float = 0.0
    retries: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None
    cost_source: str = "none"          # provider_usage | sdk_estimate | none
    stop_reason: str | None = None
    request_id: str | None = None
    error_kind: str | None = None      # panic | network | None
    request_digest: str | None = None
    response_digest: str | None = None
    effort: str | None = None
    cache_creation_tokens: int = 0   # input written to the cache on this call (1.25x for 5m, 2x for 1h)
    cache_creation_1h_tokens: int = 0  # the part of cache_creation_tokens written at the 1-hour rate
    usage_json: str | None = None    # the provider's per-model usage, verbatim, for pricing and audit
