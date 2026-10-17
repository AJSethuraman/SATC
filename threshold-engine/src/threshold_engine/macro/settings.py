"""The firm's settings for the ratings, and the refusal when any is missing.

Every setting is required and none has a default. The settings file is JSON;
each question carries an "answer", and only the answer is read. The template
also carries a "recommended" value and the reason for it, so the firm can see
the suggestion beside the blank. The tool never reads "recommended": a file
whose answers are still empty is refused, with every missing answer named, in
one message.

    python -m threshold_engine.macro settings-template OUT.json
"""
import json
import pathlib

from .catalog import HIGHER, LOWER, RATED

NOT_RATED = "not rated"
DIRECTIONS = (HIGHER, LOWER, NOT_RATED)
READINGS = ("position", "change")


class Refused(ValueError):
    """The settings are missing an answer or hold one the tool cannot use."""


def readings_of(series, change_for):
    """The readings a series carries under ``change_for`` ("all" or a list of keys).

    A series rated on its place in its own history carries that reading, and its
    change too if the firm asks for it. A series not rated on its place (a level
    that climbs over the decades) carries its change only, whatever ``change_for``
    says, since otherwise it would carry nothing."""
    if series.position:
        return ("change",)
    if change_for == "all" or series.key in change_for:
        return READINGS
    return ("position",)


def open_readings(change_for):
    """Each (series key, reading) whose direction the research leaves to the firm."""
    return [(s.key, r) for s in RATED if s.stress is None for r in readings_of(s, change_for)]


def _recommended_directions():
    rec = {
        "cpi": {"change": HIGHER},
        "cpi_core": {"change": HIGHER},
        "used_cars": {"change": HIGHER},
        "house_prices": {"change": LOWER},
        "house_price_to_income": {"position": HIGHER, "change": LOWER},
        "mortgage_rate": {"position": HIGHER, "change": HIGHER},
        "revolving_credit": {"change": HIGHER},
        "cre_prices": {"change": LOWER},
        "ci_demand": {"position": LOWER, "change": LOWER},
    }
    return {k: dict(rec[k]) for k, _ in open_readings("all")}


QUESTIONS = [
    ("cutoffs",
     "From which percentile of its own history does a reading take ratings 2, 3, 4 and 5? Four numbers, "
     "each above the last, between 0 and 100.",
     [50, 75, 90, 95],
     "A reading above the median is at least a 2, and the top two ratings sit in the tail: the Fed's "
     "Financial Stability Report speaks of the upper quartile and the 90th percentile, and the Fed staff "
     "heat map (Aikman et al. 2015) drew lines at the 65th and 85th, with a red zone at the 80th."),
    ("on_the_line",
     "A reading exactly on a cut-off: does it take the worse rating or the better one? \"worse\" or \"better\".",
     "worse",
     "The tool exists to warn; a tie goes to the warning. The loss thresholds ask the same question."),
    ("history",
     "Which history is each reading measured against? \"full\" for everything the publisher has, or "
     "{\"years\": N} for the last N years up to the latest reading.",
     "full",
     "Every series starts in a different year, so a fixed window would cut the long ones short; the start "
     "of each history is shown beside every rating, as the regulators do."),
    ("change_months",
     "Over how many months is a change counted? A whole number. Weekly and daily series count whole "
     "weeks (12 months is 52), as FRED does: a day with no reading that many weeks before has no change.",
     12,
     "A year: it takes out the seasons, and the report reads homeowner's insurance and revolving credit "
     "over a year."),
    ("show_sahm",
     "Show the Sahm reading beside the national unemployment rate? true or false. It is shown, not rated.",
     True,
     "It is the best-known published trigger for unemployment (0.50 points, Sahm 2019), and the report "
     "records its false alarm of 2024, so a reader should see it beside the rating rather than instead of it."),
    ("change_for",
     "Which series rated on their place in history also get a rating for their change? \"all\", or a list "
     "of series keys. Series rated on their change only always get it.",
     "all",
     "The report's first rule: unemployment is lowest just before recessions, so its level alone reads "
     "1 Low at the turn; the change carries the signal, and the same holds for spreads and claims."),
    ("directions",
     "For each reading the research leaves open: which way is stress? \"higher is worse\", \"lower is "
     "worse\" or \"not rated\".",
     None,  # filled in by template(), one entry per open reading
     "Prices: rising is worse for borrowers. House prices: stretched when high against income, stressed "
     "when falling (the report's second rule). Mortgage rate: higher is worse for payments. Revolving "
     "credit: faster growth is the build-up. Business loan demand: weaker is worse, the least certain of "
     "these."),
]


