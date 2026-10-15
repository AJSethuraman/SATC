"""Render the tie-out as one self-contained document (HTML with the pictures
embedded, then PDF): python build_exhibit.py"""
import base64
import html
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
NAME = "TIE-OUT-peer-loan-classes-2026q2"

spec = json.loads((ROOT / "config" / "peer-loan-classes.json").read_text(encoding="utf-8"))
roster = json.loads((HERE / "out" / "roster.json").read_text(encoding="utf-8"))
ours = json.loads((HERE / "out" / "ours.json").read_text(encoding="utf-8-sig"))
quotes = json.loads((HERE / "out" / "quotes.json").read_text(encoding="utf-8"))
words = json.loads((HERE / "out" / "student-words.json").read_text(encoding="utf-8"))
filed = json.loads((HERE / "out" / "filed.json").read_text(encoding="utf-8"))
e = html.escape


def img(name, alt):
    data = base64.b64encode((HERE / "pictures" / name).read_bytes()).decode()
    return '<img alt="%s" src="data:image/png;base64,%s">' % (e(alt), data)


fig = next(r for r in roster["rows"] if r["bank"] == "Citizens" and r["name"] == "Education")
cfg = next(b for b in spec["banks"] if b["short"] == "Citizens")
fact = next(f for f in filed["Citizens"]["facts"]
            if f[0] == sorted(["us-gaap:ConsumerPortfolioSegmentMember", "us-gaap:StudentLoanMember"]))
acc = "0000759944-26-000148"
# The printed row, found on the filed page (not typed): the Education row carrying 8,044 in its Total column.
import sys
sys.path.insert(0, str(HERE))
from compare import find_printed  # noqa: E402
row_text = find_printed((HERE / "out" / "text" / "Citizens.txt").read_text(encoding="utf-8"), "Education", "8,044")
assert row_text, "the Education row carrying 8,044 is not on the filed page"
printed_row = 8044.0
c = roster["count"]

diagram = """<svg viewBox="0 0 940 250" role="img" aria-label="The same figure travels two roads from SEC EDGAR and meets at difference 0">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#16130F"/></marker></defs>
<g font-family="Arial" font-size="12" fill="#16130F">
<rect x="10" y="95" width="130" height="56" rx="4" fill="#F4F1EC" stroke="#57534B"/><text x="75" y="118" text-anchor="middle" font-weight="bold">SEC EDGAR</text><text x="75" y="136" text-anchor="middle">Citizens 10-Q, Q2 2026</text>
<rect x="200" y="20" width="170" height="56" rx="4" fill="#fff" stroke="#57534B"/><text x="285" y="43" text-anchor="middle">extracted XBRL instance</text><text x="285" y="61" text-anchor="middle">cfg-20260630_htm.xml</text>
<rect x="430" y="20" width="170" height="56" rx="4" fill="#fff" stroke="#57534B"/><text x="515" y="43" text-anchor="middle">the tool's cache</text><text x="515" y="61" text-anchor="middle">peers classes-pull</text>
<rect x="660" y="20" width="170" height="56" rx="4" fill="#fff" stroke="#CC0000" stroke-width="2"/><text x="745" y="43" text-anchor="middle" font-weight="bold">Peer loan classes!C%(row)d</text><text x="745" y="61" text-anchor="middle">8,044 (read in Excel)</text>
<rect x="200" y="170" width="170" height="56" rx="4" fill="#fff" stroke="#57534B"/><text x="285" y="193" text-anchor="middle">the 10-Q page as filed</text><text x="285" y="211" text-anchor="middle">cfg-20260630.htm</text>
<rect x="430" y="170" width="170" height="56" rx="4" fill="#fff" stroke="#57534B"/><text x="515" y="193" text-anchor="middle">inline XBRL fact, and</text><text x="515" y="211" text-anchor="middle">the printed row</text>
<rect x="760" y="110" width="170" height="40" rx="4" fill="#E9F1E3" stroke="#57534B"/><text x="845" y="135" text-anchor="middle" font-weight="bold">difference 0</text>
<line x1="140" y1="110" x2="198" y2="55" stroke="#16130F" marker-end="url(#a)"/><line x1="370" y1="48" x2="428" y2="48" stroke="#16130F" marker-end="url(#a)"/><text x="399" y="40" text-anchor="middle" font-size="10">fetched</text>
<line x1="600" y1="48" x2="658" y2="48" stroke="#16130F" marker-end="url(#a)"/><text x="629" y="40" text-anchor="middle" font-size="10">book build</text>
<line x1="140" y1="140" x2="198" y2="192" stroke="#16130F" marker-end="url(#a)"/><line x1="370" y1="198" x2="428" y2="198" stroke="#16130F" marker-end="url(#a)"/><text x="399" y="190" text-anchor="middle" font-size="10">filed.py</text>
<line x1="745" y1="76" x2="800" y2="108" stroke="#16130F" marker-end="url(#a)"/><line x1="600" y1="198" x2="800" y2="152" stroke="#16130F" marker-end="url(#a)"/><text x="700" y="186" text-anchor="middle" font-size="10">compare.py</text>
<text x="420" y="110" text-anchor="middle" font-size="11" fill="#57534B">production road (above): the build's own file and parser</text>
<text x="420" y="128" text-anchor="middle" font-size="11" fill="#57534B">check road (below): a different file, a different parser, fetched fresh</text>
</g></svg>""" % {"row": fig["excel_row"]}

