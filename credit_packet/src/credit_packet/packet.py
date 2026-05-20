from .models import CompanyIdentity, ResearchPacket
from .cik_lookup import ticker_to_identity
from .filings import get_filing_set
from .facts import normalize_periods
from .metrics import calculate_metrics
from .rules import evaluate_rules
from .llm import LLMClient
from .filing_text import clean_filing_text
from .sections import extract_sections
from .excerpts import find_excerpts
from .changes import compare_filings_for_changes

def _process_doc(client,cik,filing):
    if not filing or not filing.primary_document: return None
    url,raw=client.download_filing_document(cik,filing.accession_number,filing.primary_document)
    text,paras=clean_filing_text(raw)
    secs=extract_sections(text,filing.form)
    section_map={}
    for i,p in enumerate(paras):
        section_map[i]=next((s['section'] for s in secs if p in s['text']),'Full Text')
    return {'form':filing.form,'filing_date':filing.filing_date,'accession_number':filing.accession_number,'source_url':url,'text':text,'paragraphs':paras,'sections':secs,'section_map':section_map}

def build_packet(client,settings,ticker:str,years:int=3):
    t,cik,name=ticker_to_identity(client,ticker)
    fs=get_filing_set(client,cik)
    filings=[x for x in [fs['latest_10k'],fs['prior_10k'],fs['latest_10q'],fs['prior_10q']] if x] + fs['recent_8k']
    periods,facts_source=normalize_periods(client,cik,years)
    metrics=calculate_metrics(periods)
    processed=[_process_doc(client,cik,f) for f in filings[:6]]
    processed=[p for p in processed if p]
    excerpts=find_excerpts(processed)
    changes=compare_filings_for_changes(_process_doc(client,cik,fs['prior_10k']) if fs['prior_10k'] else None,_process_doc(client,cik,fs['latest_10k']) if fs['latest_10k'] else None)
    flags=evaluate_rules(periods,metrics,excerpts)
    llm=LLMClient(settings)
    questions=llm.generate_review_questions(flags,changes)
    memo=llm.draft_memo_shell(None)
    audit=[f"submissions:{fs['source']}",f"facts:{facts_source}",f"cache:.cache/sec",f"llm_provider:{settings.llm_provider}"]+[f"filing:{f.filing_url}" for f in filings if f.filing_url]
    return ResearchPacket(company=CompanyIdentity(ticker=t,cik=cik,name=name),filings=filings,financial_periods=periods,calculated_metrics=metrics,watchlist_flags=flags,excerpts=excerpts,filing_changes=changes,review_questions=questions,memo_draft=memo,audit_log=audit)
