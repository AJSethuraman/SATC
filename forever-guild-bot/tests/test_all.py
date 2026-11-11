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
    assert [len(g[r]) for r in R.ROLES] == [1, 1, 0, 0, 0, 1]
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
                     "claim-panel", "claims", "unlink-member", "release",
                     "recipes", "whocan", "craftable", "gaps", "wanted", "raid-end", "help", "commands"}


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


def test_wizard_helpers_days_times_sizes_and_caps():
    now = datetime(2026, 11, 11, 18, 30, tzinfo=timezone.utc)          # 1:30 PM New York
    days = R.day_options(now, "America/New_York")
    assert len(days) == 14 and days[0] == ("Today - Wed Nov 11", "2026-11-11")
    assert days[1][1] == "2026-11-12" and days[1][0].startswith("Tomorrow")
    p3 = R.day_options(now, "America/New_York", page=3)                  # any date is reachable by paging
    assert p3[0][1] == "2026-12-23" and len(p3) == 14 and p3[-1][1] == "2027-01-05" and "2027" in p3[-1][0]
    assert [v for _, v in R.day_options(now, "America/New_York", page=1)][0] == "2026-11-25"
    late = datetime(2026, 11, 12, 3, 0, tzinfo=timezone.utc)           # 10 PM on the 11th in New York
    assert R.day_options(late, "America/New_York")[0][1] == "2026-11-11"
    times = R.time_options()
    assert times[0] == ("12:00 PM", "12:00") and ("8:00 PM", "20:00") in times and times[-1] == ("11:30 PM", "23:30")
    assert len(times) <= 25 and all(len(l) <= 100 for l, _ in times)
    assert R.parse_cap("") is None and R.parse_cap(" 2 ") == 2
    for bad in ("0", "41", "x", "-1"):
        with pytest.raises(ValueError):
            R.parse_cap(bad)
    assert R.parse_start(days[1][1], "20:00", "America/New_York") == datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc)


def test_raid_wizard_and_details_modal_build(tmp_path):
    from guildbot.bot import GuildBot, RaidWizard, RaidDetails

    async def build():
        cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
        bot = GuildBot(cfg, make_db(tmp_path), blizzard=None)
        w = RaidWizard(bot)
        assert [type(c).__name__ for c in w.children] == ["Select", "Select", "Select", "Button", "Button"]
        assert all(len(c.options) <= 25 for c in w.children[:3])
        assert RaidDetails(bot, "2026-11-15", "20:00", 10).name.default == "Raid"
    asyncio.run(build())


def test_cancel_notice_is_a_short_private_message():
    raid = {"title": "Test Raid", "starts_at": "2026-11-11T20:05:00+00:00"}
    assert R.cancel_notice(raid, 9) == "**Test Raid** (<t:1794427500:F>) was cancelled by <@9>."


def test_size_follows_role_limits_when_all_three_are_set(tmp_path):
    assert R.size_from_limits(1, 1, 3) == 5 and R.size_from_limits(1, None, 3) is None
    db = make_db(tmp_path)
    rid = db.create_raid("t", "2030-01-01T00:00:00+00:00", 9, 1, {"tank": 2, "healer": 2, "dps": 6})
    assert db.get_raid(rid)["size"] == 10                                   # typed 9, limits say 10
    db.update_raid(rid, caps={"dps": 7})
    assert db.get_raid(rid)["size"] == 11                                   # raising a limit adds a spot
    db.update_raid(rid, caps={"healer": 0})                                 # a limit removed: typed size rules
    assert db.get_raid(rid)["size"] == 11
    partial = db.create_raid("p", "2030-01-01T00:00:00+00:00", 9, 1, {"tank": 2})
    assert db.get_raid(partial)["size"] == 9


def test_item_links_search_by_exact_name_and_show_only_the_name():
    from guildbot.links import item_link, item_url
    assert item_url("Roadwatcher's Confidence") == "https://www.wowhead.com/search?q=Roadwatcher%27s%20Confidence"
    assert item_link("Loop of Sacrifice") == "[Loop of Sacrifice](https://www.wowhead.com/search?q=Loop%20of%20Sacrifice)"
    assert item_link("Odd [Name] (x)").startswith("[Odd (Name) (x)](https://www.wowhead.com/search?q=Odd%20%5BName%5D%20%28x%29)")


def test_long_gear_lists_are_split_so_no_field_passes_discords_limit():
    from guildbot.bot import chunk_lines
    from guildbot.links import item_link
    lines = [f"Slot {i}: {item_link('A Fairly Long Item Name Number ' + str(i))}" for i in range(14)]
    chunks = chunk_lines(lines, 1000)
    assert sum(len(c) for c in chunks) == 14 and len(chunks) >= 2
    assert all(len("\n".join(c)) <= 1024 for c in chunks)
    assert chunk_lines([], 1000) == []


def test_signup_asks_for_a_character_only_when_there_are_several(tmp_path):
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    bot = GuildBot(cfg, db, blizzard=None)
    rid = db.create_raid("t", "2030-01-01T00:00:00+00:00", 5, 1)
    raid = db.get_raid(rid)
    db.claim(7, ["anduin-wrynn", "judy-judgement"])
    db.set_main(7, "judy-judgement")
    assert bot.apply_signup(raid, 7, "dps", "anduin-wrynn") == "dps"
    row = [s for s in db.signups(rid) if s["discord_id"] == 7][0]
    assert (row["slug"], row["role"]) == ("anduin-wrynn", "dps")            # the chosen character, not the main
    assert bot.apply_signup(raid, 7, "healer", "anduin-wrynn") == "healer"  # role change keeps the character


