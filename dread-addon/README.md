# Dread: D2-style ARPG addon for WoW Forever (feasibility)

Status: **idea; two tests written, neither run in game yet.** Decision: go / no-go after both.

Goal: an original action RPG inside an addon window. Click-to-move, kill, loot, build. WoW's own art and sounds,
no Blizzard D2 assets, no copied code.

## What is known
- Addons can run real-time games: ZNNQuest (survivor-style, TBC Classic) does movement, spells, loot, bosses and a guild leaderboard in Lua.
- The Doom Within (GPL-2.0) runs Doom in an addon, so Lua frame rendering can keep up with a game loop on at least some clients.
- Azeroth Survivors (Ashkenazii) targets the Forever flavor, so a game addon loads there.
- Azeroth Survivors is "All Rights Reserved". Do not copy its Lua. Re-creating mechanics from observed play is fine. Not legal advice.

## Not known (the tests answer these)
1. Draw rate on Forever at ~60 updates/sec with ~100 moving objects.
2. Which WoW art and sound paths an addon can use on Forever.
3. Whether Forever restricts addon APIs in a way that blocks a game window. A game window not loading at all is a fail of Test 1.

## Run the tests
1. Double-click `dist/Install-Dread.bat` (Windows; asks for administrator permission, copies the addon into `C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\Dread`). Rebuild it with `python build_installer.py` after any change to `Dread/`. Or copy `Dread/` there by hand.
2. The `.toc` uses `## Interface: 16001`, which is what `/dump select(4, GetBuildInfo())` returned on Forever (11 Nov 2026).
3. **Test 1:** `/dread`. Leave the window open 5 minutes, with WoW in front (the client caps background FPS at about 30, which would read as a fail). Pass: FPS stays above 30 and Lua memory grows no more than 10% between minute 1 and minute 5 (both measured after a full garbage collect). The addon prints PASS or FAIL.
4. **Test 2:** `/dread assets`. Look at the 20 icons for green or blank squares. Listen to the 5 sounds and the music track. The addon prints what the client returned, but a `true` is not proof you heard it, so write down what you heard.
5. `/dread sound` plays each sound alone, announced in chat, 3 seconds apart. Write down the numbers you heard.
6. `/dread results` reprints both. They are also saved in `DreadDB.results` in `WTF/.../SavedVariables/Dread.lua`.
7. Paste the results below.

## Results (fill in)
| Test | Date | Result | Notes |
|---|---|---|---|
| 1 loop speed | 11 Nov 2026 | **PASS** | FPS avg 71.2, min 57.4, 299 samples (cap 72). Lua memory 210,071 -> 210,465 KB (+0.2%). The memory figure is all addons together, not just Dread. |
| 2 icons | 11 Nov 2026 | **PASS** | 20/20 drew, no green squares (screenshot). |
| 2 sounds | 11 Nov 2026 | **PARTIAL** | By ID (`PlaySound` with SOUNDKIT): 3 of 3 returned true. By path (`PlaySoundFile`): 2 of 2 returned nil, which may just be wrong guessed paths. Whether the ID sounds were heard is not yet confirmed. |
| 2 music | 11 Nov 2026 | **UNCONFIRMED** | Undercity path returned true. Not yet confirmed by ear. |

The icon, sound and music names in `Dread/Dread.lua` are candidates, not known-good paths. Failing ones are the finding. If paths fail, list which, and fall back to shipping our own art.

## If both pass: v0.1 scope
Click-to-move top-down arena, one town screen, one dungeon level. One class, 4 skills. Items normal / magic / rare / unique with random affixes. Inventory grid and stash, saved in SavedVariables. Out of scope: multiplayer, set items, runewords, random level generation.

## Guild bot tie-in (later)
`forever-guild-bot` can read the addon's SavedVariables through the opt-in uploader tier (see its `docs/PROJECT.md`, Phase 3): weekly leaderboard post, shared guild stash or trade board. That needs the same uploader the bot's loot tracking needs, so it adds no new install.

## Rules for the build
- Original code and names. No D2 art, names or text.
- Game logic in pure Lua with no WoW API calls (`Dread/Sim.lua`), unit tested outside the game.
- Ship small. Stop if Test 1 or 2 fails.

## Check the logic
`pip install lupa pytest && python -m pytest -q tests` (4 tests; they run `Sim.lua` under plain Lua). The drawing and the sound calls can only be checked in game.
