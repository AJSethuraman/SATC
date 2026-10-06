"""Build the bank-machine checklist as one file: Markdown -> HTML with every picture embedded -> PDF.

    python3 docs/bank-machine/build.py      (from pocketbook/; needs markdown and weasyprint)

Writes docs/BANK-MACHINE-CHECKLIST.html and .pdf beside the Markdown. The pictures are the analyst's walk's
(docs/walkthrough/2026-09-27) and Look's edge lines as LibreOffice draws them (this folder).
"""
import base64
import re
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parents[1]
SRC = DOCS / "BANK-MACHINE-CHECKLIST.md"
HTML = SRC.with_suffix(".html")
PDF = SRC.with_suffix(".pdf")


def box(x, y, w, h, fill, stroke, title, lines):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>',
           f'<text x="{x + w / 2}" y="{y + 22}" text-anchor="middle" font-weight="bold">{title}</text>']
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + w / 2}" y="{y + 42 + 17 * i}" text-anchor="middle">{ln}</text>')
    return "\n".join(out)


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#555" stroke-width="2" marker-end="url(#a)"/>'


HOME, BANK, REAL = ("#eef1f5", "#667"), ("#fce4c4", "#a86"), ("#e6f2e6", "#686")
ROUTE = f"""<figure class="route"><svg viewBox="0 0 1000 300" xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans, sans-serif">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
<g font-size="12">
{box(10, 20, 170, 100, *HOME, "1 · Before you go", ["your own computer:", "make the kit,", "check the Python"])}
{box(215, 20, 170, 100, *BANK, "2 · Install", ["unzip, open the window,", "Install now, or the", "add-ons folder"])}
{box(420, 20, 170, 100, *BANK, "3 · Dry run", ["the practice book:", "compare every number", "with the table"])}
{box(625, 20, 170, 100, *BANK, "4 · Excel", ["the live parts:", "dropdowns, verdicts,", "colours, Look's lines"])}
{box(830, 20, 160, 100, *BANK, "5 · Speed", ["the bigger book,", "Task Manager:", "one Python per core"])}
{arrow(180, 70, 213, 70)}{arrow(385, 70, 418, 70)}{arrow(590, 70, 623, 70)}{arrow(795, 70, 828, 70)}
{box(420, 170, 250, 90, *REAL, "6 · A real extract", ["the columns it needs; Look and", "Columns first; nothing leaves"])}
{box(720, 170, 270, 90, *HOME, "7 · Send back", ["from the practice book only:", "the ticks, screenshots, versions"])}
{arrow(910, 120, 670, 200)}{arrow(670, 215, 718, 215)}
<text x="10" y="200" font-size="11" fill="#666">Grey: your own computer, or what comes back to it.</text>
<text x="10" y="218" font-size="11" fill="#666">Peach: at the bank, on the practice book (made up; safe to send).</text>
<text x="10" y="236" font-size="11" fill="#666">Green: at the bank, on real data. It stays there.</text>
</g></svg><figcaption>The route. Parts 2 to 5 use only the made-up practice book.</figcaption></figure>"""

CSS = """@page { size: A4; margin: 15mm 13mm; @bottom-right { content: "page " counter(page) " of " counter(pages); font-size: 9pt; color: #777; } }
:root { color-scheme: light; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1d; background: #fff; max-width: 900px; margin: 0 auto; padding: 0 16px; }
h1 { font-size: 19pt; margin: 0 0 6pt; } h2 { font-size: 14pt; margin: 18pt 0 6pt; border-bottom: 2px solid #c00; padding-bottom: 3pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
img { max-width: 100%; border: 1px solid #ccc; border-radius: 4px; display: block; margin: 6pt 0 8pt; break-inside: avoid; }
p img { max-height: 118mm; width: auto; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; overflow-wrap: anywhere; }
pre { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 6pt 8pt; white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid; }
pre code { font-size: 9pt; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9pt; width: 100%; } td, th { border: 1px solid #ccc; padding: 3pt 6pt; text-align: left; vertical-align: top; } th { background: #f1f1f1; }
tr { break-inside: avoid; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; border-left: 4px solid #d9a441; background: #fff8e6; }
figure.route { margin: 10pt 0 14pt; break-inside: avoid; } figure.route svg { width: 100%; height: auto; } figcaption { font-size: 9pt; color: #555; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
@media screen and (max-width: 600px) { table { display: block; overflow-x: auto; } }"""


def build() -> str:
    md = SRC.read_text(encoding="utf-8")
    lines, out = md.split("\n"), []
    for ln in lines:              # Python-Markdown needs a blank line before a list
        item = re.match(r"^(\s*[-*] |\s*\d+\. )", ln) is not None
        if item and out and out[-1].strip() and not re.match(r"^(\s*[-*] |\s*\d+\. )", out[-1]):
            out.append("")
        out.append(ln)
    body = markdown.markdown("\n".join(out), extensions=["tables", "fenced_code"])
    body = body.replace("<p><!-- ROUTE --></p>", ROUTE).replace("<!-- ROUTE -->", ROUTE)

    def embed(m):
        data = base64.b64encode((DOCS / m.group(2)).read_bytes()).decode()
        return f'{m.group(1)}data:image/png;base64,{data}"'

    body = re.sub(r'(<img[^>]*src=")([^"]+\.png)"', embed, body)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>PocketBook bank checklist</title>'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


if __name__ == "__main__":
    html = build()
    HTML.write_text(html, encoding="utf-8")
    from weasyprint import HTML as W

    W(string=html).write_pdf(PDF)
    print(HTML, PDF, len(html) // 1024, "KB html")
