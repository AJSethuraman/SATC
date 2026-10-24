"""Two runs side by side: what changes if the settings change (W12).

The walk of 16 Oct 2026 asked what changes if each reading is measured against
the last 30 years instead of its full history, and the answer took a script
written by hand. This is that script, made part of the tool:

    python -m threshold_engine.macro read --settings settings.json --compare what-if.json

Both files are full settings files, and each must be complete: a what-if with
a gap refuses, naming the file and the gap, exactly as the firm's own does.
Both runs read the same pull, so the only thing that can differ is the
settings. Nothing here changes either file, and nothing is chosen: the tool
reports, for every reading, how it reads under each and what it was measured
against. Which settings to keep is the firm's call. Leaving quarters out is
the obvious what-if: the same pull read with and without the pandemic.
"""
from .catalog import READ
from .readings import DIRECTIONS

ORDER = {item.key: i for i, item in enumerate(READ)}
ITEMS = {item.key: item for item in READ}
NOT_ASKED = "not asked for by these settings"

#: Each setting, as the workbook and the printout name it.
CALLED = {"history": "History each reading is measured against", "change_months": "Change counted over",
          "normal_width": "Normal movement", "left_out": "Quarters left out",
          "axis_cut": "Readings a chart may leave off its axis", "show_sahm": "Sahm reading shown",
          "compare_p": "Dashboard: p a link must pass", "compare_leads": "Dashboard: leads tried",
          "compare_starts": "Dashboard: starting points a year", "compare_min_pairs": "Dashboard: fewest pairs to test"}


def spans(left_out):
    """The quarters left out, in words: "2020Q2 to 2021Q2; 2008Q4"."""
    return "; ".join(a if a == b else "%s to %s" % (a, b) for a, b in left_out) or "none"


def plain(name, s):
    """One answer from a run's settings (``read_all``'s ``settings``), in words."""
    v = s[name]
    if name == "history":
        return "full history" if v == "full" else "the last %d years" % v["years"]
    if name == "change_months":
        return "%d months" % v
    if name == "normal_width":
        return "the median change plus or minus %s typical move%s" % ("%g" % v, "" if v == 1 else "s")
    if name == "left_out":
        return spans(v)
    if name == "axis_cut":
        return "none: every reading stays on" if v == 0 else "%g%% at each end" % v
    if name == "show_sahm":
        return "yes" if v else "no"
    if name == "compare_p":
        return "p < %g, two-tailed" % v
    if name == "compare_leads":
        steps = {b - a for a, b in zip(v, v[1:])}
        if len(v) > 2 and len(steps) == 1:
            return "%+d to %+d months, every %d" % (v[0], v[-1], steps.pop())
        return ", ".join("%+d" % x for x in v) + " months"
    if name == "compare_starts":
        return "%d, a reading every 12 months from each" % v
    if name == "compare_min_pairs":
        return "%d pairs at every starting point" % v
    raise KeyError(name)


def settings_rows(a, b):
    """Every setting, each run's answer in words, and whether they differ."""
    return [{"setting": CALLED[n], "name": n, "a": plain(n, a), "b": plain(n, b), "differs": a[n] != b[n]}
            for n in CALLED]


SIDE = ("direction", "movement", "normal_low", "normal_high", "median", "typical", "percentile", "readings",
        "history_from", "date", "value", "sentence")


def _side(r):
    return {k: r[k] for k in SIDE if k in r}


