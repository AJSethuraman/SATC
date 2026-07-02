"""Company facts parsing → canonical annual series."""

from datetime import date

from conftest import AAPL_FACTS
from stock_helper.normalization.facts import build_annual_series


def test_revenue_tag_selection_prefers_coverage():
    series = build_annual_series(AAPL_FACTS)
    assert series["revenue"].tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(series["revenue"].points) == 3  # FY22, FY23, FY24


def test_quarterly_entries_excluded():
    revenue_ends = [p.period_end for p in build_annual_series(AAPL_FACTS)["revenue"].points]
    assert date(2024, 6, 29) not in revenue_ends


def test_latest_filed_wins_per_period():
    series = build_annual_series(AAPL_FACTS)
    fy23 = next(p for p in series["revenue"].points if p.period_end == date(2023, 9, 30))
    assert fy23.value == 383_000_000_000.0  # restated (later-filed) value
    assert fy23.accession == "0000320193-24-000123"


def test_instant_metrics_extracted():
    series = build_annual_series(AAPL_FACTS)
    assert [p.value for p in series["total_assets"].points] == [
        352_000_000_000.0,
        365_000_000_000.0,
    ]


def test_provenance_preserved():
    point = build_annual_series(AAPL_FACTS)["revenue"].points[-1]
    assert point.accession
    assert point.filed is not None
    assert point.form.startswith("10-K")


def test_as_of_replays_point_in_time_view():
    """Point-in-time foundation for backtesting/calibration: as_of excludes
    facts filed later, and the value knowable *on that date* wins."""
    # As of 2024-01-01: FY2024 (filed 2024-11-01) must not exist yet, and the
    # FY2023 value must be the ORIGINAL $380B (filed 2023-11-03), not the
    # restated $383B from the FY2024 10-K.
    series = build_annual_series(AAPL_FACTS, as_of=date(2024, 1, 1))
    revenue = series["revenue"]
    assert [p.period_end for p in revenue.points] == [date(2022, 9, 24), date(2023, 9, 30)]
    fy23 = revenue.points[-1]
    assert fy23.value == 380_000_000_000.0
    assert fy23.accession == "0000320193-23-000106"

    # Before any 10-K in the fixture was filed, nothing is knowable.
    assert "revenue" not in build_annual_series(AAPL_FACTS, as_of=date(2020, 1, 1))


def test_missing_metrics_omitted_not_guessed():
    series = build_annual_series(AAPL_FACTS)
    assert "deposits" not in series
    assert "interest_expense" not in series
