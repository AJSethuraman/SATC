"""Minimal local fallback shim for environments where beautifulsoup4 isn't installed."""
from html.parser import HTMLParser

class _Node:
    def decompose(self):
        return None

class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data):
        self.parts.append(data)

class BeautifulSoup:
    def __init__(self, html: str, parser: str = 'html.parser'):
        self.html = html
    def __call__(self, tags):
        return [_Node() for _ in tags]
    def get_text(self, sep=' ', strip=False):
        p=_Parser(); p.feed(self.html)
        t=sep.join(x.strip() for x in p.parts if x.strip())
        return t.strip() if strip else t
