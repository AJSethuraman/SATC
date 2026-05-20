from credit_packet.sec_client import SECClient
from credit_packet.config import Settings
from credit_packet.filing_text import clean_filing_text
from credit_packet.sections import extract_sections
from credit_packet.excerpts import find_excerpts
from credit_packet.changes import compare_filings_for_changes
from credit_packet.facts import normalize_periods
from credit_packet.metrics import calculate_metrics
from credit_packet.rules import evaluate_rules
from credit_packet.render import render_markdown
from credit_packet.models import CompanyIdentity, ResearchPacket

class FakeClient:
    def __init__(self,data):
        self.settings=Settings(sec_user_agent='UA')
        self.data=data
    def pad_cik(self,cik): return str(cik).zfill(10)
    def get_json(self,url): return self.data

def test_cik_and_accession_helpers():
    assert SECClient.normalize_accession('0001-22-333333')=='000122333333'
    assert SECClient.pad_cik('1234')=='0000001234'
    assert SECClient.unpad_cik('0000001234')=='1234'

def test_text_clean_sections_excerpts_changes():
    html='<html><body><h1>ITEM 1A Risk Factors</h1><p>We face liquidity pressure and debt obligations.</p><h2>Item 7 Management\'s Discussion</h2><p>going concern and substantial doubt discussed.</p></body></html>'
    text,paras=clean_filing_text(html)
    assert 'liquidity pressure' in text.lower() and len(paras)>=2
    secs=extract_sections(text,'10-K')
    assert any(s['section']=='Risk Factors' for s in secs)
    processed=[{'form':'10-K','filing_date':'2025-01-01','accession_number':'a','source_url':'u','paragraphs':paras,'section_map':{i:'Risk Factors' for i,_ in enumerate(paras)}}]
    ex=find_excerpts(processed)
    assert any(e.category=='liquidity' for e in ex)
    old={'paragraphs':['We face debt obligations and covenant terms.','Other text long enough to be paragraph.'],'source_url':'old'}
    new={'paragraphs':['We face debt obligations and covenant terms amended with waiver.','Brand new litigation claim settlement paragraph long enough.'],'source_url':'new'}
    ch=compare_filings_for_changes(old,new)
    assert any(c.change_type in {'added','modified','removed'} for c in ch)

def test_facts_metrics_rules_render():
    fixture={"facts":{"us-gaap":{"Revenues":{"units":{"USD":[{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":100},{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":80}]}},"GrossProfit":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":20}]}},"OperatingIncomeLoss":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":10}]}},"NetIncomeLoss":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":5}]}},"CashAndCashEquivalentsAtCarryingValue":{"units":{"USD":[{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":40},{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":20}]}},"Assets":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":300}]}},"Liabilities":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":250}]}},"StockholdersEquity":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":50}]}},"AssetsCurrent":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":20}]}},"LiabilitiesCurrent":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":30}]}},"LongTermDebtNoncurrent":{"units":{"USD":[{"fy":2023,"fp":"FY","form":"10-K","filed":"2024-01-01","val":50},{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":70}]}},"NetCashProvidedByUsedInOperatingActivities":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":-5}]}},"PaymentsToAcquirePropertyPlantAndEquipment":{"units":{"USD":[{"fy":2024,"fp":"FY","form":"10-K","filed":"2025-01-01","val":-3}]}}}}}
    periods,_=normalize_periods(FakeClient(fixture),'1234',2)
    assert periods[-1].capex==3
    metrics=calculate_metrics(periods)
    flags=evaluate_rules(periods,metrics,[])
    codes={f.code for f in flags}
    assert 'REVENUE_DECLINE' in codes and 'NEGATIVE_OPERATING_CASH_FLOW' in codes and 'CURRENT_RATIO_BELOW_ONE' in codes
    pkt=ResearchPacket(company=CompanyIdentity('ABC','0000001234','ABC Co'),financial_periods=periods,calculated_metrics=metrics,watchlist_flags=flags,review_questions=['Q1'])
    md=render_markdown(pkt)
    assert '## Calculated Metrics' in md and 'Manual review required' in md
