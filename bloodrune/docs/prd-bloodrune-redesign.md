# PRD: Bloodrune Redesign — a Diablo-2 ARPG as a Vampire-Survivors roguelite

**Status:** Draft · **Owner:** iamtrispec · **Last updated:** 2026-07-09

> v1 = the **Sorceress**, fully realized, plus all the new systems, on **Act 1**
> as the vertical slice. Other classes and Acts 2–5 are the roadmap. Numbers
> marked *(tuning target)* are validated by the headless balance bot, not
> hand-fixed here.

---

## 1. Problem

Bloodrune became a competent Vampire-Survivors loop wearing Diablo-2 names, and
it stopped feeling like D2. Per the owner, playing it: **skill trees are shallow**
(a point just adds flat damage to a range), **there are no synergies** (a skill's
power never depends on other points), **there's no reason to commit to one tree**
(spreading points is as good or better), **loot is "crazy usable"** (almost every
drop is an upgrade, so there's no treasure-hunt), and **greed is never punished**
(you can dump points anywhere and it works, with no matching gear required).
Telemetry confirmed the symptoms: a Sorceress cleared all of Act 1 at level 60,
took 279 damage over 9.5 minutes (a ~1000:1 ratio), and was buried in ~400
same-y drops. The moment-to-moment is fine; the **ARPG depth underneath it is
missing**.

## 2. Solution

Rebuild the depth so Bloodrune plays like Diablo 2 condensed into a roguelite
run. **Synergies become the damage**: a skill's power lives in the *hard points*
sunk into its same-tree siblings, so committing to one element is mathematically
dominant and spreading points is self-punishing — this single rule fixes shallow
trees, missing synergies, and no-reason-to-commit at once. **Loot becomes a
treasure-hunt**: rarity that matters, most drops trash/sidegrades for your build,
no auto-equip — you make loot decisions in **town**. **Greed is punished by dry
loot, not death**: a committed build is playable-but-limp on points alone and
*comes online* only when its enabler drops arrive. **Difficulty is a build
problem** (fire/cold/lightning resistances + Hell immunities), not a bigger HP
bar. Gear **persists in a tier-capped stash** you build across runs (start each
run by picking a loadout, Halls-of-Torment style), but you can only **bank it by
reaching town** — die in the field and the run's unbanked finds are lost.

## 3. Goals & Non-Goals

**Goals**
- The Sorceress has three real trees (Fire/Cold/Lightning) whose damage is driven
  by an **intra-tree synergy web**; a fully-fed capstone hits **≈3×** an
  unsupported one *(tuning target)*.
- **Committing to one tree is measurably dominant**; a thin three-tree spread does
  chip damage. Cross-tree synergy is exactly 0.
- **Gear `+skills` adds raw power (skill level → damage/radius) but ZERO synergy**,
  so manually-invested points always matter.
- Enemies have **fire/cold/lightning resistances**; Hell adds **single-element
  immunities**; each tree's **Mastery multiplies its element's damage**;
  penetration/immunity-answering comes from **gear + a secondary element**.
- Loot is **4 rarities (Common/Magic/Rare/Unique) + a sockets/runes/runewords
  aspiration ladder**, tier-gated by difficulty, tuned so **only ~10–15% of drops
  are a genuine upgrade for the current build**, falling as you gear.
- **No auto-equip.** Equipping/salvaging/socketing happens in **town** with an
  instant compare; junk salvages one-key into a craft/reroll currency.
- A **Str/Dex/Vit/Energy attribute economy** with gear requirement gates.
- **Persistent tier-capped gear stash** + a **starting-loadout picker**; character
  level/skills/attributes reset every run.
- **Town-checkpoint loot loop**: field loot is at-risk until banked in town; dying
  before town forfeits that segment's unbanked finds.
- **Standing still is lethal by construction** and no build collapses into a
  passive 360° nuke — movement stays meaningful at max power.

**Non-Goals / Out of scope (v1)**
- Other classes (Barbarian/Amazon/Necromancer). Systems are built class-agnostic;
  only the Sorceress is *content-complete* in v1.
- Acts 2–5 and the full ~45–60 min five-act run. v1 ships **Act 1** only.
- Multiplayer, cloud saves, monetization.
- Persistent *character power* of any kind (levels/skills/attributes never carry
  between runs; gear carries but is tier-capped — see §6.9). No account-wide stat
  boosts, ever.
- A full crafting tree beyond salvage → reroll/socket currency and runewords.
- Controller/gamepad support (keyboard + touch only, as today).

## 4. User Stories

1. As a player, I want each skill point to matter as a **commitment**, so that
   building my character is a real decision, not a loadout I shuffle.
2. As a player, I want **maxing one tree** to make my nuke hit dramatically
   harder than dabbling in three, so that focus is rewarded.
3. As a player, I want a skill's damage to **visibly scale with the sibling
   points I've invested** (shown in its tooltip), so that synergies are legible,
   not hidden math.
4. As a player, I want **gear that says "+2 Fire skills"** to make my whole fire
   build stronger, but *not* to replace the value of the points I chose myself.
5. As a Sorceress, I want to hit a **fire-immune** pack and have to **switch to my
   cold spells** or a penetration item, so that difficulty is a build puzzle.
6. As a player pushing Hell, I want my **Mastery** to make deep single-element
   investment scale super-linearly, so that specialization pays off late.
7. As a player, I want **most drops to be junk or sidegrades** so that a real
   upgrade feels like a find, not a stat tick.
8. As a player, I want to **decide** what to equip in a calm town screen with a
   side-by-side compare, and **salvage junk with one key**, so loot is a choice,
   not automatic.
9. As a player, I want a **Unique that turns my build on** (e.g. an orb granting
   +2 Fire skills and cast speed) to be a chase item, so gearing has a goal.
10. As a player, I want to **socket runes into gear and complete a runeword** as a
    deterministic long-term aspiration, so there's always a next goal.
11. As a player, I want a build that's **committed but under-geared to feel limp
    (slow, mana-starved), not to die randomly**, so greed is punished fairly.
12. As a player, I want to **allocate Str/Dex/Vit/Energy** and sometimes *not* be
    able to equip a great drop yet, so attributes are a live tradeoff.
13. As a player, I want to **respec once per act in town** so I can chase what
    dropped without being bricked by an early choice.
14. As a player, I want to **keep the gear I find in a stash** and **pick a
    starting loadout** before a run, so my time invested persists.
15. As a player, I want **Normal gear to never rival Nightmare/Hell gear**, so
    keeping gear doesn't trivialize higher difficulty.
16. As a player, I want to **reach town to bank my loot** (turning in a quest),
    and to **lose unbanked field loot if I die**, so there's push-your-luck
    tension in "one more area vs. cash out."
17. As a player, I want **standing still to get me killed** and every skill to
    have a **movement-coupled shape**, so positioning matters the whole run.
18. As a player, I want a **spammable filler + a heavier nuke** in my tree, so a
    rotation emerges instead of one button.
19. As a returning player, I want to **unlock more skills/pool entries/charm slots
    over time** (breadth), but never a permanent stat boost, so the game stays a
    skill test.
20. As the developer, I want **synergy math, resist/mastery/penetration, loot
    rolling, banking, attribute gates, and the standing-still-lethal property** to
    be unit-testable at the deterministic engine seam, so balance is data-driven.

## 5. Requirements

**Skills, synergies, mastery**
1. [P0] Restructure the Sorceress into **3 trees × 6 skills** (Fire/Cold/Lightning)
   per §6.1. Each tree has: a **spammable filler**, a **headline nuke** (short
   built-in cooldown), 1–2 **synergy partners**, a **Mastery** (passive), and a
   **one-point utility**.
2. [P0] Implement the **synergy formula** (§6.2): a skill's damage scales with
   **hard points in named same-tree siblings only**; cross-tree = 0; a fully-fed
   capstone ≈ **3×** unsupported *(tuning target, bot-verified)*.
3. [P0] **Gear `+skills` raises a skill's *level*** (its base damage/radius/count)
   **but contributes 0 to the synergy bracket.** Mastery scales on **hard points
   only** too.
4. [P0] Delete the current global `masteryBonus` (flat +2/point to all spells,
   summed across masteries) — it rewards spreading.
5. [P0] **Skill tooltips** show live synergy contribution and flag SCALES-to-max
   vs FLAT/one-point, so depth is legible.

**Damage types, resistances, difficulty**
6. [P0] Every damage instance carries an **element** (fire/cold/lightning/physical).
   Enemies carry `resFire/resCold/resLightning`. Damage taken =
   `dmg × (1 − effRes)` where `effRes = clamp(res − penetration, floor, 0.95)`;
   `res ≥ 1.0` = **immune** (element deals ~0; not breakable by ordinary
   penetration).
7. [P0] **Mastery** = multiplicative `+% element damage` (per hard point).
   **Penetration** (`−enemy resist`) comes from **gear affixes and a "-resist"
   utility**, never from Mastery — so beating a resistant (not immune) pack is a
   gear problem and beating an *immune* pack requires a **secondary element**.
8. [P0] **Difficulty tiers** raise base resistances and, on **Hell**, grant some
   packs a single-element **immunity**; scaling is resist/immunity/density-driven,
   **not** flat HP-sponge inflation. Telegraph an act boss's element at the town
   hub so the player can draft a counter.

**Loot & itemization**
9. [P0] **4 rarities** (Common/Magic/Rare/Unique) where each up widens the roll
   space and a Common can never match a Unique (§6.5).
10. [P0] **Item tier** = difficulty it dropped in (Normal/NM/Hell) gates affix
    brackets and unique/rune availability, so **Normal gear can never rival NM,
    nor NM rival Hell**.
11. [P0] Affix pools include **elemental / +to-specific-skill / FCR / FHR / +stat /
    resist / life / mana** affixes, some **build-restricted or "wrong for you,"** so
    most drops are sidegrades/junk for the current build. Tune to **~10–15% genuine
    upgrades** *(telemetry line: "loot too generous" if higher)*.
12. [P0] **No auto-equip / no auto-equip-into-slot.** Loot auto-*pickups* to the
    run inventory; equipping/salvaging happens in **town** with instant compare.
    **One-key salvage** → craft/reroll currency.
13. [P0] **Uniques** are fixed, build-defining items; **2–3 per build path are
    "enablers"** (e.g. an orb: +2 Fire skills, +20% FCR) that make a build spike.
14. [P1] **Sockets + runes + runewords**: bases can roll sockets; runes drop
    (tier-gated); inserting a specific rune sequence into a specific base type
    yields a fixed **runeword** — the deterministic aspiration ladder.
15. [P1] **Loot is smart-weighted toward the committed build** so the enabler *can*
    arrive — tension is "will the run give me what I need," never "RNG bricked me."

**Attributes**
16. [P0] **Str/Dex/Vit/Energy** with **N points/level** *(tuning target ~5)*; Str/Dex
    **gate equipping** gear (requirements), Vit → life, Energy → mana. A greedy
    all-Energy caster can't equip a great Str/Dex armor until they invest.
17. [P0] Equipping an item checks its **Str/Dex/level requirements**; unmet = can't
    equip (shown, not silently ignored).

**Meta, stash, town, run structure**
18. [P0] **Character resets every run**: level 1, no skill/attribute points spent.
    You farm the build fresh each run.
19. [P0] **Persistent stash** (bounded size) holds gear across runs; **before a
    run you pick a starting loadout** from the stash.
20. [P0] **Town checkpoint loop**: an act = a sequence of **quests**; clearing a
    quest's objective returns you to **town** to **turn in the quest** (reward +
    act progress), **stash** run-inventory loot, **equip/salvage/socket**, **respec**,
    and portal onward. Field loot is **unbanked/at-risk** until town.
