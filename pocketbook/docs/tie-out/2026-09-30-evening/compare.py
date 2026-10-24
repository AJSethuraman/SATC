"""Step 3: put each figure read out of the workbook beside the same figure worked out from the extract, and give it
exactly one verdict. Writes the roster (CSV: tab, cell, figure, ours, source, diff, verdict, note).

    python3 compare.py figures.json expected.json roster.csv RUN-LABEL [expected-flip.json]

expected-flip.json (by_hand_book.py given the workbook's own p-values) is used for one thing only: a figure that
DIFFERS against expected.json, and ties once the verdicts of the pockets whose shuffled p-values sit either side of 5%
within sampling error are taken the workbook's way, is TIED-WITHIN-SAMPLING, and says so.

"ours" is the workbook's figure, as read out of the calculated cell; "source" is the independent road's.

Verdicts, one per cell:
  TIED                   executed end to end; the two agree (to 1e-9 relative for arithmetic; to the last digit
                         the cell shows for a figure written into words, like "about 1,026"; to 1e-6 for a p-value
                         or a power search, which two libraries compute by different series)
  TIED-WITHIN-SAMPLING   a p-value from shuffling: both roads shuffled 10,000 times with their own random numbers,
                         so the two can only agree within sampling error. Tolerance: four standard errors of the
                         difference of two estimates, sqrt(2 p (1 - p) / 10,000), times the allowance's own
                         multiplier for that p (Benjamini-Hochberg scales a p by up to its family's size), and
                         never less than four shuffles' worth, 4 / 10,000, times that multiplier
  DIFFERS                executed end to end, and they disagree: the difference is in the diff column
  COULD NOT              no independent figure could be made; the note names the obstacle
  NAME                   a band's or segment's name that holds a digit ("496 - 653"): checked against the names
                         the independent road made from the file
  ECHO                   the analyst's own answer, or a fixed setting, shown back (95% sure, 10 losses, 20 bars)
  NOT A FIGURE           words that happen to hold a digit: a date in a heading, a cell name in an instruction
"""
import csv
import json
import math
import re
import sys

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
B = 10_000
PROFIT = {"Kept after losses", "Earned before losses"}


def numbers(text):
    out = []
    for m in NUM.finditer(str(text)):
        t = m.group()
        d = len(t.split(".")[1]) if "." in t else 0
        out.append((float(t.replace(",", "")), d))
    return out


def fmt(v):
    if isinstance(v, float):
        return f"{v:.12g}"
    return str(v)


def close(a, b, rel=1e-9, ab=1e-300):
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), ab)


def sampling_tol(e):
    raw = e.get("raw")
    fam = e.get("family") or 1
    val = e["value"]
    mult = (val / raw) if raw else fam
    mult = max(1.0, mult)
    p = raw if raw is not None else val
    return max(4 * math.sqrt(2 * p * (1 - p) / B), 4 / B) * mult


def border_p(v):
    """A p-value as a cell shows it: the number, or the number inside "borderline (p 0.048)" (30 Sep 2026)."""
    if isinstance(v, str):
        m = re.search(r"borderline \(p ([0-9.]+)\)", v)
        return float(m.group(1)) if m else None
    return v


def normalise(key):
    """The workbook prints a numbered category with its column's name ("ASSET_CLASS 4"); the independent road keys
    it by the value in the file ("4")."""
    k = list(key)
    out = []
    for x in k:
        if isinstance(x, str) and re.fullmatch(r"ASSET_CLASS \S+", x):
            x = x.split(" ", 1)[1]
        out.append(x)
    if out[0] == "grid" and out[3] == "loans":
        out[2] = "*"                      # the loans in a cell are the same whichever measure is picked
    if out[0] == "record" and len(out) == 3:      # the new-variable run's Record, named by its cell as on 28 Sep
        out = out[:2]
    return json.dumps(out)


# the tabs read once: cells that are the analyst's own answers or fixed settings, and words
ECHO = {("Control", c) for c in ("C18", "F18", "C19", "F19", "C24", "C25", "F25", "C26", "F26", "C28", "F28", "C44",
                                  "C42", "C43")}
ECHO |= {("Record", c) for c in ("F10", "F12", "F13", "F19", "F20", "G10", "G13", "G19", "G20", "F26", "F31",
                                 "F32", "F37", "F46", "G12", "G14", "G16", "G17", "F14", "F16", "F17", "F44")}
