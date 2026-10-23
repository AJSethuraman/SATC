"""The firm's settings for the readings, and the refusal when any is missing.

Every setting is required and none has a default. The settings file is JSON;
each question carries an "answer", and only the answer is read. The template
also carries a "recommended" value and the reason for it, so the firm can see
the suggestion beside the blank. The tool never reads "recommended": a file
whose answers are still empty is refused, with every missing answer named, in
one message.

    python -m threshold_engine.macro settings-template OUT.json

Nothing is rated (the firm, 22 Oct 2026: "We are not rating these. At most
these are directional"), so the settings say how a reading is measured, not
where a rating starts: which history, which horizon, how wide normal movement
is, which quarters are left out of every history, and how much of a chart may
run off its axis.
"""
import json
import pathlib
import re

READINGS = ("position", "change")

#: Settings an earlier version asked for, and why a file that still holds one is refused rather than read.
REMOVED = {
    "cutoffs": "the tool no longer rates (22 Oct 2026), so no rating starts anywhere",
    "on_the_line": "the tool no longer rates (22 Oct 2026), so no reading sits on a cut-off",
    "directions": "the tool no longer rates (22 Oct 2026); a change is read as Increasing, Stable or "
                  "Decreasing whichever way is worse",
    "change_for": "every series now has its change read, since its direction comes from it (22 Oct 2026)",
}

QUARTER = re.compile(r"^(\d{4})Q([1-4])$")


class Refused(ValueError):
    """The settings are missing an answer or hold one the tool cannot use."""


def readings_of(series):
    """The readings a series carries: its level where its place in its own history means something, and
    always its change. A level that climbs over the decades carries its change only."""
    return ("change",) if series.position else READINGS


QUESTIONS = [
    ("history",
     "Which history is each reading measured against? \"full\" for everything the publisher has, or "
     "{\"years\": N} for the last N years up to the latest reading.",
     "full",
     "Every series starts in a different year, so a fixed window would cut the long ones short; the start "
     "of each history is shown beside every reading, as the regulators do."),
    ("change_months",
     "Over how many months is a change counted? A whole number. Weekly and daily series count whole "
     "weeks (12 months is 52), as FRED does: a day with no reading that many weeks before has no change.",
     12,
     "A year: it takes out the seasons, and the report reads homeowner's insurance and revolving credit "
     "over a year."),
    ("normal_width",
     "How wide is normal movement? The median change plus or minus this many typical moves, where a typical "
     "move is 1.4826 times the median distance of the changes from their median. A number above 0. A change "
     "inside reads Stable; one at or past either edge reads Increasing or Decreasing.",
     1,
     "One typical move is the measure the loss thresholds use for ordinary year-to-year movement "
     "(threshold-engine scale.py). For changes shaped like a bell it holds about two in three of them, and a "
     "spike does not widen it, as it would a standard deviation."),
    ("left_out",
     "Which quarters are left out of every history? A list, each entry a quarter such as \"2020Q2\" or a run "
     "such as \"2020Q2-2021Q2\"; [] leaves nothing out. A reading in a quarter left out is not measured "
     "against, and a change with either end in one is not counted.",
     [],
     "Nothing until there is a reason to record. The pandemic quarters are the usual candidate: 2020Q2 to "
     "2021Q2 holds the spike in jobless claims and unemployment, and the loss thresholds' evidence was "
     "tested with and without 2020Q1 to 2023Q4."),
    ("axis_cut",
     "How much of each chart's readings may run off its axis, at each end? A percent from 0 to 10; 0 keeps "
     "every reading on the chart. The latest reading and the normal range always stay on it. Only the "
     "charts change; no reading does.",
     1,
     "A spike such as the 2020 jobless claims flattens the rest of a chart. With 1% at each end it runs off "
     "the edge, and a note under the chart names the highest reading and its date."),
    ("show_sahm",
     "Show the Sahm reading beside the national unemployment rate? true or false.",
     True,
     "It is the best-known published trigger for unemployment (0.50 points, Sahm 2019), and the report "
     "records its false alarm of 2024, so a reader should see it beside the change rather than instead of "
     "it."),
    # The Dashboard's test of whether two series' changes move together (the firm, 23 Oct 2026: "As the Excel
    # version", the comparison another agent built with the firm in the workbook that day).
    ("compare_p",
     "On the Dashboard, how small must p be for a link between two series' changes to pass? Two-tailed; a "
     "number above 0 and below 1.",
     0.05,
     "The usual level. A lead is tested at it after allowing for how many leads were tried."),
    ("compare_leads",
     "On the Dashboard, which leads are tried, in months? A list of whole numbers: a positive lead has the "
     "first series moving earlier, a negative one the second.",
     [-24, -18, -12, -6, 0, 6, 12, 18, 24, 30, 36],
     "Two years either way and three years of the first leading, in steps of six months: the range the "
     "comparison was built with."),
    ("compare_starts",
     "On the Dashboard, at how many starting points is the one-reading-a-year test run? 1, 2, 3, 4, 6 or 12; "
     "the starting months are spread evenly through the year.",
     4,
     "Charge-off rates are trailing four-quarter figures, so neighbouring quarters share most of their data. "
     "One reading every 12 months shares none, and four starting points (a quarter apart) show whether a link "
     "holds whichever quarter the count starts from."),
    ("compare_min_pairs",
     "On the Dashboard, how many one-a-year pairs must a lead have at every starting point to be tested? A "
     "whole number of at least 4.",
     6,
     "Fewer pairs than that cannot show much either way; a lead with fewer says not tested."),
]


