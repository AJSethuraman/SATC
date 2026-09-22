#!/usr/bin/env python3
"""One self-contained file from a procedure's Markdown and its screenshots.

    python tools/walkpdf.py docs/PROCEDURE-desk-test.md OUT.pdf [OUT.html] [WEB.html]

The Markdown is the source (headings, paragraphs, **bold**, `code`, fenced
blocks, bullet lists, images). Every image is embedded as base64, so the HTML
and the PDF work with no folder beside them. Chromium prints the PDF; the
caller opens it and looks at every page before calling it done.
"""

from __future__ import annotations

import base64
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from walkshot import CHROME

CSS = """
@page{size:A4;margin:16mm 14mm 18mm 14mm}
body{font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;color:#1B2430;font-size:11.5pt;line-height:1.45;max-width:180mm;margin:0 auto}
h1{font-size:22pt;margin:0 0 4pt;line-height:1.2}
h2{font-size:15pt;margin:22pt 0 6pt;padding-top:8pt;border-top:2px solid #1B2430;page-break-after:avoid}
h2:not(:first-of-type){page-break-before:always;margin-top:0}
h3{font-size:12.5pt;margin:16pt 0 4pt;page-break-after:avoid;color:#1F6F8B}
p{margin:4pt 0 6pt}
ul{margin:2pt 0 6pt 18pt;padding:0}
li{margin:2pt 0}
code{font-family:'IBM Plex Mono',ui-monospace,Consolas,monospace;font-size:10pt;background:#EEF1F0;padding:1px 4px;border-radius:3px}
pre{font-family:'IBM Plex Mono',ui-monospace,Consolas,monospace;font-size:9.5pt;background:#14181D;color:#E8ECEF;padding:8pt 10pt;border-radius:6px;white-space:pre-wrap;word-break:break-all;margin:4pt 0 8pt;page-break-inside:avoid}
figure{margin:6pt 0 10pt;page-break-inside:avoid}
figure img{max-width:100%;height:auto;display:block;border:1px solid #D5DBD8;border-radius:4px}
figcaption{font-size:9.5pt;color:#5B6673;margin-top:3pt}
.step{page-break-inside:avoid}
.lead{font-size:12.5pt;color:#5B6673;margin:0 0 12pt}
strong{color:#1B2430}
"""


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return text


WEB_CSS = """
:root{--ink:#1B2430;--paper:#F5F7F4;--card:#FFFFFF;--muted:#5B6673;--rule:#D5DBD8;--accent:#E4573D;--step:#1F6F8B;--code-bg:#E8ECE9;--term:#14181D;--term-ink:#E8ECEF}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#E8ECEF;--paper:#14181D;--card:#1C2228;--muted:#9AA6B2;--rule:#2A313A;--accent:#F07A62;--step:#6FB7D2;--code-bg:#242B33;--term:#0D1014;--term-ink:#E8ECEF}}
:root[data-theme="dark"]{--ink:#E8ECEF;--paper:#14181D;--card:#1C2228;--muted:#9AA6B2;--rule:#2A313A;--accent:#F07A62;--step:#6FB7D2;--code-bg:#242B33;--term:#0D1014;--term-ink:#E8ECEF}
body{background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;line-height:1.5;margin:0;padding-block:32px 64px;padding-inline:16px}
main{max-width:72ch;margin:0 auto}
h1{font-size:2rem;line-height:1.15;margin:0 0 .25rem;text-wrap:balance}
h2{font-size:1.35rem;margin:2.5rem 0 .5rem;padding-top:1rem;border-top:2px solid var(--ink);text-wrap:balance}
h3{font-size:1.1rem;margin:2rem 0 .35rem;color:var(--step);text-wrap:balance}
p{margin:.35rem 0 .6rem}
.lead{font-size:1.1rem;color:var(--muted);margin:0 0 1.25rem}
ul{margin:.25rem 0 .6rem 1.25rem;padding:0}
code{font-family:'IBM Plex Mono',ui-monospace,Consolas,monospace;font-size:.9em;background:var(--code-bg);padding:.05em .35em;border-radius:4px}
pre{font-family:'IBM Plex Mono',ui-monospace,Consolas,monospace;font-size:.85rem;background:var(--term);color:var(--term-ink);padding:.6rem .8rem;border-radius:8px;overflow-x:auto;margin:.35rem 0 .75rem}
pre code{background:none;padding:0;color:inherit}
figure{margin:.5rem 0 1rem;background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:8px}
figure img{max-width:100%;height:auto;display:block;border-radius:4px}
figcaption{font-size:.8rem;color:var(--muted);margin-top:6px;letter-spacing:.02em}
strong{color:var(--ink)}
em{font-style:italic}
"""


