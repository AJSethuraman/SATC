# Bloodrune

A dark-fantasy **roguelite deckbuilding card-battler** — *Slay the Spire's* turn
engine, but your deck **is** a *Diablo 2* character. You loot gear and runewords,
slot them onto a hero body, and your equipment grants your cards and summons.
Gothic, bloody, loot-hungry; D2, not D3/D4.

> **Status: design phase.** The spec is written; the build hasn't started. See
> the PRD before writing code.

## 📜 Spec

- **[docs/prd-bloodrune.md](docs/prd-bloodrune.md)** — the full PRD (design,
  requirements, testing seams, milestones, roadmap). Build from this.

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