# Look: its rows moved on 30 Sep 2026 (BLOCK 20), so its settings are named by label ("look-setting"), not by cell
ECHO |= {("Start here", c) for c in ("B10", "D10", "F10")}
COULD_NOT = {
    ("Record", "C25"): "The count of checks PocketBook ran on itself (every grid adding up to the book); nothing "
                       "outside PocketBook says how many there should be. What they claim, that every grid adds up, "
                       "is tested here directly: every loans and dollars cell of every grid ties.",
}
WORDS = {("Record", c) for c in ("F29", "F70", "F72", "F74", "F76", "F78", "F80", "F81", "F83", "F85", "C10", "C13")}

# the second run kind, Test new variables: its own answers echoed, and its own words
ECHO_SCOUT = {("Control", c) for c in ("C15", "C18", "F18", "C19", "F19", "C26", "F26", "C30", "C42", "C43", "C44",
                                       "E15", "F15")}
ECHO_SCOUT |= {("Record", c) for c in ("F10", "F11", "G11", "F14", "G14", "F15", "G15", "C38", "F56", "F57",
                                       "F60", "F64", "F65", "F67", "C51")}
ECHO_SCOUT |= {("Start here", c) for c in ("B10", "D10", "F10")}
ECHO_SCOUT |= {("Scouting", c) for c in ("C1", "C4", "C7", "C12", "C14", "B54")}
ECHO_SCOUT |= {("New variables", c) for c in ("C5", "C9", "C10", "C12", "C16", "C19")}
WORDS_SCOUT = {("Record", c) for c in ("C21", "C25", "C27", "C28", "C52", "F86", "F89", "F78")}   # C25: the pre-spec's path
WORDS_SCOUT |= {("Scouting", c) for c in ("C16", "B21", "B39", "B43", "B44")}
COULD_NOT_SCOUT = {
    ("Scouting", "C10"): "the noise floor is the largest of 24 importances with the outcomes shuffled at random: one "
                         "more draw of the same thing, on this road's own random numbers, gave 0.0090 against the "
                         "workbook's 0.0085, but the largest of 24 random draws has no small sampling error to call a "
                         "tie against",
    ("Scouting", "G19"): "the noise floor again (see Scouting!C10): this road's one draw gave 0.0090",
    ("Scouting", "F25"): "income_to_sales's suggested bins: this road's reading of the rule the tab states in words "
                         "(Scouting!C12) gave 0.1, 2 and 2.1 where the pre-spec has 0.1 and 2 (UTIL's 0.9 did land); "
                         "the words don't say how two cuts that close are merged, so the rule could not be followed "
                         "to the end from the tab alone",
    ("Control", "I15"): "the suggested worse-at line for a new variable: the workbook says it is the smallest odds ratio "
                        "a group of typical size can call significant, on the loans the groups were found on, but not "
                        "which groups are typical or at what power; one attempt (the median, over the non-reference "
                        "groups, of the odds ratio a Wald test just calls significant) gives 1.40 against the workbook's 1.43",
}


# ---------------------------------------------------------------- Borderline (30 Sep 2026; docs/statistics.md B2a)
BAR, BORDER_SE = 0.05, 2.0
WB_POCKETS = {}                 # _pockets as the workbook calculated it: [Grid, Band, Segment, Rate key] -> row
BTXT = ("Borderline: the p-value that decides, when the flag turns on it and it is within 2 standard errors of the "
        "bar")
FLAGGED = re.compile(r"^(.*?)(?: · )?borderline \(p ([0-9.]+(?: and [0-9.]+)?)\)$")


def load_wb_pockets(path):
    import os
    if os.path.exists(path):
        for r in json.load(open(path)):
            WB_POCKETS[json.dumps([r["Grid"], str(r["Band"]), str(r["Segment"]), r["Rate (key)"]])] = r


def unflag(v):
    """(the verdict's own words, the borderline p-values printed after them or ""): "Yes · borderline (p 0.048)"
    is ("Yes", "0.048"); a p-value cell's "borderline (p 0.048)" is ("", "0.048")."""
    t = "" if v is None else str(v)
    m = FLAGGED.match(t)
    return (m.group(1), m.group(2)) if m else (t, "")


