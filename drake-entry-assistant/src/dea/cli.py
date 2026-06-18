"""Command-line interface for Drake Entry Assistant."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from dea.action_plan import generate_action_plan
from dea.adapters.discovery import run_and_write_discovery_report
from dea.adapters.fake import FakeDrakeAdapter
from dea.adapters.real import RealDrakeAdapter
from dea.config_loader import ConfigLoadError, load_screen_maps
from dea.excel_loader import ExcelLoadError, load_workbook_data
from dea.logging_utils import (
    action_step_to_log_record,
    write_entry_log_csv,
    write_entry_log_xlsx,
    write_validation_report_xlsx,
)
from dea.models import ActionPlan, Client, ClientBatch, SourceCellRef, ValidationIssue
from dea.output import write_action_plans_json
from dea.validation import validate_client_batch


@dataclass(slots=True)
class WorkflowContext:
    clients: list[Client]
    issues: list[ValidationIssue]
    output_dir: Path
    validation_report_path: Path
    source_cells: dict[str, SourceCellRef] = field(default_factory=dict)


def _default_config_dir(tax_year: int) -> Path:
    return Path("configs") / "drake" / str(tax_year)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dea", description="Drake Entry Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", required=True, type=Path, help="Path to intake workbook")
    common.add_argument("--tax-year", type=int, default=2025, help="Tax year for config lookup")
    common.add_argument("--config-dir", type=Path, default=None, help="Directory containing screen maps")
    common.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Output directory")
    common.add_argument("--client-id", default=None, help="Optional single client filter")
    common.add_argument("--fail-on-warning", action="store_true", help="Treat warnings as command failure")

    subparsers.add_parser("validate", parents=[common], help="Validate workbook only")
    subparsers.add_parser("dry-run", parents=[common], help="Generate masked dry-run plan and planned logs")
    subparsers.add_parser("run-fake", parents=[common], help="Execute action plan with FakeDrakeAdapter")

    live = subparsers.add_parser("run-live", parents=[common], help="Guarded live mode stub")
    live.add_argument("--live-drake", action="store_true", help="Explicitly acknowledge guarded live mode")

    discover = subparsers.add_parser("discover-drake", help="Read-only Drake discovery harness")
    discover.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Output directory")
    discover.add_argument(
        "--window-title-contains",
        default="Drake",
        help="Case-insensitive window-title filter for candidate Drake windows",
    )

    return parser


def _select_clients(batch: ClientBatch, client_id: str | None) -> list[Client]:
    if client_id is None:
        return list(batch.clients)
    return [client for client in batch.clients if client.client_id == client_id]


def _issue_counts(issues: list[ValidationIssue]) -> tuple[int, int, int]:
    errors = sum(1 for issue in issues if issue.severity == "ERROR")
    warnings = sum(1 for issue in issues if issue.severity == "WARNING")
    infos = sum(1 for issue in issues if issue.severity == "INFO")
    return errors, warnings, infos


def _prepare_context(args: argparse.Namespace) -> WorkflowContext:
    loaded = load_workbook_data(args.input)
    clients = _select_clients(loaded.client_batch, args.client_id)
    if args.client_id and not clients:
        raise ValueError(f"Client '{args.client_id}' not found in workbook")

    issues = validate_client_batch(ClientBatch(clients=clients), source_cells=loaded.source_cells)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_report_path = output_dir / "validation_report.xlsx"
    write_validation_report_xlsx(issues, validation_report_path)

    return WorkflowContext(
        clients=clients,
        issues=issues,
        output_dir=output_dir,
        validation_report_path=validation_report_path,
        source_cells=loaded.source_cells,
    )


def _print_validation_summary(ctx: WorkflowContext) -> None:
    errors, warnings, infos = _issue_counts(ctx.issues)
    print(
        f"clients={len(ctx.clients)} errors={errors} warnings={warnings} infos={infos} "
        f"validation_report={ctx.validation_report_path}"
    )


def _should_stop_for_validation(issues: list[ValidationIssue], fail_on_warning: bool) -> bool:
    errors, warnings, _ = _issue_counts(issues)
    if errors > 0:
        return True
    if fail_on_warning and warnings > 0:
        return True
    return False


def _build_action_plans(
    clients: list[Client],
    *,
    screen_maps,
    source_cells,
) -> list[ActionPlan]:
    return [generate_action_plan(client, screen_maps, source_cells=source_cells) for client in clients]


def _planned_records_from_plans(plans: list[ActionPlan]) -> list:
    records = []
    for plan in plans:
        for step in plan.steps:
            records.append(
                action_step_to_log_record(
                    step,
                    client_id=plan.client_id,
                    tax_year=plan.tax_year,
                    mode="dry_run",
                )
            )
    return records


def _command_validate(args: argparse.Namespace) -> int:
    try:
        ctx = _prepare_context(args)
    except (ExcelLoadError, ValueError) as exc:
        print(f"validation failed before rule checks: {exc}")
        return 1

    _print_validation_summary(ctx)
    if _should_stop_for_validation(ctx.issues, args.fail_on_warning):
        return 1
    return 0


def _load_config_maps(args: argparse.Namespace):
    config_dir = args.config_dir or _default_config_dir(args.tax_year)
    return load_screen_maps(config_dir)


def _command_dry_run(args: argparse.Namespace) -> int:
    try:
        ctx = _prepare_context(args)
    except (ExcelLoadError, ValueError) as exc:
        print(f"dry-run failed: {exc}")
        return 1

    _print_validation_summary(ctx)
    if _should_stop_for_validation(ctx.issues, args.fail_on_warning):
        return 1

    try:
        screen_maps = _load_config_maps(args)
        plans = _build_action_plans(ctx.clients, screen_maps=screen_maps, source_cells=ctx.source_cells)

        action_plan_path = ctx.output_dir / "action_plan.json"
        write_action_plans_json(plans, action_plan_path)

        planned_records = _planned_records_from_plans(plans)
        planned_csv = ctx.output_dir / "planned_entry_log.csv"
        planned_xlsx = ctx.output_dir / "planned_entry_log.xlsx"
        write_entry_log_csv(planned_records, planned_csv)
        write_entry_log_xlsx(planned_records, planned_xlsx)

        print(f"dry-run action plan: {action_plan_path}")
        print(f"planned entry logs: {planned_csv}, {planned_xlsx}")
        return 0
    except (ConfigLoadError, ValueError) as exc:
        print(f"dry-run failed: {exc}")
        return 1


def _execute_fake(plans: list[ActionPlan], screen_maps) -> tuple[bool, list, str | None]:
    records = []
    for plan in plans:
        adapter = FakeDrakeAdapter()
        result = adapter.execute_action_plan(plan, screen_maps)
        records.extend(result.records)
        if not result.success:
            return False, records, result.error_message
    return True, records, None


def _command_run_fake(args: argparse.Namespace) -> int:
    try:
        ctx = _prepare_context(args)
    except (ExcelLoadError, ValueError) as exc:
        print(f"run-fake failed: {exc}")
        return 1

    _print_validation_summary(ctx)
    if _should_stop_for_validation(ctx.issues, args.fail_on_warning):
        return 1

    try:
        screen_maps = _load_config_maps(args)
        plans = _build_action_plans(ctx.clients, screen_maps=screen_maps, source_cells=ctx.source_cells)

        ok, records, error = _execute_fake(plans, screen_maps)
        entry_csv = ctx.output_dir / "entry_log.csv"
        entry_xlsx = ctx.output_dir / "entry_log.xlsx"
        write_entry_log_csv(records, entry_csv)
        write_entry_log_xlsx(records, entry_xlsx)

        print(f"fake-run entry logs: {entry_csv}, {entry_xlsx}")
        if not ok:
            if error:
                print(f"fake execution failed: {error}")
            return 1
        return 0
    except (ConfigLoadError, ValueError) as exc:
        print(f"run-fake failed: {exc}")
        return 1


def _execute_live_stub(plans: list[ActionPlan], screen_maps, live_enabled: bool) -> tuple[bool, list, str | None]:
    records = []
    adapter = RealDrakeAdapter(live_enabled=live_enabled)
    for plan in plans:
        result = adapter.execute_action_plan(plan, screen_maps)
        records.extend(result.records)
        if not result.success:
            return False, records, result.error_message
    return True, records, None


def _command_run_live(args: argparse.Namespace) -> int:
    if not args.live_drake:
        print("run-live is blocked unless --live-drake is explicitly provided")
        return 1

    try:
        ctx = _prepare_context(args)
    except (ExcelLoadError, ValueError) as exc:
        print(f"run-live failed: {exc}")
        return 1

    _print_validation_summary(ctx)
    if _should_stop_for_validation(ctx.issues, args.fail_on_warning):
        return 1

    try:
        screen_maps = _load_config_maps(args)
        plans = _build_action_plans(ctx.clients, screen_maps=screen_maps, source_cells=ctx.source_cells)

        ok, records, error = _execute_live_stub(plans, screen_maps, live_enabled=True)
        entry_csv = ctx.output_dir / "entry_log.csv"
        entry_xlsx = ctx.output_dir / "entry_log.xlsx"
        write_entry_log_csv(records, entry_csv)
        write_entry_log_xlsx(records, entry_xlsx)

        print(f"live-run entry logs: {entry_csv}, {entry_xlsx}")
        if not ok:
            if error:
                print(error)
            return 1
        return 0
    except (ConfigLoadError, ValueError) as exc:
        print(f"run-live failed: {exc}")
        return 1


def _command_discover_drake(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    result, report_path = run_and_write_discovery_report(
        output_dir=output_dir,
        window_title_contains=args.window_title_contains,
    )

    print(f"discovery report: {report_path}")
    print(
        f"platform={result.platform} supported_platform={result.supported_platform} "
        f"drake_window_found={result.drake_window_found} dependency_available={result.dependency_available}"
    )

    if result.selected_window_title:
        print(f"selected_window={result.selected_window_title}")
    if result.warnings:
        for warning in result.warnings:
            print(f"warning: {warning}")
    if result.errors:
        for error in result.errors:
            print(f"error: {error}")

    # Discovery is diagnostic and read-only; always exit gracefully.
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _command_validate(args)
    if args.command == "dry-run":
        return _command_dry_run(args)
    if args.command == "run-fake":
        return _command_run_fake(args)
    if args.command == "run-live":
        return _command_run_live(args)
    if args.command == "discover-drake":
        return _command_discover_drake(args)

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
