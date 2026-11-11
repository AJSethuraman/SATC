"""Pure raid logic (no Discord, no network) so it can be tested directly."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def day_options(now_utc: datetime, tz_name: str, days: int = 14) -> list[tuple[str, str]]:
    """Next `days` calendar days in the guild timezone as (label, 'YYYY-MM-DD') for a dropdown."""
    tz = ZoneInfo(tz_name)
    today = now_utc.astimezone(tz).date()
    out = []
    for i in range(days):
        d = today + timedelta(days=i)
        lead = "Today" if i == 0 else "Tomorrow" if i == 1 else d.strftime("%a")
        out.append((f"{lead} - {d.strftime('%a %b')} {d.day}", d.isoformat()))
    return out


def time_options() -> list[tuple[str, str]]:
    """12:00 PM to 11:30 PM in half hours as (label, 'HH:MM')."""
    out = []
    for h in range(12, 24):
        for m in (0, 30):
            hh = h - 12 if h > 12 else h
            out.append((f"{hh}:{m:02d} {'PM'}", f"{h:02d}:{m:02d}"))
    return out


SIZE_CHOICES = (2, 3, 5, 10, 20, 25, 40)


def parse_cap(text: str) -> int | None:
    """Blank means no limit. Otherwise a whole number from 1 to 40. Raises ValueError."""
    t = (text or "").strip()
    if not t:
        return None
    n = int(t)
    if not 1 <= n <= 40:
        raise ValueError(t)
    return n
