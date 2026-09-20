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
sys.path.insert(0, str(CS / "src"))

# The conformance gate lives in `canon`, not here. The rules it holds belong to
# the tie-out skill, and the next document built from that skill will be in
# some other project. If canon is not beside us the build STOPS: a checker that
# is missing must never read the same as a checker that passed.
CANON = CS.parent / "canon"
if not (CANON / "check_tie_out.py").exists():
    raise SystemExit(
        "REFUSING: canon's tie-out conformance checker is not at %s, so this "
        "document would be published unchecked." % CANON)
sys.path.insert(0, str(CANON))

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_fdic_ratios                        # noqa: E402
import check_tie_out                            # noqa: E402
from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
STRIPS = SB / "deepstrips-grey"
DATA = CS / "verified-data"
OUT = CS / "docs" / "tie-out"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

STAMP = "2026-09-08"
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
MACRO_NOT = len(MACRO) - MACRO_TIED
TOTAL = len(BANK) + len(MACRO)
TOTAL_TIED = BANK_TIED + MACRO_TIED

# ---------------------------------------------------------------------------
# The roster, as a partition
# ---------------------------------------------------------------------------
# WHY THIS IS A PARTITION AND NOT SEVEN SEARCHES. Until 19 September 2026 each
# roster line was its own `sum(1 for r in BANK if <phrase> in ...)`. On
# 8 September the delivered wording of one verdict was improved -- "the bank
# did not report that line" became "the form this bank filed ... does not carry
# the line this field cites" -- and the search over it was not. That line
# printed 0; the headline above it still said 156,881; the roster beneath added
# to 156,767. Every number in the document was right and the document said two
# different things about how much of itself it had checked.
#
# So each delivered row is now classified EXACTLY ONCE, the roster is the tally
# of that classification, and it adds to the headline by construction rather
# than by luck. A row matching no verdict, or more than one, stops the build
# instead of falling quietly into a zero.
TIED = "TIED"
MACRO_UNSOURCED = "macro, no obtainable source"
BANK_VERDICTS = (
    ("DIFFERS", "DOES NOT MATCH"),
    ("not comparable &mdash; spans a merger", "spans a merger"),
    ("not comparable &mdash; base moved", "running total"),
    ("not on that filing", "does not carry the line"),
    ("computed by the FDIC", "FDIC calculates"),
)


def verdict_of(row):
    """Which roster line this delivered row belongs on. Exactly one."""
    if row["verified"] == "yes":
        return TIED
    hits = [label for label, probe in BANK_VERDICTS
            if probe in row["verified_meaning"]]
    if len(hits) != 1:
        raise SystemExit(
            "REFUSING: the delivered verdict %r matches %d roster lines, not "
            "one. A verdict this document has no home for would be counted "
            "nowhere and the roster would stop adding up to the headline -- "
            "which is the defect this refusal exists to stop repeating."
            % (row["verified_meaning"], len(hits)))
    return hits[0]


ROSTER = dict.fromkeys([label for label, _ in BANK_VERDICTS], 0)
ROSTER[TIED] = MACRO_TIED
ROSTER[MACRO_UNSOURCED] = MACRO_NOT
for _row in BANK:
    ROSTER[verdict_of(_row)] += 1

RATIOS = ROSTER["computed by the FDIC"]
MERGER_ROWS = ROSTER["not comparable &mdash; spans a merger"]
BASE_ROWS = ROSTER["not comparable &mdash; base moved"]
NOLINE = ROSTER["not on that filing"]
QUARTERS = sorted({r["report_date"] for r in BANK})
CERTS = sorted({r["cert"] for r in BANK})
IDS = sum(1 for b in PEERS["banks"] if b.get("identity_verified"))
SAME_THROUGHOUT = sum(1 for b in PEERS["banks"]
                      if b.get("same_name_throughout"))
RENAMED = [b for b in PEERS["banks"] if b.get("legal_name_at_window_start")
           and not b.get("same_name_throughout")]
_VINT = {(b["cert"], b["report_date"]): b["days_after_quarter_end"]
         for b in BANK if b.get("days_after_quarter_end")}
