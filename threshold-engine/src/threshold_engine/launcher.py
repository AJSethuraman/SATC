"""The window: a person builds the thresholds workbook without a command line.

Steps down the left, as docs/PEERS-SPEC.md ("Window") lays them out, after
PocketBook's launcher (pocketbook/src/pocketbook/launcher.py, read, not
imported, so this project lifts out whole):

    1. Series     the CSV files, each with the product label the bank gives it
    2. Measure    name, unit, direction, smoothing, whether a value at or below
                  zero is always Low
    3. Settings   the scale's starting values (Moderate's half-width, the
                  Moderate-Low step, High's z, which score a value on a line
                  takes) and the backtest's (percentiles, horizon, history)
    4. Build      where the workbook goes; Run writes it and opens it
    5. Peers      optional: the cache folder, the roster, the quarters, the
                  products, whether delinquency and nonaccrual are included,
                  and every rule `peers build` requires. Pull fills the cache
                  from the FDIC; Build writes the peer workbook (one Peers
                  dashboard: filters at the top, every view under them) and
                  its series CSVs. Both call ``peers/run.py``, the same two functions
                  `peers pull` and `peers build` call, so the window and the
                  command line cannot drift (docs/V1-ROUND2-SPEC.md, section C)

Every field the bank must state starts EMPTY. The window fills in nothing:
Run stays off, and says which fields are still wanted, until every one is
stated; so do Pull and Build on the Peers step, each over the fields it uses.
A long operation runs on a worker thread with a status line, and a second
press while one runs is refused in words. Everything the window decides -- what is missing, what each field
turns into, what Run says -- is a plain function over a `Form`, so the tests
drive it without a display. `window()` only draws a Form.

The build calls `threshold_engine.workbook.build` directly, in this process;
Pull and Build call `threshold_engine.peers.run.pull` and `.build`.
Nothing at the top of this file imports openpyxl: the window opens without it
and says so (PocketBook's add-on check, ruling OC-34 there), rather than
failing with a traceback before anything is on screen.
"""
from __future__ import annotations

import csv
import importlib.util
import datetime as dt
import math
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# books.py is plain Python (no openpyxl), so the product names come from the
# one place the peer build reads them, and the window still opens without
# openpyxl. peers/run.py does import openpyxl, so it is loaded only on a press.
from .peers.books import PRODUCTS as _PEER_PRODUCTS
from .series import LABEL_RULE, label_ok

TITLE = "Thresholds"
STEPS = ("Series", "Measure", "Settings", "Build", "Peers")

#: Colours, the same tokens as keybank_style (a test holds them equal). Copied,
#: not imported, because keybank_style imports openpyxl and the window must
#: open on a machine that lacks it.
INK, KEY_RED, CRIMSON = "#0A0908", "#CC0000", "#960019"
PAPER, CANVAS, MIST, STONE, SLATE = "#FFFFFF", "#F4F1EC", "#E4DFD5", "#B9B4AC", "#57534B"

DIRECTIONS = (("higher_is_worse", "Higher is worse (a loss rate)"),
              ("lower_is_worse", "Lower is worse (a credit score)"))
YES_NO = (("yes", "Yes: a value at or below zero is always Low"),
          ("no", "No: zero is an ordinary value"))
ON_THE_LINE = (("worse", "The worse score"), ("better", "The better score"))

#: The workbook's calendar is quarterly; it refuses anything else, so this is
#: a fact about the tool and not a choice the window offers.
FREQUENCY = "quarterly"

#: What each add-on does, for the line the window shows when one is missing.
NEEDED = {"openpyxl": "writes the Excel workbook"}


# --------------------------------------------------------------------------
# The form: what the person has typed, as typed


@dataclass
class Form:
    """Everything the window holds, as text exactly as entered. Every field
    starts empty: nothing is a default, because every one of them is the
    bank's to state. ``half_lives`` is the one optional field (blank: none),
    as it is on the command line."""
    series: List[Tuple[str, str]] = field(default_factory=list)   # (label, path)
    name: str = ""
    unit: str = ""
    direction: str = ""           # higher_is_worse | lower_is_worse
    smoothing: str = ""
    floor_at_zero: str = ""       # yes | no
    moderate_halfwidth: str = ""
    low_step: str = ""
    high_z: str = ""
    on_the_line: str = ""         # worse | better
    percentiles: str = ""         # e.g. "50 75 90 95"
    horizon: str = ""
    min_history: str = ""
    half_lives: str = ""          # optional, e.g. "10"
    out: str = ""


def add_files(form: Form, paths) -> List[str]:
    """Add CSV files to Series, each with an empty label for the bank to give.
    A file already listed is not added twice; returns what was skipped, in
    words."""
    said = []
    have = {os.path.normcase(os.path.abspath(p)) for _, p in form.series}
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key in have:
            said.append("%s is already listed." % Path(p).name)
            continue
        have.add(key)
        form.series.append(("", str(p)))
    return said


def set_label(form: Form, i: int, label: str) -> None:
    """Give the i-th series its product label."""
    form.series[i] = (label, form.series[i][1])


def remove(form: Form, i: int) -> None:
    """Take the i-th series off the list."""
    del form.series[i]


# --------------------------------------------------------------------------
# What is wanted, and what each field becomes


def _number(text: str, what: str, step: str, out: list, whole=False, least=None, above=None):
    """``text`` as a number, or None with the reason appended to ``out``.
    'nan', 'inf' and anything too large to hold (1e309) are not numbers here:
    every range check below is a comparison, and NaN passes every comparison,
    so letting one through would write a blank into the bank's Settings."""
    t = text.strip()
    if not t:
        out.append("%s: %s is empty." % (step, what))
        return None
    try:
        v = int(t) if whole else float(t)
        if not math.isfinite(v):
            raise ValueError(t)
    except ValueError:
        out.append("%s: %s must be a %s, not %r." % (step, what, "whole number" if whole else "number", t))
        return None
    if least is not None and v < least:
        out.append("%s: %s must be %g or more." % (step, what, least))
        return None
    if above is not None and v <= above:
        out.append("%s: %s must be above %g." % (step, what, above))
        return None
    return v


def _numbers(text: str, what: str, step: str, out: list, required=True):
    """A list of numbers separated by spaces or commas; None when unreadable.
    As with ``_number``, 'nan' and 'inf' are unreadable."""
    t = text.replace(",", " ").split()
    if not t:
        if required:
            out.append("%s: %s is empty." % (step, what))
            return None
        return []
    try:
        vs = [float(x) for x in t]
        if not all(math.isfinite(v) for v in vs):
            raise ValueError(text)
        return vs
    except ValueError:
        out.append("%s: %s must be numbers separated by spaces, not %r." % (step, what, text.strip()))
        return None


def _choice(text: str, options, what: str, step: str, out: list):
    if text in [k for k, _ in options]:
        return text
    out.append("%s: choose %s." % (step, what))
    return None


#: What a product label may not hold: ``series.LABEL_RULE``, which
#: ``workbook.build`` applies too, so the window and the command line agree.
_LABEL_RULE, _label_ok = LABEL_RULE, label_ok


