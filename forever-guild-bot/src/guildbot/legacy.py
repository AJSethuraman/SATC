"""Legacy points: which challenges a member's account has finished, what is next, and which new
completions to announce. Pure logic, no Discord and no database.

What is known (docs/PROJECT.md, "Verified", 2026-11-12): each Legacy challenge is an achievement whose
reward reads "Earn 1 Legacy Point."; there are 65 (Classes 27, Tradeskills 18, Player vs. Player 12,
Dungeons 3, Raids 3, Adventure 2). Completions are shared across a Battle.net account and show on a
character only after it logs out. Which perks a character spent its points on is not in Blizzard's data.
"""
from __future__ import annotations

from datetime import datetime, timedelta

CATEGORIES = ("Classes", "Tradeskills", "Dungeons", "Raids", "Player vs. Player", "Adventure")
CLASS_MARKS = {"Novice": 25, "Experienced": 45, "Master": 60}            # "Level 25 Druid", from the criteria
TRADE_MARKS = {"Journeyman": 150, "Expert": 225, "Artisan": 300}         # "Reach 150 skill in Alchemy ..."
SPEND_CAP = 16                                                            # per character, Blizzard's article
ANNOUNCE_MAX_AGE_DAYS = 7


def mark(name: str) -> int | None:
    """The level or skill a class or tradeskill challenge asks for, from its first word."""
    first = name.split(" ", 1)[0]
    return CLASS_MARKS.get(first) or TRADE_MARKS.get(first)


def pick_earner(category: str, subcategory: str, name: str, holders: list[dict]) -> dict | None:
    """Of the guild characters showing one completion (all on one account), the one that earned it.
    A class point goes to a character of that class at the level; a tradeskill point to one with the skill.
    If none fits, a character outside the guild (or one not logged out yet) earned it: None, decide later.
    Anything else goes to the highest level holder (they are all the same player)."""
    need = mark(name)
    if category == "Classes":
        fit = [h for h in holders if h.get("class_name") == subcategory and (h.get("level") or 0) >= (need or 0)]
    elif category == "Tradeskills":
        fit = [h for h in holders if (h.get("skills") or {}).get(subcategory, 0) >= (need or 0)]
    else:
        fit = list(holders)
    if not fit:
        return None
    return sorted(fit, key=lambda h: (-(h.get("level") or 0), h["slug"]))[0]


def new_completions(completions, seen: set, known_before: set, holders: dict, now: datetime):
    """Which Legacy completions to announce.

    completions: rows with slug, challenge_id, name, category, subcategory, completed_at (ISO).
    seen: (challenge_id, completed_at) already handled. known_before: characters whose achievements were
    stored before this sync (a new member, or the first sync, announces nothing). holders: slug -> dict
    with slug, level, class_name, skills {profession: skill}.
    Returns (milestones to add as ('legacy', slug, name, challenge_id), keys to mark seen)."""
    groups: dict[tuple, list] = {}
    for r in completions:
        groups.setdefault((r["challenge_id"], r["completed_at"]), []).append(r)
    found, handled = [], []
    cutoff = now - timedelta(days=ANNOUNCE_MAX_AGE_DAYS)
    for key in sorted(groups, key=lambda k: (k[1], k[0])):
        if key in seen:
            continue
        rows = groups[key]
        first = rows[0]
        if not any(r["slug"] in known_before for r in rows) or datetime.fromisoformat(key[1]) < cutoff:
            handled.append(key)                       # old news, or nobody was known before: never announce
            continue
        earner = pick_earner(first["category"], first["subcategory"], first["name"],
                             [holders[r["slug"]] for r in rows if r["slug"] in holders])
        if earner is None:
            continue                                  # not seen yet: the right character may log out later
        handled.append(key)
        found.append(("legacy", earner["slug"], first["name"], first["challenge_id"]))
    return found, handled


def account_card(catalog, progress, characters, skills) -> dict:
    """What /legacy shows for one member.

    catalog: challenge rows (challenge_id, name, category, subcategory, description).
    progress: rows (slug, challenge_id, completed_at, steps_done, steps_total, amount) on their characters.
    characters: their claimed characters (slug, name, surname, level, class_name).
    skills: slug -> {profession: skill}.
    Returns {'earned': n, 'total': n, 'sections': [(title, [lines])]}."""
    by_id = {c["challenge_id"]: c for c in catalog}
    earned = {p["challenge_id"] for p in progress if p["completed_at"]}
    best: dict[int, tuple[int, int]] = {}
    for p in progress:
        if not p["completed_at"] and p["steps_total"] > 1 and p["steps_done"] > 0:   # real progress only
            cur = best.get(p["challenge_id"], (0, p["steps_total"]))
            if p["steps_done"] > cur[0]:
                cur = (p["steps_done"], p["steps_total"])
            best[p["challenge_id"]] = cur
    sections = []
    for cat in CATEGORIES:
        rows = [c for c in catalog if c["category"] == cat]
        if not rows:
            continue
        got = [c for c in rows if c["challenge_id"] in earned]
        lines = [f"✅ {c['name']}" for c in got]
        nxt = []
        if cat == "Classes":
            for ch in characters:
                todo = [c for c in rows if c["subcategory"] == ch["class_name"] and c["challenge_id"] not in earned]
                todo.sort(key=lambda c: mark(c["name"]) or 0)
                if todo:
                    nxt.append(f"Next: {todo[0]['name']} at level {mark(todo[0]['name'])} "
                               f"({_who(ch)} is {ch['level'] or '?'})")
        elif cat == "Tradeskills":
            for ch in characters:
                for prof, skill in sorted((skills.get(ch["slug"]) or {}).items()):
                    todo = [c for c in rows if c["subcategory"] == prof and c["challenge_id"] not in earned]
                    todo.sort(key=lambda c: mark(c["name"]) or 0)
                    if todo:
                        nxt.append(f"Next: {todo[0]['name']} at {mark(todo[0]['name'])} ({_who(ch)} has {skill})")
        elif cat == "Raids":
            nxt = [f"{c['name']}: {raid_place(c['description'])}" for c in rows if c["challenge_id"] not in earned]
        else:
            for c in rows:
                if c["challenge_id"] not in earned and c["challenge_id"] in best:
                    d, t = best[c["challenge_id"]]
                    nxt.append(f"Next: {c['name']}, {d} of {t} " + ("dungeons" if cat == "Dungeons" else "done"))
        sections.append((f"{cat}: {len(got)} of {len(rows)}", lines + nxt or ["Nothing yet."]))
    return {"earned": len(earned & set(by_id)), "total": len(by_id), "sections": sections}


