"""Render WALKTHROUGH-2026-10-13.html, every picture embedded, from the run's own files.

Run from threshold-engine/ after compare.py. Then print it to PDF with Chrome
headless (the command is in the document's last section).
"""
import base64
import html as H
import json
from pathlib import Path

HERE = Path(__file__).parent
exp = json.load(open(HERE / "steps.json", encoding="utf-8"))["steps"] + \
    json.load(open(HERE / "steps-low.json", encoding="utf-8"))["steps"]
obs = json.load(open(HERE / "out" / "observed.json", encoding="utf-8-sig"))
low = json.load(open(HERE / "out" / "observed-low.json", encoding="utf-8-sig"))
result = (HERE / "RESULT.md").read_text(encoding="utf-8").splitlines()
headline = next(l for l in result if l.startswith("**")).strip("*").split("**")[0]
rows = [l for l in result if l.startswith("| W")]


def img(name, alt):
    data = base64.b64encode((HERE / "pictures" / name).read_bytes()).decode()
    return '<img src="data:image/png;base64,%s" alt="%s">' % (data, H.escape(alt))


def fig(name, caption):
    return "<figure>%s<figcaption>%s</figcaption></figure>" % (img(name, caption), caption)


steps_table = "".join(
    "<tr><td>%s</td><td>%s</td><td class=num>%s</td><td>%s</td></tr>"
    % tuple(H.escape(c.strip()) for c in r.strip("|").split("|")) for r in rows)
how = "".join("<tr><td>%s</td><td>%s</td></tr>" % (H.escape(s["id"]), H.escape(s["how"])) for s in exp)

CSS = """
:root{--ink:#1b2430;--muted:#5a6573;--rule:#d5dbe2;--paper:#fff;--code:#f2f4f7;--ok:#1f6f43}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--code:#1e2630;--ok:#7fd3a3}}
:root[data-theme="dark"]{--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--code:#1e2630;--ok:#7fd3a3}
body{background:var(--paper);color:var(--ink);font:14px/1.5 "Segoe UI",Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px 16px}
h1{font-size:24px;margin:0 0 4px;text-wrap:balance} h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px;break-after:avoid}
.sub{color:var(--muted);margin:0 0 16px} .verdict{display:inline-block;border:2px solid var(--ok);color:var(--ok);padding:2px 10px;font-weight:700}
pre,code{font-family:Consolas,monospace;font-size:12px;background:var(--code)} pre{padding:10px;white-space:pre-wrap;word-break:break-all}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin:6px 0;font-size:13px} td,th{border:1px solid var(--rule);padding:3px 7px;text-align:left;vertical-align:top}
th{background:var(--code)} .num{text-align:right} tr{break-inside:avoid}
figure{margin:12px 0;break-inside:avoid} figure img{width:100%;border:1px solid var(--rule)} figcaption{color:var(--muted);font-size:12px}
"""

