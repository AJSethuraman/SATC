# PRD: Client interview & consolidated field registry

**Status:** Draft · **Owner:** Arjun Sethuraman · **Last updated:** 2026-08-14

---

## 1. Problem

A prospect submits the website intake. An email arrives, a row lands in
`SATC leads.xlsx`, and then the trail stops. Everything after that — deciding
whether to take the work, scoping it, pricing it, and producing the engagement
letter, fee estimate and onboarding letter — happens in Arjun's head and in
whatever he types by hand at the time.

Meanwhile six client-facing templates exist in `satc-handoff/04-TEMPLATES/`,
each with a `FIELDS` doc naming every merge field it needs. **Nothing produces
those values.** The templates are ready and unusable, because the record they
merge from does not exist.

The two problems are the same problem. The interview is where the values come
from; the registry is what the values are for. Specified apart, they drift —
and the templates already name the consequence: *"a merge that leaves
`<<ClientLetterName>>` in a letter sent to a client is the one bug that
actually costs you a client."*

## 2. Solution

A **consolidated field registry** — every merge field across all six templates,
classified by where its value comes from — and a **pre-engagement interview**
that produces the fields the registry says a human must supply.

The interview is a Microsoft Form filled during the consultation call, writing
to a second sheet of `SATC leads.xlsx`, so a lead's whole life sits in one
file. Its questions are derived from the registry, not invented: every question
exists because some template needs its answer, and every field a template needs
has a question or a documented other source.

The registry is the durable artifact. The Form is one rendering of it; a later
app is another.

## 3. Goals & Non-Goals

**Goals**
- One registry covering all six templates, each field classified: firm setting,
  client record, engagement record, interview-supplied, or computed.
- An interview question set that fills every interview-supplied field for a
  **tax return preparation** engagement, and no more.
- A machine-readable schema in the repo that the Form is built from.
- A test proving the letter, estimate and onboarding letter can always be
  filled from a completed interview record — and that no field can hold a TIN.
- Silent mismatches between templates surfaced and resolved, not inherited.

**Non-Goals / Out of scope**
- **The merge engine.** No rendering, no PDF generation, no `[[IF]]` evaluation.
  The registry specifies what a future engine consumes; building it is separate.
- **Fee calculation.** The interview *counts* billable items; it does not price
  them. `LineItems` amounts are entered by Arjun.
- **Actual prices.** The adder taxonomy is in scope; dollar figures are not.
- **Bookkeeping, advisory, planning, entity setup, notice resolution.** Deferred
  roadmap, not permanent exclusions. The bookkeeping letter's fields are in the
  registry; the interview does not fill them.
- **Invoice-time fields.** `InvoiceNumber`, `Subtotal`, `AmountDue`, credits and
  variance notes are registry entries only — they arise after the work, not at
  interview.
- **`satc_system` integration.** Its intake module is a post-engagement
  document-request engine, a different animal. No wiring in this build.
- **Automating the interview.** A human runs the call and fills the Form.

## 4. User Stories

1. As the principal, I want the interview to ask only what a template actually
   needs, so that no question is asked for nothing.
2. As the principal, I want the website's answers pre-loaded so I confirm rather
   than re-ask, so that the prospect doesn't repeat themselves.
3. As the principal, I want to name every state and locality during the call, so
   that `StateReturns` and `LocalReturns` are a real scope boundary rather than
   "multi-state".
4. As the principal, I want to count billable items as we talk, so that pricing
   afterwards is arithmetic, not recall.
5. As the principal, I want one materials deadline per return type per season,
   so that the organizer, engagement letter and onboarding letter cannot carry
   different dates.
6. As the principal, I want red flags recorded against the record, so that a
   decision to decline is evidenced.
7. As the principal, I want a hard-no list that ends the conversation, so that I
   don't quote work I cannot legally or competently do.
8. As the principal, I want the record to hold no SSN, ITIN or EIN, so that a
   OneDrive spreadsheet never becomes a PII liability.
9. As the principal, I want one engagement reference that matches across letter,
   estimate, onboarding letter and every later invoice, so that a file drawer
   stays coherent.
10. As a future developer, I want a registry naming every field and its source,
    so that a merge engine can be built without re-reading six templates.
11. As a future developer, I want a test that fails when a template adds a field
    the record cannot supply, so that templates and record cannot drift.
12. As the principal, I want the record to survive being imported elsewhere, so
    that choosing a real system later is not a migration.

## 5. Requirements

1. **[P0]** A registry file enumerating every `<<Field>>`, `[[IF]]` flag and
   `[[EACH]]` list across all six templates, with its source classification and
   which templates use it.
2. **[P0]** A machine-readable interview schema: question id, prompt, type,
   allowed values, which registry field(s) it supplies, and its `showIf`
   condition where conditional.
3. **[P0]** Every field classified `interview` in the registry has a question in
   the schema. Every question maps to at least one registry field or is tagged
   `internal` with a reason.
4. **[P0]** No schema field may be named or typed to hold an SSN, ITIN or EIN.
   A denylist test enforces it.
