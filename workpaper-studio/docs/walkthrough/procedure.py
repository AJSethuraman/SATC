"""Render a procedure in the shape of the firm's own testing procedures (canon VOICE.md, "How they write a procedure"):
a header block, Purpose, Scope, what you need before you start, then lettered steps that each start with a verb, with
screenshots as sub-steps and the control to click boxed in red. Output is Markdown (the source) and one self-contained
HTML with every screenshot embedded, printed to PDF.

    python3 workpaper-studio/docs/walkthrough/procedure_credit_review.py
    python3 workpaper-studio/docs/walkthrough/procedure_master_to_datamart.py
"""
import base64
import re
import shutil
import subprocess
from html import escape as E
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _inline(s):
    s = E(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)


def _route_svg(route, who):
    w, h, n = 1000, 150, len(route)
    bw = (w - 20) / n
    parts = []
    for i, (a, b) in enumerate(route):
        x = 10 + i * bw
        parts.append(f'<rect x="{x + 4:.0f}" y="20" width="{bw - 22:.0f}" height="58" rx="2" fill="#2B3A55"/>'
                     f'<text x="{x + bw / 2 - 9:.0f}" y="54" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">{E(a)}</text>'
                     + "".join(f'<text x="{x + bw / 2 - 9:.0f}" y="{96 + 13 * k}" fill="#3D3A35" font-size="11" text-anchor="middle">{E(t)}</text>'
                               for k, t in enumerate(b.split(" · "))))
        if i < n - 1:
            parts.append(f'<path d="M{x + bw - 18:.0f} 49 l14 0 m-5 -5 l5 5 l-5 5" stroke="#8C857A" stroke-width="2" fill="none"/>')
    for lab, a, b in who:
        x1, x2 = 10 + a * bw + 4, 10 + b * bw - 18
        parts.append(f'<path d="M{x1:.0f} 130 L{x2:.0f} 130" stroke="#CF9A33" stroke-width="3"/>'
                     f'<text x="{(x1 + x2) / 2:.0f}" y="146" font-size="11" text-anchor="middle" fill="#8A5A00">{E(lab)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Route through the screens" font-family="Arial">{"".join(parts)}</svg>'


def letters(n):
    return [chr(ord("A") + i) for i in range(n)]


def roman(i):
    return ["i", "ii", "iii", "iv", "v", "vi"][i]


def markdown(doc, shots_rel):
    out = [f"# {doc['title']}", ""]
    out += ["| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in doc["header"]] + [""]
    out += ["## Purpose", "", doc["purpose"], "", "## Scope", "", doc["scope"], "", "## Before you start", "",
            "| System | Access needed |", "|---|---|"] + [f"| {a} | {b} |" for a, b in doc["before"]] + [""]
    out += ["## Route", "", " → ".join(a for a, _ in doc["route"]), "", "## Steps", ""]
    for L, s in zip(letters(len(doc["steps"])), doc["steps"]):
        out += [f"### {L}. {s['title']}", f"*{s['role']}*", ""] + [f"- {d}" for d in s["do"]] + ["", f"**Expected result.** {s['see']}", ""]
        if s.get("note"):
            out += [f"**Note:** {s['note']}", ""]
        out += [f"({roman(i)}) ![{s['title']}]({shots_rel}/{im})" for i, im in enumerate(s["images"])] + [""]
    if doc.get("practices"):
        out += ["## Best practices", ""] + [f"- {p}" for p in doc["practices"]] + [""]
    return "\n".join(out)


CSS = """body{font:14px/1.45 Arial,sans-serif;color:#262421;background:#fff;max-width:900px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 10px;color:#2B3A55}h2{font-size:16px;color:#fff;background:#38517F;padding:5px 10px;margin:24px 0 10px;break-after:avoid}
table.hdr,table.req{border-collapse:collapse;width:100%;margin:4px 0}table.hdr td,table.req td,table.req th{border:1px solid #D3CFC8;padding:5px 8px;text-align:left;vertical-align:top}
table.hdr td:first-child{width:160px;font-weight:700;color:#2B3A55;background:#EBE7E0}table.req th{background:#EBE7E0;color:#2B3A55}
.step{break-inside:avoid-page;border-top:1px solid #D3CFC8;padding:10px 0 14px}.step h3{margin:0 0 2px;font-size:15px;color:#2B3A55}
.role{color:#8A5A00;font-size:12px;font-weight:700;text-transform:uppercase;margin-bottom:6px}.step ul{margin:4px 0 6px 18px;padding:0}
.sub{font-size:12px;color:#6D6A63;margin:8px 0 2px}img{max-width:100%;border:1px solid #BDB6A9;display:block}
.note{background:#F6E3B2;padding:6px 10px;margin:8px 0}.fig{break-inside:avoid}img{max-height:900px;object-fit:contain;object-position:left top}@page{margin:14mm}"""


def html(doc, shots):
    def b64(name):
        return "data:image/png;base64," + base64.b64encode((shots / name).read_bytes()).decode()
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><title>{E(doc['title'])}</title><style>{CSS}</style></head><body>",
           f"<h1>{E(doc['title'])}</h1>",
           '<table class="hdr">' + "".join(f"<tr><td>{E(k)}</td><td>{_inline(v)}</td></tr>" for k, v in doc["header"]) + "</table>",
           f"<h2>Purpose</h2><p>{_inline(doc['purpose'])}</p><h2>Scope</h2><p>{_inline(doc['scope'])}</p>",
           '<h2>Before you start</h2><table class="req"><tr><th>System</th><th>Access needed</th></tr>'
           + "".join(f"<tr><td>{_inline(a)}</td><td>{_inline(b)}</td></tr>" for a, b in doc["before"]) + "</table>",
           f"<h2>Route</h2>{_route_svg(doc['route'], doc['who'])}", "<h2>Steps</h2>"]
    for L, s in zip(letters(len(doc["steps"])), doc["steps"]):
        pics = "".join(f'<div class="fig"><div class="sub">({roman(i)})</div><img src="{b64(im)}" alt="Step {L} ({roman(i)})"></div>' for i, im in enumerate(s["images"]))
        note = f'<div class="note"><b>Note:</b> {_inline(s["note"])}</div>' if s.get("note") else ""
        out.append(f'<div class="step"><h3>{L}. {E(s["title"])}</h3><div class="role">{E(s["role"])}</div>'
                   f'<ul>{"".join(f"<li>{_inline(d)}</li>" for d in s["do"])}</ul><p><b>Expected result.</b> {_inline(s["see"])}</p>{note}{pics}</div>')
    if doc.get("practices"):
        out.append("<h2>Best practices</h2><ul>" + "".join(f"<li>{_inline(p)}</li>" for p in doc["practices"]) + "</ul>")
    out.append("</body></html>")
    return "".join(out)


def build(doc, shots, md_path, html_path, pdf_path):
    md_path.write_text(markdown(doc, shots.relative_to(md_path.parent).as_posix()))
    html_path.write_text(html(doc, shots))
    cands = [shutil.which("chromium") or ""] + [str(p) for p in Path("/opt/pw-browsers").glob("chromium*/chrome-linux*/chrome")]
    for c in cands:
        if c and Path(c).is_file():
            subprocess.run([c, "--headless=new", "--no-sandbox", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                           check=True, capture_output=True, timeout=120)
            break
    return md_path, html_path, pdf_path
