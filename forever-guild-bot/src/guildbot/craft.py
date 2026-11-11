"""Pure helpers for the guided /craftable menu (no Discord, no network)."""
from __future__ import annotations

ANY = "*"


def level_bands(top: int = 60) -> list[tuple[str, str]]:
    """(label, 'min-max') bands of ten levels up to `top`, for a dropdown. First band starts at 0 so items
    with no level requirement are included."""
    out, lo = [], 0
    while lo < top:
        hi = min(lo + 10, top) if lo == 0 else min(lo + 9, top)
        out.append((f"Level {max(lo, 1)}-{hi}", f"{lo}-{hi}"))
        lo = hi + 1
    return out


def parse_band(value: str | None) -> tuple[int | None, int | None]:
    if not value or value == ANY:
        return None, None
    lo, hi = value.split("-")
    return int(lo), int(hi)


def what_options(pairs) -> list[tuple[str, str]]:
    """The 'what kind of gear' dropdown: (label, 'Class|Subclass') for armor types, weapon types, and a couple
    of other kinds. pairs: (item_class, item_subclass, count) rows. 'Class|*' means any type of that class."""
    out: list[tuple[str, str]] = []
    for cls in ("Armor", "Weapon"):
        subs = sorted(((s, n) for c, s, n in pairs if c == cls and s and s != "Cosmetic"), key=lambda x: -x[1])
        if subs:
            out.append((f"Any {cls.lower()}", f"{cls}|*"))
            out += [(f"{cls}: {s}", f"{cls}|{s}") for s, _ in subs]
    for cls in ("Consumable", "Trade Goods"):
        if any(c == cls for c, _, _ in pairs):
            out.append((cls, f"{cls}|*"))
    return out[:24]


def parse_what(value: str | None) -> tuple[str | None, str | None]:
    if not value or value == ANY or "|" not in value:
        return None, None
    kind, sub = value.split("|", 1)
    return kind, (None if sub == "*" else sub)


def what_value(kind, sub) -> str:
    return ANY if not kind else f"{kind}|{sub or '*'}"
