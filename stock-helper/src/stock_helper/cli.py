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
def value(
    ticker: str,
    as_of: str = typer.Option(None, "--as-of", help="Point-in-time view date (YYYY-MM-DD)."),
) -> None:
    """Value TICKER on fundamentals: DCF fair value, reverse-DCF, multiples,
    quality factors, and forensic/stress flags. Research aid — not advice."""
    settings = _setup()
    from stock_helper.core.format import money, multiple, pct, per_share
    from stock_helper.features.context import build_market_context
    from stock_helper.features.metrics import compute_derived_metrics
    from stock_helper.storage.db import get_session, init_db
    from stock_helper.storage.queries import CompanyNotFetchedError, find_company, load_series
    from stock_helper.valuation.compose import compute_valuation

    init_db(settings)
    as_of_date = _parse_cli_date(as_of)
    try:
        with get_session(settings) as session:
            company = find_company(session, ticker)
            series = load_series(session, company, as_of=as_of_date)
            derived = compute_derived_metrics(series)
            market = None if as_of_date else build_market_context(ticker.upper(), series, settings)
            val = compute_valuation(
                session, company, ticker.upper(), series, derived, market, settings, as_of_date
            )
    except CompanyNotFetchedError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"\n[bold]{company.name} ({ticker.upper()})[/bold] · "
                  f"bucket [bold]{val.bucket}[/bold] · method {val.dcf.method if val.dcf else 'n/a'}")
    if val.price is not None:
        console.print(f"Price: {money(val.price)}/sh ({val.price_date}) — non-canonical")

    dcf = val.dcf
    vt = Table(title="Intrinsic value", show_header=False)
    vt.add_column("k")
    vt.add_column("v")
    if dcf and dcf.status == "OK":
        vt.add_row("Fair value / share", per_share(dcf.fair_value_per_share))
        vt.add_row("Margin of safety", pct(dcf.margin_of_safety) if dcf.margin_of_safety is not None else "n/a (no price)")
        vt.add_row("Base FCF", money(dcf.base_fcf))
        vt.add_row("Assumed growth / discount",
                   f"{pct(dcf.stage1_growth)} / {pct(dcf.discount_rate)}")
        vt.add_row("Terminal value weight", pct(dcf.terminal_weight) if dcf.terminal_weight else "n/a")
    elif dcf:
        vt.add_row("DCF", f"{dcf.status}: {'; '.join(dcf.caveats) or dcf.method}")
    if val.reverse and val.reverse.implied_growth is not None:
        vt.add_row("Reverse-DCF: price implies growth of", pct(val.reverse.implied_growth))
    coc = val.cost_of_capital
    if coc is not None:
        vt.add_row("Cost of equity (CAPM Ke = DCF discount)",
                   f"{pct(coc.ke)}  (rf {pct(coc.risk_free)} + β {coc.beta:.2f} × ERP {pct(coc.erp)})")
        vt.add_row("WACC (for ROIC spread)", pct(coc.wacc))
    mc = val.monte_carlo
    if mc is not None:
        pu = f" · P(undervalued) {pct(mc.prob_undervalued)}" if mc.prob_undervalued is not None else ""
        vt.add_row("Monte Carlo fair value (p10–p90)",
                   f"{per_share(mc.p10)} – {per_share(mc.p90)} (median {per_share(mc.median)}){pu}")
    ri = val.residual_income
    if ri is not None and ri.fair_value_per_share is not None:
        vt.add_row("Residual-income fair value / share", per_share(ri.fair_value_per_share))
    ep = val.economic_profit
    if ep is not None and ep.spread is not None:
        verdict = "creates value" if ep.creates_value else "erodes value"
        vt.add_row("Economic profit (ROIC − WACC)", f"{pct(ep.spread)} — {verdict}")
    console.print(vt)
    if coc is not None and coc.caveats:
        console.print(f"[dim]Cost-of-capital note: {coc.caveats[0]}[/dim]")

    if val.multiples:
        mt = Table(title="Valuation multiples")
        mt.add_column("Multiple")
        mt.add_column("Value", justify="right")
        mt.add_column("Peer implied upside", justify="right")
        for key, m in val.multiples.items():
            up = val.peer_relative.get(key)
            up_txt = pct(up.upside_pct) if up and up.upside_pct is not None else "—"
            is_yield = key.endswith("_yield")
            mt.add_row(m.label, pct(m.value) if is_yield and m.value is not None
                       else (multiple(m.value) if not is_yield else "n/m"), up_txt)
        console.print(mt)

    if val.quality:
        qt = Table(title=f"Quality & distress ({val.quality.metric_set})")
        qt.add_column("Factor")
        qt.add_column("Value", justify="right")
        qt.add_column("Note")
        for _key, f in val.quality.factors.items():
            if f.status != "OK":
                continue
            note = f.detail.get("zone", "") if getattr(f, "detail", None) else ""
            qt.add_row(f.label, f"{f.value:.2f}" if f.value is not None else "n/a", note)
        console.print(qt)

    # Forensic / stress panel — the fraud/stress scanner
    ft = Table(title="Forensic / stress flags (research screens — NOT accusations)")
    ft.add_column("Signal")
    ft.add_column("Reading")
    if val.beneish and val.beneish.m_score is not None:
        ft.add_row("Beneish M-Score",
                   f"{val.beneish.m_score:.2f} — "
                   + ("[red]possible manipulation (> -1.78)[/red]" if val.beneish.flag
                      else "below manipulation threshold"))
    if val.stress:
        if val.stress.stress_flags:
            for key, reason, _v in val.stress.stress_flags:
                ft.add_row(key, reason)
        else:
            ft.add_row("stress scan", "no red flags on latest year")
    console.print(ft)
    console.print("\n[dim]Research aid — not investment advice. "
                  "Estimates from explicit assumptions; flags are screens, not verdicts.[/dim]")