21. [P0] **Death** ends the run and **forfeits unbanked (this-segment) loot**;
    already-stashed gear is safe. Character progress (level/skills/attrs) is lost.
22. [P0] **One free full respec** (skills + attributes) **per act** in town; a rare
    farmable **token** grants extra.
23. [P1] **Breadth unlocks** carry between runs (skills/pool/charm slots/highest
    tier reached) — **never raw stat power**.
24. [P0] **Difficulty ladder**: clear Act 1 Normal → unlock Nightmare → Hell.

**Moment-to-moment**
25. [P0] Keep the one-stick loop (movement only; skills auto-fire on cooldown; Mana
    gates spam) **but make standing still lethal**: continuous omnidirectional
    spawns, rising density, and **contact/enclosure damage** so turtling can't
    out-DPS the swarm. Explicitly playtest turtle builds (orbital + lifesteal +
    armor) and verify a stationary hero dies.
26. [P0] Every skill has a **distinct movement-coupled fire geometry** (nova ring,
    homing seeker, piercing cone/line, ground zone). **Audit that no build becomes
    a 360° passive nuke.**
27. [P1] Headline nukes have a **short built-in cooldown** paired with a spammable
    same-tree filler, so a rotation emerges within a tree.
28. [P1] All item **reading/equipping happens in the calm window** (town / level-up),
    never mid-swarm.

