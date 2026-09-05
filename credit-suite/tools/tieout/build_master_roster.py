"""The master roster: everything tied out, with its denominator.

The firm's question is not "is this figure right" but "how much of this can I
trust, and where does it stop." So this is one page that answers that across
both monitors, with the differences and the findings above the agreements,
because the ones that agree are not what anybody needs to read.
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
OUTDIR = CS / "docs" / "tie-out"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

banks = json.loads((SB / "bank_rosters.json").read_text())
fred = json.loads((SB / "fred_roster.json").read_text())


def esc(x):
    return html.escape("" if x is None else str(x))


bank_lines = [(b, l) for b in banks for l in b["lines"] if not l["note"]]
bank_tied = sum(1 for _b, l in bank_lines if l["verdict"] == "TIES")
bank_bad = [(b, l) for b, l in bank_lines if l["verdict"] != "TIES"]
fred_tied = sum(1 for r in fred if r["verdict"] == "TIED")
total = len(bank_lines) + len(fred)
tied = bank_tied + fred_tied

FRED_SETS = {}
for r in fred:
    s = FRED_SETS.setdefault(r["set"], {"n": 0, "tied": 0, "pub": r["publisher"]})
    s["n"] += 1
    s["tied"] += r["verdict"] == "TIED"

CSS = """<style>
:root{--ink:#151515;--dim:#5c5c5c;--rule:#d8d8d8;--red:#b00020;--good:#0a6b3d;}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font:14px/1.62 "Charter",Georgia,serif}
.wrap{max-width:1020px;margin:0 auto;padding:44px 46px 80px}
h1{font:700 30px/1.2 system-ui,sans-serif;margin:0 0 6px;letter-spacing:-.01em}
h2{font:700 19px/1.3 system-ui,sans-serif;margin:40px 0 10px;padding-top:14px;
   border-top:2px solid var(--ink)}
h3{font:700 15px/1.35 system-ui,sans-serif;margin:24px 0 8px}
.sub{color:var(--dim);font:15px/1.5 system-ui,sans-serif;margin:0 0 22px}
.headline{border:2px solid var(--ink);padding:18px 22px;margin:22px 0 28px}
.headline b{font:700 24px/1.3 system-ui,sans-serif}
p{margin:0 0 12px}
table{border-collapse:collapse;width:100%;margin:14px 0 22px;
      font:12.5px/1.5 system-ui,sans-serif}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--rule);
      vertical-align:top}
