"""Legacy points, last login, item level and /inactive. Fixtures are real Forever responses (2026-11-12),
trimmed and with names removed."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from guildbot import blizzard as bz
from guildbot import legacy as L
from guildbot import milestones as M
from guildbot.config import load
from guildbot.db import utcnow
from guildbot.sync import sync_guild, sync_legacy_catalog
from test_all import ROSTER, FakeClient, _fx, make_db

CFG = {"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"}


def test_real_forever_profile_has_last_login_and_item_level():
    p = bz.parse_profile(_fx("profile"))
    assert p.last_login_ms == 1794368805000 and p.item_level == 17


def test_real_forever_achievements_separate_finished_from_in_progress():
    got = {a.id: a for a in bz.parse_achievements(_fx("achievements"))}
    assert got[61502].name == "Novice Druid" and got[61502].completed_ms == 1794332040000
    assert got[62025].completed_ms is None and got[62025].amount == 178              # Expert Leatherworker, 178 of 225
    assert (got[62031].steps_done, got[62031].steps_total) == (3, 6)                 # Novice Spelunker: 3 of 6 dungeons
    with pytest.raises(bz.BlizzardError):
        bz.parse_achievements({"something": "else"})


def test_real_forever_achievement_static_shapes():
    roots = bz.parse_achievement_category_index(_fx("achievement_category_index"))
    assert [n for _, n in roots] == ["Classes", "Tradeskills", "Dungeons", "Raids", "Player vs. Player", "Adventure"]
    ach, subs = bz.parse_achievement_category(_fx("achievement_category"))
    assert ach == [] and len(subs) == 9 and (15577, "Druid") in subs
    ach, _ = bz.parse_achievement_category(_fx("achievement_subcategory"))
    assert [n for _, n in ach].count("Novice Druid") == 2                            # Blizzard lists each one twice
    assert bz.parse_achievement(_fx("achievement")).legacy_point is True
    assert bz.parse_achievement(_fx("achievement_explore")).legacy_point is False    # exploration steps give no point


TWINS = {61502: "Novice Druid", 61503: "Experienced Druid", 61504: "Master Druid",
         63972: "Novice Druid", 63973: "Experienced Druid", 63974: "Master Druid"}


class LegacyClient(FakeClient):
    """Static achievement data built from the real fixtures; per-character achievements set by the test."""
    def __init__(self, roster, ach=None):
        super().__init__(roster)
        self.ach = ach or {}

    async def achievements(self, slug):
        return {"achievements": self.ach.get(slug, [])}

    async def achievement_category_index(self):
        return _fx("achievement_category_index")

    async def achievement_category(self, cid):
        if cid == 15568:                                       # Classes: keep only the Druid subcategory
            d = _fx("achievement_category")
            d["subcategories"] = [s for s in d["subcategories"] if s["name"] == "Druid"]
            return d
        if cid == 15577:
            d = _fx("achievement_subcategory")
            d["achievements"].append({"id": 855, "name": "Explore Moonglade"})        # no reward: must be left out
            return d
        return {"id": cid, "achievements": [], "subcategories": []}

    async def achievement(self, aid):
        if aid == 855:
            return _fx("achievement_explore")
        d = _fx("achievement")
        d.update(id=aid, name=TWINS[aid])
        return d


def test_legacy_catalogue_keeps_point_achievements_and_merges_the_twin_ids(tmp_path):
    db = make_db(tmp_path)
    assert asyncio.run(sync_legacy_catalog(db, LegacyClient(ROSTER))) == 6            # 6 point achievements, exploring left out
    assert [(c["challenge_id"], c["name"], c["category"], c["subcategory"]) for c in db.legacy_catalog()] == [
        (61502, "Novice Druid", "Classes", "Druid"), (61503, "Experienced Druid", "Classes", "Druid"),
        (61504, "Master Druid", "Classes", "Druid")]
    assert asyncio.run(sync_legacy_catalog(db, LegacyClient(ROSTER))) == 0            # fresh: not fetched again for a week
    db.replace_achievements("anduin-wrynn", [bz.Achievement(63972, "Novice Druid", 1794332040000, 1, 1, None)], utcnow())
    assert [p["challenge_id"] for p in db.legacy_progress(["anduin-wrynn"])] == [61502]   # the twin counts as the same one


def _done(aid, name, when):
    return {"id": aid, "achievement": {"id": aid, "name": name}, "criteria": {"is_completed": True},
            "completed_timestamp": int(when.timestamp() * 1000)}


def test_a_legacy_point_is_announced_once_for_the_character_that_earned_it(tmp_path):
    db = make_db(tmp_path)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    db.replace_legacy_catalog([
        (61997, "Novice Paladin", "Classes", "Paladin", "Reach level 25 for the first time on a Paladin.", 1),
        (63978, "Novice Paladin", "Classes", "Paladin", "Reach level 25 for the first time on a Paladin.", 1),
        (61502, "Novice Druid", "Classes", "Druid", "Reach level 25 for the first time on a Druid.", 1),
        (684, "Conqueror of the Lair", "Raids", "Raids", "Defeat Onyxia.", 6),
        (62035, "Conqueror of the Deeps", "Raids", "Raids", "Defeat the following encounters in the Barrow Deeps.", 4)],
        utcnow())
    client = LegacyClient(ROSTER, {"anduin-wrynn": [_done(61997, "Novice Paladin", now - timedelta(days=30))]})
    asyncio.run(sync_guild(db, client, "g"))                    # first sync: what is already done is old news
    assert db.get_meta("legacy_seeded") and db.pending_milestones("2000-01-01") == []
    db.conn.execute("UPDATE characters SET class_name='Warrior' WHERE slug='judy-judgement'")
    db.conn.commit()
    lair = _done(684, "Conqueror of the Lair", now - timedelta(hours=1))
    druid_at = now - timedelta(hours=2)
    druid = _done(61502, "Novice Druid", druid_at)              # earned by a Druid that is not in the guild
    client.ach = {"anduin-wrynn": [lair, druid], "judy-judgement": [lair, druid]}   # one account: same time on both
    res = asyncio.run(sync_guild(db, client, "g"))
    assert res.milestones == [("legacy", "anduin-wrynn", "Conqueror of the Lair", 684)]   # once, not once per character
    assert (61502, druid_at.isoformat(timespec="seconds")) not in db.legacy_seen()        # no Druid here: left open
    assert asyncio.run(sync_guild(db, client, "g")).milestones == []                       # never twice
    deeps = _done(62035, "Conqueror of the Deeps", now - timedelta(minutes=30))   # shows on the lower-level alt first
    client.ach = {"anduin-wrynn": [lair, druid], "judy-judgement": [lair, druid, deeps]}
    first = asyncio.run(sync_guild(db, client, "g")).milestones
    client.ach["anduin-wrynn"].append(deeps)                                     # the main logs out later: same completion
    later = asyncio.run(sync_guild(db, client, "g")).milestones
    assert first == [("legacy", "judy-judgement", "Conqueror of the Deeps", 62035)]
    assert later == []                                                           # not again under another character
    stale = _done(61997, "Novice Paladin", now - timedelta(days=9))                        # another account, long ago
    client.ach["judy-judgement"] = [lair, druid, stale]
    db.conn.execute("UPDATE characters SET class_name='Paladin' WHERE slug='judy-judgement'")
    db.conn.commit()
    assert asyncio.run(sync_guild(db, client, "g")).milestones == []
    assert M.line("legacy", "Based Gaymer", "Hunter", "Novice Hunter", 61989) == \
        "**Based Gaymer** (Hunter) earned a Legacy point: Novice Hunter."


def test_pick_earner_needs_the_class_level_or_the_skill():
    war = {"slug": "w", "level": 30, "class_name": "Warrior", "skills": {"Leatherworking": 160}}
    pal = {"slug": "p", "level": 24, "class_name": "Paladin", "skills": {}}
    assert L.pick_earner("Classes", "Paladin", "Novice Paladin", [war, pal]) is None      # paladin not 25 yet: wait
    pal25 = dict(pal, level=25)
    assert L.pick_earner("Classes", "Paladin", "Novice Paladin", [war, pal25])["slug"] == "p"
    assert L.pick_earner("Tradeskills", "Leatherworking", "Journeyman Leatherworker", [pal25, war])["slug"] == "w"
    assert L.pick_earner("Tradeskills", "Leatherworking", "Expert Leatherworker", [pal25, war]) is None
    assert L.pick_earner("Raids", "Raids", "Conqueror of the Lair", [pal25, war])["slug"] == "w"   # highest level


def test_legacy_card_counts_points_and_says_what_is_next():
    cat = [{"challenge_id": i, "name": n, "category": c, "subcategory": s, "description": d} for i, n, c, s, d in [
        (1, "Novice Paladin", "Classes", "Paladin", ""), (2, "Experienced Paladin", "Classes", "Paladin", ""),
        (3, "Journeyman Leatherworker", "Tradeskills", "Leatherworking", ""),
        (4, "Expert Leatherworker", "Tradeskills", "Leatherworking", ""),
        (5, "Novice Spelunker", "Dungeons", "Dungeons", "Complete the following dungeons."),
        (6, "Conqueror of the Deeps", "Raids", "Raids", "Defeat the following encounters in the Barrow Deeps."),
        (7, "Conqueror of the Lair", "Raids", "Raids", "Defeat Onyxia."),
        (8, "Master of Warsong Gulch", "Player vs. Player", "Reputations", "")]]

    def p(slug, cid, at, done, total, amount=None):
        return {"slug": slug, "challenge_id": cid, "completed_at": at, "steps_done": done, "steps_total": total, "amount": amount}
    prog = [p("a", 1, "2026-11-10T00:00:00+00:00", 0, 0), p("a", 3, "2026-11-11T00:00:00+00:00", 1, 1, 178),
            p("a", 5, None, 3, 6), p("b", 5, None, 1, 6), p("a", 8, None, 0, 2)]
    chars = [{"slug": "a", "name": "Sauce", "surname": "Harvester", "level": 26, "class_name": "Paladin"}]
    card = L.account_card(cat, prog, chars, {"a": {"Leatherworking": 178}})
    assert card["earned"] == 2 and card["total"] == 8
    s = dict(card["sections"])
    assert s["Classes: 1 of 2"] == ["✅ Novice Paladin", "Next: Experienced Paladin at level 45 (Sauce Harvester is 26)"]
    assert s["Tradeskills: 1 of 2"][1] == "Next: Expert Leatherworker at 225 (Sauce Harvester has 178)"
    assert s["Dungeons: 0 of 1"] == ["Next: Novice Spelunker, 3 of 6 dungeons"]                # best of their characters
    assert s["Raids: 0 of 2"] == ["Conqueror of the Deeps: Barrow Deeps", "Conqueror of the Lair: Onyxia"]
    assert s["Player vs. Player: 0 of 1"] == ["Nothing yet."]                            # 0 of 2 is not progress


def _ix(uid, officer=False):
    sent = []

    async def send_message(text=None, embed=None, ephemeral=False, **kw):
        sent.append((text, embed, ephemeral))
    return SimpleNamespace(user=SimpleNamespace(id=uid, display_name="Me"), permissions=SimpleNamespace(manage_events=officer),
                           response=SimpleNamespace(send_message=send_message)), sent


def test_legacy_command_is_private_needs_a_claim_and_shows_the_card(tmp_path):
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, sent = _ix(42)
    cmd = bot.tree.get_command("legacy")
    asyncio.run(cmd.callback(ix))
    assert "haven't loaded" in sent[-1][0] and sent[-1][2] is True
    db.replace_legacy_catalog([(61997, "Novice Paladin", "Classes", "Paladin", "", 1)], utcnow())
    asyncio.run(cmd.callback(ix))
    assert "/link" in sent[-1][0] and sent[-1][2] is True
    db.claim(42, ["anduin-wrynn"])
    db.replace_achievements("anduin-wrynn", [bz.Achievement(61997, "Novice Paladin", 1794332040000, 0, 0, None)], utcnow())
    asyncio.run(cmd.callback(ix))
    e = sent[-1][1]
    assert sent[-1][2] is True and e.description.startswith("**1 of 1** points") and e.fields[0].name == "Classes: 1 of 1"
    asyncio.run(cmd.callback(ix, SimpleNamespace(id=7, display_name="Someone")))
    assert "Officers can see anyone's" in sent[-1][0]                                      # members see only their own


def test_legacy_board_and_inactive_are_private_lists_for_officers(tmp_path):
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    bot = GuildBot(load(CFG), db, blizzard=None)
    db.replace_legacy_catalog([(61997, "Novice Paladin", "Classes", "Paladin", "", 1),
                               (684, "Conqueror of the Lair", "Raids", "Raids", "Defeat Onyxia.", 6)], utcnow())
    db.claim(1, ["anduin-wrynn"])
    db.claim(2, ["judy-judgement"])
    db.replace_achievements("anduin-wrynn", [bz.Achievement(61997, "Novice Paladin", 1794332040000, 0, 0, None)], utcnow())
    ix, sent = _ix(1, officer=True)
    asyncio.run(bot.tree.get_command("legacy-board").callback(ix))
    e = sent[-1][1]
    assert sent[-1][2] is True and e.description.splitlines() == ["<@1>: 1 of 2", "<@2>: 0 of 2"]
    assert e.fields[0].name == "Conqueror of the Lair: Onyxia" and e.fields[0].value == "2 of 2 still need it"
    db.set_profile("judy-judgement", 42, "Priest", "Human", "Alliance", utcnow(),
                   last_login_at=(datetime.now(timezone.utc) - timedelta(days=20)).isoformat(timespec="seconds"))
    asyncio.run(bot.tree.get_command("inactive").callback(ix, 7))
    e = sent[-1][1]
    assert sent[-1][2] is True and e.title == "Not on for 7+ days"
    assert "**Judy Judgement**" in e.description and "<@2>" in e.description and "Anduin Wrynn" in e.description   # no login known


def test_last_login_and_item_level_are_kept_with_history_and_inactive_list(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    for at, login, ilvl in (("2026-11-01", "2026-10-01", 50), ("2026-11-02", "2026-10-01", 50), ("2026-11-03", "2026-11-02", 52)):
        db.set_profile("anduin-wrynn", 60, "Paladin", "Human", "Alliance", f"{at}T00:00:00+00:00",
                       last_login_at=f"{login}T00:00:00+00:00", item_level=ilvl)
    h = db.history_of("anduin-wrynn")
    assert [(r["item_level"], r["last_login_at"][:10]) for r in h if r["item_level"]] == [(50, "2026-10-01"), (52, "2026-11-02")]
    db.set_profile("judy-judgement", 42, "Priest", "Human", "Alliance", "2026-11-03T00:00:00+00:00",
                   last_login_at="2026-10-15T00:00:00+00:00")
    db.claim(5, ["judy-judgement"])
    assert [(r["slug"], r["owner"]) for r in db.inactive("2026-11-01T00:00:00+00:00")] == [("judy-judgement", 5)]
    db.conn.execute("UPDATE characters SET last_login_at=NULL WHERE slug='anduin-wrynn'")
    db.conn.commit()
    assert [r["slug"] for r in db.inactive("2026-11-01T00:00:00+00:00")] == ["judy-judgement", "anduin-wrynn"]   # unknown last
