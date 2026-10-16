"""Build the tie-out document and render it through canon's checker, the only door.

    python build_exhibit.py [--chrome PATH]

Reads check-output.json (written by check.py) for every number, and the
pictures beside this file. canon's check_tie_out.render refuses the document
if its roster does not add up, if a named section is missing, or if no source
picture carries a red mark; then it renders the PDF and refuses again if the
pictures did not survive. Run as root, Chrome needs --no-sandbox: pass a
wrapper that adds it with --chrome (that skips no check).
"""
import base64
import html
import json
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CANON = pathlib.Path("/root/.claude/plugins/cache/satc/canon/1.22.0")
NAME = "TIE-OUT-gasoline-change-2026-10-16"
D = json.loads((HERE / "check-output.json").read_text("utf-8"))
O, E, R = D["ours"], D["eia"], D["eia_rows"]


def img(name, alt, source=False, width="100%"):
    data = base64.b64encode((HERE / name).read_bytes()).decode()
    mark = ' data-tieout="source"' if source else ""
    return ('<figure><img%s src="data:image/png;base64,%s" alt="%s" style="max-width:%s">'
            '<figcaption>%s</figcaption></figure>' % (mark, data, html.escape(alt), width, html.escape(alt)))


def pct(x, places=10):
    return ("%." + str(places) + "f%%") % x


ROUTE = """
<svg viewBox="0 0 1000 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Two roads to one number">
<style>.b{fill:#F4F1EC;stroke:#B9B4AC}.c{fill:#FFF2CC;stroke:#D6B656}.t{font:600 12.5px Arial;fill:#0A0908}
.s{font:11px Calibri,Carlito,Arial;fill:#57534B}.a{stroke:#57534B;stroke-width:1.4;fill:none;marker-end:url(#h)}
.g{fill:#E4EFE7;stroke:#1E7A47}</style>
<defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="#57534B"/></marker></defs>
<text x="8" y="16" class="t">The production road: what the workbook did</text>
<rect class="b" x="8" y="26" width="150" height="70"/><text x="16" y="46" class="t">FRED GASREGW</text>
<text x="16" y="62" class="s">EIA's series, republished</text><text x="16" y="76" class="s">by the St. Louis Fed</text>
<rect class="b" x="200" y="26" width="160" height="70"/><text x="208" y="46" class="t">Pull, 16 Oct 2026</text>
<text x="208" y="62" class="s">fred-GASREGW.csv</text><text x="208" y="76" class="s">SHA-256 8398f482…061f</text>
<rect class="b" x="402" y="26" width="170" height="70"/><text x="410" y="46" class="t">The tool</text>
<text x="410" y="62" class="s">4.331 ÷ 3.061 − 1; rank among</text><text x="410" y="76" class="s">1,829 changes; firm's cut-offs</text>
<rect class="c" x="614" y="26" width="180" height="70"/><text x="622" y="46" class="t">Workbook, Ratings tab</text>
<text x="622" y="62" class="s">H19 +41.49%  I19 4 Moderate-High</text><text x="622" y="76" class="s">J19 94.6%  (what the reader sees)</text>
<path class="a" d="M158,61 H198"/><path class="a" d="M360,61 H400"/><path class="a" d="M572,61 H612"/>
<text x="160" y="110" class="s">one request, no key</text><text x="362" y="110" class="s">read, 52 weeks back</text>
<text x="574" y="110" class="s">written as values</text>
<text x="8" y="176" class="t">The check: the publisher's own documents, worked by hand</text>
<rect class="b" x="8" y="186" width="190" height="70"/><text x="16" y="206" class="t">EIA's weekly table</text>
<text x="16" y="222" class="s">eia.gov, photographed;</text><text x="16" y="236" class="s">3.061 and 4.331 ringed</text>
<rect class="b" x="240" y="186" width="190" height="70"/><text x="248" y="206" class="t">EIA's own history file</text>
<text x="248" y="222" class="s">EMM_EPMR_PTE_NUS_DPGw.xls,</text><text x="248" y="236" class="s">1,887 weeks, 6 left blank</text>
<rect class="b" x="472" y="186" width="190" height="70"/><text x="480" y="206" class="t">By hand, and by formula</text>
<text x="480" y="222" class="s">4.331 ÷ 3.061 − 1 = 41.4897%</text><text x="480" y="236" class="s">COUNTIF: 1,730 of 1,829</text>
<path class="a" d="M198,221 H238"/><path class="a" d="M430,221 H470"/>
<rect class="g" x="704" y="186" width="290" height="70"/><text x="714" y="210" class="t">Difference 0</text>
<text x="714" y="228" class="s">price, change, percentile and rating;</text><text x="714" y="242" class="s">all 1,881 weeks identical in both files</text>
<path class="a" d="M662,221 H702"/><path class="a" d="M794,96 V184"/>
<text x="8" y="296" class="s">Only the lower road touches a document this firm does not control: EIA publishes the series. FRED is a</text>
<text x="8" y="312" class="s">copy of it; showing the copy is faithful, week by week, is part of what this document does.</text>
</svg>"""