def template():
    """The settings file with every answer empty and the recommendation beside it."""
    out = {"about": "Fill in every \"answer\"; the tool refuses until each one is filled. The "
                    "\"recommended\" values are suggestions and are never read by the tool."}
    for name, question, recommended, why in QUESTIONS:
        if name == "directions":
            recommended = _recommended_directions()
            answer = {k: {r: None for r in v} for k, v in recommended.items()}
        else:
            answer = None
        out[name] = {"question": question, "recommended": recommended, "why": why, "answer": answer}
    return out


def write_template(path):
    path = pathlib.Path(path)
    if path.exists():
        raise Refused("%s already exists; the template is never written over a file that may hold answers" % path)
    path.write_text(json.dumps(template(), indent=1) + "\n", "utf-8")
    return path


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def check(raw):
    """The answers from a settings dict, or Refused naming every problem."""
    problems, s = [], {}
    if not isinstance(raw, dict):
        raise Refused("the settings file must hold one JSON object")
    known = {q[0] for q in QUESTIONS} | {"about"}
    for extra in sorted(set(raw) - known):
        problems.append("%s: not a setting the tool has" % extra)

    def answer(name):
        item = raw.get(name)
        if not isinstance(item, dict) or item.get("answer") is None:
            problems.append("%s: not answered" % name)
            return None
        return item["answer"]

    c = answer("cutoffs")
    if c is not None:
        if (isinstance(c, list) and len(c) == 4 and all(_number(x) for x in c)
                and all(0 < x < 100 for x in c) and all(a < b for a, b in zip(c, c[1:]))):
            s["cutoffs"] = [float(x) for x in c]
        else:
            problems.append("cutoffs: need four numbers, each above the last, between 0 and 100; got %r" % (c,))
    o = answer("on_the_line")
    if o is not None:
        if o in ("worse", "better"):
            s["on_the_line"] = o
        else:
            problems.append("on_the_line: need \"worse\" or \"better\"; got %r" % (o,))
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
    sahm = answer("show_sahm")
    if sahm is not None:
        if isinstance(sahm, bool):
            s["show_sahm"] = sahm
        else:
            problems.append("show_sahm: need true or false; got %r" % (sahm,))
    cf = answer("change_for")
    rated_keys = {x.key for x in RATED}
    if cf is not None:
        if cf == "all":
            s["change_for"] = "all"
        elif isinstance(cf, list) and all(isinstance(k, str) for k in cf):
            unknown = sorted(set(cf) - rated_keys)
            if unknown:
                problems.append("change_for: not series the tool rates: %s" % ", ".join(unknown))
            else:
                s["change_for"] = sorted(set(cf))
        else:
            problems.append("change_for: need \"all\" or a list of series keys; got %r" % (cf,))

    d = raw.get("directions")
    given = d.get("answer") if isinstance(d, dict) else None
    if given is None:
        given = {}
    if not isinstance(given, dict):
        problems.append("directions: need an object of series keys; got %r" % (given,))
        given = {}
    open_keys = {x.key for x in RATED if x.stress is None}
    for k in sorted(set(given) - open_keys):
        why = "its direction is stated by the research" if k in rated_keys else "not a series the tool rates"
        problems.append("directions: %s: %s" % (k, why))
    # An answer for a reading a series never carries is named, as every other stray answer is (Fable on #452:
    # a direction for CPI's level, never rated, or for a misspelt reading, passed in silence).
    carried = {}
    for k, r in open_readings("all"):
        carried.setdefault(k, set()).add(r)
    for k in sorted(set(given) & open_keys):
        if isinstance(given[k], dict):
            for r in sorted(set(given[k]) - carried.get(k, set())):
                problems.append("directions: %s %s: %s" % (
                    k, r, "rated on its change only, so this answer is never read" if r == "position" else
                    "not a reading: \"position\" (its level) or \"change\""))
    directions = {}
    # Until change_for is answered, every open reading is asked for, so one
    # refusal names every gap rather than revealing them one answer at a time.
    for k, r in open_readings(s.get("change_for", "all")):
        v = given.get(k, {}).get(r) if isinstance(given.get(k), dict) else None
        if v is None:
            problems.append("directions: %s %s: not answered" % (k, r))
        elif v not in DIRECTIONS:
            problems.append("directions: %s %s: need one of %s; got %r" % (
                k, r, ", ".join('"%s"' % x for x in DIRECTIONS), v))
        else:
            directions[(k, r)] = v
    s["directions"] = directions
    if problems:
        raise Refused("the settings are not complete, so nothing is rated:\n  " + "\n  ".join(problems))
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

