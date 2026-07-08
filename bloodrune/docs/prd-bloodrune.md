# PRD: Bloodrune

**Status:** Draft · M1 + M1.5 built · **Owner:** iamtrispec@gmail.com · **Last updated:** 2026-07-08

> A dark-fantasy roguelite deckbuilding **card-battler**: *Slay the Spire's* turn
> engine, but your deck **is** a *Diablo 2* character — you loot gear and
> runewords, slot them onto a hero body, and your equipment grants your cards and
> summons. Gothic, bloody, loot-hungry; D2, not D3/D4. Lives in its own top-level
> `bloodrune/` folder, fully self-contained (no network, no PII, nothing shared
> with the SATC practice-ops code).

---

## 1. Problem

This is a **passion game project**, not practice-ops software — but it lands in
this monorepo as its own isolated top-level folder (like the existing `game/`
browser demo), so it must respect the repo's hard boundary: **zero contact with
client PII / tax code, no network, self-contained.**

The creative problem: the owner wants a roguelite deckbuilder that is *literally
Diablo 2* — an equippable character body, affix-driven loot, sockets and
runewords — fused with Slay-the-Spire card combat, and made a real **battler**
(units on a board vs. monster packs), not a lone-hero damage-race. The hard part,
and the reason it needs a real spec rather than a one-file toy, is that three
deep systems (card combat, D2 itemization, an AI opponent over lanes) have to
interlock *and be verifiable* — the loot odds, combat resolution, and runeword
rules are correctness-critical the same way invoice/tax math is elsewhere in this
repo, and "the AI feels dumb/random" is the classic failure mode for a battler.

## 2. Solution

**Bloodrune** is a browser game where each **run** you pick one of three classes
(Necromancer, Barbarian, Sorceress), descend a branching one-act map, and fight
monster packs across **3 lanes** using a turn-based, mana-driven card hand. Your
**deck is your gear**: weapons and skill items add active cards, armor/rings/amulet
add passives, and **runewords** grant signature cards *and* build-bending
keystones. Monsters **telegraph their intent** so the AI reads as fair and smart.
You **level up** mid-run to pick skills and allocate attributes, and you **loot**
your way up a full D2 rarity ladder with random affixes, sockets, runes, and
runewords. **Permadeath** ends a run, but a **growing unlock pool** and a
**Normal → Nightmare → Hell** difficulty ladder persist so you farm across runs
for better drops — Diablo's long-tail loot chase inside a true roguelite.

Built as a **dependency-free, zero-build vanilla-JS ES-module project** with a
strict split between a **pure `engine/`** (all rules/math/RNG, no DOM — the
testing seam) and a **`ui/`** render layer, so the correctness-critical systems
get headless `node --test` coverage.

## 3. Goals & Non-Goals

**Goals** — what success looks like:
- A **complete, winnable single run** end-to-end: class select → branching map →
  lane combat → loot/equip → level-up → town → boss, with permadeath.
- **Itemization is the star:** full rarity ladder, random affixes, sockets +
  runes + **runewords** (the signature hook) all present in v1.
- **The battler feels like a battler:** 3 lanes, persistent + timed units,
  telegraphed monsters, and an AI that reads as intentional.
- **The throughput-vs-value class axis is legible:** Necromancer (breadth),
  Barbarian (focus), Sorceress (glass-cannon flex) each play distinctly.
- **The correctness-critical engine is tested headlessly** (`node --test`):
  seeded loot distributions, deterministic combat, runeword-recipe validation,
  seeded AI decisions.
- **Self-contained & buildable with zero build step**: `python -m http.server`
  and play; `localStorage` saves; procedural art, no external assets.

**Non-Goals / Out of scope** (v1 — prevents ballooning):
- **Multiplayer / PvP** of any kind — it is single-player PvE.
- **Real sprite art or produced audio** — procedural visuals + glyphs only;
  optional light procedural SFX at most.
- **More than one Act** — v1 is Act I only (Acts 2+ are roadmap).
- **The D2 "unidentified item + Identify-scroll" mechanic** — Gambling is the v1
  home for the unidentified-item thrill; ID-scrolls are deferred.
- **Deep stash / persistent-character progression** — v1 persistence is the
  unlock pool + difficulty ladder only (deeper persistence is roadmap).
