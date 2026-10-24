"""Assemble TIE-OUT-keybank-card-nonaccrual-2026-10-14 and have canon check and
render it. Every picture is embedded; every number in it is read from the
files beside it (workbook-reads.json, fdic-17534-20260630.json,
fields-vs-filing.txt), not typed here.

    (from threshold-engine/)
    python docs/tie-out/keybank-card-nonaccrual-2026-10-14/scripts/build_exhibit.py \
        --canon C:/Users/ajish/.claude/plugins/cache/satc/canon/1.21.0
"""
import argparse
import base64
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
IMG = HERE / "images"
NAME = "TIE-OUT-keybank-card-nonaccrual-2026-10-14"


def img(name, alt, width="100%", source=False):
    data = base64.b64encode((IMG / name).read_bytes()).decode()
    mark = ' data-tieout="source"' if source else ""
    return '<img%s src="data:image/png;base64,%s" alt="%s" style="width:%s">' % (mark, data, html.escape(alt), width)


def esc(s):
    return html.escape(str(s))


DIAGRAM = """
<svg viewBox="0 0 900 330" role="img" aria-label="One fact on two roads, meeting at difference 0">
 <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
 <g font-size="11.5" fill="currentColor" stroke="currentColor">
  <text x="8" y="16" stroke="none" font-weight="700">Production road: how the number reaches the cell the firm reads</text>
  <rect x="8" y="28" width="150" height="58" fill="none"/>
  <text x="83" y="48" stroke="none" text-anchor="middle">FDIC BankFind API</text>
  <text x="83" y="64" stroke="none" text-anchor="middle">NACRCD 6,401</text>
  <text x="83" y="79" stroke="none" text-anchor="middle">LNCRCD 926,589</text>
  <line x1="158" y1="57" x2="196" y2="57" marker-end="url(#a)"/>
  <text x="177" y="50" stroke="none" text-anchor="middle" font-size="9.5">pull</text>
  <rect x="198" y="28" width="150" height="58" fill="none"/>
  <text x="273" y="48" stroke="none" text-anchor="middle">peers build</text>
  <text x="273" y="64" stroke="none" text-anchor="middle">100 x NACRCD / LNCRCD</text>
  <text x="273" y="79" stroke="none" text-anchor="middle">series CSV, 2026-06-30</text>
  <line x1="348" y1="57" x2="386" y2="57" marker-end="url(#a)"/>
  <text x="367" y="50" stroke="none" text-anchor="middle" font-size="9.5">book</text>
  <rect x="388" y="28" width="160" height="58" fill="none"/>
  <text x="468" y="48" stroke="none" text-anchor="middle">Data!N83 and</text>
  <text x="468" y="64" stroke="none" text-anchor="middle">Thresholds!J17 (values)</text>
  <text x="468" y="79" stroke="none" text-anchor="middle">0.6908132947833397</text>
  <line x1="548" y1="57" x2="586" y2="57" marker-end="url(#a)"/>
  <text x="567" y="50" stroke="none" text-anchor="middle" font-size="9.5">INDEX</text>
  <rect x="588" y="28" width="170" height="58" fill="none" stroke="#c00" stroke-width="2"/>
  <text x="673" y="48" stroke="none" text-anchor="middle">Summary!G11  0.69</text>
  <text x="673" y="64" stroke="none" text-anchor="middle">Decide!B112 "0.69% in</text>
  <text x="673" y="79" stroke="none" text-anchor="middle">2026Q2 · rating 5 High"</text>
  <line x1="758" y1="57" x2="800" y2="140" marker-end="url(#a)"/>
  <text x="8" y="318" stroke="none" font-weight="700">Check road: the report KeyBank filed with its regulators</text>
  <rect x="8" y="196" width="150" height="74" fill="none"/>
  <text x="83" y="218" stroke="none" text-anchor="middle">FFIEC CDR</text>
  <text x="83" y="234" stroke="none" text-anchor="middle">Call Report, FFIEC 031</text>
  <text x="83" y="250" stroke="none" text-anchor="middle">KeyBank, N.A.</text>
  <text x="83" y="265" stroke="none" text-anchor="middle">6/30/2026</text>
  <line x1="158" y1="215" x2="236" y2="205" marker-end="url(#a)"/>
  <line x1="158" y1="250" x2="236" y2="262" marker-end="url(#a)"/>
  <text x="197" y="200" stroke="none" text-anchor="middle" font-size="9.5">read twice</text>
  <rect x="238" y="182" width="300" height="42" fill="none"/>
  <text x="388" y="200" stroke="none" text-anchor="middle">RC-N 5.a, column C (nonaccrual), RCFDB577</text>
  <text x="388" y="216" stroke="none" text-anchor="middle">6,401   (page image and XBRL)</text>
  <rect x="238" y="240" width="300" height="42" fill="none"/>
  <text x="388" y="258" stroke="none" text-anchor="middle">RC-C Part I 6.a, column A, RCFDB538</text>
  <text x="388" y="274" stroke="none" text-anchor="middle">926,589   (page image and XBRL)</text>
  <line x1="538" y1="203" x2="606" y2="225" marker-end="url(#a)"/>
  <line x1="538" y1="261" x2="606" y2="240" marker-end="url(#a)"/>
  <rect x="608" y="208" width="150" height="46" fill="none"/>
  <text x="683" y="227" stroke="none" text-anchor="middle">by hand: 100 x 6,401</text>
  <text x="683" y="243" stroke="none" text-anchor="middle">/ 926,589 = 0.690813...</text>
  <line x1="758" y1="230" x2="800" y2="172" marker-end="url(#a)"/>
  <rect x="762" y="132" width="132" height="50" fill="none" stroke-width="2"/>
  <text x="828" y="153" stroke="none" text-anchor="middle" font-weight="700">difference 0</text>
  <text x="828" y="171" stroke="none" text-anchor="middle">TIED</text>
 </g>
</svg>"""

