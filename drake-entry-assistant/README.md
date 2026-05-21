# Drake Entry Assistant

Drake Entry Assistant (DEA) is a **local-first Python tool** for reducing repetitive tax data entry into Drake Tax Software.

## Project Goal

DEA helps users:
- Load taxpayer/W-2 data from source files.
- Validate and normalize that data.
- Generate deterministic entry action plans.
- Execute plans through a selected adapter (or simulate safely).

DEA does **not** replace professional tax judgment and does not perform full return preparation.

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

## Execution Modes (Planned)

- **Dry run / simulation** using `FakeDrakeAdapter` (current placeholder).
- **Future live adapter mode** for controlled data entry (not implemented in this phase).

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
