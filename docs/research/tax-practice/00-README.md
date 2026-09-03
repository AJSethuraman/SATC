# Tax practice operations — research pass (2026-07-31)

Research toward the owner's goal: **SATC as "a staff accountant, but for tax."**

## Provenance and how much to trust this

Produced by a 27-agent research workflow: ten dimensions of tax-practice
operations, each researched and then **adversarially fact-checked** by a second
agent, plus three agents reading this codebase, four synthesizing, one critiquing.

**Status: raw synthesis. Reviewed by the critic pass, NOT yet reviewed by the
owner.** Read `04-critique.md` first — it corrects the other three, and its
repo-level claims were spot-checked against the code.

The fact-check pass killed 9 claims across the set. Known corrections that
survived into the synthesis documents anyway (see `04-critique.md` §c):

- **SSTS §1.4 does not require a human review step.** That was commentary in
  *The Tax Adviser*, not the standard. Only §1.4.8 ("enhance … not supplant") is
  real. Never-auto-confirm-a-model-value is **SATC policy**, not a cited rule.
- **No "universal six-feature set"** exists across practice-management products.
  Unsourced; do not treat as a requirements baseline.
- **The "three parallel status authorities" model** is the researcher's framing,
  not an industry finding. Only Drake's EF/ACK status layer is independently
  sourced.
- **The 10% variance threshold and the 3-day / two-follow-up cadence** come from
  one practitioner's personal 2018 checklist that disclaims representing even his
  own firm. If used, they are **firm policy in config, visibly marked
  "no citation"** — never presented as a norm.
- **§10.36** requires willfulness/recklessness/gross incompetence *and* a pattern
  of firm noncompliance. It does not license "be opinionated," and its
  application to a genuine firm of one is unresolved on the text.
- **Form 1040 line numbers** must be derived per tax year from the form itself.
  One source passed off the 2019 layout as current (withholding is line 25, not
  line 17). Nothing here may be hardcoded into a line-sheet mapping.

Sources that blocked automated fetch are named in the workflow output rather than
reconstructed — Reddit (r/taxpros), taxprotalk, IRS Pub 5310/4012/5299, the AICPA
SSTS PDF, and TaxDome all refused or failed extraction. **No claim in these
documents may be attributed to a source that was never read.**

## The load-bearing finding

`04-critique.md` §d, verified in code: `StagingGate.confirm()` takes the actor as
a **caller-supplied string whose default asserts a human** (`by: str =
"preparer"`), and `AppState.confirm_field()` passes no actor at all.
`auto_confirm_high()` promotes HIGH-confidence reads to CONFIRMED with no human
involved. The staging gate is the system's evidentiary keystone — the thing that
makes a value the preparer's own act — and its actor field is unauthenticated.

Any AI capability attaches here. Per the local-LLM doctrine
(`docs/LOCAL-LLM-PATTERN.md`, rule 6: policy at the engine choke point, never in
prompts), this has to be fixed **before** a model proposes anything, not after.

**Not yet verified:** whether the write functions in `src/satc/api/tools.py`
(`post_confirmed_intake`, `run_intake`, `set_document_status`, `create_*_client`)
are reachable. They have no HTTP route — the app registers only the three
`/api/withholding/*` endpoints — and the MCP server is a **separate process**
speaking HTTP that exposes only three stateless withholding tools. So the critique's
"an MCP server in the same process" is **wrong**. The write surface looks latent
rather than live; the caller trace was not finished.

## Files

| | |
|---|---|
| `01-operating-model.md` | The domain model a tax practice runs on: entities, the return lifecycle as a state machine, the work-item model, recurring obligations |
| `02-gap-analysis-and-roadmap.md` | What SATC has vs. needs, the critical path, vertical slices, and what NOT to build |
| `03-ai-boundary.md` | Where a local 8B model may act, what the engine must verify, the choke points, the scoreboard |
| `04-critique.md` | **Read first.** What the other three missed, asserted beyond evidence, or got wrong |

## Gaps the critique found in all three (not covered anywhere)

Amended/superseding returns and the §6511 refund clock · notice response and
representation as an engagement type (SSTS No. 4) · planning and projections ·
**the owner's own capacity and scheduling** — the plan models demand and deadlines
and never models supply · trial balance / book-to-tax for business returns ·
disengagement and client continuance · state filings as separate submissions with
their own ACKs · litigation hold suspending the retention clock.

## Before building anything from this

None of it is a spec. The critique's runner-up risk is that the roadmap front-loads
a large compliance substrate ahead of any capability the owner can use, while the
one feature that pays on day one — prior-year omission diff plus a rendered chase
draft — sits behind all of it. Grill the sequencing before writing code.