def _header_problem(path: str) -> Optional[str]:
    """What is wrong with the file's header line, or None. The build reads each
    file as CSV with a ``date`` and a ``value`` column (lines starting with '#'
    skipped), so a file without that header is refused here, in words, rather
    than failing inside the build."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            first = next((ln for ln in fh if not ln.startswith("#")), "")
    except UnicodeDecodeError:
        return "Series: %s is not a text CSV file." % Path(path).name
    except OSError as exc:
        return "Series: couldn't read %s (%s)." % (Path(path).name, exc.strerror or exc)
    head = next(csv.reader([first]), [])
    if "date" not in head or "value" not in head:
        return "Series: %s must begin with the header line date,value." % Path(path).name
    return None


def _check(form: Form) -> Tuple[dict, List[str]]:
    """The build's arguments and every problem, in step order. One pass, so
    what the window lists and what Run refuses can never disagree."""
    out: List[str] = []
    # 1. Series
    if not form.series:
        out.append("Series: add at least one CSV file.")
    labels = [lbl.strip() for lbl, _ in form.series]
    for (lbl, path), clean in zip(form.series, labels):
        name = Path(path).name
        if not clean:
            out.append("Series: give %s a product label." % name)
        elif not _label_ok(clean):
            out.append("Series: the label %r can't be used: %s." % (clean, _LABEL_RULE))
        if not Path(path).is_file():
            out.append("Series: %s is not there any more." % path)
        else:
            bad = _header_problem(path)
            if bad:
                out.append(bad)
    # The workbook finds a product with Excel's MATCH, which ignores capitals:
    # 'Mortgage' and 'mortgage' are one product to it, so they are one here.
    spellings: Dict[str, List[str]] = {}
    for x in labels:
        if x:
            spellings.setdefault(x.casefold(), []).append(x)
    for key in sorted(k for k, v in spellings.items() if len(v) > 1):
        seen = list(dict.fromkeys(spellings[key]))
        if len(seen) == 1:
            out.append("Series: two files share the label %r; each product needs its own." % seen[0])
        else:
            out.append("Series: the labels %s are one label to Excel, which ignores capitals; "
                       "each product needs its own." % " and ".join(repr(x) for x in seen))
    # 2. Measure
    name, unit = form.name.strip(), form.unit.strip()
    if not name:
        out.append("Measure: the measure's name is empty.")
    if not unit:
        out.append("Measure: the unit is empty.")
    direction = _choice(form.direction, DIRECTIONS, "whether higher or lower is worse", "Measure", out)
    smoothing = _number(form.smoothing, "smoothing (quarters averaged; 1 is none)", "Measure", out,
                        whole=True, least=1)
    floor = _choice(form.floor_at_zero, YES_NO, "whether a value at or below zero is always Low", "Measure", out)
    # 3. Settings
    hw = _number(form.moderate_halfwidth, "Moderate's half-width", "Settings", out, least=0)
    ls = _number(form.low_step, "the Moderate-Low step", "Settings", out)
    hz = _number(form.high_z, "High's z", "Settings", out, above=0)
    if hw is not None and ls is not None and ls <= hw:
        out.append("Settings: Moderate-Low must begin further from the median than Moderate, so the "
                   "Moderate-Low step must be larger than Moderate's half-width.")
    line = _choice(form.on_the_line, ON_THE_LINE, "which score a value exactly on a line takes", "Settings", out)
    pcts = _numbers(form.percentiles, "the backtest percentiles", "Settings", out)
    if pcts and (pcts != sorted(set(pcts)) or not all(0 < p < 100 for p in pcts)):
        out.append("Settings: the backtest percentiles must rise and lie between 0 and 100.")
    horizon = _number(form.horizon, "the backtest horizon (quarters ahead)", "Settings", out, whole=True, least=1)
    hist = _number(form.min_history, "the backtest's minimum history (quarters)", "Settings", out,
                   whole=True, least=2)
    lives = _numbers(form.half_lives, "the half-lives", "Settings", out, required=False)
    if lives and not all(h > 0 for h in lives):
        out.append("Settings: each half-life must be above 0 years.")
    # 4. Build
    dest = form.out.strip()
    if not dest:
        out.append("Build: choose where the workbook goes.")
    elif not dest.lower().endswith(".xlsx"):
        out.append("Build: the workbook must be an .xlsx file.")
    elif Path(dest).is_dir():
        out.append("Build: %s is a folder; give the workbook a file name." % dest)
    elif not Path(dest).parent.is_dir():
        out.append("Build: the folder %s is not there." % Path(dest).parent)

    args = dict(out=Path(dest), series=[(lbl, Path(p)) for lbl, (_, p) in zip(labels, form.series)],
                name=name, unit=unit, direction=direction, frequency=FREQUENCY, smoothing=smoothing,
                floor_at_zero=None if floor is None else floor == "yes",
                moderate_halfwidth=hw, low_step=ls, high_z=hz, on_the_line=line,
                half_lives=tuple(lives or ()), percentiles=tuple(pcts or ()), horizon=horizon,
                min_history=hist)
    return args, out


def problems(form: Form) -> List[str]:
    """Every field still wanted or wrong, in words, in the order of the steps.
    Empty means Run may go."""
    return _check(form)[1]


class Refused(ValueError):
    """The form is not complete; ``problems`` lists why."""

    def __init__(self, problems_: List[str]):
        super().__init__("; ".join(problems_))
        self.problems = problems_


def arguments(form: Form) -> dict:
    """The keyword arguments for ``workbook.build``, converted from the form.
    Refuses (raises ``Refused``) while anything is wanted: no field is ever
    filled in for the bank."""
    args, wanted = _check(form)
    if wanted:
        raise Refused(wanted)
    return args


@dataclass
class Step:
    name: str
    mark: str        # done, todo
    sub: str = ""


def steps(form: Form, peers: "PeerForm") -> List[Step]:
    """The rail: each step done or with how many things it still wants. Peers
    counts what Pull and Build still want between them, each field once."""
    wanted = problems(form) + peer_problems(peers, "both")
    out = []
    for name in STEPS:
        n = sum(1 for p in wanted if p.startswith(name + ":"))
        out.append(Step(name, "done" if n == 0 else "todo",
                        "Complete" if n == 0 else "%d to fill in" % n))
    return out


# --------------------------------------------------------------------------
# Run


def missing_addons() -> List[str]:
    """The add-ons the build needs that this computer lacks. Looked for
    without loading them."""
    return [n for n in NEEDED if importlib.util.find_spec(n) is None]


def addon_words(missing: List[str]) -> str:
    """The banner's line while an add-on is missing; empty when none is."""
    if not missing:
        return ""
    return ("This computer lacks %s, which %s. Run will stay off until it is installed: "
            "python -m pip install %s" % (", ".join(missing), "; ".join(NEEDED[m] for m in missing),
                                          " ".join(missing)))


@dataclass
class Outcome:
    ok: bool
    lines: List[str]
    path: Optional[Path] = None


def run(form: Form, build: Optional[Callable] = None, open_after: bool = True) -> Outcome:
    """Run pressed: refuse in words while anything is wanted, else write the
    workbook with ``workbook.build`` and open it. A refusal from the build
    itself (a series with a gap, too little history for the backtest, the
    file open in Excel, a row missing its value) comes back as words too,
    never a traceback. A row missing its date or value surfaces from the
    build's CSV reader as KeyError or TypeError, so those are said as well."""
    gone = missing_addons()
    if gone:
        return Outcome(False, [addon_words(gone)])
    try:
        args = arguments(form)
    except Refused as exc:
        return Outcome(False, ["Run is waiting for:"] + exc.problems)
    if build is None:
        from .workbook import build
    try:
        r = build(**args)
    except PermissionError:
        return Outcome(False, ["Couldn't write %s: it may be open in Excel. Close it and press Run again."
                               % args["out"].name])
    except (ValueError, OSError) as exc:
        return Outcome(False, ["The build refused: %s" % exc])
    except (KeyError, TypeError) as exc:
        return Outcome(False, ["The build couldn't read a series (%s: %s). Each file needs the header "
                               "date,value and both on every row." % (type(exc).__name__, exc)])
    lines = ["Wrote %s: %s, %d quarters." % (r["path"], ", ".join(r["products"]), r["quarters"])]
    if open_after:
        said = open_workbook(r["path"])
        if said:
            lines.append(said)
    return Outcome(True, lines, Path(r["path"]))