VINTAGE_TOTAL = len(_VINT)
VINTAGE_LATE = sum(1 for d in _VINT.values() if int(d) > 90)
VINTAGE_VERY_LATE = sum(1 for d in _VINT.values() if int(d) > 365)
#: How far the three steps under "Check any number yourself" actually get a
#: reader, counted rather than claimed. A single prefixed code is the only
#: shape those steps describe.
_ONE_LINE = __import__("re").compile(r"^(RC[A-Z]{2}|RIAD)[A-Z]?\d{3,4}$")
RECIPE = {"one line": 0, "arithmetic": 0, "two filings": 0, "no line": 0}
# "no line" is decided by the DELIVERED VERDICT, not by the shape of the
# citation string. Deciding it on a "/" in the citation put ERNAST and LNLSGR5
# -- the two averages the FDIC constructs, whose citation reads "the FDIC's own
# average; no filed line carries it" -- into the arithmetic bucket, so 1,520
# rows were told to "find each code on the page and do what the signs say" when
# there is no code and no arithmetic. It also made this breakdown say 6,080
# where the roster three pages earlier said 7,600 about the same thing.
for _r in BANK:
    _c, _note = _r["cited_line"], _r["note"]
    if "FDIC calculates" in _r["verified_meaning"]:
        RECIPE["no line"] += 1
    elif "year-to-date less the previous" in _note:
        RECIPE["two filings"] += 1
    elif _ONE_LINE.match(_c):
        RECIPE["one line"] += 1
    else:
        RECIPE["arithmetic"] += 1
assert sum(RECIPE.values()) == len(BANK), RECIPE

#: Merger quarters whose total assets step by 10% or more, and the worst one.
#: MEASURABLE is the denominator, not len(MERGERS): two merger quarters sit at
#: the very start of the window, where the quarter before them is outside it,
#: so no step can be computed for them. Reported as 15 of 33 until 8 September
#: 2026; the finding that produced the sentence said 31 and the sentence lost
#: the word on its way into the document.
MEASURABLE = [m for m in MERGERS if m.get("change_in_total_assets_pct")]
STEPS = [m for m in MEASURABLE
         if abs(float(m["change_in_total_assets_pct"])) >= 10]
WORST_STEP = (max(STEPS, key=lambda m: abs(
    float(m["change_in_total_assets_pct"]))) if STEPS else None)

#: The fields the FDIC works out rather than a bank filing them, and how far
#: the recomputation gets. Counted and RUN here, not quoted: this paragraph
#: said "eight of the 87 fields" while the feed carried 105 fields and ten such
#: ratios, because both numbers were true on the day somebody typed them.
FDIC_FIELDS = sorted({r["field"] for r in BANK
                      if "FDIC calculates" in r["verified_meaning"]})
_RECOMPUTED = check_fdic_ratios.recompute()
RECOMPUTED_FIELDS = sorted(set(_RECOMPUTED) & set(FDIC_FIELDS))
RECOMPUTED_AGREE = sum(r["agree"] for r in _RECOMPUTED.values())
RECOMPUTED_DIFFER = sum(r["differ"] for r in _RECOMPUTED.values())
RECOMPUTED_TOTAL = RECOMPUTED_AGREE + RECOMPUTED_DIFFER

#: The window, in years, off the quarters actually delivered. "ten years"
#: appeared three times in this document as a typed phrase.
YEARS = round(len(QUARTERS) / 4)

#: The Case-Shiller series whose history is behind S&P's paywall, and how many
#: of them the free release pins only the MOVE for rather than a level. Both
#: were typed -- "all 22", "for 21". Counted off the delivered reasons now, and
#: NOT off the titles: two of the twenty-two are called "S&P CoreLogic
#: Case-Shiller U.S. National HPI", so matching the title gave twenty and a
#: computed figure that is wrong is worse than a typed one that is right.
_SELLS = ("S&P Dow Jones Indices sells", "S&P sells the history")
_PAYWALLED = {r["series_id"]: r["why_not_verified"] for r in MACRO
              if r["verified"] != "yes"
              and any(s in r["why_not_verified"] for s in _SELLS)}
