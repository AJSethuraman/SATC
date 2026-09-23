from __future__ import annotations

"""Brain files: one Markdown file per player, five headed sections, one cap.

The shape (brains/TEMPLATE.md is the copy a player is handed):

    # <Name>
    Build: <vanguard|scout|mystic|scoundrel>
    Id: <optional; letters, digits, _ and -; defaults to the file name>
    Objective: <optional; one of the engine's secret objectives; else derived from the id>

    ## Voice
    ## Wants
    ## Treats
    ## Never

Every refusal names the section and the overage (PRD §5.9), because the
person reading it is a player with a text editor open, not a developer.
"""

import re
from pathlib import Path
from typing import Any

from .models import AgentManifest, BRAIN_CAP, BRAIN_SECTIONS, ValidationError

_HEAD = re.compile(r"^#\s+(.+?)\s*$", re.M)
_META = re.compile(r"^(Build|Id|Objective):\s*(.+?)\s*$", re.M)
_SECTION = re.compile(r"^##\s+(\w+)\s*$", re.M)
_URL = re.compile(r"https?://|www\.", re.I)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏ - ﻿]")
_BLOB = re.compile(r"[A-Za-z0-9+/=]{200,}")


def parse_brain(text: str, *, default_id: str) -> dict[str, Any]:
    """Markdown -> manifest dict. Raises ValidationError with the section named."""
    if _CONTROL.search(text):
        raise ValidationError("the file carries invisible control characters; remove them")
    head = _HEAD.search(text)
    if not head or head.start() != text.lstrip().find("#") + (len(text) - len(text.lstrip())):
        raise ValidationError("the first line must be '# <Name>'")
    name = head.group(1)
    meta = {m.group(1).lower(): m.group(2) for m in _META.finditer(text[: _first_section_at(text)])}
    if "build" not in meta:
        raise ValidationError("missing 'Build: <vanguard|scout|mystic|scoundrel>' under the name")

    heads = list(_SECTION.finditer(text))
    sections: dict[str, str] = {}
    for i, h in enumerate(heads):
        key = h.group(1).lower()
        if key not in BRAIN_SECTIONS:
            raise ValidationError(
                f"unknown section '## {h.group(1)}'; the sections are "
                + ", ".join(f"## {s.title()}" for s in BRAIN_SECTIONS)
            )
        if key in sections:
            raise ValidationError(f"section '## {h.group(1)}' appears twice")
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end].strip()
        if not body:
            raise ValidationError(f"section '## {h.group(1)}' is empty")
        if _URL.search(body):
            raise ValidationError(f"section '## {h.group(1)}' contains a link; brains carry none")
        if _BLOB.search(body):
            raise ValidationError(f"section '## {h.group(1)}' contains an encoded blob; brains are prose")
        sections[key] = body
    missing = [s for s in BRAIN_SECTIONS if s not in sections]
    if missing:
        raise ValidationError("missing section(s): " + ", ".join(f"## {s.title()}" for s in missing))
    total = sum(len(v) for v in sections.values())
    if total > BRAIN_CAP:
        longest = max(sections, key=lambda s: len(sections[s]))
        raise ValidationError(
            f"the four sections total {total} characters; the cap is {BRAIN_CAP}. "
            f"Over by {total - BRAIN_CAP}. The longest section is '## {longest.title()}' "
            f"at {len(sections[longest])} characters; cut there first."
        )
    raw: dict[str, Any] = {
        "id": meta.get("id", default_id),
        "name": name,
        "kind": "character",
        "build": meta["build"].lower(),
        **sections,
    }
    if "objective" in meta:
        raw["secret_objective"] = meta["objective"].lower()
    return raw


def _first_section_at(text: str) -> int:
    m = _SECTION.search(text)
    return m.start() if m else len(text)


def default_id_for(path: Path) -> str:
    """'03_ash_the_quiet.md' -> 'ash_the_quiet'; the numeric prefix orders seats."""
    stem = path.stem
    stem = re.sub(r"^\d+[_-]", "", stem)
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem)[:40]


def load_brain(path: str | Path) -> AgentManifest:
    path = Path(path)
    try:
        raw = parse_brain(path.read_text(encoding="utf-8"), default_id=default_id_for(path))
        return AgentManifest.from_dict(raw)
    except ValidationError as exc:
        raise ValidationError(f"{path.name}: {exc}") from None


def load_brains(directory: str | Path) -> list[AgentManifest]:
    """Every *.md in the folder except TEMPLATE.md, in file-name order, which
    is seat order."""
    directory = Path(directory)
    paths = sorted(p for p in directory.glob("*.md") if p.name.upper() != "TEMPLATE.MD")
    manifests = [load_brain(p) for p in paths]
    if not 4 <= len(manifests) <= 8:
        raise ValidationError(f"expected 4..8 brain files in {directory}, found {len(manifests)}")
    ids = [m.id for m in manifests]
    if len(set(ids)) != len(ids):
        raise ValidationError(f"two brains share an id: {sorted(i for i in ids if ids.count(i) > 1)}")
    return manifests