CSS = """
@page { size: A4; margin: 14mm 13mm; }
body { font: 10.5pt/1.45 Calibri, Carlito, Arial, sans-serif; color: #16130F; max-width: 980px; margin: 0 auto; }
h1 { font: bold 19pt Arial, sans-serif; margin: 0 0 2px; }
h2 { font: bold 13pt Arial, sans-serif; border-bottom: 2px solid #0A0908; padding-bottom: 2px; margin: 22px 0 6px;
     page-break-after: avoid; }
h3 { font: bold 11pt Arial, sans-serif; margin: 14px 0 4px; page-break-after: avoid; }
.headline { font: bold 14pt Arial, sans-serif; margin: 8px 0; }
.lede { color: #57534B; }
pre { background: #F4F1EC; padding: 8px 10px; font: 9pt DejaVu Sans Mono, Consolas, monospace; white-space: pre-wrap;
      border: 1px solid #E4DFD5; page-break-inside: avoid; }
code { font: 9pt DejaVu Sans Mono, Consolas, monospace; background: #F4F1EC; padding: 0 2px; }
table { border-collapse: collapse; margin: 6px 0 10px; page-break-inside: avoid; }
td, th { border: 1px solid #E4DFD5; padding: 3px 7px; vertical-align: top; text-align: left; }
th { background: #F4F1EC; font: bold 9pt Arial, sans-serif; color: #57534B; }
figure { margin: 6px 0 12px; page-break-inside: avoid; }
figure img { border: 1px solid #E4DFD5; }
figcaption { font-size: 9pt; color: #57534B; }
.tied { font-weight: bold; color: #1E7A47; }
.route { border: 1px solid #E4DFD5; padding: 6px; margin: 10px 0; page-break-inside: avoid; }
ol li, ul li { margin: 3px 0; }
"""


