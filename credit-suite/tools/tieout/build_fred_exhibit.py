"""Build the FRED tie-out exhibit: one self-contained file, every image in it.

A note plus a folder of loose images is correct and unusable -- every picture
is a link that resolves only on the machine that wrote it. So every screenshot
here is embedded as a data URI and the whole thing renders to a single PDF a
person can open, read and forward.
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
OUTDIR = CS / "docs" / "tie-out" / "fred-142-series-2026-09-05"
OUTDIR.mkdir(parents=True, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_SHOTS = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp"
                            r"\claude-chrome-screenshots-yXpjuT")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

roster = json.loads((SB / "fred_roster.json").read_text())
ours = json.loads((SB / "fred_ours.json").read_text())
by_id = {r["series"]: r for r in roster}


def uri(path):
    path = pathlib.Path(path)
    kind = "png" if path.suffix.lower() == ".png" else "jpeg"
    return "data:image/%s;base64,%s" % (
        kind, base64.b64encode(path.read_bytes()).decode())


def esc(x):
    return html.escape(str(x if x is not None else ""))


def shot(path, caption, cls="shot"):
    if not pathlib.Path(path).exists():
        return ('<p class="missing">[missing image: %s]</p>' % esc(path))
    return ('<figure class="%s"><img src="%s" alt="%s">'
            '<figcaption>%s</figcaption></figure>'
            % (cls, uri(path), esc(caption), esc(caption)))


CELLS = SB / "fredshots"
SRC = SB / "srcshots"

# ---------------------------------------------------------------- diagram ---
DIAGRAM = """
<figure class="diagram">
<svg viewBox="0 0 980 300" role="img" width="980"
     aria-label="The same figure travelling two roads that meet at difference zero:
     the production path from the agency through FRED into the workbook cell, and
     the check, which goes to the agency's own published document.">
  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
            markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>
    </marker>
  </defs>
  <g font-family="system-ui, sans-serif" font-size="12.5" fill="currentColor">
    <text x="0" y="16" font-size="11.5" font-weight="700"
          letter-spacing="0.08em">THE PRODUCTION ROAD</text>
    <rect x="0" y="30" width="176" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="12" y="52">The agency computes</text>
    <text x="12" y="70" font-size="11.5" opacity="0.75">FHFA / Board / S&amp;P</text>

    <line x1="176" y1="56" x2="252" y2="56" stroke="currentColor"
          stroke-width="1.4" marker-end="url(#a)"/>
    <text x="182" y="48" font-size="10.5" opacity="0.75">redistributes</text>

    <rect x="252" y="30" width="150" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="264" y="52">FRED</text>
    <text x="264" y="70" font-size="11.5" opacity="0.75">one API request</text>

    <line x1="402" y1="56" x2="478" y2="56" stroke="currentColor"
          stroke-width="1.4" marker-end="url(#a)"/>
    <text x="406" y="48" font-size="10.5" opacity="0.75">build writes</text>

    <rect x="478" y="30" width="214" height="52" rx="4" fill="none"
          stroke="currentColor" stroke-width="1.4"/>
    <text x="490" y="52">The cell a person opens</text>
    <text x="490" y="70" font-size="11.5" opacity="0.75">Raw_Consumer B1980</text>

    <text x="0" y="180" font-size="11.5" font-weight="700" letter-spacing="0.08em"
          fill="#b00020">THE CHECK</text>
    <rect x="0" y="194" width="176" height="52" rx="4" fill="none"
          stroke="#b00020" stroke-width="1.6"/>
    <text x="12" y="216" fill="#b00020">The agency's own</text>
    <text x="12" y="234" fill="#b00020">published document</text>

    <line x1="176" y1="220" x2="478" y2="220" stroke="#b00020"
          stroke-width="1.6" marker-end="url(#a)" color="#b00020"/>
    <text x="196" y="212" font-size="10.5" fill="#b00020">read the row, photograph it,
      locate the column</text>

    <rect x="478" y="194" width="214" height="52" rx="4" fill="none"
          stroke="#b00020" stroke-width="1.6"/>
    <text x="490" y="222" fill="#b00020">The published figure</text>

    <line x1="585" y1="82" x2="585" y2="194" stroke="currentColor"
          stroke-width="1.4" stroke-dasharray="4 4"/>
    <rect x="712" y="100" width="196" height="76" rx="4" fill="none"
          stroke="currentColor" stroke-width="2"/>
    <text x="724" y="128" font-weight="700">difference 0</text>
    <text x="724" y="148" font-size="11.5">on 142 of 142 series</text>
    <text x="724" y="166" font-size="11.5" opacity="0.75">0 differ, 0 could not</text>
    <line x1="692" y1="138" x2="712" y2="138" stroke="currentColor"
          stroke-width="1.4" marker-end="url(#a)"/>
  </g>
