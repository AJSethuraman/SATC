"""Render ON-SITE-CHECKLIST.md as one printable file: Markdown -> HTML -> PDF.

    python docs/build_checklist.py     (from threshold-engine/; needs markdown and Chrome)

Writes docs/ON-SITE-CHECKLIST.html and .pdf beside the Markdown. The PDF goes
into the kit (tools/bank_kit.py), so render it before making the kit.
"""
import re
import subprocess
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "ON-SITE-CHECKLIST.md"
HTML, PDF = SRC.with_suffix(".html"), SRC.with_suffix(".pdf")
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

CSS = """@page { size: A4; margin: 15mm 13mm; }
:root { color-scheme: light; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1d; background: #fff;
       max-width: 900px; margin: 0 auto; padding: 0 16px; }
h1 { font-size: 19pt; margin: 0 0 6pt; text-wrap: balance; }
h2 { font-size: 14pt; margin: 18pt 0 6pt; border-bottom: 2px solid #c00; padding-bottom: 3pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
code { font-family: Consolas, monospace; font-size: 9pt; overflow-wrap: anywhere; }
pre { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 6pt 8pt; white-space: pre-wrap;
      overflow-wrap: anywhere; break-inside: avoid; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 9pt; width: 100%; font-variant-numeric: tabular-nums; }
td, th { border: 1px solid #ccc; padding: 3pt 6pt; text-align: left; vertical-align: top; } th { background: #f1f1f1; }
tr { break-inside: avoid; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
@media screen and (max-width: 600px) { table { display: block; overflow-x: auto; } }"""


def main():
    lines, out = SRC.read_text(encoding="utf-8").split("\n"), []
    for ln in lines:              # Python-Markdown needs a blank line before a list
        item = re.match(r"^(\s*[-*] |\s*\d+\. )", ln) is not None
        if item and out and out[-1].strip() and not re.match(r"^(\s*[-*] |\s*\d+\. )", out[-1]):
            out.append("")
        out.append(ln)
    body = markdown.markdown("\n".join(out), extensions=["tables", "fenced_code"])
    HTML.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    "<title>Threshold Engine On Site</title><style>%s</style></head><body>%s</body></html>"
                    % (CSS, body), encoding="utf-8")
    subprocess.run([str(CHROME), "--headless=new", "--no-pdf-header-footer", "--print-to-pdf=%s" % PDF,
                    HTML.as_uri()], check=True, capture_output=True)
    print("Wrote %s and %s" % (HTML, PDF))


if __name__ == "__main__":
    main()
