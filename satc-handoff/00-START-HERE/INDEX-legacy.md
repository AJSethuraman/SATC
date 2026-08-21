# SATC — Design Handoff

Everything needed to restyle `website/` and produce SATC documents. Built against
the real `AJSethuraman/SATC` source, not a mockup.

**Direction:** modern practice · cool ground · IBM Plex superfamily · navy
dominant · **oxblood** as the single action colour · gold demoted to hairlines ·
symbol is **the Notch** · wordmark is **SAT‑C with a small solid square as the
hyphen**, full firm name beneath.

---

## Start here

| Read | What it is |
|---|---|
| **`OVERNIGHT-BRIEF.md`** | State of the project, the batched work plan for an unattended Claude Code run, guardrails, and model selection. **Start here if you are an agent picking this up.** |
| **`AUTHORING-CONTRACT.md`** | How to make a new SAT-C **document** so it matches the existing set exactly — stylesheet contract, component vocabulary, field naming, voice, and a mechanical self-check. |
| **`SATC-STYLE-SPEC.md`** | The **website** spec. 7 steps to apply, tokens, rules, do/don't, compliance checklist. |
| **`reference.html`** | Your real markup, restyled. The target to match. |
| **`satc-restyle.css`** | Drop-in replacement for the `<style>` block in `index.html`. |

## Also in here

| File | What it is |
|---|---|
| `SATC Mark - Notch Spec.html` | The mark: construction grid, colour variants, size range, the SAT‑C wordmark, misuse, production code. |
| `SATC Figures and Tables.html` | Numeral conventions — negatives in parentheses, alignment, nil vs. zero, subtotal/total rules, both currency conventions. One formatter for money. |
| `SATC Greyscale Test.html` | Palette tested at greyscale, photocopy, and fax threshold. **Contains one real finding** — see below. |
| `WEBSITE-DISCLOSURES.md` | Footer and intake-form disclosure wording. Two of three drafted; the firm-status one is left open with a safe placeholder and the reason why. |

### Documents (print-ready, Letter)

| File | What it is |
|---|---|
| `SATC Letterhead and Statement.html` | Letterhead as an engagement letter, plus a statement of account. |
| `SATC Financial Statements.html` | Balance sheet + statement of operations, comparative, with the AR-C 70 style legend. Uses the **strict** currency convention. |
| `SATC Report Cover.html` | Navy cover for a reporting package, plus a contents / basis-of-presentation page. |
| `SATC Business Cards.html` | **Locked.** Two Letter proof sheets with the cards at true 3.5 × 2 in: main run two-sided (both fronts + one shared back), backup run single-sided, plus the printer spec. No address, no licence number. |
| `SATC Business Cards - Production.html` | **Send this to the printer.** Three pages, one card face each, at bleed size 3.75 × 2.25 in (trim 3.5 × 2 centred). No captions or trim marks. Export to PDF at 100%. |

### Client templates (merge → PDF → email)

Live in **`templates/`** — documents a client receives, generated per engagement
from a data record, rather than designed once. See `templates/README.md`.

| File | What it is |
|---|---|
| `templates/SATC Engagement Letter - Tax Preparation.html` | Tax prep engagement letter. Rebuilt from the firm's existing Word template: adds scope boundaries, an extension warning, a materials deadline, records/substantiation duties, delivery consent (Encyro), confidentiality, termination, and a suspend-for-non-payment clause. |
| `templates/FIELDS - Engagement Letter - Tax Preparation.md` | Its 19 fields + 1 conditional flag, grouped by which record supplies each value, with an example JSON payload. |
| `templates/SATC Fee Estimate.html` | Line-itemed fee estimate, subtotalling to a fixed total. Explicitly a good-faith estimate, not a quote. No expiry, no signature line, scope by reference to section 01 of the letter. |
| `templates/FIELDS - Fee Estimate.md` | Its 11 fields + 1 repeating line-item list. Nine are shared with whichever letter it accompanies — generate the pair in one call. |
| `templates/SATC Engagement Letter - Bookkeeping.html` | Bookkeeping / client accounting services letter. Cadence-driven scope, optional catch-up block, the advisory boundary (we advise, you decide) and the no-custody / no-signature-authority rule stated in writing. |
| `templates/FIELDS - Engagement Letter - Bookkeeping.md` | Its 18 fields + 1 repeating scope list + 1 conditional flag. Ten fields shared with the other two templates. |
| `templates/SATC Organizer Cover Letter.html` | January organizer cover. Per-client requested-documents list, the easy-to-overlook questions (digital assets, foreign accounts, new K-1), one deadline in a callout, and an optional fee-change paragraph. |
| `templates/FIELDS - Organizer Cover Letter.md` | Its 13 fields + 1 repeating list + 1 conditional flag. Twelve shared with the tax engagement letter — including `MaterialsDeadline`, which must match. |
| `templates/SATC Onboarding Letter.html` | What-we-need letter — the third document in the opening package and the one a client acts on. Checklist, deadline, secure-upload instructions, read-only access explanation, optional prior-accountant section. |
| `templates/FIELDS - Onboarding Letter.md` | Its 18 fields + 1 repeating list + 1 conditional flag. |
| `templates/SATC Invoice.html` | The bill. Shares the estimate's ledger vocabulary so the two compare line for line. Optional retainer credit and estimate-variance note; subtotal and amount due are computed, never typed. |
| `templates/FIELDS - Invoice.md` | Its 23 fields + 1 repeating list + 2 flags. |
| `templates/satc-doc.css` | **Canonical document stylesheet.** New templates link it and add nothing but their own unique rules. The six existing templates still inline a copy — migrating them is queued. |
| `templates/_SKELETON.html` | Copy-and-fill starting point for a new template. |
| `templates/README.md` | Merge syntax, field-naming rules, the five non-negotiables for whoever wires the software, and the queue of templates still to build. |

