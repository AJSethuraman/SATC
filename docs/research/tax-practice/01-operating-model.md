# The Operating Model

*How a small US tax practice actually runs, expressed as a system. This is the domain model SATC imitates. Drake remains the system of record for computation and e-file; everything below is the practice around Drake.*

---

## 0. The frame: three authorities and three kinds of time

Every design error in practice-management software comes from collapsing one of these.

**Three status authorities run in parallel and are never the same field.**

| Authority | Who owns it | Vocabulary | What it answers |
|---|---|---|---|
| **Internal stage** | SATC | fine-grained, ~15 states | "What must I personally do next?" |
| **Client-facing status** | SATC, deliberately coarse | ~7 states | "What do I tell the client?" |
| **Filing truth** | Drake / IRS | Drake ACK letters `P A a R B D E S T X` [Drake KB 10783] | "Is it actually filed?" |

SATC never computes the third. It records the letter the owner reads off Drake, then derives deadlines and drafts communications from it. Never show "Filed" on transmission: *"An electronically filed return isn't considered filed until the IRS acknowledges acceptance"* [IRS Pub 1345 Rev. 12-2025].

**Three kinds of date, which must never share a column.**

1. **Statutory dates** — computed, never stored as constants. Pub 509 states them structurally ("the 15th day of the 4th month after the tax year ends"), then shifted for weekends/legal holidays including DC Emancipation Day. Derived from `(entity_type, fiscal_year_end, jurisdiction, holiday_calendar)`.
2. **Regulatory clocks** — start on an *event*, and several deliberately ignore weekends. Notify the taxpayer of a reject within **24 hours**; retransmit by the **5th calendar day** after the due date for a 1040/4868; paper-file by the later of the due date or **10 calendar days** after the rejection notice [Pub 1345]. The transmission perfection period *"has never been extended regardless of weekends, holidays or the end of the year cutoff."* Conflict waiver within **30 days** [31 CFR §10.29(b)(3)]. FTC notification within **30 days** of discovering a 500+ consumer event [16 CFR §314.4(j)(1)] — but the binding one is **next business day** to the IRS Stakeholder Liaison for *any* confirmed incident, no floor [Pub 1345 Standard 6].
3. **Firm-policy dates** — the document cutoff (real firms publish March 15 / March 18 / March 25), internal targets, slot dates. These carry no citation and must be visually distinguishable from law so nobody mistakes one for the other.

---

## 1. Entities

### 1.1 Definitions

**Party layer**

- **Person** — a natural person or entity with a TIN, identified in the encrypted vault and referenced everywhere else by opaque `client_id`.
- **Client** — the party with whom the firm has a relationship; a client may comprise more than one taxpayer (MFJ) and may be an individual *or* an entity.
- **Taxpayer** — the person or entity legally liable for a given obligation. An MFJ 1040 has two taxpayers, one client relationship, one return, and **two** signature lines.
- **Relationship** — a typed, directed edge between clients (spouse-of, owner-of, partner-in, beneficiary-of, officer-of) that generates work and detects conflicts. This is the entity that makes the K-1 dependency graph and the §10.29 conflict check possible; SATC already has it (`Relationship`, `relationships` table) and under-uses it.
- **Consumer** — an FTC Safeguards counting unit, not a client. Needed only to answer two questions: are we under 5,000 (which exempts exactly §314.4(b)(1), (d)(2), (h), (i) — *and nothing else*) [16 CFR §314.6], and did a breach touch 500+.

**Contract layer**

- **Engagement** — the *contracted* relationship for a defined scope and period: engagement letter, fee basis, document cutoff, advance extension consent, §7216 consents, POA/8821 authorizations. One engagement can cover several obligations.
- **Authorization** — a signed instrument granting the firm a specific power or permission, each with signer, signed-at, scope, expiry, and its own retention clock: engagement letter, Form 8879, Form 8821, Form 2848, §7216 consent-to-disclose, §7216 consent-to-use (never the same document [26 CFR §301.7216-3(c)(1)]), extension authorization, Form 8948 taxpayer paper-file choice.
- **Position** — a judgment call taken on a return, carrying `{description, authority_level ∈ MLTN | substantial_authority | reasonable_basis | none, supporting_authorities[], disclosure_form, client_advised_at}`. Reasonable basis is only sufficient *with* adequate disclosure; a reportable transaction raises the bar to more-likely-than-not [IRC §6694(a)(2)]. Circular 230 §10.34(c) makes advising the client of reasonably likely penalties an affirmative duty, so `client_advised_at` is a compliance field, not a nicety.

**Duty layer**

- **Obligation** — a duty owed by one taxpayer, to one jurisdiction, for one period, of one kind: **file**, **pay**, **furnish** (a recipient statement), **elect**, **deposit**, or **report** (FBAR, 8886). This is the entity SATC lacks entirely and needs most.
- **Obligation Rule** — dated, cited config defining, per `(kind, form, jurisdiction)`: the due-date formula, whether extension exists and for how long, the extension form (or `none`), whether a payment obligation is separate, the perfection period, and the blocking document classes.
- **Obligation Instance** — a materialized obligation for a specific period with computed `original_due`, `extended_due`, `postponed_due`, `documents_due`, and a state.

**Work layer**

