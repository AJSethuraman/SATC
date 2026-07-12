# Bloodrune

A dark-fantasy **roguelite deckbuilding card-battler** — *Slay the Spire's* turn
engine, but your deck **is** a *Diablo 2* character. You loot gear and runewords,
slot them onto a hero body, and your equipment grants your cards and summons.
Gothic, bloody, loot-hungry; D2, not D3/D4.

> **Status: playable end-to-end run.** One class (Barbarian) through a full
> descent: pick **one of three directions** each step (**no backtracking**),
> fight **swarms** and **elites** (D2 monster affixes), take **randomized loot**
> (rarity + affixes + a paper-doll inventory), **level up** and choose a boon
> (build-crafting), **camp** to heal, **Flee** at a cost, and face the **act
> boss** — with **permadeath** and a **Normal → Nightmare → Hell** ladder that
> persists in `localStorage`. Combat is a real **Mana pool**, **tap-to-target**,
> telegraphed monsters, and **Accuracy** (attacker-driven miss + an Evasion hook
> for a future Amazon). Still to come: runewords, the other three classes, a
> town economy, and the deeper build-crafting/affix systems — see the PRD (§6,
> §12) and issues #92–#98.
>
> Combat is a **swarm**: you're surrounded by a **large** seeded pack
> (`engine/encounters.js`) — mostly homogeneous D2-style groups with a
> leader/support at the back (a Fallen Camp of several Fallen + a **Fallen
> Shaman** that mends allies — kill it first), sometimes a second pack dragged
> in. Everything swings each turn, so **AoE + Accuracy matter**. Hits resolve in
> two stages: **attacker Accuracy** (clumsy attackers miss — your hits *and*
> theirs; non-punitive, but stacking Accuracy on gear matters for heavy hits)
> then **defender Evasion** (0 for the Barbarian; the hook for an Amazon-style
> dodge class and evasive enemies). **Smite** (single, accurate) vs **Zeal**
> (AoE, weaker, less accurate) is the sweep-vs-delete tradeoff. Post-playtest
> design directions (Amazon, skill-tree build-crafting, class-specific effects)
> are captured in PRD §12.

## 📜 Spec

- **[docs/prd-bloodrune.md](docs/prd-bloodrune.md)** — the full PRD (design,
  requirements, testing seams, milestones, roadmap). Build from this.

## ▶️ Play it (M1)

Native ES modules don't load over `file://`, so serve it:

```bash
cd bloodrune && python3 -m http.server 8000   # then open http://localhost:8000
```

Play a card by clicking it (attacks hit the front monster; Cleave/Whirlwind hit
all). Watch each monster's telegraphed intent (⚔️ N) — that's the damage it deals
when you **End Turn**. Reduce it with Block. Kill the pack to win and loot a
weapon that rewrites your deck; drop to 0 Life and the run is over.

## ✅ Tests

```bash
node --test            # engine seam: deterministic combat + the gear->deck loot seam
node tests/smoke.mjs   # headless UI smoke (needs Playwright/Chromium): plays a
                       # fight to a win, equips loot, asserts zero console errors
```

The engine suite is pure and dependency-free. The smoke needs a browser and
skips cleanly if Playwright isn't installed.

## 🧭 What's built vs. planned

**Built (M1):** `engine/` (seeded RNG · card/combat resolution · gear→deck ·
loot) fully split from `ui/` (DOM render + input); Barbarian; one lane;
telegraphed monsters; win/loot/lose flow.

**Next slices (issued):** M2 branching map + town, M3 rarity ladder + affixes +
Magic Find, M4 sockets/runes/runewords, M5 3-lane board + summons + Necromancer
& Sorceress, M6 elites + monster affixes + boss + gambling, M7 permadeath meta +
Normal/Nightmare/Hell ladder.

## Isolation (hard rule)

Bloodrune is **fully self-contained** and shares nothing with the rest of this
monorepo: **no network calls, no client PII / tax / financial data, no shared
code or config** with `satc_system/` or `invoice-generator/`. Its only
persistence is game state in the browser's `localStorage`.

## Planned shape (from the PRD)

- **Zero build step.** Vanilla JavaScript **ES modules**, no bundler, no npm
  dependencies. Because native ES modules don't load over `file://`, **serve it**
  to play:
  ```bash
  cd bloodrune && python -m http.server 8000   # then visit http://localhost:8000
  ```
- **`engine/` ↔ `ui/` split.** A pure `engine/` (all rules, math, loot/affix
  rolls, runeword validation, monster AI, seeded RNG — **zero DOM**) separated
  from a `ui/` render layer. This boundary is the testing seam.
- **Tests via Node's built-in runner** (no dependencies):
  ```bash
  node --test        # engine unit tests (seeded loot, combat, runewords, AI)
  ```
  UI is verified by a headless Playwright/Chromium smoke test.
- **Procedural art** — dark gothic CSS/canvas/SVG + glyphs, no external assets.

## Roadmap

The milestone plan (M1 tracer bullet → full v1) and deferred/future items live in
the PRD (§9 Milestones, §10 Risks & Open Questions). v1 is **Act I, one difficulty
tier to start, three classes, full itemization including runewords.**
