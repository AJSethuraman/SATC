# PRD: Review Room — file-at-a-time entry UI

**Status:** Draft · **Owner:** SATC owner · **Last updated:** 2026-07-05

> The working surface for engagements: a local web app where the reviewer
> works **one file at a time**, with the sample plan as a live board — and the
> Excel workbook remains the **authoritative deliverable**, generated on
> demand with every formula intact. Decisions reached in conversation
> 2026-07-05: app store = working surface; workbook = source of truth /
> deliverable; Mode B first; local Flask app in the `satc_system` mold.

---

## 1. Problem

Keying a 60-file conformance sample into a wide spreadsheet grid is slow and
error-prone, and it is not how the reviewer thinks — the unit of work is *one
loan file*, worked start to finish. Sampling lives in hand-edited YAML with no
progress view. The owner wants entry, sampling, and reporting to be **nice,
neat, and streamlined**, with working-surface copy that reads like a banker
wrote it (no explanatory parentheticals — those belong in docs).

## 2. Solution

`credit-review ui` launches a localhost-only Flask app (same security posture
as the `satc_system` GUI). Open an engagement (program + overlay), see the
**sample board** — each product's segments with target vs done — and work
files one at a time: a single card per loan with its attributes, its
pass/fail/na checklist (keyboard-first: `p`/`f`/`n`, Enter advances), an
optional note, and live evaluation — computed tests and the FRINGE badge
react as you type. Key the pool buckets on their own card. Track finding
status/owner/due on a findings screen. One button generates the polished
workbook (plain or encrypted) through the existing deterministic builder —
**everything the app holds lands in the workbook; nothing lives only in the
app**.

## 3. Goals & Non-Goals

**Goals**
- One-file-at-a-time entry that is faster than the grid for a 60-file sample.
- Sample plan as a first-class screen: strata, targets, live progress.
- Entries flow losslessly into the generated workbook (grid rows, pool
  panels, tracking lanes) — byte-identical to a fixture-built workbook given
  equal data.
- Live in-form evaluation with **provable parity**: the app's preview of a
  computed test/FRINGE must match what the workbook's formulas produce.
- Same PII bar as Mode B (no person names — enforced at entry) and the same
  at-rest bar as real engagements (store encrypted with the existing
  AES-256-GCM layer).

**Non-Goals / Out of scope**
- **No Mode A forms in v1** — the pattern is proven on Mode B first;
  linesheet forms are the declared fast-follow.
- **No cloud, no accounts, no multi-user** — localhost, single operator.
- **No YAML editing UI** — programs/overlays stay files; the app displays
  knobs, it does not author them (roadmap).
- **No re-ingest UI** — the CLI path stands.
- **No charts/dashboards** — the deliverable's Findings/Products sheets are
  the report; the app shows the same numbers plainly.
- **No hand-edit sync-back** from a generated workbook into the store (the
  re-ingest pass exists for reading filled workbooks; bidirectional sync is
  explicitly deferred).

## 4. User Stories

1. As the reviewer, I launch `credit-review ui`, open an engagement by
   picking its overlay, and land on the sample board.
2. As the reviewer, I see per product each segment's method, stratum, target
   n, and how many files I've completed, so sampling progress is never in my
   head.
