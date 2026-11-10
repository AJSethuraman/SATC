"""Pure raid logic (no Discord, no network) so it can be tested directly."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROLES = ("tank", "healer", "dps", "bench", "absent")
ROLE_LABEL = {"tank": "Tanks", "healer": "Healers", "dps": "DPS", "bench": "Bench", "absent": "Can't make it"}
COUNTED = ("tank", "healer", "dps")  # roles that fill raid slots


def parse_start(date_s: str, time_s: str, tz_name: str) -> datetime:
    """'2026-11-15' + '20:00' in the guild's timezone -> aware UTC datetime. Raises ValueError."""
    local = datetime.strptime(f"{date_s.strip()} {time_s.strip()}", "%Y-%m-%d %H:%M")
    return local.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)


def group_signups(rows) -> dict[str, list]:
    out: dict[str, list] = {r: [] for r in ROLES}
    for s in rows:
        if s["role"] in out:
            out[s["role"]].append(s)
    return out


def filled(groups: dict[str, list]) -> int:
    return sum(len(groups[r]) for r in COUNTED)


def format_entry(s) -> str:
    if s["name"]:
        bits = [f"**{s['name']}**"]
        if s["class_name"]:
            bits.append(s["class_name"])
        if s["level"]:
            bits.append(f"L{s['level']}")
        return " ".join(bits)
    return f"<@{s['discord_id']}>"
