import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from guildbot import blizzard as bz
from guildbot import raids as R
from guildbot.config import load
from guildbot.db import Database, utcnow
from guildbot.sync import sync_guild

ROSTER = {"members": [
    {"character": {"name": "Anduin", "surname": "Wrynn", "level": 60}, "rank": 0},
    {"character": {"name": "Judy", "surname": "Judgement", "slug": "judy-judgement", "level": 42}, "rank": 3},
    {"character": {}, "rank": 1},  # nameless entry is skipped
]}
PROFILE = {"level": 60, "character_class": {"name": "Paladin"}, "race": {"name": {"en_US": "Human"}},
           "faction": {"name": "Alliance"}}
PROFS = {"primaries": [{"profession": {"name": "Alchemy"}, "skill_points": 300, "max_skill_points": 300}],
         "secondaries": [{"profession": {"name": "Cooking"},
                          "tiers": [{"skill_points": 50, "max_skill_points": 75}]}]}
GEAR = {"equipped_items": [{"slot": {"name": "Head"}, "item": {"id": 1}, "name": "Lionheart Helm",
                            "quality": {"name": "Epic"}}]}


def test_parse_roster_and_slug():
    ms = bz.parse_roster(ROSTER)
    assert [m.slug for m in ms] == ["anduin-wrynn", "judy-judgement"]
    assert ms[1].rank == 3


def test_parse_roster_fails_loudly_on_shape_change():
    with pytest.raises(bz.BlizzardError):
        bz.parse_roster({"guild": {}})


def test_parse_profile_professions_equipment():
    p = bz.parse_profile(PROFILE)
    assert (p.class_name, p.race_name, p.faction) == ("Paladin", "Human", "Alliance")
    profs = {x.name: (x.skill, x.max_skill) for x in bz.parse_professions(PROFS)}
    assert profs == {"Alchemy": (300, 300), "Cooking": (50, 75)}
    assert bz.parse_equipment(GEAR)[0].name == "Lionheart Helm"


