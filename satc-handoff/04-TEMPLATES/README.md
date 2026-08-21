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

## Shared stylesheet

`satc-doc.css` is canonical. A template links it and adds an inline `<style>`
holding **only** rules unique to that document — never a second `:root`, never a
copied-and-tweaked rule. If two templates need the same rule, it belongs in the
shared file.

> The six templates below still inline a copy of this CSS, from before the shared
> file existed. Migrating them is queued and is a no-visual-change job. **New
> work uses the shared file.**

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
   A letter that reaches a client with `<<ClientLetterName>>` still in it is the
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

Each needs the same HTML + FIELDS pair. Roughly in the order they earn their
keep:

- **Tax return delivery letter** — filing instructions, what to sign, what to
  keep, and the "our engagement ends at transmission" line.
- **Business return engagement letter** — 1120-S / 1065, with the K-1 delivery
  timing and the "we do not own your deadline, you do" language.
- **Extension notice** — short, and the one most likely to be sent in volume.
- **Disengagement letter** — the one nobody builds until they urgently need it.
