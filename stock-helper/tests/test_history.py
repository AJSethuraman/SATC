"""Point-in-time replay through the database, as-of reports, signal history,
and exploratory forward-return labels."""

from datetime import date, timedelta

import pandas as pd
import pytest
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
from stock_helper.signals.history import (
    build_signal_history,
    default_history_dates,
    forward_returns,
)
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import SignalHistory
from stock_helper.storage.queries import find_company, load_series


@pytest.fixture
def ingested(settings):
    init_db(settings)
    routes = {
        TICKER_MAP_URL: load_fixture("company_tickers.json"),
        SUBMISSIONS_URL.format(cik=320193): load_fixture("submissions_aapl.json"),
        COMPANY_FACTS_URL.format(cik=320193): AAPL_FACTS,
    }
    client = SecClient(settings, transport=transport_for(routes))
    with get_session(settings) as session:
        fetch_and_store("AAPL", session, client)
    return settings


def test_as_of_replay_from_database(ingested):
    """The DB path must reproduce the same point-in-time behavior as the raw
    JSON path: original FY23 value before restatement, no FY24 yet."""
    with get_session(ingested) as session:
        company = find_company(session, "AAPL")
        series = load_series(session, company, as_of=date(2024, 1, 1))
        revenue = series["revenue"]
        assert [p.period_end for p in revenue.points] == [
            date(2022, 9, 24), date(2023, 9, 30),
        ]
        assert revenue.points[-1].value == 380_000_000_000.0

        current = load_series(session, company)
        fy23 = next(p for p in current["revenue"].points if p.period_end == date(2023, 9, 30))
        assert fy23.value == 383_000_000_000.0  # restated view without as_of


def test_as_of_report_excludes_later_filings(ingested):
    with get_session(ingested) as session:
        report = build_report(session, "AAPL", ingested, as_of=date(2024, 1, 1))
    assert report.as_of == date(2024, 1, 1)
    # The FY2024 10-K (filed 2024-11-01) and 2025 10-Q must not appear.
    assert all(f.filed_date <= date(2024, 1, 1) for f in report.filings)
    markdown = render_markdown(report)
    assert "Point-in-time view as of 2024-01-01" in markdown
    assert "0000320193-24-000123" not in markdown


def test_default_history_dates_are_filing_dates(ingested):
    with get_session(ingested) as session:
        company = find_company(session, "AAPL")
        dates = default_history_dates(session, company)
        # 10-K filed 2024-11-01 and 10-Q filed 2025-05-02 (8-K, S-8, 10-K/A excluded)
        assert dates == [date(2024, 11, 1), date(2025, 5, 2)]
        assert default_history_dates(session, company, start=date(2025, 1, 1)) == [
            date(2025, 5, 2)
        ]


def test_signal_history_persists_and_replaces(ingested):
    with get_session(ingested) as session:
        points = build_signal_history(session, "AAPL", settings=ingested)
        assert [p.as_of for p in points] == [date(2024, 11, 1), date(2025, 5, 2)]
        # At the 10-K filing date, revenue history is knowable (3 FYs).
        first = {s.definition.key: s.outcome for s in points[0].signals}
        assert first["revenue_growth_yoy"].status == "OK"

        rows = session.exec(select(SignalHistory)).all()
        assert {r.as_of_date for r in rows} == {date(2024, 11, 1), date(2025, 5, 2)}

        # Re-running replaces, never duplicates.
        build_signal_history(session, "AAPL", settings=ingested)
        rows_again = session.exec(select(SignalHistory)).all()
        assert len(rows_again) == len(rows)


def test_forward_returns_next_session_entry():
    days = pd.bdate_range("2024-01-01", periods=200)
    prices = pd.DataFrame({"Date": days, "Close": [100.0 + i for i in range(len(days))]})
    as_of = date(2024, 1, 10)  # a Wednesday in-range

    labels = forward_returns(prices, as_of, horizons=(20, 60, 500))
    assert set(labels) == {20, 60}  # 500 exceeds available data → omitted
    label = labels[20]
    assert label.entry_date > as_of  # next session, not the as-of day itself
    entry_close = float(prices.loc[pd.to_datetime(prices["Date"]).dt.date == label.entry_date, "Close"].iloc[0])
    exit_close = float(prices.loc[pd.to_datetime(prices["Date"]).dt.date == label.exit_date, "Close"].iloc[0])
    assert label.ret == pytest.approx(exit_close / entry_close - 1.0)
    assert (label.exit_date - label.entry_date) >= timedelta(days=20)  # trading days > calendar span check


def test_forward_returns_after_history_end():
    days = pd.bdate_range("2024-01-01", periods=30)
    prices = pd.DataFrame({"Date": days, "Close": [100.0] * len(days)})
    assert forward_returns(prices, date(2025, 1, 1)) == {}
