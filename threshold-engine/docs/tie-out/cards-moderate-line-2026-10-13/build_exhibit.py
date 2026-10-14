"""Render TIE-OUT-cards-moderate-line-2026-10-13.html, every image embedded.

Run from this folder: python build_exhibit.py. Then print it to PDF with
Chrome headless (the command is in the exhibit's section 4).
"""
import base64
import html as H
from pathlib import Path

HERE = Path(__file__).parent


def img(name, alt, width="100%"):
    data = base64.b64encode((HERE / name).read_bytes()).decode()
    return '<img src="data:image/png;base64,%s" alt="%s" style="width:%s">' % (data, alt, width)


DERIVE = H.escape((HERE / "derive-output.txt").read_text(encoding="utf-8"))
SHORT = "\n".join(l for l in DERIVE.splitlines() if not l.startswith("      "))

DIAGRAM = """
<svg viewBox="0 0 880 260" role="img" aria-label="The card line on two roads, 0.0005 apart">
 <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
 <g font-size="12" fill="currentColor" stroke="currentColor">
  <text x="10" y="22" stroke="none" font-weight="700">Production road (what the bank reads)</text>
  <rect x="10" y="36" width="160" height="54" fill="none"/>
  <text x="90" y="58" stroke="none" text-anchor="middle">Fed card rates</text>
  <text x="90" y="76" stroke="none" text-anchor="middle">(CORCCACBS)</text>
  <line x1="170" y1="63" x2="228" y2="63" marker-end="url(#a)"/>
  <text x="199" y="55" stroke="none" text-anchor="middle" font-size="10">4-qtr mean,</text>
  <text x="199" y="102" stroke="none" text-anchor="middle" font-size="10">3 decimals</text>
  <rect x="230" y="36" width="170" height="54" fill="none"/>
  <text x="315" y="58" stroke="none" text-anchor="middle">tests/data/</text>
  <text x="315" y="76" stroke="none" text-anchor="middle">cards_nco_ttm.csv</text>
  <line x1="400" y1="63" x2="458" y2="63" marker-end="url(#a)"/>
  <text x="429" y="55" stroke="none" text-anchor="middle" font-size="10">workbook</text>
  <rect x="460" y="36" width="200" height="54" fill="none" stroke="#c00" stroke-width="2"/>
  <text x="560" y="58" stroke="none" text-anchor="middle">Thresholds!F5, in Excel</text>
  <text x="560" y="76" stroke="none" text-anchor="middle">3 Moderate from = 3.4641865</text>
  <line x1="660" y1="63" x2="712" y2="118" marker-end="url(#a)"/>
  <text x="10" y="242" stroke="none" font-weight="700">Check road (the Federal Reserve Board's own table)</text>
  <rect x="10" y="150" width="190" height="54" fill="none"/>
  <text x="105" y="172" stroke="none" text-anchor="middle">Board release, All Banks, SA</text>
  <text x="105" y="190" stroke="none" text-anchor="middle">Credit cards, 166 quarters</text>
  <line x1="200" y1="177" x2="258" y2="177" marker-end="url(#a)"/>
  <text x="229" y="169" stroke="none" text-anchor="middle" font-size="10">by hand</text>
  <rect x="260" y="150" width="400" height="54" fill="none"/>
  <text x="460" y="172" stroke="none" text-anchor="middle">exact means, median 3.7575, move 0.585627</text>
  <text x="460" y="190" stroke="none" text-anchor="middle">3.7575 - 0.5 x 0.585627 = 3.4646865</text>
  <line x1="660" y1="177" x2="712" y2="142" marker-end="url(#a)"/>
  <rect x="714" y="104" width="160" height="56" fill="none" stroke-width="2"/>
  <text x="794" y="126" stroke="none" text-anchor="middle" font-weight="700">difference 0.0005</text>
  <text x="794" y="146" stroke="none" text-anchor="middle">DIFFERS (rounding)</text>
 </g>
</svg>"""

