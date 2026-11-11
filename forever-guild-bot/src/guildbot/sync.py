"""Pull the guild roster and each member's profile, professions and gear into SQLite."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from . import blizzard as bz
from .db import Database, utcnow


@dataclass
class SyncResult:
    members: int = 0
    removed: int = 0
    failures: list[tuple[str, str, str]] = field(default_factory=list)  # (slug, kind, error)
    started_at: str = ""
    # per kind ("profile", "professions", "equipment"): how many came back ok / not_found / error
    counts: dict[str, dict[str, int]] = field(default_factory=dict)

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
        db.set_profile(slug, p.level, p.class_name, p.race_name, p.faction, ts)

    tasks = []
    for m in members:
        tasks.append(one(m.slug, "profile", client.character_profile, on_profile))
        tasks.append(one(m.slug, "professions", client.professions,
                         lambda s, d, ts: db.replace_professions(s, bz.parse_professions(d), ts)))
        tasks.append(one(m.slug, "equipment", client.equipment,
                         lambda s, d, ts: db.replace_equipment(s, bz.parse_equipment(d), ts)))
    await asyncio.gather(*tasks)

    db.prune_snapshots()
    db.set_meta("last_sync_at", utcnow())
    db.set_meta("last_sync_failures", str(len(res.failures)))
    return res


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
            db.set_recipe_item(rid, bz.parse_recipe_item(await guarded(client.recipe, rid)))
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