- **Job** — the unit of work that discharges one obligation instance, running a workflow from config, carrying tasks, a stage, a client status, and a due date inherited from its obligation.
- **Task** — one assignable line of work inside a job (§3).
- **Open Item** — a first-class *thing we do not yet know or have*, with owner, asked-on date, and answer, which must be empty-or-dispositioned before a job advances. Not a task, not a note. *"Open items are listed in one place with owner and deadline"* is one of the five stated conditions of review-readiness [Finsmart 1040 workpaper framework]; Mendlowitz's preparer checklist requires *"Respond to all open items in the software diagnostics so there are no items left for the reviewer."*
- **Review Note** — a defect, question, or instruction raised against a specific field or the return as a whole. Copy CCH Axcess's shape: `{type ∈ Review | Preparer | Missing Item | Note to Next Year, scope ∈ return-level | field-level, body, created_by, created_at, requires_resolution, status, cleared_by, cleared_at, resolution_text}` — the four types differ in *rollforward retention*, which is the interesting part: Preparer notes carry forward, Missing Item and Review notes purge, Note-to-Next-Year becomes next year's open Review note.
- **Inquiry** — a question put to the client *because something looked incorrect, inconsistent, or incomplete*, recorded with the question text, the answer text, and both timestamps. This is legally distinct from a document request and is the single highest-value record in the system: §10.34(d) makes the inquiry mandatory, and §1.6695-2(b)(3)(i) requires the preparer to *"contemporaneously document in the preparer's paper or electronic files any inquiries made and the responses to those inquiries."* Contemporaneous means the timestamps must be server-side and un-backdatable, and the log append-only.

**Evidence layer**

- **Requested Item** — an expected document, with a doc-type from the classifier's own taxonomy, a blocking class, an expected-late flag, and a satisfaction rule.
- **Received Document** — a file that arrived, with **provenance**: how obtained, when, from whom, on which channel, and which request it satisfied. §1.6695-2(b)(4)(i)(C) requires *"a record of how and when the information … was obtained by the tax return preparer, including the identity of any person furnishing the information."* A document with unknown provenance is a compliance defect, not a shrug.
- **Extracted Field** — a proposed value with a source document, page, extractor, and confidence — never a fact until confirmed.
- **Confirmation** — a signature over `(field, value, source_document_hash, procedure_performed, actor, at)`. Not a boolean. Drake's DoubleCheck sets the standard: *"If an item is marked as verified and a change in data entry affects this amount, the green check mark becomes a red flag that requires re-verification"* [Drake KB 13765]. `procedure_performed` exists because "using DoubleCheck as decoration — marking items reviewed without documenting what procedure was actually performed" is a named junior failure mode.
- **Workpaper** — firm-prepared evidence: the two-year comparison, tie-out sheets, computation-method narratives, research notes, the completed checklist. Distinct from source documents and from deliverables. The A–E index (Admin & Tracking / Income / Deductions & Credits / State & Local / Carryovers) is a good default order.
- **Deliverable** — something the firm sends out: the complete return copy, the keying worksheet, the organizer, a letter. Delivery is a legally ordered event, not a status flag.
- **Return** — the prepared document itself, for one taxpayer, period, jurisdiction, and form, in one version (original / superseding / amended).
- **Filing (Submission)** — one *transmission event* for a return: transmitted-at, Submission ID, ACK letter, ACK date, and, if rejected, the IRS business rule ID and element name verbatim. **A return can have many filings.** The Submission ID must be associated with the 8879 [Pub 1345].
- **Notice** — an IRS or state notice against a client: jurisdiction, notice number, date, response deadline, disposition. Failing to check last year's notices against this year's return is on Mendlowitz's Top-12 error list; so is not correcting the *cause* of a prior-year notice.
- **Retention Clock** — a per-artifact computed destroy-not-before date. Never a global tax-year purge, because the clocks genuinely differ: 8879 = max(return due date, IRS received date) + 3 years [Pub 1345]; §1.6695-2 due-diligence records = 3 years from the **latest** of four dates, the first of which keys off the **unextended** due date; conflict waivers = 36 months from *conclusion of the representation* [§10.29(c)]; other ERO records = end of the calendar year. The FTC's two-year disposal default [16 CFR §314.4(c)(6)] is displaced for these by its own "required by law" carve-out — which must be *documented*, not assumed.
- **Actor** — every state change names one: `owner`, `model:<name>@<version>`, `client`, `third_party`, `system`. This is the §10.36 "procedures are followed" evidence and the SSTS 1.4 tool-provenance record in one field.

### 1.2 Distinctions a naive model collapses

| Collapsed | Actually |
|---|---|
| "Filed" | **transmitted** ≠ **filed** ≠ **accepted**. Three events, three timestamps [Pub 1345]. |
| "Extended" | extension to **file** ≠ extension to **pay**. Two obligations, two deadlines, two failure modes. |
| "On extension" = parked | Extension is an **In Progress** status with a new due date and a still-open request list [Karbon US Core 1040/1041]. |
| "Due date" | statutory due date ≠ perfection deadline (calendar days, no weekend shift) ≠ firm cutoff ≠ postponed date (FEMA). |
| "Ask the client" | **request** (a document) ≠ **inquiry** (a §10.34(d) question about an inconsistency). Only the second is a due-diligence artifact. |
| "Note" | **review note** (a defect, purgeable) ≠ **open item** (a blocker) ≠ **EF Message** (Drake, blocks e-file) ≠ **Return Note** (Drake, informational, does not block) [Drake KB 10117]. |
| "Reviewed" | **content review** (tick-and-tie every input to a source) ≠ **issue review** (planning items, judgment calls). Mendlowitz argues exhaustive content review *degrades* quality via reviewer fatigue and should be automated or spot-checked. The machine does content; the human does issues. |
| "Document received" | received ≠ classified ≠ extracted ≠ **confirmed**. And a document can be silently *unmatched* — SurePrep files SSN-mismatched documents under "Incorrect SSN / Unused" and captures nothing. A dropped document is an omission tick-and-tie structurally cannot catch. |
| "Complete" | **SATC package complete** ≠ **owner released** ≠ **Drake green (no EF Messages)** ≠ accepted. Green EF status is technical eligibility, not permission to release. |
| "Client" | client ≠ taxpayer ≠ consumer ≠ signer. |
| "Sent" | copy **furnished** to the taxpayer ≠ 8879 **sent** ≠ 8879 **signed**. IRC §6107(a) requires the completed copy *"not later than the time such return … is presented for such taxpayer's signature."* |
| "Missing" | outstanding ≠ **expected-late** (K-1, consolidated 1099-B) ≠ **not applicable with a stated reason**. Drake Portals gets this right: the client can mark an item N/A *with an explanatory reason*, which is how "still waiting on the 1099-INT" resolves into "they closed that account in March." |
| "Fee" | engagement (contract) ≠ fee (amount) ≠ invoice (the billing event, fired at **delivery**, not at acceptance). |
| "Prior-year data" | rolled-forward values are **proposed**, never accepted. "Copying prior-year information without LookBack analysis" is a named failure mode. |