@app.command()
def screen(
    screen_name: str = typer.Option(
        None, "--screen",
        help="Named saved screen to run (deep_value, quality_compounders, "
        "magic_formula_top, distress_watch, manipulation_watch).",
    ),
    run_all: bool = typer.Option(False, "--all", help="Run every saved screen."),
    top: int = typer.Option(15, "--top", help="Show the top N candidates per screen."),
    as_of: str = typer.Option(
        None, "--as-of", help="Point-in-time view date (YYYY-MM-DD)."
    ),
) -> None:
    """Cross-sectional outlier SCREENER over the local universe.

    Ranks companies on already-computed valuation/quality/forensic figures
    (robust median/MAD z-scores, within industry bucket when large enough).
    These are CANDIDATE screens for further reading — unscored and NOT
    backtested; distress/manipulation screens are never verdicts."""
    settings = _setup()
    from stock_helper.core.format import pct
    from stock_helper.screening.engine import build_cross_section
    from stock_helper.screening.screens import SAVED_SCREENS, run_screen
    from stock_helper.storage.db import get_session, init_db

    if not run_all and not screen_name:
        console.print("[red]✗[/red] Pass --screen NAME or --all. Available: "
                      + ", ".join(SAVED_SCREENS))
        raise typer.Exit(1)
    if screen_name and screen_name not in SAVED_SCREENS:
        console.print(f"[red]✗[/red] Unknown screen {screen_name!r}. Available: "
                      + ", ".join(SAVED_SCREENS))
        raise typer.Exit(1)

    init_db(settings)
    as_of_date = _parse_cli_date(as_of)
    with get_session(settings) as session:
        cs = build_cross_section(session, settings=settings, as_of=as_of_date)

    if not cs.rows:
        console.print("[yellow]![/yellow] Empty universe. Fetch some companies first: "
                      "[bold]stock-helper fetch-universe --top 100[/bold]")
        raise typer.Exit(0)

    specs = list(SAVED_SCREENS.values()) if run_all else [SAVED_SCREENS[screen_name]]
    n_sectors = len({r.bucket for r in cs.rows})
    console.print(
        f"[cyan]ℹ[/cyan] Universe: {len(cs.rows)} companies across {n_sectors} bucket(s)"
        + (f" · point-in-time as of {as_of_date}" if as_of_date else "")
    )

    def _score(v: float | None) -> str:
        return f"{v:+.2f}" if v is not None else "—"

    for spec in specs:
        ranked = run_screen(cs, spec)[:top]
        table = Table(title=f"{spec.label} — {spec.description}")
        table.add_column("#", justify="right")
        table.add_column("Ticker")
        table.add_column("Bucket")
        table.add_column("FV gap", justify="right")
        table.add_column("Value z", justify="right")
        table.add_column("Quality z", justify="right")
        table.add_column("Flags")
        for e in ranked:
            fv = pct(e.fair_value_gap) if e.fair_value_gap is not None else "—"
            table.add_row(
                str(e.rank), e.ticker, e.bucket, fv,
                _score(e.value_score), _score(e.quality_score),
                ", ".join(e.flags) or "—",
            )
        if not ranked:
            table.add_row("—", "no candidates", "", "", "", "", "")
        console.print(table)

    console.print(
        "\n[dim]Candidate screens — NOT buy lists. Unscored and not backtested; "
        "distress/manipulation flags are screens to READ, never verdicts.[/dim]"
    )


