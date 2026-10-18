"""The book walkthrough's expected answers, from the source files, not the workbook.

Run from threshold-engine/, after the build (WALKTHROUGH.md, step 1):
    python docs/walkthrough-book/expected.py
Writes steps.json (what to click and type, where, and what each cell must then
say) and EXPECTED.md (the same, for a person). Every number comes from the
series CSVs the build read and scale.py, the reference the workbook's formulas
are held to; walk.ps1 does each step in Excel 16 and reads the answer back.

One set of lines per product and measure (the firm, 15 Oct 2026: "we don't
need to set thresholds on all 3, we need to use all 3 to set appropriate
thresholds"): Decide's row picks the source whose history sets the lines, its
settings apply to every source's own lines (Lines by source), its period left
out to the source picked, and every source's latest quarter is rated on the
lines picked (Thresholds, Summary).

The steps are cumulative, as a person's session is: what step 3 types is
still there in step 4, and step 10 saves, closes and reopens the file to show
the decisions were kept.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from threshold_engine import book as BK                              # noqa: E402
from threshold_engine import decide_tab as DT                        # noqa: E402
from threshold_engine import summary_tab as SU                       # noqa: E402
from threshold_engine import thresholds_tab as TT                    # noqa: E402
from threshold_engine.scale import scale, score                      # noqa: E402
from threshold_engine.series import check, read_csv                  # noqa: E402
from threshold_engine.workbook import assess_layout, quarter         # noqa: E402
from openpyxl.utils import get_column_letter as L                    # noqa: E402

HERE = Path(__file__).parent
BOOK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "books" / "consumer-public.json"
RATINGS = ["Low", "Moderate-Low", "Moderate", "Moderate-High", "High"]
LBS = DT.LINES_TAB

bk = BK.load(BOOK)
W = bk["workbook"]
SER = bk["series"]
LABELS = [lbl for lbl, _ in SER]
N = len(SER)
PARTS = bk["decide"]["parts"]
NAMES = bk["decide"]["names"]
COMPARE = bk["decide"]["compare"]
PAIRS, BY = DT.pairs_of(LABELS, PARTS)
THIRD = DT.sources_of(LABELS, PARTS)
LEAD = COMPARE[0] if COMPARE else THIRD[0]
COLS = DT.columns(NAMES)
DL = DT.layout(len(PAIRS), len(THIRD), COMPARE is not None)
AL = assess_layout(N)
TL = TT.layout(SU.layout(LABELS, PARTS, COMPARE)["sources"])
PTS = {lbl: check(read_csv(p), "quarterly") for lbl, p in SER}
FLOOR_OFF = set(bk["decide"]["floor_off"])


def floor_of(lbl):
    """The series' floor at zero: the workbook's, unless its measure has none (floor_off)."""
    return bool(W["floor_at_zero"]) and PARTS[lbl][1] not in FLOOR_OFF


def dcell(name, pr):
    return "%s%d" % (L(COLS[name]), DL["first"] + PAIRS.index(pr))


def refusal_text(msg):
    if msg.startswith("too little history"):
        return "Refused: too little history kept for a typical yearly move"
    if msg.startswith("High would begin beyond the worst"):
        return "Refused: High would begin beyond the worst quarter kept"
    return "Refused: " + msg


def own(lbl, window=None, hw=None, ls=None, z=None, rule=None):
    """A series' own lines, as Lines by source holds them, keyed by the plain
    layout's letters, plus "bounds" (None when refused)."""
    hw = W["moderate_halfwidth"] if hw is None else hw
    ls = W["low_step"] if ls is None else ls
    z = W["high_z"] if z is None else z
    rule = W["on_the_line"] if rule is None else rule
    kept = [None if window and window[0] <= quarter(p.date) <= window[1] else p.value for p in PTS[lbl]]
    ref = scale(kept, W["direction"], hw, ls, z, floor_of(lbl))
    latest = PTS[lbl][-1]
    row = {"B": ref["median"], "C": ref["typical_yearly_move"], "D": max(v for v in kept if v is not None),
           "I": quarter(latest.date), "J": latest.value, "bounds": None, "rule": rule}
    if ref["refused"]:
        row.update({"K": "", "M": refusal_text(ref["refused"])})
        return row
    row.update(zip("EFGH", ref["bounds"]))
    row["bounds"] = ref["bounds"]
    sc = score(latest.value, ref["bounds"], W["direction"], rule, floor_of(lbl))
    row.update({"K": sc, "L": RATINGS[sc - 1], "M": ""})
    return row