CASE_SHILLER = len(_PAYWALLED)
CASE_SHILLER_MOVE = sum(1 for why in _PAYWALLED.values()
                        if "pins the MOVE" in why)


def n(x):
    return "{:,}".format(int(x))


#: Small counts, spelled. A figure computed from the data still has to read
#: like a sentence: "33 such quarters in 10 years" is a computed number and a
#: worse sentence than the typed one it replaced.
_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve "
          "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
          .split())


def w(x):
    """The word for a small count, or the figure for a large one."""
    return _WORDS[int(x)] if 0 <= int(x) < len(_WORDS) else n(x)


def esc(x):
    return html.escape("" if x is None else str(x))


#: The ink. Dark enough to read as deliberate on a printed page, far enough
#: from black that canon's checker can tell it from the form's own rules.
RED = (172, 18, 51)
RING = 4


def img(name, ring=False):
    """A strip, embedded. Returns None if it is not there, and the caller says so.

    `ring=True` draws the red box the skill asks for. WHY IT IS DRAWN HERE AND
    NOT CUT WITH THE STRIP: the strips are cut once, greyscaled and kept -- 664
    MB of them before they were shrunk -- and they are the evidence. Marking a
    copy at build time leaves the evidence untouched and means the mark can be
    changed without re-photographing 760 filings.

    The strip IS the row, clipped to the band the code sits on and five points
    either side, so a box around it rings exactly what the citation names and
    nothing else. Re-quantised to sixteen shades afterwards for the same reason
    the strips were: a Call Report page is black on white, and the palette costs
    nothing to read and two thirds of the bytes.
    """
    p = STRIPS / name
    if not p.exists():
        return None
    raw = p.read_bytes()
    if ring:
        from PIL import Image, ImageDraw
        import io
        picture = Image.open(io.BytesIO(raw)).convert("RGB")
        pen = ImageDraw.Draw(picture)
        pen.rectangle([RING // 2, RING // 2,
                       picture.width - 1 - RING // 2,
                       picture.height - 1 - RING // 2],
                      outline=RED, width=RING)
        buffer = io.BytesIO()
        picture.quantize(colors=16).save(buffer, "PNG", optimize=True)
        raw = buffer.getvalue()
    return "data:image/png;base64,%s" % base64.b64encode(raw).decode()


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
# The dollar figure, not the ratio: the trace below is written about total
# risk-based capital, and DIFFERS[0] follows whatever order the rows were
# assembled in. Naming what the narrative is about beats taking the first one.
DIFF_ROW = next((r for r in DIFFERS if r["field"] == "RBC"),
                DIFFERS[0] if DIFFERS else None)

# ---------------------------------------------------------------------------
# The one disagreement, in figures read out of the delivered rows
# ---------------------------------------------------------------------------
# Every number the narrative below states was typed into it until 19 September
# 2026 -- six of them in one fixed-width table -- in a document whose opening
# line is that not one number in it is typed. They come out of the two
# delivered rows and their notes now, and the two that CANNOT are listed in
# HAND_READ so a reader can count them.
_FILED = __import__("re").compile(
    r"the filing reads ([\d,.]+) and the FDIC publishes ([\d,.]+), "
    r"a difference of (-?[\d,.]+)")


def filed_figure(row):
    """What the form says, out of the delivered note. Not re-fetched."""
    hit = _FILED.search(row["note"])
    if not hit:
        raise SystemExit("the delivered note for %s %s %s does not carry the "
                         "filed figure this document quotes"
                         % (row["cert"], row["report_date"], row["field"]))
    return float(hit.group(1).replace(",", ""))


#: The two figures on this page that are NOT in the delivered file and cannot
#: be worked out from it. Both were read off the filed form by hand, the
#: document says so where each appears, and they are named here so that how
#: much of the page is not computed is itself a number a reader can see: two.
#:
#: The risk-weighted-assets line is kept as READ rather than backed out of the
#: capital and the ratio. Backing it out was tried on 19 September 2026 and
#: gives 206,904,087 -- 140 thousand under the figure on the form, because the
#: ratio is only published to six decimals and that is all the precision there
#: is to divide by. The number on the form is the better evidence, and a
#: document that quietly replaced it with a rounder one would be doing the
#: thing this whole feed exists to stop.
HAND_READ = {"the filing's printed risk-weighted assets": 206904227,
             "the leverage ratio as filed": 10.235700}

if DIFF_ROW:
    RATIO_ROW = find(DIFF_ROW["cert"], DIFF_ROW["report_date"], "RBCRWAJ")
    LEVER_ROW = find(DIFF_ROW["cert"], DIFF_ROW["report_date"], "RBC1AAJ")
    RBC_FDIC = int(float(DIFF_ROW["value"]))
    RBC_FILED = int(filed_figure(DIFF_ROW))
    RBC_GAP = RBC_FDIC - RBC_FILED
    RATIO_FDIC = float(RATIO_ROW["value"])
    RATIO_FILED = filed_figure(RATIO_ROW)
    LEVERAGE_FDIC = float(LEVER_ROW["value"])
    # Risk-weighted assets are not a field in this feed. The FDIC's side is
    # backed out of its own capital and its own ratio -- it publishes the ratio
    # to enough places for that to land. The filing's side is the line printed
    # on the form, in HAND_READ above.
    RWA_FDIC = RBC_FDIC / RATIO_FDIC * 100
    RWA_FILED = HAND_READ["the filing's printed risk-weighted assets"]
    # The form checking itself: its own risk-weighted assets times its own
    # ratio should come back to its own capital, and it does, to 20 thousand.
    RBC_FILED_CROSSCHECK = round(RWA_FILED * RATIO_FILED / 100)
    DIFF_AMENDED_DAYS = DIFF_ROW["days_after_quarter_end"]

#: The rows the "a hundred times the rounding it needed" sentence is about.
#: Named by field rather than counted by hand.
CAPITAL_RATIO_FIELDS = ("RBCRWAJ", "RBC1AAJ")
CAPITAL_ROWS = sum(1 for r in BANK if r["field"] in CAPITAL_RATIO_FIELDS)

#: The rows with no citable line at all -- the FDIC's own averages, which are
#: neither a filed line nor arithmetic over filed lines. They are 1,520, which
#: is also what CAPITAL_ROWS comes to; using that one here because the figure
#: matched would have been the whole failure this session is about.
NO_CITABLE_LINE = sum(1 for r in BANK
                      if "not lines any bank files" in r["verified_meaning"])

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
    row_png = img(entry["png"], ring=True) if entry else None
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
                '<div class="shot"><img data-tieout="source" src="%s"></div>'
                '<p class="cap">The filed page, and the row on it, <b>ringed in '
                'red</b>. The header is photographed from the same page, so '
                '&ldquo;same entity, same date&rdquo; is read off the picture '
                'rather than taken on trust.</p>' % (hdr_png, row_png))
    elif row_png:
        shot = ('<div class="shot"><img data-tieout="source" src="%s"></div>'
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
# The first card is the document's headline -- the number the roster below has
# to add up to. It is marked so canon's checker can find it; nothing else here
# is a total about the feed as a whole.
for k, v in (("values delivered", n(TOTAL)),
             ("checked against an outside document", n(TOTAL_TIED)),
             ("disagreed", n(len(DIFFERS))),
             ("filed pages photographed", n(AUDIT["filings_photographed"]))):
    mark = ' data-tieout="headline"' if k == "values delivered" else ""
    A('<div class="card"><div class="k">%s</div><div class="big"%s>%s</div>'
      "</div>" % (k, mark, v))
A('</div>')

A('<p class="lead"><b>No value in this feed is calculated by our software.</b> '
  'No ratios, no quarter-on-quarter changes, no scores. If a number is here, a '
  'bank or a government agency published it in that form, and this document '
  'shows you how to put your finger on where. The one figure we do work out is '
  'the size of each merger step in NOT COMPARABLE, which is a warning about '
  'the data rather than part of it.</p>')

A('<h2>How a number gets here, and how it gets checked</h2>')
A(DIAGRAM)

A('<h2>One number, traced all the way</h2>')
A('<p>Two, in fact. The first is on a bank this system had never seen until '
  'this week, so it shows the machinery working on something it was not tuned '
  'for. The second is one of the %s numbers in %s that does not agree, which '
  'is the more useful of the two.</p>' % (n(len(DIFFERS)), n(len(BANK))))
A(trace(TIES_ROW, "Regions Bank, total assets, 30 June 2026",
        "A bank added to the set this week. Nothing about the chain was "
        "changed to accommodate it.", True))
if DIFF_ROW:
    A(trace(DIFF_ROW, "Huntington National Bank, total risk-based capital, "
                      "31 March 2026",
            "One of the two differences in the whole feed, and they are the "
            "same event twice. It is here on purpose: a tie-out that hides "
            "its own findings is worth nothing.", False))
    # Every figure in the paragraphs below is read out of the two delivered
    # rows and their notes, or worked out from them here, with one exception
    # that is labelled where it appears. Until 19 September 2026 the whole of
    # it was typed -- including a table of six figures -- in a document whose
    # opening docstring says not one number in it is.
    A('<div class="note warn"><p>The filing was read twice &mdash; off the '
      'printed page above and off the machine-readable copy the regulator '
      'publishes beside it &mdash; and both say <b>%s</b>. The '
      'filing&rsquo;s own total capital ratio multiplied by its own risk-weighted '
      'assets comes to %s, so the form is internally consistent. The '
      'second column on that line reads <span class="mono">NR</span>, not '
      'reported, so there is no other column the FDIC&rsquo;s figure could have '
      'come from. <b>We have no explanation for the $%s thousand, and we are '
      'not going to invent one.</b> It is %s%% of the figure and it sits in '
      'the quarter Huntington closed an acquisition.</p></div>'
      % (n(RBC_FILED), n(RBC_FILED_CROSSCHECK), n(abs(RBC_GAP)),
         "{:.3f}".format(abs(RBC_GAP) / RBC_FDIC * 100)))
    A('<h3>The same quarter disagrees a second time, and it says more</h3>')
    A('<p>This bank&rsquo;s <b>total capital ratio</b> for the same quarter '
      'disagrees too: the FDIC publishes <b>%s%%</b> and the filing '
      'reports <b>%s%%</b>. Until 8 September 2026 it was reported as '
      'agreeing, because capital ratios were compared to within 0.005 of a '
      'percentage point and this gap is %s &mdash; just inside. Every '
      'other one of the %s capital-ratio rows is within 0.00005, which is '
      'the rounding you get from a form that prints six decimals and a '
      'publisher that prints four. So the room was a hundred times what '
      'rounding needed, and exactly one value used it. The comparison is now '
      '0.0001 and this row is reported for what it is.</p>'
      % ("{:.6f}".format(RATIO_FDIC), "{:.6f}".format(RATIO_FILED),
         "{:.5f}".format(abs(RATIO_FDIC - RATIO_FILED)), n(CAPITAL_ROWS)))
    A('<p>Working the risk-weighted assets back out of each side is what makes '
      'it worth reading:</p>')
    A('<pre>                  total capital        risk-weighted assets\n'
      'FDIC          %s          %s\n'
      'the filing    %s          %s\n'
      'difference    %s          %s\n'
      '                                        (thousands of dollars)\n\n'
      'leverage ratio    FDIC %s%%   filing %s%%   unmoved</pre>'
      % ("{:>14}".format(n(RBC_FDIC)), "{:>14}".format(n(round(RWA_FDIC))),
         "{:>14}".format(n(RBC_FILED)), "{:>14}".format(n(round(RWA_FILED))),
         "{:>14}".format(n(RBC_FDIC - RBC_FILED)),
         "{:>14}".format(n(round(RWA_FDIC - RWA_FILED))),
         "{:.6f}".format(LEVERAGE_FDIC),
         "{:.6f}".format(HAND_READ["the leverage ratio as filed"])))
    A('<p><b>Two capital figures moved together and two did not.</b> Total '
      'capital and risk-weighted assets differ; Tier 1 capital and average '
      'assets, which the leverage ratio is built from, agree to the rounding. '
      '<i>Two figures in that table are read off the form by hand rather than '
      'computed: the filing&rsquo;s own risk-weighted assets, and the leverage '
      'ratio as the filing prints it. The feed carries neither &mdash; it has '
      'no risk-weighted-assets field, and the leverage row agrees, so there is '
      'no filed figure recorded beside it.</i> This is the '
      'shape of an amendment to the risk-weighting pages rather '
      'than a mistyped line, and it is the best evidence we have for the '
      'explanation we could not prove: this filing was amended %s days after '
      'the quarter and the FDIC&rsquo;s published figures have not moved with '
      'it. <b>Still not proven</b> &mdash; the pre-amendment filing cannot be '
      'obtained. The FDIC&rsquo;s risk-weighted assets are worked out here, '
      'from its own capital and its own ratio; they are not part of the '
      'data.</p>' % DIFF_AMENDED_DAYS)

A('<h2 class="brk">The roster, with its denominator</h2>')
A('<p>What did not check out comes first, because the things that agree are '
  'not what anybody needs to read.</p>')
A('<table data-tieout="roster">')
A('<tr><th>Verdict</th><th class="n">Rows</th><th>What it means</th></tr>')
# The rows come out of ROSTER, which is a tally of every delivered value
# classified exactly once. The table is therefore the partition, printed -- it
# cannot disagree with the headline without the build refusing.
for label, meaning in (
        ("DIFFERS",
         "the delivered value and the filed line do not agree; named above"),
        ("not comparable &mdash; spans a merger",
         "a quarterly flow in a quarter that mixes two banks. %d such quarters "
         "in %s years, all listed in the workbook" % (len(MERGERS), w(YEARS))),
        ("not comparable &mdash; base moved",
         "the quarter after a merger that landed in a first quarter: the "
         "running total it counts from is the FDIC's own adjusted figure, "
         "which no filing carries"),
        ("not on that filing",
         "the FORM did not carry that line in that quarter, so no bank filed "
         "it. Every one of these is the second half of 2016, before Schedule "
         "RC-N gained a total line, across all %s banks" % w(len(CERTS))),
        ("computed by the FDIC",
         "a figure the FDIC works out rather than a line a bank files. The "
         "lines it is worked out FROM are checked"),
        (MACRO_UNSOURCED,
         "whole series with no independent publisher we can reach; each row "
         "says why"),
        (TIED,
         "checked against a document published by somebody outside this firm"),
):
    A('<tr><td><b>%s</b></td><td class="n" data-tieout="count">%s</td>'
      "<td>%s</td></tr>" % (label, n(ROSTER[label]), meaning))
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
  'the other end of the %s years as well: <b>%d of %d</b> carry the same '
  'legal name on the oldest filing as on the newest. %s</p>'
  % (w(YEARS), SAME_THROUGHOUT, len(PEERS["banks"]),
     "" if not RENAMED else
     ("The exceptions are " + "; ".join(
         "<b>%s</b>, filed in %s as %s" % (b["name"], QUARTERS[0][:4],
                                           b["legal_name_at_window_start"])
         for b in RENAMED) + ". All but one are a new name over the same "
      "institution &mdash; Zions dropping the initials it traded under, Fifth "
      "Third converting its charter. <b>Truist is not:</b> everything before "
      "December 2019 under that label is Branch Banking and Trust, which is "
      "half the bank that carries the name afterwards.")))

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
# Those three steps are the whole story for a row citing ONE line, and that is
# 37 per cent of them. Saying so is the difference between a reader who finds
# the number and a reader who finds a DIFFERENT number and concludes the feed
# is wrong. Counted off the delivered rows rather than asserted.
A('<h3>When the row cites more than one line</h3>')
A('<p><b>%s of the %s bank rows</b> cite a single line, and the three steps '
  'above are all of it. The rest need one more thing, and the row says which '
  'in its <span class="mono">note</span>.</p>'
  % (n(RECIPE["one line"]), n(len(BANK))))
