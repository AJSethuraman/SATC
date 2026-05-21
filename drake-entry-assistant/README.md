# Drake Entry Assistant

Drake Entry Assistant (DEA) is a **local-first Python tool** for reducing repetitive tax data entry into Drake Tax Software.

## Project Goal

DEA helps users:
- Load taxpayer/W-2 data from source files.
- Validate and normalize that data.
- Generate deterministic entry action plans.
- Execute plans through a selected adapter (or simulate safely).

DEA does **not** replace professional tax judgment and does not perform full return preparation, tax diagnostics, or e-filing.

## Architecture

DEA uses strict separation of concerns:

- **Core logic (`src/dea/`)**
  - Domain models
  - Validation pipeline
  - Data ingestion
  - Action-plan generation
  - Config loading and safe logging/masking
- **Drake-specific layer (`src/dea/adapters/` + `configs/drake/...`)**
  - Adapter interfaces and implementations
  - Screen mapping and field metadata in YAML

Rule: Drake-specific behavior stays in adapters/configs, not in core modules.

## Execution Modes

DEA is designed to support the following modes:

1. **validation-only**
   - Runs ingestion + normalization + validation checks only.
   - Produces validation output without producing or executing Drake entry actions.

2. **dry-run**
   - Produces an action plan from validated data.
   - Does not execute actions against any Drake target.

3. **fake-adapter execution**
   - Executes the action plan through `FakeDrakeAdapter`.
   - Records requested steps for testing and debugging without real UI automation.

4. **future live Drake mode (explicit enablement required)**
   - Reserved for a future adapter implementation.
   - Must require explicit runtime enablement and acceptance-test gating before use.
   - Not implemented in this scaffold.

## Verification Levels

DEA development and release validation should be staged:

- **Level 1: no Drake required**
  - Unit tests, import checks, config shape checks, and validation/action-plan logic tests.
- **Level 2: fake Drake adapter**
  - End-to-end workflow checks using `FakeDrakeAdapter` with synthetic data.
- **Level 3: real Drake acceptance testing (dummy/demo data only)**
  - Controlled acceptance tests in a dedicated environment with non-client demo data.

## Safety Standard

- No process injection.
- No UI automation libraries in this skeleton.
- No live Drake automation in this phase.
- No real client data.
- No full SSNs/EINs in examples, logs, tests, or docs.

## Current Status

This is an initial scaffold only. The following are placeholders:

- Excel loader
- Validation engine
- Action-plan generation
- Live Drake adapter behavior

The repository currently provides package structure, adapter boundaries, config placeholders, and import smoke tests.
