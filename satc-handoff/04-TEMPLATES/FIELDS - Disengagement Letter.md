# Disengagement letter — required variables

Companion to `SATC Disengagement Letter.html`. The same table renders on screen below the letter itself (`@media print` hidden, so it never reaches a client).

**The letter nobody builds until they urgently need it** — which is exactly why it is built now. Written under pressure it comes out either apologetic or angry, and both are expensive. Written in advance it is what it should be: a record of dates and facts.

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

### Shared with the engagement letter (11 fields)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<LetterDate>>` | Yes | June 4, 2027 | The date the letter is sent, which may be earlier than the effective date. |
| `<<EngagementRef>>` | Yes | 2027-0114 | The engagement being ended. **One letter per ref** — a client with a personal and an entity engagement gets two letters, or one whose `ScopeEnded` says so precisely. |
| `<<PeriodLabel>>` | Yes | 2026 tax year | Appears twice — subject line and footer. |
| `<<ClientFullName>>` | Yes | Mr. and Mrs. Daniel Reyes | |
| `<<ClientLetterName>>` | Yes | Dan | Salutation only. |
| `<<ClientAddress1>>` | Yes | 418 Rockwell Street | **The address of record.** Send it there, by a method that produces a receipt, whatever else you also do with it. |
| `<<ClientCity>>` | Yes | Solon | |
| `<<ClientState>>` | Yes | OH | |
| `<<ClientZip>>` | Yes | 44139 | |
| `<<PreparerName>>` + `<<PreparerTitle>>` | Yes | Arjun Sethuraman, CPA · Managing Partner | Two fields. |

### Specific to this letter (6 fields + 2 lists + 4 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<EffectiveDate>>` | Yes | June 30, 2027 | **Appears four times.** The date everything in the letter hinges on. Drive all four from one value. |
| `<<ScopeEnded>>` | Yes | the preparation of your 2026 individual income tax returns | **A phrase, not a code**, naming precisely what ends. If another engagement continues, this is where the letter says so. |
| `<<RecordsAvailableUntil>>` | Yes | August 31, 2027 | A real date. Appears in the dateline and in section 04. |
| `<<OutstandingBalance>>` | If flag | $1,240.00 | A pre-formatted string from the one money formatter. **This template does no arithmetic.** |
| `<<PreparerEmail>>` + `<<PreparerPhone>>` | Yes | arjun@satcllp.com · 307-941-0508 | Two fields. |
| `[[EACH WorkStatus]]` | List | one or more | Two sub-fields. **Every piece of work in scope, complete or not.** |
| `<<Item.Work>>` | Yes | 2026 Federal Form 1040 | |
| `<<Item.Status>>` | Yes | Prepared and e-filed on April 9, 2027; accepted April 9 | **A sentence with a date in it**, never "done" or "in progress". |
| `[[EACH OpenDeadlines]]` | List | one or more | Two sub-fields. The dates the client now owns. |
| `<<Item.Obligation>>` | Yes | File the 2026 municipal return | Imperative; the client is the subject. |
| `<<Item.Detail>>` | Yes | City of Solon, due October 15, 2027 — extended, not filed | |
| `[[IF ClientInitiated]]` | Flag | Boolean | The client asked. One sentence, and no explanation recorded. |
| `[[IF FirmInitiated]]` | Flag | Boolean | **The exact inverse.** States that it is the firm's decision and that notice is being given. Gives no reason — see below. |
| `[[IF BalanceOutstanding]]` | Flag | Boolean | Renders section 05 with the balance. |
| `[[IF AccountSettled]]` | Flag | Boolean | **The exact inverse.** Renders section 05 saying nothing is owed. |

**Total: 17 fields + 2 repeating lists of 2 + 4 flags.** Both flag pairs are inverses; exactly one of each pair is ever true.

Not variables: firm name, address, phone, website, the Ohio LLP footer, the nothing-is-in-a-queue callout, the records-come-back-either-way sentence, the whole of section 06, and the not-a-complete-list sentence in section 03.

---

## The letter states no reason, ever

Neither branch of section 01 says why the engagement ended. **This is the most important decision in the template, and it is not an oversight.**

A reason in a disengagement letter is a statement of fact the firm has to be able to stand behind, written at the worst possible moment, that goes into a file the firm no longer controls. It has no upside. The client already knows why. Every other reader of the letter is someone the firm did not choose — a successor, a lender, a lawyer, an authority.

Say the date. Say what is outstanding. Say what happens next.

**Do not add a reason field to this template**, and do not let one arrive through `ScopeEnded`, which names what ended and not why.

---

## Section numbering under a dropped block

