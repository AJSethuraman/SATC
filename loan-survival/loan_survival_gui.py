#!/usr/bin/env python3
"""
loan_survival_gui.py - the window for loan_survival.py: data, columns, settings, comparisons, run.

The GUI does one thing: it writes the same .ini text the command line reads and hands it to
loan_survival.run(). There is no second engine, and the RunLog records exactly what was chosen.

    pythonw loan_survival_gui.py                 # start empty
    pythonw loan_survival_gui.py "C:\\path\\loans.xlsx"   # what the right-click menu passes as %1

Standard library tkinter plus the engine's own dependencies (pandas, numpy, openpyxl).

Everything above the "window" line is plain functions with no tkinter in them, so tests/gui_check.py
can prove the settings it writes without opening a window.
"""
from __future__ import annotations

import configparser
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import pandas as pd

import loan_survival as ls

HERE = Path(__file__).resolve().parent
MEMORY_FILE = HERE / "loan_survival_gui_memory.json"

# role -> (label, required?)
ROLES = [
    ("orig_date", "Origination date", True),
    ("chargeoff_date", "Charge-off date", True),
    ("first_90_date", "First 90+ days past due date", False),
    ("payoff_date", "Payoff date", False),
    ("dpd_asof", "Days past due at as-of", False),
    ("net_revenue", "Net revenue", False),
    ("amount", "Loan amount", False),
    ("loan_id", "Loan ID", False),
]
DATE_ROLES = ("orig_date", "chargeoff_date", "first_90_date", "payoff_date")
REQUIRED_ROLES = ("orig_date", "chargeoff_date")

DEFAULT_TEXT_SIZE = 12

ALIASES = {
    "orig_date": ["orig_date", "origination_date", "orig_dt", "open_date", "opened", "opened_date", "booking_date",
                  "funded_date", "funding_date", "loan_date", "origination", "date_originated"],
    "chargeoff_date": ["chargeoff_date", "charge_off_date", "chargeoff", "charge_off", "co_date", "charged_off_date",
                       "date_charged_off", "chgoff_date", "chargeoff_dt"],
    "first_90_date": ["first_90_date", "first_90", "first90", "first_90dpd", "first_90_dpd", "first_90_dpd_date",
                      "first_90_plus_date", "date_90dpd", "dpd90_date", "ninety_day_date", "first_90_dt"],
    "payoff_date": ["payoff_date", "paid_off_date", "payoff", "pif_date", "paid_in_full_date", "closed_date",
                    "close_date", "payoff_dt"],
    "dpd_asof": ["dpd_asof", "dpd", "days_past_due", "current_dpd", "dpd_current", "dpd_as_of"],
    "net_revenue": ["net_revenue", "netrev", "net_rev", "revenue_net", "net_income", "net_revenue_after_losses"],
    "amount": ["amount", "orig_amount", "original_amount", "loan_amount", "orig_balance", "original_balance",
               "commitment", "principal"],
    "loan_id": ["loan_id", "loanid", "loan_number", "loan_no", "loan_num", "account", "account_number", "acct",
                "acct_no", "id"],
}

BAD_EVENT_CHOICES = [
    ("auto", "Auto"),
    ("chargeoff", "Charge-off"),
    ("earliest", "First 90+ or charge-off"),
]

DEFAULT_SETTINGS = {
    "bad_event": "auto",
    "checkpoints": "6,12,18,24,36",
    "min_at_risk": "30",
    "dq_window": "12",
    "proxy_min_co_share": "0.60",
    "proxy_min_lead": "3",
    "early_read_horizon": "36",
}
ADVANCED = [
    ("min_at_risk", "Minimum loans at risk"),
    ("dq_window", "Months after first 90+ to watch"),
    ("proxy_min_co_share", "Minimum charge-off share of 90+ loans (Auto)"),
    ("proxy_min_lead", "Minimum lead in months, median (Auto)"),
    ("early_read_horizon", "Early-read horizon (months)"),
]

TEST_KINDS = [
    ("vintage", "Vintage (origination year)"),
    ("split", "Before / after a date"),
    ("cutoffs", "Cutoffs on a number"),
    ("flag", "One column against another (flag)"),
    ("category", "Each value of a column"),
    ("model", "Several columns together (Cox model)"),
]
KIND_LABEL = dict(TEST_KINDS)
# what a comparison produces, one line each, shown under its name in the guide
KIND_OUTPUT = {
    "vintage": "Survival by origination year, compared at the same month on book.",
    "split": "Survival of loans opened before against after a date.",
    "cutoffs": "Survival of loans below against at or above each cutoff on a numeric column.",
    "flag": "Survival where a column is greater than, less than or equal to another column or a number: Yes against No.",
    "category": "Survival for each value of a column.",
    "model": "Hazard ratio for each column alone and together (Cox).",
}
OPERATORS = (">", ">=", "<", "<=", "==", "!=")


# ============================================================================ pure helpers (no window)

def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def auto_match(headers: list[str], learned: dict[str, list[str]] | None = None) -> dict[str, str]:
    """Guess role -> header. Names the person picked before come first, then common names. Each header is used at
    most once; unmatched roles are left out."""
    learned = learned or {}
    by_norm = {}
    for h in headers:
        by_norm.setdefault(norm(h), h)
    used, out = set(), {}
    for role, _label, _req in ROLES:
        for alias in list(learned.get(role, [])) + ALIASES[role]:
            h = by_norm.get(alias)
            if h is not None and h not in used:
                out[role] = h
                used.add(h)
                break
    return out


def sorted_headers(headers) -> list[str]:
    """Alphabetical, ignoring case, for the column lists."""
    return sorted((str(h) for h in headers), key=lambda h: (h.lower(), h))


def filter_matches(values: list[str], query: str) -> list[str]:
    """What the column list shows while you type: names starting with the text first, then names containing it."""
    q = query.strip().lower()
    if not q:
        return list(values)
    starts = [v for v in values if v.lower().startswith(q)]
    inside = [v for v in values if q in v.lower() and not v.lower().startswith(q)]
    return starts + inside


def header_signature(headers: list[str]) -> str:
    return hashlib.sha1("\x1f".join(sorted(str(h) for h in headers)).encode()).hexdigest()


def load_memory(path: Path = MEMORY_FILE) -> dict:
    """What the window remembers between runs: the exact picks for a file layout, the column names you have chosen
    for each role (so the next, differently named file is guessed better), and the text size."""
    mem = {"files": {}, "aliases": {}, "text_size": DEFAULT_TEXT_SIZE}
    try:
        raw = json.loads(path.read_text())
        for k in mem:
            if isinstance(raw.get(k), type(mem[k])):
                mem[k] = raw[k]
    except (OSError, ValueError, AttributeError):
        pass
    return mem


def _save_memory(mem: dict, path: Path) -> None:
    try:
        path.write_text(json.dumps(mem, indent=1))
    except OSError:  # a locked-down folder must never stop a run
        pass


def remember_columns(headers: list[str], cols: dict[str, str], path: Path = MEMORY_FILE) -> None:
    mem = load_memory(path)
    mem["files"][header_signature(headers)] = cols
    for role, header in cols.items():
        names = mem["aliases"].setdefault(role, [])
        if norm(header) and norm(header) not in names and norm(header) not in ALIASES.get(role, []):
            names.append(norm(header))
    _save_memory(mem, path)


def remember_text_size(size: int, path: Path = MEMORY_FILE) -> None:
    mem = load_memory(path)
    mem["text_size"] = int(size)
    _save_memory(mem, path)


def preview_rows(df: pd.DataFrame, n: int = 12) -> tuple[list[str], list[list[str]], list[int]]:
    """The first rows as text for the preview: dates without a time, and each column as wide as its content (in characters)."""
    def cell(v) -> str:
        if pd.isna(v):
            return ""
        return f"{v:%Y-%m-%d}" if isinstance(v, pd.Timestamp) or hasattr(v, "strftime") else str(v)
    head = df.head(n)
    rows = [[cell(v) for v in r] for r in head.itertuples(index=False)]
    widths = []
    for i, c in enumerate(df.columns):
        longest = max([len(str(c))] + [len(r[i]) for r in rows])
        widths.append(max(8, min(longest + 2, 30)))
    return [str(c) for c in df.columns], rows, widths


def date_problems(series: pd.Series) -> tuple[int, int, int]:
    """(values that won't read as a date, filled values, blank values)."""
    parsed = ls.to_dates(series)
    filled = series.notna() & (series.astype(str).str.strip() != "")
    return int((filled & parsed.isna()).sum()), int(filled.sum()), int((~filled).sum())


def date_problem_text(series: pd.Series) -> str:
    bad, filled, blank = date_problems(series)
    if bad:
        return f"{bad:,} of {filled:,} filled values are not dates (those loans are excluded)"
    return f"{filled:,} filled values read as dates, {blank:,} blank"


def latest_date(df: pd.DataFrame, cols: dict[str, str]) -> pd.Timestamp | None:
    best = None
    for role in DATE_ROLES:
        h = cols.get(role)
        if h and h in df.columns:
            m = ls.to_dates(df[h]).max()
            if pd.notna(m) and (best is None or m > best):
                best = m
    return best


def seasoned_orig_to(as_of: str, horizon_months: int) -> str:
    """Loans opened by this date have been observable for at least `horizon_months`."""
    return f"{pd.Timestamp(as_of) - pd.DateOffset(months=int(horizon_months)):%Y-%m-%d}"


def numeric_columns(df: pd.DataFrame) -> list[str]:
    out = []
    for c in df.columns:
        s = df[c].dropna()
        if len(s) and pd.to_numeric(s, errors="coerce").notna().mean() >= 0.9 and s.nunique() > 2:
            out.append(c)
    return out


def category_columns(df: pd.DataFrame, limit: int = 15) -> list[str]:
    """The engine refuses more than 15 values, so do not offer a column it would refuse."""
    return [c for c in df.columns if 2 <= df[c].astype(str).where(df[c].notna(), "(blank)").nunique() <= limit]


def model_columns(df: pd.DataFrame) -> list[str]:
    """Columns the engine can use as model factors, judged by the engine's own reading (numbers, even as text, or Y/N)."""
    out = []
    for c in df.columns:
        s = df[c].dropna()
        if not len(s) or "," in str(c):  # a comma would split the factor list
            continue
        if re.search(r"\s+per\s+-?\d+(\.\d+)?$", str(c), flags=re.IGNORECASE):  # would read as the 'per N' step
            continue
        v = ls.model_values(s)
        if v.notna().mean() >= 0.5 and v.nunique() > 1:  # the engine leaves out loans with no usable value
            out.append(c)
    return out