def test_reminder_is_a_short_private_message():
    raid = {"title": "Test Raid", "starts_at": "2026-11-11T20:05:00+00:00"}
    assert R.reminder_text(raid) == "Reminder: **Test Raid** starts <t:1794427500:R> (<t:1794427500:t>)."


def test_tapping_a_role_with_several_characters_opens_the_picker(tmp_path):
    from types import SimpleNamespace
    from guildbot.bot import GuildBot, SignupModal
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("t", "2030-01-01T00:00:00+00:00", 5, 1)

    async def tap(user_id, role, bot):
        calls = []

        async def send_message(text=None, **kw):
            calls.append(("send", text, kw))

        async def send_modal(modal):
            calls.append(("modal", None, {"modal": modal}))

        async def edit_message(**kw):
            calls.append(("edit", None, kw))
        ix = SimpleNamespace(user=SimpleNamespace(id=user_id),
                             response=SimpleNamespace(send_message=send_message, edit_message=edit_message, send_modal=send_modal),
                             followup=SimpleNamespace(send=send_message))
        await bot.handle_signup(ix, rid, role)
        return calls

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        db.claim(7, ["anduin-wrynn", "judy-judgement"])
        for role in ("dps", "healer", "dps"):                       # first tap, a different role, the same role
            calls = await tap(7, role, bot)
            assert calls[0][0] == "modal" and isinstance(calls[0][2]["modal"], SignupModal), role
            options = calls[0][2]["modal"].choice.options
            assert [o.value for o in options] == ["anduin-wrynn", "judy-judgement"] and sum(o.default for o in options) == 1
        assert db.signups(rid) == []                                  # nothing is recorded until they pick
        db.claim(8, ["x"])                                            # unknown slug: no links
        db.conn.execute("DELETE FROM links WHERE discord_id=7 AND slug='judy-judgement'")
        calls = await tap(7, "dps", bot)                              # one character: no question
        assert calls[0][0] == "edit"
    asyncio.run(run())


def test_item_and_profession_typeahead_lists_names_with_counts(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    for slug in ("anduin-wrynn", "judy-judgement"):
        db.replace_equipment(slug, [bz.Item("Head", 1, "Lionheart Helm", "Epic"),
                                    bz.Item("Neck", 2, "Lionheart Amulet" if slug == "anduin-wrynn" else "Plain Charm", None)],
                             utcnow())
        db.replace_professions(slug, [bz.Profession("Alchemy", 300, 300)], utcnow())
    assert [(r["name"], r["n"]) for r in db.item_names("lion")] == [("Lionheart Helm", 2), ("Lionheart Amulet", 1)]
    assert [r["name"] for r in db.item_names("CHARM")] == ["Plain Charm"]                 # any part, any case
    assert len(db.item_names("")) == 3 and db.item_names("zzz") == []
    assert [(r["name"], r["n"]) for r in db.profession_names("alch")] == [("Alchemy", 2)]


def test_real_forever_professions_carry_known_recipes():
    profs = {p.name: p for p in bz.parse_professions(_fx("professions"))}
    skinning = profs["Skinning"]
    assert (skinning.skill, skinning.max_skill) == (161, 225)
    assert skinning.recipes == ((52644, "Camp Chair"),)          # the profession's own "Skinning" entry is dropped


def test_real_forever_static_profession_and_recipe_shapes():
    assert bz.parse_profession_index(_fx("profession_index")) == [(186, "Mining"), (393, "Skinning")] or \
        sorted(bz.parse_profession_index(_fx("profession_index"))) == [(186, "Mining"), (393, "Skinning")]
    assert bz.parse_profession_tiers(_fx("profession")) == [(2947, "Skinning")]
    got = bz.parse_skill_tier(_fx("skill_tier"))
    assert got == [("Camping", 52644, "Camp Chair"), ("Camping", 57017, "Field Guide"), ("Camping", 57029, "Trapper's Workbench")]
    for fn in (bz.parse_profession_index, bz.parse_profession_tiers, bz.parse_skill_tier):
        with pytest.raises(bz.BlizzardError):
            fn({"renamed": 1})


class RecipeClient(FakeClient):
    def __init__(self, roster):
        super().__init__(roster)
        self.calls = 0

    async def profession_index(self):
        self.calls += 1
        return _fx("profession_index")

    async def profession(self, pid):
        return _fx("profession")

    async def skill_tier(self, pid, tid):
        return _fx("skill_tier")


def test_recipe_catalogue_and_who_can_craft(tmp_path):
    from guildbot.sync import sync_recipe_catalog
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225, ((52644, "Camp Chair"),))], utcnow())
    client = RecipeClient(ROSTER)
    assert asyncio.run(sync_recipe_catalog(db, client)) == 6          # 2 professions x 3 recipes in the fixtures
    assert asyncio.run(sync_recipe_catalog(db, client)) == 0          # fresh copy: not fetched again
    assert client.calls == 1
    assert [r["name"] for r in db.catalog_professions("skin")] == ["Skinning"]
    rows = db.recipes_for("Skinning")
    assert [(r["name"], r["knowers"]) for r in rows] == [("Camp Chair", "Anduin Wrynn"), ("Field Guide", None),
                                                          ("Trapper's Workbench", None)]
    assert [r["name"] for r in db.recipes_for("skinning", "FIELD")] == ["Field Guide"]
    assert [(r["name"], r["n"]) for r in db.recipe_names("camp")] == [("Camp Chair", 1)]
    who = db.who_can_craft("camp chair")
    assert [(R.full_name(r), r["skill"]) for r in who] == [("Anduin Wrynn", 200)]
    assert db.who_can_craft("Nothing") == []
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225)], utcnow())   # a re-sync with none
    assert db.who_can_craft("camp chair") == []


