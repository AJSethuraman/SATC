# What is in this repository

Produced 2026-08-22 by a four-agent sweep of the whole tree, every open PR, and
all 76 remote branches. Written down because the same facts kept being
rediscovered: the interview's governing PRD sat in `docs/` unreferenced for
weeks, and a whole unmerged project has been riding along on twelve branches
without a PR of its own.

Every claim below was checked against the repository. Where two agents
disagreed, the disagreement is noted rather than averaged.

---

## 0 · The two tenet files, and why they are named here

Added 27 August 2026, because both were written and neither was reachable from
anywhere. A document nobody can find is a document nobody reads, which is the
drift failure they are themselves about.

- **`docs/SOFTWARE-TENETS.md`** — 32 tenets for the code, each cited to a real
  bug in this repository. Read before writing software here, and before
  claiming something works. Its §0 is the shape of nearly every bug this
  project has produced: **something reported success without having done the
  work**, because the verifier looked at a proxy rather than the thing.
- **`satc-handoff/00-START-HERE/DOCUMENT-TENETS.md`** — 28 tenets for anything
  a client reads, mined from the firm's own line-by-line notes and the diffs
  those notes produced. Read before writing or editing a client document. Its
  Part 6 is what stops a concision pass from over-cutting.

---

## 0b · The controls layer, built 27 August 2026

The firm's distinction, and the reason this section exists: **a test asserts a
property on a fixture; a control runs on real work, on its way to a real
client.** There were 749 tests and one control that could actually stop
something. There are **1,125** now (re-counted 29 August), and the controls below. Every bug found in the two days before this was the same shape —
software reporting success without having done the work, because the verifier
looked at a proxy rather than the thing.

| Control | Command | What it stops |
|---|---|---|
| **Pre-send gate** | runs inside `package` | A pack leaving the building that does not render, references a file it does not carry, misnumbers its sections, has an empty bullet, carries a deleted sentence, uses banned wording, has lost a compliance negation, cites a section that does not exist, or promises an enclosure it does not contain. **Blocking, with `--force --reason` logged to the engagement.** |
| **Tenet linter, exact half** | eight checks, same gate | Prose defects, from `registry/retired.yaml` and `registry/required.yaml`. Every check reports how many things it examined; one with nothing to look at prints `NONE`, never `ok` |
| **Tenet linter, advisory half** | `package --notes`, `notes.py` | Ten judgement checks (A1–A10) that **never block and never change the exit code**. Each carries the condition on which it may be promoted. Thirteen further tenets were measured and dropped — see `docs/tenet-mechanization.md` |
| **Lifecycle events** | `cli.py event --kind <k>` | Four documents no preparer could produce — delivery, organizer cover, extension notice, disengagement. Questions in `registry/lifecycle.yaml`; inverse flag pairs derived from one answer so neither can be silently false |
| **Returning client** | `cli.py returning --engagement <last year>` | Last year's answers reused without being confirmed. Nine carry and are all still asked; thirteen deliberately do not, and the command prints why for each |
| **Deploy gate** | `.github/workflows/deploy-invoicer.yml` | A red suite reaching a live payment system. Needs `RENDER_DEPLOY_HOOK_URL` and Render auto-deploy off |
| **End-of-cycle reconciliation** | `cli.py close`, `cli.py reconcile [--apply]` | The January interview and the April return quietly disagreeing. Nothing is read out of Drake; an engagement nobody closed reports as NOT CLOSED rather than being skipped |
| **Demonstration harness** | `cd client-documents && python exercise.py` | "Produced" meaning "wrote bytes". 29 scenarios, 190 documents, every one opened |
| **Generated procedures** | `cli.py procedures [--check]` | A written procedure drifting from the software. Every step is read out of the code that runs it; `--check` fails in the suite |
| **Signature register** *(29 Aug)* | `cli.py sign [--sent HOW] [--record DOC/FIELD]` | Six places in the code calling the engagement letter "signed" while nothing recorded a signature. Who must sign is censused off the templates' own `sigrow`/`siglab` blocks, so it follows the documents; the e-file authorization is declared in `registry/signing.yaml` because Drake prints it and our census cannot see it. `may_file` reports the 8879 and the unsettled invoice as **unknown, never as passed**. With no engagement it sweeps every one, overdue first, and skips a record it cannot read rather than counting it clear |
| **Covering email** *(29 Aug)* | `cli.py package --ready`, `outgoing.py` | A covering note typed from memory, and a pack attached to the wrong client. Writes an ordinary `.eml` — addressed, attached, written — and **sends nothing**: a test asserts the module names neither `smtplib`, `requests`, `urllib` nor `socket`. **Refuses to compose** while the wording is still a `[CONFIRM: ]` |

