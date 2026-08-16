# SATC Software Estate — Architecture Overview

**Audience:** an outside architect who needs an accurate picture of what exists, how mature it is, and how the pieces fit together.
**Scope of this review:** every project in the `AJSethuraman/SATC` monorepo plus every other repository on the account.
**Date of review:** 2026-07-29.

> **Confidentiality note.** This document contains no secrets, API keys, credentials, connection strings, or client PII. Where a system stores sensitive data, this document names the *category* of data and the control protecting it — never a value. Every fixture and example referenced in these codebases is synthetic by design.

---

## 1. What SATC's software does, overall

SATC (Sethuraman Accounting, Tax & Consulting) is a solo accounting, tax, and credit-consulting practice, and its software is best understood as **practice-operations tooling built by and for the practitioner** rather than a product line. Three concerns dominate. First, **running the tax practice**: a local-only Flask application (`satc_system`) that intakes clients, reads and classifies their source documents on-device, holds identity data in an encrypted vault separated from a de-identified working data mart, prepares Drake Tax inputs and reconciles Drake's output, and offers small client-facing calculations such as a withholding estimator — with Drake explicitly retained as the system of record for filed returns and computations. Second, **doing the bookkeeping and consulting work**: a homebrew, QuickBooks-style double-entry bookkeeping engine (`Occam`) in which an Excel workbook *is* the system of record and Python is the processing engine; a loan-review workpaper generator (`credit-review-os`) that produces bank-committee-grade Excel deliverables against the interagency classification framework; and a family of self-contained credit-risk monitoring workbooks driven from public regulatory data. Third, **the business surface**: a static marketing/booking site and a self-hosted invoicing application. Cutting across all of it is a consistent and unusually explicit set of engineering doctrines — *local-first by default, deterministic core with no LLM in the data path, PII split from working data and encrypted at rest, the artifact must be self-contained and emailable, and an AI agent may propose but a human commits* — expressed concretely as read-only-by-default MCP servers, config-driven rather than code-driven tax and policy parameters, and test suites that fail the build if real identifiers leak into an output.

---

## 2. The estate at a glance

### 2.1 `AJSethuraman/SATC` — the monorepo (public)

One folder per project; projects are independent codebases sharing only conventions and CI.

| Folder | What it is | Stack | Maturity |
|---|---|---|---|
| `satc_system/` | The tax practice-operations app (the flagship) | Python 3.10+ / Flask / SQLite | **Production-candidate**, real-data-ready |
| `invoice-generator/` | "Invoicer" — self-hosted invoicing SaaS-in-a-box | Python / Flask / SQLAlchemy / Stripe | **Deployed** (Render) |
| `cowork-plugin/` | Claude/Cowork plugin + MCP server for SATC withholding | Python / FastMCP / httpx | **Working prototype** |
| `website/` | Public marketing + consultation booking site | Single hand-written `index.html` | **Live** (GitHub Pages) |
| `credit-review-os/` | Loan-review workpaper engine (consulting deliverables) | Python / openpyxl / PyYAML | **v1 shipped**, unvalidated in the field |
| `stock-helper/` | Local-first SEC/XBRL research assistant | Python / SQLite / FastAPI / Streamlit | **v0.1 prototype** |
| 6 × `*-monitor` / `*-dashboard` dirs | Credit-risk `.xlsm` template series | Python + openpyxl + embedded VBA | **v1 built**, desk-validation pending |
| `control_center.py`, `build_suite.py`, `make_suite_bundle.py` | Root-level Python scripts that package and drive the template series | Python stdlib + Tkinter | **Working** |
| `.claude/skills/`, `PLAN.md`, `PROJECTS.md`, `BACKLOG.md`, `TEMPLATE_CONTRACT.md` | The agent-development pipeline and its running logs | Markdown | **In active use** |

### 2.2 Other repositories on the account

| Repo | Visibility | Firm software? | What it is |
|---|---|---|---|
| `AJSethuraman/occam` | private | **Yes — core** | The homebrew QuickBooks-style bookkeeping app (engine + local web UI + Cowork plugin) |
| `AJSethuraman/merchant-normalizer` | private | **Yes — supporting** | Deterministic merchant-descriptor normalizer and statement analyzer; feeds Occam's rule library |
| `AJSethuraman/eventos` | private | No | A Discord community event bot (TypeScript/Node/Prisma/Postgres). Unrelated to the firm. |
| `AJSethuraman/backpack_battles_assistant` | private | No | A local screenshot-analysis helper for a video game (Python). Unrelated to the firm. |

The last two are personal projects; they are listed for completeness and are not described further.

> **Documentation drift worth flagging up front.** The monorepo's `CLAUDE.md` lists only four projects (`website`, `invoice-generator`, `satc_system`, `cowork-plugin`). In reality the monorepo now also contains `credit-review-os`, `stock-helper`, and the six-template credit-risk suite, and two of the most substantial systems in the estate (Occam and merchant-normalizer) live in *separate private repos* that the monorepo never mentions. An architect reading only `CLAUDE.md` would see roughly a third of the codebase.

---

## 3. Project-by-project detail

### 3.1 `satc_system/` — SATC practice-operations app

**Purpose.** A local, hand-holding GUI that runs a solo tax practice end to end: client intake and engagement tracking, document collection and on-device reading, staging with human confirmation, a de-identified data mart, Drake input generation and reconciliation, prior-year roll-forward, client communications, and a withholding estimator. Explicitly **not** a tax engine — Drake Tax remains the system of record for computation and e-file.

**Language / stack.** Python ≥3.10 (~14,300 LOC under `src/`). Flask + Jinja2 for a localhost-only GUI; SQLite for persistence; `openpyxl` for workbook output; `cryptography` for the vault; optional `pypdf`, `pymupdf`, `pytesseract`/Pillow (OCR), `reportlab` (PDF), `pywin32` (Outlook COM on Windows), `mcp` (agent server), `pyinstaller` (packaging). Packaged as a single Windows `SATC.exe` via a GitHub Actions release workflow.

