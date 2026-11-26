"""Links out to Wowhead's WoW Forever database (https://www.wowhead.com/forever). Wowhead has a Forever
section of its own; the retail site is a different game's data. We link to an item by its number when we
have one (it comes from Blizzard's Forever API) and otherwise to a name search inside the Forever section."""
from __future__ import annotations

from urllib.parse import quote

BASE = "https://www.wowhead.com/forever"


def item_url(name: str, item_id: int | None = None) -> str:
    if item_id:
        return f"{BASE}/item={int(item_id)}"
    return f"{BASE}/search?q=" + quote(name, safe="")


def item_link(name: str, item_id: int | None = None) -> str:
    """Discord markdown that shows just the name, clickable."""
    shown = name.replace("[", "(").replace("]", ")")
    return f"[{shown}]({item_url(name, item_id)})"
