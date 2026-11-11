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
