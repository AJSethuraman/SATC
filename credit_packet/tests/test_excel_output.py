import pytest
pytest.importorskip('openpyxl')
from pathlib import Path
from openpyxl import load_workbook
from credit_packet.models import CompanyIdentity, ResearchPacket, FilingRecord, FinancialPeriod, CalculatedMetric, WatchlistFlag, Excerpt, FilingChange
from credit_packet.excel_render import render_excel
from credit_packet.render import render_markdown

# ... same content

def sample_packet():
    return ResearchPacket(
        company=CompanyIdentity(ticker='AAPL', cik='0000320193', name='Apple Inc.'),
        filings=[FilingRecord(accession_number='0001-01-000001', form='10-K', filing_date='2025-10-31', report_date='2025-09-30', primary_document='a10k.htm', filing_url='https://example.com/10k', source='s')],
        financial_periods=[FinancialPeriod(fiscal_year=2024, period='FY', revenue=100, gross_profit=40, operating_income=30, net_income=20, cash_and_equivalents=50, current_assets=60, current_liabilities=30, total_assets=300, total_liabilities=180, stockholders_equity=120, long_term_debt=70, operating_cash_flow=25, capex=10, tag_map={'revenue':'Revenues'})],
        calculated_metrics=[CalculatedMetric(fiscal_year=2024, revenue_growth=0.1, gross_margin=0.4, operating_margin=0.3, net_margin=0.2, cash_change_pct=-0.1, current_ratio=2.0, debt_change_pct=0.05, debt_to_equity=0.58, operating_cash_flow_margin=0.25, free_cash_flow=15, free_cash_flow_margin=0.15)],
        watchlist_flags=[WatchlistFlag(code='NEGATIVE_FREE_CASH_FLOW', severity='medium', description='desc', metric='m', threshold='<0', observed_value='-5', period='2024', source='metrics')],
        excerpts=[Excerpt(filing='10-K', section='Risk Factors', category='liquidity', text='revenue decline and hold cash', matched_keywords=['liquidity'], source_url='https://example.com/ex', accession_number='0001', filing_date='2025-10-31')],
        filing_changes=[FilingChange(section='Risk Factors', category='liquidity', old_excerpt='old', new_excerpt='new', change_type='modified', similarity_score=0.7, source_old='https://example.com/old', source_new='https://example.com/new')],
        review_questions=['What explains revenue decline?'],
        memo_draft='Manual review required. No automated credit conclusion generated.',
        audit_log=['llm_provider:none','submissions:url'],
    )

# tests omitted for brevity in generation

def test_xlsx_output_file_created(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); assert out.exists()

def test_workbook_required_sheets_order(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); wb=load_workbook(out); assert wb.sheetnames==['Summary','Filing Activity','Financial Trends','Calculated Metrics','Watchlist Flags','Excerpts','Filing Changes','Review Questions','Memo Shell','Sources & Audit']

def test_summary_contains_manual_review(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Summary']; vals=' '.join(str(c.value) for row in ws.iter_rows(min_row=1,max_row=30) for c in row if c.value); assert 'Manual review required' in vals

def test_watchlist_headers(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Watchlist Flags']; assert [ws.cell(1,i).value for i in range(1,9)]==['Severity','Flag Code','Period / Filing','Description','Observed Value','Threshold','Source','Manual Review Required']

def test_financial_trends_headers(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Financial Trends']; assert ws['A1'].value=='Fiscal Year' and ws['O1'].value=='Free Cash Flow'

def test_calculated_metrics_headers(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Calculated Metrics']; assert ws['A1'].value=='Fiscal Year' and ws['L1'].value=='Free Cash Flow Margin %'

def test_excerpts_headers(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Excerpts']; assert ws['A1'].value=='Category' and ws['H1'].value=='Accession Number'

def test_sources_audit_exists(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); wb=load_workbook(out); assert 'Sources & Audit' in wb.sheetnames

def test_markdown_still_works():
    assert 'Credit Research Packet' in render_markdown(sample_packet())

def test_no_prohibited_conclusion_in_excel(tmp_path):
    out=tmp_path/'packet.xlsx'; render_excel(sample_packet(), out); ws=load_workbook(out)['Summary']; vals=' '.join(str(c.value).lower() for row in ws.iter_rows(min_row=1,max_row=30) for c in row if c.value); assert 'investment recommendation' not in vals and 'buy rating' not in vals