def fits_reads(lbl, window=None, hw=None, ls=None, z=None):
    """What fits the history the lines are set from, on Decide, beside each
    setting: the ranges from the series' own median, yearly move, spread and
    worst kept (scale.py), worded and rounded as the cells word them."""
    from decimal import ROUND_HALF_UP, Decimal
    hw = W["moderate_halfwidth"] if hw is None else hw
    ls = W["low_step"] if ls is None else ls
    z = W["high_z"] if z is None else z
    kept = [None if window and window[0] <= quarter(p.date) <= window[1] else p.value for p in PTS[lbl]]
    ref = scale(kept, W["direction"], hw, ls, z, floor_of(lbl))
    med, mv, sp, wo = ref["median"], ref["typical_yearly_move"], ref["spread_of_levels"], ref["worst"]
    t = lambda x: str(Decimal(repr(x)).quantize(Decimal("0.01"), ROUND_HALF_UP))      # noqa: E731
    say = lambda ok: "It fits." if ok else "It does not fit."                        # noqa: E731
    floor = floor_of(lbl) and W["direction"] == "higher_is_worse"
    sg = 1 if W["direction"] == "higher_is_worse" else -1
    zmin, zmax, lsmax = hw * mv / sp, sg * (wo - med) / sp, med / mv
    texts = ["Fits below %s, where Moderate-Low begins. %s" % (t(ls), say(hw < ls)),
             "Fits above %s%s. %s" % (t(hw), ", and below %s so line 2 stays above zero" % t(lsmax) if floor else "",
                                     say(ls > hw and (not floor or ls < lsmax))),
             "Fits above %s (High beyond Moderate-High) and up to %s (some quarter kept can rate High). %s"
             % (t(zmin), t(zmax), say(zmin < z <= zmax)),
             "Either fits."]
    return [{"sheet": "Decide", "cell": "L%d" % (DL["settings"] + 1 + i), "expect": x} for i, x in enumerate(texts)]


#: own() keys its answers by the plain layout's letters; Lines by source lays
#: the table out as decide_tab.TH_BOOK, so each is read by meaning.
PLAIN_TO_BOOK = {DT.TH_PLAIN[k]: DT.TH_BOOK[k] for k in DT.TH_PLAIN}


def lbs_reads(lbl, row):
    r = 5 + LABELS.index(lbl)
    return [{"sheet": LBS, "cell": "%s%d" % (PLAIN_TO_BOOK[c], r), "expect": v}
            for c, v in row.items() if c in PLAIN_TO_BOOK]


def on_lines(lbl, lines):
    """A source's latest value rated on the lines picked: (number, text)."""
    if lines["bounds"] is None:
        return "", "Refused"
    sc = score(PTS[lbl][-1].value, lines["bounds"], W["direction"], lines["rule"], floor_of(lbl))
    return sc, "%d %s" % (sc, RATINGS[sc - 1])


def row_reads(pr, src, lines):
    """Thresholds' row for a product and measure, and Decide's two tables,
    with the lines set from ``src`` (``lines``, from own())."""
    r = 5 + PAIRS.index(pr)
    c, per = TL["cols"], TL["per"]
    out = [{"sheet": "Thresholds", "cell": "%s%d" % (c["lines_from"], r), "expect": src}]
    for k, v in zip(("l2", "l3", "l4", "l5"), "EFGH"):
        out.append({"sheet": "Thresholds", "cell": "%s%d" % (c[k], r), "expect": lines[v] if lines["bounds"] else ""})
    for s, lbl in BY[pr].items():
        _, text = on_lines(lbl, lines)
        out.append({"sheet": "Thresholds", "cell": "%s%d" % (per[s]["rating"], r), "expect": text})
        out.append({"sheet": "Thresholds", "cell": "%s%d" % (per[s]["latest"], r), "expect": PTS[lbl][-1].value})
    return out


