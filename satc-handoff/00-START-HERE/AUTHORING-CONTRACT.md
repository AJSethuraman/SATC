# SAT-C — Authoring Contract

**How to make a new SAT-C document so it is indistinguishable from the ones that
already exist.** Written for an agent working unattended. Follow it literally.

`../01-WEBSITE/SATC-STYLE-SPEC.md` governs the **website**. This file governs **documents** —
anything that renders on paper or as a PDF a client receives.

---

## 0 · The one-paragraph version

Copy `../04-TEMPLATES/_SKELETON.html`. Link `satc-doc.css`; add no tokens and no
duplicated rules. Write the content in the house voice. Add the screen-only
`.ref` block. Write the matching `FIELDS - <Name>.md`. Add both to
`templates/README.md`. Run the self-check at the bottom of this file. If a rule
here and a nice idea disagree, the rule wins — consistency across the set is
worth more than any single document being cleverer.

---

## 1 · Files, and the pairing rule

Every client-facing template is **a pair**:

```
04-TEMPLATES/SATC <Document Name>.html
04-TEMPLATES/FIELDS - <Document Name>.md
```

Same name, same commit, no exceptions. An HTML template with no field doc is
unwireable; a field doc with no template is fiction.

Collateral that never varies (business cards, letterhead specimen, the mark
spec) lives in `../02-BRAND/` or `../03-COLLATERAL/` and has no field doc.

---

## 2 · The stylesheet contract

`04-TEMPLATES/satc-doc.css` is canonical. A new template:

1. Links it — `<link rel="stylesheet" href="satc-doc.css"/>` — after the fonts.
2. Adds an inline `<style>` holding **only rules unique to that document**.
3. **Never redeclares `:root`.** If a colour is missing, it is missing on
   purpose; use one that exists.
4. **Never copies a rule out of `satc-doc.css` to tweak it.** If two documents
   need the rule, promote it into the shared file. If one document needs it
   different, ask whether the difference is actually justified — usually it is
   not.

> **All six existing templates have been migrated** and now carry no inline CSS
> at all. Every template in the folder links the shared file, so an inline
> `<style>` block in a new template is a claim that needs justifying, not a
> default. **New work uses the shared file.**

### Tokens — the whole print palette

`--navy #132437` · `--oxblood #6A2833` · `--ink #242C36` · `--ink-2 #4A5360` ·
`--mute #82817C` · `--hairline #D8D7D1` · `--hairline-2 #E6E5E0`

Three hard rules carried over from the brand spec:

- **No gold in print.** Gold hairlines blow out on toner. Print uses navy 0.5pt.
- **`--mute` is not a text colour** — 3.6:1. Bullets and rules only. Small type
  is `--ink-2`.
- **Oxblood is scarce and means one thing.** In documents that means: clause
  numerals, merge-field chrome, credit amounts, and the `[CONFIRM]` marker.
  Nothing else. Roughly navy 88% / oxblood 9% / everything else 3%.

### Type

IBM Plex Sans for everything; IBM Plex Mono for eyebrows, micro-labels, clause
numerals, reference codes, and **all figures**. Never mono for body copy.
Never a serif — Plex Serif is in the brand but unused across the whole system,
and a document is not the place to introduce it.

Body copy is 10pt / 1.5. **Nothing a client reads goes below 7pt**, and 7pt is
only for the legal footer.

---

## 3 · The component vocabulary

Build from these. Reaching for something not on this list is the signal to stop
and ask whether the document really needs a new component or whether it needs
the existing one used properly.

| Class | What it is | Where it's used |
|---|---|---|
| `.mast` + `.rule` | Masthead: wordmark left, contact block right, navy rule under | Page 1 of every document |
| `.meta-line` | Date left, engagement ref right | Letters |
| `.recipient` | Address block | Letters |
| `.subject` | One-line subject, ruled under | Letters |
| `.body` > `.sec` | Numbered clause with a ruled heading | Letters |
| `.callout` | Navy left-border block — one idea a client must not miss | Sparingly. Two per document is already too many |
| `.doctitle` + `.smeta` | Big title left, key/value meta table right | Estimate, invoice, statement |
| `.prepared` | "Prepared for" / "Billed to" party block | Ledger documents |
| `.led` | The ledger table — `tr.sub`, `tr.credit`, `tr.tot`, `tr.mark` | Estimate, invoice, statement |
| `.duebox` | Amount-due emphasis panel | Invoice |
| `.pay` | Three-up detail strip | Invoice |
| `.notes` | Ruled-heading list of qualifications | Ledger documents |
| `.req-list` | Checkbox action list | Onboarding, organizer |
| `.dateline` | Rule-bounded date + owner strip | Onboarding |
| `.exec` / `.sigrow` / `.accept` | Signature apparatus | Engagement letters only |
| `.signoff` | Name + title sign-off | Everything |
| `.foot` | Repeating legal footer | Everything |
| `.ref` | Screen-only documentation | Everything |

### Figures

Governed by `../03-COLLATERAL/SATC Figures and Tables.html`, not by this file. In short:
tabular numerals, right-aligned, mono, total ruled above and double-ruled below.
**One formatter produces every money string in the system** — templates receive
pre-formatted strings and never do arithmetic in markup.

---

## 4 · Merge syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block, or an inline run |
| `[[EACH List]]` … `[[END EACH]]` | Repeats what is between them |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

Fields are wrapped in `<span class="f">` so an unfilled proof is obvious.
Markers are wrapped in `<span class="cond">`. Both are stripped on the
client-facing render, along with `tr.mark` rows.

### Naming

