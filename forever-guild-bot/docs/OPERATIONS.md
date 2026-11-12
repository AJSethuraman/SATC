# Operating the bot on the Forge

For whoever keeps the bot running. Written 2026-11-12 from what was actually done on the Forge, not from a plan.
No secret appears in this file and none should: tokens live only in `.env`.

## Where everything is

| What | Where |
|---|---|
| Code | `C:\Users\ajish\SATC-forever\forever-guild-bot` (a git worktree of the SATC repo, branch `forever-bot-phase0` until PR #485 merges) |
| Python | `.venv\Scripts\python.exe` inside that folder. The system Python has no `httpx`, so tests fail with it |
| Secrets | `.env` in that folder (gitignored, access restricted). Keys: `DISCORD_TOKEN`, `BLIZZARD_CLIENT_ID`, `BLIZZARD_CLIENT_SECRET`, `GUILD_SLUG`, `ACHIEVEMENTS_CHANNEL_ID`, `BOT_CHANNEL_IDS` (empty on purpose: commands work anywhere because every answer is private) |
| Database | `guildbot.sqlite3` in the same folder (WAL mode, gitignored). **Backed up nightly** at 3:30 AM by the scheduled task **ForeverGuildBotBackup** (`forge-setup\backup_db.py`, Python's SQLite backup, safe while the bot runs, integrity-checked, last 14 kept in `forge-setup\backups\guildbot-YYYY-MM-DD.sqlite3`). Run it by hand any time with `Start-ScheduledTask ForeverGuildBotBackup` before a risky change. Restore: stop the bot (see below), copy a backup over `guildbot.sqlite3`, start it |
| Log | `C:\Users\ajish\forge-setup\bot.log` (appended forever; the bot's own output and every Blizzard request) |
| Launcher | `C:\Users\ajish\forge-setup\run-bot.cmd` |
| Persistence | Windows scheduled task **ForeverGuildBot**: runs at logon, restarts every minute if it dies (999 tries), no time limit |
| One-off scripts | `C:\Users\ajish\forge-setup\*.py`: Discord REST jobs (make a channel or role, edit the pinned post, clean test raids) and `patch_*.py` edit scripts. They read the token from `.env` and print nothing secret. Copy their pattern, never their output |

## Restart the bot (the part that is easy to get wrong)

`Stop-ScheduledTask` does **not** kill the Python process. Kill it, then start the task:

```powershell
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*guildbot*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep 3
Start-ScheduledTask -TaskName ForeverGuildBot
Start-Sleep 20
Get-Content C:\Users\ajish\forge-setup\bot.log | Select-String 'Gateway' | Select-Object -Last 1
```

Two `guildbot` processes after a start is normal (the venv launcher and the real interpreter). The bot is up when the log shows "connected to Gateway" and then "sync ok: 16 members". Look for `Traceback` in the log after any change.

## Test, change, ship

- Tests (must pass before anything counts as done, 111 at last count): `cd forever-guild-bot; $env:PYTHONPATH='src'; .venv\Scripts\python.exe -m pytest -q`
- Add or update a test with every behaviour change. Parsers get a fixture from a real saved response (`tests/fixtures/forever_*.json`).
- Database changes are idempotent `ALTER`s in `Database.__init__`, so an existing file upgrades itself. Run the backup task first, and test on a copy.
- Git: the repo's root `CLAUDE.md` is the workflow (feature branch, draft PR, merge once CI is green on the merged head and the Codex review reads Completed). Check `git status` before every commit so `.env` and `*.sqlite3` never go in. End commits with the attribution lines your session gives you.
- CI is slow (a long Actions queue). Every push restarts it, so batch changes into one push.

## Gotchas that cost real time

- **Blizzard data only updates when a character logs out.** Anything the bot shows from the API can be stale. `/skillup` takes an optional skill number for this reason. Recipes learned since the last logout will not show until then.
- Three members (one is `mooveover-onyourleft`) return 404 from the profile API, and nobody has explained why. Their data is missing, not wrong.
- **Windows tooling:** the Bash tool is Git Bash and mangles backslashes in heredocs and `sed`; use the Write tool for any script containing `\n` or Windows paths, or `chr(92)`. Set `MSYS_NO_PATHCONV=1` for API paths. Repo files are CRLF: read with `newline=""` and write the same endings back.
- Discord limits that bit us: 5 action rows per message; a bot cannot send an unprompted private message (it DMs instead); a Components V2 message cannot be turned into a normal one (the pinned claim post is V2, edit it with PATCH, see `forge-setup\panel_v2_sand.py`).
- The pinned claim post is message `1570195522340261889` in the raids channel `1570144217823711307`. Do not delete it: the claim button lives on it.

## Rules the owner set (do not relax)

- Never ask for, print, log, commit or echo a token, client secret or `.env` contents. If a secret must be entered, use a hidden-input script on the Forge or the one-shot Tailscale form pattern in `forge-setup\env-form.py`.
- The owner is a CPA, not a developer. Short, plain sentences; lead with the answer; recommend, do not survey; ask one thing at a time and only for what only they can do.
- Raid-time tools stay private (ephemeral replies and DMs). No new public lists in channels.
- Never scrape Wowhead. Link out to `https://www.wowhead.com/forever`. Skill-up ranges (`src/guildbot/data/skill_ranges.csv`) came from wago.tools; its licence is unchecked (see PROJECT.md "Skill-up planner").
- Officers are people with the Discord permission **Manage Events**; the **it was us Admin** role carries it. Anything that changes raids or forces a sync requires it.

## State on 2026-11-12

- Branch `forever-bot-phase0` is 8 commits ahead of its remote and **not pushed**. PR #485 is a draft with about 20 checks queued. Push once, mark ready, wait for green CI and the Codex review to read Completed, confirm the branch contains current `main`, then merge with a merge commit.
- Not yet exercised by the owner in the real server: `/raid-end`, the raid-create Repeat dropdown, `/history` and `/attendance`, the achievements post, a non-officer refusal, a full-bench overflow with a second real person, the DMs-closed fallback.
- Open question for the owner: which crafting materials count as "easy" for them, so `/skillup` can weigh them lightly (for example stone against smelted bars). Not built.
- Parked ideas: craft requests with materials, class roles from claimed mains, a weekly chronicle (the history table now feeds it), a raid readiness check / bring list in the reminder (owner: not yet).
- **Owner decision 2026-11-12: no nagging about bot chores.** Never DM or call out members to make them claim, or do any other bot chore. Make it worth doing instead. Raid logistics are not chores and stay: the reminder DM, the weekly "same again?" DM, and the bench promotion DM. The owner narrowed the rule to this after the adversarial review.
- **Owner decisions 2026-11-12 (after the adversarial review):** signups stay guild-only, behind a claim. The bench becomes "promote the first in line and tell them; if they say no, promote the next" (replacing timed offers, the public last call and removal on silence). The likely-alts question stays: "they may have just forgotten". Done so far: a claimed character's milestone posts show its player's name (no ping), and anyone without a claim sees one line about what claiming gets them in `/help`, `/raids` and `/roster` (only they see it). 4 of 16 characters were claimed when this was decided.
- Legacy (2026-11-12): the Legacy list is fetched weekly (meta `legacy_at`, about 190 calls); each character's achievements hourly with the sync. The first sync after the list loads marks everything done as seen (meta `legacy_seeded`), so old points are never posted. To re-post nothing after a database restore, leave `legacy_seen` alone.
- Likely alts (2026-11-12): each sync also reads every character's mounts and toys (`characters.account_items`). When the bot first works out that characters are probably one player, it DMs the **server owner** and records the pair in `likely_alts_seen` once the DM has gone (a failed DM is retried next sync). Log line: `likely alts: ...`. Clearing `likely_alts_seen` re-sends them. Pairs one member already claimed are never sent.
  A member whose claimed character is in a likely-alts group is asked privately, right after their next command (`/link` included) or a claim from the signup menu: "Is X yours too?" with Yes / No buttons. Yes links it; No is kept in `alt_answers` and that character is never grouped with them again. Unanswered, they are asked at most once a week. Never a DM (owner decision: influence, not nudges; the owner proposed this question himself on 2026-11-12). Rules and evidence: `docs/PROJECT.md`, "Likely alts".
