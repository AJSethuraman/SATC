# Bloodrune

A dark-fantasy **roguelite deckbuilding card-battler** — *Slay the Spire's* turn
engine, but your deck **is** a *Diablo 2* character. You loot gear and runewords,
slot them onto a hero body, and your equipment grants your cards and summons.
Gothic, bloody, loot-hungry; D2, not D3/D4.

> **Status: M1 + M1.5 built (playable).** One class (Barbarian), one lane, a
> real **Mana pool**, **targetable** attacks (tap a monster to focus it),
> telegraphed monsters, Hero Life, and a **Diablo-style inventory** — the full
> equipment slot set with found items that grant **cards** and **passive mods**
> (+Life, +Mana, standing Block, **+to Skills**). The rest of v1 (map, town,
> full rarity ladder + affixes, runewords, the other classes, difficulty ladder)
> is issued as slices M2–M7 — see the PRD. The full **D2 affix vocabulary**
> (+skills, resists, cast/attack-speed re-maps, leech, crit) and how each
> translates to a turn-based card game is specified in the PRD (§6).
>
> Fights use **seeded pack encounters** (`engine/encounters.js`): mostly
> homogeneous D2-style packs with a leader/support at the back — e.g. a Fallen
> Camp of several Fallen plus a **Fallen Shaman** that *mends* wounded allies
> (kill it first) — with a chance to drag in a second pack for a mixed fight.

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
