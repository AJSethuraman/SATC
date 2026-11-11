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


# "Any 1H" / "Any 2H" for weapons: groups of inventory types the slot dropdown can pick in one go.
SLOT_GROUPS = {"@1H": ("One-Hand", "Main Hand", "Off Hand"), "@2H": ("Two-Hand",)}
SLOT_GROUP_LABELS = {"@1H": "Any 1H", "@2H": "Any 2H"}


def slot_filter(value):
    """A slot dropdown value as what the database takes: one inventory type, a tuple of them, or None."""
    if not value or value == ANY:
        return None
    return SLOT_GROUPS.get(value, value)


def slot_label(value: str) -> str:
    return SLOT_GROUP_LABELS.get(value, value)


def parse_level_range(lo_text: str, hi_text: str, top: int = 60) -> tuple[int | None, int | None]:
    """Two optional whole numbers from the level pop-up. Raises ValueError for anything else."""
    def one(t: str) -> int | None:
        t = (t or "").strip()
        if not t:
            return None
        n = int(t)
        if not 0 <= n <= top:
            raise ValueError(t)
        return n
    lo, hi = one(lo_text), one(hi_text)
    if lo is not None and hi is not None and lo > hi:
        raise ValueError("from is above to")
    return lo, hi


def level_text(lo: int | None, hi: int | None) -> str:
    if lo is None and hi is None:
        return "any"
    return f"{lo if lo is not None else 0}-{hi if hi is not None else 60}"
