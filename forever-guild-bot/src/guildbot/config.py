"""Configuration, read from environment variables (or a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

REQUIRED = ("DISCORD_TOKEN", "BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET", "GUILD_SLUG")


@dataclass(frozen=True)
class Config:
    discord_token: str
    discord_guild_id: int | None  # set this to make slash commands appear instantly
    blizzard_client_id: str
    blizzard_client_secret: str
    region: str
    guild_slug: str  # e.g. "my-guild-name", lowercase with dashes
    db_path: Path
    sync_minutes: int
    timezone: str  # how raid dates/times typed in Discord are read
    channel_ids: frozenset[int] = frozenset()  # commands only work in these channels; empty = anywhere


def load(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    missing = [k for k in REQUIRED if not env.get(k)]
    if missing:
        raise SystemExit(f"Missing required settings: {', '.join(missing)} (see .env.example)")
    gid = env.get("DISCORD_GUILD_ID", "").strip()
    return Config(
        discord_token=env["DISCORD_TOKEN"],
        discord_guild_id=int(gid) if gid else None,
        blizzard_client_id=env["BLIZZARD_CLIENT_ID"],
        blizzard_client_secret=env["BLIZZARD_CLIENT_SECRET"],
        region=env.get("BLIZZARD_REGION", "us").lower(),
        guild_slug=env["GUILD_SLUG"].strip().lower(),
        db_path=Path(env.get("DB_PATH", "guildbot.sqlite3")),
        sync_minutes=int(env.get("SYNC_MINUTES", "60")),
        timezone=env.get("TIMEZONE", "America/New_York"),
        channel_ids=frozenset(int(x) for x in env.get("BOT_CHANNEL_IDS", "").replace(";", ",").split(",") if x.strip()),
    )