def test_real_forever_recipe_and_item_shapes():
    assert bz.parse_recipe_item(_fx("recipe")) == 2847
    it = bz.parse_catalog_item(_fx("item"))
    assert (it.item_id, it.name, it.quality, it.required_level) == (2847, "Copper Shortsword", "Uncommon", 4)
    assert (it.item_class, it.item_subclass, it.inventory_type) == ("Weapon", "Sword", "One-Hand")
    assert bz.parse_recipe_item({"id": 1, "name": "Enchant Thing"}) is None          # makes no item
    for fn in (bz.parse_recipe_item, bz.parse_catalog_item):
        with pytest.raises(bz.BlizzardError):
            fn({"renamed": 1})


class ItemClient(RecipeClient):
    async def recipe(self, rid):
        r = dict(_fx("recipe")); r["id"] = rid
        if rid == 57017:
            r.pop("crafted_item")                                                       # a recipe that makes nothing
        return r

    async def item(self, iid):
        return _fx("item")


def test_craftable_finds_items_by_kind_and_level_with_who_can_make_them(tmp_path):
    from guildbot.sync import sync_item_catalog, sync_recipe_catalog
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    client = ItemClient(ROSTER)
    asyncio.run(sync_recipe_catalog(db, client))
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225, ((52644, "Camp Chair"),))], utcnow())
    assert asyncio.run(sync_item_catalog(db, client)) == (3, 1)          # 3 distinct recipe ids, 1 distinct item
    assert asyncio.run(sync_item_catalog(db, client)) == (0, 0)          # nothing left to look up
    assert [r["name"] for r in db.item_facets("item_class")] == ["Weapon"]
    assert [r["name"] for r in db.item_facets("item_subclass", "sw")] == ["Sword"]
    rows = db.craftable("Weapon", "Sword", "One-Hand", 1, 10, only_known=True)
    assert [(r["name"], r["profession"], r["knowers"]) for r in rows] == [("Copper Shortsword", "Skinning", "Anduin Wrynn")]
    assert db.craftable("Armor") == [] and db.craftable("Weapon", min_level=5) == []
    assert db.craftable("Weapon", profession="Mining") == []                 # nobody known for Mining
    assert len(db.craftable("Weapon", only_known=False)) >= 2               # everything that exists
    # the recipe list refresh keeps what was already looked up
    asyncio.run(sync_recipe_catalog(db, client, force=True))
    assert db.recipes_needing_item() == []
    assert len(db.craftable("Weapon", min_level=1, only_known=False)) >= 2


def test_level_bands_cover_zero_to_top_without_gaps():
    from guildbot import craft as C
    bands = C.level_bands(60)
    assert bands[0] == ("Level 1-10", "0-10") and bands[1] == ("Level 11-20", "11-20") and bands[-1] == ("Level 51-60", "51-60")
    edges = [C.parse_band(v) for _, v in bands]
    assert edges[0][0] == 0 and edges[-1][1] == 60
    assert all(edges[i][1] + 1 == edges[i + 1][0] for i in range(len(edges) - 1))      # no gaps, no overlaps
    assert C.parse_band("*") == (None, None) and C.parse_band(None) == (None, None) and C.parse_band("20-29") == (20, 29)


def test_craft_wizard_dropdowns_follow_the_choices(tmp_path):
    from guildbot.bot import CraftWizard, craftable_result
    from guildbot.sync import sync_item_catalog, sync_recipe_catalog
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    client = ItemClient(ROSTER)
    asyncio.run(sync_recipe_catalog(db, client))
    asyncio.run(sync_item_catalog(db, client))
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225, ((52644, "Camp Chair"),))], utcnow())

    async def build():
        bot = SimpleNamespaceBot(db)
        w = CraftWizard(bot)
        selects = [c for c in w.children if type(c).__name__ == "Select"]
        assert [o.label for o in selects[0].options] == ["Any", "Any weapon", "Weapon: Sword"]
        assert [o.label for o in selects[1].options] == ["Any", "One-Hand"]
        assert len(selects[2].options) == 7 and [o.label for o in selects[3].options] == ["Any", "Strength"]
        assert len(w.children) == 7                                                  # 4 dropdowns + 3 buttons
        on = [c for c in w.children if type(c).__name__ == "Button"]
        assert on[1].label == "Gaps: shown"                                          # gaps are on by default
        off = [c for c in CraftWizard(bot, show_all=False).children if type(c).__name__ == "Button"]
        assert off[1].label == "Gaps: hidden" and off[1].style != on[1].style
        picked = [c for c in CraftWizard(bot, kind="Weapon", sub="Sword", stat="STRENGTH").children if type(c).__name__ == "Select"]
        assert [o.value for o in picked[0].options if o.default] == ["Weapon|Sword"]
        assert [o.value for o in picked[3].options if o.default] == ["STRENGTH"]
    asyncio.run(build())
    embed, msg = craftable_result(db, "Weapon", "Sword", "One-Hand", 0, 10, None, False)
    assert msg is None and "Copper Shortsword" in embed.description and "Anduin Wrynn" in embed.description
    embed, msg = craftable_result(db, "Weapon", None, None, None, None, None, True, "STRENGTH")
    text = embed.description
    assert text.index("The guild can make (1)") < text.index("Gaps (") < len(text)                   # what we have comes first
    assert "*[Copper Shortsword](" in text and "**Mining**" in text and "nobody in the guild can make these" in text
    assert "**Skinning**, Anduin Wrynn" in text and "stat: Strength" in text
    only, _ = craftable_result(db, "Weapon", None, None, None, None, None, False, "STRENGTH")
    assert "Gaps" not in only.description and "The guild can make (1)" in only.description
    embed, msg = craftable_result(db, "Weapon", None, None, None, None, None, True, "INTELLECT")
    assert embed is None
    embed, msg = craftable_result(db, "Armor", None, None, None, None, None, False)
    assert embed is None and "Nothing matches" in msg