**Key modules / entry points.**

| Entry point | What it is |
|---|---|
| `satc` (`satc.cli:main`) | CLI — `app`, `doctor`, `build`, `sort`, `seed`, `export`, `reset` |
| `satc-app` (`satc.app.server:main`) | The Flask GUI, default port 5050, bound to loopback |
| `satc-mcp` (`satc.api.mcp_server:main`) | MCP server for agents; **read/compute only unless `SATC_MCP_ALLOW_WRITES` is explicitly set** |
| `SATC.exe` / `SATC.exe --mcp` | The frozen desktop build; one binary, both modes |

Internally the code is organised in four deliberate layers — config (`configs/`, data not code), pure logic (`src/satc/<area>/`), state and persistence (`models/`, `persistence/`, `app/state.py`), and a thin UI (`app/` + templates). Notable areas: `ingest/` (classification, splitting, sorting, readers, staging gate), `crosswalk/` (dated, cited tax-law parameters by jurisdiction × year), `withholding/` (a pure estimator engine), `drake/` (preparer-set PDF parser, input generator, comms), `workbook/` (config-driven line sheets), `proforma/` (roll-forward), `persistence/crypto.py` (vault encryption).

**Inputs.** Folders of client source documents (PDFs, scans, phone photos) — W-2, 1099-INT/DIV, K-1 (1065 and 1120-S), prior-year 1040, paystubs; a Drake preparer-set PDF; typed intake data; YAML configs for tax parameters, extraction maps, classification signatures, line sheets, and workflows.

**Outputs.** A SQLite store (encrypted identity vault + de-identified mart); a sorted/relabelled copy-only document tree; an Excel workpaper workbook and a de-identified mart export; a Drake-ready intake workbook; client organizers and cover/delivery emails (draft `.eml` or an Outlook draft — never auto-sent); a withholding projection with a W-4 line-4c recommendation and an audit tape.

**Data touched and sensitivity — the highest-sensitivity system in the estate.** Full legal names, SSNs/EINs, addresses, contact details, and raw source documents. The design response is a hard two-layer split: an **identity vault** (`satc_vault.db`) whose PII columns are AES-256-GCM ciphertext at rest, with the data key sealed by Windows DPAPI to the user account (a 0600 key file elsewhere, documented as the weaker fallback); and a **de-identified data mart** keyed by `client_id + tax_year + return_type + jurisdiction` holding only masked/last-4 values. Data directory is 0700, database and key files 0600. The one artifact that necessarily carries real identity data — the Drake keying intake workbook — is explicitly ephemeral, git-ignored, and deleted after keying. MCP read tools return de-identified display labels, pinned by tests.

**External services / APIs.** By default, **none** — the system is fully offline. Optional and each individually gated: a local Ollama vision model on localhost; local Tesseract OCR; a cloud vision escape hatch (Anthropic) that requires *both* an explicit `SATC_ALLOW_CLOUD` opt-in *and* a key (a key alone does nothing); Outlook via COM for drafting mail. The compliance research recorded in `PLAN.md` treats the local-default posture as a §7216/Circular 230 feature, not a preference.

**Maturity.** The most complete system here. 255 test functions across 44 files; CI runs the suite on every push. A documented Phase 0 security remediation (2026-07-04) closed a critical plaintext-vault finding plus DNS-rebinding, CSRF, file-permission, secret-key, and intake-path findings, and the project's own log declares it safe to hold real SSNs on a Windows box with the DPAPI-sealed vault.

