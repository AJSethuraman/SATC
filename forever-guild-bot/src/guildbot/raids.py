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


def full_name(r) -> str:
    """'First Last'. Forever characters are known by both."""
    return f"{r['name']} {r['surname']}" if "surname" in r.keys() and r["surname"] else r["name"]


def format_entry(s) -> str:
    if s["name"]:
        bits = [f"**{full_name(s)}**"]
        if s["class_name"]:
            bits.append(s["class_name"])
        if s["level"]:
            bits.append(f"L{s['level']}")
        return " ".join(bits)
    return f"<@{s['discord_id']}>"


def caps_of(raid) -> dict[str, int | None]:
    """Per-role limits on a raid row; None means no limit."""
    return {"tank": raid["cap_tank"], "healer": raid["cap_healer"], "dps": raid["cap_dps"]}


def resolve_role(role: str, groups: dict[str, list], size: int, discord_id: int,
                 caps: dict[str, int | None] | None = None) -> str:
    """Role a signup actually lands in.

    A new tank/healer/DPS signup goes to the bench when the raid is full or that role is at its limit.
    Someone already holding a slot who asks for a full role stays where they are.
    """
    if role not in COUNTED:
        return role
    caps = caps or {}
    mine = next((r for r in COUNTED for s in groups[r] if s["discord_id"] == discord_id), None)
    cap = caps.get(role)
    role_full = cap is not None and sum(1 for s in groups[role] if s["discord_id"] != discord_id) >= cap
    if mine is None:
        return "bench" if role_full or filled(groups) >= size else role
    return mine if role_full else role