- **Monetization, accounts, cloud saves, telemetry.**
- **Any network calls** — nothing leaves the browser.
- **Any contact with SATC PII / tax / financial code, configs, or data.**

## 4. User Stories

1. As a player, I want to **choose one of three classes** at the start of a run,
   so that I can commit to a distinct playstyle (wide summoner / focused bruiser /
   fragile caster).
2. As a player, I want to **draw a hand of cards and spend Mana** each turn, so
   that combat has the familiar, readable Slay-the-Spire rhythm.
3. As a player, I want to **play attack, defense, and summon cards into 3 lanes**,
   so that positioning and board state matter.
4. As a player, I want **summoned units to persist on the board** (some permanent,
   some timed), so that I build up a battle line rather than casting one-shot
   effects.
5. As a player, I want **monsters to telegraph their intent** (attack for X /
   advance / cast), so that I can plan my turn and the AI feels fair.
6. As a player, I want **an undefended lane to damage my Hero directly**, so that
   lane coverage is a real, tense decision.
7. As a player, I want **my run to end when my Hero's Life hits 0**, so that the
   roguelite stakes are real.
8. As a **Necromancer**, I want **cheap, expendable summons that fill many lanes**,
   so that I win through throughput and board coverage.
9. As a **Barbarian**, I want **one lane of brutal single-target power with overkill
   that spills over, higher Magic Find and gold per kill**, so that focusing pays
   me in loot quality and burst instead of coverage.
10. As a **Sorceress**, I want **burst/AoE that can reach any lane while being
    fragile**, so that I play a high-risk flex role.
11. As a player, I want to **gain XP and level up mid-run**, so that my character
    grows stronger as I descend.
12. As a player, on level-up I want to **pick a skill from my class tree** (which
    adds or upgrades a card), so that I shape my build through my deck.
13. As a player, on level-up I want to **allocate a few attribute points**
    (Str/Dex/Vit/Energy), so that my stats and gear eligibility are my choice.
14. As a player, I want **Str/Dex to gate gear requirements, Vit to raise Life,
    Energy to raise Mana**, so that attributes are meaningful, D2-style tradeoffs.
15. As a player, I want a **limited respec**, so that an early misallocation
    doesn't brick my run.
16. As a player, I want **loot to drop across a full rarity ladder** (Normal →
    Magic → Rare → Set → Unique), so that every drop carries the Diablo thrill.
17. As a player, I want **items to roll random affixes gated by item level**, so
    that "the affixes are the content" and no two drops are identical.
18. As a player, I want a **Magic Find stat that tilts rarity rolls**, so that
    build choices (esp. Barbarian) change my loot outcomes.
19. As a player, I want **gear to grant cards and passives by slot** (weapons/skill
    items → active cards; armor/rings/amulet → passives), so that my equipment
    literally builds my deck.
20. As a player, I want to **socket items and combine runes into named runewords**,
    so that I can chase build-defining powers.
21. As a player, I want **runewords to grant both signature cards and keystone
    passives**, so that runeword hunting has two flavors of payoff.
22. As a player, I want to **navigate a branching map of ~12–15 nodes**, so that I
    choose my own path of risk and reward.
23. As a player, I want **node types** — Combat, Elite, Shrine, Town, Boss — so
    that a run has texture and pacing.
24. As a player, I want **Elites to roll 1–2 monster affixes** (Extra Fast, Fire
    Enchanted, Mana Burn, Teleporter, Waller, …), so that elite fights are varied
    and threatening — the mirror of my gear affixes.
25. As a player, I want a **Town** with a Vendor (buy/sell/repair), **Gambling**
    (spend gold on unidentified-rarity items), and a Healer, so that I have
    between-fight economy decisions with full D2 flavor.
26. As a player, I want **monsters to drop gold and belt-slotted potions I can pop
    in combat**, so that resource management spans the run.
27. As a player, I want a **boss at the end of the Act**, so that a run has a
    climax.
28. As a player, I want **permadeath to reset the run** but a **growing unlock
    pool** to persist, so that failure still advances my long-term collection.
29. As a player, I want a **Normal → Nightmare → Hell ladder** unlocked by winning,
    so that I can farm the same act at higher stakes for better loot.
