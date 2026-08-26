# Sign-off register — the documents the firm must read

Asked for by the firm, 25 August 2026:

> flag this and all other templates as something i will review and sign off on

Nothing here is blocked on code. Every item below renders today; what it is
waiting for is a human reading it and saying it is a document SATC would send.

**All ten were rendered and sent to the firm on 26 August 2026.** Six render
for real; four are stamped DRAFT because a firm decision still blocks them, and
the blocker is named against each below. Status now means: has the firm read it
and said what it thinks.

**Status values.** `sent` — rendered and delivered, waiting on a reading.
`unread` — nobody at the firm has read the rendered output.
`changes` — read, and something needs to change; the note says what. `signed` —
read and approved, with the date.

---

## The ten templates

Rendered from `satc-handoff/04-TEMPLATES/*.html`. To see one with real content:
`cd client-documents && python cli.py demo` writes the whole pack.

| Document | Status | Note |
|---|---|---|
| Fee Estimate | **sent 26 Aug** | The one that changed most. Package line now carries its covers list — the firm has seen a rendered PDF and called it "too wordy but fine where it's at" |
| Invoice | **sent 26 Aug** | DRAFT. Blocked on the materials deadline and on having real line items — the estimate-to-invoice bridge is what fills those |
| Tax engagement letter | **sent 26 Aug** | Section 06 fee clause was rewritten 25 Aug and **reverted** at the firm's instruction. Do not rewrite it again |
| Business engagement letter | **sent 26 Aug** | DRAFT. Blocked on one `[CONFIRM:` — how much the letter says about officer compensation. A substantive tax position, not an agent's to write |
| Bookkeeping engagement letter | **sent 26 Aug** | DRAFT |
| Onboarding letter | **sent 26 Aug** | Renders for real now |
| Organizer letter | **sent 26 Aug** | DRAFT. Blocked on the 2026 materials deadline |
| Delivery letter | **sent 26 Aug** | |
| Extension notice | **sent 26 Aug** | |
| Disengagement letter | **sent 26 Aug** | The one with the most legal exposure. Nothing in it was invented — it is the firm's own wording or a `[CONFIRM:` |

## The wording the software assembles

Not a template. These are sentences built at render time and printed on client
documents, so they need the same reading.

| What | Where to change it | Status |
|---|---|---|
| Package names, prices, and what each covers | `client-documents/registry/fee-schedule.yaml` → `base` | unread |
| Every add-on line's name and detail | same file → `per_unit` | unread |
| The six per-form situations and their assumptions | same file → `per_form` | **changes** — the firm asked to walk these; the situations and the assumption sentences are Claude's, not the firm's |
| The assumption sentences on every estimate | same file → `assumed` | unread |
| The connective English — "Includes:", "after the first", "this estimate assumes…" | same file → `phrases` | unread |

### New on 26 August 2026, and none of it read yet

Everything below is a sentence a client will see, written by me from a
decision the firm made. The decisions are the firm's; **these words are not.**

| What | Where | The words |
|---|---|---|
| The **Self-Employed** package name and its one-liner | `base.1040.tiers.business` | "Self-Employed" / "You work for yourself" |
| The **amended return** line | `base.1040.amended` | "Amended return" / "Form 1040-X, prepared from the return as filed" |
| The **extension** line | `per_unit.extension_estimate` | "Extension with a payment estimate" / "Computing what to pay by the original due date, from an incomplete file" |
| The **soft-cap** sentence, which prints on any estimate with five or more foreign accounts | `phrases.capped_soft` | "…capped at 4 — beyond that the additional time is billed at $150 an hour as it is worked, and we will tell you as soon as we see it" |
| The **entity starting notes** — four lines, shown wherever an entity price is | `base.1065/1120S/1120.starting_note` | "A balance sheet, where one is required" · "Inventory, where the business carries any" · "Each partner's / shareholder's K-1 after the first two" · "Returns in more than one state" |

The starting notes are the ones to read hardest: they are the only thing
standing between a published "$950" and a client who thinks that is the total.
They are also the first wording of mine that will appear on the public site
rather than on a document one client reads.

---

## Where the words live, if you want to change one

Three places, and only three.

