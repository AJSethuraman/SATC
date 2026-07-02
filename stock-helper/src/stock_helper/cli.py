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


@app.command("build-report")
def build_report_cmd(ticker: str) -> None:
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
    try:
        with get_session(settings) as session:
            report = build_report(session, ticker, settings)
            path = write_report(report, settings)
            if report.run_id is not None:
                record_output_path(session, report.run_id, path)
    except CompanyNotFetchedError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc

    ok = sum(1 for s in report.signals if s.outcome.status == "OK")
    console.print(f"[green]✓[/green] Report written: [bold]{path}[/bold]")
    console.print(
        f"  Signals: {ok} evaluated, "
        f"{sum(1 for s in report.signals if s.outcome.status == 'NOT_APPLICABLE')} n/a (industry), "
        f"{sum(1 for s in report.signals if s.outcome.status in ('UNAVAILABLE', 'INSUFFICIENT_DATA'))} missing data, "
        f"{sum(1 for s in report.signals if s.outcome.status == 'PLACEHOLDER')} planned. "
        f"Data confidence: [bold]{report.confidence.level}[/bold]"
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