def test_item_stats_are_read_stored_and_filterable(tmp_path):
    it = bz.parse_catalog_item(_fx("item"))
    assert it.stats == (("STRENGTH", "Strength", 1),)
    assert bz.parse_catalog_item({"id": 1, "name": "Plain"}).stats == ()                  # no stats block: none
    db = make_db(tmp_path)
    db.save_item(it)
    db.save_item(bz.CatalogItem(2, "Silk Cap", "Uncommon", 20, 15, "Armor", "Cloth", "Head",
                                (("INTELLECT", "Intellect", 9), ("BONUS_STAT_FROST_DAMAGE_DONE", "Frost Damage", 7))))
    assert [(r["code"], r["name"], r["n"]) for r in db.stat_facets()] == [
        ("BONUS_STAT_FROST_DAMAGE_DONE", "Frost Damage", 1), ("INTELLECT", "Intellect", 1), ("STRENGTH", "Strength", 1)]
    assert [r["name"] for r in db.stat_facets("intel")] == ["Intellect"]
    from guildbot import craft as C
    assert C.what_options(db.kind_pairs() and [(r["item_class"], r["item_subclass"], r["n"]) for r in db.kind_pairs()]) == [
        ("Any armor", "Armor|*"), ("Armor: Cloth", "Armor|Cloth"), ("Any weapon", "Weapon|*"), ("Weapon: Sword", "Weapon|Sword")]
    assert C.parse_what("Armor|Cloth") == ("Armor", "Cloth") and C.parse_what("Armor|*") == ("Armor", None)
    assert C.parse_what("*") == (None, None) and C.what_value("Armor", None) == "Armor|*" and C.what_value(None, None) == "*"
    db.conn.execute("INSERT INTO recipes (profession, recipe_id, name, category, fetched_at, item_id) VALUES ('P',1,'a','c','x',2)")
    db.conn.execute("INSERT INTO recipes (profession, recipe_id, name, category, fetched_at, item_id) VALUES ('P',2,'b','c','x',9)")
    db.conn.commit()
    assert [r["item_id"] for r in db.items_needed()] == [9]                               # 2 is done; 9 has no row
    db.conn.execute("UPDATE items SET stats_loaded=0 WHERE item_id=2")                    # an item fetched before stats
    assert [r["item_id"] for r in db.items_needed()] == [2, 9]
    assert [r["name"] for r in db.craftable(stat="INTELLECT", only_known=False)] == ["Silk Cap"]
    assert db.craftable(stat="AGILITY", only_known=False) == []


class SimpleNamespaceBot:
    def __init__(self, db):
        self.db = db


def test_profession_gaps_coverage_and_missing_recipes(tmp_path):
    from guildbot.bot import GapsView, gaps_for, gaps_overview
    from guildbot.sync import sync_item_catalog, sync_recipe_catalog
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    client = ItemClient(ROSTER)
    asyncio.run(sync_recipe_catalog(db, client))
    asyncio.run(sync_item_catalog(db, client))
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225, ((52644, "Camp Chair"),))], utcnow())
    cov = {r["name"]: (r["total"], r["members"], r["best"], r["known"]) for r in db.profession_coverage()}
    assert cov == {"Skinning": (3, 1, 200, 1), "Mining": (3, 0, None, 0)}            # nobody has Mining
    assert [r["name"] for r in db.missing_recipes("Skinning")] == ["Field Guide", "Trapper's Workbench"] or \
        {r["name"] for r in db.missing_recipes("Skinning")} == {"Field Guide", "Trapper's Workbench"}
    assert len(db.missing_recipes("Mining")) == 3
    assert [(b["skill"]) for b in db.best_in_profession("Skinning")] == [200] and db.best_in_profession("Mining") == []
    assert "Nobody has:** Mining" in gaps_overview(db).description
    assert "Anduin Wrynn 200/225" in gaps_for(db, "Skinning").description
    assert "nobody in the guild has this profession" in gaps_for(db, "Mining").description

    async def build():
        v = GapsView(SimpleNamespaceBot(db), "Skinning")
        assert [type(c).__name__ for c in v.children] == ["Select", "Button"]
        assert [o.label for o in v.children[0].options] == ["Mining", "Skinning"]
    asyncio.run(build())


def test_a_search_for_something_nobody_can_make_becomes_a_recorded_gap(tmp_path):
    from guildbot.bot import gap_card
    from guildbot.sync import sync_item_catalog, sync_recipe_catalog
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    client = ItemClient(ROSTER)
    asyncio.run(sync_recipe_catalog(db, client))
    asyncio.run(sync_item_catalog(db, client))
    db.replace_professions("anduin-wrynn", [bz.Profession("Skinning", 200, 225, ((52644, "Camp Chair"),))], utcnow())
    names = {(r["name"], r["profession"]): r["n"] for r in db.recipe_names_all("")}
    assert names[("Camp Chair", "Skinning")] == 1 and names[("Field Guide", "Skinning")] == 0   # known first, then unknown
    assert db.who_can_craft("Field Guide") == []
    card = gap_card(db, "Field Guide", 99)
    assert card.title == "Gap: nobody in the guild can make Field Guide"
    assert "Anduin Wrynn 200/225" in card.description and "wowhead.com/search?q=Field%20Guide" in card.fields[0].value
    assert gap_card(db, "No Such Recipe", 99) is None                                           # not a real recipe: no gap
    gap_card(db, "Field Guide", 100)
    gap_card(db, "Trapper's Workbench", 99)
    top = {(r["name"], r["profession"]): (r["n"], r["people"]) for r in db.wanted_top()}
    # the fixtures give the same three recipes to both professions, so each search is recorded once per profession
    assert top == {("Field Guide", "Skinning"): (2, 2), ("Field Guide", "Mining"): (2, 2),
                   ("Trapper's Workbench", "Skinning"): (1, 1), ("Trapper's Workbench", "Mining"): (1, 1)}