5. **[P0]** The schema captures `ClientAddress1` and `ClientZip`, which the
   website intake does not collect.
6. **[P0]** `PeriodLabel` is resolved as a per-document value, not one shared
   string (see Implementation Decisions).
7. **[P0]** `MaterialsDeadline` is a firm setting per return type per season,
   stored once and referenced by all three documents that print it.
8. **[P1]** A human-readable build sheet for the Microsoft Form, generated from
   or checked against the schema, so the Form cannot silently diverge.
9. **[P1]** Red-flag questions record a flag value; a defined hard-no subset is
   marked as terminating.
10. **[P1]** The interview pre-loads the website answers for confirmation.
11. **[P2]** A sample completed record, in the same JSON shape as the FIELDS
    docs' example payloads.

## 6. Implementation Decisions

### The registry

A YAML or JSON file under `docs/` or a new `field-registry/` folder. One entry
per field:

```yaml
- field: ClientLetterName
  source: interview            # firm | client | engagement | interview | computed
  templates: [tax-letter, onboarding, organizer, bookkeeping-letter]
  example: "Dan"
  notes: "Salutation only — never the legal name."
```

Field names are **PascalCase and identical across templates**, per the authoring
contract. The registry is the authority on that; a template using a different
name for the same concept is a bug in the template.

### Source classification (from the FIELDS docs)

- **Firm settings** — `PreparerName`, `PreparerTitle`, `PreparerEmail`,
  `PreparerPhone`, `BillingContactName/Email/Phone`, `ReturnInstruction`,
  `PaymentInstruction`, `AckWindow`. Set once; not asked.
- **Client record** — `ClientFullName`, `ClientLetterName`, `ClientAddress1`,
  `ClientCity`, `ClientState`, `ClientZip`, `ClientEmail`, `TaxpayerName`,
  `SpouseName`, `JointReturn`, `PriorFirmName`, `PriorFirm`.
- **Engagement record** — `EngagementRef`, `TaxYear`, `FederalReturns`,
  `StateReturns`, `LocalReturns`, `AdditionalForms`, `MaterialsDeadline`,
  `FirstDeliverableTarget`, `RequestList[]`, `Requested[]`, `LineItems[]`,
  `FeeChange`, `FeeChangeNote`.
- **Bookkeeping-only** — `Cadence`, `FirstPeriod`, `ScopeItems[]`, `CatchUp`,
  `CatchUpPeriods`, `DeliveryTarget`, `AccountingSystem`, `NoticePeriod`,
  `SignerName`, `SignerTitle`. Registered, not asked in this build.
- **Computed / later** — `LetterDate`, `InvoiceNumber`, `InvoiceDate`,
  `Subtotal`, `AmountDue`, `EstimateTotal`, credit fields, `EstimateReference`,
  `EstimateDate`, `VarianceNote`.

### Three mismatches found across the templates — resolve, don't inherit

1. **`PeriodLabel` means two different things.** The estimate and onboarding
   letter use it for the engagement period (`"2026 tax year"`); the invoice uses
   it for the **period billed** (`"March 2027"`). Storing one value and sharing
   it would print the wrong thing on one of them. **Decision:** the registry
   marks `PeriodLabel` as *derived per document*, with the derivation stated per
   template. It is not a stored record field.

2. **`EngagementRef` and the lead number use different formats.** The templates
   specify `2027-0114`; the `SATC leads.xlsx` Lead Number column generates
   `2026 - 0001`. `EngagementRef` must be byte-identical across letter,
   estimate, onboarding letter and every invoice. **Decision:** the template
   format wins — `YYYY-NNNN`, no spaces, four digits. The lead number formula
   changes to match, and a lead's number becomes its `EngagementRef` on
   conversion, so there is one identifier for a client's whole life.

3. **`MaterialsDeadline` appears in three documents**, and the organizer's
   FIELDS doc calls a mismatch *"this template's most likely bug."*
   **Decision:** stored once as a firm setting keyed by return type and season;
   all three read that value. Never entered per client.

### Interview structure

Ordered so an early answer closes later branches, the way the website intake
works (`website/intake-config.js` is the reference implementation for the
`showIf` pattern — a single predicate deciding both whether a question renders
and whether its answer may survive).

Sections, in order:

1. **Confirm identity** — legal name(s), salutation name, full address, email,
   phone. Pre-loaded from the lead row; the address is new.
2. **Filing status** — joint or single; spouse name if joint. Sets
   `JointReturn`.
3. **Return composition** — which federal forms and schedules; which states and
   the basis for each (resident, part-year, non-resident); which localities;
   additional forms. Produces `FederalReturns`, `StateReturns`, `LocalReturns`,
   `AdditionalForms` as prose strings assembled from structured answers.
4. **Billable counts** — per item where countable (rentals, states, localities,
   K-1s, entities); banded where not (brokerage activity, cleanup, document
   volume). Produces the inputs to `LineItems`, not the amounts.
5. **Prior year and predecessor** — prior firm, prior-year return availability,
   unfiled years. Sets `PriorFirm`, `PriorFirmName`, and feeds `RequestList`.