def p_text(p):
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(repr(float(p)))
    three = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if three == Decimal("0.050"):
        return str(d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    return str(three)


def wb_row(b):
    return WB_POCKETS.get(json.dumps(b.get("row"))) if b and b.get("row") else None


def wb_p(b):
    r = wb_row(b)
    v = r.get("p-value that decides") if r else None
    return v if isinstance(v, (int, float)) else None


SE_BOOK = "Shuffle's standard error of the p-value vs book, after the allowance"
SE_BAND = "Shuffle's standard error of the p-value vs band, after the allowance"


def rule_on(p, se, flag, gap, profit):
    """docs/statistics.md B2a on one p-value and its SE: (the flag's printed p or "", the same for Worse?)."""
    near = isinstance(p, (int, float)) and isinstance(se, (int, float)) and abs(p - BAR) <= BORDER_SE * se
    dec = flag in ("worse", "better", "worse, not significant", "better, not significant") or \
        (profit and flag == "in line" and isinstance(gap, (int, float)) and gap != 0)
    turns = flag in ("worse", "worse, not significant") or \
        (profit and flag == "in line" and isinstance(gap, (int, float)) and gap < 0)
    return {"any": p_text(p) if near and dec else "", "worse": p_text(p) if near and dec and turns else ""}


def row_rule(r):
    band = r.get("Judged against its band?") in (True, "TRUE", 1, "True")
    return rule_on(r.get("p-value that decides"), r.get(SE_BAND) if band else r.get(SE_BOOK), r.get("Flag"),
                   r.get("Gap that decides"), r.get("Rate (key)") in ("ranr_rate", "contribution_rate"))


def one_side(pt_w, b, printed_p=None, which=None):
    """One comparison's borderline flag: the workbook's printed p (or "") against this road's (b["bl"]). First, where
    the pocket's _pockets row is known (`which`: "any" or "worse"), what is printed must be what the rule gives the
    workbook's OWN p-value and standard error -- exactly; then it is set against this road's, within sampling.
    Returns (verdict, note)."""
    pt_r = b.get("bl", "") if "bl" in b else ""
    own = wb_p(b) if printed_p is None else printed_p
    if pt_w and own is not None and b.get("row") and p_text(own) != pt_w:
        return "DIFFERS", f"the printed p {pt_w} is not the workbook's own p-value {own:.6g} to the digits shown"
    row = wb_row(b) if which else None
    if row is not None and row_rule(row)[which] != pt_w:
        return "DIFFERS", (f"printed {pt_w or 'no flag'}; the rule on the workbook's own p and SE gives "
                           f"{row_rule(row)[which] or 'no flag'}")
    if pt_w == pt_r:
        return "TIED", ""
    if own is None and pt_w:
        own = float(pt_w)
    if own is None or b.get("p") is None or b.get("tol") is None:
        return "DIFFERS", (f"flagged there ({pt_w or 'no'}) and here ({pt_r or 'no'}); no p-value to judge the "
                           f"sampling by")
    d = abs(own - b["p"])
    how = (f"the workbook's p {own:.4g} (flag: {pt_w or 'none'}) against this road's {b['p']:.4g} "
           f"(SE {b['se']:.2g}, flag: {pt_r or 'none'})" if b.get("se") else
           f"the workbook's p {own:.4g} (flag: {pt_w or 'none'}) against this road's {b['p']:.4g} (flag: {pt_r or 'none'})")
    if d <= b["tol"]:
        return "TIED-WITHIN-SAMPLING", how + f": within sampling (tolerance {b['tol']:.2g}, the setter's)"
    return "DIFFERS", how + f": apart by {d:.3g}, more than sampling ({b['tol']:.2g})"


def border_judge(f, v, e):
    """A verdict with its borderline words, a p-value cell that may print them, or a count of borderline pockets."""
    k0, x = f["key"][0], e["value"]
    if "members" in e:                                      # a count: Start here's tile, Record's Borderline now
        got = [int(n) for n, _ in numbers(v)]
        want = [int(round(n)) for n in x]
        if f["key"][0] == "start-tile":
            got, want = (got + [0])[:3], (want + [0])[:3]
        if got == want:
            return "TIED", "; ".join(map(str, x)), "", e.get("how", "")
        # the counts differ: every pocket whose flag differs must be within sampling, and the workbook's count must be
        # what its own flags give over the same pockets
        col = "Borderline, for Worse?" if k0 == "start-tile" else None
        n_any = n_w = 0
        notes, bad = [], []
        for b in e["members"]:
            r = wb_row(b)
            wany, ww = (r.get(BTXT) or "", r.get("Borderline, for Worse?") or "") if r else ("", "")
            n_any += bool(wany)
            n_w += bool(ww)
            for mine, theirs, lab in ((b["bl"], wany, "flag"), (b["wbl"], ww, "Worse? flag")):
                if bool(mine) != bool(theirs):
                    vv, nn = one_side(theirs, {**b, "bl": mine}, which="any" if lab == "flag" else "worse")
                    (bad if vv == "DIFFERS" else notes).append(f"{'/'.join(map(str, b['row'][:3]))}: {nn}")
        if k0 == "start-tile":
            ok_own = got[2] == n_w and got[:2] == want[:2]
        else:
            ok_own = got[0] == n_any and got[2] == n_w and got[1] == want[1]
        if ok_own and not bad:
            return "TIED-WITHIN-SAMPLING", "; ".join(map(str, x)), "", ("the count differs only through pockets "
                                                                       "whose borderline flag differs within sampling: "
                                                                       + " | ".join(notes[:4]))
        return "DIFFERS", "; ".join(map(str, x)), f"{got} vs {want}", ("; ".join(bad[:3]) or
                                                                      "the workbook's count is not its own flags'")
    if "sides" in e:                                        # Together: either side's borderline p
        bw, pw = unflag(v)
        br, pr = unflag(x)
        if bw != br:
            return "DIFFERS", str(x), "text differs", e.get("how", "")
        if pw == pr:
            return "TIED", str(x), "", e.get("how", "")
        verdicts, notes = [], []
        for b in e["sides"]:
            r = wb_row(b)
            vv, nn = one_side(r.get(BTXT) or "" if r else "", b, which="any")
            verdicts.append(vv)
            notes.append(nn)
        wb_sides = [((wb_row(b) or {}).get(BTXT) or "") for b in e["sides"]]
        if " and ".join(p_ for p_ in wb_sides if p_) != pw:
            return "DIFFERS", str(x), "text differs", "Together's printed p-values are not its two sides' flags"
        if all(vv in ("TIED", "TIED-WITHIN-SAMPLING") for vv in verdicts):
            return "TIED-WITHIN-SAMPLING", str(x), "", " | ".join(n for n in notes if n)
        return "DIFFERS", str(x), "text differs", " | ".join(n for n in notes if n)
    b = e["border"]
    if b.get("split"):                                      # a split p-value: a number, or "borderline (p 0.048)"
        pw = unflag(v)[1] if isinstance(v, str) else ""
        own = float(pw) if pw else v if isinstance(v, (int, float)) else None
        vv, nn = one_side(pw, b, printed_p=own)
        return vv, fmt(x), "", nn or "the flag and the printed p, both"
    if k0 == "pk-border":                                   # the printed p alone, or blank
        pw = str(v or "")
    else:
        bw, pw = unflag(v)
        br, _ = unflag(x)
        if bw != br:
            return "DIFFERS", str(x), "text differs", e.get("how", "")
    worse = f["key"][-1] == "worse" or k0 in ("pocket", "start-top")
    vv, nn = one_side(pw, {**b, "bl": b["wbl"] if worse else b["bl"]}, which="worse" if worse else "any")
    return vv, str(x), "" if vv != "DIFFERS" else "text differs", nn or e.get("how", "")


def rule_judge(f, v):
    """The B2a rule applied to the workbook's OWN p-value and standard error: is what it printed what the rule says
    (a check of the rule's application; the p and SE themselves are tied against this road separately)."""
    i = f["inputs"]
    got = rule_on(i["p"], i["se"], i["flag"], i["gap"], i["profit"])
    want = [got["any"], got["worse"]]
    ok = list(v) == want
    return ("TIED" if ok else "DIFFERS"), "; ".join(want), "" if ok else f"{v} vs {want}", \
        "the rule (2 SEs of 5%, the word turns on it) applied to the workbook's own p and SE"


def se_judge(f, v, e):
    """A pocket's standard error after the allowance (_pockets' SE columns) against this road's: the same when both
    roads' setter is the same pocket at the same rank; else the two p-values must be within sampling."""
    b, x = e["border"], e["value"]
    if close(v, x, rel=1e-9):
        return "TIED", fmt(x), "0", "the setter's SE times m / j"
    own = wb_p(b)
    m = b.get("m") or 1
    # the SE B2a gives the workbook's OWN adjusted p, set by a raw p at some rank j of the m: sqrt(r (1 - r) / B)
    # x m / j with r = p j / m -- exact at the j that set it (the same j as here, or another where the roads' raw
    # p-values order differently)
    js = [j for j in range(1, m + 1) if own is not None and own < 1 and
          close(v, math.sqrt(max(own * j / m * (1 - own * j / m), 0) / B) * m / j, rel=1e-9)]
    mine = b["p"] / b["r"] if b.get("r") else None
    if js and own is not None and abs(own - b["p"]) <= b["tol"]:
        same = mine is not None and any(abs(m / j - mine) < 1e-9 for j in js)
        return ("TIED" if same else "TIED-WITHIN-SAMPLING"), fmt(x), f"{v - x:+.3g}", (
            f"exactly B2a's SE for the workbook's own p {own:.6g} set at rank {js[0]} of {m} (m / j "
            f"{m / js[0]:.4g}; here {mine:.4g})" + ("" if same else ": another pocket sets it on this road, within "
                                                               "sampling"))
    return "DIFFERS", fmt(x), f"{v - x:+.3g}", ("not B2a's SE for the workbook's own p at any rank" if not js else
                                                "the p-values are further apart than sampling")


def record_class(f):
    """Where-the-book-bleeds Record figures are named by the label they sit under (read_book.py): which of them are
    the analyst's settings shown back, words, or a count nothing outside PocketBook can check (28 Sep's lists, by
    label rather than by cell, since the rows move)."""
    k = f["key"]
    if f["kind"] == "words" and f["tab"] == "Record" and re.match(r"^[FG]\d+$", f["cell"]) and \
            int(f["cell"][1:]) <= 22:
        return "ECHO", "the analyst's answer or a fixed setting, shown back"
    if f["kind"] != "figure" or k[0] != "record" or len(k) != 4:
        return None
    _, col, lab, off = k
    row = int(re.sub(r"\D", "", f["cell"]))
    if (lab, off) == ("Tie-out checks", 0):
        return "COULD NOT", COULD_NOT[("Record", "C25")]
    if lab == "Borderline":
        return "ECHO", ("the rule in words (docs/statistics.md B2a): 2 of the shuffle's standard errors, the 5% bar "
                        "(the Run's 95% sure), sqrt(p (1 - p) / shuffles), and \"borderline (p 0.048)\" as an example")
    if lab in ("Extract", "Record of this run") or lab == "(the run's time)" and off >= 1:
        return "NOT A FIGURE", "a file's name, or an instruction from the walk's first, refused Run"
    if col == "F" and row <= 22 or lab in ("p-value", "Standard error", "Profit counts as more or less") or \
            lab == "Tests" and off >= 1:
        return "ECHO", "the analyst's answer or a fixed setting, shown back"
    return None


def judge(f, v, e, meta, wb_p):
    """One figure against one expected value: (verdict, source as shown, diff, note)."""
    verdict, src, diff, note = None, "", "", ""
    x = e["value"]
    k0 = f["key"][0]
    if k0 == "pk-border" and f["key"][-1] == "se":
        return se_judge(f, v, e)
    if "members" in e or "sides" in e or "border" in e and (k0 not in ("split-pocket", "split-sum")
                                                              or isinstance(v, str) or isinstance(x, str)):
        return border_judge(f, v, e)
    if k0 in ("panel", "split-differ", "pck-listed") or k0 == "pck-dot" and f["key"][-1] in ("colour",):
        # sentences and words, compared whole: a blank cell reads as an empty sentence
        got = "" if v is None else str(v)
        ok = got == ("" if x is None else str(x))
        return ("TIED" if ok else "DIFFERS"), fmt(x) if x is not None else "", "" if ok else "text differs", \
            e.get("how", "")
    if k0 == "look-dots":
        # every dot a real loan's pair of values (none answered missing), as many as the tab says it shows
        import collections
        have = collections.Counter(tuple(p) for p in x["pairs"])
        drawn = collections.Counter(tuple(float(a) for a in p) for p in v)
        extra = drawn - have
        ok = not extra and sum(drawn.values()) == x["shown"]
        return ("TIED" if ok else "DIFFERS"), f"{x['shown']} dots, each a loan's pair", \
            "" if ok else f"{sum(drawn.values())} dots, {sum(extra.values())} not a loan's pair", e.get("how", "")
    if k0 == "low-values":
        codes = x["codes"]
        bad = [c for c in v if not (c[0] == "Columns" and str(c[1]).startswith("C"))
               and (isinstance(c[2], (int, float)) and (c[2] <= -99_000_000 or c[2] in codes)
                    or isinstance(c[2], str) and any(f"{int(k):d}" in c[2].replace(",", "") for k in codes))]
        ok = not bad
        return ("TIED" if ok else "DIFFERS"), "a code only in Columns' raw sample", \
            "" if ok else f"{len(bad)} cells: {bad[:3]}", (f"{len(v)} cells at or below -1,000,000: the sample on "
                                                        f"Columns, and the rest dollar figures, none a code")
    if k0 == "pck-dot":
        ok = (v == x) if isinstance(x, list) or x is None or v is None else close(v, x, rel=1e-9)
        return ("TIED" if ok else "DIFFERS"), fmt(x) if not isinstance(x, list) else str(x), \
            "" if ok else f"{v!r} vs {x!r}", e.get("how", "")
    src = fmt(x) if not isinstance(x, list) else "; ".join(fmt(y) for y in x)
    if isinstance(x, list) and (isinstance(v, str) or f["key"][0] in ("ladder",)):
        got = numbers(v)
        if f["key"][0] == "split-chip":
            got = [g for g in got]
        if f["key"][0] in ("ladder",) and f["key"][2] == "M":
            got = got[:1]
        if f["key"][0] == "record" and f["key"][1] in ("C44",) and meta.get("run") != "scout":
            got = got[:2]
        want = [y for y in x]
        if f["key"][0] == "split-chip":
            want = [round(c, 2) for c in (meta.get("corr_fico", 0), meta.get("corr_bal", 0))]
        if f["key"][0] == "split-chip":
            got, want = sorted(got), sorted(want)
        if len(got) != len(want):
            verdict, note = "DIFFERS", f"{len(got)} numbers in the cell, {len(want)} expected"
        else:
            bad = [(g, w) for (g, d), w in zip(got, want)
                   if w is not None and abs(g - w) > 0.5 * 10 ** -d + 1e-9 * abs(w)]
            verdict = "DIFFERS" if bad else "TIED"
            note = "compared at the digits the cell shows"
            if bad:
                diff = "; ".join(f"{g:g} vs {w:.6g}" for g, w in bad)
    elif isinstance(x, str) or isinstance(v, str) and not isinstance(x, (int, float)):
        if f["key"][0] == "split-steady":
            said = re.search(r"Bad loans: ([^;.]*)", str(v))
            said = said.group(1) if said else str(v)
            got = "no sign" if "no sign" in said else "not tested" if "not tested" in said else "differs"
            ok = got == x if x in ("no sign", "not tested", "differs") else ("no sign" in str(v)) == (x == "no sign")
        else:
            ok = str(v) == str(x)
        verdict = "TIED" if ok else "DIFFERS"
        if ok and e.get("sampled_word"):
            verdict = "TIED-WITHIN-SAMPLING"
        note = e.get("how", "")
    elif isinstance(v, str):
        # a number written into words by the tab: "(1.37×)" or "(-3.64 pts)" -- a gap in brackets is
        # one its test does not call significant (Split!C7)
        got = numbers(v)
        g, d = got[0]
        ok = abs(g - x) <= 0.5 * 10 ** -d + 1e-9
        bracket = v.strip().startswith("(")
        mine_sig = e.get("p") is not None and e["p"] < 0.05
        verdict = "TIED" if ok and bracket != mine_sig else "DIFFERS"
        note = "compared at the digits the cell shows; brackets mean not significant"
        if ok and bracket == mine_sig and e.get("shuffled"):
            theirs = wb_p.get(normalise(f["key"][:-1]))
            if theirs is not None and abs(theirs - e["p"]) <= sampling_tol(
                    {"value": e["p"], "raw": e.get("raw"), "family": e.get("family")}):
                verdict = "TIED-WITHIN-SAMPLING"
                note = (f"the number ties; significant here but not there (or the other way), and the two "
                        f"shuffled p-values ({theirs:.4g}, {e['p']:.4g}) agree within sampling error")
        if not ok:
            diff = f"{g - x:+.6g}"
    elif isinstance(v, (int, float)) and isinstance(x, (int, float)):
        d = v - x
        diff = f"{d:+.3g}" if d else "0"
        if e.get("rank_range"):
            lo_, hi_ = e["rank_range"]
            verdict = "TIED" if d == 0 else "TIED-WITHIN-SAMPLING" if lo_ <= v <= hi_ else "DIFFERS"
            note = e.get("how", "")
        elif e.get("sampled"):
            verdict = "TIED-WITHIN-SAMPLING" if abs(d) <= e["tol"] else "DIFFERS"
            note = f"tolerance {e['tol']:.2g}: " + e.get("how", "")
        elif f["key"][0] == "split-pocket" and f["key"][-1] == "gap":
            # a gap shown as a plain number is one its test calls significant (Split!C8: "a gap that is not
            # significant is in brackets"): the number exactly, and significant on this road too -- or, for a
            # shuffled p, the two p-values within sampling of each other (29 Sep 2026: the 28 Sep comparison
            # judged such a gap by the shuffle's tolerance, which let any number through)
            ok = close(v, x, rel=1e-9) or abs(v - x) <= 5e-9 + 1e-9 * abs(x)
            mine_sig = e.get("p") is not None and e["p"] < 0.05
            theirs = wb_p.get(normalise(f["key"][:-1]))
            if ok and mine_sig:
                verdict, note = "TIED", "the number exactly; significant on both roads"
            elif ok and e.get("shuffled") and theirs is not None and e.get("p") is not None and \
                    abs(theirs - e["p"]) <= sampling_tol({"value": e["p"], "raw": e.get("raw"),
                                                          "family": e.get("family")}):
                verdict, note = "TIED-WITHIN-SAMPLING", (f"the number ties; significant there, not here, and the "
                                                         f"two shuffled p-values ({theirs:.4g}, {e['p']:.4g}) agree "
                                                         f"within sampling error")
            else:
                verdict, note = "DIFFERS", "shown as significant" + ("" if ok else "; the number differs")
        elif e.get("shuffled"):
            tol = sampling_tol(e)
            verdict = "TIED-WITHIN-SAMPLING" if abs(d) <= tol else "DIFFERS"
            side = (v < 0.05) == (x < 0.05)
            note = f"tolerance {tol:.2g}" + ("" if side else "; the two sit either side of 5%")
        else:
            k0, fld = f["key"][0], f["key"][-1]
            rel = 1e-6 if (fld in ("p", "caught") or "p-value" in str(fld) or "p, allowed" in str(fld)) else 1e-9
            if k0 == "nv-test" and fld == "Statistic":
                ok = abs(v - x) <= 5e-7 + 1e-9 * abs(x)
                note = "shown to six decimals"
            elif k0 == "look" and "correlation" in str(f["key"][2]):
                ok = abs(v - x) <= 0.005 + 1e-12
                note = "shown to two places"
            elif (k0 == "grid" and f["key"][3] in ("book", "band") and f["key"][2] in PROFIT
                  or k0 == "pocket" and fld == "gap" and f["key"][2] in PROFIT
                  or k0 == "grid-bound" and f["key"][2] in PROFIT
                  or k0 == "pck" and fld.endswith("-gap")):
                # a gap in points: PocketBook stores it to nine decimal places of a point
                ok = abs(v - x) <= 5e-9 + 1e-9 * abs(x)
                note = "a gap in points, stored to nine decimals"
            else:
                ok = close(v, x, rel=rel)
            verdict = "TIED" if ok else "DIFFERS"
    else:
        verdict, note = "DIFFERS", f"workbook shows {v!r}, the independent road {x!r}"
    return verdict, src, diff, note


def main():
    figs = json.load(open(sys.argv[1]))
    import os
    load_wb_pockets(os.path.join(os.path.dirname(sys.argv[1]), "wb-pockets.json"))
    exp = json.load(open(sys.argv[2]))
    E, meta = exp["expected"], exp["meta"]
    for extra in sys.argv[6:]:                   # more expected figures for the same run (the forest's)
        more = json.load(open(extra))
        E = {**E, **more["expected"]}
        meta = {**more.get("meta", {}), **meta}
    meta["run"] = sys.argv[4]
    run = sys.argv[4]
    EF = json.load(open(sys.argv[5]))["expected"] if len(sys.argv) > 5 and sys.argv[5] != "-" else None
    names = set()
    for col, labs in meta["labels"].items():
        for lab in labs:
            names |= {lab, f"{col} {lab}"}
    wb_p = {}                                   # the workbook's own p per split pocket (for the brackets)
    for f in figs:
        if f["kind"] == "figure" and f["key"][0] == "split-pocket" and f["key"][-1] == "p":
            wb_p[normalise(f["key"][:-1])] = border_p(f["value"])
    rows, seen = [], set()
    for f in figs:
        tab, cell, v, view = f["tab"], f["cell"], f["value"], f["view"]
        if f["kind"] == "figure":
            nk = normalise(f["key"])
            ident = (tab, nk)
        else:
            nk = None
            ident = (tab, cell, str(v))
        if ident in seen:
            continue
        seen.add(ident)
        where = f"{tab}!{cell}" + (f" [{view}]" if tab in ("Pockets", "Grids", "Split", "Paid, cost, kept") else "")
        what = " · ".join(str(x) for x in f["key"][1:] if x is not None) if f["kind"] == "figure" else ""
        verdict, ours, src, diff, note = None, fmt(v), "", "", ""
        if isinstance(v, list) and len(str(v)) > 200:
            ours = f"[{len(v)} items: {str(v)[:60]}...]"

        rc = record_class(f) if run != "scout" else None
        could_not = COULD_NOT if run != "scout" else {**COULD_NOT_SCOUT, **{k: v for k, v in COULD_NOT.items()
                                                                           if k[0] != "Record"}}
        words_set = WORDS if run != "scout" else WORDS_SCOUT
        echo_set = ECHO if run != "scout" else ECHO_SCOUT
        if run != "scout":                  # Record is read by label now (read_book.py): its sets are by label
            words_set = {x for x in words_set if x[0] != "Record"}
            echo_set = {x for x in echo_set if x[0] != "Record"}
            could_not = {k_: v_ for k_, v_ in could_not.items() if k_[0] != "Record"}
        if run == "scout" and f["kind"] == "figure" and f["key"][0] == "record":
            cell = f["key"][1]              # the cell it held on 29 Sep (read_scout.py: Record's rows moved)
        if run == "scout" and f["kind"] == "figure" and f["key"] == ["record-border", "Borderline"]:
            rc = ("ECHO", "the rule in words (docs/statistics.md B2a): 2 standard errors, the 5% bar")
        if rc is not None:
            verdict, note = rc
        elif (tab, cell) in could_not:
            verdict, note = "COULD NOT", could_not[(tab, cell)]
        elif (tab, cell) in words_set:
            verdict, note = "NOT A FIGURE", ("an instruction from the walk's first, refused Run: cell names and words"
                                             if run != "scout" else "a file's fingerprint, a date it was written, a name")
        elif (tab, cell) in echo_set or f["kind"] == "figure" and (f["key"][:2] == ["line", "sure"]
                                                                   or f["key"][0] == "look-setting"):
            verdict, note = "ECHO", "the analyst's answer or a fixed setting, shown back"
        elif f["kind"] == "words" and json.dumps(["cell", tab, cell]) in E:
            verdict, src, diff, note = judge({**f, "key": ["cell", tab, cell]}, v, E[json.dumps(["cell", tab, cell])],
                                             meta, wb_p)
        elif f["kind"] == "words" and tab == "Look" and cell.startswith("C") and isinstance(v, (int, float)):
            verdict, note = "COULD NOT", "a number on Look that no label names (30 Sep 2026: its rows moved)"
        elif f["kind"] == "words":
            sv = str(v).strip()
            base = re.sub(r" · (high|low)$", "", sv)
            base2 = re.sub(r"^\S+: ", "", sv).replace(" (reference)", "")
            parts = [p_.strip() for p_ in re.split(r" vs |; ", base2)]
            if sv in names or base in names or base2 in names or all(p_ in names for p_ in parts):
                verdict, note = "NAME", "a band's name, made the same way from the file"
            elif re.fullmatch(r"(ASSET_CLASS )?[1-4]( · (high|low))?", sv) or sv in meta.get("columns", ()):
                verdict, note = "NAME", "a segment's name: the value in the file"
            elif (tab, cell) == ("Start here", "C1"):
                got = numbers(v)
                ok = close(got[0][0], meta["n"]) and got[1][0] == meta.get("ncols", 10)
                verdict = "TIED" if ok else "DIFFERS"
                src, note = f"{meta['n']} loans, {meta.get('ncols', 10)} columns", "the Run's date and time are its own clock"
            else:
                verdict, note = "NOT A FIGURE", "words that hold a digit"
        else:
            e = E.get(nk)
            if f["key"][0] == "pk-rule":
                verdict, src, diff, note = rule_judge(f, v)
            elif e is None:
                verdict, note = "COULD NOT", "no figure on the independent road carries this key"
            else:
                verdict, src, diff, note = judge(f, v, e, meta, wb_p)
                ef = EF.get(nk) if EF else None
                if verdict == "DIFFERS" and ef is not None:
                    v2, s2, d2, n2 = judge(f, v, ef, meta, wb_p)
                    if v2 in ("TIED", "TIED-WITHIN-SAMPLING"):
                        verdict, diff = "TIED-WITHIN-SAMPLING", diff
                        note = ("differs only through a verdict that rests on a shuffled p-value sitting either "
                                "side of 5% within sampling error of the workbook's (listed under What it found); "
                                f"with that verdict taken the workbook's way it reads {s2}")
        rows.append({"run": run, "kind": f["key"][0], "tab": tab, "cell": where, "figure": what, "ours": ours, "source": src,
                     "diff": diff, "verdict": verdict, "note": note})
    with open(sys.argv[3], "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    tally = {}
    for r in rows:
        tally[(r["tab"], r["verdict"])] = tally.get((r["tab"], r["verdict"]), 0) + 1
    for k in sorted(tally):
        print(*k, tally[k], sep="\t")
    tot = {}
    for r in rows:
        tot[r["verdict"]] = tot.get(r["verdict"], 0) + 1
    print(tot, len(rows))


if __name__ == "__main__":
    main()