def spec_kind(spec: dict) -> str:
    if "model" in spec:
        return "model"
    if "group_by" in spec:
        return "vintage"
    if "split_date" in spec:
        return "split"
    if "cutoffs" in spec:
        return "cutoffs"
    return "category"


def model_has_column(terms: list[str], col: str) -> bool:
    """Is this column already one of the model terms? Compares the full column name, which may hold spaces."""
    return any(ls.parse_model_term(t)[0] == col for t in terms)


def model_term(col: str, scale: str, direction: str) -> str:
    """('fico', '50', 'lower') -> 'fico per -50'. No scale means plain per-unit."""
    scale = scale.strip()
    if not scale:
        return col
    n = float(scale)
    if not math.isfinite(n) or n <= 0:
        raise ValueError("The step must be a positive number.")
    plain = f"{n:.10f}".rstrip("0").rstrip(".")
    if plain in ("", "0"):
        raise ValueError("The step must be a positive number.")
    # the engine reads plain decimals only: not 1e2, .5, 50. or +50
    return f"{col} per {'-' if direction == 'lower' else ''}{plain}"


def split_model(model: str) -> list[tuple[str, str, str]]:
    """'fico per -50, flag' -> [('fico','50','lower'), ('flag','','higher')]."""
    out = []
    for term in [t.strip() for t in model.split(",") if t.strip()]:
        col, scale = ls.parse_model_term(term)
        if scale == 1.0 and not re.search(r"\s+per\s+", term, flags=re.IGNORECASE):
            out.append((col, "", "higher"))
        else:
            out.append((col, f"{abs(scale):g}", "lower" if scale < 0 else "higher"))
    return out


def flag_text(left: str, op: str, right: str) -> str:
    """('Income', '>', 'Sales') -> 'Income > Sales', the name the engine works the flag out from."""
    return f"{left.strip()} {op} {right.strip()}"


def parse_flag(text: str, columns) -> tuple[str, str, str] | None:
    """'Income > Sales' -> ('Income', '>', 'Sales') when the left side is a column; None otherwise."""
    cols = set(columns)
    for op in sorted(OPERATORS, key=len, reverse=True):
        at = text.find(op)
        while at >= 0:
            left, right = text[:at].strip(), text[at + len(op):].strip()
            if left in cols and right:
                return left, op, right
            at = text.find(op, at + 1)
    return None


def flag_counts(df: pd.DataFrame, text: str) -> dict[str, int] | None:
    """Yes, No and blank loans for a flag, worked out by the engine's own rule. None when the text is not a flag."""
    values = ls.column_values(df, text)
    if values is None:
        return None
    n = values.value_counts(dropna=False)
    return {"Yes": int(n.get("Yes", 0)), "No": int(n.get("No", 0)), "blank": int(values.isna().sum())}


def example_labels(kind: str, a: str = "", op: str = ">", b: str = "", cuts: str = "", years=(), values=(), terms=()) -> list[str]:
    """The names on the example box's curves or bars: the person's own columns and choices where they have made them."""
    if kind == "vintage":
        return [str(y) for y in years[:4]] or ["Earlier year", "Later year"]
    if kind == "split":
        d = [x.strip() for x in a.split(",") if x.strip()]
        d = d[0] if d else "date"
        return [f"Before {d}", f"{d} on"]
    if kind == "cutoffs":
        c = [x.strip() for x in cuts.split(",") if x.strip()]
        col, c = a or "Column", (c[0] if c else "cutoff")
        return [f"{col} below {c}", f"{col} {c}+"]
    if kind == "flag":
        f = flag_text(a or "Column", op, b or "value")
        return [f"{f} = Yes", f"{f} = No"]
    if kind == "category":
        return [str(v) for v in values[:4]] or ["Value A", "Value B"]
    return list(terms)[:5] or ["Column A", "Column B"]


def default_test_name(kind: str, spec: dict) -> str:
    if kind == "flag":
        return spec["column"]
    if kind == "vintage":
        return "vintage"
    if kind == "split":
        return "before vs after " + spec["split_date"].replace(",", " and ")
    if kind == "cutoffs":
        return f"{spec['column']} cutoffs"
    if kind == "category":
        return spec["column"]
    return "what drives losses"


def describe_window(spec: dict) -> str:
    f, t = spec.get("orig_from"), spec.get("orig_to")
    if f and t:
        text = f"loans opened from {f} to {t}"
    elif t:
        text = f"loans opened up to {t}"
    elif f:
        text = f"loans opened from {f}"
    else:
        text = "all loans"
    if spec.get("where"):
        text = ("loans" if text == "all loans" else text) + f" where {spec['where']}"
    return text


def describe_test(spec: dict) -> str:
    """What a comparison produces, in a line, for the list and the guide."""
    kind = spec_kind(spec)
    if kind == "vintage":
        core = "Survival by origination year"
    elif kind == "split":
        dates = [d.strip() for d in spec["split_date"].split(",") if d.strip()]
        core = "Survival before / after " + " and ".join(dates)
    elif kind == "cutoffs":
        core = f"Survival below / at or above {spec['column']} cutoffs {spec['cutoffs'].replace(',', ', ')}"
    elif kind == "category":
        core = f"Survival for each value of {spec['column']}"
    else:
        words = [f"{c} per {sc} {d}" if sc else c for c, sc, d in split_model(spec["model"])]
        core = "Hazard ratio, alone and together: " + ", ".join(words)
    window = describe_window(spec)
    return core if window == "all loans" else f"{core}; {window}"


def unique_name(name: str, taken: list[str]) -> str:
    name = re.sub(r"[\[\]\r\n]+", " ", name).strip() or "test"
    base, n = name, 2
    while name.lower() in (t.lower() for t in taken):
        name, n = f"{base} {n}", n + 1
    return name


def new_state() -> dict:
    return {"as_of": "", "cols": {}, "settings": dict(DEFAULT_SETTINGS), "tests": []}


def validate_state(state: dict) -> list[str]:
    """Plain-English problems that would stop a run. Empty list = fine to run."""
    problems = []
    for role, label, required in ROLES:
        if required and not state["cols"].get(role):
            problems.append(f"Pick the {label.lower()} column on the Columns tab.")
    used: dict = {}
    for role, label, _req in ROLES:
        h = state["cols"].get(role)
        if h and h in used:
            problems.append(f"'{h}' is picked for both {used[h]} and {label.lower()}. Each role needs its own column.")
        elif h:
            used[h] = label.lower()
    if state["settings"]["bad_event"] == "earliest" and not state["cols"].get("first_90_date"):
        problems.append("'First 90+ or charge-off' needs the first 90+ date column on the Columns tab.")
    if state["as_of"]:
        try:
            pd.Timestamp(state["as_of"])
        except (ValueError, TypeError):
            problems.append("The as-of date is not a date. Write it like 2026-09-30.")
    try:
        [int(x) for x in state["settings"]["checkpoints"].split(",") if x.strip()]
    except ValueError:
        problems.append("Checkpoints should be whole months separated by commas, like 6,12,18,24,36.")
    for key, _label in ADVANCED:
        try:
            float(state["settings"][key])
        except ValueError:
            problems.append(f"Under Advanced, '{key}' should be a number.")
    return problems


def build_settings_text(state: dict) -> str:
    """The .ini the engine reads. Same format as sample/settings_example.ini."""
    lines = ["; Written by loan_survival_gui.py", "", "[data]"]
    lines.append(f"as_of = {state['as_of']}" if state["as_of"] else "; as_of = (latest date in the file)")
    lines += ["", "[columns]"]
    lines += [f"{role:<14} = {state['cols'][role]}" for role, _l, _r in ROLES if state["cols"].get(role)]
    lines += ["", "[settings]"]
    lines += [f"{k:<18} = {state['settings'][k]}" for k in DEFAULT_SETTINGS]
    for t in state["tests"]:
        lines += ["", f"[test: {t['name']}]"]
        lines += [f"{k} = {v}" for k, v in t["spec"].items() if str(v).strip()]
    return "\n".join(lines) + "\n"


def parse_settings_text(text: str) -> dict:
    """Read a saved .ini back into a state, so Load selections shows exactly what a run would use."""
    cp = configparser.ConfigParser(interpolation=None)  # same rules as the engine: comments are whole lines only
    cp.optionxform = str
    cp.read_string(text)
    state = new_state()
    state["as_of"] = cp.get("data", "as_of", fallback="").strip()
    if cp.has_section("columns"):
        state["cols"] = {k: v.strip() for k, v in cp["columns"].items() if v.strip()}
    if cp.has_section("settings"):
        for k in DEFAULT_SETTINGS:
            if k in cp["settings"]:
                state["settings"][k] = cp["settings"][k].strip()
    for sec in cp.sections():
        if sec.lower().startswith("test:"):
            state["tests"].append({"name": sec.split(":", 1)[1].strip(),
                                   "spec": {k: v.strip() for k, v in cp[sec].items()}})
    return state


def plain_error(exc: BaseException) -> str:
    """Words for the person at the keyboard. The engine's own UserError messages are already plain."""
    if isinstance(exc, ls.UserError):
        return str(exc)
    if isinstance(exc, PermissionError):
        return ("Could not save the workbook. If it is open in Excel, close it and run again; "
                "otherwise pick a folder you can write to.")
    if isinstance(exc, FileNotFoundError):
        return f"Could not find the file: {exc.filename or exc}"
    if isinstance(exc, (pd.errors.EmptyDataError, pd.errors.ParserError)):
        return "The file could not be read as a table. Check it is a CSV or Excel file with a header row."
    if isinstance(exc, ValueError) and "Unknown datetime string" in str(exc):
        return "A date could not be read. Check the as-of date is written like 2026-09-30."
    if isinstance(exc, KeyError):
        return f"A column the run needed was not found: {exc}. Check the Columns tab."
    return f"The run stopped unexpectedly ({type(exc).__name__}: {exc}). Nothing was written."


def default_out_path(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + "_survival.xlsx")


