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
    db.save_snapshot(None, "roster", "ok", json.dumps(payload), now)
    members = bz.parse_roster(payload)
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
            db.save_snapshot(slug, kind, "ok", json.dumps(data), ts)
            try:
                handle(slug, data, ts)
                tally(kind, "ok")
            except Exception as e:  # noqa: BLE001 - a parser mismatch, raw data is saved
                res.failures.append((slug, kind, f"parse: {e}"))
                tally(kind, "error")

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