def test_parse_start_uses_guild_timezone():
    # EST (UTC-5) after DST ended Nov 1 2026
    assert R.parse_start("2026-11-15", "20:00", "America/New_York") == datetime(2026, 11, 16, 1, 0, tzinfo=timezone.utc)
    # EDT (UTC-4) in summer
    assert R.parse_start("2026-07-15", "20:00", "America/New_York") == datetime(2026, 7, 16, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        R.parse_start("15/11/2026", "8pm", "America/New_York")


class FakeClient:
    def __init__(self, roster, broken=()):
        self.roster, self.broken = roster, set(broken)

    async def guild_roster(self, slug):
        return self.roster

    async def character_profile(self, slug):
        if slug in self.broken:
            raise bz.BlizzardError("boom")
        return PROFILE

    async def professions(self, slug):
        if slug == "judy-judgement":
            raise bz.NotFound(slug)
        return PROFS

    async def equipment(self, slug):
        return GEAR


def make_db(tmp_path):
    return Database(tmp_path / "t.sqlite3")


def test_sync_populates_and_survives_failures(tmp_path):
    db = make_db(tmp_path)
    res = asyncio.run(sync_guild(db, FakeClient(ROSTER, broken={"judy-judgement"}), "g"))
    assert res.members == 2
    assert [f[:2] for f in res.failures] == [("judy-judgement", "profile")]
    row = db.find_character("anduin")
    assert row["class_name"] == "Paladin" and row["level"] == 60
    assert [r["name"] for r in db.who_has_profession("alch")] == ["Anduin"]
    assert db.search_items("lionheart")[0]["slot"] == "Head"
    # raw responses are kept
    n = db.conn.execute("SELECT COUNT(*) c FROM snapshots WHERE kind='roster'").fetchone()["c"]
    assert n == 1
    assert db.get_meta("last_sync_at")


def test_member_leaving_roster_is_flagged_not_deleted(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    one_left = {"members": [ROSTER["members"][0]]}
    res = asyncio.run(sync_guild(db, FakeClient(one_left), "g"))
    assert res.removed == 1
    assert db.find_character("judy") is None
    assert db.conn.execute("SELECT COUNT(*) c FROM characters").fetchone()["c"] == 2


def test_links_and_main(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    assert db.link(1, "anduin-wrynn") is True       # first link becomes main
    assert db.link(1, "judy-judgement") is False
    assert db.main_for(1)["name"] == "Anduin"
    assert db.set_main(1, "judy-judgement") and db.main_for(1)["name"] == "Judy"
    assert db.owner_of("anduin-wrynn") == 1
    db.unlink(1, "judy-judgement")                   # removing main promotes the other
    assert db.main_for(1)["name"] == "Anduin"
    db.release("anduin-wrynn")
    assert db.owner_of("anduin-wrynn") is None


def test_raid_signups_roles_and_reminders(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    now = datetime.now(timezone.utc)
    rid = db.create_raid("Hyjal", (now + timedelta(minutes=30)).isoformat(timespec="seconds"), 10, 99)
    db.upsert_signup(rid, 1, "anduin-wrynn", "tank", utcnow())
    db.upsert_signup(rid, 2, "judy-judgement", "dps", utcnow())
    db.upsert_signup(rid, 3, None, "absent", utcnow())
    db.upsert_signup(rid, 2, "judy-judgement", "healer", utcnow())   # changing role replaces
    g = R.group_signups(db.signups(rid))
    assert [len(g[r]) for r in R.ROLES] == [1, 1, 0, 0, 1]
    assert R.filled(g) == 2
    assert R.format_entry(g["tank"][0]) == "**Anduin** Paladin L60"
    assert R.format_entry(g["absent"][0]) == "<@3>"
    assert [r["id"] for r in db.due_reminders(now)] == [rid]
    db.mark_reminded(rid)
    assert db.due_reminders(now) == []
    far = db.create_raid("Later", (now + timedelta(days=2)).isoformat(timespec="seconds"), 10, 99)
    assert far not in [r["id"] for r in db.due_reminders(now)]
    db.cancel_raid(rid)
    assert [r["id"] for r in db.open_raids()] == [far]


def test_config_requires_core_settings():
    with pytest.raises(SystemExit):
        load({"DISCORD_TOKEN": "x"})
    c = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c",
              "GUILD_SLUG": " My-Guild "})
    assert c.guild_slug == "my-guild" and c.region == "us" and c.discord_guild_id is None


def test_bot_module_imports_and_registers_commands(tmp_path):
    from guildbot.bot import GuildBot
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    bot = GuildBot(cfg, make_db(tmp_path), blizzard=None)
    names = {c.name for c in bot.tree.get_commands()}
    assert names == {"link", "unlink", "main", "who", "roster", "professions", "whohas",
                     "raid-create", "raid-edit", "raid-cancel", "raids", "sync"}


def test_update_raid_changes_only_given_fields_and_rearms_reminder(tmp_path):
    db = make_db(tmp_path)
    now = datetime.now(timezone.utc)
    soon = (now + timedelta(minutes=30)).isoformat(timespec="seconds")
    rid = db.create_raid("Hyjal", soon, 10, 99)
    db.mark_reminded(rid)
    db.update_raid(rid, size=25)                       # size only: reminder stays done
    r = db.get_raid(rid)
    assert (r["title"], r["starts_at"], r["size"], r["reminded"]) == ("Hyjal", soon, 25, 1)
    later = (now + timedelta(days=1)).isoformat(timespec="seconds")
    db.update_raid(rid, title="Hyjal 2", starts_at_utc_iso=later)   # new time: reminder re-armed
    r = db.get_raid(rid)
    assert (r["title"], r["starts_at"], r["size"], r["reminded"]) == ("Hyjal 2", later, 25, 0)


def _s(did, role):
    return {"discord_id": did, "role": role}


def test_full_raid_sends_new_slot_signups_to_bench():
    g = R.group_signups([_s(1, "tank"), _s(2, "dps")])
    assert R.resolve_role("dps", g, 2, 3) == "bench"       # full, newcomer
    assert R.resolve_role("healer", g, 2, 2) == "healer"   # already in a slot: keeps it
    assert R.resolve_role("dps", g, 3, 3) == "dps"         # room left
    assert R.resolve_role("absent", g, 2, 3) == "absent"   # non-slot roles untouched
    assert R.resolve_role("bench", g, 2, 3) == "bench"


def test_started_raids_are_closed_once(tmp_path):
    db = make_db(tmp_path)
    now = datetime.now(timezone.utc)
    past = db.create_raid("Gone", (now - timedelta(minutes=1)).isoformat(timespec="seconds"), 10, 99)
    ahead = db.create_raid("Ahead", (now + timedelta(hours=1)).isoformat(timespec="seconds"), 10, 99)
    assert [r["id"] for r in db.close_started(now)] == [past]
    assert db.close_started(now) == []
    assert db.get_raid(past)["status"] == "closed"
    assert [r["id"] for r in db.open_raids()] == [ahead]


def test_sync_reports_denominator_including_not_found(tmp_path):
    class Missing(FakeClient):
        async def character_profile(self, slug):
            raise bz.NotFound(slug)
    db = make_db(tmp_path)
    res = asyncio.run(sync_guild(db, Missing(ROSTER), "g"))
    assert "profile: 0 of 2 loaded, 2 not found" in res.summary()
    assert res.failures == [] or all(k != "profile" for _, k, _ in res.failures)


def test_snapshots_keep_newest_two_per_character_and_kind(tmp_path):
    db = make_db(tmp_path)
    for i in range(4):
        db.save_snapshot("a-b", "profile", "ok", f"p{i}", utcnow())
        db.save_snapshot("a-b", "equipment", "ok", f"e{i}", utcnow())
        db.save_snapshot(None, "roster", "ok", f"r{i}", utcnow())
    assert db.prune_snapshots(keep=2) == 6
    rows = db.conn.execute("SELECT kind, payload FROM snapshots ORDER BY id").fetchall()
    assert sorted((r["kind"], r["payload"]) for r in rows) == [
        ("equipment", "e2"), ("equipment", "e3"), ("profile", "p2"), ("profile", "p3"),
        ("roster", "r2"), ("roster", "r3")]


def test_role_caps_set_per_raid_and_changeable(tmp_path):
    g = R.group_signups([_s(1, "tank"), _s(2, "tank"), _s(3, "healer")])
    caps = {"tank": 2, "healer": None, "dps": None}
    assert R.resolve_role("tank", g, 25, 9, caps) == "bench"      # newcomer, tanks full
    assert R.resolve_role("healer", g, 25, 9, caps) == "healer"   # no healer limit
    assert R.resolve_role("tank", g, 25, 3, caps) == "healer"     # holds a slot, tanks full: stays put
    assert R.resolve_role("tank", g, 25, 1, caps) == "tank"       # already a tank: not blocked by own seat
    assert R.resolve_role("tank", g, 25, 9, {"tank": 3}) == "tank"  # limit raised
    db = make_db(tmp_path)
    soon = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(timespec="seconds")
    rid = db.create_raid("Hyjal", soon, 25, 99, {"tank": 2, "healer": 5})
    assert R.caps_of(db.get_raid(rid)) == {"tank": 2, "healer": 5, "dps": None}
    db.update_raid(rid, caps={"tank": 3, "healer": 0})            # raise tanks, clear healers
    assert R.caps_of(db.get_raid(rid)) == {"tank": 3, "healer": None, "dps": None}