6. **Red flags** — recorded; a hard-no subset terminates.
7. **Internal** — decision, notes. Tagged `internal`; supplies no template.

### Assembling the prose fields

`FederalReturns`, `StateReturns`, `LocalReturns` and `AdditionalForms` print as
sentences but must come from structured answers, so the count that drives the
fee and the words that print are the same data. Assembly rules live with the
schema. `LocalReturns` and `AdditionalForms` emit the literal string `None` when
empty — never blank; the FIELDS docs are explicit that blank and `None` are
different statements where foreign reporting is in scope.

### PII boundary

The record holds legal name, address, email and phone. It holds **no SSN, ITIN
or EIN**, no date of birth, no bank details, and no uploaded documents. This is
the same boundary the public intake already respects, extended one step: the
interview may know *that* a client has an EIN, never the value.

Identifiers belong in Drake and in `satc_system`'s encrypted vault, per
`CLAUDE.md`. `SATC leads.xlsx` lives in OneDrive for Business and is not an
appropriate store for them.

## 7. Testing Decisions

- **Seam:** a pytest suite beside the registry that parses the six template HTML
  files for `<<Field>>`, `[[IF …]]` and `[[EACH …]]` tokens and reconciles them
  against the registry and the interview schema. Prior art:
  `website/intake.spec.py` tests the site's intake at its highest seam by
  driving the real artifact rather than its internals; `satc_system` already
  runs pytest.

- **What a good test proves:**
  1. **Every token in every template appears in the registry.** A template
     gaining a field fails the build rather than failing at a client.
  2. **Every registry field classified `interview` has a question**, and every
     question maps to a field or is tagged `internal`. Catches drift in both
     directions.
  3. **A sample completed record fills the tax letter, estimate and onboarding
     letter with no token left unresolved** — the failure the templates
     themselves call the one that costs a client.
  4. **No schema field can hold a TIN.** Denylist on names and patterns
     (`ssn`, `itin`, `ein`, `tin`, `taxid`) — a guard, not a convention.
  5. **Field names are consistent across templates.** The same concept under two
     names fails.

> **PII handling:** no test fixture may contain a real SSN, ITIN, EIN, or a real
> client's name and address. Sample records use obviously fictional data, in the
> style the FIELDS docs already use (`Daniel Reyes`, `418 Rockwell Street`).
> This matches the bar in `CLAUDE.md`: only masked or fictional values in
> artifacts, never real taxpayer PII.

## 8. Success Metrics

- All six templates reconcile against the registry with zero unaccounted tokens.
- A completed sample record fills the three opening-package documents with no
  unresolved `<<` or `[[`.
- The interview asks **no question that no template consumes**, and leaves **no
  interview-sourced field unasked**.
- Arjun can run a real consultation against the Form and produce a filled record
  without a follow-up email to the prospect.

## 9. Milestones / Rollout

- **M1 (MVP):** the registry + the interview schema + the reconciliation tests.
  Documents still filled by hand from the record.
- **M2:** the Microsoft Form built from the schema, writing to the workbook.
- **M3:** fee amounts attached to the adder taxonomy so `LineItems` amounts
  stop being typed.
- **M4:** the merge engine — out of scope here, unblocked by the registry.

## 10. Risks & Open Questions

- **Risk:** the Form drifts from the schema, since Microsoft Forms cannot be
  generated programmatically. Mitigated by requirement 8 — a generated build
  sheet — but it stays a manual step and a real failure mode.
- **Risk:** the interview is designed against six templates, four more are
  planned (delivery letter, extension notice, business return letter,
  disengagement). New templates may need fields no question asks. The
  reconciliation test turns that into a build failure rather than a surprise.
- **Risk:** prose assembly for `FederalReturns` and friends is where a scope
  boundary is actually written. A clumsy string is a legal document reading
  badly.

- **Open question (needs your decision):** the firm's legal name has three
  variants across existing documents and only one is on the Ohio filing. Every
  template hardcodes it in the footer. **Only Arjun can settle this**, and it
  blocks nothing in this build but blocks shipping any template.
- **Open question (needs your decision):** the fixed materials deadlines per
  return type — the actual dates for the coming season.
- **Open question (needs your decision):** the contents of the hard-no list.
- **Open question (needs your decision):** whether an Ohio RITA filing counts as
  one locality or several, for both `LocalReturns` prose and the billable count.
  Deferred while prices are deferred.

## 11. Done Criteria

- [ ] Registry covers all six templates; every token classified
- [ ] Interview schema exists, machine-readable, with `showIf` conditions
- [ ] Reconciliation tests pass in both directions
- [ ] TIN denylist test passes
- [ ] Sample record fills the three opening-package documents with zero
      unresolved tokens
- [ ] The three template mismatches (`PeriodLabel`, `EngagementRef`,
      `MaterialsDeadline`) are resolved in the registry, not left as notes
- [ ] Form build sheet generated
- [ ] `docs/` updated; `PLAN.md` roadmap entries added
- [ ] Verified by running a real consultation against the Form, not just tests
