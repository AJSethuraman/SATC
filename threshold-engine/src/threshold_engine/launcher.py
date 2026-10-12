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
    5. Peers      not in the window yet: the peer workbook is built from the
                  command line (`peers pull`, then `peers build`), and the
                  spec makes this step optional

Every field the bank must state starts EMPTY. The window fills in nothing:
Run stays off, and says which fields are still wanted, until every one is
stated. Everything the window decides -- what is missing, what each field
turns into, what Run says -- is a plain function over a `Form`, so the tests
drive it without a display. `window()` only draws a Form.

The build calls `threshold_engine.workbook.build` directly, in this process.
Nothing at the top of this file imports openpyxl: the window opens without it
and says so (PocketBook's add-on check, ruling OC-34 there), rather than
failing with a traceback before anything is on screen.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

TITLE = "Thresholds"
STEPS = ("Series", "Measure", "Settings", "Build", "Peers")
#: The step that is shown but not yet usable, and what it says.
COMING = {"Peers": "Not in the window yet. The peer workbook is built from the command line: "
                   "python -m threshold_engine peers pull, then python -m threshold_engine peers build."}

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


#: Characters a product label may not hold. The workbook lists the products in
#: a dropdown written as one quoted, comma-separated list, so a comma splits a
#: label in two and a double quote breaks the list (Excel will not open the
#: file); a label beginning with '=' is written as a formula, not as text.
_LABEL_RULE = "a label may not begin with '=' or hold a comma or a double quote"


def _label_ok(label: str) -> bool:
    return not label.startswith("=") and "," not in label and '"' not in label


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
    mark: str        # done, todo, coming
    sub: str = ""


def steps(form: Form) -> List[Step]:
    """The rail: each step done or with how many things it still wants."""
    wanted = problems(form)
    out = []
    for name in STEPS:
        if name in COMING:
            out.append(Step(name, "coming", "Coming next"))
            continue
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
# The window: draws a Form; decides nothing


def window(root) -> dict:
    """Draw the window on ``root`` and return its widgets by name, so a test
    can look at them. Every rule is in the functions above."""
    import tkinter as tk
    from tkinter import filedialog

    form = Form()
    w: Dict[str, object] = {"form": form, "page": "Series", "busy": False, "said": []}
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
        for i, st in enumerate(steps(form)):
            row = tk.Frame(rail, bg=CANVAS)
            row.pack(anchor="w", fill="x", padx=14, pady=5)
            here = st.name == w["page"]
            fg = STONE if st.mark == "coming" else INK
            name = label(row, "%d. %s" % (i + 1, st.name), bold=here, fg=KEY_RED if here else fg, wrap=170)
            name.pack(anchor="w")
            label(row, st.sub, size=11, fg=STONE if st.mark == "coming" else
                  (SLATE if st.mark == "done" else CRIMSON), wrap=170).pack(anchor="w")
            w["step_" + st.name] = name
            if st.mark != "coming":
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
        heading("Settings", "The starting values for the workbook's red Settings tab. You can change them "
                            "there afterwards and the lines move.")
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

    def draw_peers():
        heading("Peers", COMING["Peers"])

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
        if name in COMING:
            return
        w["page"] = name
        clear(page)
        pages[name]()
        draw_rail()

    w["show"] = show
    w["press_run"] = press_run
    show("Series")
    return w


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    window(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
