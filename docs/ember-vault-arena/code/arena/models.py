from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


RULESET_VERSION = "ember-vault-0.2"

BUILDS: dict[str, dict[str, int]] = {
    "vanguard": {"max_hp": 15, "power": 3, "armor": 2, "speed": 0, "search": 0},
    "scout": {"max_hp": 11, "power": 2, "armor": 1, "speed": 3, "search": 2},
    "mystic": {"max_hp": 11, "power": 3, "armor": 1, "speed": 1, "search": 1},
    "scoundrel": {"max_hp": 12, "power": 2, "armor": 1, "speed": 2, "search": 1},
}

OBJECTIVES = {
    "monster_hunter",
    "lorekeeper",
    "oathbreaker",
    "treasure_hoarder",
}

# "step" is intra-room tactical movement to a tile; "move" remains room-to-room
# transit. Keeping them separate leaves every existing move rule and test intact
# instead of overloading one action with two meanings.
ACTIONS = {
    "move", "step", "attack", "guard", "search", "interact", "take", "use", "rest",
}


class ValidationError(ValueError):
    pass


def _bounded_text(value: Any, field: str, maximum: int, minimum: int = 0) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    value = value.strip()
    if len(value) < minimum or len(value) > maximum:
        raise ValidationError(f"{field} must be {minimum}..{maximum} characters")
    return value


@dataclass(frozen=True)
class AgentManifest:
    id: str
    name: str
    system_prompt: str
    personality: str
    strategy: str
    build: str
    secret_objective: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AgentManifest":
        if not isinstance(raw, dict):
            raise ValidationError("agent manifest must be an object")
        expected = {
            "id",
            "name",
            "system_prompt",
            "personality",
            "strategy",
            "build",
            "secret_objective",
        }
        unknown = set(raw) - expected
        if unknown:
            raise ValidationError(f"unknown manifest fields: {sorted(unknown)}")
        build = _bounded_text(raw.get("build"), "build", 32, 1).lower()
        objective = _bounded_text(
            raw.get("secret_objective"), "secret_objective", 32, 1
        ).lower()
        if build not in BUILDS:
            raise ValidationError(f"build must be one of {sorted(BUILDS)}")
        if objective not in OBJECTIVES:
            raise ValidationError(
                f"secret_objective must be one of {sorted(OBJECTIVES)}"
            )
        agent_id = _bounded_text(raw.get("id"), "id", 40, 3)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", agent_id):
            raise ValidationError("id may contain only letters, numbers, _ and -")
        return cls(
            id=agent_id,
            name=_bounded_text(raw.get("name"), "name", 40, 2),
            system_prompt=_bounded_text(
                raw.get("system_prompt"), "system_prompt", 2_000, 10
            ),
            personality=_bounded_text(raw.get("personality"), "personality", 500, 3),
            strategy=_bounded_text(raw.get("strategy"), "strategy", 1_000, 3),
            build=build,
            secret_objective=objective,
        )

    def public_dict(self, reveal_secret: bool = False) -> dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "personality": self.personality,
            "build": self.build,
        }
        if reveal_secret:
            result.update(
                {
                    "system_prompt": self.system_prompt,
                    "strategy": self.strategy,
                    "secret_objective": self.secret_objective,
                }
            )
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "personality": self.personality,
            "strategy": self.strategy,
            "build": self.build,
            "secret_objective": self.secret_objective,
        }


@dataclass(frozen=True)
class AgentAction:
    action: str
    target: str | None = None
    destination: str | None = None
    item: str | None = None
    tile: tuple[int, int] | None = None
    speech: str = ""
    reasoning_summary: str = ""
    memory_write: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AgentAction":
        if not isinstance(raw, dict):
            raise ValidationError("action output must be an object")
        expected = {
            "action",
            "target",
            "destination",
            "item",
            "tile",
            "speech",
            "reasoning_summary",
            "memory_write",
        }
        unknown = set(raw) - expected
        if unknown:
            raise ValidationError(f"unknown action fields: {sorted(unknown)}")
        action = _bounded_text(raw.get("action"), "action", 20, 1).lower()
        if action not in ACTIONS:
            raise ValidationError(f"action must be one of {sorted(ACTIONS)}")

        def optional(field: str, maximum: int) -> str | None:
            value = raw.get(field)
            if value is None:
                return None
            return _bounded_text(value, field, maximum)

        tile_raw = raw.get("tile")
        tile: tuple[int, int] | None = None
        if tile_raw is not None:
            # Accept [x, y] only. A tile is coordinates, not free text, so it is
            # validated here rather than trusted downstream.
            if (
                not isinstance(tile_raw, (list, tuple))
                or len(tile_raw) != 2
                or not all(isinstance(v, int) and not isinstance(v, bool) for v in tile_raw)
            ):
                raise ValidationError("tile must be [x, y] integers")
            if not all(0 <= v < 32 for v in tile_raw):
                raise ValidationError("tile coordinates out of range")
            tile = (int(tile_raw[0]), int(tile_raw[1]))

        return cls(
            action=action,
            target=optional("target", 64),
            destination=optional("destination", 32),
            item=optional("item", 64),
            tile=tile,
            speech=_bounded_text(raw.get("speech", ""), "speech", 120),
            reasoning_summary=_bounded_text(
                raw.get("reasoning_summary", ""), "reasoning_summary", 240
            ),
            memory_write=_bounded_text(
                raw.get("memory_write", ""), "memory_write", 160
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "destination": self.destination,
            "item": self.item,
            "tile": list(self.tile) if self.tile else None,
            "speech": self.speech,
            "reasoning_summary": self.reasoning_summary,
            "memory_write": self.memory_write,
        }


@dataclass(frozen=True)
class ProviderResult:
    raw_output: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