### 1.3 Where SATC's vocabulary is wrong or too coarse today

| Current | Problem | Replace with |
|---|---|---|
| `EngagementRecord` (mart.py:152, PK `client_id`+`tax_year`, fee + letter status) **vs** `IntakeEngagement` (intake.py:145, workflow instance with tasks) | Two unrelated concepts share one word. Every future conversation about "the engagement" is ambiguous. | `EngagementRecord` → **Engagement** (contract: letter, fee, cutoff, consents, authorizations). `IntakeEngagement` → **Job** (a work instance discharging one obligation). `ids.engagement_key()` (ids.py:65, currently dead code) becomes the Engagement PK. |
| `PipelineStatus` (mart.py:28-30): `Awaiting docs → In prep → In review → Ready to file → Filed → Accepted → Rejected`, written in exactly one place, hardcoded to `"In prep"` (state.py:357) | Conflates all three authorities into one column; has no delivery, no signature, no transmission, no extension, no ack code, and no transition guard, history, or timestamp. "Filed" is factually wrong as a name for transmission. | Three fields: `Job.stage`, `Job.client_status`, `Filing.ack_code`. Adopt Drake CSM names where they overlap (**Waiting on Documents, In Progress, Under Review, Signed, Complete, EF Pending, EF Accepted, EF Rejected, EF Ext Accepted**) so the owner never translates between two systems [Drake KB 10580]. |
| `DocStatus = Literal["Requested","Received","Sent","Signed","N/A"]` (mart.py:166) on a single `DocumentRecord` | One enum spans four different lifecycles. A row cannot be both a thing we asked for and a thing we sent. "N/A" carries no reason. No provenance fields at all. | Four entities: **RequestedItem** (Outstanding / Expected-late / Satisfied / Not applicable + *reason* / Withdrawn), **ReceivedDocument** (+ `obtained_how`, `obtained_at`, `furnished_by`, `channel`, `satisfies_request_id`), **Deliverable** (Assembled / Furnished-at), **Authorization** (Prepared / Out for signature / Signed-at / On file / Superseded). |
| `IntakeTask.completed: bool` (intake.py:138) | Cannot express blocked, waiting-on-client, in review, waived-with-reason, cancelled, or escalated — even though the *document* it points at has five states. | Status enum + `blocked_by[]` + `waived_reason` (§3). |
| `IntakeTask.suggested_date` only; no per-task real due date; nothing anywhere compares a date to today | Nothing is ever overdue. A practice is a deadline engine; this one has no clock. | Keep `suggested_date` as the derived hint; add a real `due_date`, plus an escalation state and a follow-up round counter. |
| `ReturnRecord.is_extended: bool` (mart.py:70) | An extension is a filed return with a reason, an authorization, an estimated payment, an ack, a perfection window, and a new due date. A boolean loses all of it. | An **Extension** entity on the obligation (§2.3). |
| `preparer_id: str = ""` (mart.py:68, mart.py:161) — free text, no staff table, never written | Wrong axis for a firm of one. The question is never "which person" but "human or model, and was it confirmed." | `actor` on every event, with `model:<name>@<version>`; plus an **autonomy ceiling** per artifact class (§3.3). |
| `IntakeEngagement.period_end: str` (intake.py:153) — free text, set by nothing, read by nothing | This is the recurrence anchor and it is a string nobody writes. | A real `period_key` (`2026`, `2026Q1`, `2026-03`) — the idempotence key for the whole recurring-obligation model. |
| `LineItem.provenance` flattened to `(source_kind, citation)` on write; `Carryforward` / `OwnerBasis` / `EstimatePayment` persist none | Provenance is a legally required record [§1.6695-2(b)(4)(i)(C)], not debug metadata. Losing confidence, extractor, page, and document_id makes the file unreconstructible. | One shared `provenance` table keyed `(table_name, row_key)`, lossless. |
| `document_id = path.name` (state.py:247); `field_id = f"{document_id}:{field_path}"` | Two files with the same basename in different subfolders collide, and `StagingGate._find` returns the first match — a confirm can land on the wrong field. | Content-hash-derived document ids. A legal evidence record cannot be keyed on a colliding identifier. |
| No `created_at` / `updated_at` on any mart table except `intake_engagements` | "Contemporaneously document" is a timestamp requirement. A schema with no timestamps cannot satisfy §1.6695-2(b)(3)(i) on its own terms. | Timestamps everywhere; an append-only event log for state changes. |
| `models/review.py` (`ReviewItem`, `Checklist`, `gating`) — well-designed, never instantiated, no table; its only consumer is an Excel dropdown | The right shape with no body. Missing scope FK, author, created_at, cleared_by/at. | Make it real (§3.2). The existing `gating` flag is already the "blocks advance" hook a state machine consults. |

---

## 2. The return lifecycle

### 2.1 What the three fields hold

```
Job.stage           — internal, drives the owner's queue
Job.client_status   — coarse, selects the comms template; internal stage names never leak into client text
Filing.ack_code     — Drake's letter, keyed by the owner, never computed by SATC
```

`client_status` vocabulary: *Not started · Waiting on you · In preparation · In review · Ready for your signature · Filed — awaiting IRS · Accepted · Action needed*.

### 2.2 Main line

Each transition names what must be **TRUE** to advance. A guard that fails is an error with a named next step, not a warning (doctrine rule 3).

