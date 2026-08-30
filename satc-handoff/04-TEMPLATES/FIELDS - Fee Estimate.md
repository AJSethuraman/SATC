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
| `<<LetterDate>>` | Yes | February 3, 2027 | **The engagement letter's date**, in the one sentence that names it. Never moves — the client has signed that letter. |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. Byte-identical to the letter's, or the pair comes apart in a file drawer. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

### The engagement's scope, repeated from the letter (4 fields + a flag)

The same four lines as the engagement letter's **What we will prepare**
section, from the same four fields on the same record. The firm's ask of
26 August 2026: *"either it needs to list what we are doing in one place, or
needs to be comparable in both."* This is the second. A client holding two
sheets can put them beside each other, and the two cannot disagree because
neither is typed.

| Field | Required | Example | Notes |
|---|---|---|---|
| `[[IF ReturnScope]]` | Flag | Boolean | Derived in `interview.compose` from the federal form; never asked. Drops the whole block. |
| `<<FederalReturns>>` | If flag | Form 1040 with Schedules A, C, E, and SE | Byte-identical to the letter's |
| `<<StateReturns>>` | If flag | Ohio — resident | |
| `<<LocalReturns>>` | If flag | Solon municipal | "None" when there are none, never blank |
| `<<AdditionalForms>>` | If flag | Two K-1s as reported | "None" when there are none, never blank |

**A bookkeeping estimate has no scope block.** Its engagement letter carries
`ScopeItems`, a list, and there is no bookkeeping interview yet — so the flag
is off and the block drops, rather than printing four blanks. Give it its own
branch when that interview is built.

### Specific to the estimate (3 fields + a list of 4)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<EstimateDate>>` | Yes | March 10, 2027 | **This estimate's own date**, at the head of the sheet. Set to `LetterDate` when the engagement is created, and moved by a re-quote. See below. |
| `[[EACH LineItems]]` | List | one or more | Three sub-fields per item |
| `<<Item.Service>>` | Yes | Federal Form 1040 | The line as a client reads it |
| `<<Item.Detail>>` | Yes | With Schedules A, C, and SE | Emit an empty string when there is nothing to add — never the word "None" |
| `<<Item.Includes>>` | Yes | Includes: Your federal 1040, your first state return and your first local return; … | What a package covers, on its own line. **The estimate's only** — an invoice bills work that is done and does not restate it. Empty string on a row with nothing to list; a row that omits the key altogether fails the render. |
| `<<Item.Amount>>` | Yes | $450 | Pre-formatted by the software, including the `$` |
| `<<PeriodLabel>>` | Yes | 2026 tax year | **Self-describing** — the label on the document is only "Period". Use "2026 tax year" for a tax engagement, "Monthly, from July 2027" for bookkeeping. Appears twice. Derive it from whichever engagement this accompanies; neither letter carries this field. |
| `<<EstimateTotal>>` | Yes | $785 | **Computed, not typed.** Sum the line items in code so the arithmetic cannot be wrong on a client-facing document. |

**Total: 24 fields + 1 repeating list of 3.**

Not variables: the four assumption notes, and the pointers to the letter's scope and fees clauses.

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
  "EstimateDate": "February 3, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
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

## An engagement can be quoted again

`<<EstimateDate>>` exists because of this, and it is the one field on the sheet
that is not shared with the letter.

The work changes mid-season — a second rental in April, a K-1 that arrives, a
Schedule C that turns out to be a real business. `client-documents/requote.py`
changes the ANSWERS and prices them again through the same engine that priced
them the first time; nobody types a figure. What comes out is a second estimate,
and it needs its own date to be told from the first: two sheets in a drawer with
different totals under the same date is a question nobody can answer next
February.

**The engagement letter's date does not move**, because the client has signed
it. So the two dates on this sheet mean two different things, and only one of
them changes:

| | Moves on a re-quote? | |
|---|---|---|
| `<<EstimateDate>>` | **Yes** | The date at the head — when this quote was given |
| `<<LetterDate>>` | No | The date in the intro sentence — the letter it accompanies |

The invoice cites `<<EstimateDate>>` too, so a bill raised after a re-quote
names the estimate it is actually billing against.

**When the scope moves, the letter is out of date as well.** Adding a state
changes `<<StateReturns>>` on both this sheet and the letter, which is the whole
point of them being the same four fields — so the re-quote says so, and the pack
is rebuilt rather than the estimate sent on its own.

---

## Deliberately not here

1. **No expiry date.** An estimate that goes stale invites a client to ask for it again at the old number; without a date on it, the conversation is simply a new estimate.
2. **No signature line.** The engagement letter is the signed instrument. Two signature blocks in one envelope means one gets left blank.
3. **No restated scope.** The estimate points at the letter's scope section rather than repeating it, so there is exactly one description of the work.
4. **No hourly rates.** The line items are the answer.
5. **No payment link.** The firm, 30 August 2026: *"Quotes get no link. Only the
   invoice. Obviously."* An estimate is what the work will cost and is not yet
   owed — and this engine re-quotes, so a link on one would collect a figure
   that had since moved. `<<PaymentUrl>>` belongs to the invoice alone.

   **What stops it is this paragraph, and only this paragraph.** Do not assume
   the software will catch you: `cmd_render` merges the bill into the shared
   record whenever the invoice is among `--docs` (`cli.py:1752`), so rendering
   the estimate alongside an invoice gives it a record already carrying
   `PaymentUrl`. Add the token here and it will render, quietly, on the next
   combined run. There is no test guarding this and there should not be — a
   test does not stop somebody editing this template on purpose, it only makes
   them delete a test on the way. See `docs/SOFTWARE-TENETS.md` S30.

## Figures

Amounts use tabular numerals, right-aligned, total ruled above and double-ruled below — the house convention from `SATC Figures and Tables.html`. Format money in **one place** in the software and pass strings through; never let two templates format currency differently.
