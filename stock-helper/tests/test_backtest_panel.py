"""Point-in-time panel assembly: anti-lookahead + survivorship accounting.

These run fully offline over a tiny synthetic in-DB universe (CompanyFact rows
seeded like scripts/demo_seed) plus hand-written price CSVs in the price cache.
They lock the two properties this layer exists to guarantee:

  (1) forward_return enters the day AFTER entry_date and is None when the exit
      price is missing;
  (2) a name with a signal but no forward price is DROPPED and COUNTED in
      dropped_no_price (survivorship exposure);
  (3) build_panel scores POINT-IN-TIME fundamentals — a fact filed after the
      rebalance date does not leak into the signal;
  (4) run_backtest returns a BacktestResult whose caveats disclose survivorship.
"""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from stock_helper.backtest.engine import BacktestResult
from stock_helper.backtest.panel import (
    build_panel,
    forward_return,
    run_backtest,
)
from stock_helper.core.config import Settings
from stock_helper.normalization.xbrl_mapping import CANONICAL_METRICS
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import Company, CompanyFact, SecurityIdentifier

# Two consecutive fiscal years, enough for the Piotroski F-score (needs >= 2
# asset/net-income periods). Values improve YoY so the score is well-defined.
_FY = {
    date(2021, 12, 31): dict(
        revenue=1000, cost_of_revenue=600, operating_income=200, net_income=100,
        operating_cash_flow=150, capex=30, total_assets=800, equity=500,
        current_assets=400, current_liabilities=200, long_term_debt=100,
        diluted_shares=100, cash=50,
    ),
    date(2022, 12, 31): dict(
        revenue=1200, cost_of_revenue=680, operating_income=260, net_income=140,
        operating_cash_flow=200, capex=35, total_assets=850, equity=560,
        current_assets=430, current_liabilities=190, long_term_debt=90,
        diluted_shares=98, cash=60,
    ),
}
# Filed dates per fiscal year: a year is knowable only on/after it was filed.
_FILED = {date(2021, 12, 31): date(2022, 3, 1), date(2022, 12, 31): date(2023, 3, 1)}


def _mk_settings(tmp_path) -> Settings:
    return Settings(
        sec_user_agent="stock-helper tests (tests@example.com)",
        data_dir=tmp_path / "data",
        enable_price_data=True,  # panel needs the (cached) price source
        _env_file=None,
    )


def _seed_company(
    session, *, cik: int, ticker: str, years: list[date], bucket: str = "industrial"
) -> None:
    now = datetime.now(UTC)
    company = Company(
        cik=cik, name=ticker, industry_bucket=bucket,
        source="test", source_url="test", retrieved_at=now,
    )
    session.add(company)
    session.flush()
    session.add(SecurityIdentifier(
        company_id=company.id, ticker=ticker, source="test", retrieved_at=now,
    ))
    for pe in years:
        for key, value in _FY[pe].items():
            spec = CANONICAL_METRICS[key]
            taxonomy, tag = spec.candidates[0]
            session.add(CompanyFact(
                company_id=company.id, metric_key=key, taxonomy=taxonomy, tag=tag,
                unit=spec.unit, value=float(value), period_end=pe,
                fiscal_year=pe.year, fiscal_period="FY", form="10-K",
                accession=f"{cik}-{pe.year}", filed_date=_FILED[pe],
                source="test", source_url="test", retrieved_at=now,
            ))
    session.commit()


def _write_prices(settings: Settings, ticker: str, start: str, end: str) -> None:
    """Constant-drift daily closes over [start, end] business days into the cache
    (fetch_daily_prices reads this CSV; ages ~0s so it never hits the network)."""
    settings.price_cache_dir.mkdir(parents=True, exist_ok=True)
    days = pd.bdate_range(start, end)
    closes = [100.0 + i for i in range(len(days))]
    frame = pd.DataFrame({"Date": days, "Close": closes})
    frame.to_csv(settings.price_cache_dir / f"{ticker.lower()}.csv", index=False)


# ------------------------------------------------------- (1) forward_return


