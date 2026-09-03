# Bookkeeping engagement letter — required variables

Companion to `SATC Engagement Letter - Bookkeeping.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

Pairs with `SATC Fee Estimate.html`, which section 05 points at instead of restating a fee.

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

### Shared with the tax letter and the estimate (10 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | July 8, 2027 | |
| `<<EngagementRef>>` | Yes | 2027-0208 | The join key across letter, estimate, and invoice |
| `<<ClientFullName>>` | Yes | Clifton Millworks LLC | The entity's legal name. Appears twice. |
| `<<ClientAddress1>>` | Yes | 2140 Vine Street | |
| `<<ClientCity>>` | Yes | Cincinnati | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 45219 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

### Specific to this engagement (8 fields + a list + a flag)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<Cadence>>` | Yes | monthly | **Lowercase** — it sits mid-sentence and in the subject line. Appears twice. |
| `<<FirstPeriod>>` | Yes | the July 2027 period | The first period we own |
| `[[EACH ScopeItems]]` | List | one or more | Two sub-fields each |
| `<<Item.Service>>` | Yes | Reconciliation | |
| `<<Item.Detail>>` | Yes | All bank, card, and loan accounts, to statement | |
| `[[IF CatchUp]]` | Flag | true / false | Drops the catch-up paragraph entirely when false |
| `<<CatchUpPeriods>>` | If catch-up | January through June 2027 | |
| `<<DeliveryTarget>>` | Yes | the 20th of the following month | A commitment — make it one you can keep in April |
| `<<AccountingSystem>>` | Yes | QuickBooks Online | |
| `<<NoticePeriod>>` | Yes | thirty (30) days | |
| `<<SignerName>>` + `<<SignerTitle>>` | Yes | Dana Whitfield · Managing Member | Who signs for the entity. Not shared — replaces the tax letter's taxpayer/spouse pair. Two fields. |

**Total: 25 fields + 1 repeating list of 2 + 1 conditional flag.**

Not variables: the Encyro delivery method, and all eight clause bodies.

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
  "LetterDate": "July 8, 2027",
  "EngagementRef": "2027-0208",
  "ClientFullName": "Clifton Millworks LLC",
  "ClientAddress1": "2140 Vine Street",
  "ClientCity": "Cincinnati",
  "ClientState": "OH",
  "ClientZip": "45219",
  "SignerName": "Dana Whitfield",
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
  "Cadence": "monthly",
  "FirstPeriod": "the July 2027 period",
  "ScopeItems": [
    { "Service": "Reconciliation", "Detail": "All bank, card, and loan accounts, to statement" },
    { "Service": "Financial statements", "Detail": "Balance sheet and statement of operations for each period" },
    { "Service": "Adjusting entries and close", "Detail": "Including the year-end close" }
  ],
  "CatchUp": true,
  "CatchUpPeriods": "January through June 2027",
  "DeliveryTarget": "the 20th of the following month",
  "AccountingSystem": "QuickBooks Online",
  "NoticePeriod": "thirty (30) days"
}
```

---

## Where this differs from the tax letter, and why

1. **Section 02 draws the advisory boundary explicitly** — we advise, you decide, and we do not operate your process. This is the boundary the proposal deck sets, and a bookkeeping engagement is where it gets tested.
2. **No custody, no signature authority, no payment initiation.** Stated in writing because an outside bookkeeper with payment rights is how small businesses get defrauded, and because your insurer will care.
3. **Management responsibility is itemised in section 03** — approving transactions, custody of assets, and designating someone to oversee the work. A preparation-of-financial-statements engagement depends on the client accepting exactly those.
4. **Section 08 promises to hand the file back.** Most letters are silent on exit; saying it plainly is worth more in the sales conversation than it costs you.

## Before this template ships

1. **Confirm the legend wording that goes on prepared financial statements.** Section 02 promises each page will carry it. `SATC Financial Statements.html` has the same open item.
2. **Settle the firm's legal name and use it byte-for-byte everywhere** — the footer uses one of the three variants currently in circulation.