`docs/OPERATING-PROCEDURES.md` is generated. Do not edit it.

---

## 1 · The shape of it

**16 top-level folders, 76 remote branches, 34 open PRs.** Roughly half the
tree is practice-operations software; the other half is credit and macro
analytics for a separate consulting line.

| | Folders | Lines |
|---|---|---|
| **Practice operations** | `satc_system` · `satc-handoff` · `client-documents` · `invoice-generator` · `website` · `cowork-plugin` | ~59,000 |
| **Credit / macro analytics** | `credit-review-os` · `stock-helper` · `fdic-peer-monitor` · `cfpb-mortgage-monitor` · `edgar-crit-class-tracker` · `fred-credit-risk-dashboard` · `bureau-credit-risk-dashboard` · `macro-early-warning-dashboard` · `bls-laus-county-monitor` | ~49,000 |

**Corrected 27 August 2026: `CLAUDE.md` now documents all sixteen** — six
practice-operations folders and `docs/` in its table, the nine analytics
projects named in prose and governed by `PROJECTS.md`. The paragraph below is
the finding that produced the fix, and is kept because the failure it describes
is the one this whole file exists against.

**`CLAUDE.md` documented four of the sixteen.** It omitted `client-documents/`
and `satc-handoff/` — the two folders where the document pipeline and the
brand system live — and all nine analytics projects. Since `CLAUDE.md` is the
file loaded into every agent session here, an agent starting fresh does not
learn that the interview, the pricing engine or the templates exist. `PR #100`
made the same observation on 2026-07-29: *"An architect reading only CLAUDE.md
would see roughly a third of the codebase."* It was still true today.

## 2 · What actually works

Verified by running it, not by reading it.

| Component | State | Evidence |
|---|---|---|
| **`satc_system`** | **Works.** 12,664 LOC, 87% coverage | `259 passed`, 0 skipped. Built a 16-sheet workbook; LibreOffice evaluated **202 formulas, 0 errors**. Withholding math hand-checked against brackets. 56 Flask routes, all 200 except three deliberate guards |
| **`invoice-generator`** | **Works, deployable — with one thing to fix before real money.** Multi-tenant SaaS | 57 tests, and `exercise.py` runs 281 checks through real HTTP, **opening all 53 PDFs it produces** and comparing their totals against the database. Deploys are gated on CI (`.github/workflows/deploy-invoicer.yml`) — inert until `RENDER_DEPLOY_HOOK_URL` exists. **`amount_paid` is one mutable float with no ledger**: one click of "mark as unpaid" destroys a Stripe-confirmed payment and replaying the webhook will not restore it. Eleven more, ranked, in `docs/invoicer-scenarios.md` |
| **`client-documents`** | **Works, end to end, and can prove it.** Interview → engagement → priced documents → the whole later life of a client → the signature, and the email it travels in | **1,123 passed, 2 skipped** (1,125 collected, re-counted 29 Aug; 1,077 on 28 Aug, and the 914 here was the figure on 22 Aug), across **21 commands** and **24 photographed walkthrough screens**. `exercise.py` runs 29 real scenarios producing 190 documents, **opening every one in a browser**, then re-quotes all 27 live engagements and re-renders the estimate. Every document a client receives passes a blocking pre-send gate. The delivery letter, organizer cover, extension notice and disengagement letter gained a front door on 27 Aug (`cli.py event`); a live engagement became re-quotable on 28 Aug (`cli.py requote` — before that an engagement was priced exactly once, at the moment it was created); and the signature and the covering email landed on 29 Aug |
| **`cowork-plugin`** | **Works**, if the desktop app is running | Three stateless withholding tools. Cannot write anything |
| **`website`** | **Live** on satcllp.com via Cloudflare Pages | 11-step branching intake; leads land in `SATC leads.xlsx` |