1. **The layout and the fixed prose of a document** — headings, the paragraph
   above the table, the signature block. That is the template HTML in
   `satc-handoff/04-TEMPLATES/`. Hand-edited, no build step; open it in a
   browser to see the change.
2. **Anything the price sheet decides** — package names, prices, what each
   covers, what each add-on is called, what the estimate assumes, and the
   sentences that stitch those together. All of it is
   `client-documents/registry/fee-schedule.yaml`. One file.
3. **What the interview asks** — `client-documents/registry/interview.yaml`.

If a sentence on a client document is in none of those three, that is a bug
worth reporting: it means it is still written in Python, where the firm cannot
reach it.

---

## Round three of the sign-off room — the firm's notes, 26 August 2026

Saved at 19:05 and 21:14 UTC. Recorded here because the room is a page and a
page gets superseded; this is the durable copy of what was asked for and what
was done about it.

### Fee estimate — *changes*

> "Brokerage keying — this is way too much crap. we are actually deleting the
> $95 thing - all are $45 we will figure out how to make it efficient. however
> it is possible that brokerage statements are so messy they require keying
> which could significantly increase time and therefor result in an hourly
> charge."
>
> "notices and corresponds belong in a different letter engagement or would be
> discussed anyway, get rid of it. can't bite if not a secret"
>
> "i want all of it to be conveyed more concisely they can ask me questions if
> they have to"

Done. The $95 line and the question that fed it are gone; every statement is
$45 and a disordered one is hourly. The notices assumption is gone. Earlier
the same day: the heading match, the caption, "this estimate assumes" in every
bullet, and both static notes.

### Engagement letter — *changes*

> "delete If one is needed we will send a new estimate… replace with If your
> return requires additional work, a new estimate will be provided in writing.
> Additional work will not be begin without your written consent to the new
> estimate."
>
> "Representing you in an examination, notice response, or appeal is a separate
> engagement, quoted separately. --> …is a separately quoted engagement."

Done, in the firm's own words, with one typo fixed ("will not be begin"), and
carried to the business letter and to all three fees clauses.

### Onboarding letter — *changes*

> "we dont require login to Encyro, we just email encrypted via encyro"
> "we do not need SS cards, we do require the numbers"
> "let's make a note to incorporate a license expiry check"
> "The whole K-1 including its statements… --> Including its statements"
> "there is likely more to this - maybe we should just have a separate
> attachment for business stuff depending on your situation"
> "Emailing or otherwise transmitting unprotected documents are done so at your
> own risk. (Bolded)"
> "let's just make an attachment that we send for them to sign by default along
> with the engagement letter… work this into the software and make the template"
> "delete and we will keep that to one message rather than a run of them"

Done, except two that are build work and are in `PLAN.md`: the licence expiry
check and the business attachment. The records release authorization is built
and goes out by default with the engagement letter.

### Business engagement letter — *changes*

> "go through notes on above engagement and look for improvements then i will
> come review this"

Done — the three engagement-letter replacements are on it.

### Organizer — *come back to this*

> "i want to see this when i see the organizer - what is this and how do they
> fill it out? it should be as simple as we can make it for both of our sakes"

**There is no organizer**, only a cover letter for one. See
`docs/review-queue.md` for the three things the firm has to decide before one
can be built, and for the `doctor`/`render` disagreement this found.

### Invoice — *come back to this*

> "come back to this when the process is built, looks fine from a high level"

Untouched but for the note that duplicated the estimate's deleted sentence.

### Delivery letter — *come back to this*

> "Your returns are ready --> Action required: please review your 2026 tax
> returns"
> "Your returns are finished. --> We have completed our work on your returns."
> "This letter tells you what we prepared… --> Below is a summary of what we
> prepared and your next steps."
> "[the review paragraph] is such an awfully malformed statement to make -
> literally makes it sound like we are pinning this work on them rather than
> asking them to review it as it is ultimately theirs. you can just do better."
> "we can have a process that inputs the preliminary numbers (these) into the
> workbook which then fills the template… and then we can record final numbers"

Done, and the rest of the letter went over as asked. The numbers process is in
`PLAN.md`.

### Consistency (`make check`) — *approved*

