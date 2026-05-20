from difflib import SequenceMatcher
from .models import FilingChange

def detect_changes(excerpts):
    out=[]
    by_form={}
    for e in excerpts: by_form.setdefault(e.filing,[]).append(e)
    for form in ('10-K','10-Q'):
        arr=by_form.get(form,[])
        if len(arr)>=2:
            a,b=arr[-2],arr[-1]
            sim=SequenceMatcher(None,a.text,b.text).ratio()
            if sim<0.95:
                out.append(FilingChange(section=a.section, category=a.category, old_excerpt=a.text, new_excerpt=b.text, change_type='modified', similarity_score=sim, source_old=a.source_url, source_new=b.source_url))
    return out
