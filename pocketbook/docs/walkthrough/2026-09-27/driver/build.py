"""Build the one-file procedure: Markdown -> HTML with every picture embedded -> PDF (the walk of 27 Sep 2026).
    python3 build.py [COPY_DIR]    (needs markdown and weasyprint; COPY_DIR gets a copy of the HTML)"""
import base64
import re
import shutil
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "PROCEDURE-pocketbook-analyst.md"
HTML = HERE / "PROCEDURE-pocketbook-analyst.html"
PDF = HERE / "PROCEDURE-pocketbook-analyst.pdf"


def box(x, y, w, h, fill, stroke, title, lines):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>',
           f'<text x="{x + w / 2}" y="{y + 22}" text-anchor="middle" font-weight="bold">{title}</text>']
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + w / 2}" y="{y + 42 + 18 * i}" text-anchor="middle">{ln}</text>')
    return "\n".join(out)


def arrow(x1, y1, x2, y2, dash=False):
    d = ' stroke-dasharray="5,4"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#555" stroke-width="2"{d} marker-end="url(#a)"/>'


WIN, BOOK, READ = ("#eef1f5", "#667"), ("#fce4c4", "#a86"), ("#e6f2e6", "#686")
ROUTE = f"""<figure class="route"><svg viewBox="0 0 1000 470" xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans, sans-serif">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
<g font-size="12.5">
<text x="10" y="18" font-size="13" font-weight="bold" fill="#333">Where the book bleeds</text>
{box(10, 28, 190, 96, *WIN, "Steps 1-7 · Window", ["Install add-ons, Browse", "Set up, tick the cuts", "Next (Run too early: 9 left)"])}
{box(250, 28, 230, 96, *BOOK, "Steps 8-11 · Workbook", ["Control: pick each answer", "Columns: Treat as, C3 = Yes", "save and close"])}
{box(530, 28, 170, 96, *WIN, "Step 12 · Window", ["Run", "two tiles, first lines"])}
{box(750, 28, 240, 96, *READ, "Steps 13-18 · Results", ["Start here, Pockets,", "Paid cost kept, Grids,", "Split, Record"])}
{arrow(200, 76, 248, 76)}{arrow(480, 76, 528, 76)}{arrow(700, 76, 748, 76)}
{box(530, 160, 460, 80, *BOOK, "Steps 19-21 · Change and see", ["worse at 2 times: the tabs follow now", "fewest loans 100: waits for a Run, then Run again"])}
{arrow(870, 124, 870, 158)}
<text x="10" y="278" font-size="13" font-weight="bold" fill="#333">Test new variables</text>
{box(10, 288, 230, 110, *WIN, "Steps 22-26 · Window", ["Choose tests, Test new variables", "Install scikit-learn", "Test it x4, Hold fixed FICO", "Next, Run (20 s)"])}
{box(290, 288, 250, 110, *READ, "Steps 27-30 · Results", ["Start here, Scouting,", "New variables, Record", "the pre-spec file is written", "beside the workbook"])}
{box(590, 288, 400, 110, *BOOK, "Step 31 · Change the test afterwards", ["edit the pre-spec file, Run again:", "the window says Changed, in red,", "and Record says when and how"])}
{arrow(240, 343, 288, 343)}{arrow(540, 343, 588, 343)}
{arrow(610, 240, 125, 286, dash=True)}
<text x="250" y="258" font-size="11" fill="#666">back to Choose tests on the left</text>
<text x="10" y="440" font-size="11" fill="#666">Grey: the PocketBook window. Peach: where you answer (Excel, or the pre-spec file). Green: where you read the results.</text>
<text x="10" y="458" font-size="11" fill="#666">Nothing is typed at a command line. Step 32 is what a Run that stops looks like.</text>
</g></svg><figcaption>The route: the window, the workbook, the window again, then the results, for each kind of run.</figcaption></figure>"""

CSS = """@page { size: A4; margin: 16mm 14mm; @bottom-right { content: "page " counter(page) " of " counter(pages); font-size: 9pt; color: #777; } }
:root { color-scheme: light; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1d; background: #fff; max-width: 900px; margin: 0 auto; padding: 0 16px; }
h1 { font-size: 19pt; margin: 0 0 6pt; } h2 { font-size: 14pt; margin: 18pt 0 6pt; border-bottom: 2px solid #c00; padding-bottom: 3pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
img { max-width: 100%; border: 1px solid #ccc; border-radius: 4px; display: block; margin: 6pt 0 8pt; break-inside: avoid; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9pt; } td, th { border: 1px solid #ccc; padding: 3pt 6pt; text-align: left; vertical-align: top; } th { background: #f1f1f1; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; border-left: 4px solid #d9a441; background: #fff8e6; }
figure.route { margin: 10pt 0 14pt; break-inside: avoid; } figure.route svg { width: 100%; height: auto; } figcaption { font-size: 9pt; color: #555; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }"""

md = SRC.read_text(encoding="utf-8")
lines, out = md.split("\n"), []
for ln in lines:              # Python-Markdown needs a blank line before a list
    is_item = re.match(r"^(\s*[-*] |\s*\d+\. )", ln) is not None
    if is_item and out and out[-1].strip() and not re.match(r"^(\s*[-*] |\s*\d+\. )", out[-1]):
        out.append("")
    out.append(ln)
body = markdown.markdown("\n".join(out), extensions=["tables"])
body = body.replace("<p><!-- ROUTE --></p>", ROUTE).replace("<!-- ROUTE -->", ROUTE)


def embed(m):
    data = base64.b64encode((HERE / m.group(2)).read_bytes()).decode()
    return f'{m.group(1)}data:image/png;base64,{data}"'


body = re.sub(r'(<img[^>]*src=")([^"]+\.png)"', embed, body)
html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
        f'content="width=device-width, initial-scale=1"><title>PocketBook analyst procedure</title>'
        f'<style>{CSS}</style></head><body>{body}</body></html>')
HTML.write_text(html, encoding="utf-8")
from weasyprint import HTML as W  # noqa: E402

W(string=html).write_pdf(PDF)
if len(sys.argv) > 1:
    Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
    shutil.copy(HTML, Path(sys.argv[1]) / HTML.name)
    shutil.copy(PDF, Path(sys.argv[1]) / PDF.name)
print(HTML, PDF, len(html) // 1024, "KB html")
