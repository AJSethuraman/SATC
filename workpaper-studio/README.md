# Workpaper Studio (working title)

A configurable tool for structured workpapers and linesheets: an organization defines a review once from tested building blocks; its people complete, review and release it as a traceable record. Deterministic. No AI in the product.

**Status: design-review checkpoint. No product code.** Start with `prototype/journey.html`, then `docs/HANDOFF.md`.

**In plain terms.** The organization sets its words, lists and table patterns. A designer builds a tool from fields, tables, calculations and conditions, where every table is one primitive whose rows and columns are configured. People fill the tool in. The tool is data, so a loan review, a bank reconciliation, an audit control test and a tax intake checklist all run on one engine. `index.html` is one finished example, a credit review; it is *not* the product.

| | |
|---|---|
| `docs/DESIGN-REVIEW.md` | Understanding, decisions, architecture options, plan with acceptance criteria |
| `docs/DECISIONS.md` | Decisions needed, confirmed requirements, scope |
| `docs/HANDOFF.md` | How the next session continues |
| **`excel/`** | **Configured tools delivered as real Excel workbooks.** The generator turns a configuration into a working `.xlsx` (inputs, dropdowns, conditional sections, calculations, release check, record row; no macros). Blank tool and filled example for three configurations, checked in LibreOffice |
| **`prototype/tools.html`** | **What a configuration turns into**: three finished tools from very different configurations (credit file review, control test, bank reconciliation), each in its organization's brand, plus the creator's view of a published tool (use, shape, versions, who installed it) |
| **`prototype/journey.html`** | **Start here.** The whole path in six live steps: build a tool (configuration on the left, the result on the right), package it as one file, list it for a niche, a buyer installs it and makes it theirs, their staff use and release it, an update arrives. Five unrelated tools from one engine, and every table in them is one primitive configured differently |
| **`prototype/outputs.html`** | **What comes out, and the screens that produce it**: the signed workpaper, the workbook, the data feed and the quarter roll-up, shown as the files contain them, then five proposed screens (queue, testing a file, review, release, roll-up) |
| `examples/` | The generator and the real files: PDF, .xlsx, CSV, JSON. See `examples/README.md` |
| `docs/REFERENCE-WORKBOOK.md` | What the owner's real workbook showed, and the gaps it exposes |
| `docs/MARKET-AND-PACKS.md` | How this could be sold: packs, niches, models, risks (including who owns the know-how) |
| `prototype/index.html` | Clickable prototype of the recommended direction. Synthetic data, **fictional methods and thresholds, mocked integrations** |
| `prototype/directions.html` | Three visual directions compared |
| `prototype/check*.js` | Scripted checks (Playwright): `check.js` 25, `check-builder.js` 15, `check-journey.js` 48 |

Related, not replaced: `credit-review-os/` (generated Excel workpapers).