30. As a player, I want to **share/replay a run via a seed**, so that runs are
    reproducible.
31. As the owner/developer, I want the **engine logic separated from rendering and
    covered by headless tests**, so that loot odds, combat, and runeword rules are
    provably correct, not guessed.
32. As the owner/developer, I want the game to **run with no build step and no
    dependencies**, so that it's trivial to launch and grow.

## 5. Requirements

*Priority: [P0]=must for v1, [P1]=should, [P2]=nice-to-have.*

**Combat**
1. [P0] Turn-based combat over **exactly 3 lanes**; player turn = draw to a hand
   of ~5, spend **Mana** (base ~3/turn, modifiable by gear/runewords/Energy),
   play cards, end turn; then monsters resolve.
2. [P0] Cards have types: **Attack**, **Defense/Skill**, **Summon**. Summon cards
   place a **unit** into a chosen lane.
3. [P0] **Units persist** on the board across turns and auto-resolve combat in
   their lane; **timed units** expire after N turns; permanent units remain until
   killed.
4. [P0] Monsters **telegraph intent** each turn (e.g. "⚔️ 6", "👣 advance",
   "☠️ cast"); the displayed intent is what resolves (barring player interference).
5. [P0] Lane resolution: friendly and hostile occupants of a lane trade damage;
   surviving monsters in an **undefended lane damage the Hero's Life**.
6. [P0] **Hero Life reaching 0 ends the run** (permadeath).
7. [P1] **Blood-magic** (pay Life instead of/in addition to Mana) exists as a
   *findable build* via specific cards/gear/runewords — not the base resource.
8. [P1] **Overkill spill** (Barbarian identity): damage exceeding a target's
   remaining Life carries to the next enemy in-lane or an adjacent lane per rules.

**Classes & progression**
9. [P0] Three classes — **Necromancer, Barbarian, Sorceress** — each with a
   distinct base deck/gear and a curated **~6–8 skill tree**; skills are cards.
10. [P0] Classes sit on a **throughput-vs-value axis**: breadth (coverage,
    quantity, safety-in-numbers) vs. focus (per-kill value, Magic Find, burst,
    flex-on-demand). See §6 for the concrete knobs.
11. [P0] **XP → level-up** mid-run; on level-up the player makes **two manual
    choices**: (a) pick a skill (adds/upgrades a card), (b) allocate a small pool
    of attribute points across **Str/Dex/Vit/Energy**.
12. [P0] Attribute effects: **Str/Dex gate item requirements**, **Vit = Life**,
    **Energy = Mana**.
13. [P1] **Limited respec** available (rare consumable or Town service) to
    reallocate skills/attributes.

**Itemization**
14. [P0] Equipment slots (full D2 body): **Weapon, Off-hand, Helm, Body Armor,
    Gloves, Boots, Belt, Amulet, Ring ×2**. **Belt also holds combat potions.**
15. [P0] **Gear grants deck content by slot**: weapon + skill items add **active
    cards**; armor/rings/amulet grant **passive modifiers**. Equipping/unequipping
    updates the deck live.
16. [P0] Full rarity ladder with curated pools: **Normal** (socketable) →
    **Magic** (1 prefix + 1 suffix) → **Rare** (multi-affix) → **Set** (multi-piece
    bonuses) → **Unique** (fixed, build-defining).
17. [P0] Items roll **random affixes** from a curated prefix/suffix pool drawn
    from the D2 affix families (+to Skills, resistances, FCR/IAS re-maps, leech,
    +Life/+Mana, crit — see §6 "Affix vocabulary" for the card-battler
    translation); **item level gates** which affixes can roll.
18. [P0] **Magic Find** stat biases rarity rolls upward.
19. [P0] **Sockets + ~8 runes + ~6 named runewords** with real recipes (specific
    runes, in order, in a valid base → a named runeword). Runewords grant **both**
    a signature card **and** a keystone passive (per runeword, one or both).
20. [P1] Set/Unique/runeword items are seeded into the **unlock pool** as they're
    discovered.

