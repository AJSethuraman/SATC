import sys, os, re, glob, json
from html.parser import HTMLParser
class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in ("script","style","ix:header"): self.skip+=1
    def handle_endtag(self,tag):
        t=tag.lower()
        if t in ("script","style","ix:header"): self.skip-=1
        elif t in ("td","th"): self.parts.append(" | ")
        elif t in ("tr","p","div","br"): self.parts.append("\n")
    def handle_data(self,d):
        if not self.skip: self.parts.append(d)
D=sys.argv[1]; subs=json.load(open(os.path.join(D,"subs.json")))
for t,s in subs.items():
    prim=s["recent"][0][4]; p=Text(); p.feed(open(os.path.join(D,t,prim),encoding="utf-8",errors="replace").read())
    txt=re.sub(r"[ \t\xa0]+"," ","".join(p.parts)); txt=re.sub(r"(\s*\|\s*)+\n","\n",txt); txt=re.sub(r"\n\s*\n+","\n",txt)
    open(os.path.join(D,t,"text.txt"),"w").write(txt)
