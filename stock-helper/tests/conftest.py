"""Shared fixtures. All tests run offline: SEC HTTP is faked with
httpx.MockTransport serving files from tests/fixtures/."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from stock_helper.core.config import Settings
from stock_helper.normalization.facts import FactPoint, MetricSeries

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        sec_user_agent="stock-helper tests (tests@example.com)",
        data_dir=tmp_path / "data",
        enable_price_data=False,
        _env_file=None,
    )


def fact_entry(
    end: str,
    value: float,
    *,
    start: str | None = None,
    form: str = "10-K",
    fp: str = "FY",
    fy: int | None = None,
    filed: str = "2024-11-01",
    accession: str = "0000000000-24-000001",
) -> dict:
    entry = {
        "end": end,
        "val": value,
        "form": form,
        "fp": fp,
        "fy": fy or int(end[:4]),
        "filed": filed,
        "accn": accession,
    }
    if start:
        entry["start"] = start
    return entry


def make_companyfacts(usgaap: dict[str, dict]) -> dict:
    """usgaap: tag -> {"unit": "USD", "entries": [...]}"""
    facts = {}
    for tag, spec in usgaap.items():
        facts[tag] = {"units": {spec.get("unit", "USD"): spec["entries"]}}
    return {"cik": 320193, "entityName": "Test Co", "facts": {"us-gaap": facts}}


AAPL_FACTS = make_companyfacts(
    {
        # Preferred revenue tag with 3 clean annual periods, plus a stale
        # duplicate for FY2023 (earlier filed) that dedupe must discard, plus a
        # quarterly entry the duration filter must exclude.
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "entries": [
                fact_entry("2022-09-24", 394_000_000_000.0, start="2021-09-26",
                           filed="2022-10-28", accession="0000320193-22-000108"),
                fact_entry("2023-09-30", 380_000_000_000.0, start="2022-09-25",
                           filed="2023-11-03", accession="0000320193-23-000106"),
                fact_entry("2023-09-30", 383_000_000_000.0, start="2022-09-25",
                           filed="2024-11-01", accession="0000320193-24-000123"),
                fact_entry("2024-09-28", 391_000_000_000.0, start="2023-10-01",
                           filed="2024-11-01", accession="0000320193-24-000123"),
                fact_entry("2024-06-29", 85_000_000_000.0, start="2024-03-31",
                           form="10-Q", fp="Q3", filed="2024-08-01",
                           accession="0000320193-24-000080"),
            ]
        },
        # Sparser fallback tag — must lose the coverage contest.
        "Revenues": {
            "entries": [
                fact_entry("2024-09-28", 391_000_000_000.0, start="2023-10-01",
                           filed="2024-11-01", accession="0000320193-24-000123"),
            ]
        },
        "CostOfGoodsAndServicesSold": {
            "entries": [
                fact_entry("2022-09-24", 224_000_000_000.0, start="2021-09-26", filed="2022-10-28"),
                fact_entry("2023-09-30", 214_000_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 210_000_000_000.0, start="2023-10-01"),
            ]
        },
        "OperatingIncomeLoss": {
            "entries": [
                fact_entry("2022-09-24", 119_000_000_000.0, start="2021-09-26", filed="2022-10-28"),
                fact_entry("2023-09-30", 114_000_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 123_000_000_000.0, start="2023-10-01"),
            ]
        },
        "NetIncomeLoss": {
            "entries": [
                fact_entry("2023-09-30", 97_000_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 94_000_000_000.0, start="2023-10-01"),
            ]
        },
        "NetCashProvidedByUsedInOperatingActivities": {
            "entries": [
                fact_entry("2023-09-30", 110_000_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 118_000_000_000.0, start="2023-10-01"),
            ]
        },
        "PaymentsToAcquirePropertyPlantAndEquipment": {
            "entries": [
                fact_entry("2023-09-30", 11_000_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 9_400_000_000.0, start="2023-10-01"),
            ]
        },
        "Assets": {
            "entries": [
                fact_entry("2023-09-30", 352_000_000_000.0, filed="2023-11-03"),
                fact_entry("2024-09-28", 365_000_000_000.0),
            ]
        },
        "WeightedAverageNumberOfDilutedSharesOutstanding": {
            "unit": "shares",
            "entries": [
                fact_entry("2023-09-30", 15_800_000_000.0, start="2022-09-25", filed="2023-11-03"),
                fact_entry("2024-09-28", 15_400_000_000.0, start="2023-10-01"),
            ]
        },
    }
)


def transport_for(routes: dict[str, object], counter: dict | None = None) -> httpx.MockTransport:
    """MockTransport serving `routes` (url -> dict|str). Counts calls per URL."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if counter is not None:
            counter[url] = counter.get(url, 0) + 1
        if url not in routes:
            return httpx.Response(404, text="not found")
        payload = routes[url]
        if isinstance(payload, str):
            return httpx.Response(200, text=payload)
        return httpx.Response(200, text=json.dumps(payload))

    return httpx.MockTransport(handler)


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def mk_series(
    key: str,
    values: list[tuple[date, float]],
    tag: str = "TestTag",
    unit: str = "USD",
) -> MetricSeries:
    points = [
        FactPoint(
            metric_key=key, taxonomy="us-gaap", tag=tag, unit=unit, value=value,
            period_start=None, period_end=end, fiscal_year=end.year, fiscal_period="FY",
            form="10-K", accession=f"acc-{end.year}", filed=end,
        )
        for end, value in values
    ]
    return MetricSeries(metric_key=key, tag=tag, unit=unit, points=points)