**Run structure & economy**
21. [P0] **One Act**: a **branching map of ~12–15 nodes** the player paths through.
22. [P0] Node types: **Combat, Elite, Shrine, Town, Boss** (boss ends the Act).
23. [P0] **Elites roll 1–2 monster affixes** from a curated pool: Extra Fast,
    Fire/Cold/Lightning Enchanted (bonus elemental + death nova), Cursed, Stone
    Skin, Mana Burn, Aura (pack buff), Teleporter (jumps lanes), Waller (blocks a
    lane).
24. [P0] **Town** services: **Vendor** (buy/sell gear+potions, repair),
    **Gambling** (spend gold on unidentified-rarity items), **Healer** (restore
    Life between fights).
25. [P0] **Gold economy**: monsters drop gold; potions are belt-slotted and used
    in combat.
26. [P0] Curated **bestiary (~8–12 monster types)** + elites + **1 Act boss**.

**Meta & platform**
27. [P0] **Permadeath** resets the run; a **growing unlock pool** persists
    (discovered items/affixes/runewords/cards/classes enter future drop tables).
28. [P0] **Normal → Nightmare → Hell** difficulty ladder, unlocked by winning;
    same act, tougher monsters, better loot.
29. [P0] **Seeded deterministic RNG** drives all randomness; a run is reproducible
    from its seed.
30. [P0] **`localStorage`** persists the unlock pool + ladder progress; **no
    network**.
31. [P0] **Zero build step**: vanilla JS ES modules served statically; procedural
    art only (no external asset files).

## 6. Implementation Decisions

**Folder & platform.** New top-level folder `bloodrune/` (kebab-case, matching
repo convention; its own README + tests). Browser game, **vanilla JavaScript ES
modules**, **no bundler / no npm dependencies**. Served over HTTP for play
(`python -m http.server`), because native ES modules do **not** load over
`file://` — the README must say "serve it, don't double-click," unlike the
single-file `game/` demo.

**The load-bearing seam — `engine/` vs `ui/`.** A hard split:
- **`engine/`** — pure JavaScript, **zero DOM / zero browser APIs**. Owns all
  rules and math: deck/hand/draw, combat resolution, lane state, unit lifecycle
  (persistent/timed), loot generation, affix rolls, rarity determination, magic
  find, socket/rune/runeword validation, monster AI decisions, XP/leveling,
  attribute effects, the seeded RNG, and save-state (de)serialization as plain
  objects. Everything here is deterministic given a seed and inputs.