def open_file(path: Path) -> None:
    """Hand the file to whatever opens .xlsx on this computer."""
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_workbook(path: Path) -> str:
    """Open the workbook; what to say if it can't be opened from here, else ""."""
    try:
        open_file(path)
    except OSError as exc:
        return "Couldn't open %s from here (%s). It is in %s." % (Path(path).name, exc.strerror or exc,
                                                                 Path(path).parent)
    return ""


# --------------------------------------------------------------------------
# Peers: the form, what Pull and Build each want, and the two presses
#
# Pull and Build call peers/run.py's ``pull`` and ``build``: the functions
# `peers pull` and `peers build` call. The window checks that every field is
# stated and readable, and says so in words; run.py checks every stated
# setting again before it reads anything, and what it refuses comes back here
# as words too.

#: The products the peer build knows, in its order (peers/books.py).
PEER_PRODUCTS = tuple(_PEER_PRODUCTS)
PEER_DELINQUENCY = (("yes", "Yes: also delinquency and nonaccrual, by product"),
                    ("no", "No: charge-offs only"))
PEER_MERGERS = (("yes", "Yes: also the FDIC's merger record, from the date below"),
                ("no", "No merger record"))
PEER_REFRESH = (("yes", "Yes: fetch every quarter again, even those in the cache"),
                ("no", "No: fetch only the quarters not in the cache"))
PEER_EXEMPT = (("yes", "Yes: the bank itself is drawn whatever its size"),
               ("no", "No: the bank itself meets the minimum like any other"))
PEER_PACK = (("all", "All peers"), ("regionals", "Regionals only"))
PEER_RANK_BY = (("gross", "Gross charge-offs"), ("net", "Net charge-offs"))
#: What each press is called, and what it is doing while it runs.
PRESSES = {"pull": ("Pull", "Pulling from the FDIC"),
           "build": ("Build", "Building the peer workbook")}
#: The word that states an empty list, where the build needs one stated.
NONE_WORD = "none"

_QUARTER = re.compile(r"\d{4}Q[1-4]")
_EXTRA = re.compile(r"\d+=\d{4}Q[1-4]")


@dataclass
class PeerForm:
    """Everything the Peers step holds, as text exactly as entered, and the
    products ticked. Every field starts empty, the yes/no choices and the
    lists included: an empty list is stated by writing ``none``, because a
    blank field would not say whether there are none or nobody has looked."""
    cache: str = ""
    roster: str = ""
    first: str = ""                # YYYYQn
    last: str = ""
    products: List[str] = field(default_factory=list)
    delinquency: str = ""          # yes | no
    mergers_pull: str = ""         # yes | no: Pull also fetches the merger record
    mergers_since: str = ""        # YYYY-MM-DD, when mergers_pull is yes
    refresh: str = ""              # yes | no
    out: str = ""                  # the peer workbook, .xlsx
    series_dir: str = ""
    mergers_file: str = ""         # {cert: [quarter-end dates]}, as Pull writes it
    absorptions_file: str = ""     # who absorbed whom, as Pull writes it
    extra_acquisitions: str = ""   # CERT=YYYYQn ..., or none
    industry_combined: str = ""    # PRODUCT+PRODUCT; ..., or none
    jump: str = ""
    acquisition_share: str = ""
    min_book: str = ""
    exempt_self: str = ""          # yes | no
    pack: str = ""                 # all | regionals
    min_banks: str = ""
    rank_by: str = ""              # gross | net
    last_n: str = ""
    min_obs: str = ""
    base_quarter: str = ""         # YYYYQn
    index_min_book: str = ""
    lagged_years: str = ""         # whole years
    lag_years: str = ""
    normalisation_years: str = ""  # two years: base and end
    mix_base_year: str = ""


def tick(pf: PeerForm, product: str, on: bool) -> None:
    """Tick or untick a product; the list stays in the build's product order."""
    if product not in PEER_PRODUCTS:
        raise ValueError("%r is not one of the products: %s" % (product, ", ".join(PEER_PRODUCTS)))
    chosen = (set(pf.products) | {product}) if on else (set(pf.products) - {product})
    pf.products[:] = [p for p in PEER_PRODUCTS if p in chosen]


def _peer_path(text, what, out, kind, must_exist):
    """A stated path, or None with the reason. ``kind`` is 'folder' or 'file'.
    A folder Pull may create need not exist; one Build reads must."""
    t = text.strip()
    if not t:
        out.append("Peers: %s is empty." % what)
        return None
    p = Path(t)
    if kind == "folder":
        if p.exists() and not p.is_dir():
            out.append("Peers: %s, %s, is a file, not a folder." % (what, t))
            return None
        if must_exist and not p.is_dir():
            out.append("Peers: %s, %s, is not there; Pull fills it first." % (what, t))
            return None
    elif not p.is_file():
        out.append("Peers: %s, %s, is not there." % (what, t))
        return None
    return p


def _peer_xlsx(text, what, out):
    """Where an .xlsx goes, by the same rules as the Build step's."""
    t = text.strip()
    if not t:
        out.append("Peers: choose where %s goes." % what)
    elif not t.lower().endswith(".xlsx"):
        out.append("Peers: %s must be an .xlsx file." % what)
    elif Path(t).is_dir():
        out.append("Peers: %s is a folder; give %s a file name." % (t, what))
    elif not Path(t).parent.is_dir():
        out.append("Peers: the folder %s is not there." % Path(t).parent)
    else:
        return Path(t)
    return None


def _peer_quarter(text, what, out):
    t = text.strip()
    if not t:
        out.append("Peers: %s is empty." % what)
    elif not _QUARTER.fullmatch(t):
        out.append("Peers: %s must be a quarter written like 2006Q1, not %r." % (what, t))
    else:
        return t
    return None


def _peer_years(text, what, out, count=None):
    """Whole years separated by spaces or commas; exactly ``count`` when given.
    A year is the digits 0-9 and nothing else: ``str.isdigit`` also passes
    '²' and other characters ``int`` cannot read, and a raise here would
    reach the window's field trace instead of coming back as words."""
    t = text.replace(",", " ").split()
    if not t:
        out.append("Peers: nothing is stated for %s." % what)
        return None
    if not all(re.fullmatch(r"[0-9]+", x) for x in t):
        out.append("Peers: %s must be whole years separated by spaces, not %r." % (what, text.strip()))
        return None
    if count is not None and len(t) != count:
        out.append("Peers: %s needs exactly %d years, not %d." % (what, count, len(t)))
        return None
    return [int(x) for x in t]


