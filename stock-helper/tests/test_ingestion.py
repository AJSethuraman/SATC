"""Filing metadata + facts ingestion into the database."""

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
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import CompanyFact, Filing, SecurityIdentifier


def ingest_aapl(settings):
    init_db(settings)
    routes = {
        TICKER_MAP_URL: load_fixture("company_tickers.json"),
        SUBMISSIONS_URL.format(cik=320193): load_fixture("submissions_aapl.json"),
        COMPANY_FACTS_URL.format(cik=320193): AAPL_FACTS,
    }
    client = SecClient(settings, transport=transport_for(routes))
    with get_session(settings) as session:
        company = fetch_and_store("aapl", session, client)
        session.refresh(company)
        return company


def test_company_identity_and_bucket(settings):
    company = ingest_aapl(settings)
    assert company.cik == 320193
    assert company.name == "Apple Inc."
    assert company.sic == "3571"
    assert company.industry_bucket == "technology"
    assert company.retrieved_at is not None


def test_filing_metadata(settings):
    company = ingest_aapl(settings)
    with get_session(settings) as session:
        filings = session.exec(select(Filing).where(Filing.company_id == company.id)).all()
        forms = {f.form for f in filings}
        assert forms == {"10-Q", "8-K", "10-K", "10-K/A"}  # S-8 filtered out
        ten_k = next(f for f in filings if f.form == "10-K")
        assert ten_k.accession == "0000320193-24-000123"
        assert ten_k.filed_date == date(2024, 11, 1)
        assert ten_k.period_end == date(2024, 9, 28)
        assert ten_k.acceptance_datetime is not None
        assert "0000320193-24-000123" in ten_k.index_url
        amendment = next(f for f in filings if f.form == "10-K/A")
        assert amendment.is_amendment


def test_ticker_row_created(settings):
    company = ingest_aapl(settings)
    with get_session(settings) as session:
        identifier = session.exec(
            select(SecurityIdentifier).where(SecurityIdentifier.company_id == company.id)
        ).one()
        assert identifier.ticker == "AAPL"
        assert identifier.exchange == "Nasdaq"


def test_selected_facts_stored_with_provenance(settings):
    company = ingest_aapl(settings)
    with get_session(settings) as session:
        facts = session.exec(
            select(CompanyFact).where(
                CompanyFact.company_id == company.id, CompanyFact.metric_key == "revenue"
            )
        ).all()
        assert len(facts) == 3
        assert all(f.accession for f in facts)
        assert all(f.filed_date is not None for f in facts)
        assert all("companyfacts" in f.source_url for f in facts)


def test_reingest_is_idempotent(settings):
    ingest_aapl(settings)
    company = ingest_aapl(settings)
    with get_session(settings) as session:
        filings = session.exec(select(Filing).where(Filing.company_id == company.id)).all()
        assert len(filings) == 4
        revenue_facts = session.exec(
            select(CompanyFact).where(
                CompanyFact.company_id == company.id, CompanyFact.metric_key == "revenue"
            )
        ).all()
        assert len(revenue_facts) == 3
