"""SQLite storage. Plain SQL, one file, easy to inspect with any SQLite viewer."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS characters (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    surname TEXT,
    level INTEGER,
    class_name TEXT,
    race_name TEXT,
    faction TEXT,
    guild_rank INTEGER,
    in_guild INTEGER NOT NULL DEFAULT 1,
    profile_at TEXT,
    last_seen_at TEXT
);

-- Raw API responses, kept so parsers can be corrected and every number traced.
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    slug TEXT,
    kind TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS snapshots_idx ON snapshots (slug, kind, id);

CREATE TABLE IF NOT EXISTS professions (
    slug TEXT NOT NULL, profession TEXT NOT NULL,
    skill INTEGER NOT NULL, max_skill INTEGER NOT NULL, fetched_at TEXT NOT NULL,
    PRIMARY KEY (slug, profession)
);

CREATE TABLE IF NOT EXISTS equipment (
    slug TEXT NOT NULL, slot TEXT NOT NULL, item_id INTEGER, item_name TEXT NOT NULL,
    quality TEXT, fetched_at TEXT NOT NULL,
    PRIMARY KEY (slug, slot)
);

CREATE TABLE IF NOT EXISTS links (
    discord_id INTEGER NOT NULL, slug TEXT NOT NULL, is_main INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (discord_id, slug)
);

CREATE TABLE IF NOT EXISTS raids (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,          -- UTC ISO-8601
    size INTEGER NOT NULL,
    cap_tank INTEGER, cap_healer INTEGER, cap_dps INTEGER,   -- NULL = no limit for that role
    created_by INTEGER NOT NULL,
    channel_id INTEGER, message_id INTEGER, discord_event_id INTEGER,
    status TEXT NOT NULL DEFAULT 'open',   -- open | closed | cancelled
    reminded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signups (
    raid_id INTEGER NOT NULL, discord_id INTEGER NOT NULL,
    slug TEXT, role TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (raid_id, discord_id)
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    # ---- roster -------------------------------------------------------
    def upsert_member(self, slug, name, surname, level, rank, now) -> None:
        self.conn.execute(
            """INSERT INTO characters (slug, name, surname, level, guild_rank, in_guild, last_seen_at)
               VALUES (?,?,?,?,?,1,?)
               ON CONFLICT(slug) DO UPDATE SET name=excluded.name, surname=excluded.surname,
                 level=COALESCE(excluded.level, level), guild_rank=excluded.guild_rank,
                 in_guild=1, last_seen_at=excluded.last_seen_at""",
            (slug, name, surname, level, rank, now))
        self.conn.commit()

    def mark_absent(self, present_slugs: set[str]) -> int:
        rows = self.conn.execute("SELECT slug FROM characters WHERE in_guild=1").fetchall()
        gone = [r["slug"] for r in rows if r["slug"] not in present_slugs]
        for s in gone:
            self.conn.execute("UPDATE characters SET in_guild=0 WHERE slug=?", (s,))
        self.conn.commit()
        return len(gone)

    def set_profile(self, slug, level, class_name, race_name, faction, now) -> None:
        self.conn.execute(
            """UPDATE characters SET level=COALESCE(?, level), class_name=?, race_name=?,
               faction=?, profile_at=? WHERE slug=?""",
            (level, class_name, race_name, faction, now, slug))
        self.conn.commit()

    def prune_snapshots(self, keep: int = 2) -> int:
        """Keep the newest `keep` raw responses per (character, kind), plus the latest successful one.

        The parsed tables come from the last successful fetch, so its raw response must survive
        even when the newest attempts were errors or 404s. Returns rows deleted.
        """
        cur = self.conn.execute(
            """DELETE FROM snapshots WHERE id IN (
                 SELECT id FROM (
                   SELECT id, status, ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(slug, ''), kind ORDER BY id DESC) AS rn,
                     ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(slug, ''), kind, status ORDER BY id DESC) AS rn_status
                   FROM snapshots)
                 WHERE rn > ? AND NOT (status = 'ok' AND rn_status = 1))""", (keep,))
        self.conn.commit()
        return cur.rowcount

    def save_snapshot(self, slug, kind, status, payload, now) -> None:
        self.conn.execute(
            "INSERT INTO snapshots (slug, kind, fetched_at, status, payload) VALUES (?,?,?,?,?)",
            (slug, kind, now, status, payload))
        self.conn.commit()

    def replace_professions(self, slug, profs, now) -> None:
        self.conn.execute("DELETE FROM professions WHERE slug=?", (slug,))
        self.conn.executemany(
            "INSERT INTO professions VALUES (?,?,?,?,?)",
            [(slug, p.name, p.skill, p.max_skill, now) for p in profs])
        self.conn.commit()

    def replace_equipment(self, slug, items, now) -> None:
        self.conn.execute("DELETE FROM equipment WHERE slug=?", (slug,))
        self.conn.executemany(
            "INSERT OR REPLACE INTO equipment VALUES (?,?,?,?,?,?)",
            [(slug, i.slot, i.item_id, i.name, i.quality, now) for i in items])
        self.conn.commit()

    def set_meta(self, key, value) -> None:
        self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
        self.conn.commit()

    def get_meta(self, key) -> str | None:
        r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else None

    # ---- lookups ------------------------------------------------------
    def find_character(self, text: str):
        t = text.strip().lower()
        return self.conn.execute(
            """SELECT * FROM characters WHERE in_guild=1
               AND (slug=? OR lower(name)=?) ORDER BY (slug=?) DESC LIMIT 1""",
            (t.replace(" ", "-"), t, t.replace(" ", "-"))).fetchone()

    def search_characters(self, prefix: str, limit: int = 25):
        return self.conn.execute(
            "SELECT * FROM characters WHERE in_guild=1 AND (lower(name) LIKE ? OR slug LIKE ?) "
            "ORDER BY name LIMIT ?", (prefix.lower() + "%", prefix.lower() + "%", limit)).fetchall()

    def roster(self, class_name=None, min_level=None, limit=200):
        q, args = "SELECT * FROM characters WHERE in_guild=1", []
        if class_name:
            q += " AND lower(class_name)=?"; args.append(class_name.lower())
        if min_level:
            q += " AND level>=?"; args.append(min_level)
        q += " ORDER BY level DESC, name LIMIT ?"; args.append(limit)
        return self.conn.execute(q, args).fetchall()

    def professions_for(self, slug):
        return self.conn.execute(
            "SELECT * FROM professions WHERE slug=? ORDER BY skill DESC", (slug,)).fetchall()

    def equipment_for(self, slug):
        return self.conn.execute("SELECT * FROM equipment WHERE slug=?", (slug,)).fetchall()

    def who_has_profession(self, text: str):
        return self.conn.execute(
            """SELECT c.name, c.level, p.profession, p.skill, p.max_skill, p.fetched_at
               FROM professions p JOIN characters c ON c.slug=p.slug
               WHERE c.in_guild=1 AND lower(p.profession) LIKE ?
               ORDER BY p.skill DESC, c.name""", ("%" + text.lower() + "%",)).fetchall()

    def search_items(self, text: str):
        return self.conn.execute(
            """SELECT c.name, c.level, e.slot, e.item_name, e.quality, e.fetched_at
               FROM equipment e JOIN characters c ON c.slug=e.slug
               WHERE c.in_guild=1 AND lower(e.item_name) LIKE ?
               ORDER BY c.name""", ("%" + text.lower() + "%",)).fetchall()

    # ---- discord <-> character links ---------------------------------
    def link(self, discord_id: int, slug: str) -> bool:
        """Link a character. Returns True if it became the main."""
        has_main = self.main_for(discord_id) is not None
        self.conn.execute(
            "INSERT OR IGNORE INTO links (discord_id, slug, is_main) VALUES (?,?,?)",
            (discord_id, slug, 0 if has_main else 1))
        self.conn.commit()
        return not has_main

    def release(self, slug: str) -> None:
        """Remove every Discord link to a character (officer override)."""
        self.conn.execute("DELETE FROM links WHERE slug=?", (slug,))
        self.conn.commit()

    def unlink(self, discord_id: int, slug: str) -> None:
        was_main = self.conn.execute(
            "SELECT is_main FROM links WHERE discord_id=? AND slug=?", (discord_id, slug)).fetchone()
        self.conn.execute("DELETE FROM links WHERE discord_id=? AND slug=?", (discord_id, slug))
        if was_main and was_main["is_main"]:
            nxt = self.conn.execute(
                "SELECT slug FROM links WHERE discord_id=? ORDER BY slug LIMIT 1", (discord_id,)).fetchone()
            if nxt:
                self.conn.execute("UPDATE links SET is_main=1 WHERE discord_id=? AND slug=?",
                                  (discord_id, nxt["slug"]))
        self.conn.commit()

    def set_main(self, discord_id: int, slug: str) -> bool:
        if not self.conn.execute("SELECT 1 FROM links WHERE discord_id=? AND slug=?",
                                 (discord_id, slug)).fetchone():
            return False
        self.conn.execute("UPDATE links SET is_main=(slug=?) WHERE discord_id=?", (slug, discord_id))
        self.conn.commit()
        return True

    def main_for(self, discord_id: int):
        return self.conn.execute(
            """SELECT c.* FROM links l JOIN characters c ON c.slug=l.slug
               WHERE l.discord_id=? AND l.is_main=1""", (discord_id,)).fetchone()

    def characters_for(self, discord_id: int):
        return self.conn.execute(
            """SELECT c.*, l.is_main FROM links l JOIN characters c ON c.slug=l.slug
               WHERE l.discord_id=? ORDER BY l.is_main DESC, c.name""", (discord_id,)).fetchall()

    def owner_of(self, slug: str):
        r = self.conn.execute("SELECT discord_id FROM links WHERE slug=? ORDER BY is_main DESC LIMIT 1",
                              (slug,)).fetchone()
        return r["discord_id"] if r else None

    # ---- raids --------------------------------------------------------
    def create_raid(self, title, starts_at_utc_iso, size, created_by, caps: dict | None = None) -> int:
        caps = caps or {}
        cur = self.conn.execute(
            """INSERT INTO raids (title, starts_at, size, cap_tank, cap_healer, cap_dps, created_by)
               VALUES (?,?,?,?,?,?,?)""",
            (title, starts_at_utc_iso, size, caps.get("tank") or None, caps.get("healer") or None,
             caps.get("dps") or None, created_by))
        self.conn.commit()
        return cur.lastrowid

    def set_raid_posted(self, raid_id, channel_id, message_id, event_id) -> None:
        self.conn.execute(
            "UPDATE raids SET channel_id=?, message_id=?, discord_event_id=? WHERE id=?",
            (channel_id, message_id, event_id, raid_id))
        self.conn.commit()

    def get_raid(self, raid_id):
        return self.conn.execute("SELECT * FROM raids WHERE id=?", (raid_id,)).fetchone()

    def open_raids(self):
        return self.conn.execute(
            "SELECT * FROM raids WHERE status='open' ORDER BY starts_at").fetchall()

    def update_raid(self, raid_id, title=None, starts_at_utc_iso=None, size=None, caps: dict | None = None) -> None:
        """Change only the fields given. A new start time re-arms the reminder.

        caps: {"tank": n, ...} for the roles to change; 0 removes that role's limit.
        """
        raid = self.get_raid(raid_id)
        for role, n in (caps or {}).items():
            self.conn.execute(f"UPDATE raids SET cap_{role}=? WHERE id=?", (n or None, raid_id))
        new_start = starts_at_utc_iso or raid["starts_at"]
        reminded = 0 if new_start != raid["starts_at"] else raid["reminded"]
        self.conn.execute(
            "UPDATE raids SET title=?, starts_at=?, size=?, reminded=? WHERE id=?",
            (title or raid["title"], new_start, size or raid["size"], reminded, raid_id))
        self.conn.commit()

    def started_open(self, now_utc: datetime):
        """Open raids whose start time has passed and that still need their buttons removed."""
        return [r for r in self.open_raids() if datetime.fromisoformat(r["starts_at"]) <= now_utc]

    def mark_closed(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET status='closed' WHERE id=?", (raid_id,))
        self.conn.commit()

    def cancel_raid(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET status='cancelled' WHERE id=?", (raid_id,))
        self.conn.commit()

    def upsert_signup(self, raid_id, discord_id, slug, role, now) -> None:
        self.conn.execute(
            """INSERT INTO signups (raid_id, discord_id, slug, role, updated_at) VALUES (?,?,?,?,?)
               ON CONFLICT(raid_id, discord_id) DO UPDATE SET slug=excluded.slug,
                 role=excluded.role, updated_at=excluded.updated_at""",
            (raid_id, discord_id, slug, role, now))
        self.conn.commit()

    def signups(self, raid_id):
        return self.conn.execute(
            """SELECT s.*, c.name, c.level, c.class_name FROM signups s
               LEFT JOIN characters c ON c.slug=s.slug
               WHERE s.raid_id=? ORDER BY s.updated_at""", (raid_id,)).fetchall()

    def due_reminders(self, now_utc: datetime, lead_minutes: int = 60):
        out = []
        for r in self.open_raids():
            if r["reminded"]:
                continue
            start = datetime.fromisoformat(r["starts_at"])
            mins = (start - now_utc).total_seconds() / 60
            if 0 < mins <= lead_minutes:
                out.append(r)
        return out

    def mark_reminded(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET reminded=1 WHERE id=?", (raid_id,))
        self.conn.commit()
