# Workpaper Studio

A configurable tool for structured workpapers and linesheets: an organization defines a review once from tested building blocks; its people complete, review and release it as a traceable record. Deterministic. No AI in the product.

**Status (2 Nov 2026): first build of the application, walked end to end.** Start with the procedure, `docs/walkthrough/credit-review-2026-11-02/PROCEDURE-credit-review-2026-11-02.pdf`, then `docs/WALKTHROUGH-DEFECTS.md`, then `docs/HANDOFF.md`. The design-review material below is still the argument for it.

```bash
cd workpaper-studio
PYTHONPATH=src python -m workpaper_studio demo     # publish the three demo tools and confirm their limits (optional)
PYTHONPATH=src python -m workpaper_studio serve    # http://127.0.0.1:5077
python -m pytest -q                                # 82 tests; the parity test needs LibreOffice
```

Standard library only. `openpyxl` is needed only to export a workbook. It runs locally, makes no network calls and uses no model.

**In plain terms.** The organization sets its words, lists and table patterns. A designer builds a tool from fields, tables, calculations and conditions, where every table is one primitive whose rows and columns are configured. People fill the tool in. The tool is data, so a loan review, a bank reconciliation, an audit control test and a tax intake checklist all run on one engine. `index.html` is one finished example, a credit review; it is *not* the product.

| | |
|---|---|
| **`src/workpaper_studio/`** | **The application.** `pack.py` loads and refuses packs; `methods.py` + `vectors/` the method library; `engine.py` decides every status and result; `service.py` the append-only record and who may do what; `web.py`/`ui.py` the screens in the Paper design; `outputs.py` and `workbook.py` the feed and the workbook |
| **`packs/`** | **The three tools as data**: credit file review, control test, bank reconciliation. Synthetic examples; fictional limits |
| **`tests/`** | 82 tests, including a parity test that recalculates exported workbooks in LibreOffice and compares every status, result and total with the engine |
| **`docs/WALKTHROUGH-DEFECTS.md`**, **`docs/PROCEDURE-credit-review.md`** | The walk: 15 defects against 73 passing tests, what was fixed, and the procedure (rendered as one PDF with every screenshot) |
| `design/paper/` | The Paper design package the screens and workbooks are built to |
| `docs/DESIGN-REVIEW.md` | Understanding, decisions, architecture options, plan with acceptance criteria |
| `docs/DECISIONS.md` | Decisions needed, confirmed requirements, scope |
| `docs/HANDOFF.md` | How the next session continues |
| **`excel/`** | **Demonstration workbooks.** The generator (now `src/workpaper_studio/workbook.py`, shared with the app's export) turns a configuration into a working `.xlsx` (inputs, dropdowns, conditional sections, calculations, release check, record row; no macros). Blank tool and filled example for three configurations, checked in LibreOffice |
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
