# Bloodrune — Design Doc

The reference we build from, so genre-obvious requirements are on the table
*before* they show up as playtest corrections. Grounded in Diablo 2 via five
research passes (itemization, character systems, combat math, monsters/
difficulty, core-loop/feel) — citations in §6. Companion: `research-d2-skills.md`.
Living doc.

> **Status:** ✅ built · 🟡 partial · ⬜ not yet · ❓ open decision

---

## 0. PIVOT — real-time movement (current direction)

Combat moved from **turn-based rings** to **real-time movement** (a
Vampire-Survivors / Halls-of-Torment shape): you are a token in an arena and the
only control is **moving** (WASD / arrows / drag). Abilities **auto-fire on
cooldown** when Mana allows — *positioning is the skill*: kite the swarm, line up
a Cleave, back off to regen. The **progression is unchanged and load-bearing** —
same XP→levels→skill tree, same weapon-driven damage (`skillEffect`), same
to-hit/dodge math, loot (take-or-leave), super uniques, difficulty tiers
(Normal/Nightmare/Hell), permadeath, telemetry. **Our niche vs. VS/HoT: it's
*skill-tree* and *item-find* driven** (a D2 build, not just weapon-evolutions).

- **Engine:** `engine/arena.js` — deterministic fixed-step (`DT = 1/30`) sim,
  seeded rng, no DOM. Replaces `combat.js` at the moment-to-moment; keeps the
  `getState()/quaff()/flee()` contract `game.js` expects, adds `tick(input)` +
  `autoInput()` (headless movement autopilot for the balance bot/tests). Bolts
  **home** (VS-style auto-aim) so ranged classes reliably connect.
- **UI:** `ui/main.js` `renderCombat` is now a `<canvas>` rAF loop (movement
  input + auto-fire skill chips + potion belt); everything else (prep, blind map,
  reward, shop, skill tree, inventory, stats) is unchanged.
- **What didn't port:** rings / engagement cap / action points / front-rank
  screen / guardian body-block — replaced by real positioning. Guardians are now
  melee bruisers; casters kite-and-support.
- **Open tuning:** melee (Barbarian) is the weak class (must stand in the swarm)
  — the classic VS melee problem; needs survivability/lifesteal or reach love.
  Juice (bigger sprites, hit-stop, screen shake, XP-gem magnetism) is thin.

The turn-based sections below (§1–§5) are the **prior** design, kept for history.

---

## 1. Pillars (the fantasy)

1. **Diablo 2, turned tactical.** The D2 fantasy — a dark gothic crawl, a
   character *body* you gear, skills you spec into, loot that defines you —
   as combat you play. Explicitly D2, not D3/D4's feel. *(Pivot §0: now
   real-time movement, was turn-based tactical.)*
2. **Surrounded and outnumbered.** One hero ringed by a horde; tension is
   *who do I kill first* and *where do I stand*. *(Pivot §0: positioning is
   now literal — you move — not rings + an engagement cap.)*
3. **Start naked, become a god — or die.** One weapon-granted skill → scale via
   XP, the tree, and loot. Fix your build's weakness, or die to it. Permadeath.
4. **Your build is your character.** Class + tree + **weapon type** + gear = a
   distinct way to fight. Items change how you *play*, not just a number.
5. **Readable depth.** Everything telegraphed and legible. Complexity from
   systems interacting, not hidden math or twitch.

---

## 2. What's built today (snapshot)

- **Combat:** surrounded arena (inner/outer rings, front-rank screen, **engagement
  cap**), abilities (no cards) that roll damage ranges, **Mana as a regenerating
  pool**, guarded casters + breakthrough/Exposed, **reactive rezzer/healer
  casters**, summon **body-block** wall. ✅
- **Characters:** 3 classes (Barbarian/Amazon/Necromancer); **D2-style skill
  tree** (level+prereq+per-point gates, capstones, +Skills). No attributes,
  synergies, or respec. 🟡
- **Items:** **weapon damage feeds physical skills, weapon type gates them**;
  armor/jewelry roll magic/rare affixes. No sockets/runes/runewords, sets,
  uniques, or ilvl gating. 🟡
- **Monsters:** roster + 4 elite affixes + **super uniques** (Blood Raven et al.)
  + one act boss. One difficulty. 🟡
- **Loop:** 9-step branching blind map, XP→levels→points + loot, permadeath,
  minimal meta. No feel/juice, node-choice risk/reward, gold, potions, or
  meta-progression. 🟡

---

## 3. The sequenced roadmap

Ordered by impact-to-effort **and** dependency. Each wave is a coherent,
shippable increment. Source tags: `[loot] [char] [math] [mob] [loop]`.

