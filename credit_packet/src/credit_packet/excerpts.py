import re
from .models import Excerpt

KEYWORDS={
'liquidity':['liquidity','cash flows','working capital','capital resources','ability to fund','available liquidity'],
'debt':['credit facility','revolving credit','term loan','senior notes','notes payable','indebtedness','borrowings','debt obligations','maturity'],
'covenant':['covenant','financial covenant','compliance with covenants','required ratio'],
'default_or_waiver':['default','event of default','waiver','forbearance','amendment to credit agreement','noncompliance'],
'going_concern':['going concern','substantial doubt','ability to continue','continue as a going concern'],
'material_weakness':['material weakness','internal control over financial reporting','ineffective disclosure controls','remediation plan'],
'customer_concentration':['major customer','customer concentration','significant customer','accounted for more than'],
'litigation':['litigation','legal proceedings','lawsuit','claim','settlement'],
'cybersecurity':['cybersecurity','cyber attack','data breach','ransomware','information security'],
'executive_change':['resignation','terminated','appointed','chief executive officer','chief financial officer'],
'auditor_change':['independent registered public accounting firm','dismissed','resigned as auditor','change in accountant']}

def find_excerpts(processed_filings):
    out=[]; seen=set()
    for f in processed_filings:
        paras=f.get('paragraphs',[])
        for i,p in enumerate(paras):
            pl=p.lower()
            for cat,kws in KEYWORDS.items():
                matched=[k for k in kws if k in pl]
                if not matched: continue
                ctx=' '.join(paras[max(0,i-1):min(len(paras),i+2)])
                key=(f['accession_number'],cat,ctx[:180])
                if key in seen: continue
                seen.add(key)
                section=f.get('section_map',{}).get(i,'Full Text')
                out.append(Excerpt(filing=f['form'],section=section,category=cat,text=ctx,matched_keywords=matched,source_url=f['source_url'],accession_number=f['accession_number'],filing_date=f['filing_date'] or 'Unavailable'))
    return out
