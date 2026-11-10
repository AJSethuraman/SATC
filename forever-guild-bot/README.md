# Forever Guild Bot

Tracks who is who and who has what in the guild (official Blizzard API, hourly sync) and runs raid signups from Discord. Local-first: one SQLite file, no cloud services besides Discord and Blizzard.

## Setup (on the Forge)

1. **Discord bot.** https://discord.com/developers/applications -> New Application -> Bot -> copy the token.
   Invite it with scopes `bot` and `applications.commands`, permissions: View Channels, Send Messages, Embed Links, Manage Events.
2. **Blizzard API client.** https://develop.battle.net -> API Access -> Create Client. Copy the client ID and secret.
3. `cp .env.example .env` and fill it in. `GUILD_SLUG` is your guild's name lowercased with dashes.
4. `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
5. `PYTHONPATH=src python -m guildbot`

Run tests: `PYTHONPATH=src python -m pytest -q`

## Commands

| Command | Who | What |
|---|---|---|
| `/link` `/unlink` `/main` | anyone | connect your Discord account to your characters |
| `/who` `/roster` `/professions` `/whohas` | anyone | who is who, who has what |
| `/raids` | anyone | upcoming raids |
| `/raid-create title date time size` | Manage Events | posts signup buttons + a Discord event. Date `2026-11-15`, time `20:00` (guild timezone) |
| `/raid-edit id [title] [date time] [size]` | Manage Events | changes a raid; a new time re-arms the reminder and moves the Discord event |
| `/raid-cancel id` | Manage Events | cancels and removes the Discord event |
| `/sync` | Manage Events | refresh from Blizzard now |

Raid signup buttons: Tank / Healer / DPS / Bench / Can't make it. A signup is your Discord account plus a role; no `/link` needed (a linked main is shown if you have one). When the raid is full, new Tank/Healer/DPS signups go to the bench. Signed-up players are pinged 60 minutes before start. At start time the buttons come off and signups close.

`/sync` reports how many of each kind loaded (e.g. `profile: 280 of 300 loaded, 20 not found`).

## Known unknowns (first run)

Blizzard's Forever API is undocumented. Field names in `blizzard.py` follow community reports and have not been checked against a live response.
On first run, use `/sync`: it lists any fetch problems. Every raw API response is saved in the `snapshots` table, so a parser can be fixed from real data without refetching.