def _peer_list(text, what, out, split, ok, form_words):
    """A stated list: ``none`` for an empty one, else items split by ``split``,
    each passing ``ok``. Blank is wanted, never read as none."""
    t = text.strip()
    if not t:
        out.append("Peers: nothing is stated for %s; write %s if there are none." % (what, NONE_WORD))
        return None
    if t.lower() == NONE_WORD:
        return []
    items = [x.strip() for x in split(t) if x.strip()]
    bad = [x for x in items if not ok(x)]
    if bad or not items:
        out.append("Peers: %s takes %s, or %s; %s is not one." % (
            what, form_words, NONE_WORD, ", ".join(repr(x) for x in bad) or repr(t)))
        return None
    return items


def _combined_ok(item: str) -> bool:
    names = [n.strip() for n in item.split("+")]
    return len(names) >= 2 and len(set(names)) == len(names) and all(n in PEER_PRODUCTS for n in names)


#: Which press uses which field. ``cache`` is read differently by the two:
#: Pull may create the folder, Build reads only what is already in it.
_PULL = ("cache_pull", "first", "last", "products", "delinquency", "mergers_pull", "mergers_since",
         "refresh")
_BUILD = ("cache_build", "roster", "first", "last", "products", "delinquency", "out", "series_dir",
          "mergers_file", "absorptions_file", "extra_acquisitions", "industry_combined", "jump",
          "acquisition_share", "min_book", "exempt_self",
          "pack", "min_banks", "rank_by", "last_n", "min_obs", "base_quarter", "index_min_book",
          "lagged_years", "lag_years", "normalisation_years", "mix_base_year")
#: Every field in the order the page shows it.
_PAGE_ORDER = ("cache_pull", "cache_build", "roster", "first", "last", "products", "delinquency",
               "mergers_pull", "mergers_since", "refresh") + _BUILD[6:]


def _peer_fields(pf: PeerForm) -> Dict[str, Tuple[object, List[str]]]:
    """``{key: (value, problems)}`` for every Peers field: the value run.py
    takes, or None while it is wanted or wrong. Each problem names the field
    by the words the page shows and by its command-line flag, which is how
    run.py names it when it refuses."""
    f: Dict[str, Tuple[object, List[str]]] = {}

    def put(key, read):
        out: List[str] = []
        f[key] = (read(out), out)

    def num(attr, what, **kw):
        put(attr, lambda o: _number(getattr(pf, attr), what, "Peers", o, **kw))

    def yes_no(attr, options, what):
        put(attr, lambda o: _choice(getattr(pf, attr), options, what, "Peers", o))

    put("cache_pull", lambda o: _peer_path(pf.cache, "the cache folder (--cache)", o, "folder", False))
    put("cache_build", lambda o: _peer_path(pf.cache, "the cache folder (--cache)", o, "folder", True))
    put("roster", lambda o: _peer_path(pf.roster, "the roster file (--roster)", o, "file", True))
    put("first", lambda o: _peer_quarter(pf.first, "the first quarter (--first)", o))
    put("last", lambda o: _peer_quarter(pf.last, "the last quarter (--last)", o))
    first, last = f["first"][0], f["last"][0]
    if first and last and first > last:          # YYYYQn sorts as it reads
        f["last"] = (None, ["Peers: the last quarter (--last), %s, comes before the first, %s."
                            % (last, first)])

    def products(o):
        if not pf.products:
            o.append("Peers: tick at least one product (--products).")
            return None
        if any(p not in PEER_PRODUCTS for p in pf.products) or len(set(pf.products)) != len(pf.products):
            o.append("Peers: the products (--products) must be distinct, from %s, not %r."
                     % (", ".join(PEER_PRODUCTS), pf.products))
            return None
        return list(pf.products)
    put("products", products)
    yes_no("delinquency", PEER_DELINQUENCY,
           "whether delinquency and nonaccrual are included (--delinquency)")
    yes_no("mergers_pull", PEER_MERGERS, "whether Pull also fetches the merger record (--mergers)")

    def since(o):
        t = pf.mergers_since.strip()
        if pf.mergers_pull == "no":
            if t:
                o.append("Peers: a date for the merger record is given, but No merger record is "
                         "chosen; choose Yes or clear the date.")
            return None
        if pf.mergers_pull != "yes":
            return None             # the choice is what is wanted, and it is said once
        if not t:
            o.append("Peers: the date the merger record starts (--mergers) is empty.")
            return None
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                raise ValueError(t)
            dt.date.fromisoformat(t)
        except ValueError:
            o.append("Peers: the date the merger record starts (--mergers) must be a date written "
                     "like 2005-10-01, not %r." % t)
            return None
        return t
    put("mergers_since", since)
    yes_no("refresh", PEER_REFRESH, "whether quarters already in the cache are fetched again (--refresh)")
    put("out", lambda o: _peer_xlsx(pf.out, "the peer workbook", o))
    put("series_dir", lambda o: _peer_path(pf.series_dir, "the series folder (--series-dir)", o,
                                           "folder", False))
    put("mergers_file", lambda o: _peer_path(pf.mergers_file, "the merger file (--mergers)", o, "file", True))
    put("absorptions_file", lambda o: _peer_path(pf.absorptions_file, "the absorptions file (--absorptions)",
                                                 o, "file", True))
    put("extra_acquisitions", lambda o: _peer_list(
        pf.extra_acquisitions, "the extra acquisitions (--extra-acquisitions)", o,
        lambda t: t.replace(",", " ").replace(";", " ").split(), _EXTRA.fullmatch, "CERT=YYYYQn items"))
    put("industry_combined", lambda o: _peer_list(
        pf.industry_combined, "the combined industry series (--industry-combined)", o,
        lambda t: t.split(";"), _combined_ok,
        "two or more products joined by +, one series from the next by ;"))
    num("jump", "the jump (--jump)", least=0)
    num("acquisition_share", "the acquisition share (--acquisition-share)", least=0)
    num("min_book", "the minimum book (--min-book)", least=0)
    yes_no("exempt_self", PEER_EXEMPT, "whether the bank itself is exempt from the minimum (--exempt-self)")
    yes_no("pack", PEER_PACK, "the pack (--pack)")
    num("min_banks", "the number of banks a composite needs (--min-banks)", whole=True, least=1)
    yes_no("rank_by", PEER_RANK_BY, "what best and worst are ranked by (--rank-by)")
    num("last_n", "the number of quarters best and worst are ranked over (--last-n)", whole=True, least=1)
    num("min_obs", "the number of kept quarters a bank needs to be ranked (--min-obs)", whole=True, least=1)
    put("base_quarter", lambda o: _peer_quarter(pf.base_quarter,
                                                "the balance index's base quarter (--base-quarter)", o))
    num("index_min_book", "the smallest book indexed (--index-min-book)", least=0)
    put("lagged_years", lambda o: _peer_years(pf.lagged_years, "the lagged years (--lagged-years)", o))
    num("lag_years", "the lag in years (--lag-years)", whole=True, least=0)
    put("normalisation_years", lambda o: _peer_years(
        pf.normalisation_years, "the normalisation years (--normalisation-years)", o, 2))
    num("mix_base_year", "the mix base year (--mix-base-year)", whole=True, least=0)
    return f


def _peer_keys(action: str):
    if action == "pull":
        return set(_PULL)
    if action == "build":
        return set(_BUILD)
    if action == "both":
        return set(_PULL) | set(_BUILD)
    raise ValueError("action is pull, build or both, not %r" % (action,))


