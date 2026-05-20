import re
from bs4 import BeautifulSoup

def clean_filing_text(raw: str) -> tuple[str, list[str]]:
    raw = re.sub(r"<script.*?>.*?</script>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<style.*?>.*?</style>", " ", raw, flags=re.I|re.S)
    raw = re.sub(r"<noscript.*?>.*?</noscript>", " ", raw, flags=re.I|re.S)
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    text = soup.get_text(' ', strip=False)
    text = re.sub(r'\btable of contents\b.{0,800}?item\s+1a', ' item 1a', text, flags=re.I | re.S)
    text = re.sub(r'\s+', ' ', text).strip()
    paragraphs = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text) if len(p.strip()) > 35]
    return text, paragraphs
