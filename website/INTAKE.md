# SATC Prospect Intake — Working Log

**Living document.** Update it as decisions get made; it is the memory across
sessions. Claude Code sessions here run in ephemeral containers — anything not
committed is gone. If you are a fresh session picking this up, read this file
first, then `website/README.md`.

Last updated: **2026-08-13**

---

## 1 · What we are building

A **public prospect qualification intake** on the SATC marketing site. It should
feel like a **short guided conversation**, not an accounting questionnaire.

- Shape: high-information questions → conditional follow-ups → minimal effort.
- Target: **~8–12 meaningful interactions** for a typical prospect. Not a hard
  cap — a complicated prospect earns more questions because their own answers
  justified them.
- A straightforward prospect moves through fast. Irrelevant questions are never
  shown.

### What this is NOT

- Not a tax organizer.
- Not client onboarding.
- Not a redesign of the website.
- Not a general-purpose form-builder platform.

### Governing rule for every question

> An answer must either **provide useful information** or **determine what
> happens next.** If it does neither, cut it.

---

## 2 · Hard constraints

### Never collect in this public intake

SSNs · EINs (unless explicitly revisited) · bank account or routing numbers ·
driver's license info · IP PINs · detailed dependent info · usernames or
passwords · accounting-system credentials · tax organizer detail · itemised
deductions · tax documents · prior returns · document uploads.

Those belong to a later onboarding workflow behind real authentication. This
page is static and public — submissions traverse a third-party service, so the
list above is a security boundary, not a preference.

Repo-wide rules in `CLAUDE.md` still apply: PII is load-bearing, Drake stays the
system of record, only masked/last-4 values ever reach artifacts or logs.

### Engineering constraints

- Preserve the existing visual language. Reuse existing components and styles.
- No new framework, no build step, unless the app clearly demands it.
- Questions, choices, and branching rules must be **easy to edit** — a small
  readable config, *not* an elaborate abstraction.
- Do not break existing submission behaviour without explaining why first.

---

## 3 · Phase 1 audit — the architecture as it stands

Verified against `main` @ `fe50418` on 2026-08-13.

| Aspect | Reality |
|---|---|
| Framework / runtime | **None.** Static HTML + vanilla JS. No build, no bundler, no package.json. |
| Files | `website/index.html` (1,155 lines, 60KB) is the whole site. Plus `privacy.html`, `terms.html`, `robots.txt`, `sitemap.xml`, two PNGs, `assets/make-images.py`. |
| Routing | None. Single page, in-page anchors (`#services`, `#intake`, `#documents`, `#top`). |
| Components | None. Hand-written CSS classes, no library. |
| Design system | CSS custom properties in `:root` (`index.html:31–48`) — navy `#0B1F3A`, gold `#B08D57`, cream `#F7F5F0`, `--serif` Cormorant Garamond, `--sans` Hanken Grotesk, `--pad` clamp. |
| Reusable classes | `.wrap .btn .btn-link .eyebrow .h2 .lead .field .two .checks .check .callout .fs-note .doc-group .consent .form-status .intake-form .intake-grid .intake-aside .steps .intake-done .services .service .hero .nav .lockup` |
| Form state | **None.** One `<form id="intakeForm" novalidate>` + a `submit` listener. |
| Validation | Hand-rolled in the submit handler: name + email present, email regex, consent ticked. |
| Conditional logic | Exactly one rule — `#ownsBiz` select toggles `#bizBlock` (`index.html:1039`). |
| Submission | `fetch` POST to `https://formspree.io/f/<id>` when `SATC_CONFIG.contact.formspreeId` is set. **It is currently empty**, so every submission falls through to a pre-filled `mailto:`. |
| Backend / DB / CRM | **None exist.** No API route, no database, no webhook. Staff receive an email. |
| Config | `SATC_CONFIG` block at `index.html:972` — contact, booking, analytics. |
| JS modules | Six IIFEs: contact wiring · booking link · mobile nav · business-block toggle · intake submit · analytics. |
| Tests | **None for the website.** `.github/workflows/test.yml` runs pytest for `satc_system` only. |
| Deploy | `.github/workflows/pages.yml` → GitHub Pages on push to `main` touching `website/**`. Live at <https://ajsethuraman.github.io/SATC/>. **Edits here are production changes.** |

### Preserve

Palette, type scale, and every class above · the nav/hero/services/footer
sections · `SATC_CONFIG` as the single edit surface · the Formspree-or-mailto
fallback pattern · the no-PII callout · the honeypot (`_gotcha`) · blank-field
stripping before submit · human-readable field names in the payload.

