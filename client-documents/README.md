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
make install                       # deps + the Chromium PDF engine
make demo                          # lead -> record -> the opening package as PDFs

python cli.py interview --lead lead.json      # the consultation call
python cli.py doctor --engagement 2026-0001   # what THIS client still needs
python cli.py render --engagement 2026-0001 --out out
```

`cli.py` is the entry point:

| | |
|---|---|
| `interview` | runs the consultation from `registry/interview.yaml` — **and creates the engagement** |
| `engagements` | what exists |
| `doctor` | open decisions blocking every render; `--engagement REF` for one client, document by document |
| `from-lead` | a website intake payload → a record skeleton |
| `render` | a record, or `--engagement REF` → client-ready HTML and PDF |
| `demo` | the whole chain, from a fixture, in one command |

### The interview

Thirty questions across seven sections, with branching. It asks what the schema
says to ask, offers the website's answers as **claims to confirm rather than
facts**, and retracts an answer whose question a later change hid — answer
joint, name the spouse, change to single, and the spouse name goes, because left
behind it reaches a document with no signature block for it.

`--answers file.json` replays a saved interview without prompting: how the tests
drive it, and how you resume one you abandoned. Answers are keyed by question
id, so a schema change cannot silently shift them onto the wrong questions.

Two options are marked **HARD NO** in the schema. Ticking one refuses to create
the engagement; `--override-hard-no` exists for when it is genuinely a judgement
call rather than the list being wrong.

### The engagement

The interview's output *is* an engagement. `EngagementRef` is allocated
sequentially as `YYYY-NNNN`, never reused, validated at the door — it is
byte-compared across every document, so a malformed one is refused rather than
discovered on a client's letter.

One engagement is one folder: `engagements/2026-0001/record.json` holds the
merge fields, `interview.json` holds every answer including the internal ones —
the red flags, the decision, the notes, the billable counts. The record is
lossy on purpose; those are why the engagement was taken on, and they belong
with it rather than in it.

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

## What comes next, and why in this order

Three things stand between this and the practice running on it. They are **not
three independent gaps** — they are one chain, and the order is forced:

```
   interview  ──▶  engagement  ──▶  delivery (Encyro)
   asks the        exists, has      has something to
   questions       a ref, and       send, and someone
                   persists         to send it to
```

**1 · The interview — DONE.** `cli.py interview` runs the schema. See above.

**2 · The engagement — DONE.** The interview creates one. Refs are allocated and
persisted; see above.

**The fee schedule — BUILT, UNPRICED.** `registry/fee-schedule.yaml` turns the
interview's counts into the estimate's line items and total. Every amount in it
is `[CONFIRM:` until the firm sets one, because §9 of the authoring contract
says fee figures are a human's to set and an invented one is worse than a blank.

**An unpriced item does not become zero.** The `[CONFIRM:` is carried through to
the line and then to the total, and the estimate refuses to render — quoting a
client $0 for a service is worse than quoting nothing. `samples/fee-schedule-example.yaml`
holds fictional numbers so the mechanism can be seen working:
`--fee-schedule` prices against it.

To price the firm, either replace the placeholders in
`registry/fee-schedule.yaml` by hand, or answer the question in a unit you
actually know:

```
python cli.py price                     # asks; blank leaves an item unpriced
python cli.py price --list              # what it will ask about
python cli.py price --hours mine.yaml --round-to 25 --write registry/fee-schedule.yaml
```

Nobody knows their own prices in the abstract; they know their own work. So
`price` asks how long each item takes and multiplies by an hourly rate, both of
which are the firm's. It supplies neither, and an item left blank stays a
`[CONFIRM:` rather than becoming a guess — a half-finished sitting produces a
half-priced schedule that still refuses to render.

Rounding is off by default. `$437.50` is what 2.5 hours at $175 costs;
`$450.00` is a pricing policy, and `--round-to 25` is how you say you have one.

The write is surgical: amounts are swapped on the lines they occupy, so the
file keeps the comments that explain what each one means.

## Two front doors, one engine

Every process here is doable by a human and replicable by automation, under the
same controls. That is a constraint on the architecture, not a feature list.

```
make web            # the browser: http://127.0.0.1:5051
python cli.py ...   # the terminal
```

Both call `intake.finish`, which owns every gate: a HARD NO refuses, a decision
that is not 'yes' declines, pricing runs before the store is touched, and the
record is composed one way. Neither front door may decide anything of its own —
two tests read `cli.py` and `web.py` as source and fail if a rule is written
into either.

The web routes are **content-negotiated**: one handler answers a browser with
HTML and a script with JSON, sharing every line up to rendering. So the API is
not a parallel implementation that can drift — it is the same code path.

```
curl -X POST localhost:5051/interview       -H 'Accept: application/json'
curl       localhost:5051/interview/<draft> -H 'Accept: application/json'
curl -X POST localhost:5051/interview/<draft>/finish -H 'Accept: application/json'
```

A `refused` from that last call is the same refusal the browser shows and the
same exit code the CLI returns.

## Changing the wording

*"i want it to be very straightforward and simple. like i can just click a
template, open a section, edit it"* — the firm, 26 August 2026.

`make web`, then **/templates**. Pick a template, click a section, change a
sentence, save. `**bold**` makes a phrase bold and `<<FieldName>>` is a merge
field; that is the whole markup.

`editor.py` owns the rules, so the browser cannot save something a script
could not:

| It refuses | Because |
|---|---|
| dropping a `<<Field>>` | the document still renders and a real value silently stops printing |
| inventing a `<<Field>>` | the registry does not know it, so the render fails at a client's document |
| typing `[[IF ...]]` or `[CONFIRM:` | that decides whether whole blocks appear — structure, not wording |
| emptying a block | a gap in the document, where deleting it in the file is what was meant |
| a block it cannot rebuild exactly | shown read-only rather than mangled |

A section saves **whole or not at all**: one refused sentence saves none of
them, so nobody has to work out which half landed.

The safety property is the round trip — `to_html(to_text(x))` returns `x` byte
for byte — and `test_editor.py` checks it against every block in all ten
templates. It earned its keep on the first run: it caught that opening a
section and saving it unchanged rewrote three sentences of the delivery
letter, which is how the stylesheet bug behind that surfaced (`<b>` and
`<strong>` were rendering at different weights in the same paragraph).

```
curl localhost:5051/templates -H 'Accept: application/json'
curl -X POST localhost:5051/templates/<file> -H 'Accept: application/json' \
     -d '{"edits": {"s02.1": "The new sentence."}}'
```

**Drafts persist.** The browser writes the sitting to `_drafts/` after every
answer, so closing the laptop mid-call does not lose the consultation — which
the terminal interview cannot survive.

**3 · Delivery.** Encyro. Once an engagement exists and has documents, there is
something to send and someone to send it to. Before that there is not.

Doing these out of order does not work: a delivery step with no engagement to
deliver against is a file uploader, and an engagement with no interview to
create it is a form nobody fills in.

## Design

`docs/prd-interview-and-field-registry.md` at the repo root.