def peer_problems(pf: PeerForm, action: str) -> List[str]:
    """Every field ``action`` ('pull', 'build' or 'both') still wants or finds
    wrong, in words, in the order of the page, each said once. Empty means
    that press may go."""
    keys, f, out = _peer_keys(action), _peer_fields(pf), []
    for k in _PAGE_ORDER:
        if k in keys:
            out += [p for p in f[k][1] if p not in out]
    return out


def peer_arguments(pf: PeerForm, action: str) -> dict:
    """The keyword arguments for ``peers.run.pull`` ('pull') or
    ``peers.run.build`` ('build'), converted from the form. Refuses (raises
    ``Refused``) while anything that press uses is wanted: nothing is filled
    in for the bank."""
    if action not in ("pull", "build"):
        raise ValueError("action is pull or build, not %r" % (action,))
    wanted = peer_problems(pf, action)
    if wanted:
        raise Refused(wanted)
    v = {k: val for k, (val, _) in _peer_fields(pf).items()}

    def yes(attr):
        return getattr(pf, attr) == "yes"
    if action == "pull":
        return dict(cache=v["cache_pull"], first=v["first"], last=v["last"], products=v["products"],
                    delinquency=yes("delinquency"),
                    mergers_since=v["mergers_since"] if yes("mergers_pull") else None,
                    refresh=yes("refresh"))
    return dict(out=v["out"], cache=v["cache_build"], roster=v["roster"], series_dir=v["series_dir"],
                first=v["first"], last=v["last"], products=v["products"], mergers=v["mergers_file"],
                absorptions=v["absorptions_file"],
                extra_acquisitions=v["extra_acquisitions"], industry_combined=v["industry_combined"],
                jump=v["jump"], acquisition_share=v["acquisition_share"], min_book=v["min_book"], exempt_self=yes("exempt_self"), pack=v["pack"],
                min_banks=v["min_banks"], rank_by=v["rank_by"], last_n=v["last_n"], min_obs=v["min_obs"],
                base_quarter=v["base_quarter"], index_min_book=v["index_min_book"],
                lagged_years=v["lagged_years"], lag_years=v["lag_years"],
                normalisation_years=v["normalisation_years"], mix_base_year=v["mix_base_year"],
                delinquency=yes("delinquency"))


def peer_refusal(busy: Optional[str], action: str) -> Optional[str]:
    """A press while Pull or Build is running is refused, in words; None when
    nothing is running. ``busy`` is the press running, or None."""
    if action not in PRESSES or (busy is not None and busy not in PRESSES):
        raise ValueError("a press is pull or build, not %r" % ((busy, action),))
    if busy is None:
        return None
    return ("%s is still running. Wait for it to finish before pressing %s."
            % (PRESSES[busy][0], PRESSES[action][0]))


def status_words(action: str, said: Sequence[str]) -> str:
    """The status line while ``action`` runs: what it is doing, and the last
    thing it has said, once it has said something."""
    doing = PRESSES[action][1] + "... this takes a little while."
    return doing if not said else "%s Latest: %s" % (doing, said[-1])


def finished_words(action: str, outcome: "Outcome") -> str:
    """The status line once ``action`` has finished."""
    name = PRESSES[action][0]
    return ("%s finished." % name) if outcome.ok else ("%s did not finish; the reason is below." % name)


def _same_path(a, b) -> bool:
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def _denied_words(action: str, exc: PermissionError, args: dict) -> List[str]:
    """A PermissionError from Pull or Build, in words that name the file it
    was about, never one it was not. ``os.replace`` names the file it was
    moving (``filename``, the .part) and the one it was moving onto
    (``filename2``); the second is the one the bank has open.

    ``peers.run.build`` puts every file in place together or not at all
    (``run._commit``); a file it could not replace arrives as an OSError
    carrying ``not_replaced`` and is worded by ``_not_replaced_words``."""
    target = exc.filename2 or exc.filename
    if action == "pull":
        return ["The pull couldn't write to %s: permission was denied. Choose a cache folder you can "
                "write to and press Pull again." % (target or args["cache"])]
    out = args["out"]
    out_part = out.with_name(out.stem + ".part" + out.suffix)
    if target is None:
        return ["Couldn't write %s or a file in the series folder %s: one may be open in Excel. Close it "
                "and press Build again." % (out.name, args["series_dir"])]
    p = Path(str(target))
    if _same_path(p, out) or _same_path(p, out_part):
        return ["Couldn't write %s: it may be open in Excel. Close it and press Build again." % out.name]
    if _same_path(p.parent, args["series_dir"]):
        name = p.name[:-len(".part")] if p.name.endswith(".part") else p.name
        return ["Couldn't write the series file %s: it may be open in Excel. Close it and press Build again."
                % name]
    return ["The build was denied access to %s. Check that it can be read and written from here, "
            "and press Build again." % p]


def _not_replaced_words(exc: OSError, args: dict) -> List[str]:
    """The file ``run._commit`` could not replace, named, and whether the
    earlier files were all put back (``stuck`` empty) or which were not."""
    denied = PermissionError(13, "denied")
    denied.filename = str(exc.not_replaced)
    words = _denied_words("build", denied, args)
    if exc.stuck:
        return words + ["These could not be put back as they were, so check them before using them: %s"
                        % ", ".join(str(f) for f in exc.stuck)]
    return words + ["Nothing was changed: %s and the series files are as they were." % args["out"].name]


def _peer_press(action: str, pf: PeerForm, fn: Optional[Callable], say: Optional[Callable],
                open_after: bool) -> "Outcome":
    gone = missing_addons()
    if gone:
        return Outcome(False, [addon_words(gone)])
    name = PRESSES[action][0]
    try:
        args = peer_arguments(pf, action)
    except Refused as exc:
        return Outcome(False, ["%s is waiting for:" % name] + exc.problems)
    if fn is None:
        from .peers import run as peers_run
        fn = peers_run.pull if action == "pull" else peers_run.build
    said: List[str] = []

    def tell(line):
        said.append(str(line))
        if say is not None:
            say(str(line))
    try:
        fn(say=tell, **args)
    except PermissionError as exc:
        return Outcome(False, said + _denied_words(action, exc, args))
    except ValueError as exc:
        return Outcome(False, said + ["The %s refused: %s" % (action, exc)])
    except OSError as exc:
        if getattr(exc, "not_replaced", None) is not None:
            return Outcome(False, said + _not_replaced_words(exc, args))
        return Outcome(False, said + ["The %s stopped: %s" % (action, exc)])
    except RuntimeError as exc:
        return Outcome(False, said + ["The %s stopped: %s" % (action, exc)])
    if action == "pull":
        return Outcome(True, said, args["cache"])
    if open_after:
        could_not = open_workbook(args["out"])
        if could_not:
            said.append(could_not)
    return Outcome(True, said, args["out"])


def peer_pull(pf: PeerForm, pull: Optional[Callable] = None,
              say: Optional[Callable[[str], None]] = None) -> "Outcome":
    """Pull pressed: refuse in words while a field Pull uses is wanted, else
    call ``peers.run.pull`` (``pull`` replaces it in a test) with the form's
    arguments. Each line it says goes to ``say`` as it is said (the status
    line) and into the outcome. A refusal (ValueError) or a failed fetch or
    write (OSError, RuntimeError) comes back as words, never a traceback."""
    return _peer_press("pull", pf, pull, say, open_after=False)


