# Onboarding letter — required variables

Companion to `SATC Onboarding Letter.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

The third document in the opening package, sent with the engagement letter and the fee estimate. It is the one the client actually acts on, so it carries the deadline and the checklist and nothing legal.

Clauses in the other documents are referenced **by name**, never by number.

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

### Shared with the engagement letter and estimate (11 fields)

Same records, same values. Generate all three documents in one call.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | February 3, 2027 | The package's date. Identical across all three documents. |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. |
| `<<PeriodLabel>>` | Yes | 2026 tax year | Self-describing; same field the estimate uses. Appears twice. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields. Name appears twice — the dateline and the sign-off. |

### Specific to this letter (7 fields + a list + a flag)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<ClientEmail>>` | Yes | dreyes@example.com | **Printed on purpose** — the upload link and the Encyro signing invitation both go here, and it is the first thing a client asks. |
| `<<MaterialsDeadline>>` | Yes | March 15, 2027 | A real date, never "early March". The tax letter's timing clause carries the same value — set it once. |
| `[[EACH RequestList]]` | List | one or more | Two sub-fields. The point of the letter — **build it from the engagement type, not by hand.** |
| `<<Item.Document>>` | Yes | All W-2 forms | As a client would name it, not as the tax code does |
| `<<Item.Detail>>` | Yes | For both of you, including part-year employment | Empty string when there is nothing to add — never "None" |
| `<<FirstDeliverableTarget>>` | Yes | April 1, 2027 | The promise the client remembers. Date or phrase. |
| `<<PreparerEmail>>` | Yes | arjun@satcllp.com | The only way the letter offers to reach us. No phone goes on a client document until the firm has a business line. |
| `<<PriorFirmName>>` | If flag | Halloran & Reeve CPAs | |
| `[[IF PriorFirm]]` | Flag | Boolean | Drops the previous-accountant section for a client with no predecessor. |

**Total: 23 fields + 1 repeating list of 2 + 1 flag.**

Not variables: the upload and Encyro instructions, and the what-happens-next paragraph.

---

## Section numbering under a dropped block

This is the first template where a conditional removes a **numbered** section. Two options — the software must pick one:

1. **Renumber sequentially after the merge** (preferred). A client should never see 03 followed by 05.
2. Make the numbers static and accept the gap.

Do not leave it to chance. The numbers exist so a client can point at a clause on the phone.

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
  "ClientEmail": "dreyes@example.com",
  "MaterialsDeadline": "March 15, 2027",
  "FirstDeliverableTarget": "April 1, 2027",
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
  "PreparerEmail": "arjun@satcllp.com",
  "PriorFirm": true,
  "PriorFirmName": "Halloran & Reeve CPAs",
  "RequestList": [
    { "Document": "Signed engagement letter", "Detail": "Nothing begins until this is back" },
    { "Document": "All W-2 forms", "Detail": "For both of you, including any part-year employment" },
    { "Document": "All 1099 forms", "Detail": "Interest, dividends, brokerage, contract work, state refunds" },
    { "Document": "Prior year filed return", "Detail": "Federal, state, and local, as filed" },
    { "Document": "Mortgage interest and property tax statements", "Detail": "Form 1098 and the county bill" },
    { "Document": "Charitable contribution acknowledgements", "Detail": "Written acknowledgement required for anything over $250" },
    { "Document": "Digital asset activity", "Detail": "Every exchange, wallet, and transfer — including transfers that were not sales" },
    { "Document": "Foreign account or asset details", "Detail": "Any account, trust, or gift outside the United States, however small" }
  ]
}
```

---

## Deliberately not here

1. **No fee, no scope, no terms.** The engagement letter and the estimate own those. This document is a to-do list with a date on it.
2. **No signature line.** Three signature blocks in one package guarantees one comes back blank.
3. **No "please don't hesitate to contact us".** The questions section asks for the question outright, which is the behaviour you actually want.

## Notes for the software

1. The checkboxes are printed squares, for a client working on paper. **Do not turn them into PDF form fields** — a half-completed form is worse than a list.
2. The `[[EACH RequestList]]` markers sit outside the `<ul>`. Repeat the whole `ul` per item, or move the markers inside and repeat the `li` — either works, but match how the fee estimate's row repeat is wired.
3. `RequestList` should come from a **template per engagement type** with per-client additions, not from free typing. The checklist is where a firm's institutional memory lives.
