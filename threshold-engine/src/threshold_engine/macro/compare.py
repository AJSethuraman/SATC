"""Two rating runs side by side: what changes if the settings change (W12).

The walk of 16 Oct 2026 asked what changes if each reading is measured against
the last 30 years instead of its full history, and the answer took a script
written by hand. This is that script, made part of the tool:

    python -m threshold_engine.macro rate --settings settings.json --compare what-if.json

Both files are full settings files, and each must be complete: a what-if with
a gap refuses, naming the file and the gap, exactly as the firm's own does.
Both runs read the same pull, so the only thing that can differ is the
settings. Nothing here changes either file, and nothing is chosen: the tool
reports, for every reading, the rating under each and what it was measured
against. Which settings to keep is the firm's call.
"""
from .catalog import RATED

ORDER = {item.key: i for i, item in enumerate(RATED)}
ITEMS = {item.key: item for item in RATED}
NOT_ASKED = "not asked for by these settings"

#: Each setting, as the workbook and the printout name it.
CALLED = {"cutoffs": "Where ratings 2 to 5 start", "on_the_line": "A reading exactly on a cut-off",
          "history": "History each reading is measured against", "change_months": "Change counted over",
          "show_sahm": "Sahm reading shown", "change_for": "Also rated on their change"}


def plain(name, s):
    """One answer from a run's settings (``rate_all``'s ``settings``), in words."""
    v = s[name]
    if name == "cutoffs":
        return ", ".join("%g" % c for c in v) + " (percentiles where 2, 3, 4 and 5 start)"
    if name == "on_the_line":
        return v + " rating"
    if name == "history":
        return "full history" if v == "full" else "the last %d years" % v["years"]
    if name == "change_months":
        return "%d months" % v
    if name == "show_sahm":
        return "yes" if v else "no"
    if name == "change_for":
        return "all series" if v == "all" else ", ".join(v) or "none"
    raise KeyError(name)


def settings_rows(a, b):
    """Every setting, each run's answer in words, and whether they differ.

    ``a`` and ``b`` are the ``settings`` of two runs. Directions are listed
    reading by reading; one answered in only one run (``change_for`` asks for
    the reading in one and not the other) shows "not asked" for the other."""
    rows = [{"setting": CALLED[n], "name": n, "a": plain(n, a), "b": plain(n, b), "differs": a[n] != b[n]}
            for n in CALLED]
    da = {(k, r): v for k, r, v in a["directions"]}
    db = {(k, r): v for k, r, v in b["directions"]}
    titles = {item.key: item.title for item in RATED}
    for k, r in sorted(set(da) | set(db), key=lambda kr: (ORDER.get(kr[0], 0), kr[1])):
        va, vb = da.get((k, r), "not asked"), db.get((k, r), "not asked")
        rows.append({"setting": "Which way is worse: %s, %s" % (titles.get(k, k), "level" if r == "position" else
                                                                "change"),
                     "name": "directions", "a": va, "b": vb, "differs": va != vb})
    return rows


def _side(r):
    keep = ("rating", "percentile", "readings", "history_from", "date", "value", "lines", "direction", "sentence")
    return {k: r[k] for k in keep}


