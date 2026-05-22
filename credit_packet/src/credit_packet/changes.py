from difflib import SequenceMatcher
from .models import FilingChange
from .excerpts import KEYWORDS

def _cat(text: str) -> str:
    t = text.lower()
    for c, kws in KEYWORDS.items():
        if any(k in t for k in kws):
            return c
    return 'general'

def _paras(section_text: str) -> list[str]:
    return [p.strip() for p in section_text.split('. ') if len(p.strip()) > 30]

def compare_filings_for_changes(old_doc, new_doc, max_changes=20):
    if not old_doc or not new_doc:
        return []
    old_sections = {s['section']: s['text'] for s in old_doc.get('sections', [])}
    new_sections = {s['section']: s['text'] for s in new_doc.get('sections', [])}
    names = sorted(set(old_sections) & set(new_sections))
    out = []
    for section in names:
        old_par = _paras(old_sections[section])
        new_par = _paras(new_sections[section])
        used = set()
        for np in new_par:
            best_i, best = -1, 0.0
            for i, op in enumerate(old_par):
                if i in used:
                    continue
                s = SequenceMatcher(None, op, np).ratio()
                if s > best:
                    best_i, best = i, s
            if best < 0.55:
                out.append(FilingChange(section=section, category=_cat(np), old_excerpt='', new_excerpt=np, change_type='added', similarity_score=best, source_old=old_doc['source_url'], source_new=new_doc['source_url']))
            elif best < 0.9:
                used.add(best_i)
                out.append(FilingChange(section=section, category=_cat(np + old_par[best_i]), old_excerpt=old_par[best_i], new_excerpt=np, change_type='modified', similarity_score=best, source_old=old_doc['source_url'], source_new=new_doc['source_url']))
            else:
                used.add(best_i)
        for i, op in enumerate(old_par):
            if i not in used:
                out.append(FilingChange(section=section, category=_cat(op), old_excerpt=op, new_excerpt='', change_type='removed', similarity_score=0.0, source_old=old_doc['source_url'], source_new=new_doc['source_url']))
    out.sort(key=lambda c: (c.category != 'general', 1 - c.similarity_score), reverse=True)
    return out[:max_changes]
