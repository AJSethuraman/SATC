# Organizer email — required variables

Companion to `SATC Organizer Email.html`.

The email a returning client gets in January with their organizer. The highest
volume document in the set: it goes to every returning client every year, so it
is also the one most likely to ship a merge bug at scale.

**It was a PDF cover letter until 24 October 2026.** The firm, marking it on the
template review: *"this is actually supposed to be sent as an email not an
attachment."* The words are the letter's, with only what the change forces: no
letterhead, date, address block, reference line or footer; "is enclosed" became
"is attached"; and the section numbers went, because an email's headings are
plain bold lines.

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
| `<<TaxYear>>` | Yes | 2026 | The year being organised. In the subject line and the first sentence. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | The greeting. |
| `<<MaterialsDeadline>>` | Yes | March 15, 2027 | **The same date the engagement letter will carry.** Two different dates across the two is the mistake this email is most likely to make. |
| `[[EACH Requested]]` | List | one or more | Two sub-fields. Drive it from last year's return, not a generic checklist; a list naming what the client actually had gets returned faster. |
| `<<Item.Category>>` | Yes | W-2s | |
| `<<Item.Detail>>` | Yes | Both employers, including the one you left in March | |
| `[[IF FeeChange]]` | Flag | true / false | Drops the fee paragraph entirely when false. |
| `<<FeeChangeNote>>` | If flagged | Our fees for individual returns are increasing modestly this year. | One or two sentences. **Say it in January or not at all.** |
| `<<PreparerName>>` | Yes | Arjun Sethuraman, CPA | The sign-off. |
| `<<PreparerTitle>>` | Yes | Managing Partner | The sign-off. |
| `<<FirmName>>` | Yes | SAT-C LLP | The sign-off. |

**Total: 7 fields + 1 repeating list of 2 + 1 conditional flag.**

Not variables: the secure upload instruction, and the five items under "What to tell us about".

---

## Example payload

```json
{
  "TaxYear": "2026",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "MaterialsDeadline": "March 15, 2027",
  "Requested": [
    { "Category": "W-2s", "Detail": "Both employers, including the one you left in March" },
    { "Category": "1099s and brokerage statements", "Detail": "Consolidated 1099, plus anything new" }
  ],
  "FeeChange": false,
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "FirmName": "SAT-C LLP"
}
```

---

## How this one earns its keep

1. **The requested list is per-client, not generic.** Generating it from last year's return, naming their employers, their brokerage, their rental, is the difference between an organizer that comes back in two weeks and one that comes back in April.
2. **"What to tell us about" asks the questions clients answer wrong by omission.** Digital assets, foreign accounts, a new K-1. Asking in January costs nothing; finding out in April costs a filing.
3. **The deadline appears once, in bold.** It is the only thing in the email that must survive a skim.
4. **The fee-change paragraph is conditional and belongs here.** January is when a client can absorb a fee change without resentment.

## Notes for the software

1. **The organizer is not ours to attach.** It is printed from Drake. `cli.py event organizer` writes this email as an `.eml` draft that opens addressed and written; the preparer attaches the organizer before pressing send. The first sentence says it is attached, and the pre-send gate holds that promise to the `organizer` attachment the preparer declares.
2. Its subject is the `<div class="subject">` line, merged like any other field.
