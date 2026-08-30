# Records release authorization — required variables

Companion to `SATC Records Release Authorization.html`. The same table renders
on screen below the document itself (`@media print` hidden, so it never reaches
a client).

**The client signs this, not the firm.** It is written in the client's voice,
addressed to their former preparer, and the firm's name appears only as the
place records go.

It travels **with the engagement letter**, by default, to any client who had a
previous accountant. The firm, 26 August 2026: *"let's just make an attachment
that we send for them to sign by default along with the engagement letter."*
It replaces the onboarding letter's paragraph about contacting the predecessor,
which asked the client to authorize something in writing without giving them
the writing.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block |

**Fail the render on any unresolved `<<` or `[[`.**

---

## Fields

### The firm itself (8 fields)

Masthead and footer. Set in `client-documents/registry/firm-settings.yaml`
under `firm:` and merged like any other field.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<FirmName>>` | Yes | SAT-C LLP | Masthead, and the body's "I have engaged …" |
| `<<FirmLegalName>>` | Yes | Sethuraman Accounting, Tax, and Consulting LLP | Footer only |
| `<<FirmAddress1>>` | Yes | 6544 Copley Avenue | Masthead and footer |
| `<<FirmCity>>` + `<<FirmState>>` + `<<FirmZip>>` | Yes | Solon · OH · 44139 | Three fields |
| `<<FirmWebsite>>` | Yes | satcllp.com | No protocol, no `www.` |
| `<<FirmJurisdiction>>` | Yes | Ohio | The footer's partnership sentence |

### Shared with the engagement letter (7 fields)

Same record, same values. Generate the pair in one call.

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | February 3, 2027 | The package's date, identical to the letter's |
| `<<EngagementRef>>` | Yes | 2027-0114 | The join key |
| `<<PeriodLabel>>` | Yes | 2026 tax year | |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | Identifies whose records these are, to a firm that may hold several families |
| `<<ClientAddress1>>` + `<<ClientCity>>` + `<<ClientState>>` + `<<ClientZip>>` | Yes | 418 Rockwell Street · Solon · OH · 44139 | Four fields, on one line here rather than an address block |
| `<<PreparerName>>` + `<<PreparerEmail>>` | Yes | Arjun Sethuraman, CPA · arjun_sethuraman@satcllp.com | Where the records go |

### Specific to this document (3 fields + a flag)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<PriorFirmName>>` | Yes | Halloran & Reeve CPAs | **No address.** The client sends this to a firm they already deal with, and a wrong address on a signed authorization is worse than none. |
| `<<TaxpayerName>>` | Yes | Daniel Reyes | Under the signature line — not the joint addressee form |
| `<<SpouseName>>` | If flag | Maria Reyes | |
| `[[IF JointReturn]]` | Flag | Boolean | A second signature line: a joint return's records belong to both. |

**Total: 21 fields + 1 flag.**

Not variables: the list of what to send, the "electronic copies are preferred"
line, and the not-a-dispute sentence.

---

## Example payload

```json
{
  "LetterDate": "February 3, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "FirmName": "SAT-C LLP",
  "FirmLegalName": "Sethuraman Accounting, Tax, and Consulting LLP",
  "FirmAddress1": "6544 Copley Avenue",
  "FirmCity": "Solon",
  "FirmState": "OH",
  "FirmZip": "44139",
  "FirmWebsite": "satcllp.com",
  "FirmJurisdiction": "Ohio",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "TaxpayerName": "Daniel Reyes",
  "SpouseName": "Maria Reyes",
  "JointReturn": true,
  "PriorFirmName": "Halloran & Reeve CPAs",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerEmail": "arjun_sethuraman@satcllp.com"
}
```

---

## Notes for whoever wires the software

1. **Rendered only when `PriorFirm` is true.** A client with no predecessor
   gets the opening package without it. `cli.OPENING_PACKAGE` decides; the
   document itself carries no flag for its own existence.
2. **Two signature lines on a joint return.** The records of a joint return
   belong to both people, and one signature invites the predecessor to ask.
3. Name the output: `SAT-C Records Release — Reyes — 2026.pdf`.

## What this document deliberately does not do

1. **It makes no claim about anyone's obligations.** It asks; it does not tell
   the predecessor what any rule requires of them. What a former preparer must
   release, and on what terms, is between the client and that firm.
2. **It does not say the firm will chase them.** The client signs and sends it,
   which is faster and needs no second authorization.
3. **No fee, no scope, no deadline.** One instruction, on one page.
