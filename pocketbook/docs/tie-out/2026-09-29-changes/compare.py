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
ECHO = {("Control", c) for c in ("C18", "F18", "C19", "F19", "C24", "C25", "F25", "C26", "F26", "C28", "F28",
                                  "C42", "C43")}
ECHO |= {("Record", c) for c in ("F10", "F12", "F13", "F19", "F20", "G10", "G13", "G19", "G20", "F26", "F31",
                                 "F32", "F37", "F46", "G12", "G14", "G16", "G17", "F14", "F16", "F17", "F44")}
ECHO |= {("Look", c) for c in ("C20", "C21", "C22", "C39", "C40", "C41", "C58", "C59", "C60", "C69", "C88")}
ECHO |= {("Start here", c) for c in ("B10", "D10", "F10")}
COULD_NOT = {
    ("Record", "C25"): "702 counts the checks PocketBook ran on itself (every grid adding up to the book); nothing "
                       "outside PocketBook says how many there should be. What they claim, that every grid adds up, "
                       "is tested here directly: every loans and dollars cell of every grid ties.",
}
WORDS = {("Record", c) for c in ("F29", "F70", "F72", "F74", "F76", "F78", "F80", "F81", "F83", "F85", "C10", "C13")}

# the second run kind, Test new variables: its own answers echoed, and its own words
ECHO_SCOUT = {("Control", c) for c in ("C15", "C18", "F18", "C19", "F19", "C26", "F26", "C30", "C42", "C43",
                                       "E15", "F15")}
ECHO_SCOUT |= {("Record", c) for c in ("F10", "F11", "G11", "F14", "G14", "F15", "G15", "C38", "F56", "F57",
                                       "F60", "F64", "F65", "F67", "C51")}
ECHO_SCOUT |= {("Start here", c) for c in ("B10", "D10", "F10")}
ECHO_SCOUT |= {("Scouting", c) for c in ("C1", "C4", "C7", "C12", "C14", "B54")}
ECHO_SCOUT |= {("New variables", c) for c in ("C5", "C9", "C10", "C12", "C16", "C19")}
WORDS_SCOUT = {("Record", c) for c in ("C21", "C27", "C28", "C52", "F86", "F89", "F78")}
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
            wb_p[normalise(f["key"][:-1])] = f["value"]
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
        if rc is not None:
            verdict, note = rc
        elif (tab, cell) in could_not:
            verdict, note = "COULD NOT", could_not[(tab, cell)]
        elif (tab, cell) in words_set:
            verdict, note = "NOT A FIGURE", ("an instruction from the walk's first, refused Run: cell names and words"
                                             if run != "scout" else "a file's fingerprint, a date it was written, a name")
        elif (tab, cell) in echo_set or f["kind"] == "figure" and f["key"][:2] == ["line", "sure"]:
            verdict, note = "ECHO", "the analyst's answer or a fixed setting, shown back"
        elif f["kind"] == "words" and json.dumps(["cell", tab, cell]) in E:
            verdict, src, diff, note = judge({**f, "key": ["cell", tab, cell]}, v, E[json.dumps(["cell", tab, cell])],
                                             meta, wb_p)
        elif f["kind"] == "words" and tab == "Look" and cell.startswith("C") and isinstance(v, (int, float)):
            verdict, note = "ECHO", "the chart's bars, From and To: the analyst's view, shown back"
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
            if e is None:
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