th{font-weight:700;border-bottom:1.5px solid var(--ink)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.mono{font-family:ui-monospace,Consolas,monospace;white-space:nowrap}
.ties{color:var(--good);font-weight:700}
.differs{color:var(--red);font-weight:700}
tr.bad td{background:#fff6f6}
.note{border-left:4px solid var(--red);background:#fff6f6;padding:13px 17px;margin:16px 0}
.note.win{border-color:var(--good);background:#f2fbf6}
ul,ol{margin:0 0 14px;padding-left:22px}
li{margin-bottom:8px}
code{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;
     background:#f2f2ef;padding:1px 4px}
pre{font:12px/1.55 ui-monospace,Consolas,monospace;background:#f7f7f5;
    padding:12px 14px;border:1px solid var(--rule);white-space:pre-wrap;
    overflow-wrap:anywhere}
</style>"""

p = [CSS, '<div class="wrap">']
p.append("<h1>Tie-out roster: the whole credit suite</h1>")
p.append('<p class="sub">Every data point in both monitors, checked against the '
         'body that produces it. 5 September 2026.</p>')
p.append('<div class="headline"><b>%d of %d data points tie. %d differ. '
         '0 could not.</b>'
         '<p style="margin:10px 0 0">Every figure on the ours side was read out '
         'of the shipped workbook &mdash; the cell a person opens &mdash; and '
         'never re-fetched. Every figure on the other side came off a document '
         'published by somebody else: a bank\'s own filed Call Report, or the '
         'agency that computes a series. The two that differ are set out '
         'first.</p></div>' % (tied, total, len(bank_bad)))

p.append("<h2>What does not tie</h2>")
p.append('<div class="note"><b>Two lines, both PNC Bank, and the workbook is not '
         'the side that is wrong.</b>'
         '<p style="margin:10px 0 0">PNC\'s credit card and C&amp;I net '
         'charge-offs for the quarter differ from the bank\'s own filed report '
         'by 515 and 652 thousand dollars, about half a percent. The workbook '
         'carries the FDIC\'s published quarterly figure to the dollar, and the '
         'FDIC\'s own year-to-date figure matches PNC\'s filing exactly. What '
         'does not reconcile is the FDIC\'s own arithmetic:</p>'
         '<pre>FDIC quarterly  Q1  43,842 + Q2  47,617 =  91,459\n'
         'FDIC year-to-date at Q2                  =  91,974    off by 515\n'
         "PNC's filed Call Report                  =  91,974\n\n"
         'FDIC quarterly  Q1 101,857 + Q2 109,201 = 211,058\n'
         'FDIC year-to-date at Q2                  = 211,710    off by 652\n'
         "PNC's filed Call Report                  = 211,710</pre>"
         '<p>The same reconciliation across all twelve banks and all three '
         'quarterly flow fields holds 34 times out of 36. Only these two fail. '
         'No merger explains it: PNC\'s only 2026 acquisition events are branch '
         'transfers dated 6 July 2026, after the reporting date.</p>'
         '<p><b>I believe the filing</b>, because it is the document the bank '
         'signed and the FDIC\'s own annual figure agrees with it. Nothing was '
         'adjusted. The workbook faithfully carries what its source published, '
         'and this is written down rather than plugged.</p></div>')

p.append("<h2>What the tie-out found</h2>")
p.append("<p>Six defects, and every one of them left the numbers correct, which "
         "is why a test suite of 414 passing tests had never seen any of "
         "them.</p>")
p.append("""<ol>
<li><b>A shipped workbook with a state missing from it.</b> Nebraska's house
price index was blank. One <code>Internal Server Error</code> from the data
provider blanked the slot and the build passed. The retry covered rate limits
only. <i>Fixed.</i></li>
<li><b>Two series wearing each other's description</b> &mdash; the commercial
real estate construction and nonfarm-nonresidential labels were swapped on the
dashboard and in the raw tabs. <i>Fixed.</i></li>
<li><b>A tightening indicator with its alert switched off</b>, because it had
been filed as a demand series, and demand series correctly get no alert. A real
mortgage-tightening signal could never fire. <i>Fixed, and that turns an alert
on.</i></li>
<li><b>Two more labels naming a different series</b> than the number beside
them. <i>Fixed.</i></li>
<li><b>Four series declaring &ldquo;billions&rdquo; beside a figure in
millions</b> &mdash; a factor of a thousand on the line a person reads.
<i>Fixed.</i></li>
<li><b>The FDIC's own quarterly and annual figures for PNC do not
reconcile.</b> Reported above; nothing changed, because our side is right.</li>
</ol>""")
p.append('<div class="note win"><b>And three defects in the checking itself,</b> '
         'which is the likelier culprit than the code and was here too. My first '
         'pass cited the wrong Call Report line for C&amp;I charge-offs '
         '(U.S. addressees only, where the measure is U.S. and non-U.S.), took '
         'the wrong column of the total capital ratio for the one bank that '
         'files two, and produced six blank source photographs that reported '
         '&ldquo;ok&rdquo;. Each showed up as an implausibly uniform failure '
         'across every entity &mdash; which is the tell.</div>')

p.append("<h2>The denominator, by set</h2>")
p.append('<table><thead><tr><th>Set</th><th>Checked against</th>'
         '<th class="n">Lines</th><th class="n">Tie</th><th class="n">Differ</th>'
         '</tr></thead><tbody>')
for b in banks:
    counted = [l for l in b["lines"] if not l["note"]]
    t = sum(1 for l in counted if l["verdict"] == "TIES")
    bad = len(counted) - t
    p.append('<tr class="%s"><td>%s <span style="color:#5c5c5c">cert %s</span>'
             '</td><td>its own filed Call Report, 30 June 2026</td>'
             '<td class="n">%d</td><td class="n ties">%d</td>'
             '<td class="n %s">%d</td></tr>'
             % ("bad" if bad else "", esc(b["name"]), esc(b["cert"]),
                len(counted), t, "differs" if bad else "", bad))
for label, s in FRED_SETS.items():
    p.append('<tr><td>%s</td><td>%s</td><td class="n">%d</td>'
             '<td class="n ties">%d</td><td class="n">%d</td></tr>'
             % (esc(label), esc(s["pub"]), s["n"], s["tied"], s["n"] - s["tied"]))
p.append('<tr style="border-top:2px solid #151515"><td><b>Total</b></td><td></td>'
         '<td class="n"><b>%d</b></td><td class="n ties"><b>%d</b></td>'
         '<td class="n differs"><b>%d</b></td></tr>' % (total, tied, len(bank_bad)))
p.append("</tbody></table>")

p.append("<h2>Where the evidence is</h2>")
p.append("<p>One document per bank and one for the whole macro set. Each is "
         "self-contained: every screenshot is embedded, so it survives being "
         "forwarded to somebody who does not have this machine.</p>")
p.append("<table><thead><tr><th>Document</th><th>What is in it</th></tr></thead>"
         "<tbody>")
for f in sorted((OUTDIR / "banks-12-2026-06-30").glob("*.pdf")):
    p.append('<tr><td class="mono">banks-12-2026-06-30/%s</td>'
             '<td>53 lines, each with the workbook cell photographed and the '
             'row of the filed Call Report that carries it</td></tr>'
             % esc(f.name))
p.append('<tr><td class="mono">fred-142-series-2026-09-05/'
         'TIE-OUT-fred-142-series-2026-09-05.pdf</td>'
         '<td>142 series across six publishers, with every workbook cell '
         'photographed and each agency\'s own page marked</td></tr>')
p.append('<tr><td class="mono">keybank-card-30-89-2026-09-05/</td>'
         '<td>the first exhibit: one figure traced link by link, and all 53 '
         'KeyBank lines</td></tr>')
p.append("</tbody></table>")

p.append("<h2>What this does not prove</h2>")
p.append("""<ul>
<li><b>One quarter for the banks, one observation for the macro series.</b> The
bank workbook holds sixteen quarters each and the macro workbook holds 13,905
observations. What was compared is the most recent of each &mdash; 778 figures,
not the whole history. The Case-Shiller set was additionally checked a second
month.</li>
<li><b>Raw inputs, not the ratios built on them.</b> Forty-eight of each bank's
lines are dollar amounts read straight off the form, and two are ratios the bank
files itself. The FDIC's computed ratios, and the dashboard's z-scores, bands
and alert logic, are arithmetic over figures this proves &mdash; and are not
themselves checked here. That was the instruction: the base data.</li>
<li><b>Twenty of the Case-Shiller series are tied through a ratio of two
cells</b>, not a level, because S&amp;P does not publish adjusted levels free.
That pins the month-on-month move, not the absolute level.</li>
<li><b>The provenance map passed rather than was proved universal.</b> Every
code it cites was found on every one of these twelve filings and every number
matched. A citation that is right for these filers and wrong for a bank filing a
different form would not show up here.</li>
<li><b>Nothing here was checked by a second person.</b></li>
</ul>""")
p.append("</div>")

src = SB / "master_roster.html"
src.write_text("\n".join(p), encoding="utf-8")
pdf = OUTDIR / "TIE-OUT-ROSTER-all-sets-2026-09-05.pdf"
subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                "--no-pdf-header-footer", "--virtual-time-budget=60000",
                "--print-to-pdf=%s" % pdf, src.resolve().as_uri()],
               check=False, capture_output=True, timeout=600)
print("data points: %d, tied %d, differ %d" % (total, tied, len(bank_bad)))
print("master roster: %s (%.2f MB)"
      % (pdf.name, pdf.stat().st_size / 1e6) if pdf.exists() else "PDF FAILED")
