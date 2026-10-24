# Onboarding email — required variables

Companion to `SATC Onboarding Email.html`.

The body of the email that carries the opening pack: the engagement letter and
the fee estimate, and the records release when there was a previous accountant.
It is the one the client actually acts on, so it carries the deadline and the
checklist and nothing legal.

**It was a PDF letter attached to that email until 24 October 2026.** The firm,
marking it on the template review: *"this is actually supposed to be sent as an
email not an attachment."* The words are the letter's, with only what the change
forces: no letterhead, date, address block, reference line or footer; "This
letter tells you" became "Below is"; "We have included" became "We have
attached"; the section numbers went, because an email's headings are plain bold
lines; and the covering note the firm wrote on 31 August 2026 ("Attached is your
engagement letter, with the fee estimate. Please thoroughly review and sign.")
opens it.

Arial 12pt with real lists: the format the firm set for client email in Outlook
on 13 October 2026.

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

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<PeriodLabel>>` | Yes | 2026 tax year | In the subject line, "Your 2026 tax year engagement letter". |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | The greeting. |
| `<<FirmName>>` | Yes | SAT-C LLP | "Thank you for choosing", and the sign-off. |
| `<<MaterialsDeadline>>` | Yes | March 15, 2027 | A real date, never "early March". The tax letter's timing clause carries the same value; set it once. |
| `<<PreparerName>>` | Yes | Arjun Sethuraman, CPA | The point of contact, and the sign-off. |
| `<<PreparerTitle>>` | Yes | Managing Partner | The sign-off. |
| `<<PreparerEmail>>` | Yes | arjun@satcllp.com | The only way the email offers to reach us. |
| `<<ClientEmail>>` | Yes | dreyes@example.com | Where the upload link and the Encyro signing invitation go. |
| `[[EACH RequestList]]` | List | one or more | Two sub-fields. The point of the email; built from the engagement type, not by hand. |
| `<<Item.Document>>` | Yes | All W-2 forms | As a client would name it, not as the tax code does. |
| `<<Item.Detail>>` | Yes | For both of you, including part-year employment | Empty string when there is nothing to add, never "None". |
| `<<FirstDeliverableTarget>>` | Yes | April 1, 2027 | The promise the client remembers. Date or phrase. |
| `<<PriorFirmName>>` | If flag | Halloran & Reeve CPAs | |
| `[[IF PriorFirm]]` | Flag | Boolean | Drops the previous-accountant paragraph for a client with no predecessor. When it prints, it says the authorization is attached, and the pack carries it. |

**Total: 10 fields + 1 repeating list of 2 + 1 flag.**

Not variables: the upload and Encyro instructions, the what-happens-next paragraph, and the opening lines about the attached engagement letter and estimate.

---

## Example payload

```json
{
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientEmail": "dreyes@example.com",
  "MaterialsDeadline": "March 15, 2027",
  "FirstDeliverableTarget": "April 1, 2027",
  "FirmName": "SAT-C LLP",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "PreparerEmail": "arjun@satcllp.com",
  "PriorFirm": true,
  "PriorFirmName": "Halloran & Reeve CPAs",
  "RequestList": [
    { "Document": "All W-2 forms", "Detail": "For both of you, including any part-year employment" },
    { "Document": "Prior year filed return", "Detail": "Federal, state, and local, as filed" }
  ]
}
```

---

## Deliberately not here

1. **No fee, no scope, no terms.** The engagement letter and the estimate own those. This is a to-do list with a date on it.
2. **No signature line.** The engagement letter is what is signed.

## Notes for the software

1. **It is the message, not an attachment.** `outgoing.compose` finds the pack's email body by what it is (`<div class="email">`) and sends it as the email, HTML with a plain-text version; everything else in the pack is attached. Its subject is the `<div class="subject">` line.
2. `RequestList` should come from a template per engagement type with per-client additions, not from free typing. The checklist is where a firm's institutional memory lives.