def convert(md_path: Path, web: bool = False) -> str:
    """The Markdown as one HTML string: a printable document by default, or
    (`web`) a page for publishing, with the title first and both themes."""
    base = md_path.parent
    if web:
        out = ["<title>Analysis Pack Desk Test</title>",
               "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap'>",
               f"<style>{WEB_CSS}</style><main>"]
    else:
        out = [f"<!doctype html><html><head><meta charset='utf-8'><title>Analysis Pack Desk Test</title><style>{CSS}</style></head><body>"]
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    para: list[str] = []
    in_list = False

    def flush():
        nonlocal para
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para = []

    def end_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush(); end_list()
            j = i + 1
            block = []
            while j < len(lines) and not lines[j].startswith("```"):
                block.append(lines[j]); j += 1
            out.append(f"<pre>{html.escape(chr(10).join(block))}</pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if m:
            flush(); end_list()
            level = len(m.group(1))
            if level == 3:
                out.append(f"<div class='step'><h3>{_inline(m.group(2))}</h3>")
                # a step's block ends at the next heading; close it there
                j = i + 1
                while j < len(lines) and not re.match(r"^#{1,3}\s", lines[j]):
                    j += 1
                lines.insert(j, "<!--/step-->")
            else:
                out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if ln.strip() == "<!--/step-->":
            flush(); end_list()
            out.append("</div>")
            i += 1
            continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", ln)
        if m:
            flush(); end_list()
            img = base / m.group(2)
            data = base64.b64encode(img.read_bytes()).decode("ascii")
            cap = f"<figcaption>{_inline(m.group(1))}</figcaption>" if m.group(1) else ""
            out.append(f"<figure><img src='data:image/png;base64,{data}'>{cap}</figure>")
            i += 1
            continue
        m = re.match(r"^\s*[-*]\s+(.*)$", ln)
        if m:
            flush()
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue
        if not ln.strip():
            flush(); end_list()
            i += 1
            continue
        if ln.startswith("> "):
            flush(); end_list()
            out.append(f"<p class='lead'>{_inline(ln[2:])}</p>")
            i += 1
            continue
        para.append(ln.strip())
        i += 1
    flush(); end_list()
    out.append("</main>" if web else "</body></html>")
    return "".join(out)


def main(argv: list[str]) -> int:
    md, pdf = Path(argv[0]), Path(argv[1])
    html_out = Path(argv[2]) if len(argv) > 2 else pdf.with_suffix(".html")
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(convert(md), encoding="utf-8")
    if len(argv) > 3:   # the page to publish, beside the printable one
        Path(argv[3]).write_text(convert(md, web=True), encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="walkpdf-"))
    r = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={tmp / 'profile'}",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{html_out.resolve()}"],
                       capture_output=True, text=True, timeout=300)
    if not pdf.exists():
        print(r.stderr[-2000:], file=sys.stderr)
        return 1
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = re.search(r"Pages:\s+(\d+)", info)
    print(f"wrote {pdf} ({pdf.stat().st_size:,} bytes, {pages.group(1) if pages else '?'} pages) and {html_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
