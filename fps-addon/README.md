# Gauntlet: a first-person shooter inside WoW (feasibility)

A first-person shooter drawn entirely with WoW's own widgets and assets, as an addon for the Forever client. This folder is the
feasibility test: can an addon draw a raycast 3D view fast enough, with real WoW wall textures, WoW 3D models as enemies and WoW
sounds, and can it be played with the keyboard and mouse? Same method as the last project: test the unknowns in the real client
first, then build.

## What it is
- **Raycaster** (`Ray.lua`, pure maths): one ray per screen column, found by stepping square to square; walls are thin textured
  strips. Flat floor and ceiling, walls at one height: an early-shooter look, not full 3D.
- **Enemies are real WoW 3D models**, placed by distance and hidden when a wall is in front of them.
- **Names and art are WoW's.** Nothing from Doom (names, art, maps, text) is used; only the general idea of the genre.

## Run it
1. Double-click `Install-Gauntlet.bat` (it is in `Install-Gauntlet.zip`, extract it first). It copies the addon into the Forever
   AddOns folder.
2. In WoW: `/reload`, then `/gaunt`.
3. It does everything by itself, about 40 seconds: the speed test at 160, 240 and 320 columns, the asset check (14 wall textures,
   6 models, 3 gun sounds), a page showing every candidate wall texture, and takes screenshots on its own.
4. Then you can walk around: **W/S** move, **A/D** strafe, **Q/E** or the **mouse** turn (the cursor's distance from the middle of
   the window sets the turn speed; keep it near the middle to go straight), **click or space** fires, **Esc** leaves.
5. To hand me the result: `/reload`, then double-click `Collect-Gauntlet-Report.bat`. It puts `Gauntlet-report.zip` on the
   Desktop with the saved report and the newest screenshots. Or `/gaunt report` opens the report text to copy.

Commands: `/gaunt` (tests, then walk), `/gaunt walk` (skip the tests), `/gaunt report`, `/gaunt mouse on|off`, `/gaunt stop`.

## What the report says
- **Test 1, speed:** average fps, the lowest, and the average of the slowest 1% of frames, per width. **GO** if 240+ columns hold
  60 fps with no stutter, **MAYBE** if only 160 do, **NO-GO** otherwise.
- **Test 2, assets:** how many wall textures drew, whether each model loaded, whether each sound will play.
- Whether the textures *look* right is in the screenshots (the texture page shows all 14 numbered).

## Files
`Gauntlet/Ray.lua` the raycaster, collision and shooting maths. `Level.lua` the test map and the asset lists. `Bench.lua` the camera
route, frame statistics, verdict and report text. `Render.lua` drawing with widgets. `Gauntlet.lua` the flow, keys, mouse, shooting.
Tests: `python -m pytest -q tests` (each test runs on Lua 5.5 and on 5.1, which is what WoW runs).

## What the tests cannot say
How it looks and feels in the real client. They prove the maths with hand-worked cases, that every step runs against a stand-in
client, and the rules (a wall hides an enemy, a key does what it says, a shot stops at a wall).
