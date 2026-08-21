
---

## Batch 3 — the six templates onto the shared stylesheet

**Branch** `claude/satc-handoff-batches-2-4-n2qrl9-b3-shared-stylesheet`
**Files** the six templates, `satc-doc.css`, `04-TEMPLATES/README.md`,
`00-START-HERE/AUTHORING-CONTRACT.md`.

### Method

Not by eye. A small CSS parser normalised every declaration in each template's
inline `<style>` and in `satc-doc.css`, then classified every rule as
**identical**, **divergent** (same selector, different declarations) or
**unique** (selector absent from the shared file). Then each template was
rendered at 1000px full-page **before and after** and the two images
pixel-diffed.

### The result

| Template | Identical | Divergent | Unique |
|---|---|---|---|
| Engagement Letter — Tax Preparation | 82 | 0 | 0 |
| Engagement Letter — Bookkeeping | 82 | 0 | 0 |
| Organizer Cover Letter | 82 | 0 | 0 |
| Onboarding Letter | 92 | 0 | 0 |
| Fee Estimate | 74 | **2** | 0 |
| Invoice | 87 | **2** | 0 |

**Not one rule in any of the six was unique.** All six now link `satc-doc.css`
and carry **no inline `<style>` block at all**. The two divergences were the
same two rules in both ledger documents, and both were resolved rather than
copied — copying a shared rule to tweak it is what §2.4 of the contract forbids.

1. **`.signoff`** — shared `margin-top:16pt`, ledger documents `20pt`. A ledger
   sign-off follows a `.notes` block rather than the `.sp` signature gap, so the
   difference is real. Two documents needing the same rule is the definition of
   one that belongs in the shared file, so **`.doc .signoff{margin-top:20pt}`
   was promoted into `satc-doc.css`**, scoped to the wrapper the ledger
   documents already use. Neither template needs an override now.
2. **`.cond`** — shared is block-level with vertical margin, which is right for
   a letter wrapping a whole numbered section. Every conditional marker in the
   ledger documents sits inside a `<td>` or mid-sentence in an `<li>`, where
   block display would break the line and inflate the row. **`satc-doc.css`
   already carried `.cond.inline` for exactly this**, so the eight markers use
   the class instead of the templates redeclaring the rule.

### The pixel diff — and what it caught

Four of the six changed. Every change is the migration **fixing something**, and
each was traced to a specific rule the old inline copy was missing.

- **Fee Estimate: 0 pixels.** The `.signoff` promotion and the `.cond.inline`
  class reproduce the old rendering exactly.
- **Bookkeeping, Tax Preparation, Onboarding, Organizer: one reflowed footer
  line each.** Cause: these four **lacked `.foot .f{font-size:7pt}`**, which
  only the Fee Estimate and the Invoice had. Without it the footer's merge
  fields inherit `.f{font-size:0.92em}` of 7pt body — **6.44pt**, under the 7pt
  floor §8 of the contract sets. Linking the shared file lifts them to 7pt,
  which widens the reference column slightly and moves one word of the legal
  sentence onto the next line. **This is the migration repairing a §8 violation
  in four templates**, not a regression. Only merge chrome is affected, and
  merge chrome is stripped on the client render — but a proof was showing type
  below the floor.
- **Invoice: the screen-only `.ref` table reflowed.** Cause: the Invoice
  **lacked `.ref .opt`**, the shared rule that styles the "If CreditsApplied" /
  "If EstimateReference" optionality markers and gives them `white-space:nowrap`.
  With it, the table's column widths settle differently. `.ref` is
  `@media print` hidden and never reaches a client; this is documentation
  rendering more like the other five, which is the point of the exercise.

### Verified

- Every template renders with **zero console errors** before and after.
- `grep`: all six link `satc-doc.css`; **zero** `<style>` blocks; **zero**
  `:root` declarations; **zero** gold; **zero** `--mute` on text.
- `client-documents` — **26 pass**. The registry reconciliation still matches
  the templates, so no field was disturbed.

### Contradictions found