def test_forward_return_enters_next_session_and_handles_missing_exit():
    days = pd.bdate_range("2024-01-01", periods=40)
    prices = pd.DataFrame({"Date": days, "Close": [100.0 + i for i in range(len(days))]})
    entry = date(2024, 1, 10)  # a Wednesday in range

    # Entry is the FIRST session strictly after entry_date (no same-day lookahead).
    entry_dates = pd.to_datetime(prices["Date"]).dt.date
    first_after = prices[entry_dates > entry].reset_index(drop=True)
    entry_close = float(first_after.loc[0, "Close"])
    exit_close = float(first_after.loc[5, "Close"])
    assert forward_return(prices, entry, 5) == pytest.approx(exit_close / entry_close - 1.0)

    # Horizon running past the last available session -> None (missing exit price).
    assert forward_return(prices, entry, 10_000) is None
    # entry_date after all data -> no session after it -> None.
    assert forward_return(prices, date(2025, 1, 1), 5) is None
    # No/empty frame -> None (never a fabricated number).
    assert forward_return(None, entry, 5) is None
    assert forward_return(pd.DataFrame({"Date": [], "Close": []}), entry, 5) is None


# ------------------------------------------- (2) survivorship drop is counted


def test_delisted_name_dropped_and_counted(tmp_path):
    settings = _mk_settings(tmp_path)
    init_db(settings)
    with get_session(settings) as session:
        _seed_company(session, cik=900001, ticker="LIVE", years=list(_FY))
        _seed_company(session, cik=900002, ticker="DELIST", years=list(_FY))

    as_of = date(2023, 6, 1)  # both fiscal years knowable by now
    # LIVE keeps trading well past as_of + horizon; DELIST's prices STOP in 2022.
    _write_prices(settings, "LIVE", "2022-01-01", "2023-12-31")
    _write_prices(settings, "DELIST", "2021-06-01", "2022-10-01")

    with get_session(settings) as session:
        panel, diag = build_panel(
            session, signal_name="piotroski_f", dates=[as_of],
            horizon_days=5, settings=settings, tickers=["LIVE", "DELIST"],
        )

    assert len(panel) == 1
    obs = panel[0]
    # The surviving name is scored; the delisted name is absent from the panel...
    assert "LIVE" in obs.signals
    assert "DELIST" not in obs.signals
    # ...but its exclusion is COUNTED as survivorship exposure, not silent.
    assert diag["dropped_no_price"] == 1
    assert diag["signal_name"] == "piotroski_f"
    assert diag["horizon_days"] == 5


# ---------------------------------- (3) point-in-time fundamentals (no leak)


def test_build_panel_uses_as_of_fundamentals(tmp_path):
    settings = _mk_settings(tmp_path)
    init_db(settings)
    with get_session(settings) as session:
        _seed_company(session, cik=900003, ticker="PIT", years=list(_FY))
    _write_prices(settings, "PIT", "2021-06-01", "2024-06-30")

    # FY2022 was filed 2023-03-01. On 2022-09-01 only FY2021 is knowable -> a
    # single fiscal year -> Piotroski needs >= 2 -> None -> PIT absent. If the
    # later-filed FY2022 fact leaked in, the score would compute and PIT appear.
    early = date(2022, 9, 1)
    late = date(2023, 9, 1)
    with get_session(settings) as session:
        panel, _ = build_panel(
            session, signal_name="piotroski_f", dates=[early, late],
            horizon_days=5, settings=settings, tickers=["PIT"],
        )

    by_date = {obs.as_of: obs for obs in panel}
    # Early date: the FY2022 fact filed after it must NOT appear -> no signal.
    assert early not in by_date or "PIT" not in by_date[early].signals
    # Late date: both years knowable -> the signal computes.
    assert late in by_date and "PIT" in by_date[late].signals


# --------------------------------------- (4) run_backtest end-to-end + caveat


def test_run_backtest_returns_result_with_survivorship_caveat(tmp_path):
    settings = _mk_settings(tmp_path)
    init_db(settings)
    with get_session(settings) as session:
        for i, ticker in enumerate(("AAA", "BBB", "CCC", "DDD")):
            _seed_company(session, cik=900010 + i, ticker=ticker, years=list(_FY))
    for ticker in ("AAA", "BBB", "CCC", "DDD"):
        _write_prices(settings, ticker, "2022-06-01", "2024-06-30")

    with get_session(settings) as session:
        result = run_backtest(
            session, signal_name="piotroski_f",
            start=date(2023, 3, 15), end=date(2023, 9, 15),
            step_days=30, horizon_days=5, settings=settings, n_trials=3,
        )

    assert isinstance(result, BacktestResult)
    # Every backtest output must disclose survivorship exposure (honesty is
    # load-bearing) — both the engine's standing caveat and the merged count line.
    joined = " ".join(result.caveats).lower()
    assert "survivorship" in joined
    assert "not a performance claim" in joined
    assert any("name-dates dropped" in c for c in result.caveats)
