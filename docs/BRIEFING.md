# SATC — a briefing for someone joining the conversation

Written to hand to another agent or person for brainstorming. It says what this
is, what it is *not*, what has been built, what was learned along the way, and
where the genuinely open questions are.

---

## 1 · What this is

**SATC** is practice-operations software for **one** US tax practice —
Sethuraman Accounting, Tax & Consulting, a solo shop. It runs locally, on the
owner's machine, in a browser at `127.0.0.1:5050`.

The owner's own framing, and the thing to hold onto:

> "This is intended to help be the tax staff accountant."
> "Every form emailed that I didn't need to, everything signed I didn't have to
> worry about."

So the product is **time and attention**, not tax computation.

### What it deliberately is NOT

* **Not a tax engine.** Drake stays the system of record for filed returns and
  computations. SATC prepares and reconciles inputs; it never recomputes tax and
  never e-files.
* **Not a TaxDome / Canopy competitor.** No client portal, no marketplace, no
  multi-tenant anything. One practice, one machine.
* **Not a sender.** There is no SMTP anywhere in the codebase and an
  AST-walking test proves it. Every client-facing artefact is a *draft* the
  owner copies into their own mail client.

That last one is a principle, not a limitation-for-now: **the value has to come
from making the click cheap, not from removing the click.**

---

## 2 · Shape of the thing

Four layers, and a change belongs in exactly one of them:

| Layer | Where | Rule |
|---|---|---|
| **Config** | `configs/*.yaml` | Domain knowledge is data. Hand-editable. Hot-reloaded. |
| **Pure logic** | `src/satc/<area>/` | No Flask, no SQL. Each area has its own test file. |
| **Persistence** | `src/satc/persistence/` | SQLite. **Vault** (encrypted PII) physically split from **mart** (de-identified working data). |
| **UI** | `src/satc/app/*_views.py` | Thin. Gathers input, calls the engine, renders what it says back. |

~130 Python modules, **1351 tests**, 56 commits on the current branch.

A **local LLM** (Ollama) is wired in as a read-only assistant — it can read
aggregated views and pick between pre-written options. It cannot send, sign,
file, confirm a staged value, or compute a tax figure, and not by prompting:
those capabilities do not exist on its tool surface and the engine refuses them
from every path.

---

## 3 · The doctrine — the most distinctive thing here

`docs/DESIGN-PRINCIPLES.md` holds 17 principles. **Each is enforced by a test,
not by intention**, and the file is updated in the same commit as the decision
that changes it. It exists because the sister project accumulated seven
false-passing checks and nobody noticed.

The ones that do the most work:

1. **Never invent a value.** No fact → the slot is *visibly* marked. Never
   blanked, never plausibly defaulted.
2. **Facts are recorded, never inferred**, and carry *how we know*. Whether an
   employer files a 941 or a 944 is assigned by the IRS in writing — it is not
   derivable from last year.
3. **Computed, never stored.** A due date is a rule landed on a calendar.
   `configs/obligations/*.yaml` contains **no dates at all**.
4. **Law and firm policy never look alike.** Statute is computed from a cited
   rule and cannot be argued with; a firm cutoff is a preference the owner
   changes over coffee. Different files, different loaders, different rendering.
   *A missed SLA is an apology; a missed deadline is a penalty.*
5. **Refuse rather than default.** A state with no sourced rules **raises**; it
   does not fall back to the federal calendar.
6. **The model proposes; the engine disposes.** The actor is *derived from
   request context*, never accepted as an argument — nothing can *claim* to be
   the owner, it can only *be* in a live browser request.
6a. **The model chooses from a finite set.** It returns a KEY; the engine looks
   up the text. Free generation has an infinite output space, so nobody can ever
   read every sentence that might reach a client.
9. **Propose, never dispose.** One click, not zero.
11. **Only masked identifiers leave the machine** — and **the machine holding
   the vault does not face the internet.**
12. **A check that has never failed is not evidence.** Invariants are
   mutation-tested: break the rule on purpose, confirm the suite catches it.
13. **A queue that becomes noise is worse than no queue.** A row that can never
   be cleared is the one that teaches the owner to scroll past.

---

## 4 · What is built

**Working end to end, verified through the real app:**

* **Interview → engagement.** One set of answers fans out to document requests,
  a priced quote, the statutory deadline (from a cited rule, not a typed date),
  and the engagement-letter facts. Generating twice is a no-op.
* **Work queue** (`/work`). "What can I pick up right now, and which first."
  The job *stage* is **derived** from documents and task state, never stored —
  a stored status lies the moment a document arrives. Ordering weights are firm
  policy in `configs/firm_policy.yaml`.
* **Today queue.** Deterministic proposers: chase documents, chase signature,
  extension candidate, unbilled work, overdue invoice, unissued draft.
* **Billing.** 12-service catalogue, six sliding-scale rate plans. An invoice
  shows **full value → the named discount → what is due**, because someone on a
  reduced rate should see what they were given. Contingent fees are
  *structurally inexpressible* (Circular 230 §10.27).
* **Payments.** A ledger, not a flag. Part payments, overpayments, and a
  three-rung reconciliation ladder — reference match, sole-amount match, then a
  shortlist a human or model picks from.
