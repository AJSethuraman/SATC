# Project: Forever Guild Bot

Status as of 2026-11-10: minimum version written and unit-tested with mocked data. **Never run against live Discord or Blizzard yet.**

## Goal
A Discord bot for the owner's WoW: Forever guild (launched Nov 4, 2026; a separate third version of WoW alongside modern and Classic). Two jobs:

1. **Who is who, who has what.** Track guild members' characters, levels, classes, professions, and gear from the official Blizzard API. Time lag is accepted.
2. **Run raids from Discord.** The owner creates and manages raids in Discord and does not want to do it in game. Members sign up with buttons.

Later (not built): Wowhead-style lookups from our own database, and a "Tonight's plan" feature.

## Constraints and preferences (from the owner)
- Local-first, privacy-conscious, runs on his home server ("the Forge").
- Deterministic, auditable tooling. Short, direct communication.
- Bias toward shipping a minimum over over-engineering.
- Wants **our own bot**, not an off-the-shelf one (explicitly rejected adding Wowhead's bot).
- The owner is the central organizer of events for the whole guild; the guild is full size, not a small group.

## Decisions already made
| Decision | Why |
|---|---|
| Official Blizzard API for roster data, accept lag | Simplest, no player installs. Data updates when a character logs out. |
| Raids managed entirely through Discord (slash command + buttons + Discord scheduled event) | Owner doesn't want to manage in game. |
| In-game addon + uploader is **opt-in**, built later | Addons can't reach the network; an uploader program on each player's PC is needed, so a full guild won't all install it. |
| Don't scrape Wowhead | It has no API and tries to block parsing; its terms page couldn't be read. Link out instead. Possible later: ask Wowhead for permission. |
| Build our own lookup data from open sources | See "Data sources" below. Curated FAQ rejected as too much work. |
| Python, discord.py, httpx, SQLite | Small, local, easy for Claude Code to maintain. |
| Signup = Discord account + role, no character needed | The Blizzard app token can't tell which account owns a character or who a Discord user is; linking would need each member to log in with Battle.net. `/link` stays optional, for `/who` and display. |
| Raid times typed as `YYYY-MM-DD` and `HH:MM` in guild timezone | Deterministic parsing; natural language rejected. |

## Architecture
See `CLAUDE.md` for the file map. Data flow:

`Blizzard API --(sync.py, hourly)--> SQLite (snapshots raw + parsed tables) --> Discord commands (bot.py)`

Raids: `/raid-create` -> row in `raids` -> embed + persistent buttons (`custom_id=raid:<id>:<role>`) -> `signups` table -> embed re-rendered on each click. Reminders ping signed-up players 60 minutes before start. Buttons are re-registered on startup for open raids.

Players connect Discord to characters with `/link`; the main character is the one used for raid signups.

## What is verified vs. unverified

**Verified from sources (community reports and Blizzard forum threads, Nov 2026; not tested by us):**
- Forever API namespaces: `profile-forever-{region}`, `dynamic-forever-{region}`.
- Characters have no realm; they have a name and surname. Slug is `{name}-{surname}` lowercase.
- Guild endpoints realmless: `/data/wow/guild/{guild-slug}` plus `/roster`, `/activity`, `/achievements` (profile namespace); roster members carry surname and slug.
- Character sub-endpoints reported working: achievements, appearance, collections, encounters, equipment, media, Mythic Keystone, professions, PvP summary, quests, reputations, specializations, statistics, titles.
- Account summary (user token) can lag the character profile by 20 to 40 minutes.
- Public character lookups returned 404 on launch day (Nov 4); later reports say they work. Re-test.
- Forever shares Mainline UI architecture and Midnight's addon restrictions (secrets). Addons cannot read the combat log in Forever, per the DOINK addon page.
- Blizzard's native Discord guild-chat link (patch 12.1) also works in Forever. A bot in the linked channel could read guild chat (our inference; untested).

**Unverified. Test first:**
- Exact JSON field names in roster, profile, professions, equipment responses. `blizzard.py` is written defensively but from guesses. Raw responses are saved in `snapshots`, so fix parsers from real data.
- That a client-credentials (app) token can read public characters' professions/equipment without each member linking Battle.net.
- That the quests endpoint returns what "Tonight's plan" would need (completed vs. open quests).
- Whether a Forever static-data namespace (items, creatures) exists.
- Whether the API exposes Forever's new "Legacy" system.

## Roadmap

**Phase 0: first run (do this first)**
1. Owner supplies Discord bot token, Blizzard client ID/secret, guild slug in `.env` on the Forge.
2. Run the bot, run `/sync`, read the failures list. Fix `blizzard.py` parsers against the saved raw snapshots. Add fixtures from real responses to tests.
3. Record what is now verified in this file.

**Phase 1: make raids good**
- Test the whole raid flow in the real server: create, sign up, change role, remind, cancel.
- Done 2026-11-10: `/raid-edit` (title/time/size), unit-tested, not yet tried in a real server.
- Done 2026-11-10: raids close at start time; a full raid sends new slot signups to Bench; `/sync` shows loaded/not-found counts per kind.
- Open: keep or prune old `snapshots` (unanswered; nothing is pruned).
- Likely needs: role caps (needs the owner's numbers per raid size), let a member pick which linked character signs up, post raid summary after.

**Phase 2: lookup database ("Wowhead in our bot")**
- Import open data into SQLite: CMaNGOS classic-db (GPL-3.0) and QuestieDB (an October 10 Forever snapshot exists in a published Questie archive). **Check licenses first** (Questie's repo has `LICENSE.md` and `gpl-3.0.md`; one mirror says MIT; unconfirmed).
- Commands: `/item`, `/npc`, `/quest`, `/zone`, `/farm <item>` with drop rates.
- Forever differs from Classic. Mark anything not confirmed for Forever as unconfirmed.
- Link out to Wowhead for what we can't answer.

**Phase 3: our own observed data (opt-in)**
- Addon records loot/kills; a small uploader on each opted-in player's PC posts to the Forge. Pattern to copy: the DOINK addon (addon writes saved variables, companion posts them; data only lands on logout, `/reload`, or exit).
- Test first whether the addon can attribute loot to the creature killed in Forever. If not, this phase is weak.
- Show sample size and contributor count with every drop rate. One-click installer to improve opt-in. Collect only loot/kills/zone, never chat.

**Phase 4: Tonight's plan** (owner picked this idea)
- For a raid or event: who signed up, their levels and quests, which dungeon fits best, who's missing quests. Rules-based scoring that shows its reasons. Depends on the quests endpoint (see unverified).

**Ideas not chosen yet:** help matching (find guildies who finished a quest), weekly guild chronicle, Legacy-system co-pilot, who-can-craft, upgrade finder, deaths board once Hardcore ships.

## Open questions for the owner
1. Guild name/slug and region (US assumed).
2. How many members will realistically install an uploader? Decides how much to invest in Phase 3.
3. Does the owner want to email Wowhead for permission (Phase 2 alternative)?

## Sources (checked Nov 2026)
- Forever API: https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334
- Forever namespaces: https://us.forums.blizzard.com/en/blizzard/t/world-of-warcraft-forever-api-namespace/59774
- Realmless roster example: https://github.com/cageymage/fuzion/pull/186
- Addon restrictions in Forever: https://warcraft.wiki.gg/wiki/Patch_1.60.1/API_changes/notes
- Addon/uploader pattern: https://www.curseforge.com/wow/addons/doink
- Open data examples: https://github.com/shagu/pfQuest, https://www.curseforge.com/wow/addons/codex-classic, https://github.com/Questie/Questie
- CMaNGOS database license note: https://github.com/jilinge2/classic-db
- Wowhead has no API / blocks parsing: https://us.forums.blizzard.com/en/blizzard/t/questions-about-blizzard-developer-api-terms-of-use/57897
- Blizzard addon policy (free, visible code): https://fanlore.org/wiki/Addon
- Native Discord guild chat link: https://pcgamer.com/games/world-of-warcraft/world-of-warcraft-players-will-never-have-to-leave-the-mmo-once-blizzard-adds-discord-chat-for-guilds-in-the-next-update/
