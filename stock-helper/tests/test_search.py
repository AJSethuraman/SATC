"""Full-text search over filing sections (FTS5 with LIKE fallback)."""

from datetime import UTC, date, datetime

from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import Company, Filing, FilingSection
from stock_helper.storage.search import rebuild_fts, search_sections


def seed_sections(settings):
    init_db(settings)
    with get_session(settings) as session:
        company = Company(cik=1, name="Test Co", retrieved_at=datetime.now(UTC))
        session.add(company)
        session.flush()
        filing = Filing(
            company_id=company.id, accession="0000000001-24-000001", form="10-K",
            filed_date=date(2024, 11, 1), retrieved_at=datetime.now(UTC),
        )
        session.add(filing)
        session.flush()
        for i, text in enumerate(
            [
                "Supply chain disruption could materially harm our operations.",
                "We repurchase shares under a board-authorized program.",
            ]
        ):
            session.add(
                FilingSection(
                    filing_id=filing.id, section_name="risk_factors",
                    chunk_id=f"0000000001-24-000001:risk_factors:{i}",
                    chunk_index=i, text=text, parser_version="test",
                    created_at=datetime.now(UTC),
                )
            )
        session.commit()
        count = rebuild_fts(session)
        assert count == 2


def test_fts_search_and_snippets(settings):
    seed_sections(settings)
    with get_session(settings) as session:
        hits = search_sections(session, "supply chain")
        assert len(hits) == 1
        assert hits[0].chunk_id.endswith(":0")
        assert "supply" in hits[0].snippet.lower()
        assert search_sections(session, "nonexistentterm") == []
        assert search_sections(session, "") == []


def test_rebuild_is_idempotent(settings):
    seed_sections(settings)
    with get_session(settings) as session:
        assert rebuild_fts(session) == 2  # re-run does not duplicate
        assert len(search_sections(session, "shares")) == 1
