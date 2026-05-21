from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path




def _header(ws, headers):
    ws.append(headers)
    for c in ws[1]:
        c.fill = NAVY; c.font = WHITE; c.border = THIN
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{chr(64+len(headers))}1"


def _style_rows(ws, wrap_cols=()):
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = THIN
            if cell.column_letter in wrap_cols:
                cell.alignment = Alignment(wrap_text=True, vertical='top')


def render_excel(packet, output_path: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    except Exception as exc:
        raise RuntimeError("openpyxl is required for .xlsx output. Install dependencies via python bootstrap.py") from exc

    global NAVY, WHITE, THIN
    NAVY = PatternFill('solid', fgColor='1F3A5F')
    WHITE = Font(color='FFFFFF', bold=True)
    THIN = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

    wb=Workbook()
    wb.remove(wb.active)

    # 1 Summary
    ws=wb.create_sheet('Summary')
    rows=[
        ('Workbook Title','Credit Research Packet'),('Company',packet.company.name),('Ticker',packet.company.ticker),('CIK',packet.company.cik),
        ('Generated',datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')),
        ('Latest 10-K',next((f.filing_date for f in packet.filings if f.form=='10-K'),'Unavailable')),
        ('Latest 10-Q',next((f.filing_date for f in packet.filings if f.form=='10-Q'),'Unavailable')),
        ('Recent 8-K Count',sum(1 for f in packet.filings if f.form=='8-K')),
        ('Watchlist Flags',len(packet.watchlist_flags)),('Excerpts',len(packet.excerpts)),('Filing Changes',len(packet.filing_changes)),
        ('LLM Mode',next((a.split(':',1)[1] for a in packet.audit_log if a.startswith('llm_provider:')),'none')),
        ('Manual Credit Conclusion','Manual review required. No automated credit conclusion generated.'),
    ]
    for r in rows: ws.append(r)
    ws.append(('', ''))
    ws.append(('How to use this workbook','Review Filing Activity, Financial Trends, Calculated Metrics, Watchlist Flags, Excerpts, Filing Changes, then complete Manual Credit Conclusion in Memo Shell.'))
    ws.column_dimensions['A'].width=30; ws.column_dimensions['B'].width=120
    for c in ws['A']: c.font=Font(bold=True)
    ws['B14'].alignment=Alignment(wrap_text=True)

    # 2 Filing Activity
    ws=wb.create_sheet('Filing Activity'); _header(ws,['Form','Filing Date','Report Date','Accession Number','Primary Document','Source URL'])
    for f in packet.filings:
        ws.append([f.form,f.filing_date,f.report_date,f.accession_number,f.primary_document,f.filing_url or f.source])
        cell=ws.cell(ws.max_row,6); cell.hyperlink=cell.value
    _style_rows(ws); ws.column_dimensions['F'].width=70

    # 3 Financial Trends
    ws=wb.create_sheet('Financial Trends'); _header(ws,['Fiscal Year','Revenue','Gross Profit','Operating Income','Net Income','Cash & Equivalents','Current Assets','Current Liabilities','Total Assets','Total Liabilities','Stockholders’ Equity','Long-Term Debt','Operating Cash Flow','Capex','Free Cash Flow'])
    for p in packet.financial_periods:
        fcf = None if p.operating_cash_flow is None or p.capex is None else p.operating_cash_flow-p.capex
        ws.append([p.fiscal_year,p.revenue,p.gross_profit,p.operating_income,p.net_income,p.cash_and_equivalents,p.current_assets,p.current_liabilities,p.total_assets,p.total_liabilities,p.stockholders_equity,p.long_term_debt,p.operating_cash_flow,p.capex,fcf])
    for row in ws.iter_rows(min_row=2,min_col=2,max_col=15):
        for c in row:
            c.number_format='$#,##0';
            if c.value is None: c.fill=PatternFill('solid',fgColor='EFEFEF')
    _style_rows(ws)

    # 4 Calculated Metrics
    ws=wb.create_sheet('Calculated Metrics'); _header(ws,['Fiscal Year','Revenue Growth %','Gross Margin %','Operating Margin %','Net Margin %','Cash Change %','Current Ratio','Debt Change %','Debt / Equity','Operating Cash Flow Margin %','Free Cash Flow','Free Cash Flow Margin %'])
    for m in packet.calculated_metrics:
        ws.append([m.fiscal_year,m.revenue_growth,m.gross_margin,m.operating_margin,m.net_margin,m.cash_change_pct,m.current_ratio,m.debt_change_pct,m.debt_to_equity,m.operating_cash_flow_margin,m.free_cash_flow,m.free_cash_flow_margin])
    for r in ws.iter_rows(min_row=2,max_row=ws.max_row):
        for idx in [2,3,4,5,6,8,10,12]: r[idx-1].number_format='0.0%'
        r[6].number_format='0.00x'; r[8].number_format='0.00x'; r[10].number_format='$#,##0'
        if isinstance(r[10].value,(int,float)) and r[10].value<0: r[10].fill=PatternFill('solid',fgColor='F8CBAD')
    _style_rows(ws)

    # 5 flags
    ws=wb.create_sheet('Watchlist Flags'); _header(ws,['Severity','Flag Code','Period / Filing','Description','Observed Value','Threshold','Source','Manual Review Required'])
    if packet.watchlist_flags:
      for f in packet.watchlist_flags:
        ws.append([f.severity,f.code,f.period,f.description,f.observed_value,f.threshold,f.source,f.requires_manual_review])
        sev=ws.cell(ws.max_row,1).value
        if sev=='high': ws.cell(ws.max_row,1).fill=PatternFill('solid',fgColor='F4CCCC')
        elif sev=='medium': ws.cell(ws.max_row,1).fill=PatternFill('solid',fgColor='FCE5CD')
    else: ws.append(['info','NO_FLAGS','N/A','No rule-based watchlist flags triggered based on available data.','','','','True'])
    _style_rows(ws,wrap_cols=('D',))

    # 6 excerpts
    ws=wb.create_sheet('Excerpts'); _header(ws,['Category','Filing Form','Filing Date','Section','Matched Keywords','Excerpt','Source URL','Accession Number'])
    if packet.excerpts:
      for e in packet.excerpts:
        ws.append([e.category,e.filing,e.filing_date,e.section,', '.join(e.matched_keywords),e.text[:1500],e.source_url,e.accession_number]); ws.cell(ws.max_row,7).hyperlink=e.source_url
    else: ws.append(['info','','','','','No excerpts were detected based on controlled keyword search.','',''])
    _style_rows(ws,wrap_cols=('F',)); ws.column_dimensions['F'].width=90; ws.column_dimensions['G'].width=60

    # 7 changes
    ws=wb.create_sheet('Filing Changes'); _header(ws,['Section','Category','Change Type','Similarity Score','Old Text','New Text','Old Source','New Source'])
    if packet.filing_changes:
      for c in packet.filing_changes:
        ws.append([c.section,c.category,c.change_type,c.similarity_score,c.old_excerpt[:1200],c.new_excerpt[:1200],c.source_old,c.source_new]); ws.cell(ws.max_row,7).hyperlink=c.source_old; ws.cell(ws.max_row,8).hyperlink=c.source_new
    else: ws.append(['','','','','No filing changes were detected or comparison was unavailable.','','',''])
    _style_rows(ws,wrap_cols=('E','F')); ws.column_dimensions['E'].width=70; ws.column_dimensions['F'].width=70

    ws=wb.create_sheet('Review Questions'); _header(ws,['Question #','Question','Based On','Source / Trigger'])
    for i,q in enumerate(packet.review_questions,1): ws.append([i,q,'Deterministic flags/excerpts/changes','packet'])
    _style_rows(ws,wrap_cols=('B',)); ws.column_dimensions['B'].width=100

    ws=wb.create_sheet('Memo Shell')
    memo_sections=['Company Overview','Recent Filing Activity','Financial Trend Summary','Rule-Based Watchlist Flags','Notable Filing Language','Open Questions','Manual Credit Conclusion']
    for s in memo_sections:
        ws.append([s]); ws.cell(ws.max_row,1).font=Font(bold=True); ws.append([''])
    ws.append(['Manual review required. No automated credit conclusion generated.'])
    ws.column_dimensions['A'].width=120; ws['A15'].alignment=Alignment(wrap_text=True)

    ws=wb.create_sheet('Sources & Audit'); _header(ws,['Type','Value'])
    for a in packet.audit_log: ws.append(['audit',a])
    ws.append(['generated',datetime.now(timezone.utc).isoformat()])
    ws.append(['cache','.cache/sec'])
    for p in packet.financial_periods:
        for field,tag in p.tag_map.items(): ws.append(['xbrl_tag',f'{p.fiscal_year}:{field}:{tag}'])
    _style_rows(ws,wrap_cols=('B',)); ws.column_dimensions['B'].width=120

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)