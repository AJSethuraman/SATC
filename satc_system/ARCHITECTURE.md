# SATC architecture — a map for refining one piece at a time

This document answers a single practical question: **"I want to change X — which
one place do I edit, and which test guards it?"**

The system is built as **separable, individually-refinable pieces**. A "piece" is
one process living in one place, with its own test, that you can change without
touching the rest. That is what lets us improve the tool steadily (and fold in
outside tools piece by piece) instead of wrestling one big script.

## The four layers

Almost every change maps to exactly one layer:

1. **Config (data, no code)** — `configs/`. Tax numbers, questionnaires, field
   mappings, line sheets. Edit a value here and nothing else moves.
2. **Pure logic (functions + tests)** — `src/satc/<area>/`. Readers, the
   estimator engine, intake/matching, workbook building. Each area is a folder of
   small functions you can test in isolation.
3. **State & persistence** — `src/satc/models/`, `src/satc/persistence/`,
   `src/satc/app/state.py`. The data shapes and how they're saved/loaded.
4. **UI (thin)** — `src/satc/app/` + `app/templates/`. Flask routes and Jinja
   templates. Changing a screen never changes the math.

**Golden rules**
- A tax-law value is **never** hardcoded — it lives in the crosswalk with a
  citation. (See the estimator below.)
- Every reader produces the same `ReadResult` and flows through the **same**
  staging/confirmation gate, so new readers inherit human review for free.
- Each piece has a test file. If you refine a piece, run its test.

## Where each process lives

| Process / "I want to change…" | Code | Config | Tests |
| --- | --- | --- | --- |
| **A tax-law value** (brackets, deductions, rates) | `src/satc/crosswalk/loader.py` | `configs/crosswalk/<JURIS>/<YEAR>.yaml` | `tests/test_crosswalk.py` |
| **How a document is read** (PDF/scan/photo/paystub) | `src/satc/ingest/readers/` | `configs/extraction/` | `tests/test_readers.py`, `tests/test_text_anchor.py`, `tests/test_local_readers.py`, `tests/test_paystub_reader.py` |
| **Doc classify / sort / split** | `src/satc/ingest/classify.py`, `sort.py`, `split.py` | — | `tests/test_classify.py`, `tests/test_sort.py`, `tests/test_split.py` |
| **Label → field mapping & staging** | `src/satc/ingest/extractors/mapping.py`, `staging_gate.py` | `configs/extraction/` | `tests/test_ingest.py`, `tests/test_staging_edits.py` |
| **Client intake / organizer / matching** | `src/satc/intake/` | `configs/workflows/` | `tests/test_intake*.py`, `tests/test_importer.py` |
| **Questionnaires / workflows** | `src/satc/intake/workflows.py`, `src/satc/app/workflow_views.py` | `configs/workflows/` | `tests/test_workflows_engine.py`, `tests/test_workflow_configs.py`, `tests/test_workflow_overrides.py` |
| **Withholding estimate** (the math) | `src/satc/withholding/engine.py` | `configs/crosswalk/federal/*.yaml` | `tests/test_withholding_engine.py` |
| **Reading a paystub → estimate** | `src/satc/ingest/readers/paystub.py`, `src/satc/withholding/intake.py` | — | `tests/test_paystub_reader.py` |
| **Prior-year roll-forward / pro forma** | `src/satc/proforma/` | — | `tests/test_proforma.py` |
| **Drake export** | `src/satc/drake/` | `configs/drake/` | `tests/test_drake.py`, `tests/test_input_generator.py` |
| **The Excel workbook** (sheets, layout) | `src/satc/workbook/` | `configs/line_sheets/` | `tests/test_build.py` |
| **Assembling the deliverable** | `src/satc/build.py` | — | `tests/test_build.py` |
| **PII masking** (SSN/EIN) | `src/satc/masking.py` | — | covered via reader/staging tests |
| **The data shapes** | `src/satc/models/` | — | `tests/test_foundation.py`, `tests/test_validation.py` |
| **Saving / loading / export** | `src/satc/persistence/` | — | `tests/test_persistence.py`, `tests/test_store_sample.py` |
| **A web screen / route** | `src/satc/app/server.py`, `intake_views.py`, `app/templates/*.html` | — | `tests/test_app*.py`, `tests/test_post.py` |
| **CLI / health checks** | `src/satc/cli.py`, `doctor.py`, `settings.py` | — | `tests/test_doctor.py` |

## Worked example: the withholding estimator

The estimator is the clearest illustration of "pieces you can refine alone." It is
five independent pieces, each changeable without disturbing the others:

| Piece | File | Refine it = |
| --- | --- | --- |
| Tax constants | `configs/crosswalk/federal/<year>.yaml` | edit a cited number — no code |
| The math | `src/satc/withholding/engine.py` | change a calculation, test in isolation |
| Crosswalk hookup | `src/satc/withholding/tax_data.py` | change *where* the numbers come from |
| Paystub reading | `src/satc/ingest/readers/paystub.py` | improve reading; math untouched |
| Confirmed-fields → input | `src/satc/withholding/intake.py` | change how a read paystub becomes an estimate |

The math (`engine.py`) is pure: give it inputs, it returns a projection — no UI, no
database — which is why a single line like "$78k single → $8,774" is a one-line
test. The numbers it uses come only from the crosswalk, so updating tax law is a
YAML edit, not a code change.

## How to add a piece (the pattern)

1. Put the logic in the right `src/satc/<area>/` folder as small functions.
2. Read inputs from `configs/` where they're data, not code.
3. Emit the area's shared shape (e.g. a reader returns `ReadResult`) so it joins
   the existing downstream path.
4. Add a `tests/test_<piece>.py` with a couple of hand-checked cases.
5. Wire the UI last, as a thin route + template.
