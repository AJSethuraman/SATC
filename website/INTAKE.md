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
| Deploy | `.github/workflows/pages.yml` → GitHub Pages on push to `main` touching `website/**`. Live at <https://ajsethuraman.github.io/satc/>. **Edits here are production changes.** |

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

---

## 5 · Open product decisions

Blocking nothing yet, but each needs an answer before or during Phase 2.

1. **Split `intake.js` / `intake-config.js` out of `index.html`?**
   The branching config plus engine will push the single file past ~90KB.
   Plain `<script src>` keeps zero build step and directly serves the
   "easy to edit the questions" requirement. `CLAUDE.md` currently describes the
   site as a single `index.html`, so this changes a stated convention.
   *Recommendation: split.* — **undecided**

2. **Drop the "What you'll need" document checklist?**
   It currently asks prospects to confirm they hold photo ID, prior returns,
   W-2s, etc. The new spec excludes driver's-license info, prior returns, and
   detailed tax documents. Confirming possession is not collecting, but it is
   organizer texture in what should be a qualification form.
   *Recommendation: cut it, move to onboarding.* — **undecided**

3. **Is an emailed summary enough for staff?**
   The spec asks for clean structured data. With no backend, staff get a
   well-formatted email, not a queryable record. Adding storage is a backend
   project outside this scope.
   *Recommendation: accept email for v1, revisit if volume grows.* — **undecided**

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

## 7 · Progress

- [x] **Phase 1 — Audit.** Complete, findings in §3.
- [ ] **Phase 2 — Implementation plan.** Map the model in §6 onto the codebase; resolve §5.
- [ ] **Phase 3 — Implement.** Smallest reasonable change set.
- [ ] **Phase 4 — Validate.** Ten representative paths + stale-data adversarial checks.

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
