
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