@app.command()
def backtest(
    signal: str = typer.Option("value_composite", "--signal",
                               help="Signal to evaluate (value_composite, quality_composite, "
                               "earnings_yield, fcf_yield, piotroski_f)."),
    start: str = typer.Option(..., "--start", help="First rebalance date (YYYY-MM-DD)."),
    end: str = typer.Option(..., "--end", help="Last rebalance date (YYYY-MM-DD)."),
    step_days: int = typer.Option(63, "--step-days", help="Days between rebalances (~quarterly)."),
    horizon_days: int = typer.Option(63, "--horizon-days", help="Forward-return holding window (trading days)."),
    n_trials: int = typer.Option(1, "--n-trials", help="How many signal variants you've tried (Deflated-Sharpe penalty)."),
) -> None:
    """Walk-forward test whether SIGNAL sorted future returns (point-in-time).

    EDUCATIONAL ONLY: runs on non-canonical, survivorship-biased free prices —
    delisted names are absent, which inflates results. NOT a performance claim."""
    settings = _setup()
    from stock_helper.backtest.panel import SIGNAL_FUNCTIONS, run_backtest
    from stock_helper.backtest.verdict import backtest_verdict
    from stock_helper.storage.db import get_session, init_db

    if signal not in SIGNAL_FUNCTIONS:
        console.print(f"[red]✗[/red] Unknown signal {signal!r}. Choices: "
                      + ", ".join(sorted(SIGNAL_FUNCTIONS)))
        raise typer.Exit(1)
    start_d, end_d = _parse_cli_date(start), _parse_cli_date(end)
    init_db(settings)
    with get_session(settings) as session:
        result = run_backtest(
            session, signal_name=signal, start=start_d, end=end_d,
            step_days=step_days, horizon_days=horizon_days, settings=settings, n_trials=n_trials,
        )

    def _f(v, fmt="{:+.3f}"):
        return fmt.format(v) if v is not None else "—"

    # --- Plain-English verdict FIRST (the part you actually act on) ---
    v = backtest_verdict(result)
    color = {"good": "bold green", "bad": "bold red", "neutral": "bold yellow"}[v.tone]
    console.print()
    console.print(f"[{color}]VERDICT: {v.label}[/{color}] — testing '{signal}', "
                  f"{start} → {end}")
    console.print(f"[italic]{v.headline}[/italic]")
    for pt in v.plain_points:
        console.print(f"  • {pt}")
    console.print()

    # --- Detailed stats underneath, for the curious ---
    t = Table(title="Detailed stats (for reference)")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Rebalance dates tested", str(result.n_dates))
    t.add_row("Avg companies / date", _f(result.n_names_avg, "{:.0f}"))
    t.add_row("Skill score (−100..+100, 0=luck)",
              _f(round((result.mean_ic or 0) * 100), "{:+.0f}") if result.mean_ic is not None else "—")
    t.add_row("  ↳ raw IC / t-stat",
              f"{_f(result.mean_ic)} / {_f(result.ic_t_stat, '{:.2f}')}")
    t.add_row("Cheap-minus-expensive return / period", _f(result.quantile_spread_mean, "{:+.2%}"))
    t.add_row("Sharpe (annualized) — mostly market, ignore",
              _f(result.sharpe_annualized, "{:.2f}"))
    console.print(t)
    console.print("[dim]Reminder: free, survivorship-biased prices — delisted names are "
                  "absent, which flatters every number. Educational, not a performance claim.[/dim]")


