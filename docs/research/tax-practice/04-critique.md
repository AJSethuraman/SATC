# Critique of the three synthesis documents

Verified against the repo where claims were checkable (`grep`/`sed` on `satc_system/`).

---

## (a) Real practice work no document covers

1. **Amended and superseding returns, and the §6511 refund clock.** The operating model lists `version ∈ original/superseding/amended` on `Return` and stops. No 1040-X lifecycle, no link to the original filing, no reason code, and — the real omission — **no refund statute of limitations** (3 years from filing / 2 years from payment). §0's "three kinds of date" never mentions it. Confirmed: zero occurrences of `amend`/`1040-X`/`supersed` in `src/` or `configs/workflows/`.
2. **Notice response / representation as an engagement type.** All three docs reduce a notice to a register row. Actual work: 2848 vs 8821, the notice's own 30/60-day response deadline, CP2000 vs exam vs collection, FTA abatement, installment agreements. **AICPA SSTS No. 4 (Tax Representation Services)** — new in the 1/1/2024 set and named in the research — appears nowhere in the AI boundary.
3. **Planning and projections.** Mendlowitz's preparer checklist requires reconciling the final return to the projection. There is no `Projection` entity and no slice for it; the withholding estimator is the only forward-looking code and is wired to nothing. Year-end planning has a hard Dec 31 deadline and is the advisory revenue a solo firm lives on.
4. **Capacity and scheduling.** The strongest solo-specific research finding (honest capacity 66 vs ~90 "produced"; slots; client document-due date one week before the slot; automatic reschedule) is dropped by all three documents. The plan models demand and deadlines and never models the owner's supply.
5. **Trial balance / book-to-tax.** Most of the business reviewer checklist is tie-outs to a TB (retained earnings, capital accounts, cash to bank recs, gross payroll to W-3, sales-tax sales to income-tax sales). `business_scorp_tax.yaml` and `business_partnership_tax.yaml` exist; "trial balance" appears only as a regex family and a fixture string. Business returns are modeled as a form type, not a workflow with a TB input.
6. **Disengagement and client acceptance/continuance.** Engagement letters are everywhere; termination is nowhere. No disengagement letter, no §10.28 records-return-on-exit, no January "who do I not take back." Acceptance is also where the §10.29 conflict check actually belongs.
7. **State filings as separate submissions.** `Filing` carries one `ack_code`. Federal+state is two submissions, two ACKs, often a state-specific signature form with its own retention rule, and linked/unlinked semantics. The research flagged this as an open question; the operating model resolved it by not modeling it.
8. **Litigation hold.** Both the purge-on-close review-note rule and the retention-clock disposal queue can destroy records after a claim is foreseeable. Nothing suspends disposal.

---

## (b) Conflicts with the research or the doctrine

1. **Model classification can silently write durable state.** The AI boundary allows a model classification rung (capped MEDIUM) *and* forbids the model from marking a request Received — but `reconcile_received` (`intake/service.py:166`) fires on `c.label` from **any** rung during `run_intake` (`state.py:251`), which the gap analysis itself names as the only automatic durable write. Those two rows contradict unless model-provenance classifications are excluded from reconcile. That must be stated, not implied.
2. **Model-corrected OCR can auto-confirm.** "Correct/normalize OCR text — PROPOSE" feeds `TextAnchorReader`, which is not a model reader; `auto_confirm_high` promotes STAGED+HIGH. The "non-model provenance" test is defined on the reader, not on the text. Provenance must be sticky and transitive or the gate leaks silently.
3. **Doctrine rule 1 is never addressed.** "Author an extraction map from a sample document," "narrate content-review exceptions," "draft the two-year variance explanation" all imply feeding a prior-year 1040 or a consolidated 1099 to an 8k-context 8B model. No document states a per-task input budget or a chunk/aggregate rule. This is rules 1+2, and it is the first thing that fails in practice.
4. **Doctrine rule 9 is not designed for.** Slice 0 makes the staging gate durable, which without a rule makes a half-finished model run durable too. Needs an explicit invariant: a partial model run leaves no durable trace, or exactly one clearly-marked batch that is inert until accepted.
5. **`Actor` includes `client` and `third_party`.** In a single-user local app with no portal, a client never performs a state change; recording `actor: client` fabricates an event inside a record whose entire purpose is evidentiary. Correct shape is `recorded_by: human:owner` + `information_furnished_by: <person>` — which is literally the §1.6695-2(b)(4)(i)(C) field.
6. **Purge-vs-retain is asserted as resolved and isn't.** Review notes purge on close, but the append-only event log records every state change, and §10.34(a)(2) "pattern of conduct," the §1.6695-2 inquiry log, and 16 CFR §314.4(c)(8) all want survival. If the log carries note bodies the purge is cosmetic; if it doesn't the §10.36 evidence is thinner than claimed. Neither document says which.
7. **The 3-day stockpiling trigger.** The gap analysis lists "stockpiling at 3 calendar days" with no trigger named; the research's checker specifically corrected "3 days from 8879 signature" (wrong) to "more than three calendar days once the ERO has all information necessary for origination." Keyed to the signature date, the alert misfires on every extension and every reject loop.