def build():
    yb = O["gasoline_tab_2025_10_13"]
    lt = O["gasoline_tab_2026_10_12"]
    ch = O["gasoline_change"][0] * 100
    pc = O["gasoline_percentile"][0] * 100
    rows_fred = [line for line in (HERE / "pull-2026-10-16-fred-GASREGW.csv").read_text().splitlines()
                 if line.startswith(("observation_date", "2025-10-13", "2026-10-05", "2026-10-12"))]
    fv = D["fred_vs_eia"]
    f = D["files"]
    parts = []
    add = parts.append
    add("<h1>Tie-out: gasoline's change over a year, +41.49%, rated 4</h1>")
    add('<p class="lede">The economic conditions workbook, Ratings tab, built %s from the pull of %s. The top reading '
        'on the tab, traced from the cell the reader sees to the publisher, the U.S. Energy Information '
        'Administration, and worked again by hand. Three more of the tab\'s headline figures are tied in the '
        'roster.</p>' % (O["run"]["built"], O["run"]["pull"]))
    add('<p class="headline" data-tieout="headline">4 of 4 figures tied out to their publishers</p>')
    add('<div class="route">%s</div>' % ROUTE)

    add("<h2>1 · The figure</h2>")
    add("<p>Where the reader sees it: <b>Ratings</b> tab, row 19, <i>Retail gasoline price, regular</i>, under "
        "<i>Prices and insurance</i>. Read out of the workbook file (<code>economic-conditions.xlsx</code>, "
        "SHA-256 <code>%s…</code>) with openpyxl, cell by cell, and photographed as LibreOffice shows it:</p>"
        % f["economic-conditions.xlsx"][:16])
    add("<table><tr><th>Cell</th><th>Stored value</th><th>Shown as</th><th>Meaning</th></tr>"
        "<tr><td>H19</td><td>%r</td><td>+41.49%%</td><td>change over 12 months to 12 Oct 2026</td></tr>"
        "<tr><td>I19</td><td>%s</td><td>4 Moderate-High</td><td>its rating</td></tr>"
        "<tr><td>J19</td><td>%r</td><td>94.6%%</td><td>its percentile in its own history</td></tr>"
        "<tr><td>D19</td><td>%r</td><td>4.33</td><td>latest price, dollars a gallon (shown to two places)</td></tr>"
        "<tr><td>Gasoline!O%s, O%s</td><td>%r, %r</td><td>3.061, 4.331</td><td>the prices for the weeks of 13 Oct 2025 "
        "and 12 Oct 2026, on the series' own tab</td></tr></table>"
        % (O["gasoline_change"][0], O["gasoline_rating"], O["gasoline_percentile"][0], O["gasoline_latest"][0],
           yb[0][1:], lt[0][1:], yb[1], lt[1]))
    add(img("ours-ratings-gasoline.png", "Ours: the Ratings tab's gasoline row, the four cells ringed (workbook "
            "rendered in LibreOffice)"))

    add("<h2>2 · The call</h2>")
    add("<p>The pull made one request to FRED, with no key and no User-Agent (FRED stalls on one that names a "
        "browser):</p><pre>curl -sS \"https://fred.stlouisfed.org/graph/fredgraph.csv?id=GASREGW\"</pre>"
        "<p>The response, saved as <code>work/macro-cache/2026-10-16/fred-GASREGW.csv</code>; the lines that carry "
        "the figure:</p><pre>%s</pre><p>Its SHA-256, <code>%s</code>, is the fingerprint the workbook's "
        "<b>Sources</b> tab gives for that file, so this is the file the workbook read. It is kept beside this "
        "document as <code>pull-2026-10-16-fred-GASREGW.csv</code>.</p>"
        % (html.escape("\n".join(rows_fred)), fv["fred_file_sha256"]))

    add("<h2>3 · The derivation</h2><ol>"
        "<li>Every week with a price is kept; a week FRED prints as <code>.</code> is left empty, never zero "
        "(%s priced weeks, 20 Aug 1990 to 12 Oct 2026).</li>"
        "<li>For each week, the price 52 weeks earlier: the reading nearest the date 364 days before, at most three "
        "days away. For the week of 12 Oct 2026 that is the week of 13 Oct 2025, exactly 364 days.</li>"
        "<li>The change: 4.331 ÷ 3.061 − 1 = <b>%s</b>.</li>"
        "<li>Its percentile: the share of all %s such changes, 19 Aug 1991 on, that are at or below it (for gasoline "
        "a rise is worse): %s ÷ %s = <b>%s</b>.</li>"
        "<li>Its rating: the firm's cut-offs (<code>docs/macro/settings.json</code>, 16 Oct 2026) start 2, 3, 4 and 5 "
        "at the 50th, 75th, 90th and 95th percentiles, and a reading on a line takes the worse rating. 94.587 is at "
        "or past 90 and short of 95: <b>4 Moderate-High</b>.</li></ol>"
        % ("{:,}".format(E["weeks"]), pct(E["change_pct"], 4), "{:,}".format(E["changes"]), "{:,}".format(E["at_or_below"]),
           "{:,}".format(E["changes"]), pct(E["percentile"], 3)))

    add("<h2>4 · The independent source</h2>")
    add("<table><tr><th>Publisher</th><td>U.S. Energy Information Administration (EIA)</td></tr>"
        "<tr><th>Series</th><td>Weekly U.S. Regular All Formulations Retail Gasoline Prices, "
        "<code>EMM_EPMR_PTE_NUS_DPG</code></td></tr>"
        "<tr><th>Units</th><td>Dollars per gallon, as published (three places)</td></tr>"
        "<tr><th>Where</th><td>eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&amp;s=EMM_EPMR_PTE_NUS_DPG&amp;f=W, "
        "<i>View history: Weekly</i></td></tr>"
        "<tr><th>Rows, columns</th><td>row <b>2025-Oct</b>, week <b>10/13</b>: <b>3.061</b>; row <b>2026-Oct</b>, "
        "week <b>10/12</b>: <b>4.331</b></td></tr>"
        "<tr><th>Fetched</th><td>16 Oct 2026, 05:27 UTC, in Chromium, certificate checks on</td></tr></table>")
    add(img("source-eia-weekly-gasoline.png", "Source: EIA's own weekly table, the page's title and units above, "
            "the two weeks ringed", source=True))
    add("<p><b>Read twice.</b> The same page's <i>Download Data (XLS File)</i>, "
        "<code>https://www.eia.gov/dnav/pet/hist_xls/EMM_EPMR_PTE_NUS_DPGw.xls</code> (SHA-256 "
        "<code>668bee46…233c</code>), sheet <i>Data 1</i>, carries the whole history: row 1838, 10/13/2025, 3.061; "
        "row 1890, 10/12/2026, 4.331. It has %s rows, a row for every week, %s of them blank (December 1990 to "
        "January 1991, when EIA published no price). It is kept beside this document as "
        "<code>eia-EMM_EPMR_PTE_NUS_DPGw.csv</code>, the sheet saved as CSV by LibreOffice.</p>"
        % ("{:,}".format(R["rows"]), R["blank_rows"]))

    add("<h2>5 · The comparison</h2>")
    add("<table><tr><th></th><th>Ours: the workbook</th><th>Source: EIA</th><th>Difference</th></tr>"
        "<tr><td>Price, week of 12 Oct 2026</td><td>4.331 (Ratings!D19; Gasoline!O%s)</td>"
        "<td>4.331 (table; XLS row 1890)</td><td>0</td></tr>"
        "<tr><td>Price, week of 13 Oct 2025</td><td>3.061 (Gasoline!O%s)</td><td>3.061 (table; XLS row 1838)</td>"
        "<td>0</td></tr>"
        "<tr><td>Change over 12 months</td><td>%s (H19)</td><td>%s (by hand)</td><td>%s</td></tr>"
        "<tr><td>Percentile in its own history</td><td>%s (J19)</td><td>%s (1,730 of 1,829)</td><td>0</td></tr>"
        "<tr><td>Rating, the firm's cut-offs</td><td>4 Moderate-High (I19)</td><td>4 (94.587 &ge; 90, &lt; 95)</td>"
        "<td>0</td></tr></table>"
        % (lt[0][1:], yb[0][1:], pct(ch), pct(E["change_pct"]), "%.10f" % abs(ch - E["change_pct"]),
           pct(pc), pct(E["percentile"])))
    add("<p>The change agrees to ten decimal places, which is as many as the tool keeps. <b>Week by week:</b> the "
        "FRED file the workbook read and EIA's own file hold the same %s priced weeks, and not one price differs "
        "(%s weeks in both, %d only in FRED, %d only in EIA). So the road through FRED changed nothing for this "
        "series.</p>"
        % ("{:,}".format(fv["eia_weeks"]), "{:,}".format(fv["in_both"]), len(fv["only_fred"]), len(fv["only_eia"])))
    add("<p><b>The four sameness checks.</b> Same series: FRED's GASREGW is EIA's EMM_EPMR_PTE_NUS_DPG, all 1,881 "
        "weeks equal. Same dates: the weeks of 13 Oct 2025 and 12 Oct 2026. Same basis: the weekly retail price, "
        "taxes in, not seasonally adjusted, as EIA publishes it. Same units: dollars a gallon, three places "
        "(the workbook shows two and stores three). Verdict: <span class=\"tied\">TIED</span>.</p>")

    add("<h2>The roster</h2>")
    add('<table data-tieout="roster"><tr><th>Verdict</th><th>Figures</th><th>Which</th></tr>'
        '<tr><td>DIFFERS</td><td data-tieout="count">0</td><td></td></tr>'
        '<tr><td>COULD NOT</td><td data-tieout="count">0</td><td></td></tr>'
        '<tr><td>TIED</td><td data-tieout="count">4</td><td>gasoline\'s change; the unemployment rate; the Sahm '
        'reading; government-backed mortgages 90+ days late, their change</td></tr></table>')
    add("<table><tr><th>Figure, as the Ratings tab shows it</th><th>Ours (the workbook)</th><th>Source</th>"
        "<th>Diff</th><th>Verdict</th></tr>"
        "<tr><td>Gasoline, change over 12 months to 12 Oct 2026: +41.49%%, rated 4</td><td>H19 %r; I19; J19</td>"
        "<td>EIA, above</td><td>0</td><td class=\"tied\">TIED</td></tr>"
        "<tr><td>Unemployment rate, September 2026</td><td>Ratings, D column: %r</td><td>BLS LNS14000000, "
        "2026, Sep: %s</td><td>0</td><td class=\"tied\">TIED</td></tr>"
        "<tr><td>Sahm reading, September 2026</td><td>%s</td><td>FRED SAHMCURRENT, 2026-09-01: %s</td><td>0</td>"
        "<td class=\"tied\">TIED</td></tr>"
        "<tr><td>Government-backed mortgages 90+ days late, change over 12 months to 2026 Q2</td><td>Ratings, D: %r; "
        "H: %r points</td><td>FHFA NMDB: 2025Q2 %s, 2026Q2 %s; change %s</td><td>0</td><td class=\"tied\">TIED</td>"
        "</tr></table>"
        % (O["gasoline_change"][0], O["unemployment"][0], D["bls"]["2026_sep"],
           html.escape(re.match(r"(\S+): ([\d.]+ in \w+ \d{4})", O["sahm_text"]).group(0)), D["sahm"]["2026-09-01"],
           O["gov_90_level"][0], O["gov_90_change"][0], D["fhfa"]["2025Q2"][0], D["fhfa"]["2026Q2"][0],
           D["fhfa"]["change_points"]))
    add("<h3>The unemployment rate: BLS's own table</h3><p>The tool reads FRED's UNRATE, which is BLS series "
        "LNS14000000. BLS's data page, fetched 16 Oct 2026 in Chromium: series id, seasonally adjusted, ages 16 and "
        "over; 2026, September: 4.2. October 2025 shows <code>-(9)</code>, BLS's mark for the lapse in "
        "appropriations, which the tool keeps as an empty month.</p>")
    add(img("source-bls-unemployment.png", "Source: BLS, LNS14000000, 2026 September ringed", source=True))
    add("<h3>The Sahm reading: the St. Louis Fed's own</h3><p>The tool works out its own Sahm reading from the "
        "unemployment rate; FRED publishes SAHMCURRENT, worked out by the St. Louis Fed. Two computations, one "
        "published: September 2026, 0.00 in both (and all 931 months agreed on 15 Oct 2026).</p>")
    add(img("source-fred-sahm.png", "Source: FRED, SAHMCURRENT, the September 2026 observation ringed",
            source=True, width="70%"))
    add("<h3>Government-backed mortgages 90+ days late: FHFA's own file</h3><p>Downloaded fresh from FHFA "
        "(SHA-256 <code>2083c4e1…4e89</code>, the same as the file the pull read). The rows, every column as filed:"
        "</p>")
    add(img("source-fhfa-gov-90.png", "Source: FHFA, National Mortgage Database file, the two quarters ringed",
            source=True))

    add("<h2>How to run it yourself</h2><ol>"
        "<li>Open <code>https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&amp;s=EMM_EPMR_PTE_NUS_DPG&amp;f=W"
        "</code>. In row <b>2025-Oct</b>, the price beside <b>10/13</b> is <b>3.061</b>; in row <b>2026-Oct</b>, "
        "beside <b>10/12</b>, <b>4.331</b>. Find them by row and week: 3.061 also appears beside 12/03 in 2007 "
        "and 11/24 in 2025.</li>"
        "<li>Divide: <code>4.331 / 3.061 - 1</code> = <b>0.414897</b>, which is +41.49%.</li>"
        "<li>Click <i>Download Data (XLS File)</i> and open sheet <i>Data 1</i>. In cell <code>C56</code> type "
        "<code>=IF(AND(ISNUMBER(B4),ISNUMBER(B56)),B56/B4-1,\"\")</code> and fill it down to <code>C1890</code> "
        "(each week against the row 52 above: the sheet has a row for every week). Then "
        "<code>=COUNTIF(C56:C1890,\"&lt;=\"&amp;C1890)</code> gives <b>1730</b>, "
        "<code>=COUNT(C56:C1890)</code> gives <b>1829</b>, and their ratio <b>0.9459</b> (run in LibreOffice on 16 Oct "
        "2026: 0.945872061235648).</li>"
        "<li>94.59% is at or past 90 and short of 95, the firm's cut-offs for 4 and 5: <b>4 Moderate-High</b>.</li>"
        "<li>Open the workbook's <b>Ratings</b> tab: row <i>Retail gasoline price, regular</i> shows +41.49%, "
        "4 Moderate-High, 94.6%.</li>"
        "<li>Or run the check. From <code>threshold-engine/</code>, make the workbook as the procedure does, then "
        "fetch the three roster sources into this folder and run it (the EIA file is already here):"
        "<pre>python -m threshold_engine.macro pull --cache work/macro-cache\n"
        "python -m threshold_engine.macro rate --cache work/macro-cache --settings docs/macro/settings.json "
        "--workbook work/economic-conditions.xlsx\n"
        "cd docs/macro/tie-out/gasoline-change-2026-10-16\n"
        "curl -sS -A \"Mozilla/5.0\" -o bls-LNS14000000.html "
        "\"https://data.bls.gov/timeseries/LNS14000000?from_year=2024&amp;to_year=2026&amp;output_view=data\"\n"
        "curl -sS -o fred-SAHMCURRENT.csv \"https://fred.stlouisfed.org/graph/fredgraph.csv?id=SAHMCURRENT\"\n"
        "curl -sS -A \"Mozilla/5.0\" -o fhfa-nmdb.zip \"https://www.fhfa.gov/document/d/nmdb/"
        "nmdb-mortgage-performance-statistics-national-census-areas-quarterly.zip\"\n"
        "python check.py ../../../../work/economic-conditions.xlsx ../../../../work/macro-cache/2026-10-16 "
        "eia-EMM_EPMR_PTE_NUS_DPGw.csv bls-LNS14000000.html fred-SAHMCURRENT.csv fhfa-nmdb.zip ../../settings.json"
        "</pre>Use the dated pull folder the workbook names on its Run tab.</li>"
        "<li>On a later day the latest week moves on, and so do the numbers; the two weeks above stay where they "
        "are in EIA's table.</li></ol>")

    add('<h2 data-tieout="what-it-found">What it found</h2><ul>'
        "<li><b>Every figure tied; nothing in the workbook needed correcting.</b> The price, the change, the "
        "percentile and the rating all came out the same from EIA's own documents, worked a second time without "
        "the tool's code.</li>"
        "<li><b>The road through FRED costs nothing for gasoline:</b> all 1,881 priced weeks are identical in "
        "FRED's copy and EIA's own file, the gaps of 1990 and 1991 included.</li>"
        "<li><b>A figure found by its text can be the wrong week.</b> EIA's table prints 3.061 in three weeks "
        "(3 Dec 2007, 13 Oct 2025, 24 Nov 2025). A reader checking by eye, or a tool matching on text, can land "
        "on the wrong one and still read 3.061. The how-to above finds it by row and week for that reason.</li>"
        "<li><b>The spreadsheet route works on EIA's own file as published:</b> one formula, filled down, gives "
        "the same 1,730 of 1,829, so a reader with Excel and no Python can redo the rating.</li></ul>")
    add('<h2 data-tieout="what-i-got-wrong">What I got wrong</h2><ul>'
        "<li><b>My first picture of EIA's page ringed the wrong week.</b> I placed the ring on the first cell "
        "reading 3.061, which is the week of 3 Dec 2007. The number was right and the week was wrong, and it "
        "would have passed this document's red-ink check. I saw it only when I cropped the picture and read the "
        "row label. The ring is now placed by row and week.</li>"
        "<li><b>My first ring on FRED's page marked nothing.</b> The first element reading 0.00 was a hidden one "
        "at the page's corner. The picture now rings the visible <i>Sep 2026: 0.00</i>.</li>"
        "<li><b>My first picture of the workbook missed the gasoline row.</b> The rings were drawn, but on the "
        "page outside the crop; the picture showed the rows beneath. Recropped from the row's position on the "
        "page.</li>"
        "<li><b>Earlier in this work I said a fix was made when it was not:</b> a chart-label format, claimed "
        "fixed, did nothing in LibreOffice. The walk of the same day found it (W7 in the walk's defects).</li></ul>")
    add('<h2 data-tieout="what-this-does-not-prove">What this does not prove</h2><ul>'
        "<li><b>Four figures of 158 readings.</b> The other 154 rest on the same code, on the comparison of 12-month "
        "changes with FRED's own for 13 series (15 Oct 2026, every date), and on the Sahm comparison over 931 "
        "months; none of them is tied to its publisher.</li>"
        "<li><b>FRED's copies of the other series are assumed faithful.</b> Shown here for gasoline only.</li>"
        "<li><b>The FHFA figure is checked against the same file the tool read</b> (a fresh download, identical "
        "fingerprint). That proves the tool read FHFA's file correctly, not that the file is right. A second "
        "rendering, FHFA's online charts, was not tried.</li>"
        "<li><b>The Sahm figure is two computations from one BLS series:</b> it proves the arithmetic, not the "
        "unemployment data, which the BLS row above ties separately.</li>"
        "<li><b>Percentiles move when history is revised.</b> These are as published on 16 Oct 2026; whether EIA "
        "revises past weekly prices was not checked.</li>"
        "<li><b>The workbook was opened in LibreOffice, not Excel.</b> Cell values were read from the file with "
        "openpyxl; how Excel displays them was not seen.</li>"
        "<li><b>A rating is the firm's settings applied to a history.</b> It says where +41.49% ranks among "
        "gasoline's own changes, nothing about what it means for borrowers.</li></ul>")
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Tie-out: gasoline change, 16 Oct 2026'
            '</title><style>%s</style></head><body>%s</body></html>' % (CSS, "\n".join(parts)))
    return page


if __name__ == "__main__":
    sys.path.insert(0, str(CANON))
    import check_tie_out
    chrome = sys.argv[sys.argv.index("--chrome") + 1] if "--chrome" in sys.argv else None
    # The HTML the checker renders from goes to a scratch folder: every picture is
    # in it again, and the PDF beside this file is the deliverable.
    check_tie_out.render(build(), HERE / (NAME + ".pdf"), what="the gasoline tie-out", chrome=chrome,
                         scratch=tempfile.mkdtemp(prefix="tie-out-"))
