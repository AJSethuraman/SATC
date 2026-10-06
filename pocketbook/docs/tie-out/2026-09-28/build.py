"""Render the tie-out: the Markdown source to one self-contained HTML page, every picture embedded, then to a PDF
through canon's checker (check_tie_out.render), which refuses unless the roster adds to the headline, the three
named sections are there and a source picture carries red ink.

    python3 build.py                      # canon's check_tie_out.py found in the installed plugin, or CANON=<dir>

Needs the `markdown` package and Chrome or Chromium (CHROME=<path> if it is not where canon looks).
"""
import base64
import glob
import os
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
NAME = "TIE-OUT-pocketbook-top-pocket-2026-09-28"


def canon_dir() -> str:
    if os.environ.get("CANON"):
        return os.environ["CANON"]
    found = sorted(glob.glob(os.path.expanduser("~/.claude/plugins/cache/*/canon/*/check_tie_out.py")))
    if not found:
        raise SystemExit("canon's check_tie_out.py not found; set CANON to the folder that holds it")
    return str(Path(found[-1]).parent)


def chrome() -> str | None:
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return found[-1] if found else None


def embed(html: str) -> str:
    def sub(m):
        src = m.group(1)
        data = base64.b64encode((HERE / src).read_bytes()).decode()
        return f'src="data:image/png;base64,{data}"'
    return re.sub(r'src="([^"]+\.png)"', sub, html)


CSS = """
@page { size: Letter; margin: 15mm 13mm; }
:root { --ink:#16181b; --soft:#525a64; --faint:#8a919b; --rule:#d8d3ca; --hair:#ebe7e0; --paper:#fff;
        --ox:#7a2230; --good:#25644a; --goodwash:#eef4f1; --bad:#8c2d1a; --badwash:#fbefe9;
        --amber:#7a5a12; --amberwash:#fbf5e6; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
       font:400 10.2pt/1.5 "IBM Plex Sans","DejaVu Sans","Segoe UI",system-ui,sans-serif; }
.sheet { max-width:190mm; margin:0 auto; }
.kicker { font:500 8pt/1 "IBM Plex Mono","DejaVu Sans Mono",monospace; letter-spacing:.16em;
          text-transform:uppercase; color:var(--ox); margin-bottom:6px; }
h1 { font:600 21pt/1.15 "Newsreader","DejaVu Serif",Georgia,serif; margin:0 0 6px; }
.lead { color:var(--soft); font-size:10.5pt; margin:0 0 6px; }
.meta { font:400 8pt/1.5 "IBM Plex Mono","DejaVu Sans Mono",monospace; color:var(--faint);
        border-bottom:2px solid var(--ink); padding-bottom:10px; margin-bottom:12px; }
.headline-box { background:var(--goodwash); border:1px solid #b9d3c6; border-radius:3px; padding:10px 13px;
                margin:8px 0 6px; }
.headline-box .big { font-weight:700; font-size:12pt; }
h2 { font:600 9.5pt/1 "IBM Plex Mono","DejaVu Sans Mono",monospace; letter-spacing:.12em; text-transform:uppercase;
     color:var(--soft); margin:24px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--rule);
     page-break-after:avoid; }
h3 { font:600 12pt/1.3 "Newsreader","DejaVu Serif",Georgia,serif; margin:16px 0 6px; page-break-after:avoid; }
p, li { margin:0 0 7px; }
code { font-family:"IBM Plex Mono","DejaVu Sans Mono",monospace; font-size:.86em; background:var(--hair);
       padding:1px 4px; border-radius:2px; }
pre { background:#f7f5f1; border:1px solid var(--rule); border-radius:3px; padding:8px 10px;
      font:400 7.6pt/1.45 "IBM Plex Mono","DejaVu Sans Mono",monospace; white-space:pre-wrap; word-break:break-word;
      page-break-inside:avoid; }
pre code { background:none; padding:0; font-size:1em; }
figure { margin:10px 0 14px; page-break-inside:avoid; }
figure img { max-width:100%; display:block; margin:0 auto; border:1px solid var(--rule); }
figure.diagram svg { width:100%; height:auto; display:block; }
figcaption { font-size:8.5pt; color:var(--soft); margin-top:5px; line-height:1.45; }
table { width:100%; border-collapse:collapse; margin:8px 0 12px; font-size:8.8pt; page-break-inside:avoid; }
th { text-align:left; font:600 7.5pt/1.2 "IBM Plex Mono","DejaVu Sans Mono",monospace; letter-spacing:.06em;
     text-transform:uppercase; color:var(--faint); padding:0 8px 5px 0; border-bottom:1px solid var(--rule); }
td { padding:4px 8px 4px 0; border-bottom:1px solid var(--hair); vertical-align:top; }
td[style*="right"], th[style*="right"], td.r, th.r { text-align:right; font-variant-numeric:tabular-nums; }
.v { font:700 7.5pt/1 "IBM Plex Mono","DejaVu Sans Mono",monospace; letter-spacing:.08em; padding:2px 5px;
     border-radius:2px; white-space:nowrap; }
.v.tied { color:var(--good); background:var(--goodwash); border:1px solid #b9d3c6; }
.v.differs { color:var(--bad); background:var(--badwash); border:1px solid #e2b6a5; }
.v.couldnot { color:var(--amber); background:var(--amberwash); border:1px solid #e3d3a8; }
"""


def main():
    sys.path.insert(0, canon_dir())
    import check_tie_out

    src = (HERE / f"{NAME}.md").read_text(encoding="utf-8")
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "md_in_html"])
    html = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>PocketBook top pocket tie-out</title><style>{CSS}</style></head>"
            f'<body><div class="sheet">{embed(body)}</div></body></html>\n')
    check_tie_out.render(html, HERE / f"{NAME}.pdf", what="the PocketBook top-pocket tie-out",
                         chrome=chrome())


if __name__ == "__main__":
    main()
