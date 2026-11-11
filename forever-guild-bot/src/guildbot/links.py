"""Links out to Wowhead. We link to a name search, never to a guessed item number: Forever's item
numbers are not confirmed to match Wowhead's, and a wrong number would open the wrong item."""
from __future__ import annotations

from urllib.parse import quote


def item_url(name: str) -> str:
    return "https://www.wowhead.com/search?q=" + quote(name, safe="")


def item_link(name: str) -> str:
    """Discord markdown that shows just the name, clickable."""
    shown = name.replace("[", "(").replace("]", ")")
    return f"[{shown}]({item_url(name)})"
