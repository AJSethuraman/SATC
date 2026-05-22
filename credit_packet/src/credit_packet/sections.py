import re

TARGETS = {
    '10-K': [
        ('Risk Factors', r'item\s*1a\.?\s*risk\s*factors'),
        ('Legal Proceedings', r'item\s*3\.?\s*legal\s*proceedings'),
        ('MD&A', r"item\s*7\.?\s*management['’]?s\s*discussion"),
        ('Controls and Procedures', r'item\s*9a\.?\s*controls'),
    ],
    '10-Q': [
        ('Risk Factors', r'part\s*ii\s*item\s*1a\.?\s*risk\s*factors'),
        ('Legal Proceedings', r'part\s*ii\s*item\s*1\.?\s*legal\s*proceedings'),
        ('MD&A', r"item\s*2\.?\s*management['’]?s\s*discussion"),
        ('Controls and Procedures', r'item\s*4\.?\s*controls'),
    ],
}

def extract_sections(text: str, form: str):
    candidates = TARGETS.get(form, [])
    lowered = text.lower()
    hits = []
    for name, pat in candidates:
        for m in re.finditer(pat, lowered, re.I):
            # avoid ToC-like early hits
            if m.start() < 400 and 'table of contents' in lowered[:500]:
                continue
            hits.append((name, m.start()))
            break
    hits.sort(key=lambda x: x[1])
    out = []
    for i, (name, start) in enumerate(hits):
        end = hits[i + 1][1] if i + 1 < len(hits) else len(text)
        out.append({'section': name, 'text': text[start:end], 'start': start, 'end': end, 'confidence': 'high' if end - start > 250 else 'medium'})
    if not out:
        out.append({'section': 'Full Text', 'text': text, 'start': 0, 'end': len(text), 'confidence': 'low'})
    return out
