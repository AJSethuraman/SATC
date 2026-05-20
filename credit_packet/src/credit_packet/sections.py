import re
TARGETS={
 '10-K':[('Risk Factors',r'item\s*1a\.?\s*risk\s*factors'),('Legal Proceedings',r'item\s*3\.?\s*legal\s*proceedings'),('MD&A',r"item\s*7\.?\s*management['’]s\s*discussion"),('Market Risk',r'item\s*7a\.?\s*quantitative'),('Financial Statements',r'item\s*8\.?\s*financial\s*statements'),('Controls and Procedures',r'item\s*9a\.?\s*controls')],
 '10-Q':[('Financial Statements',r'item\s*1\.?\s*financial\s*statements'),('MD&A',r"item\s*2\.?\s*management['’]s\s*discussion"),('Market Risk',r'item\s*3\.?\s*quantitative'),('Controls and Procedures',r'item\s*4\.?\s*controls'),('Legal Proceedings',r'part\s*ii\s*item\s*1\.?\s*legal'),('Risk Factors',r'part\s*ii\s*item\s*1a\.?\s*risk')]
}

def extract_sections(text:str,form:str):
    targets=TARGETS.get(form,[])
    lower=text.lower()
    matches=[]
    for name,pat in targets:
        m=list(re.finditer(pat,lower,re.I))
        if not m:
            continue
        pos=max(m,key=lambda x:x.start())
        matches.append((name,pos.start()))
    matches=sorted(matches,key=lambda x:x[1])
    out=[]
    for i,(name,start) in enumerate(matches):
        end=matches[i+1][1] if i+1<len(matches) else min(len(text),start+120000)
        out.append({'section':name,'text':text[start:end],'start':start,'end':end,'confidence':'high' if end-start>300 else 'medium'})
    if not out:
        out=[{'section':'Full Text','text':text,'start':0,'end':len(text),'confidence':'low'}]
    return out
