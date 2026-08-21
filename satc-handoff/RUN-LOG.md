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