def test_roster_summary_and_end_of_raid_bookkeeping(tmp_path):
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    rid = db.create_raid("Test Raid", "2026-11-11T20:30:00+00:00", 5, 9)
    db.upsert_signup(rid, 1, "anduin-wrynn", "tank", utcnow())
    db.upsert_signup(rid, 2, None, "bench", utcnow())
    db.upsert_signup(rid, 3, None, "absent", utcnow())
    text = R.roster_summary(db.get_raid(rid), db.signups(rid))
    assert text.splitlines()[0] == "**Test Raid** (<t:1794429000:F>) roster:"
    assert "**Tanks (1):** **Anduin Wrynn** Paladin L60" in text and "**Bench (1):** <@2>" in text
    assert "**Healers (0):** -" in text and "**Can't make it (1):** <@3>" in text
    db.mark_closed(rid)
    start = datetime(2026, 11, 11, 20, 30, tzinfo=timezone.utc)
    assert db.closed_ended_before(start + timedelta(hours=2, minutes=59), 3) == []
    assert [r["id"] for r in db.closed_ended_before(start + timedelta(hours=3), 3)] == [rid]
    db.set_raid_posted(rid, 10, 20, 30)
    assert db.raid_by_message(20)["id"] == rid and db.raid_by_event(30)["id"] == rid and db.raid_by_message(99) is None
    db.mark_ended(rid)
    assert db.closed_ended_before(start + timedelta(days=1), 3) == [] and db.get_raid(rid)["status"] == "ended"


class _Msg:
    pinned = True

    def __init__(self):
        self.deleted, self.edits, self.unpinned = 0, [], 0

    async def delete(self):
        self.deleted += 1

    async def edit(self, **kw):
        self.edits.append(kw)

    async def unpin(self):
        self.unpinned += 1


class _Chan:
    def __init__(self, msg):
        self.msg = msg

    async def fetch_message(self, mid):
        return self.msg


class _User:
    bot = False

    def __init__(self, log):
        self.log = log

    async def send(self, text):
        self.log.append(text)


def test_finish_raid_keeps_the_post_as_a_completed_record_unpins_it_and_dms_the_roster(tmp_path):
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Test Raid", "2026-11-11T20:30:00+00:00", 5, 9)
    db.set_raid_posted(rid, 10, 20, None)
    db.upsert_signup(rid, 1, "anduin-wrynn", "dps", utcnow())
    msg, sent = _Msg(), []

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        bot.get_channel = lambda cid: _Chan(msg)
        bot.get_user = lambda uid: _User(sent)
        assert await bot.finish_raid(rid, remove_event=False, dm_ids=[9, 9, 8], note="Done.") is True
        assert await bot.finish_raid(rid, remove_event=False, dm_ids=[9]) is False        # already ended: nothing repeats
        raid = db.get_raid(rid)
        await bot._handled_by_hand(raid, "signup post")                                     # ended raids are left alone
        assert 9 not in bot._busy
    asyncio.run(run())
    assert msg.deleted == 0 and msg.unpinned == 1 and db.get_raid(rid)["status"] == "ended"      # the post stays
    assert len(msg.edits) == 1 and msg.edits[0]["view"] is None
    assert msg.edits[0]["embed"].title == "COMPLETED: Test Raid  (#1)"
    assert len(sent) == 2 and sent[0].startswith("Done.\n**Test Raid**") and "DPS (1)" in sent[0]   # users 9 and 8, once each


def test_ending_the_event_by_hand_ends_a_started_raid_and_tells_the_organizer(tmp_path):
    import discord
    from types import SimpleNamespace
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Test Raid", "2026-11-11T20:30:00+00:00", 5, 9)
    db.set_raid_posted(rid, 10, 20, 30)
    db.upsert_signup(rid, 1, "anduin-wrynn", "dps", utcnow())
    db.mark_closed(rid)                                                    # already started
    msg, sent = _Msg(), []

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        bot.get_channel = lambda cid: _Chan(msg)
        bot.get_user = lambda uid: _User(sent)
        running = SimpleNamespace(id=30, status=discord.EventStatus.active)
        await bot.on_scheduled_event_update(None, running)                # still running: nothing happens
        assert db.get_raid(rid)["status"] == "closed"
        await bot.on_scheduled_event_update(None, SimpleNamespace(id=30, status=discord.EventStatus.completed))
        await bot.on_scheduled_event_update(None, SimpleNamespace(id=30, status=discord.EventStatus.completed))  # twice is fine
    asyncio.run(run())
    assert db.get_raid(rid)["status"] == "ended" and msg.unpinned == 1 and len(msg.edits) == 1
    assert len(sent) == 1 and "removed by hand" in sent[0] and "DPS (1)" in sent[0]


def _row(uid, role, at, wanted=None):
    return {"discord_id": uid, "role": role, "updated_at": at, "wanted": wanted,
            "name": None, "surname": None, "level": None, "class_name": None}


