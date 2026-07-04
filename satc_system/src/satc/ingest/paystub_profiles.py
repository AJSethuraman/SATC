"""Practice-wide local storage for click-to-teach paystub profiles.

Profiles are plain JSON files in the SATC data dir (``~/.satc/data/paystub_profiles``
in the packaged app, ``satc_system/build/data/...`` in a dev checkout, and
``SATC_DATA_DIR`` overrides). No database, no network — a profile you teach is a
single portable JSON file, shared across all clients. Only the layout (regions +
labels) is stored, never a client's amounts.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from satc.ingest.paystub_layout import Layout, Profile, best_profile


def profiles_dir() -> Path:
    """Directory where profiles live (created on demand), frozen-aware."""
    override = os.environ.get("SATC_DATA_DIR")
    if override:
        base = Path(override)
    elif getattr(sys, "frozen", False):
        base = Path.home() / ".satc" / "data"
    else:
        base = Path(__file__).resolve().parents[3] / "build" / "data"
    out = base / "paystub_profiles"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "profile"


def _path_for(name: str) -> Path:
    return profiles_dir() / f"{_slug(name)}.json"


def save_profile(profile: Profile) -> Path:
    """Write a profile to disk atomically and return its path."""
    if not profile.name.strip():
        raise ValueError("Profile name cannot be empty.")
    path = _path_for(profile.name)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def load_profile(name: str) -> Profile | None:
    path = _path_for(name)
    if not path.exists():
        return None
    return Profile.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_profiles() -> list[Profile]:
    """Load every saved profile, sorted by name. Skips unreadable files."""
    out: list[Profile] = []
    for path in sorted(profiles_dir().glob("*.json")):
        try:
            out.append(Profile.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    out.sort(key=lambda p: p.name.lower())
    return out


def delete_profile(name: str) -> bool:
    path = _path_for(name)
    if path.exists():
        path.unlink()
        return True
    return False


def match_profile(layout: Layout, threshold: float = 0.6) -> Profile | None:
    """Best saved profile for this layout (by label/keyword overlap), or None."""
    return best_profile(layout, list_profiles(), threshold)
