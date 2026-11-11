# Dread: D2-style ARPG addon for WoW Forever (feasibility)

Status: **idea; two tests written, neither run in game yet.** Decision: go / no-go after both.

Goal (updated 11 Nov 2026): a beta with **one full Mage with a 30-skill, three-tree skill system with synergies, and a Blood Moor-style first zone**. See `docs/BETA-SCOPE.md`.

Original goal: an original action RPG inside an addon window. Click-to-move, kill, loot, build. WoW's own art and sounds,
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

## Play it (beta, first playable)
`/dread play` opens the game window. Your own character is the player and the monsters are WoW's own 3D models.
- **Left click** walk. The window is scaled up (`/dread scale 2` for bigger, `/dread scale 1.2` for smaller). Nothing moves while the skill tree is open or before you have a spell. **Right click** cast the selected spell at the cursor. **1 to 9** pick a spell. **K** skill tree.
- Waves come from the top of the field. Kill them for experience; each level gives a skill point and refills life and mana.
- A new character has one point: press K and spend it. Your level and points are saved; `/dread reset` starts over.
- Castable so far: Scorch, Frostbolt, Ice Lance, Arcing Bolts, Lightning Bolt, Fireball, Glacial Spike, Frost Nova, Thunder Nova. The other skills show "Not castable yet" in their tooltip.

## Results (fill in)
| Test | Date | Result | Notes |
|---|---|---|---|
| 1 loop speed | 11 Nov 2026 | **PASS** | FPS avg 71.2, min 57.4, 299 samples (cap 72). Lua memory 210,071 -> 210,465 KB (+0.2%). The memory figure is all addons together, not just Dread. |
| 2 icons | 11 Nov 2026 | **PASS** | 20/20 drew, no green squares (screenshot). |
| 2 sounds | 11 Nov 2026 | **PASS by ID, FAIL by path** | `PlaySound` with SOUNDKIT: 3 of 3 returned true and were heard. `PlaySoundFile` with a path: 2 of 2 returned nil (guessed paths, so maybe just wrong). v0.1 uses sound IDs. |
| 3 visuals | 11 Nov 2026 | **PASS for models, FAIL for spell-effect paths** | Your character, your target and 6 creature ids drew as 3D models (they need a few seconds to load). `SetModel` with a spell-effect path failed ("Invalid model file: FileData ID 0"). Texture paths all drew; the two world-map ones are parchment art, not terrain. |
| 2 music | 11 Nov 2026 | **UNCONFIRMED, not needed** | Undercity path returned true. Not confirmed by ear (music volume 0.4 on master 0.1, and the track wasn't known). Left out of v0.1. |

**Decision, 11 Nov 2026: GO.** Loop speed has a lot of room (71 FPS with 100 moving objects), icons all draw, and sound works by ID. Start v0.1, with sound by ID only and no music.

The icon, sound and music names in `Dread/Dread.lua` are candidates, not known-good paths. Failing ones are the finding. If paths fail, list which, and fall back to shipping our own art.

## If both pass: v0.1 scope
Click-to-move top-down arena, one town screen, one dungeon level. One class, 4 skills. Items normal / magic / rare / unique with random affixes. Inventory grid and stash, saved in SavedVariables. Out of scope: multiplayer, set items, runewords, random level generation.

## Guild bot tie-in (later)
`forever-guild-bot` can read the addon's SavedVariables through the opt-in uploader tier (see its `docs/PROJECT.md`, Phase 3): weekly leaderboard post, shared guild stash or trade board. That needs the same uploader the bot's loot tracking needs, so it adds no new install.

## Rules for the build
- Original code. WoW names and art are fine; no D2 art, names or text (changed 11 Nov 2026, was "original names").
- Game logic in pure Lua with no WoW API calls (`Dread/Sim.lua`, `Dread/Skills.lua`, `Dread/Tree.lua`), unit tested outside the game.
- Ship small. Stop if Test 1 or 2 fails.

## Check the logic
`pip install lupa pytest && python -m pytest -q tests` (they run `Sim.lua`, `Skills.lua` and `Tree.lua` under plain Lua). The drawing and the sound calls can only be checked in game.