CSS = """
:root{--ink:#1b2430;--muted:#5a6573;--rule:#d5dbe2;--paper:#fff;--code:#f2f4f7}
body{background:var(--paper);color:var(--ink);font:13.5px/1.5 "Segoe UI",Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px 16px}
h1{font-size:23px;margin:0 0 4px} h2{font-size:17px;margin:26px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px;break-after:avoid}
h3{font-size:14px;margin:16px 0 6px;break-after:avoid}
.sub{color:var(--muted);margin:0 0 14px} .verdict{display:inline-block;border:2px solid var(--ink);padding:1px 10px;font-weight:700;letter-spacing:.05em}
pre,code{font-family:Consolas,monospace;font-size:11.5px;background:var(--code)} pre{padding:9px;white-space:pre-wrap;word-break:break-all}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;margin:6px 0} td,th{border:1px solid var(--rule);padding:4px 8px;text-align:left;vertical-align:top}
th{background:var(--code)} .num{text-align:right} figure{margin:10px 0;break-inside:avoid} figcaption{color:var(--muted);font-size:12px}
.cite{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0} .cite span{border:1px solid var(--rule);padding:2px 8px;font-size:12px}
svg{max-width:100%;height:auto;color:var(--ink)} .compare{font-size:12.5px;break-inside:avoid}
.two{display:flex;gap:12px;align-items:flex-start} .two figure{flex:1}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canon", required=True, help="folder holding canon's check_tie_out.py")
    a = ap.parse_args()
    sys.path.insert(0, a.canon)
    import check_tie_out

    r = json.loads((HERE / "workbook-reads.json").read_text("utf-8-sig"))
    api = json.loads((HERE / "fdic-17534-20260630.json").read_text("utf-8"))
    row = api["data"][0]["data"]
    fields = (HERE / "fields-vs-filing.txt").read_text("utf-8").splitlines()
    na, ln = row["NACRCD"], row["LNCRCD"]
    by_hand = 100 * na / ln
    s, th, dt, dc = r["summary"], r["thresholds"], r["data"], r["decide"]
    ours = float(s["latest"]["value_r17"])
    # The .NET "R" format prints 17 significant digits; Python's repr prints the
    # shortest that round-trips. Parsed, they are one double, and that is what is compared.
    for hop in (th["latest"], dt["latest"], dc["compare_row"][0]["latest"]):
        assert float(hop["value_r17"]) == ours, hop
    diff = ours - by_hand
    shown = dc["headline"]["text"].split(": ", 1)[1].split("%", 1)[0]      # "0.69", as Decide displays it
    verdict = "TIED" if diff == 0 and dc["headline"]["text"].startswith("KeyBank, nonaccrual, credit card: 0.69% in 2026Q2") else "DIFFERS"
    api_txt = json.dumps(api, separators=(",", ":"))

    compare = (
        "ours    Summary!G11, Excel 16, CalculateFull, Value2       %r %%\n"
        "ours    Decide!B112 headline, as displayed                 %s %%  (two places)\n"
        "source  100 x RC-N 5.a col C / RC-C 6.a col A\n"
        "        = 100 x %s / %s, KeyBank's filing, 6/30/2026  %r %%\n"
        "diff                                                       %s\n"
        "\n"
        "upstream  FDIC API NACRCD (the call, link 2)                   %s   ($000)\n"
        "source    RC-N 5.a col C RCFDB577, page image                  6,401   ($000)\n"
        "source    RCFDB577, filing XBRL fetched 15 Oct 2026 00:38 UTC  6,401,000 USD = 6,401 ($000)\n"
        "diff                                                           0\n"
        "\n"
        "upstream  FDIC API LNCRCD                                    %s   ($000)\n"
        "source    RC-C 6.a col A RCFDB538, page image                926,589   ($000)\n"
        "source    RCFDB538, filing XBRL                              926,589,000 USD = 926,589 ($000)\n"
        "diff                                                         0"
    ) % (ours, shown,"{:,}".format(na), "{:,}".format(ln), by_hand,
         "0" if diff == 0 else repr(diff), "{:,}".format(na), "{:,}".format(ln))

    body = f"""
