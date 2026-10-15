"""The book walkthrough's expected answers, from the source files, not the workbook.

Run from threshold-engine/, after the build (WALKTHROUGH.md, step 1):
    python docs/walkthrough-book/expected.py
Writes steps.json (what to click and type, where, and what each cell must then
say) and EXPECTED.md (the same, for a person). Every number comes from the
series CSVs the build read and scale.py, the reference the workbook's formulas
are held to; walk.ps1 does each step in Excel 16 and reads the answer back.

The steps are cumulative, as a person's session is: what step 3 types is
still there in step 4, and step 9 saves, closes and reopens the file to show
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
from threshold_engine.scale import scale, score                      # noqa: E402
from threshold_engine.series import check, read_csv                  # noqa: E402
from threshold_engine.workbook import assess_layout, quarter         # noqa: E402

HERE = Path(__file__).parent
BOOK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "books" / "consumer-public.json"
RATINGS = ["Low", "Moderate-Low", "Moderate", "Moderate-High", "High"]

bk = BK.load(BOOK)
W = bk["workbook"]
SER = bk["series"]
LABELS = [lbl for lbl, _ in SER]
N = len(SER)
PARTS = bk["decide"]["parts"]
NAMES = bk["decide"]["names"]
COMPARE = bk["decide"]["compare"]
THIRD = []
for lbl in LABELS:
    if PARTS[lbl][2] not in THIRD:
        THIRD.append(PARTS[lbl][2])
COLS = DT.columns(NAMES)
DL = DT.layout(N, len(THIRD), COMPARE is not None)
AL = assess_layout(N)
PTS = {lbl: check(read_csv(p), "quarterly") for lbl, p in SER}
from openpyxl.utils import get_column_letter as L                    # noqa: E402


def dcell(name, lbl):
    return "%s%d" % (L(COLS[name]), DL["first"] + LABELS.index(lbl))


def refusal_text(msg):
    if msg.startswith("too little history"):
        return "Refused: too little history kept for a typical yearly move"
    if msg.startswith("High would begin beyond the worst"):
        return "Refused: High would begin beyond the worst quarter kept"
    return "Refused: " + msg


def thresholds(lbl, window=None, hw=None, ls=None, z=None, rule=None):
    hw = W["moderate_halfwidth"] if hw is None else hw
    ls = W["low_step"] if ls is None else ls
    z = W["high_z"] if z is None else z
    rule = W["on_the_line"] if rule is None else rule
    kept = [None if window and window[0] <= quarter(p.date) <= window[1] else p.value for p in PTS[lbl]]
    ref = scale(kept, W["direction"], hw, ls, z, W["floor_at_zero"])
    latest = PTS[lbl][-1]
    row = {"B": ref["median"], "C": ref["typical_yearly_move"], "D": max(v for v in kept if v is not None),
           "I": quarter(latest.date), "J": latest.value}
    if ref["refused"]:
        row.update({"K": "", "M": refusal_text(ref["refused"])})
        return row
    row.update(zip("EFGH", ref["bounds"]))
    sc = score(latest.value, ref["bounds"], W["direction"], rule, W["floor_at_zero"])
    row.update({"K": sc, "L": RATINGS[sc - 1], "M": ""})
    return row


#: thresholds() keys its answers by the plain layout's letters; the book lays
#: Thresholds out differently (decide_tab.TH_BOOK), so each is read by meaning.
PLAIN_TO_BOOK = {DT.TH_PLAIN[k]: DT.TH_BOOK[k] for k in DT.TH_PLAIN}


def th_reads(lbl, row):
    r = 5 + LABELS.index(lbl)
    return [{"sheet": "Thresholds", "cell": "%s%d" % (PLAIN_TO_BOOK[c], r), "expect": v} for c, v in row.items()]


def rating_text(row):
    return "Refused" if row["K"] == "" else "%d %s" % (row["K"], row["L"])


def headline(lbl, row):
    p, m, s = PARTS[lbl]
    return "%s, %s, %s: %.2f%s in %s" % (s, m.lower(), p.lower(), row["J"], W["unit"], row["I"])


def chip(row):
    return "No rating: see the Check" if row["K"] == "" else "%d %s" % (row["K"], row["L"])


def decided(n_acc, n_rej):
    return "Decided: %d of %d · accepted %d · rejected %d" % (n_acc + n_rej, N, n_acc, n_rej)


def summary_cell(lbl):
    """The row and column of a series' latest value on Summary; its rating is
    the next column (summary_tab.layout, the builder's own)."""
    r, latest, _ = SU.layout(LABELS, PARTS, COMPARE)["cells"][lbl]
    return r, latest


def slicers(**picks):
    return [{"type": "slicer", "caption": k, "value": v} for k, v in picks.items()]


def typed(lbl, name, value):
    return {"type": "cell", "sheet": "Decide", "cell": dcell(name, lbl), "value": value}


steps = []
# ---- B1: open ----
first = LABELS[0]
steps.append({"id": "B1", "what": "Open the workbook as built",
              "shows": "It opens on Summary; the tabs in order; three slicers, each with one button picked; "
                       "Decide shows the first series and nothing decided",
              "actions": [], "reads": [
                  {"special": "active", "expect": "Summary"},
                  {"special": "sheets", "expect": ["Decide", "Summary", "Peers", "Thresholds", "Internal", "Evidence",
                                                   "Backtest", "Glossary", "Sources", "Run", "Data", "Peers data",
                                                   "Peers delinquency data", "Internal data", "Assess", "Chart",
                                                   "Peers workings"]},
                  {"special": "slicers", "expect": {n: v for n, v in zip(NAMES, PARTS[first])}},
                  {"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"]]},
                  {"sheet": "Decide", "cell": "L1", "expect": decided(0, 0)},
                  {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(first, thresholds(first))},
                  {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": chip(thresholds(first))},
                  {"special": "links", "expect": []},
                  {"special": "errors", "expect": 0}],
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b1-decide.png"},
                          {"sheet": "Summary", "range": "A1:T34", "file": "b1-summary.png"}]})