- **`ui/`** — reads engine state and renders it (DOM/canvas/SVG), captures input,
  and calls engine methods. Owns no rules. Owns `localStorage` I/O (serializing
  the engine's plain-object save state).

This boundary is the single testing seam (see §7). If a rule can only be
exercised by clicking the UI, it's in the wrong layer.

**Seeded RNG.** A small deterministic PRNG (e.g. a mulberry32/xorshift-style
function seeded from a run seed) is the *only* source of randomness in `engine/`.
No `Math.random()` anywhere in `engine/`. The RNG is threaded explicitly (passed
in / held on the run state), so tests can construct a known seed and assert exact
or statistical outcomes. Run seeds are shareable strings.

**Combat model.** State per fight: 3 lanes, each holding an ordered list of
friendly units and hostile monsters; the Hero (with Life, Mana, block); the deck
(draw/hand/discard piles). Turn order: (1) start-of-turn — draw to hand size,
refill Mana, tick timed units/effects; (2) player plays cards until they end the
turn; (3) resolution — friendly units and queued attacks trade with monsters
per lane; unblocked monster damage in an undefended lane hits Hero Life; (4)
monster intents re-roll and telegraph for next turn. Monster AI is a pure
function `(laneState, monster, rng) -> Intent`; "telegraph" means the chosen
Intent is committed and displayed a turn ahead.

**Throughput-vs-value knobs (class balance axis — a durable design principle).**
Concretely tuned via: summon cost/power/count and unit durability (Necromancer:
many/cheap/weak; Barbarian: none/few but hero-centric), per-kill **Magic Find**
and **gold** multipliers (Barbarian > Necromancer), **overkill spill** rules
(Barbarian only), and lane-reach (Sorceress can target any lane; Barbarian is
lane-locked but bursty). These live as data/config in `engine/`, not hardcoded in
logic, so they're tunable.

**Itemization data model.** An item is a plain object: `{ base, slot, rarity,
itemLevel, requirements:{str,dex}, affixes:[...], sockets:[...runes],
grants:{cards:[...], mods:{...}} }`. Rarity + affix generation is a pure
pipeline: pick base → roll rarity (biased by Magic Find) → roll N affixes from
the pool eligible at `itemLevel` → compute `grants`. **Runewords** are validated
by matching an ordered rune sequence against a recipe table keyed by base type;
a valid match adds the runeword's `card` and/or `mods` keystone. Affix pools,
rarity weights, rune list, and runeword recipes are **data tables** in `engine/`.

**Affix vocabulary (D2 families → card-battler translation).** Item mods are an
additive map summed across equipped slots (`deriveStats`); the affix pool draws
from these families. Two of D2's stats are *real-time* and have no literal
meaning in a turn-based card game, so they are **deliberately re-mapped** — this
is a design decision, not an oversight:

| D2 affix | Bloodrune meaning |
|---|---|
| **+to Skills / +% skill damage** | flat/percent bonus to your cards' damage & block (`plusSkills`) — *live in M1.5* |
| **Resistances (fire/cold/lightning/poison %)** | reduce incoming *typed* damage; matters once monsters/elite-affixes deal elemental damage (M6). Present on gear before then, inert until sources exist. |
| **Faster Cast Rate (FCR)** | *re-map:* **skill cards cost less Mana** (you "cast" more per pool) |
| **Increased Attack Speed (IAS)** | *re-map:* **draw more / an extra card play** (you "swing" more per turn) |
| **Life / Mana Leech** | heal Life / regain Mana when your cards deal damage |
| **Faster Hit Recovery (FHR)** | more standing Block (`startBlock`) / recover Block mid-turn |
| **+Max Life / +Max Mana** | as written (`maxLife`, `maxMana`) — *live in M1.5* |
| **Deadly Strike / Crushing Blow** | chance to deal double / %-of-current-HP damage |
| **Magic Find** | biases loot rarity rolls upward (see §5 R18) |

Resists, FCR, IAS, leech, and crit land in the **M3/M4** slices (issue #94/#95);
M1.5 wires `maxLife`, `maxMana`, `startBlock`, and `plusSkills` as the first
members of this same additive-mod system, so the rest drop in without a refactor.

**Map generation.** A seeded branching DAG of ~12–15 nodes with typed nodes and a
Boss terminal; generation is a pure function of the seed + difficulty tier.

**Save state.** The engine exposes `serialize() -> plainObject` and
`load(plainObject)`; the UI persists it to `localStorage` under a single
namespaced key. Persisted across runs: unlock pool, ladder progress, settings.
Not persisted across a death: the in-progress run (that's the roguelite reset).

**Art.** Dark gothic palette (blacks, blood reds, bone), procedural via CSS +
canvas/SVG, unicode/emoji glyphs (⚔️ 💀 🩸 🔥) for icons. No external image/audio
files. Optional minimal procedural WebAudio SFX ([P2]).

## 7. Testing Decisions

- **Seam(s):** the **pure `engine/` module boundary** is the primary (and ideally
  only) seam, exercised **headlessly with Node's built-in test runner
  (`node --test`)** — no build, no test dependencies. There is no existing JS test
  tooling in the repo (sibling projects use `pytest`); this introduces `node
  --test` as the JS analogue, matching the repo's "correctness-critical math gets
  tests" culture (cf. invoice/withholding math). The **`ui/`** layer is verified
  by a **headless Playwright/Chromium smoke test** (Chromium is preinstalled in
  this environment), not unit tests.
- **What a good test proves:**
  - **Loot / affix distributions** — over many seeded rolls, rarity frequencies
    fall within tolerance of configured weights; Magic Find shifts them upward;
    affixes never roll above what `itemLevel` permits. *(seeded, statistical)*
  - **Combat resolution** — given a fixed seed and board, a turn resolves to an
    exact expected end-state (damage, deaths, Hero Life, undefended-lane bleed).
    *(seeded, exact)*
  - **Runeword recipes** — the correct ordered rune sequence in a valid base
    yields the runeword; wrong order / wrong base / partial sequence does not.
    *(exact)*
  - **Monster AI** — given a fixed seed and lane state, the chosen Intent is
    deterministic and legal. *(seeded, deterministic)*
  - **UI smoke (Playwright):** page loads with **zero console errors**; a run
    starts; a combat is played to a win; loot drops, is equipped, and the deck
    visibly changes.

> **PII / sensitive data:** N/A by construction. Bloodrune touches **no** client
> PII, tax, or financial data, makes **no** network calls, and shares no code or
> config with `satc_system/` or `invoice-generator/`. Its only persistence is
> game state in `localStorage`. This isolation is itself a requirement (§3
> Non-Goals, §5.30).

## 8. Success Metrics

- A fresh player can complete a **full winnable run** (class select → map → boss)
  on Normal without reading code.
- **Death reliably ends the run**; the unlock pool grows and is visible next run.
- **All three classes are mechanically distinct** and win via different means
  (coverage vs. per-kill value vs. flex burst).
- **Runewords are attainable and impactful** within a single run.
- **`node --test` is green**, including the statistical loot test and exact
  combat/runeword/AI tests; the **Playwright smoke passes with zero console
  errors**.
- Launch-to-play is **one command** (`python -m http.server`) with **no install**.

## 9. Milestones / Rollout

- **M1 (MVP tracer bullet):** **one class (Barbarian)** end-to-end — one-lane (or
  3-lane with 1 active) combat with Mana, telegraphed intents, and Hero Life; a
  couple of gear drops that grant cards; win/lose states. Proves the
  `engine/`↔`ui/` split, seeded RNG, and the first `node --test`.
- **M2:** the **branching map** (typed nodes, seeded) + basic **Town** (Vendor,
  Healer) + gold economy + belt potions.
- **M3:** the **rarity ladder + random affixes + Magic Find** across the full
  slot set; equip/unequip updates the deck.
- **M4:** **sockets + runes + runewords** (the signature hook).
- **M5:** the **Necromancer & Sorceress** (summons, timed units, lane-reach) and
  the throughput-vs-value knobs.
- **M6:** **Elites + monster affixes**, the **Act boss**, and **Gambling**.
- **M7:** **permadeath meta** — unlock pool + **Normal → Nightmare → Hell** ladder.

## 10. Risks & Open Questions

- **Risk — AI feel.** A battler lives or dies on the opponent feeling
  intentional. Mitigation: committed, telegraphed intents + lanes (tractable AI)
  + seeded AI tests; if it still feels flat, add per-monster behavior scripts.
- **Risk — balance of the throughput-vs-value axis.** Easy to make one class
  strictly better. Mitigation: knobs live as tunable data, and the class-distinct
  win metric (§8) is an explicit gate.
- **Risk — scope.** Three deep systems in v1. Mitigation: the M1–M7 tracer-bullet
  slicing; each milestone is independently playable.
- **Risk — content volume masquerading as engineering.** Affix/rune/monster
  tables are content; keep them small and curated for v1 (the numbers in §5).
- **Open question (needs your decision, non-blocking):** none blocking the build.
  Deferred *by choice* to the roadmap (see PLAN.md): deeper persistence / a stash;
  Acts 2+; the ID-scroll mechanic; an optional open-license pixel-art pass. These
  are logged, not open.

## 11. Done Criteria

- [ ] All **[P0]** requirements and their user stories are met; a **full run on
      Normal is winnable** and **death ends the run**.
- [ ] All three classes are implemented and mechanically distinct.
- [ ] Itemization is complete for v1: rarity ladder + affixes + Magic Find +
      sockets/runes/**runewords**, with gear granting cards/passives by slot.
- [ ] **`node --test` passes** at the `engine/` seam: seeded loot distributions
      (within tolerance), exact combat resolution, runeword-recipe validation,
      deterministic monster-AI decisions.
- [ ] **Playwright/Chromium smoke passes** with **zero console errors**, covering
      start → combat → win → loot → equip → deck-changes.
- [ ] Verified by **playing the real flow**, not just tests.
- [ ] `bloodrune/README.md` documents how to serve, play, and run tests; confirms
      self-contained / no-network / no-PII isolation.
- [ ] `[LOG]` items appended to `PLAN.md` (balance principle, deferred
      persistence, roadmap).