def test_next_offers_follows_the_queue_and_respects_limits_and_pending_offers():
    raid = {"size": 3, "cap_tank": None, "cap_healer": None, "cap_dps": 2}
    full = [_row(1, "tank", "1"), _row(2, "dps", "2"), _row(3, "dps", "3"),
            _row(4, "bench", "4", "dps"), _row(5, "bench", "5", "healer"), _row(6, "bench", "6")]
    assert R.next_offers(raid, full, []) == []                                   # raid is full: nobody is asked
    open_one = [r for r in full if r["discord_id"] != 3]                         # a DPS left: one slot
    assert R.next_offers(raid, open_one, []) == [(4, "dps")]                     # first in line, and DPS has room
    assert R.next_offers(dict(raid, cap_dps=1), open_one, []) == [(5, "healer")]  # DPS capped: skip to someone else
    pend = [{"discord_id": 4, "role": "dps", "state": "pending"}]
    assert R.next_offers(raid, open_one, pend) == []                             # the slot is already promised
    gone = [{"discord_id": 4, "role": "dps", "state": "declined"}]
    assert R.next_offers(raid, open_one, gone) == [(5, "healer")]                # 4 said no; 5 is next
    assert R.next_offers(raid, open_one, gone + [{"discord_id": 5, "role": "healer", "state": "declined"}]) == [(6, "tank")]                  # 6 tapped plain Bench: any role will do
    bigger = dict(raid, size=4)
    assert R.next_offers(bigger, full, []) == [(5, "healer")]                    # room added: first eligible in line
    two = dict(raid, size=5)
    assert R.next_offers(two, full, []) == [(5, "healer"), (6, "tank")]          # 6 (any role) gets the next open role
    when = datetime(2026, 11, 11, 20, 45, tzinfo=timezone.utc)
    text = R.offer_text(raid | {"title": "T", "starts_at": "2026-11-11T20:30:00+00:00"}, "dps", when)
    assert "Take it or pass." in text and "remind you once more, then take you off the bench" in text
    last = R.ping_text({"title": "T"}, "dps", 7, when, last_call=True)
    assert last == f"<@7> still want the **DPS** spot in **T**? Answer <t:{int(when.timestamp())}:R> or you come off the bench."
    assert "still want" not in R.ping_text({"title": "T"}, "dps", 7, when)


def test_offer_window_scales_with_time_until_the_raid():
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def window(minutes_left):
        ping, end = R.offer_window(now, now + timedelta(minutes=minutes_left))
        return round((ping - now).total_seconds() / 60, 2), round((end - now).total_seconds() / 60, 2)
    assert window(10 * 24 * 60) == (2880.0, 4320.0)       # ten days out: two days, last call, then one more day
    assert window(30 * 24 * 60) == (2880.0, 4320.0)       # a month out: the same, capped at three days
    assert window(2 * 24 * 60) == (576.0, 864.0)          # two days out: about 14 hours, last call after 9.6
    assert window(4 * 60) == (48.0, 72.0)                 # four hours out: 72 minutes
    assert window(60) == (12.0, 18.0)                     # an hour out: 18 minutes
    assert window(10) == (6.0, 9.0)                       # starting very soon: never past the start
    assert window(1)[1] == 1.0 and window(0)[1] == 1.0


def test_bench_queue_end_to_end_offer_accept_and_pass(tmp_path):
    from types import SimpleNamespace
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 2, 9)
    sent, edits = [], []

    class U:
        bot = False

        def __init__(self, uid):
            self.uid = uid

        dm_channel = None

        async def send(self, text, view=None):
            sent.append((self.uid, text, view))
            return SimpleNamespace(id=1000 + len(sent))

        async def create_dm(self):
            return SimpleNamespace(get_partial_message=lambda mid: SimpleNamespace(edit=_noop))

    async def _noop(**kw):
        return None

    def ix(uid):
        async def edit_message(**kw):
            edits.append((uid, kw))
        return SimpleNamespace(user=SimpleNamespace(id=uid), response=SimpleNamespace(edit_message=edit_message))

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        bot.get_user = lambda uid: U(uid)
        raid = db.get_raid(rid)
        for uid, role in ((1, "dps"), (2, "dps"), (3, "dps"), (4, "dps")):           # 1, 2 in; 3 then 4 bounced to the bench
            bot.apply_signup(raid, uid, role, None)
        rows = {s["discord_id"]: (s["role"], s["wanted"]) for s in db.signups(rid)}
        assert rows == {1: ("dps", None), 2: ("dps", None), 3: ("bench", "dps"), 4: ("bench", "dps")}
        await bot.fill_open_slots(rid)
        assert sent == []                                                            # full: nobody is asked
        bot.apply_signup(raid, 2, "absent", None)                                    # 2 backs out
        await bot.fill_open_slots(rid)
        assert [(u, "Take it or pass" in t) for u, t, _ in sent] == [(3, True)]             # 3 is first in line
        await bot.fill_open_slots(rid)
        assert len(sent) == 1                                                        # not asked twice for one slot
        offer = db.offers_for_raid(rid)[0]
        await bot.answer_offer(ix(3), offer["id"], False)                            # 3 passes: 4 is asked
        assert [u for u, _, _ in sent] == [3, 4] and db.get_offer(offer["id"])["state"] == "declined"
        assert 3 not in {s["discord_id"] for s in db.signups(rid)}                    # passing takes you off the bench
        offer4 = db.offers_for_raid(rid)[1]
        await bot.answer_offer(ix(4), offer4["id"], True)
        assert db.get_offer(offer4["id"])["state"] == "accepted"
        await bot.answer_offer(ix(4), offer4["id"], True)                            # a second tap does nothing
    asyncio.run(run())
    final = {s["discord_id"]: (s["role"], s["wanted"]) for s in db.signups(rid)}
    assert final[4] == ("dps", None) and 3 not in final
    assert "You're in as DPS" in edits[-2][1]["content"] and edits[-1][1]["content"] == "That offer has expired."