</svg>
<figcaption><b>Only the lower road touches a document nobody here controls.</b>
That is what makes this evidence rather than a second opinion from the same
source: FRED is the redistributor, and every figure was checked against the
agency that computed it.</figcaption>
</figure>
"""

# --------------------------------------------------------------- sections ---
SETS = [
    ("FHFA All-Transactions house price indexes", "fhfa", [
        (SRC / "fhfa-state.png",
         "FHFA hpi_at_state.csv, the agency's own quarterly file. Header row, "
         "then Alaska, California and Georgia at 2026 Q2."),
        (SRC / "fhfa-us.png",
         "FHFA hpi_at_us_and_census.csv, row USA 2026 Q2."),
    ]),
    ("Charge-off and delinquency rates at commercial banks", "fed", [
        (SRC / "fed-delallsa.png",
         "Federal Reserve Board, delinquency rates at all commercial banks, "
         "row 2026:2. Eleven loan categories across the row."),
        (SRC / "fed-chgallsa.png",
         "Federal Reserve Board, charge-off rates at all commercial banks, "
         "row 2026:2."),
        (SRC / "fed-deltop100sa.png",
         "The same measure for the hundred largest banks."),
        (SRC / "fed-delothersa.png",
         "And for every other bank."),
    ]),
    ("G.19 consumer credit, the debt service ratios, FHFA monthly", "other", [
        (SRC / "g19-hist-sa.png",
         "G.19 historical table, seasonally adjusted levels, row Jun 2026. "
         "Total, revolving and nonrevolving, to the cent."),
        (SRC / "g19-current.png",
         "The current G.19 release, which carries the percent change and the "
         "unadjusted level as well, rounded to a tenth of a billion."),
        (SRC / "dsr-current.png",
         "The debt service ratios, row 2026:1, on the credit-bureau "
         "methodology in force since the 2024:Q2 publication."),
        (SRC / "dsr-archived.png",
         "The page that would have been the wrong source: an archive frozen at "
         "2024:1, last updated 6 September 2024, computed a different way."),
    ]),
    ("Senior Loan Officer Opinion Survey", "sloos", [
        (SRC / "sloos-chartdata.png",
         "The Board's SLOOS chart data, row 2026:3, with the panel headings "
         "copied in from the top of the same table."),
        (SRC / "sloos-table1.png",
         "SLOOS Table 1, question 1: the response counts split three ways, "
         "All Respondents / Large Banks / Other Banks. The large-banks net "
         "percentage is computed from this."),
    ]),
    ("S&P Cotality Case-Shiller house price indexes", "cs", []),
    ("Z.1 commercial property price indexes", "z1", []),
]

# The Case-Shiller source shots came out of the browser session.
CS_SHOTS = sorted(CHROME_SHOTS.glob("*.png"))
CS_CAPS = {
    "screenshot-1788587217813-9.png":
        "S&P Dow Jones Indices, June 2026 release, Table 3: the seasonally "
        "adjusted month-on-month change for every metro. This is what the "
        "twenty adjusted series are proved against.",
    "screenshot-1788587226504-11.png":
        "The same release, Table 2: the unadjusted June index LEVEL. The "
        "national unadjusted series ties to 336.66 here, directly. Detroit "
        "shows no June value at all, which is the release agreeing with our "
        "workbook about an absence.",
}


def set_rows(label):
    return [r for r in roster if r["set"] == label]


def roster_table(rows):
    out = ['<table class="roster"><thead><tr>'
           '<th>Series</th><th>What it is</th><th>Workbook cell</th>'
           '<th class="n">Ours</th><th class="n">Publisher</th>'
           '<th class="n">Diff</th><th>Verdict</th></tr></thead><tbody>']
    for r in sorted(rows, key=lambda x: x["series"]):
        cell = r.get("cell") or r.get("cell_new") or ""
        tab = r.get("tab", "")
        title = (r.get("workbook_title") or r.get("title") or "")
        out.append(
            '<tr class="%s"><td class="sid">%s</td><td>%s</td>'
            '<td class="mono">%s</td><td class="n">%s</td><td class="n">%s</td>'
            '<td class="n">%s</td><td class="v %s">%s</td></tr>'
            % (r["verdict"].split()[0].lower(), esc(r["series"]), esc(title[:64]),
               esc("%s!%s" % (tab, cell) if cell else ""),
               esc(r.get("ours")), esc(r.get("theirs")), esc(r.get("diff")),
               r["verdict"].split()[0].lower(), esc(r["verdict"])))
    out.append("</tbody></table>")
    return "\n".join(out)


def cell_gallery(rows):
    out = ['<div class="gallery">']
    for r in sorted(rows, key=lambda x: x["series"]):
        png = CELLS / ("%s.png" % r["series"])
        if not png.exists():
            out.append('<div class="cellcard missing">%s: no shot</div>'
                       % esc(r["series"]))
            continue
        where = r.get("source_where") or ""
        out.append(
            '<div class="cellcard"><img src="%s" alt="%s in the workbook">'
            '<div class="cc"><b>%s</b> &nbsp;<span class="tag %s">%s</span><br>'
            '<span class="src">source: %s</span></div></div>'
            % (uri(png), esc(r["series"]), esc(r["series"]),
               r["verdict"].split()[0].lower(), esc(r["verdict"]), esc(where[:150])))
    out.append("</div>")
    return "\n".join(out)


# --------------------------------------------------------------- assemble ---
tot = len(roster)
tied = sum(1 for r in roster if r["verdict"] == "TIED")

parts = []
parts.append("""<style>
:root { --ink:#151515; --dim:#5c5c5c; --rule:#d8d8d8; --red:#b00020;
        --good:#0a6b3d; --paper:#ffffff; }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
       font:14px/1.62 "Charter","Georgia",serif; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 42px 46px 80px; }