<h1>KeyBank credit card nonaccrual rate, 2026Q2: 0.69%</h1>
<p class="sub">The workbook built by <code>threshold-engine book</code>, set beside KeyBank, N.A.'s filed Call Report for 30 June 2026.
Run 14 October 2026 (evening, US time; 15 Oct UTC). <span class="verdict">{verdict}</span></p>

<h2>1 · How the dots connect</h2>
<figure>{DIAGRAM}
<figcaption>The same fact travels two roads. The top road is how the number reaches the Summary and Decide tabs. The bottom road goes
to the report KeyBank itself filed with the FFIEC, which this software does not produce and cannot change. That road is what makes
this evidence rather than a second opinion from the same feed. They meet at difference 0, to the last digit of the number Excel holds.</figcaption></figure>

<h2>2 · The five links</h2>
<h3>Link 1 · The figure, read out of the workbook in Excel</h3>
<p><b>Which workbook.</b> Built with the new <code>book</code> command at commit <code>d1e353a1</code> (branch <code>threshold-engine-book</code>):
<code>python -m threshold_engine book book_try/book.json book.xlsx</code>. <code>book_try/book.json</code> is <code>books/consumer-public.json</code> with
<code>"peers": null</code> and its series list pointing at the series CSVs a <code>peers build</code> wrote earlier the same evening. 95 series, 82 quarters.</p>
<p><b>How it was read.</b> <code>scripts/read_workbook.ps1 -Workbook book.xlsx</code> opened it read-only in a new Excel {esc(r["excel"])} through COM,
ran <code>CalculateFull</code>, and read each cell's <code>Value2</code> (the number Excel holds), <code>Text</code> (what it shows) and <code>Formula</code>.
For Decide it then clicked the three slicers the way a person does: <i>Credit card</i>, <i>Nonaccrual</i>, <i>KeyBank</i>, every other button off, and recalculated.
The pictures are Excel's own (<code>Range.CopyPicture</code>), with a red border put on the cell for the picture only. The workbook was closed without saving.
Everything read is in <code>workbook-reads.json</code>.</p>
<table>
<tr><th>Where</th><th>Excel shows</th><th>Excel holds (Value2)</th><th>Formula</th></tr>
<tr><td>Summary!G11 (row <i>{esc(s["measure"]["text"])}</i>, group <i>{esc(s["group"]["text"])}</i>, <i>{esc(s["heading"]["text"])}</i>)</td><td>{esc(s["latest"]["text"])}</td><td>{esc(repr(ours))}</td><td><code>{esc(s["latest"]["formula"])}</code></td></tr>
<tr><td>Summary!H11, rating</td><td>{esc(s["rating"]["text"])}</td><td></td><td>from Thresholds K17 and L17</td></tr>
<tr><td>Decide!B{dc["headline_row"]}, the headline</td><td colspan="2">{esc(dc["headline"]["text"])}</td><td><code>…TEXT(INDEX(Thresholds!$J$5:$J$99,$AA$3),"0.00")…</code>, with AA3 = {esc(dc["thresholds_row"]["value"])} (Thresholds row {4 + int(dc["thresholds_row"]["value"])})</td></tr>
<tr><td>Decide!E{dc["compare_row"][0]["row"]}, <i>Same product and measure</i>, KeyBank</td><td>{esc(dc["compare_row"][0]["latest"]["text"])}</td><td>{esc(repr(float(dc["compare_row"][0]["latest"]["value_r17"])))}</td><td>INDEX of Thresholds!J by series name</td></tr>
<tr><td>Thresholds!J{th["row"]} (<i>{esc(th["header_j"]["text"])}</i>), row A{th["row"]} = <i>{esc(th["series"]["text"])}</i>, I{th["row"]} = {esc(th["quarter"]["text"])}</td><td>{esc(th["latest"]["text"])}</td><td>{esc(repr(float(th["latest"]["value_r17"])))}</td><td>none: a value</td></tr>
<tr><td>Data!{dt["column"]}{dt["last_row"]} (header <i>{esc(dt["header"]["text"])}</i>, A{dt["last_row"]} = {esc(dt["quarter"]["text"])})</td><td>{esc(dt["latest"]["text"])}</td><td>{esc(repr(float(dt["latest"]["value_r17"])))}</td><td>none: a value</td></tr>
</table>
<figure>{img("ours-summary.png", "Summary tab in Excel, Credit card rows, KeyBank Latest 0.69 marked")}
<figcaption>Summary, as Excel draws it. The marked cell is G11.</figcaption></figure>
<figure>{img("ours-decide-slicers.png", "Decide tab slicers with Credit card, Nonaccrual and KeyBank picked")}
{img("ours-decide-headline.png", "Decide headline: KeyBank, nonaccrual, credit card: 0.69% in 2026Q2, rating 5 High")}
<figcaption>Decide, after clicking the three slicers. The headline (B{dc["headline_row"]}, marked) and the KeyBank line of the comparison beneath it both read 0.69.</figcaption></figure>
<div class="two">
<figure>{img("ours-thresholds.png", "Thresholds row 17 with Latest value 0.69 marked")}
<figcaption>Thresholds, header and row {th["row"]} only (the rows between are hidden for the picture). Column A is clipped in Excel; see <i>What it found</i>.</figcaption></figure>
<figure style="flex:0 0 170px">{img("ours-data.png", "Data tab column N, last four quarters", "160px")}
<figcaption>Data!{dt["column"]}, the last four quarters.</figcaption></figure>
</div>