`satc_system` needs `openpyxl`, which is a real project dependency rather than
a dev extra. Without it the suite does not fail — it fails to *collect*, which
reads like a broken repository. `pip install openpyxl` and it passes.

## 3 · Correctness risks, in priority order

These are the findings that could produce a wrong number for a client.

1. **OBBBA (P.L. 119-21, July 2025) is not reconciled into the tax crosswalks.**
   TY2025 carries `salt_deduction_cap: 10000` and `bonus_depreciation_pct: 0.40`
   — pre-OBBBA values, flagged in-file as `scheduled_reversion`. A preparer
   relying on either today would be relying on superseded law. The files are
   honest about it; nobody has acted on it.
2. **Ohio 2025 brackets are 2024 copied forward**, self-documented: *"mirrors
   2024 as a placeholder — VERIFY."*
3. **`federal/2026.yaml` is labelled "VERSIONING TEST FIXTURE"** and ships in
   the same directory as real law. The estimator correctly refuses to use it.
4. **`qss` filing status raises `KeyError`** in the withholding estimator. The
   crosswalk supplies qss data; `_STATUS_TO_XWALK` maps only four of five.
5. **LTCG 15%/20% rates are hardcoded and uncited** while their thresholds are
   config-driven — inconsistent with the design everywhere else.

Everything else in the tax data is unusually disciplined: parameters cite Rev.
Proc. and IRC sections, carry `retrieved` dates, and `TaxTables._v()` **raises
rather than substituting** when a value is unpublished.

## 4 · Blocked on a human

**Re-measured 28 August 2026.** Most of what this table used to list is closed.
`cd client-documents && make doctor` now reports *"No open decisions. Real
renders will produce documents."* — the legal name, the four materials
deadlines, the acknowledgement window, the billing address, the hard-no list and
every fee figure are settled and wired in. `fee-schedule.yaml` carries a real
hourly `rate: 150` and real amounts. **Five live `[CONFIRM:` placeholders remain
in the whole tree** — four on 28 August, plus the covering note added with
`outgoing.py` on 29 August, which is one decision written across a subject line
and a body. Everything else that greps as one is prose *about* the convention or
a historical log entry.

