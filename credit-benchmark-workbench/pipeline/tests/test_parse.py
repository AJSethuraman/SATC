"""Stage 1: malformed filings, fiscal alignment, basic extraction."""

from datetime import date

import pytest

from ccbw.parse import (MalformedFilingError, extract_facts, fiscal_year_label,
                        select_annual)
from conftest import company_facts, fact_entry, tag_block


class TestMalformed:
    def test_no_facts_key(self):
        with pytest.raises(MalformedFilingError):
            extract_facts({"cik": 1})

    def test_no_cik(self):
        with pytest.raises(MalformedFilingError):
            extract_facts({"facts": {"us-gaap": {}}})

    def test_taxonomy_not_object(self):
        with pytest.raises(MalformedFilingError):
            extract_facts({"cik": 1, "facts": {"us-gaap": ["nope"]}})

    def test_garbage_entries_skipped_not_fatal(self):
        cf = company_facts(usgaap={
            "Revenues": tag_block({"USD": [
                {"val": "not-a-number-at-all"},          # no end, bad val
                {"end": "2020-12-31"},                    # no val
                {"val": None, "end": "2020-12-31"},       # null val
                fact_entry(5e6, end="2020-12-31", start="2020-01-01"),
            ]}),
            "BrokenTag": {"units": "not-a-dict"},
            "AlsoBroken": "not-even-an-object",
        })
        facts = extract_facts(cf)
        assert len(facts) == 1
        assert facts[0].val == 5e6

    def test_missing_filed_date_defaults_not_crashes(self):
        e = fact_entry(1e6, end="2020-12-31", start="2020-01-01")
        del e["filed"]
        cf = company_facts(usgaap={"Revenues": tag_block({"USD": [e]})})
        facts = extract_facts(cf)
        assert facts[0].filed == date(1900, 1, 1)


class TestFiscalAlignment:
    def test_december_fye_labels_same_year(self):
        assert fiscal_year_label(date(2023, 12, 31)) == 2023

    def test_january_fye_labels_prior_year(self):
        # A Jan-2024 FYE covers essentially calendar 2023
        assert fiscal_year_label(date(2024, 1, 31)) == 2023

    def test_june_fye_labels_same_year(self):
        assert fiscal_year_label(date(2023, 6, 30)) == 2023

    def test_may_fye_labels_prior_year(self):
        assert fiscal_year_label(date(2023, 5, 31)) == 2022

    def test_offset_filers_land_in_same_label(self):
        # Dec-2023 filer and Jan-2024 filer are the same economic year
        assert fiscal_year_label(date(2023, 12, 31)) == \
            fiscal_year_label(date(2024, 1, 31))


class TestAnnualSelection:
    def test_quarterly_durations_excluded(self):
        cf = company_facts(usgaap={"Revenues": tag_block({"USD": [
            fact_entry(25e6, end="2020-03-31", start="2020-01-01", form="10-Q"),
            fact_entry(50e6, end="2020-06-30", start="2020-01-01", form="10-Q"),
            fact_entry(100e6, end="2020-12-31", start="2020-01-01", form="10-K"),
        ]})})
        sel, _ = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100e6

    def test_annual_duration_from_quarterly_form_used_as_fallback(self):
        # some filers only carry the FY figure in a 10-Q comparative
        cf = company_facts(usgaap={"Revenues": tag_block({"USD": [
            fact_entry(100e6, end="2020-12-31", start="2020-01-01", form="10-Q"),
        ]})})
        sel, _ = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100e6

    def test_instant_facts_prefer_fiscal_year_end_dates(self):
        cf = company_facts(usgaap={"Assets": tag_block({"USD": [
            fact_entry(90e6, end="2020-06-30", form="10-Q"),
            fact_entry(100e6, end="2020-12-31", form="10-K"),
        ]})})
        sel, _ = select_annual(
            extract_facts(cf), "total_assets",
            fiscal_year_ends={2020: date(2020, 12, 31)})
        assert sel[2020].val == 100e6