def compare(a, b, label_a, label_b):
    """Compare two ``read_all`` results made from the same pull.

    Returns the settings side by side, a row per reading, the 3 x 3 count of
    direction against direction for the changes, and the totals. A change
    row's ``move`` is the what-if's direction less the direction as set, in
    steps from Decreasing through Stable to Increasing: above zero reads more
    upward, below zero more downward. A level row has no move; its two
    percentiles say where it sits under each. A reading read in one run only
    says why it is missing from the other, in that run's own words, and one
    neither run could read is a row too, with each run's reason (Codex on
    #452)."""
    if a["vintage"] != b["vintage"]:
        raise ValueError("the two runs read different pulls (%s, %s); compare runs of one pull"
                         % (a["vintage"], b["vintage"]))
    # One pull is one set of bytes, not one folder name: a file changed between the two runs would show as a
    # move the settings did not make (Codex on #452).
    differ = sorted(n for n in set(a["read_sha"]) | set(b["read_sha"]) if a["read_sha"].get(n) != b["read_sha"].get(n))
    if differ:
        raise ValueError("the two runs read different bytes of the pull of %s (%s: changed, gone or new between "
                         "them); compare two runs of one reading of it" % (a["vintage"], ", ".join(differ)))
    ra = {(r["key"], r["reading"]): r for r in a["readings"]}
    rb = {(r["key"], r["reading"]): r for r in b["readings"]}
    why_a = {(x["key"], x["reading"]): x["why"] for x in a["not_read"]}
    why_b = {(x["key"], x["reading"]): x["why"] for x in b["not_read"]}
    same_change = a["settings"]["change_months"] == b["settings"]["change_months"]
    rows = []
    matrix = [[0] * 3 for _ in range(3)]
    totals = {"compared": 0, "same": 0, "up": 0, "down": 0, "only_a": 0, "only_b": 0, "neither": 0}
    keys = set(ra) | set(rb) | set(why_a) | set(why_b)
    for key, reading in sorted(keys, key=lambda kr: (ORDER.get(kr[0], 0), kr[1] != "position")):
        x, y = ra.get((key, reading)), rb.get((key, reading))
        first = x or y or {"title": ITEMS[key].title, "group": ITEMS[key].group}
        row = {"key": key, "title": first["title"], "group": first["group"], "reading": reading,
               "care": bool(ITEMS[key].care) if hasattr(ITEMS[key], "care") else False,
               "a": _side(x) if x else None, "b": _side(y) if y else None,
               "why_a": None if x else why_a.get((key, reading), NOT_ASKED),
               "why_b": None if y else why_b.get((key, reading), NOT_ASKED),
               # A change over a different number of months is a different measure, so its lines are not
               # comparable on one chart; its directions still are, each against its own history.
               "same_measure": reading == "position" or same_change, "move": None}
        if x and y:
            if reading == "change":
                i, j = DIRECTIONS.index(x["direction"]), DIRECTIONS.index(y["direction"])
                row["move"] = j - i
                matrix[i][j] += 1
                totals["compared"] += 1
                totals["same" if i == j else "up" if j > i else "down"] += 1
        elif x or y:
            row["why_missing"] = row["why_b"] if x else row["why_a"]
            totals["only_a" if x else "only_b"] += 1
        else:
            totals["neither"] += 1
        rows.append(row)
    return {"vintage": a["vintage"], "a": label_a, "b": label_b,
            # what the comparison was made from, so a workbook can check it is this run's (Codex on #452)
            "read_sha": a["read_sha"], "baseline": a["settings"],
            # each side's horizon: a change counted over different months is named with both wherever it is shown
            "months": [a["settings"]["change_months"], b["settings"]["change_months"]],
            "settings": settings_rows(a["settings"], b["settings"]), "rows": rows, "matrix": matrix,
            "totals": totals}


def when(d):
    """A history's first date, as the printout says it: 'Jan 1948'."""
    import calendar
    return "%s %s" % (calendar.month_abbr[int(d[5:7])], d[:4])


def reading_label(reading, months):
    """A reading's name with each side's horizon: one horizon when both count the change the same way, both
    when they differ, since then each side reads a different change (Codex on #452)."""
    if reading == "position":
        return "level"
    a, b = months
    return "change over %d months" % a if a == b else "change over %d months; what if: over %d months" % (a, b)


def row_label(r, months):
    """A comparison row's reading, naming the horizon of each side the row speaks for: the sides that read
    it, or, when neither did, the sides whose settings asked for it (Codex on #452, twice)."""
    if r["reading"] == "position" or months[0] == months[1]:
        return reading_label(r["reading"], months)
    if r["a"] or r["b"]:
        sides = bool(r["a"]), bool(r["b"])
    else:
        sides = r["why_a"] != NOT_ASKED, r["why_b"] != NOT_ASKED
    if all(sides):
        return reading_label("change", months)
    return "change over %d months" % months[0] if sides[0] else "change (what if: over %d months)" % months[1]


def lines(c):
    """The comparison as the terminal prints it: what differs, then each change whose direction moves."""
    out = ["What if: %s against %s, both from the pull of %s." % (c["b"], c["a"], c["vintage"]), ""]
    differ = [s for s in c["settings"] if s["differs"]]
    if not differ:
        out.append("The two files give the same answers, so every reading is the same.")
    for s in differ:
        out.append("  %s: %s -> %s" % (s["setting"], s["a"], s["b"]))
    t = c["totals"]
    out += ["", "%d changes read under both: %d the same way, %d more upward, %d more downward. %d read as you "
                "have it only, %d under the what-if only.%s" % (
                    t["compared"], t["same"], t["up"], t["down"], t["only_a"], t["only_b"],
                    " %d under neither." % t["neither"] if t["neither"] else ""), ""]
    for r in sorted(c["rows"], key=lambda r: (-abs(r["move"] or 0), ORDER.get(r["key"], 0))):
        name = "%s, %s" % (r["title"], row_label(r, c["months"]))
        if r["move"]:
            a, b = r["a"], r["b"]
            out.append("  %s  %-60s %s -> %s  (%+.1f typical moves of %s since %s -> %+.1f of %s since %s)" % (
                "up" if r["move"] > 0 else "dn", name, a["direction"], b["direction"], a["movement"],
                "{:,}".format(a["readings"]), when(a["history_from"]), b["movement"], "{:,}".format(b["readings"]),
                when(b["history_from"])))
        elif r["a"] is None and r["b"] is None:
            out.append("  ..  %-60s read under neither: as you have it, %s; under the what-if, %s"
                       % (name, r["why_a"], r["why_b"]))
        elif not (r["a"] and r["b"]):
            side = "as you have it" if r["a"] else "under the what-if"
            out.append("  ..  %-60s read %s only; the other: %s" % (name, side, r["why_missing"]))
    return out
