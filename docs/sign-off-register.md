# Sign-off register — the documents the firm must read

Asked for by the firm, 25 August 2026:

> flag this and all other templates as something i will review and sign off on

Nothing here is blocked on code. Every item below renders today; what it is
waiting for is a human reading it and saying it is a document SATC would send.

**Status values.** `unread` — nobody at the firm has read the rendered output.
`changes` — read, and something needs to change; the note says what. `signed` —
read and approved, with the date.

---

## The ten templates

Rendered from `satc-handoff/04-TEMPLATES/*.html`. To see one with real content:
`cd client-documents && python cli.py demo` writes the whole pack.

| Document | Status | Note |
|---|---|---|
| Fee Estimate | unread | The one that changed most. Package line now carries its covers list — the firm has seen a rendered PDF and called it "too wordy but fine where it's at" |
| Invoice | unread | |
| Tax engagement letter | unread | Section 06 fee clause was rewritten 25 Aug and **reverted** at the firm's instruction. Do not rewrite it again |
| Business engagement letter | unread | |
| Bookkeeping engagement letter | unread | |
| Onboarding letter | unread | Blocked from a real render by the materials deadlines, which are a firm setting |
| Organizer letter | unread | |
| Delivery letter | unread | |
| Extension notice | unread | |
| Disengagement letter | unread | The one with the most legal exposure. Nothing in it was invented — it is the firm's own wording or a `[CONFIRM:` |

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