def decide_reads(pr, lines, others):
    """Decide's screen for the row shown: every source on the lines picked,
    and what each source's own history gives (``others``: source -> own())."""
    out = []
    for i, s in enumerate(THIRD):
        lbl = BY[pr].get(s)
        if lbl is None:
            continue
        k, text = on_lines(lbl, lines)
        out += [{"sheet": "Decide", "cell": "M%d" % (DL["compare_first"] + i),
                 "expect": text if lines["bounds"] else "No rating"},
                {"sheet": "Decide", "cell": "N%d" % (DL["compare_first"] + i), "expect": PTS[lbl][-1].value}]
        o = others[s]
        g = DL["gives_first"] + i
        if o["bounds"]:
            out += [{"sheet": "Decide", "cell": "%s%d" % (c, g), "expect": o[v]} for c, v in zip("MNOP", "EFGH")]
        else:
            out.append({"sheet": "Decide", "cell": "M%d" % g, "expect": "Refused"})
        out.append({"sheet": "Decide", "cell": "Q%d" % g, "expect": o["D"]})
    return out


def chip(pr, lines):
    k, text = on_lines(BY[pr][LEAD], lines)
    return "No rating: see the Check" if k == "" else "%s: %s" % (LEAD, text)


def headline(pr, src):
    tail = ": lines set from %s" % src if src else ": no %s picked to set the lines yet" % NAMES[2].lower()
    return "%s, %s%s" % (pr[0], pr[1].lower(), tail)


def decided(n_acc, n_rej):
    return "Decided: %d of %d · accepted %d · rejected %d" % (n_acc + n_rej, len(PAIRS), n_acc, n_rej)


def summary_cell(lbl):
    """The row and column of a series' latest value on Summary; its rating is
    the next column (summary_tab.layout, the builder's own)."""
    r, latest, _ = SU.layout(LABELS, PARTS, COMPARE)["cells"][lbl]
    return r, latest


def slicers(**picks):
    return [{"type": "slicer", "caption": k, "value": v} for k, v in picks.items()]


def typed(pr, name, value):
    return {"type": "cell", "sheet": "Decide", "cell": dcell(name, pr), "value": value}


def every_own(pr, **kw):
    return {s: own(lbl, **kw) for s, lbl in BY[pr].items()}


IND, PEER = [s for s in THIRD if s != LEAD][:2] if len(THIRD) >= 3 else (THIRD[0], THIRD[-1])
OK = "Check: OK, your settings fit the history the lines are set from."
steps = []
# ---- B1: open ----
first = PAIRS[0]
steps.append({"id": "B1", "what": "Open the workbook as built",
              "shows": "It opens on Summary; the tabs in order; two slicers, each with one button picked; Decide "
                       "shows the first product and measure, no source picked and nothing decided",
              "actions": [], "reads": [
                  {"special": "active", "expect": "Summary"},
                  {"special": "sheets", "expect": ["Decide", "Summary", "Peers", "Peer loan classes", "Thresholds", LBS, "Internal",
                                                   "Evidence", "Backtest", "Glossary", "Sources", "Reporting changes", "Run", "Data",
                                                   "Peers data", "Peers delinquency data", "Internal data", "Assess",
                                                   "Chart", "Peers workings"]},
                  {"special": "slicers", "expect": {NAMES[0]: first[0], NAMES[1]: first[1]}},
                  {"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"]]},
                  {"sheet": "Decide", "cell": "L1", "expect": decided(0, 0)},
                  {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(first, None)},
                  {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": "No rating: see the Check"},
                  {"sheet": "Decide", "cell": "B%d" % DL["check"],
                   "expect": "Check: pick the %s whose history sets the lines, under %s."
                             % (NAMES[2].lower(), DT.LINES_FROM)},
                  {"special": "links", "expect": []},
                  {"special": "errors", "expect": 0}],
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b1-decide.png"},
                          {"sheet": "Summary", "range": "A1:T34", "file": "b1-summary.png"}]})

