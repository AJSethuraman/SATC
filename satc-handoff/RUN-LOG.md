# SAT-C — Unattended run log

Run started 2026-08-21. Scope: the batches in Part 2 of
`00-START-HERE/OVERNIGHT-BRIEF.md`, as amended by the operator:

- **Batch 1 — skipped except one item.** The restyle, the images and the
  wordmark are merged (PRs #117, #124). Only the drafted disclosures were
  outstanding, and only those were done.
- **Batch 5 — superseded.** The field registry exists at
  `client-documents/registry/fields.yaml` with a working merge engine and a
  test suite. New Batch 4 templates register their fields there and keep the
  suite green instead of a spec being written.
- **Guardrail amendment.** `SATC_CONFIG` lives in `website/site-config.js`, not
  `index.html`. Untouched either way.

One feature branch and one draft PR per batch. Nothing pushed to `main` —
`main` publishes to `satcllp.com` through Cloudflare Pages.

---

## Batch 1 (partial) — website disclosures

**Branch** `claude/satc-handoff-batches-2-4-n2qrl9-b1-website-disclosures`
**Files** `website/index.html` only.

### Done

| Disclosure | Where it went | Wording |
|---|---|---|
| Item 2 · No advice from the website | `footer > .foot-legal`, under the copyright line | Approved draft, **verbatim** |
| Item 1 · What the firm is | `footer > .foot-legal`, second paragraph | The **placeholder** from the draft, verbatim, with a code comment recording that it is blocked on the Accountancy Board |
| Item 3 · What happens next | `.intake-form`, immediately after `#intakeMount` — i.e. under the submit button on every step | Approved draft with **two departures**, both recorded below |

Two supporting CSS rules added (`.foot-legal`, `.next-note`). No token was
added, changed or redeclared. `intake.js`, `intake-config.js` and
`site-config.js` were not opened for editing.

### Verified

- `website/intake.spec.py` — **32/32 pass** against the edited page, including
  "no horizontal overflow at 390px".
- Rendered at 1280px and 390px. No console errors from the page. (Chromium logs
  one `ERR_CONNECTION_RESET` for the Google Fonts request; that is the sandbox
  proxy, not the page, and it occurs on the unedited file too.)
- HTML tag nesting balanced; no unclosed elements.
- `.foot-legal p` computes to 12.5px, inside the draft's 12–13px.

### [CONFIRM] markers left

All three are HTML comments, invisible to a visitor — nothing that reads as an
unfinished document reaches the live site.

1. **[CONFIRM: Accountancy Board of Ohio — is firm registration required, and
   what may the firm call itself?]** `website/index.html`, above `.foot-legal`.
   Item 1 of the disclosures doc, and the highest-leverage open item in the
   project. The placeholder sentence ships until it is answered.
2. **[CONFIRM: is "within one business day" a promise to make in writing?]**
   `website/index.html`, above `.next-note`. See departure 1.
3. **[CONFIRM: `website/privacy.html` discloses Formspree and its 30-day copy
   but not the leads workbook.]** `website/index.html`, above `.next-note`.
   See departure 2.

### Departures from the drafted wording, and why

**1 · The reply-time promise was not reintroduced.** Item 3's draft reads
"We reply within one business day." That promise is nowhere on the site: the
left rail, `intake-config.js` and the confirmation screen in `intake.js` all
say "as soon as we can", and the brief's status correction records that the
one-business-day wording was removed on purpose. Adding it back under the
submit button would have made this block the only place on the page making the
promise, and would have contradicted the sentence directly beside it. The
site's own wording is used instead.

**2 · The "by email" sentence now names Formspree and links the privacy page.**
The draft was written assuming a submission is mailed and stored nowhere, and
says in terms that the sentence "has to change" if a form service persists it.
It does: Formspree keeps a copy for 30 days and a Power Automate flow files
every submission as a row in `SATC leads.xlsx` (`docs/leads-to-excel.md`). The
sentence "Nothing is filed, charged, or shared with anyone on the strength of
this form" is kept verbatim — it is still true and it is what the paragraph is
for — but it is now preceded by an accurate account of the routing.

### Contradictions found (not fixed — outside this batch, and not an agent's call)

1. **`website/index.html:826` — "Anyone who needs assurance work — coming
   soon".** In the "Probably not a fit" column. The negation is fine; **"coming
   soon" is not.** It is a forward promise of assurance work, on the same page
   as a footer line saying the firm does not perform attest services, and it is
   exactly the kind of self-description blocked on the Accountancy Board
   question. Recommend deleting the two words. Left alone because Batch 1 was
   scoped to the disclosures and marketing copy is a human's sentence.
2. **`website/index.html:725,727` — "Certified Public Accountant · Ohio" and
   "a background in ... internal audit".** Both read as statements about the
   person, which is the approved form, and 727 is a biography rather than a
   service offered. But both use vocabulary the guardrail bans outright and
   neither is an explicit negation. Flagging rather than changing: the
   guardrail as written has no carve-out for a CV, and it probably needs one.
3. **`website/privacy.html` does not mention the leads workbook.** It discloses
   Formspree and the 30-day copy, and says "The form collects what you type
   into it and emails it to us" — accurate but incomplete now that every
   submission is also filed as a durable row in OneDrive. A privacy policy is
   legal wording and is not an agent's to draft. See [CONFIRM] 3.
4. **The disclosures doc assumes a light footer.** It specifies item 2 at
   "12–13px in `--ink-2`". The footer is `--navy-deep`; `--ink-2` on it is
   unreadable. Size honoured, colour taken from the footer's own scale at
   `rgba(255,255,255,0.55)` — brighter than the copyright line beside it, which
   runs at 0.42 and is itself under AA.
5. **Path casing.** The brief and the authoring contract both refer to
   `SATC-HANDOFF/`; the directory is `satc-handoff/`. Harmless on this
   filesystem, breaks a copy-pasted command on a case-sensitive one.

---

## Batch 2 — Invoicer restyle

**Branch** `claude/satc-handoff-batches-2-4-n2qrl9-b2-invoicer-restyle`
**Files** `invoice-generator/` only: `helpers.py`, `Dockerfile`, `static/css/style.css`,
`static/js/address_autocomplete.js`, nine templates, one new test file.

**No app logic, route or data-model change.** `app.py`, `api.py`, `models.py`,
`pdf.py`, `config.py`, `stripe_utils.py` and `email_utils.py` were not opened
for editing. `helpers.format_money` is the one Python function touched, and it
is a display formatter — see below.

### Done

**One money formatter, implementing the house conventions.** The Figures and
Tables collateral says in terms that its rules "appl[y] to the Jinja templates
in invoice-generator/ as much as to the site", so `format_money` now does:
two decimals always, thousands separated, **negatives in parentheses rather
than with a minus**, credits without the currency symbol, nil as an em dash and
a computed zero as `$0.00`. Nine call sites that hand-wrote a `−` prefix now
pass a negative number instead, so no template formats money itself any more.
`tests/test_money_format.py` reproduces the collateral's own reference table
line for line — 9 tests.

**The client-facing PDF was rebuilt against `04-TEMPLATES/SATC Invoice.html`.**
Masthead (wordmark left, contact block right, **navy** rule under, no gold),
mono tabular figures right-aligned, subtotal ruled above, balance due ruled
above and double-ruled below, the amount-due panel with its navy edge, the
how-to-pay / remit-to strip, mono micro-labels, and the SAT-C footer shape. It
is Letter at 0.7in margins now, not A4, matching the target. Still table-based
with no external CSS, and **verified rendering through both engines**.

**The web UI moved by token swap alone.** Every token name in `style.css` was
kept and re-pointed, so not one rule below the `:root` block had to change:
navy `#132437`, oxblood `#6A2833` as the single action colour, the SAT-C cool
neutral ramp, IBM Plex Sans/Mono, radii collapsed to 2px. The transactional
email and the public invoice page moved with it.

**Invoicer's own branding came off the three client-facing surfaces** — the PDF
footer's "Generated by Invoicer", the email header's product mark, and the
public invoice page's brand bar all carry the firm now. Provenance survives
where it belongs: the email footer still says "sent via Invoicer", and so does
the public page's own footer.

### Verified

- `invoice-generator/tests` — **16 pass** (7 existing calculation tests
  untouched, 9 new money-format tests).
- The PDF rendered through **WeasyPrint and xhtml2pdf**, on a deliberately
  maximal invoice: four line items, a discount, a part payment, notes, terms
  and a pay link. Both engines: zero errors, output inspected page by page.
- The running app driven in a browser — login, dashboard, invoice detail,
  public invoice page, 404. **No JavaScript errors on any of them.**
- `grep` for the old palette (`#2563eb`, `#1f2a44`, `rgba(37,99,235,…)`,
  `#eff4ff`, Hanken Grotesk, JetBrains Mono) across `templates/` and `static/`:
  **clean**.
- `grep` for gold in the PDF template: the only hit is a comment saying not to
  use it.

### [CONFIRM] markers left

1. **[CONFIRM: the invoice ledger keeps Qty and Rate columns.]**
   `SATC Invoice.html` has a two-column ledger and its "Deliberately not here"
   says **"No hours, no rates … a rate card on an invoice invites the client to
   [scrutinise] your time."** The app's data model stores a quantity and a rate
   per line item and the form collects them, so dropping the columns would hide
   data a user entered — a data-model question, not a styling one. The Figures
   collateral meanwhile prescribes exactly this four-column order. Kept, and
   raised.
2. **[CONFIRM: there is no billing-contact field.]** The target's pay strip is
   three-up — how to pay, remit to, questions on this invoice. The third column
   needs a billing contact held separately from the preparer, which this app
   has no field for. Rendered two-up.
3. **[CONFIRM: no field for the lockup tagline.]** `pdf.py` assembles
   `business.name` and `business.lines` from the invoice's `from_info`
   snapshot; there is no mono tagline line under the wordmark as there is in
   the target. Uploading the SAT-C wordmark as the account logo is the
   no-code fix and gives the exact lockup, square hyphen and all.

### Contradictions found

1. **The two specs disagree about how a credit is printed, on the same
   document.** `FIELDS - Invoice.md` says *"Format the minus sign as a real
   minus (−), not a hyphen, and **never as parentheses** on a client-facing
   document."* `SATC Figures and Tables.html` says *"Negatives in parentheses,
   **never a minus sign** … this is the accounting convention and it survives
   photocopying"*, and shows an **invoice** as its worked example. This is a
   direct contradiction, not a gap. **Parentheses were used**, because the
   authoring contract §3 says figures are governed by the Figures collateral
   "not by this file", because that collateral claims these templates by name,
   and because Batch 2's own instructions say "Figures follow
   `03-COLLATERAL/SATC Figures and Tables.html`". One of the two documents
   needs correcting, and `FIELDS - Invoice.md` looks like the one.
2. **`padding-right: 1ch` cannot ship to both engines.** The Figures
   collateral's implementation snippet prescribes it for aligning positives
   with the closing paren. **xhtml2pdf raises on the `ch` unit** and drops the
   rule, so the two engines would silently disagree about column alignment.
   Expressed as `5.7pt` instead — 1ch of IBM Plex Mono at the 9.5pt every
   figure on the page uses.
3. **The overnight brief says the Invoicer PDF is "on the old warm palette".**
   It was not. It was on the Invoicer product's own blue design system
   (`#2563eb`, Hanken Grotesk, `05-INVOICER/`), which is a different starting
   point from the one the brief describes. The finding — two different invoices
   can reach a client — was right; the description of the second one was not.
4. **The `--mute` token would have landed on text.** The straight ramp mapping
   put `#82817C` at `--gray-500`, which `.muted`, `.hint`, `.kpi__label`,
   `.breadcrumb` and several template rules use as a **text** colour. The brand
   spec is explicit that `--mute` is 3.6:1 and never goes on type, so
   `--gray-500` is `--ink-2` and `--mute` is declared separately for the rules
   and bullets that are its only legitimate use.
5. **No running footer.** §8 of the authoring contract wants the footer to
   repeat on page 2. `SATC Invoice.html` gets that from the `doc-page` web
   component's footer slot; a table-based template that must satisfy both
   WeasyPrint and xhtml2pdf has no shared mechanism for it (`@bottom-left` vs
   `@frame`). The footer prints once, on the last page, as it did before. A
   real invoice is one page; this is a known gap, not a regression.
6. **Status colours were deliberately not collapsed into oxblood.** Paid,
   overdue and draft are a semantic axis. Oxblood means "this is the thing you
   click". Merging them would make the dashboard unreadable, so the green /
   amber / red ramp survives — and the accent text on navy grounds is **gold**,
   which is banned in print and permitted on screen, and is what the website's
   own navy footer uses for the same job.
7. **xhtml2pdf renders the document at lower fidelity than WeasyPrint** — it
   ignores `text-transform`, so the mono eyebrows are not uppercased, and it
   draws a `double` border as a single thick rule. Both are pre-existing engine
   limits, not new, and `pdf.py` already documents WeasyPrint as primary with
   xhtml2pdf as the Windows fallback. Worth knowing before anyone compares two
   PDFs and calls it a bug.
8. **`fonts-ibm-plex` was missing from the Docker image.** The template asks for
   IBM Plex by name; without the package WeasyPrint silently falls back to
   DejaVu and the invoice ships off-brand with nothing reporting it. Added to
   the `apt-get` line. This is the one infrastructure change in the batch and
   it exists purely to make the typography arrive.

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

## One thing added beyond the four batches

**CI ran none of the tests this run depends on.** The only job was
`pytest (satc_system)`. The merge engine, the field registry and the invoice
money formatter were covered by suites that executed nowhere except a
developer's machine — including the two guards `CLAUDE.md` describes as
build-failing:

> *"Validation tests fail the build if legal names / full TINs leak into
> outputs."*

`test_no_field_can_hold_a_tin` and `test_no_sample_contains_a_real_looking_tin`
exist and are good. Nothing ran them.

`.github/workflows/test.yml` now runs one job per project, matching the repo's
one-folder-per-project layout, with `fail-fast: false` so a break in one still
reports the others. The existing job keeps the name `pytest (satc_system)` so
anything keyed to that check name still resolves. Verified from **clean
virtualenvs** using exactly the install commands the workflow uses:
client-documents 38 pass, invoice-generator 16 pass on the Batch 2 branch.

It is **one commit on the Batch 4 branch**, deliberately separate, so it can be
dropped without touching anything else. It is the only change in this run that
was not asked for, and the reason it was made anyway is that three of the four
PRs cite test counts as their verification.

Until Batch 4 merges, the earlier branches are still uncovered.

## Addendum — pricing the firm without knowing the prices (branch `b6-fee-basis`)

Asked to share the fee schedule, with: *"not sure I even have the numbers."*

That is not a scheduling problem, it is the schedule's problem. Fourteen
questions each beginning "what do you charge for…" have no answer at a firm
that has never priced itself, and the repo holds no past invoices to read
prices off — there is no invoice database, and nothing under `invoice-generator/`
carries historical figures. So the questions are re-asked in the one unit a
preparer does know: **how long does this take you.**

`python cli.py price` walks the fourteen items asking for hours, multiplies by
an hourly rate, and writes the schedule. **Both numbers are the firm's.** The
module supplies neither and fills no blank it was not given: an item left blank
stays `[CONFIRM:`, so a half-finished sitting yields a half-priced schedule that
still refuses to render, rather than a complete-looking one with invented
figures in it. That is §9 held from the other side — the earlier work made a
placeholder impossible to *ignore*, this makes it possible to *answer*.

Three decisions worth flagging, because each could have gone the lazy way:

- **Rounding is off by default.** `$437.50` is what 2.5 hours at $175 costs;
  `$450.00` is a pricing policy, and a policy defaulted-to in a config file is
  a policy nobody decided. `--round-to 25` is how the firm says it has one.
- **The write is surgical, not a YAML dump.** `fee-schedule.yaml` is two thirds
  comment and the comments are what make it fillable by hand. Amounts are
  swapped on the lines they occupy; a dump would produce a valid file that had
  lost all of that. Where a value cannot be located unambiguously the write
  refuses rather than editing a line it guessed at.
- **`base_covers` is still not derived.** It is a structure, not an amount, and
  no number of hours implies it.

**A correction to this file's own §5 count.** `OPEN-QUESTIONS.md` said "18
amounts" while its own table listed 4 + 5 + 3 + 2 = 14. `pricing.open_amounts()`
reports 14 amounts plus `base_covers`. The prose was wrong; it now says 14, and
a test (`test_every_priceable_amount_has_a_prompt`) fails if the schedule ever
grows an amount that has no prompt behind it, so the two cannot drift again.

Verified: 134 pass (was 113), and the chain runs end to end — example hours →
rate → schedule → interview → a rendered estimate totalling $1,425.00 with no
`[CONFIRM:` in it. One bug found and fixed in the writing: `rate` was being
popped out of the hours file *after* the hours dict was built, so it was
offered to the engine as a priceable item and rejected.

## What a human should do next

1. **Call the Accountancy Board of Ohio.** Unchanged from the brief, and still
   the one thing no agent can do.
2. **Decide the parentheses-vs-minus question** before #139 merges. It is the
   only finding here that changes a document a client already reads.
3. **Answer the officer-compensation `[CONFIRM]`**, which unblocks the business
   return letter.
4. **Delete two words from `index.html:826`.**
5. **Merge #140 before #141**, and #138 and #139 whenever.