### Wave 1 — Make it FEEL like an ARPG *(highest ROI, no engine risk)* `[loop]`
The research's loudest finding: the biggest gap isn't a system, it's **feel**.
Turn-based *helps* — time isn't scarce, so you can afford elaborate per-hit
feedback.
- **Juice + audio** on every hit / death / loot / level-up: hit-flash, screen
  shake, animated (not snapping) damage numbers, death particle burst, a
  **loot-drop "jackpot" moment**, a **pack-wipe cascade**. ⬜
- **Telegraphed enemy intent** is already partly there (attack/support/wait) —
  push it: every enemy shows its next action clearly, so a turn is a *puzzle*.

### Wave 2 — Accuracy & the defensive layers you asked for `[math][char]`
D2 stacks independent gates (hit? block? dodge? mitigate?). Adding them is what
makes builds matter — and you explicitly asked for accuracy and Amazon evade.
- **To-hit: Accuracy vs Evade.** ✅ Physical attacks roll to-hit
  (`clamp(0.75 + (acc − eva)·0.04, 0.35, 0.95)`); **spells/summons auto-hit** (the
  caster edge). Accuracy = class base + level + gear (Keen/of Precision affixes);
  enemies carry Evade (goatman/archer are nimble). Hit % shows on the attack
  button; misses narrate. Kept light — "matters, not punitive."
- **Amazon Dodge/Evade.** ✅ Incoming blows can be dodged, **scaled against the
  attacker's accuracy** (your idea, better than D2's attacker-blind roll): a
  sloppy foe is juked, a precise one connects. Amazon has high base Evade (her
  identity — it lifted her from ~7/16 to ~12/16); gear adds more (Nimble/of the
  Cat). Evade shows in the bar; dodges narrate.
