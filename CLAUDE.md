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
| `client-documents/` | The document pipeline: interview → engagement → priced, merged client documents. CLI **and** browser front doors over one core | Python, Flask, YAML registries | `cd client-documents && python -m pytest -q`; `make web` for the browser front door |
| `satc-handoff/` | Brand, the ten client document templates + their FIELDS specs, the authoring contract, the run log and the open-questions list | HTML/CSS/Markdown, no build | Read `satc-handoff/START-HERE.md`; templates render in a browser |
| `docs/` | Specs and research that govern the above — including `prd-interview-and-field-registry.md`, which the interview is built to | Markdown | — |

**The repo also holds nine credit and macro analytics projects** —
`credit-review-os/`, `stock-helper/`, `fdic-peer-monitor/`,
`cfpb-mortgage-monitor/`, `edgar-crit-class-tracker/`,
`fred-credit-risk-dashboard/`, `bureau-credit-risk-dashboard/`,
`macro-early-warning-dashboard/`, `bls-laus-county-monitor/`. They belong to a
separate consulting line, are governed by `PROJECTS.md`, `BACKLOG.md` and
`TEMPLATE_CONTRACT.md`, and are unrelated to the practice-ops work above. Log
work on them to `BACKLOG.md`, not `PLAN.md`.

> **Before starting anything substantial, read `docs/REPO-INVENTORY.md`.** It
> maps what works, what is stranded on the 76 branches, what is blocked on a
> human, and which documents are stale. It exists because this table used to
> list four of sixteen folders and the same facts kept being rediscovered.

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
