"""Build the one-file procedure: Markdown -> HTML with every picture embedded -> PDF.
    python3 build.py   (from anywhere)"""
import base64, re
from pathlib import Path
import markdown

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "PROCEDURE-origination-workbook.md"
HTML = HERE / "PROCEDURE-origination-workbook.html"
PDF = HERE / "PROCEDURE-origination-workbook.pdf"

ROUTE = """<figure class="route"><svg viewBox="0 0 1000 350" xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans, sans-serif">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
<g font-size="13">
<rect x="10" y="20" width="200" height="90" rx="8" fill="#eef1f5" stroke="#667"/>
<text x="110" y="45" text-anchor="middle" font-weight="bold">Steps 1-3 · Window</text><text x="110" y="66" text-anchor="middle">Browse... the extract</text><text x="110" y="86" text-anchor="middle">1. Set up from this extract</text>
<rect x="270" y="20" width="440" height="90" rx="8" fill="#fce4c4" stroke="#a86"/>
<text x="490" y="45" text-anchor="middle" font-weight="bold">Steps 4-10 · Workbook in Excel</text>
<text x="490" y="66" text-anchor="middle">Start here → Control (9 calls; 3 offer a suggestion)</text><text x="490" y="86" text-anchor="middle">→ Columns (C3 = Yes) → Odd values (real / missing)</text>
<rect x="770" y="20" width="220" height="90" rx="8" fill="#eef1f5" stroke="#667"/>
<text x="880" y="45" text-anchor="middle" font-weight="bold">Step 11 · Window</text><text x="880" y="66" text-anchor="middle">save, close Excel,</text><text x="880" y="86" text-anchor="middle">2. Run the cube</text>
<line x1="210" y1="65" x2="268" y2="65" stroke="#555" stroke-width="2" marker-end="url(#a)"/>
<line x1="710" y1="65" x2="768" y2="65" stroke="#555" stroke-width="2" marker-end="url(#a)"/>
<rect x="520" y="190" width="470" height="110" rx="8" fill="#e6f2e6" stroke="#686"/>
<text x="755" y="215" text-anchor="middle" font-weight="bold">Steps 12-17 · Results in the same workbook</text>
<text x="755" y="236" text-anchor="middle">Where it bleeds → Losses vs revenue (9 boxes) → Grids</text><text x="755" y="256" text-anchor="middle">→ Materiality → Check (suggested numbers) → Log</text><text x="755" y="280" text-anchor="middle" font-size="11">planted pocket: FICO under 654 / Broker, first; "Losing more, earning the same"</text>
<line x1="880" y1="110" x2="880" y2="188" stroke="#555" stroke-width="2" marker-end="url(#a)"/>
<rect x="10" y="190" width="440" height="110" rx="8" fill="#eef1f5" stroke="#667"/>
<text x="230" y="215" text-anchor="middle" font-weight="bold">Steps 18-24 · Change and go again</text>
<text x="230" y="236" text-anchor="middle">Split + Three-way (REV_DEBT, then ASSET_CLASS)</text><text x="230" y="256" text-anchor="middle">Show per pocket · edges or every 20 · Set up again</text><text x="230" y="276" text-anchor="middle">Forget on Learned · the next extract</text>
<line x1="518" y1="245" x2="452" y2="245" stroke="#555" stroke-width="2" marker-end="url(#a)"/>
<path d="M230,190 C230,150 150,140 110,112" fill="none" stroke="#999" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#a)"/>
<text x="120" y="160" font-size="11" fill="#666">Columns, then Run again</text>
<text x="10" y="335" font-size="11" fill="#666">Peach = where you answer (Excel). Grey = the window. Green = where you read the results. Nothing is typed at a command line.</text>
</g></svg><figcaption>The route: two buttons in the window, one workbook in Excel.</figcaption></figure>"""

CSS = """@page { size: A4; margin: 16mm 14mm; @bottom-right { content: "page " counter(page) " of " counter(pages); font-size: 9pt; color: #777; } }
:root { color-scheme: light; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1d; background: #fff; max-width: 900px; margin: 0 auto; padding: 0 16px; }
h1 { font-size: 20pt; margin: 0 0 6pt; } h2 { font-size: 14pt; margin: 18pt 0 6pt; border-bottom: 1px solid #ddd; padding-bottom: 3pt; break-after: avoid; }
img { max-width: 100%; border: 1px solid #ccc; border-radius: 4px; display: block; margin: 6pt 0 8pt; break-inside: avoid; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9pt; } td, th { border: 1px solid #ccc; padding: 3pt 6pt; text-align: left; vertical-align: top; } th { background: #f1f1f1; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; border-left: 4px solid #d9a441; background: #fff8e6; }
figure.route { margin: 10pt 0 14pt; break-inside: avoid; } figure.route svg { width: 100%; height: auto; } figcaption { font-size: 9pt; color: #555; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }"""

md = SRC.read_text(encoding="utf-8")
# Python-Markdown needs a blank line before a list; the source is written the GitHub way, without one.
lines, out = md.split("\n"), []
for ln in lines:
    is_item = re.match(r"^(\s*[-*] |\s*\d+\. )", ln) is not None
    if is_item and out and out[-1].strip() and not re.match(r"^(\s*[-*] |\s*\d+\. )", out[-1]):
        out.append("")
    out.append(ln)
md = "\n".join(out)
body = markdown.markdown(md, extensions=["tables"])
body = body.replace("<p><!-- ROUTE --></p>", ROUTE).replace("<!-- ROUTE -->", ROUTE)

def embed(m):
    p = HERE / m.group(2)
    data = base64.b64encode(p.read_bytes()).decode()
    return f'{m.group(1)}data:image/png;base64,{data}"'
body = re.sub(r'(<img[^>]*src=")([^"]+\.png)"', embed, body)
html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Origination workbook procedure</title><style>{CSS}</style></head><body>{body}</body></html>'
HTML.write_text(html, encoding="utf-8")
from weasyprint import HTML as W
W(string=html).write_pdf(PDF)
print(HTML, PDF, len(html) // 1024, "KB html")