def peer_build(pf: PeerForm, build: Optional[Callable] = None,
               say: Optional[Callable[[str], None]] = None, open_after: bool = True) -> "Outcome":
    """Build pressed: refuse in words while a field Build uses is wanted, else
    call ``peers.run.build`` (``build`` replaces it in a test), the function
    `peers build` calls, and open the peer workbook. A file open in Excel
    (named: the workbook or the series file it was), a refusal from the
    build, or a failed read comes back as words."""
    return _peer_press("build", pf, build, say, open_after=open_after)


# --------------------------------------------------------------------------
# The window: draws a Form; decides nothing


def window(root) -> dict:
    """Draw the window on ``root`` and return its widgets by name, so a test
    can look at them. Every rule is in the functions above."""
    import tkinter as tk
    from tkinter import filedialog

    form, pf = Form(), PeerForm()
    w: Dict[str, object] = {"form": form, "peers": pf, "page": "Series", "busy": False, "said": [],
                            "peer_busy": None, "peer_status_text": "", "peer_lines": []}
    root.title(TITLE)
    root.geometry("940x640")
    root.minsize(760, 520)
    root.configure(bg=PAPER)

    rail = tk.Frame(root, bg=CANVAS, width=200)
    rail.pack(side="left", fill="y")
    rail.pack_propagate(False)
    tk.Frame(root, bg=MIST, width=1).pack(side="left", fill="y")
    page = tk.Frame(root, bg=PAPER, padx=20, pady=18)
    page.pack(side="left", fill="both", expand=True)

    def label(master, text, size=13, bold=False, fg=INK, wrap=620, **kw):
        return tk.Label(master, text=text, font=("Arial", -size, "bold" if bold else "normal"), fg=fg,
                        bg=master.cget("bg"), anchor="w", justify="left", wraplength=wrap, **kw)

    def clear(f):
        for c in f.winfo_children():
            c.destroy()

    def changed(*_):
        draw_rail()
        if w["page"] == "Build":
            draw_wanted()
        if w["page"] == "Peers":
            draw_peer_state()

    def text_field(master, title, attr, hint=""):
        """A labelled entry that writes straight into the form."""
        label(master, title, bold=True).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar(value=getattr(form, attr))
        var.trace_add("write", lambda *_: (setattr(form, attr, var.get()), changed()))
        e = tk.Entry(master, textvariable=var, font=("Arial", -13), relief="solid", bd=1, width=40)
        e.pack(anchor="w")
        if hint:
            label(master, hint, size=11, fg=SLATE).pack(anchor="w")
        w["field_" + attr] = e
        w["var_" + attr] = var
        return e

    def choice_field(master, title, attr, options):
        """Radio buttons with none picked until the bank picks one."""
        label(master, title, bold=True).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar(value=getattr(form, attr))
        var.trace_add("write", lambda *_: (setattr(form, attr, var.get()), changed()))
        for key, words in options:
            tk.Radiobutton(master, text=words, value=key, variable=var, bg=PAPER, anchor="w",
                           font=("Arial", -13)).pack(anchor="w")
        w["var_" + attr] = var

    def draw_rail():
        clear(rail)
        label(rail, TITLE, size=16, bold=True).pack(anchor="w", padx=16, pady=(18, 4))
        tk.Frame(rail, bg=KEY_RED, height=3, width=160).pack(anchor="w", padx=16, pady=(0, 14))
        for i, st in enumerate(steps(form, pf)):
            row = tk.Frame(rail, bg=CANVAS)
            row.pack(anchor="w", fill="x", padx=14, pady=5)
            here = st.name == w["page"]
            name = label(row, "%d. %s" % (i + 1, st.name), bold=here, fg=KEY_RED if here else INK, wrap=170)
            name.pack(anchor="w")
            label(row, st.sub, size=11, fg=SLATE if st.mark == "done" else CRIMSON, wrap=170).pack(anchor="w")
            w["step_" + st.name] = name
            for x in (row, name):
                x.bind("<Button-1>", lambda e, n=st.name: show(n))
                x.configure(cursor="hand2")

    def heading(text, note=""):
        label(page, text, size=18, bold=True).pack(anchor="w")
        if note:
            label(page, note, size=12, fg=SLATE).pack(anchor="w", pady=(2, 6))

    def draw_series():
        heading("Series", "One CSV per product, with a date,value header. Give each the label the "
                          "workbook will show for it.")
        box = tk.Frame(page, bg=PAPER)
        box.pack(anchor="w", fill="x", pady=(6, 6))
        for i, (lbl, path) in enumerate(form.series):
            row = tk.Frame(box, bg=PAPER)
            row.pack(anchor="w", fill="x", pady=2)
            var = tk.StringVar(value=lbl)
            var.trace_add("write", lambda *_, i=i, v=var: (set_label(form, i, v.get()), changed()))
            tk.Entry(row, textvariable=var, width=22, font=("Arial", -13), relief="solid", bd=1).pack(side="left")
            label(row, Path(path).name, wrap=380).pack(side="left", padx=8)
            tk.Button(row, text="Remove", command=lambda i=i: (remove(form, i), show("Series"))).pack(side="right")
            w["label_%d" % i] = var
        if not form.series:
            label(box, "No files yet.", fg=SLATE).pack(anchor="w")

        def pick():
            got = filedialog.askopenfilenames(title="Add series", filetypes=[("CSV files", "*.csv")])
            w["said"] = add_files(form, got)
            show("Series")
        w["add"] = tk.Button(page, text="Add CSV files...", command=pick)
        w["add"].pack(anchor="w", pady=(6, 0))
        for s in w["said"]:
            label(page, s, size=12, fg=SLATE).pack(anchor="w")
        w["said"] = []

    def draw_measure():
        heading("Measure", "Shared by every product: one scale, one measure.")
        text_field(page, "Name", "name", "e.g. TTM net charge-off rate")
        text_field(page, "Unit", "unit", "e.g. %")
        choice_field(page, "Which way is worse", "direction", DIRECTIONS)
        text_field(page, "Smoothing", "smoothing", "Quarters averaged before anything else; 1 is none.")
        choice_field(page, "Is a value at or below zero always Low?", "floor_at_zero", YES_NO)
        label(page, "Calendar: quarterly (the only one the workbook builds).", size=11, fg=SLATE).pack(
            anchor="w", pady=(10, 0))

    def draw_settings():
        heading("Settings", "The starting values for Your settings on the workbook's red Assess tab. You can "
                            "change them there afterwards and the lines move.")
        cols = tk.Frame(page, bg=PAPER)
        cols.pack(anchor="w", fill="x")
        left, right = tk.Frame(cols, bg=PAPER), tk.Frame(cols, bg=PAPER)
        left.pack(side="left", anchor="n", padx=(0, 30))
        right.pack(side="left", anchor="n")
        label(left, "The scale", size=14, bold=True).pack(anchor="w")
        text_field(left, "Moderate: half-width", "moderate_halfwidth", "In typical yearly moves around the median.")
        text_field(left, "Moderate-Low step", "low_step", "Typical yearly moves below the median.")
        text_field(left, "High: z", "high_z", "Median + z x spread of levels.")
        choice_field(left, "A value exactly on a line takes", "on_the_line", ON_THE_LINE)
        label(right, "The backtest", size=14, bold=True).pack(anchor="w")
        text_field(right, "Percentiles", "percentiles", "Where scores 2, 3, ... begin, e.g. 50 75 90 95.")
        text_field(right, "Horizon", "horizon", "Quarters ahead each score is judged against.")
        text_field(right, "Minimum history", "min_history", "Quarters of history before the first test.")
        text_field(right, "Half-lives (optional)", "half_lives", "Years; blank means none.")

    def draw_wanted():
        box = w.get("wanted")
        if box is None or not box.winfo_exists():
            return
        clear(box)
        gone = missing_addons()
        wanted = problems(form)
        if gone:
            label(box, addon_words(gone), fg=CRIMSON).pack(anchor="w")
        elif wanted:
            label(box, "Run is waiting for:", bold=True, fg=CRIMSON).pack(anchor="w")
            for p in wanted:
                label(box, "  " + p, size=12, fg=CRIMSON).pack(anchor="w")
        else:
            label(box, "Everything is stated. Run writes the workbook and opens it.", fg=SLATE).pack(anchor="w")
        w["run"].configure(state="normal" if not wanted and not gone and not w["busy"] else "disabled")

    def draw_build():
        heading("Build", "Where the workbook goes. Run writes it and opens it.")
        row = tk.Frame(page, bg=PAPER)
        row.pack(anchor="w", fill="x", pady=(8, 0))
        var = tk.StringVar(value=form.out)
        var.trace_add("write", lambda *_: (setattr(form, "out", var.get()), changed()))
        tk.Entry(row, textvariable=var, width=60, font=("Arial", -13), relief="solid", bd=1).pack(side="left")
        w["var_out"] = var

        def choose():
            got = filedialog.asksaveasfilename(title="Save the workbook as", defaultextension=".xlsx",
                                               filetypes=[("Excel workbook", "*.xlsx")])
            if got:
                var.set(got)
        tk.Button(row, text="Choose...", command=choose).pack(side="left", padx=8)
        w["run"] = tk.Button(page, text="Run", command=press_run, bg=KEY_RED, fg=PAPER,
                             font=("Arial", -13, "bold"), disabledforeground=STONE)
        w["run"].pack(anchor="w", pady=(12, 8))
        w["wanted"] = tk.Frame(page, bg=PAPER)
        w["wanted"].pack(anchor="w", fill="x")
        w["result"] = label(page, "\n".join(w.get("result_lines", [])), size=12)
        w["result"].pack(anchor="w", pady=(10, 0))
        draw_wanted()

    # ---- Peers: the fields scroll; Pull, Build and the status line stay put

    def peer_text(master, title, attr, hint="", browse=None):
        """A labelled entry writing into the PeerForm; ``browse`` adds a
        Choose... button ('folder', 'file' or 'save')."""
        label(master, title, bold=True).pack(anchor="w", pady=(8, 2))
        row = tk.Frame(master, bg=PAPER)
        row.pack(anchor="w")
        var = tk.StringVar(value=getattr(pf, attr))
        var.trace_add("write", lambda *_: (setattr(pf, attr, var.get()), changed()))
        tk.Entry(row, textvariable=var, font=("Arial", -13), relief="solid", bd=1, width=52).pack(side="left")
        if browse:
            def choose():
                if browse == "folder":
                    got = filedialog.askdirectory(title=title)
                elif browse == "save":
                    got = filedialog.asksaveasfilename(title=title, defaultextension=".xlsx",
                                                       filetypes=[("Excel workbook", "*.xlsx")])
                else:
                    got = filedialog.askopenfilename(title=title, filetypes=[("JSON files", "*.json")])
                if got:
                    var.set(got)
            tk.Button(row, text="Choose...", command=choose).pack(side="left", padx=8)
        if hint:
            label(master, hint, size=11, fg=SLATE).pack(anchor="w")
        w["peer_var_" + attr] = var

    def peer_choice(master, title, attr, options):
        """Radio buttons with none picked until the bank picks one."""
        label(master, title, bold=True).pack(anchor="w", pady=(8, 2))
        var = tk.StringVar(value=getattr(pf, attr))
        var.trace_add("write", lambda *_: (setattr(pf, attr, var.get()), changed()))
        for key, words in options:
            tk.Radiobutton(master, text=words, value=key, variable=var, bg=PAPER, anchor="w",
                           font=("Arial", -13)).pack(anchor="w")
        w["peer_var_" + attr] = var

    def section(master, text):
        label(master, text, size=14, bold=True).pack(anchor="w", pady=(16, 0))

    def draw_peer_state():
        """The buttons, the status line, the last outcome and what each press
        still wants: all from the functions above."""
        box = w.get("peer_wanted")
        if box is None or not box.winfo_exists():
            return
        gone = missing_addons()
        wants = {a: peer_problems(pf, a) for a in PRESSES}
        for a in PRESSES:
            w[a].configure(state="normal" if not wants[a] and not gone and w["peer_busy"] is None
                           else "disabled")
        w["peer_status"].configure(text=w["peer_status_text"])
        w["peer_result"].configure(text="\n".join(w["peer_lines"]))
        clear(box)
        if gone:
            label(box, addon_words(gone), fg=CRIMSON).pack(anchor="w")
            return
        for a in PRESSES:
            if wants[a]:
                label(box, "%s is waiting for:" % PRESSES[a][0], bold=True, fg=CRIMSON).pack(
                    anchor="w", pady=(6, 0))
                for p in wants[a]:
                    label(box, "  " + p, size=12, fg=CRIMSON).pack(anchor="w")
        if not any(wants.values()):
            label(box, "Everything is stated. Pull fills the cache; Build writes the peer workbook "
                       "(one Peers tab: pick at the top, every chart and table follows) and opens it.", fg=SLATE).pack(anchor="w")

    def draw_peers():
        heading("Peers", "Optional. The bank against its peers, from public FDIC Call Reports. Pull "
                         "fills the cache folder from the FDIC; Build reads only the cache.")
        bar = tk.Frame(page, bg=PAPER)
        bar.pack(anchor="w", fill="x", pady=(4, 0))
        for a in PRESSES:
            w[a] = tk.Button(bar, text=PRESSES[a][0], command=lambda a=a: press_peer(a), bg=KEY_RED,
                             fg=PAPER, font=("Arial", -13, "bold"), disabledforeground=STONE, width=8)
            w[a].pack(side="left", padx=(0, 10))
        w["peer_status"] = label(page, "", size=12, fg=SLATE)
        w["peer_status"].pack(anchor="w", pady=(6, 0))
        w["peer_result"] = label(page, "", size=12)
        w["peer_result"].pack(anchor="w")

        holder = tk.Frame(page, bg=PAPER)
        holder.pack(fill="both", expand=True, pady=(8, 0))
        canvas = tk.Canvas(holder, bg=PAPER, highlightthickness=0)
        scroll = tk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=PAPER)
        canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def wheel(e):
            canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        w["peer_canvas"] = canvas

        section(body, "Where, and what")
        peer_text(body, "Cache folder (--cache)", "cache", "Pull writes one file per quarter here; "
                  "Build reads only these.", browse="folder")
        peer_text(body, "Roster file (--roster)", "roster", "Which banks are peers, and which is the bank "
                  "itself, e.g. config/peers.json.", browse="file")
        peer_text(body, "First quarter (--first)", "first", "Written like 2006Q1.")
        peer_text(body, "Last quarter (--last)", "last", "Written like 2026Q2.")
        label(body, "Products (--products)", bold=True).pack(anchor="w", pady=(8, 2))
        for p in PEER_PRODUCTS:
            var = tk.BooleanVar(value=p in pf.products)
            var.trace_add("write", lambda *_, p=p, v=var: (tick(pf, p, v.get()), changed()))
            tk.Checkbutton(body, text=p, variable=var, bg=PAPER, anchor="w",
                           font=("Arial", -13)).pack(anchor="w")
            w["peer_product_" + p] = var
        peer_choice(body, "Delinquency and nonaccrual (--delinquency)", "delinquency", PEER_DELINQUENCY)

        section(body, "Pull")
        peer_choice(body, "Merger record (--mergers)", "mergers_pull", PEER_MERGERS)
        peer_text(body, "Merger record from", "mergers_since", "A date written like 2005-10-01; Pull "
                  "writes the record into the cache folder as mergers.json.")
        peer_choice(body, "Quarters already in the cache (--refresh)", "refresh", PEER_REFRESH)

        section(body, "Build")
        peer_text(body, "Peer workbook", "out", "The .xlsx Build writes: one Peers tab, a dashboard. Its "
                  "yellow cells (product, rate, Peer A and B, how many quarters the charts show, which banks are "
                  "in the pack) start from the settings below and can be changed there.", browse="save")
        peer_text(body, "Series folder (--series-dir)", "series_dir", "Where the date,value CSVs go, for "
                  "the Series step.", browse="folder")
        peer_text(body, "Merger file (--mergers)", "mergers_file", "{cert: [quarter-end dates]}, as Pull "
                  "writes it.", browse="file")
        peer_text(body, "Absorptions file (--absorptions)", "absorptions_file", "Who absorbed whom, as "
                  "Pull writes it beside the merger file (absorptions.json).", browse="file")
        peer_text(body, "Extra acquisitions (--extra-acquisitions)", "extra_acquisitions",
                  "Acquisitions the FDIC record does not show, as CERT=YYYYQn separated by spaces; "
                  "write none if there are none.")
        peer_text(body, "Combined industry series (--industry-combined)", "industry_combined",
                  "Products summed together, joined by +, one series from the next by ; "
                  "(e.g. Other consumer+Auto); write none if there are none.")

        section(body, "The rules")
        peer_text(body, "Jump (--jump)", "jump", "A quarter-on-quarter balance move above this is "
                  "structural (0.25 is 25%). Under delinquency it blanks a four-quarter average, never "
                  "a quarter-end rate.")
        peer_text(body, "Acquisition share (--acquisition-share)", "acquisition_share", "When a bank's "
                  "acquisitions in a quarter, added together, bring in at least this share of its book "
                  "(0.05 is 5%), its next four quarters are left out: the bought loans' losses are not "
                  "its own.")
        peer_text(body, "Minimum book (--min-book)", "min_book", "The smallest average balance ($000) "
                  "whose rate is kept; for delinquency, the quarter-end balance.")
        peer_choice(body, "Is the bank itself exempt from the minimum? (--exempt-self)", "exempt_self",
                    PEER_EXEMPT)
        peer_choice(body, "Pack to start with (--pack): the banks whose Yes/No starts Yes", "pack", PEER_PACK)
        peer_text(body, "Banks a composite needs (--min-banks)", "min_banks", "Kept banks a composite or "
                  "band needs; a whole number.")
        peer_choice(body, "Best and worst are ranked by (--rank-by)", "rank_by", PEER_RANK_BY)
        peer_text(body, "Ranked over (--last-n)", "last_n", "Quarters best and worst are ranked over.")
        peer_text(body, "Quarters to be ranked (--min-obs)", "min_obs", "Kept quarters a bank needs to "
                  "be ranked.")

        section(body, "The other views on the Peers tab")
        peer_text(body, "Balance index base (--base-quarter)", "base_quarter", "Written like 2019Q4.")
        peer_text(body, "Smallest book indexed (--index-min-book)", "index_min_book", "In $000, at the base.")
        peer_text(body, "Lagged years (--lagged-years)", "lagged_years", "Whole years separated by spaces.")
        peer_text(body, "Lag (--lag-years)", "lag_years", "In whole years.")
        peer_text(body, "Normalisation years (--normalisation-years)", "normalisation_years",
                  "Two years: the base, then the end.")
        peer_text(body, "Mix base year (--mix-base-year)", "mix_base_year", "A whole year.")

        w["peer_wanted"] = tk.Frame(body, bg=PAPER)
        w["peer_wanted"].pack(anchor="w", fill="x", pady=(16, 8))
        draw_peer_state()

    def press_peer(action):
        """Pull or Build pressed: refused in words while either is running,
        else run on a worker thread, with a status line while it runs.
        ``peer_busy`` is set before anything that can raise, so anything
        that raises before the worker has started clears it again: a busy
        mark with no worker behind it would refuse every press until the
        window is closed."""
        refusal = peer_refusal(w["peer_busy"], action)
        if refusal:
            w["peer_status_text"] = refusal
            draw_peer_state()
            return
        w["peer_busy"] = action
        said: List[str] = []
        done: dict = {}
        press = peer_pull if action == "pull" else peer_build

        def work():
            try:
                done["out"] = press(pf, say=said.append)
            except Exception as exc:          # noqa: BLE001 -- said on the page, never a traceback
                done["out"] = Outcome(False, ["Something went wrong that the window didn't expect: %s: %s"
                                              % (type(exc).__name__, exc)])
        try:
            w["peer_status_text"], w["peer_lines"] = status_words(action, said), []
            draw_peer_state()
            t = threading.Thread(target=work, daemon=True)
            t.start()
        except Exception as exc:              # noqa: BLE001 -- said on the page, and the press freed
            w["peer_busy"] = None
            w["peer_outcome"] = Outcome(False, ["Something went wrong that the window didn't expect: %s: %s"
                                                % (type(exc).__name__, exc)])
            w["peer_status_text"] = finished_words(action, w["peer_outcome"])
            w["peer_lines"] = w["peer_outcome"].lines
            draw_peer_state()
            return

        def wait():
            if t.is_alive():
                w["peer_status_text"] = status_words(action, list(said))
                draw_peer_state()
                root.after(200, wait)
                return
            w["peer_busy"] = None
            w["peer_outcome"] = done["out"]
            w["peer_status_text"] = finished_words(action, done["out"])
            w["peer_lines"] = done["out"].lines
            draw_rail()
            draw_peer_state()
        root.after(200, wait)

    def press_run():
        if w["busy"]:
            return
        w["busy"] = True
        w["result_lines"] = ["Building... this takes a little while."]
        show("Build")
        done: dict = {}

        def work():
            try:
                done["out"] = run(form)
            except Exception as exc:          # noqa: BLE001 -- said on the page, never a traceback
                done["out"] = Outcome(False, ["Something went wrong that the window didn't expect: %s: %s"
                                              % (type(exc).__name__, exc)])
        t = threading.Thread(target=work, daemon=True)
        t.start()

        def wait():
            if t.is_alive():
                root.after(200, wait)
                return
            w["busy"] = False
            w["result_lines"] = done["out"].lines
            w["outcome"] = done["out"]
            show("Build")
        root.after(200, wait)

    pages = {"Series": draw_series, "Measure": draw_measure, "Settings": draw_settings,
             "Build": draw_build, "Peers": draw_peers}

    def show(name):
        w["page"] = name
        clear(page)
        pages[name]()
        draw_rail()

    w["show"] = show
    w["press_run"] = press_run
    w["press_peer"] = press_peer
    show("Series")
    return w


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    window(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
