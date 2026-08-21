# SAT-C LLP — Handoff

Everything for the SAT-C brand, website, and client documents. One folder, in
reading order. **Date of this snapshot: 2026-08-20.**

> **Agent picking this up for an unattended run?** Read
> `00-START-HERE/OVERNIGHT-BRIEF.md` and then
> `00-START-HERE/AUTHORING-CONTRACT.md`. Do not start work before both.

---

## The folders

| Folder | What's in it | Who reads it |
|---|---|---|
| **`00-START-HERE/`** | The brief and the authoring method | **Both of you, first** |
| **`01-WEBSITE/`** | Spec, stylesheet, reference page, disclosure drafts | Whoever restyles `website/` |
| **`02-BRAND/`** | The mark, greyscale proof, business cards | Reference; cards are print-ready |
| **`03-COLLATERAL/`** | Letterhead, statements, report cover, signature, portal, figures, proposal deck | Reference for new work |
| **`04-TEMPLATES/`** | The six client documents + field docs + shared stylesheet + skeleton | The merge pipeline |
| **`05-INVOICER/`** | Invoicer app design system and app notes | Whoever restyles the Flask app |
| **`99-DECISION-HISTORY/`** | Rejected palettes, marks, and website directions | **Nobody, unless tempted to reopen a settled decision** |

---

## 00-START-HERE

| File | What it is |
|---|---|
| `OVERNIGHT-BRIEF.md` | State of the project, the five batches for tonight's run, hard guardrails, model recommendation, and a copy-paste opening prompt. |
| `AUTHORING-CONTRACT.md` | **How to make a new SAT-C document so it matches the existing set exactly.** Stylesheet contract, component vocabulary, field naming, house voice, and a mechanical self-check. |
| `INDEX-legacy.md` | The original handoff index. Superseded by this file; kept for the palette/type/greyscale detail it carries. |
| `scratchpad.md` | Working notes. Not authoritative. |

## 01-WEBSITE

`SATC-STYLE-SPEC.md` (the 7 steps) · `satc-restyle.css` · `reference.html` (the
target to match) · `make-images.py` (regenerates `og-image.png` and
`apple-touch-icon.png` — **not optional**, the old gold seal is still on both) ·
`WEBSITE-DISCLOSURES.md` (two drafted, one deliberately left open).

## 02-BRAND

`SATC Mark - Notch Spec.html` · `SATC Greyscale Test.html` (contains the finding
that navy and oxblood are 1.47:1 in greyscale, which is why shape carries
meaning, never hue) · `SATC Business Cards.html` · `SATC Business Cards -
Production.html` (**locked, printer-ready**) · `SATC Brand Identity.html`.

## 03-COLLATERAL

Letterhead and statement · financial statements · report cover · email signature
· client portal screen · **figures and tables conventions** (governs every number
in the system) · proposal deck.

## 04-TEMPLATES

Six client documents, each an HTML + `FIELDS - *.md` pair:

| Document | Fields |
|---|---|
| Engagement letter — tax preparation | 19 + 1 flag |
| Engagement letter — bookkeeping | 18 + 1 list + 1 flag |
| Fee estimate | 11 + 1 list |
| Organizer cover letter | 13 + 1 list + 1 flag |
| Onboarding letter | 18 + 1 list + 1 flag |
| Invoice | 23 + 1 list + 2 flags |

Plus `satc-doc.css` (canonical stylesheet), `_SKELETON.html` (start here for a
new one), and `README.md` (merge syntax and the build queue).

## 05-INVOICER

The Flask app's own design system and notes. **Its client-facing invoice PDF is
still on the old warm palette** and must be brought onto
`04-TEMPLATES/SATC Invoice.html`. Two different invoices can currently reach a
client — the most visible defect in the project.

---

## Waiting on Arjun — nothing ships without these

1. **Call the Accountancy Board of Ohio.** Fifteen minutes. Governs how the firm
   may describe itself on every surface. The highest-leverage unblock here.
2. **Yes or no on the financial statement legend** (bookkeeping letter §02).
   Unblocks three documents.
3. **Read the six templates.** All complete, none approved. The merge pipeline
   cannot start until they are.
4. **Confirm the intake form's "within one business day"** promise, and that
   submissions are emailed and stored nowhere.

## The direction, settled

Modern practice · cool ground · IBM Plex superfamily · navy dominant · oxblood as
the single action colour · gold demoted to hairlines · symbol is the **Notch** ·
wordmark is **SAT-C with a small solid square as the hyphen**. No photography,
ever. No AI imagery, ever. No licence numbers and no Ohio SoS number in print.

`99-DECISION-HISTORY/` holds the rejected alternatives. They exist so nobody
relitigates a settled choice.
