from datetime import datetime
from .models import FilingRecord

def _to_records(recent, source, cik):
    out=[]
    for i,form in enumerate(recent.get('form',[])):
        acc=recent.get('accessionNumber',[None])[i]
        if not acc:
            continue
        primary=recent.get('primaryDocument',[''])[i]
        acc_n=acc.replace('-','')
        filing_url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_n}/{primary}' if primary else None
        out.append(FilingRecord(accession_number=acc,form=form,filing_date=recent.get('filingDate',[None])[i],report_date=recent.get('reportDate',[None])[i],primary_document=primary,filing_url=filing_url,source=source))
    return out

def get_submissions(client,cik:str):
    cik_p=client.pad_cik(cik)
    url=f'{client.settings.sec_base_submissions}/CIK{cik_p}.json'
    return client.get_json(url),url

def _sort_date(r):
    return datetime.fromisoformat((r.filing_date or '1900-01-01'))

def _pick(forms,exact,amend):
    primary=[f for f in forms if f.form==exact]
    use=primary if primary else [f for f in forms if f.form==amend]
    return sorted(use,key=_sort_date,reverse=True)

def get_filing_set(client,cik:str):
    sub,url=get_submissions(client,cik)
    recent=sub.get('filings',{}).get('recent',{})
    rec=_to_records(recent,url,cik)
    k_list=_pick(rec,'10-K','10-K/A')
    q_list=_pick(rec,'10-Q','10-Q/A')
    eights=sorted([f for f in rec if f.form=='8-K'],key=_sort_date,reverse=True)[:8]
    return {'all':rec,'latest_10k':k_list[0] if k_list else None,'prior_10k':k_list[1] if len(k_list)>1 else None,'latest_10q':q_list[0] if q_list else None,'prior_10q':q_list[1] if len(q_list)>1 else None,'recent_8k':eights,'source':url}