@app.command("backtest-compare")
def backtest_compare(
    start: str = typer.Option(..., "--start", help="First rebalance date (YYYY-MM-DD)."),
    end: str = typer.Option(..., "--end", help="Last rebalance date (YYYY-MM-DD)."),
    step_days: int = typer.Option(63, "--step-days", help="Days between rebalances (~quarterly)."),
    horizon_days: int = typer.Option(63, "--horizon-days", help="Forward-return holding window."),
) -> None:
    """Test EVERY signal over the same period and rank them by skill — one table.

    Runs each available signal through the same walk-forward and shows a plain
    leaderboard so you can see at a glance which (if any) actually sorted future
    winners from losers. EDUCATIONAL: survivorship-biased free prices."""
    settings = _setup()
    from stock_helper.backtest.panel import SIGNAL_FUNCTIONS, run_backtest
    from stock_helper.backtest.verdict import backtest_verdict
    from stock_helper.storage.db import get_session, init_db

    start_d, end_d = _parse_cli_date(start), _parse_cli_date(end)
    init_db(settings)
    rows = []
    with get_session(settings) as session:
        for name in sorted(SIGNAL_FUNCTIONS):
            console.print(f"[dim]testing {name}…[/dim]")
            result = run_backtest(
                session, signal_name=name, start=start_d, end=end_d,
                step_days=step_days, horizon_days=horizon_days,
                settings=settings, n_trials=len(SIGNAL_FUNCTIONS),
            )
            v = backtest_verdict(result)
            rows.append((name, v, result))

    # Rank: best skill score first (None/ untestable sinks to the bottom).
    rows.sort(key=lambda r: (r[2].mean_ic if r[2].mean_ic is not None else -9), reverse=True)

    tone_tag = {"good": "[green]WORTH A LOOK[/green]",
                "bad": "[red]BACKWARDS[/red]",
                "neutral": "[yellow]NO EDGE[/yellow]"}
    t = Table(title=f"Signal leaderboard · {start} → {end} · {horizon_days}d hold")
    t.add_column("Signal")
    t.add_column("Verdict")
    t.add_column("Skill (−100..+100)", justify="right")
    t.add_column("Cheap−exp / period", justify="right")
    for name, v, result in rows:
        score = f"{round((result.mean_ic or 0) * 100):+d}" if result.mean_ic is not None else "—"
        spread = f"{result.quantile_spread_mean:+.2%}" if result.quantile_spread_mean is not None else "—"
        label = tone_tag.get(v.tone, v.label) if v.label != "COULDN'T TEST" else "[dim]couldn't test[/dim]"
        t.add_row(name, label, score, spread)
    console.print(t)
    console.print("\n[bold]How to read this:[/bold] 'Skill' is 0 for a coin flip; "
                  "positive means the cheaper/better-ranked stocks tended to win afterward. "
                  "Only [green]WORTH A LOOK[/green] cleared the not-luck bar — and even that "
                  "needs a longer, survivorship-free test before you'd trust it with money.")


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
