# Manual Drake Acceptance Checklist (Dummy Data Only)

This checklist is for future controlled acceptance runs after live automation is implemented.

Current state: live Drake entry is not implemented in DEA and should remain blocked.

## Preconditions

- Drake is installed and manually launchable by an operator.
- DEA environment is set up and tests are passing.
- You are using synthetic demo data only.
- No real client/taxpayer data is in the workbook or outputs.

## Environment Safety

- Confirm output directory is local and controlled.
- Confirm no cloud-synced temp or output path is used by default.
- Confirm operator understands stop-first behavior on unexpected states.

## Required Preparation Sequence

1. Create/open a dummy Drake client manually.
2. Confirm expected tax year is correct in Drake.
3. Run `dea validate` first.
4. Run `dea dry-run` next.
5. Review masked `action_plan.json` and planned logs.
6. Run `dea run-fake` and verify expected fake execution behavior.
7. Do not run live mode until explicit implementation and approval are complete.

## Screen 1 Manual Checks

- Taxpayer name fields match expected synthetic inputs.
- Filing status target field is mapped correctly.
- Address fields align with configured screen-map order.
- Spouse fields are present/omitted per filing status and data.

## W-2 Manual Checks

- Employer EIN/Name mapping is correct.
- W-2 box fields follow screen-map order.
- Manual-review and unsupported fields are skipped rather than guessed.

## Expected Results

- Validation issues are explicitly reported with source sheet/cell.
- Dry-run outputs contain masked values only.
- Execution stops on first failure condition.
- Logs are written for traceability.

## Stop Conditions (Do Not Continue)

- Unexpected Drake screen or popup.
- Missing expected screen markers.
- Missing target field.
- Validation ERROR issues.
- Any ambiguity in field mapping.

## Failure Recovery

1. Stop immediately.
2. Review `validation_report.xlsx` and entry logs.
3. Fix source workbook or screen-map config.
4. Re-run `validate`, then `dry-run`, then `run-fake`.
5. Only resume manual Drake checks after deterministic local pass.

## Entry Log Review

- Confirm statuses are appropriate (`ENTERED`, `SKIPPED_*`, `FAILED_*`).
- Confirm masked values are present and raw sensitive identifiers are not exposed.

## Before Continuing Return Work

- Perform manual review of all entered/skipped fields.
- Confirm unresolved manual-review items are handled by a human operator.

## When Drake Layout Changes

1. Update YAML under `configs/drake/<tax_year>/`.
2. Re-run config-loader and action-plan tests.
3. Re-run full suite before any acceptance execution.
