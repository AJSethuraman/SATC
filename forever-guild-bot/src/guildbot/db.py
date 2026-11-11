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

-- Recipes each character knows (from the character's professions response).
CREATE TABLE IF NOT EXISTS known_recipes (
    slug TEXT NOT NULL, profession TEXT NOT NULL, recipe_id INTEGER NOT NULL, name TEXT NOT NULL,
    PRIMARY KEY (slug, profession, recipe_id)
);

-- Every recipe each profession has, from Blizzard's static data (same for all players).
CREATE TABLE IF NOT EXISTS recipes (
    profession TEXT NOT NULL, recipe_id INTEGER NOT NULL, name TEXT NOT NULL, category TEXT,
    fetched_at TEXT NOT NULL,
    item_id INTEGER,            -- the item this recipe makes: NULL = not looked up yet, 0 = makes no item
    PRIMARY KEY (profession, recipe_id)
);

-- What recipes make, from Blizzard's static data.
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY, name TEXT NOT NULL, quality TEXT, level INTEGER, required_level INTEGER,
    item_class TEXT, item_subclass TEXT, inventory_type TEXT,
    stats_loaded INTEGER NOT NULL DEFAULT 0      -- 1 once this item's stats have been read
);

-- The stats an item gives (Intellect, Stamina, Spell Power, ...), for the /craftable stat filter.
CREATE TABLE IF NOT EXISTS item_stats (
    item_id INTEGER NOT NULL, stat TEXT NOT NULL, label TEXT NOT NULL, value INTEGER NOT NULL,
    PRIMARY KEY (item_id, stat)
);