### Risks

1. **No test coverage and no staging.** `main` deploys straight to production.
   Verification has to be explicit (headless browser) or it does not exist.
2. **Formspree unconfigured.** Until an ID is pasted in, submissions depend on
   the visitor's mail client — which frequently fails silently on mobile.
3. **Structured data vs. email delivery.** Normalized values must survive as a
   readable email, since there is no record store.
4. **Single file is getting large.** 60KB before a branching engine is added.

---

## 4 · Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-08-13 | Site reduced to `Nav → Hero → Services → Intake → Footer` | Wanted a page to send leads to; the marketing sections were not serving that. Full prior page kept at `docs/website-archive/index-full-marketing-2026-08-13.html`. |
| 2026-08-13 | Form collects **no** SSNs/EINs/documents; documents move over a secure upload link sent in the reply | Static page, third-party form relay — wrong channel for a TIN. |
| 2026-08-13 | Formspree as the delivery mechanism, mailto as fallback | No backend exists; keeps the form on-page and in-design. |
| 2026-08-13 | Model **Opus 5**, effort **high**; ultracode fan-out reserved for Phase 4 validation only | Phases 1–3 are a single-file edit — parallel agents would collide. Phase 4's ten scenario paths fan out cleanly. |
| 2026-08-13 | **Split into `intake-config.js` + `intake.js`**, loaded by plain `<script src>` | `index.html` is already 60KB; the questions and branching rules need to be editable on their own. Still zero build step. `CLAUDE.md` convention updated to match. |
| 2026-08-13 | **Cut the "What you'll need" document checklist** | ~20 checkbox decisions of tax-organizer texture inside a 8–12 interaction target, covering items on the no-collect list. Moves to onboarding after the first conversation. |
| 2026-08-13 | **One question per step**, contact details grouped onto a single step | Makes it read as a conversation and maps onto the 8–12 target; conditional questions simply never appear rather than leaving gaps in a page. |
| 2026-08-13 | **Formspree for delivery + a machine-parseable block in the payload** so submissions can reach a spreadsheet without a paid tier | Formspree free retains submissions only **30 days** and gates Zapier behind a paid plan, so it cannot be the record. See §5.4. |

---

## 5 · Product decisions

1–3 **resolved 2026-08-13** (see the decision log). 4 is open.

### 5.4 · Getting submissions into a spreadsheet — open

Researched 2026-08-13. The constraints are real and worth recording:

| Fact | Consequence |
|---|---|
| Formspree free: ~50 submissions/month, **30-day** submission history | The dashboard is **not** an archive. The email is the record. |
| Formspree Zapier/integrations are **paid-plan** features | Cannot chain Formspree → Excel on the free tier. |
| Power Automate **"When an HTTP request is received" is a premium trigger** | Cannot POST the page directly at a Microsoft flow without a Power Automate Premium licence. |
| Power Automate **"When a new email arrives"** (Office 365 Outlook) is a **standard** connector | Free path to Excel exists — trigger on the Formspree notification email and parse it. |

**Recommended:** make the submission email carry a compact, machine-parseable
block (fixed `key: value` lines plus a single-line JSON payload) alongside the
human-readable summary. Then either route works, with no lock-in and no paid
tier:

- **Microsoft-native, free:** Power Automate → *When a new email arrives* →
  parse the JSON block → *Add a row into a table* in an Excel workbook on
  OneDrive.
- **Simpler, free:** the page also POSTs to a Google Apps Script web app that
  appends a row to a Sheet; export to `.xlsx` when Excel is wanted.

Designing the payload to be parseable is worth doing **either way**, so this
does not block Phase 2 or 3.

---

## 6 · The v1 intake model

Eight sections. Section 1 is the primary routing question; everything after is
conditional on it.

1. **Services needed** (multi-select) — routes everything downstream.
2. **Individual tax complexity** (select-all) — only when individual services apply.
3. **Business profile** (structure) — only when business services/ownership apply.
   *Legal structure ≠ tax treatment; keep the model able to separate them later.*
4. **Business complexity basket** (multi-select) — complexity flags, not detail questions.
5. **Current status** — varies by service (tax status vs. bookkeeping status).
6. **Conditional scale/workload** — only where an earlier answer justifies it. Prefer ranges.
7. **Timing / urgency** — exact deadline only when the situation warrants.
8. **Additional context** — one optional free-text field. Not a substitute for structure.

Plus **contact info** grouped logically (name, email, phone, state) — never one
field per step. No street address.

### Normalized values

