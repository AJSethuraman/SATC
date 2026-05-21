from __future__ import annotations
import re


def _slug(v: str) -> str:
    return re.sub(r'[^a-z0-9:_-]+', '-', (v or '').lower()).strip('-')


def _fmt_pct(v):
    return None if v is None else f"{v*100:.1f}%"


def build_evidence_bundle(packet, text_limit: int = 600):
    filings=[]
    for f in packet.filings:
        fid=f"filing:{_slug(f.form)}:{f.filing_date or 'na'}:{_slug(f.accession_number)}"
        filings.append({'id':fid,'form':f.form,'filing_date':f.filing_date,'report_date':f.report_date,'accession_number':f.accession_number,'source_url':f.filing_url or f.source})

    metrics=[]
    for m in packet.calculated_metrics:
        items=[('revenue_growth','Revenue Growth',m.revenue_growth, _fmt_pct(m.revenue_growth)),('gross_margin','Gross Margin',m.gross_margin,_fmt_pct(m.gross_margin)),('operating_margin','Operating Margin',m.operating_margin,_fmt_pct(m.operating_margin)),('net_margin','Net Margin',m.net_margin,_fmt_pct(m.net_margin)),('cash_change_pct','Cash Change',m.cash_change_pct,_fmt_pct(m.cash_change_pct)),('current_ratio','Current Ratio',m.current_ratio,m.current_ratio),('debt_change_pct','Debt Change',m.debt_change_pct,_fmt_pct(m.debt_change_pct)),('debt_to_equity','Debt/Equity',m.debt_to_equity,m.debt_to_equity),('operating_cash_flow_margin','OCF Margin',m.operating_cash_flow_margin,_fmt_pct(m.operating_cash_flow_margin)),('free_cash_flow','Free Cash Flow',m.free_cash_flow,m.free_cash_flow),('free_cash_flow_margin','FCF Margin',m.free_cash_flow_margin,_fmt_pct(m.free_cash_flow_margin))]
        for key,label,raw,val in items:
            metrics.append({'id':f'metric:{key}:{m.fiscal_year}','label':label,'period':str(m.fiscal_year),'value':val,'raw_value':raw,'source':'calculated_metrics'})

    flags=[{'id':f"flag:{_slug(f.code)}:{_slug(f.period)}",'code':f.code,'severity':f.severity,'description':f.description,'period':f.period,'observed_value':f.observed_value,'threshold':f.threshold,'source':f.source} for f in packet.watchlist_flags]

    excerpts=[]
    for i,e in enumerate(packet.excerpts,1):
        excerpts.append({'id':f'excerpt:{_slug(e.category)}:{i:03d}','category':e.category,'filing':e.filing,'filing_date':e.filing_date,'section':e.section,'text':(e.text or '')[:text_limit],'source_url':e.source_url,'accession_number':e.accession_number})

    changes=[]
    for i,c in enumerate(packet.filing_changes,1):
        changes.append({'id':f'change:{_slug(c.section)}:{i:03d}','section':c.section,'category':c.category,'change_type':c.change_type,'similarity_score':c.similarity_score,'old_text':(c.old_excerpt or '')[:text_limit],'new_text':(c.new_excerpt or '')[:text_limit],'old_source':c.source_old,'new_source':c.source_new})

    audit=[{'id':f'audit:{i:03d}','value':a} for i,a in enumerate(packet.audit_log,1)]

    return {'company':{'id':f"company:{_slug(packet.company.ticker)}",'ticker':packet.company.ticker,'name':packet.company.name,'cik':packet.company.cik},'filings':filings,'metrics':metrics,'flags':flags,'excerpts':excerpts,'filing_changes':changes,'audit':audit}


def valid_evidence_ids(bundle):
    ids={bundle.get('company',{}).get('id')}
    for k in ('filings','metrics','flags','excerpts','filing_changes','audit'):
        ids.update(x.get('id') for x in bundle.get(k,[]))
    return {i for i in ids if i}


def allowed_values(bundle):
    vals=set()
    for m in bundle.get('metrics',[]):
        for k in ('value','raw_value','period'): vals.add(str(m.get(k)))
    for f in bundle.get('flags',[]):
        vals.add(str(f.get('observed_value'))); vals.add(str(f.get('threshold')))
    return {v for v in vals if v and v!='None'}
