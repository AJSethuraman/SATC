# Project: Forever Guild Bot

Status as of 2026-11-11: running on the Forge (Windows, Task Scheduler task `ForeverGuildBot`) against the real Discord server and the real Blizzard API. Parsers are confirmed against real responses. The raid flow, claiming, recipes and the bench queue have been walked in the real server by the owner. See README for the commands.

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

**Verified by running it (2026-11-11, US region, guild slug `it-was-us`, 16 members):**
- An **app (client-credentials) token reads public characters**: profile, professions and equipment returned 200 for 13 of 16 members, with no Battle.net link needed. The other 3 returned 404 on all three endpoints. They are the lowest-level members (levels 1, 6 and 9, all rank 5 or 3). Cause not known (not yet logged out, or private). The bot reports them as "not found", not as failures.
- Guild roster path is right: `GET /data/wow/guild/it-was-us/roster?namespace=profile-forever-us` (realmless, guild slug is the lowercased guild name with dashes). Each roster member has `character.name`, `surname`, `slug`, `level`, `faction.type`, and class/race as **ids only**; `rank` is on the member. Class and race names come from the character profile.
- Profile: `character_class.name`, `race.name`, `faction.name`, `level`, `last_login_timestamp` (ms), `average_item_level`, `guild`. Matches `parse_profile` with no change.
- Professions: `primaries` and `secondaries`, each with `tiers[]` holding `skill_points`, `max_skill_points` and `known_recipes[]`. Classic-style caps (75/150/225). Matches `parse_professions`.
- Equipment: `equipped_items[]` with `slot.type` and `slot.name`, `name`, `quality`, `item.id`. **Rings are named "Ring 1" and "Ring 2"** (types `FINGER_1`/`FINGER_2`), so the slot key does not collide. Trinkets were not seen in this sample (no member had one equipped); expected "Trinket 1/2" by the same pattern, unconfirmed.
- Quests: `GET /profile/wow/character/{slug}/quests` returns `in_progress[]` (quest name + id) and `completed` (a link); `GET .../quests/completed` returns `quests[]` (name + id). So **completed and open are both available** with an app token. Not used by the bot yet.
- A static-data namespace exists: item, quest and class links in the responses point at `static-1.60.1_70399-forever-us`. Not tested by us yet.
- Raw responses are saved in the `snapshots` table; trimmed, name-anonymised copies are in `tests/fixtures/forever_*.json` and tested in `tests/test_all.py`.
- Static data works with an app token and **needs no version number**: namespace `static-forever-us` (the responses name `static-1.60.1_70399-forever-us`, which also works, but that suffix will change with patches). `GET /data/wow/profession/index` lists professions (plus a Blizzard test entry "[DNT]", skipped); `/data/wow/profession/{id}` lists `skill_tiers`; `/data/wow/profession/{id}/skill-tier/{tier}` lists `categories[].recipes[]` (id + name). About 2,490 recipes across 12 professions. Includes everything in the data, not only what is learnable in game now.
- `GET /data/wow/recipe/{id}` has `crafted_item` (id + name; absent for recipes that make no item, such as enchants), `reagents`, `crafted_quantity`. `GET /data/wow/item/{id}` has `quality`, `level`, `required_level`, `item_class`, `item_subclass`, `inventory_type`. About 1,850 distinct crafted items. Item ids for classic-origin items match Classic ids (for example 2847 Copper Shortsword).
- Professions response: each tier has `known_recipes[]` (id + name). The profession's own entry (for example "Skinning") appears as a known recipe and is dropped.
- Blizzard does **not** say where a recipe is learned (no trainer, vendor or drop data). The bot links out to Wowhead. **Wowhead has a WoW Forever section** (`https://www.wowhead.com/forever`; its top nav has a FOREVER tab, owner confirmed 2026-11-11). The bot links to `/forever/item={id}` when it has an item number from Blizzard's Forever API and to `/forever/search?q=...` otherwise. The first search links pointed at the retail site (`/search?q=`) and returned retail results: do not use that. Item-number pages are not yet confirmed for every Forever-specific id.
- Discord: a bot cannot start a private (ephemeral) message; only a reply to a click can be private. "Whispers" are used for replies and DMs elsewhere. Pinning a message adds a "pinned a message" line to the channel; the bot deletes that line itself. `discord.py` 2.7 supports a select menu inside a pop-up (used for the character choice at signup).
- **Legacy (verified 2026-11-12, app token).** There is no `legacy` endpoint (`/legacy`, `/legacy-points`, `/legacy-tree`, `/legacy-perks` under the character, and `/data/wow/legacy*` in the static namespace, all 404; the user-account path `/profile/user/wow` is 403 with an app token). The Legacy **challenges are ordinary achievements**: each carries `reward_description: "Earn 1 Legacy Point."` and `is_account_wide: true`. Static root categories (`/data/wow/achievement-category/index`) are Classes, Tradeskills, Dungeons, Raids, Player vs. Player, Adventure (plus a hidden "Do Not Display"), matching Blizzard's six Legacy categories. A character's `/achievements` lists the ones it earned (`achievement.id`, `completed_timestamp`). Example: a level-30 Hunter has "Novice Hunter" (id 61989, the level-25 mark). Raids are "Conqueror of the Wilds" (Hyjal Summit), "Conqueror of the Deeps" (Barrow Deeps), "Conqueror of the Lair" (Onyxia). **Open:** every achievement exists twice under two id ranges (for example Novice Hunter 61989 and 63975; the Raids category lists six, Blizzard's article says 3), so the category counts come out at exactly double Blizzard's 27/18/12/3/3. Why is not known. **Checked 2026-11-12 across all 13 visible members: every completion is on the lower id set (61502 to 63342 plus 684 for Onyxia); nobody has anything on the higher set (63969 to 64033).** The bot treats the two copies of a name as one challenge, so it is right whichever set a character uses.
  - Exactly 130 achievements have the "Earn 1 Legacy Point." reward: 65 names twice, split Classes 27, Tradeskills 18, Player vs. Player 12, Dungeons 3, Raids 3, Adventure 2 (Blizzard's numbers). The other 46 in those categories are zone exploration steps with no reward (they feed "Explorer").
  - What each needs, from the achievement's own `description`/`criteria`: class "Novice/Experienced/Master <Class>" = level 25/45/60 of that class; tradeskill "Journeyman/Expert/Artisan" = 150/225/300 skill "for the first time" (Alchemy, Blacksmithing, Enchanting, Engineering, Leatherworking, Tailoring; not gathering, cooking, first aid or fishing); "Novice/Experienced/Master Spelunker" = complete 6/10/17 listed dungeons; PvP = honor ranks 3/7/10/13/14, exalted with four battleground factions, Field of Honor weeks 4/7/10; Adventure = "Lord Valthalak Laid to Rest" (a questline) and "Explorer".
  - A character's `/achievements` lists **in-progress entries too**: only entries with `completed_timestamp` (ms) are earned. In-progress entries carry `criteria.child_criteria[].amount` and `is_completed` (for example Enchanting 94 toward 150).
  - **Completions are shared across a Battle.net account.** A Warrior shows "Novice Paladin" and a Mage shows "Novice Druid", each with the same `completed_timestamp` (to the minute) as the account's Paladin or Druid. So one character shows its whole account's Legacy progress, as of that character's last logout (a character that has not logged out since shows an older set). Two characters with the same completion and timestamp are almost certainly one account. Exploration achievements are per character (own timestamps).
  - **Likely alts (verified 2026-11-12, all 13 visible members, every character sub-endpoint tried).** The two pairs sharing a Legacy timestamp each share a *solo* point (Novice Druid, Novice Paladin), and one pair is a member's claimed main and alt. `collections/mounts` and `collections/toys` hold only what comes with the account: Cerulean Prideclaw (mount 3111) and Shen'dorei Windwell (toy 1761) always together, and Veteran Adventurer's Loyal Companion (mount 3130) on some of those; level-14 characters have them, so they are not earned. The guild splits 6 / 4 / 3 across none / edition / edition + veteran, and both known pairs match. An empty collection leaves the list out of the response. **What does not help:** `surname` (13 different), `achievement_points` and `titles` (0 / empty for all), `achievements/statistics` (per character), character `id`, logout times. Group points (Dungeons, Raids, PvP) are earned by a whole group in the same minute, so they are not evidence (owner's catch). The bot's rule (`legacy.likely_alts`): a shared solo point in the same minute, the same known account items, and nothing against it (no point held at two different times, not claimed by two members); a group with any bad pair is dropped whole. It is a guess and is labelled so. **Owner decision 2026-11-12:** likely alts are shown only to officers (`/legacy-board`) and in a DM to the server owner when a new pair turns up; never to members or in a channel. A claim always wins. Whether the edition and veteran items are what they look like is not confirmed; the rule only needs them to be per account.
  - Dungeon progress ("Novice Spelunker": 6 child criteria) is **per character**, not shared: on 2026-11-12 members ranged from 1 to 4 of 6. `amount` on a child is a run count.
  - Every member's profile has `ruleset` "PvP" (id 1). Whether the unused second id set belongs to another ruleset is not tested.
  - The Legacy **perks and spent points** (the three trees) were not found in any endpoint tried. Blizzard's own description: https://news.blizzard.com/en-us/article/24307383/ (undated). Each point is earned on the account and each character spends up to 16 across the Professions, Adventure and Resourcefulness trees.
- Windows needs the `tzdata` package for `zoneinfo`.

**Verified from sources (community reports and Blizzard forum threads, Nov 2026; not tested by us):**
- Forever API namespaces: `profile-forever-{region}`, `dynamic-forever-{region}`.
- Characters have no realm; they have a name and surname. Slug is `{name}-{surname}` lowercase.
- Guild endpoints realmless: `/data/wow/guild/{guild-slug}` plus `/roster`, `/activity`, `/achievements` (profile namespace); roster members carry surname and slug.
- Character sub-endpoints reported working: achievements, appearance, collections, encounters, equipment, media, Mythic Keystone, professions, PvP summary, quests, reputations, specializations, statistics, titles.
- Account summary (user token) can lag the character profile by 20 to 40 minutes.
- Public character lookups returned 404 on launch day (Nov 4); later reports say they work. Re-tested 2026-11-11: they work (see Verified).
- Forever shares Mainline UI architecture and Midnight's addon restrictions (secrets). Addons cannot read the combat log in Forever, per the DOINK addon page.
- Blizzard's native Discord guild-chat link (patch 12.1) also works in Forever. A bot in the linked channel could read guild chat (our inference; untested).

**Unverified. Test first:**
- Legacy: the challenges are readable as achievements (see Verified); the spent points and chosen perks are not found in any endpoint tried. Why each achievement appears twice is unexplained.
- Why 3 of 16 low-level members return 404 (see Verified).
- Whether trinket slots are named "Trinket 1/2".
- Whether the static namespace has usable item and creature data (a namespace exists).

## Roadmap

**Phase 0: first run (done 2026-11-11)**
1. Owner supplies Discord bot token, Blizzard client ID/secret, guild slug in `.env` on the Forge.
2. Run the bot, run `/guild-sync`, read the failures list. Fix `blizzard.py` parsers against the saved raw snapshots. Add fixtures from real responses to tests.
3. Record what is now verified in this file.

**Phase 1: make raids good** (done 2026-11-11, walked in the real server)
- Raid creation is guided (`/raid-create` with no options). Limits are per raid; with all three roles limited, the size is their total.
- Claiming characters: first claim wins, max 5 each, officers can purge (`/unlink-member`) or free one (`/release`). Signing up needs a claimed character; with several, a pop-up asks which. Ownership cannot be proven (the app token cannot tell who owns a character), so this is trust plus officer cleanup.
- Buttons are Tank / Healer / DPS / Tentative / Can't make it. Bench is not a button: it is where a full role sends you automatically, and it is the queue for a spot. Tentative is a maybe that takes no slot (owner decision 2026-11-11).
- No answer to a bench offer, or Pass, takes the person off the bench (their signup is removed; they are told and can tap a role to rejoin). Owner decision 2026-11-11.
- Bench is a queue with offers by DM, a last-call @ in the channel, and a window that scales with the time left. Reminders, cancellations and roster summaries are DMs, not channel posts, so the channel stays clean.
- Raid posts are pinned while live, marked COMPLETED and unpinned when done, and kept as the record. Hand-made deletions of the post or event are noticed.
- Commands are limited to `BOT_CHANNEL_IDS`. The sync command is `/guild-sync` because another bot on the server already has `/sync`.
- Owner decisions: Discord permission **Manage Events** defines an officer (role "<it was us> Admin"); everything "noisy" is private; links to items go to Wowhead's Forever section (the item page when we have its number, a Forever search otherwise).
- Not yet tried live: a full role pushing a second real person to the bench and back, a non-officer refused an officer command, DMs-closed fallback, `/raid-end`.

**Done 2026-11-11 (Phase 2, partly):** `/recipes`, `/whocan`, `/craftable`, `/gaps`, `/wanted` from Blizzard's static data. Not built: creatures, NPCs, drop rates, quest chains (still the open-data plan below).

**Done 2026-11-11:** guild achievements (levels and profession skill marks, own channel), raid history and attendance (credit at the start, `/raid-attendance`, `/history`, `/attendance`), repeating raids that ask last week's regulars back. Owner on craft requests with materials: interesting but maybe annoying, iterate later.

**Done 2026-11-12:** Legacy points from Blizzard's achievements (`/legacy`, `/legacy-board`, a post per point earned), last login and item level kept with a history (`character_history`, one row per change), `/inactive`, item level in `/who` and `/roster`.

**Next (owner picked):** class roles from claimed mains (a Discord role per class; `/unlink-member` removes them), an item level board, quest buddies and "Tonight's plan" (quests endpoint is verified), weekly chronicle and level-up feed, inactive report from `last_login_timestamp`.

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

## Skill-up planner (`/skillup`)
- Orange, yellow, green and gray are not in Blizzard's API. They come from the game's own `SkillLineAbility` table (learn / yellow / gray skill per recipe), saved as `src/guildbot/data/skill_ranges.csv`. Source: wago.tools, WoW Forever build 1.60.1.70888 (covers 2,490 of the 2,493 catalogue recipes; Blizzard recipe id = that table's row ID). Blizzard's own static namespace is build 70399, so a recipe changed between the two builds could be off. Not confirmed by Blizzard's API.
- **Licence of that table is unchecked** (CLAUDE.md rule 4). It is raw game data extracted from the client and wago.tools is not Wowhead, and nothing was scraped from a page, but the owner should decide whether to keep it committed.
- "Cheap" means raw materials, never gold: a recipe's materials are expanded to what is gathered (a Bronze Bar counts as the copper and tin behind it). Within a stretch the planner always crafts the cheapest recipe that is still orange (every craft is a skill-up, so cheapest per craft is cheapest per point); it falls back to yellow only when nothing orange is left, counted at a rough 75% chance (not published). Assumes one skill point per craft.
- Needs each recipe's materials, which the item-catalogue sync now stores (`recipe_reagents`); an existing database refetches them once.

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