## 6. Implementation Decisions

Keep the current architecture: pure deterministic **`engine/*.js`** (no DOM,
seeded `rng.js`) behind a `getState()`-style API, driven by the canvas rAF UI in
`ui/main.js`, with a **headless movement autopilot** for tests/balance. Content
lives data-driven in `engine/content.js`; loot in `engine/loot.js`; run/meta
orchestration in `engine/game.js`; the real-time sim in `engine/arena.js`; skill
math in `engine/combat.js` (`skillEffect`). The redesign extends these, not a
rewrite.

### 6.1 Sorceress trees (3 × 6)

Each skill declares: `tab` (fire/cold/light), `role`
(filler|nuke|synergy|mastery|utility), `element`, `geometry`
(seeker|projectile|nova|cone|ground|self), `cost`, base damage/level curve, a
built-in `cooldown`, and a **`synergies` map** `{siblingSkillId: pctPerHardPoint}`.

- **FIRE** — *Fire Bolt* (filler, fast seeker) · *Fire Ball* (nuke, AoE burst) ·
  *Meteor* (synergy nuke, delayed ground zone) · *Inferno* (synergy, short cone) ·
  *Fire Mastery* (mastery, ×% fire) · *Warmth* (utility, +mana regen).
  Fire Ball synergized by Fire Bolt + Meteor + Inferno.
