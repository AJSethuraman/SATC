import re

def clean_filing_text(raw:str)->tuple[str,list[str]]:
    text=raw
    text=re.sub(r'<script.*?>.*?</script>',' ',text,flags=re.I|re.S)
    text=re.sub(r'<style.*?>.*?</style>',' ',text,flags=re.I|re.S)
    text=re.sub(r'<[^>]+>',' ',text)
    text=re.sub(r'\btable of contents\b.*?(?=item\s+1a|item\s+1\b)',' ',text,flags=re.I|re.S)
    text=re.sub(r'\s+',' ',text).strip()
    paras=[p.strip() for p in re.split(r'(?<=[\.!?])\s+',text) if len(p.strip())>40]
    return text,paras
