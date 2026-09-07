"""Render the withholding tie-out exhibit to one self-contained HTML file.

Every image is embedded as a data URI, because a note plus a folder of loose
pictures is correct and unusable: the links resolve only on the machine that
wrote them, and nobody forwards that to an auditor.
"""
from __future__ import annotations

import base64
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def img(name: str) -> str:
    data = base64.b64encode((HERE / name).read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


PAGE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Tie-out · withholding estimator · 6 September 2026</title>
<style>
  @page {{ size: Letter; margin: 16mm 14mm; }}
  :root {{
    --ink:#16181b; --soft:#525a64; --faint:#8a919b;
    --rule:#d8d3ca; --hair:#ebe7e0; --paper:#fff;
    --ox:#7a2230; --oxwash:#f8eeee;
    --good:#25644a; --goodwash:#eef4f1;
    --bad:#8c2d1a; --badwash:#fbefe9;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font:400 10.5pt/1.5 "IBM Plex Sans","Segoe UI",system-ui,sans-serif; }}
  .sheet {{ max-width:190mm; margin:0 auto; }}
  h1 {{ font:600 22pt/1.15 "Newsreader",Georgia,serif; margin:0 0 4px;
        letter-spacing:-.01em; }}
  .kicker {{ font:500 8pt/1 "IBM Plex Mono",ui-monospace,monospace;
             letter-spacing:.16em; text-transform:uppercase; color:var(--ox); }}
  .mast {{ border-bottom:2px solid var(--ink); padding-bottom:10px; margin-bottom:16px; }}
  .mast p {{ margin:6px 0 0; color:var(--soft); font-size:10pt; max-width:64ch; }}
  .meta {{ margin-top:9px; font:400 8.5pt/1.5 "IBM Plex Mono",monospace; color:var(--faint); }}
  h2 {{ font:600 9.5pt/1 "IBM Plex Mono",monospace; letter-spacing:.13em;
        text-transform:uppercase; color:var(--soft);
        margin:26px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--rule);
        page-break-after:avoid; }}
  h3 {{ font:500 13pt/1.3 "Newsreader",Georgia,serif; margin:18px 0 6px;
        page-break-after:avoid; }}
  p {{ margin:0 0 9px; }}
  .lead {{ color:var(--soft); }}
  code, .mono {{ font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:.88em; }}
  code {{ background:var(--hair); padding:1px 4px; border-radius:2px; }}
  pre {{ background:#f7f5f1; border:1px solid var(--rule); border-radius:3px;
         padding:9px 11px; overflow-x:auto; font:400 8.5pt/1.45 "IBM Plex Mono",monospace;
         margin:0 0 10px; white-space:pre-wrap; word-break:break-word; }}
  figure {{ margin:12px 0 16px; page-break-inside:avoid; }}
  figure img {{ max-width:100%; max-height:158mm; width:auto; margin:0 auto;
                border:1px solid var(--rule); border-radius:2px; display:block; }}
  figure.wide img {{ width:100%; max-height:none; }}
  figcaption {{ font:400 8.5pt/1.45 "IBM Plex Sans",sans-serif; color:var(--soft);
                margin-top:5px; }}
  .cite {{ display:flex; flex-wrap:wrap; gap:4px 14px; margin:6px 0 0;
           font:400 8pt/1.4 "IBM Plex Mono",monospace; }}
  .cite b {{ color:var(--faint); font-weight:500; display:block;
             text-transform:uppercase; letter-spacing:.08em; font-size:7pt; }}
  table {{ width:100%; border-collapse:collapse; margin:8px 0 14px; font-size:9.5pt; }}
  th {{ text-align:left; font:500 7.5pt/1 "IBM Plex Mono",monospace;
        letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
        padding:0 9px 6px 0; border-bottom:1px solid var(--rule); }}
  td {{ padding:6px 9px 6px 0; border-bottom:1px solid var(--hair); vertical-align:top; }}
  td.r, th.r {{ text-align:right; font-variant-numeric:tabular-nums;
                font-family:"IBM Plex Mono",monospace; }}
  tr:last-child td {{ border-bottom:none; }}
  .verdict {{ border-radius:3px; padding:10px 13px; margin:10px 0 14px;
              page-break-inside:avoid; }}
  .verdict.tied {{ background:var(--goodwash); border:1px solid #b9d3c6; }}
  .verdict.differs {{ background:var(--badwash); border:1px solid #e2b6a5; }}
  .verdict .lbl {{ font:600 8pt/1 "IBM Plex Mono",monospace; letter-spacing:.12em;
                   text-transform:uppercase; display:block; margin-bottom:5px; }}
  .verdict.tied .lbl {{ color:var(--good); }}
  .verdict.differs .lbl {{ color:var(--bad); }}
  .verdict pre {{ background:rgba(255,255,255,.65); margin:6px 0 0; }}
  .pill {{ display:inline-block; font:500 7.5pt/1 "IBM Plex Mono",monospace;
           letter-spacing:.1em; text-transform:uppercase; padding:3px 6px;
           border-radius:2px; vertical-align:2px; margin-left:6px; }}
  .pill.tied {{ background:var(--goodwash); color:var(--good); }}
  .pill.differs {{ background:var(--badwash); color:var(--bad); }}
  ul {{ margin:0 0 10px; padding-left:0; list-style:none; }}
  li {{ position:relative; padding-left:17px; margin-bottom:7px; }}
  li::before {{ content:"—"; position:absolute; left:0; color:var(--faint);
                font-family:"IBM Plex Mono",monospace; }}
  .break {{ page-break-before:always; }}
  svg {{ width:100%; height:auto; display:block; }}
</style></head><body><div class="sheet">

<header class="mast">
  <div class="kicker">SATC · Tie-out · sample of one</div>
  <h1>Does the withholding estimator agree with the IRS?</h1>
  <p>One figure — the federal tax on a single filer with $100,000 of wages for
  2025 — traced from the screen a preparer reads, back to the Internal Revenue
  Service's own published tables. Nothing here is confirmed by SATC's own
  software.</p>
  <div class="meta">
    6 September 2026 · satc_system @ main 70144b9 ·
    engine <span class="mono">src/satc/withholding/engine.py</span>
  </div>
</header>

<h2>How the dots connect</h2>
<p class="lead">Two roads carry the same fact. The left is what the software
does. The right is the IRS's own document, read by hand. They are supposed to
meet.</p>

<figure>
<svg viewBox="0 0 900 340" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, Segoe UI, sans-serif">
  <defs>
    <marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="#525a64"/>
    </marker>
  </defs>
  <text x="196" y="20" font-size="12" font-weight="600" fill="#7a2230" text-anchor="middle">THE PRODUCTION PATH</text>
  <text x="196" y="34" font-size="10" fill="#8a919b" text-anchor="middle">what the software does</text>
  <text x="700" y="20" font-size="12" font-weight="600" fill="#25644a" text-anchor="middle">THE CHECK</text>
  <text x="700" y="34" font-size="10" fill="#8a919b" text-anchor="middle">the IRS's document, read by hand</text>

  <g fill="#fff" stroke="#d8d3ca">
    <rect x="60" y="52"  width="272" height="42" rx="3"/>
    <rect x="60" y="124" width="272" height="42" rx="3"/>
    <rect x="60" y="196" width="272" height="42" rx="3"/>
    <rect x="564" y="52"  width="272" height="42" rx="3"/>
    <rect x="564" y="124" width="272" height="42" rx="3"/>
    <rect x="564" y="196" width="272" height="42" rx="3"/>
  </g>
  <g font-size="11" fill="#16181b">
    <text x="74" y="70">Rev. Proc. 2024-40 copied into</text>
    <text x="74" y="85" font-family="IBM Plex Mono, monospace" font-size="10">configs/crosswalk/federal/2025.yaml</text>
    <text x="74" y="142">engine walks the brackets</text>
    <text x="74" y="157" font-family="IBM Plex Mono, monospace" font-size="10">withholding/engine.py</text>
    <text x="74" y="214">the artifact a preparer opens</text>
    <text x="74" y="229" font-family="IBM Plex Mono, monospace" font-size="10">/withholding screen · audit tape C17</text>

    <text x="578" y="70">irs.gov · Rev. Proc. 2024-40</text>
    <text x="578" y="85" font-family="IBM Plex Mono, monospace" font-size="10">sec. 2.01 Table 3 · sec. 2.15</text>
    <text x="578" y="142">its printed base amount</text>
    <text x="578" y="157" font-family="IBM Plex Mono, monospace" font-size="10">"$5,578.50 plus 22% of the excess"</text>
    <text x="578" y="214">arithmetic done by hand</text>
    <text x="578" y="229" font-family="IBM Plex Mono, monospace" font-size="10">5,578.50 + 22% × (TI − 48,475)</text>
  </g>
  <g stroke="#525a64" stroke-width="1.2" marker-end="url(#a)" fill="none">
    <path d="M196,94 L196,120"/><path d="M196,166 L196,192"/>
    <path d="M700,94 L700,120"/><path d="M700,166 L700,192"/>
    <path d="M332,217 L430,217 L430,268 L448,268"/>
    <path d="M564,217 L466,217 L466,268 L448,268"/>
  </g>
  <g font-size="9" fill="#8a919b">
    <text x="204" y="112">one YAML read</text>
    <text x="204" y="184">Decimal, no rounding</text>
    <text x="708" y="112">page 6, captured</text>
    <text x="708" y="184">pen and paper</text>
  </g>

  <rect x="298" y="256" width="304" height="46" rx="3" fill="#eef4f1" stroke="#b9d3c6"/>
  <text x="450" y="275" font-size="12" font-weight="600" fill="#25644a" text-anchor="middle">$13,614.00 = $13,614.00</text>
  <text x="450" y="292" font-size="10" fill="#25644a" text-anchor="middle">difference 0.00 — on the brackets</text>

  <text x="450" y="322" font-size="10" fill="#8c2d1a" text-anchor="middle" font-weight="600">…and then the right-hand road was walked one step further, to the law enacted after that table was published.</text>
</svg>
<figcaption>Only the right-hand road touches a document SATC does not control. That
is the road that makes this evidence rather than a second opinion from the same
source.</figcaption>
</figure>

<h2>The roster</h2>
<pre>Tied out: 19 of 20 checks
  DIFFERS      1   the 2025 standard deduction is superseded by P.L. 119-21  (link 6)
  TIED        19   18 printed bracket bases + 1 full computed figure
  COULD NOT    0</pre>
<p class="lead">The one that differs is below the ones that agree, because the
nineteen that agree are not what anybody needs to read.</p>

<h2 class="break">Link 1 · The figure, read out of the artifact</h2>
<p>The number being proved is <b>Total tax liability $13,614</b> for the case
below. It was read out of <b>two</b> artifacts a person actually opens — not
from the engine's return value.</p>

<table>
  <tr><th>Artifact</th><th>How the value was read</th><th class="r">Value</th></tr>
  <tr><td>The <b>/withholding</b> screen</td>
      <td>Opened in Chrome at <code>127.0.0.1:5095/withholding</code>, form submitted,
          row <b>Total tax liability</b> in the Result panel</td><td class="r">$13,614</td></tr>
  <tr><td>The <b>audit tape</b> workbook</td>
      <td><code>audit-tape-single-100k-2025.xlsx</code>, sheet
          <b>Withholding Estimate</b>, cell <b>C25</b> (label in A25)</td><td class="r">13614</td></tr>
</table>

<figure class="wide">
  <img src="{img('zoom-ours-screen-tax-rows.jpg')}" alt="The result rows on the withholding screen, with Ordinary income tax ringed">
  <figcaption>The Result panel, enlarged. <b>Ordinary income tax $13,614</b> ringed;
  <b>Total tax liability $13,614</b> beneath it. Read off the screen, not recomputed.</figcaption>
</figure>

<figure>
  <img src="{img('ours-withholding-screen-result.jpg')}" alt="The full withholding screen showing the result panel">
  <figcaption>The same screen in full, so the figure is visible in its context —
  standard deduction $15,000, taxable income $85,000, and the inputs above it.</figcaption>
</figure>

<h2>Link 2 · The call</h2>
<p>Run the app against a scratch store, then post the case. Both blocks are
copy-pastable with the real values in them.</p>
<pre>cd C:/Users/ajish/Documents/Main/Claude/SATC_Prod_Software/SATC/satc_system
SATC_DATA_DIR=/tmp/tieout PYTHONPATH=src .venv/Scripts/python.exe -c "from satc.app.server import create_app; create_app().run(port=5095)"</pre>
<pre>curl -s -X POST http://127.0.0.1:5095/withholding \\
  -d filing_status=single -d tax_year=2025 \\
  -d j0_name=Tie-out+case -d j0_pay_frequency=annual \\
  -d j0_gross_pay_per_period=100000 \\
  -d j0_federal_tax_withheld_per_period=0 \\
  -d j0_retirement_pretax_per_period=0 \\
  -d j0_pay_periods_remaining=1</pre>

<h2>Link 3 · The derivation, so a person can redo it</h2>
<p>Not "then the system computes it". Every step, in order:</p>
<table>
  <tr><th>Step</th><th>What happens</th><th class="r">Running figure</th></tr>
  <tr><td>1</td><td>Annual gross wages, one pay period, nothing pre-tax</td><td class="r">100,000.00</td></tr>
  <tr><td>2</td><td>No other income, no above-the-line adjustments → AGI</td><td class="r">100,000.00</td></tr>
  <tr><td>3</td><td>Subtract the standard deduction for a single filer</td><td class="r">−15,000.00</td></tr>
  <tr><td>4</td><td><b>Taxable income</b></td><td class="r">85,000.00</td></tr>
  <tr><td>5</td><td>85,000 falls in the band "over $48,475, not over $103,350"</td><td class="r">—</td></tr>
  <tr><td>6</td><td>Base for that band</td><td class="r">5,578.50</td></tr>
  <tr><td>7</td><td>22% × (85,000 − 48,475) = 22% × 36,525</td><td class="r">8,035.50</td></tr>
  <tr><td>8</td><td>No capital gains, no SE tax, no NIIT, no credits</td><td class="r">0.00</td></tr>
  <tr><td>9</td><td><b>Total tax liability</b></td><td class="r"><b>13,614.00</b></td></tr>
</table>
<p>All arithmetic is <code>Decimal</code>; the engine never rounds between steps.</p>

<h2 class="break">Link 4 · The independent source</h2>
<p>The Internal Revenue Service publishes the 2025 rate schedules in
<b>Rev. Proc. 2024-40</b>. Anyone can fetch it:</p>
<pre>https://www.irs.gov/pub/irs-drop/rp-24-40.pdf</pre>

<div class="cite">
  <span><b>Document</b> Rev. Proc. 2024-40</span>
  <span><b>Section</b> 2.01 Tax Rate Tables</span>
  <span><b>Table</b> 3 — § 1(j)(2)(C) Unmarried Individuals</span>
  <span><b>Page</b> 6</span>
  <span><b>Row</b> Over $48,475 but not over $103,350</span>
  <span><b>Column</b> The Tax Is</span>
  <span><b>Units</b> whole dollars, not thousands</span>
  <span><b>Fetched</b> 6 Sep 2026</span>
</div>

<figure class="wide">
  <img src="{img('zoom-irs-table3-22pct-row.jpg')}" alt="IRS Table 3, the 22 percent row, ringed in red">
  <figcaption>The row this figure depends on, enlarged and ringed:
  <b>$5,578.50 plus 22% of the excess over $48,475</b>.</figcaption>
</figure>

<figure>
  <img src="{img('source-irs-rp2024-40-p6-rate-schedules.jpg')}" alt="Page 6 of Rev. Proc. 2024-40 in Chrome">
  <figcaption>Page 6 as served by irs.gov, captured in Chrome — the whole of
  Table 3 (Single) and Table 4 (MFS), so the ringed row can be seen in place.
  The page number and table headings are in the same shot as the figures.</figcaption>
</figure>

<p><b>Read twice.</b> Every figure above was taken from the rendered page
<i>and</i> from the same PDF's embedded text layer, extracted with
<code>pypdf</code>. The two readings agree. One apparent disagreement resolved on
inspection and is recorded under <i>what I got wrong</i>.</p>

<h2>Link 5 · The comparison</h2>

<div class="verdict tied">
  <span class="lbl">Verdict · tied</span>
  <pre>ours    (/withholding screen, Result → Total tax liability)        13,614.00
ours    (audit tape .xlsx, sheet "Withholding Estimate", C25)      13,614.00
source  (IRS Rev. Proc. 2024-40 §2.01 Table 3, p.6, by hand)
          5,578.50 + 0.22 × (85,000.00 − 48,475.00)                13,614.00
diff                                                                    0.00</pre>
</div>

<p>The four sameness tests, each checked rather than assumed:</p>
<table>
  <tr><th>Test</th><th>Same?</th><th>How it was checked</th></tr>
  <tr><td>Entity</td><td>yes</td><td>Both sides are a single filer, no dependants — a synthetic case, no client data</td></tr>
  <tr><td>Period</td><td>yes</td><td>Tax year 2025 on both sides; the screen prints "Result — TY2025"</td></tr>
  <tr><td>Basis</td><td>yes</td><td>Federal ordinary income tax before credits and before payroll taxes, on both sides</td></tr>
  <tr><td>Units</td><td>yes</td><td>Whole US dollars on both; the Rev. Proc. tables are not in thousands</td></tr>
</table>

<h2>The bracket structure, all of it</h2>
<p>One figure proves one path through the table. The IRS prints, for every band,
the tax accumulated below it — <code>$5,578.50</code>, <code>$17,651</code>, and
so on. Those printed bases are an independent arithmetic statement about the
whole schedule, so each one can be checked against what SATC's own bracket edges
imply. Eighteen of them, across three filing statuses:</p>

<pre>--- single ---              IRS printed   ours implies    diff
      11,925                   1,192.50      1,192.50     0.00
      48,475                   5,578.50      5,578.50     0.00
     103,350                  17,651.00     17,651.00     0.00
     197,300                  40,199.00     40,199.00     0.00
     250,525                  57,231.00     57,231.00     0.00
     626,350                 188,769.75    188,769.75     0.00
--- married filing jointly ---
      23,850                   2,385.00      2,385.00     0.00
      96,950                  11,157.00     11,157.00     0.00
     206,700                  35,302.00     35,302.00     0.00
     394,600                  80,398.00     80,398.00     0.00
     501,050                 114,462.00    114,462.00     0.00
     751,600                 202,154.50    202,154.50     0.00
--- head of household ---
      17,000                   1,700.00      1,700.00     0.00
      64,850                   7,442.00      7,442.00     0.00
     103,350                  15,912.00     15,912.00     0.00
     197,300                  38,460.00     38,460.00     0.00
     250,500                  55,484.00     55,484.00     0.00
     626,350                 187,031.50    187,031.50     0.00

VERDICT: TIED - all 18 printed bases reproduced exactly</pre>

<p>This is a check that could have failed. A single mistyped bracket edge shifts
every base above it, and the IRS's printed figure would not match.</p>

<h2 class="break">Link 6 · And then the source was followed one step further <span class="pill differs">Differs</span></h2>

<p>Rev. Proc. 2024-40 is the authority for the 2025 <i>inflation adjustments</i>,
published October 2024. It is not the last word on 2025 law. SATC's own
crosswalk file says so, in a note nobody had acted on:</p>

<pre>configs/crosswalk/federal/2025.yaml, line 10

    NOTE: several TCJA provisions were later modified by P.L. 119-21
    (OBBBA, July 2025); reconcile to enacted law before filing TY2025.</pre>

<p><b>Public Law 119-21</b> — the One Big Beautiful Bill Act, signed 4 July 2025
— raised the standard deduction <b>for tax year 2025 itself</b>, not for 2026
onwards. The IRS publishes the enacted figures on a page written specifically for
people adjusting their withholding mid-year:</p>

<div class="cite">
  <span><b>Document</b> irs.gov · Forms &amp; Instructions</span>
  <span><b>Page</b> How to update withholding to account for tax law changes for 2025</span>
  <span><b>Section</b> "An increase in the standard deduction"</span>
  <span><b>Reviewed</b> 28-Jul-2026 (printed on the page)</span>
  <span><b>Fetched</b> 6 Sep 2026</span>
</div>

<figure class="wide">
  <img src="{img('zoom-irs-obbba-single.jpg')}" alt="The three enacted 2025 standard deduction amounts, enlarged and ringed">
  <figcaption>Enlarged. Each line states the enacted figure <b>and the Rev. Proc.
  figure it replaced</b> &mdash; and the one it replaced is the one SATC is still
  using.</figcaption>
</figure>

<figure>
  <img src="{img('source-irs-obbba-2025-standard-deduction.jpg')}" alt="IRS page showing the increased 2025 standard deduction, ringed in red">
  <figcaption>The three enacted amounts, ringed. The IRS states each as an
  increase from the Rev. Proc. figure — <b>$15,750 (up from $15,000)</b> — which
  is precisely the figure SATC is still using. The page's own "Last Reviewed or
  Updated" date is in the same shot.</figcaption>
</figure>

<div class="verdict differs">
  <span class="lbl">Verdict · differs</span>
  <pre>                          ours (crosswalk)   IRS (P.L. 119-21)      diff
single / MFS                     15,000.00           15,750.00   −750.00
married filing jointly           30,000.00           31,500.00 −1,500.00
head of household                22,500.00           23,625.00 −1,125.00</pre>
</div>

<p><b>What it costs on the figure this exhibit set out to prove.</b> The engine's
arithmetic is not at fault — hand it the enacted deduction and it lands on the
IRS schedule to the cent:</p>

<pre>                                    deduction   taxable inc          tax
as the software ships today         15,000.00     85,000.00    13,614.00
with the enacted OBBBA figure       15,750.00     84,250.00    13,449.00
                                                OVERSTATED BY       165.00

hand, from IRS Table 3:  5,578.50 + 22% × (84,250 − 48,475)  =  13,449.00
engine, given the enacted figure                             =  13,449.00
diff                                                                 0.00</pre>

<p>So the estimator would tell this taxpayer to withhold <b>$165 more</b> than
2025 law requires. On a household, the joint figure is $1,500 of deduction — and
the error grows with the marginal rate.</p>

<p><b>Which side is believed:</b> the IRS. A statute enacted in July 2025 governs
tax year 2025 over a revenue procedure published in October 2024. This is not a
close call, and it is not being plugged or rounded away — the crosswalk needs the
enacted figures, and the note in that file needs deleting only once they are in.</p>

<h2>What it found</h2>
<ul>
  <li><b>The estimator overstates 2025 federal tax by $165 on the case above,
  and by more on a joint return.</b> It uses the standard deduction as published
  in October 2024, superseded by law in July 2025. Nothing in the test suite
  could catch this: the tests hand-compute their expected figures from the same
  tables the engine reads, so the code and the tests agree with each other and
  both are wrong.</li>
  <li><b>The file knew.</b> <code>2025.yaml</code> carries a written instruction
  to reconcile to enacted law before filing, and it had not been done. A note in
  a config that nothing enforces is a note that gets read once.</li>
  <li><b>2026 is worse and says so.</b> <code>load_tax_tables(2026)</code>
  returns 2025's tables with the note <i>"Federal tax tables for 2026 are not
  fully published in the crosswalk; using 2025 tables for this estimate."</i>
  Honest, and unusable for a 2026 estimate.</li>
  <li><b>The bracket machinery is sound.</b> Eighteen printed base amounts across
  three filing statuses reproduce exactly, and the engine's arithmetic given a
  correct deduction lands on the IRS schedule to the cent. The defect is one
  constant, not the design.</li>
</ul>

<h2>What I got wrong</h2>
<ul>
  <li><b>I nearly reported a discrepancy that was not one.</b> The text extracted
  from page 5 showed a top-bracket base of <code>$187,031.50</code> where the
  rendered page 6 showed <code>$188,769.75</code>. I read that as the two
  renderings disagreeing. They were different tables — Heads of Households and
  Single, both topping out at $626,350. The wider HOH bands accumulate less tax,
  so the lower figure is right where it sits. Checked before it was written down,
  and recorded because a tie-out that hides its own misreads is worth nothing.</li>
  <li><b>My first framing of this exercise was too narrow.</b> I set out to prove
  the estimator against Rev. Proc. 2024-40 and would have stopped at
  <i>TIED, difference 0</i>. That verdict is true and would have been
  misleading — the revenue procedure is not the same thing as enacted law, and
  the interesting question was one step past the source I had chosen.</li>
</ul>

<h2>What this does not prove</h2>
<ul>
  <li><b>One path through the engine.</b> Wages, standard deduction, one bracket
  band. <b>Not tied to any IRS source:</b> the capital-gains stacking, the
  self-employment tax, the Additional Medicare Tax, the Net Investment Income
  Tax, the safe-harbor calculation, or the per-paycheck W-4 line 4c
  recommendation. Each has a unit test; each of those tests computes its expected
  value from the same constants the engine uses.</li>
  <li><b>Federal only.</b> Ohio and every other state withholding is outside the
  estimator entirely, and most SATC clients file one.</li>
  <li><b>The other constants in the crosswalk.</b> Eighteen bracket bases and
  three standard deductions were checked against the IRS. The Social Security
  wage base, the SE tax rates, the NIIT and Additional Medicare thresholds, and
  the capital-gains breakpoints were <b>not</b>.</li>
  <li><b>The paystub reader.</b> This exhibit typed its inputs. Nothing here
  tests whether a scanned paystub yields the right figures to feed it.</li>
  <li><b>The full OBBBA reconciliation.</b> This found one superseded constant by
  following one note. P.L. 119-21 also created deductions for tips, overtime,
  vehicle loan interest and seniors, raised the SALT cap, and changed the child
  tax credit — <b>none of which the estimator models</b>. The IRS's own page says
  its Tax Withholding Estimator is not updated for most of them either. How much
  that matters has not been assessed.</li>
</ul>

<h2>How to run this yourself</h2>
<p>Every step, with the real values in it. No editing required.</p>
<pre>cd C:/Users/ajish/Documents/Main/Claude/SATC_Prod_Software/SATC/satc_system</pre>
<pre>PYTHONPATH=src .venv/Scripts/python.exe -c "from decimal import Decimal as D; from satc.withholding.engine import estimate; from satc.withholding.models import EstimatorInput; r=estimate(EstimatorInput.from_dict({{'filing_status':'single','tax_year':2025,'paystub':{{'pay_frequency':'annual','taxable_wages_per_period':100000,'pay_periods_remaining':1}}}})); print('deduction',r.breakdown.deduction_used,'| taxable',r.breakdown.taxable_income,'| tax',r.breakdown.total_tax_liability)"</pre>
<p>Then open the IRS table and do the arithmetic by hand:</p>
<pre>https://www.irs.gov/pub/irs-drop/rp-24-40.pdf#page=6
Table 3, row "Over $48,475 but not over $103,350":
    5,578.50 + 0.22 × (taxable income − 48,475)</pre>
<p>And check the deduction the software used against enacted law:</p>
<pre>https://www.irs.gov/forms-pubs/how-to-update-withholding-to-account-for-tax-law-changes-for-2025
section "An increase in the standard deduction"</pre>

<p style="margin-top:26px; padding-top:12px; border-top:1px solid var(--rule);
   font-size:9pt; color:var(--faint);">
Exhibit source and captures:
<span class="mono">docs/tie-out/withholding-2026-09-06/</span>. The case is
synthetic; no client data appears in this document.</p>

</div></body></html>
"""

out = HERE / "TIE-OUT-withholding-2026-09-06.html"
out.write_text(PAGE, encoding="utf-8")
print(f"wrote {out}  ({len(PAGE):,} bytes)")