def test_offers_expire_with_time_and_when_the_raid_starts(tmp_path):
    db = make_db(tmp_path)
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 2, 9)
    a = db.create_offer(rid, 3, "dps", "2026-11-11T20:00:00+00:00", "2026-11-11T20:10:00+00:00", "2026-11-11T20:15:00+00:00")
    b = db.create_offer(rid, 4, "dps", "2026-11-11T20:30:00+00:00", "2026-11-11T20:40:00+00:00", "2026-11-11T20:45:00+00:00")
    assert [o["id"] for o in db.expire_old_offers("2026-11-11T20:20:00+00:00")] == [a]
    assert db.get_offer(a)["state"] == "expired" and db.get_offer(b)["state"] == "pending"
    db.mark_closed(rid)
    assert db.get_offer(b)["state"] == "expired" and db.pending_offers() == []


def test_signing_up_needs_a_claimed_character(tmp_path):
    from types import SimpleNamespace
    from guildbot.bot import ClaimPicker, GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 5, 9)

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        calls = []

        async def send_message(text=None, **kw):
            calls.append(("send", text, kw))

        async def edit_message(**kw):
            calls.append(("edit", None, kw))
        ix = SimpleNamespace(user=SimpleNamespace(id=5), response=SimpleNamespace(
            send_message=send_message, edit_message=edit_message), followup=SimpleNamespace(send=send_message))
        for role in ("tank", "dps", "absent"):                              # every button, even "can't make it"
            calls.clear()
            await bot.handle_signup(ix, rid, role)
            assert calls[0][0] == "send" and "who you are" in calls[0][1] and isinstance(calls[0][2]["view"], ClaimPicker)
            assert calls[0][2]["ephemeral"] is True
        assert db.signups(rid) == []                                         # nothing was recorded
        db.claim(5, ["anduin-wrynn"])
        calls.clear()
        await bot.handle_signup(ix, rid, "dps")
        assert calls[0][0] == "edit"
    asyncio.run(run())
    assert [(s["discord_id"], s["role"], s["slug"]) for s in db.signups(rid)] == [(5, "dps", "anduin-wrynn")]


def test_unanswered_or_undeliverable_offers_get_an_at_ping_in_the_raid_channel(tmp_path):
    import discord
    from types import SimpleNamespace
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 2, 9)
    db.set_raid_posted(rid, 10, 20, None)
    pings, deleted, whispers, dms = [], [], [], []

    class Chan:
        async def send(self, text, view=None, allowed_mentions=None):
            pings.append((text, allowed_mentions))
            return SimpleNamespace(id=500 + len(pings))

        def get_partial_message(self, mid):
            async def delete():
                deleted.append(mid)
            return SimpleNamespace(delete=delete)

        async def fetch_message(self, mid):                                   # the raid post, refreshed after a take
            async def edit(**kw):
                return None
            return SimpleNamespace(edit=edit)

    class ClosedDMs:
        bot = False
        async def send(self, *a, **k):
            raise discord.Forbidden(SimpleNamespace(status=403, reason="x"), "Cannot send messages to this user")

    class OpenDMs:
        bot = False
        dm_channel = None

        async def send(self, text, view=None):
            dms.append(text)
            return SimpleNamespace(id=700 + len(dms))

        async def create_dm(self):
            return SimpleNamespace(get_partial_message=lambda mid: SimpleNamespace(edit=_ok))

    async def _ok(**kw):
        return None

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        bot.get_channel = lambda cid: Chan()
        raid = db.get_raid(rid)
        for uid in (1, 2, 3, 4):
            bot.apply_signup(raid, uid, "dps", None)
        bot.get_user = lambda uid: ClosedDMs() if uid == 3 else OpenDMs()
        bot.apply_signup(raid, 2, "absent", None)
        await bot.fill_open_slots(rid)                                       # 3 has DMs closed: pinged in the channel at once
        assert len(pings) == 1 and pings[0][0].startswith("<@3> a spot opened up in **Run**") and dms == []
        offer = db.offers_for_raid(rid)[0]
        assert offer["chan_msg_id"] == 501 and offer["state"] == "pending"
        wrong = SimpleNamespace(user=SimpleNamespace(id=4), response=SimpleNamespace(send_message=_whisper(whispers)))
        await bot.answer_offer(wrong, offer["id"], True)                     # someone else's button does nothing
        assert whispers == [("That spot was offered to someone else.", True)] and db.get_offer(offer["id"])["state"] == "pending"
        mine = SimpleNamespace(user=SimpleNamespace(id=3), message=SimpleNamespace(id=501),
                               response=SimpleNamespace(send_message=_whisper(whispers)))
        await bot.answer_offer(mine, offer["id"], True)                      # clicked in the channel: answer is a whisper
        assert whispers[-1][0].startswith("You're in as DPS") and whispers[-1][1] is True
        assert deleted == [501]                                              # and the ping is removed
        assert db.get_offer(offer["id"])["cleaned"] == 1
    asyncio.run(run())


def _whisper(log):
    async def send_message(text, ephemeral=False):
        log.append((text, ephemeral))
    return send_message


