from credit_packet.facts import normalize_periods
from credit_packet.metrics import calculate_metrics
from credit_packet.rules import evaluate_rules
from credit_packet.excel_view_model import data_quality_rows
from credit_packet.models import ResearchPacket, CompanyIdentity

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

def test_cash_fallback_restricted_cash_tag():
    data = fixture_data()
    data['facts']['us-gaap'].pop('CashAndCashEquivalentsAtCarryingValue', None)
    data['facts']['us-gaap']['CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents']={"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":88}]}}
    periods,_ = normalize_periods(FakeClient(data), '1', 1)
    assert periods[-1].cash_and_equivalents == 88
    assert periods[-1].tag_map['cash_and_equivalents'] == 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'

def test_total_liabilities_direct_liabilities_preferred():
    periods,_ = normalize_periods(FakeClient(fixture_data()), '1', 1)
    assert periods[-1].total_liabilities == 260
    assert periods[-1].tag_map['total_liabilities'] == 'Liabilities'

def test_total_liabilities_derived_when_missing_direct_tag():
    data = fixture_data()
    data['facts']['us-gaap'].pop('Liabilities', None)
    periods,_ = normalize_periods(FakeClient(data), '1', 1)
    assert periods[-1].total_liabilities == 260
    assert periods[-1].tag_map['total_liabilities'] == 'DERIVED:AssetsMinusStockholdersEquity'

def test_current_liabilities_does_not_use_total_liabilities():
    data = fixture_data()
    data['facts']['us-gaap'].pop('LiabilitiesCurrent', None)
    periods,_ = normalize_periods(FakeClient(data), '1', 1)
    assert periods[-1].current_liabilities is None

def test_long_term_debt_prefers_noncurrent_tag():
    data = fixture_data()
    data['facts']['us-gaap']['LongTermDebtNoncurrent']={"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-02","val":95}]}}
    periods,_ = normalize_periods(FakeClient(data), '1', 1)
    assert periods[-1].long_term_debt == 95
    assert periods[-1].tag_map['long_term_debt'] == 'LongTermDebtNoncurrent'

def test_data_quality_rows_include_missing_and_derived_notes():
    data = fixture_data()
    data['facts']['us-gaap'].pop('Liabilities', None)
    data['facts']['us-gaap'].pop('GrossProfit', None)
    periods,_ = normalize_periods(FakeClient(data), '1', 1)
    packet = ResearchPacket(company=CompanyIdentity(ticker='INTC', cik='1', name='Intel'), financial_periods=periods)
    rows = data_quality_rows(packet)
    details = [r['detail'] for r in rows]
    assert any('gross_profit' in d for d in details)
    assert any('total_liabilities derived from total_assets - stockholders_equity' in d for d in details)

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


def test_material_weakness_flag_enriched_with_excerpt_context():
    from credit_packet.models import Excerpt
    ex=[Excerpt(filing='10-K',section='Controls and Procedures',category='material_weakness',text='material weakness in internal control over financial reporting with remediation plan',matched_keywords=['material weakness'],source_url='https://example.com/mw',accession_number='a',filing_date='2025-01-01')]
    flags = evaluate_rules([], [], ex)
    f = next(x for x in flags if x.code=='MATERIAL_WEAKNESS_LANGUAGE')
    assert f.excerpt_preview and 'material weakness' in f.excerpt_preview.lower()
    assert f.evidence_id == 'excerpt:material_weakness:001'
    assert f.section == 'Controls and Procedures' and f.filing == '10-K'
