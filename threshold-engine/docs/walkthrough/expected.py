"""The walkthrough's expected answers, written before the walkthrough is run.

Run from threshold-engine/:  python docs/walkthrough/expected.py
Writes steps.json (what to type, where, and what each cell must then say) and
EXPECTED.md (the same, for a person). The answers come from the source files
and scale.py, the reference the workbook's formulas are held to; walk.ps1
then does each step in Excel 16 and reads the answers off the workbook.

Two answers do not come from scale.py at all: the card lines and counts with
the crisis and the pandemic left out were recorded in LOG.md on 7 Oct 2026,
when this scale was agreed (3.171 / 3.464 / 4.050 / 5.981; 25 / 22 / 29 / 55
/ 4). The 6 Oct figures in LOG.md (3.757 / 4.469 / ...) belong to the scale
retired that evening and are not an answer for this one. And the input
files' fingerprints are taken with hashlib from the files themselves.
"""
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from threshold_engine.backtest import backtest                     # noqa: E402
from threshold_engine.evidence import evidence                     # noqa: E402
from threshold_engine.scale import scale, score                    # noqa: E402
from threshold_engine.series import check, read_csv                # noqa: E402
from threshold_engine.workbook import assess_layout, quarter       # noqa: E402

HERE = Path(__file__).parent
PRODUCTS = [("Credit card", "tests/data/cards_nco_ttm.csv"), ("Mortgage", "tests/data/mortgage_nco_ttm.csv"),
            ("Home equity", "tests/data/home_equity_nco_ttm.csv"),
            ("Other consumer", "tests/data/other_consumer_as_filed_nco_ttm.csv")]
