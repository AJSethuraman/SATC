# SAT-C — State of Play & Overnight Brief

**Date:** 2026-08-20 · **Repo:** `AJSethuraman/SATC` (branch `main`, scope `website/`)

For a second agent and Arjun to read together before an unattended Claude Code
run. Part one is what exists. Part two is what tonight should do. Part three is
what the run must not do.

---

> ## ⚠️ STATUS CORRECTION — 2026-08-14 session
>
> **Read this before acting on Part 2.** Work landed after this brief was
> written, and following it verbatim would redo finished work.
>
> **Batch 1 is essentially DONE and merged to `main`.**
> - The restyle is applied to `website/` (PR #117), matching `reference.html`.
> - `website/assets/make-images.py` was replaced with the handoff copy and
>   re-run; `og-image.png` and `apple-touch-icon.png` no longer carry the old
>   gold seal.
> - The **SAT-C wordmark** was adopted in the nav and footer (PR #124), per the
>   updated Notch spec. §02 of that spec won over §04/§06: the symbol **does**
>   appear in the nav, with the oxblood piece.
> - **Still open from Batch 1:** the two drafted disclosures in
>   `01-WEBSITE/WEBSITE-DISCLOSURES.md` have **not** been added. That is the
>   remaining piece.
>
> **Batches 2–5 are untouched and still valid.**
>
> **Two guardrails need amending:**
> - *"Never touch … `SATC_CONFIG`"* — it now lives in `website/site-config.js`,
>   loaded by both `index.html` and `privacy.html`. Still do not touch it.
> - The site is **live on `satcllp.com`** via Cloudflare Pages, which builds on
>   push to `main`. GitHub Pages still deploys too. "Never push to `main`" is now
>   doubly true: it publishes to the real domain.
>
> **Part 4's closing item is resolved and inverted.** The intake form no longer
> promises "within one business day" — that wording is gone. And submissions
> **are** now stored: Formspree retains them 30 days, and a Power Automate flow
> files every one as a row in `SATC leads.xlsx`. See `docs/leads-to-excel.md`.
>
> **New since this brief:** `docs/email-authentication.md`,
> `docs/leads-to-excel.md`, `website/GOING-LIVE.md`, `website/privacy.html`.

---

# Part 1 — Where the project stands

## What this project is

A complete visual and document system for **SAT-C LLP** (Sethuraman Accounting,
Tax & Consulting), a solo-principal Ohio accounting practice. It began as a
restyle of a one-page intake site and became the firm's whole output system:
brand, website, client documents, and the merge pipeline that will generate them.

**The direction, settled and not up for renegotiation:** modern practice · cool
ground · IBM Plex superfamily · navy dominant · oxblood as the single action
colour · gold demoted to hairlines · symbol is the **Notch** · wordmark is
**SAT-C with a small solid square as the hyphen**.

Reasoning is preserved in the decision-history files in `99-DECISION-HISTORY/`
(`Palette Directions.html`, `SATC Mark - Razor.html`, and the rejected
alternatives). They exist so nobody relitigates a settled choice.

## Decided and locked

- **Palette, type, and the mark.** Including the finding that navy and oxblood
  sit at 1.47:1 in greyscale, which is why shape rather than hue always carries
  meaning.
- **Business cards.** Production file ready for the printer.
- **No photography, ever. No AI imagery, ever.** A written policy, not a gap.
- **Licence numbers and the Ohio SoS number are not printed.** Decided.
- **No assurance vocabulary** anywhere in any surface, except explicit negation.

## Built and awaiting review

| Area | State |
|---|---|
| Website restyle | `satc-restyle.css` + `reference.html` + `01-WEBSITE/SATC-STYLE-SPEC.md`. Not yet applied to the repo. |
| Collateral | Letterhead, financial statements, report cover, email signature, portal screen, figures/tables conventions, greyscale test, proposal deck. |
| Client templates | **Six pairs**, HTML + FIELDS doc each: tax prep engagement letter, bookkeeping engagement letter, fee estimate, organizer cover, onboarding letter, invoice. |
| Authoring method | **`00-START-HERE/AUTHORING-CONTRACT.md`** + `04-TEMPLATES/satc-doc.css` + `04-TEMPLATES/_SKELETON.html` — new as of today. This is what makes an unattended run safe. |
| Website disclosures | **`01-WEBSITE/WEBSITE-DISCLOSURES.md`** — two of three drafted, one left open deliberately. |

Nothing has been formally signed off. Everything above is "ready to review."

## The open items, honestly

1. **Firm registration with the Accountancy Board of Ohio** — unconfirmed, and
   it governs how the firm may describe itself everywhere. Closeable with a
   fifteen-minute phone call. **This is the highest-leverage unblock in the
   project** and no agent can do it.
2. **Financial statement legend** — draft v2 now sits in bookkeeping §02:
   *"Prepared by SAT-C LLP from information provided by management. We have not
   audited or reviewed these financial statements and express no opinion or
   assurance on them."* Deliberately does **not** restrict who the client shows
   the statements to — v1 did, and that was wrong; a client should be able to
   take them to a bank the way they would a QuickBooks P&L. Needs a yes.
3. **Six templates unread.** Review is cheap and unblocks the merge pipeline.

## Known inconsistency

The Invoicer Flask app (`invoicer/` in this folder, `invoice-generator/` in the repo) still renders its
client-facing invoice PDF on the **old warm palette**. As of today there is also
a new `SATC Invoice.html` template on the new system. Two different invoices
can currently reach a client. This is the most visible defect in the project.

---

# Part 2 — What tonight should do

Ordered so that each batch is independently valuable and independently
revertible. A run that completes only batch 1 is still a good night.

## Batch 1 — Apply the website restyle *(highest value, fully specced)*

Everything needed already exists; this is execution, not design.

- Apply `01-WEBSITE/SATC-STYLE-SPEC.md` to `website/` — the 7 steps, in order.
- Match `reference.html` exactly. Do not improvise.
- Replace `website/assets/make-images.py` with `01-WEBSITE/make-images.py` and
  re-run it, so `og-image.png` and `apple-touch-icon.png` stop showing the old
  gold seal. **Skipping this leaves the old brand on every link preview and iOS
  home screen** — the two surfaces seen outside the page.
- Add the two drafted disclosures from `01-WEBSITE/WEBSITE-DISCLOSURES.md` (items 2 and 3).
  Use the firm-status **placeholder** for item 1 and leave a code comment saying
  it is pending the Accountancy Board answer.
- Feature branch → **draft PR**. Never push to `main`; it auto-deploys.

## Batch 2 — Restyle the Invoicer app

- Bring `invoicer/` in this folder, `invoice-generator/` Jinja templates onto the new tokens.
- The client-facing invoice PDF must match **`04-TEMPLATES/SATC Invoice.html`** —
  same masthead, same ledger conventions, same footer. Treat that file as the
  target the way `reference.html` is the target for the website.
- Figures follow `03-COLLATERAL/SATC Figures and Tables.html`. One money formatter.
- Do not change app logic, routes, or data model. Presentation only.

## Batch 3 — Migrate the six templates onto the shared stylesheet

Mechanical and high-value: it is what makes every future template consistent by
construction rather than by discipline.

- Each existing template inlines a near-identical copy of what is now
  `04-TEMPLATES/satc-doc.css`. Replace the inline block with a `<link>`, keeping
  only genuinely unique rules inline.
- **Render each before and after and diff the screenshots.** Any visual change
  is a bug in the migration, not an improvement.

## Batch 4 — Build the remaining templates

Using `AUTHORING-CONTRACT.md` and `_SKELETON.html`. In priority order:

1. **Tax return delivery letter** — filing instructions, what to sign, what to
   keep, "our engagement ends at transmission".
2. **Extension notice** — short, highest volume.
3. **Business return engagement letter** — 1120-S / 1065, K-1 timing.
4. **Disengagement letter** — nobody builds it until they urgently need it.

Each is an HTML + FIELDS pair, a README row, and a pass of the self-check in
§8 of the contract. **Leave `[CONFIRM: …]` markers rather than inventing legal
wording** — see §9.

## Batch 5 — The merge engine spec *(only if 1–4 land)*

Not the engine. The **spec**: consolidated field registry across all templates,
join-key rules, the strip-and-render contract, PDF naming, failure modes. It
should be derivable almost entirely from the existing FIELDS docs — if it is
not, the FIELDS docs have a gap worth reporting.

---

# Part 3 — Guardrails

Non-negotiable for an unattended run.

```
Never push to main. Feature branch → draft PR, per batch, not one giant PR.
Never invent legal, regulatory, or assurance wording. Leave [CONFIRM: …].
Never use: audit, audited, assurance, attest, opinion, review engagement,
  examination — except in explicit negation.
Never call the firm a "CPA firm" or "Certified Public Accountants".
  The approved form is "led by a licensed CPA".
Never print gold. Never put --mute on text. Never add photography or icons.
Never touch intake.js, intake-config.js, or SATC_CONFIG.
Never change Invoicer logic, routes, or data model.
Never relitigate a decision recorded in the decision-history files.
Stop and report rather than guess when a fact is missing.
```

**Leave a run log** at `SATC-HANDOFF/RUN-LOG-2026-08-20.md`: what was done, what
was skipped and why, every `[CONFIRM]` left behind, and anything encountered
that contradicts the specs. The contradictions are the most valuable output of
an unattended run — they are the things the specs got wrong.

---

# Part 4 — Model selection

**Recommendation: Opus for batches 3–5, Sonnet for batches 1–2.**

The split follows one question: *does the batch require judgement about voice,
legal risk, or system coherence?*

| Batch | Model | Why |
|---|---|---|
| 1 · Website restyle | **Sonnet** | Fully specced, target file to match, no open questions. Judgement would be a liability here — the spec says "don't improvise" and Sonnet is less inclined to. |
| 2 · Invoicer restyle | **Sonnet** | Same shape: known tokens, a target file, presentation only. |
| 3 · Stylesheet migration | **Opus** | Deciding which rules are genuinely unique versus accidentally divergent is a real judgement call, and getting it wrong silently changes documents. |
| 4 · New templates | **Opus, without question** | Legal-adjacent client-facing copy in an established voice, with a hard compliance vocabulary and an obligation to recognise when to stop and leave a `[CONFIRM]`. This is the batch where a cheaper model costs money — an invented clause that reads plausibly is worse than a blank. |
| 5 · Merge spec | **Opus** | Synthesis across six documents; the value is in noticing the inconsistencies, not in transcribing. |

**If it has to be one model for the whole run: Opus.** Batches 1 and 2 are
cheaper on Sonnet, but they are also the smaller share of the work, and the cost
of a mistake in batch 4 exceeds the savings on 1 and 2 several times over.

**Practical notes for the run**

- Give it `AUTHORING-CONTRACT.md` **first**, before any batch. It is written for
  exactly this and it is the difference between output that matches and output
  that merely rhymes.
- One batch per PR. An overnight run that produces one 40-file PR is unreviewable
  and will sit unmerged.
- Have it run the §8 self-check and **paste the completed checklist into each
  PR description**. The checklist is mechanical; making it visible is what makes
  it get run.
- Field-count errors have happened before. §8 says count, don't estimate.

---

## Suggested opening prompt

```
Read SATC-HANDOFF/00-START-HERE/AUTHORING-CONTRACT.md and
SATC-HANDOFF/00-START-HERE/OVERNIGHT-BRIEF.md
before doing anything else.

Work through the batches in Part 2 in order. One feature branch and one draft
PR per batch. Never push to main.

Observe every guardrail in Part 3 without exception. Where a fact is missing or
a decision needs a human, leave a [CONFIRM: ...] marker and keep going.

Run the self-check in section 8 of the authoring contract on every document you
touch, and paste the completed checklist into the PR description.

Write SATC-HANDOFF/RUN-LOG-2026-08-20.md as you go: what you did, what you
skipped and why, every [CONFIRM] you left, and anything you found that
contradicts the specs.
```

---

## What Arjun should do that no agent can

1. **Call the Accountancy Board of Ohio.** Fifteen minutes. It unblocks the
   firm's self-description across every surface in the project.
2. **Yes or no on the financial statement legend.** Unblocks three documents.
3. **Read the six templates.** They cannot be wired until they are approved.
4. **Confirm the intake form's "within one business day" promise** and that
   submissions are emailed and not stored anywhere.