CSS = """
:root{--ink:#1b2430;--muted:#5a6573;--rule:#d5dbe2;--paper:#fff;--accent:#b00020;--code:#f2f4f7}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--accent:#ff6b7f;--code:#1e2630}}
:root[data-theme="dark"]{--ink:#e6eaef;--muted:#a3adb9;--rule:#38414c;--paper:#141a21;--accent:#ff6b7f;--code:#1e2630}
body{background:var(--paper);color:var(--ink);font:14px/1.5 "Segoe UI",Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px 16px}
h1{font-size:24px;margin:0 0 4px;text-wrap:balance} h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px;break-after:avoid}
h3{font-size:14px;margin:16px 0 6px;break-after:avoid}
.sub{color:var(--muted);margin:0 0 16px} .verdict{display:inline-block;border:2px solid var(--ink);padding:2px 10px;font-weight:700;letter-spacing:.05em}
pre,code{font-family:Consolas,monospace;font-size:12px;background:var(--code)} pre{padding:10px;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin:6px 0} td,th{border:1px solid var(--rule);padding:4px 8px;text-align:left;vertical-align:top}
th{background:var(--code)} .num{text-align:right} figure{margin:10px 0;break-inside:avoid} figcaption{color:var(--muted);font-size:12px}
.cite{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0} .cite span{border:1px solid var(--rule);padding:2px 8px;font-size:12px}
svg{max-width:100%;height:auto;color:var(--ink)} .compare{font-size:13px}
"""

