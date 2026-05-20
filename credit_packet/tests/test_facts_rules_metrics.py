from credit_packet.facts import normalize_periods
from credit_packet.metrics import calculate_metrics
from credit_packet.rules import evaluate_rules

class FakeClient:
    def __init__(self,data):
        self.data=data
        class S: sec_base_facts='https://data.sec.gov/api/xbrl/companyfacts'
        self.settings=S()
    def pad_cik(self,cik): return str(cik).zfill(10)
    def get_json(self,url): return self.data

def fixture_data():
    return {"facts":{"us-gaap":{
    "RevenueFromContractWithCustomerExcludingAssessedTax":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-02-01","val":120}]}} ,
    "Revenues":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":100},{"fy":2024,"fp":"Q1","form":"10-Q","filed":"2024-04-01","val":20},{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":150}]}} ,
    "GrossProfit":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":30}]}} ,
    "OperatingIncomeLoss":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":10}]}} ,
    "ProfitLoss":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":5}]}} ,
    "CashAndCashEquivalentsAtCarryingValue":{"units":{"USD":[{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":100},{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":70}]}} ,
    "Assets":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":300}]}} ,
    "Liabilities":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":260}]}} ,
    "StockholdersEquity":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":40}]}} ,
    "AssetsCurrent":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":30}]}} ,
    "LiabilitiesCurrent":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":50}]}} ,
    "LongTermDebt":{"units":{"USD":[{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":80},{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":110}]}} ,
    "NetCashProvidedByUsedInOperatingActivities":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":-4}]}} ,
    "PaymentsToAcquireProductiveAssets":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":-6}]}} }}}

def test_xbrl_annual_selection_skips_q():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    assert periods[-1].revenue in (100,120)

def test_xbrl_tag_fallback_used():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    assert periods[-1].tag_map['net_income'] == 'ProfitLoss'

def test_capex_abs_normalization():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    assert periods[-1].capex == 6

def test_metrics_free_cash_flow():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    m = calculate_metrics(periods)[-1]
    assert m.free_cash_flow == -10

def test_metrics_divide_by_zero_none():
    from credit_packet.models import FinancialPeriod
    m = calculate_metrics([FinancialPeriod(fiscal_year=2024,period='FY',revenue=0,current_liabilities=0,current_assets=1)])[0]
    assert m.current_ratio is None and m.gross_margin is None

def test_rule_revenue_decline():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='REVENUE_DECLINE' for f in flags)

def test_rule_cash_decline():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='CASH_DECLINE' for f in flags)

def test_rule_debt_increase():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='DEBT_INCREASE' for f in flags)

def test_rule_current_ratio_below_one():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='CURRENT_RATIO_BELOW_ONE' for f in flags)

def test_rule_negative_ocf():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='NEGATIVE_OPERATING_CASH_FLOW' for f in flags)

def test_rule_negative_fcf():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 2)
    flags = evaluate_rules(periods, calculate_metrics(periods), [])
    assert any(f.code=='NEGATIVE_FREE_CASH_FLOW' for f in flags)

def test_no_false_trigger_missing_data():
    from credit_packet.models import FinancialPeriod
    periods=[FinancialPeriod(fiscal_year=2024,period='FY')]
    flags=evaluate_rules(periods,calculate_metrics(periods),[])
    assert len(flags)==0
