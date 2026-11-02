"""Build the procedure as one self-contained document from PROCEDURE-refresh.md.

    python build_procedure.py            writes PROCEDURE-refresh-2026-10-16.html (not kept in git:
                                         the PDF below is the deliverable)
    chromium --headless=new --no-pdf-header-footer \\
        --print-to-pdf=PROCEDURE-refresh-2026-10-16.pdf file:///<this folder>/PROCEDURE-refresh-2026-10-16.html

Every screenshot is embedded, so the file works without this folder beside it.
It opens with a picture of the route. Standard library only; it reads only the
Markdown that this folder's procedure uses (headings, paragraphs, lists,
indented commands, pictures, bold, italics, code).
"""
import base64
import html
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "PROCEDURE-refresh.md"
OUT = HERE / "PROCEDURE-refresh-2026-10-16.html"

ROUTE = """
<svg viewBox="0 0 980 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="The route">
 <style>
  .box{fill:#F4F1EC;stroke:#B9B4AC;stroke-width:1}
  .t{font:600 13px Arial;fill:#0A0908}
  .s{font:11px Calibri,Arial;fill:#57534B}
  .a{stroke:#57534B;stroke-width:1.5;fill:none;marker-end:url(#h)}
  .r{fill:#CC0000}
 </style>
 <defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="#57534B"/></marker></defs>
 <text x="10" y="18" class="t">The terminal</text>
 <rect class="r" x="10" y="24" width="960" height="2"/>
 <g>
  <rect class="box" x="10" y="40" width="150" height="62"/><text x="20" y="62" class="t">1 Install</text>
  <text x="20" y="80" class="s">pip install .</text>
  <rect class="box" x="200" y="40" width="150" height="62"/><text x="210" y="62" class="t">2 List</text>
  <text x="210" y="80" class="s">85 series, what each is</text>
  <rect class="box" x="390" y="40" width="170" height="62"/><text x="400" y="62" class="t">3 Pull</text>
  <text x="400" y="80" class="s">a dated folder, kept</text><text x="400" y="94" class="s">about a minute, no key</text>
  <rect class="box" x="600" y="40" width="170" height="62"/><text x="610" y="62" class="t">4 Rate</text>
  <text x="610" y="80" class="s">with the firm's settings</text><text x="610" y="94" class="s">refuses if one is missing</text>
  <rect class="box" x="810" y="40" width="160" height="62"/><text x="820" y="62" class="t">5 Workbook</text>
  <text x="820" y="80" class="s">--workbook FILE.xlsx</text>
  <path class="a" d="M160,71 H198"/><path class="a" d="M350,71 H388"/><path class="a" d="M560,71 H598"/>
  <path class="a" d="M770,71 H808"/>
 </g>
 <text x="10" y="148" class="t">The workbook</text>
 <rect class="r" x="10" y="154" width="960" height="2"/>
 <path class="a" d="M890,102 V128 H85 V168"/>
 <g>
  <rect class="box" x="10" y="170" width="150" height="62"/><text x="20" y="192" class="t">6 Ratings</text>
  <text x="20" y="210" class="s">counts, topics, the 4s</text>
  <rect class="box" x="200" y="170" width="190" height="62"/><text x="210" y="192" class="t">7-10 A series' tab</text>
  <text x="210" y="210" class="s">where each rating starts,</text><text x="210" y="224" class="s">history over the bands</text>
  <rect class="box" x="430" y="170" width="120" height="62"/><text x="440" y="192" class="t">11 States</text>
  <text x="440" y="210" class="s">worst first</text>
  <rect class="box" x="590" y="170" width="190" height="62"/><text x="600" y="192" class="t">12-14 Glossary,</text>
  <text x="600" y="208" class="t">Run, Sources</text><text x="600" y="224" class="s">words, settings, fingerprints</text>
  <path class="a" d="M160,201 H198"/><path class="a" d="M390,201 H428"/><path class="a" d="M550,201 H588"/>
  <text x="160" y="250" class="s">click a series' name; "Back to Ratings" returns</text>
 </g>
 <g>
  <rect class="box" x="810" y="170" width="160" height="62"/><text x="820" y="192" class="t">15-16 What if</text>
  <text x="820" y="210" class="s">a copy of the settings;</text><text x="820" y="224" class="s">what an empty one does</text>
  <path class="a" d="M780,201 H808"/>
 </g>
 <text x="10" y="285" class="s">Each step below has its screenshot and what a correct screen looks like.</text>
</svg>
"""