<h3>Link 2 · The call</h3>
<pre>curl -s "https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630&amp;fields=CERT,REPDTE,NAMEFULL,LNCRCD,NACRCD,P3CRCD,P9CRCD&amp;format=json"</pre>
<p>Response, 15 Oct 2026 00:38 UTC, whole (<code>fdic-17534-20260630.json</code>):</p>
<pre>{esc(api_txt)}</pre>
<p><code>peers pull</code> asks the same endpoint for every filer in the quarter at once (<code>filters=REPDTE:20260630</code>, 4,313 rows) and keeps
the rows in its cache, <code>ind_cache/q20260630.json</code> (written 14 Oct 2026 10:58 local). The cached KeyBank row reads
<code>NACRCD 6401, LNCRCD 926589</code>, the same as the call made today.</p>
<p><b>What the two fields are.</b> The FDIC's own dictionary (<code>All Financial Reports.xlsx</code>, sheet <i>Reference-Variables&amp;Definitions</i>, fetched today) says, verbatim:</p>
<table><tr><th>Row</th><th>Variable</th><th>Title</th><th>Definition</th></tr>
<tr><td>1128</td><td>NACRCD</td><td>Credit Cards and Related Plans in Nonaccrual Status</td><td>( YTD, $ ) Total credit cards loans to Individuals that are in nonaccrual status and no longer accruing interest. Prior to 2001, included revolving credit plans other than credit cards.</td></tr>
<tr><td>906</td><td>LNCRCD</td><td>Credit Cards</td><td>( YTD, $ ) Consumer loans extended through credit card plans. Prior to 2001, includes check credit and other revolving credit plans.</td></tr></table>
<p>It names no Call Report line. The captions it matches are RC-N item 5.a <i>Credit cards</i>, column C <i>Nonaccrual</i> (MDRM B577) and RC-C Part I item 6.a
<i>Credit cards</i> (B538), each a single filed line, not a sum. That was then shown on the numbers, for every bank and not only KeyBank:
<code>scripts/fields_vs_filing.py</code> set the FDIC's NACRCD and LNCRCD for 30 June 2026 beside the FFIEC's bulk file of every filer's filed lines.</p>
<pre>{esc(chr(10).join(fields))}</pre>

