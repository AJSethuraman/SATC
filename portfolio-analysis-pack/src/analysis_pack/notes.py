"""Method notes and cover sentences, filled from `wording.yaml`.

No sentence is assembled in code. A template with a placeholder the caller
did not supply raises, so a note can never silently print a blank where a
count belongs (design principle 1: never invent a value).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_WORDING: dict[str, Any] | None = None


def wording() -> dict[str, Any]:
    global _WORDING
    if _WORDING is None:
        p = Path(__file__).with_name("wording.yaml")
        _WORDING = yaml.safe_load(p.read_text(encoding="utf-8"))
    return _WORDING


class _Strict(dict):
    def __missing__(self, key: str):
        raise KeyError(f"wording placeholder {{{key}}} was not supplied")


def fill(path: str, **values: Any) -> str:
    """Fill the template at a dotted path, e.g. fill('cover.question', ...)."""
    node: Any = wording()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"no wording at {path!r}")
        node = node[part]
    if not isinstance(node, str):
        raise KeyError(f"wording at {path!r} is not a template")
    return node.format_map(_Strict(values)).strip()


def pick(path: str, key: str, **values: Any) -> str:
    """Fill the variant `key` under `path` (a finite set the state selects from)."""
    node: Any = wording()
    for part in path.split("."):
        node = node[part]
    if key not in node:
        raise KeyError(f"no wording variant {key!r} under {path!r}")
    return str(node[key]).format_map(_Strict(values)).strip()
