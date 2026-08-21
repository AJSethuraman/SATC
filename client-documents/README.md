# client-documents

The machinery that turns a client record into the documents a client receives.

Templates live in `../satc-handoff/04-TEMPLATES` — six of them, each paired with
a `FIELDS` doc. This folder holds the registry that describes them, the
interview schema that supplies the values, and the merge engine that fills them.

```
registry/fields.yaml          every merge field across all six templates
registry/interview.yaml       the pre-engagement interview — THE FILE TO EDIT
registry/firm-settings.yaml   values that are the same on every document
merge.py                      fill a template; refuse to ship a holed one
samples/                      a fictional record that fills the opening package
tests/                        reconciliation + merge behaviour
```

## Run it

```bash
cd client-documents
pip install pytest pyyaml
python -m pytest -q
```

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

Found by reading all six `FIELDS` docs together, and recorded in
`registry/fields.yaml`:

1. **`PeriodLabel` means two different things** — the engagement period on the
   estimate and onboarding letter, the period *billed* on the invoice. Derived
   per document, never stored as one shared value.
2. **`EngagementRef` is `YYYY-NNNN`** and must be byte-identical across letter,
   estimate, onboarding letter and every invoice. The leads workbook generates
   `2026 - 0001`; the template format wins, and a lead's number becomes its
   `EngagementRef` on conversion.
3. **`MaterialsDeadline` prints in three documents.** A firm setting keyed by
   return type and season, never a per-client answer — the organizer's field doc
   calls a mismatch its most likely bug.

## Design

`docs/prd-interview-and-field-registry.md` at the repo root.