**Known gaps / TODOs.**
- The `PLAN.md` "blocked on a human" item is still open: a matching `SATC.exe` release has not been cut, so the published binary predates the withholding API, MCP mode, and the Cowork plugin. Code, released exe, and docs describe three different products.
- Packaging is still `--onefile`; the researched decision to move to `--onedir` (faster start, materially less AV-quarantine risk) is unimplemented, as is code signing and the one-click `.mcpb` bundle that would launch `SATC.exe --mcp`.
- A WISP template (IRS Pub 5708) was scoped as a shippable product artifact; not built.
- Estimated-tax reminders are specified in a PRD and sliced into three open issues (#56–#58) — worklist, safe-harbor pre-fill, draft reminder email — none built.
- The non-Windows key-sealing fallback is a documented weakness; the local JSON API is unauthenticated (mitigated by the loopback bind and Host allow-list, not by auth).

---

### 3.2 `AJSethuraman/occam` — the homebrew QuickBooks-style app

**Purpose.** A local-first double-entry bookkeeping system for the practice: bank and credit-card CSV exports go in, GAAP-style financial statements come out. The organising bet is that **the Excel workbook is the system of record** and Python is the processing engine — one workbook per client, many accounting periods inside it, closed periods preserved forever and write-protected. Its stated product vision is "provable books, an AI staff accountant, and a transparent substrate," with Excel described as "replaceable only by something *more* auditable, never by something more convenient."

**Language / stack.** Python 3.11+ (~28,400 LOC in the engine package) with `openpyxl`; FastAPI for a localhost-only API; React 18 + TypeScript + Vite + Storybook for the browser UI (shipped prebuilt, so Node is not needed to run it); a legacy PySide6 desktop UI; PowerShell installers/launchers. Windows 10/11 target.

**Key modules / entry points.**

| Entry point | What it is |
|---|---|
| `launch_web.ps1` → `occam_processor/api/server.py` | The local FastAPI server + prebuilt React UI, `127.0.0.1:8765` (~45 write endpoints) |
| `occam-processor` CLI | Full fallback for every operation (`open-period`, `close-check`, `close`, `reopen-period`, `reports`, `import-rules`, …) |
| `launch_ui.ps1` | Legacy PySide6 desktop UI |
| `cowork-plugin/mcp/occam_mcp.py` | The MCP server (see §3.3) |

The engine decomposes into recognisable accounting concerns: `csv_importer`/`csv_detect`/`csv_repair`/`import_validator` (ingestion), `normalizer`/`merchant_clean`/`merchant_normalize`/`merchant_aliases` (descriptor cleanup), `rules_engine`/`promote_rules`/`rules_import` (categorisation), `split_engine`, `transfer_matcher`, `review_queue`/`reviewer_gate`/`reviewer_flags`, `journal_poster`, `reconciliation`, `statement_reader`, `opening_balances`, `periods`/`period_close`/`period_protection`/`period_reset`/`period_migration`, `master_coa`/`starter_coa`/`coa_renumber`/`chart_migration`, `reports`, `confirmations`, `audit`, `snapshots`, `approval`.

**Inputs.** Bank and credit-card CSV exports; PDF/CSV statements (for reconciliation and proven openings); a global categorisation-rule CSV (`data/global_rules.csv`); Setup-Wizard answers; reviewer decisions; client confirmation responses.

**Outputs.** The client workbook itself (the record) — normalized imports, review queue, splits, journals, periods, audit rows; period-aware Income Statement, Trial Balance, Balance Sheet with a proper equity roll-forward, General Ledger, Journal Entries, and Exceptions; a client-facing confirmation workbook; an auto-derived client request list; promoted rule CSVs.

**Data touched and sensitivity.** Real client financial data — full transaction histories, merchant descriptors, account balances, statement figures, and account last-4 identifiers. Sensitive commercially and personally, though it holds no SSNs/TINs. Everything is local: no database, no cloud, `127.0.0.1` bind only. Rule promotion from client-specific to global is a governed step that requires provenance scrubbing — client names, descriptor patterns, and periods must not leave the local workbook.

**External services / APIs.** None. No bank feeds, no Plaid, no cloud. File-based inputs and export-based client contact are explicit current stances (though multi-user, live feeds, and a client portal are deliberately *not* declared non-goals).

**Maturity.** **Substantial but mid-remediation.** v1.4.0, 67 test files with ~1,257 test functions, a full multi-period demo, and pilot documentation (`QUICKSTART`, `PILOT_SCOPE`, `LIMITATIONS`, `RUNBOOK`). However, an adversarial multi-agent review (`docs/ULTRA_REVIEW.md`, 2026-07) produced 37 confirmed findings, and the retroactive PRD's roadmap step 1 is literally "make the invariants true." The most recent commit ("parsers: close the proof pipeline's escape hatches") is remediation work in progress.

**Known gaps / TODOs — the confirmed review findings, summarised by theme.**
1. **The double-entry invariant is not asserted at the posting boundary.** Mixed-sign splits can post an unbalanced journal stamped `Posted`, and the pro-forma preview reproduces the same error, so the human review gate cannot catch it (the single CRITICAL finding). Related: any transaction with rows in the splits table posts as a split with no re-validation, so stale split rows can silently override an approved category.
2. **The statement parser's checksum gate has escape hatches.** Wrong dates, invented balances from date digits, truncated comma-less amounts, mis-yeared card transactions, block-grouping hijacked by merchant text shaped like a date, and zero-line parses can all emerge stamped "checksum-verified" — corrupting exactly the numbers the never-plug reconciliation discipline depends on.
3. **Subsystems are locally correct but jointly incoherent.** Matched-transfer contra legs are released once their counterpart posts (double-counting cash and manufacturing phantom revenue); the reconciliation book pool silently excludes transfer rows; a client's "personal" response on a posted transaction is silently dropped while the close still reports green; and closing a named period runs the readiness gate against the *current* period rather than the target.
4. **Platform and trust-boundary gaps.** The "atomic" workbook save is a truncate-and-copy on Windows (a crash mid-write leaves an unreadable source of record), reads happen outside the write lock, and untrusted bank descriptor text flows unsanitised into live Excel formulas in both the operator's workbook and the client-facing export (formula-injection). A chart-migration routine can clobber custom accounts occupying reserved codes.
5. Fifteen further medium findings are recorded as unverified leads, including no CSRF/Host-header defence on the unauthenticated local write API.
6. Open product questions with named triggers: rule-graduation thresholds for automation, the guessed-item lifecycle threshold, multi-client scale, monthly cadence, materiality ownership, and writer identity in the audit trail.

---

### 3.3 `occam/cowork-plugin/` — the Occam Cowork plugin

**Purpose.** Drive Occam in plain language from Claude Cowork — review the queue, match transfers, reconcile, post, close, and curate rules — with a human on every ledger-changing action.

**Stack.** Python MCP server (`mcp/occam_mcp.py`, ~800 LOC) using FastMCP + httpx as a thin HTTP proxy to the running Occam API; a `.mcpb` desktop-extension manifest for the connector; six skills (`occam-review`, `occam-month-end`, `occam-reconcile`, `occam-run-books`, `occam-begin-balances`, `occam-promote-rules`).

**Interface.** ~40 tools split into reads that run freely (`occam_status`, `occam_coa`, `occam_review_summary`, `occam_review_queue`, `occam_close_check`, `occam_reconciliation`, `occam_proforma_trial_balance`, …) and writes tagged with `destructiveHint` that require explicit confirmation (`occam_decide`, `occam_bulk_decide`, `occam_match_transfers`, `occam_reconcile`, `occam_set_opening_balances`, `occam_post_journals`, `occam_close`, …).

**Maturity / gaps.** Working prototype, v0.2.0. It is the surface the PRD says should become "the product" (roadmap step 2: agent-first, API-and-tool before UI). Gaps: the legacy `/api/close` path it uses takes no pre-close snapshot and returns success on a blocked close; installation is a two-piece manual flow (deps + `.mcpb` connector + plugin upload); the guardrail model is enforced by skill prose and tool annotations rather than by the server.

---

### 3.4 `AJSethuraman/merchant-normalizer`

**Purpose.** Deterministic, explicitly **non-AI** merchant-descriptor normalization and statement analysis for CSV and PDF bank/card statements. It is the upstream sibling of Occam's categorisation layer: the rules project whose output regenerates Occam's `global_rules.csv`.

**Stack.** Python 3.11+, ~3,400 LOC, `pandas` core; optional extras for PDF (`pdfplumber`/`camelot`/`tabula`), a Streamlit review UI, and SQLAlchemy-backed rule storage. Entry points: `merchant-normalizer` CLI (`normalize`, `scan`, `label`) and `streamlit run app_streamlit.py`.

**Pipeline.** `cleaning.py` (Unicode normalization, processor-prefix stripping, URL/domain removal, ACH and channel metadata extraction, date/reference-noise removal, city/state tail trimming) → `matching.py` (strict precedence: user override → global exact → processor exact → bounded fuzzy fallback) → `confidence.py` (deterministic score in five bands) → `review.py`/`storage.py`/`overrides.py` (accept / override / promote, with overrides as plain JSON).

**Inputs / outputs.** Statement CSVs (auto-detecting common bank and card column layouts, including split debit/credit columns) and best-effort PDFs; out come normalized merchant keys with raw descriptions preserved for auditability, plus a statement report grouping recurring charges by cadence, summing fees and interest, separating transfers from spend, flagging same-day duplicates, and ranking merchants needing review.

**Data / external services.** Real transaction data; everything local and deterministic — "no bank login, no Plaid, no data leaves your machine." No external APIs.

**Maturity.** v0.1.0 scaffold but well-tested — 46 test functions across 13 files covering cleaning, matching, confidence, aliases, ingestion, review actions, overrides, storage, and PDF handling.

**Known gaps / TODOs (self-declared).** PDF extraction is best-effort and layout-dependent; scanned PDFs unsupported; normalization is imperfect on truncated/ambiguous descriptors (user correction is treated as part of the workflow, not an edge case). The README's file links are absolute Windows paths from the author's machine and are broken for any other reader.

---

### 3.5 `invoice-generator/` — "Invoicer"

**Purpose.** A self-hosted invoice generator: accounts, a web invoice builder, PDF rendering, Stripe Checkout collection, SMTP delivery, and a per-user JSON API. Explicitly an independent implementation, not a wrapper on any commercial invoicing API.

**Stack.** Flask 3 + Flask-Login + Flask-WTF + Flask-Limiter, SQLAlchemy 2 (SQLite locally, PostgreSQL in production), WeasyPrint or xhtml2pdf for PDF, Stripe SDK, Gunicorn, Docker. ~5,200 LOC. Module split: `app.py` (factory, auth, web routes), `api.py` (JSON blueprint), `models.py` (User/Invoice/LineItem + totals), `pdf.py`, `stripe_utils.py`, `email_utils.py`, `helpers.py`, `config.py`.

**Inputs / outputs.** Invoice form data or JSON API payloads (parties, line items, tax/discount/shipping, logo upload) → persisted invoices, rendered PDFs, CSV export of the invoice list, Stripe Checkout payment links, and emailed invoices with the PDF attached.

**Data touched.** Multi-tenant customer data: account emails, hashed passwords, per-user API keys, business identity including a tax-ID field, bill-to/ship-to details, invoice amounts, Stripe connected-account identifiers, and per-user SMTP settings. Moderately sensitive and — unlike everything else here — **internet-facing and multi-tenant**, which makes it the largest attack surface in the estate.

**External services.** Stripe (Checkout, Connect Express direct charges, webhooks), SMTP, optional Sentry, Render (hosting + managed PostgreSQL).

**Maturity.** **Deployed.** `render.yaml` at the repo root autodeploys it as a Docker service with a managed Postgres. Security posture is genuinely considered: hashed passwords, strict per-user scoping, CSRF on browser forms (with the key-authed API and signature-verified webhook exempted by design), rate limiting on auth routes, token-based email verification and password reset, secure cookies, and webhook signature verification.

**Known gaps / TODOs.** Test coverage is the weakest in the estate — **7 test functions in a single file, covering invoice math only**; there are no tests for auth, tenant isolation, the API, the Stripe webhook path, or PDF rendering, in a live multi-tenant app that handles payment flows. Monetization (platform fee, subscription tiers) is built but dormant. The Terms and Privacy pages are unfilled templates flagged as needing legal review before public launch. The free Render database tier has retention limits the README itself warns against relying on. Per-user SMTP passwords are stored in the application database.

---

### 3.6 `cowork-plugin/` (monorepo) — the SATC withholding plugin

**Purpose.** Let an agent run SATC's withholding estimator conversationally: project a household's full-year federal withholding and recommend a W-4 line-4c adjustment.

**Stack.** Python MCP server (`mcp/satc_mcp.py`, 114 LOC) built on FastMCP + httpx; a plugin manifest, an `.mcpb` desktop-extension manifest, an `.mcp.json` template, and one skill (`satc-withholding`).

**Architecture.** Deliberately a **thin HTTP proxy**: `agent → plugin → MCP server → the running SATC app's local JSON API`. It imports no SATC internals and holds no state. Three tools, all read/compute: `satc_withholding_meta` (`GET /api/withholding/meta`), `satc_read_paystub` (`POST /api/withholding/read-paystub`), `satc_estimate_withholding` (`POST /api/withholding/estimate`).

**Data touched.** Withholding is stateless compute over figures the user supplies — pay amounts, withholding, YTD totals, filing status. **No vault access, no data mart access, no stored client record, no PII.** That scoping is the point: the fuller in-process `satc-mcp` server (create clients, run intake, post a return) is intentionally excluded from this plugin because it shares the local store.

**Maturity.** Working prototype, v0.1.0. Error handling is thoughtful — it surfaces the API's own guard messages and refuses to let an HTTP-200-with-error-body read as success.

**Known gaps.** Setup requires a pinned port and a manual template rename; the one-click `.mcpb` path that would bundle `SATC.exe --mcp` is designed but not built; there are no tests in the plugin folder itself (the API it proxies is tested in `satc_system`).

---

### 3.7 `credit-review-os/`

**Purpose.** A portable, config-driven loan-review workpaper system for the consulting side of the practice. It produces bank-committee-grade Excel deliverables — a linesheet per loan, a master roll-up, a de-identified data mart, and a findings register — with a built-in regulatory crosswalk proving the methodology satisfies the interagency standard.

**Stack.** Python (~3,600 LOC) with `openpyxl` + `PyYAML`; the `formulas` engine for recalculation in tests; AES-256-GCM at rest. Entry point: the `credit-review` CLI (`build`, `ingest`, `bundle`, and a planned `ui`).

**Two-layer configuration** is the core design idea: a **program** YAML per line of business is portable and client-agnostic (rating framework, linesheet sections, exception rules, evidence checklist, cited crosswalk — the loader rejects client-specific keys outright), and a thin **engagement overlay** per bank carries client identity, as-of date, rating-scale mapping, policy thresholds, scope, and the loan list. Adding a client bank is an overlay; adding a line of business is a program. Neither is a code change. Shipped programs: C&I, income-producing CRE, owner-occupied CRE, construction/ADC, agricultural, and retail. Two review modes are built — Mode A (loan-level commercial credit files) and Mode B (retail product-conformance on a sample, with URCCP classification computed by live formula).

**Inputs / outputs.** Program + engagement YAML in; one self-contained `.xlsm`/`.xlsx` engagement workbook out (Cover, per-loan or per-product sheets, Master/Products, Data Mart, Findings, `_methodology`, `_config`, `_readme`), plus a JSON findings re-ingest and a single pure-ASCII builder script for transmission through a bank's DLP boundary.

**Data touched.** Borrower names and loan numbers appear **only** in the engagement workbook (the bank's own data, returned to the bank), which is AES-256-GCM encrypted at rest with the same DPAPI-sealed key pattern as `satc_system`. TINs are last-4 only everywhere and loaders reject full-TIN shapes. The data mart and every re-ingest export are de-identified with engagement-scoped ids. Mode B is stricter still: loan number only, never a person name.

**External services.** None — a deterministic core with no network and no clock in outputs; identical inputs produce a byte-identical workbook.

**Maturity.** v1 shipped 2026-07-05 with 102 test functions across 13 files at three declared seams (recalc-against-hand-checked-values, re-ingest round trip, and a byte-scan that fails the build on any PII leak).

**Known gaps / TODOs.** The single most important open item is a **pin-cite confirmation sprint** — the regulatory page citations in the crosswalk have not been verified against the live regulator PDFs, and the automated attempt failed because the agencies' sites block automated egress. This requires a human browser before any filed workpaper. A "Review Room" file-at-a-time UI is specified and sliced into open issues #75–#76 but unbuilt. Deferred by decision: mixed-mode workbooks and a statistical sample-size calculator. Roadmap: consumer/residential build-out, document parsing/OCR pre-fill (proposal lane only), an optional local human-confirmed LLM extraction assist that may never write a rating, and ACL/CECL export.

---

### 3.8 The credit-risk `.xlsm` template series + the root Python scripts

**Purpose.** Six self-contained Excel monitoring workbooks over public regulatory data, plus the tooling that builds, bundles, and drives them. One reusable pattern: Python pulls a source, lands raw data in the workbook, formula-driven dashboards render it, and a watchlist lane admits only series carrying a genuine portfolio-joinable key (a geography or an entity id) — national aggregates are structurally refused.

| Directory | Workbook | Source |
|---|---|---|
| `fred-credit-risk-dashboard/` | FRED Credit-Risk Dashboard | FRED (147 series) |
| `bureau-credit-risk-dashboard/` | Consumer Credit Risk Monitor | NY Fed Household Debt & Credit (anonymized 5% sample) |
| `macro-early-warning-dashboard/` | Macro Early-Warning Monitor | FRED (national + 151 state-keyed series) |
| `fdic-peer-monitor/` | Bank Peer Monitor | FDIC BankFind Suite API (keyless) |
| `cfpb-mortgage-monitor/` | Mortgage Delinquency Monitor | CFPB Mortgage Performance Trends |
| `edgar-crit-class-tracker/` | Crit/Class Tracker | SEC EDGAR (XBRL + submissions) |
| `bls-laus-county-monitor/` | *(spec only — build spec, no code)* | BLS LAUS |

**Stack.** Python + `pandas` + `openpyxl`, with an extract-only VBA bootstrap embedded in each workbook. Each directory is self-contained by design and carries its own copies of the shared modules (`keybank_style.py`, `vba_writer.py`, `assemble_xlsm.py`) plus a `runner.py`, `build_workbook.py`, `make_bundle.py`, an `email_sim.py` acceptance harness, and tests (14–33 test functions each).

**The root-level Python scripts.**
- **`control_center.py`** (~460 LOC, Tkinter GUI + headless CLI) — the one place to run everything. It discovers any workbook carrying a `_code_py` tab, reads its live state (last run, alert counts, staleness) without opening it, extracts that workbook's *own* embedded runner, and drives it in demo or live mode. Nothing template-specific lives in it, so contract-compliant templates appear automatically. `--doctor` answers "will this machine work?" by checking dependencies and which provider hosts the network allows.
- **`build_suite.py`** (~465 KB, pure ASCII) — a single-file installer carrying the entire suite gzip+base64-encoded. It exists to solve a transfer problem: one emailable ASCII file reconstitutes `control_center.py` plus every template into its own subfolder with demo-populated workbooks.
- **`make_suite_bundle.py`** — regenerates `build_suite.py` by discovering every `*/build_*.py` bundle in the repo, so new templates join the suite automatically.
- **`website/assets/make-images.py`** — a small Pillow script that regenerates the site's branded OG image and touch icon.

**Inputs / outputs.** Public API responses and CSVs in; a demo-populated or live-refreshed `.xlsm` out, with `_provenance` (metric → source document → schedule/line → link) and `_config` tabs the operator edits as data (`[PEERS]` by CERT or CIK, `[FOOTPRINT]` by county FIPS, `[THRESHOLDS]` as numbers).

**Data touched.** Entirely public data — no PII, no client data. The one sensitive input is the operator's own peer/footprint list, which reveals competitive interest.

**External services.** FRED (free API key), FDIC BankFind (keyless), NY Fed, CFPB (keyless), SEC EDGAR (keyless but requires a User-Agent configured in `_config`).

**Maturity.** All six built and passing their own suites, but **not desk-validated**. `BACKLOG.md` §1 tracks validation debts that require the operator's own machine: no `.xlsm` has ever been opened in real desktop Excel or had its ExtractFiles macro clicked; the FRED/macro templates await a live run with a key; the FDIC template needs its illustrative seed CERTs replaced with a real peer list; and the bureau template's `_parse_table` is deliberately unbound because the NY Fed table layout could not be verified from the build box — demo works fully, live needs a real column mapping.

**Other gaps.** The FRED template predates `TEMPLATE_CONTRACT.md` and needs an alignment audit; a suite-level conformance check (asserting shared modules are byte-identical, embedded code is ASCII, tabs match the contract) is unbuilt; the visual suite-overview page is hand-assembled rather than generated.

---

### 3.9 `stock-helper/`

**Purpose.** A local-first stock research helper that digests SEC filings, XBRL company facts, and industry context into evidence-backed signal reports. Explicitly not a buy/sell bot — every signal traces to a source document, accession number, or a calculation over disclosed facts, with a confidence level and a caveat.

**Stack.** Python (~5,000 LOC), SQLite with FTS5, FastAPI, Streamlit, `uv`. Entry point: the `stock-helper` CLI (`init`, `fetch-sec`, `build-report`, `signal-history`, `run-ui`). Modules: `connectors/sec.py`, `ingestion/`, `normalization/` (XBRL → canonical metrics), `parsing/` (filing sections, text metrics, wordlists), `signals/` (engine, definitions, history), `features/`, `industry/sic_buckets.py`, `storage/`, `reports/tearsheet.py`, `ai/` (interfaces + a no-op and a rule-based implementation).

**Inputs / outputs.** A ticker; out come cached SEC submissions and company facts stored with full provenance (source URL, accession, filed date, retrieved timestamp, parser version), a normalized metric library, a rule-based signal scorecard, Markdown tear sheets, and JSON over FastAPI.

**Data / external services.** Entirely public: SEC EDGAR (requires a configured User-Agent) and optionally Stooq for price data, gated off by default and clearly labelled non-canonical. No PII, no client data.

**Maturity.** v0.1 prototype (Phase 0 + a thin Phase 1) but disciplined — 66 test functions across 13 files, and a point-in-time replay mode so reports can be rebuilt as they were knowable on a past date.

**Known gaps (self-declared and unusually honest).** No footnote extraction or robust section boundaries; peer percentiles use only the locally fetched universe, not the market; CET1 and table-only bank metrics need filing-table parsing; no macro layer; **no model-based AI at all** (the `ai/` package is interfaces plus rule-based fallbacks — nothing calls an LLM); and no backtesting, hit rates, or performance claims of any kind. An open PR (#89) proposes a fundamental-valuation, forensic/distress and outlier-screener expansion.

---

### 3.10 `website/`

**Purpose.** The public marketing and consultation-booking page.

**Stack.** A single hand-written `index.html` (~1,230 lines, HTML + CSS + vanilla JS, no build step, no framework), plus `privacy.html`, `terms.html`, `robots.txt`, `sitemap.xml`, and generated images. All editable content lives in one `SATC_CONFIG` block at the bottom of `index.html`.

**Inputs / outputs / external services.** Config-block content in, a responsive static page out. It embeds a third-party scheduler (Calendly or Cal.com) and optionally a Formspree contact form — the only external dependencies, and both are configuration values rather than integrations. Data touched: prospect-submitted contact details, which flow to those third parties, not to SATC infrastructure.

**Maturity.** **Live.** `.github/workflows/pages.yml` deploys to GitHub Pages on any push to `main` touching `website/` — an edit here is a production change. Content discipline is explicit: no fake testimonials, metrics, or blog posts.

**Known gaps.** No tests and no link checking; privacy/terms are templates; the booking link and Formspree id must be configured for the page to do its job.

---

### 3.11 Repo-level tooling and process

- **`.claude/skills/`** — a committed pipeline of single-purpose agent skills with human gates between them: the spine is `/grill-me` → `/to-prd` → `/to-issues` → build (fronted by `/occam`), with `handoff`, `diagnosing-bugs`, `tdd`, `research`, `domain-modeling`, `codebase-design`, and `triage` as supporting steps. The pipeline treats maintaining the running log (`PLAN.md`, `BACKLOG.md`) as a built-in step. This is a genuine part of the architecture: most recent work in these repos was produced through it.
- **`TEMPLATE_CONTRACT.md`** — binding on every new credit-risk template (tab taxonomy, `_config` schema, runner CLI, extract-only macro, seam contract, watchlist gate, verification bar). It is what makes templates interchangeable and launcher-compatible.
- **CI** — `test.yml` runs `pytest` for `satc_system` on every push and PR; `build-desktop-app.yml` builds `SATC.exe` on a `v*` tag or manual dispatch and attaches it to the release; `pages.yml` deploys the website.
- **Deploy paths that ship automatically:** `website/` → GitHub Pages on push to `main`; `invoice-generator/` → Render via `render.yaml` with autodeploy. Treat edits to either as production changes.
- **Branch and PR state.** The repo carries **25 open pull requests and 22 open issues**, most of them draft PRs on agent-generated feature branches — a Consumer Credit Population Bench (#78, with slices #79–#87), a Credit Review OS Review Room (#77, #75–#76), stock-helper expansion (#89), desk-validation follow-ups (#88), an assortment of earlier Codex-era prototypes (#1–#19), and two game projects (#90, #99, issues #91–#98) that are not firm software and are staged to move out. An architect should read this as a large, mostly unmerged idea backlog rather than as work in flight.

---

## 4. How the pieces connect

There is **no shared runtime, no shared database, and no service mesh**. Every system is independently runnable, and the connections between them are of four kinds: a human moving a file, a localhost HTTP call, a config artifact regenerated from one project into another, and a shared design pattern deliberately copied rather than imported.

### 4.1 The tax-return path (the practice's core loop)

```
Client documents (PDF / scan / photo)
   │
   ▼  folder intake
satc_system: split → classify by content → read (5 rungs: form fields → embedded
   text → local OCR → local vision → cloud [off by default])
   │
   ▼  every reader emits the same ReadResult
STAGING GATE — nothing is trusted until confirmed; HIGH confidence auto-confirms,
   everything else waits for the human; TINs masked to last-4; amounts never guessed
   │
   ├──► ENCRYPTED IDENTITY VAULT  (names, SSN/EIN, addresses — AES-256-GCM)
   │
   └──► DE-IDENTIFIED DATA MART   (line items keyed client_id|year|return_type|
                                   jurisdiction, with SOURCE_DOC provenance)
                │
                ├──► Drake INPUT workbook  ──►  [HUMAN KEYS INTO DRAKE]  ──► filed return
                │       (ephemeral, carries real identity, deleted after keying)
                │
                ◄──── Drake preparer-set PDF ──► parsed → seeds the mart (no re-keying)
                │                                 → reconciliation back to Drake's output
                │
                ├──► Excel workpaper workbook + de-identified mart export
                ├──► organizer / cover letter / delivery email (drafts only, never auto-sent)
                └──► prior-year roll-forward → next year's pro forma
```

**Drake is the boundary and the system of record.** SATC prepares inputs and reconciles outputs; it never computes the filed return. The Drake handoff is deliberately a human keying step.

### 4.2 The bookkeeping path

```
Bank / card CSV exports          PDF or CSV statements
   │                                 │
   ▼                                 ▼
Occam: import → normalize     statement_reader (checksum-gated)
   → merchant clean               │
   → rules engine (global +       ├─► reconciliation target (ending balance)
     client-learned)              └─► proven opening (two-statement bracket)
   → transfer matcher                 │
   → REVIEW QUEUE  ◄── AI proposes ───┤
        │                             │
   [REVIEWER DECIDES — the only gate that changes the ledger]
        │
        ├─► pro-forma trial balance (same code path as the poster)
        ├─► post journals ──► reconcile (named items, never a plug) ──► close period
        └─► client confirmation export ──► client answers ──► corrections
                                                  │
   provisional patterns ──► client rule ──► [governed, provenance-scrubbed] ──► global rule
                                                  ▲
                                    merchant-normalizer regenerates global_rules.csv
```

**merchant-normalizer → Occam** is the one genuine cross-repo data dependency in the estate, and it is deliberately loose: the contract is a single CSV file with a documented column schema, and Occam's importer de-duplicates by rule name and validates every account code against the client's chart of accounts, skipping unknown ones.

### 4.3 The agent path

```
Claude Cowork / Claude Desktop
   │
   ├── satc-withholding plugin ──► satc_mcp.py ──HTTP──► SATC app :5050
   │      (3 read/compute tools, no PII, stateless)        /api/withholding/*
   │
   ├── satc-mcp (in-process, packaged in SATC.exe --mcp)
   │      read + compute by default; writes only with an explicit env opt-in;
   │      reads return de-identified labels, pinned by tests
   │
   └── occam plugin ──► occam_mcp.py ──HTTP──► Occam API :8765 ──► client workbook
          (~40 tools; reads free, writes annotated destructive and confirmation-gated)
```

Both MCP servers are **thin HTTP proxies to a locally-running app**, never direct database or file access. Both encode the same authority model: *the agent proposes and computes, the human commits.* In SATC this is enforced by wiring — write tools are not registered at all unless the opt-in is set, so they do not exist to be called. In Occam it is enforced by tool annotations plus skill prose, which is weaker.

### 4.4 The consulting and business paths

The credit-risk template series and `credit-review-os` are **downstream of nothing** — they take public data or a bank's own loan file and emit a self-contained workbook. `control_center.py` sits above the templates as a launcher that discovers them by contract rather than by registration. `credit-review-os` is connected to `satc_system` only by **pattern reuse**: it copied the AES-256-GCM + DPAPI vault design and the PII-byte-scan test seam rather than importing them (open issue #80 proposes extracting a genuinely shared credit core). `invoice-generator` and `website` are independent of everything; nothing feeds them and they feed nothing.

### 4.5 The seams that matter to an architect

| Seam | Contract | Coupling |
|---|---|---|
| SATC ↔ Drake | An intake workbook shaped for keying; a preparer-set PDF parsed back | Human-in-the-loop, deliberately manual |
| Vault ↔ mart | `client_id` only; masked/last-4 in the mart | Enforced by tests that fail the build on a leak |
| merchant-normalizer → Occam | `global_rules.csv`, documented column schema | File-level; validated on import |
| Any MCP → its app | Localhost JSON over HTTP | Thin proxy; no shared state |
| Template → Control Center | `TEMPLATE_CONTRACT.md` + a `_code_py` tab | Discovery by convention, zero wiring |
| credit-review-os ↔ satc_system | Copied crypto and PII-guard patterns | **Duplication, not reuse** — a known debt |

---

## 5. Where AI automation could plug in to help run the firm

The estate is unusually well-prepared for this: the MCP surfaces already exist, the authority model is already decided (*propose, never commit*), and the local-first architecture is already the right answer to the §7216 / Circular 230 question — client data does not leave the machine, so the compliance exposure is confined to explicitly-gated cloud paths. The following are ranked by leverage against effort, and each names the seam it would attach to.

**1. Document classification, routing, and auto-generated request lists (highest leverage).** SATC already classifies documents by content and Occam already derives a client request list. The unbuilt step is the one industry research identified as the #1 practitioner pain point — *69% of accountants say they spend too much time gathering documents*. An agent that watches the engagement checklist, routes each uploaded document to the right checklist item, and generates next year's document-request list from the prior-year mart would attack the biggest time sink using data both systems already hold. Seam: `satc_system`'s existing classifier plus the `intake_engagements`/`intake_tasks` tables.

**2. The reviewer's queue in Occam — already designed, needs the invariants underneath it.** The Occam PRD's stated end state is "full close," reached not by trusting the model more but by *promoting judgments into deterministic rules*: per-rule clean-streak counters, demotion on the first correction, and invariant-gated automation switches. This is the right design. It cannot safely be turned on until the confirmed review findings are fixed — an agent auto-approving into a poster that does not assert debits equal credits would industrialise the error. **Fix the invariants first, then automate.** Seam: the existing `occam_bulk_decide` / `occam_post_journals` tools plus a new graduation ledger.

**3. Estimated-tax and deadline chasing.** Already specified (`prd-estimated-tax-reminders.md`, issues #56–#58) and unbuilt. An agent surfacing "who owes what, when" across all clients and drafting the reminder — with the existing never-auto-send rule intact — is a small, contained, high-value win. Seam: the `estimate_payments` table and the existing `.eml` draft mechanism.

**4. Statement and document extraction as a proposal lane.** Both `credit-review-os` and Occam name this on their roadmaps with the same constraint: extraction may *propose* values a human confirms into the workbook, and never writes a rating, a classification, or a ledger value. Occam's parser findings actually strengthen the case — a model that reads a statement and flags "this ending balance looks like a date, not an amount" would catch precisely the class of bug the regex-based reader currently ships. Seam: `statement_reader` and the linesheet input cells, both behind the existing human-confirmation gate.

**5. Practice-wide status synthesis.** Nothing today answers "what is outstanding, for whom, across every engagement?" in one place. The data exists across `satc_system`'s engagement tables, Occam's period ledger, and the invoicing app. A read-only agent that assembles a daily practice brief needs no new authority — it composes existing read tools. Seam: the read-only halves of both MCP servers.

**6. Regulatory-citation verification.** `credit-review-os` carries an explicit blocking debt: crosswalk page pin-cites unverified against live regulator PDFs, because those sites block automated egress. This is a well-shaped agent task with a human browser in the loop, and it currently gates the first filed workpaper.

**7. Codebase and correctness review.** The most valuable AI work done in this estate so far was not a feature — it was the adversarial multi-agent review that produced Occam's `ULTRA_REVIEW.md` and, from it, the retroactive PRD. Repeating that pass on `satc_system` (whose vault and web surface were audited but whose tax and withholding math has not had an equivalent adversarial pass) and on `invoice-generator` (a live multi-tenant payment app with 7 tests) is probably the highest-value AI application available right now.

### Guardrails any of this must respect

These are not aspirational; they are already encoded in the codebases and their tests, and an outside architect should treat them as constraints on design rather than preferences.

- **The agent proposes; the human commits.** Write tools are unregistered by default in SATC, not merely hidden. Preserve that shape — authority enforced by wiring beats authority enforced by prompt.
- **No LLM in the data path.** Deterministic engines compute the numbers. A model may read, propose, explain, or route; it may never be the thing that produced a rating, a classification, a posting, or a tax value.
- **PII stays split and stays local.** Names and TINs live encrypted in the vault; artifacts, logs, exports, and workbooks carry masked/last-4 values only, with tests that fail the build on a leak. Any cloud-AI feature touching identifiable data needs a §7216 consent workflow first, and de-identification alone is *not* established as sufficient.
- **Drake stays the system of record.** SATC prepares and reconciles; it does not compute or file.
- **Every automated number carries its proof.** Provenance tabs, source-document references, cited crosswalk parameters, and audit tapes are load-bearing, not decorative. An AI-generated number without a proof path is a to-do, not a result.

---

*Prepared 2026-07-29 from a direct review of the working tree of `AJSethuraman/SATC` and fresh clones of `AJSethuraman/occam`, `AJSethuraman/merchant-normalizer`, `AJSethuraman/eventos`, and `AJSethuraman/backpack_battles_assistant`, together with the repositories' own PRDs, review reports, backlogs, and open issues and pull requests. Line counts and test counts are measured from source; maturity assessments combine measured coverage with each project's own documented status. No secrets, credentials, or client data are reproduced anywhere in this document.*