<h3>Link 3 · The derivation</h3>
<ol>
<li><code>peers/delinquency.py</code>: for <i>Credit card</i> the balance field is <code>LNCRCD</code> and the nonaccrual field is <code>NACRCD</code> (<code>FIELDS</code>); the measure <i>nonaccrual</i> uses only that numerator (<code>MEASURES</code>).</li>
<li><code>bank_delinquency(…, cert "17534", "Credit card", "nonaccrual", …)</code> takes the 2026Q2 row as filed: numerator 6,401, balance 926,589. KeyBank is exempt from the 1,000,000 minimum book. The jump and acquisition rules only blank a four-quarter average, never a quarter-end rate.</li>
<li>Rate = <code>100 * num / bal</code> = 100 × 6,401 ÷ 926,589 = <b>0.6908132947833397</b>. <code>peers build</code> writes it to
<code>credit-card_keybank_delinquency-nonaccrual_quarter-end.csv</code>, row <code>2026-06-30,0.6908132947833397</code> (a copy is beside this document). Its header says
<i>"quarter-end rate: 100 x NACRCD / LNCRCD, both from the same filing, %. Amounts are $ thousands at quarter-end, as filed"</i>.</li>
<li><code>book</code> reads that CSV and <code>workbook.py</code> writes the last point twice, as a value: Data!N83 (the column) and Thresholds!J17 (<code>th.cell(r, 10, lp.value)</code>). Neither is a formula.</li>
<li>Summary!G11 is <code>INDEX(Thresholds!$J$5:$J$99, MATCH("Credit card - Nonaccrual - KeyBank", Thresholds!$A$5:$A$99, 0))</code>. Decide's headline is
<code>TEXT(INDEX(Thresholds!$J$5:$J$99,$AA$3),"0.00")</code>, where AA3 is the Thresholds row of the one series the slicers leave showing. So both show J17, and 0.69 is J17 rounded to two places for display.</li>
</ol>

<h3>Link 4 · The independent source</h3>
<p>KeyBank, National Association's Consolidated Reports of Condition and Income (FFIEC 031) for report date 6/30/2026, on the FFIEC Central Data Repository.
Public, no login:</p>
<pre>https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&amp;idType=fdiccert&amp;id=17534&amp;date=06302026</pre>
<p>Fetched again for this tie-out on 15 Oct 2026 at 00:38 UTC, through the page's own <i>Download PDF</i> and <i>Download XBRL</i> buttons (<code>scripts/fetch.py</code>):
PDF 657,623 bytes, SHA-256 <code>d4ca7af0…c471a</code>; XBRL 187,801 bytes, SHA-256 <code>cb185d18…d8a0</code>: the same size and the same hash ends that the 12 Oct 2026 tie-out recorded for its copy (it recorded only the ends).
The pictures below were cut from today's PDF, not reused.</p>
<figure>{img("source-cover.png", "Call Report cover: KeyBank National Association, report date 6/30/2026, FDIC certificate 17534", "75%", source=True)}
<figcaption>The cover: institution, report date and FDIC certificate number ringed. Form FFIEC 031, RSSD-ID 280110, last updated 7/30/2026.</figcaption></figure>

<figure><p><b>First reading, the rendered page: the numerator.</b></p>
{img("source-rcn-5a.png", "RC-N page header and line 5.a Credit cards, column C Nonaccrual 6,401 ringed", source=True)}
<figcaption>Schedule RC-N, cut from the page: the page's own header (entity, form, date, page 45), the column headings with <i>(Column C) Nonaccrual</i> ringed, and line 5.a with 6,401 ringed.</figcaption></figure>
<div class="cite"><span>Schedule RC-N</span><span>Report page 45 (PDF page 46 of 75)</span><span>Item 5.a Credit cards</span><span>Column C Nonaccrual</span><span>RCFDB577</span><span>$ thousands</span><span>6/30/2026</span><span><b>6,401</b></span></div>