```
services:               individual_tax · business_tax · bookkeeping · payroll ·
                        tax_planning · tax_resolution · entity_setup
individual_complexity:  w2 · self_employment · business_owner · rentals ·
                        investments · k1 · retirement · crypto · multistate · foreign
business_complexity:    employees · contractors · inventory · sales_tax · ecommerce ·
                        accounts_receivable · accounts_payable · multi_location · multistate
```

### The stale-data rule

Changing an earlier answer **must** clear downstream answers it no longer
justifies. Canonical failure case:

> Select rentals → enter `rental_count = 3` → go back and deselect rentals.
> The submitted payload must **not** contain `rental_count`.

This is the most bug-prone requirement in the spec. Treat it as correctness-critical.

---

## 6a · Phase 2 — implementation plan

### Files

| File | Role | Size |
|---|---|---|
| `website/intake-config.js` | **The edit surface.** Steps, questions, choices, branching predicates. This is the file you open to change the form. | ~250 lines |
| `website/intake.js` | The engine. Renders the current step, tracks answers, prunes stale data, builds the payload, submits. | ~300 lines |
| `website/index.html` | Intake `<section>` markup replaced with a mount point + two `<script src>` tags. Everything else untouched. | −250 / +30 |

Nav, hero, services, footer, the CSS token block, and the contact / booking /
mobile-nav / analytics IIFEs are **not touched**.

### The step graph

Predicates read the `answers` object. `∋` = "selection includes".

| # | id | type | shown when |
|---|---|---|---|
| 1 | `services` | multi | always |
| 2 | `individual_complexity` | multi | services ∩ {individual_tax, tax_planning, tax_resolution} |
| 3 | `rental_count` | single | ind ∋ `rentals` |
| 4 | `business_structure` | single | services ∩ {business_tax, bookkeeping, payroll, entity_setup} **or** ind ∋ `business_owner` |
| 5 | `entity_count` | single | `business_structure` = multiple |
| 6 | `business_complexity` | multi | step 4 answered, unless services = {entity_setup} only |
| 7 | `headcount` | single | biz ∋ `employees` **or** services ∋ payroll |
| 8 | `contractor_count` | single | biz ∋ `contractors` |
| 9 | `states_detail` | text | ind ∋ `multistate` **or** biz ∋ `multistate` |
| 10 | `revenue_band` | single | step 4 answered |
| 11 | `tax_status` | single | services ∩ {individual_tax, business_tax, tax_planning, tax_resolution} |
| 12 | `unfiled_years` | single | `tax_status` = multiple_unfiled |
| 13 | `bookkeeping_status` | single | services ∋ bookkeeping |
| 14 | `transaction_volume` | single | services ∋ bookkeeping |
| 15 | `urgency` | single | always |
| 16 | `deadline` | text | `urgency` ∈ {deadline, notice, unfiled} |
| 17 | `notes` | textarea | always, optional |
| 18 | `contact` | group | always, last |

**Path lengths** — validates the 8–12 target:

| Prospect | Steps |
|---|---|
| W-2 individual | 1, 2, 11, 15, 17, 18 → **6** |
| Individual + rentals/investments | + 3 → **7** |
| Business tax only | 1, 4, 6, 10, 11, 15, 17, 18 → **8** |
| Bookkeeping cleanup | + 13, 14 → **9** |
| Tax + books + payroll | → **12** |

### Config shape

```js
{
  id: 'rental_count',
  type: 'single',
  question: 'How many rental properties?',
  help: 'A rough count is fine.',
  required: true,
  options: [
    { value: '1',    label: 'Just one' },
    { value: '2_3',  label: '2–3' },
    { value: '4_9',  label: '4–9' },
    { value: '10up', label: '10 or more' },
  ],
  showIf: a => (a.individual_complexity || []).includes('rentals'),
}
```

**Decision — predicate functions, not a declarative rule DSL.** A data-only rule
format (`{field, op, value}`) would need an interpreter, which is exactly the
form-engine abstraction the brief rules out. With no build step and no
framework, a one-line arrow function is readable, debuggable in the console, and
costs nothing. Trade-off: config is JS, not JSON — acceptable, since nothing
consumes it but the browser.

### Stale-data pruning — the correctness core

**One source of truth.** `showIf` decides *both* whether a step renders *and*
whether its answer may exist. Visibility and retention cannot drift apart,
because they are the same predicate.

**Prune to a fixpoint, not one pass.** Removing an answer can strand a step
downstream of it; that step's answer must go too.

