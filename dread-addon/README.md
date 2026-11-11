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

## Play it (beta)
`/dread play` opens the game. Your own character is the player; the monsters, trees, rocks, graves and spell effects are WoW's own models, and the ground is a WoW terrain texture. All by file ID, from the community listfile.
- **The world:** The Gloam Moor (2400 x 1500) with a camp where you start, nine packs of monsters that sleep until you come close (and wake together), trees and rocks you walk round, and a cave mouth in the far corner. Walk in and you are in The Hollow Den, with a boss. Killing it finishes the quest and pays one skill point (once).
- **Mouse:** left click walks; left click a monster to walk up and attack it with your **wand** (free, no mana, level-scaled damage). Right click casts the selected skill at the cursor. Shift + left click casts without moving. Drag the window by its **title bar** only.
- **Skill bar (8 slots):** keys **1-8** select a slot; **Tab** or the **mouse wheel** rotate to the next one. Open the tree with **K**, hover a skill and press **1-8** to put it on that slot. New skills fill the first empty slot. The bar is saved.
- **Mana and life:** mana comes back at 4% of your pool a second (more with Evocation). Monsters sometimes drop a mana or life globe: walk over it for 35%.
- **The bottom bar:** a red life orb on the left, a blue mana orb on the right, your 8 skill slots between them with the experience bar underneath. **Skills (K)** and **New game** (click it twice) are in the title bar, which also shows the build time.
- **Solid things:** trees, fallen logs and rocks block you and the monsters; bushes and graves do not. `/dread solid` draws the blocking circles over the scenery so you can see exactly what stops you, and `/dread cam` / `/dread tile` tune how big things look.
- **Nothing moves while the tree is open.** `/dread scale 2` makes the window bigger. `/dread reset` starts over.
- Castable so far: Scorch, Frostbolt, Ice Lance, Arcing Bolts, Lightning Bolt, Fireball, Glacial Spike, Frost Nova, Thunder Nova. The others show "Not castable yet" in their tooltip.
- **Tuning without reinstalling:** `/dread tile 128` changes how big the ground texture tiles (`/dread tile` alone resets it). `/dread cam tree 3` moves the camera away from the trees (or `fallen`, `bush`, `grave`, `rock`) if they look cut off or too big or small. Both are saved.
- **Unverified in the client:** the animation id for casting (a guess: `/dread animtest` lets you pick it by eye), which way models face (`/dread facing <radians>` nudges it), and whether every file ID in `Zone.lua` and `Game.lua` exists in Forever.

## Multiplayer: what is known and what is not
Nothing is built. The idea: the game rules (`Combat.lua`) are deterministic, so every player can run the same simulation and only **inputs** (a click, a cast) need to cross the network, a few bytes each. That fits addon messages (255 bytes each, throttled). It needs the combat core to handle several players, a lobby (party leader hosts) and a desync check. **Unknown, and it decides everything:** whether Forever lets two players exchange addon messages at all, how fast, and how many before it throttles. `/dread net` (in a party with a friend who also has Dread) measures exactly that: 10 pings for round-trip time, then a burst of 40 messages to see what gets through. Results are saved in `DreadDB.results.net`.

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
