"""Render TIE-OUT-keybank-card-90plus-2026-10-12.html, every image embedded.

Run from this folder: python build_exhibit.py. Then print it to PDF with
Chrome headless (the command is in the exhibit's section 4).
"""
import base64
from pathlib import Path

HERE = Path(__file__).parent


def img(name, alt, width="100%"):
    data = base64.b64encode((HERE / name).read_bytes()).decode()
    return '<img src="data:image/png;base64,%s" alt="%s" style="width:%s">' % (data, alt, width)


DIAGRAM = """
<svg viewBox="0 0 860 250" role="img" aria-label="One fact on two roads, meeting at difference 0">
 <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
 <g font-size="12" fill="currentColor" stroke="currentColor">
  <text x="10" y="22" stroke="none" font-weight="700">Production road (what the bank reads)</text>
  <rect x="10" y="36" width="150" height="54" fill="none"/>
  <text x="85" y="58" stroke="none" text-anchor="middle">FDIC BankFind API</text>
  <text x="85" y="76" stroke="none" text-anchor="middle">P9CRCD, cert 17534</text>
  <line x1="160" y1="63" x2="228" y2="63" marker-end="url(#a)"/>
  <text x="194" y="55" stroke="none" text-anchor="middle" font-size="10">peers pull</text>
  <rect x="230" y="36" width="150" height="54" fill="none"/>
  <text x="305" y="58" stroke="none" text-anchor="middle">cache</text>
  <text x="305" y="76" stroke="none" text-anchor="middle">q20260630.json</text>
  <line x1="380" y1="63" x2="448" y2="63" marker-end="url(#a)"/>
  <text x="414" y="55" stroke="none" text-anchor="middle" font-size="10">peers build</text>
  <rect x="450" y="36" width="190" height="54" fill="none" stroke="#c00" stroke-width="2"/>
  <text x="545" y="58" stroke="none" text-anchor="middle">peers.xlsx, DelinquencyData</text>
  <text x="545" y="76" stroke="none" text-anchor="middle">cell F2051 = 9,346</text>
  <line x1="640" y1="63" x2="700" y2="120" marker-end="url(#a)"/>
  <text x="10" y="232" stroke="none" font-weight="700">Check road (a document KeyBank filed)</text>
  <rect x="10" y="150" width="150" height="54" fill="none"/>
  <text x="85" y="172" stroke="none" text-anchor="middle">FFIEC CDR</text>
  <text x="85" y="190" stroke="none" text-anchor="middle">Call Report, 6/30/2026</text>
  <line x1="160" y1="177" x2="228" y2="177" marker-end="url(#a)"/>
  <text x="194" y="169" stroke="none" text-anchor="middle" font-size="10">read twice</text>
  <rect x="230" y="150" width="410" height="54" fill="none"/>
  <text x="435" y="172" stroke="none" text-anchor="middle">RC-N line 5.a, column B, RCFDB576 = 9,346</text>
  <text x="435" y="190" stroke="none" text-anchor="middle">(page image, and the filing's XBRL: 9346000 USD)</text>
  <line x1="640" y1="177" x2="700" y2="140" marker-end="url(#a)"/>
  <rect x="702" y="104" width="148" height="52" fill="none" stroke-width="2"/>
  <text x="776" y="126" stroke="none" text-anchor="middle" font-weight="700">difference 0</text>
  <text x="776" y="144" stroke="none" text-anchor="middle">TIED</text>
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
<h1>KeyBank card 90+ days past due, still accruing, 30 June 2026</h1>
<p class="sub">threshold-engine peer workbook against KeyBank's filed Call Report. Run 12 October 2026. <span class="verdict">TIED</span></p>

<h2>1 · How the dots connect</h2>
<figure>{DIAGRAM}
<figcaption>The same fact travels two roads. The top road is how the number reaches the cell the bank reads. The bottom road goes to the
report KeyBank itself filed with its regulators, which this software does not produce and cannot change. That is what makes it
evidence and not a second opinion from the same feed.</figcaption></figure>

<h2>2 · The five links</h2>
<h3>Link 1 · The figure, read out of the workbook in Excel</h3>
<p>File <code>peers.xlsx</code>, built 12 Oct 2026 by <code>peers build</code> (command in section 4). Opened in Excel 16 through COM
automation, recalculated in full (<code>CalculateFull</code>), tab <b>DelinquencyData</b>, row 2051. Excel's displayed text of each cell:</p>
<table><tr><th>A Product</th><th>B Measure</th><th>C Bank</th><th>D Certificate</th><th>E Quarter-end</th><th class="num">F Numerator ($000)</th><th class="num">G Balance ($000)</th><th class="num">H Quarter-end rate (%)</th></tr>
<tr><td>Credit card</td><td>90+ accruing</td><td>KeyBank</td><td>17534</td><td>2026Q2</td><td class="num"><b>9,346</b></td><td class="num">926,589</td><td class="num">1.0086</td></tr></table>
<figure>{img("hdr-after.png", "DelinquencyData header row in Excel")}
{img("ours-delinquencydata-rows.png", "DelinquencyData rows 2049 to 2051 in Excel")}
<figcaption>Pictures of the header and rows 2049–2051, taken from Excel (<code>Range.CopyPicture</code>), not from Python.</figcaption></figure>
<p>The Delinquency tab charts this column. With the measure set to <i>90+ accruing</i> and the basis to <i>quarter-end</i>, the red line ends at 1.01 in 2026Q2:</p>
<figure>{img("Delinquency_90-accruing-quarter-end.png", "Delinquency chart, 90+ accruing, quarter-end")}
<figcaption>Exported from Excel after recalculation. In this setting the tab held no formula error and no #N/A.</figcaption></figure>

<h3>Link 2 · The call</h3>
<pre>curl -s "https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630&amp;fields=CERT,REPDTE,LNCRCD,P3CRCD,P9CRCD,NACRCD&amp;format=json"</pre>
<p>Response on 12 Oct 2026 (the part that carries the figure):</p>
<pre>"data":[{{"data":{{"P3CRCD":8528,"REPDTE":"20260630","LNCRCD":926589,"CERT":17534,"NACRCD":6401,"P9CRCD":9346,"ID":"17534_20260630"}}}}]
"index":{{"name":"risview_20260819185831","createTimestamp":"2026-08-19T18:58:33Z"}}</pre>
<p><code>peers pull --delinquency yes</code> asks the same endpoint for every filer in the quarter (4,313 in 2026Q2) and stores the rows
in <code>cache/q20260630.json</code>. The cached KeyBank row reads <code>LNCRCD 926589, P9CRCD 9346</code>.</p>

<h3>Link 3 · The derivation</h3>
<ol>
<li>The measure <i>90+ accruing</i> has numerator field P9 (<code>peers/delinquency.py</code>, <code>MEASURES</code>); for credit card that is <code>P9CRCD</code>, and the balance is <code>LNCRCD</code>.</li>
<li><code>bank_delinquency(data, "17534", "Credit card", "90+ accruing", jump=0.25, min_book=1000000, exempt_min_book=True)</code> takes the 2026Q2 row as filed: numerator 9,346, balance 926,589. KeyBank is exempt from the minimum book, and the jump rule does not apply to a quarter-end rate, which comes from one filing.</li>
<li>Rate = 100 × 9,346 ÷ 926,589 = 1.008646 %. By hand: 9,346 ÷ 926,589 = 0.0100865.</li>
<li><code>peers_workbook.py</code> writes those three numbers to DelinquencyData row 2051, columns F, G and H. They are values, not formulas.</li>
</ol>

<h3>Link 4 · The independent source</h3>
<p>KeyBank, National Association's Consolidated Reports of Condition and Income (FFIEC 031), report date 6/30/2026, on the FFIEC Central Data Repository.
It is public, with no login:</p>
<pre>https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&amp;idType=fdiccert&amp;id=17534&amp;date=06302026</pre>
<p><b>First reading, the rendered page.</b> Schedule RC-N, page 45 of the report (page 46 of 75 in the viewer). The page was photographed on 5 Sep 2026 for an earlier credit-suite tie-out.
Its header gives the entity, the form and the period:</p>
<figure>{img("source-rc-n-identity.png", "RC-N page header: KeyBank National Association, FFIEC 031, Report Date 6/30/2026", "70%")}</figure>
<figure>{img("source-rc-n-5a-marked.png", "Schedule RC-N page with line 5.a ringed")}
{img("source-rc-n-5a-zoom.png", "RC-N line 5.a enlarged")}
<figcaption>Line 5.a <i>Credit cards</i>, ringed in red, then enlarged under its column headings.</figcaption></figure>
<div class="cite"><span>Schedule RC-N</span><span>Report page 45</span><span>Line 5.a Credit cards</span><span>Column B: Past due 90 days or more and still accruing</span><span>RCFDB576</span><span>$ thousands</span><span>Report date 6/30/2026</span><span>Last updated 7/30/2026</span><span><b>9,346</b></span></div>
<p>For the rate, the balance comes from Schedule RC-C Part I, line 6.a, Column A (Consolidated Bank):</p>
<figure>{img("source-rc-c-identity.png", "RC-C page header", "70%")}
{img("source-rc-c-6a-zoom.png", "RC-C line 6.a enlarged")}</figure>
<div class="cite"><span>Schedule RC-C Part I</span><span>Report page 23</span><span>Line 6.a Credit cards</span><span>Column A Consolidated Bank</span><span>RCFDB538</span><span>$ thousands</span><span><b>926,589</b></span></div>
<p><b>Second reading, the filing's XBRL</b> (the machine-readable copy the FFIEC publishes alongside the pages). Downloaded on 12 Oct 2026, 22:30 UTC, through the facsimile page's <i>Download XBRL</i> button,
using <code>credit-suite</code>'s <code>filing.fetch_xbrl("17534", "2026-06-30")</code>. 187,801 bytes, SHA-256 <code>cb185d18…d8a0</code>. The lines, verbatim:</p>
<pre>&lt;cc:RCFDB576 contextRef="CI_280110_2026-06-30" unitRef="USD" decimals="0"&gt;9346000&lt;
&lt;cc:RCFDB538 contextRef="CI_280110_2026-06-30" unitRef="USD" decimals="0"&gt;926589000&lt;</pre>
<p>The XBRL is in dollars: 9,346,000 USD = 9,346 in thousands. The context <code>280110</code> is KeyBank's RSSD ID, printed on the page header.</p>

<h3>Link 5 · The comparison</h3>
<pre class="compare">ours    peers.xlsx DelinquencyData!F2051, read in Excel        9,346   ($000)
source  RC-N 5.a col B RCFDB576, page image (photo 5 Sep 2026)  9,346   ($000)
source  RCFDB576, filing XBRL fetched 12 Oct 2026          9,346,000   (USD) = 9,346 ($000)
diff                                                            0

ours    DelinquencyData!G2051 (balance)                       926,589
source  RC-C 6.a col A RCFDB538, page and XBRL                926,589
diff                                                            0

ours    DelinquencyData!H2051 (rate, %)                        1.0086
source  100 x 9,346 / 926,589, both from the filing           1.0086
diff                                                            0</pre>
<table><tr><th>Must match</th><th>Ours</th><th>Source</th><th></th></tr>
<tr><td>Entity</td><td>cert 17534, KeyBank</td><td>KeyBank National Association, RSSD 280110 (FDIC cert 17534 is the id the CDR link uses)</td><td>same</td></tr>
<tr><td>Period</td><td>2026Q2 quarter-end</td><td>Report date 6/30/2026</td><td>same</td></tr>
<tr><td>Basis</td><td>90+ days past due and still accruing; consolidated bank</td><td>RC-N column B, RCFD (consolidated) line</td><td>same</td></tr>
<tr><td>Units</td><td>$ thousands</td><td>page: $ thousands; XBRL: USD, converted</td><td>same</td></tr></table>
<p><span class="verdict">TIED</span> on all three: the numerator, the balance and the rate.</p>

<h2>3 · Roster</h2>
<table><tr><th>Figure</th><th>Verdict</th></tr>
<tr><td>KeyBank card 90+ accruing, 2026Q2, $000 (DelinquencyData!F2051)</td><td>TIED</td></tr>
<tr><td>KeyBank card balance, 2026Q2, $000 (G2051)</td><td>TIED</td></tr>
<tr><td>KeyBank card 90+ accruing rate, 2026Q2 (H2051)</td><td>TIED</td></tr></table>
<p>3 of 3 tied. DIFFERS 0, COULD NOT 0.</p>

<h2>4 · How to run it yourself</h2>
<p>In PowerShell or Git Bash, from <code>C:\\Users\\ajish\\SATC\\threshold-engine</code>.</p>
<ol>
<li>Pull the public FDIC data, with the delinquency fields (about 6 minutes):
<pre>python -m threshold_engine peers pull --cache fdic-cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --mergers 2005-10-01 --delinquency yes</pre></li>
<li>Build the peer workbook (about 12 minutes):
<pre>python -m threshold_engine peers build peers.xlsx --cache fdic-cache --roster config/peers.json --series-dir peer-series --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --mergers fdic-cache/mergers.json --extra-acquisitions 6672=2022Q2 --delinquency yes --industry-combined --jump 0.25 --min-book 1000000 --exempt-self yes --pack all --min-banks 5 --rank-by net --last-n 20 --min-obs 12 --base-quarter 2019Q4 --index-min-book 500000 --lagged-years 2019 2025 --lag-years 2 --normalisation-years 2019 2025 --mix-base-year 2019</pre>
(Before installing the package, set <code>PYTHONPATH=src</code>.)</li>
<li>Open <code>peers.xlsx</code> in Excel. On the <b>DelinquencyData</b> tab, filter column A to <i>Credit card</i>, B to <i>90+ accruing</i>, C to <i>KeyBank</i> and E to <i>2026Q2</i>. Column F reads 9,346.</li>
<li>Open the filing in a browser:
<pre>https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&amp;idType=fdiccert&amp;id=17534&amp;date=06302026</pre>
Go to Schedule RC-N (page 45 of the report), line 5.a <i>Credit cards</i>, Column B. It reads 9,346.</li>
<li>For the rate, on the same filing go to Schedule RC-C Part I (page 23), line 6.a, Column A: 926,589. Then 9,346 ÷ 926,589 × 100 = 1.0086.</li>
</ol>

<h2>5 · What it found</h2>
<ul>
<li><b>The DelinquencyData headers were clipped in Excel.</b> <i>Four-quarter average (%)</i> and <i>Four-quarter average kept</i> were cut off at the top of the cell.
openpyxl's widths could not show that; opening the file in Excel did. The columns are now wider (<code>peers_workbook.py</code>), and the header picture in link 1 was taken from Excel after the fix.</li>
<li><b>Citizens reports zero card loans 90+ days past due and still accruing in all 82 quarters</b>, 2006Q1 to 2026Q2. On this measure its line lies on the axis. This is
what Citizens filed, not an error. A bank that stops accruing on a card before 90 days has nothing to report in column B, so <i>90+ accruing</i> alone
does not compare banks like for like. <i>90+ incl. nonaccrual</i> is the measure that does, which is why all three are built.</li>
<li><b>KeyBank's card 90+ accruing is exactly 0</b> in 2008Q1–2009Q3 (a $5–7 million book) and in 2012Q3–2013Q2 ($690–730 million, the first four quarters after the book reappears at that size; it was 0 from 2009Q4 to 2012Q2). Then 2014Q1 jumps to 2.08 %.
These are the values in the filings. On a quarter-end basis no rule leaves them out, so a scale built on KeyBank's own card history from those years will see them.</li>
</ul>

<h2>6 · What I got wrong</h2>
<ul>
<li>The first build pointed <code>--mergers</code> at a file that does not exist. It refused before writing anything.</li>
<li>The DelinquencyData column widths, above. That was found here, not by the 675 tests.</li>
</ul>

<h2>7 · What this does not prove</h2>
<ul>
<li><b>One cell, one bank, one quarter.</b> DelinquencyData has 32,800 rows. The rest are assumed to be right because they come from the same code and the same pull, and that is an inference, not something this check ran.
The build's own acceptance test compared KeyBank's 25 product × measure values for 2026Q2 with a separate computation from the raw API data. That proves the code matches the API, not the filing.</li>
<li><b>The page image dates from 5 Sep 2026.</b> It says <i>Last updated 7/30/2026</i>. The XBRL was fetched today and agrees, so no amendment has changed these two lines since then. Other lines were not checked.</li>
<li><b>The width fix was checked on a copy</b> of this build, with the new widths applied. The 12-minute build was not rerun after the code change.</li>
<li><b>Not proved:</b> four-quarter averages, the pack composite, the band, the industry series, the other measures and products, and any peer bank's figure.
The live Delinquency tab is recalculated against Python in the tests (<code>formulas</code>), but none of it is tied to a filing here.</li>
</ul>
"""

html = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>KeyBank Card 90+ Tie-Out</title><style>%s</style></head><body>%s</body></html>" % (CSS, BODY))
(HERE / "TIE-OUT-keybank-card-90plus-2026-10-12.html").write_text(html, encoding="utf-8")
print("written")