| # | Stage | Guard to ENTER | Artifact produced | Who may advance |
|---|---|---|---|---|
| 0 | **Rolled Forward** | Obligation instance materialized for the period | Prior-year-derived requested-item list; predicted extension reason code | model |
| 1 | **Engaged** | Signed engagement letter on file for this scope + period | Engagement letter (signed); fee basis; document cutoff date; advance extension consent | human |
| 2 | **Waiting on Documents** | Request list opened; first request rendered | Missing-items request enumerating the *actual* open list | model drafts, human sends |
| 3 | **Prep Ready** | Every **blocking** requested item is Satisfied or N/A-with-reason; expected-late items may remain open; readiness computed and *recorded* | Readiness record: what was unsatisfied, what was N/A and why, who decided to proceed | human acknowledges |
| 4 | **In Prep** | — | Drake keying worksheet, ordered to minimise EF Messages (identity/dependents → income → state), each line hyperlinked to its confirmed source page, with a "prior year had data here, this year does not" column | model proposes, human confirms every field |
| 5 | **Self-Review Done** | Zero unexplained variances over threshold; zero unmatched documents; zero open items without disposition; every posted amount traced to a confirmed source; 8867 record complete for **each** benefit claimed | Two-year comparison with a typed explanation on every flagged line; content-review header ("N of N amounts traced, M exceptions"); research notes; open-items list | model completes, human attests |
| 6 | **Under Review** | Stage 5 passed | One-page **Issues for you** sheet (judgment items and planning opportunities, ranked) — *not* 200 ticks | human only |
| 7 | **Reviewed** | Every `requires_resolution` review note cleared by the owner; reviewer checklist attested; **Drake EF Messages cleared federal-then-state and every Return Note dispositioned** (a fact the owner keys — SATC does not own Drake's red X) | Signed, dated review event; printable checklist with Client / Year / Date / By | human only |
| 8 | **Delivered** | Complete return copy assembled; preparer signature + PTIN present | `furnished_at` recorded. IRC §6107(a) makes furnishing a *precondition of signature*; §6695(a)–(e) failures are $65 each up to $33,000 for returns filed in 2027 — all of them practice-ops failures, not Drake's problem | human |
| 9 | **Awaiting Signature** | `delivered_at IS NOT NULL` | 8879 out; signature method recorded (`wet` / `in-person e-sign` / `remote e-sign`) | human |
| 10 | **Signed** | Signed 8879 exists **with the taxpayer's own signature date ≥ `delivered_at` and ≤ today**; the five signed figures snapshotted; for remote e-sign, identity verification recorded, and after three failed KBA attempts the required artifact switches to a wet signature | Snapshot of Total income, AGI, Total tax, Federal withholding, Refund, Amount owed | human only |
| 11 | **Ready to Transmit** | All W-2 / W-2G / 1099-R in hand **or** a Form 4852 on file; signature still valid under the $50/$14 test; no unresolved position lacking required disclosure | "You may hit send in Drake" | engine computes, human acts |
| 12 | **Transmitted** | Owner records it; ack becomes `P` | Submission ID | human |
| 13 | **Accepted** | ack `A` (or `a` for an extension) | IRS received date → starts retention clocks | human keys |
| 14 | **Complete** | Billing fired at **delivery**, not here; invoice itemised with the extras discovered during prep | — | human |
| 15 | **Archived** | Required set present: signed 8879 + Submission ID, W-2/1099-R copies, signed consents, complete return copy, ACK; every retention clock computed; **review-note bodies purged** | Retention manifest with destroy-not-before dates | human |

**Two aging alarms on the main line.** Stage 11 sitting **3 calendar days** after all information needed for origination was in hand is a Provider-compliance problem, not slow service — *"stockpiling refers to waiting more than three calendar days to submit the return to the IRS once the ERO has all necessary information for origination"* [Pub 1345]. (Note: this clock starts on *having everything*, **not** on the 8879 signature date; the widely repeated "transmit within three days of receiving the signed 8879" conflates two different rules.) Stage 12 sitting without an ack near a due date is the highest-severity item on the dashboard.

**Guard 3 is the one that pays for the product.** *"Do not start work on a return until you are sure all the information has been provided"* [Mendlowitz], with the real-world carve-out *"I won't work on a file until data is complete besides a late K-1 or brokerage statement"* [Burkemper client letter]. So requested items need three flavours: **blocking** (W-2/W-2G/1099-R are blocking by IRS rule), **expected-late** (does not block prep start, does block stage 11), and **non-blocking**.

**Verification invalidation cascades.** If a source document is re-classified, re-extracted, or replaced after a value was confirmed, the confirmation reverts to unconfirmed *and the job falls back from stage 5 to stage 4*. This is Drake DoubleCheck's semantics [KB 13765] applied one layer upstream, and it is cheap here because classification is already content-hash based.

### 2.3 The extension branch

Extension is **not a stage**. It is a separate obligation instance with its own return, filing, ack, perfection window, and payment sub-obligation, attached to the parent.

```
[cutoff date passes with readiness < threshold]  OR  [predicted reason code at rollover]
        ↓
   Extend Candidate            ← flag only; SATC proposes, never decides
        ↓  requires ExtensionAuthorization {client, date, channel, estimated_tax_shown}
   Extension Prepared          ← guard: estimated tax > 0
        ↓
   Extension Transmitted → ack 'a' → EF Ext Accepted
        ↓
   parent.due_date := extended_due;  parent.stage stays In Progress;  request list stays open
```

**Non-negotiables on this branch:**

- **The client decides, in writing.** *"Even for current clients and clients who have historically filed an extension, do not do so until you receive the client's written permission"* — filing without authorization can destroy the client's reasonable-cause defense and implicate §7216 [Journal of Accountancy]. SATC must refuse to mark an engagement extended without the authorization artifact.
- **A $0 extension is a hard error, not a warning.** Treas. Reg. §1.6081-4(b)(4) requires *"the total amount properly estimated as tax for the tax year"*; Rev. Rul. 79-113 invalidated a zero-liability extension. The withholding estimator is the natural source of the figure, carrying an explicit "Drake computes the filed number" disclaimer.
- **Payment is a separate obligation with a separate deadline.** Model the variant where the client pays online and checks the extension box — that produces no 4868 artifact at all and would otherwise look like a missing document forever.
- **Extension lengths are per-form config, not `+6 months`.** 1040/1065/1120-S/1120/990 → 6 months; **Form 1041 → 5½ months (Sept 30, not Oct 15)**; 990-N → not extendable at all, so the UI must refuse to offer it. The June-30 fiscal-year 1120 seven-month rule sunsets for tax years beginning in 2026 — already expired for anything being specced now.
- **Extension reason codes drive the message.** "Waiting on your K-1" reads nothing like "we are holding the return open for your SEP decision." Reason codes assigned at rollover produce a January list of *"these N clients will extend"* — the single highest-leverage planning artifact for a firm of one.

### 2.4 The rejection loop

```
ack 'R'
  ├─ record business rule ID + element name VERBATIM (the client notice must contain them)
  ├─ notify_by     = rejected_at + 24 hours          ← loudest alarm in the app
  ├─ retransmit_by = due_date + 5 calendar days      (1040 / 4868 / 7004 / 8868)
  │                = due_date + 10 calendar days     (1120, 1120-S, 1065, 1041, 990)
  │                  ← calendar days; NEVER shifted for weekends or holidays
  └─ paper_file_by = max(due_date, rejection_notice_date + 10 calendar days)
        ↓ fix
   re-run the $50 / $14 test against the signature snapshot
        ├─ within tolerance → Ready to Transmit on the original signature
        │                     (and give the taxpayer copies of the corrected return data)
        └─ over tolerance   → back to Awaiting Signature; new 8879 required
```

`ack 'D'` (duplicate) **hard-blocks** any resend. `ack 'B'` / `'X'` are transport failures, not IRS rejections, and must not start the 24-hour clock.

**Pre-transmit name-control check.** *"Incorrect TINs, using the same TIN on more than one return or associating the wrong name with a TIN are some of the most common causes of rejected returns"* [Pub 1345] — classically a newly married taxpayer whose name change has not reached SSA. One intake question ("did you marry or change your name this year?") plus the vault's last-4 prevents the largest reject class.

**Unresolved, do not guess:** Drake KB 13325 and Pub 1345 both give **5 days** for a 1040, but Intuit publishes April 23 for an April 15 deadline (8 days). Treat the vendor-published calendar date as authoritative over your own arithmetic, surface the discrepancy to the owner, and read IRM 3.42.5.14.6 before encoding either.

### 2.5 The post-signature change loop

Any keyed figure change after stage 10 — a late 1099, a reject fix, a review correction — re-runs the comparison against the snapshot and emits a **hard verdict with the arithmetic shown**:

> **RE-SIGN REQUIRED.** AGI moved $1,240 (limit $50). Total tax moved $310 (limit $14).

This is a comparison, not a tax computation, so it does not touch "Drake is the system of record." The thresholds are Publication-set and **not permanent** — dated config keyed to the publication revision, never constants.

### 2.6 Off-ramps

- **Paper filed** — reachable from client preference or an unfixable reject. Requires a reason mapped to a Form 8948 line, plus a documented taxpayer-choice statement when the reason is client preference (a preparer expecting 11+ covered returns is mandated to e-file). Without this the paper branch is where compliance quietly leaks.
- **Disengaged / Withdrawn** — must trigger a **client records export** that returns everything the client provided and everything a third party provided, promptly, *notwithstanding a fee dispute* [§10.28(a)]. Hard-code the exemption: if invoicing ever gains a dunning feature, this export must never be gated on payment. (One genuine carve-out: the firm's *own* prior-year work product may be withheld pending payment of the fee **for that specific document** — the exclusion is document-specific.) Also triggers a POA/8821 withdrawal review [Pub 4557].
- **Amended / Superseding** — a new Return version against the same obligation, with its own filing chain.

---

## 3. The work item model

### 3.1 Task

A **Task** is one unit of assignable work inside a job.

```
Task {
  task_id, job_id, template_id          # template_id preserves identity across regeneration
  title, category, audience             # internal | client
  status        ∈ Not started | In progress | Waiting on client | Blocked
                  | Awaiting review | Done | Waived(reason) | Cancelled
  actor_allowed ∈ model_may_complete | model_may_propose | human_only
  assignee      ∈ owner | model
  due_date                              # real, per-task
  suggested_date                        # derived hint from days_before_due
  blocked_by[]                          # task or obligation ids
  requires_resolution: bool             # gates the job's stage advance
  follow_up_round: int                  # 0,1,2… drives WHICH template renders
  escalated_at                          # set after the second unanswered follow-up
  document_id                           # for client requests
  completion { by, at, procedure }      # never a bare checkbox
  minutes_owner, minutes_model
}
```

**Status, not a boolean.** `IntakeTask.completed: bool` cannot express the states the work actually occupies, and the linked document already has five.

**Follow-up is a counter, not a calendar.** *"If you need to contact a client for additional information, do so, and follow up every three days thereafter until you get the information. If you do not receive what you request after two follow up calls, notify your supervisor when it would be the time for you to make a third follow up call"* [Mendlowitz]. Reminders fire off **document status**, not arbitrary calendar intervals, and the reminder text names the specific missing documents, regenerated fresh at send time. A second request must render different copy from a first — that is what the round counter is for. (One vendor default worth adopting as the floor: first nudge at T+3.)

**Ad-hoc tasks must be possible.** Today the only way a task exists is because a workflow condition matched. Notices, research, a one-off client ask, and firm admin have no home. Tasks need durable identity independent of config.

### 3.2 The three things that are not tasks

| | Answers | Retention | Blocks? |
|---|---|---|---|
| **Open Item** | "What don't we have or know?" | Durable through close | Yes — job cannot advance |
| **Review Note** | "What's wrong with this and why?" | **Body purged at sign-off; event retained** | If `requires_resolution` |
| **Inquiry** | "We asked the client X because Y looked wrong; they said Z" | 3 years from the latest of four dates | No — but its absence blocks |

**The review-note retention decision — make it explicitly.** Mendlowitz is blunt: *"Keeping review notes after the return is completed … can create liability issues if there is ever a controversy over the return … Retaining these notes cannot ever help you."* But §10.34(a)(2) ("a pattern of conduct is a factor") and §1.6695-2(d) ("normal office procedures … reasonably designed and routinely followed") both want evidence over time. **Resolution: split the note.** The *body* is ephemeral and purged by an explicit "Close review" action that asserts zero open items and logs that the purge happened. The *event* — a note of type T was raised on field F, cleared by the owner on date D — is durable, PII-free, and is exactly the aggregate the §1.6695-2(d) defense needs. Never silently persist model-authored critique text into the archived engagement.

**A review note needs two fields, not one.** *What is wrong* and *why / what the correct treatment is*. The second is what survives as next year's Preparer note and what defends a position later — and it is exactly where a model must cite the confirmed source document or the prior-year value rather than assert.

**Do not build "reviewer fixes it inline."** Build "reviewer flags, and the flag reverts the field to unconfirmed." That matches DoubleCheck and preserves the record of what changed.

*(CCH Axcess permits clearing notes created by other staff and logs it; it does **not** prohibit self-clearing. If SATC enforces creator ≠ clearer — e.g. the model raised it, the owner clears it; the owner raised it, a second pass on a different day clears it — own that as a SATC design decision, not as vendor parity.)*

### 3.3 Four roles collapsed onto one human and one local model

Karbon's shipped 1040/1041 template defines **Admin, Preparer, Reviewer, Client Manager**. In a firm of one the *people* collapse but the **handoff points survive** — and the Preparer→Reviewer handoff is exactly where the model must stop.

| Role | Who | Autonomy |
|---|---|---|
| **Admin** | model | May complete: classify, split, name, file, build the checklist from prior year, compute readiness, materialize obligations, render drafts. |
| **Preparer** | model proposes, human confirms | May propose: extracted values, variance explanations, inquiry wording, review notes, research notes, requested-item lists. May not accept anything into the mart. |
| **Reviewer** | **human only** | No model output may auto-clear a note, satisfy a checklist item, or advance a stage. |
| **Client Manager** | human sends, model drafts | No SMTP by design; every outbound artifact is a draft a human reads and sends. |

**Why the reviewer line is hard and not stylistic.** §10.22(b)'s due-diligence presumption is written for reliance on *"the work product of another person"* with reasonable care in engaging, supervising, training, and evaluating them — by its terms it does not reach a tool, and no authority extends it (§10.35 competence is the better hook for tool use). AICPA SSTS 1.4.8: *"Tools should be used to enhance or improve the member's understanding of a tax issue, not to supplant the member's professional judgment"* — and 1.4.4, *"use of a tool does not absolve the member of professional obligations."* IRS OPR's 2026 AI guidance frames AI output as *"a starting point, not a finished product."* **Note honestly what SSTS 1.4 does *not* say:** it contains no mandatory-final-review-step and no generative-AI language — that is commentary. Build the gate because the doctrine and §10.35 demand it; do not cite 1.4 as if it mandates the gate.

**Autonomy ceiling by artifact class** — the modern replacement for "which preparer level":

| Artifact | Model may | Never |
|---|---|---|
| Document classification | propose, and auto-file at HIGH confidence | flip a **Requested → Received** status on a regex match without a gate |
| Extracted field | propose at LOW confidence | reach the keying worksheet unconfirmed |
| Extraction map / family pattern / line mapping (**config**) | propose a diff a human merges | edit config at runtime |
| Variance explanation, inquiry text, review note, client draft | draft | send, or resolve the thing it drafted about |
| Any tax figure, eligibility determination, position | — | **anything**. Frontier models correctly compute fewer than a third of even simplified 1040s and misjudge CTC/EITC eligibility [TaxCalcBench, arXiv 2507.16126 — an academic benchmark from a commercial vendor, not a regulator]. An 8B model is strictly worse. |

**The 30-minute leash, applied literally.** *"If you need to look up or research something, do not spend more than 30 minutes on it … Include on your list of open items a brief summary of what you found out or weren't able to find out."* The model's research note has a fixed shape: **question / what I found / source / what I could not determine / effort**. A model that cannot answer must be able to return *"not found"* and have SATC render that as an open item — a tool that always produces an answer is worse than one that admits ignorance.

**Give-up tail (doctrine rule 9).** A half-finished model run must be **inert by construction**: everything lands staged, nothing posts. There is no partial state a wrapper's retry can corrupt.

### 3.4 Capacity is denominated in owner-minutes

For a firm of one, the preparer and the reviewer are the same person, so the classic "reviewer minutes are the constraint" framing partly dissolves — but the *measurement* does not. Track two numbers per engagement and nothing else:

- **`minutes_owner`** — actual time the human spent at the confirmation gate, in review, and chasing the client.
- **`kickback_rate`** — share of model-proposed fields the human corrected.

If an AI feature raises `minutes_owner` per return, it has made the firm smaller, and the dashboard should say so in those words. Do not build timesheets, WIP aging, or realization reporting — that is multi-person overhead. Do compare `minutes_owner` against the fee, per return, per season: a return whose effective rate collapses year over year is mispriced or has scope-crept, and that is January's pricing conversation.

**Capacity is a schedule, not a queue.** One solo practitioner who moved from first-come to a calendar found honest capacity was **66 returns** against ~90 he had been producing — *"The calendar wasn't wrong. It was honest."* Hold back a reserve (that account implies 25–30%) for amendments, notices, prior-year cleanup, and rescue work. Each engagement gets a scheduled prep week and a client-facing document-due date a week earlier; missing it reschedules to the next open slot as a **normal state transition**, not an exception. Surface the gap in January: "you have 66 slots and 71 engagements."

**Queue order is derived, never hand-set:** sort by *the date the file became prep-ready*, which is a different timestamp from the date the client engaged or the date documents started arriving.

---

## 4. The recurring obligation model

The goal: **nobody ever remembers to create work.** Obligations are derived from facts about the client; jobs are derived from obligations.

```
Client facts (Obligation Profile)
      × Obligation Rules (dated, cited config)
      → Obligation Instances (materialized per period)
      → Jobs (a workflow from config)
      → Tasks
```

### 4.1 Obligation Profile — the facts that generate duties

Per client: entity type; **fiscal year end** (without it no date can be computed at all); jurisdictions of filing / residency / nexus; payroll status (941 vs **944 — IRS-assigned by written notice, stored as a fact with its source document, never inferred**; monthly vs semiweekly depositor, redetermined annually from the lookback period); information-return volume (the 10-return aggregate threshold across *all* types changes the filing channel); foreign financial accounts with a **max** balance over $10,000 at any time (not year-end); PTET election eligibility; estimated-tax requirement; K-1 sources via the relationship graph; disaster-area county.

### 4.2 Obligation Rule — dated config, alongside `configs/workflows/`

```yaml
- kind: file
  form: "1041"
  jurisdiction: US
  due: {basis: fiscal_year_end, months: 4, day: 15}
  extension: {available: true, form: "7004", months: 5.5}   # Sept 30, NOT Oct 15
  perfection_days: 10
  blocking_docs: []
  source: "IRS Instructions for Form 7004 (Rev. December 2025)"
  effective_filing_year: 2026
```

`extension.available: false` for Form 990-N and for a PTET *election* means the UI physically cannot offer relief that does not exist.

### 4.3 Obligation Instance

`{taxpayer_id, kind, form, jurisdiction, period_key}` — that composite is the **idempotence key**. Carries `original_due` (computed), `extended_due` (only once an extension is accepted), `postponed_due` (a FEMA override record with declaration ID, counties, source URL, and the date recorded — never inferred, and never auto-applied since eligibility keys off the IRS *address of record*), `documents_due` (firm policy), and a state.

### 4.4 What fires the generator

| Trigger | Generates |
|---|---|
| **Season rollover** (mirrors Drake's `Last Year Data > Update Clients`) | Next year's obligations for every active client; last year's requested-item list as this year's opening request list — *the single highest-leverage automated-junior move*; an explicit retention decision for any client present last year and not rolled |
| **Period close** | 941/940 quarters, estimate installments, monthly bookkeeping, payroll deposits |
| **Entity return accepted** | K-1 **furnish** obligation → unblocks each partner's/shareholder's 1040 |
| **New fact on a document** | A new state on any W-2/1099 → a state return obligation; a 1099-B → an expected-late flag |
| **Intake answer or vault delta** | Address change vs prior address → "confirm residence sale / §121" + "part-year state returns?"; age crossing 73 → RMD task; marriage/name change → name-control pre-check; foreign accounts → FBAR |
| **Cutoff date reached with readiness below threshold** | Extend-candidate flag + extension-authorization draft |
| **Client marked inactive** | POA/8821 withdrawal review |
| **Model detects an inconsistency** | An **Inquiry** (never a correction) |

**Estimates and information returns are the two streams a 1040-centric calendar silently drops.** Individual installments run 4/15, 6/15, 9/15, 1/15-of-the-following-year over unequal 2-, 3-, and 4-month income periods; **corporations run 4/15, 6/15, 9/15, 12/15 with no January installment**. On the January side, 1099-NEC and W-2 have a hard January 31 date with **no automatic extension available** (Form 8809 explicitly excludes them), while 1099-MISC splits recipient-furnish from IRS-file — model furnish and file as **two obligations on one form**.

### 4.5 Dependency edges are the whole point

`blocks(obligation_a, obligation_b)`. The canonical case: an extended 1065/1120-S is due Sept 15 and the 1040 consuming its K-1 is due Oct 15 — a **30-day window**. An extended 1041 K-1 lands Sept 30, leaving **15 days**. On Sept 16, "which 1040s unblocked today?" is a query, and "which are still blocked?" is an escalation list. This is the dependency a firm of one gets wrong most often, and it is the most legible job a local model can be given: reason over the graph, never over the numbers.

### 4.6 Idempotence and drift

Regenerating a period must never duplicate: keyed on the composite above, "already exists as requested" is **success**, not a conflict (doctrine rule 4). Today `create_engagement` mints a brand-new engagement and a brand-new set of Requested documents every time, and a task dropped by a changed condition **orphans its DocumentRecord forever** — `regenerate_engagement` (workflows.py:388) already preserves progress by `template_id` and is tested, but is wired to no route, and nothing retires orphaned requests. Both must be fixed before recurrence can be trusted: a document-reconciliation step that withdraws orphaned Requested rows belongs next to `create_engagement`, the only place requests are opened.

### 4.7 Firm-level recurring obligations

Not client-scoped, and exactly the chores a solo owner drops. They belong in the same task list:

- **Weekly** — EFIN/PTIN return-count check, recording the observed count so an anomaly is a jump rather than a vibe; backup verification (weekly in season, monthly out) [Pub 4557].
- **Every 30 / 90 days** — security review; event-log review. *(These cadences come from IRS Pub 5708, which is a **sample template**, not a mandate — label them as recommended practice, not law.)*
- **Mid-July** — 1099/W-2 correction sweep before the August 1 penalty tier steps up.
- **October** — refresh the dated-parameter table from the new revenue procedure.
- **Annually** — WISP review dated within 12 months, wired as a dependency on the PTIN renewal task. *(Form W-12 Line 11 asks the preparer to check Yes/No on **awareness** that a WISP is required; the application as a whole is signed under penalties of perjury. Do not tell the owner that checking the box is a sworn representation that a plan exists.)*
- **Within 30 days of any change** — update the IRS e-file application when the Responsible Official, address, or phone changes. Undeliverable mail is itself grounds for EFIN inactivation, which stops filing mid-season.

---

## 5. Invariants the engine refuses to break

These are guards, not warnings. Each names its next step when it fires.

1. **No transmission before signature, no signature before delivery.** `signed_at ≥ delivered_at`; a signature date in the future blocks [Pub 1345; IRC §6107(a)].
2. **No e-file before the W-2/W-2G/1099-R are in hand** or a Form 4852 is on file [Pub 1345].
3. **A materially changed return invalidates its signature** by the dated $50/$14 test, and re-opens the 8879 state.
4. **A changed source document invalidates every confirmation derived from it**, and knocks the job back a stage [Drake DoubleCheck semantics].
5. **The model never writes a value that matters.** Only CONFIRMED fields post. Every proposal enters at LOW confidence; only deterministic, text-layer-matched reads may auto-confirm. Doctrine rule 6: policy lives at the engine choke point, never in a prompt.
6. **The model never resolves an inconsistency by choosing a value.** It may only draft the inquiry [§10.34(d)].
7. **No client data leaves the machine.** §7216 defines disclosure as *"making tax return information known to any person in any manner whatever"*, and tax return information expressly includes what the preparer *derives or generates* — including statistical compilations, so the de-identified mart is **not** outside §7216. A model whose weights sit on the owner's machine engages no recipient; that is an unlitigated reading of the text, not a blessed safe harbor, so state the architecture fact ("data never leaves this machine"), not the legal conclusion. Enforce it: no telemetry, no crash reporting carrying client-derived fields, no remote inference endpoint, no bring-your-own-API-key escape hatch, and a test that fails the build if any egress-capable call site is reachable from a code path touching vault plaintext.
8. **No outbound artifact to a non-taxpayer recipient without a §7216 consent** naming that recipient and purpose, from a locked template carrying the Rev. Proc. 2013-14 §5.04 mandatory language verbatim, refusing to render with any unfilled placeholder, never mixing a consent-to-use and a consent-to-disclose in one document, immutable after signature.
9. **No engagement reaches Archived** with a missing required artifact or an uncomputed retention clock; **review-note bodies are purged** as part of that transition, and the purge is logged.
10. **No written advice containing audit-lottery reasoning.** §10.37(a)(2) forbids taking into account *"the possibility that a tax return will not be audited"* — lint every template and every model draft for that phrase family and **block**, not warn.
11. **No contingent fee for return preparation** in any future invoicing surface, except against one of the four §10.27(b) exceptions [§10.27].
12. **No signature-ready status for any return claiming EITC / CTC-ACTC-ODC / AOTC / HOH** until **each** benefit's due-diligence record is complete — four independent records, four independent penalty exposures at $650 per failure for returns filed in 2026 ($665 for 2027), uncapped, up to $2,600 on one return [§1.6695-2(a)(1)].
13. **Overrides are recorded, never silent.** A skipped step with a reason and a timestamp preserves the §1.6695-2(d) "normal office procedures … routinely followed" defense; a silent bypass destroys it.
14. **Records return is never gated on payment** [§10.28(a)].

---

## 6. What must be dated config, never a constant

Every one of these moved recently or moves annually. Each row carries a source URL, a revision, and an **effective filing year** — because several are keyed to the year of *filing*, not the tax year.

| Parameter | Note |
|---|---|
| 8879 re-signature thresholds ($50 income/AGI, $14 tax/withholding/refund/balance) | Publication-set, not statutory |
| §6695(g) due-diligence penalty | $650 for returns filed in 2026; $665 for 2027; indexed under §6695(h) |
| §6695(a)–(e) penalties | $65 each / $33,000 cap for 2027 filings — the un-indexed "$50 / $25,000" statutory figures are wrong to display |
| §6698/§6699 per-partner-per-month | $255 (2026 filings) / $260 (2027) — drives March 15 alert severity by partner count |
| §6721/§6722 tiers and the August 1 step-up | $340 / $60 / $130 for 2027, with different caps by gross receipts |
| Perfection periods | 5 days (1040, 4868, 7004, 8868) / 10 days (business returns) — and the Intuit-vs-arithmetic discrepancy flagged, not resolved by guessing |
| Extension lengths | Including 1041's 5½ months and the expired 1120 June-30 seven-month rule |
| MeF blackout + filing-season open dates | Announced by QuickAlerts each fall; four separate reopen dates by return family |
| Federal + DC Emancipation Day + state holiday calendar | Drives the weekend/holiday shift |
| FEMA disaster postponements | A data feed with provenance and a human confirmation gate — never a rule |
| **Form line numbers** | **Derive per tax year from the form itself.** Withholding is line 25 on the current 1040, not line 17 (a 2019 layout still circulating in practitioner blogs); line 1 is now subdivided 1a–1z. Freezing line numbers from any secondary source points the owner at the wrong line on a real return. |
| Variance threshold (10%), follow-up cadence (3 days), research cap (30 min), document cutoff | **Firm policy**, no citation — displayed as policy, editable, visibly separate from law |

---

## 7. Open questions this model deliberately does not answer

- **Does Drake expose CSM status, EF Messages, DoubleCheck state, or LookBack values in any readable file or export?** This decides whether SATC's queue is a read-only mirror of Drake truth or an independently maintained state that drifts. Until confirmed, design for a small guided reconcile screen where the owner keys the ACK letter and SATC computes everything downstream.
- **How does a single operator perform a preparer/reviewer split on themselves?** Every review source assumes two humans. Whether the defensible substitute is a cooling-off period, a print-and-read-on-paper pass, a peer swap with another solo, or a model-generated review-note pass is unanswered by anything retrievable, and needs a practitioner conversation, not more searching.
- **Does the owner want the content-review result as all ticks, exceptions only, or a sampled spot check?** Mendlowitz argues exhaustive content review causes the fatigue that destroys review quality. This is a product decision to grill, not a research finding.
- **How does the FTC's 500-consumer threshold count an MFJ return** — one consumer or two? It changes the breach math and no guidance resolves it.
- **What review-note wording does this owner actually use?** No source produced a real review note verbatim. If a local model is going to author them, sample the phrasing from the owner's own files rather than inventing a house style.
- **State layer beyond the home state.** Per-jurisdiction due dates, extension mechanics (Virginia's is automatic with no form — so "extension filed?" as a boolean is already wrong), state 8879 equivalents with their own retention rules, state AG breach deadlines, and PTET election calendars. Ship only the states the firm actually files, each as dated cited config, and **refuse to guess** for the rest rather than defaulting to the federal date.