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
    recipes: tuple = ()          # ((recipe_id, recipe_name), ...) this character knows


@dataclass(frozen=True)
class Item:
    slot: str
    item_id: int | None
    name: str
    quality: str | None


@dataclass(frozen=True)
class CatalogItem:
    """An item from Blizzard's static data (what a recipe makes), not something a character wears."""
    item_id: int
    name: str
    quality: str | None
    level: int | None
    required_level: int | None
    item_class: str | None        # Weapon, Armor, Consumable, ...
    item_subclass: str | None     # Sword, Plate, Cloth, ...
    inventory_type: str | None    # One-Hand, Chest, Head, ...


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


def _known_recipes(entry: dict) -> list[tuple[int, str]]:
    """Recipes a character knows, from `known_recipes` on the entry or on any of its tiers."""
    out: list[tuple[int, str]] = []
    for holder in [entry, *(entry.get("tiers") or [])]:
        for r in holder.get("known_recipes") or []:
            if isinstance(r, dict) and r.get("id") is not None and r.get("name"):
                out.append((int(r["id"]), str(r["name"])))
    return out


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
            out.append(Profession(name=name, skill=int(skill), max_skill=int(mx or 0),
                                  recipes=tuple(r for r in _known_recipes(p) if r[1] != name)))   # not the profession's own entry
    best: dict[str, Profession] = {}                 # one row per profession: keep the highest skill
    for p in out:
        if p.name not in best or p.skill > best[p.name].skill:
            best[p.name] = p
    merged = {}                                      # ...but keep every recipe seen for it
    for p in out:
        merged.setdefault(p.name, {})
        merged[p.name].update(dict(p.recipes))
    return [Profession(p.name, p.skill, p.max_skill, tuple(sorted(merged[p.name].items())))
            for p in best.values()]


def parse_recipe_item(payload: dict) -> int | None:
    """The item a recipe makes, or None when it makes none (enchants and the like)."""
    if "id" not in payload or "name" not in payload:
        raise BlizzardError(f"recipe response not recognised (keys: {sorted(payload)})")
    ci = payload.get("crafted_item")
    return int(ci["id"]) if isinstance(ci, dict) and ci.get("id") is not None else None


def parse_catalog_item(payload: dict) -> CatalogItem:
    if "id" not in payload or "name" not in payload:
        raise BlizzardError(f"item response not recognised (keys: {sorted(payload)})")
    return CatalogItem(
        item_id=int(payload["id"]), name=_name(payload["name"]) or "?",
        quality=_name(payload.get("quality")), level=payload.get("level"),
        required_level=payload.get("required_level"),
        item_class=_name(payload.get("item_class")), item_subclass=_name(payload.get("item_subclass")),
        inventory_type=_name(payload.get("inventory_type")))


# ---- static data: every profession and every recipe it has, same for all players ----------------
def parse_profession_index(payload: dict) -> list[tuple[int, str]]:
    if "professions" not in payload:
        raise BlizzardError(f"profession index not recognised (keys: {sorted(payload)})")
    return [(int(p["id"]), p["name"]) for p in payload["professions"] if p.get("id") and p.get("name")]


def parse_profession_tiers(payload: dict) -> list[tuple[int, str]]:
    if "skill_tiers" not in payload:
        raise BlizzardError(f"profession response has no 'skill_tiers' (keys: {sorted(payload)})")
    return [(int(t["id"]), t["name"]) for t in payload["skill_tiers"] if t.get("id") and t.get("name")]


def parse_skill_tier(payload: dict) -> list[tuple[str, int, str]]:
    """(category, recipe_id, recipe_name) for every recipe in one skill tier."""
    if "categories" not in payload:
        raise BlizzardError(f"skill tier not recognised (keys: {sorted(payload)})")
    return [(c.get("name") or "Other", int(r["id"]), r["name"])
            for c in payload["categories"] for r in c.get("recipes") or []
            if r.get("id") is not None and r.get("name")]


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
        self.static_namespace = f"static-forever-{region}"   # same for every player; verified 2026-11-11
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

    async def get(self, path: str, namespace: str | None = None) -> dict:
        """GET a path (profile namespace unless told otherwise). Returns parsed JSON. Raises NotFound on 404."""
        for attempt in range(4):
            token = await self._ensure_token()
            r = await self._http.get(
                self.base + path,
                params={"namespace": namespace or self.namespace, "locale": "en_US"},
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

    async def profession_index(self) -> dict:
        return await self.get("/data/wow/profession/index", self.static_namespace)

    async def profession(self, profession_id: int) -> dict:
        return await self.get(f"/data/wow/profession/{profession_id}", self.static_namespace)

    async def skill_tier(self, profession_id: int, tier_id: int) -> dict:
        return await self.get(f"/data/wow/profession/{profession_id}/skill-tier/{tier_id}", self.static_namespace)

    async def recipe(self, recipe_id: int) -> dict:
        return await self.get(f"/data/wow/recipe/{recipe_id}", self.static_namespace)

    async def item(self, item_id: int) -> dict:
        return await self.get(f"/data/wow/item/{item_id}", self.static_namespace)
