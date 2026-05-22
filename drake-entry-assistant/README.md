# Drake Entry Assistant

Drake Entry Assistant (DEA) is a local-first Python tool for validating intake data and preparing deterministic, masked Drake entry workflows.

## Milestone Status (Current)

Implemented now:
- Excel intake loading for `Clients` and `W2s`
- Validation engine with source-cell traceability
- YAML screen-map loading and validation
- Masked action-plan generation for Screen 1 and W-2
- Masked logging and validation-report writers
- Fake adapter execution simulation with safe stop conditions
- CLI commands: `validate`, `dry-run`, `run-fake`, `run-live` (guarded)
- Read-only `discover-drake` diagnostic harness

Not implemented yet:
- Live Drake UI automation
- Any real OS/UI interaction

## Safety Boundaries

- No process injection
- No `pyautogui`
- No `pywinauto`
- No screenshots or clipboard automation
- No real client data in project artifacts
- Drake-specific behavior remains in `configs/drake/...` and `src/dea/adapters/...`

## Installation

From `drake-entry-assistant/`:

```bash
python -m pip install -e .[dev]
```

## CLI Usage

Console script:

```bash
dea --help
```

Commands:

1. Validate only:

```bash
dea validate --input examples/sample_intake.xlsx --tax-year 2025 --output-dir outputs/demo
```

2. Dry-run (no adapter execution):

```bash
dea dry-run --input examples/sample_intake.xlsx --tax-year 2025 --output-dir outputs/demo
```

3. Fake execution:

```bash
dea run-fake --input examples/sample_intake.xlsx --tax-year 2025 --output-dir outputs/demo
```

4. Guarded live command (still refuses real entry):

```bash
dea run-live --input examples/sample_intake.xlsx --tax-year 2025 --output-dir outputs/demo --live-drake
```

5. Read-only Drake discovery:

```bash
dea discover-drake --output-dir outputs/discovery
dea discover-drake --window-title-contains Drake --output-dir outputs/discovery
```

`discover-drake` is diagnostic only:
- does not enter data
- does not click or type
- does not use screenshots
- does not use clipboard operations
- writes `discovery_report.json` for review

## Output Artifacts

By command, DEA writes artifacts under `--output-dir`:
- `validation_report.xlsx`
- `action_plan.json` (dry-run)
- `planned_entry_log.csv` / `planned_entry_log.xlsx` (dry-run)
- `entry_log.csv` / `entry_log.xlsx` (run-fake / run-live)

Action/log outputs contain masked values only.

## Generate Sample Workbook

DEA includes a deterministic synthetic workbook generator:

```bash
python -c "from dea.demo import create_sample_workbook; create_sample_workbook('examples/sample_intake.xlsx')"
```

This creates demo-only data. Do not use real taxpayer data.

## Run Tests

```bash
PYTHONPATH=src pytest -q
```

## Manual Acceptance Checklist

For future controlled Drake testing with dummy data only, see:
- `docs/manual_drake_acceptance_checklist.md`
