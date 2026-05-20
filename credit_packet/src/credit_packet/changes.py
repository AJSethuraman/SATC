from difflib import SequenceMatcher
from .models import FilingChange
from .excerpts import KEYWORDS

def _cat(text):
    t=text.lower()
    for c,kw in KEYWORDS.items():
        if any(k in t for k in kw): return c
    return 'general'

def compare_filings_for_changes(old_doc,new_doc,max_changes=20):
    if not old_doc or not new_doc: return []
    old_par=[p for p in old_doc.get('paragraphs',[]) if len(p)>20]
    new_par=[p for p in new_doc.get('paragraphs',[]) if len(p)>20]
    used=set(); changes=[]
    for n in new_par:
        best_i,best= -1,0.0
        for i,o in enumerate(old_par):
            if i in used: continue
            s=SequenceMatcher(None,o,n).ratio()
            if s>best: best_i,best=i,s
        if best<0.55:
            changes.append(FilingChange(section='Unknown',category=_cat(n),old_excerpt='',new_excerpt=n,change_type='added',similarity_score=best,source_old=old_doc['source_url'],source_new=new_doc['source_url']))
        elif best<0.9:
            used.add(best_i)
            changes.append(FilingChange(section='Unknown',category=_cat(n+old_par[best_i]),old_excerpt=old_par[best_i],new_excerpt=n,change_type='modified',similarity_score=best,source_old=old_doc['source_url'],source_new=new_doc['source_url']))
        else:
            used.add(best_i)
    for i,o in enumerate(old_par):
        if i not in used:
            changes.append(FilingChange(section='Unknown',category=_cat(o),old_excerpt=o,new_excerpt='',change_type='removed',similarity_score=0.0,source_old=old_doc['source_url'],source_new=new_doc['source_url']))
    changes.sort(key=lambda c:(c.category!='general',1-c.similarity_score),reverse=True)
    return changes[:max_changes]