def template():
    """The settings file with every answer empty and the recommendation beside it."""
    out = {"about": "Fill in every \"answer\"; the tool refuses until each one is filled. The "
                    "\"recommended\" values are suggestions and are never read by the tool."}
    for name, question, recommended, why in QUESTIONS:
        out[name] = {"question": question, "recommended": recommended, "why": why, "answer": None}
    return out


def write_template(path):
    path = pathlib.Path(path)
    if path.exists():
        raise Refused("%s already exists; the template is never written over a file that may hold answers" % path)
    path.write_text(json.dumps(template(), indent=1) + "\n", "utf-8")
    return path


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def quarter_index(label):
    """2020Q2 as a count of quarters, so runs of quarters compare and step; None if it is not a quarter."""
    m = QUARTER.match(label) if isinstance(label, str) else None
    return int(m.group(1)) * 4 + int(m.group(2)) - 1 if m else None


def quarter_label(n):
    return "%dQ%d" % (n // 4, n % 4 + 1)


def quarter_of(date):
    """The quarter a date (YYYY-MM-DD) falls in, as 2020Q2."""
    return "%sQ%d" % (date[:4], (int(date[5:7]) - 1) // 3 + 1)


def runs(entries):
    """The quarters left out, as [first, last] runs in order, from the firm's list; raises ValueError naming
    the first entry that is not a quarter or a run of them."""
    out = []
    for e in entries:
        first, _, last = e.partition("-") if isinstance(e, str) else (None, "", None)
        last = last or first
        a, b = quarter_index(first), quarter_index(last)
        if a is None or b is None or a > b:
            raise ValueError(e)
        out.append([quarter_label(a), quarter_label(b)])
    return sorted(out)


def left_out_set(left_out):
    """Every quarter in the runs left out, as labels."""
    return {quarter_label(n) for a, b in left_out for n in range(quarter_index(a), quarter_index(b) + 1)}


def check(raw):
    """The answers from a settings dict, or Refused naming every problem."""
    problems, s = [], {}
    if not isinstance(raw, dict):
        raise Refused("the settings file must hold one JSON object")
    known = {q[0] for q in QUESTIONS} | {"about"}
    for extra in sorted(set(raw) - known):
        problems.append("%s: %s" % (extra, "no longer a setting: " + REMOVED[extra] if extra in REMOVED else
                                    "not a setting the tool has"))

    def answer(name):
        item = raw.get(name)
        if not isinstance(item, dict) or item.get("answer") is None:
            problems.append("%s: not answered" % name)
            return None
        return item["answer"]

    h = answer("history")
    if h is not None:
        if h == "full":
            s["history"] = "full"
        elif (isinstance(h, dict) and set(h) == {"years"} and isinstance(h["years"], int)
              and not isinstance(h["years"], bool) and h["years"] > 0):
            s["history"] = {"years": h["years"]}
        else:
            problems.append("history: need \"full\" or {\"years\": N} with N a whole number above 0; got %r" % (h,))
    m = answer("change_months")
    if m is not None:
        if isinstance(m, int) and not isinstance(m, bool) and m > 0:
            s["change_months"] = m
        else:
            problems.append("change_months: need a whole number of months above 0; got %r" % (m,))
    w = answer("normal_width")
    if w is not None:
        if _number(w) and 0 < w <= 10:
            s["normal_width"] = float(w)
        else:
            problems.append("normal_width: need a number of typical moves above 0 and at most 10; got %r" % (w,))
    lo = answer("left_out")
    if lo is not None:
        if not isinstance(lo, list):
            problems.append("left_out: need a list of quarters such as \"2020Q2\" or runs such as "
                            "\"2020Q2-2021Q2\"; got %r" % (lo,))
        else:
            try:
                s["left_out"] = runs(lo)
            except ValueError as e:
                problems.append("left_out: %r is not a quarter such as \"2020Q2\" or a run such as "
                                "\"2020Q2-2021Q2\" whose first quarter comes first" % (e.args[0],))
    cut = answer("axis_cut")
    if cut is not None:
        if _number(cut) and 0 <= cut <= 10:
            s["axis_cut"] = float(cut)
        else:
            problems.append("axis_cut: need a percent from 0 to 10; got %r" % (cut,))
    sahm = answer("show_sahm")
    if sahm is not None:
        if isinstance(sahm, bool):
            s["show_sahm"] = sahm
        else:
            problems.append("show_sahm: need true or false; got %r" % (sahm,))
    cp = answer("compare_p")
    if cp is not None:
        if _number(cp) and 0 < cp < 1:
            s["compare_p"] = float(cp)
        else:
            problems.append("compare_p: need a number above 0 and below 1; got %r" % (cp,))
    leads = answer("compare_leads")
    if leads is not None:
        if (isinstance(leads, list) and leads and all(isinstance(x, int) and not isinstance(x, bool)
                                                      and abs(x) <= 120 for x in leads)
                and len(set(leads)) == len(leads)):
            s["compare_leads"] = sorted(leads)
        else:
            problems.append("compare_leads: need a list of different whole numbers of months, each from -120 to "
                            "120; got %r" % (leads,))
    starts = answer("compare_starts")
    if starts is not None:
        if starts in (1, 2, 3, 4, 6, 12) and not isinstance(starts, bool):
            s["compare_starts"] = starts
        else:
            problems.append("compare_starts: need 1, 2, 3, 4, 6 or 12; got %r" % (starts,))
    pairs = answer("compare_min_pairs")
    if pairs is not None:
        if isinstance(pairs, int) and not isinstance(pairs, bool) and pairs >= 4:
            s["compare_min_pairs"] = pairs
        else:
            problems.append("compare_min_pairs: need a whole number of at least 4; got %r" % (pairs,))
    if problems:
        raise Refused("the settings are not complete, so nothing is read:\n  " + "\n  ".join(problems))
    return s


def load(path):
    path = pathlib.Path(path)
    if not path.exists():
        raise Refused("no settings file at %s; write one to fill in with: python -m threshold_engine.macro "
                      "settings-template %s" % (path, path))
    try:
        raw = json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as e:
        raise Refused("%s is not readable JSON: %s" % (path, e))
    return check(raw)