h1 { font:700 30px/1.22 system-ui,sans-serif; margin:0 0 6px; letter-spacing:-.01em; }
h2 { font:700 19px/1.3 system-ui,sans-serif; margin:44px 0 10px;
     padding-top:14px; border-top:2px solid var(--ink); }
h3 { font:700 15px/1.35 system-ui,sans-serif; margin:26px 0 8px; }
.sub { color:var(--dim); font:15px/1.5 system-ui,sans-serif; margin:0 0 22px; }
.headline { border:2px solid var(--ink); padding:16px 20px; margin:22px 0 30px; }
.headline b { font:700 22px/1.3 system-ui,sans-serif; }
p { margin: 0 0 12px; }
.lede { font-size:15px; }
figure { margin: 16px 0 22px; }
figure img { width:100%; border:1px solid var(--rule); display:block; }
figcaption { font:12.5px/1.5 system-ui,sans-serif; color:var(--dim);
             margin-top:7px; }
.diagram svg { width:100%; height:auto; border:1px solid var(--rule);
               padding:14px; }
table { border-collapse:collapse; width:100%; margin:14px 0 20px;
        font:12px/1.45 system-ui,sans-serif; }
th,td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--rule);
        vertical-align:top; }
th { font-weight:700; border-bottom:1.5px solid var(--ink); white-space:nowrap; }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums;
             white-space:nowrap; }