BODY = f"""
<h1>The walkthrough, run in Excel</h1>
<p class="sub">threshold-engine on public data, 13 October 2026. Excel {H.escape(obs["excel"])}, through its automation interface.
<span class="verdict">{H.escape(headline)}</span></p>

<h2>What was done</h2>
<p>The expected answer for every cell was written first, by <code>expected.py</code>, from the source files and
<code>scale.py</code>, and committed before Excel was opened (commit <code>6f3505d</code>). <code>walk.ps1</code> then built the
workbooks with the same command a person types, opened them in Excel, typed each step's values into Settings or Assess,
let Excel recalculate, and read every cell back from Excel. Nothing was read from Python. <code>compare.py</code> put each
reading beside its expected answer: a number must agree to within 1e-9, text exactly. After every step the typed cells
were put back, and the Check column read blank again.</p>
<p>The card lines with the crisis and the pandemic left out (step W5) are held to a record made a week earlier, not to
<code>scale.py</code>: LOG.md, 7 October 2026, <b>3.171 / 3.464 / 4.050 / 5.981</b>, with 25 / 22 / 29 / 55 / 4 quarters kept
in each score. One card line is tied out separately to the Federal Reserve's own table
(<code>docs/tie-out/cards-moderate-line-2026-10-13/</code>).</p>

<h2>Result, step by step</h2>
<table><tr><th>Step</th><th>What</th><th class=num>Cells</th><th>Result</th></tr>{steps_table}</table>

<h2>What it looked like</h2>
{fig("w1-thresholds.png", "W1–W2. Thresholds as built: every product, Check blank.")}
{fig("w5-thresholds.png", "W5. The rehearsal settings for cards: 3.171 / 3.464 / 4.050 / 5.981, as recorded on 7 Oct.")}
{fig("w5-assess-cards-rehearsal.png", "W5. Assess, cards: five bands, the two periods left out as grey dots and dark strips.")}
{fig("w5-assess-counts.png", "W5. Assess, the quarters in each score: 25 / 22 / 29 / 55 / 4.")}
{fig("w3-assess-3.png", "W3.3. Assess, home equity, after the fix: every band, Low reaching below zero.")}
{fig("w14-thresholds.png", "W14. A lower-is-worse score: the lines fall from 2 to 5.")}
{fig("w14-assess.png", "W14. Its Assess chart, after the fix: the axis starts just under the data, not at zero.")}
{fig("w12-chart.png", "W12. Chart with Mortgage switched off; the legend below the plot, after the fix.")}
{fig("w11-run.png", "W11. Run: each file's SHA-256, equal to the files' own.")}

<h2>What it found</h2>
<ul>
<li><b>Assess drew the wrong bands for three of the four products.</b> For a product whose data starts after the first
quarter on the calendar (mortgage 1991, home equity and other consumer 1992), the chart's top and floor were
<code>MAX</code> and <code>MIN</code> over a column holding <code>#N/A</code>, so both were <code>#N/A</code>: Low and High vanished
and the other bands were drawn from zero. Every count was right; only the picture was wrong. The tests charted cards only,
which covers the whole calendar. Fixed with a helper column that is blank, not <code>#N/A</code>, and a test for each product.</li>
<li><b>A credit score drew from zero.</b> For a measure not floored at zero the chart's floor now sits just under the data,
and the axis, which Excel starts at zero unless told otherwise, is given a fixed round minimum at build. The strip for
periods left out now stands on an invisible base so it no longer pulls the axis down.</li>
<li><b>The Chart tab's legend covered the cutoff lines'</b> right-hand ends. It sits below the plot now.</li>
<li><b>WHAT-IT-DOES.md said the Glossary has 33 terms; it has 35.</b> The script's expected answer came from that document,
and Excel disagreed. The document was wrong and is corrected.</li>
<li><b>The card file in the repository is rounded to three decimals</b>, which moves every card line by 0.0005 against the
Federal Reserve's own figures and changes no score: see the tie-out.</li>
</ul>

<h2>What I got wrong</h2>
<ul>
<li>The script's first card reference was LOG.md of 6 October, which belongs to the scale retired that evening. The 7 October
record is the one for this scale; the script stopped on the mismatch before anything was run.</li>
<li>Four readings failed on the first run because of the runner, not the workbook: a formula that returns a cell came back
as a cell object, and <code>#N/A</code> in a hidden column reads as blank text. Both are read correctly now.</li>
<li>Steps W3 and W14 gained readings of the chart's floor and top after the first run, because that run showed the
pictures wrong while every cell the script read was right. They were added after, not before.</li>
</ul>

<h2>What this does not prove</h2>
<ul>
<li><b>A person's hands.</b> Excel did the arithmetic and drew the charts, but the typing was done through its automation
interface. The window (<code>Thresholds.pyw</code>) was not walked here; its tests drive it, and one opens the real window.</li>
<li><b>Every dial row.</b> Three dial rows were read against Thresholds (W6–W8); the tests hold every row to <code>scale.py</code>.</li>
<li><b>Evidence and Backtest</b> are written at build by the same Python the expected answers came from: W13 shows they
reach Excel intact, not that they are right. The tests and the 12 Oct tie-out cover them.</li>
<li><b>The peer workbook</b> is not in this walkthrough. It was run end to end and tied to KeyBank's filed Call Report on
12 October (<code>docs/tie-out/keybank-card-90plus-2026-10-12/</code>).</li>
<li><b>The bank's data.</b> Nothing internal was run. The on-site checklist covers that, at the bank.</li>
</ul>

<h2>The steps, as typed</h2>
<table><tr><th>Step</th><th>What was typed</th></tr>{how}</table>
<p>Every cell read and its expected answer: <code>docs/walkthrough/EXPECTED.md</code>. What Excel said: <code>out/observed.json</code>,
<code>out/observed-low.json</code>. To run it again, from <code>threshold-engine/</code>:</p>
<pre>python docs/walkthrough/expected.py
(build both workbooks: the commands are in WALKTHROUGH.md)
powershell -NoProfile -ExecutionPolicy Bypass -File docs/walkthrough/walk.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File docs/walkthrough/walk.ps1 -Workbook docs/walkthrough/out/score.xlsx -StepsFile steps-low.json -ObservedFile observed-low.json
python docs/walkthrough/compare.py
python docs/walkthrough/build_exhibit.py</pre>
"""

page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Threshold Walkthrough</title><style>%s</style></head><body>%s</body></html>" % (CSS, BODY))
(HERE / "WALKTHROUGH-2026-10-13.html").write_text(page, encoding="utf-8")
print("written")