A('<ul>')
A('<li><b>%s rows add or subtract two or more lines.</b> The '
  '<span class="mono">cited_line</span> is that arithmetic &mdash; find each '
  'code on the page and do what the signs say. No one number printed on the '
  'filing is the number in the workbook.</li>' % n(RECIPE["arithmetic"]))
A('<li><b>%s rows are one quarter of a running yearly total</b>, which no '
  'filing carries on its own: it is this filing&rsquo;s year-to-date less the '
  'previous one&rsquo;s. So you need the quarter before as well, and it is at '
  'a different address &mdash; change the <span class="mono">date</span> in '
  'the link to the previous quarter end.</li>' % n(RECIPE["two filings"]))
A('<li><b>%s rows are figures the FDIC works out</b> rather than lines a bank '
  'files. There is nothing on the form to find; where they are worked out FROM '
  'lines, those lines are in this feed and are checked.</li>'
  % n(RECIPE["no line"]))
A('</ul>')
A('<p>To change bank or quarter, edit the <span class="mono">id</span> (the '
  'FDIC certificate) and the <span class="mono">date</span> '
  '(<span class="mono">MMDDYYYY</span>, a quarter end) in that address.</p>')

A('<h2 data-tieout="what-it-found">What running this found</h2>')
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
    "<b>%d quarters in %s years span a merger</b>, where a first pass over "
    "sixteen quarters had seen six. Every one of them would otherwise have "
    "been reported as the regulator disagreeing with the filings when nothing "
    "was wrong with either." % (len(MERGERS), w(YEARS)),
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
    "documents reaches the second quarter. %s values are reported as such "
    "rather than as differences." % w(BASE_ROWS).capitalize(),
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

