# Forever Guild Bot: instructions for Claude Code

Read `docs/PROJECT.md` first. It has the goals, the decisions already made, what is verified vs. unverified, and the roadmap.

## What this is
A Discord bot for one WoW: Forever guild. It tracks who is who and who has what (official Blizzard API) and runs raid signups from Discord so the organizer never has to do it in game. Runs on the owner's home server (the Forge), local-first, one SQLite file.

## Commands
- Run tests: `PYTHONPATH=src python -m pytest -q` (must pass before any change is considered done)
- Run bot: `PYTHONPATH=src python -m guildbot`
- Setup and env vars: `README.md`, `.env.example`

## Layout
- `src/guildbot/blizzard.py`: the ONLY file that knows Blizzard's API shape (URLs, field names, parsers).
- `src/guildbot/sync.py`: roster/profile/professions/gear sync. Saves raw responses to `snapshots` before parsing.
- `src/guildbot/db.py`: all SQL. Schema is `SCHEMA` at the top.
- `src/guildbot/raids.py`: pure raid logic (time parsing, signup grouping). No Discord imports.
- `src/guildbot/bot.py`: Discord commands, signup buttons, background jobs.
- `tests/test_all.py`: unit tests with mocked API data.

## Rules
1. **Deterministic and auditable.** Same inputs, same outputs. Every number the bot shows must be traceable to a stored snapshot. Show "as of" times on anything from Blizzard.
2. **Local-first.** No new cloud services or third-party hosted dependencies without asking the owner.
3. **Keep Blizzard knowledge in `blizzard.py`.** The Forever API is undocumented and may change. Parsers fail loudly on shape changes (see `parse_roster`).
4. **Never scrape Wowhead** or other sites that block parsing. Link out to them instead. Use open data (CMaNGOS, QuestieDB) only after checking its license.
5. **Mark uncertainty in the product.** Data that came from Classic and is not confirmed for Forever must be labeled unconfirmed, not shown as fact.
6. **Secrets.** Never commit `.env`, tokens, or the SQLite file. Never log tokens or client secrets.
7. **Ship small.** Bias toward working and simple over general. No framework, no ORM, no extra services unless a real need shows up.
8. **Discord permissions.** Anything that changes raids or forces a sync requires Manage Events (`has_permissions`), not just a hidden command.
9. **Don't state unverified facts.** If you don't know how the Forever API behaves, test it or say so. Record what you learn in `docs/PROJECT.md` under "Verified".
10. Add or update tests with every behavior change. Parsers get a fixture from a real saved response once one exists.

## Working with the owner
The owner is a CPA who builds his own tools. Be direct, keep responses short, give a recommended option when asking a question, and say what changed and what's next.
