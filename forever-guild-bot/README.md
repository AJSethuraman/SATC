# Forever Guild Bot

Tracks who is who and who has what in the guild (official Blizzard API, hourly sync) and runs raid signups from Discord. Local-first: one SQLite file, no cloud services besides Discord and Blizzard.

## Setup (on the Forge)

1. **Discord bot.** https://discord.com/developers/applications -> New Application -> Bot -> copy the token.
   Invite it with scopes `bot` and `applications.commands`, permissions: View Channels, Send Messages, Embed Links, Manage Events, Manage Messages (to pin and unpin raid posts and remove Discord's "pinned a message" line).
2. **Blizzard API client.** https://develop.battle.net -> API Access -> Create Client. Copy the client ID and secret.
3. `cp .env.example .env` and fill it in. `GUILD_SLUG` is your guild's name lowercased with dashes. `BOT_CHANNEL_IDS` (optional, comma-separated channel IDs) limits the slash commands to those channels; anywhere else the bot answers privately "Use me in #channel".
4. `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
5. `PYTHONPATH=src python -m guildbot`

Run tests: `PYTHONPATH=src python -m pytest -q`

## Commands

Slash commands only work in the channels listed in `BOT_CHANNEL_IDS` (the bot answers privately anywhere else). "Officer" means the Discord permission **Manage Events**: give a role that permission and everyone with the role is an officer.

| Command | Who | What |
|---|---|---|
| `/link` `/unlink` `/main` | anyone | claim your characters (type a few letters; first claim wins, max 5). You must claim one before you can sign up for a raid |
| `/claim-panel` `/claims` `/unlink-member` `/release` | officer | post the claim button, see who claimed what, purge a troll, free one character |
| `/who` `/roster` `/professions` `/whohas` | anyone | who is who, who has what (item names link to Wowhead's Forever database) |
| `/recipes` `/whocan` | anyone | what a profession can make and which guildies know each recipe; who can craft a recipe. A recipe nobody knows shows as a gap |
| `/craftable` | anyone | guided search: pick kind, type, slot and level, see who in the guild can make it (private) |
| `/gaps` | anyone | profession coverage, and the recipes nobody in the guild has |
| `/skillup` | anyone | what to craft to level a profession, guaranteed (orange) first and cheapest in raw materials, plus a shopping list |
| `/wanted` | officer | searches that found nobody who can make the item |
| `/raids` | anyone | upcoming raids |
| `/history` | anyone (officers can look up anyone) | your raids attended, no-shows and late drops |
| `/raid-create` | officer | no options: a guided menu (day, time, size, then name and role limits). Or fill in `title date time size [tanks] [healers] [dps]` to skip it |
| `/raid-edit id ...` | officer | change title, time, size or limits. When tanks, healers and DPS are all limited, the size is their total |
| `/raid-cancel id` | officer | removes the post and event and messages everyone signed up |
| `/raid-end id` | officer | ends a raid now: post marked COMPLETED and unpinned, roster sent to you |
| `/raid-repeat-stop id` | officer | stops a raid repeating every week |
| `/raid-attendance id member showed` | officer | correct who showed up |
| `/attendance` | officer | who shows up, no-shows and late drops |
| `/guild-sync` | officer | refresh from Blizzard now |

## How a raid runs

- **Posting.** The raid post is pinned while the raid is live. A Discord event is created with it.
- **Signing up.** Tank / Healer / DPS, or Tentative (a maybe: no slot, no place in the queue; tap a role later to firm it up), or Can't make it. You need a claimed character. With several, a pop-up asks which one you are bringing.
- **Bench is automatic overflow, not a button.** A full role sends you to the bench and the bot remembers which role you wanted; the bench is a queue. When a slot opens, the next person in line gets a DM: Take it / Pass. How long they have is 30% of the time left until the raid (15 minutes at least, 3 days at most). Two thirds of the way through, an @ reminder goes in the raid channel (removed once they answer). If they still do not answer they are taken off the bench and told so, and the next person is asked. Passing also takes you off the bench; tap a role on the post to get back in.
- **Reminder.** Everyone signed up (slots, bench and tentative) gets a DM an hour before.
- **Start.** The buttons come off, the post says STARTED, and the organizer gets a DM with the roster.
- **Repeating.** The raid wizard asks "Repeat?". A weekly raid posts next week's by itself when this one ends (same time on the clock, daylight saving included) or is cancelled, and DMs last week's regulars (credited, tentative or bench) asking if it's the same again: Same as last time / Tentative / Can't make it. Nobody is signed up automatically.
- **Attendance.** Whoever is in a tank, healer or DPS slot when the raid starts is credited; the organizer corrects it with `/raid-attendance`. A late drop is leaving a slot within 24 hours of the start.
- **Guild achievements.** Each sync, the bot posts level 10/20/30/40/50/60 and profession 75/150/225/300 milestones in the achievements channel (`ACHIEVEMENTS_CHANNEL_ID`). New members and the first sync announce nothing.
- **End.** Three hours after the start (or `/raid-end`, or ending the Discord event by hand) the post says COMPLETED, is unpinned, and stays in the channel. Deleting the post or event by hand is noticed and the raid is closed.

## Recipes and items

The recipe list (about 2,500 recipes) and what each makes come from Blizzard's static data, fetched once and refreshed weekly. Known recipes come from each character's professions. The list includes everything in Blizzard's data, not only what can be learned in game today. Blizzard does not say where a recipe is learned, so each item links to Wowhead's Forever section.

`/guild-sync` reports how many of each kind loaded (e.g. `profile: 280 of 300 loaded, 20 not found`).

## Running it on the Forge

The Forge is Windows. The bot runs as the scheduled task `ForeverGuildBot` (starts at logon, restarts if it exits with an error). Logs go to `forge-setup\bot.log` next to the repo, outside it.

## Known unknowns

Blizzard's Forever API is undocumented. The field names in `blizzard.py` were checked against live responses on 2026-11-11 (see `docs/PROJECT.md`, Verified), but Blizzard can change them; parsers fail loudly when a shape changes.
If a sync reports problems, `/guild-sync` lists them. Raw API responses are saved in the `snapshots` table, so a parser can be fixed from real data without refetching.
