"""EVIDENCE.html: one document, every chart embedded, of what was tested for
the consumer book's early-warning dimension, what was kept, and why the rest
was set aside. Built from the same scripts and data as the analysis pages
(build.py, focus.py, comp.py, mock.py) so every figure is rerun here."""
import datetime as dt
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]
src = (HERE / "mock.py").read_text(encoding="utf-8").split('\nt = (HERE / "template.html")')[0]
g = {"__file__": str(HERE / "mock.py")}
exec(compile(src, "mock.py", "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})

T = (HERE / "template.html").read_text(encoding="utf-8")
STYLE = T[:T.index("<main>")].replace("<title>Refreshed FICO Evidence</title>", "<title>Early Warning Evidence</title>")
EXTRA = """<style>
.row { background: var(--panel); border: 1px solid var(--grid); border-radius: 4px; padding: 14px 16px; display: grid; gap: 8px; }
.rowhead { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-bottom: 3px solid var(--key); padding-bottom: 8px; }
.pm { font-weight: 700; font-size: 16px; } .src { font-size: 12px; color: var(--muted); }
.now { text-align: right; } .now .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.now .val { font: 500 13px var(--f-mono); }
.chip { display: inline-block; padding: 3px 10px; border-radius: 3px; font-weight: 700; font-size: 13px; background: var(--grid); color: var(--ink); }
.chip.r1, .sw2.r1 { background: var(--z1); } .chip.r2, .sw2.r2 { background: var(--z2); } .chip.r3, .sw2.r3 { background: var(--z3); }
.chip.r4, .sw2.r4 { background: var(--z4); } .chip.r5, .sw2.r5 { background: var(--z5); }
.settings { font-size: 12px; background: var(--bg); padding: 6px 8px; border: 1px solid var(--grid); }
.warn { font-size: 12px; color: var(--c-card); }
.grid2 { display: grid; grid-template-columns: minmax(0, 2.2fr) minmax(0, 1fr); gap: 14px; align-items: start; }
@media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } }
table.begins { border-collapse: collapse; font-size: 12px; width: 100%; } table.begins th { text-align: left; color: var(--muted); font-weight: 600; }
table.begins td, table.begins th { padding: 4px 6px; border-bottom: 1px solid var(--grid); } td.num { text-align: right; font-family: var(--f-mono); }
.sw2 { display: inline-block; width: 10px; height: 10px; margin-right: 6px; border: 1px solid var(--grid); }
.ctx .rowhead { border-bottom-color: var(--muted); }
h2.grp { font-size: 15px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: 8px 0 0; }
.part { border-top: 4px solid var(--key); padding-top: 10px; margin-top: 10px; }
.part h1 { font-size: 22px; }
table.dec { border-collapse: collapse; font-size: 13px; width: 100%; } table.dec th, table.dec td { text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid var(--grid); }
.kept { color: var(--c-he); font-weight: 700; } .aside { color: var(--c-card); font-weight: 700; } .ctxk { color: var(--c-mtg); font-weight: 700; }
@media print { .box, .row, .panel { break-inside: avoid; } details.raw { break-inside: avoid; } }
</style>"""

ZONES = ('<div class="zones"><span style="background:var(--z1)">1 Low</span><span style="background:var(--z2)">2 Moderate-Low</span>'
         '<span style="background:var(--z3)">3 Moderate</span><span style="background:var(--z4)">4 Moderate-High</span>'
         '<span style="background:var(--z5)">5 High</span></div>')


def part(title, lede, body):
    return '<section class="part"><h1>%s</h1><p class="lede">%s</p></section>%s' % (title, lede, body)


DECISION = [
    ("30+ to charge-off (card, other consumer): industry, peer group, KeyBank", "kept", "Rated by level",
     "Smooth, moves with every source, and rates on the book's lines. The inherent-risk reading: how much delinquency turns into loss.", "A1"),
    ("Gap to peers and gap to industry on 30+ to charge-off (card, other consumer)", "kept", "Rated by level, no floor at zero",
     "The relative reading: when KeyBank turns more of its delinquency into loss than peers do. Common forces cancel out.", "A1"),
    ("Share of card accounts paying only the minimum (large banks)", "kept", "Rated by level",
     "Moves with 30&ndash;89 and about a year ahead of charge-offs; it carries what stretched utilization carries (0.92).", "A3"),
    ("Mortgage: rate on nonaccrual rather than charge-offs", "kept", "Lines on the existing measure",
     "Mortgage charge-offs are near zero since 2014 and the industry's lines are refused; nonaccrual still separates quarters and leaves out government-guaranteed 90+.", "A4"),
    ("Card origination score; new accounts under 660; banks easing standards", "ctx", "Shown, not rated",
     "They come 2 to 3 years before card losses, but they are lending policy, closer to an economic indicator; Book 2's territory.", "A5"),
    ("Other consumer 30&ndash;89 as a mortgage signal", "ctx", "Shown, not rated",
     "Comes about 3 quarters before mortgage 90+, but mortgage's own 30&ndash;89 turns at the same time: it confirms, it does not lead.", "A6"),
    ("Refreshed FICO (the weakest tenth's score; KeyCorp's share under 660)", "aside", "Set aside",
     "Moves in the same quarter as 30&ndash;89: its year's lead on charge-offs is only the time delinquency takes to become a loss. Adds nothing 30&ndash;89 does not show.", "B1"),
    ("Card balances under 660 as a rating", "aside", "Kept as a peer comparison only",
     "Orders banks only roughly against losses (0.55 across five banks); mix and charge-off practice move the loss rate as much.", "B2"),
    ("Purchase volume by accounts under 660", "aside", "Set aside",
     "Falls in the same quarter delinquency rises (&minus;0.7 to &minus;0.85): a reaction, and purchases, not balances.", "B3"),
    ("Mortgage origination terms (DTI, LTV, score) and current LTV", "aside", "Set aside",
     "DTI moves with rates and refinancing; LTV and score only match through 2005&ndash;2010; a large equity cushion is why high DTI makes no foreclosures now. Economic data, Book 2.", "B4"),
    ("Roll steps 1 and 2 on their own (30&ndash;89 to 90+; 90+ to charge-off)", "aside", "Watch only",
     "Step 2 is mechanical (180 and 120 days) and matches across sources; step 1 is where cures differ, which the bank's own cohort data measures far better.", "A2"),
]
CLS = {"kept": ("kept", "Kept"), "aside": ("aside", "Set aside"), "ctx": ("ctxk", "Context")}
dec_rows = "".join('<tr><td>%s</td><td class="%s">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (m, CLS[k][0], CLS[k][1], how, why, sec) for m, k, how, why, sec in DECISION)
SUMMARY_TABLE = ('<section class="box"><h2>The decision, measure by measure</h2>'
                 '<table class="dec"><tr><th>Measure</th><th>Outcome</th><th>How</th><th>Why</th><th>Section</th></tr>%s</table>'
                 '<p class="cap">Every &ldquo;why&rdquo; is drawn in the section named, from public data, so a reader can disagree with '
                 'the chart rather than the sentence. The settings used throughout are the book&rsquo;s agreed ones (width 0.5, '
                 'Moderate-Low 1.0, z 2.5) unless a row says the Check refused them.</p></section>' % dec_rows)

def panel_html(t_):
    """A KeyCorp product panel, as build.py lays it out on its own page."""
    title, chart, bchart, verdict, first, last_q, before = t_
    extra = (' The dashed gray line before 2020 is KeyCorp&rsquo;s &ldquo;Residential, prime&rdquo; class, mortgage and home '
             'equity together, as it reported them then.') if before else ""
    return ('<section class="panel"><h3><span class="sw" style="background:%s"></span>%s</h3>'
            '<div class="chart">%s</div><div class="chart small">%s</div>'
            '<p class="cap">Share of scored balances with a refreshed FICO under 660, %s to %s (top; shading is the five rating '
            'zones the book&rsquo;s method draws from this history at the agreed settings); scored balance (bottom).%s</p>'
            '<p class="verdict">%s</p></section>' % (COL[title], title, chart, bchart, first, last_q, extra, verdict))


waterfall_html = "".join('<div class="wfc"><h3>%s</h3><div class="chart">%s</div><p class="cap">%.2f%% to %.2f%% under 660; '
                         'scored balance $%.1fbn to $%.1fbn.</p></div>' % (ti, sv, v[0], v[4], a0, a1) for ti, sv, v, a0, a1 in WF)
KEYCORP = ('<section class="box"><h2>KeyCorp, refreshed FICO by product, from its own 10-Qs and 10-Ks</h2>'
           '<p class="cap">2018Q2 to 2026Q2 from 33 filings (2021Q1 read from the printed table: that filing has no tagged data). '
           'Share of scored balances with a refreshed score under 660, with the rating zones the book&rsquo;s method draws from each '
           'history, and the scored balance beneath.</p>%s%s'
           '<h3>Why KeyCorp&rsquo;s share under 660 rose: the waterfall</h3>'
           '<p class="cap">Since 2020 each bank&rsquo;s FICO table is split by the year the loans were made, which separates new loans, '
           'run-off and mix, and the same loans&rsquo; scores moving. KeyCorp, end-2023 to mid-2026.</p>%s</section>'
           % (ZONES, "".join(panel_html(t_) for t_ in panels), waterfall_html))
SCORES = ('<section class="box"><h2>Large-bank card and mortgage scores (Philadelphia Fed), as a ruler and over time</h2>'
          '<p class="cap">Read the ruler: line up every account from lowest score to highest; the 10th percentile is the score one in '
          'ten accounts fall at or below, the 25th one in four, the median half. Where a dot sits in the red zone, at least that share '
          'scores under 660.</p><div class="chart">%s</div>'
          '<h3>Card accounts, current score percentiles, and industry card net charge-offs</h3><div class="chart">%s</div><div class="chart">%s</div>'
          '<h3>First-lien mortgage accounts, current score percentiles, and industry mortgage net charge-offs</h3>'
          '<div class="chart">%s</div><div class="chart">%s</div>'
          '<p class="cap">Card: refused at z 2.5 at every percentile; nothing since 2012 is far enough from normal. Mortgage: the 10th '
          'percentile rose from 555 to 697 and never fell back, so lines from it rate a trend, not a cycle.</p></section>'
          % (RULER, phil, nco, mtg, mnco))

A = (part("A. What was kept, and the evidence for it",
          "Each measure here is in the book, or shown beside its ratings. The charts are the test.", "")
     + '<h2 class="grp">A1 &middot; 30+ to charge-off, and the gaps to peers and industry</h2>' + RATE + ROLLS + WIN
     + '<h2 class="grp">A2 &middot; The roll steps, movement and divergence</h2>' + MOVE + DIV
     + '<h2 class="grp">A3 &middot; Borrower strain: paying only the minimum</h2>' + STRAIN + MINPAY_NOTE
     + '<h2 class="grp">A4 &middot; Mortgage on delinquency</h2>' + MDQ
     + '<h2 class="grp">A5 &middot; Underwriting and origination quality, as context</h2>' + CARD_ORIG + UW + SHIFT
     + '<h2 class="grp">A6 &middot; Across products</h2>' + CROSS)
B = (part("B. What was set aside, and the evidence for that",
          "Each of these was tested the same way. The charts show why it adds nothing the kept measures do not, or measures something else.", "")
     + '<h2 class="grp">B1 &middot; Refreshed FICO</h2>' + CHANGE + LAG + STACK + EVAL + EVAL2 + KEYCORP + COMP + SCORES
     + '<h2 class="grp">B2 &middot; Card balances under 660 as a rating</h2>' + U660S
     + '<h2 class="grp">B3 &middot; Purchase volume by score</h2>' + PVS
     + '<h2 class="grp">B4 &middot; Mortgage origination terms and current LTV</h2>' + ORIG + LITERAL + MORT + EQUITY)
C = (part("C. The kept measures, as they sit in the book",
          "Each row is laid out as a row on Decide: what is rated, the history its lines come from, the settings, the rating "
          "now, the chart with its zones, and where each rating begins. Built into the book on 18 Oct 2026.", "")
     + "".join('<h2 class="grp">%s</h2>%s' % (gname, body) for gname, body in MEAS)
     + '<h2 class="grp">Context, shown beside the ratings</h2>' + CTX)

DATA_ROWS = [
    ("FDIC Call Reports, every filer, 2006Q1&ndash;2026Q2", "the book&rsquo;s cache (<code>peers pull</code>); the series files under <code>docs/walkthrough-book/out/series</code>",
     "charge-offs, delinquency, balances; 30+ to charge-off; roll steps", "https://banks.data.fdic.gov/docs/"),
    ("Philadelphia Fed, Large Bank Credit Card and Mortgage Data, 2012Q3&ndash;2026Q2", "<code>data/philly/26Q2-*.csv</code>",
     "scores, minimum payments, utilization, originations, mortgage DTI/LTV", "https://www.philadelphiafed.org/surveys-and-data/large-bank-credit-card-and-mortgage-data"),
    ("FRED copies of the same score series", "<code>data/RCC*.csv</code>, <code>data/RCM*.csv</code>", "a second reading; 56 of 56 quarters agree", "https://fred.stlouisfed.org/series/RCCCBSCOREPCT10"),
    ("Federal Reserve Senior Loan Officer Opinion Survey, 1996&ndash;2026", "<code>data/sloos/DRTSCLCC.csv</code>", "banks tightening or easing card standards", "https://fred.stlouisfed.org/series/DRTSCLCC"),
    ("SEC 10-Q and 10-K XBRL, 11 holding companies, 2019Q4&ndash;2026Q2", "<code>data/peerfico/peers.json</code> (from <code>peerfico_pull.py</code>, <code>bands.py</code>, <code>peers.py</code>); <code>data/keyhist/</code>",
     "each bank&rsquo;s refreshed FICO bands by class; KeyCorp back to 2018", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000091576&type=10-Q"),
    ("FHFA National Mortgage Database aggregate statistics, 1998&ndash;2026", "<code>data/nmdb/nmdb.json</code>, <code>mtm.json</code>",
     "mortgage terms at origination; current LTV of the outstanding book", "https://www.fhfa.gov/data/dashboard/nmdb-aggregate-statistics"),
]
D = (part("D. Data, scripts and how to rerun", "Every chart above is drawn by the scripts in this folder from the data beside them.", "")
     + '<section class="box"><h2>Sources</h2><table class="dec"><tr><th>Source</th><th>In this record</th><th>Used for</th><th>Where</th></tr>'
     + "".join('<tr><td>%s</td><td>%s</td><td>%s</td><td><a href="%s">%s</a></td></tr>' % (a, b_, c_, u, u.split("/")[2]) for a, b_, c_, u in DATA_ROWS)
     + '</table></section>'
     + '<section class="box"><h2>Rerun</h2><p class="cap">From <code>threshold-engine</code>, after the book has been built (its series '
       'files are read for the Call Report measures):</p>'
       '<pre style="font:12px var(--f-mono);overflow-x:auto">python docs/early-warning-2026-10/record/evidence.py\n'
       '# the derived data, when the caches are to hand:\n'
       'python docs/early-warning-2026-10/record/rolls.py CACHE config/peers.json docs/early-warning-2026-10/record/data/rolls/rolls.json\n'
       'python docs/early-warning-2026-10/record/fdic_numbers.py CACHE config/peers.json docs/early-warning-2026-10/record/data/rolls/numbers.json\n'
       'python docs/early-warning-2026-10/record/peerfico_pull.py docs/early-warning-2026-10/record/data/peerfico "NAME EMAIL"\n'
       'python docs/early-warning-2026-10/record/peers.py docs/early-warning-2026-10/record/data/peerfico/facts.json docs/early-warning-2026-10/record/data/peerfico/peers.json</pre>'
       '<p class="cap">The SEC facts file (14 MB) is not in the repository; <code>peers.json</code>, read from it, is. The FHFA zips (21 MB) '
       'are not; <code>nmdb.json</code>, the national series read from them, is.</p></section>'
     + '<section class="box"><h2>What was not checked</h2><div class="notes"><ul>'
       '<li>Competitors&rsquo; FICO figures come from their filings&rsquo; tagged data; only KeyCorp&rsquo;s 2026Q2 amounts were tied to a printed table.</li>'
       '<li>Whether every KeyBank nonaccrual card loan is past due: the internal check that decides whether KeyBank&rsquo;s 30+ share is flattered.</li>'
       '<li>Which FICO version each bank uses, and whether the Philadelphia Fed counts every open account or only active ones for the score percentiles.</li>'
       '<li>The lines in sections A and B are set from the same history they rate; the book&rsquo;s Backtest, which sets each quarter&rsquo;s lines from earlier quarters only, is the strict test and runs in the workbook.</li>'
       '<li>With 2020&ndash;2023 left out the card matches rest on 20 to 37 quarters; the mortgage matches rest mostly on 2005&ndash;2010.</li>'
       '</ul></div></section>')

html = (STYLE + EXTRA + '<main><header style="display:grid;gap:8px"><div class="eyebrow">CONSUMER INDUSTRY ANALYSIS &middot; EVIDENCE RECORD &middot; %s</div>'
        '<h1>Early warning signals for consumer credit: what was tested, what was kept, and why the rest was set aside</h1>'
        '<p class="lede">Over 16 and 17 October 2026 the analyst asked whether FICO should be a rated dimension of the consumer book, '
        'and the question widened to every public signal that might come before card and mortgage losses. This is the record: each '
        'signal drawn against what later happened, in its own units and rescaled for timing, with the numbers behind it. Public data '
        'only. The outcome is at the top; the evidence follows in the order the decision was made.</p></header>'
        % dt.date.today().strftime("%d %b %Y").upper()
        + SUMMARY_TABLE + A + B + C + D + "</main>")
out = HERE.parent / "EVIDENCE.html"
out.write_text(html, encoding="utf-8")
print("written", out, len(html), "bytes, sha256", hashlib.sha256(html.encode("utf-8")).hexdigest()[:16])