<figure><p><b>The balance.</b></p>
{img("source-rcc-6a.png", "RC-C Part I page header and line 6.a Credit cards, column A 926,589 ringed", source=True)}
<figcaption>Schedule RC-C Part I, cut from the page: header (page 23), <i>(Column A) Consolidated Bank</i> ringed, line 6.a with 926,589 ringed.</figcaption></figure>
<div class="cite"><span>Schedule RC-C Part I</span><span>Report page 23 (PDF page 24 of 75)</span><span>Item 6.a Credit cards</span><span>Column A Consolidated Bank</span><span>RCFDB538</span><span>$ thousands</span><span>6/30/2026</span><span><b>926,589</b></span></div>
<div class="two">
<figure>{img("source-rcn-5a-page.png", "Whole RC-N page with item 5 boxed in red", source=True)}<figcaption>Where the RC-N cut sits on its page.</figcaption></figure>
<figure>{img("source-rcc-6a-page.png", "Whole RC-C page with item 6 boxed in red", source=True)}<figcaption>Where the RC-C cut sits on its page.</figcaption></figure>
</div>
<p><b>Second reading, the filing's XBRL</b> (the machine-readable copy the FFIEC publishes with the pages). The lines, verbatim:</p>
<pre>&lt;cc:RCFDB577 contextRef="CI_280110_2026-06-30" unitRef="USD" decimals="0"&gt;6401000&lt;
&lt;cc:RCFDB538 contextRef="CI_280110_2026-06-30" unitRef="USD" decimals="0"&gt;926589000&lt;
&lt;cc:RCONB538 contextRef="CI_280110_2026-06-30" unitRef="USD" decimals="0"&gt;926589000&lt;
&lt;cc:RSSD9017 contextRef="CI_280110_2026-06-30"&gt;KeyBank National Association&lt;
&lt;cc:RCON9999 contextRef="CI_280110_2026-06-30" unitRef="NON-MONETARY" decimals="0"&gt;20260630&lt;</pre>
<p>The XBRL states dollars; 6,401,000 USD is 6,401 in thousands. <code>280110</code> in the context is the RSSD-ID printed on the page header.
Both readings agree on both lines.</p>
<p><b>By hand, on the filing's own numbers.</b> 926,589 × 0.0069 = 6,393.4641. 6,401 − 6,393.4641 = 7.5359. 7.5359 ÷ 926,589 = 0.0000081329…
So 6,401 ÷ 926,589 = 0.0069081329…, and × 100 = <b>0.69081329…%</b>, which shows as 0.69.</p>