def test_a_quiet_dm_offer_also_gets_a_channel_ping_at_its_last_call_time(tmp_path):
    db = make_db(tmp_path)
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 2, 9)
    old = db.create_offer(rid, 3, "dps", "2026-11-11T20:00:00+00:00", "2026-11-11T20:03:00+00:00", "2026-11-11T20:20:00+00:00")
    new = db.create_offer(rid, 4, "dps", "2026-11-11T20:04:00+00:00", "2026-11-11T20:05:00+00:00", "2026-11-11T20:20:00+00:00")
    assert [o["id"] for o in db.offers_to_ping("2026-11-11T20:05:00+00:00")] == [old, new]
    assert [o["id"] for o in db.offers_to_ping("2026-11-11T20:03:00+00:00")] == [old]
    assert db.offers_to_ping("2026-11-11T20:02:00+00:00") == []                              # not yet time for either
    db.set_offer_messages(old, chan=77)
    assert [o["id"] for o in db.offers_to_ping("2026-11-11T20:05:00+00:00")] == [new]       # already pinged: not again
    db.set_offer_state(old, "declined")
    assert [o["id"] for o in db.offers_to_clean()] == [old]
    db.mark_offer_cleaned(old)
    assert db.offers_to_clean() == []


def test_tentative_is_a_maybe_that_takes_no_slot_and_bench_is_only_overflow(tmp_path):
    from guildbot.bot import BUTTONS, GuildBot, raid_embed
    assert [b[0] for b in BUTTONS] == ["tank", "healer", "dps", "tentative", "absent"]     # no Bench button
    assert R.ROLES.index("tentative") > R.ROLES.index("bench")
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 1, 9)
    raid = db.get_raid(rid)
    bot = GuildBot(cfg, db, blizzard=None)
    assert bot.apply_signup(raid, 1, "dps", None) == "dps"
    assert bot.apply_signup(raid, 2, "tentative", None) == "tentative"           # a maybe: no slot taken, no queue place
    assert bot.apply_signup(raid, 3, "dps", None) == "bench"                     # a full role sends you to the bench
    rows = {s["discord_id"]: (s["role"], s["wanted"]) for s in db.signups(rid)}
    assert rows == {1: ("dps", None), 2: ("tentative", None), 3: ("bench", "dps")}
    g = R.group_signups(db.signups(rid))
    assert R.filled(g) == 1 and [s["discord_id"] for s in g["tentative"]] == [2]
    bot.apply_signup(raid, 1, "absent", None)                                    # the slot opens: the queue, not the maybe
    assert R.next_offers(raid, db.signups(rid), []) == [(3, "dps")]
    names = [f.name for f in raid_embed(db, raid).fields]
    assert names == ["\U0001F7E6 Tanks (0)", "\U0001F7E9 Healers (0)", "\U0001F7E5 DPS (0)", "Bench (1)",
                     "\U0001F7E8 Tentative (1)", "\u2B1C Can't make it (1)"]
    assert "**Tentative (1):**" in R.roster_summary(raid, db.signups(rid))


def test_help_lists_every_command_and_shows_officer_ones_only_to_officers(tmp_path):
    from guildbot.bot import GuildBot, help_embed
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    bot = GuildBot(cfg, make_db(tmp_path), blizzard=None)
    member = " ".join(f.value for f in help_embed(False).fields)
    officer = " ".join(f.value for f in help_embed(True).fields)
    assert [f.name for f in help_embed(False).fields] == ["Claim and sign up", "Look stuff up"]
    assert help_embed(True).fields[-1].name == "Officers"
    for c in bot.tree.get_commands():
        if c.name == "commands":                                              # an alias of /help
            continue
        assert f"`/{c.name}`" in officer, f"/{c.name} is missing from /help"                 # nothing can be forgotten
    assert "/raid-create" not in member and "/wanted" not in member


def test_no_answer_takes_you_off_the_bench_and_asks_the_next_person(tmp_path):
    from types import SimpleNamespace
    from guildbot.bot import GuildBot
    db = make_db(tmp_path)
    asyncio.run(sync_guild(db, FakeClient(ROSTER), "g"))
    cfg = load({"DISCORD_TOKEN": "a", "BLIZZARD_CLIENT_ID": "b", "BLIZZARD_CLIENT_SECRET": "c", "GUILD_SLUG": "g"})
    rid = db.create_raid("Run", "2030-01-01T20:30:00+00:00", 1, 9)
    sent = []

    async def _noop2(**kw):
        return None

    class U:
        bot = False
        dm_channel = None

        def __init__(self, uid):
            self.uid = uid

        async def send(self, text, view=None):
            sent.append((self.uid, text))
            return SimpleNamespace(id=900 + len(sent))

        async def create_dm(self):
            return SimpleNamespace(get_partial_message=lambda mid: SimpleNamespace(edit=_noop2))

    async def run():
        bot = GuildBot(cfg, db, blizzard=None)
        bot.get_user = lambda uid: U(uid)
        raid = db.get_raid(rid)
        for uid in (1, 2, 3):                                                  # 1 holds the slot; 2 then 3 wait
            bot.apply_signup(raid, uid, "dps", None)
        bot.apply_signup(raid, 1, "absent", None)
        await bot.fill_open_slots(rid)
        assert [u for u, _ in sent] == [2] and "take you off the bench" in sent[0][1]
        db.conn.execute("UPDATE offers SET expires_at='2000-01-01T00:00:00+00:00'")      # time runs out
        db.conn.commit()
        await bot._expire_offers()
    asyncio.run(run())
    rows = {s["discord_id"]: s["role"] for s in db.signups(rid)}
    assert 2 not in rows and rows[3] == "bench"                                 # 2 is off the bench, 3 is next in line
    assert [u for u, _ in sent] == [2, 2, 3] and "took you off the bench" in sent[1][1]
