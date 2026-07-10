"""Stage 1: duplicate facts across filings, amendments, restatements."""

from ccbw.parse import dedupe_facts, extract_facts
from conftest import company_facts, fact_entry, tag_block


def _facts(entries):
    return extract_facts(company_facts(
        usgaap={"Revenues": tag_block({"USD": entries})}))


class TestDedupe:
    def test_comparative_rereport_collapses_to_one(self):
        # FY2019 revenue appears in the 2019 10-K and again as the
        # comparative column of the 2020 10-K -- same value, two accessions.
        entries = [
            fact_entry(100e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-20-000001", filed="2020-03-01", fy=2019),
            fact_entry(100e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-21-000001", filed="2021-03-01", fy=2020),
        ]
        out = dedupe_facts(_facts(entries))
        assert len(out) == 1
        # identical values: no superseded noise recorded
        assert out[0].superseded == []

    def test_restatement_latest_filed_wins(self):
        entries = [
            fact_entry(100e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-20-000001", filed="2020-03-01"),
            fact_entry(103e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-21-000001", filed="2021-03-01"),
        ]
        out = dedupe_facts(_facts(entries))
        assert len(out) == 1
        assert out[0].val == 103e6
        # original retained for audit
        assert [f.val for f in out[0].superseded] == [100e6]

    def test_amendment_wins_on_same_filed_date(self):
        entries = [
            fact_entry(100e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-20-000001", filed="2020-03-01",
                       form="10-K"),
            fact_entry(110e6, end="2019-12-31", start="2019-01-01",
                       accn="0000900001-20-000002", filed="2020-03-01",
                       form="10-K/A"),
        ]
        out = dedupe_facts(_facts(entries))
        assert out[0].val == 110e6
        assert out[0].form == "10-K/A"

    def test_different_periods_not_merged(self):
        entries = [
            fact_entry(100e6, end="2019-12-31", start="2019-01-01"),
            fact_entry(110e6, end="2020-12-31", start="2020-01-01"),
            fact_entry(25e6, end="2020-03-31", start="2020-01-01", form="10-Q"),
        ]
        out = dedupe_facts(_facts(entries))
        assert len(out) == 3

    def test_provenance_records_supersession_count(self):
        entries = [
            fact_entry(100e6, end="2019-12-31", start="2019-01-01",
                       filed="2020-03-01"),
            fact_entry(105e6, end="2019-12-31", start="2019-01-01",
                       filed="2020-09-01", form="10-K/A",
                       accn="0000900001-20-000009"),
        ]
        out = dedupe_facts(_facts(entries))
        prov = out[0].provenance()
        assert prov["n_superseded"] == 1
        assert prov["form"] == "10-K/A"
        assert prov["accn"] == "0000900001-20-000009"
