"""Blizzard Battle.net API client for WoW Forever.

Everything that touches Blizzard's (undocumented) Forever API lives in this file.
If Blizzard changes a field name, this is the only place to fix.

Field names below follow community reports (Nov 2026) and the standard Blizzard
profile API shape. They have NOT been checked against a live response yet; every
raw response is stored by sync.py so parsers can be corrected from real data.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

TOKEN_URL = "https://oauth.battle.net/token"


class BlizzardError(Exception):
    pass


class NotFound(BlizzardError):
    pass


@dataclass(frozen=True)
class Member:
    slug: str
    name: str
    surname: str | None
    level: int | None
    rank: int | None


@dataclass(frozen=True)
class Profile:
    level: int | None
    class_name: str | None
    race_name: str | None
    faction: str | None


@dataclass(frozen=True)
class Profession:
    name: str
    skill: int
    max_skill: int


@dataclass(frozen=True)
class Item:
    slot: str
    item_id: int | None
    name: str
    quality: str | None


def _name(v: Any) -> str | None:
    """Blizzard names are sometimes a string, sometimes {'en_US': ...}, sometimes {'name': ...}."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        if "name" in v:
            return _name(v["name"])
        if "en_US" in v:
            return v["en_US"]
        for val in v.values():
            if isinstance(val, str):
                return val
    return None


def parse_roster(payload: dict) -> list[Member]:
    if "members" not in payload:
        raise BlizzardError(f"roster response has no 'members' (keys: {sorted(payload)})")
    out: list[Member] = []
    for m in payload["members"]:
        c = m.get("character") or {}
        name = c.get("name")
        if not name:
            continue
        surname = c.get("surname")
        slug = c.get("slug") or "-".join(p for p in (name, surname) if p).lower()
        out.append(Member(slug=slug.lower(), name=name, surname=surname,
                          level=c.get("level"), rank=m.get("rank")))
    return out


def parse_profile(payload: dict) -> Profile:
    if not any(k in payload for k in ("level", "character_class", "race", "faction")):
        raise BlizzardError(f"profile response not recognised (keys: {sorted(payload)})")
    return Profile(
        level=payload.get("level"),
        class_name=_name(payload.get("character_class")),
        race_name=_name(payload.get("race")),
        faction=_name(payload.get("faction")),
    )


def parse_professions(payload: dict) -> list[Profession]:
    if not any(k in payload for k in ("primaries", "secondaries", "professions")):
        raise BlizzardError(f"professions response not recognised (keys: {sorted(payload)})")
    out: list[Profession] = []
    for group in ("primaries", "secondaries", "professions"):
        for p in payload.get(group) or []:
            name = _name(p.get("profession"))
            if not name:
                continue
            if "skill_points" in p:
                skill, mx = p["skill_points"], p.get("max_skill_points", 0)
            else:
                tiers = p.get("tiers") or []
                if not tiers:
                    continue
                best = max(tiers, key=lambda t: t.get("skill_points", 0))
                skill, mx = best.get("skill_points", 0), best.get("max_skill_points", 0)
            out.append(Profession(name=name, skill=int(skill), max_skill=int(mx or 0)))
    return out


def parse_equipment(payload: dict) -> list[Item]:
    if "equipped_items" not in payload:
        raise BlizzardError(f"equipment response not recognised (keys: {sorted(payload)})")
    out: list[Item] = []
    for it in payload.get("equipped_items") or []:
        name = _name(it.get("name")) or _name(it.get("item"))
        if not name:
            continue
        item = it.get("item") or {}
        out.append(Item(
            slot=_name(it.get("slot")) or "Unknown",
            item_id=item.get("id") if isinstance(item, dict) else None,
            name=name,
            quality=_name(it.get("quality")),
        ))
    return out


class BlizzardClient:
    def __init__(self, client_id: str, client_secret: str, region: str = "us",
                 http: httpx.AsyncClient | None = None):
        self.client_id, self.client_secret, self.region = client_id, client_secret, region
        self.namespace = f"profile-forever-{region}"
        self.base = f"https://{region}.api.blizzard.com"
        self._http = http or httpx.AsyncClient(timeout=20)
        self._token: str | None = None
        self._token_expiry = 0.0

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = await self._http.post(TOKEN_URL, data={"grant_type": "client_credentials"},
                                  auth=(self.client_id, self.client_secret))
        if r.status_code != 200:
            raise BlizzardError(f"token request failed: HTTP {r.status_code}")
        body = r.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 3600))
        return self._token

    async def get(self, path: str) -> dict:
        """GET a profile-namespace path. Returns parsed JSON. Raises NotFound on 404."""
        for attempt in range(4):
            token = await self._ensure_token()
            r = await self._http.get(
                self.base + path,
                params={"namespace": self.namespace, "locale": "en_US"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                raise NotFound(path)
            if r.status_code == 401:
                self._token = None
            if r.status_code in (401, 429, 500, 502, 503, 504) and attempt < 3:
                await asyncio.sleep(2 ** attempt)
                continue
            raise BlizzardError(f"{path}: HTTP {r.status_code}")
        raise BlizzardError(f"{path}: gave up after retries")

    async def guild_roster(self, guild_slug: str) -> dict:
        return await self.get(f"/data/wow/guild/{guild_slug}/roster")

    async def character_profile(self, slug: str) -> dict:
        return await self.get(f"/profile/wow/character/{slug}")

    async def professions(self, slug: str) -> dict:
        return await self.get(f"/profile/wow/character/{slug}/professions")

    async def equipment(self, slug: str) -> dict:
        return await self.get(f"/profile/wow/character/{slug}/equipment")