3. As the reviewer, I click "next file" (or a segment's add button) and get
   one clean card: loan number, segment, the product's attributes, its
   checklist, a note field.
4. As the reviewer, I work the checklist from the keyboard — `p`/`f`/`n` per
   test, Tab/Enter to advance — and finish a file without touching the mouse.
5. As the reviewer, I see computed tests evaluate as I type (DTI 47% turns
   the DTI test red) and a FRINGE badge appear when a file sits at the box
   edge, so I know what I just recorded.
6. As the reviewer, I key each product's delinquency buckets on a pool card
   and see the URCCP classification preview.
7. As the reviewer, I review findings on one screen — each test's rate vs
   tolerance and flag — and set status/owner/due there, which lands in the
   workbook's tracking lane.
8. As the reviewer, I press "Build workbook" and get the deliverable
   (encrypted by default, plain for synthetic work) written where I choose.
9. As the reviewer, I close the laptop mid-sample and resume later — the
   store persisted (encrypted) with every entry intact.
10. As the owner, I never see a person's name in the app: entry validation
    refuses name-shaped input the same way the samples loader does.
11. As a maintainer, I can prove app-entered data and fixture data produce
    byte-identical workbooks, so the UI can never fork the deliverable.

## 5. Requirements

1. [P0] **Launcher**: `credit-review ui [--port]` starts a localhost-only
   Flask app (default port 5060); non-loopback Host headers rejected
   (`satc_system` H2 pattern); single-threaded.
2. [P0] **Engagement session**: open = choose overlay YAML (program resolved
   from it or `--program`); the app creates/loads the engagement's **store**.
3. [P0] **Store**: one file per engagement under `~/.credit-review/
   engagements/`, AES-256-GCM encrypted via the existing crypto layer (same
   key), holding: overlay/program references, per-product file entries
   (loan_number, segment, attributes, attestations, note), pool buckets, and
   per-(product,test) tracking (status/owner/due/cleared). Plain JSON inside
   the ciphertext; versioned.
4. [P0] **Sample board**: per product — segments with method/stratum/target/
   done, pool-entry status, and overall coverage; the working queue.
5. [P0] **File card**: create/edit one file entry; server-side validation
   identical to the samples loader (segment in plan, attestations pass/fail/
   na, numeric attributes, person-name refusal); keyboard-first entry; a
   free-text note per file (rendered into the grid's note column).
6. [P0] **Live evaluation**: computed test results and the FRINGE badge
   render on the card from the same comparison semantics as the workbook
   formulas; a parity test proves preview == recalc on the demo fixture.
7. [P0] **Pool card** per product (buckets; residential extras) with a
   classification preview.
8. [P0] **Findings screen**: per-(product,test) n/fails/rate/tolerance/flag
   preview + editable status/owner/due/cleared, persisted to the store and
   threaded into the built workbook's tracking lane.
9. [P0] **Build**: generate the workbook from the store through
   `build_engagement_workbook` — no parallel builder. Given identical data,
   the store-built workbook is **byte-identical** to the fixture-built one.
   Output plain or encrypted.
10. [P0] **Copy discipline**: every label in the UI comes from the program/
    overlay configs (same strings as the sheets); no explanatory
    parentheticals; no framework component look — the workbook's design
    system (ink/red/cream), hand-rolled CSS.
11. [P1] **File note column** added to the Mode B grid (note lands beside the
    file's row; excluded from mart/exports).
12. [P1] **Demo mode**: `credit-review ui --demo` opens the synthetic retail
    engagement read-write against a scratch store, for trying the flow.
13. [P2] Mode A file-at-a-time forms (declared fast-follow, not in v1).

## 6. Implementation Decisions

- **Placement**: inside `credit-review-os` (`src/credit_review/app/` +
  templates/static), launched from the existing CLI — it is a feature of this
  project, not a new top-level project.
- **Store shape**: dataclass-backed JSON document (versioned `"v": 1`),
  encrypted whole-file on save via `crypto.encrypt_bytes`; loaded fully into
  memory per request cycle (single operator, small data). Loan numbers are
  the most sensitive datum present, by Mode B design.
- **One evaluation source**: a small pure module exposes the comparison
  semantics (test breach, fringe banding, URCCP bucket sums) used by BOTH the
  card preview and tests; the workbook's formulas remain the authoritative
  computation in the deliverable, and the parity test pins the two together.
- **Build path**: store → `ProductSample`/tracking structures → existing
  builder. The store is upstream of the builder, never a second builder.
- **No JS framework**: server-rendered pages + a small hand-written script
  for keyboard flow and live evaluation (values POSTed; evaluation logic
  server-side, echoed as JSON).
- **Flask prior art**: `satc_system/src/satc/app` (Host guard, single-thread,
  secret handling, test style in `satc_system/tests/test_app*.py`).

## 7. Testing Decisions

- **Seam 1 (primary): the Flask test client** — open demo engagement, POST a
  file entry (valid + each invalid class), read the board state, POST pool +
  tracking, trigger build; assert store contents and responses.
  (Prior art: `satc_system/tests/test_app.py`.)
- **Seam 2: build parity** — enter the demo fixture's data through the store
  API, build, and assert **byte-identical** output vs `build_demo_retail_
  workbook()`; plus preview-vs-recalc parity for computed tests/FRINGE on
  every demo file.
- **Seam 3 (existing): PII + crypto** — store bytes on disk are ciphertext
  (no loan numbers readable), person-name entry refused at the route, 0600
  perms; existing no-PII suite untouched.
- **What a good test proves:** the UI cannot produce a different deliverable
  than the engine, cannot leak plaintext to disk, and cannot accept data the
  samples loader would refuse.

> **PII rules (binding):** unchanged from Mode B — no person names anywhere
> (entry-validated), loan numbers only, store encrypted at rest, exports stay
> product/segment level. The app binds to 127.0.0.1 only.

## 8. Success Metrics

- The demo 10-file auto sample can be entered start-to-finish from the
  keyboard and built to a workbook byte-identical to the fixture build.
- Zero plaintext engagement bytes on disk at any point (store + build-temp
  both verified).
- Preview/recalc parity: 0 discrepancies across the demo fixture.

## 9. Milestones / Rollout

- **M1 (tracer, issue 1):** launcher + encrypted store + open engagement +
  file card (validation, live evaluation, keyboard flow) + build button —
  one product end-to-end, parity-tested.
- **M2 (issue 2):** sample board with segment progress, pool cards, findings
  tracking screen, file-note grid column, demo mode, polish pass, README.

## 10. Risks & Open Questions

- **Risk — dual evaluation drift** (preview vs formulas): held closed by the
  shared-semantics module + parity test; any new computed-test feature must
  extend both or the test fails.
- **Risk — the store becomes a second truth**: held closed by the byte-parity
  test and the no-sync-back non-goal.
- **Open question (yours, non-blocking):** per-file nuance beyond
  pass/fail/na + note — if some tests deserve a per-file severity or a
  structured comment, say so and the card grows a field; the store schema
  already tolerates additive fields.

## 11. Done Criteria

- [ ] R1–R12 met; stories 1–11 satisfied
- [ ] Tests green at all three seams (client, byte-parity + preview parity,
      PII/crypto); existing 108 untouched
- [ ] Verified by running the app and entering the demo sample by hand
      (keyboard-only), then opening the built workbook
- [ ] README updated (Review Room section); BACKLOG logs Mode A forms +
      YAML-editing UI + sync-back as deferred roadmap items
