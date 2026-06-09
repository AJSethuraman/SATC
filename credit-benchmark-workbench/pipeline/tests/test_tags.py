"""Stage 1: tag fragmentation -- alternate tags, fallback notes, units."""

from ccbw.parse import extract_facts, select_annual
from ccbw.tags import CONCEPTS
from conftest import company_facts, fact_entry, tag_block


class TestTagFallback:
    def test_asc606_filer_revenue_found_via_fallback(self):
        cf = company_facts(usgaap={
            "RevenueFromContractWithCustomerExcludingAssessedTax": tag_block({
                "USD": [fact_entry(100e6, end="2020-12-31", start="2020-01-01")],
            }),
        })
        sel, notes = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100e6
        assert sel[2020].tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
        assert any("fallback" in n for n in notes)

    def test_primary_tag_preferred_when_both_present(self):
        cf = company_facts(usgaap={
            "Revenues": tag_block({"USD": [
                fact_entry(100e6, end="2020-12-31", start="2020-01-01")]}),
            "SalesRevenueNet": tag_block({"USD": [
                fact_entry(999e6, end="2020-12-31", start="2020-01-01")]}),
        })
        sel, notes = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100e6
        assert sel[2020].tag == "Revenues"

    def test_mixed_tags_across_years_filled_and_noted(self):
        # filer switched tags at ASC 606 adoption: Revenues through 2017,
        # the 606 tag from 2018
        cf = company_facts(usgaap={
            "Revenues": tag_block({"USD": [
                fact_entry(90e6, end="2017-12-31", start="2017-01-01",
                           fy=2017, filed="2018-03-01")]}),
            "RevenueFromContractWithCustomerExcludingAssessedTax": tag_block({
                "USD": [fact_entry(100e6, end="2018-12-31",
                                   start="2018-01-01", fy=2018,
                                   filed="2019-03-01")]}),
        })
        sel, notes = select_annual(extract_facts(cf), "revenue")
        assert sel[2017].val == 90e6
        assert sel[2018].val == 100e6
        assert any("multiple tags" in n for n in notes)

    def test_provenance_records_actual_tag_used(self):
        cf = company_facts(usgaap={
            "SalesRevenueNet": tag_block({"USD": [
                fact_entry(50e6, end="2020-12-31", start="2020-01-01")]}),
        })
        sel, _ = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].provenance()["tag"] == "SalesRevenueNet"


class TestUnits:
    def test_non_usd_unit_rejected_with_note(self):
        cf = company_facts(usgaap={
            "Revenues": tag_block({
                "EUR": [fact_entry(90e6, end="2020-12-31", start="2020-01-01")],
                "USD": [fact_entry(100e6, end="2020-12-31", start="2020-01-01")],
            }),
        })
        sel, notes = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100e6
        assert any("rejected unit 'EUR'" in n for n in notes)

    def test_only_wrong_unit_means_no_value_not_wrong_value(self):
        cf = company_facts(usgaap={
            "Revenues": tag_block({
                "EUR": [fact_entry(90e6, end="2020-12-31", start="2020-01-01")],
            }),
        })
        sel, notes = select_annual(extract_facts(cf), "revenue")
        assert sel == {}
        assert any("rejected unit" in n for n in notes)

    def test_values_are_raw_units_not_scaled(self):
        # 100e6 in means 100e6 out -- no thousands/millions guessing
        cf = company_facts(usgaap={
            "Revenues": tag_block({"USD": [
                fact_entry(100_000_000, end="2020-12-31", start="2020-01-01")]}),
        })
        sel, _ = select_annual(extract_facts(cf), "revenue")
        assert sel[2020].val == 100_000_000


def test_every_concept_has_tags_and_kind():
    for name, spec in CONCEPTS.items():
        assert spec.tags, name
        assert spec.kind in ("duration", "instant"), name