def open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606 - local file the person just made
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ============================================================================ the window
#
# One look throughout, the same as PocketBook's launcher: Ink and Key Red on white, Arial, a rail of numbered steps on the
# left, each page laid out the same way (title, a rule, content in a centred column, Back and Next in the bottom corners).
# The guide for a comparison follows the same skeleton. Nothing on a page explains itself; the rules are in README.md.

PALETTE = {"INK": "#0A0908", "KEY_RED": "#CC0000", "CRIMSON": "#960019", "PAPER": "#FFFFFF", "CANVAS": "#F4F1EC",
           "MIST": "#E4DFD5", "STONE": "#B9B4AC", "SLATE": "#57534B", "DISABLED": "#9A958C", "RULE": "#EFEBE4"}
PAGES = (("data", "Data"), ("cols", "Columns"), ("set", "Settings"), ("tests", "Comparisons"), ("run", "Run"))
COLUMN_WIDTH = 900          # the centred column's widest
PAD = 24                    # the one spacing unit pages and the guide are built from
GAP = 12
LABEL_CHARS = 30            # the label column on every form


def window_size(screen_w: int, screen_h: int) -> tuple[int, int]:
    """The first size: as much of the screen as leaves room for the taskbar, 960 x 640 at the least and 1280 x 900 at the most."""
    return max(960, min(1280, screen_w - 120)), max(640, min(900, screen_h - 140))