| | What it blocks |
|---|---|
| **RITA: one locality or several?** | The local-return count, and so the fee on any Cleveland-area client. `registry/interview.yaml:445` |
| **The document-request wording** | Nothing — it has a working default. `registry/document-requests.yaml:100` |
| **Square or Stripe** | **Every invoice.** The settled payment sentence names a Square link; the invoice has 41 merge fields and none is a URL, and there is no Square code in the repository. The firm's leaning, 28 Aug: *"square is fine for now I think maybe price dependent."* A leaning, not a decision — nothing should be built against either until it is one |
| **Getting a signature** | **Re-measured 29 Aug: the software half is built and the vendor half is decided.** `cli.py sign` records who signed what, by what means and when, chases what is outstanding, and `may_file` reports what it cannot see rather than assuming it. **Option A, decided 28 Aug: Encyro carries the signature, sent by hand; the software tracks and chases.** Not an API vendor — Encyro has no customer API. What is still blocked on a human: **the covering-note wording**, a `[CONFIRM: ]` in `registry/signing.yaml` that `outgoing.py` refuses to compose past, and the four-question email to Encyro in `docs/research-e-signature.md` §5/§5b |
| **Reading Pub 1345 with human eyes** | Any sentence anybody writes about identity proofing. **No regulatory wording in `docs/research-e-signature.md` was read from a primary source** — this environment's proxy answers 403 on CONNECT for `irs.gov`, `govinfo.gov`, `uscode.house.gov`, `codes.ohio.gov`, `ecfr.gov` and `ftc.gov`, and for every vendor domain. Whether Pub 1345's KBA regime reaches **8879-CORP and 8879-PE** is governed by Pub 4163 and is genuinely unresolved; `registry/signing.yaml` names the forms and asserts nothing |
| **A second copy of the data** | Nothing today, and everything tomorrow. Engagements are plain files on one disk and `satc_system`'s vault is two local SQLite files. No sync, no backup, anywhere in the code |
| **`RENDER_DEPLOY_HOOK_URL`** | The Invoicer deploy gate, built 27 Aug and **inert** until the secret exists and Render's own auto-deploy is turned off |
| **Invoicer's `Payment` table** | Nothing today. A schema change to a live payment system, and the only remaining Invoicer bug that is about money rather than a cent or a symbol |
| **The amendment paragraph** | Nothing today — the letter names the return correctly ("Amended Form 1040") since 27 Aug. What the firm *says* about an amendment engagement is unwritten |
| **The entity request list** | Nothing today. Two lines were transcribed from section 04 of the business letter on 27 Aug and carry a `[CONFIRM:` for shortening or splitting |
| **`accompanies` on T20's list** | The plain-language check. It is banned in `DOCUMENT-TENETS.md` and live, unobjected-to, in five templates; the linter ships without it and the tenet carries a `[CONFIRM:` |
| **Template approval** | All **twelve** are complete; none is approved |

**On prices, this was true on 22 August and is not any more.** `fee-schedule.yaml`
now carries the firm's own figures — an hourly rate, package amounts, per-unit
prices and allowances — derived with `cli.py hours` from hours × rate rather
than typed, and the same numbers are published on the price page with a build
check that fails if the two ever diverge. The paragraph below is kept because it
is the history of how the figures were arrived at.

**As of 22 August 2026, the firm had never written a price down.**
The whole tree was searched. The `450 / 185 / 95` set traces to a single
illustrative JSON payload used to demo a template, and every reappearance is
labelled fictional. `invoice-generator` — the one component that moves money —
contains no fee schedule, no rate card and no seeded invoices.

`PLAN.md` does hold real competitor research: Drake Portals $230/yr, TaxDome
~$800/user/yr, Canopy $540–800/yr, SafeSend $13–17/return, e-sign ~$1/signature.

## 5 · Stranded work worth harvesting

### `drake-entry-assistant/` — 38 files, on twelve branches, on none of their PRs, not on `main`

The most valuable orphan here. `satc_system`'s own Drake module says the
keystrokes are done *"by the preparer (or a separate automation tool not part
of this repo)."* **This is that tool**, sitting unmerged: validation engine with
source-cell traceability, YAML screen maps for Drake 2025, an adapter seam,
masked action plans, 16 test files.

Its README is honest that live UI automation is not implemented — so what is
harvestable is the architecture, not working automation. Newest tree is on
`claude/tax-withholding-estimator-R5N9p`.

### PR #13 — capabilities with no counterpart on `main`

PAdES tamper-evident PDF signing · per-client retention archives with keep-until
dates · **Encyro packet export** (the delivery step nothing else implements) ·
AR aging buckets · year rollover · engagement-letter / 8879 / filed trackers ·
extraction diagnostics · per-form Drake CSV export.

### PR #12 — `tax_packet_qa`

Packet-completeness QA over an already-sorted client folder, producing
**auto-drafted client follow-up questions** from what is missing. Not
superseded: `satc_system` does workflow checklists, not completeness QA.

### PR #4 — `occam_template_desk`

Merge core is superseded. Worth lifting: the **Ready / Needs-Review / Blocked**
validation model, per-field source provenance, and an output package carrying
an audit log plus an input snapshot.

