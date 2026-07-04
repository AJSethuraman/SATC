"""Typer CLI — the primary local entrypoint (`stock-helper …`)."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from stock_helper.core.config import get_settings
from stock_helper.core.logging import configure_logging

app = typer.Typer(
    name="stock-helper",
    help="Local-first stock research helper. Research aid — not investment advice.",
    no_args_is_help=True,
)
console = Console()


def _setup():
    settings = get_settings()
    configure_logging(settings.log_level)
    return settings


def _parse_cli_date(value: str | None):
    from datetime import date

    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        console.print(f"[red]✗[/red] Invalid date {value!r} — expected YYYY-MM-DD.")
        raise typer.Exit(1) from exc


@app.command()
def init() -> None:
    """Create data folders and initialize the local SQLite database."""
    settings = _setup()
    from stock_helper.storage.db import init_db

    init_db(settings)
    console.print(f"[green]✓[/green] Data directories created under {settings.data_dir}/")
    console.print(f"[green]✓[/green] Database initialized at {settings.db_url}")
    try:
        settings.require_sec_user_agent()
        console.print("[green]✓[/green] SEC_USER_AGENT configured")
    except RuntimeError as exc:
        console.print(f"[yellow]![/yellow] {exc}")


@app.command("fetch-sec")
def fetch_sec(
    ticker: str,
    with_documents: bool = typer.Option(
        False, "--with-documents",
        help="Also download the latest 10-K/10-Q primary document and extract sections (best-effort).",
    ),
) -> None:
    """Fetch SEC submissions + XBRL company facts for TICKER and store them."""
    settings = _setup()
    import httpx

    from stock_helper.connectors.sec import SecClient, TickerNotFoundError
    from stock_helper.ingestion.sec_ingest import fetch_and_store
    from stock_helper.storage.db import get_session, init_db

    init_db(settings)
    try:
        client = SecClient(settings)
    except RuntimeError as exc:  # missing/placeholder SEC_USER_AGENT
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc
    try:
        with get_session(settings) as session:
            company = fetch_and_store(ticker, session, client, with_documents=with_documents)
            console.print(
                f"[green]✓[/green] {company.name} (CIK {company.cik}, "
                f"SIC {company.sic or 'n/a'}, bucket [bold]{company.industry_bucket}[/bold]) stored."
            )
    except TickerNotFoundError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc
    except httpx.HTTPError as exc:
        console.print(
            f"[red]✗[/red] SEC request failed ({exc.__class__.__name__}: {exc}). "
            "Check network access to sec.gov / data.sec.gov and retry; cached "
            "responses under data/raw/sec/ are reused when available."
        )
        raise typer.Exit(1) from exc
    finally:
        client.close()
    console.print(f"Next: [bold]stock-helper build-report {ticker.upper()}[/bold]")


@app.command("fetch-universe")
def fetch_universe_cmd(
    top: int = typer.Option(
        None, "--top",
        help="Fetch the first N companies from the SEC ticker file "
        "(ordered roughly by market cap).",
    ),
    tickers: str = typer.Option(
        None, "--tickers", help="Comma-separated tickers to fetch (overrides --top)."
    ),
    tickers_file: str = typer.Option(
        None, "--tickers-file", help="File with one ticker per line (overrides --top)."
    ),
    refresh_days: float = typer.Option(
        7.0, help="Skip tickers fetched within this many days (resumable runs)."
    ),
    with_documents: bool = typer.Option(
        False, "--with-documents",
        help="Also download/extract filing documents per ticker (much slower).",
    ),
) -> None:
    """Bulk-fetch many tickers to build a wide local universe.

    Widens peer percentiles and enables cross-company calibration. Respects the
    SEC throttle (~2 requests/ticker): 100 tickers ≈ 1 min, 500 ≈ 4 min."""
    settings = _setup()
    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

    from stock_helper.connectors.sec import SecClient
    from stock_helper.ingestion.universe import fetch_universe
    from stock_helper.storage.db import get_session, init_db

    if not top and not tickers and not tickers_file:
        console.print("[red]✗[/red] Pass --top N, --tickers, or --tickers-file.")
        raise typer.Exit(1)
    ticker_list = None
    if tickers:
        ticker_list = tickers.split(",")
    elif tickers_file:
        ticker_list = Path(tickers_file).read_text().split()

    init_db(settings)
    try:
        client = SecClient(settings)
    except RuntimeError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeRemainingColumn(),
        console=console,
    ) as bar:
        task = bar.add_task("fetching", total=None)

        def on_progress(ticker: str, status: str, i: int, n: int) -> None:
            bar.update(task, total=n, completed=i, description=f"{ticker} ({status})")

        try:
            with get_session(settings) as session:
                result = fetch_universe(
                    session, client,
                    top=top, tickers=ticker_list,
                    refresh_days=refresh_days, with_documents=with_documents,
                    progress=on_progress,
                )
        finally:
            client.close()

    console.print(
        f"[green]✓[/green] Universe fetch: {len(result.fetched)} fetched, "
        f"{len(result.skipped)} fresh (skipped), {len(result.failed)} failed "
        f"of {result.total}."
    )
    for ticker, reason in result.failed[:10]:
        console.print(f"  [yellow]![/yellow] {ticker}: {reason}")
    if len(result.failed) > 10:
        console.print(f"  …{len(result.failed) - 10} more failures (see logs)")
    console.print(
        "Peer percentiles now use this wider universe automatically. "
        "Next: [bold]stock-helper build-report TICKER[/bold]"
    )


@app.command("build-report")
def build_report_cmd(
    ticker: str,
    as_of: str = typer.Option(
        None, "--as-of",
        help="Point-in-time view date (YYYY-MM-DD): use only facts/filings filed "
        "on or before this date, with originally-filed values instead of restatements.",
    ),
) -> None:
    """Compute metrics + signals for TICKER and write a Markdown tear sheet."""
    settings = _setup()
    from stock_helper.reports.tearsheet import (
        CompanyNotFetchedError,
        build_report,
        record_output_path,
        write_report,
    )
    from stock_helper.storage.db import get_session, init_db

    init_db(settings)
    as_of_date = _parse_cli_date(as_of)
    try:
        with get_session(settings) as session:
            report = build_report(session, ticker, settings, as_of=as_of_date)
            path = write_report(report, settings)
            if report.run_id is not None:
                record_output_path(session, report.run_id, path)
    except CompanyNotFetchedError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc

    ok = sum(1 for s in report.signals if s.outcome.status == "OK")
    if as_of_date:
        console.print(f"[cyan]ℹ[/cyan] Point-in-time view as of {as_of_date}")
    console.print(f"[green]✓[/green] Report written: [bold]{path}[/bold]")
    console.print(
        f"  Signals: {ok} evaluated, "
        f"{sum(1 for s in report.signals if s.outcome.status == 'NOT_APPLICABLE')} n/a (industry), "
        f"{sum(1 for s in report.signals if s.outcome.status in ('UNAVAILABLE', 'INSUFFICIENT_DATA'))} missing data, "
        f"{sum(1 for s in report.signals if s.outcome.status == 'PLACEHOLDER')} planned. "
        f"Data confidence: [bold]{report.confidence.level}[/bold]"
    )


@app.command("signal-history")
def signal_history_cmd(
    ticker: str,
    start: str = typer.Option(None, help="Earliest as-of date (YYYY-MM-DD)."),
    end: str = typer.Option(None, help="Latest as-of date (YYYY-MM-DD)."),
    with_outcomes: bool = typer.Option(
        False, "--with-outcomes",
        help="Join exploratory forward returns from the non-canonical price source "
        "(requires ENABLE_PRICE_DATA=true). Not a backtest; no performance claim.",
    ),
) -> None:
    """Replay the scorecard at each past 10-K/10-Q filing date (point-in-time).

    Stores SignalHistory rows — the raw material for future calibration."""
    settings = _setup()
    from stock_helper.signals.history import OUTCOME_CAVEAT, build_signal_history
    from stock_helper.storage.db import get_session, init_db
    from stock_helper.storage.queries import CompanyNotFetchedError

    init_db(settings)
    try:
        with get_session(settings) as session:
            points = build_signal_history(
                session, ticker,
                start=_parse_cli_date(start), end=_parse_cli_date(end),
                settings=settings, with_outcomes=with_outcomes,
            )
    except CompanyNotFetchedError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc

    if not points:
        console.print("[yellow]![/yellow] No 10-K/10-Q filing dates stored in that range. "
                      f"Run stock-helper fetch-sec {ticker.upper()} first.")
        raise typer.Exit(0)

    shown = points[-8:]  # most recent as-of dates
    table = Table(
        title=f"{ticker.upper()} — point-in-time signal history "
        f"({len(points)} dates, showing last {len(shown)})"
    )
    table.add_column("Signal")
    for point in shown:
        table.add_column(str(point.as_of), justify="center")
    icons = {"improving": "▲", "deteriorating": "▼", "stable": "▬", "mixed": "◆"}
    keys = [s.definition.key for s in shown[0].signals if s.definition.implemented]
    for key in keys:
        row = [key]
        for point in shown:
            outcome = next(s.outcome for s in point.signals if s.definition.key == key)
            row.append(icons.get(outcome.direction, "·") if outcome.status == "OK" else "·")
        table.add_row(*row)
    if with_outcomes:
        for horizon in (20, 60, 120):
            row = [f"fwd {horizon}d return*"]
            for point in shown:
                label = point.outcomes.get(horizon)
                row.append(f"{label.ret * 100:+.1f}%" if label else "—")
            table.add_row(*row)
    console.print(table)
    console.print("· = not applicable / no data at that date")
    if with_outcomes:
        console.print(f"[yellow]*[/yellow] {OUTCOME_CAVEAT}")
        from stock_helper.signals.history import calibration_summary

        cells = calibration_summary(points)
        if cells:
            calib = Table(
                title="Direction vs forward-return sign (sanity check — NOT validation)"
            )
            calib.add_column("Signal")
            calib.add_column("Horizon")
            calib.add_column("▲ then up")
            calib.add_column("▼ then up")
            for cell in cells:
                calib.add_row(
                    cell.signal_key,
                    f"{cell.horizon_days}d",
                    f"{cell.improving_up}/{cell.improving_total}"
                    if cell.improving_total else "—",
                    f"{cell.deteriorating_up}/{cell.deteriorating_total}"
                    if cell.deteriorating_total else "—",
                )
            console.print(calib)
            console.print(
                "[yellow]![/yellow] Tiny n, single company, no costs/benchmark/"
                "significance tests. Real validation is Phase 7."
            )
    console.print(
        f"[green]✓[/green] {len(points)} history dates stored "
        "(SignalHistory rows; rerun replaces previous history)."
    )


@app.command()
def info(ticker: str) -> None:
    """Print a quick terminal summary for TICKER (must be fetched first)."""
    settings = _setup()
    from stock_helper.reports.tearsheet import CompanyNotFetchedError, find_company, load_series
    from stock_helper.storage.db import get_session, init_db

    init_db(settings)
    try:
        with get_session(settings) as session:
            company = find_company(session, ticker)
            series = load_series(session, company)
            table = Table(title=f"{company.name} ({ticker.upper()})")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("CIK", str(company.cik))
            table.add_row("SIC", f"{company.sic or 'n/a'} — {company.sic_description or ''}")
            table.add_row("Industry bucket", company.industry_bucket)
            table.add_row("Canonical metrics mapped", str(len(series)))
            console.print(table)
    except CompanyNotFetchedError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command("run-ui")
def run_ui(port: int = 8501) -> None:
    """Launch the Streamlit UI."""
    _setup()
    ui_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ui_path), "--server.port", str(port)],
        check=False,
    )


@app.command("run-api")
def run_api(port: int = 8000) -> None:
    """Launch the FastAPI server."""
    _setup()
    import uvicorn

    uvicorn.run("stock_helper.api.main:api", port=port)


if __name__ == "__main__":
    app()
