# SATC Monorepo — Working Notes for Claude

This repo holds the software for **Sethuraman Accounting, Tax & Consulting (SATC)**.
It's a monorepo with a **one-folder-per-project** layout. The projects are
independent — treat each folder as its own codebase with its own stack,
conventions, and way of verifying.

**Positioning (from `PLAN.md`):** SATC is **practice-operations software for the
owner** — not a tax engine, not a TaxDome/Canopy competitor. **Drake stays the
system of record** for filed returns and computations. SATC runs the business,
collects/retains client info, and provides small services around Drake.

## Projects

| Folder | What it is | Stack | How to verify a change |
|---|---|---|---|
| `website/` | Public site — now a prospect **intake form** (hero + services + intake). Working log and decisions: **`website/INTAKE.md` — read it first.** | Single `index.html`, no build step, no framework | Serve and eyeball it: `cd website && python -m http.server 8000` (no test suite — drive a real browser) |
| `invoice-generator/` | "Invoicer" — self-hosted invoice web app (accounts, PDF, Stripe, email, JSON API) | Python / Flask + SQLAlchemy | `pytest` in `invoice-generator/tests`; run locally (`run.ps1`, `docker compose up`, or Render) |
| `satc_system/` | The SATC practice-ops app: local Flask GUI, client intake, document readers, tax line-sheets, encrypted identity vault + de-identified data mart, Drake input/reconcile seam, withholding estimator | Python (`satc` package), Flask, SQLite | `cd satc_system && PYTHONPATH=src pytest -q`; run the app (`SATC.bat` / `satc-app`, default port 5050); `satc doctor` for a readiness check |
| `cowork-plugin/` | Claude/Cowork plugin + MCP server (`mcp/satc_mcp.py`) to drive SATC's withholding API in plain language; **read-only by default** | Python MCP server + plugin manifest | Load the MCP; exercise against the local withholding API |
| `game/` | "Ashfall" — action-roguelite prototype (Diablo II itemisation in a Hades-shaped run). Unrelated to the accounting practice; lives here only because this is the working monorepo | Godot 4 / GDScript, no addons | `godot --headless --path game --script res://tests/run_tests.gd` (import once first); balance sim under `game/sim/` |

## Conventions

- **Match each project's existing style.** The website is hand-edited HTML/CSS
  with content in `website/site-config.js` (the `SATC_CONFIG` block). Invoicer
  follows a Flask module split (`app.py`, `api.py`, `models.py`, `pdf.py`,
  `email_utils.py`, `stripe_utils.py`, `config.py`). `satc_system` is a
  `src/satc/...` package; Drake-adjacent behavior stays config-driven under
  `satc_system/configs/...`.
- **New projects go in their own top-level folder** with their own README,
  dependencies, and tests — mirroring the existing ones.

## Hard constraints (do not cross without explicit sign-off)

- **Client PII is load-bearing.** Names/SSNs/EINs live in an **encrypted identity
  vault** (AES-256), split from the de-identified working data mart. Only
  masked/last-4 values belong in artifacts, logs, and workbooks — **never** real
  taxpayer PII. Validation tests fail the build if legal names / full TINs leak
  into outputs. The SATC MCP is **read-only by default**.
- **Drake stays the system of record.** SATC does not replace Drake's
  calculations or e-file; it prepares/reconciles inputs.
- **Money & tax correctness.** Invoice math, Stripe webhooks, withholding math,
  and tax line-sheet logic are correctness-critical — add/keep tests and
  double-check rather than guess. Cite sources for tax parameters.

## Deploy paths (these ship automatically — treat edits as production changes)

- `website/` → GitHub Pages via `.github/workflows/pages.yml` on push to `main`.
- `invoice-generator/` → Render via `render.yaml` (Docker + PostgreSQL, autodeploy).
- `satc_system/` desktop `SATC.exe` → built by a GitHub Actions release workflow
  on a `v*` tag (packaged build is **local-only**).

## Working with agents (the skills pipeline)

Reusable skills live in `.claude/skills/` — see `.claude/skills/README.md`. The
spine for new work is **`grill-me` → `to-prd` → `to-issues` → build**, with
`handoff`, `diagnosing-bugs`, `tdd`, `research`, `domain-modeling`,
`codebase-design`, and `triage` as supporting steps. Use `PRD_TEMPLATE.md` at the
repo root as the PRD shape.

## Git workflow

- Develop on a feature branch; commit with clear messages.
- Push and open a **draft PR** — don't push to `main` without explicit approval.