def main(argv=None) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter import font as tkfont

    C = PALETTE
    root = tk.Tk()
    ui = {"size": int(load_memory().get("text_size", DEFAULT_TEXT_SIZE))}
    BASE = {"title": (20, "bold"), "h2": (20, "bold"), "app": (17, "bold"), "body": (15, "normal"),
            "bold": (15, "bold"), "small": (14, "normal"), "sub": (13, "normal"), "head": (13, "bold"),
            "step": (15, "bold")}
    FONT = {k: tkfont.Font(root=root, family="Arial", size=-v[0], weight=v[1]) for k, v in BASE.items()}

    def px(base: int) -> int:
        return max(9, round(base * ui["size"] / 12))

    def fit_fonts():
        for k, f in FONT.items():
            f.configure(size=-px(BASE[k][0]))

    class Button(tk.Canvas):
        """Rounded, 30 px high: primary is Key Red, secondary is white with a Stone border, disabled is Mist."""

        def __init__(self, master, text, command, kind="secondary"):
            self._text, self._cmd, self._kind = text, command, kind
            super().__init__(master, height=34, width=FONT["bold"].measure(text) + 32, highlightthickness=0, bd=0,
                             bg=master.cget("bg"), cursor="hand2")
            self.bind("<Button-1>", lambda e: self.invoke())
            self._draw()

        def invoke(self):
            if str(self.cget("state")) != "disabled" and self._cmd:
                return self._cmd()

        def configure(self, cnf=None, **kw):
            if "text" in kw:
                self._text = kw.pop("text")
                kw["width"] = FONT["bold"].measure(self._text) + 32
            got = super().configure(cnf, **kw)
            self._draw()
            return got

        config = configure

        def cget(self, key):
            return self._text if key == "text" else super().cget(key)

        def _draw(self):
            if not hasattr(self, "_kind"):
                return
            self.delete("all")
            w, h = int(super().cget("width")), int(super().cget("height"))
            off = str(super().cget("state")) == "disabled"
            fill, line, fg = ((C["MIST"], C["MIST"], C["DISABLED"]) if off else
                              (C["KEY_RED"], C["KEY_RED"], C["PAPER"]) if self._kind == "primary" else
                              (C["PAPER"], C["STONE"], C["INK"]))
            r = 6
            x1, y1, x2, y2 = 1, 1, w - 2, h - 2
            pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2,
                   x1, y2 - r, x1, y1 + r, x1, y1]
            self.create_polygon(pts, smooth=True, fill=fill, outline=line)
            self.create_text(w // 2, h // 2, text=self._text, fill=fg, font=FONT["bold"])

    def label(master, text="", font="body", fg="INK", bg=None, wrap=False, **kw):
        lab = tk.Label(master, text=text, font=FONT[font], fg=C[fg], bg=bg or master.cget("bg"), anchor="w",
                       justify="left", **kw)
        if wrap:
            lab.bind("<Configure>", lambda e: lab.configure(wraplength=max(e.width - 4, 160)))
        return lab

    def field(master, var, width=14):
        return tk.Entry(master, textvariable=var, font=FONT["body"], width=width, relief="solid", bd=1, fg=C["INK"],
                        bg=C["PAPER"], insertbackground=C["INK"], highlightthickness=0)

    def rule(master, color="MIST"):
        return tk.Frame(master, bg=C[color], height=1)

    class Radio(tk.Frame):
        """A radio button, Ink when on: drawn, not the platform's, so it reads the same everywhere."""

        def __init__(self, master, text, var, value, command=None):
            super().__init__(master, bg=master.cget("bg"), cursor="hand2")
            self.var, self.value, self.command, self.enabled = var, value, command, True
            self.dot = tk.Canvas(self, width=20, height=20, highlightthickness=0, bd=0, bg=master.cget("bg"))
            self.dot.pack(side="left")
            self.text = label(self, text, "body", bg=master.cget("bg"))
            self.text.pack(side="left", padx=(6, 0))
            for w in (self, self.dot, self.text):
                w.bind("<Button-1>", self._click)
            self._trace = var.trace_add("write", lambda *_: self.paint())
            self.paint()

        def _click(self, _e):
            if self.enabled:
                self.var.set(self.value)
                if self.command:
                    self.command()

        def set_enabled(self, on: bool):
            self.enabled = on
            self.text.configure(fg=C["INK"] if on else C["DISABLED"])
            self.paint()

        def paint(self):
            try:
                self.dot.delete("all")
            except tk.TclError:
                return
            on = self.var.get() == self.value
            col = C["STONE"] if not self.enabled else (C["INK"] if on else C["STONE"])
            self.dot.create_oval(3, 3, 17, 17, outline=col, width=1.5, fill=col if on else C["PAPER"])
            if on:
                self.dot.create_oval(7, 7, 13, 13, fill=C["PAPER"], outline="")

    class ColumnPicker(tk.Frame):
        """A column chooser you can type into. The list is alphabetical and narrows as you type; click a name or press
        Enter to pick it. An optional picker has an x to clear it."""

        def __init__(self, master, var, on_change=None, optional=False, width=34, allow_text=False):
            super().__init__(master, bg=master.cget("bg"))
            self.var, self.on_change, self.optional, self.allow_text = var, on_change, optional, allow_text
            self.values: list[str] = []
            self.query = tk.StringVar(value=var.get())
            self.entry = field(self, self.query, width)
            self.entry.pack(side="left", fill="x", expand=True, ipady=4)
            self._chip("▾", self.toggle)
            if optional:
                self._chip("✕", self.clear)
            self.popup = None
            self.lb = None
            self._typing = False
            for seq, fn in (("<KeyRelease>", self._typed), ("<Down>", self._down), ("<Up>", self._up), ("<Return>", self._enter),
                            ("<Escape>", lambda _e: self.close_popup()), ("<FocusOut>", self._focus_out),
                            ("<Button-1>", lambda _e: self.show_popup())):
                self.entry.bind(seq, fn)
            var.trace_add("write", self._sync)

        def _chip(self, text, command):
            chip = tk.Label(self, text=text, font=FONT["bold"], fg=C["SLATE"], bg=C["CANVAS"], padx=10, cursor="hand2")
            chip.pack(side="left", fill="y", padx=(4, 0))
            chip.bind("<Button-1>", lambda _e: command())

        def set_values(self, values):
            self.values = sorted_headers(values)

        def matches(self, text: str | None = None) -> list[str]:
            return filter_matches(self.values, self.query.get() if text is None else text)

        def _sync(self, *_):
            if not self._typing and self.query.get() != self.var.get():
                self.query.set(self.var.get())

        def commit(self, value: str):
            self.var.set(value)
            self.query.set(value)
            self.close_popup()
            if self.on_change:
                self.on_change()

        def clear(self):
            self.commit("")

        def toggle(self):
            self.close_popup() if self.popup else (self.entry.focus_set(), self.show_popup(all_values=True))

        def show_popup(self, all_values: bool = False):
            items = self.values if all_values or self.query.get() == self.var.get() else self.matches()
            if not items:
                self.close_popup()
                return
            if self.popup is None:
                self.popup = tk.Toplevel(self)
                self.popup.overrideredirect(True)
                self.lb = tk.Listbox(self.popup, exportselection=False, activestyle="none", font=FONT["body"], relief="solid",
                                     bd=1, highlightthickness=0, selectbackground=C["INK"], selectforeground=C["PAPER"],
                                     bg=C["PAPER"], fg=C["INK"])
                self.lb.pack(side="left", fill="both", expand=True)
                self.lb.bind("<ButtonRelease-1>", lambda _e: self._pick_selected())
            self.lb.delete(0, "end")
            for v in items:
                self.lb.insert("end", v)
            self.lb.configure(height=min(10, len(items)))
            self.update_idletasks()
            x, y = self.entry.winfo_rootx(), self.entry.winfo_rooty() + self.entry.winfo_height()
            self.popup.geometry(f"{max(self.entry.winfo_width(), 280)}x{self.lb.winfo_reqheight()}+{x}+{y}")
            self.popup.lift()

        def close_popup(self):
            if self.popup is not None:
                self.popup.destroy()
                self.popup = self.lb = None

        def _pick_selected(self):
            if self.lb is not None and self.lb.curselection():
                self.commit(self.lb.get(self.lb.curselection()[0]))

        def _typed(self, event):
            if event.keysym in ("Down", "Up", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
                return
            self._typing = True
            try:
                self.show_popup()
            finally:
                self._typing = False

        def _move(self, step):
            if self.lb is None:
                self.show_popup(all_values=not self.query.get())
            if self.lb is None:
                return "break"
            n = self.lb.size()
            cur = self.lb.curselection()
            i = (cur[0] + step) if cur else (0 if step > 0 else n - 1)
            i = max(0, min(n - 1, i))
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(i)
            self.lb.see(i)
            return "break"

        def _down(self, _e):
            return self._move(1)

        def _up(self, _e):
            return self._move(-1)

        def _enter(self, _e):
            if self.lb is not None and self.lb.curselection():
                self._pick_selected()
            else:
                self._settle()
            return "break"

        def _focus_out(self, _e):
            self.after(150, self._settle)

        def _settle(self):
            """Leave the box: take what was typed if it names exactly one column, otherwise go back to the last pick."""
            if not self.winfo_exists():
                return
            text = self.query.get().strip()
            self.close_popup()
            if text == self.var.get():
                return
            if not text and self.optional:
                self.commit("")
                return
            if self.allow_text:
                try:
                    float(text)
                    self.commit(text)       # a number typed in place of a column
                    return
                except ValueError:
                    pass
            exact = [v for v in self.values if v.lower() == text.lower()]
            found = exact or (self.matches(text) if len(self.matches(text)) == 1 else [])
            if found:
                self.commit(found[0])
            else:
                self.query.set(self.var.get())

    class ExampleBox(tk.Canvas):
        """A drawn example of what the chosen comparison produces, named with the person's own columns. Not their data."""
        W, H = 340, 330
        SHADES = ("SLATE", "KEY_RED", "DISABLED", "INK", "STONE")
        DASHES = (None, None, None, (6, 3), (2, 3))      # a fourth and fifth series differ by dash as well as colour

        def __init__(self, master):
            # white with a thin border, so it sits on the page as a panel instead of a block of colour
            super().__init__(master, width=self.W, height=self.H, bg=C["PAPER"], highlightthickness=1,
                             highlightbackground=C["STONE"], highlightcolor=C["STONE"], bd=0)

        @staticmethod
        def _cut(text: str, n: int = 34) -> str:
            return text if len(text) <= n else text[:n - 1] + "…"

        def show(self, kind: str, labels: list[str]):
            self.delete("all")
            self.create_rectangle(1, 1, self.W - 1, 28, fill=C["CANVAS"], outline="")
            self.create_text(self.W - 12, 15, text="Example, not your data", anchor="e", fill=C["SLATE"], font=FONT["sub"])
            left, right, top = 46, self.W - 18, 46
            rows = max(len(labels), 2)
            bottom = self.H - 40 - 20 * rows
            for k in range(1, 4):
                if kind != "model":
                    y = bottom - (bottom - top) * k / 4
                    self.create_line(left, y, right, y, fill=C["RULE"])
            self.create_line(left, top, left, bottom, fill=C["STONE"])
            self.create_line(left, bottom, right, bottom, fill=C["STONE"])
            if kind == "model":
                self.create_text(12, 15, text="Hazard ratio", anchor="w", fill=C["INK"], font=FONT["sub"])
                self.create_text((left + right) // 2, bottom + 16, text="1.0 = no effect", fill=C["SLATE"], font=FONT["sub"])
                one = left + (right - left) * 0.4
                self.create_line(one, top, one, bottom, fill=C["DISABLED"], dash=(4, 3))
                gap = (bottom - top) / max(len(labels), 1)
                for i, lab in enumerate(labels):
                    hr = (1.8, 0.7, 1.3, 1.1, 2.2)[i % 5]
                    y = top + gap * (i + 0.5)
                    x = left + (right - left) * 0.4 * hr
                    self.create_rectangle(min(one, x), y - 9, max(one, x), y + 9, fill=C[self.SHADES[i % 5]], outline="")
                    self.create_text(left + 6, y - 16, text=self._cut(lab, 40), anchor="w", fill=C["INK"], font=FONT["sub"])
                return
            self.create_text(12, 15, text="Cumulative bad", anchor="w", fill=C["INK"], font=FONT["sub"])
            self.create_text((left + right) // 2, bottom + 16, text="Months on book", fill=C["SLATE"], font=FONT["sub"])
            for i, lab in enumerate(labels[:5]):
                rate = (0.016, 0.027, 0.011, 0.021, 0.014)[i % 5]   # in no order: the example says nothing about which group does worse
                pts = []
                for m in range(0, 37, 3):
                    frac = 1 - math.exp(-rate * m)
                    pts += [left + (right - left) * m / 36, bottom - (bottom - top) * min(frac * 1.6, 1) * 0.95]
                self.create_line(*pts, fill=C[self.SHADES[i % 5]], width=2, smooth=True, dash=self.DASHES[i % 5])
            for i, lab in enumerate(labels[:5]):
                y = bottom + 34 + 20 * i
                self.create_line(left, y, left + 22, y, fill=C[self.SHADES[i % 5]], width=2, dash=self.DASHES[i % 5])
                self.create_text(left + 30, y, text=self._cut(lab), anchor="w", fill=C["INK"], font=FONT["sub"])

    class TestWizard(tk.Toplevel):
        """Add or edit one comparison in three steps. Result is {'name':..., 'spec': {...}} in self.result, or None."""

        STEPS = ("Comparison", "Details", "Loans")

        def __init__(self, app, existing=None, taken=()):
            super().__init__(app.root)
            self.app, self.result, self.taken, self.step = app, None, list(taken), 0
            self.title("Add a comparison" if not existing else "Edit a comparison")
            self.configure(bg=C["PAPER"])
            self.transient(app.root)
            df = app.df
            self.num_cols = sorted_headers(numeric_columns(df)) if df is not None else []
            self.cat_cols = sorted_headers(category_columns(df)) if df is not None else []
            self.mod_cols = sorted_headers(model_columns(df)) if df is not None else []
            spec = existing["spec"] if existing else {}
            self.kind = tk.StringVar(value=spec_kind(spec) if existing else "vintage")
            self.name = tk.StringVar(value=existing["name"] if existing else "")
            self.old_name = existing["name"] if existing else None
            self.var_a, self.var_b, self.var_scale = tk.StringVar(), tk.StringVar(), tk.StringVar()
            self.var_dir = tk.StringVar(value="lower")
            self.orig_from = tk.StringVar(value=spec.get("orig_from", ""))
            self.orig_to = tk.StringVar(value=spec.get("orig_to", ""))
            self.window_choice = tk.StringVar(value="dates" if (spec.get("orig_from") or spec.get("orig_to")) else "")
            self.var_op = tk.StringVar(value=">")
            self.conds: list[str] = [c.strip() for c in spec.get("where", "").split(";") if c.strip()]   # "FICO >= 660", ...
            self.band_col, self.band_from, self.band_to = tk.StringVar(), tk.StringVar(), tk.StringVar()
            self.fl_a, self.fl_op, self.fl_b = tk.StringVar(), tk.StringVar(value=">"), tk.StringVar()   # the flag builder in the model step
            self.terms: list[str] = []
            if existing:
                k = spec_kind(spec)
                if k == "split":
                    self.var_a.set(spec["split_date"])
                elif k in ("cutoffs", "category"):
                    self.var_a.set(spec["column"])
                    self.var_b.set(spec.get("cutoffs", ""))
                    flag = parse_flag(spec["column"], df.columns) if (k == "category" and df is not None and spec["column"] not in df.columns) else None
                    if flag:
                        self.kind.set("flag")
                        self.var_a.set(flag[0])
                        self.var_op.set(flag[1])
                        self.var_b.set(flag[2])
                elif k == "model":
                    self.terms = [model_term(*t) for t in split_model(spec["model"])]

            outer = tk.Frame(self, bg=C["PAPER"], padx=PAD, pady=PAD)
            outer.pack(fill="both", expand=True)
            self.lbl_step = label(outer, "", "small", fg="SLATE")
            self.lbl_step.pack()
            self.lbl_head = label(outer, "", "h2")
            self.lbl_head.pack(pady=(2, GAP))
            rule(outer).pack(fill="x", pady=(0, GAP))
            bt = tk.Frame(outer, bg=C["PAPER"])
            bt.pack(side="bottom", fill="x", pady=(GAP, 0))
            self.msg = label(outer, "", "small", fg="CRIMSON", wrap=True)
            self.msg.pack(side="bottom", anchor="w", fill="x", pady=(GAP // 2, 0))
            self.summary = label(outer, "", "small", fg="SLATE", wrap=True)
            self.summary.pack(side="bottom", anchor="w", fill="x", pady=(GAP, 0))
            self.body = tk.Frame(outer, bg=C["PAPER"])
            self.body.pack(fill="both", expand=True)
            self.example = ExampleBox(self.body)
            self.example.pack(side="right", anchor="n", padx=(PAD, 0))
            self.btn_back = Button(bt, "Back", self.back)
            self.btn_back.pack(side="left")
            self.btn_next = Button(bt, "Next", self.next, "primary")
            self.btn_next.pack(side="right")
            Button(bt, "Cancel", self.destroy).pack(side="right", padx=(0, GAP // 2))
            self.minsize(1040, 700)
            self.show_step()
            self.grab_set()
            self.wait_visibility()

        # ---- navigation
        def show_step(self):
            if getattr(self, "block", None) is not None and self.block.winfo_exists():
                self.block.destroy()
            self.block = tk.Frame(self.body, bg=C["PAPER"])
            self.block.pack(side="left", anchor="n")       # the form is one block; what is inside lines up on the left
            self.lbl_step.config(text=f"{self.step + 1} of 3")
            self.lbl_head.config(text=self.STEPS[self.step])
            self.btn_back.config(state="normal" if self.step else "disabled")
            self.btn_next.config(text="Add" if self.step == 2 else "Next")
            self.msg.config(text="")
            (self.build_question, self.build_details, self.build_loans)[self.step]()
            self.update_summary()
            self.update_idletasks()

        def choose_kind(self, key: str):
            self.kind.set(key)
            self.update_summary()

        def back(self):
            if self.step:
                self.step -= 1
                self.show_step()

        def next(self):
            spec, err = self.build_spec(self.step)
            if err:
                self.msg.config(text=err)
                return
            if self.step < 2:
                self.step += 1
                if self.step == 2 and not self.window_choice.get():
                    self.window_choice.set("seasoned" if self.kind.get() in ("cutoffs", "flag", "category", "model") and self.app.v_asof.get().strip() else "all")
                self.show_step()
            else:
                self.finish()

        def finish(self):
            spec, err = self.build_spec(2)
            if err:
                self.msg.config(text=err)
                return
            k = self.kind.get()
            taken = [t for t in self.taken if t != self.old_name]
            self.result = {"name": unique_name(self.name.get().strip() or default_test_name(k, spec), taken), "spec": spec}
            self.destroy()

        def row(self, text, widget_factory):
            """One form row: the label in the fixed label column, the control beside it. Every form is built from these."""
            r = tk.Frame(self.block, bg=C["PAPER"])
            r.pack(anchor="w", pady=(0, GAP))
            lab = label(r, text, "body", fg="SLATE")
            lab.configure(width=26)
            lab.pack(side="left", anchor="n", pady=4)
            w = widget_factory(r)
            w.pack(side="left", fill="x", expand=True, anchor="w")
            return r

        # ---- step 1
        def build_question(self):
            for key, text in TEST_KINDS:
                Radio(self.block, text, self.kind, key, self.update_summary).pack(anchor="w")
                label(self.block, KIND_OUTPUT[key], "small", fg="SLATE").pack(anchor="w", padx=(26, 0), pady=(0, GAP))

        # ---- step 2
        def build_details(self):
            k, b = self.kind.get(), self.block
            if k == "vintage":
                label(b, "Grouped by origination year.", "body", fg="SLATE").pack(anchor="w")
            elif k == "split":
                def make(r):
                    e = field(r, self.var_a, 26)
                    e.bind("<KeyRelease>", lambda _e: self.update_summary())
                    return e
                self.row("Date (YYYY-MM-DD)", make)
            elif k == "flag":
                self.flag_form(self.var_a, self.var_op, self.var_b, self.on_flag)
                self.lbl_range = label(b, "", "small", fg="SLATE")
                self.lbl_range.pack(anchor="w", pady=(0, GAP))
                self.on_flag()
            elif k in ("cutoffs", "category"):
                def make_pick(r):
                    self.picker = ColumnPicker(r, self.var_a, on_change=self.on_column, width=34)
                    self.picker.set_values(self.num_cols if k == "cutoffs" else self.cat_cols)
                    return self.picker
                self.row("Column", make_pick)
                self.lbl_range = label(b, "", "small", fg="SLATE", wrap=True)
                self.lbl_range.pack(anchor="w", fill="x", pady=(0, GAP))
                if k == "cutoffs":
                    def make(r):
                        e = field(r, self.var_b, 26)
                        e.bind("<KeyRelease>", lambda _e: self.update_summary())
                        return e
                    self.row("Cutoffs (comma separated)", make)
                self.on_column()
            else:
                def make_pick(r):
                    self.picker = ColumnPicker(r, self.var_a, width=28)
                    self.picker.set_values(self.mod_cols)
                    return self.picker
                self.row("Column", make_pick)

                def make_per(r):
                    f = tk.Frame(r, bg=C["PAPER"])
                    field(f, self.var_scale, 8).pack(side="left", ipady=4)
                    Radio(f, "lower", self.var_dir, "lower").pack(side="left", padx=(GAP, 0))
                    Radio(f, "higher", self.var_dir, "higher").pack(side="left", padx=(GAP, 0))
                    Button(f, "Add", self.add_term).pack(side="left", padx=(GAP, 0))
                    return f
                self.row("Per", make_per)
                label(b, "Flag", "bold").pack(anchor="w", pady=(GAP // 2, GAP))
                self.flag_form(self.fl_a, self.fl_op, self.fl_b, self.on_model_flag)
                self.lbl_flag = label(b, "", "small", fg="SLATE")
                self.lbl_flag.pack(anchor="w", pady=(0, GAP // 2))
                Button(b, "Add flag", self.add_flag_term).pack(anchor="w", pady=(0, GAP))
                self.lb = tk.Listbox(b, height=4, font=FONT["body"], relief="solid", bd=1, highlightthickness=0,
                                     selectbackground=C["INK"], selectforeground=C["PAPER"], activestyle="none")
                self.lb.pack(fill="x")
                for t in self.terms:
                    self.lb.insert("end", t)
                Button(b, "Remove", self.del_term).pack(anchor="w", pady=(GAP, 0))

        def flag_form(self, a, op, right, command):
            """Column, operator, then a column or a number: the three rows a flag is built from."""
            def make_a(r):
                pk = ColumnPicker(r, a, on_change=command, width=30)
                pk.set_values(self.num_cols)
                return pk
            self.row("Column", make_a)

            def make_op(r):
                f = tk.Frame(r, bg=C["PAPER"])
                for o in OPERATORS:
                    Radio(f, o, op, o, command).pack(side="left", padx=(0, GAP))
                return f
            self.row("Is", make_op)

            def make_b(r):
                pk = ColumnPicker(r, right, on_change=command, width=30, allow_text=True)
                pk.set_values(self.num_cols)
                return pk
            self.row("Against (column or number)", make_b)

        def _flag_said(self, a, op, right) -> str:
            df = self.app.df
            if df is None or not a.get() or not right.get().strip():
                return ""
            c = flag_counts(df, flag_text(a.get(), op.get(), right.get()))
            return f"Yes {c['Yes']:,}, No {c['No']:,}, blank {c['blank']:,}" if c else "Needs a numeric column against a numeric column or a number."

        def on_flag(self):
            if hasattr(self, "lbl_range") and self.lbl_range.winfo_exists():
                self.lbl_range.config(text=self._flag_said(self.var_a, self.var_op, self.var_b))
            self.update_summary()

        def on_model_flag(self):
            if hasattr(self, "lbl_flag") and self.lbl_flag.winfo_exists():
                self.lbl_flag.config(text=self._flag_said(self.fl_a, self.fl_op, self.fl_b))

        def add_flag_term(self):
            a, c = self.fl_a.get(), self.fl_b.get().strip()
            if not a or not c:
                self.msg.config(text="Pick a column and what to compare it against.")
                return
            text = flag_text(a, self.fl_op.get(), c)
            if self.app.df is not None and flag_counts(self.app.df, text) is None:
                self.msg.config(text="Needs a numeric column against a numeric column or a number.")
                return
            if text in self.terms:
                self.msg.config(text="That flag is already added.")
                return
            self.msg.config(text="")
            self.terms.append(text)
            self.lb.insert("end", text)
            for v in (self.fl_a, self.fl_b):
                v.set("")
            self.lbl_flag.config(text="")
            self.update_summary()

        def on_column(self):
            col = self.var_a.get()
            if not hasattr(self, "lbl_range") or not self.lbl_range.winfo_exists():
                return
            text, df = "", self.app.df
            if col and df is not None and col in df.columns:
                if self.kind.get() == "cutoffs":
                    v = pd.to_numeric(df[col], errors="coerce").dropna()
                    if len(v):
                        text = f"{v.min():g} to {v.max():g}, median {v.median():g}"
                else:
                    text = "Values: " + ", ".join(sorted(df[col].dropna().astype(str).unique())[:15])
            self.lbl_range.config(text=text)
            self.update_summary()

        def add_term(self):
            if not self.var_a.get():
                self.msg.config(text="Pick a column.")
                return
            try:
                t = model_term(self.var_a.get(), self.var_scale.get(), self.var_dir.get())
            except ValueError as e:
                self.msg.config(text=str(e) if "positive" in str(e) else "Per must be a number.")
                return
            if model_has_column(self.terms, self.var_a.get()):
                self.msg.config(text="That column is already added.")
                return
            self.msg.config(text="")
            self.terms.append(t)
            self.lb.insert("end", t)
            self.var_scale.set("")
            self.var_a.set("")
            self.update_summary()

        def del_term(self):
            for i in reversed(self.lb.curselection()):
                self.lb.delete(i)
                del self.terms[i]
            self.update_summary()

        # ---- step 3
        def build_loans(self):
            b = self.block
            horizon = self.app.v_set["early_read_horizon"].get()
            seasoned_to = ""
            try:
                if self.app.v_asof.get().strip():
                    seasoned_to = seasoned_orig_to(self.app.v_asof.get().strip(), int(float(horizon)))
            except (ValueError, TypeError):
                pass
            self.seasoned_to = seasoned_to
            Radio(b, "All loans", self.window_choice, "all", self.update_summary).pack(anchor="w", pady=(0, GAP))
            seasoned = Radio(b, f"Seasoned: opened by {seasoned_to}" if seasoned_to else "Seasoned", self.window_choice,
                             "seasoned", self.update_summary)
            seasoned.pack(anchor="w", pady=(0, GAP))
            seasoned.set_enabled(bool(seasoned_to))
            dates = tk.Frame(b, bg=C["PAPER"])
            dates.pack(anchor="w", pady=(0, GAP))
            Radio(dates, "Opened from", self.window_choice, "dates", self.update_summary).pack(side="left")
            e1 = field(dates, self.orig_from, 12)
            e1.pack(side="left", padx=(GAP, 6), ipady=4)
            label(dates, "to", "body", fg="SLATE").pack(side="left")
            e2 = field(dates, self.orig_to, 12)
            e2.pack(side="left", padx=(6, 0), ipady=4)
            for e in (e1, e2):
                e.bind("<KeyRelease>", lambda _e: (self.window_choice.set("dates"), self.update_summary()))
            label(b, "Only loans where", "bold").pack(anchor="w", pady=(GAP // 2, GAP))

            def make_band(r):
                f = tk.Frame(r, bg=C["PAPER"])
                pk = ColumnPicker(f, self.band_col, width=22)
                pk.set_values(self.num_cols)
                pk.pack(side="left")
                label(f, "from", "body", fg="SLATE").pack(side="left", padx=(GAP, 6))
                field(f, self.band_from, 7).pack(side="left", ipady=4)
                label(f, "to", "body", fg="SLATE").pack(side="left", padx=(GAP, 6))
                field(f, self.band_to, 7).pack(side="left", ipady=4)
                Button(f, "Add", self.add_band).pack(side="left", padx=(GAP, 0))
                return f
            self.row("Column", make_band)
            self.lb_conds = tk.Listbox(b, height=3, font=FONT["body"], relief="solid", bd=1, highlightthickness=0,
                                       selectbackground=C["INK"], selectforeground=C["PAPER"], activestyle="none")
            self.lb_conds.pack(fill="x")
            for c in self.conds:
                self.lb_conds.insert("end", c)
            Button(b, "Remove", self.del_band).pack(anchor="w", pady=(GAP // 2, GAP))
            self.row("Name", lambda r: field(r, self.name, 40))

        def add_band(self):
            col = self.band_col.get()
            if not col:
                self.msg.config(text="Pick a column.")
                return
            added = []
            for op, var in ((">=", self.band_from), ("<=", self.band_to)):
                v = var.get().strip()
                if not v:
                    continue
                try:
                    v = f"{float(v):g}"
                except ValueError:
                    self.msg.config(text="From and to must be numbers.")
                    return
                text = flag_text(col, op, v)
                if self.app.df is not None and flag_counts(self.app.df, text) is None:
                    self.msg.config(text="Needs a numeric column.")
                    return
                added.append(text)
            if not added:
                self.msg.config(text="Enter a from, a to, or both.")
                return
            self.msg.config(text="")
            for text in added:
                if text not in self.conds:
                    self.conds.append(text)
                    self.lb_conds.insert("end", text)
            for v in (self.band_col, self.band_from, self.band_to):
                v.set("")
            self.update_summary()

        def del_band(self):
            for i in reversed(self.lb_conds.curselection()):
                self.lb_conds.delete(i)
                del self.conds[i]
            self.update_summary()

        # ---- what the choices add up to
        def build_spec(self, upto: int):
            """(spec, error). Checks each step up to `upto`."""
            k = self.kind.get()
            spec: dict = {}
            if upto >= 1:
                if k == "vintage":
                    spec["group_by"] = "year"
                elif k == "split":
                    try:
                        cuts = [x.strip() for x in self.var_a.get().split(",") if x.strip()]
                        [pd.Timestamp(x) for x in cuts]
                    except (ValueError, TypeError):
                        cuts = []
                    if not cuts:
                        return spec, "Enter a date as YYYY-MM-DD."
                    spec["split_date"] = ", ".join(cuts)
                elif k == "cutoffs":
                    try:
                        cuts = [float(x) for x in self.var_b.get().split(",") if x.strip()]
                    except ValueError:
                        cuts = []
                    if not self.var_a.get() or not cuts:
                        return spec, "Pick a column and enter at least one cutoff."
                    spec["column"], spec["cutoffs"] = self.var_a.get(), self.var_b.get().replace(" ", "")
                elif k == "flag":
                    a, c = self.var_a.get(), self.var_b.get().strip()
                    if not a or not c:
                        return spec, "Pick a column and what to compare it against."
                    text = flag_text(a, self.var_op.get(), c)
                    if self.app.df is not None and flag_counts(self.app.df, text) is None:
                        return spec, "Needs a numeric column against a numeric column or a number."
                    spec["column"] = text
                elif k == "category":
                    if not self.var_a.get():
                        return spec, "Pick a column."
                    spec["column"] = self.var_a.get()
                else:
                    if not self.terms:
                        return spec, "Add at least one column."
                    spec["model"] = ", ".join(self.terms)
            if upto >= 2:
                choice = self.window_choice.get() or "all"
                if choice == "seasoned" and getattr(self, "seasoned_to", ""):
                    spec["orig_to"] = self.seasoned_to
                elif choice == "dates":
                    for key, var in (("orig_from", self.orig_from), ("orig_to", self.orig_to)):
                        v = var.get().strip()
                        if v:
                            try:
                                pd.Timestamp(v)
                            except (ValueError, TypeError):
                                return spec, f"'{v}' is not a date. Use YYYY-MM-DD."
                            spec[key] = v
                if self.conds:
                    spec["where"] = "; ".join(self.conds)
            return spec, ""

        def update_summary(self):
            if not self.summary.winfo_exists():
                return
            spec, err = self.build_spec(1 if self.step < 2 else 2)
            self.summary.config(text="" if err else describe_test(spec))
            self.refresh_example()

        def refresh_example(self):
            k, df = self.kind.get(), self.app.df
            years, values = [], []
            if df is not None:
                o = self.app.v_cols["orig_date"].get()
                if o and o in df.columns:
                    years = sorted(pd.to_datetime(df[o], errors="coerce", format="mixed").dt.year.dropna().astype(int).unique())[:4]
                col = self.var_a.get()
                if k == "category" and col in df.columns:
                    values = list(df[col].dropna().astype(str).value_counts().index[:4])
            terms = [split_model(t)[0][0] for t in self.terms] if self.terms else []
            self.example.show(k, example_labels(k, self.var_a.get(), self.var_op.get(), self.var_b.get(), self.var_b.get(),
                                                years, values, terms))

    class App:
        def __init__(self, root):
            self.root = root
            root.title("Loan Survival")
            root.geometry("{}x{}".format(*window_size(root.winfo_screenwidth(), root.winfo_screenheight())))
            root.minsize(900, 620)
            root.configure(bg=C["PAPER"])
            self.df: pd.DataFrame | None = None
            self.path: Path | None = None
            self.tests: list[dict] = []
            self.last_out: Path | None = None
            self._asof_auto = ""
            self._busy = False
            self._worker: threading.Thread | None = None
            self._selections_loaded = False  # File > Load selections was used: choosing a file must not reset them
            self._ran = False
            self.current = "data"
            self._visited = {"data"}
            self.v_asof = tk.StringVar()
            self.v_cols = {role: tk.StringVar() for role, _l, _r in ROLES}
            self.v_set = {k: tk.StringVar(value=v) for k, v in DEFAULT_SETTINGS.items()}
            self.v_file = tk.StringVar(value="")
            self.style = ttk.Style(root)
            self.style.theme_use("clam")
            self.text_size = ui["size"]

            menu = tk.Menu(root)
            fm = tk.Menu(menu, tearoff=0)
            fm.add_command(label="Open data file...", command=self.pick_file)
            fm.add_command(label="Save selections...", command=self.save_selections)
            fm.add_command(label="Load selections...", command=self.load_selections)
            fm.add_separator()
            fm.add_command(label="Quit", command=self.close)
            menu.add_cascade(label="File", menu=fm)
            vm = tk.Menu(menu, tearoff=0)
            vm.add_command(label="Larger text   Ctrl +", command=lambda: self.apply_text_size(self.text_size + 1))
            vm.add_command(label="Smaller text   Ctrl -", command=lambda: self.apply_text_size(self.text_size - 1))
            vm.add_command(label="Reset text size   Ctrl 0", command=lambda: self.apply_text_size(DEFAULT_TEXT_SIZE))
            menu.add_cascade(label="View", menu=vm)
            root.config(menu=menu)
            root.protocol("WM_DELETE_WINDOW", self.close)
            for seq, delta in (("<Control-plus>", 1), ("<Control-equal>", 1), ("<Control-minus>", -1)):
                root.bind(seq, lambda _e, d=delta: self.apply_text_size(self.text_size + d))
            root.bind("<Control-0>", lambda _e: self.apply_text_size(DEFAULT_TEXT_SIZE))

            body = tk.Frame(root, bg=C["PAPER"])
            body.pack(fill="both", expand=True)
            self.rail = tk.Frame(body, bg=C["CANVAS"], width=230)
            self.rail.pack(side="left", fill="y")
            self.rail.pack_propagate(False)
            tk.Frame(body, bg=C["MIST"], width=1).pack(side="left", fill="y")
            self.stage = tk.Frame(body, bg=C["PAPER"])
            self.stage.pack(side="left", fill="both", expand=True)
            self.pages = {key: tk.Frame(self.stage, bg=C["PAPER"]) for key, _ in PAGES}
            self.build_data()
            self.build_cols()
            self.build_settings()
            self.build_tests()
            self.build_run()
            self.stage.bind("<Configure>", self._layout)
            self.apply_text_size(self.text_size, save=False)
            self.go("data")

        # ---- the frame
        def _layout(self, _e=None):
            try:
                width = min(COLUMN_WIDTH, max(420, self.stage.winfo_width() - 2 * PAD))
                self.pages[self.current].place_configure(width=width)   # only the page on show: placing a hidden one would show it
            except tk.TclError:
                pass

        def apply_text_size(self, size: int, save: bool = True):
            size = max(9, min(24, int(size)))
            self.text_size = ui["size"] = size
            fit_fonts()
            self.style.configure("Treeview", rowheight=int(px(15) * 1.9), font=FONT["body"], background=C["PAPER"],
                                 fieldbackground=C["PAPER"], foreground=C["INK"], bordercolor=C["MIST"], borderwidth=1)
            self.style.configure("Treeview.Heading", font=FONT["head"], background=C["INK"], foreground=C["PAPER"],
                                 relief="flat", padding=(8, 6))
            self.style.map("Treeview", background=[("selected", C["MIST"])], foreground=[("selected", C["INK"])])
            self.style.map("Treeview.Heading", background=[("active", C["INK"])])
            self.style.configure("Vertical.TScrollbar", background=C["MIST"], troughcolor=C["CANVAS"], bordercolor=C["CANVAS"],
                                 arrowcolor=C["SLATE"])
            self.style.configure("Horizontal.TScrollbar", background=C["MIST"], troughcolor=C["CANVAS"], bordercolor=C["CANVAS"],
                                 arrowcolor=C["SLATE"])
            if save:
                remember_text_size(size)

        def go(self, key: str):
            for k, f in self.pages.items():
                f.place_forget() if k != key else f.place(relx=0.5, rely=0, anchor="n", relheight=1,
                                                        width=min(COLUMN_WIDTH, max(420, self.stage.winfo_width() - 2 * PAD)))
            self.current = key
            self._visited.add(key)
            self.refresh_rail()
            if key == "run":
                self.update_ready()

        def sub(self, key: str) -> tuple[str, str]:
            """(mark, the line under the step's name) for the rail."""
            if key == "data":
                return ("done", f"{len(self.df):,} loans") if self.df is not None else ("todo", "")
            if key == "cols":
                n = sum(1 for v in self.v_cols.values() if v.get())
                ok = all(self.v_cols[r].get() for r in REQUIRED_ROLES)
                return ("done" if ok else "todo", f"{n} set" if n else "")
            if key == "set":
                label_ = dict((k, lbl) for k, lbl, *_ in BAD_EVENT_CHOICES).get(self.v_set["bad_event"].get(), "")
                return ("done" if "set" in self._visited else "todo", label_)
            if key == "tests":
                n = len(self.tests)
                return ("done" if n else "todo", f"{n} added" if n else "")
            if self.path is None:
                return "todo", ""
            return ("done", "Done") if self._ran else ("todo", "")

        def refresh_rail(self):
            for w in self.rail.winfo_children():
                w.destroy()
            label(self.rail, "Loan Survival", "app", bg=C["CANVAS"]).pack(anchor="w", padx=PAD - 6, pady=(PAD, 6))
            tk.Frame(self.rail, bg=C["KEY_RED"], height=3, width=170).pack(anchor="w", padx=PAD - 6, pady=(0, PAD))
            for i, (key, name) in enumerate(PAGES):
                mark, said = self.sub(key)
                current = key == self.current
                row = tk.Frame(self.rail, bg=C["CANVAS"], cursor="hand2")
                row.pack(anchor="w", fill="x", padx=PAD - 8, pady=6)
                m = tk.Canvas(row, width=26, height=26, highlightthickness=0, bd=0, bg=C["CANVAS"])
                m.pack(side="left", anchor="n")
                if current:
                    m.create_oval(1, 1, 25, 25, fill=C["KEY_RED"], outline=C["KEY_RED"])
                    m.create_text(13, 14, text=str(i + 1), fill=C["PAPER"], font=FONT["head"])
                elif mark == "done":
                    m.create_oval(1, 1, 25, 25, fill=C["INK"], outline=C["INK"])
                    m.create_text(13, 14, text="✓", fill=C["PAPER"], font=FONT["head"])
                else:
                    m.create_oval(2, 2, 24, 24, outline=C["STONE"], width=1.5)
                    m.create_text(13, 14, text=str(i + 1), fill=C["STONE"], font=FONT["head"])
                words = tk.Frame(row, bg=C["CANVAS"], cursor="hand2")
                words.pack(side="left", padx=(10, 0))
                name_l = label(words, name, "step", fg="INK" if current or mark == "done" else "STONE", bg=C["CANVAS"])
                name_l.pack(anchor="w")
                parts = [row, m, words, name_l]
                if said:
                    sub_l = label(words, said, "sub", fg="SLATE", bg=C["CANVAS"])
                    sub_l.pack(anchor="w")
                    parts.append(sub_l)
                for w in parts:
                    w.bind("<Button-1>", lambda _e, k=key: self.go(k))
                    w.configure(cursor="hand2")

        def skeleton(self, key: str, title: str, back: str | None, forward: tuple[str, str, object] | None):
            """The one page layout: title, a rule, the content, and Back and Next in the bottom corners."""
            f = self.pages[key]
            f.configure(padx=0, pady=PAD)
            label(f, title, "title").pack()
            rule(f).pack(fill="x", pady=(GAP, PAD))
            foot = tk.Frame(f, bg=C["PAPER"])
            foot.pack(side="bottom", fill="x", pady=(GAP, 0))
            if back:
                Button(foot, "Back", lambda: self.go(back)).pack(side="left")
            if forward:
                text, kind, cmd = forward
                btn = Button(foot, text, cmd, kind)
                btn.pack(side="right")
            else:
                btn = None
            content = tk.Frame(f, bg=C["PAPER"])
            content.pack(fill="both", expand=True)
            return content, foot, btn

        def close(self):
            """Close the window. A run in progress keeps going until the workbook is written, so every Tk object is freed
            here, on the main thread; if a worker thread freed one, Tcl would abort the whole process."""
            import gc
            root = self.root
            try:
                root.destroy()
            except tk.TclError:
                pass
            root.app = None
            self.__dict__.clear()
            del root
            gc.collect()

        # ---- Data
        def build_data(self):
            f, _foot, _btn = self.skeleton("data", "Data", None, ("Next", "primary", lambda: self.go("cols")))
            top = tk.Frame(f, bg=C["PAPER"])
            top.pack(anchor="n")
            Button(top, "Choose file...", self.pick_file, "primary").pack(side="left")
            path = label(top, "", "body", fg="SLATE", textvariable=self.v_file)
            path.configure(wraplength=560)
            path.pack(side="left", padx=(GAP, 0))
            self.lbl_rows = label(f, "", "body", fg="SLATE")
            self.lbl_rows.pack(pady=(GAP, 0))
            r2 = tk.Frame(f, bg=C["PAPER"])
            r2.pack(anchor="n", pady=(GAP, GAP))
            label(r2, "As-of date", "body", fg="SLATE").pack(side="left")
            field(r2, self.v_asof, 14).pack(side="left", padx=(GAP, 0), ipady=4)
            holder = tk.Frame(f, bg=C["PAPER"])
            holder.pack(fill="both", expand=True)
            self.tree = ttk.Treeview(holder, show="headings", height=10)
            sx = ttk.Scrollbar(holder, orient="horizontal", command=self.tree.xview)
            sy = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
            self.tree.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
            sx.pack(side="bottom", fill="x")
            sy.pack(side="right", fill="y")
            self.tree.pack(side="left", fill="both", expand=True)

        # ---- Columns
        def build_cols(self):
            f, foot, _btn = self.skeleton("cols", "Columns", "data", ("Next", "primary", lambda: self.go("set")))
            Button(foot, "Guess again", self.reguess).pack(side="left", padx=(GAP, 0))
            self.pickers, self.lbl_dates = {}, {}
            holder = tk.Frame(f, bg=C["PAPER"])
            holder.pack(fill="both", expand=True)
            canvas = tk.Canvas(holder, highlightthickness=0, borderwidth=0, bg=C["PAPER"])
            bar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=bar.set)
            bar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            inner = tk.Frame(canvas, bg=C["PAPER"])
            win = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

            def wheel(e):
                canvas.yview_scroll(-1 if (e.num == 4 or getattr(e, "delta", 0) > 0) else 1, "units")
            canvas.bind("<Enter>", lambda _e: [canvas.bind_all(s, wheel) for s in ("<MouseWheel>", "<Button-4>", "<Button-5>")])
            canvas.bind("<Leave>", lambda _e: [canvas.unbind_all(s) for s in ("<MouseWheel>", "<Button-4>", "<Button-5>")])
            self.cols_canvas = canvas

            block = tk.Frame(inner, bg=C["PAPER"])
            block.pack(anchor="n")

            def section(title, roles, first):
                label(block, title, "bold").pack(anchor="w", pady=(0 if first else PAD, GAP // 2))
                rule(block).pack(fill="x", pady=(0, GAP))
                for role in roles:
                    text = dict((r, l) for r, l, _q in ROLES)[role]
                    row = tk.Frame(block, bg=C["PAPER"])
                    row.pack(anchor="w", pady=(0, GAP))
                    lab = label(row, text, "body", fg="SLATE")
                    lab.configure(width=LABEL_CHARS // 2 + 4)
                    lab.grid(row=0, column=0, sticky="nw", pady=4, padx=(0, GAP))
                    pk = ColumnPicker(row, self.v_cols[role], on_change=lambda r=role: self.on_map(r), optional=role not in REQUIRED_ROLES, width=34)
                    pk.grid(row=0, column=1, sticky="w")
                    self.pickers[role] = pk
                    lb = label(row, "", "small", fg="SLATE")
                    lb.grid(row=1, column=1, sticky="w", pady=(2, 0))
                    self.lbl_dates[role] = lb
            section("Required", REQUIRED_ROLES, True)
            section("Optional", [r for r, _l, q in ROLES if r not in REQUIRED_ROLES], False)

        # ---- Settings
        def build_settings(self):
            f, _foot, _btn = self.skeleton("set", "Settings", "cols", ("Next", "primary", lambda: self.go("tests")))
            f = tk.Frame(f, bg=C["PAPER"])
            f.pack(anchor="n")
            label(f, "Bad event", "bold").pack(anchor="w", pady=(0, GAP))
            for key, text, *_ in BAD_EVENT_CHOICES:
                Radio(f, text, self.v_set["bad_event"], key, self.refresh_rail).pack(anchor="w", pady=(0, GAP))
            r = tk.Frame(f, bg=C["PAPER"])
            r.pack(anchor="w", pady=(GAP, GAP))
            lab = label(r, "Checkpoints (months on book)", "body", fg="SLATE")
            lab.pack(side="left")
            field(r, self.v_set["checkpoints"], 22).pack(side="left", padx=(GAP, 0), ipady=4)
            self.adv_open = tk.BooleanVar(value=False)
            self.adv_toggle = label(f, "Advanced  ▸", "bold", fg="SLATE")
            self.adv_toggle.pack(anchor="w", pady=(GAP, GAP))
            self.adv_toggle.configure(cursor="hand2")
            self.adv_toggle.bind("<Button-1>", lambda _e: (self.adv_open.set(not self.adv_open.get()), self.toggle_adv()))
            self.adv = tk.Frame(f, bg=C["PAPER"])
            for i, (key, text) in enumerate(ADVANCED):
                field(self.adv, self.v_set[key], 8).grid(row=i, column=0, pady=4, ipady=4, sticky="w")
                label(self.adv, text, "body", fg="SLATE").grid(row=i, column=1, sticky="w", padx=GAP)

        def toggle_adv(self):
            self.adv_toggle.config(text="Advanced  ▾" if self.adv_open.get() else "Advanced  ▸")
            self.adv.pack(anchor="w") if self.adv_open.get() else self.adv.pack_forget()

        # ---- Comparisons
        def build_tests(self):
            f, _foot, _btn = self.skeleton("tests", "Comparisons", "set", ("Next", "primary", lambda: self.go("run")))
            row = tk.Frame(f, bg=C["PAPER"])
            row.pack(anchor="n", pady=(0, GAP))
            Button(row, "Add", self.add_test, "primary").pack(side="left", padx=(0, GAP // 2))
            for text, cmd in (("Edit", self.edit_test), ("Copy", self.dup_test), ("Remove", self.del_test)):
                Button(row, text, cmd).pack(side="left", padx=(0, GAP // 2))
            holder = tk.Frame(f, bg=C["PAPER"])
            holder.pack(fill="both", expand=True)
            self.tt = ttk.Treeview(holder, columns=("name", "what"), show="headings", height=10)
            for c, text, w in (("name", "Name", 220), ("what", "Comparison", 640)):
                self.tt.heading(c, text=text, anchor="center")
                self.tt.column(c, width=w, anchor="center")
            self.tt.column("what", stretch=True)
            self.tt.pack(fill="both", expand=True)
            self.tt.bind("<Double-1>", lambda _e: self.edit_test())

        def refresh_tests(self):
            self.tt.delete(*self.tt.get_children())
            for i, t in enumerate(self.tests):
                self.tt.insert("", "end", iid=str(i), values=(t["name"], describe_test(t["spec"])))
            self.refresh_rail()

        def sel_index(self):
            s = self.tt.selection()
            return int(s[0]) if s else None

        def new_wizard(self, existing=None):
            return TestWizard(self, existing=existing, taken=[t["name"] for t in self.tests])

        def add_test(self):
            if self.df is None:
                messagebox.showinfo("Loan Survival", "Choose a data file first.")
                return
            d = self.new_wizard()
            self.root.wait_window(d)
            if d.result:
                self.tests.append(d.result)
                self.refresh_tests()

        def edit_test(self):
            i = self.sel_index()
            if i is None:
                return
            d = self.new_wizard(existing=self.tests[i])
            self.root.wait_window(d)
            if d.result:
                self.tests[i] = d.result
                self.refresh_tests()

        def dup_test(self):
            i = self.sel_index()
            if i is None:
                return
            t = self.tests[i]
            self.tests.insert(i + 1, {"name": unique_name(t["name"] + " copy", [x["name"] for x in self.tests]), "spec": dict(t["spec"])})
            self.refresh_tests()

        def del_test(self):
            i = self.sel_index()
            if i is not None:
                del self.tests[i]
                self.refresh_tests()

        # ---- Run
        def build_run(self):
            f, foot, self.btn_run = self.skeleton("run", "Run", "tests", ("Run", "primary", self.start_run))
            self.lbl_ready = label(f, "", "bold", wrap=True)
            self.lbl_ready.configure(anchor="center", justify="center")
            self.lbl_ready.pack(fill="x")
            r = tk.Frame(f, bg=C["PAPER"])
            r.pack(fill="x", pady=(GAP, GAP))
            label(r, "Save as", "body", fg="SLATE").pack(side="left")
            self.v_out = tk.StringVar()
            field(r, self.v_out, 20).pack(side="left", fill="x", expand=True, padx=(GAP, GAP), ipady=4)
            Button(r, "Change...", self.pick_out).pack(side="left")
            self.status = tk.Text(f, height=10, wrap="word", state="disabled", font=FONT["body"], relief="solid", bd=1,
                                  highlightthickness=0, bg=C["PAPER"], fg=C["INK"], padx=10, pady=8)
            self.status.pack(fill="both", expand=True)
            r2 = tk.Frame(f, bg=C["PAPER"])
            r2.pack(anchor="n", pady=(GAP, 0))
            self.btn_open = Button(r2, "Open workbook", lambda: open_path(self.last_out))
            self.btn_open.config(state="disabled")
            self.btn_open.pack(side="left", padx=(0, GAP // 2))
            self.btn_folder = Button(r2, "Open folder", lambda: open_path(self.last_out.parent))
            self.btn_folder.config(state="disabled")
            self.btn_folder.pack(side="left")

        def ready_text(self) -> str:
            if self.path is None:
                return "Choose a data file."
            state = self.get_state()
            problems = validate_state(state)
            if problems:
                return "Not ready:\n- " + "\n- ".join(problems)
            n = len(state["tests"])
            return (f"Ready: {len(self.df):,} loans, as of {state['as_of'] or 'the latest date in the file'}, "
                    + (f"{n} comparison{'s' if n != 1 else ''}." if n else "no comparisons added (vintage by default)."))

        def update_ready(self):
            if hasattr(self, "lbl_ready") and self.current == "run":
                self.lbl_ready.config(text=self.ready_text())

        def say(self, text: str, clear: bool = False):
            self.status.config(state="normal")
            if clear:
                self.status.delete("1.0", "end")
            self.status.insert("end", text + "\n")
            self.status.config(state="disabled")

        # ---- data + mapping
        def pick_file(self):
            p = filedialog.askopenfilename(title="Loan file", filetypes=[("Loan files", "*.csv *.xlsx *.xlsm *.xls"), ("All files", "*.*")])
            if p:
                self.load_file(Path(p))

        def load_file(self, path: Path, keep_state: bool | None = None) -> bool:
            keep_state = self._selections_loaded if keep_state is None else keep_state
            try:
                df = ls.load(path)
            except Exception as e:  # noqa: BLE001 - shown to the person in plain words
                messagebox.showerror("Loan Survival", plain_error(e))
                return False
            self.path, self.df = path, df
            self.v_file.set(str(path))
            self.lbl_rows.config(text=f"{len(df):,} rows, {len(df.columns)} columns")
            heads, rows, widths = preview_rows(df)
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = heads
            cw = max(8, int(px(15) * 0.62))
            for c, w in zip(heads, widths):
                self.tree.heading(c, text=c, anchor="center")
                self.tree.column(c, width=w * cw, minwidth=w * cw, stretch=True, anchor="center")
            for r in rows:
                self.tree.insert("", "end", values=r)
            for pk in self.pickers.values():
                pk.set_values(df.columns)
            self.v_out.set(str(default_out_path(path)))
            if not keep_state:
                mem = load_memory()
                remembered = mem["files"].get(header_signature(list(df.columns)))
                self.set_cols(remembered if remembered and all(v in df.columns for v in remembered.values())
                              else auto_match(list(df.columns), mem["aliases"]))
                self.tests = []
                self.refresh_tests()
            for role in self.v_cols:
                self.on_map(role, refresh_asof=False)
            self.refresh_asof()
            self._ran = False
            self.refresh_rail()
            if keep_state:
                missing = [v.get() for v in self.v_cols.values() if v.get() and v.get() not in df.columns]
                if missing:
                    messagebox.showwarning("Loan Survival", "Not in this file: " + ", ".join(missing))
            return True

        def set_cols(self, cols: dict):
            for role, var in self.v_cols.items():
                var.set(cols.get(role, ""))

        def reguess(self):
            if self.df is not None:
                self.set_cols(auto_match(list(self.df.columns), load_memory()["aliases"]))
                for role in self.v_cols:
                    self.on_map(role, refresh_asof=False)
                self.refresh_asof()

        def on_map(self, role: str, refresh_asof: bool = True):
            h = self.v_cols[role].get()
            if role in DATE_ROLES:
                self.lbl_dates[role].config(text=date_problem_text(self.df[h]) if (h and self.df is not None and h in self.df.columns) else "")
            if refresh_asof:
                self.refresh_asof()
            self.refresh_rail()

        def refresh_asof(self):
            if self.df is None:
                return
            m = latest_date(self.df, {r: v.get() for r, v in self.v_cols.items()})
            auto = f"{m:%Y-%m-%d}" if m is not None else ""
            if self.v_asof.get().strip() in ("", self._asof_auto):
                self.v_asof.set(auto)
            self._asof_auto = auto

        # ---- state in/out
        def get_state(self) -> dict:
            return {"as_of": self.v_asof.get().strip(),
                    "cols": {r: v.get() for r, v in self.v_cols.items() if v.get()},
                    "settings": {k: v.get().strip() for k, v in self.v_set.items()},
                    "tests": [{"name": t["name"], "spec": dict(t["spec"])} for t in self.tests]}

        def apply_state(self, state: dict):
            self.v_asof.set(state["as_of"])
            self._asof_auto = ""
            self.set_cols(state["cols"])
            for k, v in state["settings"].items():
                self.v_set[k].set(v)
            self.tests = state["tests"]
            self.refresh_tests()
            for role in self.v_cols:
                self.on_map(role, refresh_asof=False)
            self.refresh_asof()   # a blank as-of in the saved choices means "the file's latest date"
            self._selections_loaded = True

        def save_selections(self):
            p = filedialog.asksaveasfilename(defaultextension=".ini", filetypes=[("Settings", "*.ini")], initialfile="loan_survival_settings.ini")
            if p:
                Path(p).write_text(build_settings_text(self.get_state()))

        def load_selections(self):
            p = filedialog.askopenfilename(filetypes=[("Settings", "*.ini"), ("All files", "*.*")])
            if not p:
                return
            try:
                state = parse_settings_text(Path(p).read_text())
            except (configparser.Error, OSError) as e:
                messagebox.showerror("Loan Survival", f"Could not read the settings file: {e}")
                return
            self.apply_state(state)
            if self.df is not None:
                missing = [v for v in state["cols"].values() if v not in self.df.columns]
                if missing:
                    messagebox.showwarning("Loan Survival", "Not in the current file: " + ", ".join(missing))

        # ---- run
        def pick_out(self):
            p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile=Path(self.v_out.get() or "out.xlsx").name)
            if p:
                self.v_out.set(p)

        def start_run(self, wait: bool = False):
            if self._busy:
                return
            self.go("run")
            if self.path is None:
                self.say("Choose a data file first.", clear=True)
                return
            state = self.get_state()
            problems = validate_state(state)
            if problems:
                self.say("Not ready:\n- " + "\n- ".join(problems), clear=True)
                return
            text = build_settings_text(state)
            out = Path(self.v_out.get() or default_out_path(self.path))
            remember_columns(list(self.df.columns), state["cols"])
            self._busy = True
            self.btn_run.config(state="disabled")
            self.btn_open.config(state="disabled")
            self.btn_folder.config(state="disabled")
            self.say("Running...", clear=True)
            box: dict = {}

            src = self.path  # plain values only: if the window closes mid-run, the worker must not be the one to free Tk objects

            def work():
                try:
                    box["r"] = ls.run(src, text, out, settings_label="(chosen in loan_survival_gui.py)")
                except BaseException as e:  # noqa: BLE001 - everything is turned into words for the screen
                    box["e"] = e

            # not a daemon: closing the window must not cut the workbook off mid-write; the process waits for it
            th = threading.Thread(target=work, daemon=False)
            self._worker = th
            th.start()

            def poll():
                if th.is_alive():
                    self.root.after(150, poll)
                else:
                    self.finish_run(box)

            if wait:
                th.join()
                self.finish_run(box)
            else:
                self.root.after(150, poll)

        def finish_run(self, box: dict):
            self._busy = False
            self.btn_run.config(state="normal")
            if "e" in box:
                self.say("The run did not finish.\n\n" + plain_error(box["e"]), clear=True)
                return
            r = box["r"]
            self.last_out = r["out"]
            self._ran = True
            lines = [f"Done. {r['out']}", "", f"As-of {r['as_of']:%Y-%m-%d}. Rows used {r['rows_used']:,} of {r['rows_read']:,}; excluded {r['rows_excluded']:,} (Excluded sheet).",
                     f"Bad event used: {r['bad_event']}", f"{r['verdict']}"]
            self.say("\n".join(lines), clear=True)
            self.btn_open.config(state="normal")
            self.btn_folder.config(state="normal")
            self.refresh_rail()

    app = App(root)
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        app.load_file(Path(argv[0]))
    root.app = app  # lets tests/gui_check.py drive the same window
    return root


if __name__ == "__main__":
    main().mainloop()
