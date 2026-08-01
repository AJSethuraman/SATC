# THE AI BOUNDARY
### Where a local 8B model may and may not act inside SATC

**Status:** design constraint document. Binding on any AI feature in `satc_system/`.
**Governing doctrine:** `docs/LOCAL-LLM-PATTERN.md` — *the model proposes; a deterministic engine verifies, refuses, or executes.*
**Governing constraint:** Drake is the system of record. SATC never recomputes tax and never e-files.

---

## 0. The rule, restated for tax

A tax practice is not a place where a model produces answers. It is a place where a licensed human produces a **defensible evidentiary record** that specific inquiries were made at specific times and that specific values trace to specific documents. Everything the model is allowed to do is in service of that record; nothing it does may *be* that record.

Three sentences that decide every row in the table below:

1. **The model never emits a number that lands on a return.** Grounded empirically, not just legally: TaxCalcBench (arXiv 2507.16126, Column Tax authors — an academic benchmark, not authority) found frontier models compute **~81% of lines correctly but only ~32% of complete returns correctly** on 51 *simplified* 1040s, and specifically "consistently misuse tax tables, make errors in tax calculation, and incorrectly determine eligibility," naming CTC and EITC. An 8B model is materially worse than what was measured. Per-line accuracy is irrelevant when one wrong line fails the return.
2. **The model never writes durable state.** It hands proposals through a single typed door; a deterministic engine decides. Doctrine rule 6 — policy expressed in a prompt holds roughly 1 run in 3.
3. **The model never sees more taxpayer data than the task needs, and never sees any of it off this machine.** IRC §7216 is a criminal statute and "disclosure" means "making tax return information known to **any person in any manner whatever**" (26 CFR §301.7216-1(b)(5)).

A corollary that must be stated because it is tempting and wrong: **the model is not junior staff, legally.** Circular 230 §10.22(b)'s due-diligence presumption is written for reliance on "the work product of **another person**" whom the practitioner engaged, supervised, trained and evaluated. By its terms it does not reach a tool, and no authority extends it to software. Tool use is governed instead by §10.35 (competence) and, for AICPA members, SSTS §1.4 (Reliance on Tools), whose operative line is that tools "enhance or improve the member's understanding … not … supplant the member's professional judgment." Product consequence: **the audit trail must never render the model as a named preparer.** Actor is an enum — `human:owner` or `tool:<model-id>@<version>` — and only the former can satisfy a review, a confirmation, or a signature.

**Legend for the Ground column:** `C230` = 31 CFR Part 10 (Circular 230) · `SSTS` = AICPA Statements on Standards for Tax Services (eff. 1/1/2024) · `6694` / `6695` / `6107` / `7216` / `6713` = IRC · `1.6695-2` = Treas. Reg. (due diligence) · `1345` = IRS Pub. 1345 (Rev. 12-2025) · `SG` = FTC Safeguards Rule, 16 CFR Part 314 · `D#` = doctrine rule number · `BENCH` = measured model failure.

---

## 1. The task-by-task boundary

`Role` values: **AUTHOR-CONFIG** (proposes a config/rule diff a human merges — the safest form) · **PROPOSE** (drafts a value/text a human must accept) · **NARRATE** (read-only prose over engine-computed facts) · **NONE**.

### A. Client, engagement, and authority setup

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| Create client / import roster | No | NONE | Identity writes go to the vault only; `client_id` minted by `ids.py` | "Client records are created by you. I can list rows in your CSV that look like duplicates of SATC-001042 — open Import Preview." | 7216(b)(3)(i) TRI includes name/address/TIN; D5 (model never assembles ID lists for bulk action) |
| **Conflict-of-interest check** | Partial | NARRATE | Engine runs the query: shared address, shared dependent TIN, shared EIN, prior joint filing, `relationships` graph. Model may only phrase the finding | "I can describe a conflict the engine found. I cannot clear one. §10.29 requires each affected client's informed consent confirmed in writing within 30 days — open Conflicts." | C230 §10.29(b)(3), (c) (retain consents 36 months from conclusion of representation) |
| Draft the engagement letter | Yes | PROPOSE | `comms/render.py:81 render()` → `RenderResult.is_complete`; unfilled placeholders block "sent" | "Two placeholders are unfilled: `{document_cutoff_date}`, `{fee_basis}`. Fill them before this can be marked sent." | SSTS 1.4.8; D3 (errors are the interface) |
| **Set or suggest a fee** | No | NONE | Fee is a `EngagementRecord.fee_amount` typed by the owner | "I can't propose a fee. §10.27 bars a contingent fee for return preparation, so fee structure is a decision you record, not one I suggest." | C230 §10.27(b),(c)(1) (percentage of refund or of tax saved is contingent) |
| **Draft a §7216 consent** | Config only | AUTHOR-CONFIG | Consent template is **locked**: Rev. Proc. 2013-14 §5.04 mandatory language verbatim, ≥12-pt, use and disclosure in **separate documents**, no blank spaces, named recipient, copy delivered at execution | "The §7216 consent is a locked template. Its wording is prescribed by Rev. Proc. 2013-14 §5.04 and cannot be paraphrased. I can fill the recipient name and purpose fields only." | 7216; 26 CFR §301.7216-3(a)(3), (b), (c)(1),(3); Rev. Proc. 2013-14 §5.04 |
| PTIN / EFIN / firm-profile tracking | Yes | NARRATE | Engine computes: PTIN expiry ≥ current filing year; any edit to Responsible Official/address/phone raises a 30-day "update e-file application" task | "Your firm address changed 4 days ago. Pub. 3112 requires the e-file application updated within 30 days; undeliverable mail is grounds for EFIN inactivation." | Pub. 3112; 1.6695-1(c) |

