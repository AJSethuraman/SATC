"""End-to-end (offline): ingest AAPL fixtures → build report → render Markdown."""

from sqlmodel import select

from conftest import AAPL_FACTS, load_fixture, transport_for
from stock_helper.connectors.sec import (
    COMPANY_FACTS_URL,
    SUBMISSIONS_URL,
    TICKER_MAP_URL,
    SecClient,
)
from stock_helper.ingestion.sec_ingest import fetch_and_store
from stock_helper.reports.tearsheet import build_report, render_markdown, write_report
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import EvidenceReference, ReportRun, SignalResult


def build(settings):
    init_db(settings)
    routes = {
        TICKER_MAP_URL: load_fixture("company_tickers.json"),
        SUBMISSIONS_URL.format(cik=320193): load_fixture("submissions_aapl.json"),
        COMPANY_FACTS_URL.format(cik=320193): AAPL_FACTS,
    }
    client = SecClient(settings, transport=transport_for(routes))
    with get_session(settings) as session:
        fetch_and_store("AAPL", session, client)
    with get_session(settings) as session:
        report = build_report(session, "AAPL", settings)
    return report


def test_report_builds_and_persists(settings):
    report = build(settings)
    assert report.ticker == "AAPL"
    assert report.confidence.level in ("low", "medium", "high")
    assert report.run_id is not None
    with get_session(settings) as session:
        run = session.exec(select(ReportRun)).one()
        assert run.ticker == "AAPL"
        results = session.exec(select(SignalResult)).all()
        assert results
        evidence = session.exec(select(EvidenceReference)).all()
        assert evidence  # OK signals carry stored evidence rows


def test_markdown_output(settings):
    report = build(settings)
    markdown = render_markdown(report)
    assert "Apple Inc. (AAPL)" in markdown
    assert "not investment advice" in markdown.lower()
    assert "Signal scorecard" in markdown
    assert "Revenue growth" in markdown
    assert "0000320193-24-000123" in markdown  # evidence accession appears
    assert "technology" in markdown

    path = write_report(report, settings)
    assert path.endswith(".md")


def test_missing_data_marked_not_crashing(settings):
    report = build(settings)
    statuses = {s.definition.key: s.outcome.status for s in report.signals}
    # AAPL fixture lacks debt & liquidity tags: honest UNAVAILABLE, no crash.
    assert statuses["debt_to_assets"] == "UNAVAILABLE"
    assert statuses["current_ratio"] == "UNAVAILABLE"
    assert statuses["revenue_growth_yoy"] == "OK"
    markdown = render_markdown(report)
    assert "unavailable" in markdown
