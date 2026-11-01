# Workpaper Studio (working title)

A configurable tool for structured workpapers and linesheets: an organization defines a review once from tested building blocks; its people complete, review and release it as a traceable record. Deterministic. No AI in the product.

**Status: design-review checkpoint. No product code.** Start with `prototype/configurable.html`, then `docs/HANDOFF.md`.

**In plain terms.** The organization sets its words and lists. A designer builds a tool from blocks (fields, tables, calculations, conditions). People fill the tool in. The tool is data, so a loan review, a bank reconciliation, an audit control test and a tax intake checklist all run on one engine. `index.html` is one finished example, a credit review; it is *not* the product.

| | |
|---|---|
| `docs/DESIGN-REVIEW.md` | Understanding, decisions, architecture options, plan with acceptance criteria |
| `docs/DECISIONS.md` | Decisions needed, confirmed requirements, scope |
| `docs/HANDOFF.md` | How the next session continues |
| **`prototype/configurable.html`** | **Start here.** The point of the project: edit a tool's configuration on the left, see the workpaper it produces on the right. Four unrelated tools from the same engine |
| `prototype/index.html` | Clickable prototype of the recommended direction. Synthetic data, **fictional methods and thresholds, mocked integrations** |
| `prototype/directions.html` | Three visual directions compared |
| `prototype/check.js` | Scripted checks of the prototype (Playwright) |

Related, not replaced: `credit-review-os/` (generated Excel workpapers).