1. **`<<TaxYear>>` is still alive, and the contract forbids it.** §4 of
   `AUTHORING-CONTRACT.md` says in terms: *"`PeriodLabel` is self-describing …
   **Never add `TaxYear` back**."* But `SATC Engagement Letter - Tax
   Preparation.html` uses it **three times**, `SATC Organizer Cover Letter.html`
   uses it **three times**, both FIELDS docs document it, and
   `client-documents/registry/fields.yaml` faithfully registers it because the
   templates do. **Six live uses of a field the contract says must not exist.**
   Not fixed here: renaming it touches two templates, two field docs, the
   registry and the test suite at once, which is a content change and not a
   stylesheet migration. It is the single most concrete piece of drift in the
   template set and it should be closed deliberately, in its own commit.
   [CONFIRM: does `PeriodLabel` replace `TaxYear` in the tax letter and the
   organizer, or does the contract's rule get relaxed?]
2. **§8's assurance grep flags four templates, and all of them are clean.** The
   hits are explicit negations ("We will not audit or otherwise verify them",
   "We do not perform audits, reviews, or any assurance engagement", "We have
   not audited or reviewed these financial statements") plus two ordinary
   English uses: "invites the client to audit your time" in the Invoice's
   screen-only `.ref`, and "outside the system's **audit trail**" in the
   client-facing Onboarding Letter. The mechanical grep cannot tell these apart
   and will flag them on every future run. Worth either a documented allowlist
   or a note in §8 that the grep needs a human to read the hits.
3. **`.foot .f` and `.ref .opt` were missing from some templates and present in
   others** — the divergence the shared file exists to end, and evidence that
   "accidentally divergent" was the common case rather than the exception. Zero
   rules across all six were genuinely unique.

---

## Batch 4 — the four remaining templates

**Branch** `claude/satc-handoff-batches-2-4-n2qrl9-b4-new-templates`, **stacked on
the Batch 3 branch** because the new templates link `satc-doc.css` and there is
no honest way to build them against a stylesheet that had not been adopted yet.

**Batch 5 is superseded**, per the operator. The field registry exists at
`client-documents/registry/fields.yaml` with a working merge engine, so the new
templates were registered there and the tests were kept green — that is the
verification, in place of the spec the brief asked for.

### Built

Four HTML + FIELDS pairs, in the brief's priority order.

| Template | Fields | Notes |
|---|---|---|
| Tax return delivery letter | 15 + 2 lists + 3 flags | Closes the engagement at transmission. Carries no fee and no amount payable to the firm — the invoice owns those. |
| Extension notice | 17 + 2 lists + 2 flags | The shortest and highest-volume document. Both conditionals sit *inside* section 02, so nothing renumbers. |
| Business return engagement letter | 21 + 3 flags, no lists | The entity twin of the tax letter, worded identically wherever it can be. Section 02 is the K-1 timing clause. **One open `[CONFIRM]`.** |
| Disengagement letter | 17 + 2 lists + 4 flags | **States no reason, deliberately.** Records dates and facts; returns records regardless of the balance. |

Counts were **taken from the parser, not estimated** — §8 says count, don't
estimate, and the first draft of the delivery letter's `.ref` said 14 when the
parser said 15.

### Also done

- **Ten README rows**, replacing the "still to build" list with what would
  actually earn its keep next: a statement of account (which the invoice's own
  field doc says should exist), a notice-response engagement letter (which
  every other letter refers to and nothing describes), and an amended-return
  letter.
- **`client-documents/` registry rewritten from the templates**, not by hand:
  every `templates:` list recomputed from what the templates contain, existing
  sources and notes preserved verbatim, and 10 fields / 12 flags / 6 lists
  added. Three new source values — `delivery`, `extension`, `disengagement` —
  alongside the existing `invoice`, on the same principle: values that arise at
  a particular moment in an engagement rather than at interview time.
- **`merge.tokens_in` gained `list_items`**, per-list sub-fields. The old
  template-wide union could not distinguish the delivery letter's two lists.

### Verified

- **`client-documents`: 38 pass**, up from 26. Twelve new tests.
- **Each new template merges from the example payload in its own FIELDS doc.**
  §7 calls the payload the acceptance test — *"if it does not render a clean
  document, the pair is not done"* — so the samples are **lifted out of the
  FIELDS docs by a script**, and documentation and test cannot drift apart.
- **The business letter is tested to REFUSE to render** while its `[CONFIRM]`
  is open, and separately tested that everything else in it resolves — so the
  test cannot pass on a letter riddled with holes, and it goes green the moment
  a human answers the question.
- **Every inverse flag pair is tested in both states**, asserting exactly one
  branch renders. Five pairs.
- The two new reconciliation tests were **confirmed red-capable** by breaking
  the registry on purpose and watching them fail.
- All four render with **zero console errors**; printed to Letter through
  Chromium, **the footer repeats on every page**, no clipping, no orphaned
  headings.
- Mechanical greps: all four link `satc-doc.css`; **zero** inline `<style>`,
  `:root`, gold, `--mute`, and nothing below 7pt. Oxblood appears in exactly
  the four permitted ways — clause numerals, merge chrome, conditional markers,
  and the `[CONFIRM]` marker.
- Banned assurance vocabulary: every hit is an **explicit negation** ("We will
  not audit or otherwise verify it", "We do not perform audits, reviews, or any
  assurance engagement", "It is not an opinion about your records") or the
  referral the individual letter already uses.

### [CONFIRM] left

**One, and it is genuinely blocked on a human.**

> `SATC Engagement Letter - Business Return.html`, section 03:
> **[CONFIRM: does the firm want to say more here about officer compensation,
> or is scope exclusion the whole of it? This is a substantive tax position and
> the wording is not an agent's to write.]**

The scope exclusion itself is written — the firm reports the compensation the
entity actually paid, and setting or reviewing it is out of scope unless
section 01 lists it. Whether the firm wants to say anything *further* about
reasonable compensation under an S election is a tax and risk decision. §9 of
the contract is explicit that invented legal wording is worse than a blank, and
this is the clearest case of it in the batch.

The letter **cannot reach a client** while the marker is there, and a test says
so.

### Deliberate omissions worth knowing about

- **The disengagement letter states no reason, in either branch.** A reason is
  a statement of fact the firm must stand behind, written at the worst possible
  moment, into a file the firm no longer controls. The client already knows;
  every other reader is someone the firm did not choose. Its field doc says
  "do not add a reason field to this template" so the next author does not.
- **No statutory dates anywhere in the prose.** Every date is a merge field. A
  hardcoded March 15 is wrong for a fiscal-year filer and wrong again the next
  time Congress moves something.
- **No `TaxYear`.** The contract forbids it and the new templates use
  `PeriodLabel` throughout. The six pre-existing uses are unchanged and still
  reported below.

### Contradictions found

1. **`MaterialsDeadline` needs a wider key than `firm-settings.yaml` gives it.**
   The settings file keys it by season and return type. Two of the new
   documents need a third dimension: the business letter needs the **entity**
   deadline, which is earlier than the individual one, and the extension notice
   needs the **extension-season** deadline rather than the original one. Same
   field name, three different settings behind it. `registry/fields.yaml`
   already calls a `MaterialsDeadline` mismatch the organizer's most likely
   bug; this is two more ways for it to happen.
2. **The registry had no per-list sub-field check.** `test_registry` verified
   which templates use a field but nothing verified a list's `Item.*` shape, so
   a renamed sub-field would have passed silently. Invisible while every
   template had one list; the delivery letter has two with different shapes.
   Fixed, and the fix is red-capable.
3. **§8's "footer repeats on page 2" is checkable, and nothing was checking
   it.** The contract describes it as a manual print-preview with filler text.
   All ten templates already satisfy it through `doc-page`'s footer slot, and
   Chromium's print-to-PDF confirms it mechanically in about a second. It
   belongs in the test suite rather than in a checklist a human is asked to
   remember.
4. **`SignerName` / `SignerTitle` were exempted from the interview check as
   "bookkeeping-only".** They are now used by the business return letter too.
   The exemption still holds — both are entity signatory fields and the tax
   interview covers individual returns — but the comment explaining it was
   wrong, and is updated.


---

# Summary

## What shipped

| PR | Batch | Branch |
|---|---|---|
| #138 | 1 (remainder) — website disclosures | `…-b1-website-disclosures` |
| #139 | 2 — Invoicer restyle | `…-b2-invoicer-restyle` |
| #140 | 3 — six templates onto the shared stylesheet | `…-b3-shared-stylesheet` |
| #141 | 4 — the four remaining templates | `…-b4-new-templates` |

All four are **draft**. Nothing was pushed to `main`, which publishes to
`satcllp.com` through Cloudflare Pages.

**#141 is based on #140**, not on `main` — the new templates link
`satc-doc.css`, and building them against a stylesheet that had not been
adopted yet would have been dishonest. Merge #140 first and GitHub retargets
#141 automatically. #138 and #139 are independent of both and of each other.

## What was skipped, and why

- **Batch 1, everything except the disclosures.** Already merged (#117, #124),
  per the status correction at the top of the brief. Redoing it was the failure
  mode the correction exists to prevent.
- **Batch 5, the merge-engine spec.** Superseded by instruction: the engine and
  the registry exist. Batch 4's templates were registered and tested against
  them instead, which is a stronger form of the same guarantee — a spec cannot
  fail, and the tests can.
- **The `<<TaxYear>>` rename.** Found, reported, not done. It touches two
  templates, two field docs, the registry and the test suite at once and is a
  content change rather than anything in these four batches. See below.
- **The `website/index.html` marketing copy** flagged in Batch 1. The brief
  scoped Batch 1 to the disclosures and those sentences are a human's to write.

## Every [CONFIRM] left behind

Seven, across four documents. None is a gap that could have been filled by
reading harder.

| # | Where | The question |
|---|---|---|
| 1 | `website/index.html`, footer | **Accountancy Board of Ohio** — is firm registration required, and what may the firm call itself? The placeholder ships until this is answered. |
| 2 | `website/index.html`, intake | Is **"within one business day"** a promise to make in writing? If yes it belongs in three places at one value. |
| 3 | `website/index.html`, intake | `privacy.html` discloses Formspree and its 30-day copy but **not the leads workbook**. |
| 4 | `invoice-generator/`, run log | The invoice ledger keeps **Qty and Rate** columns, which `SATC Invoice.html` says not to have. Data-model question, not a styling one. |
| 5 | `invoice-generator/`, run log | **No billing-contact field** exists, so the pay strip is two-up instead of three. |
| 6 | `satc-handoff/04-TEMPLATES`, run log | Does **`PeriodLabel` replace `TaxYear`**, or does the contract's rule get relaxed? |
| 7 | `SATC Engagement Letter - Business Return.html` §03 | **Officer compensation** under an S election — is the scope exclusion the whole of it? |

Number 7 is the only one inside a client-facing document, and the merge engine
refuses to render that letter while it is there.

**Number 1 is still the highest-leverage unblock in the project**, exactly as
the brief said. It is a fifteen-minute phone call and it settles the firm's
self-description on every surface.

## The contradictions, ranked by what they cost

The brief says these are the most valuable output of an unattended run. In
order of how much a reader should care:

1. **Two specs disagree about how a credit prints, on the same document.**
   `FIELDS - Invoice.md` says a real minus and **never** parentheses.
   `SATC Figures and Tables.html` says parentheses and **never** a minus — and
   uses an invoice as its worked example. Parentheses were used, because the
   authoring contract defers figures to that collateral, because it claims
   these templates by name, and because Batch 2's instructions say so. **One of
   the two documents is wrong and it looks like the FIELDS doc.**
2. **`<<TaxYear>>` is alive in six places** — three uses in the tax engagement
   letter, three in the organizer, plus both field docs and the registry —
   while §4 of the contract says *"Never add `TaxYear` back."*
3. **`website/index.html:826` promises "assurance work — coming soon"** on the
   same page as a new footer line saying the firm performs no attest services,
   and it is exactly the self-description blocked on the Accountancy Board
   question. Two words, delete them.
4. **`privacy.html` does not mention the leads workbook.** Accurate but
   incomplete now that every submission is filed as a durable OneDrive row.
5. **`MaterialsDeadline` needs a wider key than the settings file gives it** —
   entity vs individual, original season vs extension season. Same field name,
   three settings behind it, and the registry already calls a mismatch the
   organizer's most likely bug.
6. **Four templates were rendering footer merge fields at 6.44pt**, under §8's
   own 7pt floor, because they lacked `.foot .f`. Fixed by the migration.
7. **`padding-right: 1ch`, prescribed by the figures collateral, cannot ship to
   both PDF engines** — xhtml2pdf raises on the unit.
8. **The brief's description of the Invoicer PDF as "on the old warm palette"
   was wrong.** It was on the Invoicer product's own blue design system. The
   finding was right; the description of it was not.
9. **§8's assurance grep flags clean documents** — negations, a CV line, and
   the words "audit trail" — and always will. It needs a human to read the
   hits, and §8 could say so.
10. **The contract's `--ink-2` guidance assumes a light ground.** The website
    footer is navy, where that token is unreadable.
11. **Path casing.** Every document refers to `SATC-HANDOFF/`; the directory is
    `satc-handoff/`.

## What a human should do next

1. **Call the Accountancy Board of Ohio.** Unchanged from the brief, and still
   the one thing no agent can do.
2. **Decide the parentheses-vs-minus question** before #139 merges. It is the
   only finding here that changes a document a client already reads.
3. **Answer the officer-compensation `[CONFIRM]`**, which unblocks the business
   return letter.
4. **Delete two words from `index.html:826`.**
5. **Merge #140 before #141**, and #138 and #139 whenever.