- **COLD** — *Ice Bolt* (filler seeker, applies Chill/slow) · *Glacial Spike*
  (nuke, AoE that Freezes) · *Blizzard* (synergy nuke, ground zone) · *Frost Nova*
  (synergy/utility, nova ring) · *Cold Mastery* (mastery, ×% cold) · *Frozen Armor*
  (utility, defensive absorb).
- **LIGHTNING** — *Charged Bolt* (filler, bolt spray) · *Nova* (nuke, expanding
  ring) · *Chain Lightning* (synergy nuke, arcs) · *Static Field* (synergy/utility,
  %-current-HP softener in radius) · *Lightning Mastery* (mastery, ×% lightning) ·
  *Energy Shield* (utility, damage drains Mana instead of Life).

Prerequisites **double as synergies** so the unlock tax is never wasted — the
natural leveling path is the optimal endgame path. Point budget for a full Act-1
run is tuned so **~one tree's core + synergies + mastery is maxable** and nothing
else *(tuning target)*.

### 6.2 Synergy & damage formula

```
skillLevel   = hardPoints[id] + gearPlusSkills          // gear raises LEVEL only
base         = damageCurve(id, skillLevel)              // grows with level (hard+gear)
synergyMult  = 1 + Σ_over_sameTreeSiblings( synergies[id][sib] × hardPoints[sib] )   // HARD points only
masteryMult  = 1 + masteryPctPerPoint × hardPoints[treeMastery]                      // multiplicative, hard only
hit          = base × synergyMult × masteryMult
```

Tune `synergies` and `masteryPctPerPoint` so a fully-fed, mastery-maxed capstone
is **≈3×** a 1-point unsupported capstone at the same character level *(bot-verified;
see §7)*. `skillEffect` in `combat.js` is rewritten to this; the old
`masteryBonus` is deleted.

### 6.3 Elements, resistances, penetration, mastery

Damage instances carry `element`. Enemies carry per-element resist and (Hell) an
optional `immune: 'fire'|'cold'|'lightning'`. `effRes = clamp(res − penetration,
−maxAbsorbFloor, 0.95)`; immune → element deals ~0. `penetration` sums from gear
`-resist` affixes and the `Static Field`/`-resist` utility, **not** from Mastery.

### 6.4 Attributes

`Str/Dex/Vit/Energy`; `~5` points/level *(tuning)*. Derived: `Vit → maxLife`,
`Energy → maxMana` (+ regen contribution), `Str/Dex → equip requirements` (and a
small physical/block contribution). `equipFromStash(item)` refuses if
`str<req.str || dex<req.dex || level<req.level` with a visible reason.

### 6.5 Loot model

`rollItem(rng, {tier, magicFind, buildProfile})` returns
`{ base, slot, rarity, itemTier, affixes[], sockets, requirements, uniqueId?,
runeword? }`. Rarity weights favor Common/Magic; `itemTier` (from the difficulty
that dropped it) caps affix brackets and unique/rune availability so
**Normal < NM < Hell** is guaranteed. Affix pools include element/+skill/FCR/FHR/
+stat/resist/life/mana, tagged by build-fit; ~10–15% of drops should be a genuine
upgrade for the current `buildProfile` *(tuning target)*. **Uniques** are fixed
`content.js` entries (2–3 "enabler" uniques per build path). **Runewords**: a base
with the right sockets + a specific rune sequence resolves to a fixed set of mods.