# ---- B2: every Summary cell, before a source is picked ----
reads = []
for lbl in LABELS:
    r, c = summary_cell(lbl)
    reads.append({"sheet": "Summary", "cell": "%s%d" % (L(c), r), "expect": PTS[lbl][-1].value})
    reads.append({"sheet": "Summary", "cell": "%s%d" % (L(c + 1), r), "expect": TT.NOT_PICKED})
reads += [own_read for lbl in LABELS for own_read in lbs_reads(lbl, own(lbl))]
steps.append({"id": "B2", "what": "Read Summary, and every source's own lines on Lines by source",
              "shows": "Every series' latest value, and Pick a source where its rating goes: %d series, each with "
                       "its own lines on Lines by source" % N,
              "actions": [], "reads": reads, "picture": []})

# ---- B3: click Credit card, Nonaccrual; set the lines from KeyBank ----
CN = ("Credit card", "Nonaccrual")
kb = BY[CN][LEAD]
lines3 = own(kb)
others3 = every_own(CN)
steps.append({"id": "B3", "what": "On Decide, click Credit card and Nonaccrual, and pick %s under %s"
                                  % (LEAD, DT.LINES_FROM),
              "shows": "One row shows; the lines are %s's own; every source is rated on them, beside what its own "
                       "history would give" % LEAD,
              "actions": slicers(**{NAMES[0]: CN[0], NAMES[1]: CN[1]}) + [typed(CN, DT.LINES_FROM, LEAD)],
              "reads": [{"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"] + PAIRS.index(CN)]},
                        {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(CN, LEAD)},
                        {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": chip(CN, lines3)},
                        {"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": OK}]
                       + [{"sheet": "Decide", "cell": "M%d" % (DL["ratings_first"] + 1 + j), "expect": lines3[c]}
                          for j, c in enumerate("EFGH")]
                       + decide_reads(CN, lines3, others3) + row_reads(CN, LEAD, lines3) + lbs_reads(kb, lines3)
                       + fits_reads(kb),
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b3-decide.png"},
                          {"sheet": "Thresholds", "range": "A1:%s%d" % (TL["cols"]["check"], 5 + len(PAIRS)),
                           "file": "b3-thresholds.png"}]})

# ---- B4: raise How rare High is to 3.5 on that row: every source's own lines move ----
lines4 = own(kb, z=3.5)
r, c = summary_cell(kb)
steps.append({"id": "B4", "what": "Type 3.5 under How rare High is (z), in the yellow row",
              "shows": "High's line moves for every source of the row; Thresholds and Summary follow",
              "actions": [typed(CN, "How rare High is (z)", 3.5)],
              "reads": row_reads(CN, LEAD, lines4) + [lr for s, lbl in BY[CN].items()
                                                     for lr in lbs_reads(lbl, own(lbl, z=3.5))]
                       + [{"sheet": "Summary", "cell": "%s%d" % (L(c + 1), r), "expect": on_lines(kb, lines4)[1]}]
                       + fits_reads(kb, z=3.5),
              "picture": []})

