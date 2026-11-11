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
    assert R.format_entry(g["tank"][0]) == "**Anduin Wrynn** Paladin L60"
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
                     "raid-create", "raid-edit", "raid-cancel", "raids", "guild-sync",
                     "claim-panel", "claim", "claims", "unlink-member", "release"}


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


def test_started_raids_stay_pending_until_marked_closed(tmp_path):
    db = make_db(tmp_path)
    now = datetime.now(timezone.utc)
    past = db.create_raid("Gone", (now - timedelta(minutes=1)).isoformat(timespec="seconds"), 10, 99)
    ahead = db.create_raid("Ahead", (now + timedelta(hours=1)).isoformat(timespec="seconds"), 10, 99)
    assert [r["id"] for r in db.started_open(now)] == [past]
    assert [r["id"] for r in db.started_open(now)] == [past]     # Discord failed: still pending, retried
    db.mark_closed(past)
    assert db.started_open(now) == []
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


def test_prune_keeps_last_successful_snapshot_when_newest_attempts_failed(tmp_path):
    db = make_db(tmp_path)
    db.save_snapshot("a-b", "profile", "ok", "good", utcnow())
    for _ in range(3):
        db.save_snapshot("a-b", "profile", "not_found", None, utcnow())
    db.prune_snapshots(keep=2)
    kept = [(r["status"], r["payload"]) for r in db.conn.execute("SELECT * FROM snapshots ORDER BY id")]
    assert ("ok", "good") in kept and len(kept) == 3


def test_unrecognised_payloads_raise_instead_of_wiping_cached_data(tmp_path):
    for fn in (bz.parse_profile, bz.parse_professions, bz.parse_equipment):
        with pytest.raises(bz.BlizzardError):
            fn({"renamed": {}})
    class Wrapped(FakeClient):
        async def character_profile(self, slug):
            return {"data": {"level": 1}}
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    before = db.find_character("anduin")["class_name"]
    res = asyncio.run(sync_guild(db, Wrapped(ROSTER), "g"))
    assert db.find_character("anduin")["class_name"] == before          # not cleared
    assert "profile: 0 of 2 loaded, 2 failed" in res.summary()


def test_data_as_of_uses_oldest_row_not_last_sync():
    from guildbot.bot import data_as_of
    rows = [{"fetched_at": "2026-11-10T10:00:00+00:00"}, {"fetched_at": "2026-11-09T08:00:00+00:00"}]
    assert "2026-11-09T08:00:00" in data_as_of(rows, "2026-11-10T12:00:00+00:00")
    assert "never" in data_as_of([], None)
    assert "2026-11-01" in data_as_of([{"profile_at": "2026-11-01T00:00:00+00:00"}, {"profile_at": None}],
                                      "2026-11-10", key="profile_at")


def test_unparsable_response_is_not_marked_ok_and_older_good_snapshot_survives(tmp_path):
    class Wrapped(FakeClient):
        async def character_profile(self, slug):
            return {"data": {"level": 1}}
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))                       # good profile saved
    for _ in range(3):
        asyncio.run(sync_guild(db, Wrapped(ROSTER), "g"))                      # malformed 200s
    rows = db.conn.execute(
        "SELECT status, payload FROM snapshots WHERE slug='anduin-wrynn' AND kind='profile'").fetchall()
    statuses = [r["status"] for r in rows]
    assert "ok" in statuses and "parse_error" in statuses
    assert any(r["status"] == "ok" and "Paladin" in r["payload"] for r in rows)   # source of cached data


