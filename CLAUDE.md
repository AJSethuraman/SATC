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
| `client-documents/` | The document pipeline and the whole life of an engagement: interview → priced documents → billing → delivery, extension, disengagement → close-out and reconciliation. CLI **and** browser front doors over one core. **Most documents a client receives pass a blocking pre-send gate — NOT all of them.** The gate has exactly two callers, `sending.py:177` and `previewing.py:237`, and neither is on the path `cli.py event` takes: the delivery letter, the organizer cover, the extension notice, the disengagement letter and the invoice via `render` ship UNGATED. *(This line read "Every document" until 4 Sep 2026, when it was checked against the callers and found false. `docs/WHERE-THINGS-STAND.md` had the gap recorded as "the biggest hole still open"; this file asserted the opposite, and it is the file loaded into every session.)*; `docs/OPERATING-PROCEDURES.md` is generated from the software and must not be edited by hand | Python, Flask, YAML registries | `cd client-documents && python -m pytest -q` (**1,434 passed, 2 skipped**, ~8 min — measured 4 Sep 2026 in both checkouts), then `python exercise.py` — 29 real scenarios, **109 documents**, every one opened in a browser, and `python capture.py` — 22 screens, 97 controls, photographed. **Ten of those tests skip until the two harnesses have run**, silently, so a suite that has never seen them reports 1,424 / 12 and looks fine. *(This line said 190 documents until 4 Sep 2026; the run produced 109 and the difference is not explained — recorded rather than quietly corrected.)* `make web` for the browser front door |
| `satc-handoff/` | Brand, the ten client document templates + their FIELDS specs, the authoring contract, the run log and the open-questions list | HTML/CSS/Markdown, no build | Read `satc-handoff/START-HERE.md`; templates render in a browser |
| `canon/` | **The practice brain, and it is a plugin — installed, not imported.** Thirty-five tenets each cited to a real bug, the firm's convictions in their own words, and eighteen standing behaviours for how a session conducts itself. Count Bassy challenges a decision from that record and never from an opinion; `/canon:docket` hands back what is open as a form the firm fills in. Holds no client data and mirrors no project's code, deliberately — it has to lift out whole | Python, stdlib only | `cd canon && pytest -q` (138). Installed with `claude plugin update canon`; `marketplace update` refreshes the listing and does **not** install |
| `desk/` | **⚠ UNDER ACTIVE DESIGN BY ANOTHER SESSION as of 4 Sep 2026 — read it before relying on it, and expect it to have moved.** Expert desks: what an agent consults so a question does not reach the firm. A desk answers only from authority it can cite, says how binding that authority is, and escalates rather than guesses; the citation rule is enforced in `engine.py` rather than asked for in a prompt, because the same policy written as skill prose was obeyed *"100%, 4%, 0% of runs"*. One desk exists so far: `fixed-assets`. Depends on `canon`; canon uses nothing from it. **This row is a pointer, not a specification** — it was written from the README by a session that does not own the design | Python, stdlib only | `cd desk && pytest -q` (174 at the time of writing). Offline by construction — `conftest.py` replaces the socket layer, and a test proves that guard can fail |
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

## Read these first, every session

Three documents define what "right" looks like here. They are short, and they
are binding — read them before building, not after.

| Document | Answers |
|---|---|
| **`docs/DESIGN-PRINCIPLES.md`** | **What any change has to be true of.** The anti-drift doc: never invent a value, facts are recorded not inferred, refuse rather than default, the model proposes and the engine disposes, propose never dispose. Each principle is enforced by a test, not by intention. |
| `docs/LOCAL-LLM-PATTERN.md` | The ten rules for anything touching the local model. Binding wherever a model is involved. |
| `satc_system/ARCHITECTURE.md` | Which of the four layers a change belongs in, and which test guards it. |

**`DESIGN-PRINCIPLES.md` must stay current.** When a decision changes a
principle, update that file **in the same commit** — a principle that lives only
in a commit message is one the next session will not read. When adding anything,
answer its three questions: which principle does this rest on, which does it
strain, and what test makes it stick.

## Client-facing copy is a different register from everything else