# ---- B5: leave out what the evidence suggests, from the history picked ----
WINDOW = ("2012Q3", "2013Q4")                  # Decide's Suggested for KeyBank's series in the build of 14 Oct 2026
lines5 = own(kb, window=WINDOW, z=3.5)
ind5 = BY[CN][IND]
steps.append({"id": "B5", "what": "Leave out %s to %s, the period Decide suggests, with a reason" % WINDOW,
              "shows": "%s's lines move as the reference says; the other sources' own lines do not; Assess lists "
                       "the period under %s's series, its Status whole" % (LEAD, LEAD),
              "actions": [typed(CN, "Leave out from", WINDOW[0]), typed(CN, "Leave out to", WINDOW[1]),
                          typed(CN, "Why left out", "Suggested by the evidence: unusual stretch")],
              "reads": [{"sheet": "Decide", "cell": "D%d" % DL["evidence"], "expect": "Leave out %s to %s" % WINDOW},
                        {"sheet": "Assess", "cell": "N%d" % AL["lo_top"], "expect": kb},
                        {"sheet": "Assess", "cell": "T%d" % AL["lo_top"], "expect": "Left out: 6 quarters"}]
                       + lbs_reads(kb, lines5) + lbs_reads(ind5, own(ind5, z=3.5)) + row_reads(CN, LEAD, lines5),
              "picture": []})

# ---- B6: half a period refuses, in words; then put it back ----
steps.append({"id": "B6", "what": "Clear the reason", "shows": "The lines are refused, saying why and what to do",
              "actions": [typed(CN, "Why left out", "")],
              "reads": [{"sheet": LBS, "cell": "%s%d" % (DT.TH_BOOK["refusal"], 5 + LABELS.index(kb)),
                         "expect": "Refused: a period left out for this product is not whole; its Status on Assess "
                                   "says what is missing"},
                        {"sheet": "Thresholds", "cell": "%s%d" % (TL["cols"]["check"], 5 + PAIRS.index(CN)),
                         "startswith": "To fix: Finish its row on Decide"},
                        {"sheet": "Decide", "cell": dcell("Check", CN), "expect": "Refused: see the fix below"}],
              "picture": []})
steps.append({"id": "B6b", "what": "Type the reason back", "shows": "The lines are back as in B5",
              "actions": [typed(CN, "Why left out", "Suggested by the evidence: unusual stretch")],
              "reads": lbs_reads(kb, lines5) + row_reads(CN, LEAD, lines5), "picture": []})

# ---- B7: the decision ----
steps.append({"id": "B7", "what": "Pick Accept these lines and write a note",
              "shows": "The count at the top; the decision on Thresholds, and on Lines by source beside the source "
                       "the lines are set from",
              "actions": [typed(CN, "Decision", "Accept these lines"),
                          typed(CN, "Note", "Walkthrough: accepted with z 3.5")],
              "reads": [{"sheet": "Decide", "cell": "L1", "expect": decided(1, 0)},
                        {"sheet": "Thresholds", "cell": "%s%d" % (TL["cols"]["decision"], 5 + PAIRS.index(CN)),
                         "expect": "Accept these lines"},
                        {"sheet": LBS, "cell": "%s%d" % (DT.TH_BOOK["decision"], 5 + LABELS.index(kb)),
                         "expect": "Accept these lines"},
                        {"sheet": LBS, "cell": "%s%d" % (DT.TH_BOOK["decision"], 5 + LABELS.index(ind5)),
                         "expect": ""}], "picture": []})

