"""
Dynamax and Max Battles.

Why this is a separate module with a different provenance to everything else:
none of it is in the game master. That file is checked and current, and it
contains no Dynamax data at all — Niantic keeps it server-side. So unlike
costs.py and pvp.py, which compute from Niantic's own numbers, this encodes
figures gathered from community documentation.

Two consequences worth keeping in mind:

  * The Max Particle costs are certain. They are fixed at 400 / 600 / 800 per
    level for every species, which is why the planner can cost particles
    exactly while asking you for one thing: the species' candy group.
  * The tier lists go stale. They carry a date. Treat them as a snapshot to
    check against, not a source of truth.

The internal-consistency test in the suite catches transcription errors:
fully upgrading all three moves on a group-1 Pokemon must come to 5,400 MP,
450 Candy and 120 Candy XL, which is published independently of the per-level
figures used to derive it.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_DATE = "2026-09"

# Max Particles per level. Identical for every species and every move slot.
PARTICLES = {1: 400, 2: 600, 3: 800}

# Candy per level by species cost group. Level 3 is paid in Candy XL.
CANDY_GROUPS = {
    1: {1: 50, 2: 100, 3: 0},
    2: {1: 60, 2: 110, 3: 0},
    3: {1: 70, 2: 120, 3: 0},
    4: {1: 80, 2: 130, 3: 0},
}
XL_GROUPS = {1: 40, 2: 45, 3: 50, 4: 55}

# What each level actually buys.
EFFECTS = {
    "attack": {1: "250 base power (350 Gigantamax)",
               2: "300 base power (400 Gigantamax)",
               3: "350 base power (450 Gigantamax)"},
    "guard":  {1: "+20 bonus HP", 2: "+40 bonus HP", 3: "+60 bonus HP"},
    "spirit": {1: "heals 8% of max HP to self and all allies",
               2: "heals 12% of max HP to self and all allies",
               3: "heals 16% of max HP to self and all allies"},
}

# Particle economy.
DAILY_PARTICLE_CAP = 800
PARTICLE_STORAGE_CAP = 1500
PARTICLES_PER_WALK = 300          # for 2 km, counts Adventure Sync
WALK_KM_FOR_PARTICLES = 2
POWER_SPOT_FIRST = 100            # first tap on a freshly activated spot
POWER_SPOT_REPEAT = 20

# Current tier lists. Snapshot — recheck rather than trust.
BEST_ATTACKERS = [
    ("Zacian Crowned Sword", 332, "STEEL", True),
    ("Gigantamax Inteleon", 262, "WATER", True),
    ("Gigantamax Gengar", 261, "GHOST", True),
    ("Gigantamax Kingler", 240, "WATER", True),
    ("Gigantamax Rillaboom", 239, "GRASS", True),
    ("Gigantamax Cinderace", 238, "FIRE", True),
    ("Gigantamax Machamp", 234, "FIGHTING", True),
    ("Gigantamax Grimmsnarl", 224, "DARK", True),
    ("Gigantamax Toxtricity", 224, "ELECTRIC", True),
    ("Gigantamax Charizard", 223, "FIRE", True),
]

BEST_DEFENDERS = [
    ("Regirock", 499), ("Regice", 499), ("Crowned Shield Zamazenta", 484),
    ("Registeel", 475), ("Suicune", 460), ("Latias", 436),
    ("Crowned Sword Zacian", 432), ("Metagross", 418),
    ("Corviknight", 413), ("Duraludon", 359),
]

BEST_HEALERS = [
    ("Blissey", 496), ("Wailord", 347), ("Snorlax", 330), ("Lapras", 277),
    ("Vaporeon", 277), ("Eternatus", 268), ("Greedent", 260),
    ("Entei", 251), ("Walrein", 242), ("Excadrill", 242),
]

ROLE_NOTES = {
    "attacker": ("Only comes out during the Max phase, so its Defense and HP "
                 "are irrelevant — it takes no damage. Wants a high Attack "
                 "stat and Max Attack levelled. Gigantamax is a large upgrade: "
                 "100 more base power at every level."),
    "defender": ("Does the work outside the Max phase, charging the meter with "
                 "fast moves. Wants high Defense and HP, useful resistances, "
                 "and ideally a 0.5-second fast move. Dynamax versus "
                 "Gigantamax makes no difference here. Wants Max Guard."),
    "healer":   ("Wants a high HP stat, because Max Spirit heals a percentage "
                 "of the user's max HP. Dynamax versus Gigantamax makes no "
                 "difference. Wants Max Spirit."),
}


@dataclass
class MaxCost:
    particles: int = 0
    candy: int = 0
    xl_candy: int = 0
    steps: int = 0
    notes: list[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []

    def dict(self) -> dict:
        return {"particles": self.particles, "candy": self.candy,
                "xl_candy": self.xl_candy, "steps": self.steps,
                "notes": self.notes}


def step_cost(group: int, to_level: int) -> MaxCost:
    """Cost of one Max Move level, for a species in the given cost group."""
    if group not in CANDY_GROUPS:
        raise ValueError(f"unknown cost group {group!r}; expected 1-4")
    if to_level not in PARTICLES:
        raise ValueError(f"Max Moves go to level 3, not {to_level}")
    return MaxCost(
        particles=PARTICLES[to_level],
        candy=CANDY_GROUPS[group][to_level],
        xl_candy=XL_GROUPS[group] if to_level == 3 else 0,
        steps=1,
    )


def upgrade_cost(group: int, from_level: int, to_level: int) -> MaxCost:
    """Cost of taking one move from one level to another. Level 0 is locked."""
    total = MaxCost()
    for lv in range(from_level + 1, to_level + 1):
        c = step_cost(group, lv)
        total.particles += c.particles
        total.candy += c.candy
        total.xl_candy += c.xl_candy
        total.steps += 1
    if total.xl_candy:
        total.notes.append("Level 3 is paid in Candy XL, which needs trainer level 31.")
    return total


def full_build(group: int, current: dict[str, int] | None = None) -> MaxCost:
    """Cost of taking all three Max Moves to level 3.

    Every Dynamax Pokemon starts with Max Attack at level 1 and the other two
    locked, so that is the default starting point.
    """
    current = current or {"attack": 1, "guard": 0, "spirit": 0}
    total = MaxCost()
    for slot in ("attack", "guard", "spirit"):
        c = upgrade_cost(group, current.get(slot, 0), 3)
        total.particles += c.particles
        total.candy += c.candy
        total.xl_candy += c.xl_candy
        total.steps += c.steps
    return total


def days_of_particles(particles: int, walking: bool = True) -> float:
    """How many days of collecting a particle total represents.

    The daily cap is the binding constraint on Max Battles, not candy or dust.
    Assumes you hit the cap, which needs real effort at Power Spots.
    """
    per_day = DAILY_PARTICLE_CAP + (PARTICLES_PER_WALK if walking else 0)
    return round(particles / per_day, 1)


def max_attack_type(is_gigantamax: bool, fast_move_type: str | None) -> str:
    """What type the Max Attack will be.

    Gigantamax Pokemon have a fixed type. Dynamax Pokemon inherit the type of
    whichever fast move they currently have, so a Fast TM retypes the Max
    Attack — and does not reset any Max Move levels.
    """
    if is_gigantamax:
        return "fixed by species"
    if not fast_move_type:
        return "unknown — depends on the current fast move"
    return fast_move_type.upper()