SETTINGS = dict(halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse")
CRISIS = ("2007Q4", "2012Q4", "financial crisis")
PANDEMIC = ("2021Q3", "2023Q1", "pandemic forbearance")
RATINGS = ["Low", "Moderate-Low", "Moderate", "Moderate-High", "High"]
BUILD = ('python -m threshold_engine workbook "{out}" '
         + " ".join('--series "%s=%s"' % (lbl, f) for lbl, f in PRODUCTS)
         + ' --name "Net charge-off rate (TTM)" --unit "%" --direction higher_is_worse --frequency quarterly'
           ' --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5'
           ' --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41')

PTS = {lbl: check(read_csv(ROOT / f), "quarterly") for lbl, f in PRODUCTS}
CAL = sorted({quarter(p.date) for pts in PTS.values() for p in pts})


def kept(lbl, windows=()):
    out = []
    for p in PTS[lbl]:
        q = quarter(p.date)
        out.append(None if any(a <= q <= b for a, b, *_ in windows) else p.value)
    return out


def refusal_text(msg):
    """scale.py's refusal, as the workbook's Check column words it."""
    if msg.startswith("too little history"):
        return "Refused: too little history kept for a typical yearly move"
    if msg.startswith("High would begin beyond the worst"):
        return "Refused: High would begin beyond the worst quarter kept"
    return "Refused: " + msg


def thresholds(lbl, windows=(), hw=0.5, ls=1.0, z=2.5, rule="worse"):
    """What Thresholds row and Assess counts must say for one product."""
    k = kept(lbl, windows)
    ref = scale(k, "higher_is_worse", hw, ls, z, True)
    vals = [v for v in k if v is not None]
    latest = PTS[lbl][-1]
    row = {"B": ref["median"], "C": ref["typical_yearly_move"], "D": max(vals), "I": quarter(latest.date),
           "J": latest.value}
    if ref["refused"]:
        row["M"] = refusal_text(ref["refused"])
        row["K"] = ""
        return row, None
    row.update(zip("EFGH", ref["bounds"]))
    sc = score(latest.value, ref["bounds"], "higher_is_worse", rule, True)
    row.update({"K": sc, "L": RATINGS[sc - 1], "M": ""})
    cnt_kept = [sum(1 for v in vals if score(v, ref["bounds"], "higher_is_worse", rule, True) == s)
                for s in range(1, 6)]
    cnt_all = [sum(1 for p in PTS[lbl] if score(p.value, ref["bounds"], "higher_is_worse", rule, True) == s)
               for s in range(1, 6)]
    return row, (cnt_kept, cnt_all)


def settings_actions(row, windows=(), hw=None, ls=None, z=None, rule=None):
    acts = []
    for (a, b, why), (ca, cb, cw) in zip(windows, (("B", "C", "D"), ("E", "F", "G"))):
        acts += [("Settings", "%s%d" % (ca, row), a), ("Settings", "%s%d" % (cb, row), b),
                 ("Settings", "%s%d" % (cw, row), why)]
    for col, v in (("H", hw), ("I", ls), ("J", z), ("K", rule)):
        if v is not None:
            acts.append(("Settings", "%s%d" % (col, row), v))
    return acts


def reads_for(lbl, row_th, exp, counts, assess=True):
    r = 5 + [p for p, _ in PRODUCTS].index(lbl)
    reads = [("Thresholds", "%s%d" % (c, r), v) for c, v in sorted(exp.items())]
    if assess and counts:
        reads += [("Assess", "Q%d" % (10 + i), n) for i, n in enumerate(counts[0])]
        reads += [("Assess", "S%d" % (10 + i), n) for i, n in enumerate(counts[1])]
    if assess and not counts:
        reads.append(("Assess", "B6", {"startswith": exp["M"] + ". To fix: "}))
    return reads


STEPS = []
LAY = assess_layout(len(PRODUCTS))


def on_assess(actions):
    """Since 13 Oct 2026 every input is on Assess. The steps still name the old
    Settings cells (row 6 Credit card ... 9; B-D a first period left out, E-G a
    second, H-K the three distances and the on-the-line rule), which read well;
    this puts each where it now is. A period becomes a row of Periods left out
    that names its product; a setting, a cell of Your settings."""
    out = []
    for sheet, ref, v in actions:
        if sheet != "Settings":
            out.append((sheet, ref, v))
            continue
        col, k = ref[0], int(ref[1:]) - 6
        if col in "BCDEFG":
            r = LAY["lo_top"] + 2 * k + (0 if col in "BCD" else 1)
            if ("Assess", "N%d" % r, PRODUCTS[k][0]) not in out:
                out.append(("Assess", "N%d" % r, PRODUCTS[k][0]))
            out.append(("Assess", "%s%d" % ("OPQ"["BCDEFG".index(col) % 3], r), v))
        else:
            out.append(("Assess", "%s%d" % ("OPQR"["HIJK".index(col)], LAY["set_top"] + k), v))
    return out


def step(sid, title, how, actions, reads, picture=None, product="Credit card", note=""):
    actions = on_assess(actions)
    if actions and not how.startswith("Type "):
        how += " Typed on Assess: " + "; ".join("%s %s" % (c, v) for _, c, v in actions) + "."
    STEPS.append({"id": sid, "title": title, "how": how, "product": product, "note": note,
                  "actions": [{"sheet": s, "cell": c, "value": v} for s, c, v in actions],
                  "reads": [{"sheet": s, "cell": c, "expected": v} for s, c, v in reads],
                  "picture": picture or []})


# W1 the build, read off Excel
step("W1", "Build the four-product workbook and open it",
     "Run the build command (section 1), then open the file in Excel.",
     [], [("=", "COUNTA(Data!A2:A1000)", len(CAL)), ("=", "Data!A2", CAL[0]),
          ("=", "INDEX(Data!A2:A1000,%d)" % len(CAL), CAL[-1]),
          ("=", "COUNTA(Thresholds!A5:A8)", 4), ("=", "COUNTA(Glossary!A5:A200)", 36)]
     + [("Thresholds", "A%d" % (5 + i), lbl) for i, (lbl, _) in enumerate(PRODUCTS)],
     picture=[{"sheet": "Thresholds", "range": "A1:M10", "file": "w1-thresholds.png"},
              {"sheet": "Assess", "range": "M16:U38", "file": "w1-assess-inputs.png"}],
     note="Sheets, in order: Assess, Thresholds, Chart, Evidence, Backtest, Sources, Glossary, Data, Run. "
          "The Glossary count was 33 when first written, from WHAT-IT-DOES.md; the first run found 35, and "
          "the document was out of date (two terms added since 6 Oct). Corrected here and there.")

# W2 every product as built
reads = []
for i, (lbl, _) in enumerate(PRODUCTS):
    exp, cnt = thresholds(lbl)
    reads += reads_for(lbl, 5 + i, exp, cnt, assess=False)
step("W2", "Thresholds as built: every product, nothing left out",
     "Read the Thresholds tab. Nothing typed yet.", [], reads)

# W3 Assess, each product picked from the list
for i, (lbl, _) in enumerate(PRODUCTS):
    exp, cnt = thresholds(lbl)
    rr = [("Assess", "B6", "Check: OK. Every setting is valid and every period left out is complete.")] \
        + [("Assess", "Q%d" % (10 + j), n) for j, n in enumerate(cnt[0])] \
        + [("Assess", "S%d" % (10 + j), n) for j, n in enumerate(cnt[1])] \
        + [("Assess", "O11", exp["E"]), ("Assess", "O14", exp["H"])]
    # The chart's floor and top (added after the first run, which found them #N/A in Excel for every product
    # whose data starts after the calendar): floor = MIN(0, data, lines); top 8% of the range above the highest.
    vals = [p.value for p in PTS[lbl]] + [exp[c] for c in "EFGH"]
    lo = min(0, min(vals))
    rr += [("Assess", "AI3", lo), ("Assess", "AI2", max(vals) + 0.08 * (max(vals) - lo)),
           ("Assess", "AJ2", lo), ("Assess", "AD2", exp["E"] - lo)]
    step("W3.%d" % (i + 1), "Assess: pick %s" % lbl, "On Assess, pick %s in B4." % lbl,
         [("Assess", "B5", lbl)], rr, product=lbl,
         picture=[{"sheet": "Assess", "chart": 1, "file": "w3-assess-%d.png" % (i + 1)}] if i in (0, 2) else [])

# W4, W5 the card leave-outs
exp, cnt = thresholds("Credit card", [CRISIS])
step("W4", "Leave out the financial crisis on Credit card",
     "Settings row 6: B6 2007Q4, C6 2012Q4, D6 'financial crisis'.",
     settings_actions(6, [CRISIS]), reads_for("Credit card", 5, exp, cnt))
REH = [CRISIS, PANDEMIC]
exp, cnt = thresholds("Credit card", REH)
step("W5", "Add the second leave-out: the pandemic (the rehearsal settings)",
     "Also E6 2021Q3, F6 2023Q1, G6 'pandemic forbearance'. Expected to equal LOG.md, 7 Oct: "
     "3.171 / 3.464 / 4.050 / 5.981, and 25 / 22 / 29 / 55 / 4 quarters kept.",
     settings_actions(6, REH), reads_for("Credit card", 5, exp, cnt)
     + [("Run", "A21", "Credit card"), ("Run", "B21", "2007Q4"), ("Run", "C21", "2012Q4"),
        ("Run", "D21", "financial crisis"), ("Run", "E21", "Left out: 21 quarters"),
        ("Run", "A22", "Credit card"), ("Run", "B22", "2021Q3"), ("Run", "C22", "2023Q1"),
        ("Run", "D22", "pandemic forbearance"), ("Run", "E22", "Left out: 7 quarters"),
        ("Assess", "T%d" % LAY["lo_top"], "Left out: 21 quarters")]
     + [("Assess", "%s%d" % (c, LAY["scen_yours"]), v) for c, v in zip("CDEF", [exp[x] for x in "EFGH"])]
     + [("Assess", "%s%d" % (c, LAY["scen_all"]), v) for c, v in zip("CDEF", [thresholds("Credit card")[0][x]
                                                                         for x in "EFGH"])],
     picture=[{"sheet": "Thresholds", "range": "A1:M10", "file": "w5-thresholds.png"},
              {"sheet": "Assess", "chart": 1, "file": "w5-assess-cards-rehearsal.png"},
              {"sheet": "Assess", "range": "M8:U15", "file": "w5-assess-counts.png"}])
LOG_7OCT = {"E": 3.171, "F": 3.464, "G": 4.050, "H": 5.981}
assert all(abs(exp[c] - v) < 0.0005 for c, v in LOG_7OCT.items()), "scale.py no longer gives the 7 Oct lines"
assert cnt[0] == [25, 22, 29, 55, 4], "scale.py no longer gives the 7 Oct counts"

# W6-W8 each distance, from the rehearsal settings; the dial's row must agree
DIAL = {"hw": (LAY["dials"]["halfwidth"], [0.25, 0.5, 0.75, 1.0]),
        "ls": (LAY["dials"]["low_step"], [0.75, 1.0, 1.5, 2.0]),
        "z": (LAY["dials"]["high_z"], [2.0, 2.5, 3.0, 3.5])}
for sid, key, val, text in (("W6", "hw", 0.75, "Moderate's half-width 0.5 to 0.75 (H6)"),
                            ("W7", "ls", 1.5, "Moderate-Low step 1.0 to 1.5 (I6)"),
                            ("W8", "z", 3.0, "High's z 2.5 to 3.0 (J6)")):
    kw = {"hw": 0.5, "ls": 1.0, "z": 2.5, key: val}
    exp, cnt = thresholds("Credit card", REH, **kw)
    dial_row = DIAL[key][0] + DIAL[key][1].index(val)
    rr = reads_for("Credit card", 5, exp, cnt) + [("Assess", "%s%d" % (c, dial_row), exp[t])
                                                   for c, t in zip("CDEF", "EFGH")]
    rr += [("Assess", "%s%d" % (c, dial_row), n) for c, n in zip("GHIJK", cnt[0])]
    step(sid, text, "From the rehearsal settings, change %s. The dial row for %g on Assess must say the same."
         % (text.split(" (")[0], val), settings_actions(6, REH, **kw), rr)

# W9 the on-the-line rule, where it matters: half-width 0 puts two lines on the median, a value cards took
for sid, rule in (("W9a", "worse"), ("W9b", "better")):
    exp, cnt = thresholds("Credit card", REH, hw=0, rule=rule)
    step(sid, "On the line takes the %s score (half-width 0)" % rule,
         "From the rehearsal settings, H6 0 and K6 '%s'. The median kept (%.3f) is a quarter cards actually "
         "had, so it sits on two lines and the rule decides its score." % (rule, exp["B"]),
         settings_actions(6, REH, hw=0, rule=rule), reads_for("Credit card", 5, exp, cnt))
assert thresholds("Credit card", REH, hw=0, rule="worse")[1] != thresholds("Credit card", REH, hw=0, rule="better")[1]

# W10 a refusal of each kind, triggered on purpose, Check read off Thresholds and Assess
LO = "Refused: a period left out for this product is not whole; its Status on Assess says what is missing"


def refuse(sid, title, acts, text, lbl="Credit card", status=None):
    r = 5 + [p for p, _ in PRODUCTS].index(lbl)
    full = on_assess(acts + ([("Assess", "B5", lbl)] if lbl != "Credit card" else []))
    typed = "; ".join("%s!%s %s" % (sh, c, v) for sh, c, v in full)
    reads = [("Thresholds", "M%d" % r, text), ("Thresholds", "K%d" % r, ""),
             ("Assess", "B6", {"startswith": text + ". To fix: "})]
    if status:
        reads += [("Assess", "T%d" % row_, st_) for row_, st_ in status]
    step(sid, "Refused: " + title, "Type %s; read the Check column and Assess." % typed, full, reads, product=lbl)


refuse("W10.1", "a leave-out with a start and nothing else", [("Settings", "B6", "2008Q1")], LO,
       status=[(LAY["lo_top"], "Missing: To, reason (Credit card refused)")])
refuse("W10.2", "a second leave-out in reverse order",
       [("Settings", "E6", "2021Q1"), ("Settings", "F6", "2020Q1"), ("Settings", "G6", "x")], LO,
       status=[(LAY["lo_top"] + 1, "From is after To (Credit card refused)")])
refuse("W10.3", "a leave-out with no reason", [("Settings", "B6", "2008Q1"), ("Settings", "C6", "2012Q4")],
       LO, status=[(LAY["lo_top"], "Missing: reason (Credit card refused)")])
refuse("W10.4", "a half-width below 0", [("Settings", "H6", -0.1)], "Refused: Moderate's half-width must be 0 or more")
refuse("W10.5", "a z of 0", [("Settings", "J6", 0)], "Refused: High's z must be above 0")
refuse("W10.6", "a step typed as text", [("Settings", "I6", "one")], "Refused: Moderate-Low's step must be a number")
w = [("1985Q4", "2025Q2", "test")]
assert thresholds("Credit card", w)[0]["M"] == "Refused: too little history kept for a typical yearly move"
refuse("W10.7", "too little history kept", settings_actions(6, w),
       "Refused: too little history kept for a typical yearly move")

# the median at or below zero: keep only a stretch whose median is <= 0, on a product that has one
found = None
for i, (lbl, _) in enumerate(PRODUCTS):
    qs = [quarter(p.date) for p in PTS[lbl]]
    vs = [p.value for p in PTS[lbl]]
    for a in range(len(vs)):
        for b in range(len(vs) - 1, a + 5, -1):
            if statistics.median(vs[a:b + 1]) <= 0:
                cand = (lbl, i, a, b)
                if not found or (b - a) > (found[3] - found[2]):
                    found = cand
                break
assert found, "no product has a stretch with a median at or below zero"
lbl, i, a, b = found
qs = [quarter(p.date) for p in PTS[lbl]]
w = ([(CAL[0], qs[a - 1], "test")] if a > 0 else []) + ([(qs[b + 1], CAL[-1], "test")] if b + 1 < len(qs) else [])
if len(w) == 1 and a == 0:
    pass
exp_m = thresholds(lbl, w)[0]
assert exp_m["M"] == "Refused: the median is at or below zero", exp_m
refuse("W10.8", "the median at or below zero (%s, keeping %s to %s)" % (lbl, qs[a], qs[b]),
       settings_actions(6 + i, w), exp_m["M"], lbl=lbl)

refuse("W10.9", "Moderate-Low inside Moderate", [("Settings", "I6", 0.4)],
       "Refused: Moderate-Low must begin further from the median than Moderate")
for z in (0.5, 0.4, 0.3, 0.2, 0.1, 0.05):
    if thresholds("Credit card", (), z=z)[0].get("M") == "Refused: High must begin beyond Moderate-High's line":
        break
else:
    raise SystemExit("no small z refuses High inside Moderate-High")
refuse("W10.10", "High inside Moderate-High (z %g)" % z, [("Settings", "J6", z)],
       "Refused: High must begin beyond Moderate-High's line")
for z in (5, 8, 10, 15, 20):
    if thresholds("Credit card", (), z=z)[0].get("M") == "Refused: High would begin beyond the worst quarter kept":
        break
else:
    raise SystemExit("no large z puts High beyond the worst")
refuse("W10.11", "High beyond the worst quarter kept (z %g)" % z, [("Settings", "J6", z)],
       "Refused: High would begin beyond the worst quarter kept")
for ls in (2, 3, 4, 5, 6, 8, 10):
    if thresholds("Credit card", (), ls=ls)[0].get("M") == "Refused: Moderate-Low would begin at or below zero":
        break
else:
    raise SystemExit("no step puts Moderate-Low at or below zero")
refuse("W10.12", "Moderate-Low at or below zero (step %g)" % ls, [("Settings", "I6", ls)],
       "Refused: Moderate-Low would begin at or below zero")

# W11 the Run tab: fingerprints of the files themselves
step("W11", "Run tab: each file's fingerprint and the decisions as typed",
     "Read Run C9:C12 and compare with the SHA-256 of each file (certutil -hashfile FILE SHA256).", [],
     [("Run", "F%d" % (14 + i), hashlib.sha256((ROOT / f).read_bytes()).hexdigest()) for i, (_, f) in enumerate(PRODUCTS)]
     + [("Run", "C%d" % (14 + i), len(PTS[lbl])) for i, (lbl, _) in enumerate(PRODUCTS)]
     + [("Run", "E%d" % (21 + i), "") for i in range(12)],
     picture=[{"sheet": "Run", "range": "A1:F40", "file": "w11-run.png"}])

# W12 the Chart tab's switches
step("W12", "Chart: switch Mortgage off", "Chart B3: FALSE. Mortgage's column is #N/A (nothing drawn).",
     [("Chart", "C5", False)], [("Chart", "AP2", "#N/A"), ("=", "ISNUMBER(Chart!AO2)", True)],
     picture=[{"sheet": "Chart", "chart": 1, "file": "w12-chart.png"}])

# W13 Evidence and Backtest, written at build: the same as the evidence and backtest commands
ev = evidence(PTS["Credit card"], "Credit card", "%", "higher_is_worse", "quarterly", 1, None, True)
sp = ev["spells"]
bt = backtest(PTS["Credit card"], "Credit card", "%", "higher_is_worse", "quarterly", 1, (50, 75, 90, 95), 4, 41,
              True)
res = bt["runs"][0]
step("W13", "Evidence and Backtest for Credit card",
     "Read Evidence rows 6-9 (spells) and Backtest row 6.", [],
     [("Evidence", "E%d" % (6 + j), s["robust_z"]) for j, s in enumerate(sp)]
     + [("Evidence", "B%d" % (6 + j), quarter(s["peak_date"])) for j, s in enumerate(sp)]
     + [("Backtest", "C6", res["score_vs_level_ahead"]), ("Backtest", "D6", res["score_vs_change_ahead"]),
        ("Backtest", "J6", res["periods_tested"])])

json.dump({"build": BUILD, "products": PRODUCTS, "steps": STEPS}, open(HERE / "steps.json", "w"), indent=1)

# W14 a lower-is-worse measure (a credit score), in its own workbook: cards mirrored, 800 - 40 x rate
(HERE / "out").mkdir(exist_ok=True)
SCORE = HERE / "out" / "score.csv"
SCORE.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, 800 - 40 * p.value) for p in PTS["Credit card"]),
                 encoding="utf-8")