- **Block as a % chance to negate** (D2's real model), alongside the current
  flat-absorb Guard — room for both (chance-block shields vs absorb-barriers). ⬜
- **Round out per-class defense:** Barb soak (have Guard/War Cry), Necro **curse**
  (Amplify — weaken enemies / your minions already tank). ⬜

### Wave 3 — Damage types + resistances *(the build-variety spine)* `[math][mob]`
Everything is physical today, so there's no "this pack resists fire, adapt."
This is the prerequisite for resistances, immunities, elemental affixes, and
elemental runes/uniques later.
- **Damage types:** Physical + Fire/Cold/Lightning/Poison + Magic; tag skills &
  enemies. Physical routes through armor/block; elements through resists. ⬜
- **Resistances:** linear % mitigation, 75% cap; **depth-scaled resist penalty**
  (your Nightmare/Hell analog in one dial). **Immunities** sparingly on back-half
  elites, always with an in-run break/bypass. Status flavor: cold=slow,
  poison=DoT, fire=on-death burn. ⬜

### Wave 4 — Elite/monster texture *(cheap, and it plays off your identity)* `[mob]`
The cheapest tactical texture in the game, and several affixes specifically
interact with your engagement-cap identity.
- **Affix-count by depth** = the whole difficulty curve (steps 1–3: 1 affix;
  4–6: 2; 7–9: 3). **This replaces Normal/Nightmare/Hell** — a single deepening
  descent, not three playthroughs. ⬜
- **Aura Enchanted** (Fanaticism = pack hits harder; Conviction = your resists
  down; Holy Freeze = you're slowed) → *kill the carrier first*. ⬜
- **On-death AoE** (Cold nova / Fire burst) → killing order & where you stand
  matter. ⬜
- **Screen-breakers** — **Teleport** and **Extra Fast** ignore/beat the
  engagement cap and hit your back line. Your signature "the cap won't save you
  this time." ⬜
- **Champion pack** tier (buffed identical pack, no leader/affix); **Cursed/
  Amplify**; **Multishot** archer; Fallen **flee** behavior. ⬜

### Wave 5 — Loot depth *(the chase)* `[loot]`
- **Depth-gated affix tiers (ilvl):** deeper drops roll higher tiers — deeper
  runs *feel* better. Reuses the affix roller. ⬜
- **Unique items** that **grant abilities / auras / +skills** (in an ability
  game, a unique that adds a *way to play* beats +damage). ⬜
- **Sockets + runes + runewords** — the top loot hook: deterministic goals amid
  RNG, and **runewords can grant a skill** (a perfect fit for weapon-type-gates-
  skills — a runeword can unlock a skill your weapon type wouldn't allow). ⬜
- **Set items** (collection/synergy meta-goal). ⬜

### Wave 6 — Progression & build-per-run depth `[char][loop]`
- **Skill synergies:** hard points in one skill boost a related one (compressed
  magnitudes so a 3–5 point cluster already *feels* specialized). Turns "spent
  points" into "a build." ⬜
- **Drafted build-per-run powers** offered at camps/elites (Hades/Death-Must-Die
  style) so runs differ by *build*, not just map RNG. ⬜
- **Node choice = risk/reward:** deeper branch = higher monster level = better
  loot + more affixes. Makes the blind map a *decision*. ⬜
- ~~Lean attributes~~ — **DECIDED: no attributes.** Level (guaranteed drip) +
  gear (spiky) carry progression; accuracy/evade/life come from class base +
  level + gear affixes, not a stat-point screen. Keeps the run lean.
- ~~Potions / between-fight resource~~ **✅ BUILT.** D2-authentic Mana economy:
  Mana **persists across the whole run** (no free refill between packs), regens
  **slowly**, topped up with a **potion belt** (Life + Mana), refilled at camps
  and found as drops. **Leveling up fully restores Life & Mana.**
- **Auto-attack + action economy ✅ BUILT.** A universal **Auto-Attack** — a
  basic weapon swing, *not* a tree skill (melee weapon hits inner, a bow the
  outer), free of Mana — is your out-of-Mana fallback. **Action points** (3/turn)
  are the shared budget: a swing, a Mana skill, *and* a potion each cost 1 AP, so
  a sip is a real tradeoff. Mana gates *which* skills; AP gates *how many* actions.
  (Sets up "attack speed = more actions" as a future gear stat.)
- **Data-driven difficulty ✅ (telemetry loop working).** Playtest data showed a
  faceroll (15:1 dealt/taken, Necro 268:1, zero deaths) — worst in the LATE game
  (geared level-13 one-shotting whole packs in 1 turn). Tuned off it: tougher/
  harder-hitting enemies, engagement cap 4→5, skeleton wall blocks only the
  single heaviest blow (was every blow), lower Amazon evade, and — the key
  late-game fix — **area-level scaling**: packs scale HP (+12%/depth) & attack
  (+7%/depth) so your rising power stays challenged (boss hand-tuned, exempt).
  Balance bot (now equips gear, so it measures real power): Barbarian 14/16,
  Amazon 10/16, Necro 15/16 — all dropping to ~20% life, ratios ~4:1 / 7:1,
  fights 4-6 turns (no more 1-turn wipes).
- **Rezzer fairness ✅.** A Shaman/Blood Raven can only raise a body while it
  still has a screen (a living inner-ring ally). Clear the whole front and the
  caster is pinned — it can't instantly re-wall itself; you earned the turn to
  strike it.
- **Space-limited inventory + Shops ✅ BUILT.** Bag capped at 12; loot drops on
  the **ground** and must be **taken** (space permitting) — **overflow is left
  behind, never auto-sold** (no reward for nothing; managing space is the
  looter's tension). DROP an item to make room; a **Shop** node sells bag items
  for gold and buys potions. Gold in the header.
- **Telemetry ✅ BUILT.** Unbiased play logging (runs, win/loss by class, skill
  usage, potions, hit rate, dmg dealt/taken, avg turns, deaths by depth) in a
  Stats screen + JSON export — so balance is data-driven, not eyeballed.
- **Between-run meta-hub** (Hades' House, *not* an in-run town) + light
  meta-progression that banks every run. ⬜
- **Mercenary** — build it as an *extension of the summon actor*: a persistent,
  gear-wearing ally that projects one party aura. ⬜

---

## 4. Design calls the research settled (worth knowing)

- ~~No Normal/Nightmare/Hell~~ **REVERSED after playtest data.** The game already
  had the tiers in the UI but they did *nothing* — a skilled player facerolled
  even "Hell." Now they're real multipliers on enemy HP/attack (Nightmare
  ×1.4/1.25, Hell ×1.85/1.5), stacked on area-level depth scaling. Normal =
  approachable, Nightmare = a genuine test, Hell = brutal endgame. Geared bot:
  Normal 9-13/16, Nightmare 0-3/16, Hell 0/16. `[mob]`
- **Your dodge idea beats D2's.** Real D2 avoidance is a flat roll that ignores
  the attacker; scaling evade against attacker accuracy (as you wanted) is a
  genuine improvement — do it your way. `[math]`
- **Don't copy D2 attributes literally.** In practice 90% of D2 builds do "min
  Str for gear, all Vit, ignore Energy." Port the *tension* (every point off
  life costs survival) with a lean 3-stat model, not four stats. `[char]`
- **Gold/vendors/town are the LOWEST-priority asks.** A persistent town clashes
  with bounded runs; D2's economy is a release valve. The roguelite-correct
  version is a between-run meta-hub. Feel > intent/choice > build-draft > loot
  depth > economy. `[loop]`
- **Runewords should grant skills**, not just stats — deterministic build
  enablement that rides your existing weapon-type-gates-skills system. `[loot]`
- **Miss = a wasted turn is harsher than in real-time D2** — soften with a ~35%
  hit floor and/or graze, so neglected accuracy is *frustrating-fixable*, not a
  dead run. `[math]`
- **Two power axes, both firing:** keep level (guaranteed drip) AND gear (spiky,
  luck-driven). Don't collapse them. `[loop]`

---

## 5. Open decisions (for us to talk through)
- **Attributes:** lean 3-stat model, or none (let level/gear carry it)? `[char]`
- **Damage types:** full 4 elements + poison + magic, or a lighter 2–3 to start? `[math]`
- **Where to start:** I recommend **Wave 1 (feel) + the accuracy/dodge half of
  Wave 2** — they're your explicit asks, highest ROI, and low risk. Then Wave 3
  (damage types) unlocks the biggest downstream depth.
- **Build-draft vs. pure skill tree:** do we want Hades-style drafted powers on
  top of the tree, or keep progression tree-only?

---

## 6. Research citations

**Itemization** — [Item Rarity (Wowhead)](https://www.wowhead.com/diablo-2/guide/item-rarity-explained) ·
[Item quality (DiabloWiki)](https://diablo2.diablowiki.net/Item_quality) ·
[Item Affixes (PD2)](https://wiki.projectdiablo2.com/wiki/Item_Affixes) ·
[Item Level (Fandom)](https://diablo.fandom.com/wiki/Item_Level) ·
[Runewords (Arreat Summit)](https://classic.battle.net/diablo2exp/items/runewords.shtml) ·
[Runeword Tier List (Maxroll)](https://maxroll.gg/d2/tierlists/runeword-tier-list) ·
[Unique Items (Maxroll)](https://maxroll.gg/d2/items/unique-items) ·
[Set Items (Maxroll)](https://maxroll.gg/d2/items/sets) ·
[Magic Find (Maxroll)](https://maxroll.gg/d2/resources/gold-magic-find)

**Character systems** — [Attributes (Fandom)](https://diablo.fandom.com/wiki/Character_Attributes) ·
[Synergies (DiabloWiki)](https://diablo2.diablowiki.net/Synergies) ·
[Skill Trees (Fandom)](https://diablo.fandom.com/wiki/Skill_Trees) ·
[Mercenary Mechanics (Maxroll)](https://maxroll.gg/d2/resources/mercenary) ·
[Breakpoints (DiabloWiki)](https://diablo2.diablowiki.net/Breakpoints)

**Combat math** — [Hit Chance Mechanics (Maxroll)](https://maxroll.gg/d2/resources/hit-chance-mechanics) ·
[Block Mechanics (Maxroll)](https://maxroll.gg/d2/resources/block-mechanics) ·
[Evade (Fandom)](https://diablo.fandom.com/wiki/Evade) ·
[Monster Immunities (Maxroll)](https://maxroll.gg/d2/resources/immunities) ·
[Resistances (Arreat Summit)](https://classic.battle.net/diablo2exp/basics/resistances.shtml) ·
[Life & Mana Mechanics (Maxroll)](https://maxroll.gg/d2/resources/life-mana-mechanics)

**Monsters & difficulty** — [Monster modifier (DiabloWiki)](https://diablo2.diablowiki.net/Monster_modifier) ·
[Monster Bonuses (Arreat Summit)](https://classic.battle.net/diablo2exp/monsters/bonus.shtml) ·
[Aura Enchanted (Fandom)](https://diablo.fandom.com/wiki/Aura_Enchanted) ·
[Elite Monsters (Maxroll)](https://maxroll.gg/d2/resources/elite-monster) ·
[Difficulty (DiabloWiki)](https://diablo2.diablowiki.net/Difficulty) ·
[Item Generation / Treasure Class (Wowhead)](https://www.wowhead.com/diablo-2/guide/item-generation-treasure-class)

**Core loop & feel** — [D2 Loot Interview (TheGamer)](https://www.thegamer.com/diablo-2-loot-interview/) ·
[Experience Mechanics (Maxroll)](https://maxroll.gg/d2/resources/experience) ·
[Potion Belt (Wowhead)](https://www.wowhead.com/diablo-2/guide/potion-belt-healing-mana-antidote-tips) ·
[Roguelite Meta-Progression (Bugnet)](https://bugnet.io/blog/how-to-design-a-roguelite-meta-progression) ·
[Slay the Spire (Wikipedia)](https://en.wikipedia.org/wiki/Slay_the_Spire) ·
[Squeezing juice (GameAnalytics)](https://www.gameanalytics.com/blog/squeezing-more-juice-out-of-your-game-design)