### Merge hazard — read before touching the old PRs

**PRs #1–#23 share no ancestor with `main`.** Merging any one re-adds
`drake-entry-assistant/` and sometimes an old `invoice-generator/`. Harvest with
`git show <branch>:<path>` onto a fresh branch off `main`. Never merge them.

**PR #143 is a content superset of #140, #141 and #142** — merge it and close
those three rather than merging four.

`feat/comms-templates` is a 688-file tree tracking `main` with **no open PR**.
Look before deleting.

## 6 · Documents that are stale and not marked

| File | Why |
|---|---|
| `website/README.md` | Old rejected palette; says GitHub Pages only and *"Later: connect satcllp.com"* — Cloudflare Pages is live |
| `website/GOING-LIVE.md` | Concludes "Path A is the job"; Path B was taken |
| `satc-handoff/START-HERE.md` | Says six templates; there are **twelve** — a C-corporation letter was added 26 Aug, and the count has been wrong twice now |
| `satc-handoff/00-START-HERE/OVERNIGHT-BRIEF.md` | Contradicted by its own inline correction |
| `satc_system/README.md`, `docs/METHODOLOGY.md` | Describe the vault as external SharePoint; it is a local encrypted SQLite vault |
| `PLAN.md` §"Where things stand" / §"In flight" | Old branch, old PR, "242 passing" vs "259 passing" in the same file. Also claims the plugin bundle path is broken — **it is not**, verified on this branch and `main` |
| `01-WEBSITE/SATC-STYLE-SPEC.md` | Still asks about licence and SoS numbers that were decided "not to be printed" |
| ~~`CLAUDE.md`~~ | ~~Documents 4 of 16 projects~~ — **fixed 27 Aug**; all sixteen are now reachable from it. Its `client-documents` test count was still the 22 Aug figure and was corrected to 1,123 on 29 Aug |

## 7 · Rules a builder here must not break

Gathered from `AUTHORING-CONTRACT.md`, `CLAUDE.md` and `PLAN.md`, because they
are scattered:

- **Never invent** legal, regulatory or assurance wording, fee figures, rates,
  or firm-policy deadlines. *"Invented legal wording is worse than a blank. A
  blank gets filled; an invention ships."*
- **Assurance vocabulary is banned** — audit, assurance, attest, opinion,
  review engagement, examination — except in explicit negation. A compliance
  rule, not a style rule.
- **No TIN anywhere** in the interview record. A denylist test enforces it.
- **Fail loudly** on any unresolved `<<` or `[[`. A letter reaching a client
  with `<<ClientLetterName>>` in it is *"the one bug that costs a client."*
- **A refusal writes nothing.** A refusal that left a file on disk would be
  worse than none, because somebody would send it.
- **Drake stays the system of record.** SATC prepares and reconciles inputs; it
  does not replace Drake's computations or e-file.
- **The FTC Safeguards Rule applies to a solo preparer.** The under-5,000
  exemption waives four *written* deliverables only — encryption at rest and
  in transit, MFA and access controls are **not** waivable.

---

## The session handoffs, which carry what a snapshot cannot

This file says what is true. It does not say what was decided, by whom, in what
words, or which of an agent's claims the firm corrected — and those are the
things that vanish when a container is wiped. They are written down per session:

- **`docs/handoff-2026-08-26.md`** — the fee schedule finished, cheapest-eligible
  selection moved into the engine, and six bugs that share one shape.
- **`docs/handoff-2026-08-29.md`** — re-quoting a live engagement, the signature
  register, the covering email, Option A on signing, the standing constraints
  the firm has set, and two mistakes an agent made that are recorded rather than
  quietly fixed.

## How to refresh this

It is a snapshot, and the tree moves. The four sweeps were: open PRs and
branches · `satc_system` maturity by execution · docs, decisions and research ·
`invoice-generator` + `cowork-plugin` + a whole-tree search for fee figures.
Re-run them the same way and diff against this file.