---

## (c) Asserted beyond what the research established

1. **"Three status authorities run in parallel"** is stated as how practices work. Only the third (Drake ACK) is sourced; the checker found the three-layer model was the researcher's own framing (SmartVault doesn't say it; TaxDome 403'd). Label it as SATC's design decision.
2. **§10.36 as "the regulatory license to be opinionated."** Corrected twice in the research: §10.36(b) requires willfulness/recklessness/gross incompetence **and** an actual pattern or practice of noncompliance by firm personnel, and its application to a genuine firm of one is unresolved on the text. Both docs lean on it to justify the audit log and exception report.
3. **SSTS 1.4 cited as requiring a mandatory human review step.** The checker read the actual PDF: §1.4 contains no such step — that is *The Tax Adviser*'s commentary. §1.4.8 ("enhance … not supplant") is real and sufficient. Cite only 1.4.8; label never-auto-confirm-model-values as SATC policy.
4. **"CCH Axcess: a note can only be cleared by someone other than its creator."** Corrected in the research — CCH *permits* clearing others' notes and prohibits nothing. If SATC wants creator≠clearer, own it as a design choice.
5. **The 10% variance threshold and the 3-day / two-follow-ups cadence** come from one practitioner's 2018 personal checklist whose cover page disclaims that it represents his firm's practices. The AI boundary labels 10% correctly ("a practitioner convention, not law"); the operating model and gap analysis treat both as norms. Make the labeling consistent and both config, visibly marked "firm policy, no citation."
6. **`ids.engagement_key()` "already matches `EngagementRecord`'s PK exactly."** True (and confirmed: zero callers), but the gap analysis then proposes `obligation_key(client_id, tax_year, obligation_type)` — a *different* key that cannot express 941 quarters, monthly deposits, or `2026Q1`. The obligation key needs `period_key`, not `tax_year`. Free to fix now, expensive later.
7. **`comms/render.py:81 render()` → `RenderResult.is_complete` "blocks 'sent'."** Both exist (lines 81 and 55) — but nothing is blocked, because there is no "sent" state on a rendered communication at all. Presented as an existing gate; it is a proposal.

---

## (d) The single biggest risk

**The AI boundary has no enforcement point, and no slice in the plan adds one.**

Verified in the code: `StagingGate.confirm(field_id, *, by: str = "preparer", ...)` takes the actor as a caller-supplied string **whose default asserts a human**, and `AppState.confirm_field(field_id)` (`state.py:146`) takes no actor at all. There is one module-global `STATE`, no authorization boundary (`server.py:63` is a Host/CSRF guard, not authz), and an MCP server in the same process. So today — and after every slice as written — any in-process caller, including a model rung or an MCP tool, can confirm a staged field, post it into `LineItem`s, and have it recorded as the preparer's own act. Doctrine rule 6 says prompt policy holds one run in three; a Markdown policy document is weaker than a prompt.

That inverts the plan's whole value proposition: the deliverable is a record a regulator can rely on, and the record's key field is unauthenticated.

**Fix belongs in Slice 0/1, not Slice 12:** one typed ingress for every model-originated proposal; `actor` stamped by the engine and never accepted from a caller; provenance sticky and transitive through readers, OCR post-correction, and extractors; and a failing test proving a `tool:`-provenance value cannot reach `CONFIRMED`, cannot reach a `LineItem`, and cannot close a `Requested` document.

*Runner-up, one line:* CP-0→CP-3 is a large compliance substrate ahead of any capability the owner can use, while the one feature that pays on day one (prior-year omission diff plus a rendered chase draft) sits behind all of it — and a half-built compliance engine is worse than none, because its partial gates read as assurances.