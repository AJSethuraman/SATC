import re
from html.parser import HTMLParser

try:
    from bs4 import BeautifulSoup as _BS4
except Exception:
    class _MiniParser(HTMLParser):
        def __init__(self):
            super().__init__(); self.text=[]; self.skip=False
        def handle_starttag(self, tag, attrs):
            if tag in {'script','style','noscript'}: self.skip=True
            if tag in {'p','div','li','td','h1','h2','h3','h4','h5'}: self.text.append('\n')
        def handle_endtag(self, tag):
            if tag in {'script','style','noscript'}: self.skip=False
        def handle_data(self, data):
            if not self.skip: self.text.append(data)
    class _BS4:  # fallback shim
        def __init__(self, raw, _parser):
            p=_MiniParser(); p.feed(raw); self._text=''.join(p.text)
        def get_text(self, sep=' ', strip=False):
            t=self._text
            return t.strip() if strip else t
        def __call__(self, *args, **kwargs):
            return []


def clean_filing_text(raw: str) -> tuple[str, list[str]]:
    soup = _BS4(raw, 'html.parser')
    for tag in getattr(soup, '__call__', lambda *a, **k: [])(['script', 'style', 'noscript']):
        try:
            tag.decompose()
        except Exception:
            pass
    text = soup.get_text(' ', strip=False)
    text = re.sub(r'\btable of contents\b.{0,800}?item\s+1a', ' item 1a', text, flags=re.I | re.S)
    text = re.sub(r'\s+', ' ', text).strip()
    paragraphs = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text) if len(p.strip()) > 35]
    return text, paragraphs