def compare(a, b, label_a, label_b):
    """Compare two ``rate_all`` results made from the same pull.

    Returns the settings side by side, a row per reading, the 5 x 5 count of
    rating against rating, and the totals. A row's ``move`` is the what-if
    rating minus the rating as set: above zero rates higher (worse), below
    zero lower. A reading rated in one run only says why it is missing from
    the other, in that run's own words. A reading either run asked for and
    neither rated is a row too, with each run's reason (Codex on #452: one only
    the what-if asked for, and could not rate, was left out altogether)."""
    if a["vintage"] != b["vintage"]:
        raise ValueError("the two runs read different pulls (%s, %s); compare runs of one pull"
                         % (a["vintage"], b["vintage"]))
    # One pull is one set of bytes, not one folder name: a file changed between the two runs would show as a
    # move the settings did not make (Codex on #452).
    differ = sorted(n for n in set(a["read_sha"]) | set(b["read_sha"]) if a["read_sha"].get(n) != b["read_sha"].get(n))
    if differ:
        raise ValueError("the two runs read different bytes of the pull of %s (%s: changed, gone or new between "
                         "them); compare two runs of one reading of it" % (a["vintage"], ", ".join(differ)))
    ra = {(r["key"], r["reading"]): r for r in a["ratings"]}
    rb = {(r["key"], r["reading"]): r for r in b["ratings"]}
    why_a = {(x["key"], x["reading"]): x["why"] for x in a["not_rated"]}
    why_b = {(x["key"], x["reading"]): x["why"] for x in b["not_rated"]}
    same_change = a["settings"]["change_months"] == b["settings"]["change_months"]
    rows = []
    matrix = [[0] * 5 for _ in range(5)]
    totals = {"compared": 0, "same": 0, "higher": 0, "lower": 0, "only_a": 0, "only_b": 0, "neither": 0}
    keys = set(ra) | set(rb) | set(why_a) | set(why_b)
    for key, reading in sorted(keys, key=lambda kr: (ORDER.get(kr[0], 0), kr[1] != "position")):
        x, y = ra.get((key, reading)), rb.get((key, reading))
        first = x or y or {"title": ITEMS[key].title, "group": ITEMS[key].group}
        row = {"key": key, "title": first["title"], "group": first["group"], "reading": reading,
               "a": _side(x) if x else None, "b": _side(y) if y else None,
               # each run's reason where it has no rating: its own words, or not asked for
               "why_a": None if x else why_a.get((key, reading), NOT_ASKED),
               "why_b": None if y else why_b.get((key, reading), NOT_ASKED),
               # A change over a different number of months is a different measure, so its lines are not
               # comparable on one chart; its ratings still are, each against its own history.
               "same_measure": reading == "position" or same_change}
        if x and y:
            row["move"] = y["rating"] - x["rating"]
            matrix[x["rating"] - 1][y["rating"] - 1] += 1
            totals["compared"] += 1
            totals["same" if row["move"] == 0 else "higher" if row["move"] > 0 else "lower"] += 1
        elif x or y:
            row["move"] = None
            row["why_missing"] = row["why_b"] if x else row["why_a"]
            totals["only_a" if x else "only_b"] += 1
        else:
            row["move"] = None
            totals["neither"] += 1
        rows.append(row)
    return {"vintage": a["vintage"], "a": label_a, "b": label_b,
            # what the comparison was made from, so a workbook can check it is this rating's (Codex on #452)
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
    when they differ, since then each side's rating is of a different change (Codex on #452)."""
    if reading == "position":
        return "level"
    a, b = months
    return "change over %d months" % a if a == b else "change over %d months; what if: over %d months" % (a, b)


def row_label(r, months):
    """A comparison row's reading, naming the horizon of each side the row speaks for: the sides that rated
    it, or, when neither did, the sides whose settings asked for it. So a change rated as you have it only
    is over your months, and one only the what-if asked for is over the what-if's (Codex on #452, twice:
    the label named a horizon whose side made no rating, then one whose settings never asked)."""
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
    """The comparison as the terminal prints it: what differs, then each reading that moves."""
    out = ["What if: %s against %s, both from the pull of %s." % (c["b"], c["a"], c["vintage"]), ""]
    differ = [s for s in c["settings"] if s["differs"]]
    if not differ:
        out.append("The two files give the same answers, so every rating is the same.")
    for s in differ:
        out.append("  %s: %s -> %s" % (s["setting"], s["a"], s["b"]))
    t = c["totals"]
    out += ["", "%d readings rated under both: %d at the same rating, %d higher, %d lower. %d rated as you have "
                "it only, %d under the what-if only.%s" % (t["compared"], t["same"], t["higher"], t["lower"],
                                                           t["only_a"], t["only_b"], " %d under neither." %
                                                           t["neither"] if t["neither"] else ""), ""]
    for r in sorted(c["rows"], key=lambda r: (-(abs(r["move"]) if r["move"] else 0), ORDER.get(r["key"], 0))):
        name = "%s, %s" % (r["title"], row_label(r, c["months"]))
        if r["move"]:
            a, b = r["a"], r["b"]
            out.append("  %+d  %-60s %d -> %d  (%.1f%% of %s since %s -> %.1f%% of %s since %s)" % (
                r["move"], name, a["rating"], b["rating"], a["percentile"], "{:,}".format(a["readings"]),
                when(a["history_from"]), b["percentile"], "{:,}".format(b["readings"]), when(b["history_from"])))
        elif r["move"] is None and (r["a"] or r["b"]):
            side = "as you have it" if r["a"] else "under the what-if"
            out.append("  ..  %-60s rated %s only; the other: %s" % (name, side, r["why_missing"]))
        elif r["move"] is None:
            out.append("  ..  %-60s not rated under either: as you have it, %s; under the what-if, %s"
                       % (name, r["why_a"], r["why_b"]))
    return out
