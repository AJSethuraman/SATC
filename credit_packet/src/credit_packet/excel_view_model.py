from __future__ import annotations


def filing_activity_rows(packet):
    return [{'form':f.form,'filing_date':f.filing_date,'report_date':f.report_date,'accession_number':f.accession_number,'primary_document':f.primary_document,'source_link':'Open filing','source_url':f.filing_url or f.source} for f in packet.filings]

def financial_trend_rows(packet):
    rows=[]
    for p in packet.financial_periods:
        fcf=None if p.operating_cash_flow is None or p.capex is None else p.operating_cash_flow-p.capex
        rows.append({'fiscal_year':p.fiscal_year,'revenue':p.revenue,'gross_profit':p.gross_profit,'operating_income':p.operating_income,'net_income':p.net_income,'cash_and_equivalents':p.cash_and_equivalents,'current_assets':p.current_assets,'current_liabilities':p.current_liabilities,'total_assets':p.total_assets,'total_liabilities':p.total_liabilities,'stockholders_equity':p.stockholders_equity,'long_term_debt':p.long_term_debt,'operating_cash_flow':p.operating_cash_flow,'capex':p.capex,'free_cash_flow':fcf})
    return rows

def calculated_metric_rows(packet):
    return [m.__dict__.copy() for m in packet.calculated_metrics]

def watchlist_flag_rows(packet):
    return [{'severity':f.severity,'code':f.code,'period':f.period,'description':f.description,'observed_value':f.observed_value,'threshold':f.threshold,'source':f.source,'requires_manual_review':f.requires_manual_review} for f in packet.watchlist_flags]

def excerpt_rows(packet, preview_chars: int = 500):
    rows=[]
    for e in packet.excerpts:
        rows.append({'category':e.category,'filing':e.filing,'filing_date':e.filing_date,'section':e.section,'matched_keywords':', '.join(e.matched_keywords),'excerpt_preview':((e.text or '')[:preview_chars] + ('…' if len(e.text or '')>preview_chars else '')),'excerpt_full':e.text or '','source_link':'Open source','source_url':e.source_url,'accession_number':e.accession_number})
    return rows or [{'category':'info','filing':'','filing_date':'','section':'','matched_keywords':'','excerpt_preview':'No excerpts were detected based on controlled keyword search.','excerpt_full':'','source_link':'','source_url':'','accession_number':''}]

def filing_change_rows(packet, preview_chars: int = 350):
    rows=[]
    for c in packet.filing_changes:
        rows.append({'section':c.section,'category':c.category,'change_type':c.change_type,'similarity_score':c.similarity_score,'old_preview':((c.old_excerpt or '')[:preview_chars] + ('…' if len(c.old_excerpt or '')>preview_chars else '')),'new_preview':((c.new_excerpt or '')[:preview_chars] + ('…' if len(c.new_excerpt or '')>preview_chars else '')),'old_full':c.old_excerpt or '','new_full':c.new_excerpt or '','old_source_link':'Open old source','new_source_link':'Open new source','old_source':c.source_old,'new_source':c.source_new})
    return rows or [{'section':'','category':'','change_type':'','similarity_score':None,'old_preview':'No filing changes were detected or comparison was unavailable.','new_preview':'','old_full':'','new_full':'','old_source_link':'','new_source_link':'','old_source':'','new_source':''}]

def review_question_rows(packet):
    out=[]
    sb=packet.source_bound_brief
    if sb and sb.review_questions:
        for i,q in enumerate(sb.review_questions,1): out.append({'question_no':i,'question':q.question,'based_on':', '.join(q.based_on),'source_trigger':'source_bound','priority':'Medium'})
    else:
        for i,q in enumerate(packet.review_questions,1): out.append({'question_no':i,'question':q,'based_on':'deterministic','source_trigger':'packet','priority':'Medium'})
    return out

def evidence_index_rows(packet):
    b=packet.evidence_bundle or {}
    rows=[]
    for f in b.get('filings',[]): rows.append({'evidence_id':f['id'],'type':'filing','label':f.get('form'),'period_or_date':f.get('filing_date'),'source':f.get('source_url')})
    for m in b.get('metrics',[]): rows.append({'evidence_id':m['id'],'type':'metric','label':m.get('label'),'period_or_date':m.get('period'),'source':m.get('source')})
    for fl in b.get('flags',[]): rows.append({'evidence_id':fl['id'],'type':'flag','label':fl.get('code'),'period_or_date':fl.get('period'),'source':fl.get('source')})
    for e in b.get('excerpts',[]): rows.append({'evidence_id':e['id'],'type':'excerpt','label':e.get('category'),'period_or_date':e.get('filing_date'),'source':e.get('source_url')})
    for c in b.get('filing_changes',[]): rows.append({'evidence_id':c['id'],'type':'change','label':c.get('category'),'period_or_date':c.get('section'),'source':c.get('new_source')})
    return rows

def run_metadata_rows(packet, generated_ts):
    return [{'key':'Generated Timestamp','value':generated_ts},{'key':'LLM Provider/Mode','value':next((a.split(':',1)[1] for a in packet.audit_log if a.startswith('llm_provider:')),'none')},{'key':'Source-Bound Validation','value':next((a.split(':',1)[1] for a in packet.audit_log if a.startswith('source_bound_validation:')),'unknown')}]

def source_document_rows(packet):
    return [{'label':f'{f.form} {f.filing_date or ""}','url':f.filing_url or f.source,'accession':f.accession_number} for f in packet.filings]

def field_audit_rows(packet):
    rows=[]
    for p in packet.financial_periods:
        for field,tag in p.tag_map.items(): rows.append({'fiscal_year':p.fiscal_year,'field':field,'selected_tag':tag})
    return rows

def data_quality_rows(packet, preview_chars: int = 500):
    rows=[]
    for p in packet.financial_periods:
        missing=[k for k,v in p.__dict__.items() if k in {'revenue','gross_profit','operating_income','net_income','cash_and_equivalents','total_assets','total_liabilities','stockholders_equity','current_assets','current_liabilities','long_term_debt','operating_cash_flow','capex'} and v is None]
        if missing: rows.append({'issue':'missing financial fields','detail':f"FY{p.fiscal_year}: {', '.join(missing)}"})
    if len([f for f in packet.filings if f.form=='10-K'])<2: rows.append({'issue':'unavailable comparison filings','detail':'Prior comparable 10-K unavailable for change comparison.'})
    if not packet.excerpts: rows.append({'issue':'no excerpts detected','detail':'Controlled keyword search returned no excerpts.'})
    if not packet.filing_changes: rows.append({'issue':'no filing changes detected','detail':'No filing changes detected or comparison unavailable.'})
    sb=packet.source_bound_brief
    if sb: rows.append({'issue':'source-bound brief validation status','detail':f"{sb.validation_status}: {' | '.join(sb.validation_notes) if sb.validation_notes else 'no notes'}"})
    if sb and sb.generation_mode!='ollama': rows.append({'issue':'LLM disabled/fallback status','detail':sb.generation_mode})
    if packet.excerpts: rows.append({'issue':'truncated previews','detail':f'Excerpt previews capped at {preview_chars} chars.'})
    if packet.filing_changes: rows.append({'issue':'truncated previews','detail':'Filing change previews capped at 350 chars.'})
    return rows