### 6.6 Town / checkpoint loop & run structure

Run state gains `phase: 'town' | 'field' | ...`, `runInventory[]` (unbanked),
`stash[]` (persistent, size-capped, in `localStorage`), `quests[]`, `act`,
`respecUsedThisAct`. An **act = ordered quests**; each quest = a field survival
segment with an objective (its super-unique gate). Clearing → **town**: quest
turn-in (reward + progress), **bank** `runInventory → stash`, equip/salvage/
socket/respec, portal to next quest. **Death** discards `runInventory` and the
run's character progress; `stash` persists. Meta (`localStorage`): stash,
unlocked skills/pool/charms, highest tier — **no raw power**.

### 6.7 Moment-to-moment

Spawn director sustains omnidirectional pressure and **enclosure damage** so a
stationary hero is overwhelmed regardless of clear (bot test: a still hero dies;
a moving one survives far longer). Each skill's `geometry` couples fire to
position; a build audit test asserts no single skill covers a full 360° kill zone
indefinitely. Nukes carry a short cooldown; fillers are spammable.

### 6.8 Balance harness

Extend the existing headless autopilot + `scratchpad/sim.mjs` to report, per
class/tier: win rate, end level, **movement %**, **damage-taken ratio**, **fed-vs-
unsupported capstone damage**, **% of drops that were upgrades**, and
resist/immunity encounters — the data lines that catch every failure this PRD
targets.

### 6.9 What carries between runs (the anti-flatten guarantee)

Gear carries (tier-capped) + breadth unlocks. **Nothing** that raises raw stats
persists; every run starts level 1 with 0 spent points. Because loot power is
gated by `itemTier`, a Normal stash is appropriate for Normal and under-geared for
NM — the curve stays honest.

## 7. Testing Decisions

- **Seam(s):** the **existing deterministic engine seam** — `bloodrune/tests/*.test.js`
  run with `node --test`, driving `engine/*.js` via seeded `rng.js` and the
  headless movement autopilot; the canvas UI via the Playwright `tests/smoke.mjs`.
  Prior art: `arena.test.js` (deterministic outcomes, movement bounds, nova, skill
  toggle), `run.test.js` (survival run, loot pipeline, mana persistence), and the
  artifact smoke. **No new seam is introduced.**
- **What a good test proves (engine seam):**
  - **Synergy:** a capstone's damage with a fed synergy web + maxed mastery is
    ≈3× the same capstone at 1 point / no siblings; **gear +skills changes base
    damage but NOT the synergy bracket**; cross-tree points add 0.
  - **Resist/mastery/penetration:** a fire hit into 50% fire-resist takes half;
    into an immune pack deals ~0; a `-resist` source restores damage on a
    *resistant* (not immune) pack; Mastery multiplies but never breaks immunity.
  - **Attributes:** equipping an item over Str/Dex/level requirement is refused;
    within requirement, allowed; Vit/Energy change max life/mana.
  - **Loot:** across many seeds at a fixed `buildProfile`, the **fraction of drops
    that are upgrades sits in the target band**; `itemTier` caps affix brackets so
    a Normal drop cannot exceed an NM drop; a runeword resolves deterministically.
  - **Town banking:** loot in `runInventory` moves to `stash` only on reaching
    town; simulating death in the field discards `runInventory` but preserves
    `stash`.
  - **Standing-still-lethal:** a zero-input hero dies materially faster than an
    autopilot-moving hero of the same build (regression against turtle viability).
  - **Determinism:** same seed + same inputs → identical outcome (existing
    invariant preserved).
- **UI smoke:** the built single-file artifact loads and runs a full autopilot run
  (field → town → field → boss) with **zero console errors**.

*(No tax data, financials, or client PII — Bloodrune is an isolated game folder,
per CLAUDE.md's hard boundary that game work stays out of the PII/practice-ops
code.)*

## 8. Success Metrics

- **Commitment is dominant:** a focused one-tree build out-damages a three-tree
  spread of equal total points by **≥2.5×** on its capstone *(bot)*.