CSS = """
@page { size: A4 landscape; margin: 12mm 14mm; }
body { font: 11pt/1.45 Calibri, Carlito, Arial, sans-serif; color: #16130F; max-width: 1060px; margin: 0 auto; }
h1 { font: bold 22pt Arial, sans-serif; margin: 0 0 4px; }
h2 { font: bold 14pt Arial, sans-serif; border-bottom: 2px solid #0A0908; padding-bottom: 3px; margin-top: 26px;
     page-break-after: avoid; }
h3 { font: bold 12pt Arial, sans-serif; margin: 20px 0 4px; page-break-after: avoid; }
p, li { margin: 4px 0; }
pre { background: #18181B; color: #EEE; padding: 8px 10px; font: 9.5pt DejaVu Sans Mono, Consolas, monospace;
      white-space: pre-wrap; word-break: break-all; border-radius: 3px; page-break-inside: avoid; }
code { font: 9.5pt DejaVu Sans Mono, Consolas, monospace; background: #F4F1EC; padding: 0 3px; }
figure { margin: 8px 0 14px; page-break-inside: avoid; }
figure img { max-width: 100%; border: 1px solid #E4DFD5; }
figcaption { font-size: 9.5pt; color: #57534B; margin-top: 2px; }
.route { border: 1px solid #E4DFD5; padding: 8px; margin: 12px 0 6px; page-break-inside: avoid; }
.lede { color: #57534B; }
"""


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def picture(path, caption):
    data = base64.b64encode((HERE / path).read_bytes()).decode()
    return ('<figure><img src="data:image/png;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>'
            % (data, html.escape(caption), inline(caption)))


def build():
    lines = SOURCE.read_text("utf-8").split("\n")
    out, para, items, code, first_h2 = [], [], [], [], True

    def flush():
        nonlocal para, items, code
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
        if items:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(i) for i in items))
        if code:
            out.append("<pre>%s</pre>" % html.escape("\n".join(code)))
        para, items, code = [], [], []

    for line in lines:
        m = re.match(r"!\[(.*)\]\((.*)\)", line.strip())
        if line.startswith("    ") and not items:
            if para:
                flush()
            code.append(line[4:])
        elif code and not line.strip():
            flush()
        elif m:
            flush()
            out.append(picture(m.group(2), m.group(1)))
        elif line.startswith("# "):
            flush()
            out.append("<h1>%s</h1>" % inline(line[2:]))
        elif line.startswith("## "):
            flush()
            if first_h2:                     # the route, before step 1
                out.append('<div class="route">%s</div>' % ROUTE)
                first_h2 = False
            out.append("<h2>%s</h2>" % inline(line[3:]))
        elif line.startswith("### "):
            flush()
            out.append("<h3>%s</h3>" % inline(line[4:]))
        elif line.startswith("- "):
            if para:
                out.append("<p>%s</p>" % inline(" ".join(para)))
                para = []
            items.append(line[2:])
        elif line.startswith("  ") and items:
            items[-1] += " " + line.strip()
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Refresh the economic conditions "
            "workbook</title><style>%s</style></head><body>%s</body></html>" % (CSS, "\n".join(out)))
    OUT.write_text(page, "utf-8")
    return OUT


if __name__ == "__main__":
    print(build())