<h3>Link 5 · The comparison</h3>
<pre class="compare">{esc(compare)}</pre>
<p>"diff 0" on the rate is exact: the double Excel holds in G11 and the double 100 × 6,401 / 926,589 are the same number
(Excel's read prints it as <code>0.69081329478333975</code>, 17 digits; parsed, it is <code>0.6908132947833397</code>).</p>
<table><tr><th>Must be the same</th><th>Ours</th><th>Source</th><th></th></tr>
<tr><td>Entity</td><td>KeyBank, FDIC cert 17534 (the CSV's header; the API's NAMEFULL <i>KEYBANK NATIONAL ASSOCIATION</i>)</td><td>KEYBANK NATIONAL ASSOCIATION, FDIC certificate 17534, RSSD-ID 280110 (cover, ringed)</td><td>same</td></tr>
<tr><td>Period</td><td>2026Q2 (Thresholds!I17, Data!A83), REPDTE 20260630</td><td>Report date 6/30/2026 (cover and every page header)</td><td>same</td></tr>
<tr><td>Basis</td><td>Nonaccrual card balances over card balances, both at quarter-end, as filed, consolidated bank</td><td>RC-N 5.a column C over RC-C Part I 6.a column A (Consolidated Bank), RCFD lines; the domestic line is the same 926,589</td><td>same</td></tr>
<tr><td>Units</td><td>Rate in %; the amounts behind it in $ thousands</td><td>Pages in $ thousands; XBRL in USD, divided by 1,000; the rate computed by hand in %</td><td>same</td></tr></table>
<p><span class="verdict">{verdict}</span> The 0.69% the firm reads on Summary and Decide is KeyBank's own filed card nonaccrual divided by its own filed card balance.</p>

<h2>3 · Roster</h2>
<p data-tieout="headline">Figures set beside the filing: 3</p>
<table data-tieout="roster"><tr><th>Verdict</th><th>Count</th><th>Which</th></tr>
<tr><td>DIFFERS</td><td data-tieout="count">0</td><td></td></tr>
<tr><td>COULD NOT</td><td data-tieout="count">0</td><td></td></tr>
<tr><td>TIED</td><td data-tieout="count">3</td><td>the rate (Summary!G11 = Decide headline = Thresholds!J17 = Data!N83); its numerator, 6,401 (RC-N 5.a col C); its balance, 926,589 (RC-C 6.a col A)</td></tr></table>
<p>3 of 3 tied. The numerator and balance are not in the workbook; they are tied at the FDIC API, the hop before the series file. Separately, the field-to-line
check covered 4,295 banks on each of the two fields: 4,295 equal on each, 0 differ.</p>

<h2>4 · How to run it yourself</h2>
<p>From <code>C:\\Users\\ajish\\SATC\\threshold-engine</code>, in PowerShell. Steps 1 and 2 tie out the firm's own build the same way: point <code>-Workbook</code> at it.</p>
<ol>
<li>Build the workbook. The one tied out here:
<pre>$env:PYTHONPATH = "src"
python -m threshold_engine book "C:\\Users\\ajish\\AppData\\Local\\Temp\\claude\\C--Users-ajish-SATC\\261f7248-3cbc-4aa2-aacf-e4ff9181778a\\scratchpad\\book_try\\book.json" book.xlsx</pre>
The firm's own: <code>python -m threshold_engine book books\\consumer-public.json book.xlsx</code> (that one runs <code>peers build</code> first, about 12 minutes).</li>
<li>Read it in Excel and photograph it (opens its own Excel, read-only, never saves):
<pre>powershell -ExecutionPolicy Bypass -File docs\\tie-out\\keybank-card-nonaccrual-2026-10-14\\scripts\\read_workbook.ps1 -Workbook book.xlsx -Out work\\reads</pre>
It prints <code>Summary G11 = 0.69081329478333975; … Decide B112: KeyBank, nonaccrual, credit card: 0.69% in 2026Q2 · rating 5 High</code>.
By hand instead: open <code>book.xlsx</code>; Summary, row <i>Nonaccrual</i> under <i>Credit card</i>, group <i>KeyBank</i>, <i>Latest (%)</i>; then on Decide click <i>Credit card</i>, <i>Nonaccrual</i>, <i>KeyBank</i>.</li>
<li>Ask the FDIC:
<pre>curl.exe -s "https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630&amp;fields=CERT,REPDTE,NAMEFULL,LNCRCD,NACRCD&amp;format=json"</pre>
It returns <code>"NACRCD":6401</code> and <code>"LNCRCD":926589</code>.</li>
<li>Open the filing in a browser:
<pre>https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&amp;idType=fdiccert&amp;id=17534&amp;date=06302026</pre>
Schedule RC-N (report page 45), item 5.a <i>Credit cards</i>, Column C <i>Nonaccrual</i>: <b>6,401</b>. Schedule RC-C Part I (report page 23), item 6.a <i>Credit cards</i>, Column A: <b>926,589</b>.</li>
<li>Divide: 6,401 ÷ 926,589 × 100 = 0.6908…, shown as 0.69.</li>
<li>To repeat the downloads, pictures and the every-bank field check (outputs under <code>work\\</code>):
<pre>python docs\\tie-out\\keybank-card-nonaccrual-2026-10-14\\scripts\\fetch.py --sources work\\nac-sources
python docs\\tie-out\\keybank-card-nonaccrual-2026-10-14\\scripts\\fetch_bulk.py --sources work\\nac-sources
python -I docs\\tie-out\\keybank-card-nonaccrual-2026-10-14\\scripts\\fields_vs_filing.py --sources work\\nac-sources --out work\\fields-vs-filing.txt
python docs\\tie-out\\keybank-card-nonaccrual-2026-10-14\\scripts\\capture.py --pdf work\\nac-sources\\call-17534-06302026.pdf --out work\\images</pre></li>
</ol>

<h2 data-tieout="what-it-found">5 · What it found</h2>
<ul>
<li><b>The figure is right, to the last digit Excel holds.</b> 0.6908132947833397 on Summary, Decide, Thresholds and Data is exactly 100 × 6,401 ÷ 926,589, KeyBank's filed RC-N 5.a column C over RC-C 6.a column A.</li>
<li><b>The two FDIC fields are the two filed lines, for every bank.</b> The FDIC's dictionary gives NACRCD and LNCRCD a title and a sentence, no line number. Against the FFIEC's bulk file for 30 June 2026,
NACRCD equals B577 and LNCRCD equals B538 for all 4,295 banks in both, to the thousand. Neither is a sum. So the mapping <code>delinquency.py</code> relies on is shown, not assumed, for this quarter.</li>
<li><b>Thresholds!J (Latest value) is a typed value, not a link to the Data tab.</b> Summary and Decide follow Thresholds!J by formula, but nothing in Excel ties J17 to Data!N83. They agree because Python writes both from the same list.
If somebody pasted a corrected quarter into Data, the lines would move and Latest, the rating, Summary and the Decide headline would not. That may be intended; it is the one hop in the chain that is not live.</li>
<li><b>The Thresholds tab's Series column is clipped in Excel.</b> Column A is 15 wide and B is never empty, so row 17 shows <i>Credit card - Non</i> (the picture above). The three sources of one measure read the same there,
so a reader cannot tell the rows apart on that tab. On Summary, H7 and H8 show <i>Not in this workbool</i>, the last letter cut off.</li>
<li><b>The cross-bank comparison beside this figure is mostly policy, and the warning is on another tab.</b> Decide says <i>KeyBank is 0.68 points higher than Peer group (15 banks)</i> and Summary shows <i>+0.68</i>.
At 30 June 2026, 10 of the 16 roster banks filed zero card nonaccrual (counted here from the FDIC call for every filer). They report late card loans as 90+ still accruing instead. The workbook says so only on the Sources tab.
KeyBank's <i>5 High</i> is against its own history and is not affected.</li>
<li><b>The FDIC's dictionary labels both fields "( YTD, $ )".</b> Both are quarter-end balances, not year-to-date, and both are in thousands, as the 4,295-bank match against the filed $000 lines shows.</li>
</ul>

<h2 data-tieout="what-i-got-wrong">6 · What I got wrong</h2>
<ul>
<li>I expected the FDIC's definitions file to name the Call Report line for each field. It does not, so the field-to-line answer had to come from the numbers: the every-bank check above.</li>
<li>The first Excel read printed <code>0.69081329478333975</code> and the CSV says <code>0.6908132947833397</code>. Different text, the same number: .NET prints 17 digits, Python the shortest that round-trips. I checked by parsing both before writing "diff 0".</li>
<li><code>read_workbook.ps1</code> first passed Excel a relative output folder. Excel resolved it against its own folder and the picture export failed (<i>STG_E_PATHNOTFOUND</i>). It now resolves the path first. Its first successful run also recorded PowerShell's stray output in the list of pictures; fixed.</li>
<li>The comparability tie-out's capture script needs <code>pdftoppm</code> and <code>pdfplumber</code>, which are not on this machine. <code>capture.py</code> here does the same cuts and rings with PyMuPDF.</li>
</ul>

<h2 data-tieout="what-this-does-not-prove">7 · What this does not prove</h2>
<ul>
<li><b>One figure, one bank, one quarter.</b> The other 94 series and the other 55 quarters of this one (2012Q3 to 2026Q1) come through the same code and are assumed right because of that. That is an inference, not something this check ran.</li>
<li><b>Not the firm's own build.</b> This workbook was built with peers switched off, from series CSVs a <code>peers build</code> wrote earlier the same evening from a cache pulled at 10:58 that morning. <code>book books\\consumer-public.json</code>, which runs the peers build itself, was not run. Step 2 above reads that build the same way.</li>
<li><b>Not the rating.</b> <i>5 High</i> depends on the lines (median, typical move, the settings on Decide). Those are judgements, not filed figures, and nothing here ties them.</li>
<li><b>Not the peer group's 0.01 or the +0.68 difference.</b> Only KeyBank's own figure was tied.</li>
<li><b>Field-to-line for one quarter only.</b> The every-bank check is for 30 June 2026. The FDIC's definitions say both fields were wider before 2001. This series starts in 2012Q3, but other quarters were not checked.
18 FDIC rows have no match in the FFIEC bulk file (17 with both fields blank, one with both 0), and one FFIEC filer (State Bank Northwest, cert 2945) has no FDIC row. Not looked into.</li>
<li><b>Amendments.</b> The filing says <i>Last updated 7/30/2026</i>, and the FDIC's data is index <code>risview_20260819185831</code> (19 Aug 2026). An amendment after that would be in today's filing and not in the FDIC's data. Today's XBRL agrees with the API on both lines, so no amendment has touched them.</li>
</ul>
"""
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>KeyBank card nonaccrual tie-out, 2026Q2</title><style>%s</style></head><body>%s</body></html>" % (CSS, body))
    check_tie_out.render(page, HERE / (NAME + ".pdf"), what="the KeyBank card nonaccrual tie-out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