* **Comms.** 18 templates, per-client drafts, unfilled slots visibly marked.
* **Obligations calendar.** Federal + Massachusetts, IRC §7503 weekend/holiday
  shifts, refuses unsourced states.
* **Documents.** Intake, classification, staging gate, content-hash ids,
  accuracy scoreboard.
* **Pricing editor** (`/pricing`). Edits the YAML *surgically* — comments
  intact, one-line diffs — with a dated change record: what, when, who, from →
  to. Detects hand edits and records them as authorless rather than pretending
  the log is complete.
* **Withholding estimator**, paystub reading, Excel export, Drake seam.

---

## 5 · The direction, stated as decisions

**Config-first.** Anything the owner might reasonably disagree with is a YAML
edit rather than a code change: prices, rate plans, SLA durations, queue
ordering weights, which services an interview answer implies, comms wording.
The owner has said clearly they will not exercise this for a while, so the bias
is toward *making disagreement cheap later* rather than guessing correctly now.

**The interview is the origin fact.** Everything about an engagement is derived
from those answers rather than maintained beside them. A second place to record
"this client has a rental" is a second place for it to be wrong.

**Collection lives elsewhere.** Taking card payments needs a public webhook
endpoint. The sibling `invoice-generator/` project already has one, deployed,
with Stripe. SATC records that money arrived and reconciles it; it never holds a
card. *The machine with the identity vault stays off the public network.*
**This seam is designed but not built.**

---

## 6 · What the build process taught — worth a brainstorm on its own

Work has been done by **fan-out agent teams**: 3–4 build in parallel on disjoint
file sets, then an equal number **recheck adversarially**, explicitly told *not*
to read the fix reports but to reproduce through the real app and real store.

That structure has been worth more than the building. Findings that a **fully
green test suite** did not catch:

* An **invoice issued with zero lines** — a bill for $0.00 against work that was
  done, sitting in the register looking ordinary.
* **Changing a rate plan's discount retroactively repriced every issued
  invoice.** A client paid $337.50; the record said $270.00.
* A **1999 cheque auto-matched a 2026 invoice** on amount alone, with nobody
  deciding.
* A payment hash that **silently destroyed revenue** when two identical cheques
  arrived the same morning.
* A guard that let you **cut a bill 60% with nothing recorded** — the engine
  refused, the screen routed around it.

### The one defect shape that recurs

**A guard is put on the path the fixer was looking at, and the other path stays
open.** Found at least six times: the rate override (view, not engine), the
payment hash (one id shape), the quote's unit check (client, not config), the
condition validator (`services:` but not `tasks:`), the SLA scope (year filtered
unconditionally, client only `if client_id` — *one line apart, by the agent that
had just fixed the year*), and the engagement letter (browser door guarded, agent
door not).

The rechecker's standing instruction is now literally: *"Is this on ONE path or
ALL of them? Try the other one."*

### The second shape: environment monoculture in tests

* Every store test builds a **fresh temp database** → the migration path had no
  coverage *by construction* → a column added to the DDL and not to `_migrate`
  passed everything and corrupted real installs.
* Every test ran on **one line ending** → a cross-platform failure reached CI.

Both are the same lesson: *if all tests share an environment property, that
property is untested.*

This is why `scripts/demo_arc.py` exists — it drives a whole engagement over
HTTP against a store **with a history**, and found the $0 invoice in under a
minute.

---

## 7 · Genuinely open — good brainstorm material

**Needs the owner, not an agent:**
* Ohio obligation rules — the state site defeated seven scraping attempts.
* A Massachusetts discrepancy: Form 1-ES says June 16, Form 355-ES says June 15.
  Needs a call to DOR. Parked with the uncertainty *recorded*, not guessed.

**Design questions with no settled answer:**
* **Facts that don't exist yet.** Several SLAs cannot be measured because
  nothing records "the documents went complete at", and a notice response goes
  to the *agency*, not the client. The module refuses rather than substituting a
  proxy. Is that right, or is approximate measurement better than none?
* **Cross-job dependencies.** A 1065 whose K-1s gate three 1040s is the real
  case, and nothing models it — so the work queue's "does finishing this unblock
  other work" factor only sees *within* a job.
* **Document-reading accuracy at scale.** The vision fallback is unmeasured
  because the corpus has no scans. How do you test an AI reader honestly?
* **Does the queue order match a real March?** Entirely unvalidated. The owner
  has not used it in a season and will not for a while.
* **Bloat.** The doc names the smell — a field nobody writes, a status nobody
  sets, a config knob with one caller. Some has been cut; more probably needs to
  be.

**Known broken, catalogued:**
* Nothing on a 1040 plan reaches the "blocks starting prep" class — the
  classifier does not fire, and the screen *says so on itself*.
* `rate_on` answers historical questions from today's file without checking the
  fingerprint first.
* A price file re-saved in Windows ANSI encoding 500s the pricing screen.

---

## 8 · If you want the code

* `docs/DESIGN-PRINCIPLES.md` — read first. It is short and binding.
* `docs/LOCAL-LLM-PATTERN.md` — the ten rules for anything touching the model.
* `satc_system/ARCHITECTURE.md` — which layer a change belongs in.
* `satc_system/scripts/demo_arc.py` — the whole arc, runnable.
* `PYTHONPATH=src pytest -q` from `satc_system/` — 1351 tests, ~3 minutes.