# ---- B2: every Summary cell against the reference ----
reads = []
for lbl in LABELS:
    row = thresholds(lbl)
    r, c = summary_cell(lbl)
    reads.append({"sheet": "Summary", "cell": "%s%d" % (L(c), r), "expect": row["J"]})
    reads.append({"sheet": "Summary", "cell": "%s%d" % (L(c + 1), r), "expect": rating_text(row)})
steps.append({"id": "B2", "what": "Read Summary", "shows": "Every series' latest value and rating, %d series" % N,
              "actions": [], "reads": reads, "picture": []})

# ---- B3: click KeyBank, credit card, nonaccrual ----
kb = "Credit card - Nonaccrual - KeyBank"
row = thresholds(kb)
cmp_reads = []
for i, src in enumerate(THIRD):
    lab = "%s - %s - %s" % ("Credit card", "Nonaccrual", src)
    rr = thresholds(lab)
    cmp_reads += [{"sheet": "Decide", "cell": "N%d" % (DL["compare_first"] + i), "expect": rr["J"]},
                  {"sheet": "Decide", "cell": "M%d" % (DL["compare_first"] + i), "expect": rating_text(rr)}]
steps.append({"id": "B3", "what": "On Decide, click Credit card, Nonaccrual, KeyBank",
              "shows": "One row shows, KeyBank's; the screen speaks for it and sets it beside the industry and peers",
              "actions": slicers(Product="Credit card", Measure="Nonaccrual", Source="KeyBank"),
              "reads": [{"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"] + LABELS.index(kb)]},
                        {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(kb, row)},
                        {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": chip(row)},
                        {"sheet": "Decide", "cell": "B%d" % DL["check"],
                         "expect": "Check: OK, your settings fit this series."}]
                       + [{"sheet": "Decide", "cell": "M%d" % (DL["ratings_first"] + 1 + j), "expect": row[c]}
                          for j, c in enumerate("EFGH")] + cmp_reads + th_reads(kb, row),
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b3-decide.png"}]})

# ---- B4: raise How rare High is to 3.5 on that row ----
row4 = thresholds(kb, z=3.5)
r, c = summary_cell(kb)
steps.append({"id": "B4", "what": "Type 3.5 under How rare High is (z), in the yellow row",
              "shows": "Only High's line moves; Thresholds and Summary follow",
              "actions": [typed(kb, "How rare High is (z)", 3.5)],
              "reads": th_reads(kb, row4) + [{"sheet": "Summary", "cell": "%s%d" % (L(c + 1), r),
                                              "expect": rating_text(row4)}], "picture": []})

# ---- B5: leave out what the evidence suggests ----
WINDOW = ("2012Q3", "2013Q4")                  # Decide's Suggested for this series in the build of 14 Oct 2026
row5 = thresholds(kb, window=WINDOW, z=3.5)
steps.append({"id": "B5", "what": "Leave out %s to %s, the period Decide suggests, with a reason" % WINDOW,
              "shows": "The lines move as the reference says; Assess lists the period, its Status whole",
              "actions": [typed(kb, "Leave out from", WINDOW[0]), typed(kb, "Leave out to", WINDOW[1]),
                          typed(kb, "Why left out", "Suggested by the evidence: unusual stretch")],
              "reads": [{"sheet": "Decide", "cell": "D%d" % DL["evidence"], "expect": "Leave out %s to %s" % WINDOW},
                        {"sheet": "Assess", "cell": "N%d" % AL["lo_top"], "expect": kb},
                        {"sheet": "Assess", "cell": "T%d" % AL["lo_top"], "expect": "Left out: 6 quarters"}]
                       + th_reads(kb, row5), "picture": []})

# ---- B6: half a period refuses, in words; then put it back ----
steps.append({"id": "B6", "what": "Clear the reason", "shows": "The series is refused, saying why",
              "actions": [typed(kb, "Why left out", "")],
              "reads": [{"sheet": "Thresholds", "cell": "%s%d" % (DT.TH_BOOK["refusal"], 5 + LABELS.index(kb)),
                         "expect": "Refused: a period left out for this product is not whole; its Status on Assess "
                                   "says what is missing"}], "picture": []})
steps.append({"id": "B6b", "what": "Type the reason back", "shows": "The lines are back as in B5",
              "actions": [typed(kb, "Why left out", "Suggested by the evidence: unusual stretch")],
              "reads": th_reads(kb, row5), "picture": []})

# ---- B7: the decision ----
steps.append({"id": "B7", "what": "Pick Accept these lines and write a note",
              "shows": "The count at the top", "actions": [typed(kb, "Decision", "Accept these lines"),
                                                           typed(kb, "Note", "Walkthrough: accepted with z 3.5")],
              "reads": [{"sheet": "Decide", "cell": "L1", "expect": decided(1, 0)},
                        {"sheet": "Thresholds", "cell": "%s%d" % (DT.TH_BOOK["decision"], 5 + LABELS.index(kb)),
                         "expect": "Accept these lines"}], "picture": []})

# ---- B8: life to date ----
au = "Auto - Net charge-offs - KeyBank"
row8 = thresholds(au)
r8, c8 = summary_cell(au)
steps.append({"id": "B8", "what": "Click Auto, Net charge-offs, KeyBank",
              "shows": "Life to date: %d quarters, its lines shown and the Check in words; Summary agrees"
                       % len(PTS[au]),
              "actions": slicers(Product="Auto", Measure="Net charge-offs", Source="KeyBank"),
              "reads": [{"special": "visible_rows", "sheet": "Decide", "expect": [DL["first"] + LABELS.index(au)]},
                        {"sheet": "Decide", "cell": "B%d" % DL["headline"], "expect": headline(au, row8)},
                        {"sheet": "Summary", "cell": "%s%d" % (L(c8 + 1), r8), "expect": rating_text(row8)}]
                       + ([{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": row8["M"]},
                           {"sheet": "Decide", "cell": "I%d" % DL["check"], "startswith": "To fix: "}]
                          if row8["M"] else []) + th_reads(au, row8),
              "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1), "file": "b8-life-to-date.png"}]})

# ---- B9: a refused series, and its To fix followed ----
mg = "Mortgage - Net charge-offs - Industry (every bank)"
row9 = thresholds(mg)
steps.append({"id": "B9", "what": "Click Mortgage, Net charge-offs, Industry",
              "shows": "Refused, with what to type", "actions": slicers(Product="Mortgage", Measure="Net charge-offs",
                                                                         Source="Industry (every bank)"),
              "reads": [{"sheet": "Decide", "cell": "B%d" % DL["check"], "expect": row9["M"]},
                        {"sheet": "Decide", "cell": "I%d" % DL["check"], "startswith": "To fix: "},
                        {"sheet": "Decide", "cell": "I%d" % DL["chip"], "expect": "No rating: see the Check"}]
                       + th_reads(mg, row9), "picture": [{"sheet": "Decide", "range": "A1:Q%d" % (DL["notes"] + 1),
                                                          "file": "b9-refused.png"}]})

# ---- B10: save, close, reopen ----
steps.append({"id": "B10", "what": "Save (Ctrl+S), close Excel, open the file again",
              "shows": "Every decision and setting typed is still there, and the lines with them",
              "actions": [{"type": "reopen"}],
              "reads": [{"sheet": "Decide", "cell": dcell("How rare High is (z)", kb), "expect": 3.5},
                        {"sheet": "Decide", "cell": dcell("Leave out from", kb), "expect": WINDOW[0]},
                        {"sheet": "Decide", "cell": dcell("Decision", kb), "expect": "Accept these lines"},
                        {"sheet": "Decide", "cell": dcell("Note", kb), "expect": "Walkthrough: accepted with z 3.5"},
                        {"sheet": "Decide", "cell": "L1", "expect": decided(1, 0)},
                        {"special": "slicers", "expect": {"Product": "Mortgage", "Measure": "Net charge-offs",
                                                          "Source": "Industry (every bank)"}}] + th_reads(kb, row5),
              "picture": []})

(HERE / "steps.json").write_text(json.dumps({"book": str(BOOK), "series": N, "steps": steps},
                                            indent=1, default=str), encoding="utf-8")
lines = ["# Expected answers: the book walkthrough", "",
         "From `%s` and the series files the build wrote, through `scale.py`. %d series." % (BOOK.name, N), ""]
for s in steps:
    lines += ["## %s · %s" % (s["id"], s["what"]), "", s["shows"] + ".", "",
              "%d reads." % len(s["reads"]), ""]
(HERE / "EXPECTED.md").write_text("\n".join(lines), encoding="utf-8")
print("%d steps, %d reads" % (len(steps), sum(len(s["reads"]) for s in steps)))
