"""Local, file-based storage for learned paystub profiles.

Profiles are plain JSON files in a per-user directory (override with the
``TWE_PROFILE_DIR`` environment variable). No database, no network — a profile
you teach on one machine is a single portable JSON file.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from twe.paystub import Profile


def profiles_dir() -> Path:
    """Directory where profiles are stored (created on demand)."""

    override = os.environ.get("TWE_PROFILE_DIR")
    base = Path(override) if override else Path.home() / ".twe" / "profiles"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "profile"


def _path_for(name: str) -> Path:
    return profiles_dir() / f"{_slug(name)}.json"


def save_profile(profile: Profile) -> Path:
    """Write a profile to disk and return its path."""

    if not profile.name.strip():
        raise ValueError("Profile name cannot be empty.")
    path = _path_for(profile.name)
    path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
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
