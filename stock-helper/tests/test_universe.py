"""Bulk universe fetch: selection, resume, and failure tolerance."""

import json

from sqlmodel import select

from conftest import AAPL_FACTS, fact_entry, load_fixture, make_companyfacts, transport_for
from stock_helper.connectors.sec import (
    COMPANY_FACTS_URL,
    SUBMISSIONS_URL,
    TICKER_MAP_URL,
    SecClient,
)
from stock_helper.ingestion.universe import fetch_universe, select_universe_tickers
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import Company

KEY_SUBMISSIONS = {
    "cik": "91576",
    "sic": "6022",
    "sicDescription": "State Commercial Banks",
    "name": "KeyCorp",
    "tickers": ["KEY"],
    "exchanges": ["NYSE"],
    "fiscalYearEnd": "1231",
    "entityType": "operating",
    "filings": {
        "recent": {
            "accessionNumber": ["0000091576-25-000012"],
            "form": ["10-K"],
            "filingDate": ["2025-02-20"],
            "acceptanceDateTime": ["2025-02-20T16:03:00.000Z"],
            "reportDate": ["2024-12-31"],
            "primaryDocument": ["key-20241231.htm"],
            "primaryDocDescription": ["10-K"],
            "isXBRL": [1],
        }
    },
}

KEY_FACTS = make_companyfacts(
    {
        "Deposits": {
            "entries": [
                fact_entry("2023-12-31", 145_000_000_000.0, filed="2024-02-21"),
                fact_entry("2024-12-31", 150_000_000_000.0, filed="2025-02-20"),
            ]
        },
    }
)


def routes():
    # Ticker map fixture order: AAPL, KEY, MSFT. MSFT submissions 404 on purpose.
    return {
        TICKER_MAP_URL: load_fixture("company_tickers.json"),
        SUBMISSIONS_URL.format(cik=320193): load_fixture("submissions_aapl.json"),
        COMPANY_FACTS_URL.format(cik=320193): AAPL_FACTS,
        SUBMISSIONS_URL.format(cik=91576): json.dumps(KEY_SUBMISSIONS),
        COMPANY_FACTS_URL.format(cik=91576): KEY_FACTS,
    }


def test_select_universe_tickers(settings):
    client = SecClient(settings, transport=transport_for(routes()))
    assert select_universe_tickers(client, top=2) == ["AAPL", "KEY"]
    assert select_universe_tickers(client, tickers=[" aapl", "key "]) == ["AAPL", "KEY"]


def test_fetch_universe_resume_and_failures(settings):
    init_db(settings)
    client = SecClient(settings, transport=transport_for(routes()))
    seen = []

    with get_session(settings) as session:
        result = fetch_universe(
            session, client, top=3,
            progress=lambda t, s, i, n: seen.append((t, s, i, n)),
        )
        # AAPL and KEY fetched; MSFT fails (404) without aborting the run.
        assert result.fetched == ["AAPL", "KEY"]
        assert [t for t, _ in result.failed] == ["MSFT"]
        assert seen[-1][2:] == (3, 3)  # progress reached 3/3

        companies = session.exec(select(Company)).all()
        buckets = {c.name: c.industry_bucket for c in companies}
        assert buckets["KeyCorp"] == "banking"
        assert buckets["Apple Inc."] == "technology"

    # Second run: both fresh → skipped, nothing re-fetched.
    with get_session(settings) as session:
        again = fetch_universe(session, client, top=3)
        assert again.fetched == []
        assert set(again.skipped) == {"AAPL", "KEY"}
        # refresh_days=0 forces a re-fetch.
        forced = fetch_universe(session, client, top=2, refresh_days=0)
        assert forced.fetched == ["AAPL", "KEY"]


def test_peer_percentiles_use_wider_universe(settings):
    """The point of the universe: KEY gains a same-bucket peer set only after
    more banks are fetched; with just AAPL+KEY, banking has no peers yet."""
    init_db(settings)
    client = SecClient(settings, transport=transport_for(routes()))
    with get_session(settings) as session:
        fetch_universe(session, client, top=2)
        from stock_helper.features.context import build_peer_context
        from stock_helper.features.metrics import compute_derived_metrics
        from stock_helper.storage.queries import find_company, load_series

        key = find_company(session, "KEY")
        derived = compute_derived_metrics(load_series(session, key))
        assert build_peer_context(session, key, derived) is None  # no other banks

        aapl = find_company(session, "AAPL")
        aapl_derived = compute_derived_metrics(load_series(session, aapl))
        assert build_peer_context(session, aapl, aapl_derived) is None  # no other tech
