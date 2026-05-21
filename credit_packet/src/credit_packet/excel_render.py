from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

def render_excel(packet, output_path: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    except Exception as exc:
        raise RuntimeError('openpyxl is required for .xlsx output. Install dependencies via python bootstrap.py') from exc

    NAVY = PatternFill('solid', fgColor='1F3A5F')
    WHITE = Font(color='FFFFFF', bold=True)
    THIN = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

    def header(ws, headers):
        ws.append(headers)
        for c in ws[1]: c.fill=NAVY; c.font=WHITE; c.border=THIN
        ws.freeze_panes='A2'; ws.auto_filter.ref=f"A1:{chr(64+len(headers))}1"

    def style(ws, wrap=()):
        for r in ws.iter_rows(min_row=2,max_row=ws.max_row):
            for c in r:
                c.border=THIN
                if c.column_letter in wrap: c.alignment=Alignment(wrap_text=True, vertical='top')

    wb=Workbook(); wb.remove(wb.active)

    ws=wb.create_sheet('Summary')
    for r in [('Workbook Title','Credit Research Packet'),('Company',packet.company.name),('Ticker',packet.company.ticker),('CIK',packet.company.cik),('Generated',datetime.now(timezone.utc).isoformat()),('Latest 10-K',next((f.filing_date for f in packet.filings if f.form=='10-K'),'Unavailable')),('Latest 10-Q',next((f.filing_date for f in packet.filings if f.form=='10-Q'),'Unavailable')),('Number of recent 8-Ks reviewed',sum(1 for f in packet.filings if f.form=='8-K')),('Number of watchlist flags',len(packet.watchlist_flags)),('Number of filing excerpts',len(packet.excerpts)),('Number of filing changes',len(packet.filing_changes)),('LLM provider/mode',next((a.split(':',1)[1] for a in packet.audit_log if a.startswith('llm_provider:')),'none')),('Statement','Manual review required. No automated credit conclusion generated.')]: ws.append(r)
    ws.append(('How to use this workbook','Review Filing Activity; Financial Trends and Calculated Metrics; Watchlist Flags; Excerpts and Filing Changes; complete Manual Credit Conclusion in Memo Shell.'))
    ws.column_dimensions['A'].width=40; ws.column_dimensions['B'].width=120

    ws=wb.create_sheet('Filing Activity'); header(ws,['Form','Filing Date','Report Date','Accession Number','Primary Document','Source URL'])
    for f in packet.filings: ws.append([f.form,f.filing_date,f.report_date,f.accession_number,f.primary_document,f.filing_url or f.source]); ws.cell(ws.max_row,6).hyperlink=ws.cell(ws.max_row,6).value
    style(ws)

    ws=wb.create_sheet('Financial Trends'); header(ws,['Fiscal Year','Revenue','Gross Profit','Operating Income','Net Income','Cash & Equivalents','Current Assets','Current Liabilities','Total Assets','Total Liabilities','Stockholders’ Equity','Long-Term Debt','Operating Cash Flow','Capex','Free Cash Flow'])
    for p in packet.financial_periods:
        fcf=None if p.operating_cash_flow is None or p.capex is None else p.operating_cash_flow-p.capex
        ws.append([p.fiscal_year,p.revenue,p.gross_profit,p.operating_income,p.net_income,p.cash_and_equivalents,p.current_assets,p.current_liabilities,p.total_assets,p.total_liabilities,p.stockholders_equity,p.long_term_debt,p.operating_cash_flow,p.capex,fcf])
    for row in ws.iter_rows(min_row=2,min_col=2,max_col=15):
        for c in row: c.number_format='$#,##0';
    style(ws)

    ws=wb.create_sheet('Calculated Metrics'); header(ws,['Fiscal Year','Revenue Growth %','Gross Margin %','Operating Margin %','Net Margin %','Cash Change %','Current Ratio','Debt Change %','Debt / Equity','Operating Cash Flow Margin %','Free Cash Flow','Free Cash Flow Margin %'])
    for m in packet.calculated_metrics: ws.append([m.fiscal_year,m.revenue_growth,m.gross_margin,m.operating_margin,m.net_margin,m.cash_change_pct,m.current_ratio,m.debt_change_pct,m.debt_to_equity,m.operating_cash_flow_margin,m.free_cash_flow,m.free_cash_flow_margin])
    style(ws)

    ws=wb.create_sheet('Watchlist Flags'); header(ws,['Severity','Flag Code','Period / Filing','Description','Observed Value','Threshold','Source','Manual Review Required'])
    for f in packet.watchlist_flags: ws.append([f.severity,f.code,f.period,f.description,f.observed_value,f.threshold,f.source,f.requires_manual_review])
    style(ws,wrap=('D',))

    ws=wb.create_sheet('Excerpts'); header(ws,['Category','Filing Form','Filing Date','Section','Matched Keywords','Excerpt','Source URL','Accession Number'])
    if packet.excerpts:
        for e in packet.excerpts: ws.append([e.category,e.filing,e.filing_date,e.section,', '.join(e.matched_keywords),e.text[:1200],e.source_url,e.accession_number]); ws.cell(ws.max_row,7).hyperlink=e.source_url
    else: ws.append(['','','','','','No excerpts were detected based on controlled keyword search.','',''])
    style(ws,wrap=('F',))

    ws=wb.create_sheet('Filing Changes'); header(ws,['Section','Category','Change Type','Similarity Score','Old Text','New Text','Old Source','New Source'])
    if packet.filing_changes:
        for c in packet.filing_changes: ws.append([c.section,c.category,c.change_type,c.similarity_score,c.old_excerpt[:1200],c.new_excerpt[:1200],c.source_old,c.source_new]); ws.cell(ws.max_row,7).hyperlink=c.source_old; ws.cell(ws.max_row,8).hyperlink=c.source_new
    else: ws.append(['','','','','No filing changes were detected or comparison was unavailable.','','',''])
    style(ws,wrap=('E','F'))

    ws=wb.create_sheet('Review Questions'); header(ws,['Question #','Question','Based On','Source / Trigger'])
    if packet.source_bound_brief and packet.source_bound_brief.review_questions:
        for i,q in enumerate(packet.source_bound_brief.review_questions,1): ws.append([i,q.question,', '.join(q.based_on),'source_bound'])
    else:
        for i,q in enumerate(packet.review_questions,1): ws.append([i,q,'deterministic','packet'])
    style(ws,wrap=('B',))

    ws=wb.create_sheet('Memo Shell')
    for s in ['Company Overview','Recent Filing Activity','Financial Trend Summary','Rule-Based Watchlist Flags','Notable Filing Language','Open Questions','Manual Credit Conclusion']:
        ws.append([s]); ws.cell(ws.max_row,1).font=Font(bold=True); ws.append([''])
    ws.append(['Manual review required. No automated credit conclusion generated.'])

    ws=wb.create_sheet('Sources & Audit'); header(ws,['Type','Value'])
    for a in packet.audit_log: ws.append(['audit',a])
    ws.append(['cache','.cache/sec'])
    style(ws,wrap=('B',))

    ws=wb.create_sheet('Source-Bound Brief'); header(ws,['Type','Text','Sources','Validation Status'])
    brief=packet.source_bound_brief
    if brief:
        for x in brief.summary_points: ws.append(['summary_point',x.text,', '.join(x.sources),brief.validation_status])
        for x in brief.review_themes: ws.append(['review_theme',f"{x.theme}: {x.why_it_matters}",', '.join(x.sources),brief.validation_status])
        for x in brief.missing_information: ws.append(['missing_information',f"{x.item}: {x.reason}",'',brief.validation_status])
    style(ws,wrap=('B',))

    ws=wb.create_sheet('Evidence Index'); header(ws,['Evidence ID','Type','Label / Category','Period / Filing Date','Source URL / Source'])
    b=packet.evidence_bundle or {}
    for f in b.get('filings',[]): ws.append([f['id'],'filing',f.get('form'),f.get('filing_date'),f.get('source_url')])
    for m in b.get('metrics',[]): ws.append([m['id'],'metric',m.get('label'),m.get('period'),m.get('source')])
    for fl in b.get('flags',[]): ws.append([fl['id'],'flag',fl.get('code'),fl.get('period'),fl.get('source')])
    for e in b.get('excerpts',[]): ws.append([e['id'],'excerpt',e.get('category'),e.get('filing_date'),e.get('source_url')])
    for c in b.get('filing_changes',[]): ws.append([c['id'],'change',c.get('category'),c.get('section'),c.get('new_source')])
    style(ws)

    # reorder to required + added sheets
    order=['Summary','Filing Activity','Financial Trends','Calculated Metrics','Watchlist Flags','Excerpts','Filing Changes','Review Questions','Memo Shell','Sources & Audit','Source-Bound Brief','Evidence Index']
    wb._sheets=[wb[s] for s in order]
    output_path.parent.mkdir(parents=True, exist_ok=True); wb.save(output_path)