BUILD_LOW = ('python -m threshold_engine workbook "{out}" --series "Score=docs/walkthrough/out/score.csv" --name "Score"'
             ' --unit "points" --direction lower_is_worse --frequency quarterly --smoothing 1 --floor-at-zero no'
             ' --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95'
             ' --horizon 4 --min-history 41')
mir = [800 - 40 * p.value for p in PTS["Credit card"]]
LOW = []
for sid, rule in (("W14a", "worse"), ("W14b", "better")):
    ref = scale(mir, "lower_is_worse", 0.5, 1.0, 2.5, False)
    assert ref["bounds"] == sorted(ref["bounds"], reverse=True)
    sc = score(mir[-1], ref["bounds"], "lower_is_worse", rule, False)
    cnt = [sum(1 for x in mir if score(x, ref["bounds"], "lower_is_worse", rule, False) == k) for k in range(1, 6)]
    reads = [("Thresholds", "B5", ref["median"]), ("Thresholds", "C5", ref["typical_yearly_move"]),
             ("Thresholds", "D5", min(mir))] + [("Thresholds", c + "5", b) for c, b in zip("EFGH", ref["bounds"])]         + [("Thresholds", "J5", mir[-1]), ("Thresholds", "K5", sc), ("Thresholds", "L5", RATINGS[sc - 1]),
           ("Thresholds", "M5", "")] + [("Assess", "Q%d" % (10 + i), n) for i, n in enumerate(cnt)]
    # The chart's floor: not floored at zero, so 8% of the range below the lowest value or line (added after
    # the first run, which showed the score squeezed into the top of a chart that started at zero).
    mn, mx = min(mir + ref["bounds"]), max(mir + ref["bounds"])
    reads += [("Assess", "AI3", mn - 0.08 * (mx - mn)), ("Assess", "AI2", mx + 0.08 * (mx - (mn - 0.08 * (mx - mn))))]
    LOW.append({"id": sid, "title": "A lower-is-worse score, on the line takes the %s score" % rule,
                "how": "Build the score workbook (cards mirrored as 800 - 40 x rate), open it, K6 '%s'. Its lines "
                       "fall: worst is lowest." % rule, "product": "Score", "note": "",
                "actions": [{"sheet": "Assess", "cell": "R%d" % LAY["set_top"], "value": rule}],
                "reads": [{"sheet": a, "cell": b, "expected": c} for a, b, c in reads],
                "picture": [{"sheet": "Thresholds", "range": "A1:M8", "file": "w14-thresholds.png"},
                            {"sheet": "Assess", "chart": 1, "file": "w14-assess.png"}] if rule == "worse" else []})
