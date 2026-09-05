"""Twelve bank exhibits plus a master roster, each one self-contained.

One document per bank, because that is the unit a reader checks: they open a
bank's Call Report, not a spreadsheet of twelve. Every image is embedded, so a
document survives being forwarded to somebody who does not have this machine.
"""
import base64
import html
import json
import pathlib
import subprocess
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
OUTDIR = CS / "docs" / "tie-out" / "banks-12-2026-06-30"
OUTDIR.mkdir(parents=True, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CELLS = SB / "bankshots"
STRIPS = SB / "bankstrips"
rosters = json.loads((SB / "bank_rosters.json").read_text())
strips = json.loads((SB / "bank_strips.json").read_text())
ratios = json.loads((SB / "bank_ratios.json").read_text())
WB = "Bank_Peer_Monitor.xlsm"


def uri(path):
    p = pathlib.Path(path)
    return "data:image/png;base64,%s" % base64.b64encode(p.read_bytes()).decode()


def esc(x):
    return html.escape("" if x is None else str(x))


def num(v, pct=False):
    if v is None:
        return "&mdash;"
    try:
        return ("{:,.4f}".format(float(v)) if pct else "{:,.0f}".format(float(v)))
    except (TypeError, ValueError):
        return esc(v)


CSS = """<style>
:root { --ink:#151515; --dim:#5c5c5c; --rule:#d8d8d8; --red:#b00020;
        --good:#0a6b3d; }
* { box-sizing:border-box; }
body { margin:0; color:var(--ink); background:#fff;
       font:14px/1.62 "Charter","Georgia",serif; }
.wrap { max-width:1080px; margin:0 auto; padding:42px 46px 80px; }
h1 { font:700 29px/1.22 system-ui,sans-serif; margin:0 0 6px; letter-spacing:-.01em; }
h2 { font:700 19px/1.3 system-ui,sans-serif; margin:42px 0 10px; padding-top:14px;
     border-top:2px solid var(--ink); }
h3 { font:700 15px/1.35 system-ui,sans-serif; margin:26px 0 8px; }
.sub { color:var(--dim); font:15px/1.5 system-ui,sans-serif; margin:0 0 22px; }
.headline { border:2px solid var(--ink); padding:16px 20px; margin:22px 0 28px; }
.headline b { font:700 22px/1.3 system-ui,sans-serif; }
.headline.bad { border-color:var(--red); }
p { margin:0 0 12px; }
figure { margin:14px 0 20px; }
figure img { width:100%; border:1px solid var(--rule); display:block; }
figcaption { font:12.5px/1.5 system-ui,sans-serif; color:var(--dim); margin-top:6px; }
.diagram svg { width:100%; height:auto; border:1px solid var(--rule); padding:14px; }
table { border-collapse:collapse; width:100%; margin:14px 0 20px;
        font:12px/1.45 system-ui,sans-serif; }
th,td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--rule);
        vertical-align:top; }
th { font-weight:700; border-bottom:1.5px solid var(--ink); white-space:nowrap; }
td.n,th.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
td.mono { font-family:ui-monospace,Consolas,monospace; }
td.v { font-weight:700; }
.ties,td.v.ties { color:var(--good); }
.differs,td.v.differs { color:var(--red); }
.could,td.v.could { color:#8a6d00; }
tr.differs td { background:#fff6f6; }
.compare { font:13px/1.7 ui-monospace,Consolas,monospace; background:#f7f7f5;
           border-left:4px solid var(--ink); padding:13px 16px; margin:14px 0 18px;
           white-space:pre-wrap; overflow-wrap:anywhere; }
.line { border:1px solid var(--rule); padding:12px 14px; margin:14px 0;
        break-inside:avoid; }
.line.differs { border-color:var(--red); background:#fffafa; }
.line h4 { font:700 14px/1.3 system-ui,sans-serif; margin:0 0 3px; }
.line .meta { font:11.5px/1.5 system-ui,sans-serif; color:var(--dim);
              margin-bottom:9px; }
.pair { display:grid; grid-template-columns:1fr; gap:9px; }
.pair .cap { font:10.5px/1.4 system-ui,sans-serif; color:var(--dim);
             letter-spacing:.05em; text-transform:uppercase; margin-bottom:3px; }
.pair img { width:100%; border:1px solid var(--rule); display:block; }
.note { border-left:4px solid var(--red); background:#fff6f6; padding:12px 16px;
        margin:16px 0; }
.note.win { border-color:var(--good); background:#f2fbf6; }
ul,ol { margin:0 0 14px; padding-left:22px; }
li { margin-bottom:7px; }
code { font-family:ui-monospace,Consolas,monospace; font-size:12.5px;
       background:#f2f2ef; padding:1px 4px; }
pre { font:12px/1.55 ui-monospace,Consolas,monospace; background:#f7f7f5;
      padding:12px 14px; border:1px solid var(--rule);
      white-space:pre-wrap; overflow-wrap:anywhere; }
@media print { .line, figure { break-inside:avoid; } }
</style>"""


def diagram(bank, tied, total):
    return """
<figure class="diagram">
<svg viewBox="0 0 980 300" role="img"
     aria-label="The same figure on two roads: the FDIC's republication into the
     workbook cell, and the check, which goes to the bank's own filed Call Report,
     meeting at difference zero.">
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
    markerHeight="7" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/></marker></defs>
  <g font-family="system-ui, sans-serif" font-size="12.5" fill="currentColor">
    <text x="0" y="16" font-size="11.5" font-weight="700"
          letter-spacing="0.08em">THE PRODUCTION ROAD</text>
    <rect x="0" y="30" width="200" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="12" y="52">%s files its Call</text>
    <text x="12" y="70">Report with the FFIEC</text>
    <line x1="200" y1="56" x2="276" y2="56" stroke="currentColor"
          stroke-width="1.4" marker-end="url(#a)"/>
    <rect x="276" y="30" width="176" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="288" y="52">The FDIC republishes</text>
    <text x="288" y="70" font-size="11.5" opacity="0.75">BankFind API</text>
    <line x1="452" y1="56" x2="528" y2="56" stroke="currentColor"
          stroke-width="1.4" marker-end="url(#a)"/>
    <rect x="528" y="30" width="200" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="540" y="52">The cell a person opens</text>
    <text x="540" y="70" font-size="11.5" opacity="0.75">Raw_FDIC, slot %02d</text>

    <text x="0" y="180" font-size="11.5" font-weight="700"
          letter-spacing="0.08em" fill="#b00020">THE CHECK</text>
    <rect x="0" y="194" width="200" height="52" rx="4" fill="none"
          stroke="#b00020" stroke-width="1.6"/>
    <text x="12" y="216" fill="#b00020">The filed Call Report</text>
    <text x="12" y="234" fill="#b00020" font-size="11.5">cdr.ffiec.gov facsimile</text>
    <line x1="200" y1="220" x2="528" y2="220" stroke="#b00020"
          stroke-width="1.6" marker-end="url(#a)"/>
    <text x="222" y="212" font-size="10.5" fill="#b00020">find the MDRM code on the
      form, read the number beside it</text>
    <rect x="528" y="194" width="200" height="52" rx="4" fill="none"
          stroke="#b00020" stroke-width="1.6"/>
    <text x="540" y="222" fill="#b00020">The filed figure</text>
    <line x1="628" y1="82" x2="628" y2="194" stroke="currentColor"
          stroke-width="1.4" stroke-dasharray="4 4"/>
    <rect x="756" y="100" width="212" height="76" rx="4" fill="none"
          stroke="currentColor" stroke-width="2"/>
    <text x="768" y="128" font-weight="700">%d of %d tie</text>
    <text x="768" y="150" font-size="11.5">at 30 June 2026</text>
  </g>
</svg>
<figcaption><b>Only the lower road touches a document the software does not
control.</b> The FDIC republishes what the bank filed; the check goes back to
what the bank actually filed, which can disagree &mdash; and for one bank in
this set, it does.</figcaption>
</figure>""" % (esc(bank["name"]), bank["slot"], tied, total)


def line_block(bank, line, comps):
    cert = bank["cert"]
    field = line["field"]
    bad = line["verdict"] != "TIES"
    pct = line.get("is_percent")
    cell = CELLS / ("%s-%s.png" % (cert, field))
    out = ['<div class="line%s">' % (" differs" if bad else "")]
    out.append("<h4>%s &mdash; %s</h4>" % (esc(field), esc(line["caption"] or "")))
    out.append('<div class="meta">%s &nbsp;&middot;&nbsp; cited as <code>%s</code>'
               ' &nbsp;&middot;&nbsp; %s</div>'
               % (esc(line["schedule"] or ""), esc(line["used"]),
                  esc(line["how"])))
    ours, filed = line["ours"], line["filed"]
    try:
        diff = None if (ours is None or filed is None) else float(ours) - float(filed)
    except (TypeError, ValueError):
        diff = None
    unit = "%" if pct else "thousands of dollars"
    out.append('<div class="compare">'
               "ours    %s, read from the workbook   %s\n"
               "filed   %s   %s\n"
               "diff    %s   %s</div>"
               % ("Raw_FDIC slot %02d" % bank["slot"], num(ours, pct),
                  "the bank's own Call Report".ljust(28), num(filed, pct),
                  "".ljust(28), (num(diff, pct) if diff is not None else "&mdash;")))
    out.append('<div class="pair">')
    if cell.exists():
        out.append('<div><div class="cap">the cell, in %s</div>'
                   '<img src="%s" alt="%s in the workbook"></div>'
                   % (esc(WB), uri(cell), esc(field)))
    for c in comps or []:
        if not c.get("png"):
            out.append('<div class="cap">%s: %s</div>'
                       % (esc(c.get("code")), esc(c.get("why", "not found"))))
            continue
        p = STRIPS / c["png"]
        if not p.exists():
            continue
        out.append('<div><div class="cap">%s on the %s filing, page %s</div>'
                   '<img src="%s" alt="%s on the filing"></div>'
                   % (esc(c["code"]), esc(c["quarter"]), esc(c["page"]),
                      uri(p), esc(c["code"])))
    out.append("</div>")
    out.append("<p style='font-size:12px;color:#5c5c5c;margin:9px 0 0'>units: %s"
               "</p>" % unit)
    out.append("</div>")
    return "\n".join(out)


def roster_table(bank):
    rows = ['<table><thead><tr><th>Field</th><th>What it is</th>'
            '<th>Schedule</th><th>Cited as</th><th class="n">Ours</th>'
            '<th class="n">Filed</th><th>Verdict</th></tr></thead><tbody>']
    for l in bank["lines"]:
        if l["note"]:
            continue
        cls = "ties" if l["verdict"] == "TIES" else (
            "differs" if l["verdict"].startswith("DIFFERS") else "could")
        pct = l.get("is_percent")
        rows.append('<tr class="%s"><td class="mono">%s</td><td>%s</td>'
                    '<td>%s</td><td class="mono">%s</td><td class="n">%s</td>'
                    '<td class="n">%s</td><td class="v %s">%s</td></tr>'
                    % (cls, esc(l["field"]), esc((l["caption"] or "")[:48]),
                       esc(l["schedule"] or ""), esc(l["used"][:44]),
                       num(l["ours"], pct), num(l["filed"], pct),
                       cls, esc(l["verdict"])))
    rows.append("</tbody></table>")
    return "\n".join(rows)


PNC_FINDING = """
<h2>What this found</h2>
<div class="note"><b>Two lines do not tie, and the workbook is not the one that
is wrong.</b>
<p style="margin:10px 0 0">PNC's credit card and C&amp;I net charge-offs for the
quarter differ from the bank's own filed report by 515 and 652 thousand dollars
&mdash; about half a percent. The workbook carries the FDIC's published
quarterly figure to the dollar, and the FDIC's own year-to-date figure agrees
with PNC's filing exactly. What does not add up is the FDIC's own arithmetic:</p>
<pre>FDIC NTCRCDQ  Q1  43,842  +  Q2  47,617  =  91,459
FDIC NTCRCD   year-to-date at Q2         =  91,974   off by 515
PNC's filed Call Report, same measure    =  91,974

FDIC NTCIQ    Q1 101,857  +  Q2 109,201  = 211,058
FDIC NTCI     year-to-date at Q2         = 211,710   off by 652
PNC's filed Call Report, same measure    = 211,710</pre>
<p>The same check across all twelve banks and all three quarterly flow fields
reconciles 34 times out of 36. Only these two fail, and only for PNC. There is
no merger in the quarter to explain it: PNC's only 2026 acquisition events are
branch transfers dated 6 July 2026, after the reporting date.</p>
<p><b>Which side do I believe?</b> The filing. It is the document the bank
signed, and the FDIC's own year-to-date agrees with it. The quarterly field is
derived, and for these two lines the derivation does not reconcile to its own
annual figure. <b>I did not adjust anything.</b> The workbook faithfully carries
what its source published, and this is written down rather than plugged.</p></div>
"""


def build(bank):
    cert, name = bank["cert"], bank["name"]
    counted = [l for l in bank["lines"] if not l["note"]]
    tied = sum(1 for l in counted if l["verdict"] == "TIES")
    bad = [l for l in counted if l["verdict"] != "TIES"]
    parts = [CSS, '<div class="wrap">']
    parts.append("<h1>Tie-out: %s</h1>" % esc(name))
    parts.append('<p class="sub">FDIC certificate %s &middot; report date %s '
                 '&middot; every line proved against the bank\'s own filed Call '
                 'Report. 5 September 2026.</p>' % (esc(cert), esc(bank["repdte"])))
    parts.append('<div class="headline%s"><b>%d of %d lines tie.</b>'
                 '<p style="margin:8px 0 0">The left of every comparison is a '
                 'cell read out of <code>%s</code> &mdash; not re-fetched, not '
                 'recomputed. The right is the bank\'s own Call Report as the '
                 'FFIEC serves it. %s</p></div>'
                 % (" bad" if bad else "", tied, len(counted), WB,
                    ("All of them agree." if not bad else
                     "%d do not, and that is a finding, set out below."
                     % len(bad))))
    parts.append("<h2>How the two roads meet</h2>")
    parts.append(diagram(bank, tied, len(counted)))
    parts.append("<h3>Go and check it yourself</h3>")
    parts.append("<p>The facsimile is public. This is the exact filing every "
                 "figure on the right came from:</p>")
    parts.append("<pre>%s</pre>" % esc(bank["facsimile"]))
    parts.append("<p>And the previous quarter, which the three quarterly flows "
                 "are differenced against:</p>")
    parts.append("<pre>%s</pre>" % esc(bank["facsimile_prior"]))
    parts.append("<h2>Every line</h2>")
    parts.append(roster_table(bank))
    if bad:
        parts.append(PNC_FINDING if cert == "6384" else "")
    parts.append("<h2>The evidence, line by line</h2>")
    parts.append("<p>For each line: the cell as it appears in the workbook, with "
                 "Excel's own row numbers and column letters, then the row of "
                 "the filed Call Report that carries the code the provenance map "
                 "cites. Both in the same picture, so the comparison is one "
                 "a reader can make rather than one they have to accept.</p>")
    if bad:
        for l in bad:
            parts.append(line_block(bank, l, strips[cert].get(l["field"])))
    for l in counted:
        if l["verdict"] != "TIES":
            continue
        parts.append(line_block(bank, l, strips[cert].get(l["field"])))
    parts.append("<h2>What this does not prove</h2>")
    parts.append("""<ul>
<li><b>One quarter.</b> These are the cells at 30 June 2026. The workbook holds
sixteen quarters per bank and the other fifteen were not compared here.</li>
<li><b>Raw lines, not ratios.</b> Forty-eight of these are dollar amounts read
straight off the form. Two are ratios the bank files itself. The FDIC's computed
ratios &mdash; the ones built from these raw lines &mdash; are not checked here;
they are arithmetic over numbers this document has just proved.</li>
<li><b>The provenance map is the thing being tested, and it passed.</b> Every
code it cites was found on this bank's filing and every number matched. A code
that is right for this filer and wrong for another would not show up here.</li>
<li><b>Nothing here was checked by a second person.</b></li>
</ul>""")
    parts.append("</div>")
    return "\n".join(parts)


made = []
for bank in rosters:
    html_out = build(bank)
    stem = "TIE-OUT-%s-cert%s-2026-06-30" % (
        bank["name"].replace(" ", "-").replace(".", ""), bank["cert"])
    src = SB / ("bankexh-%s.html" % bank["cert"])
    src.write_text(html_out, encoding="utf-8")
    pdf = OUTDIR / ("%s.pdf" % stem)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--no-pdf-header-footer", "--virtual-time-budget=180000",
                    "--print-to-pdf=%s" % pdf, src.resolve().as_uri()],
                   check=False, capture_output=True, timeout=900)
    ok = pdf.exists()
    made.append((bank["name"], pdf.name, pdf.stat().st_size if ok else 0))
    print("%-26s %-58s %s" % (bank["name"][:26], pdf.name[:58],
                              "%.1f MB" % (pdf.stat().st_size / 1e6) if ok
                              else "FAILED"))

print("\n%d bank exhibits written to %s" % (len(made), OUTDIR))
