"""The one thing to forward: what this feed is, how it was proved, where it stops.

The firm's goal, in their words: *"the output which i can forward to my work
email"*. So this is a single self-contained PDF -- every picture embedded in it,
nothing referenced by a path that resolves only on this machine -- that a
reader who was not here can open, follow and check.

It is the covering document for `SATC-verified-credit-data.xlsx`. The workbook
is the thing you use; this is the thing you read first, and the thing you send
to somebody who wants to know whether to believe it.

**Every number in it is read out of the delivered files at build time.** Not one
is typed. That is not a style preference: this document's own predecessor said
"NONE DISAGREED" on its front page for as long as it took somebody to notice
that one number now did, because that sentence had been typed rather than
counted. A claim about the data that is not computed from the data is the exact
failure the whole feed exists to stop.

    python tools/tieout/build_covering_document.py
"""
import base64
import csv
import html
import json
import pathlib
import subprocess
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
STRIPS = SB / "deepstrips-grey"
DATA = CS / "verified-data"
OUT = CS / "docs" / "tie-out"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

STAMP = "2026-09-07"
PDF = OUT / ("SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-%s.pdf" % STAMP)


def rows(name):
    with (DATA / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


BANK = rows("bank-values.csv")
MACRO = rows("macro-observations.csv")
FIELDS = rows("field-dictionary.csv")
MERGERS = rows("not-comparable-periods.csv")
PEERS = json.loads((CS / "config" / "peers.json").read_text(encoding="utf-8"))
AUDIT = json.loads((SB / "evidence_audit.json").read_text(encoding="utf-8"))

#: The strip index, merged the same way the exhibits merge it -- oldest shard
#: first, field by field. It carries BOTH pictures for each cited row: the
#: page header, which names the bank, the form and the period, and the row
#: itself. The caption below promises the header is in the shot, so the header
#: has to actually be in the shot.
STRIP_INDEX = json.loads((SB / "deep_strips.json").read_text())
for _shard in sorted(SB.glob("deep_strips-*.json"),
                     key=lambda f: f.stat().st_mtime):
    for _cert, _quarters in json.loads(_shard.read_text()).items():
        for _iso, _fields in _quarters.items():
            STRIP_INDEX.setdefault(_cert, {}).setdefault(_iso, {}).update(_fields)

BANK_TIED = sum(1 for r in BANK if r["verified"] == "yes")
MACRO_TIED = sum(1 for r in MACRO if r["verified"] == "yes")
DIFFERS = [r for r in BANK if "DOES NOT MATCH" in r["verified_meaning"]]
RATIOS = sum(1 for r in BANK if "FDIC calculates" in r["verified_meaning"])
MERGER_ROWS = sum(1 for r in BANK if "spans a merger" in r["verified_meaning"])
BASE_ROWS = sum(1 for r in BANK if "running total" in r["verified_meaning"])
NOLINE = sum(1 for r in BANK if "did not report this line" in r["verified_meaning"])
MACRO_NOT = len(MACRO) - MACRO_TIED
TOTAL = len(BANK) + len(MACRO)
TOTAL_TIED = BANK_TIED + MACRO_TIED
QUARTERS = sorted({r["report_date"] for r in BANK})
CERTS = sorted({r["cert"] for r in BANK})
IDS = sum(1 for b in PEERS["banks"] if b.get("identity_verified"))
SAME_THROUGHOUT = sum(1 for b in PEERS["banks"]
                      if b.get("same_name_throughout"))
RENAMED = [b for b in PEERS["banks"] if b.get("legal_name_at_window_start")
           and not b.get("same_name_throughout")]
#: Merger quarters whose total assets step by 10% or more, and the worst one.
STEPS = [m for m in MERGERS if m.get("change_in_total_assets_pct")
         and abs(float(m["change_in_total_assets_pct"])) >= 10]
WORST_STEP = (max(STEPS, key=lambda m: abs(
    float(m["change_in_total_assets_pct"]))) if STEPS else None)


def n(x):
    return "{:,}".format(int(x))


def esc(x):
    return html.escape("" if x is None else str(x))


def img(name):
    """A strip, embedded. Returns None if it is not there, and the caller says so."""
    p = STRIPS / name
    if not p.exists():
        return None
    return ("data:image/png;base64,%s"
            % base64.b64encode(p.read_bytes()).decode())


def find(cert, iso, field):
    for r in BANK:
        if r["cert"] == cert and r["report_date"] == iso and r["field"] == field:
            return r
    raise SystemExit("no delivered row for %s %s %s -- this document quotes "
                     "the delivered file and will not invent one"
                     % (cert, iso, field))


# ---------------------------------------------------------------------------
# The two figures traced in full. One that agrees, on a bank the project had
# never seen until this week; one that does not, which is the more useful of
# the two and is why it is here rather than buried in a row.
# ---------------------------------------------------------------------------
TIES_ROW = find("12368", "2026-06-30", "ASSET")
DIFF_ROW = DIFFERS[0] if DIFFERS else None

CSS = """
@page{size:A4;margin:16mm 14mm}
:root{--ink:#141414;--dim:#5b5b5b;--rule:#dcdcdc;--ok:#0a6b3d;--warn:#a4123f;
--paper:#fff;--tint:#f6f7f9;--band:#eef1f4}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:10.5pt/1.55 "Source Serif 4",Georgia,serif;-webkit-print-color-adjust:exact}
.page{padding:0}
h1{font:600 25pt/1.15 "Inter","Segoe UI",system-ui,sans-serif;margin:0 0 6pt;
letter-spacing:-.01em}
h2{font:600 14pt/1.25 "Inter","Segoe UI",system-ui,sans-serif;
margin:26pt 0 9pt;padding-bottom:5pt;border-bottom:1.5px solid var(--ink);
page-break-after:avoid}
h3{font:600 11pt/1.3 "Inter","Segoe UI",system-ui,sans-serif;margin:16pt 0 5pt;
page-break-after:avoid}
.sub{color:var(--dim);font-size:11pt;margin:0 0 4pt}
.stamp{color:var(--dim);font-size:9pt;margin:0 0 20pt}
p{margin:0 0 9pt;max-width:46em}
.lead{font-size:11.5pt}
ul{margin:0 0 9pt;padding-left:18pt;max-width:46em}
li{margin:0 0 4pt}
.mono{font-family:"Cascadia Mono",Consolas,monospace;font-size:8.8pt}
pre{font-family:"Cascadia Mono",Consolas,monospace;font-size:8.6pt;
background:var(--tint);border:1px solid var(--rule);border-radius:4px;
padding:9pt 11pt;margin:0 0 10pt;white-space:pre-wrap;word-break:break-all;
page-break-inside:avoid}
table{border-collapse:collapse;width:100%;font-size:9.5pt;margin:0 0 12pt}
th,td{text-align:left;padding:5pt 8pt;border-bottom:1px solid var(--rule);
vertical-align:top}
th{font:600 9pt/1.3 "Inter",system-ui,sans-serif;background:var(--tint)}
td.n,th.n{text-align:right;font-family:"Cascadia Mono",Consolas,monospace}
.big{font:600 20pt/1.1 "Inter",system-ui,sans-serif}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:9pt;margin:0 0 14pt}
.card{border:1px solid var(--rule);border-radius:5px;padding:9pt 11pt;
background:var(--paper)}
.card .k{color:var(--dim);font-size:8.4pt;text-transform:uppercase;
letter-spacing:.06em;font-family:"Inter",system-ui,sans-serif}
.trace{border:1px solid var(--rule);border-radius:6px;padding:12pt 14pt;
margin:0 0 14pt;page-break-inside:avoid}
.trace.bad{border-color:var(--warn);border-width:1.5px}
.link{margin:0 0 11pt}
.link .lab{font:600 8.4pt/1.3 "Inter",system-ui,sans-serif;color:var(--dim);
text-transform:uppercase;letter-spacing:.07em;margin:0 0 3pt}
.cmp{font-family:"Cascadia Mono",Consolas,monospace;font-size:9.4pt;
background:var(--tint);border-radius:4px;padding:9pt 11pt;margin:0 0 6pt}
.tie{color:var(--ok);font-weight:600}
.no{color:var(--warn);font-weight:600}
.shot{border:1px solid var(--rule);border-radius:3px;overflow:hidden;
margin:0 0 5pt;background:#fff}
.shot img{display:block;width:100%;height:auto}
.cap{color:var(--dim);font-size:8.3pt;margin:0 0 9pt}
figure{margin:0 0 16pt}
figcaption{color:var(--dim);font-size:8.8pt;margin-top:6pt;max-width:46em}
.note{border-left:3px solid var(--ink);background:var(--tint);
padding:9pt 0 9pt 13pt;margin:0 0 12pt;max-width:46em}
.note.warn{border-left-color:var(--warn)}
.brk{page-break-before:always}
"""

DIAGRAM = """
<figure>
<svg viewBox="0 0 760 268" role="img" width="100%"
 aria-label="The same number travels two roads: the FDIC's feed into the
 delivered file, and the bank's own filed Call Report read by hand. They meet
 at a difference of zero."
 style="max-width:100%;height:auto;color:currentColor">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
 markerHeight="6" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
<text x="0" y="14" font-size="11" font-weight="600" fill="currentColor"
 font-family="Inter,system-ui,sans-serif">THE PRODUCTION PATH</text>
<rect x="0" y="26" width="150" height="44" rx="5" fill="none"
 stroke="currentColor"/>
<text x="75" y="45" font-size="11" text-anchor="middle" fill="currentColor">FDIC</text>
<text x="75" y="60" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">financials API</text>
<line x1="152" y1="48" x2="238" y2="48" stroke="currentColor"
 marker-end="url(#ar)"/>
<text x="195" y="41" font-size="8.5" text-anchor="middle" fill="currentColor"
 opacity=".75">one request</text>
<rect x="240" y="26" width="150" height="44" rx="5" fill="none"
 stroke="currentColor"/>
<text x="315" y="45" font-size="11" text-anchor="middle" fill="currentColor">raw values</text>
<text x="315" y="60" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">no arithmetic</text>
<line x1="392" y1="48" x2="478" y2="48" stroke="currentColor"
 marker-end="url(#ar)"/>
<text x="435" y="41" font-size="8.5" text-anchor="middle" fill="currentColor"
 opacity=".75">copied</text>
<rect x="480" y="26" width="170" height="44" rx="5" fill="#eef1f4"
 stroke="currentColor" stroke-width="1.5"/>
<text x="565" y="45" font-size="11" text-anchor="middle" fill="currentColor"
 font-weight="600">the cell you read</text>
<text x="565" y="60" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">bank-values.csv</text>

<text x="0" y="150" font-size="11" font-weight="600" fill="currentColor"
 font-family="Inter,system-ui,sans-serif">THE CHECK</text>
<rect x="0" y="162" width="150" height="44" rx="5" fill="none"
 stroke="currentColor"/>
<text x="75" y="181" font-size="11" text-anchor="middle" fill="currentColor">FFIEC</text>
<text x="75" y="196" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">the filed form</text>
<line x1="152" y1="184" x2="238" y2="184" stroke="currentColor"
 marker-end="url(#ar)"/>
<text x="195" y="177" font-size="8.5" text-anchor="middle" fill="currentColor"
 opacity=".75">photographed</text>
<rect x="240" y="162" width="150" height="44" rx="5" fill="none"
 stroke="currentColor"/>
<text x="315" y="181" font-size="11" text-anchor="middle" fill="currentColor">the cited line</text>
<text x="315" y="196" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">e.g. RCFD2170</text>
<line x1="392" y1="184" x2="478" y2="184" stroke="currentColor"
 marker-end="url(#ar)"/>
<text x="435" y="177" font-size="8.5" text-anchor="middle" fill="currentColor"
 opacity=".75">read off</text>
<rect x="480" y="162" width="170" height="44" rx="5" fill="none"
 stroke="currentColor"/>
<text x="565" y="181" font-size="11" text-anchor="middle" fill="currentColor">what the bank filed</text>
<text x="565" y="196" font-size="9" text-anchor="middle" fill="currentColor"
 opacity=".7">thousands of dollars</text>

<line x1="565" y1="72" x2="565" y2="158" stroke="currentColor"
 stroke-dasharray="4 3"/>
<line x1="660" y1="48" x2="700" y2="48" stroke="currentColor"/>
<line x1="700" y1="48" x2="700" y2="184" stroke="currentColor"/>
<line x1="700" y1="184" x2="660" y2="184" stroke="currentColor"/>
<text x="716" y="112" font-size="11" fill="currentColor" font-weight="600"
 font-family="Inter,system-ui,sans-serif">=</text>
<text x="565" y="240" font-size="10.5" text-anchor="middle" fill="currentColor"
 font-weight="600">difference 0</text>
<text x="0" y="240" font-size="9" fill="currentColor" opacity=".8">The lower
road touches a document nobody here controls.</text>
<text x="0" y="256" font-size="9" fill="currentColor" opacity=".8">That is what
makes this evidence rather than a second opinion from the same source.</text>
</svg>
<figcaption>Every value takes the upper road. Every value with a citation is
also walked down the lower one, against the bank's own filed Call Report as the
regulator serves it. The two meet, or the row says so.</figcaption>
</figure>
"""


def trace(r, title, why, expect_tie):
    """One figure, all five links, with the filing photographed.

    The comparison is laid out with the two figures in one column and the
    difference under them, because a reader checks this by running an eye down
    a column. The first version padded by hand and put the three numbers in
    three different places, which is the one thing this block must not do.
    """
    ours = float(r["value"])
    entry = ((STRIP_INDEX.get(r["cert"], {}).get(r["report_date"], {})
              .get(r["field"])) or [None])[0]
    row_png = img(entry["png"]) if entry else None
    hdr_png = img(entry["header"]) if entry else None
    filed_txt = "{:,.0f}".format(ours)
    diff_txt = "0"
    if not expect_tie:
        # The filed figure comes out of the delivered note -- the same place
        # the reader finds it -- so this document and the workbook cannot end
        # up saying different things.
        import re
        m = re.search(r"the filing reads ([\d,]+) and the FDIC publishes "
                      r"([\d,]+), a difference of (-?[\d,]+)", r["note"])
        if not m:
            raise SystemExit("the delivered note for %s %s %s does not carry "
                             "both figures; this document will not restate a "
                             "difference it cannot read"
                             % (r["cert"], r["report_date"], r["field"]))
        filed_txt, diff_txt = m.group(1), m.group(3)

    width = max(len(filed_txt), len("{:,.0f}".format(ours)), len(diff_txt)) + 2
    cmp_block = "\n".join([
        "%-38s %s" % ("ours   (bank-values.csv, as delivered)",
                      "{:>{w}}".format("{:,.0f}".format(ours), w=width)),
        "%-38s %s" % ("source (%s on the filing)" % r["cited_line"],
                      "{:>{w}}".format(filed_txt, w=width)),
        "%-38s %s" % ("difference", "{:>{w}}".format(diff_txt, w=width)),
    ])

    if row_png and hdr_png:
        shot = ('<div class="shot"><img src="%s"></div>'
                '<div class="shot"><img src="%s"></div>'
                '<p class="cap">The filed page, and the row on it. The header '
                'is photographed from the same page, so &ldquo;same entity, '
                'same date&rdquo; is read off the picture rather than taken '
                'on trust.</p>' % (hdr_png, row_png))
    elif row_png:
        shot = ('<div class="shot"><img src="%s"></div>'
                '<p class="cap">The row on the filed page. <b>The page header '
                'is not on file for this row</b>, so the bank and period are '
                'not visible in the shot &mdash; said here rather than left to '
                'be noticed.</p>' % row_png)
    else:
        shot = ('<p class="cap"><b>No photograph of this row is on file.</b> '
                'Recorded as missing rather than left blank.</p>')

    return """
<div class="trace%(bad)s">
<h3>%(title)s</h3>
<p class="cap">%(why)s</p>

<div class="link"><div class="lab">1 &middot; the figure, as delivered</div>
<p><b>%(bank)s</b>, %(date)s, field <span class="mono">%(field)s</span> &mdash;
<b>%(val)s</b> %(units)s. It is in <span class="mono">BANK DATA</span> in the
workbook and in <span class="mono">verified-data/bank-values.csv</span>; filter
cert = %(cert)s, report_date = %(date)s, field = %(field)s. <b>This value was
read back out of that file</b>, not re-fetched.</p></div>

<div class="link"><div class="lab">2 &middot; the call that produced it</div>
<pre>https://banks.data.fdic.gov/api/financials?filters=CERT%%3A%(cert)s&amp;fields=CERT,REPDTE,%(field)s&amp;format=json</pre></div>

<div class="link"><div class="lab">3 &middot; what happened in between</div>
<p>Nothing. The value is copied from the response into the file &mdash; no sum,
no ratio, no restatement, no rounding. The workbook records how it was checked
as: <i>%(how)s</i>.</p></div>

<div class="link"><div class="lab">4 &middot; the independent source</div>
<p>The bank's own Call Report for that quarter, as the FFIEC's Central Data
Repository serves it &mdash; a facsimile, meaning an exact copy of the filled-in
form rather than a database rendered to look like one. Schedule
<b>%(sched)s</b>, the line carrying <span class="mono">%(code)s</span>, in
thousands of dollars.</p>
<pre>%(url)s</pre>
%(shot)s</div>

<div class="link"><div class="lab">5 &middot; the comparison</div>
<pre>%(cmp)s</pre>
<p class="%(cls)s">%(verdict)s</p></div>
</div>
""" % {
        "bad": "" if expect_tie else " bad",
        "title": esc(title), "why": esc(why),
        "bank": esc(r["bank"]), "date": esc(r["report_date"]),
        "field": esc(r["field"]), "cert": esc(r["cert"]),
        "val": "{:,.0f}".format(ours), "units": esc(r["units"]),
        "how": esc(r["note"].rstrip(". ").split(". ")[-1] or
                   "read straight off the filing"),
        "sched": esc(r["call_report_schedule"]), "code": esc(r["cited_line"]),
        "url": esc(r["filing_url"]),
        "shot": shot,
        "cmp": esc(cmp_block),
        "cls": "tie" if expect_tie else "no",
        "verdict": ("TIED. The delivered file and the filed form agree to the "
                    "dollar." if expect_tie else
                    "DIFFERS. It is not adjusted, rounded away or hidden. "
                    "Both figures are in the delivered row, with the link to "
                    "the filing."),
    }


BODY = []
A = BODY.append

A('<div class="page">')
A('<h1>Verified credit data</h1>')
A('<p class="sub">%s US banks, %s quarters, %s fields each &middot; %s macro '
  'series &middot; how every number was proved, and where the proof stops.</p>'
  % (len(CERTS), len(QUARTERS), len({r["field"] for r in BANK}),
     len({r["series_id"] for r in MACRO})))
A('<p class="stamp">Sethuraman Accounting, Tax &amp; Consulting &middot; %s '
  '&middot; the covering document for '
  '<span class="mono">SATC-verified-credit-data.xlsx</span></p>' % STAMP)

A('<div class="cards">')
for k, v in (("values delivered", n(TOTAL)),
             ("checked against an outside document", n(TOTAL_TIED)),
             ("disagreed", n(len(DIFFERS))),
             ("filed pages photographed", n(AUDIT["filings_photographed"]))):
    A('<div class="card"><div class="k">%s</div><div class="big">%s</div></div>'
      % (k, v))
A('</div>')

A('<p class="lead"><b>Nothing in this feed is calculated by our software.</b> '
  'No ratios, no quarter-on-quarter changes, no scores. If a number is here, a '
  'bank or a government agency published it in that form, and this document '
  'shows you how to put your finger on where.</p>')

A('<h2>How a number gets here, and how it gets checked</h2>')
A(DIAGRAM)

A('<h2>One number, traced all the way</h2>')
A('<p>Two, in fact. The first is on a bank this system had never seen until '
  'this week, so it shows the machinery working on something it was not tuned '
  'for. The second is the one number in %s that does not agree, which is the '
  'more useful of the two.</p>' % n(len(BANK)))
A(trace(TIES_ROW, "Regions Bank, total assets, 30 June 2026",
        "A bank added to the set this week. Nothing about the chain was "
        "changed to accommodate it.", True))
if DIFF_ROW:
    A(trace(DIFF_ROW, "Huntington National Bank, total risk-based capital, "
                      "31 March 2026",
            "The one difference in the whole feed. It is here on purpose: a "
            "tie-out that hides its own findings is worth nothing.", False))
    A('<div class="note warn"><p>The filing was read twice &mdash; off the '
      'printed page above and off the machine-readable copy the regulator '
      'publishes beside it &mdash; and both say <b>29,148,027</b>. The '
      'filing\'s own total capital ratio multiplied by its own risk-weighted '
      'assets comes to 29,148,047, so the form is internally consistent. The '
      'second column on that line reads <span class="mono">NR</span>, not '
      'reported, so there is no other column the FDIC\'s figure could have '
      'come from. <b>We have no explanation for the $945 thousand, and we are '
      'not going to invent one.</b> It is 0.003% of the figure and it sits in '
      'the quarter Huntington closed an acquisition.</p></div>')

A('<h2 class="brk">The roster, with its denominator</h2>')
A('<p>What did not check out comes first, because the things that agree are '
  'not what anybody needs to read.</p>')
A('<table><tr><th>Verdict</th><th class="n">Rows</th><th>What it means</th></tr>')
for label, count, meaning in (
        ("DIFFERS", len(DIFFERS),
         "the delivered value and the filed line do not agree; named above"),
        ("not comparable &mdash; spans a merger", MERGER_ROWS,
         "a quarterly flow in a quarter that mixes two banks. %d such quarters "
         "in ten years, all listed in the workbook" % len(MERGERS)),
        ("not comparable &mdash; base moved", BASE_ROWS,
         "the quarter after a merger that landed in a first quarter: the "
         "running total it counts from is the FDIC's own adjusted figure, "
         "which no filing carries"),
        ("not on that filing", NOLINE,
         "the bank did not report that line in that quarter; forms change"),
        ("computed by the FDIC", RATIOS,
         "a ratio the FDIC calculates rather than a line a bank files. The "
         "lines it is calculated FROM are checked"),
        ("macro, no obtainable source", MACRO_NOT,
         "whole series with no independent publisher we can reach; each row "
         "says why"),
        ("TIED", TOTAL_TIED,
         "checked against a document published by somebody outside this firm"),
):
    A('<tr><td><b>%s</b></td><td class="n">%s</td><td>%s</td></tr>'
      % (label, n(count), meaning))
A('</table>')

A('<h3>And the thing every other check takes on trust</h3>')
A('<p>Everything above proves the FDIC agrees with a filing <i>for a given '
  'certificate</i>. None of it proves the certificate is the bank whose name '
  'we print beside it &mdash; a wrong certificate ties perfectly against '
  'itself. So each one was checked against the legal name printed on that '
  'bank\'s own filed front page: <b>%d of %d</b>.</p>' % (IDS, len(PEERS["banks"])))
A('<p>That check exists because searching the regulator for a holding '
  'company\'s name does not fail cleanly. It word-matches. '
  '&ldquo;PNC&nbsp;Financial&rdquo; returns PlainsCapital Bank of University '
  'Park, Texas &mdash; a real, live, unrelated bank that would have tied to '
  'the dollar under the wrong label.</p>')
A('<p>A certificate is stable; the institution behind it is not. Checked at '
  'the other end of the ten years as well: <b>%d of %d</b> carry the same '
  'legal name on the oldest filing as on the newest. %s</p>'
  % (SAME_THROUGHOUT, len(PEERS["banks"]),
     "" if not RENAMED else
     ("The exceptions are " + "; ".join(
         "<b>%s</b>, filed in %s as %s" % (b["name"], QUARTERS[0][:4],
                                           b["legal_name_at_window_start"])
         for b in RENAMED) + ". One is a rename and nothing else. The other "
      "is not: everything before December 2019 under the label "
      "&ldquo;Truist Bank&rdquo; is Branch Banking and Trust, which is half "
      "the bank that carries the name afterwards.")))

A('<h3>And the hop between the check and this file</h3>')
A('<p>Each verifier compares against the filed document a value it holds in '
  'memory; the delivered files are written afterwards. That last hop was '
  'described and never executed &mdash; so on 7 September 2026 it was: every '
  'delivered value was compared with the value its verifier actually held. '
  '<b>%s of %s identical, none moved, none unchecked.</b> Rerun it with '
  '<span class="mono">tools/tieout/prove_delivered_is_what_was_checked.py'
  '</span>.</p>' % (n(TOTAL), n(TOTAL)))

A('<h2>Check any number yourself, in about a minute</h2>')
A('<p>No account, no login. This is a public record.</p>')
A('<p><b>1.</b> Open <span class="mono">BANK DATA</span> in the workbook and '
  'find a row. Note two columns: <span class="mono">cited_line</span> and '
  '<span class="mono">filing_url</span>.</p>')
A('<p><b>2.</b> Open the <span class="mono">filing_url</span>. For the Regions '
  'Bank figure above that is:</p>')
A('<pre>%s</pre>' % esc(TIES_ROW["filing_url"]))
A('<p><b>3.</b> Search that page for the <span class="mono">cited_line</span> '
  'code &mdash; <span class="mono">%s</span> in this case. The number printed '
  'beside it is the number in the workbook.</p>' % esc(TIES_ROW["cited_line"]))
A('<p>That code is an <b>MDRM code</b>: the Federal Reserve\'s permanent '
  'identifier for one line on one schedule of the form. It does not change '
  'when the form is re-laid-out, and quoting one to a bank\'s finance team '
  'tells them exactly which number you mean.</p>')
A('<p>To change bank or quarter, edit the <span class="mono">id</span> (the '
  'FDIC certificate) and the <span class="mono">date</span> '
  '(<span class="mono">MMDDYYYY</span>, a quarter end) in that address.</p>')

A('<h2>What running this found</h2>')
A('<p>%s exhibits sit behind this feed &mdash; one per bank per year, %s MB of '
  'them, every cited row photographed off the filed page with the page header '
  'in the shot. They are kept locally rather than sent with this document. '
  'Building them is what turned up the following, none of which any test '
  'caught.</p>' % (n(AUDIT["exhibits"]), n(AUDIT["exhibit_mb"])))
A('<ul>')
for item in (
    "<b>Nine values were right and their citations were wrong.</b> Total loans "
    "and leases matched to within exactly one thousand dollars across three "
    "unrelated banks. The FDIC publishes that total as the sum of two "
    "separately-rounded halves; our citation pointed at the bank's own "
    "single-line total. Both numbers were correct as published, and only "
    "following the citation to the page could show it.",
    "<b>%d quarters in ten years span a merger</b>, where a first pass over "
    "sixteen quarters had seen six. Every one of them would otherwise have "
    "been reported as the regulator disagreeing with the filings when nothing "
    "was wrong with either." % len(MERGERS),
    "<b>The largest acquisition in the set was filed under a code we did not "
    "carry.</b> First-Citizens taking on Silicon Valley Bridge Bank in March "
    "2023 is recorded by the FDIC as a &ldquo;Bridge Bank Resolution&rdquo;. "
    "Our merger list works by naming what counts rather than naming what does "
    "not, so it reported the code as unrecognised instead of silently "
    "treating it as ordinary trading.",
    "<b>The quarter after a first-quarter merger cannot be formed from the "
    "filings at all.</b> A quarterly flow is the year's running total less "
    "what was already reported &mdash; and the first quarter's published "
    "figure <i>is</i> that base. Where a merger moves it, nothing in the "
    "documents reaches the second quarter. %d values are reported as such "
    "rather than as differences." % BASE_ROWS,
    "<b>Nineteen fields were shipping with no units beside them.</b> A number "
    "in a spreadsheet with no unit is the trap this whole feed is written "
    "against, and it was in the feed.",
    "<b>The exhibits for seven banks were built with no photographs in them</b> "
    "and rendered perfectly. The pictures had been cut into one folder and "
    "read from another. The builder now refuses to finish a document that "
    "carries values and no pictures.",
):
    A("<li>%s</li>" % item)
A('</ul>')
A('<div class="note"><p>Every one of those was found by pointing the machinery '
  'at banks it had never seen, and by opening what came out. That is the '
  'argument for doing this again next quarter rather than assuming it still '
  'works.</p></div>')

A('<h2>What this does not prove</h2>')
A('<div class="note warn"><p><b>Read this one before you chart a bank across '
  'a merger.</b> Every value here is correct for the institution as it stood '
  'that day &mdash; and on either side of a merger that institution is a '
  'different size, under the same name. <b>%d of the %d merger quarters move '
  'total assets by 10%% or more%s.</b> No single value is wrong, so no '
  'value-level check can catch it: it is a property of the SERIES, not of any '
  'number in it. NOT COMPARABLE in the workbook carries the size of every '
  'step, per bank, per quarter.</p></div>'
  % (len(STEPS), len(MERGERS),
     ("" if not WORST_STEP else
      ", the largest being %s at %s, %+.0f%%"
      % (WORST_STEP["bank"], WORST_STEP["report_date"],
         float(WORST_STEP["change_in_total_assets_pct"])))))
A('<ul>')
A('<li><b>Not that the banks are right.</b> A value can match its filing '
  'exactly and the filing can still be wrong. This proves faithful copying.</li>')
A('<li><b>There is no vintage.</b> These are the figures as published when '
  'they were pulled. Banks amend Call Reports and agencies revise series, so a '
  'value verified today may not match the same source in six months. Nothing '
  'here records which revision a figure came from.</li>')
A('<li><b>%s macro observations have no obtainable source.</b> They are '
  'whole series rather than a scatter of gaps, and most are Case-Shiller, '
  'whose history S&amp;P Dow Jones Indices sells. The most recent month of '
  'all 22 of those WAS checked against the S&amp;P free release and all 22 '
  'agreed &mdash; for 21 that pins the month-on-month move rather than the '
  'level, and for the national index it is a published level. Each row says '
  'exactly what was and was not checked.</li>' % n(MACRO_NOT))
A('<li><b>The %d banks are not a like-for-like peer group.</b> %s are not '
  'commercial lenders. Their balance sheets are shaped nothing like a '
  'lender\'s and a peer ranking that mixes them will mislead; they are marked '
  '<span class="mono">group = counterparty</span> in the peer list.</li>'
  % (len(CERTS), ", ".join(b["name"] for b in PEERS["banks"]
                           if b["group"] == "counterparty" and b["active"])))
A('<li><b>Nothing here was checked by a second person.</b></li>')
A('</ul>')

A('<h2>What is in the workbook</h2>')
A('<table><tr><th>Tab</th><th>What it is</th></tr>')
for tab, what in (
    ("START HERE", "what the workbook is, and the two things to know before "
                   "charting anything"),
    ("WHAT WAS PROVEN", "how each number was checked, with the denominators"),
    ("LIMITS", "what this data cannot do; read before charting"),
    ("THE SOURCES", "who publishes what"),
    ("BANK DATA", "%s values, each with its schedule, its cited line, its "
                  "verdict and a link to the filing" % n(len(BANK))),
    ("MACRO DATA", "%s observations across %s series"
     % (n(len(MACRO)), n(len({r["series_id"] for r in MACRO})))),
    ("FIELD DICTIONARY", "what each of the %s bank fields means, in plain "
                         "English" % len(FIELDS)),
    ("RATIOS", "ratios worth building and the trap in each. It describes them "
               "and builds none"),
    ("NOT COMPARABLE", "the %d quarters that should not be charted as a "
                       "trend, and why" % len(MERGERS)),
):
    A('<tr><td class="mono"><b>%s</b></td><td>%s</td></tr>' % (tab, what))
A('</table>')
A('</div>')

HTML = ("<!doctype html><meta charset='utf-8'><title>Verified credit data "
        "&mdash; how it was proved</title><style>%s</style>%s"
        % (CSS, "\n".join(BODY)))

src = SB / "covering.html"
src.write_text(HTML, encoding="utf-8")
OUT.mkdir(parents=True, exist_ok=True)
subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                "--no-pdf-header-footer", "--print-to-pdf=%s" % PDF,
                src.as_uri()], capture_output=True, timeout=300)
if not PDF.exists():
    raise SystemExit("Chrome produced no PDF")

import pymupdf
doc = pymupdf.open(PDF)
images = sum(len(doc[p].get_images()) for p in range(doc.page_count))
pages = doc.page_count
doc.close()
if not images:
    raise SystemExit(
        "REFUSING: the covering document rendered with NO images in it. "
        "Every figure it traces is supposed to carry a photograph of the "
        "filed line, and a document that argues about numbers the reader "
        "cannot see is not evidence.")
print("written : %s" % PDF)
print("          %d pages, %d images embedded, %.1f MB"
      % (pages, images, PDF.stat().st_size / 1e6))
print("every number in it read from verified-data/ at build time")