def test_officer_release_promotes_an_alt_for_the_previous_owner(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    db.link(1, "anduin-wrynn")                 # main
    db.link(1, "judy-judgement")               # alt
    db.release("anduin-wrynn")                 # officer hands the main to someone else
    assert db.main_for(1)["name"] == "Judy"
    db.release("judy-judgement")               # last link gone: no main, and no error
    assert db.main_for(1) is None


def test_unposted_raid_can_be_removed(tmp_path):
    db = make_db(tmp_path)
    soon = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(timespec="seconds")
    rid = db.create_raid("Hyjal", soon, 10, 99)
    db.upsert_signup(rid, 5, None, "dps", utcnow())
    db.delete_raid(rid)
    assert db.get_raid(rid) is None and db.signups(rid) == [] and db.open_raids() == []


def test_signups_carry_profile_time_for_the_footer(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    soon = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(timespec="seconds")
    rid = db.create_raid("Hyjal", soon, 10, 99)
    db.upsert_signup(rid, 1, "anduin-wrynn", "tank", utcnow())
    assert db.signups(rid)[0]["profile_at"]


def test_who_footer_dates_each_part_separately():
    from guildbot.bot import who_footer
    char = {"profile_at": "2026-11-10T12:00:00+00:00"}
    profs = [{"fetched_at": "2026-11-09T08:00:00+00:00"}, {"fetched_at": "2026-11-10T12:00:00+00:00"}]
    out = who_footer(char, profs, [])
    assert "Profile 2026-11-10T12:00:00" in out
    assert "professions 2026-11-09T08:00:00" in out      # the older row, not the newer profile time
    assert "gear never" in out


def test_failed_profession_replacement_keeps_old_rows(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    before = [(r["profession"], r["skill"]) for r in db.professions_for("anduin-wrynn")]
    assert before
    dup = [bz.Profession("Alchemy", 1, 1), bz.Profession("Alchemy", 2, 2)]   # violates the primary key
    with pytest.raises(Exception):
        db.replace_professions("anduin-wrynn", dup, utcnow())
    db.save_snapshot("anduin-wrynn", "professions", "parse_error", "x", utcnow())   # commits the connection
    assert [(r["profession"], r["skill"]) for r in db.professions_for("anduin-wrynn")] == before


def test_profession_listed_twice_keeps_highest_skill():
    payload = {"primaries": [{"profession": {"name": "Alchemy"}, "skill_points": 100, "max_skill_points": 300}],
               "professions": [{"profession": {"name": "Alchemy"}, "skill_points": 250, "max_skill_points": 300}]}
    profs = bz.parse_professions(payload)
    assert [(p.name, p.skill) for p in profs] == [("Alchemy", 250)]


def test_raid_titles_are_limited_to_what_discord_accepts(tmp_path):
    from guildbot.bot import GuildBot
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    bot = GuildBot(cfg, make_db(tmp_path), blizzard=None)
    for name in ("raid-create", "raid-edit"):
        title = next(p for p in bot.tree.get_command(name).parameters if p.name == "title")
        assert (title.min_value, title.max_value) == (1, 100)


def test_roster_returns_every_matching_member(tmp_path):
    db = make_db(tmp_path)
    for i in range(250):
        db.upsert_member(f"p{i}-x", f"P{i}", "X", 60, 1, utcnow())
    assert len(db.roster()) == 250
    assert len(db.roster(limit=10)) == 10
    lines = [f"**P{i}**: L60 Paladin" for i in range(500)]
    from guildbot.bot import clip
    out = clip(lines, 4000)
    assert "more" in out and out.count("**P") < 500       # long lists are cut with an honest "and N more"


# ---- real Forever responses (saved 2026-11-11, character names replaced) ---------------------------
def _fx(name):
    from pathlib import Path
    return json.loads((Path(__file__).parent / "fixtures" / f"forever_{name}.json").read_text())


def test_real_forever_roster_carries_slug_surname_rank_and_faction_type():
    ms = bz.parse_roster(_fx("roster"))
    assert [(m.slug, m.name, m.surname, m.level, m.rank) for m in ms] == [
        ("testa-example", "Testa", "Example", 27, 2), ("testb-example", "Testb", "Example", 25, 3)]


def test_real_forever_profile_has_class_and_race_names():
    p = bz.parse_profile(_fx("profile"))
    assert (p.level, p.class_name, p.race_name, p.faction) == (25, "Paladin", "Undead", "Horde")


def test_real_forever_professions_read_skill_from_tiers():
    got = {x.name: (x.skill, x.max_skill) for x in bz.parse_professions(_fx("professions"))}
    assert got == {"Skinning": (161, 225), "Herbalism": (128, 150), "Cooking": (2, 75), "Fishing": (1, 75)}


def test_real_forever_rings_have_distinct_slot_names():
    items = bz.parse_equipment(_fx("equipment"))
    assert [i.slot for i in items] == ["Neck", "Ring 1", "Ring 2", "Main Hand"]
    assert items[0].name == "Roadwatcher's Confidence" and items[0].item_id == 281265


def test_commands_are_limited_to_the_configured_channels(tmp_path):
    from types import SimpleNamespace
    from guildbot.bot import GuildBot
    base = {"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"}
    assert load(base).channel_ids == frozenset()
    cfg = load({**base, "BOT_CHANNEL_IDS": "11, 22"})
    assert cfg.channel_ids == frozenset({11, 22})
    sent = []

    async def send_message(text, ephemeral):
        sent.append((text, ephemeral))
    def ix(channel_id):
        return SimpleNamespace(channel_id=channel_id, response=SimpleNamespace(send_message=send_message))
    bot = GuildBot(cfg, make_db(tmp_path), blizzard=None)
    assert asyncio.run(bot.tree.interaction_check(ix(11))) is True
    assert asyncio.run(bot.tree.interaction_check(ix(99))) is False
    assert sent == [("Use me in <#11> or <#22>.", True)]
    open_bot = GuildBot(load(base), make_db(tmp_path), blizzard=None)
    assert asyncio.run(open_bot.tree.interaction_check(ix(99))) is True


def test_claim_is_first_come_capped_and_officer_purge_frees_characters(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    a, b = "anduin-wrynn", "judy-judgement"
    assert len(db.unclaimed_characters()) == 2
    assert db.claim(1, [a]) == {"linked": [a], "taken": [], "over_cap": []}
    assert db.main_for(1)["slug"] == a
    assert db.claim(2, [a, b]) == {"linked": [b], "taken": [a], "over_cap": []}   # a troll cannot take a claimed one
    assert db.owner_of(a) == 1 and [r["slug"] for r in db.unclaimed_characters()] == []
    assert len(db.claims()) == 2
    assert db.unlink_all(2) == 1                                                   # officer purge
    assert [r["slug"] for r in db.unclaimed_characters()] == [b]
    db.MAX_CLAIMS = 1
    assert db.claim(3, [b]) == {"linked": [b], "taken": [], "over_cap": []}
    assert db.claim(3, ["nobody-here"]) == {"linked": [], "taken": [], "over_cap": []}


def test_full_names_alphabetical_and_searchable_unclaimed_list(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    assert R.full_name(db.find_character("anduin")) == "Anduin Wrynn"
    assert db.find_character("Judy Judgement")["slug"] == "judy-judgement"            # full name works too
    assert [R.full_name(r) for r in db.unclaimed_characters()] == ["Anduin Wrynn", "Judy Judgement"]
    assert [R.full_name(r) for r in db.unclaimed_characters("dgem")] == ["Judy Judgement"]   # search inside the name
    assert db.unclaimed_characters("zzz") == []
    assert [r["slug"] for r in db.search_characters("wrynn")] == ["anduin-wrynn"]