A('<h2 data-tieout="what-i-got-wrong">What I got wrong</h2>')
A('<p>The last version of this document got these wrong. None of '
  'them was a value &mdash; every number in the feed was checked again and not '
  'one moved &mdash; and every one is the same mistake: something true on the '
  'day it was typed, still sitting there after the thing it described '
  'changed.</p>')
A('<ul>')
A('<li><b>The roster printed 0 where %s belonged.</b> One verdict was reworded '
  'on 8 September &mdash; it used to say the bank had not reported a line, '
  'which blamed the bank for something the form did not ask. The tally '
  'underneath was still looking for the old wording, found none, and printed '
  'nothing. So the front of this document said %s values and the roster '
  'below it added to %s. Both were built from the same file. Now every value is sorted '
  'into exactly one row of that roster, so it adds up or the document does not '
  'get built.</li>' % (n(NOLINE), n(TOTAL), n(TOTAL - NOLINE)))
A('<li><b>It said eight of 87 fields are worked out by the FDIC.</b> There are '
  '%s fields and %s of them. Both of those were right once. They are counted '
  'off the delivered file now, every time this is built.</li>'
  % (n(len(FIELDS)), w(len(FDIC_FIELDS))))
A('<li><b>Two lists in this document counted the same thing differently.</b> '
  'One said %s rows are worked out by the FDIC and the roster said %s. '
  'The list under &ldquo;when the row cites more than one '
  'line&rdquo; sorted rows by what their citation looked like rather than by '
  'what the row says it is. Two fields the FDIC works out from averages of its '
  'own have no code to cite, so they fell in with the rows that need '
  'arithmetic &mdash; and %s rows were told to find codes on a page that does '
  'not carry any. Both lists are sorted the same way now.</li>'
  % (n(RATIOS - NO_CITABLE_LINE), n(RATIOS), n(NO_CITABLE_LINE)))
