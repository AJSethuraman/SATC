# What the firm's workbook shows, and what the product learned from it

*1 November 2026. From 35 photographs of the owner's working linesheet. **The photographs are not in this repository** (they carry an employer classification label and employer policy references). Nothing below copies their wording, thresholds, product names or policy citations. Every example question in the prototype is written fresh and marked EXAMPLE TEXT.*

## What the workbook is

A **test linesheet**: a reviewer samples a credit and tests it against a numbered framework of questions, rating each one and commenting. It also holds supporting calculation screens (debt-to-income, cash flow by owner and period, collateral, balance sheet ratios, a rating model), a feed that sends each finished sheet to a database, and several admin tabs. The product's first design (a credit decision with ratios at the centre) misread this. **The questions are the core; the calculations support them.**

## How it is administered (the part that matters for a product)

| In the workbook | What it is, in product terms | Where it lands now |
|---|---|---|
| A **framework tab**: section, question number, question, test steps. The form is built from it | The configuration is a **table of questions**. Test steps are the author's know-how, shown beside each question | A **pattern** of the one table primitive (fixed rows with guidance, rating and comment columns), with a spreadsheet-style editor and **paste from Excel** (Build) |
| One **rating list** and a **comment** per question | A rating list owned by the organization; comment required for chosen ratings | Built; the comment rule is configurable and the example values are the prototype's own |
| Questions that apply only to some credits ("for new money requests…", "for SBA credits…") | **Per-question conditions** | Built (“Only when…” per question) |
| Header: tester, reviewer, scope, dates; a **facilities table** of up to six rows | Fields and a repeating table | Built |
| **Lists on a separate sheet marked "dev-only, do not move cells"** | A managed reference list, edited in the product, never fragile | Built (organization defaults; retire, never delete) |
| Calculation screens that print **"No Debt", "No Income", "n/a"** where a number cannot exist | The same problem as missing, zero and not applicable, solved by hand per cell | Built as first-class states |
| **Feed**: one wide row per sheet, a column per field and per question, sent to a database; plus audit, schema and contract tabs | A **flat feed generated from the configuration**, so adding a question adds a column | Flat row built (a flat row cannot say why a value is empty, so a missing count rides beside it). Audit, schema and contract **not built** |
| **Error log**: reference id, user, procedure, step, error number, description, what the cleanup did | The **diagnostic log**, separate from what a user sees | Designed (two kinds of error log); screen **not built** |
| **Change log** tab and a version in the file name | Version history with a diff | Diff built; history screen **not built** |
| **Master table** of saved sheets; "view or edit existing" by entity, quarter and borrower | Saved records and retrieval | Autosave in the prototype; **retrieval by lookup not built** |
| Policy guidance and a questions tab | Reference content beside the work | Guidance per field and per question; a policy-guidance library **not built** |

## Gaps this exposes (not yet in the design)

1. ~~**Matrix blocks.**~~ **Done differently, 1 Nov 2026:** not a new block but one table primitive with configurable axes (P16). Line items by person, by period, and valuation by class are now patterns of it.
2. **Record retrieval** by entity, period and subject, with view and edit.
3. **Admin screens**: change log, diagnostic log, feed audit.
4. **Sampling.** A reviewer tests a sample; the sampling basis and scope belong on the record.
5. **A rating model block** (a graded model feeding a rating) is a specialist calculation like the others and would join the library only with tested vectors.
6. **Import of an existing framework**: pasting works; reading an `.xlsx` framework tab directly is a natural next step.

## What was set aside

The `_KIT_*` tabs are development scaffolding for automated workbook builds and are not part of the product. Their lessons (fail loudly, keep configuration out of code, verify what you build) are already principles here.
