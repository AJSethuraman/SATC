# Tax return delivery letter — required variables

Companion to `SATC Tax Return Delivery Letter.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

The last document of a tax engagement, sent with the finished returns. It tells a client what to sign, what to pay, what to keep, and that the work is over. It is the only document in the set that closes an engagement rather than opening or billing one.

Clauses in the engagement letter are referenced **by name**, never by number — the responsibility clause is 03 in the individual letter and 04 in the business one.

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

### Shared with the engagement letter (12 fields)

Same records, same values, same engagement. `EngagementRef` is what ties this letter back to the letter, the estimate and every invoice.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | April 2, 2027 | The delivery date. `SignatureDeadline` is measured from it. |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. |
| `<<PeriodLabel>>` | Yes | 2026 tax year | Self-describing; the same field every other document uses. Appears twice — subject line and footer. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields. Name appears twice — the dateline and the sign-off. |

### Specific to this letter (3 fields + 2 lists + 3 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<SignatureDeadline>>` | Yes | April 10, 2027 | **A real date, never "as soon as possible".** A deadline with no date is not one. |
| `<<PreparerEmail>>` | Yes | arjun@satcllp.com | The only way the letter offers to reach us. No phone goes on a client document until the firm has a business line. |
| `[[EACH ReturnsDelivered]]` | List | one or more | Two sub-fields. Every return in the package, in the order they are stacked. |
| `<<Item.Return>>` | Yes | Federal Form 1040 | As the form is named on its own face |
| `<<Item.Detail>>` | Yes | Refund of $1,240, direct deposit to the account ending 4417 | Empty string when there is nothing to add — never "None" |
| `[[EACH ActionList]]` | List | one or more | Two sub-fields. The checklist a client works down. |
| `<<Item.Action>>` | Yes | Pay the Ohio balance due | Imperative. The client is the subject of every one of these. |
| `<<Item.Detail>>` | Yes | $412.00 to Ohio Treasurer of State by April 15, 2027 | Amount, authority, date. **The amount is a pre-formatted string** — see below. |
| `[[IF EFiled]]` | Flag | Boolean | The e-file branch: signing the authorisation, and the confirmation the firm owes. |
| `[[IF PaperFiled]]` | Flag | Boolean | **The exact inverse of `EFiled`.** Puts filing on the client, which is the most important sentence in the letter when it applies. |
| `[[IF EstimatedPayments]]` | Flag | Boolean | Drops the next-year estimates section when there are no vouchers in the package. |

**Total: 20 fields + 2 repeating lists of 2 + 3 flags.**

Not variables: the review-before-you-sign paragraph, the never-send-a-payment-to-us warning, the certified-mail advice, the retention paragraph, and the whole of the "Where this engagement ends" section.

---

## Section numbering under a dropped block

Three conditionals, two of which are numbered sections.

- `EFiled` and `PaperFiled` **both render as 03**, because exactly one of them is ever true.
- `EstimatedPayments` renders as **04** and can drop.

**Renumber sequentially after the merge.** A client must never see 03 followed by 05, and must never see two sections numbered 03.

### The assumption this template makes

**A return package is either e-filed or paper-filed. Never both, never neither.**

That is why `EFiled` and `PaperFiled` share a number, and it is the assumption to check before wiring. A package that mixes the two — a federal e-file alongside a paper municipal return — is not covered, and the honest fix is a third branch rather than rendering both sections.

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

Both flag states are exercised: this one is e-filed with estimates, so `PaperFiled` is false.

```json
{
  "LetterDate": "April 2, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "SignatureDeadline": "April 10, 2027",
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
  "EFiled": true,
  "PaperFiled": false,
  "EstimatedPayments": true,
  "ReturnsDelivered": [
    { "Return": "Federal Form 1040", "Detail": "Refund of $1,240.00, direct deposit to the account ending 4417" },
    { "Return": "Ohio IT 1040", "Detail": "Balance due of $412.00" },
    { "Return": "Ohio SD 100", "Detail": "Solon City School District — no balance and no refund" },
    { "Return": "City of Solon municipal return", "Detail": "Balance due of $86.00" }
  ],
  "ActionList": [
    { "Action": "Sign the federal and Ohio e-file authorisations", "Detail": "Form 8879 and Ohio IT 8879, both spouses, by April 10, 2027" },
    { "Action": "Pay the Ohio balance due", "Detail": "$412.00 to Ohio Treasurer of State by April 15, 2027" },
    { "Action": "Pay the Solon municipal balance due", "Detail": "$86.00 to City of Solon by April 15, 2027" },
    { "Action": "File the first estimated payment for 2027", "Detail": "Voucher enclosed — due April 15, 2027" }
  ]
}
```

The paper-filed variant is the same payload with `"EFiled": false, "PaperFiled": true` and the signing action removed from `ActionList`.

---

## Deliberately not here

1. **No fee, and no amount payable to us.** The invoice owns that. A letter that mixes the tax you owe the government with the fee you owe your accountant makes both harder to read and one of them easier to miss.
2. **No restated scope.** The engagement letter owns it. This letter points at three of its clauses by name and restates none of them.
3. **No signature block.** The thing being signed is the e-file authorisation, which is its own form with its own perjury statement. A signature line here invites a client to sign the wrong piece of paper and think they are done.
4. **No refund-timing promise.** "Refunds usually arrive in three weeks" is the taxing authority's schedule, not the firm's, and the client who waits five will remember who said three.
5. **No congratulations.** A refund is the client's own money coming back. Calling it good news is a habit worth not having.
6. **No record-retention period.** The engagement letter owns the firm's seven years. This letter says only that the firm's retention is not a substitute for the client's own — which is a different statement, and the one clients get wrong.

## Notes for the software

1. **`EFiled` and `PaperFiled` must be derived from one stored value, not stored as two booleans.** Two independent flags can both be false, and a delivery letter with no section 03 tells a client nothing about how their return gets filed. Derive them; do not ask twice.
2. **`ActionList` is built from the returns, not typed.** Each item carries an amount, an authority and a date. Every amount is a pre-formatted string from the one money formatter — this template does no arithmetic, and **a human should never type a tax figure into this letter.** It is the one document where a transcription error looks like advice.
3. `ReturnsDelivered` should be generated from the same list of returns that produced the engagement letter's scope section. If the two disagree, something was prepared that was not engaged for, or engaged for and not prepared — either is worth failing on rather than papering over.
4. The checkboxes in `ActionList` are printed squares, for a client working on paper. **Do not turn them into PDF form fields.**
5. Strip the `.f` class and the `.cond` markers on the client-facing render.
6. Name the output for a human: `SAT-C Return Delivery — Reyes — 2026.pdf`.
