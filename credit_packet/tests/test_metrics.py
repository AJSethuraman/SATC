from credit_packet.models import FinancialPeriod
from credit_packet.metrics import calculate_metrics

def test_metrics_and_missing_handling():
    periods=[FinancialPeriod(fiscal_year=2023,period='FY',revenue=100,gross_profit=30,operating_income=10,net_income=5,cash_and_equivalents=40,long_term_debt=50,current_assets=20,current_liabilities=10,stockholders_equity=25,operating_cash_flow=8,capex=3),FinancialPeriod(fiscal_year=2024,period='FY',revenue=80,gross_profit=20,operating_income=4,net_income=2,cash_and_equivalents=20,long_term_debt=70,current_assets=8,current_liabilities=12,stockholders_equity=20,operating_cash_flow=-1,capex=2)]
    m=calculate_metrics(periods)
    assert m[1].revenue_growth == -0.2
    assert m[0].revenue_growth is None
    assert m[1].free_cash_flow == -3

def test_divide_zero_unavailable():
    p=[FinancialPeriod(fiscal_year=2024,period='FY',revenue=0,current_assets=1,current_liabilities=0)]
    m=calculate_metrics(p)[0]
    assert m.gross_margin is None
    assert m.current_ratio is None
