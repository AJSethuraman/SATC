from .models import Excerpt
KEYWORDS = {
    'liquidity':['liquidity','capital resources'], 'debt':['debt','borrowings'],
    'covenant':['covenant'], 'default_or_waiver':['waiver','default','amendment'],
    'going_concern':['going concern','substantial doubt'], 'material_weakness':['material weakness','internal control'],
    'customer_concentration':['customer concentration'], 'litigation':['litigation','legal proceedings'],
    'cybersecurity':['cybersecurity','cyber attack'], 'executive_change':['chief executive officer','resigned'],
    'auditor_change':['auditor','accounting firm']
}

def find_excerpts(filings):
    excerpts=[]
    for f in filings:
        txt=(f.primary_document or '').lower()
        for cat, kws in KEYWORDS.items():
            if any(k in txt for k in kws):
                excerpts.append(Excerpt(filing=f.form, section='Unknown', category=cat, text=f'Keyword hit in primary document name: {f.primary_document}', source_url=f.filing_url or f.source, accession_number=f.accession_number, filing_date=f.filing_date or 'Unavailable'))
    return excerpts
