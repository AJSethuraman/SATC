# Business return engagement letter — required variables

Companion to `SATC Engagement Letter - Business Return.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

The entity twin of `SATC Engagement Letter - Tax Preparation.html`, for a 1120-S or 1065 filer. Everything that is the same is **worded the same, on purpose** — a client who has both letters should be able to read the second one quickly and find the differences where they actually are.

What differs is **section 02**, which exists because the Schedule K-1 is the joint the whole engagement turns on: the entity return produces it, and no owner's personal return can be *prepared* — not merely filed — until it exists.

Clauses are referenced **by name**, never by number. The fees clause is 06 in the individual letter and 07 here.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block |

No repeating lists in this template.

**Fail the render on any unresolved `<<` or `[[`.**

---

## Fields

### Shared with the individual tax letter (16 fields)

Same names, same records, same values where the client is the same. This is the rule the whole set depends on.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | January 20, 2027 | Identical across the letter, the estimate and the onboarding letter it ships with. |
| `<<EngagementRef>>` | Yes | 2027-0117 | The join key. **The entity gets its own**, separate from any owner's. |
| `<<PeriodLabel>>` | Yes | 2026 tax year | The self-describing period field. **Not `TaxYear`** — §4 of the authoring contract says that name must never come back. Appears twice. |
| `<<ClientFullName>>` | Yes | Larchmere Holdings LLC | **The entity's exact registered name**, not a trading name. Appears three times: recipient block, opening sentence, signature label. |
| `<<ClientAddress1>>` | Yes | 1240 Larchmere Boulevard | The entity's address, which is not always an owner's. |
| `<<ClientCity>>` | Yes | Cleveland | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44120 | |
| `<<FederalReturns>>` | Yes | Form 1120-S and Schedules K-1 | |
| `<<StateReturns>>` | Yes | Ohio IT 4738 | **Name every state.** This is the scope boundary. |
| `<<LocalReturns>>` | Yes | City of Cleveland net profit return | |
| `<<AdditionalForms>>` | Yes | None | **Emit the literal "None" when empty**, never a blank. With foreign reporting in scope, blank and "None" are different statements. |
| `<<MaterialsDeadline>>` | Yes | February 15, 2027 | **The entity value, which is earlier than the individual one.** Appears twice — sections 02 and 05. |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields. |

### Specific to this letter (5 fields + 3 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<EntityType>>` | Yes | an Ohio limited liability company taxed as an S corporation | **A phrase, not a code**, written to drop into the opening sentence after a comma. It is the letter's statement of what it believes the entity is, put where the client can correct it. |
| `<<ScheduleK1Target>>` | Yes | March 10, 2027 | When the K-1s are delivered. **A real date** — every owner's preparer schedules around it. |
| `<<OwnerCount>>` | Yes | 3 | From `count_owners`, now **required** for a 1120-S or 1065. Section 01 is the scope statement, and how many K-1s the engagement produces is part of that scope. Same number the estimate prices owner K-1s from, so the two cannot disagree. **Gated on `EntityIssuesK1s`** — a C corporation issues none. |
| `<<SignerName>>` + `<<SignerTitle>>` | Yes | Daniel Reyes · Managing Member | Two fields, **the same pair the bookkeeping letter uses**. An entity signs through a person, and that person must be able to bind it. |
| `[[IF OwnerReturnsPrepared]]` | Flag | Boolean | The firm also prepares the owners' personal returns. |
| `[[IF OwnerReturnsElsewhere]]` | Flag | Boolean | **The exact inverse.** |
| `[[IF EntityIssuesK1s]]` | Yes | Flag | Boolean, derived from the federal form — true for a 1120-S or a 1065, false for a 1120. **A C corporation issues no K-1s.** Gates the K-1 scope line in section 01. |
| `[[IF SCorpElection]]` | Flag | Boolean | Adds the officer-compensation scope exclusion in section 03, which is meaningless for a partnership. |

**Total: 28 fields + 4 flags. No repeating lists.**

Sixteen of the twenty-one are the same fields, from the same records, as the individual tax letter.

Not variables: the whole of the "what this engagement is not" language, the responsibilities list, the extension callout, the unclear-law clause, the records and confidentiality clauses, and the execution note.

### On `ScheduleK1Target` and the name

PascalCase forbids the hyphen in "K-1", so the field is `ScheduleK1Target` — digits are allowed, hyphens are not. It is the only field in the set whose name is a compromise with the naming rule rather than a straight reading of the thing it names, which is why it is called out here.

---

## Section numbering under a dropped block

**Nothing needs renumbering.** All three conditionals sit *inside* numbered sections.

That is deliberate and it is not a coincidence: **this letter is signed.** A signed document with a gap in its clause numbers invites exactly the question you least want asked about it two years later. The individual letter can renumber after a merge; a countersigned one should not have to.

### Section 02 must never be silent

`OwnerReturnsPrepared` and `OwnerReturnsElsewhere` are inverses and exactly one must render. The single question this letter exists to answer is *who turns the K-1 into a personal return, and by when*. An entity letter that leaves it unstated produces the April phone call about a K-1 nobody was expecting — from an owner who is not your client, about a deadline you did not set.

### The firm itself (8 fields)

Masthead, footer, and the sign-off's "on behalf of" line. Set in
`client-documents/registry/firm-settings.yaml` under `firm:`, and merged like
any other field — until 26 August 2026 they were typed into all ten templates,
byte for byte, which is what made a change of address a ten-file edit.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<FirmName>>` | Yes | SAT-C LLP | The short form a client reads. Masthead and sign-off. |
| `<<FirmLegalName>>` | Yes | Sethuraman Accounting, Tax, and Consulting LLP | The registered name. Footer only. |
| `<<FirmAddress1>>` | Yes | 6544 Copley Avenue | Masthead and footer |
| `<<FirmCity>>` + `<<FirmState>>` + `<<FirmZip>>` | Yes | Solon · OH · 44139 | Three fields. Masthead and footer. |
| `<<FirmWebsite>>` | Yes | satcllp.com | No protocol, no `www.` |
| `<<FirmJurisdiction>>` | Yes | Ohio | The state of registration, named in the footer's partnership sentence |

The logo lockup is **not** a field. The wordmark is artwork: a firm that
changes its name gets a new mark drawn, not a string substituted.

---

## Example payload

An S corporation whose owners' personal returns the firm also prepares. The other branch is the same payload with `OwnerReturnsPrepared` false and `OwnerReturnsElsewhere` true; `SCorpElection` is false for a 1065 filer.

```json
{
  "LetterDate": "January 20, 2027",
  "EngagementRef": "2027-0117",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Larchmere Holdings LLC",
  "ClientAddress1": "1240 Larchmere Boulevard",
  "ClientCity": "Cleveland",
  "ClientState": "OH",
  "ClientZip": "44120",
  "EntityType": "an Ohio limited liability company taxed as an S corporation",
  "FederalReturns": "Form 1120-S and Schedules K-1 for each owner",
  "StateReturns": "Ohio IT 4738",
  "LocalReturns": "City of Cleveland net profit return",
  "AdditionalForms": "None",
  "MaterialsDeadline": "February 15, 2027",
  "ScheduleK1Target": "March 10, 2027",
  "OwnerCount": 3,
  "SignerName": "Daniel Reyes",
  "SignerTitle": "Managing Member",
  "FirmName": "SAT-C LLP",
  "FirmLegalName": "Sethuraman Accounting, Tax, and Consulting LLP",
  "FirmAddress1": "6544 Copley Avenue",
  "FirmCity": "Solon",
  "FirmState": "OH",
  "FirmZip": "44139",
  "FirmWebsite": "satcllp.com",
  "FirmJurisdiction": "Ohio",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "OwnerReturnsPrepared": true,
  "OwnerReturnsElsewhere": false,
  "SCorpElection": true
}
```

---

## Open item

**One `[CONFIRM]` remains, in section 03**, on officer compensation under an S election. The scope exclusion itself is written — the firm reports the compensation the entity actually paid, and setting or reviewing it is out of scope unless section 01 lists it. Whether the firm wants to say anything *further* is a substantive tax and risk decision, and inventing it would be worse than leaving the blank.

**The template will not ship while the marker is there.** `merge.render()` treats a surviving `[CONFIRM:` exactly like an unresolved field and raises rather than producing the document.

---

## Deliberately not here

1. **No owner signature block.** One signature binds the entity. Collecting owner signatures on an entity letter implies each owner is a client of *this* engagement, which is the opposite of what section 02 says and the opposite of what section 09 says about who may see the return.
2. **No K-1 sent straight to owners.** Section 02 says the K-1 goes to the entity, and that the entity distributes it. A firm that mails K-1s to owners on its own initiative has made a disclosure decision that was not its to make.
3. **No statutory dates in the prose.** Every date is a merge field. A hardcoded March 15 is wrong for a fiscal-year filer, and wrong again whenever Congress moves something.
4. **No reasonable-compensation figure, and no method for reaching one.** A number in an engagement letter reads as advice, and this is not the document where that advice belongs.
5. **No fee.** The estimate owns it; this letter points at it by name.
6. **No entity-formation or election advice.** Whether the entity *should* be taxed the way it is has a different risk profile and needs a different engagement.
7. **No per-owner penalty figure.** Section 05 says the late-filing penalty is commonly charged per owner per month, which is the shape of the risk and the reason it matters more here than on a 1040. It does not name an amount, because amounts change.

## Notes for the software

1. **`OwnerReturnsPrepared` and `OwnerReturnsElsewhere` must be derived from one stored value.** Two independent booleans can both be false, leaving section 02 silent on the single question this letter exists to answer.
2. **`MaterialsDeadline` is keyed by return type**, and the entity value is earlier than the individual one. `registry/fields.yaml` already calls a `MaterialsDeadline` mismatch the organizer's most likely bug. An entity letter carrying the 1040 date is the same bug, one season earlier, with every owner downstream of it.
3. **`ScheduleK1Target` is a promise other people schedule around.** If the software can only produce it as a guess, it should refuse rather than guess.
4. **The entity's `EngagementRef` is its own.** Do not reuse an owner's. One engagement, one ref — an entity with three owners must not inherit whichever owner happened to be set up first.
5. `EntityType` should be generated from the entity record rather than typed, so that the letter and the return cannot disagree about what the entity is.
6. Strip the `.f` class and the `.cond` markers on the client-facing render.
7. Name the output for a human: `SAT-C Business Engagement Letter — Larchmere Holdings — 2026.pdf`.
