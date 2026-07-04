# SATC Monorepo — Working Notes for Claude

This repo holds the software for **Sethuraman Accounting, Tax & Consulting (SATC)**.
It's a monorepo with a **one-folder-per-project** layout. The projects are
independent — no shared code between them — so treat each folder as its own
codebase with its own stack, conventions, and way of verifying.

## Projects

| Folder | What it is | Stack | How to verify a change |
|---|---|---|---|
| `website/` | Public marketing + booking site | Single `index.html`, no build step, no framework | Open/serve `index.html` and eyeball it: `cd website && python -m http.server 8000` |
| `invoice-generator/` | "Invoicer" — self-hosted invoice web app (accounts, PDF, Stripe, email, JSON API) | Python / Flask + SQLAlchemy | `pytest` in `invoice-generator/tests`; run the app locally (`run.ps1`, `docker compose up`, or Render) |
| `drake-entry-assistant/` | "DEA" — local-first CLI that validates tax intake data and prepares **masked** Drake-entry plans | Python package (`dea`), `openpyxl` + `PyYAML` | `PYTHONPATH=src pytest -q`; exercise the CLI on the synthetic sample workbook |

## Conventions

- **Match each project's existing style.** The website is hand-edited HTML/CSS
  with content in a `SATC_CONFIG` block at the bottom of `index.html`. Invoicer
  follows a Flask module split (`app.py`, `api.py`, `models.py`, `pdf.py`,
  `email_utils.py`, `stripe_utils.py`, `config.py`). DEA follows a standard
  `src/dea/...` package layout with a `dea` console script.
- **New projects go in their own top-level folder** with their own README,
  dependencies, and tests — mirroring the three existing ones.

## Hard constraints (do not cross without explicit sign-off)

- **DEA safety boundaries** are load-bearing: no real UI automation, no
  `pyautogui`/`pywinauto`, no screenshots/clipboard automation, no real taxpayer
  data in artifacts, all logged/plan values **masked**. Keep Drake-specific
  behavior in `configs/drake/...` and `src/dea/adapters/...`.
- **Money & tax correctness.** Invoice math, Stripe webhooks, and tax-entry
  logic are correctness-critical — add/keep tests and double-check rather than
  guess.

## Deploy paths (these ship automatically — treat edits as production changes)

- `website/` → GitHub Pages via `.github/workflows/pages.yml` on push to `main`.
- `invoice-generator/` → Render via `render.yaml` (Docker + PostgreSQL, autodeploy).

## Git workflow

- Develop on a feature branch; commit with clear messages.
- Push and open a **draft PR** — don't push to `main` without explicit approval.

## Starting a new project

Use `PRD_TEMPLATE.md` at the repo root to write the PRD first, then scaffold the
new project folder from it.
