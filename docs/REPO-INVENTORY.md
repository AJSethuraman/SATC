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

- **`docs/SOFTWARE-TENETS.md`** — 27 tenets for the code, each cited to a real
  bug in this repository. Read before writing software here, and before
  claiming something works. Its §0 is the shape of nearly every bug this
  project has produced: **something reported success without having done the
  work**, because the verifier looked at a proxy rather than the thing.
- **`satc-handoff/00-START-HERE/DOCUMENT-TENETS.md`** — 28 tenets for anything
  a client reads, mined from the firm's own line-by-line notes and the diffs
  those notes produced. Read before writing or editing a client document. Its
  Part 6 is what stops a concision pass from over-cutting.

---

## 1 · The shape of it

**16 top-level folders, 76 remote branches, 34 open PRs.** Roughly half the
tree is practice-operations software; the other half is credit and macro
analytics for a separate consulting line.

| | Folders | Lines |
|---|---|---|
| **Practice operations** | `satc_system` · `satc-handoff` · `client-documents` · `invoice-generator` · `website` · `cowork-plugin` | ~59,000 |
| **Credit / macro analytics** | `credit-review-os` · `stock-helper` · `fdic-peer-monitor` · `cfpb-mortgage-monitor` · `edgar-crit-class-tracker` · `fred-credit-risk-dashboard` · `bureau-credit-risk-dashboard` · `macro-early-warning-dashboard` · `bls-laus-county-monitor` | ~49,000 |

**`CLAUDE.md` documents four of the sixteen.** It omits `client-documents/`
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
| **`invoice-generator`** | **Works, deployable.** Multi-tenant SaaS | Auth, email verification, Stripe Connect, JSON API with per-user keys, rate limiting, CSRF, Render config. **One test file**, covering arithmetic only — nothing tests auth, tenancy isolation, the webhook, or the API |
| **`client-documents`** | **Works.** Interview → engagement → priced documents | 197 tests. Browser and CLI front doors over one core |
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

| | What it blocks |
|---|---|
| **`legal_name`** | **Every template.** Three variants appear across the ten templates and only one can be on the Ohio filing. It is *hardcoded in footers, not merged*, so the engine's `[CONFIRM:` guard cannot catch a wrong one — it ships silently. `firm-settings.yaml`: *"Until this is settled, no template should ship to a client."* |
| **Fee figures** | The estimate. Sixteen `[CONFIRM:` amounts plus one structural decision |
| **Nine firm settings** | Every real render — four dates, two sentences |
| **The financial-statement legend** | Three documents |
| **Template approval** | All ten are complete; none is approved |

**On prices, the answer is definitive: the firm has never written one down.**
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
| `satc-handoff/START-HERE.md` | Says six templates; there are ten |
| `satc-handoff/00-START-HERE/OVERNIGHT-BRIEF.md` | Contradicted by its own inline correction |
| `satc_system/README.md`, `docs/METHODOLOGY.md` | Describe the vault as external SharePoint; it is a local encrypted SQLite vault |
| `PLAN.md` §"Where things stand" / §"In flight" | Old branch, old PR, "242 passing" vs "259 passing" in the same file. Also claims the plugin bundle path is broken — **it is not**, verified on this branch and `main` |
| `01-WEBSITE/SATC-STYLE-SPEC.md` | Still asks about licence and SoS numbers that were decided "not to be printed" |
| `CLAUDE.md` | Documents 4 of 16 projects |

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

## How to refresh this

It is a snapshot, and the tree moves. The four sweeps were: open PRs and
branches · `satc_system` maturity by execution · docs, decisions and research ·
`invoice-generator` + `cowork-plugin` + a whole-tree search for fee figures.
Re-run them the same way and diff against this file.
