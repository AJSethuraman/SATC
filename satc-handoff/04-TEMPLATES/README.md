# SATC — Client Templates

Merge templates: documents a client actually receives, generated per engagement
from a data record. Distinct from the collateral one folder up, which is
designed once and never varies.

**Making a new one?** Read `../00-START-HERE/AUTHORING-CONTRACT.md` first, copy
`_SKELETON.html`, and link `satc-doc.css`. The contract carries the component
vocabulary, the field-naming rules, the house voice, and a mechanical self-check
to run before calling a document finished.

**Every template here is a pair.** The HTML renders; the `FIELDS` markdown lists
every variable it needs, grouped by which record supplies the value. Neither is
useful alone — if you add a template, add its field doc in the same commit.

---

## Templates

| Template | Fields | Status |
|---|---|---|
| `SATC Engagement Letter - Tax Preparation.html` | `FIELDS - Engagement Letter - Tax Preparation.md` | **Ready to review.** 19 fields + 1 flag. No open legal placeholders. |
| `SATC Fee Estimate.html` | `FIELDS - Fee Estimate.md` | **Ready to review.** 11 fields + 1 repeating list. Referenced by section 06 of the tax letter and section 05 of the bookkeeping letter; generated with whichever letter it accompanies. |
| `SATC Engagement Letter - Bookkeeping.html` | `FIELDS - Engagement Letter - Bookkeeping.md` | **Ready to review.** 18 fields + 1 list + 1 flag. Draws the advisory boundary and the no-custody rule explicitly. One open item: the financial-statement legend wording. |
| `SATC Organizer Cover Letter.html` | `FIELDS - Organizer Cover Letter.md` | **Ready to review.** 13 fields + 1 list + 1 flag. Sent in January ahead of the letter and estimate. Highest volume document in the set. |
| `SATC Onboarding Letter.html` | `FIELDS - Onboarding Letter.md` | **Ready to review.** 18 fields + 1 list + 1 flag. Third document in the opening package — the one the client acts on. First template where a conditional drops a *numbered* section; see the numbering note. |
| `SATC Invoice.html` | `FIELDS - Invoice.md` | **Ready to review.** 23 fields + 1 list + 2 flags. Shares the estimate's ledger vocabulary so the two compare line for line. Subtotal and amount due are computed, never typed. |
| `SATC Engagement Letter - Business Return.html` | `FIELDS - Engagement Letter - Business Return.md` | **Ready to review.** 21 fields + 3 flags, no lists. The entity twin of the tax letter, worded identically wherever it can be. Section 02 is the K-1 timing clause the whole engagement turns on. **One open `[CONFIRM]`** — officer compensation under an S election. |
| `SATC Tax Return Delivery Letter.html` | `FIELDS - Tax Return Delivery Letter.md` | **Ready to review.** 15 fields + 2 lists + 3 flags. Ships with the finished returns and closes the engagement at transmission. No fee and no amount payable to the firm — the invoice owns those. |
| `SATC Extension Notice.html` | `FIELDS - Extension Notice.md` | **Ready to review.** 17 fields + 2 lists + 2 flags. The shortest document in the set and the highest volume. Sent the day the extension is filed, because the payment date does not move. |
| `SATC Disengagement Letter.html` | `FIELDS - Disengagement Letter.md` | **Ready to review.** 17 fields + 2 lists + 4 flags. **States no reason, deliberately** — see its field doc. Records dates and facts, returns records regardless of the balance, and offers no opinion on anything. |

## Shared stylesheet

`satc-doc.css` is canonical. A template links it and adds an inline `<style>`
holding **only** rules unique to that document — never a second `:root`, never a
copied-and-tweaked rule. If two templates need the same rule, it belongs in the
shared file.

> **Migrated.** All six templates now link `satc-doc.css` and carry **no inline
> CSS at all** — every rule they had was either already in the shared file or
> belonged there. Two divergences were resolved rather than copied: the ledger
> documents' sign-off spacing became `.doc .signoff` in the shared file, and
> their inline conditional markers now use the `.cond.inline` class the shared
> file already carried for that case. See `../RUN-LOG.md`.

## Conventions every template follows

**Two syntaxes**, deliberately different so a regex can tell them apart:

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block |
| `[[EACH List]]` … `[[END EACH]]` | Repeats what is between them, once per item |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

**Field naming** — PascalCase, no spaces, no underscores. A field that means the
same thing in two templates carries the same name in both. `EngagementRef` is
the join key across the letter, the invoice, and the statement; it is not
optional anywhere.

**Non-negotiables for the software:**

1. **Escape values on substitution.** A client named "Ross & Sons" otherwise
   breaks the page.
2. **Fail loudly on any unresolved `<<` or `[[`** before the PDF is rendered.
   A letter that reaches a client with `<<ClientFullName>>` still in it is the
   one bug that costs a client.
3. **Strip the `.f` class and the `.cond` markers** (and the `tr.mark` marker rows) on the client-facing render.
   They exist so an unfilled proof is obvious; a real letter shows no field
   chrome at all.
4. PDF at Letter, 100%, no browser headers or footers. The footer block repeats
   on every printed page on its own — nothing needs positioning by hand.
5. Name output for a human: `SAT-C Engagement Letter — Reyes — 2026.pdf`. It
   sits in a client's downloads folder for years.

**Placeholders needing a human** are written as `[CONFIRM: …]` in oxblood mono,
so they are impossible to miss in a proof and impossible to ship by accident.

**Screen-only blocks** (`.ref`) are `@media print` hidden. They document the
template for whoever is wiring it and never reach a client.

`doc-page.js` here is a copy of the one a folder up, because these templates
load it relatively. Don't edit either copy.

---

## The opening package

Three documents, one data record, one call: **engagement letter + fee estimate +
onboarding letter**. `EngagementRef`, `LetterDate`, `PeriodLabel` and the client
address block are shared by all three — generate them together and they cannot
disagree. The invoice joins the same `EngagementRef` later; one engagement has
many invoices, so `InvoiceNumber` is its own sequence.

## Still to build

**Nothing on the original list.** All four — the delivery letter, the business
return engagement letter, the extension notice and the disengagement letter —
are built, paired, registered in `client-documents/registry/fields.yaml`, and
covered by tests that merge each one from the example payload in its own field
doc.

What would earn its keep next, in rough order:

- **Statement of account** — an aging balance across several invoices. The
  invoice's field doc says in terms that it has no aging table and that overdue
  balances belong in a separate document; this is that document.
- **Notice response engagement letter** — every other letter calls responding
  to a notice "a separate engagement, quoted separately". Nothing yet describes
  that engagement.
- **Amended return engagement letter** — the delivery letter says new work
  starts with a new letter. An amendment is the most likely new work.
- **The bookkeeping interview**, which is a `client-documents/` job rather than
  a template: those fields are registered and nothing asks for them yet.