**Nothing needs renumbering**, and the template is built that way on purpose.

- `ClientInitiated` / `FirmInitiated` sit **inside** section 01.
- `BalanceOutstanding` / `AccountSettled` render **two versions of section 05**, of which exactly one survives.

A disengagement letter is the one most likely to be read closely by someone other than the client. A gap in its clause numbers is the kind of detail that gets asked about.

### Section 05 always renders

Silence about money in a disengagement letter is read as a threat. If there is a balance, the letter states it and states that records come back regardless. If there is not, the letter says so and says no final invoice will follow. There is no third case.

---

## Example payload

Firm-initiated with a balance outstanding — the harder of the two combinations, and the one worth proofing. The other states are the same payload with the flags inverted; `OutstandingBalance` drops when `AccountSettled` is true.

```json
{
  "LetterDate": "June 4, 2027",
  "EngagementRef": "2027-0114",
  "PeriodLabel": "2026 tax year",
  "ClientFullName": "Mr. and Mrs. Daniel Reyes",
  "ClientLetterName": "Dan",
  "ClientAddress1": "418 Rockwell Street",
  "ClientCity": "Solon",
  "ClientState": "OH",
  "ClientZip": "44139",
  "EffectiveDate": "June 30, 2027",
  "ScopeEnded": "the preparation of your 2026 individual income tax returns and the related state and municipal filings",
  "RecordsAvailableUntil": "August 31, 2027",
  "OutstandingBalance": "$1,240.00",
  "PreparerName": "Arjun Sethuraman, CPA",
  "PreparerTitle": "Managing Partner",
  "PreparerEmail": "arjun@satcllp.com",
  "PreparerPhone": "307-941-0508",
  "ClientInitiated": false,
  "FirmInitiated": true,
  "BalanceOutstanding": true,
  "AccountSettled": false,
  "WorkStatus": [
    { "Work": "2026 Federal Form 1040", "Status": "Prepared and e-filed on April 9, 2027; accepted April 9" },
    { "Work": "2026 Ohio IT 1040", "Status": "Prepared and e-filed on April 9, 2027; accepted April 10" },
    { "Work": "2026 City of Solon municipal return", "Status": "Not prepared. An extension was filed on April 14, 2027; the return itself is outstanding." },
    { "Work": "2027 estimated payment vouchers", "Status": "Not prepared." }
  ],
  "OpenDeadlines": [
    { "Obligation": "File the 2026 municipal return", "Detail": "City of Solon, due October 15, 2027 — extended, not filed" },
    { "Obligation": "Make the 2027 second-quarter estimated payment", "Detail": "Due June 15, 2027. No voucher was prepared; your new preparer will need the 2026 return to calculate it." }
  ]
}
```

---

## Deliberately not here

1. **No reason.** See above. The single most deliberate omission in the set.
2. **No successor named, and no recommendation.** Recommending a firm to a client you are leaving attaches you to whatever happens next.
3. **No opinion on anything.** Section 06 says so outright, because a letter arriving at the end of a relationship is the one most likely to be shown to a third party.
4. **No records held against payment.** Section 05 says the records come back either way, in terms. Leaving it unsaid invites the client to assume the opposite — and to say so to someone.
5. **No signature line, and no acknowledgement to return.** This is notice, not agreement. Asking a departing client to countersign creates a document that can be withheld, and a fact that can then be disputed.
6. **No good wishes.** Warmth here reads as either insincere or as an opening. The engagement letter set the tone; this one records dates.
7. **No offer to help "if anything comes up".** Section 06 states exactly what will be done about a notice and calls it a courtesy rather than an engagement. An open-ended offer is an engagement nobody priced.

## Notes for the software

1. **Both flag pairs must be derived from one stored value each.** Two independent booleans can both be false. A disengagement letter that is silent about who ended it, or silent about money, is worse than no letter at all.
2. **`WorkStatus` must cover every engaged item**, complete or not, generated from the engagement scope rather than typed. The callout beneath it says nothing else is being worked on — that sentence is only safe if the list above it is generated.
3. **`OpenDeadlines` is a statement of what the firm knows.** Section 03 says in terms that it is not a complete list of the client's obligations. Do not let that sentence be edited out: it is the difference between telling a client what you know and taking on a duty to know everything.
4. **Send it by a method that produces a receipt, and store the receipt with the engagement.** The date this letter took effect is the fact the whole document exists to fix.
5. The checkboxes in `OpenDeadlines` are printed squares. **Do not turn them into PDF form fields.**
6. Strip the `.f` class and the `.cond` markers on the client-facing render.
7. Name the output for a human: `SAT-C Disengagement — Reyes — 2026.pdf`.