**Anything a client reads must sound simpler than how we talk about it.** The
fee schedule's comments, the briefs, the PRDs, the specs and the commit messages
are written to argue a case, and that is correct for them. A website page, an
engagement letter or an estimate is not that.

The failure this exists to stop, from the price page (26 Aug 2026):

> These are prices, not a quote. You get an estimate in writing with your own
> lines on it, and the engagement letter governs the work.

The firm's read: *"i would never expect a client to understand what an
engagement letter is inherently. 'governs the work' come on."*

It was not a style slip. The pricing brief told the builder *"An estimate is not
a quote. The engagement letter governs; the estimate accompanies it"* — and that
sentence was transcribed onto the page. **A requirement written for whoever
builds the thing is not copy.** The requirement says what the page must be true
about; the copy has to say it in words the reader already brought with them.

The rules, in order of how often they catch something:

1. **Never transcribe a spec.** If a sentence exists to satisfy a requirement,
   write what the requirement protects, then delete the requirement's wording.
2. **No term a first-time reader would have to look up** — and no term of art
   from our own process. Say the thing: "nothing begins until you've seen it and
   said yes", not "the engagement letter governs the work".
3. **No contract-desk verbs**: governs, constitutes, accompanies, pursuant, in
   accordance with, at our discretion, deemed, shall be, herein.
4. **Cut any sentence whose only job is to protect us.** If it protects us *and*
   tells the reader something useful, keep the useful half.
5. **Length is the tell.** A client-facing sentence past ~25 words was written to
   be complete rather than to be read.
6. **Read it as if saying it across a desk.** If you would not say it out loud to
   a person, do not publish it.

`website/pricing.spec.py` enforces 3 and 5 mechanically over the published copy,
and it is the pattern to copy for any other client-facing surface.

**Six rules were not enough.** They were written mid-build, and the firm rejected
copy five more times afterwards — one sentence that passed all six drew
*"literally AI dribble, why can't you get that?"*. **`website/TENETS.md` is the
superset: nine tenets, ordered by how often each caught something, covering
layout as well as words. Read it before drafting anything for the website.** The
short version of what these six miss: they ask whether a sentence is *worded*
right and never whether it should exist; they cover sentences that protect us but
not ones that flatter us; and they say nothing about layout, which is what
produces filler copy in the first place.

## Hard constraints (do not cross without explicit sign-off)

- **Client PII is load-bearing.** Names/SSNs/EINs live in an **encrypted identity
  vault** (AES-256), split from the de-identified working data mart. Only
  masked/last-4 values belong in artifacts, logs, and workbooks — **never** real
  taxpayer PII. Validation tests fail the build if legal names / full TINs leak
  into outputs. The SATC MCP is **read-only by default**.
- **The system of record is split, and the split is load-bearing.** The firm,
  26 August 2026: *"we are not copying out of drake — drake is only system of
  record for info. but our interview and such is system of record until proven
  wrong. we should update the data to match what we file if required."*
  - **Drake owns what was FILED** — the calculations, the e-file, the return.
    SATC does not replace any of it.
  - **SATC's interview owns what we were TOLD**, and is authoritative *until
    proven wrong*. Never argue that Drake owns a fact and therefore SATC must
    not hold it; that reading is backwards and has caused work to be dropped.
  - **The proving happens at the end of the cycle.** `cli.py close` records
    what was actually filed, in-house, nothing read out of Drake;
    `cli.py reconcile [--apply]` reports every divergence and moves the record
    when the return is right, logging each move.
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

## The line that governs a change here

**Change anything a test can prove; change nothing a client reads or pays.**

Client-facing wording is the firm's. Where a sentence is missing, transcribe
what they have already written elsewhere — the engagement letters are full of
it — or leave `[CONFIRM: ...]`, which makes the document *refuse* rather than
ship a placeholder. `exercise.py` reports those as **waiting on the firm**, not
as failures.

And never claim something works without opening the artifact. `docs/SOFTWARE-TENETS.md`
is 35 tenets on that theme, each cited to a real bug in this repository; the
first one exists because a proof artifact once declared 190 documents fine when
every one of them was unreadable.

## Git workflow

- Develop on a feature branch; commit with clear messages.
- Push and open a **draft PR** — don't push to `main` without explicit approval.