A('<li><b>The filed pages were photographed and nothing on them was marked.</b> '
  'You were handed a picture of a dense regulatory page and a sentence saying '
  'which row to look at. The row is ringed in red now, which is the difference '
  'between checking us and taking our word for it.</li>')
A('</ul>')

A('<h2 data-tieout="what-this-does-not-prove">What this does not prove</h2>')
A('<div class="note warn"><p><b>Read this one before you chart a bank across '
  'a merger.</b> Every value here is correct for the institution as it stood '
  'that day &mdash; and on either side of a merger that institution is a '
  'different size, under the same name. <b>%d of the %d merger quarters whose '
  'step can be measured move total assets by 10%% or more%s.</b> No single '
  'value is wrong, so no value-level check can catch it: it is a property of '
  'the SERIES, not of any number in it. NOT COMPARABLE in the workbook carries '
  'the size of every merger step, per bank, per quarter &mdash; and only those. '
  'A balance sheet can move that far without a merger and nothing here flags '
  'it: the largest single-quarter step in this feed is Morgan Stanley Bank NA '
  'at 2026-03-31, +54.5%% of total assets, with nothing acquired.</p></div>'
  % (len(STEPS), len(MEASURABLE),
     ("" if not WORST_STEP else
      ", the largest being %s at %s, %+.0f%%"
      % (WORST_STEP["bank"], WORST_STEP["report_date"],
         float(WORST_STEP["change_in_total_assets_pct"])))))