```js
function prune(answers) {
  let changed = true;
  while (changed) {                       // cascade: rentals → count, business → entity_count
    changed = false;
    for (const step of STEPS) {
      if (step.showIf && !step.showIf(answers) && step.id in answers) {
        delete answers[step.id];
        changed = true;
      }
    }
  }
}
```

Runs after every answer mutation. The canonical bug — deselect rentals, keep
`rental_count = 3` — is structurally impossible, not patched.

### Other decisions this architecture forces

- **Full re-render of the current step from state**, no DOM diffing. No framework
  to do it for us, and one step is cheap.
- **Reuse existing classes** — `.field .two .checks .check .btn .form-status
  .callout .fs-note` already carry the visual language. Almost no new CSS.
- **Progress bar without a denominator.** Branching means the total isn't known
  up front; showing "3 of 12" would be a lie. A bar over the currently-known
  visible steps, recomputed as answers resolve.
- **`sessionStorage` resume.** Answers survive an accidental reload; cleared on
  successful submit. Not `localStorage` — this shouldn't outlive the visit.
- **Contact last.** Lowest friction to start, highest completion. Trade-off:
  abandonment yields nothing. Revisit if drop-off proves to be a problem.

### Payload

Preserves everything that works today — Formspree POST, mailto fallback,
`_subject`, `_replyto`, `_gotcha` honeypot, blank stripping — and adds:

- Human-readable `Label: value` lines, so the email stays legible.
- A single-line `_json` field carrying normalized values, so a Power Automate or
  Apps Script flow can parse it into a spreadsheet row (§5.4).

---

## 7 · Progress

- [x] **Phase 1 — Audit.** Complete, findings in §3.
- [x] **Phase 2 — Implementation plan.** Complete, in §6a.
- [x] **Phase 3 — Implement.** `intake-config.js` + `intake.js`; `index.html` reduced to a mount point.
- [x] **Phase 4 — Validate.** 77 agents: 10 scenario walks + 7 review lenses, every
      finding independently refuted before counting. **52 confirmed, 8 refuted.**
      All fixed; 23/23 regression checks pass.

### What validation caught (2026-08-13)

Worth keeping, because the failure mode generalises.

**Blocker — `const SATC_CONFIG` is not `window.SATC_CONFIG`.** A top-level
`const` in a classic script is lexically scoped and never becomes a window
property. `index.html`'s own inline IIFEs read the bare identifier and worked
fine, so the page looked healthy; `intake.js`, loaded as a separate file, read
`window.SATC_CONFIG`, got `undefined`, and sent **every** submission to
`mailto:undefined`. `contact.email` was undefined for the same reason, so the
documented fallback was broken too — no config made it work, and the error text
read "Please email undefined". All 16 agents found it independently.

*Lesson:* splitting a file across a script boundary changes variable
reachability, and the only symptom was at submit time — which no smoke test that
stops short of pressing the button will ever reach.

**Also fixed:** `prune()` ignored orphaned answers from a changed config ·
`business_complexity` interrogated a business the prospect said doesn't exist ·
`entity_setup`-only suppressed the business subtree for actual business owners ·
mailto fallback omitted name and email · honeypot wedged the form on "Sending…" ·
three new CSS rules lost the cascade to pre-existing `.intake-form` selectors ·
progress bar ran backwards · no visible keyboard focus on choice rows · nested
`aria-live` re-announced the whole form · 21px tap targets · answers saved only
on navigation, so a reload mid-step discarded them.

**Held up:** the fixpoint pruning core. No agent got `rental_count` — or any
other stale answer — to survive a deselect.

**Known and accepted:** after a *failed* send the button re-enables, so each
retry click fires a request. Cannot duplicate a lead, because a successful
submit replaces the form immediately.

### Definition of done

Intake works in the existing site · irrelevant questions hidden · baskets produce
structured values · conditional follow-ups correct · **stale data cleared** ·
submission wiring intact · usable on mobile · validation works · errors handled ·
no unrelated changes · readable, no form-engine abstraction · major paths tested ·
changes and remaining product decisions clearly explained.

---

## 8 · How to verify a change

```bash
cd website && python -m http.server 8000     # then http://localhost:8000
```

There is no test suite for the website. Verification means driving a real
browser — Chromium is preinstalled at `/opt/pw-browsers/chromium-1194/`, and
`pip install playwright` gives you the Python bindings. Check at 1440px and
390px, confirm `document.documentElement.scrollWidth` never exceeds the
viewport, and exercise both submit paths.

Google Fonts is blocked by the sandbox proxy, so a local render falls back to
Times/system sans. That is an environment artifact, not a page bug.
