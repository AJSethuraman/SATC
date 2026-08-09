# Acts, not floors

## What was wrong

The prototype's unit of progression was the **floor**: one arena, one clear, one
item, one boon, repeat, up to fifteen times. That is a Hades *chamber* wearing
the name of a Diablo *act*, and it gave a run no shape. Every encounter was the
same size, paid the same reward, and led to another identical one. There was
nowhere to arrive.

## What the reference games actually do

Both games agree that the unit is a **sequence of spaces ending in a named
fight**, and they agree closely on how long it is.

| Game | Unit | Spaces before the boss | Boss |
|---|---|---|---|
| Hades | Tartarus | 15 chambers | Megaera |
| Hades | Asphodel | 10 chambers | Lernie |
| Hades | Elysium | 11 chambers (ends area 37) | Theseus & Asterius |
| Diablo II | Act I | 9 waypoints | Andariel |
| Diablo II | Acts II, III, V | 9 waypoints each | act boss |
| Diablo II | Act IV | 3 waypoints (deliberately short) | Diablo |

So: **8–15 spaces, mixed kinds, ending in a boss.** Hades runs about 37 chambers
to a full clear across four biomes; Diablo II runs five acts.

Sources: [Hades — Tartarus](https://hades.fandom.com/wiki/Tartarus),
[Asphodel](https://hades.fandom.com/wiki/Asphodel),
[Elysium](https://hades.fandom.com/wiki/Elysium),
[Diablo II waypoints](https://diablo2.diablowiki.net/Waypoint),
[Diablo II Act 1](https://diablo2.wiki.fextralife.com/Act+1).

## What Ashfall does

**4 acts × 8 areas = 32 areas** to a full clear — near Hades' 37, and four acts
like Diablo II's first four.

Eight rather than fifteen because an Ashfall area is a full arena clear of
seven to ten bodies, not a Hades chamber's handful. Same wall-clock, fewer
doors.

### An act

| # | Act I — The Cinderwaste | Kind | Pays |
|---|---|---|---|
| 1 | The Ashen Verge | combat | item |
| 2 | Cold Kilns | combat | boon |
| 3 | The Slagfields | combat | item |
| 4 | Emberwatch | **respite** | nothing — heals 50% |
| 5 | The Clinker Road | combat | boon |
| 6 | Bonemeal Yard | **elite** | item |
| 7 | The Last Furnace | combat | boon |
| 8 | The Great Kiln | **boss** | item rolled 7 deeper, at 85% magic, plus a boon |

Acts II–IV are the Sunken Works, the Glass Reach and Ashfall, each with their
own eight. All 32 names live in `core/progression.gd`.

Three items and three boons per act, deliberately equal: an item's tags widen
the boon pool, so an act that pays lopsidedly in one currency starves the other.

The rhythm is fixed rather than rolled so a player can see two areas ahead and
decide whether to push on at low health for the thing they need. Without a
door-choice UI, that is the only interesting decision a linear act offers.

The old floor granted an item **and** a boon on every clear. There are now four
times as many encounters, so each pays roughly half as much.

### Scaling

Everything is written against **depth in areas** (1–32), so difficulty never
depends on how the run is chopped into acts.

| | per area | per act entered | across a full clear |
|---|---|---|---|
| enemy health | ×1.09 | ×1.25 | ~28× |
| enemy damage | ×1.028 | ×1.10 | ~3.1× |

The act steps are separate from the area rates so an act boundary is a *felt*
event rather than a smooth ramp.

Damage is the term that came down. The balance simulator's most useful finding
was that random boon picks performed as well as greedy ones — which meant boon
choice was not deciding runs. The cause was enemy damage compounding faster than
player survival, which arrives in flat lumps from gear and defensive boons. A
~3× damage curve against a ~28× health curve is the correction: going deeper
should test whether a build *scales*, not whether it can survive a one-shot.

## Why "area" and not "floor"

"Floor 11" is a coordinate. It tells you how far you have counted and nothing
else, and a run made of coordinates has no sense of going anywhere — which was
the original complaint about floors, restated at the level of the word.

Diablo II never says floor. You are in the Blood Moor, then the Cold Plains,
then the Stony Field. The names are how you know both where you are and that
you are travelling. Hades does the same with its chambers hung off named
biomes. A numbered stack of identical rungs cannot do that no matter how many
rungs it has.

So the unit inside an act is an **area**, and every one of the 32 has a name. A
test asserts that none is missing and none repeats, because a clamped lookup
would quietly turn part of the map back into a number.

## What the simulator said about the first cut

The first version of this curve was measured at 200 runs per policy and came
back bimodal rather than merely hard:

    depth   p10 1 | median 2 | p90 23 | max 32
    cleared all 4 acts: 1.0% of runs
    ttk:  r1 2.9s  r5 1.5s  r9 1.2s  r13 1.2s  r21 1.7s  r29 2.5s

The median run died in **area 2 of act I** while the ninetieth percentile
reached area 23. Most runs ended before any gear had arrived to decide them
with, and the ones that survived that window snowballed — time-to-kill more
than halved between areas 1 and 9.

Density was the term at fault. At seven bodies an act-I area cost about 57% of
a full health bar, against a 12% restore between areas, so two areas emptied
the bar no matter what was equipped. Three changes, all aimed at the opening
rather than the ceiling:

- combat density `6 + act` → `4 + act` (five in act I rather than seven)
- restore between areas 12% → 22%
- boss health 9× → 6× — a boss is time on the clock, and every second of it is
  damage taken

## Still open

- **The reliquary has no home.** Banking one item per run is a decision that
  wants somewhere the player is not being hit, and the respite area is the
  obvious place. The rules exist in `core/reliquary.gd`; nothing calls them.
- **The boss is a stat line, not a fight.** `RunState.boss_for_act` gives it 9×
  health, 1.6× damage and 0.82× speed. It has no phases and no unique telegraph,
  so right now it is a wall rather than an encounter.
- **Areas are all the same arena.** Acts differ in numbers, not in place.
