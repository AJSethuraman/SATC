"""Shared fixture builders: hand-rolled CompanyFacts-shaped payloads."""

from __future__ import annotations

import pytest


def fact_entry(val, end, start=None, accn="0000900000-21-000001",
               fy=2020, fp="FY", form="10-K", filed=None):
    e = {"val": val, "end": end, "accn": accn, "fy": fy, "fp": fp,
         "form": form, "filed": filed or "2021-03-01"}
    if start:
        e["start"] = start
    return e


def company_facts(cik=900001, name="Test Corp", usgaap=None):
    return {"cik": cik, "entityName": name, "facts": {"us-gaap": usgaap or {}}}


def tag_block(unit_entries: dict):
    """unit_entries: {'USD': [entry, ...]}"""
    return {"units": unit_entries}


@pytest.fixture
def simple_company():
    """Three clean fiscal years (FY2018-FY2020, Dec FYE) with one annual
    10-K fact per concept -- the happy path."""
    def annual(tag_vals: dict[str, list[float]], duration=True):
        out = {}
        years = [2018, 2019, 2020]
        for tag, vals in tag_vals.items():
            entries = []
            for fy, v in zip(years, vals):
                entries.append(fact_entry(
                    v, end=f"{fy}-12-31",
                    start=f"{fy}-01-01" if duration else None,
                    accn=f"0000900001-{fy + 1 - 2000:02d}-000001",
                    fy=fy, filed=f"{fy + 1}-03-01"))
            out[tag] = tag_block({"USD": entries})
        return out

    usgaap = {}
    usgaap.update(annual({
        "Revenues": [100e6, 110e6, 120e6],
        "CostOfRevenue": [60e6, 66e6, 72e6],
        "OperatingIncomeLoss": [12e6, 13e6, 14e6],
        "DepreciationDepletionAndAmortization": [4e6, 4.2e6, 4.4e6],
        "InterestExpense": [3e6, 3.1e6, 3.2e6],
        "NetIncomeLoss": [6e6, 6.5e6, 7e6],
        "PaymentsToAcquirePropertyPlantAndEquipment": [3e6, 3e6, 3e6],
        "NetCashProvidedByUsedInOperatingActivities": [9e6, 9.5e6, 10e6],
    }))
    usgaap.update(annual({
        "Assets": [150e6, 160e6, 170e6],
        "AssetsCurrent": [50e6, 53e6, 56e6],
        "LiabilitiesCurrent": [25e6, 26e6, 27e6],
        "Liabilities": [90e6, 93e6, 96e6],
        "CashAndCashEquivalentsAtCarryingValue": [10e6, 11e6, 12e6],
        "AccountsReceivableNetCurrent": [15e6, 16e6, 17e6],
        "InventoryNet": [18e6, 19e6, 20e6],
        "AccountsPayableCurrent": [9e6, 9.5e6, 10e6],
        "LongTermDebtNoncurrent": [40e6, 41e6, 42e6],
        "LongTermDebtCurrent": [5e6, 5e6, 5e6],
        "StockholdersEquity": [60e6, 67e6, 74e6],
        "RetainedEarningsAccumulatedDeficit": [30e6, 35e6, 40e6],
    }, duration=False))
    return company_facts(usgaap=usgaap)