PascalCase, no spaces, no underscores. **A field that means the same thing in
two templates carries the same name in both** — this is the rule the whole set
depends on. Before inventing a field name, grep the existing FIELDS docs:

```bash
grep -h '^| `<<' SATC-HANDOFF/04-TEMPLATES/FIELDS*.md | sort -u
```

Established names, do not fork them:

`EngagementRef` `LetterDate` `PeriodLabel` `ClientFullName` `ClientLetterName`
`ClientAddress1` `ClientCity` `ClientState` `ClientZip` `ClientEmail`
`PreparerName` `PreparerTitle` `PreparerEmail` `PreparerPhone`
`MaterialsDeadline` `Item.Service` `Item.Detail` `Item.Amount`

`EngagementRef` is the join key across every document. `PeriodLabel` is
**self-describing** — "2026 tax year", "Monthly, from July 2027" — so one field
serves tax and bookkeeping alike. Never add `TaxYear` back.

### Conditionals that drop a numbered section

Renumber in code after the merge. A client must never see 03 followed by 05.
State which choice the template assumes, in its FIELDS doc.

---

## 5 · Voice

The documents are the firm's argument for itself. They read as one person
wrote them, and that person is precise, unhedged, and slightly blunt.

**Do**

- Short declarative sentences. One idea each.
- Say the uncomfortable thing plainly: *"Nothing begins until the signed
  engagement letter is back with us."* *"We cannot tell a missing document from
  one that does not exist."*
- Give the reason with the rule. A rule with a reason gets followed.
- Use **bold** for the thing a client must not miss, roughly once per section.
- Address the client as *you*, the firm as *we*.
- Reference other clauses **by name**, never by number — the fees clause is 06
  in the tax letter and 05 in the bookkeeping letter.

**Don't**

- "Please don't hesitate to contact us." Ask for the question outright.
- "We are pleased to…", "Thank you for your business", "As you know".
- Hedges: *generally, typically, in most cases* — unless the hedge is the fact.
- Exclamation marks, em-dash pile-ups, rhetorical questions, emoji.
- Restate scope or fees in a document that isn't the one that owns them.
- **Any of these words, anywhere:** *audit, audited, auditing, assurance,
  opinion, review engagement, attest, examination* — except in an explicit
  negation ("we do not perform audits"). This is a compliance rule, not style.
- Describe the firm as a "CPA firm" or "Certified Public Accountants". The
  approved form is **"led by a licensed CPA"** — a statement about a person.
  See item 1 in `../01-WEBSITE/WEBSITE-DISCLOSURES.md`.

### Every document declares what it is not

Each `.ref` block carries a **"Deliberately not here"** list. This is not
decoration — it is how the set stays disciplined. Writing down that the invoice
has no aging table, and why, is what stops the next author adding one.

---

## 6 · Scope boundaries between documents

A fact lives in exactly one document. Others point at it by name.

| Fact | Owned by |
|---|---|
| Scope of work | The engagement letter |
| Fees, terms, interest | The engagement letter (the estimate quotes, the invoice bills) |
| What the client must send, and by when | The onboarding letter |
| Line-item pricing | The fee estimate |
| Amount payable now | The invoice |
| Filing instructions | The delivery letter |

If a new document wants to restate something from this table, it is the wrong
document.

---

## 7 · The FIELDS doc

Mirror `04-TEMPLATES/FIELDS - Invoice.md`. Required structure:

1. One-line statement of what the template is and when it is sent.
2. The syntax table.
3. Fields **grouped by source record** — shared fields first, document-specific
   second. Columns: Field · Required · Example · Notes.
4. A total line: *N fields + M repeating lists + K flags.*
5. An explicit list of what is **not** a variable.
6. A complete example JSON payload that would render the document correctly.
7. "Deliberately not here."
8. Notes for the software.

The example payload is the acceptance test. If it does not render a clean
document, the pair is not done.

---

## 8 · Self-check before calling a document finished

Run all of it. Mechanical, so no judgement required.

```
[ ] Links satc-doc.css; declares no :root; inline <style> is unique rules only
[ ] Renders with zero console errors
[ ] Prints to Letter with no clipping and no orphaned heading
[ ] Footer repeats on page 2 (add filler text, print-preview, remove it)
[ ] No gold anywhere; no --mute on text; oxblood used ≤ 4 distinct ways
[ ] Nothing below 7pt; body copy 10pt/1.5
[ ] Every <<Field>> in the HTML appears in the FIELDS doc, and vice versa
[ ] Every field name matches its use in the other templates (grep first)
[ ] The example JSON payload covers every field and every flag, both states
[ ] Banned assurance vocabulary absent (grep -iE 'audit|assurance|attest|opinion|review engagement|examination')
[ ] No [CONFIRM: …] left unless it is genuinely blocked on a human
[ ] .ref block present, @media print hidden, with "Deliberately not here"
[ ] Clause cross-references are by name, not number
[ ] 04-TEMPLATES/README.md row added, with field counts that match the doc
[ ] Field counts in the .ref block and the FIELDS doc agree with each other
```

The last one has been wrong before. Count, don't estimate.

---

## 9 · What needs a human

Stop and leave a `[CONFIRM: …]` marker rather than inventing:

- Any statement about firm registration or how the firm may describe itself.
- Any assurance-adjacent wording, including the financial statement legend.
- Fee figures, rates, retainer amounts, interest rates beyond "the maximum rate
  Ohio law permits".
- Deadlines that are firm policy rather than statutory.
- Anything a client could reasonably read as a guarantee of outcome.

Invented legal wording is worse than a blank. A blank gets filled; an invention
ships.
