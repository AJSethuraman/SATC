# Gauntlet: a first-person shooter inside WoW

A first-person shooter drawn entirely with WoW's own widgets and assets, as an addon for the Forever client. It is a playable five-level game.

## What it is
- **Raycaster** (`Ray.lua`, pure maths): one ray per screen column, found by stepping square to square; walls are thin textured
  strips. Flat floor and ceiling, walls at one height: an early-shooter look, not full 3D.
- **Enemies are real WoW 3D models**, placed by distance and hidden when a wall is in front of them.
- **Names and art are WoW's.** Nothing from Doom (names, art, maps, text) is used; only the general idea of the genre.

## Run it
1. Extract `Install-Gauntlet.zip`, double-click `Install-Gauntlet.bat`. It copies the addon into the Forever AddOns folder.
2. In WoW: `/reload`, then `/gaunt`.
3. Five levels of rooms and doors. Find the key, open the locked door, reach the exit. Level 5 ends at a boss (Gorefang the Unwelcome).
4. Controls: **W/S** move, **A/D** strafe, **Q/E**, arrows or the **mouse** turn, **space or click** fires, **1-4** pick a weapon
   (pistol, blunderbuss, repeater, rocket launcher; found on the way), **wheel** cycles, **Esc** leaves. Progress is saved.
5. To hand me the result: `/reload`, then double-click `Collect-Gauntlet-Report.bat` (puts `Gauntlet-report.zip` on the Desktop with
   the report and screenshots), or `/gaunt report` to copy the text.

Commands: `/gaunt` (play or resume), `/gaunt new`, `/gaunt report`, `/gaunt cols 80-320`, `/gaunt scale 1.5`, `/gaunt shots on|off`,
`/gaunt mouse on|off`, `/gaunt test` (the speed and asset tests), `/gaunt stop`.

## How it is built
`Rules.lua` weapons, enemies, items, walls, sounds. `Gen.lua` makes each level from a seed (rooms, corridors, doors, one locked door
with its key placed before it, checked by flood-fill). `Nav.lua` lets monsters path to you. `Play.lua` is the whole game with no
WoW calls in it. `Main.lua` is the window, HUD, keys, saving and the report. `Ray.lua`, `Render.lua` the drawing.
Measured in the real client: 320 columns held 72 fps (the client cap).

## Files
`Gauntlet/Ray.lua` the raycaster, collision and shooting maths. `Level.lua` the test map and the asset lists. `Bench.lua` the camera
route, frame statistics, verdict and report text. `Render.lua` drawing with widgets. `Gauntlet.lua` the flow, keys, mouse, shooting.
Tests: `python -m pytest -q tests` (each test runs on Lua 5.5 and on 5.1, which is what WoW runs).

## What the tests cannot say
How it looks and feels in the real client. They prove the maths with hand-worked cases, that every step runs against a stand-in
client, and the rules (a wall hides an enemy, a key does what it says, a shot stops at a wall).
