# Invoice — required variables

Companion to `SATC Invoice.html`. The same table renders on screen below the invoice itself (`@media print` hidden, so it never reaches a client).

Shares the fee estimate's ledger vocabulary on purpose: a client who saw the estimate should recognise the invoice at a glance and be able to compare it line for line.

Clauses in the engagement letter are referenced **by name** — the fees clause is section 06 in the tax letter and 05 in the bookkeeping letter, so a number would be wrong half the time.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block — **or an inline run of text** |
| `[[EACH List]]` … `[[END EACH]]` | Repeats the rows between them, once per item |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

**Fail the render on any unresolved `<<` or `[[`.**

---

## Fields

### Shared with the engagement letter and estimate (9 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. **One engagement, many invoices** — this repeats across them; the invoice number does not. |
| `<<PeriodLabel>>` | Yes | March 2027 | Same field as the estimate. For recurring bookkeeping this is the **period billed**, not the engagement span. Appears twice. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

### Specific to the invoice (14 fields + a list + 2 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<InvoiceNumber>>` | Yes | INV-2027-0361 | **Sequential, never reused, never reissued under the same number.** Appears three times. A correction gets a new number plus a credit line against the old one. |
| `<<InvoiceDate>>` | Yes | April 12, 2027 | The date the thirty-day clock in the terms runs from |
| `[[EACH LineItems]]` | List | one or more | Three sub-fields — **identical shape to the fee estimate's**, so one formatter serves both |
| `<<Item.Service>>` | Yes | Federal Form 1040 | The line as a client reads it |
| `<<Item.Detail>>` | Yes | With Schedules A, C, and SE | Empty string when there is nothing to add — never "None" |
| `<<Item.Amount>>` | Yes | $450 | Pre-formatted, including the `$` |
| `<<Subtotal>>` | Yes | $785 | **Computed.** Sum of the line items. |
| `<<AmountDue>>` | Yes | $635 | **Computed:** subtotal plus credits (credits negative). Appears twice — ledger and due box — from one value. |
| `<<CreditLabel>>` | If flag | Retainer applied | |
| `<<CreditDetail>>` | If flag | Received February 3, 2027 | |
| `<<CreditAmount>>` | If flag | −$150 | **A real minus sign (−), not a hyphen.** Never parentheses on a client-facing document. |
| `[[IF CreditsApplied]]` | Flag | Boolean | Drops the credit row so a clean invoice has no empty line |
| `<<PaymentInstruction>>` | Yes | Pay by card or bank transfer through the link in the delivery email, or by cheque to the address at right. | **One sentence, from firm settings, not per client.** Changes in one place when the processor changes. |
| `<<BillingContactName>>` + `<<BillingContactEmail>>` | Yes | Arjun Sethuraman · billing@satcllp.com · 307-941-0508 | Three fields. Separate from the preparer on purpose — a billing question shouldn't have to find the preparer. |
| `<<EstimateTotal>>` | If flag | $785 | Pulled from the estimate record, not retyped |
| `<<EstimateDate>>` | If flag | February 3, 2027 | |
| `<<PaymentUrl>>` | Optional | https://square.link/u/xxxxxxxx | The link the client pays at. **Issued per invoice and never for an estimate** — a quote is what the work will cost and is not yet owed, and this engine can re-quote, so the figure moves. Created by `payments.py` from `registry/payments.yaml`; the whole block drops when there is none, so an invoice raised before this existed still renders. |
| `<<VarianceNote>>` | If flag | The difference is the additional state return added at your request on March 8. | **If the invoice exceeds the estimate this is not optional.** An unexplained overage is the most common billing dispute there is. |
| `[[IF EstimateReference]]` | Flag | Boolean | Off for recurring bookkeeping invoices, where restating the estimate monthly is noise |

**Total: 31 fields + 1 repeating list of 3 + 2 flags.**

Not variables: the due-on-presentation terms, the interest language, and the three notes.

---

## Arithmetic is the software's job

Never let a human type `Subtotal` or `AmountDue`. Sum the line items, apply the credit, format currency in **one place** and pass strings through.

A client who finds an arithmetic error on an accountant's invoice has learned something about the firm that no amount of good work undoes.

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
  "InvoiceNumber": "INV-2027-0361",
  "InvoiceDate": "April 12, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "LineItems": [
    { "Service": "Federal Form 1040", "Detail": "With Schedules A, C, and SE", "Amount": "$450" },
    { "Service": "Ohio IT 1040", "Detail": "Resident return", "Amount": "$185" },
    { "Service": "Solon municipal return", "Detail": "", "Amount": "$95" },
    { "Service": "Quarterly estimates for the following year", "Detail": "Calculated in the same pass", "Amount": "$55" }
  ],
  "Subtotal": "$785",
  "CreditsApplied": true,
  "CreditLabel": "Retainer applied",
  "CreditDetail": "Received February 3, 2027",
  "CreditAmount": "−$150",
  "AmountDue": "$635",
  "PaymentInstruction": "Pay by card or bank transfer through the link in the delivery email, or by cheque to the address at right.",
  "BillingContactName": "Arjun Sethuraman",
  "BillingContactEmail": "billing@satcllp.com",
  "EstimateReference": true,
  "EstimateTotal": "$785",
  "EstimateDate": "February 3, 2027",
  "VarianceNote": "No change from the estimate.",
  "FirmName": "SAT-C LLP",
  "FirmLegalName": "Sethuraman Accounting, Tax, and Consulting LLP",
  "FirmAddress1": "6544 Copley Avenue",
  "FirmCity": "Solon",
  "FirmState": "OH",
  "FirmZip": "44139",
  "FirmWebsite": "satcllp.com",
  "FirmJurisdiction": "Ohio",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner"
}
```

---

## Deliberately not here

1. **No hours, no rates.** Consistent with the estimate — the line items are the answer. A rate card invites the client to audit your time.
2. **No "thank you for your business".** The letter and the delivery email carry the warmth; an invoice should be easy to read and easy to pay.
3. **No aging table.** A first invoice showing a 30/60/90 grid reads as an accusation. Overdue balances belong on a separate statement document.
4. **No restated scope or terms.** Both live in the engagement letter, which this points at by name.

## Notes for the software

1. The due box repeats `<<AmountDue>>` from the ledger deliberately — a client who skims sees the figure without reading the table. **Two renders of one value, never two values.**
2. `[[IF EstimateReference]]` wraps text **inside** a list item. The marker stripper must handle inline conditionals as well as block ones.
3. Strip the `.f` class, the `.cond` markers, and the `tr.mark` marker rows on the client-facing render.
4. Name the output `SAT-C Invoice INV-2027-0361 — Reyes.pdf`. The number goes in the filename; a client with three invoices needs to tell them apart.
