"""Pure raid logic (no Discord, no network) so it can be tested directly."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# bench is not a button: it is where a full role sends you, and the queue for a spot. tentative is the "maybe".
ROLES = ("tank", "healer", "dps", "bench", "tentative", "absent")
ROLE_LABEL = {"tank": "Tanks", "healer": "Healers", "dps": "DPS", "bench": "Bench", "tentative": "Tentative",
              "absent": "Can't make it"}
COUNTED = ("tank", "healer", "dps")  # roles that fill raid slots
ROLE_SINGULAR = {"tank": "tank", "healer": "healer", "dps": "DPS"}
ROLE_EMOJI = {"tank": "🟦", "healer": "🟩", "dps": "🟥", "bench": "",
              "tentative": "🟨", "absent": "⬜"}      # blue, green, red, (none), yellow, white
# How long a bench player has to answer "a spot opened up" depends on how far off the raid is:
OFFER_SHARE = 0.30            # 30% of the time left until the start ...
OFFER_MIN_MINUTES = 15        # ... but never less than this ...
OFFER_MAX_MINUTES = 72 * 60   # ... and never more than three days (two to answer, then one after the last call)
LAST_CALL_SHARE = 1 / 3       # the last third of the window follows the "last call" ping in the raid channel


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


def day_options(now_utc: datetime, tz_name: str, days: int = 14, page: int = 0) -> list[tuple[str, str]]:
    """`days` calendar days in the guild timezone as (label, 'YYYY-MM-DD') for a dropdown. `page` 0 starts
    today; each page after it moves `days` further out, so any date is reachable."""
    tz = ZoneInfo(tz_name)
    today = now_utc.astimezone(tz).date()
    out = []
    for i in range(page * days, (page + 1) * days):
        d = today + timedelta(days=i)
        lead = "Today" if i == 0 else "Tomorrow" if i == 1 else d.strftime("%a")
        year = f" {d.year}" if d.year != today.year else ""
        out.append((f"{lead} - {d.strftime('%a %b')} {d.day}{year}", d.isoformat()))
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


def cancel_notice(raid, cancelled_by: int) -> str:
    """The private message sent to each signed-up player when a raid is cancelled."""
    ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
    return f"**{raid['title']}** (<t:{ts}:F>) was cancelled by <@{cancelled_by}>."


def size_from_limits(tanks, healers, dps) -> int | None:
    """When all three role limits are set, the raid has exactly that many slots; otherwise None
    (the typed size applies). Keeps the size from disagreeing with the limits."""
    if tanks and healers and dps:
        return int(tanks) + int(healers) + int(dps)
    return None


def reminder_text(raid) -> str:
    """The private reminder sent an hour before start."""
    ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
    return f"Reminder: **{raid['title']}** starts <t:{ts}:R> (<t:{ts}:t>)."


END_AFTER_HOURS = 3     # how long after the start the raid post is removed (matches the Discord event length)


def roster_summary(raid, signup_rows) -> str:
    """Who signed up, by role, as a plain message for the organizer."""
    g = group_signups(signup_rows)
    ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
    parts = [f"**{raid['title']}** (<t:{ts}:F>) roster:"]
    for role in ROLES:
        entries = [format_entry(s) for s in g[role]]
        parts.append(f"**{ROLE_LABEL[role]} ({len(entries)}):** " + (", ".join(entries) if entries else "-"))
    return "\n".join(parts)


def next_offers(raid, rows, offers) -> list[tuple[int, str]]:
    """Who the bench queue should ask about an open slot right now, as (discord_id, role).

    rows: the raid's signups (discord_id, role, wanted, updated_at). offers: its offers so far
    (discord_id, role, state). The bench is a queue in the order people joined it. Each person is asked
    about the role they wanted (any role, if they just tapped Bench), at most once per role per raid, and
    never while another question to them is still pending. Open slots already promised to someone who
    has not answered yet are not offered again."""
    g = group_signups(rows)
    caps = caps_of(raid)
    pending = [o for o in offers if o["state"] == "pending"]
    asked = {(o["discord_id"], o["role"]) for o in offers}
    busy = {o["discord_id"] for o in pending}
    count = {role: len(g[role]) + sum(1 for o in pending if o["role"] == role) for role in COUNTED}
    room = raid["size"] - filled(g) - len(pending)
    out: list[tuple[int, str]] = []
    for s in sorted(g["bench"], key=lambda x: x["updated_at"]):
        if room <= 0:
            break
        if s["discord_id"] in busy:
            continue
        wanted = s["wanted"] if "wanted" in s.keys() else None
        for role in ([wanted] if wanted else list(COUNTED)):
            cap = caps.get(role)
            if (s["discord_id"], role) in asked or (cap is not None and count[role] >= cap):
                continue
            out.append((s["discord_id"], role))
            busy.add(s["discord_id"])
            count[role] += 1
            room -= 1
            break
    return out


def offer_window(now: datetime, start: datetime) -> tuple[datetime, datetime]:
    """(last-call time, expiry time) for an offer made at `now` for a raid that starts at `start`.
    A raid days away gives hours to answer; a raid starting soon gives the minimum. It never runs past the start."""
    left = (start - now).total_seconds() / 60
    total = min(max(left * OFFER_SHARE, OFFER_MIN_MINUTES), OFFER_MAX_MINUTES)
    total = min(total, max(left - 1, 1))
    return now + timedelta(minutes=total * (1 - LAST_CALL_SHARE)), now + timedelta(minutes=total)


def offer_text(raid, role: str, expires_at: datetime) -> str:
    ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
    return (f"A spot opened up in **{raid['title']}** (<t:{ts}:F>): **{ROLE_SINGULAR[role]}**.\n"
            f"Take it or pass. If you don't answer by <t:{int(expires_at.timestamp())}:t> "
            f"I'll remind you once more, then take you off the bench.")


def ping_text(raid, role: str, discord_id: int, expires_at: datetime, last_call: bool = False) -> str:
    """The @ in the raid channel. last_call: they were already DMed and did not answer; this is the reminder."""
    when = int(expires_at.timestamp())
    if last_call:
        return (f"<@{discord_id}> still want the **{ROLE_SINGULAR[role]}** spot in **{raid['title']}**? "
                f"Answer <t:{when}:R> or you come off the bench.")
    return (f"<@{discord_id}> a spot opened up in **{raid['title']}**: **{ROLE_SINGULAR[role]}**. "
            f"Take it or pass by <t:{when}:t> or you come off the bench.")