td.mono, td.sid { font-family:ui-monospace,Consolas,monospace; white-space:nowrap; }
td.v { font-weight:700; }
.tied, td.v.tied { color:var(--good); }
.differs, td.v.differs { color:var(--red); }
.could, td.v.could { color:#8a6d00; }
.compare { font:13px/1.7 ui-monospace,Consolas,monospace; background:#f7f7f5;
           border-left:4px solid var(--ink); padding:13px 16px; margin:14px 0 18px;
           white-space:pre-wrap; }
.gallery { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:16px 0; }
.cellcard { border:1px solid var(--rule); padding:8px; break-inside:avoid; }
.cellcard img { width:100%; display:block; }
.cc { font:11px/1.45 system-ui,sans-serif; margin-top:6px; }
.cc .src { color:var(--dim); }
.tag { font:700 9.5px/1 system-ui,sans-serif; padding:2px 5px; border:1px solid;
       border-radius:2px; letter-spacing:.06em; }
.note { border-left:4px solid var(--red); background:#fff6f6; padding:12px 16px;
        margin:16px 0; }
.note.win { border-color:var(--good); background:#f2fbf6; }
ol,ul { margin:0 0 14px; padding-left:22px; }
li { margin-bottom:7px; }
code { font-family:ui-monospace,Consolas,monospace; font-size:12.5px;
       background:#f2f2ef; padding:1px 4px; }
pre { font:12px/1.55 ui-monospace,Consolas,monospace; background:#f7f7f5;
      padding:12px 14px; border:1px solid var(--rule);
      white-space:pre-wrap; overflow-wrap:anywhere; }
.missing { color:var(--red); font-weight:700; }
@media print { h2 { break-before:auto; } .cellcard, figure { break-inside:avoid; } }
</style>""")

parts.append('<div class="wrap">')
parts.append("<h1>Tie-out: every number in the FRED credit monitor</h1>")
parts.append('<p class="sub">142 series, each proved against the agency that '
             'computes it &mdash; not against FRED, which only redistributes '
             'them. 5 September 2026.</p>')

parts.append('<div class="headline"><b>%d of %d tied. 0 differ. 0 could not.</b>'
             '<p style="margin:8px 0 0">Every figure on the left of every '
             'comparison below was read out of the shipped workbook, '
             '<code>FRED_Credit_Risk_Dashboard.xlsm</code>, and every figure on '
             'the right came off a document published by the agency that '
             'computed it. The tie-out found five defects, one of which was '
             'shipping a state with no data in it, and all five are in '
             '&ldquo;What this found&rdquo; below.</p></div>' % (tied, tot))

parts.append("<h2>How the two roads meet</h2>")
parts.append(DIAGRAM)

# ---- the worked example -----------------------------------------------------
parts.append("<h2>One figure, traced all the way</h2>")
parts.append('<p class="lede">The roster covers all 142. This is one of them '
             'followed link by link, so a reader can see the shape of the check '
             'before trusting the count.</p>')

t = by_id["TOTALSL"]
parts.append("<h3>1 &middot; The figure</h3>")
parts.append("<p>Total consumer credit outstanding, seasonally adjusted, at "
             "June 2026. In the workbook it is on the <code>Raw_Consumer</code> "
             "tab. Open the file, go to that tab and that cell, and this is "
             "what is there:</p>")
parts.append(shot(CELLS / "TOTALSL.png",
                  "FRED_Credit_Risk_Dashboard.xlsm, Raw_Consumer. Excel's own "
                  "row numbers and column letters are printed, so the reference "
                  "can be checked rather than taken on trust."))

parts.append("<h3>2 &middot; The call that produced it</h3>")
parts.append("<pre>curl \"https://api.stlouisfed.org/fred/series/observations"
             "?series_id=TOTALSL&amp;api_key=$FRED_API_KEY&amp;file_type=json\"</pre>")
parts.append("<p>That is the build's request. It is <em>not</em> the check: FRED "
             "redistributes this series, so asking FRED whether FRED is right "
             "is the mirror. The check is link 4.</p>")

parts.append("<h3>3 &middot; What happens in between</h3>")
parts.append("<p>Nothing. The series is a level and the workbook stores it as "
             "landed, in millions of dollars, newest observation first. There is "
             "no transform, no rescaling and no unit conversion between the "
             "response and the cell &mdash; which is worth saying out loud, "
             "because &ldquo;then the system computes it&rdquo; is exactly the "
             "gap a tie-out exists to close.</p>")

parts.append("<h3>4 &middot; The independent source</h3>")
parts.append("<p>The Federal Reserve Board computes and publishes the G.19. "
             "Anyone can fetch the same table:</p>")
parts.append("<pre>https://www.federalreserve.gov/releases/g19/hist/"
             "cc_hist_sa_levels.html</pre>")
parts.append("<p>The figure sits in the row labelled <b>Jun 2026</b>, in the "
             "column headed <b>Total</b>, under &ldquo;Consumer credit "
             "outstanding, seasonally adjusted&rdquo;, in millions of dollars. "
             "Here is that page, with the row ringed and the table's own column "
             "headings brought into the same frame:</p>")
parts.append(shot(SRC / "g19-hist-sa.png",
                  "Federal Reserve Board, G.19 historical table. Last updated "
                  "7 August 2026, per the line under the table."))

parts.append("<h3>5 &middot; The comparison</h3>")
parts.append('<div class="compare">'
             "ours    Raw_Consumer B%s, read from the workbook      %s\n"
             "source  G.19 historical SA levels, Jun 2026, 'Total'  %s\n"
             "diff                                                  %s</div>"
             % (esc(ours["TOTALSL"]["latest"]["row"]), esc(t["ours"]),
                esc(t["theirs"]), esc(t["diff"])))
parts.append("<p>Same entity (all US consumer credit), same period (June 2026), "
             "same basis (seasonally adjusted, outstanding level), same units "
             "(millions of dollars). Verdict <b class=\"tied\">TIED</b>, read "
             "off that block rather than written before it.</p>")

# ---- per-publisher sections -------------------------------------------------
parts.append("<h2>The sets, and the sources behind them</h2>")
parts.append("<p>Split by who publishes the number, because that is what "
             "determines where the check has to go and how hard it is to get "
             "there.</p>")

for label, key, shots in SETS:
    rows = set_rows(label)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    parts.append("<h2>%s</h2>" % esc(label))
    parts.append('<p class="sub" style="margin-bottom:12px">%s &mdash; '
                 '<b>%d of %d tied</b>%s</p>'
                 % (esc(rows[0]["publisher"]), counts.get("TIED", 0), len(rows),
                    "" if set(counts) == {"TIED"} else
                    " (" + ", ".join("%s %d" % (k, v) for k, v in counts.items()
                                     if k != "TIED") + ")"))
    if key == "cs":
        parts.append(
            "<p>S&amp;P Dow Jones Indices refuses scripted requests outright "
            "&mdash; every attempt returned <code>HTTP 403</code>. The obstacle "
            "was real. It was not the verdict: S&amp;P publishes a free monthly "
            "release, and that release carries the unadjusted index level for "
            "every metro and the seasonally adjusted month-on-month change for "
            "every metro. Twenty of these twenty-two series are the adjusted "
            "<em>levels</em>, which the release does not print &mdash; but two "
            "adjacent cells of our own workbook imply the change, and the change "
            "is published.</p>")
        for p in CS_SHOTS:
            if p.name in CS_CAPS:
                parts.append(shot(p, CS_CAPS[p.name]))
        parts.append(
            '<div class="note win"><b>The residual was explained, not '
            'tolerated.</b> Comparing at full precision, five of twenty-two '
            'lines missed the printed value by 0.005 to 0.0074 percentage '
            'points &mdash; tiny, and outside the rounding of a two-decimal '
            'percent. Widening the tolerance would have turned them green and '
            'taught nobody anything. Running the same arithmetic on the '
            'previous month, which the same table publishes, showed no series '
            'missing twice and the signs random: noise, not a data difference. '
            'The cause is that S&amp;P publishes levels to two decimals and '
            'computes its printed change from those. Rounding our two cells the '
            'same way reproduces the release <b>exactly</b> on 42 of 42 '
            'comparisons across both months &mdash; a stricter test than the '
            'one that was failing, not a looser one.</div>')
    if key == "z1":
        parts.append(
            "<p>These two nearly went down as <b>COULD NOT</b>, and the obstacle "
            "was real but wrong. The Z.1 release ships a public CSV bundle; "
            "reading every member of it and collecting the series codes gives "
            "6,107 codes, and neither of ours is among them. The Board's "
            "Financial Accounts Guide has a page for each code, but it prints "
            "the definition and no data, and its clipboard flow came back "
            "empty. Two dead ends, both accurately described. The third route "
            "works: the Board's Data Download Program publishes the entire Z.1 "
            "as one package, and that package carries both series. "
            "<em>It is not in the file I looked in</em> was never the same "
            "statement as <em>the Board does not publish it</em>.</p>")
        parts.append(
            "<p>One more thing had to be right before these could tie. FRED "
            "stamps a quarter at its first day and the Board stamps it at its "
            "last, so matching on the literal date reported &ldquo;no "
            "observation&rdquo; for a series that is plainly published. Same "
            "quarter, two conventions.</p>")
    for path, cap in shots:
        parts.append(shot(path, cap))
    parts.append("<h3>Every line in this set</h3>")
    parts.append(roster_table(rows))
    parts.append("<h3>And the workbook cell behind each one</h3>")
    parts.append(cell_gallery(rows))

# ---- run it yourself --------------------------------------------------------
parts.append("<h2>How to run the whole thing yourself</h2>")
parts.append("<p>Real values, already filled in. Nothing here needs editing "
             "before it will run.</p>")
parts.append("""<ol>
<li>Rebuild the workbook, so the cells you check are the ones the code
produces:<pre>cd C:\\Users\\ajish\\SATC-cs\\credit-suite
$env:FRED_API_KEY = "&lt;your key&gt;"
python -m credit_suite.sources.fred.runner --live</pre></li>
<li>Open <code>example-output\\FRED_Credit_Risk_Dashboard.xlsm</code> and go to
<code>Raw_Consumer</code>. Every series is a header row carrying its id and
title, then date/value rows newest first.</li>
<li>Fetch the Board's own G.19 table and read the row for the newest month:
<pre>https://www.federalreserve.gov/releases/g19/hist/cc_hist_sa_levels.html</pre></li>
<li>For the house price indexes, fetch FHFA's own quarterly files:
<pre>https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv
https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv
https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.csv</pre></li>
<li>For the charge-off and delinquency rates, the Board publishes six tables:
<pre>https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm
https://www.federalreserve.gov/releases/chargeoff/delallsa.htm
https://www.federalreserve.gov/releases/chargeoff/chgtop100sa.htm
https://www.federalreserve.gov/releases/chargeoff/deltop100sa.htm
https://www.federalreserve.gov/releases/chargeoff/chgothersa.htm
https://www.federalreserve.gov/releases/chargeoff/delothersa.htm</pre></li>
<li>For the survey, the Board's chart data and its Table 1:
<pre>https://www.federalreserve.gov/data/sloos/sloos-202607-chart-data.htm
https://www.federalreserve.gov/data/sloos/sloos-202607-table-1.htm</pre></li>
<li>For the debt service ratios, use the CURRENT release, not the archive:
<pre>https://www.federalreserve.gov/releases/dsr/</pre></li>
<li>For Z.1, the complete package rather than the release page's CSV bundle:
<pre>https://www.federalreserve.gov/datadownload/Output.aspx?rel=Z1&amp;filetype=zip</pre></li>
<li>For Case-Shiller, the monthly release. Tables 2 and 3 carry the levels and
the adjusted changes:
<pre>https://www.spglobal.com/spdji/en/index-family/indicators/sp-cotality-case-shiller/</pre></li>
</ol>""")

# ---- what it found ----------------------------------------------------------
parts.append("<h2>What this found</h2>")
parts.append("<p>Five things, none of which any test in the suite could have "
             "caught, because every one of them left the numbers correct.</p>")
parts.append("""
<h3>1 &middot; A shipped workbook with a state missing from it</h3>
<p>Nebraska's house price index was blank. FRED publishes it, with data through
April 2026, and it fetched first time when asked again. The build had hit one
<code>Internal Server Error</code>, recorded it honestly in its own status
&mdash; <code>"errors": ["NESTHPI: Internal Server Error"]</code> &mdash;
blanked the slot, and passed. The retry logic covered rate limits only, so a
single 5xx out of 142 requests shipped a monitor with a state missing.
<b>Fixed:</b> transient server errors, timeouts and dropped connections are now
retried; a dead series id still fails on the first try, because that is how five
retired series were caught earlier and retrying it would hide the next one.</p>

<h3>2 &middot; Two series wearing each other's description</h3>
<p><code>SUBLPDRCSC</code> is commercial real estate <b>construction and land
development</b> and was labelled nonfarm nonresidential. <code>SUBLPDRCSN</code>
is <b>nonfarm nonresidential</b> and was labelled construction and land. Both
values were right, on the dashboard and in the raw tabs, which is exactly why
nothing noticed.</p>

<h3>3 &middot; A tightening indicator with its alert switched off</h3>
<p>The costly one. <code>SUBLPDHMSENQ</code> measures banks tightening standards
on GSE-eligible mortgages. It was labelled a <em>demand</em> series, and the
seed's helper gives demand series <code>alert_rule = "none"</code> &mdash; right
for a demand series, and this is not one. So a real mortgage-tightening signal
sat on the dashboard and could never fire. <b>Fixed</b>, and that turns an alert
on: it is a change in what the dashboard flags, not just in what it says.</p>

<h3>4 &middot; Two more labels that described a different series</h3>
<p><code>DRTSSP</code> is subprime <b>mortgage</b> standards, not consumer loans.
<code>SUBLPDCILSLGNQ</code> is <b>large banks</b> tightening standards, not
increasing spreads. Right value, wrong label, is invisible until somebody reads
the label against the publisher's own definition.</p>


<h3>5 &middot; Four series that told the reader &ldquo;billions&rdquo; beside a
figure in millions</h3>
<p>Look again at the workbook shot in the worked example above. The metadata
line reads <code>units=billions $</code> and the value under it is
<b>5,166,907.71</b>. Five quadrillion dollars of consumer credit. The number is
right &mdash; it ties to the cent against the Board's own table, which prints
that figure in <b>millions</b>, and FRED publishes all four of these as
&ldquo;Millions of U.S. Dollars&rdquo;. Only the declared unit was wrong, by a
factor of a thousand, on the line a person reads.</p>
<p>Nothing computes with that field; it is displayed. That is precisely why no
numeric test could see it, and why it took photographing the cell to notice.
<b>Fixed</b>, with the declared unit now checked against the publisher's own.
The shots in this document still say &ldquo;billions&rdquo;, deliberately: they
are the evidence, and replacing them would erase the finding.</p>

<div class="note"><b>One thing deliberately left alone.</b> The two Z.1
commercial-property series carry a unit I could not settle. Our config calls
both &ldquo;millions $&rdquo;. FRED labels one &ldquo;Mil. of $&rdquo; and the
other &ldquo;%&rdquo;. The Board's own Financial Accounts Guide describes both
identically, as price indexes &mdash; and calls neither a dollar level. Three
authorities, three answers, and the values themselves tie exactly against the
Board's package. I could not establish which unit is right, so nothing was
changed and it is written down here instead. Unknown is a third answer.</div>

<div class="note win"><b>The guard that now holds it down.</b>
<code>tests/test_fred_labels.py</code> checks each label against the publisher's
own definition: a series must carry the words its definition requires, must
<em>not</em> carry a sibling's words (which is what catches a swap), and a
tightening measure must not be wired as a demand one. It refuses if a survey
series is added with no recorded definition, so the check cannot quietly stop
covering things. Four mutations against it, all killed, on a 409-test
baseline.</div>
""")

# ---- what I got wrong -------------------------------------------------------
parts.append("<h2>What I got wrong</h2>")
parts.append("""
<ul>
<li><b>I read the wrong debt-service page first.</b> The Board's
<code>/releases/housedebt/</code> page is an archive, frozen at 2024:1 and last
updated in September 2024, because the DSR moved to a credit-bureau methodology
from the 2024:Q2 publication. Comparing a 2026 figure against it produced three
apparent differences of 1.4 percentage points. Nothing was wrong with the data;
I had picked a discontinued series computed a different way. It is in this
document as a photograph, above, because it is the exact failure the
&ldquo;same basis&rdquo; check exists to stop.</li>
<li><b>I called five Case-Shiller lines DIFFERS before I understood them.</b>
They were within 0.0074 of a percentage point. The right response was not a
wider tolerance; it was finding out why, which took one extra month of the same
published table and turned 22 near-misses into 22 exact matches.</li>
<li><b>Six of my first twelve source photographs were blank and reported
&ldquo;ok&rdquo;.</b> <code>window.scrollBy</code> produces an empty capture in
headless Chrome, so every one of them came back as an identical 6,615-byte white
rectangle. I only know because I opened them. Nothing in the pipeline would
have told me.</li>
<li><b>My first Z.1 answer was going to be COULD NOT</b>, with an obstacle I
could describe precisely and had not finished testing. It was two clicks from
being wrong in a document.</li>
</ul>
""")

# ---- what it does not prove -------------------------------------------------
parts.append("<h2>What this does not prove</h2>")
parts.append("""
<ul>
<li><b>It proves the latest observation, not the whole history.</b> Each series
was checked at its most recent period &mdash; 142 of 142 &mdash; and the
Case-Shiller set additionally at the month before. The other 13,763 observations
in the workbook were not individually compared to anything.</li>
<li><b>The twenty adjusted Case-Shiller metros are tied through a ratio, not a
level.</b> S&amp;P does not publish adjusted levels free. Two adjacent workbook
cells reproduce S&amp;P's published change exactly, which pins the month-on-month
move and the relationship between those two cells. It would not catch a constant
scale error applied to the whole series.</li>
<li><b>It proves the number, not the formula.</b> Nothing here checks the
dashboard's z-scores, bands or alert logic. That was deliberate and it is the
firm's own instruction: the mission was the base data.</li>
<li><b>The column maps rest on the tables' own headings.</b> Where a Federal
Reserve table has eleven unlabelled numeric columns, the mapping was read off
the header and then confirmed by the values agreeing across every series in that
table. A mapping that is wrong in a way that still agrees on every series is not
excluded, though it is hard to construct.</li>
<li><b>Nothing here was checked by a second person.</b></li>
</ul>
""")

parts.append("</div>")

html_out = "\n".join(parts)
src = OUTDIR / "TIE-OUT-fred-142-series.html"
src.write_text(html_out, encoding="utf-8")
print("html written: %.1f MB" % (src.stat().st_size / 1e6))

pdf = OUTDIR / "TIE-OUT-fred-142-series-2026-09-05.pdf"
subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                "--no-pdf-header-footer", "--virtual-time-budget=180000",
                "--print-to-pdf=%s" % pdf, src.resolve().as_uri()],
               check=False, capture_output=True, timeout=900)
print("pdf: %s  %.1f MB" % (pdf.name, pdf.stat().st_size / 1e6)
      if pdf.exists() else "PDF FAILED")
