"""Regression: co-registrants sharing an SEC accession must both ingest.

A utility holding company can file a single 8-K listing several co-registrants,
so the same accession legitimately appears in multiple companies' submission
feeds. Uniqueness is per (company, accession); a global unique on accession
crashed a wide `fetch-universe` run with IntegrityError. This reproduces the two
companies + shared accession case and asserts both filings persist.
"""

import json

from sqlmodel import select

from conftest import transport_for
from stock_helper.connectors.sec import (
    COMPANY_FACTS_URL,
    SUBMISSIONS_URL,
    TICKER_MAP_URL,
    SecClient,
)
from stock_helper.ingestion.sec_ingest import fetch_and_store
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import Filing

_SHARED_ACCESSION = "0001109357-22-000013"


def _submissions(cik: int, ticker: str, name: str) -> str:
    return json.dumps({
        "cik": cik,
        "entityType": "operating",
        "sic": "4911",
        "sicDescription": "Electric Services",
        "name": name,
        "tickers": [ticker],
        "exchanges": ["Nasdaq"],
        "fiscalYearEnd": "1231",
        "stateOfIncorporation": "PA",
        "filings": {"recent": {
            "accessionNumber": [_SHARED_ACCESSION],
            "form": ["8-K"],
            "filingDate": ["2022-01-10"],
            "acceptanceDateTime": ["2022-01-10T21:29:59.000Z"],
            "reportDate": ["2022-01-10"],
            "primaryDocument": ["exc-20220110.htm"],
            "primaryDocDescription": ["8-K"],
            "isXBRL": [1],
        }},
    })


def _empty_facts(cik: int) -> str:
    return json.dumps({"cik": cik, "entityName": "x", "facts": {}})


def test_two_companies_share_one_accession(settings):
    init_db(settings)
    ticker_map = json.dumps({
        "0": {"cik_str": 1109357, "ticker": "EXC", "title": "Exelon Corp"},
        "1": {"cik_str": 902739, "ticker": "PECO", "title": "PECO Energy Co"},
    })
    routes = {
        TICKER_MAP_URL: ticker_map,
        SUBMISSIONS_URL.format(cik=1109357): _submissions(1109357, "EXC", "Exelon Corp"),
        SUBMISSIONS_URL.format(cik=902739): _submissions(902739, "PECO", "PECO Energy Co"),
        COMPANY_FACTS_URL.format(cik=1109357): _empty_facts(1109357),
        COMPANY_FACTS_URL.format(cik=902739): _empty_facts(902739),
    }
    client = SecClient(settings, transport=transport_for(routes))
    with get_session(settings) as session:
        # Second call previously raised IntegrityError on the shared accession.
        fetch_and_store("EXC", session, client)
        fetch_and_store("PECO", session, client)
        rows = session.exec(
            select(Filing).where(Filing.accession == _SHARED_ACCESSION)
        ).all()
    # One filing row per company — both co-registrants kept.
    assert len(rows) == 2
    assert {r.company_id for r in rows} and len({r.company_id for r in rows}) == 2