### B. Document gathering and the chase

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Build the expected-document list from prior year** | Yes | PROPOSE | Engine computes the set difference from the mart (prior-year payers/form types vs current-year received). Model may *word* the request, not choose the set | — (this is the model's best job) | SSTS 2.3.2 (consider prior-year returns whenever feasible); D8 (deterministic priors shrink the problem) |
| Generate the interview / task list from answers | No | NONE | `intake/workflows.py:184 evaluate_condition` — pure, recursive, unit-tested | "Task generation is config-driven. I can propose a change to `configs/workflows/personal_1040_core.yaml`; I cannot decide which tasks apply to this client." | D6 (policy at the choke point, not the prompt) |
| **Word the missing-items chase message** | Yes | PROPOSE | Engine supplies the outstanding list fresh at render time from `documents` where `status='Requested'`; the list is never model-authored | "This engagement has 0 outstanding requests. Nothing to chase." | D2 (aggregate server-side, hand the model something small) |
| Decide follow-up cadence / escalate | No | NONE | Engine timer: nudge at T+3 days, escalate after the second unanswered follow-up (owner-configurable). A firm policy value, not law | "Follow-up cadence is your firm policy, set in Settings. I drafted reminder #2; sending is yours." | Practitioner norm (Mendlowitz 2018 checklists — his own stated practice, not a standard); D9 |
| **Mark a requested document Received** | **No** | NONE | `intake/service.py:166 reconcile_received` — pure-regex family match in `matching.py:64 matches()` / `:80 specificity()`. See choke point CP-5: this is the only automatic durable write in the pipeline | "I can propose a new pattern for `_FAMILY_PATTERNS` covering 'consolidated broker statement'. I cannot close a request." | D5; C230 §10.34(d) (the register is the evidence of what was asked) |
| Mark a request **Not Applicable** | No | NONE | N/A requires a typed reason string; empty reason is refused | "'Not applicable' needs a reason recorded — it becomes part of the completeness record. Type one." | 1.6695-2(b)(3)(i); C230 §10.34(d) |
| **Decide the file is complete enough to start prep** | No | NARRATE | Engine computes readiness: outstanding count, blocking-class count (W-2 / W-2G / 1099-R are blocking per Pub. 1345), `expected_late` exclusions | "Readiness is 88%. Two blocking documents outstanding (W-2, 1099-R). Pub. 1345 prohibits e-filing before those are in hand absent a Form 4852." | 1345 (no e-file before W-2/W-2G/1099-R); D10 |

### C. Document ingestion, classification, extraction

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Classify a document type** | Yes | PROPOSE | `ingest/classify.py` ladder runs deterministic signals first (AcroForm fingerprint → text layer ≥ `text_threshold: 6` → local OCR → filename). A model rung may fire **only** when all deterministic signals were silent, and is **capped at MEDIUM** so `run_intake` surfaces it | "Classified as 1099-NEC at MEDIUM by a local model. This will not auto-extract. Confirm the type at /staging." | D8; SurePrep precedent — even *certain* OCR requires human verification; only text-layer-matched values auto-verify |
| **Author a new extraction map** | Yes | AUTHOR-CONFIG | Human merges the YAML diff; extraction is 100% deterministic thereafter. Ten recognized doc types currently carry `key: null` (1099-NEC, 1099-K, 1099-R, 1095-A, 1098-T, 8879, organizer …) — this is the highest-leverage model job in the repo | — | D8; SSTS 1.4.7 (tool appropriate for its intended purpose: authoring config ≠ producing figures) |
| **Read a field value off a document** | Yes | PROPOSE | Value enters only via `MapExtractor.extract(labeled_fields, confidences)`; unmapped labels are **dropped**; `parse_money` refuses anything not unambiguously numeric; `sensitive: true` TINs are masked to last-4 at stage time | "Read 4 fields, 1 unparseable ('1,2 34.00'). Staged NEEDS_REVIEW with a blank amount." | 1.6695-2(b)(3)(i); SSTS 1.4.8 |
| **Auto-confirm a model-read value** | **Never** | NONE | `auto_confirm_high` must promote only `STAGED` + `HIGH` + **non-model provenance**. See CP-1 — this is currently unenforced | "This value came from a local vision model. Model-read values never auto-confirm — confirm it against page 1 at /staging." | SSTS 1.4.8; C230 §10.35; D6 |
| **Decide the split boundary of a combined PDF** | Yes | PROPOSE | `split.py:segment_pages` deterministic rule ("an unclassified page attaches to the preceding form") remains the fallback; split plan is previewed before intake reads it | "Proposed 3 segments; deterministic segmentation found 1. Review the split preview before running intake." | D8 |
| Propose the sorted filename / payer label | Yes | PROPOSE | `sort.py` `apply=False` returns a **plan**; apply **copies, never moves**; canonical name uses the de-identified `client_id`, never a legal name | "Proposed name contains what looks like a taxpayer name. Filenames use client IDs only." | Repo PII constraint; SG §314.4(c)(3) |
| Correct/normalize OCR text | Yes | PROPOSE | Post-corrected text still goes through the same anchor logic and `parse_money`; original token retained in `value_text` | — | — |

### D. Preparation and the Drake keying worksheet

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Compute any tax, credit, or eligibility** | **Never** | NONE | Not implemented, and must be structurally impossible: no model output path may write a numeric field consumed by the worksheet | "SATC does not compute tax. Drake is the system of record. I can show what the confirmed source documents say." | BENCH (~32% return-level correct on simplified 1040s; named CTC/EITC eligibility failures); 6694(a) |
| **Determine filing status / dependency / HOH** | **Never** | NONE | Config-driven interview branch producing a **question for the owner** | "Filing status is a determination. §1.6695-2 requires you to make and contemporaneously document the inquiry — I've drafted the questions." | 1.6695-2(b)(3); 6695(g) ($650/failure, returns filed 2026; $665 for 2027 — **keyed to filing year, config not constant**) |
| **Decide a return position's authority level** | **Never** | NONE | `position` record typed by the owner: `{more_likely_than_not \| substantial_authority \| reasonable_basis \| none}` + citations + disclosure form | "Position authority is a judgment §10.34 assigns to you. If you record `reasonable_basis`, the engine will require Form 8275/8275-R before this return can reach ready-to-key." | C230 §10.34(a),(c); 6694(a)(2) |
| Roll forward prior-year values | No | NONE | Rolled-forward values enter as **proposed, unconfirmed** with `PRIOR_YEAR_CARRYFORWARD` provenance — never as accepted data | "Carryforwards are proposed, never accepted. 3 carryforwards need confirmation against last year's return." | SSTS 2.3.2; named failure mode: "copying prior-year data without validation" |
| Post confirmed fields to line items | No | NONE | `state.py:343 post_confirmed` + `staging_gate.py:178 to_line_items` — only `CONFIRMED` fields, human `confirmed_by`, `SOURCE_DOC` provenance, idempotent re-post | "3 fields are still NEEDS_REVIEW. Posting requires every field either confirmed or rejected." | D4 (idempotent writes); D6 |
| Propose `field_path → line_code` mappings | Yes | AUTHOR-CONFIG | Human merges rows into `MAPPING_1040`; `to_line_items` itself stays model-free | — | D8 |
| **Order the keying worksheet** | Yes | NARRATE | Ordering only; every printed line carries a source-document reference and masked identifiers only | — | Repo PII constraint |
| Draft the two-year variance explanation | Yes | PROPOSE | Engine computes prior vs current, delta, delta% from the mart; explanation is **required** above the configured threshold (10% is a practitioner convention, not law) and is stored as a workpaper note | "Wages up 34% with no explanation. An explanation is required before this engagement can advance." | Practitioner norm (Mendlowitz); C230 §10.34(d) |

### E. Review

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Content review** (tick-and-tie: every keyed value traced to a source) | Yes | PROPOSE | Engine does the tracing: N of N amounts traced to a confirmed source doc, M exceptions. Model may narrate exceptions only | — (this is the second-best model job) | Practitioner argument that exhaustive manual tick-and-tie causes reviewer fatigue; SSTS 1.4.7 |
| **Issue review** (planning items, elections, judgment calls) | Partial | PROPOSE | Model may surface a *candidate list* from engine-computed facts (Schedule C present → hobby-loss item; age ≥ 73 → RMD item; new state on any W-2 → state-return item). It may not resolve one | "I can list candidate issues. Whether the real-estate-professional election applies is a determination — §10.35 competence is yours." | C230 §10.35, §10.37; SSTS 1.4.8 |
| **Clear a review note** | **Never** | NONE | Only `human:owner` may clear. A cleared note records `cleared_by`, `cleared_at`, `resolution_text` | "Notes are cleared by you. If I raised it, I can't clear it." | C230 §10.22(a) ("approving" is itself a diligence-bearing act); D6 |
| **Verification invalidation on change** | No | NONE | Engine: a confirmation is a signature over `(field, value, source_doc_hash)`. If the extraction or the driving intake answer changes, any prior confirmation **reverts to flagged** | "Box 1 changed after you confirmed it. This line is unconfirmed again — re-verify against page 1." | Drake DoubleCheck precedent (verified→red-flag on change); D4 |
| **Draft the client inquiry** on an inconsistency | Yes | PROPOSE | Engine detects the inconsistency (prior-year payer missing, income down 40%, dependent aged out, charitable/AGI outlier). Model drafts the *question*. It may **never resolve an inconsistency by choosing a value** | "This looks inconsistent with the 2024 return. I've drafted a question. I can't pick which figure is right." | C230 §10.34(d) — all four triggers: incorrect, inconsistent with an important fact, inconsistent with another factual assumption, incomplete |
| **Record the client's answer** to an inquiry | **Never** | NONE | Answer text, `answered_at`, and `furnished_by` are typed by the owner. Append-only; server-side timestamps the UI cannot backdate | "The client's answer has to be recorded by you, verbatim. §1.6695-2(b)(3)(i) requires it documented *contemporaneously* — a file reconstructed later doesn't satisfy the reg on its own terms." | 1.6695-2(b)(3)(i); 1.6695-2(b)(4)(i)(C) |
| **Form 8867 due diligence** (EIC, CTC/ACTC/ODC, AOTC, HOH) | Draft questions only | PROPOSE | Four **independent** records, four completion states, four penalty exposures. Engine hard-blocks ready-to-key while any is incomplete | "Two of four due-diligence records are incomplete (AOTC, HOH). Each incomplete benefit is a separate §6695(g) penalty — up to $2,600 on this return for returns filed in 2026." | 6695(g); 1.6695-2(a)(1), (b)(1)-(4); Examples 1–8 at (b)(3)(ii) |
| **Reportable-transaction screen** | No | NONE | A `yes` on any screen question raises required authority to more-likely-than-not, surfaces Form 8886, and **blocks any model-assisted disposition** | "This engagement is flagged for a reportable transaction. Model assistance is disabled on this return's positions." | 26 CFR §1.6011-4(b); 6694(a)(2)(C) |
| Free-text "ask me a tax question" | **No such feature** | NONE | Not built. If research help is wanted: retrieval over a curated local corpus returning **the passage**, extractive quoting only | "I don't answer tax questions. Here are three passages from your local corpus; the conclusion is yours." | C230 §10.35, §10.37 (independent verification of AI-supplied law/facts); consumer-chatbot failure record (WaPo test of TurboTax/H&R Block, Mar 2024 — journalist's informal test, cited only for the "no unsupervised Q&A" conclusion) |
| Research note under a time cap | Yes | PROPOSE | Fixed artifact shape: question / what I found / source / **what I could not determine** / time spent. The model must be able to return "not found" and the engine renders that as an open item, not a guess | "Could not determine whether the 2025 basis election applies. Recorded as an open item." | SSTS 1.4.7; D3; D9 (accept the give-up tail) |

### F. Signature, transmission, acknowledgement

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Mark Form 8879 Signed** | **Never** | NONE | Ordered gate: `return copy delivered → 8879 sent → signed (taxpayer's own signature date) → ready to transmit`. Engine **blocks** `signed_at < delivered_at` as an error, not a warning | "Signature date precedes delivery of the return copy. Pub. 1345 requires the taxpayer sign *after* reviewing the return. This cannot advance." | 1345 (sign after review, before origination); 6107(a) (complete copy furnished no later than presentation for signature) |
| **Re-signature after a post-signature change** | No | NARRATE | Engine snapshots the five signed figures at signature and recomputes deltas: **> $50** total income/AGI, **> $14** total tax / withheld / refund / balance due ⇒ RE-SIGN REQUIRED, with arithmetic shown. Publication-set thresholds → dated config, never a constant | "AGI moved $612 after signature. Pub. 1345 requires a new Form 8879." | 1345 (Rev. 12-2025) |
| **Transmit / e-file** | Never (SATC doesn't) | NONE | SATC records the ACK letter the owner reads from Drake (`P/A/a/R/B/D/E/S/T/X`). `D` (duplicate) hard-blocks resend | "SATC does not transmit. Drake does. I can tell you the gate is now open." | 1345 |
| Aging alert on ready-but-not-transmitted | Yes | NARRATE | Engine clock: escalate at **3 calendar days** after having everything needed for origination | "This return has been ready to originate for 4 days. Pub. 1345 treats waiting more than three calendar days as stockpiling." | 1345 (stockpiling) |
| **Rejected e-file remediation** | Partial | PROPOSE | Engine derives three clocks: notify taxpayer within **24h**; retransmit by the **5th calendar day after the due date** (1040/4868 — **10 days for 1120/1120-S/1065/1041/990**); paper-file by later of due date or **10 days after the rejection notice**. Perfection period is **per-form-type config**, never a constant, and never weekend-shifted | "Rejected. The business rule ID and element name must be copied verbatim from Drake — Pub. 1345 requires the client be given them. I've drafted the message around the fields you paste." | 1345; Drake KB 13325 |
| **File an extension** | **Never** | PROPOSE (the authorization request only) | Two objects: an engine-derived `EXTEND-CANDIDATE` flag and a separate signed `ExtensionAuthorization` artifact. **A $0 estimate is hard-blocked with an error** | "No extension authorization on file. An extension is the taxpayer's decision, and a zero-dollar extension is invalid — Treas. Reg. §1.6081-4(b)(4) requires the properly estimated tax." | 26 CFR §1.6081-4(b)(4); Rev. Rul. 79-113; 7216 (filing without authorization) |
| **Paper-file branch** | No | NONE | Requires a reason mapping to a Form 8948 line; client-preference reason requires a documented taxpayer-choice statement | "Paper filing needs a Form 8948 reason. You are a specified tax return preparer (≥11 covered returns)." | 6011(e); Form 8948; Rev. Proc. 2011-25 |
| Send anything to a client | **Never** | PROPOSE | No SMTP exists. Every outbound artifact is a rendered draft a human sends. This is a **product invariant, not a setting** | "Drafted. Sending is yours — SATC has no mail transport by design." | CAMICO risk-management position (insurer guidance, not a standard): the line is whether AI interacts *directly* with the client |

### G. Post-filing, records, and the practice layer

| Task | Model may touch | Role | Deterministic engine verifies | Refusal must say | Ground |
|---|---|---|---|---|---|
| **Discovered error on a filed return** | Draft only | PROPOSE | `discovered_error` record; the gap between `discovered_at` and `advised_at` is a dashboard aging item. Engine must make it **impossible** to auto-close, and impossible to generate IRS-directed correspondence without an explicit owner action | "I can draft the advisory to the client. §10.21's duty runs to the client only — nothing goes to the Service without your action." | C230 §10.21 (advise promptly of the fact **and** the consequences) |
| Retention clocks | No | NARRATE | Per-artifact computed field, never a global tax-year purge: 8879 = max(due date, IRS received date) + 3y; §1.6695-2 records = 3y from the **latest of four** dates in (b)(4)(ii), (A) keyed to the **unextended** due date; conflict consents = 36 months from conclusion of representation | "Retention is per artifact. This engagement has three different clocks." | 1345; 6107(b); 1.6695-2(b)(4)(ii); C230 §10.29(c) |
| **Disposal / purge** | **Never** | NARRATE | Engine computes a disposal-eligible queue; the owner executes. SG's two-year disposal default is displaced for records law requires retained — the **legal basis must be stored**, per artifact | "12 artifacts are disposal-eligible. Deletion is yours. Nine others are held under a recorded legal basis." | SG §314.4(c)(6) and its "required to be retained by law or regulation" carve-out vs. 6107(b)/1345 |
| **Purge review notes at close** | No | NONE | Two *different objects*, and conflating them is the most likely design error in this whole document: **(a) QC/critique notes** — ephemeral, purged at engagement close, model may draft; **(b) inquiry-and-response records** — durable, retained, model may draft the *question* only | "Closing review will delete 14 note bodies and retain the fact that review was completed. Your 6 inquiry records are unaffected — those are required to be retained." | (a) practitioner position on retained review notes as liability (Mendlowitz, his own stated view, not a standard); (b) 1.6695-2(b)(3)(i), (b)(4)(i)(C); C230 §10.34(a)(2) "pattern of conduct" |
| Deadline lattice / calendar math | No | NONE | Structural rules per obligation (`month_offset`, `day`, `basis=fiscal_year_end`) + a dated holiday table. Extension lengths are **per-obligation config**: 1041 is **5½ months (Sept 30)**, not 6 | "1041 extended due dates are Sept 30, not Oct 15. Config, cited, dated." | Pub. 509; Form 7004 instructions (Rev. 12-2025) |
| **Disaster-relief postponement** | No | PROPOSE (the prompt only) | Never inferred from a rule. A per-client override record (declaration ID, counties, postponed-to date, source URL) behind a human gate — eligibility keys off the **IRS address of record** | "This client's county appears in FEMA declaration DR-XXXX. Confirm before I shift any date — wrongly applying relief is worse than not knowing." | IRS disaster-relief program (per-declaration, ad hoc); D8 |
| Return of client records on request | No | NARRATE | One-action export, **explicitly exempt from any payment gate**, tagging each item `client_provided \| third_party \| practitioner_prepared` (the last is subject to §10.28(b)'s document-specific fee carve-out) | "Records export is never gated on an unpaid balance." | C230 §10.28(a),(b) |
| **Security-incident reporting** | No | NARRATE | Two clocks, and the tighter one must be the louder one: **next business day** to the IRS Stakeholder Liaison (Pub. 1345 Standard 6, no consumer floor) and **30 days** to the FTC at ≥500 consumers | "Report to your IRS Stakeholder Liaison by tomorrow. That deadline is tighter than the FTC's 30 days and has no minimum size." | 1345 Standard 6; SG §314.4(j)(1),(2) |
| WISP generation | Yes | AUTHOR-CONFIG | Generated **from** the engine's own registers (PII-location inventory, access log, hardware list) so it cannot drift from reality. Under 5,000 consumers, §314.6 exempts only §§314.4(b)(1), (d)(2), (h), (i) — mark those *exempt-with-basis*, not *unmet* | — | SG §314.4, §314.6; Pub. 5708 (a **sample template**, not a mandate); Pub. 4557 |
| Billing / invoicing | Yes | PROPOSE | Fee-type enumeration must not offer percentage-of-refund or percentage-of-tax-saved for return prep | "That fee type isn't available for return preparation." | C230 §10.27 |
| **Any written advice** | Draft only | PROPOSE | Lint over template text and model output: block drafts containing audit-lottery reasoning ("unlikely to be audited," "the IRS rarely checks," "low audit risk"). **Block, not warn.** Written advice requires a facts-and-assumptions block | "This draft reasons from audit probability. §10.37 forbids taking into account the possibility that a return will not be audited. Rewrite before it can be marked ready." | C230 §10.37(a)(2) |

---

## 2. The choke points

Doctrine rule 6: policy lives at the engine choke point, not in prompts. Every rule above must hold from *every* path — the Flask route, the CLI, a future MCP call, a test fixture. Below are the exact seams, verified against the code.

### CP-0 — **P0 defect: the boundary is currently unenforceable at the gate**

`ingest/extractors/base.py:47 make_staged_field(..., extractor=...)` is called from `extractors/mapping.py:84` with a hardcoded `extractor=f"MapExtractor[{self.doc_type}]"`. **The reader backend is discarded.** `ReadResult.backend` (`readers/base.py`) is used only to build a UI note string via `_READER_LABELS` in `state.py:277`.

Consequence: `Provenance` does not record whether a value came from `PdfFormReader` (deterministic AcroForm read) or `OllamaVisionReader` (a model). `staging_gate.py:64 auto_confirm_high()` gates on exactly two things —

```
if f.status == "STAGED" and f.provenance.confidence == "HIGH":
```

— so it **structurally cannot** distinguish model-derived from deterministic values. The only thing preventing local-model output from auto-confirming today is that `readers/ollama.py:80` voluntarily sets `uncertain_labels=set(labeled)` in its own return statement, and `readers/vision.py:167` computes `uncertain` **from the model's own self-report**. That is reader-side convention and model self-assessment standing in for policy — precisely the failure doctrine rule 6 was written about.

**Required fix, in this order:**
1. Thread `ReadResult.backend` through `MapExtractor.extract(..., backend=...)` into `make_staged_field(extractor=...)` so `Provenance.extractor` names the real reader.
2. Add `_MODEL_BACKENDS: frozenset[str]` and clamp in `make_staged_field`: if the extractor names a model backend, `confidence` is forced to `LOW` regardless of what was passed in. A model cannot declare itself HIGH.
3. Add the same check as an independent second gate in `auto_confirm_high`: skip any field whose `provenance.extractor` is a model backend, even if confidence somehow reads HIGH. Two independent checks, because one of them will be refactored away someday.
4. Regression test that **proves the check can fail**: construct a `StagedField` with `confidence="HIGH"` and a model extractor, call `auto_confirm_high()`, assert it returns 0. Then flip the extractor to `PdfFormReader` and assert it returns 1.

### CP-1 — the confirmation gate: `ingest/staging_gate.py`

`auto_confirm_high` (`:64`), `confirm` (`:77`), `reject` (`:89`), `unconfirm` (`:99`), `delete_field` (`:111`), `edit` (`:120`). This is the single control the system is built around and the one place field-level policy belongs.

- `confirm(by=...)` must reject any `by` value that is not `human:*`. Today `by` is a free string defaulting to `"preparer"`.
- Add **invalidation on change** (Drake DoubleCheck semantics): a confirmation is a signature over `(field_path, value, source_document_hash)`. If the underlying extraction or the driving intake answer changes, revert to `NEEDS_REVIEW` with a note. Without this, a re-run of intake silently preserves stale confirmations.
- **Known correctness precondition:** `field_id = f"{document_id}:{field_path}"` and `document_id = path.name` (`state.py:247`). Two files with the same basename in different subfolders of one intake collide, and `_find` (`:57`) returns the first match — so a confirm can land on the wrong field. Per-field policy is meaningless until field identity is unique. Fix before enforcing anything per-field.
- **The gate is in-memory only.** `persistence/store.py` has no staged tables (`identities, vault_addresses, vault_contacts, public_clients, returns, line_items, carryforwards, owner_basis, estimate_payments, engagements, documents, relationships, intake_engagements, intake_tasks, workflow_overrides, app_meta`). Restart mid-review and un-posted confirmations are gone. Any asynchronous proposer, and the entire scoreboard in §3, requires `staged_documents` / `staged_fields` tables. Adding tables is cheap (`CREATE TABLE IF NOT EXISTS` appended to `_MART_DDL`); widening existing ones is not (positional `INSERT OR REPLACE`).

### CP-2 — the value door: `ingest/extractors/base.py` + `mapping.py`

`parse_money` (`base.py:21`), `mask_value`, `make_staged_field` (`base.py:47`), `MapExtractor.extract` (`mapping.py:49`).

Every proposer hands values in through `labeled_fields` + `confidences` and nowhere else. **Never put a model inside `parse_money` or `mask_value`** — those are where "an unparseable amount stays blank" and "a TIN is masked to last-4" are enforced. Unmapped labels are dropped: this is the conservatism that makes a hallucinated field name harmless.

### CP-3 — the reader ladder: `app/state.py:289 _read_document`

Rung order is policy, not preference. A model rung may execute **only** if every cheaper rung produced nothing. Enforce by structure: `_read_document` returns on the first non-empty result, so a model rung inserted at position 3.5 or 4 can never pre-empt `PdfFormReader` or `TextAnchorReader`. Follow `OllamaVisionReader`'s injectable-`transport` pattern so the rung is unit-testable fully offline.

### CP-4 — the mart write: `app/state.py:343 post_confirmed`

Plus `staging_gate.py:156 to_line_values`, `:178 to_line_items`, `:223 MAPPING_1040`. Only `CONFIRMED` fields cross; re-posting is idempotent (all prior `SOURCE_DOC` lines for the return are deleted first — doctrine rule 4). Add: refuse to post if any field's `confirmed_by` is not `human:*`. `to_line_items` stays model-free permanently; `MAPPING_1040` should move to `configs/` so it becomes an AUTHOR-CONFIG target.

### CP-5 — the one un-gated automatic write: `intake/service.py:166 reconcile_received`

Called from `state.py:251` during intake. It flips a `DocumentRecord` from `Requested` to `Received` and completes the linked `IntakeTask` on a regex-family match with **no human confirmation**. It is the only place an automatic classification mutates durable state.

Enforcement: the `doc_type` argument must be traceable to a classification whose provenance is **not** a model backend. If the classification came from a model rung, `reconcile_received` must not be called — the document lands as received-but-unmatched and the owner reconciles it at `/documents`. The model may propose new `_FAMILY_PATTERNS` entries (`matching.py:23`) as a config diff; `matches()` (`:64`) and `specificity()` (`:80`) stay pure regex forever.

### CP-6 — the store: `persistence/store.py`

Every durable write funnels here. `set_document_status` (`:334`) is the established targeted-UPDATE pattern (`state.py:138` validates against `DOC_FLOW`, then calls the store, then syncs the in-memory mart). Two additions:
- An `actor` parameter on every mutating store method, defaulted to nothing — callers must be explicit.
- An append-only `state_events(event_id, subject_kind, subject_key, from_state, to_state, actor, at, note)` table. This is the §10.36 "procedures were followed" evidence and the SG §314.4(c)(8) activity log in one object. Log the `client_id` and last-4 only — **the log itself must never contain PII.**

`app/state.py:483 STATE = AppState()` is a module-level singleton with `check_same_thread=False`. Single-actor is currently an architectural assumption, not a choice; introducing a second actor (`tool:<model>`) into the audit trail requires deciding that deliberately.

### CP-7 — the egress switch: `settings.py` + `doctor.py`

`cloud_allowed()` (`:22`), `cloud_vision_enabled()` (`:27`), `ollama_enabled()` (`:45`), `ollama_host()` (`:55`). The existing posture is correct and unusually strong: cloud requires `SATC_ALLOW_CLOUD=1` **and** a key — a key alone is deliberately insufficient.

Harden:
- A single `egress_allowed()` predicate every network-capable reader must call, so there is one place to audit.
- `ollama_host()` must **refuse non-loopback values**. A local model with a configurable base URL is one env var away from being a third-party disclosure under §7216.
- **Never ship a "bring your own API key" escape hatch.** It converts a no-consent-needed architecture into a criminal-penalty one silently.
- Add a `doctor.py:46 run_checks()` entry reporting model provenance, model version, and egress state — the readiness screen is where the boundary is made legible to the owner, and legibility is the §10.35 competence artifact.
- CI test: assert no code path reachable from vault plaintext can reach an outbound-capable call site.

### CP-8 — the outbound door: `comms/render.py:81 render()`

`RenderResult.is_complete` (`:55`) already blocks on unfilled placeholders. Add two lints that **block, not warn**:
1. Audit-lottery phrases (§10.37).
2. Unmasked SSN/EIN patterns in any rendered body, including model-drafted text.

Locked templates (§7216 consent, taxpayer-choice statement for Form 8948) must be flagged in `configs/comms/templates.yaml` as non-editable and skipped by any model-assisted rewrite.

### CP-9 — task generation: `intake/workflows.py:184 evaluate_condition`

Pure, recursive, unit-tested, fail-open on unrecognized leaves. The model never evaluates it and never supplies `answers`. Its legitimate role is AUTHOR-CONFIG: propose a diff to a `configs/workflows/*.yaml` or a `relationship_tasks:` block. Widening the `answers` dict built by `_normalize_answers` (`:228`) into a richer fact dict (`client.*`, `prior_year.*`, `today`) is the single highest-leverage seam in that module, and it is a *deterministic* upgrade — it makes more rules expressible without a model.

---

## 3. The scoreboard

Doctrine rule 10: measure against engine state, never the model's prose, and prove every check can fail. Nothing below reads a model's self-report, and none of it is computable until the staging gate is persisted (CP-1).

### 3.1 Metrics that read engine state only

| Metric | Definition (all from `staged_fields` / `documents` / `state_events`) | Why it is the right number |
|---|---|---|
| **Field acceptance rate** | `confirmed_without_edit / proposed`, per doc type, per reader backend | The only honest measure of extraction quality |
| **Correction rate** | `edited / proposed`, plus normalized edit distance on the changed value | Distinguishes "close" from "wrong"; a systematically-off-by-one-digit reader is a different bug from a hallucinating one |
| **Rejection rate** | `rejected / proposed` | Fields the model invented |
| **Return-level clean rate** | Returns where **every** proposed field was confirmed unedited ÷ returns processed | The metric that matters. TaxCalcBench's 81% line-level vs ~32% return-level gap is exactly why per-field accuracy flatters. Report both; lead with this one |
| **Classification agreement** | Model-proposed label vs the label the owner confirmed on the `DocumentRecord` | Measured against a human decision recorded in the register, not against classifier confidence |
| **Silent-acceptance audit** | Sample *n*% of auto-accepted classifications monthly and re-verify against the source file | Explicitly guards against the TaxDome trap: a vendor-reported 1.97% manual-override rate measures **what users bothered to change**, not accuracy. An unnoticed misfiled K-1 is invisible until it is a missing K-1 |
| **Owner-minutes at the gate, per return** | From `state_events` timestamps: first gate open → post | At a firm of one, review minutes are the entire constraint. If an AI feature raises this number, it made the firm smaller — and the dashboard should say so in those words. Establish your own baseline; do not import a vendor's "30% kickback rate," which was a demo default |
| **Refusal rate and refusal quality** | Count of blocked actions by rule ID; and the share whose message names a concrete next step | Doctrine rule 3. A refusal that doesn't route the human is a bug |
| **Give-up rate** | Runs where the model returned "not found / low confidence" ÷ runs attempted | Should be *non-zero*. A model that never gives up is guessing (doctrine rule 9) |

### 3.2 Tax-specific outcome metrics

| Metric | Definition | Reads |
|---|---|---|
| **Omission recall** | Prior-year payers/forms with no current-year match that the engine surfaced ÷ those the owner ultimately requested | `documents` + prior-year mart. This is the one thing tick-and-tie structurally cannot catch, so it is where the system earns its keep |
| **Omission precision** | Surfaced items the owner marked `N/A` with a reason ÷ total surfaced | Too low and the owner stops reading the list |
| **Inquiry-log completeness** | Engagements where every §10.34(d)/§1.6695-2(b)(3) trigger has a recorded question *and* answer ÷ engagements with a trigger | The §1.6695-2(d) "normal office procedures … routinely followed" defense is literally this number |
| **Due-diligence completion, per benefit** | Four independent rates (EIC, CTC/ACTC/ODC, AOTC, HOH) | §6695(g) penalties are per benefit, so a per-return rate hides the exposure |
| **Override rate on hard gates** | Times the owner bypassed a blocking check, with reasons, per season | §1.6695-2(d) requires the failure be *isolated*. A system that lets you bypass silently destroys the defense; one that records the bypass preserves it. This number must be visible, and it must be low |
| **Chase efficiency** | Median days Requested→Received, and follow-ups per closed request, before vs after model-drafted reminders | `documents` + `state_events` |
| **Time-to-advise on discovered errors** | `advised_at − discovered_at`, distribution | C230 §10.21 |
| **Ready-to-transmit aging** | Hours in `Ready to transmit`, p50/p95 | Pub. 1345 stockpiling: escalate at 3 calendar days |

### 3.3 Proving every check can fail

Each of the following must have a test that makes the check **fire**, and a paired test that makes it pass. A check with no red test is decoration — the named industry failure mode is "using DoubleCheck as decoration."

- `auto_confirm_high` with a model-provenance HIGH field ⇒ returns 0.
- `post_confirmed` with a `confirmed_by` that is not `human:*` ⇒ refuses.
- 8879 with `signed_at < delivered_at` ⇒ blocks advance.
- Post-signature delta of $51 to AGI ⇒ RE-SIGN REQUIRED; $49 ⇒ signature still valid. Test both sides of both thresholds.
- Extension with a $0 estimate ⇒ hard error.
- Rendered draft containing "unlikely to be audited" ⇒ blocked.
- Rendered draft containing an unmasked 9-digit TIN pattern ⇒ blocked.
- `ollama_host()` set to a non-loopback address ⇒ refuses to start.
- Perfection-period arithmetic: 1040 = 5 days, 1120-S = 10 days, and **no** weekend shift on either.
- Retention: extended 1040 with due date, filing date, and presentation date all different ⇒ clock keys off the **latest**, with (A) computed from the **unextended** due date.

**Never measured, and never displayed as if it were a measurement:** the model's stated confidence, the model's summary of its own work, "N documents processed successfully," or any count the model produced rather than the engine.

---

## 4. Confidentiality: what may enter a model at all

### 4.1 The three definitions that decide everything

- **Disclosure** — "the act of making tax return information known to **any person in any manner whatever**." 26 CFR §301.7216-1(b)(5).
- **Use** — "any circumstance in which a tax return preparer refers to, or relies upon, tax return information as the basis to take or permit an action." §301.7216-1(b)(4)(i).
- **Tax return information** — anything furnished for or in connection with preparing a return, **plus** information the preparer "derives or generates from tax return information," **plus** statistical compilations "even in a form that cannot be associated with … a particular taxpayer" (§301.7216-1(b)(3)(i), (i)(B)).

That last clause is the one that catches people: **SATC's de-identified data mart is still tax return information.** De-identification does not license export.

Penalties: §7216 is criminal — up to $1,000 and/or one year, plus prosecution costs. §6713 adds $250 per unauthorized disclosure or use, $10,000/year cap.

### 4.2 Local model

A model whose weights sit on the owner's machine and whose inference never leaves the process makes tax return information known to **no person**. On the text of §301.7216-1(b)(5), no disclosure occurs and no consent question arises.

**Say this precisely, and no more.** In any UI copy, README, or client-facing text, state the *architecture fact* — "documents never leave this machine" — not the *legal conclusion* — "§7216-exempt." No IRS guidance addresses on-device inference. It is an unlitigated reading of the text, not a safe harbor. Two related corrections worth carrying: §301.7216-2 is a list of disclosures **permitted without consent**, so intra-firm sharing is an excepted disclosure rather than a non-disclosure; and a hosted vendor may separately qualify under the §301.7216-2(d) auxiliary-services path, so "local" is the lowest-risk configuration, not the only compliant one.

**Use is still constrained even locally.** §7216(a)(2) permits use "to prepare, or assist in preparing" the return. Local inference that classifies this taxpayer's documents, drafts this taxpayer's missing-items letter, or proposes this taxpayer's variance explanation is preparation. Three things exit that permission **even with zero network traffic**:

1. **Training or fine-tuning any model on client data.** Prohibited outright. Not a setting.
2. **Cross-client aggregation or analytics** beyond preparing the specific taxpayer's return. §301.7216-2(o) permits only narrow statistical-compilation uses; read it in full before the mart is used for anything else.
3. **Marketing or segmentation** off client data.

### 4.3 Third-party model

Sending any of it to a hosted model is a disclosure. To be lawful it needs a consent that is:

- **taxpayer-signed before** the disclosure (no retroactive consent, §301.7216-3(b)(1));
- **naming the specific recipient** — "OpenAI" or "Anthropic," never "various AI tools" (§301.7216-3(a)(3)(ii));
- **Rev. Proc. 2013-14 §5.04 compliant** — mandatory statements in sequence, the TIGTA statement, affirmative opt-in only, handwritten signature for paper, ≥12-pt on 8½×11, **no blank spaces**, no alteration after signature;
- **separate documents for use vs. disclosure** (§301.7216-3(c)(1));
- **copied to the taxpayer at execution** (§301.7216-3(c)(3));
- **not a condition of service** (§301.7216-3(a)(1)).

And SSNs may not be disclosed to a preparer or service provider **outside the United States** absent an adequate data protection safeguard; otherwise they must be redacted or masked (§301.7216-3(b)(4)).

**Safeguards Rule consequence, which is the more persuasive argument in practice:** every cloud AI dependency triggers 16 CFR §314.4(f) — reasonable steps to select and retain, a **contract** requiring safeguards, and **periodic assessment** of that provider, forever, personally discharged by the owner. A local model creates none of that. That is a recurring-compliance-cost argument, not a privacy preference, and it is the one to put in the ADR.

### 4.4 The data classification table

Enforce this at a **single redactor** on the prompt-assembly path, not per call site.

| Data class | Local model | Third-party (with valid consent) | Never |
|---|---|---|---|
| Full SSN / EIN | ✗ — masked to last-4 before any prompt; `sensitive: true` masking already happens at stage time | ✗ (§301.7216-3(b)(4) offshore bar; and no operational reason) | Any log, any artifact, any rendered draft, the `state_events` table |
| Legal name, address, DOB | Only when the task genuinely needs it (a name-control/TIN sanity check does not) | Requires consent naming the recipient | Filenames, the mart, the audit log, printed worksheets (masked identifiers only) |
| Bank routing / account | ✗ | ✗ | Any model, any prompt, any time |
| **Document page images** | ✓ — this is the one class that unavoidably carries full PII into the model, which is exactly why image-mode rungs must be **local-only, no exceptions**. A cloud vision reader receiving a W-2 image discloses everything on the page | ✗ | — |
| Extracted amounts + `field_path` | ✓ | Consent required (still TRI) | — |
| De-identified mart aggregates / prior-year comparisons | ✓ | Consent required — §301.7216-1(b)(3)(i)(B) pulls statistical compilations into TRI | Export, telemetry, crash reports |
| Firm config: workflow YAML, extraction maps, comms templates, statutory parameters | ✓ | ✓ (no TRI) | — |
| Statutory/regulatory text, IRS publications | ✓ | ✓ | — |

### 4.5 Non-negotiable engineering invariants

1. No telemetry, no analytics SDK, no crash reporting, and no auto-update payload may carry any field derived from client data.
2. No model download or tokenizer/embedding fetch at inference time. Verify with an offline integration test.
3. `ollama_host()` refuses non-loopback. No configurable inference base URL.
4. The SATC MCP surface returns masked/aggregate values only — never a document body, never an unmasked TIN. "Read-only" is not the mitigation; the risk is the read **leaving the machine**, and an MCP client is by definition an external process. Test that fails the build if any MCP tool can return unmasked vault content.
5. SATC is itself an "information system" holding customer information under SG §314.4(c)(5). A localhost Flask app with no authentication is a live gap. Two lawful paths: add real MFA, or produce and store a Qualified-Individual written approval of the compensating controls (full-disk encryption, OS account MFA, loopback-only binding, physical control). Path two is probably right for a local app — **but the written artifact must actually exist.**
6. The vault key's location and protection must be answerable in one place, because §314.2's encryption definition requires "appropriate safeguards for cryptographic key material," and §314.2's notification-event definition treats data as unencrypted "if the encryption key was accessed by an unauthorized person."
7. If a contractor ever works on this codebase against real client data, §301.7216-2(d)(2) requires they receive **written notice** of §§7216/6713. Keep that notice as a template.

---

## 5. Verification status — read before quoting any of this

This firm files real returns. The following are flagged honestly rather than smoothed over.

- **Verbatim and confirmed against primary text:** 31 CFR §§10.21, 10.22, 10.27, 10.28, 10.29, 10.34, 10.35, 10.36, 10.37 (via eCFR renderer API / Cornell LII); 26 CFR §1.6695-2 including the (b)(3)(ii) Examples 1–8 and the (b)(4)(ii) four-date retention rule; 26 CFR §§301.7216-1, -2, -3; 16 CFR §§314.2, 314.4, 314.6; IRC §§6107, 6694, 6695, 7216, 6713; IRS Pub. 1345 (Rev. 12-2025, Cat. 64382J) including Standard 6, the $50/$14 thresholds and the stockpiling definition; Rev. Proc. 2024-40 and 2025-32 penalty tables; Drake KB 10117, 10580, 10783, 13325, 13765, 14110.
- **Secondhand, not verified against the standard itself:** every AICPA SSTS paragraph number and quotation (1.3, 1.4.2, 1.4.3, 1.4.4, 1.4.7, 1.4.8, 2.3.2). The AICPA PDF was not machine-readable; these come from *The Tax Adviser*. **Verify §1.4.7 and §1.4.8 against the AICPA source before either appears in shipped copy or a generated procedures document.** Specifically: SSTS §1.4 does **not** contain a "mandatory final review step," does not mention generative AI, and does not say "results not found" — those are commentary. The standard's actual posture is proportional judgment and care, and that a tool never absolves the member.
- **Reported but unverified at source:** IRS OPR Alert 2026-19 (June 2026). Two trade outlets report it; the primary text was not retrieved and it did not appear on OPR's public alert list past Issue 2026-13. Independent write-ups enumerate **six** Circular 230 provisions (§§10.22, 10.27, 10.35, 10.36, 10.37, 10.51(a)(15)). Do not cite it in a compliance artifact without retrieving the alert.
- **Unresolved conflict:** the 1040 transmission perfection period. Pub. 1345 says "the fifth calendar day after the due date" and Drake KB 13325 and Thomson Reuters both say 5 days for 1040/4868 (10 for 1120/1120-S/1065/1041/990). Intuit publishes April 23 for an April 15 deadline, which is neither. IRM 3.42.5.14.6 would settle it and was not retrievable. **Ship it as per-form-type config with the citation inline and a flag for the owner — do not code the arithmetic as if it were settled.**
- **Practitioner conventions, not authority:** the 10% variance threshold, the 30-minute research cap, the 3-day follow-up cadence, and the destroy-review-notes-at-close position all come from Ed Mendlowitz's 2018 tax-season checklists, whose own cover page states the views are his and not his firm's. They are excellent defaults and are labeled as firm policy in the UI, visibly separate from statutory rules.
- **Every dollar figure in this document is dated and indexed.** §6695(g) is $650 per failure for returns **filed** in 2026 and $665 for 2027 (no maximum); §6695(a)–(e) is $65 with a $33,000 cap for 2027 filings. §6694's $1,000/$5,000 are **not** indexed. The $50/$14 re-signature thresholds are publication-set, not statutory. All of these belong in a config table keyed to **filing year**, refreshed each October when the revenue procedure drops. None may be a constant.
- **Not researched:** state board of accountancy requirements (some states impose longer retention floors than Circular 230), and state-specific e-file signature forms and perfection periods.