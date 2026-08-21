# Extension notice — required variables

Companion to `SATC Extension Notice.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

**The highest-volume document in the set, and the shortest.** Sent the day the extension is filed, not weeks later — a client who first hears about it at the extended deadline has already missed the payment date, which is the one thing an extension does not move.

Clauses in the engagement letter are referenced **by name**, never by number.

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

### Shared with the rest of the engagement (12 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | April 14, 2027 | The day the extension was filed. **Send the letter the same day.** |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key. |
| `<<PeriodLabel>>` | Yes | 2026 tax year | Appears twice — subject line and footer. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientLetterName>>` | Yes | Dan | Salutation only. |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<MaterialsDeadline>>` | Yes | August 15, 2027 | **The extension-season value, not the original season's.** Same field name as the onboarding letter and the organizer; different value at this stage. See the software note. |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields. |

### Specific to this letter (5 fields + 2 lists + 2 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<ExtendedDeadline>>` | Yes | October 15, 2027 | **Appears three times** — opening paragraph, dateline, section 04. Drive all three from one value. |
| `<<PaymentDeadline>>` | Yes | April 15, 2027 | The **original** due date, which the extension did not move. Appears twice. If this ever equals `ExtendedDeadline`, something is wrong. |
| `<<EstimatedPaymentAmount>>` | If flag | $2,150.00 | A pre-formatted string from the one money formatter. **This template does no arithmetic.** |
| `<<PreparerEmail>>` + `<<PreparerPhone>>` | Yes | arjun@satcllp.com · 307-941-0508 | Two fields. |
| `[[EACH ExtendedReturns]]` | List | one or more | Two sub-fields. **Exactly what was filed**, never what is assumed to follow from it. |
| `<<Item.Return>>` | Yes | Federal Form 4868 | The extension form, named as it is filed |
| `<<Item.Detail>>` | Yes | Extends the Form 1040 to October 15, 2027 | Empty string when there is nothing to add — never "None" |
| `[[EACH OutstandingItems]]` | List | one or more | Two sub-fields — **the same shape as the onboarding letter's `RequestList`**, so one formatter serves both. |
| `<<Item.Document>>` | Yes | K-1 from Larchmere Holdings LLC | As a client would name it |
| `<<Item.Detail>>` | Yes | Expected from the partnership by September 1 | |
| `[[IF PaymentEnclosed]]` | Flag | Boolean | An extension payment was estimated and is due. |
| `[[IF NoPaymentRequired]]` | Flag | Boolean | **The exact inverse of `PaymentEnclosed`.** |

**Total: 17 fields + 2 repeating lists of 2 + 2 flags.**

Not variables: firm name, address, phone, website, the Ohio LLP footer, the more-time-to-file-not-to-pay callout, the estimate-is-not-the-final-liability paragraph, and the missing-document line.

---

## Section numbering under a dropped block

**Nothing needs renumbering here.** Both conditionals sit *inside* section 02, so neither can drop a numbered section. That is deliberate: this is the letter most likely to be generated in bulk, and a numbering bug in it would reach the most clients.

### Section 02 must never be silent

`PaymentEnclosed` and `NoPaymentRequired` are inverses, and one of them must render. A client who reads the "interest runs from the original due date" callout and then finds no instruction underneath it concludes there is nothing to pay. That conclusion has to be a statement the firm made, not a gap it left.

---

## Example payload

`PaymentEnclosed` true, so `NoPaymentRequired` is false. The other state is the same payload inverted, with `EstimatedPaymentAmount` dropped.

```json
{
  "LetterDate": "April 14, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientLetterName": "Dan",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "ExtendedDeadline": "October 15, 2027",
  "PaymentDeadline": "April 15, 2027",
  "MaterialsDeadline": "August 15, 2027",
  "EstimatedPaymentAmount": "$2,150.00",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "PreparerEmail": "arjun@satcllp.com",
  "PreparerPhone": "307-941-0508",
  "PaymentEnclosed": true,
  "NoPaymentRequired": false,
  "ExtendedReturns": [
    { "Return": "Federal Form 4868", "Detail": "Extends the Form 1040 to October 15, 2027" },
    { "Return": "Ohio IT 40P extension", "Detail": "Ohio honours the federal extension; the payment voucher is filed separately" },
    { "Return": "City of Solon extension request", "Detail": "Filed directly with the municipality — Ohio municipalities do not all follow the state" }
  ],
  "OutstandingItems": [
    { "Document": "K-1 from Larchmere Holdings LLC", "Detail": "Expected from the partnership by September 1" },
    { "Document": "Brokerage consolidated 1099", "Detail": "The corrected one — the original showed a wash-sale adjustment still pending" },
    { "Document": "Digital asset activity for the year", "Detail": "Every exchange, wallet and transfer, including transfers that were not sales" }
  ]
}
```

---

## Deliberately not here

1. **No apology, and no reason.** Why the extension was needed is a conversation, not a paragraph in a form letter. Whichever side it favours, putting it in writing on a document that goes out hundreds of times a season is a bad trade.
2. **No fee.** The invoice owns it. An extension notice that also asks for money reads as a bill and gets filed as one — and this is the letter that most needs reading.
3. **No signature line.** Nothing here needs signing. The extension is already filed.
4. **No deadline the firm invented.** Every date in this letter is either statutory or the materials deadline the firm already publishes.
5. **No "don't worry".** An extension is routine, and the letter says so by being one page. Saying it out loud invites the opposite reading.
6. **No second extension.** Section 04 says the extension cannot be extended again, and offers nothing in its place, because there is nothing to offer.

## Notes for the software

1. **`PaymentEnclosed` and `NoPaymentRequired` must be derived from one stored value.** Two independent booleans can both be false, which leaves section 02 with a warning and no instruction — the worst possible version of this letter.
2. **`MaterialsDeadline` is keyed by season *stage* as well as return type.** The onboarding letter and the organizer carry the original-season value; this letter carries the extension-season one. Same field name, different setting. A registry storing one value per return type will print the wrong date here — and `registry/fields.yaml` already flags a `MaterialsDeadline` mismatch as the organizer's most likely bug. This is the second way it can happen.
3. **`OutstandingItems` is what is still missing**, which means deriving it by subtracting what arrived from the onboarding letter's `RequestList`. Done by hand, it will drift, and a client chased for something they already sent stops reading these letters.
4. `ExtendedReturns` must list what was actually filed. Some authorities extend automatically on the federal extension and some do not; a template that assumes is a template that tells a client a municipal return is covered when it is not.
5. The checkboxes are printed squares. **Do not turn them into PDF form fields.**
6. Strip the `.f` class and the `.cond` markers on the client-facing render.
7. Name the output: `SAT-C Extension Notice — Reyes — 2026.pdf`.