- **Loot is a hunt:** **≤15%** of drops are upgrades for the current build at a
  representative mid-run gear level *(telemetry/bot)*.
- **Greed is punished, not lethal:** a committed-but-unenabled build shows clearly
  slower clears / higher mana-starvation but **death is caused by damage taken,
  not by a single unavoidable spike** *(telemetry: no >50%-max-life single hits in
  normal play)*.
- **Difficulty is a build check:** Hell runs record **immunity encounters** that
  force a secondary element; no build clears Hell mono-element *(bot)*.
- **Movement matters:** median **movement % > 60%** in winning runs; a stationary
  build cannot clear Act 1 *(telemetry/bot)*.
- **Gear doesn't flatten:** a Normal-geared character entering NM shows a measured
  power deficit vs NM-geared *(bot)*.
- **Stability:** all engine tests pass; artifact smoke = 0 console errors.

## 9. Milestones / Rollout

- **M1 — Synergy core (the headline fix):** rewrite `skillEffect` to the synergy
  formula + hard-points-only rule + delete `masteryBonus`; restructure the three
  Sorceress trees (§6.1) with synergy maps + tooltips. Tests for §7 synergy.
- **M2 — Elements & difficulty:** elements on damage/enemies, resistances,
  Mastery-as-×%, penetration, Hell immunities, tiered scaling.
- **M3 — Loot rework:** 4 rarities + itemTier gating + build-fit affixes; kill
  auto-equip; town equip/compare/salvage; ~10–15% upgrade tuning.
- **M4 — Attributes + requirements:** Str/Dex/Vit/Energy economy + equip gates.
- **M5 — Town loop, stash, starting loadout, respec, at-risk banking.**
- **M6 — Sockets/runes/runewords + enabler uniques (aspiration ladder).**
- **M7 — Moment-to-moment pass:** standing-still-lethal, per-skill geometry audit,
  nuke/filler rotation; full balance-bot tuning + artifact smoke.

## 10. Risks & Open Questions

- **Risk — scope:** this is a large redesign; M1–M2 are the load-bearing "feels
  like D2" fixes and should be validated (bot + a hosted playtest) before M3+.
- **Risk — balance surface:** synergy + mastery + resist + gear tiers multiply
  into a big tuning space; the balance harness (§6.8) is the mitigation — tune
  from data, not vibes.
- **Risk — town friction:** returning to town between quests could feel slow;
  keep town a fast, single-screen calm window, not a hub to wander.
- **Open question (needs your decision, non-blocking):** exact **run length** feel
  for Act 1 with the town loop (how many quests, ~how many minutes) — will be
  proposed from the bot + your playtest, not guessed here.
- **Open question (non-blocking):** stash **size cap** number — start at a D2-ish
  bounded grid and tune.

## 11. Done Criteria

- [ ] Sorceress = 3 trees × 6 with a working synergy web; tooltips show live
      synergy contribution.
- [ ] `skillEffect` uses the synergy formula; gear +skills = 0 synergy;
      `masteryBonus` deleted; committing ≥2.5× a spread (bot).
- [ ] Elements + resistances + Hell immunities + ×% Masteries + gear penetration;
      no mono-element Hell clear.
- [ ] 4 rarities + itemTier gating; ~10–15% upgrade rate; no auto-equip; town
      equip/compare + one-key salvage; enabler uniques; sockets/runes/runewords.
- [ ] Str/Dex/Vit/Energy + equip requirement gates.
- [ ] Persistent tier-capped stash + starting-loadout picker; character resets per
      run; town-checkpoint banking with at-risk field loot; per-act respec.
- [ ] Standing-still-lethal + per-skill geometry audit pass.
- [ ] Engine tests added/passing at the seam; artifact smoke 0 errors.
- [ ] Verified by a real hosted playtest run (field → town → boss), not just tests.
- [ ] `docs/DESIGN.md` + `PLAN.md` updated (LOG items in §12).

## 12. Running-log (PLAN.md) items

- **Decision reversed:** attributes are **in** (Str/Dex/Vit/Energy) — supersedes the
  earlier "skip attributes, let level carry it."
- **Principle:** *meta carries tier-capped gear + breadth, never raw power.*
- **Roadmap:** Acts 2–5 + the full ~45–60 min five-act run; other classes to
  parity. v1 = **Act 1 + Sorceress** vertical slice.
- **Principle:** *synergy is the damage (hard points only); committing to one tree
  is mathematically dominant; loot is mostly not an upgrade.*
