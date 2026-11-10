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


async def sync_guild(db: Database, client, guild_slug: str, concurrency: int = 5) -> SyncResult:
    """Full sync. One bad character never stops the rest; failures are reported."""
    now = utcnow()
    res = SyncResult(started_at=now)

    payload = await client.guild_roster(guild_slug)
    db.save_snapshot(None, "roster", "ok", json.dumps(payload), now)
    members = bz.parse_roster(payload)
    res.members = len(members)
    for m in members:
        db.upsert_member(m.slug, m.name, m.surname, m.level, m.rank, now)
    res.removed = db.mark_absent({m.slug for m in members})

    sem = asyncio.Semaphore(concurrency)

    async def one(slug: str, kind: str, fetch, handle) -> None:
        async with sem:
            try:
                data = await fetch(slug)
            except bz.NotFound:
                db.save_snapshot(slug, kind, "not_found", None, utcnow())
                return
            except Exception as e:  # noqa: BLE001 - report and continue
                db.save_snapshot(slug, kind, "error", str(e), utcnow())
                res.failures.append((slug, kind, str(e)))
                return
            ts = utcnow()
            db.save_snapshot(slug, kind, "ok", json.dumps(data), ts)
            try:
                handle(slug, data, ts)
            except Exception as e:  # noqa: BLE001 - a parser mismatch, raw data is saved
                res.failures.append((slug, kind, f"parse: {e}"))

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

    db.set_meta("last_sync_at", utcnow())
    db.set_meta("last_sync_failures", str(len(res.failures)))
    return res
