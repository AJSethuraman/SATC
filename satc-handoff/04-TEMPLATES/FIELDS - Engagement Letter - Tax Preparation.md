# Engagement letter — required variables

Companion to `SATC Engagement Letter - Tax Preparation.html`. The same table renders on screen below the letter itself (it is `@media print` hidden, so it never reaches a client).

Two syntaxes, deliberately different so a regex can tell them apart:

- `<<Field>>` — substitutes a value
- `[[IF Name]] … [[END IF]]` — keeps or drops a block

**Fail the render on any unresolved `<<` or `[[`.** A merge that leaves `<<ClientFullName>>` in a letter sent to a client is the one bug that actually costs you a client.

---

## Grouped by where the value comes from

Grouping matters more than the alphabetical list: it tells you which system of record has to exist before the letter can generate at all.

### Generated at send time (1 field)

| Field | Example | Notes |
|---|---|---|
| `<<LetterDate>>` | February 3, 2027 | Spelled out. Never 2/3/27. |

### From the client record (8 fields + a flag)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | Addressee block |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<TaxpayerName>>` | Yes | Daniel Reyes | Printed under the signature line so the right person signs |
| `<<SpouseName>>` | If joint | Maria Reyes | |
| `[[IF JointReturn]]` | Flag | true / false | Drops the spouse signature block **and** the joint-representation paragraph for a single filer |

An optional `Address2` line is not in the template. Add it only if your data actually has one — an empty line in an address block looks like a bug.

### From the engagement record (7 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<EngagementRef>>` | Yes | 2027-0114 | Must match the invoice and the statement for the same engagement |
| `<<TaxYear>>` | Yes | 2026 | Appears three times in the letter — drive them all from one value |
| `<<FederalReturns>>` | Yes | Form 1040 with Schedules A, C, and SE | |
| `<<StateReturns>>` | Yes | Ohio IT 1040 | Name every state. **This is your scope boundary.** |
| `<<LocalReturns>>` | Yes | Solon municipal | Name every locality. Emit `None` when there are none. |
| `<<AdditionalForms>>` | Yes | Two K-1s as reported; FBAR (FinCEN 114) | Emit `None` when empty. Never blank — with foreign reporting in scope, blank and "None" are not the same statement. |
| `<<MaterialsDeadline>>` | Yes | March 15, 2027 | A real date, not "early March" |

### Firm settings — set once, rarely change (3 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<ReturnInstruction>>` | Yes | Sign through Encyro and it comes straight back to us. | Replaces the old "return it in the envelope provided", which is wrong for an emailed letter |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields |

**Total: 26 fields + 1 conditional flag.**

Not variables — hardcoded in the template, and correct to keep that way: the Encyro delivery method, and all nine clause bodies.

**The fee is deliberately not a field.** Section 06 points at the estimate attached to the letter instead of restating a number, so the letter and the estimate can never disagree. A re-quote means reissuing the estimate, not editing the letter.

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
  "TaxYear": "2026",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "TaxpayerName": "Daniel Reyes",
  "SpouseName": "Maria Reyes",
  "JointReturn": true,
  "FederalReturns": "Form 1040 with Schedules A, C, and SE",
  "StateReturns": "Ohio IT 1040",
  "LocalReturns": "Solon municipal",
  "AdditionalForms": "Two K-1s as reported",
  "MaterialsDeadline": "March 15, 2027",
  "ReturnInstruction": "Sign through Encyro and it comes straight back to us.",
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

## Notes for whoever wires the software

1. **Escape the values.** Substitution goes into HTML — a client named "Ross & Sons" will otherwise break the page.
2. **Fail loudly** on any unresolved `<<` or `[[` before rendering the PDF. No silent pass-through.
3. **Strip the `.f` class and the `.cond` markers on the client-facing render.** They exist so an unfilled proof is obvious; a real letter should show no field chrome at all.
4. PDF at Letter, 100%, no browser headers or footers. The footer block repeats on every page automatically — nothing needs positioning by hand.
5. Name the output for a human: `SAT-C Engagement Letter — Reyes — 2026.pdf`. It sits in a client's downloads folder for years.

---

## Before this template ships

**Settle the firm's legal name and use it byte-for-byte everywhere.** Your current documents carry three variants — "Sethuraman Accounting Tax and Consulting, LLP", "Sethuraman Accounting Tax & Consulting LLP", and "Sethuraman Accounting, Tax, and Consulting LLP". Only one is on the Ohio filing.
