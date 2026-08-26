# Organizer cover letter — required variables

Companion to `SATC Organizer Cover Letter.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

Sent in January with the tax organizer, ahead of the engagement letter and estimate for the same year. **Highest-volume document in the set** — it goes to every returning client — so it is the one most likely to ship a merge bug at scale.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block |
| `[[EACH List]]` … `[[END EACH]]` | Repeats what is between them, once per item |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

**Fail the render on any unresolved `<<` or `[[`.**

---

## Fields

### Shared with the tax engagement letter (12 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | January 12, 2027 | |
| `<<EngagementRef>>` | Yes | 2027-0114 | **The ref for the year being organised** — the letter and estimate reuse it when they follow |
| `<<TaxYear>>` | Yes | 2026 | Appears three times |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<MaterialsDeadline>>` | Yes | March 15, 2027 | **The same date the engagement letter will carry.** Two different dates across the two documents is this template's most likely bug. |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

### Specific to this letter (1 field + a list + a flag)

| Field | Required | Example | Notes |
|---|---|---|---|
| `[[EACH Requested]]` | List | one or more | Two sub-fields each |
| `<<Item.Category>>` | Yes | W-2s | |
| `<<Item.Detail>>` | Yes | Both employers, including the one you left in March | |
| `[[IF FeeChange]]` | Flag | true / false | Drops the fee paragraph entirely when false |
| `<<FeeChangeNote>>` | If flagged | Our fees for individual returns are increasing modestly this year. | One or two sentences. **Say it in January or not at all.** |

**Total: 13 fields + 1 repeating list of 2 + 1 conditional flag.**

Not variables: firm name, address, phone, website, the Ohio LLP footer, the Encyro upload instruction, and the five items in section 02.

---

## Example payload

```json
{
  "LetterDate": "January 12, 2027",
  "EngagementRef": "2027-0114",
  "TaxYear": "2026",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "MaterialsDeadline": "March 15, 2027",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "Requested": [
    { "Category": "W-2s", "Detail": "Both employers, including the one you left in March" },
    { "Category": "1099s and brokerage statements", "Detail": "Fidelity consolidated 1099, plus anything new" },
    { "Category": "Rental income and expenses", "Detail": "The Rockwell Street duplex — income, repairs, mortgage interest" },
    { "Category": "Charitable contributions", "Detail": "Written acknowledgement for anything over $250" }
  ],
  "FeeChange": false
}
```

---

## How this one earns its keep

1. **The requested list is per-client, not generic.** Generating it from last year's return — naming their employers, their brokerage, their rental — is the difference between an organizer that comes back in two weeks and one that comes back in April.
2. **Section 02 asks the questions clients answer wrong by omission.** Digital assets, foreign accounts, a new K-1. Asking in January costs nothing; finding out in April costs a filing.
3. **The deadline appears once, in a callout.** It is the only thing on the page that must survive a skim.
4. **The fee-change paragraph is conditional and belongs here.** January is when a client can absorb a fee change without resentment.

## What this is not

This is the **cover**. The organizer itself — the questionnaire and prior-year figures a client fills in — is a separate document, and the one piece in this set worth generating from tax software rather than designing by hand.