rows = []
for r in roster["rows"]:
    cls = {"TIED": "ok", "DIFFERS": "bad", "COULD NOT": "warn"}[r["verdict"]]
    rows.append("<tr><td>%s</td><td>%s</td><td class=n>%s</td><td class=n>%s</td><td>%s</td><td class=%s>%s</td></tr>" % (
        e(r["bank"]), e(r["name"]), e(r["ours_shown"]),
        "{:,.1f}".format(r["filed"]) if "filed" in r else "", e("XBRL fact" if r["how"].startswith("Read") else
                                                              "printed: " + r.get("evidence", r.get("why", ""))[:90]),
        cls, r["verdict"]))

student_rows = "".join("<tr><td>%s</td><td>%s</td><td class=n>%d</td></tr>" % (
    e(k), "not stated" if v[0] else "stated", v[1]) for k, v in words.items())

doc = """<!doctype html><html><head><meta charset="utf-8"><title>Tie-out: Peer loan classes, 2026Q2</title><style>
@page {{ size: Letter; margin: 12mm 13mm; }}
body {{ font: 10pt/1.42 Calibri, sans-serif; color: #16130F; }}
h1 {{ font: 700 17pt Arial; margin: 0 0 1mm; }} h2 {{ font: 700 12pt Arial; margin: 6mm 0 2mm; border-bottom: 2px solid #0A0908; padding-bottom: 1mm; }}
.sub {{ color: #57534B; border-bottom: 2px solid #CC0000; padding-bottom: 2mm; }}
.verdict {{ font: 700 14pt Arial; background: #E9F1E3; padding: 3mm 4mm; margin: 4mm 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 8.6pt; }} th {{ background: #E4DFD5; text-align: left; padding: 1mm 1.5mm; }}
td {{ border-bottom: 1px solid #EFEBE4; padding: 0.8mm 1.5mm; vertical-align: top; }} .n {{ text-align: right; font-variant-numeric: tabular-nums; }}
.ok {{ color: #1E4637; font-weight: bold; }} .bad {{ color: #960019; font-weight: bold; }} .warn {{ color: #8C5A00; font-weight: bold; }}
pre {{ background: #F4F1EC; padding: 2mm; font: 8pt Consolas; white-space: pre-wrap; word-break: break-all; }}
.cmp {{ font: 10pt Consolas; background: #F4F1EC; padding: 3mm; white-space: pre; }}
img {{ max-width: 100%; border: 1px solid #B9B4AC; }} .cap {{ color: #57534B; font-size: 9pt; margin: 1mm 0 3mm; }}
.cite {{ display: grid; grid-template-columns: 34mm 1fr; gap: 0.5mm 3mm; font-size: 9.4pt; }} .cite b {{ color: #57534B; }}
</style></head><body>
<h1>Tie-out: Peer loan classes, quarter ended 30 June 2026</h1>
<div class="sub">Every class amount on the workbook's Peer loan classes tab, read out of Excel, against each bank's own 10-Q as filed with the SEC. Built 15 Oct 2026 by threshold-engine (PR #442).</div>
<div class="verdict">Tied out: {tied} of {total} class amounts. TIED {tied} &middot; DIFFERS {differs} &middot; COULD NOT {could}</div>
<p>Workbook: <code>{wbfile}</code>, opened in Excel {excel} after a full recalculation; the tab has {err} error cells. Every one of the {nq} quotes behind the findings was found word for word in the filed text; {ns} findings say "not stated" and are listed as searches, not as proof of zero.</p>

<h2>1 &middot; How the dots connect</h2>
{diagram}
<p class="cap">The same fact travels two roads. Only the lower one is the check: it reads the 10-Q document the reader sees, fresh from SEC, with its own parser, so a fault in the build's pull or parser would show as a difference. Both roads start at a document neither the bank's analyst nor this tool controls.</p>

<h2>2 &middot; One figure, traced end to end: Citizens' student loans, $8,044 million</h2>
<p><b>Link 1, the figure.</b> On the Peer loan classes tab, row {row}, "Education", $ millions: Excel shows <b>{shown}</b> (value {val}). Read by <code>read_workbook.ps1</code> through Excel itself, not by reading the file's XML.</p>
<p><b>Link 2, the call.</b> The tool's pull, <code>peers classes-pull</code>, made these requests (SEC requires a contact in the User-Agent header):</p>
<pre>GET https://data.sec.gov/submissions/CIK0000759944.json      → 10-Q, report date 2026-06-30, accession {acc}, filed 2026-08-03
GET https://www.sec.gov/Archives/edgar/data/759944/000075994426000148/index.json
GET https://www.sec.gov/Archives/edgar/data/759944/000075994426000148/cfg-20260630_htm.xml   (the extracted XBRL instance)
GET https://www.sec.gov/Archives/edgar/data/759944/000075994426000148/cfg-20260630_lab.xml   (its labels)</pre>
<p><b>Link 3, the derivation.</b> In the instance, the fact <code>us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss</code> (loans at amortized cost, before the allowance) whose context is the instant 2026-06-30 and whose only dimensions are <code>us-gaap:ConsumerPortfolioSegmentMember</code> and <code>us-gaap:StudentLoanMember</code> holds 8,044,000,000. Divided by 1,000,000: 8,044. Nothing else is done to it. Which members make "Education" is stated in <code>config/peer-loan-classes.json</code> (Citizens, its first class), as is that it counts as Student.</p>
<p><b>Link 4, the independent source.</b> Citizens Financial Group, Inc., Form 10-Q for the quarter ended June 30, 2026, accession {acc}, filed 3 Aug 2026: {url}. Anyone can open it; nothing about it is ours.</p>
{cover}
<p class="cap">The filed 10-Q's cover, as Chrome renders the document SEC serves: Form 10-Q, quarterly period ended June 30, 2026, ticker CFG, One Citizens Plaza, Providence.</p>
{table}
<p class="cap">The filed table, cut out of the same document with its own styling; the red outline is the only thing added. It is the past-due table of the credit quality note: Education's Total column is the class's amortized cost.</p>
{zoom}
<div class="cite"><b>Schedule</b><span>Notes to the financial statements, credit quality: loans by days past due, June 30, 2026</span><b>Row</b><span>Education (under Total retail)</span><b>Column</b><span>Total</span><b>Units</b><span>$ millions ("dollars in millions")</span><b>Also printed</b><span>MD&A Table 5, Composition of Loans and Leases: Education 8,044 (the same figure, a second printing)</span><b>Inline XBRL</b><span>the filed page tags it as {concept}, shown as "{fshown}", members as above</span></div>
<p><b>Link 5, the comparison.</b> Written before the verdict and read off it:</p>
<div class="cmp">ours    Peer loan classes!C{row}, read in Excel                       {ours:>10,.0f}
source  10-Q as filed, inline XBRL fact (members as above)          {fv:>10,.0f}
source  10-Q as filed, printed row "Education", column Total        {pv:>10,.0f}
diff                                                                {diff:>10,.0f}</div>
<p>Same entity (Citizens Financial Group, Inc., the holding company: the tab says so), same date (30 June 2026), same basis (amortized cost, before the allowance), same units ($ millions). <b>TIED.</b></p>

<h2>3 &middot; The roster: every class on the tab</h2>
<table><tr><th>Bank</th><th>Class, as on the tab</th><th class=n>Workbook (Excel)</th><th class=n>Filing</th><th>How the filing was read</th><th>Verdict</th></tr>
{rows}</table>
<p class="cap">"XBRL fact": the class's amount is compared with the inline XBRL fact of the same members in the filed document. "Printed": the class is not tagged by class, so the filed page was searched for a table row with the class's label carrying the printed figure (the row is quoted), or, for a figure printed in a sentence, for the sentence. SoFi prints thousands; Bank of America and Fifth Third's RV and marine print billions in a sentence.</p>

<h2>4 &middot; How to run it yourself</h2>
<p>From <code>threshold-engine</code>, with Python 3.9 or later and Excel. Put your own name and email in place of the contact (SEC refuses requests without one; it is not stored).</p>
<pre>python -m threshold_engine peers classes-pull --cache books/sec_cache --classes config/peer-loan-classes.json --quarter 2026Q2 --user-agent "Your Name you@yourbank.com"</pre>
<pre>python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx</pre>
<pre>cd docs/tie-out/peer-loan-classes-2026q2
powershell -File read_workbook.ps1 -Path ..\\..\\..\\consumer-credit.xlsx -Out out\\ours.json</pre>
<pre>set SEC_USER_AGENT=Your Name you@yourbank.com
python filed.py ../../../config/peer-loan-classes.json out/filed.json</pre>
<pre>python compare.py ../../../config/peer-loan-classes.json out/ours.json out/filed.json out/roster.json</pre>
<p>The last prints "Tied out: N of 33" and every row that is not TIED, with why. To check one figure by hand: open the 10-Q link above, find the table in the photograph, and read the Education row's Total.</p>

<h2>5 &middot; What it found</h2>
<ul>
<li><b>The filings settle who holds student loans.</b> Citizens (Education, $8,044m) and SoFi ($16,921m, at fair value) carry them as classes of their own; PNC folded education loans into Other consumer on 1 Jan 2026 "based on materiality considerations", with no amount; KeyCorp holds $182m in discontinued operations, outside loans, and names student loan refinancing among its products. Capital One's 10-Q says Discover "sold its student loan portfolio" before the merger closed. The word "student" does not appear at all in the other twelve 10-Qs (table below).</li>
<li><b>One bank is a clean comparison for unsecured lending: Capital One</b> (Personal loans, $8,619m, its own class; its Call Report other consumer is these loans). Fifth Third splits out its unsecured loans ($626m, Table 44) and its solar loans ($4,314m, counted as unsecured by the analyst's ruling), but together they are about half its Call Report other consumer ($10.2bn average); the rest is RV and marine, other secured and point-of-sale, so its rate is not an unsecured rate. Every other bank's other consumer mixes unsecured lending with student, secured or undefined lending, or is mostly something else (M&T's recreational finance, Wells Fargo's and Bank of America's securities-based lending, SoFi's fair-value loans).</li>
<li><b>The readers missed two sentences, and this tie-out found them.</b> The three agents that read the filings recorded "not stated" for KeyCorp's secured non-auto lending and Capital One's student loans. The tie-out's own search of the filed text found "Our consumer loans have collateral that includes residential real estate, automobiles, boats, and RVs." (KeyCorp) and the Discover sentence (Capital One). Both findings were corrected before this build.</li>
</ul>
<table><tr><th>Bank</th><th>Student finding</th><th class=n>"student" in the filed 10-Q</th></tr>{student_rows}</table>

<h2>6 &middot; What I got wrong</h2>
<ul>
<li>The first comparison showed 3 DIFFERS: Fifth Third's RV and marine and Bank of America's two sentence figures. The fault was in the comparison script, not the workbook: it multiplied "$2.8 billion" by the whole amount instead of by $1,000 million a billion. Corrected; the workbook did not change.</li>
<li>The first photograph of the Citizens table came out blank: the 10-Q does not render scrolled in headless Chrome. The table is now cut out of the filed document and rendered alone, with its own styling.</li>
<li>I first marked Fifth Third a clean comparison for unsecured lending. That held for its balance split, not its loss rate: its Call Report other consumer is $10.2bn, of which $626m is unsecured. Corrected to Mixed.</li>
<li>Two findings the readers recorded as "not stated" were wrong (section 5): I had taken their records as the record. Every quote and every "not stated" is now checked against the filed text by the tie-out itself.</li>
</ul>

<h2>7 &middot; What this does not prove</h2>
<ul>
<li><b>What a class is counted as is a judgment.</b> The amounts tie to the filings; "counted as" does not tie to anything. Where a filing does not define a class (KeyCorp's Other consumer loans, Truist's Other consumer, M&amp;T's Other, U.S. Bank's Installment), its contents are unknown and the tab says Mixed.</li>
<li><b>"Not stated" is a search, not a zero.</b> It means the terms named were looked for in the 10-Q and not found. A bank can hold a small book it does not mention.</li>
<li><b>Holding company, not bank.</b> The 10-Q is the holding company's; the Call Report's other consumer is the bank's. For consumer loans they are close but they were not reconciled here.</li>
<li><b>A printed figure is matched by its row's label and number</b>, not by the table's title: a same-labeled row elsewhere in the filing carrying the same number would also pass. Each matched row is quoted in the roster so a reader can see which.</li>
<li><b>One quarter.</b> The tab is for 30 June 2026; next quarter's filings need the pull run again, and a bank that changes its classes needs its entry in the file changed.</li>
</ul>
</body></html>""".format(
    tied=c["TIED"], differs=c["DIFFERS"], could=c["COULD NOT"], total=roster["total"], wbfile=e(ours["file"]),
    excel=ours["excel"], err=ours["errors"], nq=quotes["found"], ns=quotes["not_stated"], diagram=diagram,
    row=fig["excel_row"], shown=e(fig["ours_shown"]), val=fig["ours"], acc=acc, url=e(cfg["filing_url"]),
    cover=img("source-cover.png", "The filed 10-Q's cover"), table=img("source-table.png", "The filed table, Education ringed"),
    zoom=img("source-row-zoom.png", "The Education row, enlarged"),
    concept="us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss", fshown=e(fact[2]),
    ours=fig["ours"], fv=fig["filed"], pv=printed_row, diff=fig["ours"] - fig["filed"], rows="\n".join(rows), student_rows=student_rows)

out = HERE / (NAME + ".html")
out.write_text(doc, encoding="utf-8")
subprocess.run([CHROME, "--headless=new", "--no-pdf-header-footer", "--print-to-pdf=%s" % (HERE / (NAME + ".pdf")),
                out.as_uri()], check=True, capture_output=True)
print("wrote", out, "and the PDF")
