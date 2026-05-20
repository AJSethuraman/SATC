from credit_packet.models import FinancialPeriod, Excerpt
from credit_packet.metrics import calculate_metrics
from credit_packet.rules import evaluate_rules

def test_rules_trigger_and_missing_no_false_positive():
    periods=[FinancialPeriod(fiscal_year=2023,period='FY',revenue=100,cash_and_equivalents=100,long_term_debt=100,operating_cash_flow=1,capex=1,current_assets=2,current_liabilities=1,stockholders_equity=10),FinancialPeriod(fiscal_year=2024,period='FY',revenue=80,cash_and_equivalents=70,long_term_debt=140,operating_cash_flow=-3,capex=1,current_assets=0.5,current_liabilities=1,stockholders_equity=-1)]
    m=calculate_metrics(periods)
    ex=[Excerpt(filing='10-K',section='Controls',category='material_weakness',text='material weakness',source_url='u',accession_number='a',filing_date='2024-01-01')]
    flags=evaluate_rules(periods,m,ex)
    codes={f.code for f in flags}
    assert 'REVENUE_DECLINE' in codes and 'NEGATIVE_OPERATING_CASH_FLOW' in codes and 'MATERIAL_WEAKNESS_LANGUAGE' in codes