-- Searches that found nothing the guild can make: what people want and we lack.
CREATE TABLE IF NOT EXISTS wanted (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, profession TEXT, discord_id INTEGER, asked_at TEXT NOT NULL
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
    status TEXT NOT NULL DEFAULT 'open',   -- open | closed (started) | ended (post removed) | cancelled
    reminded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signups (
    raid_id INTEGER NOT NULL, discord_id INTEGER NOT NULL,
    slug TEXT, role TEXT NOT NULL, updated_at TEXT NOT NULL,
    wanted TEXT,                      -- on the bench: the role they asked for (NULL = any role)
    PRIMARY KEY (raid_id, discord_id)
);

-- "A spot opened up, want it?" questions sent to people waiting on the bench.
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY, raid_id INTEGER NOT NULL, discord_id INTEGER NOT NULL, role TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',      -- pending | accepted | declined | expired
    sent_at TEXT NOT NULL,
    ping_at TEXT, expires_at TEXT,             -- when to send the last-call ping, and when the offer lapses
    dm_msg_id INTEGER, chan_msg_id INTEGER,     -- the DM, and the ping in the raid channel (if one was sent)
    cleaned INTEGER NOT NULL DEFAULT 0          -- 1 once those messages have been tidied up
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
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(recipes)")}
        if "item_id" not in cols:                       # database created before recipes knew their item
            self.conn.execute("ALTER TABLE recipes ADD COLUMN item_id INTEGER")
            self.conn.commit()
        ocols = {r["name"] for r in self.conn.execute("PRAGMA table_info(offers)")}
        for col, ddl in (("dm_msg_id", "INTEGER"), ("chan_msg_id", "INTEGER"), ("cleaned", "INTEGER NOT NULL DEFAULT 0"),
                         ("ping_at", "TEXT"), ("expires_at", "TEXT")):
            if col not in ocols:                        # database created before offers had messages to tidy
                self.conn.execute(f"ALTER TABLE offers ADD COLUMN {col} {ddl}")
                self.conn.commit()
        self.conn.execute(                              # offers made before windows were stored: 15 / 20 minutes
            """UPDATE offers SET ping_at=strftime('%Y-%m-%dT%H:%M:%S+00:00', sent_at, '+15 minutes'),
                 expires_at=strftime('%Y-%m-%dT%H:%M:%S+00:00', sent_at, '+20 minutes') WHERE expires_at IS NULL""")
        self.conn.commit()
        if "stats_loaded" not in {r["name"] for r in self.conn.execute("PRAGMA table_info(items)")}:
            self.conn.execute("ALTER TABLE items ADD COLUMN stats_loaded INTEGER NOT NULL DEFAULT 0")   # fetched before stats
            self.conn.commit()
        if "wanted" not in {r["name"] for r in self.conn.execute("PRAGMA table_info(signups)")}:
            self.conn.execute("ALTER TABLE signups ADD COLUMN wanted TEXT")     # database created before the bench queue
            self.conn.commit()

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
        """Keep the newest `keep` raw responses per (character, kind), plus the latest "ok" one and the
        latest "parse_error" one.

        "ok" means fetched and successfully parsed, so the parsed tables come from it and it must
        survive newer errors or 404s. The latest "parse_error" is the raw response needed to fix a
        parser. Returns rows deleted.
        """
        cur = self.conn.execute(
            """DELETE FROM snapshots WHERE id IN (
                 SELECT id FROM (
                   SELECT id, status, ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(slug, ''), kind ORDER BY id DESC) AS rn,
                     ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(slug, ''), kind, status ORDER BY id DESC) AS rn_status
                   FROM snapshots)
                 WHERE rn > ? AND NOT (status IN ('ok', 'parse_error') AND rn_status = 1))""", (keep,))
        self.conn.commit()
        return cur.rowcount

    def save_snapshot(self, slug, kind, status, payload, now) -> None:
        self.conn.execute(
            "INSERT INTO snapshots (slug, kind, fetched_at, status, payload) VALUES (?,?,?,?,?)",
            (slug, kind, now, status, payload))
        self.conn.commit()

    def replace_professions(self, slug, profs, now) -> None:
        """Swap a character's professions in one transaction. If anything fails the old rows stay."""
        try:
            self.conn.execute("DELETE FROM professions WHERE slug=?", (slug,))
            self.conn.executemany(
                "INSERT INTO professions VALUES (?,?,?,?,?)",
                [(slug, p.name, p.skill, p.max_skill, now) for p in profs])
            self.conn.execute("DELETE FROM known_recipes WHERE slug=?", (slug,))
            self.conn.executemany(
                "INSERT OR REPLACE INTO known_recipes VALUES (?,?,?,?)",
                [(slug, p.name, rid, rname) for p in profs for rid, rname in p.recipes])
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def replace_equipment(self, slug, items, now) -> None:
        """Swap a character's gear in one transaction. If anything fails the old rows stay."""
        try:
            self.conn.execute("DELETE FROM equipment WHERE slug=?", (slug,))
            self.conn.executemany(
                "INSERT INTO equipment VALUES (?,?,?,?,?,?)",
                [(slug, i.slot, i.item_id, i.name, i.quality, now) for i in items])
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

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
               AND (slug=? OR lower(name)=? OR lower((name || COALESCE(' ' || surname, '')))=?) ORDER BY (slug=?) DESC LIMIT 1""",
            (t.replace(" ", "-"), t, t, t.replace(" ", "-"))).fetchone()

    def search_characters(self, prefix: str, limit: int = 25):
        return self.conn.execute(
            "SELECT * FROM characters WHERE in_guild=1 AND (lower(" + "(name || COALESCE(' ' || surname, ''))" + ") LIKE ? OR slug LIKE ?) "
            "ORDER BY (lower(name) LIKE ?) DESC, name, surname LIMIT ?",
            ("%" + prefix.lower() + "%", "%" + prefix.lower().replace(" ", "-") + "%", prefix.lower() + "%", limit)).fetchall()

    def roster(self, class_name=None, min_level=None, limit=None):
        q, args = "SELECT * FROM characters WHERE in_guild=1", []
        if class_name:
            q += " AND lower(class_name)=?"; args.append(class_name.lower())
        if min_level:
            q += " AND level>=?"; args.append(min_level)
        q += " ORDER BY level DESC, name, surname"
        if limit:
            q += " LIMIT ?"; args.append(limit)
        return self.conn.execute(q, args).fetchall()

    def professions_for(self, slug):
        return self.conn.execute(
            "SELECT * FROM professions WHERE slug=? ORDER BY skill DESC", (slug,)).fetchall()

    def equipment_for(self, slug):
        return self.conn.execute("SELECT * FROM equipment WHERE slug=?", (slug,)).fetchall()

    def who_has_profession(self, text: str):
        return self.conn.execute(
            """SELECT c.name, c.surname, c.level, p.profession, p.skill, p.max_skill, p.fetched_at
               FROM professions p JOIN characters c ON c.slug=p.slug
               WHERE c.in_guild=1 AND lower(p.profession) LIKE ?
               ORDER BY p.skill DESC, c.name, c.surname""", ("%" + text.lower() + "%",)).fetchall()

    def search_items(self, text: str):
        return self.conn.execute(
            """SELECT c.name, c.surname, c.level, e.slot, e.item_name, e.quality, e.fetched_at
               FROM equipment e JOIN characters c ON c.slug=e.slug
               WHERE c.in_guild=1 AND lower(e.item_name) LIKE ?
               ORDER BY c.name, c.surname""", ("%" + text.lower() + "%",)).fetchall()

    def item_names(self, text: str, limit: int = 25):
        """Distinct equipped item names containing `text`, with how many guild members wear each.
        Feeds the type-ahead on /whohas."""
        return self.conn.execute(
            """SELECT e.item_name AS name, COUNT(*) AS n
               FROM equipment e JOIN characters c ON c.slug=e.slug
               WHERE c.in_guild=1 AND lower(e.item_name) LIKE ?
               GROUP BY e.item_name ORDER BY n DESC, e.item_name LIMIT ?""",
            ("%" + text.strip().lower() + "%", limit)).fetchall()

    def profession_names(self, text: str, limit: int = 25):
        return self.conn.execute(
            """SELECT p.profession AS name, COUNT(*) AS n
               FROM professions p JOIN characters c ON c.slug=p.slug
               WHERE c.in_guild=1 AND lower(p.profession) LIKE ?
               GROUP BY p.profession ORDER BY p.profession LIMIT ?""",
            ("%" + text.strip().lower() + "%", limit)).fetchall()

    # ---- recipes ------------------------------------------------------
    def replace_recipes(self, rows, now) -> None:
        """Bring the recipe catalogue up to date in one transaction, keeping what we already looked up
        (the item each recipe makes). rows: (profession, recipe_id, name, category)."""
        try:
            self.conn.executemany(
                """INSERT INTO recipes (profession, recipe_id, name, category, fetched_at) VALUES (?,?,?,?,?)
                   ON CONFLICT(profession, recipe_id) DO UPDATE SET name=excluded.name,
                     category=excluded.category, fetched_at=excluded.fetched_at""",
                [(p, rid, n, cat, now) for p, rid, n, cat in rows])
            self.conn.execute("DELETE FROM recipes WHERE fetched_at<>?", (now,))      # gone from Blizzard's list
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def recipes_needing_item(self):
        return self.conn.execute(
            "SELECT DISTINCT recipe_id FROM recipes WHERE item_id IS NULL ORDER BY recipe_id").fetchall()

    def set_recipe_item(self, recipe_id: int, item_id: int | None) -> None:
        self.conn.execute("UPDATE recipes SET item_id=? WHERE recipe_id=?", (item_id or 0, recipe_id))
        self.conn.commit()

    def items_needed(self):
        """Item ids that recipes make and that we have no row for, or whose stats we have not read yet."""
        return self.conn.execute(
            """SELECT DISTINCT r.item_id FROM recipes r LEFT JOIN items i ON i.item_id=r.item_id
               WHERE r.item_id>0 AND (i.item_id IS NULL OR i.stats_loaded=0) ORDER BY r.item_id""").fetchall()

    def save_item(self, it) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO items (item_id, name, quality, level, required_level, item_class, item_subclass,
                 inventory_type, stats_loaded) VALUES (?,?,?,?,?,?,?,?,1)""",
            (it.item_id, it.name, it.quality, it.level, it.required_level,
             it.item_class, it.item_subclass, it.inventory_type))
        self.conn.execute("DELETE FROM item_stats WHERE item_id=?", (it.item_id,))
        self.conn.executemany("INSERT OR REPLACE INTO item_stats VALUES (?,?,?,?)",
                              [(it.item_id, code, label, value) for code, label, value in it.stats])
        self.conn.commit()

    def kind_pairs(self):
        return self.conn.execute(
            "SELECT item_class, item_subclass, COUNT(*) AS n FROM items GROUP BY item_class, item_subclass").fetchall()

    def stat_facets(self, text: str = "", limit: int = 25):
        """Stats that craftable items give, most common first. Rows: code, name, n."""
        return self.conn.execute(
            """SELECT stat AS code, MIN(label) AS name, COUNT(DISTINCT item_id) AS n FROM item_stats
               WHERE lower(label) LIKE ? GROUP BY stat ORDER BY n DESC, name LIMIT ?""",
            ("%" + text.strip().lower() + "%", limit)).fetchall()

    def item_facets(self, column: str, text: str = "", item_class: str | None = None, limit: int = 25,
                    item_subclass: str | None = None):
        """Distinct values (item_class / item_subclass / inventory_type) among craftable items, for dropdowns,
        optionally narrowed to one kind and/or type."""
        assert column in ("item_class", "item_subclass", "inventory_type")
        q = f"SELECT {column} AS name, COUNT(*) AS n FROM items WHERE {column} IS NOT NULL AND lower({column}) LIKE ?"
        args: list = ["%" + text.strip().lower() + "%"]
        if item_class:
            q += " AND item_class=?"
            args.append(item_class)
        if item_subclass:
            q += " AND item_subclass=?"
            args.append(item_subclass)
        return self.conn.execute(q + f" GROUP BY {column} ORDER BY {column} LIMIT ?", (*args, limit)).fetchall()

    def craftable(self, item_class=None, item_subclass=None, slot=None, min_level=None, max_level=None,
                  profession=None, only_known=True, limit=200, stat=None, gaps_only=False):
        """Items that recipes make, filtered, each with the guild members who can make it. Highest level first."""
        q = """SELECT i.item_id, i.name, i.quality, i.required_level, i.item_class, i.item_subclass, i.inventory_type,
                 r.profession,
                 (SELECT GROUP_CONCAT(c.name || COALESCE(' ' || c.surname, ''), ', ')
                    FROM known_recipes k JOIN characters c ON c.slug=k.slug
                   WHERE k.profession=r.profession AND k.recipe_id=r.recipe_id AND c.in_guild=1) AS knowers
               FROM recipes r JOIN items i ON i.item_id=r.item_id WHERE 1=1"""
        args: list = []
        for col, val in (("i.item_class", item_class), ("i.item_subclass", item_subclass),
                         ("i.inventory_type", slot), ("r.profession", profession)):
            if not val:
                continue
            if isinstance(val, (tuple, list)):                  # several allowed values, e.g. every one-hand slot
                q += f" AND lower({col}) IN ({','.join('?' * len(val))})"
                args.extend(v.strip().lower() for v in val)
            else:
                q += f" AND lower({col})=?"
                args.append(val.strip().lower())
        if min_level is not None:
            q += " AND COALESCE(i.required_level,0)>=?"
            args.append(min_level)
        if max_level is not None:
            q += " AND COALESCE(i.required_level,0)<=?"
            args.append(max_level)
        if stat:
            q += " AND EXISTS (SELECT 1 FROM item_stats st WHERE st.item_id=i.item_id AND st.stat=?)"
            args.append(stat)
        if only_known or gaps_only:
            q += (" AND NOT" if gaps_only else " AND") + """ EXISTS (SELECT 1 FROM known_recipes k JOIN characters c ON c.slug=k.slug
                                  WHERE k.profession=r.profession AND k.recipe_id=r.recipe_id AND c.in_guild=1)"""
        return self.conn.execute(q + " ORDER BY COALESCE(i.required_level,0) DESC, i.name LIMIT ?",
                                 (*args, limit)).fetchall()

    def catalog_professions(self, text: str = ""):
        return self.conn.execute(
            """SELECT profession AS name, COUNT(*) AS n FROM recipes WHERE lower(profession) LIKE ?
               GROUP BY profession ORDER BY profession""", ("%" + text.strip().lower() + "%",)).fetchall()

    def recipe_names_all(self, text: str, limit: int = 25):
        """Type-ahead for /whocan: recipes someone knows first (with how many), then catalogue recipes nobody
        knows (n = 0). Rows: name, profession, n."""
        rows = [dict(name=r["name"], profession=r["profession"], n=r["n"]) for r in self.recipe_names(text, limit)]
        if len(rows) < limit:
            have = {(r["name"], r["profession"]) for r in rows}
            more = self.conn.execute(
                """SELECT r.name AS name, r.profession AS profession FROM recipes r
                   WHERE lower(r.name) LIKE ? AND NOT EXISTS (
                     SELECT 1 FROM known_recipes k JOIN characters c ON c.slug=k.slug
                      WHERE c.in_guild=1 AND k.profession=r.profession AND k.recipe_id=r.recipe_id)
                   ORDER BY r.name LIMIT ?""", ("%" + text.strip().lower() + "%", limit * 2)).fetchall()
            for r in more:
                if (r["name"], r["profession"]) not in have and len(rows) < limit:
                    rows.append(dict(name=r["name"], profession=r["profession"], n=0))
                    have.add((r["name"], r["profession"]))
        return rows

    def catalog_recipe(self, name: str):
        """Catalogue entries (one per profession) for an exact recipe name."""
        return self.conn.execute(
            """SELECT r.profession, r.recipe_id, r.name, r.category, i.required_level, i.item_subclass, i.inventory_type
               FROM recipes r LEFT JOIN items i ON i.item_id=r.item_id WHERE lower(r.name)=? ORDER BY r.profession""",
            (name.strip().lower(),)).fetchall()

    def add_wanted(self, name: str, profession, discord_id: int, now: str) -> None:
        self.conn.execute("INSERT INTO wanted (name, profession, discord_id, asked_at) VALUES (?,?,?,?)",
                          (name, profession, discord_id, now))
        self.conn.commit()

    def wanted_top(self, limit: int = 20):
        return self.conn.execute(
            """SELECT name, profession, COUNT(*) AS n, COUNT(DISTINCT discord_id) AS people, MAX(asked_at) AS last_at
               FROM wanted GROUP BY name, profession ORDER BY n DESC, last_at DESC LIMIT ?""", (limit,)).fetchall()

    def profession_coverage(self):
        """Per profession in the catalogue: how many guildies have it, the best skill, and how many of its
        recipes anyone in the guild knows."""
        return self.conn.execute(
            """SELECT r.profession AS name, COUNT(*) AS total,
                 (SELECT COUNT(*) FROM professions p JOIN characters c ON c.slug=p.slug
                   WHERE c.in_guild=1 AND p.profession=r.profession) AS members,
                 (SELECT MAX(p.skill) FROM professions p JOIN characters c ON c.slug=p.slug
                   WHERE c.in_guild=1 AND p.profession=r.profession) AS best,
                 (SELECT COUNT(*) FROM recipes r2 WHERE r2.profession=r.profession AND EXISTS (
                    SELECT 1 FROM known_recipes k JOIN characters c ON c.slug=k.slug
                     WHERE c.in_guild=1 AND k.profession=r2.profession AND k.recipe_id=r2.recipe_id)) AS known
               FROM recipes r GROUP BY r.profession ORDER BY r.profession""").fetchall()

    def best_in_profession(self, profession: str, limit: int = 3):
        return self.conn.execute(
            """SELECT c.name, c.surname, p.skill, p.max_skill FROM professions p JOIN characters c ON c.slug=p.slug
               WHERE c.in_guild=1 AND p.profession=? ORDER BY p.skill DESC, c.name LIMIT ?""",
            (profession, limit)).fetchall()

    def missing_recipes(self, profession: str, limit: int = 5000):
        """Recipes of a profession that nobody in the guild knows: items with a level requirement first, lowest
        first, then the ones with none."""
        return self.conn.execute(
            """SELECT r.recipe_id, r.name, r.category, i.required_level, i.item_class, i.item_subclass, i.inventory_type
               FROM recipes r LEFT JOIN items i ON i.item_id=r.item_id
               WHERE r.profession=? AND NOT EXISTS (
                 SELECT 1 FROM known_recipes k JOIN characters c ON c.slug=k.slug
                  WHERE c.in_guild=1 AND k.profession=r.profession AND k.recipe_id=r.recipe_id)
               ORDER BY COALESCE(NULLIF(i.required_level, 0), 999), r.name LIMIT ?""", (profession, limit)).fetchall()

    def recipes_for(self, profession: str, match: str = ""):
        """Catalogue recipes of a profession (name contains `match`), each with the guild members who know it."""
        rows = self.conn.execute(
            """SELECT r.recipe_id, r.name, r.category,
                 (SELECT GROUP_CONCAT(c.name || COALESCE(' ' || c.surname, ''), ', ')
                    FROM known_recipes k JOIN characters c ON c.slug=k.slug
                   WHERE k.profession=r.profession AND k.recipe_id=r.recipe_id AND c.in_guild=1) AS knowers
               FROM recipes r WHERE lower(r.profession)=? AND lower(r.name) LIKE ?
               ORDER BY r.category, r.name""", (profession.strip().lower(), "%" + match.strip().lower() + "%")).fetchall()
        return rows

    def recipe_names(self, text: str, limit: int = 25):
        """Recipe names someone in the guild knows, with how many know each (type-ahead for /whocan)."""
        return self.conn.execute(
            """SELECT k.name AS name, k.profession AS profession, COUNT(DISTINCT k.slug) AS n
               FROM known_recipes k JOIN characters c ON c.slug=k.slug
               WHERE c.in_guild=1 AND lower(k.name) LIKE ?
               GROUP BY k.name, k.profession ORDER BY n DESC, k.name LIMIT ?""",
            ("%" + text.strip().lower() + "%", limit)).fetchall()

    def who_can_craft(self, name: str, profession: str | None = None):
        q = """SELECT c.name, c.surname, c.level, k.profession, p.skill, p.max_skill, p.fetched_at
               FROM known_recipes k JOIN characters c ON c.slug=k.slug
               LEFT JOIN professions p ON p.slug=k.slug AND p.profession=k.profession
               WHERE c.in_guild=1 AND lower(k.name)=?"""
        args = [name.strip().lower()]
        if profession:
            q += " AND k.profession=?"
            args.append(profession)
        return self.conn.execute(q + " ORDER BY p.skill DESC, c.name, c.surname", args).fetchall()

    # ---- discord <-> character links ---------------------------------
    def link(self, discord_id: int, slug: str) -> bool:
        """Link a character. Returns True if it became the main."""
        has_main = self.main_for(discord_id) is not None
        self.conn.execute(
            "INSERT OR IGNORE INTO links (discord_id, slug, is_main) VALUES (?,?,?)",
            (discord_id, slug, 0 if has_main else 1))
        self.conn.commit()
        return not has_main

    def _promote_alt(self, discord_id: int) -> None:
        """If this member has links but no main, make the first alt (by slug) their main."""
        if self.conn.execute("SELECT 1 FROM links WHERE discord_id=? AND is_main=1", (discord_id,)).fetchone():
            return
        nxt = self.conn.execute(
            "SELECT slug FROM links WHERE discord_id=? ORDER BY slug LIMIT 1", (discord_id,)).fetchone()
        if nxt:
            self.conn.execute("UPDATE links SET is_main=1 WHERE discord_id=? AND slug=?",
                              (discord_id, nxt["slug"]))

    def release(self, slug: str) -> None:
        """Remove every Discord link to a character (officer override). A previous owner who lost
        their main keeps a main: one of their remaining characters is promoted."""
        owners = [r["discord_id"] for r in self.conn.execute(
            "SELECT discord_id FROM links WHERE slug=?", (slug,))]
        self.conn.execute("DELETE FROM links WHERE slug=?", (slug,))
        for d in owners:
            self._promote_alt(d)
        self.conn.commit()

    def unlink(self, discord_id: int, slug: str) -> None:
        self.conn.execute("DELETE FROM links WHERE discord_id=? AND slug=?", (discord_id, slug))
        self._promote_alt(discord_id)
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
               WHERE l.discord_id=? ORDER BY l.is_main DESC, c.name, c.surname""", (discord_id,)).fetchall()

    def owner_of(self, slug: str):
        r = self.conn.execute("SELECT discord_id FROM links WHERE slug=? ORDER BY is_main DESC LIMIT 1",
                              (slug,)).fetchone()
        return r["discord_id"] if r else None

    MAX_CLAIMS = 5   # characters one Discord account may claim itself (officers can link more)

    def unclaimed_characters(self, query: str = ""):
        """Unclaimed guild characters, alphabetical by full name; `query` keeps names containing it."""
        return self.conn.execute(
            """SELECT * FROM characters WHERE in_guild=1
               AND slug NOT IN (SELECT slug FROM links)
               AND lower((name || COALESCE(' ' || surname, ''))) LIKE ? ORDER BY lower(name), lower(COALESCE(surname, ''))""",
            ("%" + query.strip().lower() + "%",)).fetchall()

    def claim(self, discord_id: int, slugs) -> dict:
        """Self-service claim. First claim wins; a taken character is skipped, never stolen, and one
        account is capped at MAX_CLAIMS. Returns {'linked': [...], 'taken': [...], 'over_cap': [...]}."""
        out = {"linked": [], "taken": [], "over_cap": []}
        have = len(self.characters_for(discord_id))
        for slug in slugs:
            if not self.conn.execute("SELECT 1 FROM characters WHERE slug=? AND in_guild=1", (slug,)).fetchone():
                continue
            owner = self.owner_of(slug)
            if owner == discord_id:
                continue
            if owner:
                out["taken"].append(slug)
            elif have >= self.MAX_CLAIMS:
                out["over_cap"].append(slug)
            else:
                self.link(discord_id, slug)
                out["linked"].append(slug)
                have += 1
        return out

    def unlink_all(self, discord_id: int) -> int:
        """Officer purge: remove every link a Discord account holds. Returns how many were removed."""
        n = self.conn.execute("DELETE FROM links WHERE discord_id=?", (discord_id,)).rowcount
        self.conn.commit()
        return n

    def claims(self):
        return self.conn.execute(
            """SELECT l.discord_id, l.is_main, c.name, c.surname, c.level, c.class_name
               FROM links l JOIN characters c ON c.slug=l.slug
               ORDER BY l.discord_id, l.is_main DESC, c.name, c.surname""").fetchall()

    # ---- raids --------------------------------------------------------
    def create_raid(self, title, starts_at_utc_iso, size, created_by, caps: dict | None = None) -> int:
        caps = caps or {}
        from .raids import size_from_limits
        size = size_from_limits(caps.get("tank"), caps.get("healer"), caps.get("dps")) or size
        cur = self.conn.execute(
            """INSERT INTO raids (title, starts_at, size, cap_tank, cap_healer, cap_dps, created_by)
               VALUES (?,?,?,?,?,?,?)""",
            (title, starts_at_utc_iso, size, caps.get("tank") or None, caps.get("healer") or None,
             caps.get("dps") or None, created_by))
        self.conn.commit()
        return cur.lastrowid

    def delete_raid(self, raid_id) -> None:
        """Remove a raid that never got posted (and any signups on it)."""
        self.conn.execute("DELETE FROM signups WHERE raid_id=?", (raid_id,))
        self.conn.execute("DELETE FROM raids WHERE id=?", (raid_id,))
        self.conn.commit()

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
        now = self.get_raid(raid_id)
        from .raids import size_from_limits
        total = size_from_limits(now["cap_tank"], now["cap_healer"], now["cap_dps"])
        self.conn.execute(
            "UPDATE raids SET title=?, starts_at=?, size=?, reminded=? WHERE id=?",
            (title or raid["title"], new_start, total or size or raid["size"], reminded, raid_id))
        self.conn.commit()

    def started_open(self, now_utc: datetime):
        """Open raids whose start time has passed and that still need their buttons removed."""
        return [r for r in self.open_raids() if datetime.fromisoformat(r["starts_at"]) <= now_utc]

    def mark_closed(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET status='closed' WHERE id=?", (raid_id,))
        self._expire_raid_offers(raid_id)                  # the raid has started: no more spots to give out
        self.conn.commit()

    def closed_ended_before(self, now_utc: datetime, hours: int):
        """Started raids that began more than `hours` ago and whose post is still up."""
        from datetime import timedelta
        cutoff = now_utc - timedelta(hours=hours)
        return [r for r in self.conn.execute("SELECT * FROM raids WHERE status='closed'").fetchall()
                if datetime.fromisoformat(r["starts_at"]) <= cutoff]

    def mark_ended(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET status='ended' WHERE id=?", (raid_id,))
        self._expire_raid_offers(raid_id)
        self.conn.commit()

    def raid_by_message(self, message_id: int):
        return self.conn.execute("SELECT * FROM raids WHERE message_id=?", (message_id,)).fetchone()

    def raid_by_event(self, event_id: int):
        return self.conn.execute("SELECT * FROM raids WHERE discord_event_id=?", (event_id,)).fetchone()

    def cancel_raid(self, raid_id) -> None:
        self.conn.execute("UPDATE raids SET status='cancelled' WHERE id=?", (raid_id,))
        self._expire_raid_offers(raid_id)
        self.conn.commit()

    def upsert_signup(self, raid_id, discord_id, slug, role, now, wanted=None) -> None:
        self.conn.execute(
            """INSERT INTO signups (raid_id, discord_id, slug, role, updated_at, wanted) VALUES (?,?,?,?,?,?)
               ON CONFLICT(raid_id, discord_id) DO UPDATE SET slug=excluded.slug,
                 role=excluded.role, updated_at=excluded.updated_at, wanted=excluded.wanted""",
            (raid_id, discord_id, slug, role, now, wanted))
        self.conn.commit()

    def remove_signup(self, raid_id, discord_id) -> None:
        self.conn.execute("DELETE FROM signups WHERE raid_id=? AND discord_id=?", (raid_id, discord_id))
        self.conn.commit()

    # ---- bench queue offers ------------------------------------------------
    def create_offer(self, raid_id, discord_id, role, now, ping_at, expires_at) -> int:
        cur = self.conn.execute(
            "INSERT INTO offers (raid_id, discord_id, role, sent_at, ping_at, expires_at) VALUES (?,?,?,?,?,?)",
            (raid_id, discord_id, role, now, ping_at, expires_at))
        self.conn.commit()
        return cur.lastrowid

    def get_offer(self, offer_id):
        return self.conn.execute("SELECT * FROM offers WHERE id=?", (offer_id,)).fetchone()

    def set_offer_state(self, offer_id, state) -> None:
        self.conn.execute("UPDATE offers SET state=? WHERE id=?", (state, offer_id))
        self.conn.commit()

    def offers_for_raid(self, raid_id):
        return self.conn.execute("SELECT * FROM offers WHERE raid_id=? ORDER BY id", (raid_id,)).fetchall()

    def pending_offers(self):
        return self.conn.execute("SELECT * FROM offers WHERE state='pending' ORDER BY id").fetchall()

    def expire_old_offers(self, now_iso: str):
        """Pending offers whose time is up become expired. Returns the ones that did."""
        rows = self.conn.execute("SELECT * FROM offers WHERE state='pending' AND expires_at<=?", (now_iso,)).fetchall()
        self.conn.execute("UPDATE offers SET state='expired' WHERE state='pending' AND expires_at<=?", (now_iso,))
        self.conn.commit()
        return rows

    def set_offer_messages(self, offer_id, dm=None, chan=None) -> None:
        if dm is not None:
            self.conn.execute("UPDATE offers SET dm_msg_id=? WHERE id=?", (dm, offer_id))
        if chan is not None:
            self.conn.execute("UPDATE offers SET chan_msg_id=? WHERE id=?", (chan, offer_id))
        self.conn.commit()

    def offers_to_ping(self, now_iso: str):
        """Pending offers whose last-call time has come and that have no ping in the raid channel yet."""
        return self.conn.execute(
            "SELECT * FROM offers WHERE state='pending' AND chan_msg_id IS NULL AND ping_at<=? ORDER BY id",
            (now_iso,)).fetchall()

    def offers_to_clean(self):
        """Answered or expired offers whose messages are still lying around."""
        return self.conn.execute(
            """SELECT * FROM offers WHERE state<>'pending' AND cleaned=0
               AND (dm_msg_id IS NOT NULL OR chan_msg_id IS NOT NULL) ORDER BY id""").fetchall()

    def mark_offer_cleaned(self, offer_id) -> None:
        self.conn.execute("UPDATE offers SET cleaned=1 WHERE id=?", (offer_id,))
        self.conn.commit()

    def _expire_raid_offers(self, raid_id) -> None:
        self.conn.execute("UPDATE offers SET state='expired' WHERE raid_id=? AND state='pending'", (raid_id,))

    def signups(self, raid_id):
        return self.conn.execute(
            """SELECT s.*, c.name, c.surname, c.level, c.class_name, c.profile_at FROM signups s
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
