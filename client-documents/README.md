# client-documents

The machinery that turns a client record into the documents a client receives.

Templates live in `../satc-handoff/04-TEMPLATES` — **ten** of them, each paired
with a `FIELDS` doc. This folder holds the registry that describes them, the
interview schema that supplies the values, and the merge engine that fills them.

```
registry/fields.yaml          every merge field across all ten templates
registry/interview.yaml       the pre-engagement interview — THE FILE TO EDIT
registry/firm-settings.yaml   values that are the same on every document
merge.py                      fill a template; refuse to ship a holed one
samples/                      fictional records: the opening package, and one per
                              later document, lifted from its own FIELDS doc
tests/                        reconciliation + merge behaviour
```

## Run it

```bash
cd client-documents
make install          # deps + the Chromium PDF engine
make doctor           # what is still blocking a real render
make demo             # lead -> record -> the opening package as PDFs
make test
```

`cli.py` is the entry point. Four commands:

| | |
|---|---|
| `doctor` | every open decision blocking a real render, and the question behind it |
| `from-lead` | a website intake payload → a record skeleton, with what the interview still owes marked rather than guessed |
| `render` | a record → client-ready HTML, and PDF where an engine is installed |
| `demo` | the whole chain, from a fixture, in one command |

```bash
python cli.py render samples/tax-opening-package.json --out out
python cli.py render record.json --docs invoice delivery-letter --out out
python cli.py render record.json --draft --out out     # see below
```

A record needs `_season` (the tax year being filed — it selects the materials
deadline) and optionally `_return_type`. Firm settings fill in behind it; the
record wins where it sets something, because a per-engagement override is
legitimate and ignoring it silently would be worse.

### Two modes, and the difference is the point

**Real** (default) writes nothing at all when a document would be holed. Not a
warning, not a partial file — an unresolved field or a surviving `[CONFIRM]`
raises and the render is abandoned. A refusal that still left a file on disk
would be worse than no refusal, because somebody would send the file.

**Draft** (`--draft`) renders anyway, so the pipeline can be exercised before
the firm's decisions are made. Every page is stamped, every open decision is
marked in oxblood where it would print, and the filename says DRAFT. The stamp
goes in `doc-page`'s running header slot rather than a fixed banner, because a
banner on page one leaves page two byte-identical to the real letter — and page
two is what gets handed across a desk on its own.

### The PDF engine

Chromium is primary. The templates are flexbox and were designed and proofed in
a browser; WeasyPrint's flex support is partial, so it renders the SAT-C
wordmark as overlapping letters and collides clause numerals with their
headings. The document is correct either way — it just does not look like the
brand. `doctor` reports which engine you have.

## What the tests actually protect

**The templates, the registry and the interview cannot drift apart.** A template
gaining a field fails the build here rather than failing at a client. So does an
interview question that supplies nothing, and a registry entry claiming a
template that no longer uses it.

**A document is complete or it does not exist.** `merge.render()` raises rather
than returning a document with a hole in it — the templates' own field docs call
an unresolved `<<ClientLetterName>>` reaching a client the one bug that actually
costs you a client, so it is a hard failure, not a warning.

**Undecided things cannot escape.** `firm-settings.yaml` carries
`[CONFIRM: ...]` placeholders where a decision has not been made. The engine
treats a surviving `[CONFIRM:` exactly like an unresolved field. The machinery
therefore works today, with the decisions still open, and cannot quietly ship
one.

**No field can hold a TIN.** A denylist over field names and question text, plus
a check that no sample contains anything shaped like an SSN or EIN. The record
lives in OneDrive; identifiers belong in Drake and in `satc_system`'s encrypted
vault, per `CLAUDE.md`.

## What is deliberately not here

- **PDF rendering.** The engine produces client-ready HTML. Printing is the
  caller's job; the templates already specify Letter, 100%, no browser chrome.
- **Fee calculation.** The interview *counts* billable items. Amounts are typed
  until a fee schedule exists — `feeds: LineItems` marks the questions that will
  drive it.
- **The bookkeeping interview.** Those fields are registered; nothing asks them
  yet. Scope here is tax return preparation.

## Three template mismatches, resolved rather than inherited

Found by reading the `FIELDS` docs together, and recorded in
`registry/fields.yaml`:

1. **`PeriodLabel` means two different things** — the engagement period on the
   estimate and onboarding letter, the period *billed* on the invoice. Derived
   per document, never stored as one shared value.
2. **`EngagementRef` is `YYYY-NNNN`** and must be byte-identical across letter,
   estimate, onboarding letter and every invoice. The leads workbook generates
   `2026 - 0001`; the template format wins, and a lead's number becomes its
   `EngagementRef` on conversion.
3. **`MaterialsDeadline` prints in five documents.** A firm setting keyed by
   return type and season, never a per-client answer — the organizer's field doc
   calls a mismatch its most likely bug. Two later documents widen the key
   rather than the value: the **business return letter** needs the entity
   deadline, which is earlier than the individual one, and the **extension
   notice** needs the *extension-season* deadline rather than the original
   one. Same field name, three different settings behind it.

## What the merge engine also refuses to ship

`SATC Engagement Letter - Business Return.html` carries **one open
`[CONFIRM]`**, on officer compensation under an S election. `test_merge.py`
asserts that the letter raises rather than rendering while it is there, and
separately that everything *else* in the letter resolves — so the marker cannot
be forgotten, and the test goes green the moment a human answers it.

## Design

`docs/prd-interview-and-field-registry.md` at the repo root.
