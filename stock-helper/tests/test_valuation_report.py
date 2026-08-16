"""End-to-end (offline): ingest AAPL fixtures → build report → assert the
valuation / quality-forensic sections render and persist, and that a
point-in-time replay leaves the composed valuation off (never leaking prices)."""

from datetime import date

from sqlmodel import select

from conftest import AAPL_FACTS, load_fixture, transport_for
from stock_helper.connectors.sec import (
    COMPANY_FACTS_URL,
    SUBMISSIONS_URL,
    TICKER_MAP_URL,
    SecClient,
)
from stock_helper.ingestion.sec_ingest import fetch_and_store
from stock_helper.reports.tearsheet import build_report, render_markdown
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import (
    QualityComponent,
    QualityFactorRow,
    Valuation,
    ValuationAssumption,
)
from stock_helper.storage.queries import (
    find_company,
    load_quality_factors,
    load_valuation,
)


def _ingest(settings) -> None:
    init_db(settings)
    routes = {
        TICKER_MAP_URL: load_fixture("company_tickers.json"),
        SUBMISSIONS_URL.format(cik=320193): load_fixture("submissions_aapl.json"),
        COMPANY_FACTS_URL.format(cik=320193): AAPL_FACTS,
    }
    client = SecClient(settings, transport=transport_for(routes))
    with get_session(settings) as session:
        fetch_and_store("AAPL", session, client)


def test_valuation_sections_render(settings):
    _ingest(settings)
    with get_session(settings) as session:
        report = build_report(session, "AAPL", settings)

    assert report.valuation is not None
    markdown = render_markdown(report)
    assert "\n## Valuation\n" in markdown
    assert "\n## Quality, distress & forensic screens\n" in markdown
    # Headline lines are present even when price data is off (rendered as n/m).
    assert "DCF fair value / share" in markdown
    assert "Reverse-DCF implied FCF growth" in markdown
    assert "Beneish M-score" in markdown
    # The forensic section must state screens-not-verdicts.
    assert "not accusations of fraud" in markdown.lower()
    # New valuation signals appear on the scorecard.
    assert "Intrinsic margin of safety" in markdown
    assert "Piotroski F-score" in markdown


def test_valuation_and_quality_rows_persist(settings):
    _ingest(settings)
    with get_session(settings) as session:
        build_report(session, "AAPL", settings)

    with get_session(settings) as session:
        company = find_company(session, "AAPL")

        valuation = load_valuation(session, company)
        assert valuation is not None
        assert valuation.ticker == "AAPL"
        assert valuation.as_of_date is None
        assert VALUATION_MARKER in valuation.engine_version

        # Assumptions (DCF inputs) are stored for the audit trail.
        assumptions = session.exec(
            select(ValuationAssumption).where(
                ValuationAssumption.valuation_id == valuation.id
            )
        ).all()
        assert {a.name for a in assumptions} >= {"discount_rate", "terminal_growth", "fcf_basis"}

        # Quality factor rows (+ components) persist, incl. Piotroski.
        factor_rows = load_quality_factors(session, company)
        assert factor_rows
        assert any(r.factor_key == "piotroski_f" for r in factor_rows)
        components = session.exec(select(QualityComponent)).all()
        assert components


def test_asof_replay_leaves_valuation_none(settings):
    _ingest(settings)
    with get_session(settings) as session:
        report = build_report(session, "AAPL", settings, as_of=date(2023, 6, 30))

    # Point-in-time replay does not reconstruct prices/peers -> no valuation.
    assert report.valuation is None
    markdown = render_markdown(report)
    assert "Point-in-time view" in markdown
    # The composed valuation section is skipped, not fabricated (the "### Valuation"
    # trailing-multiples scorecard row is a different, honestly-unavailable line).
    assert "\n## Valuation\n" not in markdown

    # And nothing was written to the current-view valuation slot.
    with get_session(settings) as session:
        company = find_company(session, "AAPL")
        assert load_valuation(session, company, as_of=None) is None
        # The as-of run also writes no valuation (extras were never built).
        assert session.exec(select(Valuation)).first() is None
        assert session.exec(select(QualityFactorRow)).first() is None


# engine_version marker, kept in one place so a version bump only touches here.
VALUATION_MARKER = "valuation-"