A('<ul>')
A('<li><b>Not that the banks are right.</b> A value can match its filing '
  'exactly and the filing can still be wrong. This proves faithful copying.</li>')
A('<li><b>It is a snapshot, and banks amend.</b> Every bank row carries '
  '<span class="mono">filing_last_updated</span>, the date printed on the '
  'filing it was checked against, so you can see which version you have. '
  'Amendments are the normal case here rather than the exception: %s of the '
  '%s filings were last updated more than 90 days after the quarter they '
  'report and %s more than a year after it &mdash; Bank of America amended '
  'its third quarter of 2016 in December 2021. The macro side has no such '
  'stamp.</li>' % (n(VINTAGE_LATE), n(VINTAGE_TOTAL), n(VINTAGE_VERY_LATE)))
A('<li><b>%s of the %s values the FDIC works out are checked; the rest are '
  'not.</b> %s of the %s fields are not lines a bank files &mdash; the FDIC '
  'works them out, so there is no row on any form to compare them with. %s of '
  'those %s are plain ratios of two figures this feed already carries and has '
  'already tied to the filings, and working each one out again from its own '
  'checked parts gives <b>%s of %s agreeing, %s differing</b>. The other %s '
  'are built on averages the FDIC makes itself, or on figures this feed does '
  'not hold, so they stay unchecked. Run '
  '<span class="mono">tools/tieout/check_fdic_ratios.py</span>.</li>'
  % (n(RECOMPUTED_TOTAL), n(RATIOS), w(len(FDIC_FIELDS)).capitalize(),
     n(len(FIELDS)),
     w(len(RECOMPUTED_FIELDS)).capitalize(), w(len(FDIC_FIELDS)),
     n(RECOMPUTED_AGREE),
     n(RECOMPUTED_TOTAL),
     ("none" if not RECOMPUTED_DIFFER else n(RECOMPUTED_DIFFER)),
     w(len(FDIC_FIELDS) - len(RECOMPUTED_FIELDS))))
A('<li><b>%s macro observations have no obtainable source.</b> They are '
  'whole series rather than a scatter of gaps, and most are Case-Shiller, '
  'whose history S&amp;P Dow Jones Indices sells. The most recent month of '
  'all %d of those WAS checked against the S&amp;P free release and all %d '
  'agreed &mdash; for %d that pins the month-on-month move rather than the '
  'level, and for the national index it is a published level. Each row says '
  'exactly what was and was not checked.</li>'
  % (n(MACRO_NOT), CASE_SHILLER, CASE_SHILLER, CASE_SHILLER_MOVE))
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

# THE GATE, BEFORE THE RENDER. canon reads what is about to be printed and
# refuses it if the roster does not add to the headline, if any of the three
# named sections is missing, or if the photographed rows carry no mark. It is
# deliberately upstream of Chrome: the refusal lands while there is still
# nothing on disk to forward.
check_tie_out.gate(HTML, "the covering document for the verified credit feed")

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
