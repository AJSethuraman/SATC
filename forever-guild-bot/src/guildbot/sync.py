"""Pull the guild roster and each member's profile, professions and gear into SQLite."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from . import blizzard as bz
from . import legacy as L
from . import milestones as M
from .db import Database, ms_to_iso, utcnow


@dataclass
class SyncResult:
    members: int = 0
    removed: int = 0
    failures: list[tuple[str, str, str]] = field(default_factory=list)  # (slug, kind, error)
    started_at: str = ""
    # per kind ("profile", "professions", "equipment"): how many came back ok / not_found / error
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    milestones: list = field(default_factory=list)   # (kind, slug, detail, value) reached since the last sync

    def summary(self) -> str:
        """One line per kind with the denominator, e.g. 'profile: 280 of 300 loaded, 20 not found'."""
        lines = []
        for kind, c in sorted(self.counts.items()):
            total = sum(c.values())
            extra = [f"{c[k]} {label}" for k, label in (("not_found", "not found"), ("error", "failed"))
                     if c.get(k)]
            lines.append(f"{kind}: {c.get('ok', 0)} of {total} loaded" + (", " + ", ".join(extra) if extra else ""))
        return "\n".join(lines)


async def sync_guild(db: Database, client, guild_slug: str, concurrency: int = 5) -> SyncResult:
    """Full sync. One bad character never stops the rest; failures are reported."""
    now = utcnow()
    res = SyncResult(started_at=now)
    before_levels, before_skills = db.level_snapshot(), db.skill_snapshot()

    payload = await client.guild_roster(guild_slug)
    try:
        members = bz.parse_roster(payload)
    except Exception:
        db.save_snapshot(None, "roster", "parse_error", json.dumps(payload), now)   # keep the raw response
        raise
    db.save_snapshot(None, "roster", "ok", json.dumps(payload), now)
    res.members = len(members)
    for m in members:
        db.upsert_member(m.slug, m.name, m.surname, m.level, m.rank, now)
    res.removed = db.mark_absent({m.slug for m in members})

    sem = asyncio.Semaphore(concurrency)

    def tally(kind: str, status: str) -> None:
        res.counts.setdefault(kind, {}).setdefault(status, 0)
        res.counts[kind][status] += 1

    async def one(slug: str, kind: str, fetch, handle) -> None:
        async with sem:
            try:
                data = await fetch(slug)
            except bz.NotFound:
                db.save_snapshot(slug, kind, "not_found", None, utcnow())
                tally(kind, "not_found")
                return
            except Exception as e:  # noqa: BLE001 - report and continue
                db.save_snapshot(slug, kind, "error", str(e), utcnow())
                res.failures.append((slug, kind, str(e)))
                tally(kind, "error")
                return
            ts = utcnow()
            try:
                handle(slug, data, ts)
            except Exception as e:  # noqa: BLE001 - a parser mismatch; the raw response is kept
                db.save_snapshot(slug, kind, "parse_error", json.dumps(data), ts)
                res.failures.append((slug, kind, f"parse: {e}"))
                tally(kind, "error")
            else:
                db.save_snapshot(slug, kind, "ok", json.dumps(data), ts)   # "ok" = parsed and stored
                tally(kind, "ok")

    def on_profile(slug, data, ts):
        p = bz.parse_profile(data)
        db.set_profile(slug, p.level, p.class_name, p.race_name, p.faction, ts,
                       last_login_at=ms_to_iso(p.last_login_ms), item_level=p.item_level)

    known_achievements = db.achievement_slugs()
    tasks = []
    for m in members:
        tasks.append(one(m.slug, "profile", client.character_profile, on_profile))
        tasks.append(one(m.slug, "professions", client.professions,
                         lambda s, d, ts: db.replace_professions(s, bz.parse_professions(d), ts)))
        tasks.append(one(m.slug, "equipment", client.equipment,
                         lambda s, d, ts: db.replace_equipment(s, bz.parse_equipment(d), ts)))
        if hasattr(client, "achievements"):
            tasks.append(one(m.slug, "achievements", client.achievements,
                             lambda s, d, ts: db.replace_achievements(s, bz.parse_achievements(d), ts)))
        if hasattr(client, "collections"):
            tasks.append(one(m.slug, "collections", client.collections,
                             lambda s, d, ts: db.set_account_items(s, bz.account_items(d["mounts"], d["toys"]))))
    await asyncio.gather(*tasks)

    found = M.find(before_levels, db.level_snapshot(), before_skills, db.skill_snapshot())
    found += legacy_milestones(db, known_achievements)
    res.milestones = db.new_milestones(found, utcnow())
    db.prune_snapshots()
    db.set_meta("last_sync_at", utcnow())
    db.set_meta("last_sync_failures", str(len(res.failures)))
    return res


def legacy_milestones(db: Database, known_before: set[str]) -> list:
    """New Legacy completions worth announcing. The first time there is anything to compare (catalogue
    loaded, achievements stored), everything already finished is marked as seen and nothing is announced."""
    from datetime import datetime, timezone
    if not db.legacy_catalog():
        return []
    completions = db.legacy_completions()
    if db.get_meta("legacy_seeded") is None:
        db.add_legacy_seen({(r["challenge_id"], r["completed_at"]) for r in completions})
        db.set_meta("legacy_seeded", utcnow())
        return []
    holders = {}
    for r in db.roster():
        holders[r["slug"]] = {"slug": r["slug"], "level": r["level"], "class_name": r["class_name"],
                              "skills": {p["profession"]: p["skill"] for p in db.professions_for(r["slug"])}}
    player_of = {s: n for n, p in enumerate(board_players(db)) for s in p["slugs"]}   # claims, then likely alts
    found, handled = L.new_completions(completions, db.legacy_seen(), known_before, holders,
                                       datetime.now(timezone.utc), player_of, db.legacy_posted())
    db.add_legacy_seen(handled)
    return found


def likely_alts(db: Database) -> list[dict]:
    """legacy.likely_alts over what is stored, honouring every "not mine" answer."""
    return L.likely_alts(db.legacy_completions(), db.account_items(), db.owners(), db.alt_rejections())


def board_players(db: Database) -> list[dict]:
    """legacy.players over what is stored: claims, the likely-alts guess, and every guild character with Legacy data."""
    in_guild = {r["slug"] for r in db.roster()}
    claims = {d: kept for d, slugs in db.claimed_by_member().items()          # a claim that left the guild is not
              if (kept := [s for s in slugs if s in in_guild])}              # on the board, nor its points
    return L.players(claims, likely_alts(db), db.achievement_slugs() & in_guild)


ASK_AGAIN_DAYS = 7


def alt_question(db: Database, discord_id: int, now: str) -> str | None:
    """A character the likely-alts guess puts with this member's claim that they have not answered about,
    or None. Not asked again within a week of the last time."""
    from datetime import datetime, timedelta
    asked = db.alt_asked(discord_id)
    cutoff = (datetime.fromisoformat(now) - timedelta(days=ASK_AGAIN_DAYS)).isoformat(timespec="seconds")
    for p in board_players(db):
        if p["owner"] != discord_id:
            continue
        for slug in p["guessed"]:
            a = asked.get(slug)
            if a is None or (a["answer"] is None and a["asked_at"] < cutoff):
                return slug
    return None


def likely_alt_news(db: Database) -> list[tuple[dict, list[tuple[str, str]]]]:
    """Groups of characters that are probably one player, with the pairs in each the owner has not been told
    about yet. A pair both claimed by the same member is not news. Mark pairs told with add_likely_alts_seen
    once the message has gone."""
    owners = db.owners()
    seen = db.likely_alts_seen()
    out = []
    for g in likely_alts(db):
        s = g["slugs"]
        pairs = [(a, b) for i, a in enumerate(s) for b in s[i + 1:]
                 if (a, b) not in seen and not (owners.get(a) and owners.get(a) == owners.get(b))]
        if pairs:
            out.append((g, pairs))
    return out


LEGACY_MAX_AGE_DAYS = 7


async def sync_legacy_catalog(db: Database, client, force: bool = False) -> int:
    """Fetch the Legacy challenges from Blizzard's static achievement data (about 190 calls) and store the
    ones whose reward is a Legacy point. Skipped while the stored copy is under a week old. Returns how
    many achievements were stored (0 = skipped)."""
    from datetime import datetime, timedelta, timezone
    last = db.get_meta("legacy_at")
    if last and not force and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(days=LEGACY_MAX_AGE_DAYS):
        return 0
    now = utcnow()
    found: list[tuple[int, str, str]] = []          # (achievement_id, category, subcategory)

    async def walk(cid: int, root: str, sub: str, depth: int) -> None:
        ach, subs = bz.parse_achievement_category(await client.achievement_category(cid))
        found.extend((aid, root, sub) for aid, _ in ach)
        if depth < 3:
            for sid, sname in subs:
                await walk(sid, root, sname, depth + 1)

    for cid, name in bz.parse_achievement_category_index(await client.achievement_category_index()):
        await walk(cid, name, name, 0)
    sem = asyncio.Semaphore(8)
    rows = []

    async def one(aid: int, root: str, sub: str) -> None:
        async with sem:
            info = bz.parse_achievement(await client.achievement(aid))
        if info.legacy_point:
            rows.append((info.id, info.name, root, sub, info.description, info.display_order))

    await asyncio.gather(*(one(*x) for x in dict.fromkeys(found)))
    if not rows:
        raise bz.BlizzardError("no Legacy-point achievements found: Blizzard's data may have changed")
    db.replace_legacy_catalog(rows, now)
    db.set_meta("legacy_at", now)
    return len(rows)


RECIPES_MAX_AGE_DAYS = 7


async def sync_recipe_catalog(db: Database, client, force: bool = False) -> int:
    """Fetch every profession's recipes from Blizzard's static data (about forty calls) and store them.
    Skipped when the stored copy is newer than a week. Returns the number of recipes stored (0 = skipped)."""
    from datetime import datetime, timedelta, timezone
    last = db.get_meta("recipes_at")
    if last and not force and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(days=RECIPES_MAX_AGE_DAYS):
        return 0
    now = utcnow()
    index = bz.parse_profession_index(await client.profession_index())
    rows = []
    for pid, pname in index:
        if "[DNT]" in pname:                       # Blizzard's own "do not translate" test entry
            continue
        for tid, _tname in bz.parse_profession_tiers(await client.profession(pid)):
            data = await client.skill_tier(pid, tid)
            try:
                found = bz.parse_skill_tier(data)
            except Exception:
                db.save_snapshot(None, f"skill-tier:{pid}:{tid}", "parse_error", json.dumps(data), now)
                raise
            db.save_snapshot(None, f"skill-tier:{pid}:{tid}", "ok", json.dumps(data), now)
            rows.extend((pname, rid, rname, cat) for cat, rid, rname in found)
    db.replace_recipes(rows, now)
    db.set_meta("recipes_at", now)
    return len(rows)


async def sync_item_catalog(db: Database, client, concurrency: int = 8, budget: int = 6000) -> tuple[int, int]:
    """Look up, for every recipe, the item it makes and that item's class, slot and level. Only what is
    still missing is fetched, so after the first run this is a handful of calls. Returns (recipes, items)
    looked up this time. A single bad response is logged and skipped; it never stops the rest."""
    import logging
    log = logging.getLogger("guildbot")
    sem = asyncio.Semaphore(concurrency)
    done = {"recipes": 0, "items": 0}
    calls = {"n": 0}

    async def guarded(fetch, arg):
        async with sem:
            calls["n"] += 1
            return await fetch(arg)

    async def one_recipe(rid: int) -> None:
        try:
            item, made, reagents = bz.parse_recipe(await guarded(client.recipe, rid))
            db.set_recipe_item(rid, item, made, reagents)
            done["recipes"] += 1
        except bz.NotFound:
            db.set_recipe_item(rid, None)             # no such recipe in the data: do not ask again
        except Exception as e:  # noqa: BLE001
            log.warning("recipe %s skipped: %s", rid, e)

    todo = [r["recipe_id"] for r in db.recipes_needing_item()][:budget]
    await asyncio.gather(*(one_recipe(r) for r in todo))

    async def one_item(iid: int) -> None:
        try:
            db.save_item(bz.parse_catalog_item(await guarded(client.item, iid)))
            done["items"] += 1
        except bz.NotFound:
            db.save_item(bz.CatalogItem(iid, f"Item {iid}", None, None, None, None, None, None))
        except Exception as e:  # noqa: BLE001
            log.warning("item %s skipped: %s", iid, e)

    todo_items = [r["item_id"] for r in db.items_needed()][:max(0, budget - calls["n"])]
    await asyncio.gather(*(one_item(i) for i in todo_items))
    return done["recipes"], done["items"]
