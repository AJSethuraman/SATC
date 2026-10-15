"""The walkthrough as one file to open and forward: WALKTHROUGH.md, the result,
and the pictures Excel took, embedded. Run after compare.py:

    python docs/walkthrough-book/build_exhibit.py      (needs markdown and Chrome)

Writes WALKTHROUGH-BOOK.html and WALKTHROUGH-BOOK.pdf beside this file.
"""
import base64
import json
import re
import subprocess
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
plan = json.loads((HERE / "steps.json").read_text(encoding="utf-8"))
result = (HERE / "RESULT.md").read_text(encoding="utf-8")
headline = next(l for l in result.splitlines() if l.startswith("**"))

CSS = """@page { size: A4; margin: 14mm 12mm; }
:root { color-scheme: light; }
body { font: 10.5pt/1.45 Calibri, "Segoe UI", sans-serif; color: #16130F; max-width: 180mm; margin: 0 auto; }
h1 { font: 700 19pt Arial, sans-serif; margin: 0 0 4mm; }
h2 { font: 700 13pt Arial, sans-serif; border-bottom: 2px solid #16130F; padding-bottom: 1mm; margin-top: 7mm; }
h3 { font: 700 11pt Arial, sans-serif; margin: 5mm 0 2mm; }
code, pre { font: 8.5pt Consolas, monospace; }
pre { background: #F4F1EC; padding: 2.5mm; white-space: pre-wrap; word-break: break-all; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 2mm 0 4mm; }
th, td { border-bottom: 1px solid #D9D4CB; padding: 1.2mm 1.5mm; text-align: left; vertical-align: top; }
th { background: #16130F; color: #fff; }
.verdict { font: 700 14pt Arial, sans-serif; background: #D9EAD3; padding: 3mm; margin: 4mm 0; }
figure { margin: 3mm 0 6mm; page-break-inside: avoid; }
figure img { width: 100%; border: 1px solid #D9D4CB; }
figcaption { font-size: 9pt; color: #57534B; }
"""

body = markdown.markdown((HERE / "WALKTHROUGH.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
parts = ["<!doctype html><html><head><meta charset='utf-8'><title>Book walkthrough</title><style>%s</style></head><body>"
         % CSS, body, "<h2>5. The result</h2>",
         "<div class='verdict'>%s</div>" % headline.strip("*")]
rows = []
for s in plan["steps"]:
    m = re.search(r"## %s · .*?: (\d+) of (\d+)" % re.escape(s["id"]), result)
    rows.append("<tr><td>%s</td><td>%s</td><td>%s of %s</td></tr>" % (s["id"], s["what"], m.group(1), m.group(2)))
parts.append("<table><tr><th>Step</th><th>What you do</th><th>Reads as expected</th></tr>%s</table>" % "".join(rows))
parts.append("<h2>6. What Excel showed</h2>")
for s in plan["steps"]:
    for p in s.get("picture", []):
        f = HERE / "pictures" / p["file"]
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            parts.append("<figure><img src='data:image/png;base64,%s'><figcaption>%s · %s (%s tab, photographed by "
                         "Excel during the walk)</figcaption></figure>" % (b64, s["id"], s["what"], p["sheet"]))
parts.append("</body></html>")
html = HERE / "WALKTHROUGH-BOOK.html"
html.write_text("\n".join(parts), encoding="utf-8")
pdf = HERE / "WALKTHROUGH-BOOK.pdf"
subprocess.run([str(CHROME), "--headless=new", "--no-pdf-header-footer", "--print-to-pdf=%s" % pdf, html.as_uri()],
               check=True, capture_output=True)
print("Wrote %s and %s" % (html.name, pdf.name))
