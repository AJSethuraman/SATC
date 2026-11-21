"""Which weapon skills each class can train.

The list is Classic's (WoW 1.12). Blizzard's Forever API has no such data (docs/PROJECT.md, Verified
2026-11-13), so the list is NOT confirmed for Forever and the bot says so. What members actually wield is
the evidence: a character cannot equip a weapon it has no skill for, so a weapon seen on a member proves
that class can use it here, whatever the list says.
"""
from __future__ import annotations

SKILLS = ("One-Handed Axes", "Two-Handed Axes", "One-Handed Maces", "Two-Handed Maces", "One-Handed Swords",
          "Two-Handed Swords", "Daggers", "Fist Weapons", "Polearms", "Staves", "Bows", "Crossbows", "Guns",
          "Thrown", "Wands")

_RANGED = ("Bows", "Crossbows", "Guns", "Thrown")
CLASSIC = {
    "Warrior": set(SKILLS) - {"Wands"},
    "Paladin": {"One-Handed Axes", "Two-Handed Axes", "One-Handed Maces", "Two-Handed Maces", "One-Handed Swords",
                "Two-Handed Swords", "Polearms"},
    "Hunter": {"One-Handed Axes", "Two-Handed Axes", "One-Handed Swords", "Two-Handed Swords", "Daggers",
               "Fist Weapons", "Polearms", "Staves", *_RANGED},
    "Rogue": {"One-Handed Swords", "One-Handed Maces", "Daggers", "Fist Weapons", *_RANGED},
    "Priest": {"One-Handed Maces", "Daggers", "Staves", "Wands"},
    "Shaman": {"One-Handed Axes", "Two-Handed Axes", "One-Handed Maces", "Two-Handed Maces", "Daggers",
               "Fist Weapons", "Staves"},
    "Mage": {"One-Handed Swords", "Daggers", "Staves", "Wands"},
    "Warlock": {"One-Handed Swords", "Daggers", "Staves", "Wands"},
    "Druid": {"One-Handed Maces", "Two-Handed Maces", "Daggers", "Fist Weapons", "Staves"},
}
NOTES = {("Shaman", "Two-Handed Axes"): "needs the Enhancement talent",
         ("Shaman", "Two-Handed Maces"): "needs the Enhancement talent"}
CLASSES = tuple(CLASSIC)

# Forever's weapon types (item-class 2) name one- and two-handed alike ("Axe" twice), so the hand comes
# from the item's inventory type.
_HANDED = {"Axe": "Axes", "Mace": "Maces", "Sword": "Swords"}
_PLAIN = {"Dagger": "Daggers", "Fist Weapon": "Fist Weapons", "Polearm": "Polearms", "Staff": "Staves",
          "Bow": "Bows", "Crossbow": "Crossbows", "Gun": "Guns", "Thrown": "Thrown", "Wand": "Wands"}
_FOREVER_ONLY = {"Warglaives", "Spear", "Exotic"}       # in Forever's type list, not Classic's skills


def skill_for(subclass: str | None, inventory_type: str | None) -> str | None:
    """The weapon skill an equipped item needs, or None for anything that is not a weapon skill."""
    if subclass in _HANDED:
        return ("Two-Handed " if inventory_type == "Two-Hand" else "One-Handed ") + _HANDED[subclass]
    if subclass in _PLAIN:
        return _PLAIN[subclass]
    return subclass if subclass in _FOREVER_ONLY else None


def report(class_name: str, wielded) -> tuple[list[tuple[str, str | None, list[str]]], list[tuple[str, list[str]]]]:
    """Classic's list for a class, each skill with its note and who in the guild wields one, plus the skills
    members of that class wield that are NOT on the list (Forever differs from Classic there).
    `wielded` is (character name, item subclass, inventory type) for that class's equipped items."""
    seen: dict[str, list[str]] = {}
    for who, sub, inv in wielded:
        skill = skill_for(sub, inv)
        if skill and who not in seen.setdefault(skill, []):
            seen[skill].append(who)
    listed = CLASSIC.get(class_name, set())
    rows = [(s, NOTES.get((class_name, s)), seen.get(s, [])) for s in SKILLS if s in listed]
    extra = [(s, seen[s]) for s in sorted(seen) if s not in listed]
    return rows, extra