def _who(ch) -> str:
    return " ".join(p for p in (ch["name"], ch["surname"]) if p)


# Points one character earns alone (levelling a class, raising a skill). Group content (dungeons, raids,
# PvP) is left out: a whole group finishes it in the same minute, and they are different players.
SOLO_CATEGORIES = ("Classes", "Tradeskills")


def likely_alts(completions, items: dict, owners: dict, rejected=frozenset()) -> list[dict]:
    """Groups of guild characters that are probably one player, worked out from three checks that must all agree:
      1. they share a solo Legacy point finished in the same minute (an account point shows on every character
         of the account with one time);
      2. they have the same account items (mounts and toys that come with the account), and both are known;
      3. nothing contradicts it: no Legacy point both hold at different times, and not claimed by two members.
    A group in which any two members fail 2 or 3 is dropped whole rather than split by guesswork.
    completions: rows with slug, challenge_id, name, category, completed_at. items: slug -> text or None.
    owners: slug -> Discord id. rejected: (member, slug) pairs where the member said "not mine". Returns [{"slugs": [...], "shared": [(name, completed_at), ...]}], sorted."""
    done: dict[str, dict[int, str]] = {}
    solo: dict[tuple[int, str], set[str]] = {}
    names: dict[int, str] = {}
    for r in completions:
        done.setdefault(r["slug"], {})[r["challenge_id"]] = r["completed_at"]
        names[r["challenge_id"]] = r["name"]
        if r["category"] in SOLO_CATEGORIES:
            solo.setdefault((r["challenge_id"], r["completed_at"]), set()).add(r["slug"])

    def compatible(a: str, b: str) -> bool:
        if items.get(a) is None or items.get(a) != items.get(b):
            return False
        if owners.get(a) and owners.get(b) and owners[a] != owners[b]:
            return False
        if (owners.get(a), b) in rejected or (owners.get(b), a) in rejected:
            return False
        da, db_ = done.get(a, {}), done.get(b, {})
        return all(da[c] == db_[c] for c in da.keys() & db_.keys())

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for slugs in solo.values():
        ordered = sorted(slugs)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                if compatible(a, b):
                    parent[find(a)] = find(b)
    groups: dict[str, list[str]] = {}
    for s in parent:
        groups.setdefault(find(s), []).append(s)
    out = []
    for members in groups.values():
        members.sort()
        if len(members) < 2:
            continue
        if not all(compatible(a, b) for i, a in enumerate(members) for b in members[i + 1:]):
            continue
        shared = sorted((names[c], t) for (c, t), slugs in solo.items() if len(slugs & set(members)) > 1)
        out.append({"slugs": members, "shared": shared})
    return sorted(out, key=lambda g: g["slugs"])


def players(claims: dict, groups: list[dict], with_data: set[str]) -> list[dict]:
    """Everyone on the board, one entry per player:
      {"owner": discord_id or None, "slugs": [...], "guessed": [slugs placed by the likely-alts guess]}.
    A claim decides. A likely-alts group joins the member who claimed one of its characters; a group nobody claimed
    is one entry (all of it guessed); any other character with Legacy data is its own entry.
    Characters without Legacy data (Blizzard returns nothing for them yet) only appear through a claim."""
    out, placed = [], set()
    by_owner = {}
    for did, slugs in claims.items():
        entry = {"owner": did, "slugs": list(slugs), "guessed": []}
        by_owner[did] = entry
        out.append(entry)
        placed.update(slugs)
    owner_of = {s: did for did, slugs in claims.items() for s in slugs}
    for g in groups:
        owners = {owner_of[s] for s in g["slugs"] if s in owner_of}
        extra = [s for s in g["slugs"] if s not in placed]
        if not extra or len(owners) > 1:
            continue
        if owners:
            entry = by_owner[owners.pop()]
            entry["slugs"] += extra
            entry["guessed"] += extra
        else:
            out.append({"owner": None, "slugs": extra, "guessed": extra if len(extra) > 1 else []})
        placed.update(extra)
    for s in sorted(with_data - placed):
        out.append({"owner": None, "slugs": [s], "guessed": []})
    return out


def raid_place(description: str | None) -> str:
    """'Defeat the following encounters in Hyjal Summit.' -> 'Hyjal Summit'; 'Defeat Onyxia.' -> 'Onyxia'."""
    d = (description or "").strip().rstrip(".")
    if " in " in d:
        return d.rsplit(" in ", 1)[1].removeprefix("the ")
    return d.removeprefix("Defeat ") or "?"
