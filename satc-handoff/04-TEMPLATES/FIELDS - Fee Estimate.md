# Fee estimate — required variables

Companion to `SATC Fee Estimate.html`. The same table renders on screen below the estimate itself (`@media print` hidden, so it never reaches a client).

Referenced by the **Fees and billing** section of either engagement letter — tax preparation or bookkeeping — which points at this document instead of restating a fee. The two are generated together and travel together.

Clauses are referenced **by name**, never by number: the fees clause is section 06 in the tax letter and section 05 in the bookkeeping letter, so a number would be wrong half the time.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[EACH List]]` … `[[END EACH]]` | Repeats the rows between them, once per item |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

**Fail the render on any unresolved `<<` or `[[`.**

---

## Fields

### Shared with either engagement letter (9 fields)

Same records, same values. Generate the pair in one call.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | February 3, 2027 | **The letter's date, not today's.** Appears twice. |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. Byte-identical to the letter's, or the pair comes apart in a file drawer. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

### Specific to the estimate (2 fields + a list)

| Field | Required | Example | Notes |
|---|---|---|---|
| `[[EACH LineItems]]` | List | one or more | Three sub-fields per item |
| `<<Item.Service>>` | Yes | Federal Form 1040 | The line as a client reads it |
| `<<Item.Detail>>` | Yes | With Schedules A, C, and SE | Emit an empty string when there is nothing to add — never the word "None" |
| `<<Item.Amount>>` | Yes | $450 | Pre-formatted by the software, including the `$` |
| `<<PeriodLabel>>` | Yes | 2026 tax year | **Self-describing** — the label on the document is only "Period". Use "2026 tax year" for a tax engagement, "Monthly, from July 2027" for bookkeeping. Appears twice. Derive it from whichever engagement this accompanies; neither letter carries this field. |
| `<<EstimateTotal>>` | Yes | $785 | **Computed, not typed.** Sum the line items in code so the arithmetic cannot be wrong on a client-facing document. |

**Total: 11 fields + 1 repeating list of 3.**

Not variables: firm name, address, phone, website, the Ohio LLP footer, the four assumption notes, and the pointers to the letter's scope and fees clauses.

---

## Example payload

```json
{
  "LetterDate": "February 3, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "LineItems": [
    { "Service": "Federal Form 1040", "Detail": "With Schedules A, C, and SE", "Amount": "$450" },
    { "Service": "Ohio IT 1040", "Detail": "Resident return", "Amount": "$185" },
    { "Service": "Solon municipal return", "Detail": "", "Amount": "$95" },
    { "Service": "Quarterly estimates for the following year", "Detail": "Calculated in the same pass", "Amount": "$55" }
  ],
  "EstimateTotal": "$785"
}
```

---

## Deliberately not here

1. **No expiry date.** An estimate that goes stale invites a client to ask for it again at the old number; without a date on it, the conversation is simply a new estimate.
2. **No signature line.** The engagement letter is the signed instrument. Two signature blocks in one envelope means one gets left blank.
3. **No restated scope.** The estimate points at the letter's scope section rather than repeating it, so there is exactly one description of the work.
4. **No hourly rates.** The line items are the answer.

## Figures

Amounts use tabular numerals, right-aligned, total ruled above and double-ruled below — the house convention from `SATC Figures and Tables.html`. Format money in **one place** in the software and pass strings through; never let two templates format currency differently.