BODY = f"""
<h1>Credit card: where Moderate begins, rehearsal settings</h1>
<p class="sub">threshold-engine workbook against the Federal Reserve Board's own charge-off table. Run 13 October 2026.
<span class="verdict">DIFFERS by 0.0005</span> &nbsp;cause found: the repository's card file is rounded to 3 decimals; no score changes.</p>

<h2>1 · How the dots connect</h2>
<figure>{DIAGRAM}
<figcaption>The top road is how the line reaches the cell the bank reads: the Fed's quarterly card rates, averaged over four quarters
and saved to three decimals in the repository's test file, then built into the workbook. The bottom road starts from the Board's own
published table, which this software does not produce, and does the same arithmetic by hand with exact decimals. The roads meet
0.0005 apart, and section 5 shows why.</figcaption></figure>

<h2>2 · The five links</h2>
<h3>Link 1 · The figure, read out of the workbook in Excel</h3>
<p>File <code>docs/walkthrough/out/rehearsal.xlsx</code>, built 13 Oct 2026 by the walkthrough's build command (section 4). Opened in Excel 16
through its automation interface. On Settings, Credit card's row was given the rehearsal leave-outs: <code>2007Q4</code> to <code>2012Q4</code>,
<i>financial crisis</i>, and <code>2021Q3</code> to <code>2023Q1</code>, <i>pandemic forbearance</i>, with the starting values half-width 0.5,
step 1.0 and z 2.5. Excel recalculated, and the walkthrough read tab <b>Thresholds</b>, cell <b>F5</b> (<i>3 Moderate from</i>, Credit card):
the value <b>3.4641865</b>, displayed as <b>3.464</b>. This is walkthrough step W5.</p>
<figure>{img("ours-thresholds-marked.png", "Thresholds tab in Excel with the Credit card 3 Moderate from cell ringed")}
{img("ours-thresholds-zoom.png", "The same row enlarged")}
<figcaption>Taken from Excel (<code>Range.CopyPicture</code>) during step W5, not drawn from Python.</figcaption></figure>
<div class="cite"><span>Tab Thresholds</span><span>Row 5 Credit card</span><span>Column F: 3 Moderate from</span><span>percent, TTM net charge-off rate</span><span>value 3.4641865</span><span>displayed <b>3.464</b></span></div>

<h3>Link 2 · The call</h3>
<p>There is no live call on the production road: the workbook reads the repository's file <code>tests/data/cards_nco_ttm.csv</code>, whose
header says it is <i>Federal Reserve CORCCACBS, all commercial banks, credit card; 4-quarter mean</i>. The build command, with every value in it,
is in section 4. The Run tab records the file's SHA-256 fingerprint, <code>8291d7d2…</code>, and the walkthrough checked it against the file (step W11).</p>

<h3>Link 3 · The derivation</h3>
<ol>
<li>Each quarter in the file is the mean of four quarterly Fed rates, ending in that quarter, saved to three decimals.</li>
<li>Quarters kept: every quarter except 2007Q4–2012Q4 and 2021Q3–2023Q1. 163 quarters, 135 kept.</li>
<li>Median kept: the middle of the 135 kept values (Data!F, <code>=MEDIAN</code>).</li>
<li>Typical yearly move: every four-quarter change whose both ends are kept (123 of them), then 1.4826 × the median absolute deviation of those changes.</li>
<li>3 Moderate from = median kept − half-width × typical yearly move = median − 0.5 × move.</li>
</ol>

<h3>Link 4 · The independent source</h3>
<p>Board of Governors of the Federal Reserve System, <i>Charge-Off and Delinquency Rates on Loans and Leases at Commercial Banks</i>,
table <i>Charge-Off Rates, All Banks, SA</i>, column <i>Consumer loans: Credit cards</i>. Public, with no login:</p>
<pre>https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm</pre>
<p>The page reads <i>Last update: August 25, 2026</i>. Fetched 13 Oct 2026. CORCCACBS, the series named in the file's header, is this column as
republished by FRED.</p>
<figure>{img("source-board-marked.png", "The Board's charge-off table, title, table name and the four latest card rates ringed")}
<figcaption>The page, photographed by headless Chrome on 13 Oct 2026. Ringed: the release title, the table (<i>All Banks, SA</i>) and the
credit card rates for 2025:3 to 2026:2.</figcaption></figure>
<figure>{img("source-board-zoom.png", "Credit card rates 2025:3 to 2026:2 enlarged")}</figure>
<div class="cite"><span>Board release: Charge-Off and Delinquency Rates</span><span>Charge-Off Rates, All Banks, SA</span><span>Column: Consumer loans, Credit cards</span><span>percent, annualized</span><span>2026:2 3.82 · 2026:1 3.82 · 2025:4 4.09 · 2025:3 4.18</span></div>
<p><b>Read twice.</b> The page's table was parsed into <code>board-credit-cards-sa.csv</code> (166 quarters, 1985:1 to 2026:2), and the four latest
rates were read off the photograph by eye. They agree: 4.18, 4.09, 3.82, 3.82. A third reading, from FRED's copy of CORCCACBS, could not be
made: <code>fred.stlouisfed.org</code> reset the connection and then timed out from this machine, twice.</p>
<p>The arithmetic, in <code>derive.py</code> (Python's standard library and exact decimals only; nothing from threshold-engine):</p>
<pre>{SHORT}</pre>

<h3>Link 5 · The comparison</h3>
<pre class="compare">ours    Thresholds!F5, read in Excel (W5)          3.4641865   (shown 3.464)
source  Board table, exact means, by hand          3.4646865   (3.465)
diff                                               -0.0005

ours    Thresholds!B5, median kept                 3.757
source  median of the exact means, 2020Q2          3.7575
diff                                               -0.0005

ours    Thresholds!C5, typical yearly move         0.585627
source  by hand                                    0.585627
diff                                               0

ours    Thresholds!J5, latest (2026Q2)             3.978
source  (4.18 + 4.09 + 3.82 + 3.82) / 4            3.9775
diff                                               +0.0005</pre>
<table><tr><th>Must match</th><th>Ours</th><th>Source</th><th></th></tr>
<tr><td>Entity</td><td>all commercial banks, credit card</td><td>All Banks, Credit cards</td><td>same</td></tr>
<tr><td>Period</td><td>1985Q4–2026Q2, quarterly</td><td>1985:1–2026:2 (the first three only feed the first mean)</td><td>same</td></tr>
<tr><td>Basis</td><td>net charge-off rate, SA, mean of four quarters</td><td>net charge-off rate, SA, annualized; mean taken by hand</td><td>same</td></tr>
<tr><td>Units</td><td>percent</td><td>percent</td><td>same</td></tr>
<tr><td>Precision</td><td>each mean saved to 3 decimals</td><td>exact (4 decimals)</td><td><b>differs</b></td></tr></table>
<p><span class="verdict">DIFFERS</span> by 0.0005 on the line, and on all four lines alike. The cause is the precision of the input file,
shown in section 5; the arithmetic agrees to the last digit once the file's rounding is applied (section 3).</p>

<h2>3 · Roster</h2>
<table><tr><th>Figure</th><th>Verdict</th></tr>
<tr><td>3 Moderate from, Credit card, rehearsal settings (Thresholds!F5)</td><td>DIFFERS 0.0005 (input rounding)</td></tr>
<tr><td>The other three lines, 2 / 4 / 5 (E5, G5, H5)</td><td>DIFFERS 0.0005 each (the same cause)</td></tr>
<tr><td>Latest value, 2026Q2 (J5): 3.978 against 3.9775</td><td>DIFFERS 0.0005 (the same cause)</td></tr>
<tr><td>Typical yearly move (C5)</td><td>TIED (0.585627; the changes cancel the rounding)</td></tr>
<tr><td>Quarters kept in each score, 25 / 22 / 29 / 55 / 4 (Assess!E8:E12)</td><td>TIED: the same from the exact means</td></tr>
<tr><td>Latest score, 2026Q2: 3 Moderate (K5)</td><td>TIED: 3.9775 is Moderate too</td></tr>
<tr><td>Every quarter of the input file against the Board's means</td><td>163 of 163 within rounding: 83 equal at 3 decimals; 80 are means ending in 5, saved 0.0005 up or down</td></tr>
<tr><td>The same line, recomputed from the file's 3-decimal values</td><td>TIED: 3.4641865 exactly</td></tr></table>
<p>Of 8 workbook figures, 3 tied (the move, the counts, the latest score) and 5 differ by 0.0005 (the four lines and the latest value, J5), all from one cause. COULD NOT: 0. The third reading (FRED) could not be made.</p>

<h2>4 · How to run it yourself</h2>
<p>From <code>C:\\Users\\ajish\\SATC\\threshold-engine</code>.</p>
<ol>
<li>Build the rehearsal workbook:
<pre>python -m threshold_engine workbook docs/walkthrough/out/rehearsal.xlsx --series "Credit card=tests/data/cards_nco_ttm.csv" --series "Mortgage=tests/data/mortgage_nco_ttm.csv" --series "Home equity=tests/data/home_equity_nco_ttm.csv" --series "Other consumer=tests/data/other_consumer_as_filed_nco_ttm.csv" --name "Net charge-off rate (TTM)" --unit "%" --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41</pre>
(Before installing the package, set <code>PYTHONPATH=src</code>.)</li>
<li>Open it in Excel. On <b>Settings</b>, row 6 (Credit card): B6 <code>2007Q4</code>, C6 <code>2012Q4</code>, D6 <code>financial crisis</code>,
E6 <code>2021Q3</code>, F6 <code>2023Q1</code>, G6 <code>pandemic forbearance</code>. On <b>Thresholds</b>, F5 reads 3.464.</li>
<li>Open the Board's table:
<pre>https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm</pre>
Column <i>Credit cards</i> under <i>Consumer loans</i>. For 2026:2 the mean of the four latest rates is (4.18 + 4.09 + 3.82 + 3.82) / 4 = 3.9775.</li>
<li>For the line itself, run the derivation, which reads the table saved beside this document:
<pre>cd docs/tie-out/cards-moderate-line-2026-10-13
python derive.py</pre></li>
<li>Render this document:
<pre>python build_exhibit.py
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --headless=new --no-pdf-header-footer --print-to-pdf=TIE-OUT-cards-moderate-line-2026-10-13.pdf TIE-OUT-cards-moderate-line-2026-10-13.html</pre></li>
</ol>

<h2>5 · What it found</h2>
<ul>
<li><b>The repository's public card file is rounded to three decimals, and that moves every card line by 0.0005.</b> A four-quarter mean of
rates published to two decimals is exact at four. In 80 of 163 quarters it ends in 5, and the file keeps three, rounded by Python's
floating-point rounding: 43 went up and 37 down (2026Q2: 3.9775 saved as 3.978; 2020Q2: 3.7575 saved as 3.757). 2020Q2 is the median kept
under the rehearsal settings, so the median, and every line built on it, is 0.0005 lower than the Fed's figures give. No kept quarter and
not the latest changes score.</li>
<li><b>It touches nothing the bank will run.</b> On site the workbook reads the bank's own files. The rounding is in a test file made before
this check, and the tests compare the workbook with the reference on that same file, so they could not see it. Only the Board's table could.
The file is left as it is, so its fingerprint and every test built on it stand; this document and LOG.md record its precision.</li>
</ul>

<h2>6 · What I got wrong</h2>
<ul>
<li>A first quick comparison flagged only 13 of the 80 rounded quarters: it compared in binary floating point, where most exact halves land a
hair inside 0.0005. <code>derive.py</code> compares in exact decimals and finds all 80.</li>
<li>The walkthrough's script first took its card reference from LOG.md of 6 Oct (3.757 / 4.469 / 5.180 / 5.892). Those figures belong to the
scale retired that evening. The 7 Oct figures for this scale are the ones it now holds the workbook to.</li>
</ul>

<h2>7 · What this does not prove</h2>
<ul>
<li><b>One product.</b> Mortgage (CORSFRMACBS) is built the same way and likely carries the same rounding; it was not tied here. Home equity
and other consumer come from FDIC sums, a different road, and were not tied.</li>
<li><b>Not the bank's numbers.</b> The scale on KeyBank's internal data is run on site; nothing here says those files are right.</li>
<li><b>Revisions.</b> The Board revises history. The file and the table agree today within rounding in all 163 quarters, so no revision has
moved a value since the file was made; a later release may.</li>
<li><b>One reading of the full table.</b> All 166 quarters were parsed from the page; only the four latest were also read by eye. FRED, the
second publisher, could not be reached.</li>
</ul>
"""

html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Card Moderate Line Tie-Out</title><style>%s</style></head><body>%s</body></html>" % (CSS, BODY))
(HERE / "TIE-OUT-cards-moderate-line-2026-10-13.html").write_text(html, encoding="utf-8")
print("written")