### Screen

| File | What it is |
|---|---|
| `SATC Proposal Deck.html` | 11 slides, 1920×1080. Shows the full range an engagement can cover, **no prices** — everything quoted per engagement. Exports to PDF and PPTX from the page. |
| `SATC Email Signature.html` | Table-based, **no images** — the mark is drawn with table borders. Outlook + Gmail install steps and a plain-text fallback. |
| `SATC Client Portal.html` | Portal sign-in screen. Leads on "this is the only place to send documents," which backs up the promise the intake form makes. |

### Support

| File | What it is |
|---|---|
| `make-images.py` | Replaces `website/assets/make-images.py`. Regenerates `og-image.png` and `apple-touch-icon.png` with the new mark. |
| `doc-page.js` | Print shell used by every document above. Don't edit. `templates/` carries its own copy, since those files load it relatively. |

---

## The agent prompt

```
Read satc-handoff/SATC-STYLE-SPEC.md and apply it to website/.
reference.html is the target to match — match it, don't improvise.
Replace website/assets/make-images.py with the copy in that folder
and re-run it so the raster brand assets match.
Feature branch → draft PR. Do not push to main.
```

Optionally add to the repo's root `CLAUDE.md` under `website/`:

> Visual direction is specced in `satc-handoff/SATC-STYLE-SPEC.md`. Match it for
> any change to `website/`.

---

## Three findings worth knowing

**1 · Navy and oxblood are 1.47:1 in greyscale.** They nearly merge on a
photocopy. The system survives because everywhere it uses both, *shape* carries
the meaning — the button is a filled block, the mark is outline-versus-solid. But
it produces hard rules: never oxblood text on navy, never status coded by hue
alone, and **never gold hairlines on print** (use navy at 0.5pt). Details in the
greyscale test.

**2 · The site is an intake form, not a marketing site.** Structure is
`Nav → Hero → Services → Who this is for → Intake → Footer`. The restyle adds one
section ("Who this is for") and touches nothing in `intake.js`,
`intake-config.js`, or `SATC_CONFIG`. All JS hooks are preserved.

**3 · `--mute` (#82817C) is not a text colour.** It measures 3.6–3.9:1 on the
light grounds — below the 4.5 AA floor for any size in this system. Use
`--ink-2` (#4A5360, 7.65:1) for small type and keep `--mute` for bullets and
rules. **If the agent has already applied an earlier copy of `satc-restyle.css`,
it needs the current one** — 11 uses of the failing colour were corrected,
including `.eyebrow`, which is used site-wide.

---

## Supplied

| Item | Value |
|---|---|
| Office | 6544 Copley Avenue, Solon, OH 44139 |
| Phone | 307-941-0508 |
| Licence numbers | **Not to be printed** — remove these lines from all templates |
| Ohio SoS registration number | **Not to be printed.** Decided — not used on correspondence or the website. |
| Firm status | **An LLP registered in Ohio. Not registered with the Accountancy Board of Ohio.** The footer states the LLP fact and nothing more. |

## Blocked on you

| Item | Where |
|---|---|
| **Firm registration with the Accountancy Board of Ohio** | Governs how the firm may describe itself everywhere. A fifteen-minute phone call closes it. The highest-leverage unblock in the project. |
| **Financial statement legend** | Draft v2 is in bookkeeping §02 and needs a yes. Required *on the statements*, not just in the engagement letter — blocks `SATC Financial Statements.html` and `SATC Report Cover.html`. |
| Intake form promise | Confirm "within one business day", and that submissions are emailed and stored nowhere. |
| Review of the six client templates | All complete, none approved. The merge pipeline cannot start until they are. |

Website disclosure wording is **no longer blocked** — see `WEBSITE-DISCLOSURES.md`.
Two of the three are drafted; the third has a safe factual placeholder pending
the Accountancy Board answer.

The templates use `[BRACKETED PLACEHOLDERS]` in oxblood so they're impossible to
miss. Nothing invented.

## Not built yet

- **`invoice-generator/` restyle** — the Invoicer Flask app's Jinja templates are
  still on the old warm palette, including the invoice PDF clients receive.
  Contained job now that the tokens are settled.
- **Print-ready PDFs** — every document above exports from its own page; no PDFs
  have been generated, since the placeholders should be filled first.
- **The rest of the client templates** — bookkeeping/CAS engagement letter,
  business return letter, extension notice, organizer cover, disengagement
  letter. Queue and rationale in `templates/README.md`.

---

## Decision history

Kept at the project root, outside this folder — the reasoning behind the
direction, if anyone asks why:

- `Palette Directions.html` — the original palette diagnosis and four alternatives
- `Palette Direction D.html` — the chosen direction, tightened
- `Palette Direction D - Type.html` — six type pairings, IBM Plex chosen
- `SATC Mark - Razor.html` — six ways to signify Occam's razor, the Notch chosen
- `SATC Mark - SAT-C.html` · `SATC Mark - Fill the Gap.html` · `SATC Mark - C is the Piece.html`
  — attempts to build the letter C into the symbol itself. **All rejected.** The
  symbol stays abstract; the letters live in the wordmark, where the notched
  square acts as the hyphen.
- `SATC Website - Modern.html` / `SATC Website - Traditional.html` — the direction pick