json.dump({"build": BUILD_LOW, "steps": LOW}, open(HERE / "steps-low.json", "w"), indent=1)
STEPS += LOW


def fmt(v):
    if isinstance(v, float):
        return "%.4f" % v
    return "`%s`" % v if v != "" else "(blank)"


lines = ["# Expected answers (written before the walkthrough was run)", "",
         "Generated by `expected.py` from the source files and `scale.py`. Each row is a cell to read in Excel "
         "after doing the step; `=` rows are read with a formula typed into any empty cell.", ""]
for s in STEPS:
    lines += ["## %s. %s" % (s["id"], s["title"]), "", s["how"], ""]
    if s["actions"]:
        lines += ["Type: " + "; ".join("%s!%s = %s" % (a["sheet"], a["cell"], a["value"]) for a in s["actions"]), ""]
    lines += ["| Read | Expected |", "|---|---|"]
    lines += ["| %s%s | %s |" % ("" if r["sheet"] == "=" else r["sheet"] + "!", r["cell"], fmt(r["expected"]))
              for r in s["reads"]]
    lines.append("")
(HERE / "EXPECTED.md").write_text("\n".join(lines), encoding="utf-8")
print("%d steps, %d reads" % (len(STEPS), sum(len(s["reads"]) for s in STEPS)))
