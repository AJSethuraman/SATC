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
| Hades | Elysium | 11 chambers (ends room 37) | Theseus & Asterius |
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

**4 acts × 8 rooms = 32 rooms** to a full clear — near Hades' 37, and four acts
like Diablo II's first four.

Eight rather than fifteen because an Ashfall room is a full arena clear of
seven to ten bodies, not a Hades chamber's handful. Same wall-clock, fewer
doors.

### An act

| Room | Kind | Pays |
|---|---|---|
| 1 | combat | item |
| 2 | combat | boon |
| 3 | combat | item |
| 4 | **respite** | nothing — heals 50% |
| 5 | combat | boon |
| 6 | **elite** | item |
| 7 | combat | boon |
| 8 | **boss** | item rolled 7 deeper, at 85% magic, plus a boon |

Three items and three boons per act, deliberately equal: an item's tags widen
the boon pool, so an act that pays lopsidedly in one currency starves the other.

The rhythm is fixed rather than rolled so a player can see two rooms ahead and
decide whether to push on at low health for the thing they need. Without a
door-choice UI, that is the only interesting decision a linear act offers.

The old floor granted an item **and** a boon on every clear. There are now four
times as many encounters, so each pays roughly half as much.

### Scaling

Everything is written against **depth in rooms** (1–32), so difficulty never
depends on how the run is chopped into acts.

| | per room | per act entered | across a full clear |
|---|---|---|---|
| enemy health | ×1.09 | ×1.25 | ~28× |
| enemy damage | ×1.028 | ×1.10 | ~3.1× |

The act steps are separate from the room rates so an act boundary is a *felt*
event rather than a smooth ramp.

Damage is the term that came down. The balance simulator's most useful finding
was that random boon picks performed as well as greedy ones — which meant boon
choice was not deciding runs. The cause was enemy damage compounding faster than
player survival, which arrives in flat lumps from gear and defensive boons. A
~3× damage curve against a ~28× health curve is the correction: going deeper
should test whether a build *scales*, not whether it can survive a one-shot.

## Still open

- **The reliquary has no home.** Banking one item per run is a decision that
  wants somewhere the player is not being hit, and the respite room is the
  obvious place. The rules exist in `core/reliquary.gd`; nothing calls them.
- **The boss is a stat line, not a fight.** `RunState.boss_for_act` gives it 9×
  health, 1.6× damage and 0.82× speed. It has no phases and no unique telegraph,
  so right now it is a wall rather than an encounter.
- **Rooms are all the same arena.** Acts differ in numbers, not in place.
