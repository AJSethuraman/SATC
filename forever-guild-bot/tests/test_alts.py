"""Working out which characters are probably one player: account items, the three checks, the board, the DM."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from guildbot import blizzard as bz
from guildbot import legacy as L
from guildbot.config import load
from guildbot.db import utcnow
from guildbot.sync import likely_alt_news, sync_guild
from test_all import ROSTER, _fx, make_db
from test_legacy import CFG, LegacyClient, _done, _ix


def test_real_forever_collections_give_the_account_items():
    assert bz.parse_collection(_fx("mounts"), "mounts") == [3111, 3130]   # edition mount + veteran mount
    assert bz.parse_collection(_fx("mounts_empty"), "mounts") == []        # Blizzard leaves the list out when empty
    assert bz.parse_collection(_fx("toys"), "toys") == [1761]
    assert bz.account_items(_fx("mounts"), _fx("toys")) == "mount:3111,mount:3130,toy:1761"
    assert bz.account_items(_fx("mounts_empty"), {"_links": {}}) == ""
    with pytest.raises(bz.BlizzardError):
        bz.parse_collection({"something": "else"}, "mounts")
    with pytest.raises(bz.BlizzardError):
        bz.parse_collection({"_links": {}, "mounts": {"oops": 1}}, "mounts")


def _c(slug, cid, name, cat, at):
    return {"slug": slug, "challenge_id": cid, "name": name, "category": cat, "completed_at": at}


T1, T2, T3 = "2026-11-10T17:34:00+00:00", "2026-11-11T01:21:00+00:00", "2026-11-11T20:00:00+00:00"


def test_likely_alts_need_a_solo_point_the_same_items_and_nothing_against_it():
    rows = [
        _c("a", 1, "Novice Druid", "Classes", T1), _c("b", 1, "Novice Druid", "Classes", T1),          # linked
        _c("c", 9, "Conqueror of the Lair", "Raids", T2), _c("d", 9, "Conqueror of the Lair", "Raids", T2),  # a raid group
        _c("e", 2, "Novice Paladin", "Classes", T2), _c("f", 2, "Novice Paladin", "Classes", T2),      # items differ
        _c("g", 3, "Novice Mage", "Classes", T1), _c("h", 3, "Novice Mage", "Classes", T1),
        _c("g", 9, "Conqueror of the Lair", "Raids", T2), _c("h", 9, "Conqueror of the Lair", "Raids", T3),  # contradiction
        _c("i", 4, "Novice Rogue", "Classes", T1), _c("j", 4, "Novice Rogue", "Classes", T1),          # two claimers
        _c("k", 5, "Journeyman Tailor", "Tradeskills", T3), _c("l", 5, "Journeyman Tailor", "Tradeskills", T3),  # k unknown
    ]
    items = {s: "mount:3111,toy:1761" for s in "abcdghijl"}
    items.update(e="", f="mount:3111,toy:1761", k=None)
    got = L.likely_alts(rows, items, {"i": 1, "j": 2})
    assert got == [{"slugs": ["a", "b"], "shared": [("Novice Druid", T1)]}]


def test_a_chain_with_any_bad_pair_is_dropped_whole():
    rows = [_c("m", 1, "Novice Druid", "Classes", T1), _c("n", 1, "Novice Druid", "Classes", T1),
            _c("n", 2, "Novice Mage", "Classes", T2), _c("o", 2, "Novice Mage", "Classes", T2),
            _c("m", 7, "Journeyman Tailor", "Tradeskills", T1), _c("o", 7, "Journeyman Tailor", "Tradeskills", T3)]
    items = dict.fromkeys("mno", "")
    assert L.likely_alts(rows, items, {}) == []                  # m and o contradict, so no guess about any of them
    assert L.likely_alts(rows[:4], items, {})[0]["slugs"] == ["m", "n", "o"]


def test_players_follow_claims_first_then_the_guess():
    groups = [{"slugs": ["a", "b"]}, {"slugs": ["d", "e"]}, {"slugs": ["x", "y"]}]
    got = L.players({1: ["a"], 2: ["x"], 3: ["y"]}, groups, {"a", "b", "c", "d", "e", "x", "y"})
    assert got == [{"owner": 1, "slugs": ["a", "b"], "guessed": ["b"]},
                   {"owner": 2, "slugs": ["x"], "guessed": []},
                   {"owner": 3, "slugs": ["y"], "guessed": []},           # claimed by two members: claims win
                   {"owner": None, "slugs": ["d", "e"], "guessed": ["d", "e"]},
                   {"owner": None, "slugs": ["c"], "guessed": []}]


class AltClient(LegacyClient):
    def __init__(self, roster, ach=None, items=None):
        super().__init__(roster, ach)
        self.items = items or {}

    async def collections(self, slug):
        mounts = {"_links": {}}
        if self.items.get(slug):
            mounts["mounts"] = [{"mount": {"id": i, "name": "?"}} for i in self.items[slug]]
        return {"mounts": mounts, "toys": {"_links": {}}}


def _setup(tmp_path):
    db = make_db(tmp_path)
    db.replace_legacy_catalog([(61502, "Novice Druid", "Classes", "Druid", "Reach level 25 for the first time on a Druid.", 1),
                               (684, "Conqueror of the Lair", "Raids", "Raids", "Defeat Onyxia.", 6)], utcnow())
    when = datetime(2026, 11, 10, 17, 34, tzinfo=timezone.utc)
    druid = _done(61502, "Novice Druid", when)
    client = AltClient(ROSTER, {"anduin-wrynn": [druid], "judy-judgement": [druid]},
                       {"anduin-wrynn": [3111], "judy-judgement": [3111]})
    asyncio.run(sync_guild(db, client, "g"))
    return db, client


def test_sync_stores_account_items_and_finds_the_pair(tmp_path):
    db, client = _setup(tmp_path)
    assert db.account_items() == {"anduin-wrynn": "mount:3111", "judy-judgement": "mount:3111"}
    news = likely_alt_news(db)
    assert [(g["slugs"], pairs) for g, pairs in news] == [(["anduin-wrynn", "judy-judgement"], [("anduin-wrynn", "judy-judgement")])]
    client.items["judy-judgement"] = [3111, 3130]                     # different account items: not one player
    asyncio.run(sync_guild(db, client, "g"))
    assert likely_alt_news(db) == []


def test_the_server_owner_is_told_once_and_a_failed_dm_is_retried(tmp_path):
    from guildbot.bot import GuildBot
    db, _ = _setup(tmp_path)
    bot = GuildBot(load(CFG), db, blizzard=None)
    sent, up = [], [False]

    async def dm(uid, text, view=None):
        if up[0]:
            sent.append((uid, text))
        return up[0]
    bot.dm_user = dm
    bot._server = lambda: SimpleNamespace(owner_id=99)
    asyncio.run(bot.announce_likely_alts())                           # DMs closed: nothing marked as told
    assert sent == [] and db.likely_alts_seen() == set()
    up[0] = True
    asyncio.run(bot.announce_likely_alts())
    asyncio.run(bot.announce_likely_alts())                           # never twice
    assert len(sent) == 1 and sent[0][0] == 99
    assert "**Anduin Wrynn** and **Judy Judgement** look like the same player" in sent[0][1]
    assert "**Novice Druid**" in sent[0][1] and "a `/link` claim always wins" in sent[0][1]


def test_a_pair_one_member_already_claimed_is_not_news(tmp_path):
    db, _ = _setup(tmp_path)
    db.claim(5, ["anduin-wrynn", "judy-judgement"])
    assert likely_alt_news(db) == []


def test_the_board_covers_unclaimed_characters_and_marks_the_guess(tmp_path):
    from guildbot.bot import GuildBot
    db, _ = _setup(tmp_path)
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, sent = _ix(1, officer=True)
    board = bot.tree.get_command("legacy-board").callback
    asyncio.run(board(ix))
    e = sent[-1][1]
    assert sent[-1][2] is True
    assert e.description.splitlines() == ["Anduin Wrynn + Judy Judgement *(probably one player)*: 1 of 2"]
    assert e.fields[0].value == "1 of 1 still need it"
    db.claim(7, ["judy-judgement"])
    asyncio.run(board(ix))
    assert sent[-1][1].description.splitlines() == ["<@7> (+ probably Anduin Wrynn): 1 of 2"]


def _member(uid):
    """A fake interaction that records what the bot says back, privately or not."""
    said = []

    async def followup(text, view=None, ephemeral=False):
        said.append(("followup", text, view, ephemeral))

    async def edit(content=None, view=None):
        said.append(("edit", content, view, None))
    ix = SimpleNamespace(user=SimpleNamespace(id=uid, display_name="Me"), guild=object(),
                         permissions=SimpleNamespace(manage_events=False),
                         response=SimpleNamespace(is_done=lambda: True, edit_message=edit),
                         followup=SimpleNamespace(send=followup))
    return ix, said


def test_a_member_whose_claim_is_grouped_is_asked_privately_once_a_week(tmp_path):
    from guildbot.bot import AltView, GuildBot
    from guildbot.sync import alt_question
    db, _ = _setup(tmp_path)
    db.claim(5, ["anduin-wrynn"])
    now = utcnow()
    later = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(timespec="seconds")
    assert alt_question(db, 5, now) == "judy-judgement" and alt_question(db, 6, now) is None   # only the claimer
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, said = _member(5)
    asyncio.run(bot.on_app_command_completion(ix, None))          # after any command they run
    kind, text, view, private = said[-1]
    assert kind == "followup" and private is True and isinstance(view, AltView)
    assert text.startswith("Is **Judy Judgement** yours too?")
    asyncio.run(bot.on_app_command_completion(ix, None))
    assert len(said) == 1                                         # not again the same week
    assert alt_question(db, 5, later) == "judy-judgement"         # a week on, if never answered
    asyncio.run(bot.answer_alt(ix, "judy-judgement", True))
    assert said[-1][:2] == ("edit", "Linked **Judy Judgement**. Use `/main` if it should be the one that signs up.")
    assert db.owner_of("judy-judgement") == 5 and alt_question(db, 5, later) is None


def test_no_means_never_asked_or_grouped_again(tmp_path):
    from guildbot.bot import GuildBot
    from guildbot.sync import alt_question, board_players, likely_alt_news
    db, _ = _setup(tmp_path)
    db.claim(5, ["anduin-wrynn"])
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, said = _member(5)
    asyncio.run(bot.answer_alt(ix, "judy-judgement", False))
    assert "isn't yours" in said[-1][1] and db.owner_of("judy-judgement") is None
    later = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
    assert alt_question(db, 5, later) is None and likely_alt_news(db) == []
    assert [p["guessed"] for p in board_players(db)] == [[], []]     # shown apart on the board


def test_linking_a_character_asks_about_its_likely_alt_straight_away(tmp_path):
    from guildbot.bot import GuildBot
    db, _ = _setup(tmp_path)
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, said = _member(5)
    sent = []

    async def send_message(text=None, **kw):
        sent.append(text)
    ix.response.send_message = send_message
    link = bot.tree.get_command("link")
    asyncio.run(link.callback(ix, "anduin-wrynn"))
    asyncio.run(bot.on_app_command_completion(ix, link))          # what discord.py does once /link has answered
    assert sent == ["Linked **Anduin Wrynn**."] and said[-1][1].startswith("Is **Judy Judgement** yours too?")


def test_claiming_from_the_signup_menu_asks_too(tmp_path):
    from guildbot.bot import ClaimPicker, GuildBot
    db, _ = _setup(tmp_path)
    bot = GuildBot(load(CFG), db, blizzard=None)
    ix, said = _member(5)
    ix.data = {"values": ["anduin-wrynn"]}

    async def run():
        await ClaimPicker(bot)._picked(ix)
    asyncio.run(run())
    assert said[0][1].startswith("Linked: **Anduin Wrynn**")
    assert said[-1][0] == "followup" and said[-1][1].startswith("Is **Judy Judgement** yours too?")
