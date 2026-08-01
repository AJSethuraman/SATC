## The gap, in one sentence

SATC today is a **document intake system with a workflow generator bolted onto it**. A staff accountant is a **closing loop**: it knows what is owed, by when, what is missing, what is inconsistent, and it refuses to let the file advance until each of those is answered or explicitly overridden with a recorded reason. SATC has the inputs (documents, prior-year mart, intake answers) and the outputs (keying worksheet, comms templates, withholding estimator) but has **no durable record of work state and no clock** — nothing in the app is ever overdue, blocked, waiting, stale, or refused.

That has a second consequence that drives the entire ordering below. The binding doctrine is *the model proposes; a deterministic engine verifies, refuses, or executes*. **SATC currently has no engine that can refuse.** Every gate that would make an 8B junior safe — legal status transitions, open-items-must-be-empty, signed-after-delivered, explain-the-variance — does not exist yet. So "add the AI junior" is the last slice, and every slice before it is the supervisor being built.

---

## 1. Capability gap

Honesty key: **solid** = works, tested, in the live path. **partial** = exists but incomplete for practice use. **demo-only** = vocabulary/schema exists, nothing drives it. **stub** = dataclass with no table and no caller. **none** = greenfield.

### A. Work state and the clock

| Capability the research says a practice needs | SATC today | Layer it belongs in | Nearest existing code / note |
|---|---|---|---|
| A durable work record per unit of work, with a legal status machine | **demo-only** | state (new events table) + pure logic (transition fn) + thin UI | `PipelineStatus` (`models/mart.py:28`) is written in exactly one place, hardcoded `"In prep"` at `app/state.py:357`. No transitions, no guards, no history. |
| Append-only event log naming the actor (human vs model+version) | **none** | state | Nearest is `DocumentRecord.actor`/`as_of` — one mutable row, not a log. |
| Statutory due dates computed per entity type / fiscal year end / jurisdiction | **none for returns** | config (dated) + pure logic | `ReturnRecord` has **no due date column at all**. Only date math in the repo is `calculate_suggested_date` (`intake/workflows.py:219`), a single-anchor subtraction. |
| Weekend/holiday shift, extension lengths (1041 = 5½ mo), non-extendable forms | **none** | config (dated) + pure logic | greenfield |
| "Overdue" / "stale" / "blocked" as computed facts | **none** | pure logic | Nothing anywhere compares any stored date to today. `suggested_date` is a hint no code reads. |
| Extension as a first-class in-progress branch (reason code, client authorization artifact, extended due date, estimated payment) | **none** | config + state + thin UI | `ReturnRecord.is_extended` is a bare bool with no extended-date column, no reason, no authorization. |
| Document cutoff date → auto extend-candidate flag | **none** | config (firm policy, visibly separate from statute) + pure logic | greenfield |
| Perfection-period / reject / stockpiling clocks | **none** | config (per form family) + pure logic | greenfield |
| Entity→owner blocking edge (a 1065 K-1 blocks the partner's 1040) | **partial** | config + pure logic | `relationships` table is solid; `_relationship_templates` (`workflows.py:294`) is hardcoded Python branching on three literal workflow keys. Pattern demo, not a facility. |
| Client-facing status coarser than internal stage | **none** | state + config (comms) | SATC's own design choice, not a sourced industry finding — but cheap and it stops internal stage names leaking into client text. |

### B. Client documents and the chase

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| Documents register Requested / Received / Sent / Signed / N/A | **solid** | state | `models/mart.py:169`, mutation seam at `state.py:138` → `store.py:334`. |
| N/A with a **mandatory reason** | **partial** | state + thin UI | `N/A` exists; only a free-text `note`. The reason is the audit trail §10.34(d) wants. |
| Blocking vs expected-late document classes (W-2/W-2G/1099-R block e-file per Pub 1345; K-1 and consolidated 1099 do not block prep) | **none** | config + pure logic | This distinction is the difference between a usable queue and one where nothing is ever eligible. |
| Provenance on receipt: how, when, from whom (26 CFR §1.6695-2(b)(4)(i)(C)) | **none** | state | Legally required for any return claiming EIC/CTC/AOTC/HOH. |
| Follow-up cadence with a round counter, escalation after the 2nd, termination on completion | **none** | config + pure logic + thin UI | greenfield. This is the single most staff-accountant-shaped feature in the roadmap. |
| Expected-document list derived from the prior year | **partial** | pure logic | `prior_1040` extraction map + prior-year mart exist; no diff engine. |
| Omission detector ("payer present last year, absent this year") | **none** | pure logic | The highest-leverage thing an automated junior can do before a human touches the file. |
| Content-based classification + human confirmation gate | **solid as logic, partial in practice** | state (needs staged tables) | `StagingGate` is **in-memory only** — `persistence/store.py` has no staged tables. Restart mid-review and un-posted confirmations are gone. `document_id = path.name` collides across subfolders (`state.py:247`). |
| Automatic request↔arrival reconciliation | **solid but ungated** | pure logic + state | `reconcile_received` (`intake/service.py:166`) is the **only** place an automatic classification mutates durable state. Any model influence here needs a new gate. |

### C. Preparation and review

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| Two-year comparison with a required explanation over a threshold | **none** | config (threshold) + pure logic + thin UI | Mendlowitz's >10% rule; the core review artifact for a 1040. |
| Named deterministic rulesets (missing prior-year 1099 payer, vanished carryforward, unconfirmed estimates, ratio outliers, unaddressed prior-year notice, dependent aged out) | **none** | config + pure logic | Every one is computable against the existing mart. |
| Review notes as objects (type / scope / requires-resolution / cleared-by / resolution text) | **stub** | state + thin UI | `models/review.py` is well-designed and **never instantiated anywhere in `src/`** — its only consumer is an Excel dropdown (`workbook/components.py:73`). No table, no scope FK, no author, no timestamps. |
| Ephemeral critique vs durable inquiry split, with purge-on-close | **none** | state | The real tension: Mendlowitz says destroy review notes at completion; §1.6695-2(b)(3)(i) and §10.34(a)(2) require the *inquiry and response* log to survive. These are two different objects and must be two different tables. |
| Verification invalidation — confirming is a signature over (field, value, source hash), reverting when the source changes | **none** | pure logic + state | Today a confirmation is a boolean over a value. Drake's DoubleCheck already proves the semantic. |
| Open Items as a first-class blocking object | **none** | state + pure logic + thin UI | Only `note`/`notes` single overwritable scalars on four dataclasses. |
| Inquiry record (question text, asked_at, verbatim answer, answered_at) | **none** | state | §10.34(d) + §1.6695-2(b)(3)(i) "contemporaneously document". |
| "Review-ready" as a computed gate, not a percent-complete bar | **none** | pure logic | greenfield |
| Drake keying worksheet ordered to Drake's data-entry sequence, with per-line source-document links and a content-review header | **partial** | pure logic + thin UI | Worksheet exists (`workbook/`); no ordering claim, no source links, no traced/exceptions header. |
| Withholding estimator | **solid** | pure logic | Not wired to produce the "properly estimated tax" figure an extension legally requires. |
| Per-task status beyond done/not-done, assignee, real due date, dependencies | **none** | state (columns on `intake_tasks`) + pure logic | `IntakeTask.completed` is a bool; `intake_tasks` has exactly 15 columns; `_insert_task` (`store.py:395`) is a positional INSERT. |
| Add an ad-hoc task to an engagement | **none** | state + thin UI | Tasks can only exist because a template condition matched. |
| Regeneration that preserves progress | **partial** | — | `regenerate_engagement` (`workflows.py:388`) is implemented **and tested** but wired to no route or template. Re-running the live path mints duplicate `Requested` documents and orphans the old ones forever. |

### D. Signature, filing, and the record

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| 8879 as an ordered two-event artifact (copy delivered → signed, `signed_at >= delivered_at`) | **none** | state + pure logic | Pub 1345: taxpayer must sign *after* reviewing the return, before origination. |
| $50 / $14 re-signature check against a signature-time snapshot | **none** | config (dated, Pub-set not statutory) + pure logic | Pure comparison over Drake's figures — does not violate "Drake is system of record". |
| Drake ACK letter capture (P/A/a/R/B/D/E/S/T/X) + derived downstream clocks | **none** | config + state + thin UI | `D` (duplicate) must hard-block resend; `a` (extension accepted) is a separate branch from `A`. |
| Reject loop: 24h notify, perfection deadline, paper-file fallback, business-rule ID stored verbatim | **none** | config + pure logic | greenfield |
| Retention clocks per artifact class | **none** | config + pure logic + state | Different bases and terms per artifact: 8879 = 3y from later of due/received; 8867 bundle = 3y from the *latest of four* dates keyed off the **unextended** due date; conflict waivers = 36 months from end of representation. A single tax-year purge is wrong. |
| Client records export on request, never payment-gated (§10.28) | **none** | pure logic + thin UI | Excel export exists but produces workpapers, not client records. |
| 8867 per-benefit due-diligence records (four independent) | **none** | config + state + thin UI | Largest per-return penalty exposure in the roadmap. |
| Paper-file branch requiring a Form 8948 reason | **none** | config + state | This is where compliance quietly leaks. |
| §7216 consent artifact as a locked template (Rev. Proc. 2013-14 §5.04 verbatim) | **none** | config (locked) + state | Only needed when an outbound recipient is not the taxpayer. |

### E. Recurring and non-return work

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| Recurring obligations (941/940 filings and deposits, quarterly estimates, information returns, FBAR, state elections) | **none** | config + pure logic + state | `IntakeEngagement.period_end` is a free-text string **set by nothing and read by nothing**. `business_monthly_bookkeeping.yaml` exists but each month is a hand-created engagement with a hand-typed due date. |
| Notices register (jurisdiction, notice number, deadline, disposition, checked next year) | **none** | state + thin UI | Mendlowitz names failing to check prior-year notices as a top-12 error. |
| Season rollover creating next year's work + carrying the document profile | **none** | state + thin UI | `regenerate_engagement` is the nearest seam and it is unrouted. |
| Client attributes that switch a recurring stream on (941 vs 944 — IRS-assigned by written notice; depositor schedule; foreign accounts; PTET states) | **none** | config + state | 944 must be stored as a *fact with a source document*, never inferred. |

### F. Firm-level compliance

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| Encrypted identity vault / de-identified mart split | **solid** | state | The strongest thing in the codebase. |
| Local-only, no-egress posture | **solid** | config + pure logic | `settings.py` env opt-ins + `doctor.py` checks. This is what keeps a local model out of §7216 territory entirely. |
| Append-only audit log (16 CFR §314.4(c)(8), which the <5,000-consumer exemption does **not** lift) | **none** | state | Same table as the work-spine event log. Must log mart ID + last-4, never legal names or full TINs. |
| Firm profile (PTIN / EFIN / Responsible Official) with 30-day e-file-application update tasks | **none** | state + config | Undeliverable mail is grounds for EFIN inactivation — this stops filing mid-season. |
| WISP artifact, PII-location register, recurring security chores (weekly EFIN/PTIN return-count check, backup verification) | **partial** | config + state + thin UI | `doctor.py` is exactly the right seam and already has a `Check` shape. |
| Incident record with next-business-day IRS clock and 30-day / 500-consumer FTC clock | **none** | config + pure logic | Pub 1345 Standard 6 (next business day, no consumer floor) is the *tighter* clock, not the FTC's 30 days. |
| Conflict check at engagement creation + 30-day waiver timer + 36-month retention | **none** | pure logic (query over vault + relationships) + state | The vault can already answer "shared address / shared dependent SSN / prior joint filing". |
| Exception report: where a required step was skipped or overridden | **none** | pure logic + thin UI | This is the §1.6695-2(d) "routinely followed" and §10.36 "procedures are followed" evidence. Without it, an override is invisible; with it, an override is *defensible*. |
| Provenance surviving the store boundary | **partial** | state | `LineItem.provenance` is flattened to two columns and rehydrated as a stub (confidence, extractor, page, document_id lost). `Carryforward`, `OwnerBasis`, `EstimatePayment` declare provenance with **no columns at all**. |

### G. The AI junior

| Capability | SATC today | Layer | Note |
|---|---|---|---|
| Human confirmation gate on model output | **solid for extraction, absent everywhere else** | pure logic | `StagingGate` + HIGH-only auto-confirm is genuinely the SSTS-1.4-shaped pattern. Generalize it; do not weaken it. |
| Model + prompt version stamped on every proposal; accept/correct-rate report | **none** | state + thin UI | This report *is* the "tool is appropriate for its intended purpose" evidence. |
| Model as config author (the ten `key: null` doc types with no extraction map) | **none** | config + pure logic | Highest-leverage, lowest-risk surface: model touches YAML, never a taxpayer figure. |
| Model structurally barred from computing a number or an eligibility determination | **implicit, not enforced** | pure logic + test | Frontier models correctly compute <⅓ of simplified 1040s; an 8B model is far worse. This must be a failing test, not a convention. |

---

## 2. The critical path

Four things must exist before anything else is worth building, and the order is forced by dependency, not by value.

### CP-0 — The persistence layer stops lying

**Why first:** three unrelated things are called "engagement" (`EngagementRecord` = fee row keyed `(client_id, tax_year)`; `IntakeEngagement` = workflow instance; `ReturnRecord` = Drake-side return facts), `ids.engagement_key()` is dead code that already matches one of them, `_migrate()` is a single hardcoded column check with no schema-version table, and `save_mart` uses positional `INSERT OR REPLACE` so widening any existing table silently corrupts every write unless the tuple is edited in lockstep. Every slice below adds tables and columns. Fixing this after Slice 3 means rewriting Slices 1–3.

**The naming decision, made:** stop using "engagement" for the work spine. The spine is an **Obligation** — a thing owed to a jurisdiction (or to a client) by a date. Promote `IntakeEngagement` to it (it is the mature half: it already has `due_date`, `risk_flags`, a task list, and `period_end`), add `obligation_type`, `status`, `extended_due_date`, `period_key`. Rename `EngagementRecord` → `EngagementFee`. Delete `ReturnRecord.status` outright rather than leaving two status fields to drift. This costs a day and it makes notices, payroll, estimates, FBAR and elections first-class without a second workflow engine.

### CP-1 — The work spine: a status you can trust

**Why second:** deadlines attach to it, open items scope to it, review notes scope to it, the 8879 gate is a transition on it, the audit log is its event stream, and the §10.36 / §1.6695-2(d) evidence is a query over its events. Nothing else can be built without inventing a private version of it. The one working precedent in the repo — `set_document_status` validating against `DOC_FLOW`, calling a targeted UPDATE, then syncing memory — is the exact pattern to copy.

### CP-2 — The clock

**Why third:** "overdue", "document cutoff", "extend-candidate", "3-day follow-up", "stockpiling at 3 calendar days", "24-hour reject notice", "perfection period", "retention_until", "quarterly estimate due" are one function family over one holiday calendar. Build it once as dated, cited config, or build it six times inconsistently and get the 1041 September 30 date wrong in five of them. It depends on CP-1 because the computed dates need somewhere durable to land.

### CP-3 — Open Items and the inquiry record

**Why fourth:** it is simultaneously (a) the §10.34(d) / §1.6695-2(b)(3)(i) contemporaneous evidence, (b) what review notes resolve into, (c) what the chase cadence generates, (d) what an 8867 due-diligence inquiry *is*, and (e) the only object the local model is ever allowed to propose into. Chase, review, and due-diligence all reduce to open items with different config. Build any of them first and you build three private inbox implementations.

**After CP-3 the graph fans out.** Slices 4–11 are largely parallelizable; the order given is by value density for a solo practice, with one stated exception (Slice 10 promotes to position 4 if the practice does meaningful EITC/CTC/AOTC/HOH volume — it is mostly config over CP-3's machinery and it carries the largest per-return penalty exposure in the roadmap).

**Slice 12 is last by construction.** The doctrine makes the model a consumer of gates. Every slice above is the gate.

---

## 3. Vertical slices, in dependency order

### Slice 0 — The persistence layer stops lying

**Outcome:** One name for a unit of work, a versioned schema you can migrate safely, and a staging gate that survives a restart.

- **Config:** none. This is structural.
- **Pure logic:** an ordered `migrations` list of `(version, sql)`; named-column INSERT helpers replacing the positional tuples in `save_mart` (`store.py:279`) and `_insert_task` (`store.py:395`); `ids.engagement_key()` retired in favour of `obligation_key(client_id, tax_year, obligation_type)`.
- **State:** `schema_migrations` table; `staged_documents` / `staged_fields` tables (`StagedDocument`/`StagedField` are already plain dataclasses ready to serialize); `document_id` becomes `(content_hash, relative_path)` instead of `path.name`; `delete_client`'s cascade list (`store.py:358`) updated in the same commit.
- **UI:** one new `satc doctor` check reporting schema version and staged-review durability. `/staging` survives a restart.
- **Testing seam:** the store. Open a v1 DB file, migrate, round-trip every table. Assert two files with the same basename in different subfolders produce distinct field ids. Assert confirmations persist across a store reopen.
- **Real-use signal:** the owner closes the app mid-review at 6pm, reopens at 9pm, and every confirmation is still there. `StagingGate._find` can no longer land on the wrong field.

### Slice 1 — The work spine

**Outcome:** Every unit of work carries one status drawn from Drake's own vocabulary, changed only through a function that can refuse, with an append-only event log naming who — or what — did it.

- **Config:** `configs/workflow_states.yaml` — the status enum, the legal-transition table, and the precondition each transition requires. Mirror Drake CSM names for the overlapping states (**Waiting on Documents, In Progress, Under Review, Signed, On Hold, EF Pending, EF Accepted, EF Rejected, EF Ext Accepted, Complete**) so the owner never translates between two systems. SATC-only states (Not started/Rollover, Preparer self-review done, Ready to transmit, Delivered, Extension needed, Archived) map to Drake Custom Status 6–20 if a write-back ever exists. Also carry a coarse client-facing status, separate from the internal stage.
- **Pure logic:** `transitions.py` — `can_transition(from, to, facts) -> Ok | Refusal(reason, next_step)`. Refusals name the next step (doctrine 3). Setting the current status is success, not a 409 (doctrine 4).
- **State:** `obligation_status_events(event_id, obligation_key, from_status, to_status, actor_kind, actor_id, model_version, at, reason, note)`, append-only. `set_obligation_status` = targeted UPDATE + event insert, copying the `set_document_status` seam exactly.
- **UI:** a status control and a history panel on the obligation page. Refusals render their reason inline. **Never show "Filed" on transmission** — that word belongs only after an accepted ACK.
- **Testing seam:** `can_transition` is pure — table-driven over every `(from, to)` pair, every precondition. A store test that a refused transition writes nothing and that the event log rejects updates.
- **Real-use signal:** the owner tries to mark a return Ready to file with an open item outstanding and the app names exactly which one. The history panel answers "when did this move and why" without anyone remembering.

### Slice 2 — The clock

**Outcome:** Every obligation knows its own due date, extended date, document cutoff, and lateness — computed from dated config, with the rule that produced it visible.

- **Config:** `configs/deadlines/federal_<year>.yaml` (per obligation type: month offset, day, basis = fiscal year end, extension form, extension months **including 1041 = 5.5**, `extension_available: false` for 990-N and for W-2/1099-NEC, perfection days per form family); `configs/deadlines/holidays_<year>.yaml` (federal + DC Emancipation Day + Patriots' Day); `configs/deadlines/mef_windows_<year>.yaml`; `configs/practice.yaml` for the document cutoff offset — firm policy, rendered visibly differently from statute so nobody mistakes it for law. Every file carries `source_url`, `retrieved_on`, `effective_for`.
- **Pure logic:** `due_dates.py` — `statutory_due()`, `shift_for_weekend_holiday()`, `extended_due()`, `perfection_deadline(form_family, rejected_on)` (**calendar days, and the one function that must NOT use the business-day helper**), `is_overdue(as_of)`. Plus `blocked_by(obligation, relationships)` walking the existing `relationships` table so a partner's 1040 is blocked by the entity's K-1 obligation.
- **State:** computed dates cached on the obligation and recomputed when config changes; a `date_overrides` table for FEMA disaster postponements carrying declaration id and source URL — **never inferred**, always confirmed by a human, because eligibility keys off the IRS address of record.
- **UI:** a "What's due" list sorted by days-remaining showing the blocking reason; a per-obligation deadline panel naming the config rule that produced each date.
- **Testing seam:** `due_dates.py` is pure — golden tests per entity type and year: the 1041 September 30 case, the 990-N non-extendable case, the June-30 1120 seven-month rule and its 2026 sunset, a statutory date landing on Emancipation Day, and a 1040 rejected on the due date.
- **Real-use signal:** on 16 September the dashboard shows exactly which 1040s just unblocked because their 1065 hit EF Accepted, and not one date on the screen was typed by a human.

### Slice 3 — Open items and the inquiry record

**Outcome:** Every question the file raises is a durable object with an asked-date, a verbatim answer and an answered-date, and an obligation cannot leave prep while one is open and unexplained.

- **Config:** `configs/open_items.yaml` — item kinds, which transition each blocks, default owner (client / owner / model), and the comms-template key for the wording.
- **Pure logic:** `open_items.py` — `blocking_items(items, target_status)` and `is_stale(item, as_of, cadence)`, both pure; Slice 1's precondition function consumes them.
- **State:** `open_items(item_id, obligation_key, kind, subject_ref, question_text, asked_at, asked_via, owner, answer_text, answered_at, resolution, created_by_actor, blocks)`. Answers are **append-only** — a correction is a new row, because "contemporaneously document" means the file cannot be rewritten later.
- **UI:** an Open Items panel on the obligation; a one-click "draft the ask" that renders from the comms library; an "answer received" form that captures the client's words, not a paraphrase.
- **Testing seam:** `blocking_items` is pure. A store test proving an answer row cannot be edited in place. A transition test proving Ready-to-file is refused with the specific item named.
- **Real-use signal:** at close the owner can print every question asked this year with the client's answer and both dates — the §10.34(d) file, produced as a by-product of doing the work.

### Slice 4 — The chase

**Outcome:** Outstanding requested documents generate dated, escalating, self-terminating follow-up drafts whose body is the current outstanding list, regenerated at render time.

- **Config:** `configs/chase.yaml` — first nudge at T+3, interval 3 days, escalate after the second unanswered, stop on completion or expiry (whichever first); document classes (**blocking**: W-2, W-2G, 1099-R per Pub 1345, or a Form 4852; **expected-late**: K-1, consolidated 1099-B/DIV/INT, corrected forms, 1095-A corrections; **not-applicable**: requires a reason); template key per round, because a second request should not read like a first.
- **Pure logic:** `chase.py` — `due_nudges(register, as_of, cadence) -> list[Nudge]`. Pure over the register plus a clock.
- **State:** the documents register gains `round`, `last_nudged_at`, `expected_late`, `blocking_class`, `na_reason`, and the §1.6695-2 provenance fields on receipt (`obtained_how`, `obtained_at`, `furnished_by` — a person, not "client"). Record "client replied by email" as an event so silence and a reply are distinguishable.
- **UI:** a Chase queue — "Monday 09:00 — draft nudge #2 for client X, 3 items outstanding" — each row rendering a draft the human sends. Every draft carries an explicit stop-nudging sentence. The N/A action demands a reason before it will save.
- **Testing seam:** `due_nudges` is pure — frozen-clock tests for round 1, round 2, escalation, and termination. A completed register must yield zero nudges (doctrine 4).
- **Real-use signal:** in February the owner works one queue instead of scanning eight engagement pages, and nobody is nudged twice in a day or nudged for something they already sent.

### Slice 5 — Rollover and the omission detector

**Outcome:** Next season's obligations, task lists and expected-document lists are created from last year's file, and anything present last year but absent this year becomes an open item before a human touches the return.

- **Config:** `configs/rollover.yaml` — which prior-year facts mint which expected documents (payer + form type), and which mint tasks: age crossing 73 → RMD; address change vs vault-held prior address → residence-sale/§121 and part-year state questions; a new state on any W-2/1099 → state return. Plus the standing rule that rolled-forward values enter as **proposed, never confirmed**.
- **Pure logic:** `rollover.py` — `expected_documents(prior_mart, client)` and `omissions(expected, received)`. Pure, mart-only, no PII.
- **State:** rollover creates obligations in `Not started / Rollover`; clients present last year and not rolled forward are flagged as an explicit retention decision; IP PIN is stored under a tax-year key and **refuses to roll forward**.
- **UI:** a January "Season rollover" screen: N clients, N obligations to create, N retention decisions, N predicted extensions (from K-1/PTP reason codes).
- **Testing seam:** both functions are pure over two marts — golden tests from de-identified fixtures, plus a test that a rolled-forward value can never be read as confirmed.
- **Real-use signal:** the first document request of the season names the actual payers by name, and a 1099-INT that quietly stopped arriving surfaces as a question in February instead of a CP2000 in November.

### Slice 6 — Preparer self-review: the two-year comparison

**Outcome:** A printed comparison sheet — prior year, current year, delta, delta %, explanation, source reference — with a required typed explanation on every line over the threshold, and no advancement without it.

- **Config:** `configs/review/variance.yaml` (default 10% threshold, per-line overrides, materiality floor); `configs/review/rulesets/top12.yaml` (prior-year 1099 payer with no current match; carryforward present last year and absent this year; estimated payments not confirmed against a client record; charitable-to-AGI outlier; mortgage interest threshold; prior-year notice not addressed; dependent aged out). **Line references derive per tax year from the crosswalk, never frozen from a blog post** — Form 1040's withholding line moved from 17 to 25d and line 1 is now subdivided 1a–1z.
- **Pure logic:** `variance.py` — `compare(prior, current, config) -> list[VarianceLine]`; `run_ruleset(mart, ruleset) -> list[Finding]`. Findings become open items via Slice 3.
- **State:** explanations persist as **workpaper notes** on the obligation — durable, distinct from review critique.
- **UI:** a Comparison tab and a printable artifact issued alongside the Drake keying worksheet. The explanation box sits inline on the flagged line. Add the one-minute test literally: a final screen showing refund/balance due with the last three years for context and a single "does this look right for this client" confirmation.
- **Testing seam:** `compare` and `run_ruleset` are pure — table-driven per rule, and **every rule ships with a case that must fail** (doctrine 10).
- **Real-use signal:** the owner stops opening last year's PDF beside this year's screen, and every surprising number on a delivered return already has a sentence in the file explaining it.

### Slice 7 — Review notes, and the confirmation that can be revoked

**Outcome:** Review notes are typed, scoped, resolvable objects with rollforward rules; confirming a value is a signature over `(field, value, source_doc_hash)` that reverts automatically when the source changes.

- **Config:** `configs/review/notes.yaml` — types **Review** (purge at close), **Preparer** (carries forward), **Note to Next Year** (carries one period, converts to Review), **Missing Item** (purge). `configs/review/programs/<return_type>.yaml` — the versioned reviewer checklist, each item with an id, text and, where possible, an auto-evaluable predicate; conditional items injected by fact (Schedule C present → hobby-loss and startup-cost items; K-1 with losses → passive-activity/suspended-loss).
- **Pure logic:** `notes.py` — `rollforward(notes)`; `invalidate(confirmations, changed_fields) -> list[FieldRef]`, the DoubleCheck semantic.
- **State:** a real `review_notes` table — `models/review.py` finally gets the scope FK, author, `created_at`, `resolved_at`/`resolved_by` it has always lacked. `staged_fields.confirmation` becomes `(confirmed_by, confirmed_at, procedure, source_doc_hash)`, where `procedure` records *what was done* (traced to doc X page N / recomputed / client-confirmed) so a confirmation is never a bare checkbox. A **Close review** action asserts zero open blocking notes, records that review happened and by whom, and deletes the critique bodies — while touching nothing in `open_items`.
- **UI:** notes render inline on the keying-worksheet line. "Close review" states exactly what it will purge and what it will keep, before it does it.
- **Testing seam:** `invalidate` is pure — re-reading a document under a different hash must revert every confirmation derived from it. A test that purge-on-close removes note bodies and removes **zero** rows from `open_items`.
- **Real-use signal:** a corrected 1099 arrives in March and the app un-confirms exactly the three lines it touched, instead of the owner trying to remember which ones.

### Slice 8 — Delivery, signature, transmission, acknowledgement

**Outcome:** Copy delivered, 8879 signed, transmitted and acknowledged are ordered states with legal preconditions, and a post-signature change produces a hard RE-SIGN verdict with the arithmetic shown.

- **Config:** `configs/filing/signature_thresholds_<filing_year>.yaml` ($50 total income/AGI, $14 total tax / federal withheld / refund / amount owed — Publication-set, **not statutory**, cited and dated); `configs/filing/perfection_<year>.yaml` per form family (1040 and 4868 = 5 calendar days; 1120/1120-S/1065/1041/990 = 10; 7004/8868 = 5 — and record the unresolved Intuit-published-date discrepancy *in the config file* rather than resolving it in code); `configs/filing/ack_codes.yaml` mapping Drake's letters to semantic states, with `D` hard-blocking any resend and `a` routed to the extension branch.
- **Pure logic:** `signature.py` — `requires_new_8879(snapshot, current, thresholds) -> Verdict` returning the deltas, not just a boolean; `filing_clocks.py` — `notify_by = rejected_at + 24h`, `retransmit_by`, `paper_file_by = max(due_date, rejection_notice + 10d)`, `stockpiling_alert_at`.
- **State:** `signature_authorizations(obligation_key, delivered_at, signed_at, method, snapshot_json, submission_id, retention_until)` with a store-level rule that `signed_at >= delivered_at` is an **error, not a warning**; `filing_events` capturing the ACK letter the owner keys from Drake; the signed 8879 lives in the vault (it carries a full SSN and the taxpayer's PIN), never in the mart. Signature method is an enum (in-person wet / in-person e-sign / remote e-sign via an external provider) and after three failed KBA attempts the required artifact switches to a wet signature as a **state transition**, not a note.
- **UI:** a "Cleared to transmit / not cleared" banner naming the missing precondition; an ACK entry form; a rejected state showing three live clocks with the IRS business-rule ID and element name stored verbatim for the client letter.
- **Testing seam:** `requires_new_8879` is pure and table-driven at the boundaries ($50.00 vs $50.01). A store test that a signature dated before delivery is rejected. A test that the transmit precondition includes "all blocking-class documents received or a 4852 on file".
- **Real-use signal:** a late K-1 arrives after signature and the app says *RE-SIGN REQUIRED — AGI moved $1,240* and drafts the re-signature request, instead of the owner guessing at a threshold he half-remembers.

### Slice 9 — Retention and release

**Outcome:** Every retained artifact carries a computed destroy-not-before date, and a client can get their records back in one action that no payment state can block.

- **Config:** `configs/retention.yaml` — per artifact class, the basis and the term, each cited: 8879 = 3y from the later of due date or IRS received date; the §1.6695-2 bundle = 3y from the **latest of four** dates, the first of which is the **unextended** due date; conflict waivers = 36 months from the conclusion of representation. Document the FTC §314.4(c)(6) two-year disposal default and the "required by law" displacement as data, not as an unresolvable conflict.
- **Pure logic:** `retention.py` — `retention_until(artifact_class, dates)` (latest-of arithmetic is the part that gets coded wrong); `records_export_scope(register)` implementing the §10.28(b) split: client-provided and third-party-provided materials always go back; SATC's own prior-year work product may be withheld only against the unpaid fee **for that specific document**, and unpaid 2024 fees never license withholding the 2023 deliverable.
- **State:** `retention_until` + `retention_basis` on every retained artifact; a disposal queue.
- **UI:** a "Disposal due" worklist; a "Return client records" button that is **never disabled** by an unpaid balance.
- **Testing seam:** pure `retention_until` tests for each of the four trigger dates including an extended return. A test asserting the export code path contains **no branch** on `invoiced` or `paid`.
- **Real-use signal:** a departing client asks for their file on a Friday and gets it that afternoon; the owner is not still storing 2016 source documents.

### Slice 10 — 8867 due diligence, per benefit

*(Promote to position 4, immediately after Slice 3, if this practice files meaningful EITC/CTC/AOTC/HOH volume.)*

**Outcome:** HOH, EIC, CTC/ACTC/ODC and AOTC each get an independent record of the questions asked, the answers received, the documents relied on, and its own retention bundle.

- **Config:** `configs/due_diligence/<benefit>.yaml` — the inquiry set seeded from the regulation's own example fact patterns: a young taxpayer claiming near-age dependents (relationship verification); a taxpayer living in a parent's household (is the taxpayer themselves a qualifying child?); a niece/nephew or non-child relative (residency, relationship, income, support, share of household costs); Schedule C income with no expenses. `configs/penalties_<filing_year>.yaml` for internal severity ranking only.
- **Pure logic:** `due_diligence.py` — `required_benefits(facts)`, `incomplete(record)`. Both pure.
- **State:** **four independent records** per obligation, four completion states, four penalty exposures. The inquiries themselves are `open_items` rows, so the contemporaneous timestamps come free from Slice 3.
- **UI:** a Due Diligence tab with four cards. The obligation cannot reach ready-to-key with any card incomplete.
- **Testing seam:** pure `required_benefits` over fact fixtures. A test that a prior-year answer **cannot** auto-satisfy this year's inquiry, with the two narrow regulatory exceptions encoded explicitly rather than assumed.
- **Real-use signal:** the owner can hand an examiner one bundle per benefit per return, and the compliance-rate report shows the procedure was followed on *every* return — which is the §1.6695-2(d) "routinely followed" argument, not a claim about intent.

### Slice 11 — Work that isn't a return

**Outcome:** Payroll filings and deposits, estimates, information returns, FBAR, state elections and notice responses appear on the same queue as returns, generated from recurrence rules instead of remembered.

- **Config:** `configs/obligations/*.yaml` — a recurrence block per type (cadence, anchor, period key, jurisdiction, extension availability). Client attributes that switch a stream on: 941 vs 944 (**stored as a fact with a source document, because it is IRS-assigned by written notice — never inferred**), monthly vs semiweekly depositor, foreign accounts (FBAR is aggregate and at-any-time, so intake must ask for a max balance), PTET states (the election is a *decision* deadline with no extension, and its estimates run in the calendar year **before** the return year).
- **Pure logic:** `recurrence.py` — `next_occurrences(rule, client_facts, horizon)`. Pure.
- **State:** `client_obligations(obligation_id, client_id, type, cadence, anchor, next_due, last_generated, active)`; a notices register as an obligation of type `notice_response` carrying jurisdiction, notice number, date, deadline and disposition, with a rollover rule that surfaces last year's notices during this year's prep.
- **UI:** the same "What's due" queue, filtered; a per-client obligations tab.
- **Testing seam:** `next_occurrences` is pure — golden tests for a monthly depositor, quarterly 941s with the conditional 10-day grace rendered as a **note, not a date** (the grace depends on a fact SATC may not know), the four individual estimate installments, and the corporate 12th-month installment a 1040-centric calendar silently drops.
- **Real-use signal:** the January queue populates itself on 2 January, and an FBAR is never discovered in October.

### Slice 12 — The junior

**Outcome:** The local model proposes into every gate that now exists — and can write nothing, compute nothing, and send nothing.

- **Config:** `configs/llm.yaml` — model id, prompt versions, and a per-surface allow-list of what may be proposed. A hard loopback check on any inference `base_url`, with no bring-your-own-key escape hatch, because that single option silently converts a no-consent architecture into a criminal-penalty one.
- **Pure logic:** every proposal is a `Proposal(surface, model_id, prompt_version, inputs, output, confidence)`, and **the same deterministic verifier that accepts a human's input accepts or refuses it** — there is no second path. The model never assembles ID lists for bulk action; it names a criterion and the engine selects the rows (doctrine 5). Half-finished runs are inert by construction (doctrine 9).
- **State:** a `proposals` table recording the human decision (accepted / edited / rejected) and the edit distance. That table is the SSTS 1.4.7 "appropriate for its intended purpose" evidence and the evaluation record §10.35 competence expects.
- **UI:** proposals render as advisory text beside the control the human still has to operate — never as a pre-filled value. An Accuracy page showing accept/correct rate per surface per model version.
- **Testing seam:** an offline integration test asserting zero non-loopback network calls. A test that every proposal surface flows through the same verifier as human input. A test that the model path **cannot reach** `parse_money`, `mask_value`, `auto_confirm_high`, `to_line_items` / `post_confirmed`, `write_pages` / `sort_folder(apply=True)`, `reconcile_received`'s status write, or any transition function.
- **First surfaces, in order:** (1) author the missing `configs/extraction/<key>.yaml` maps for the ten `key: null` doc types — the model touches YAML, a human reviews a diff, extraction is deterministic forever; (2) draft the variance explanation from confirmed documents ("W-2 wages up $18k; new employer W-2 received 2026-02-03"); (3) draft chase and inquiry wording; (4) propose new `_FAMILY_PATTERNS` entries — **the rule, never the row**.
- **Real-use signal:** the classification accept rate is high enough that the owner stops reading them one at a time, and the reject rate on variance explanations is visible enough to decide whether that surface earns its keep — which is a decision made on measured engine state, not on the model's prose.

---

## 4. What SATC should not build

### Because Drake owns it

- **Any tax computation, e-file transmission, EF Message clearing, or ACK retrieval.** SATC records the ACK letter the owner reads off Drake and computes the downstream clocks; it never touches the wire.
- **A competing status *vocabulary*.** SATC needs its own status *machine* (Drake's CSM stops auto-updating at Complete and knows nothing about the pre-entry or delivery legs) but must reuse CSM's *names* wherever they overlap.
- **A Drake import file.** The printable keying worksheet is the seam. Writing into Drake breaks "Drake is the system of record" and inherits GruntWorx's known failure mode — populated screens the preparer is merely told to "review for accuracy."
- **A client portal or any document-exchange surface.** Drake Portals already exists and already auto-checks-off client uploads. SATC is the ledger of what was asked for and what is still open; Portals is the pipe.
- **A twenty-page client organizer.** Drake generates one, and practitioners report 10–15% come back usable. Generate a short signed questionnaire covering only what the client alone can answer, plus a named-document checklist.
- **Return assembly, printing, or the proforma of the return itself.**

### Because it is multi-person overhead a solo firm does not have

- **Timesheets, WIP aging, realization, utilization, staff dashboards.** At most, track elapsed minutes against fee per engagement — that is the mispricing and scope-creep detector; everything else is a firm-size artifact. Billing itself belongs to the existing `invoice-generator/` project, triggered on Delivered, not on Accepted.
- **Assignment, routing, roles, approval chains, workload balancing, Kanban-by-assignee.** There is no user table and no reason to build one. The only surviving "role" distinction is *human vs local model*, which Slice 12 handles as an actor field.
- **Creator-≠-clearer enforcement as a hard rule.** CCH does not actually prohibit self-clearing, and a firm of one cannot satisfy it. If a second-pass discipline is wanted, ship a cooling-off requirement (a note raised today cannot be cleared in the same session) and **label it as SATC's own design decision**, not as parity with a vendor.
- **SQMS No. 1 scaffolding.** SQMS 1 scopes to SAS/SSARS/SSAE engagements; a tax-only practice is governed by the SSTSs. Build it as a config toggle only, and confirm with the owner whether any SSARS-scope work exists before declaring it out of scope.
- **A capacity/scheduling calendar, complexity scoring, tiered turnaround promises.** Worth building eventually; worth nothing before the queue and the clock exist.

### Because the rules or the doctrine forbid it

- **E-signature for Form 8879.** Pub 1345 requires NIST SP 800-63 IAL2 knowledge-based authentication every time, a six-item tamper-proof evidence set including the taxpayer's IP address and login ID, and a mandatory fallback to a handwritten signature after three failed attempts. A local, no-cloud, single-user app cannot deliver this, and a weak version creates real exposure. Model the wet-signature and external-provider paths, which Pub 1345 expressly blesses.
- **SMTP, or auto-sending anything.** SATC renders drafts a human sends. This is also the line the profession's malpractice insurer draws: AI assisting a supervised professional is fine; AI interacting directly with the client is not.
- **Any network egress of tax return information — ever.** §7216 defines disclosure as making information known "to any person in any manner whatever," and it is a criminal statute. No cloud model, no cloud OCR fallback, no BYO-API-key option, no telemetry, no crash reporting, no auto-update payload carrying client-derived fields. **De-identification does not license export** — §301.7216-1(b)(3)(i)(B) pulls statistical compilations into tax return information. The MCP surface must return masked/last-4 values only, and a test should fail the build if any outbound-capable call site is reachable from a code path touching vault plaintext.
- **The model computing any number that lands on a return, or making any eligibility determination.** Frontier models correctly compute fewer than a third of simplified 1040s and reliably botch CTC/EITC eligibility. Circular 230 §10.22(b)'s reliance presumption is written for a *person*; tools are governed by §10.35 and SSTS 1.4, and 1.4.8 says a tool must not supplant judgment. Enforce this as a failing test, not a convention.
- **A free-text "ask me a tax question" box**, even for the owner. If research help is wanted, the right shape is retrieval over a curated local corpus returning *the passage*, with extractive quoting at most.
- **Auto-filing an extension, or treating extension as an assumed default.** An extension is the taxpayer's decision; filing without written authorization can destroy the client's reasonable-cause defense. The cutoff date is a deterministic rule that flips a flag and raises a prompt — nothing more.
- **A zero-dollar extension.** Treas. Reg. §1.6081-4(b)(4) requires the properly estimated tax; a $0 estimate must be a hard error with an explanation, not a warning. Wire the withholding estimator into the extension draft.
- **A penalty calculator, or any penalty dollar figure in client-facing output.** Use the amounts internally for queue severity only.
- **Auto-applying disaster relief.** Eligibility keys off the IRS address of record, not the current address. Surface "this client's county appears in FEMA declaration X — confirm?" as a human gate.
- **Persisting LLM critique text into the archived engagement.** But note the tension and resolve it deliberately: critique bodies purge at close; the **inquiry-and-response log must survive**, because §1.6695-2(b)(3)(i) requires contemporaneous documentation and §10.34(a)(2) makes "pattern of conduct" a factor. Two objects, two tables, two lifetimes.
- **Audit-lottery reasoning anywhere.** §10.37(a)(2) forbids taking the possibility of non-audit into account in written advice. Lint the comms templates *and* model output for "unlikely to be audited" / "the IRS rarely checks" / "low audit risk" and block the draft rather than warning.
- **Percentage-of-refund or percentage-of-tax-saved fee types** in the invoicing seam (§10.27).
- **Gating the client-records export on payment** (§10.28).

### Do not hardcode — every one of these is dated, cited config

| Value | Why it moves |
|---|---|
| Form line numbers (1040 line 17 vs 25d; line 1 subdivided 1a–1z) | Change per tax year. Derive from the crosswalk, never from a blog post. |
| $50 / $14 re-signature thresholds | Publication-set (Pub 1345), not statutory. |
| §6695(g) due-diligence penalty ($650 for 2026 filings, $665 for 2027) | Indexed annually; keyed to **filing year**, not tax year. |
| §6695(a)–(e) ($65 each, $32,500 / $33,000 caps) | Same. |
| §6698/§6699 per-partner-per-month amounts | Re-indexed every October. |
| Perfection periods (5 days for 1040 and 4868; 10 for business returns) | Per form family, and the published-date discrepancy is unresolved. |
| Extension lengths (1041 = 5½ months; 1120 June-30 seven-month rule) | The June-30 rule sunsets for tax years beginning in 2026. |
| Filing-season open date and MeF blackout windows | Announced by QuickAlerts every autumn. |
| 1099-MISC box 8/10 February 15, and every other statutory date | Shifts for weekends and holidays; store the rule and the calendar, not the date. |
| Federal / DC Emancipation Day / state holidays | Per year. |
| FTC civil-penalty amounts | Inflation-adjusted; and they should not appear in the UI at all. |

### Verify before you freeze any of this into config

- **Drake CSM's exact status list and which are auto-set** (KB 10580). The retrieved research disagrees with itself on the editable/automatic split; Slice 1's mapping depends on getting it right.
- **Whether Drake exposes any machine-readable seam** for CSM status, EF Messages, DoubleCheck state, or LookBack prior-year values. If yes, Slices 1, 6 and 8 get materially cheaper. If no, the honest design is a small guided reconcile screen where the owner keys what Drake shows — and SATC becomes the only durable, exportable review record, which is a real product seam rather than duplication.
- **The 1040 perfection period.** Drake KB 13325 and Pub 1345 both say five calendar days; Intuit publishes April 23 for an April 15 deadline. Read Pub 4164 / IRM 3.42.5.14.6 before coding, and record the discrepancy in the config file either way.
- **AICPA SSTS §1.3 and §1.4 paragraph text.** Every citation currently in play is secondhand via *The Tax Adviser*; the standard's own text does not say what one popular summary claims it says.
- **OPR Alert 2026-19's primary text.** Two trade outlets report it consistently but list different Circular 230 sections; do not cite section numbers in a shipped policy artifact until the alert itself is read.
- **The firm's state(s).** State due dates, state extension mechanics (Virginia proves "automatic, no form" is a real shape, so a boolean `extension_filed` is the wrong model), state 8879 equivalents with their own retention rules, state retention floors that may exceed the federal three years, and state AG breach deadlines. Ship only the states the practice actually files, each as dated config with the DOR URL, and **refuse to guess** for unconfigured states rather than defaulting to the federal date.
- **This practice's EITC/CTC/AOTC/HOH volume.** It is the single input that decides whether Slice 10 sits at position 10 or position 4.