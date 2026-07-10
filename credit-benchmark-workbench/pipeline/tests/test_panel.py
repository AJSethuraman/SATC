"""Stage 1: panel building -- debt derivation, EBITDA, gaps, provenance."""

from ccbw.panel import build_company_panel
from conftest import company_facts, fact_entry, tag_block


def _bs(tag_vals, fy=2020):
    """Single-year balance-sheet style payload + minimal income statement."""
    usgaap = {
        "Revenues": tag_block({"USD": [
            fact_entry(100e6, end=f"{fy}-12-31", start=f"{fy}-01-01")]}),
        "OperatingIncomeLoss": tag_block({"USD": [
            fact_entry(12e6, end=f"{fy}-12-31", start=f"{fy}-01-01")]}),
        "DepreciationDepletionAndAmortization": tag_block({"USD": [
            fact_entry(4e6, end=f"{fy}-12-31", start=f"{fy}-01-01")]}),
    }
    for tag, val in tag_vals.items():
        usgaap[tag] = tag_block({"USD": [fact_entry(val, end=f"{fy}-12-31")]})
    return company_facts(usgaap=usgaap)


class TestTotalDebt:
    def test_standard_components_sum(self):
        rows = build_company_panel(_bs({
            "LongTermDebtNoncurrent": 40e6,
            "LongTermDebtCurrent": 5e6,
            "ShortTermBorrowings": 3e6,
        }))
        assert rows[0].get("total_debt") == 48e6

    def test_debtcurrent_preferred_over_components_no_double_count(self):
        rows = build_company_panel(_bs({
            "LongTermDebtNoncurrent": 40e6,
            "DebtCurrent": 8e6,             # already includes the next two
            "LongTermDebtCurrent": 5e6,
            "ShortTermBorrowings": 3e6,
        }))
        assert rows[0].get("total_debt") == 48e6

    def test_combined_longtermdebt_fallback_flagged(self):
        rows = build_company_panel(_bs({"LongTermDebt": 45e6}))
        pv = rows[0].values["total_debt"]
        assert pv.value == 45e6
        assert any("combined LongTermDebt" in n for n in pv.notes)

    def test_no_debt_tags_is_a_gap_not_zero(self):
        rows = build_company_panel(_bs({}))
        assert rows[0].get("total_debt") is None
        assert any("total_debt" in g for g in rows[0].gaps)

    def test_provenance_lists_all_components(self):
        rows = build_company_panel(_bs({
            "LongTermDebtNoncurrent": 40e6,
            "LongTermDebtCurrent": 5e6,
        }))
        prov = rows[0].values["total_debt"].provenance
        tags = {p["tag"] for p in prov}
        assert tags == {"LongTermDebtNoncurrent", "LongTermDebtCurrent"}


class TestEbitda:
    def test_ebitda_is_oi_plus_da(self):
        rows = build_company_panel(_bs({}))
        assert rows[0].get("ebitda") == 16e6

    def test_missing_da_understated_with_gap(self):
        cf = _bs({})
        del cf["facts"]["us-gaap"]["DepreciationDepletionAndAmortization"]
        rows = build_company_panel(cf)
        assert rows[0].get("ebitda") == 12e6
        assert any("D&A missing" in g for g in rows[0].gaps)
        assert any("understated" in n
                   for n in rows[0].values["ebitda"].notes)

    def test_missing_operating_income_no_ebitda(self):
        cf = _bs({})
        del cf["facts"]["us-gaap"]["OperatingIncomeLoss"]
        rows = build_company_panel(cf)
        assert rows[0].get("ebitda") is None
        assert any("operating income missing" in g for g in rows[0].gaps)


class TestPanelShape:
    def test_three_clean_years(self, simple_company):
        rows = build_company_panel(simple_company)
        assert [r.fy for r in rows] == [2018, 2019, 2020]
        r = rows[-1]
        assert r.get("revenue") == 120e6
        assert r.get("total_debt") == 47e6          # 42 + 5
        assert r.get("ebitda") == 14e6 + 4.4e6
        assert r.fye == "2020-12-31"

    def test_core_concept_missing_recorded_as_gap(self, simple_company):
        del simple_company["facts"]["us-gaap"]["InterestExpense"]
        rows = build_company_panel(simple_company)
        assert any("interest_expense" in g for g in rows[-1].gaps)

    def test_pre_xbrl_years_dropped(self):
        cf = _bs({"LongTermDebtNoncurrent": 40e6}, fy=2008)
        assert build_company_panel(cf, min_fy=2010) == []

    def test_january_fye_assigned_prior_label(self):
        usgaap = {
            "Revenues": tag_block({"USD": [
                fact_entry(100e6, end="2024-01-31", start="2023-02-01",
                           fy=2024, filed="2024-04-01")]}),
            "OperatingIncomeLoss": tag_block({"USD": [
                fact_entry(12e6, end="2024-01-31", start="2023-02-01",
                           fy=2024, filed="2024-04-01")]}),
        }
        rows = build_company_panel(company_facts(usgaap=usgaap))
        assert [r.fy for r in rows] == [2023]
        assert rows[0].fye == "2024-01-31"