# ---- B8: KeyBank's short history rated on the industry's lines ----
AN = ("Auto", "Net charge-offs")
au, aui = BY[AN][LEAD], BY[AN][IND]
lines8 = own(aui)
r8, c8 = summary_cell(au)
steps.append({"id": "B8", "what": "Click Auto and Net charge-offs, and pick %s under %s" % (IND, DT.LINES_FROM),
              "shows": "%s's life-to-date history (%d quarters) rated on the lines the industry's longer history "
                       "gives; Summary agrees" % (LEAD, len(PTS[au])),
              "actions": slicers(**{NAMES[0]: AN[0], NAMES[1]: AN[1]}) + [typed(AN, DT.LINES_FROM, IND)],
              "reads": [{"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"] + PAIRS.index(AN)]},
                        {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(AN, IND)},
                        {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": chip(AN, lines8)},
                        {"sheet": "Summary", "cell": "%s%d" % (L(c8 + 1), r8), "expect": on_lines(au, lines8)[1]}]
                       + ([{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": OK}] if lines8["bounds"] else
                          [{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": lines8["M"]}])
                       + decide_reads(AN, lines8, every_own(AN)) + row_reads(AN, IND, lines8),
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b8-life-to-date.png"}]})

# ---- B9: lines that are refused, and the To fix ----
MN = ("Mortgage", "Net charge-offs")
mg = BY[MN][IND]
lines9 = own(mg)
steps.append({"id": "B9", "what": "Click Mortgage and Net charge-offs, and pick %s" % IND,
              "shows": "Refused, with what to type" if lines9["M"] else "The lines stand",
              "actions": slicers(**{NAMES[0]: MN[0], NAMES[1]: MN[1]}) + [typed(MN, DT.LINES_FROM, IND)],
              "reads": ([{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": lines9["M"]},
                         {"sheet": "Decide", "cell": "I%d" % DL["check"], "startswith": "To fix: "},
                         {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": "No rating: see the Check"},
                         {"sheet": "Thresholds", "cell": "%s%d" % (TL["cols"]["check"], 5 + PAIRS.index(MN)),
                          "startswith": "To fix: "}] if lines9["M"] else
                        [{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": OK}])
                       + row_reads(MN, IND, lines9) + lbs_reads(mg, lines9),
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b9-refused.png"}]})

# ---- B10: save, close, reopen ----
steps.append({"id": "B10", "what": "Save (Ctrl+S), close Excel, open the file again",
              "shows": "Every decision, pick and setting typed is still there, and the lines with them",
              "actions": [{"type": "reopen"}],
              "reads": [{"sheet": "Decide", "cell": dcell(DT.LINES_FROM, CN), "expect": LEAD},
                        {"sheet": "Decide", "cell": dcell("How rare High is (z)", CN), "expect": 3.5},
                        {"sheet": "Decide", "cell": dcell("Leave out from", CN), "expect": WINDOW[0]},
                        {"sheet": "Decide", "cell": dcell("Decision", CN), "expect": "Accept these lines"},
                        {"sheet": "Decide", "cell": dcell("Note", CN), "expect": "Walkthrough: accepted with z 3.5"},
                        {"sheet": "Decide", "cell": "L1", "expect": decided(1, 0)},
                        {"special": "slicers", "expect": {NAMES[0]: MN[0], NAMES[1]: MN[1]}}]
                       + lbs_reads(kb, lines5) + row_reads(CN, LEAD, lines5), "picture": []})

# ---- B11 to B13: the peer group follows the banks in the pack on Peers ----
# (the firm, 15 Oct 2026: "this tab needs to adjust with peers and i need a
# faster way to select and de-select peers"). The expected composites are
# summed here, in Python, from the per-bank rows the build wrote to Peers data
# and Peers delinquency data (facts per bank and quarter, values, not
# formulas), over the banks the step leaves in the pack; the workbook's live
# formulas must land on the same numbers.
from openpyxl import load_workbook                                   # noqa: E402
from threshold_engine.peers import peers_workbook as PW              # noqa: E402
from threshold_engine.peers import roster as RO                      # noqa: E402

BUILT = HERE / "out" / "consumer-credit.xlsx"
roster = RO.load(bk["peers"]["roster"])
peers_ = RO.peers(roster)
MB = bk["peers"]["min_banks"]
_wb = load_workbook(BUILT, read_only=True)
CO_ROWS = [r for r in _wb["Peers data"].iter_rows(min_row=2, values_only=True)]
DQ_ROWS = [r for r in _wb["Peers delinquency data"].iter_rows(min_row=2, values_only=True)]
LIVE = [("Credit card", "Net charge-offs", "net"), ("Other consumer", "Net charge-offs", "net"),
        ("Credit card", "90+ days past due incl. nonaccrual", "90+ incl. nonaccrual")]


def peer_label(product, measure):
    return next(lbl for lbl in LABELS if PARTS[lbl][0] == product and PARTS[lbl][1] == measure
                and PARTS[lbl][2] == PEER_SRC)


PEER_SRC = next(s_ for s_ in THIRD if s_.startswith("Peer group"))


def composite(product, kind, q, certs):
    if kind in ("net", "gross"):
        rows = [r for r in CO_ROWS if r[0] == product and r[3] == q and r[2] in certs and r[9] is True]
        if len(rows) < MB:
            return None
        g, rc, b = (sum(r[i] for r in rows) for i in (4, 5, 6))
        return 100 * ((g - rc) if kind == "net" else g) / b
    rows = [r for r in DQ_ROWS if r[0] == product and r[1] == kind and r[4] == q and r[3] in certs and r[8] is True]
    if len(rows) < MB:
        return None
    return 100 * sum(r[5] for r in rows) / sum(r[6] for r in rows)


def latest_live(product, measure, kind, certs):
    """The latest quarter the series had a value in, with a composite over
    ``certs``, and that value: what Lines by source must then show."""
    for pt in reversed(PTS[peer_label(product, measure)]):
        v = composite(product, kind, quarter(pt.date), certs)
        if v is not None:
            return quarter(pt.date), v
    return "", ""


def live_reads(certs):
    out = []
    for product, measure, kind in LIVE:
        q, v = latest_live(product, measure, kind, certs)
        r = 5 + LABELS.index(peer_label(product, measure))
        out += [{"sheet": LBS, "cell": "L%d" % r, "expect": q}, {"sheet": LBS, "cell": "M%d" % r, "expect": v}]
    return out


every = {b["cert"] for b in peers_}
regionals = {b["cert"] for b in peers_ if b["regional"]}
jpm = next(j for j, b in enumerate(peers_) if b["short"] == "JPMorgan")
PACK_CELL, JPM_CELL = PW.picker_cell("pack"), PW.include_cell(jpm)
steps.append({"id": "B11", "what": "On Peers, set Banks in the pack to Regionals only",
              "shows": "Every peer group series on Decide, Lines by source, Thresholds and Summary is summed over "
                       "the %d regionals: the latest values below are their composite" % len(regionals),
              "actions": [{"type": "cell", "sheet": "Peers", "cell": PACK_CELL, "value": PW.PACK_PICKS[1]}],
              "reads": live_reads(regionals), "picture": []})
steps.append({"id": "B12", "what": "Set Banks in the pack back to Every peer, and JPMorgan's cell to No",
              "shows": "The peer group is every peer but JPMorgan",
              "actions": [{"type": "cell", "sheet": "Peers", "cell": PACK_CELL, "value": PW.PACK_PICKS[0]},
                          {"type": "cell", "sheet": "Peers", "cell": JPM_CELL, "value": PW.NO}],
              "reads": live_reads(every - {peers_[jpm]["cert"]}), "picture": []})
steps.append({"id": "B13", "what": "Set JPMorgan's cell back to Pack",
              "shows": "The peer group is every peer again: each latest value is the series file's own",
              "actions": [{"type": "cell", "sheet": "Peers", "cell": JPM_CELL, "value": PW.FOLLOW}],
              "reads": live_reads(every) + [
                  {"sheet": LBS, "cell": "M%d" % (5 + LABELS.index(peer_label(pr, me))),
                   "expect": PTS[peer_label(pr, me)][-1].value} for pr, me, _ in LIVE], "picture": []})

(HERE / "steps.json").write_text(json.dumps({"book": str(BOOK), "series": N, "rows": len(PAIRS), "steps": steps},
                                            indent=1, default=str), encoding="utf-8")
lines = ["# Expected answers: the book walkthrough", "",
         "From `%s` and the series files the build wrote, through `scale.py`. %d series, %d products and measures."
         % (BOOK.name, N, len(PAIRS)), ""]
for s in steps:
    lines += ["## %s · %s" % (s["id"], s["what"]), "", s["shows"] + ".", "",
              "%d reads." % len(s["reads"]), ""]
(HERE / "EXPECTED.md").write_text("\n".join(lines), encoding="utf-8")
print("%d steps, %d reads" % (len(steps), sum(len(s["reads"]) for s in steps)))
