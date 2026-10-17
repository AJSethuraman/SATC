#!/usr/bin/env python3
"""
loan_survival_gui.py - Pop-ups for loan_survival.py. Pick the file, pick the columns, add tests, run.

The GUI does one thing: it writes the same .ini text the command line reads and hands it to
loan_survival.run(). There is no second engine, and the RunLog records exactly what was chosen.

    pythonw loan_survival_gui.py                 # start empty
    pythonw loan_survival_gui.py "C:\\path\\loans.xlsx"   # what the right-click menu passes as %1

Standard library tkinter plus the engine's own dependencies (pandas, numpy, openpyxl). Nothing leaves the machine.

Everything above the "window" line is plain functions with no tkinter in them, so tests/gui_check.py
can prove the settings it writes without opening a window.
"""
from __future__ import annotations

import configparser
import hashlib
import json
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

# What each optional column buys you, in the words the Columns tab shows next to it.
ROLE_HELP = {
    "orig_date": "The date the loan was opened. Loans are compared at the same month after this date.",
    "chargeoff_date": "The date the loan went bad (charged off). Leave a loan's cell blank if it never did.",
    "first_90_date": "Lets the tool check whether 90+ days late is a good early warning for a charge-off.",
    "payoff_date": "Stops following a loan once it is paid off, so paid-off loans are not counted as good forever.",
    "dpd_asof": "Days late today. Splits loans that recovered from loans that are still late.",
    "net_revenue": "With the loan amount, shows revenue per $1,000 lent for each group.",
    "amount": "With net revenue, shows revenue per $1,000 lent for each group.",
    "loan_id": "Lets the tool spot a loan that appears twice.",
}
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
    ("auto", "Let the tool decide",
     "Uses 90+ days past due as the early warning if most 90+ loans end up charged off and it comes well "
     "before the charge-off. Otherwise it counts charge-offs only. The run says which it picked."),
    ("chargeoff", "Charge-off only",
     "A loan is bad only when it is charged off. Slowest to show problems, but nothing to argue about."),
    ("earliest", "First 90+ or charge-off",
     "A loan is bad the first time it is 90+ days past due or charged off, whichever comes first. "
     "Needs the first-90+ date column."),
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
    ("min_at_risk", "Stop showing a month once fewer loans than this are still observed"),
    ("dq_window", "Months after first 90+ to watch for a charge-off"),
    ("proxy_min_co_share", "Auto uses 90+ only if at least this share of 90+ loans charge off (0 to 1)"),
    ("proxy_min_lead", "...and 90+ comes at least this many months earlier (median)"),
    ("early_read_horizon", "Month treated as 'eventual' in the early-read table"),
]

TEST_KINDS = [
    ("vintage", "Vintage (compare origination years)"),
    ("split", "Before / after a date"),
    ("cutoffs", "Cutoffs (backtest a rule on a number)"),
    ("category", "Flag or category (each value)"),
    ("model", "Several factors at once (Cox model)"),
]
KIND_LABEL = dict(TEST_KINDS)

# Step 1 of "Add a comparison": the question first, the method second.
KIND_QUESTIONS = [
    ("vintage", "Did newer loans do better or worse than older ones?",
     "Groups loans by the year they were opened and compares them month by month after opening."),
    ("split", "Did loans opened after a certain date do better or worse?",
     "Good for checking a policy or underwriting change. You pick the date."),
    ("cutoffs", "Would a cutoff on a number have caught the bad loans?",
     "Pick a column of numbers (a score, a ratio, an amount) and try cutoffs. Shows how much worse the flagged loans did, "
     "and how many flagged loans were fine."),
    ("category", "Do loans with different values in one column perform differently?",
     "Pick a column with only a few values, like yes/no or a product type."),
    ("model", "Which columns matter most when you look at them together?",
     "Pick several columns. For each one, the tool shows how much it adds once the others are counted."),
]


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
        return f"{bad:,} of {filled:,} filled values won't read as dates; those loans are left out of the run"
    return f"All {filled:,} filled values read as dates ({blank:,} blank)"


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
    if n <= 0:
        raise ValueError("The step must be a positive number.")
    return f"{col} per {'-' if direction == 'lower' else ''}{scale}"


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


def default_test_name(kind: str, spec: dict) -> str:
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
        return f"loans opened from {f} to {t}"
    if t:
        return f"loans opened up to {t}"
    if f:
        return f"loans opened from {f}"
    return "all loans"


def describe_test(spec: dict) -> str:
    """One plain sentence for a comparison, shown in the list and in the wizard."""
    kind = spec_kind(spec)
    if kind == "vintage":
        core = "Compare loans by the year they were opened"
    elif kind == "split":
        dates = [d.strip() for d in spec["split_date"].split(",") if d.strip()]
        core = f"Compare loans opened before and after {' and '.join(dates)}"
    elif kind == "cutoffs":
        core = (f"Try cutoffs of {spec['cutoffs'].replace(',', ', ')} on {spec['column']}: "
                "loans below each cutoff against loans at or above it")
    elif kind == "category":
        core = f"Compare loans by their value in {spec['column']}"
    else:
        words = [f"{c} (per {sc} {d})" if sc else c for c, sc, d in split_model(spec["model"])]
        core = "Show how much each of these matters, with the others counted: " + ", ".join(words)
    return f"{core}. Uses {describe_window(spec)}."


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
    return f"The run stopped unexpectedly ({type(exc).__name__}: {exc}). Nothing was written. Send this line to whoever maintains the tool."


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

def main(argv=None) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter import font as tkfont

    MUTED = "#555555"

    class ColumnPicker(ttk.Frame):
        """A column chooser you can type into. The list is alphabetical and narrows as you type; click a name or press
        Enter to pick it. An optional picker has an x to clear it."""

        def __init__(self, master, var, on_change=None, optional=False, width=34):
            super().__init__(master)
            self.var, self.on_change, self.optional = var, on_change, optional
            self.values: list[str] = []
            self.query = tk.StringVar(value=var.get())
            self.entry = ttk.Entry(self, textvariable=self.query, width=width)
            self.entry.pack(side="left", fill="x", expand=True)
            ttk.Button(self, text="▾", width=3, command=self.toggle).pack(side="left", padx=(2, 0))
            if optional:
                ttk.Button(self, text="✕", width=3, command=self.clear).pack(side="left", padx=(2, 0))
            self.popup = None
            self.lb = None
            self._typing = False
            for seq, fn in (("<KeyRelease>", self._typed), ("<Down>", self._down), ("<Up>", self._up), ("<Return>", self._enter),
                            ("<Escape>", lambda _e: self.close_popup()), ("<FocusOut>", self._focus_out),
                            ("<Button-1>", lambda _e: self.show_popup())):
                self.entry.bind(seq, fn)
            var.trace_add("write", self._sync)

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
                self.lb = tk.Listbox(self.popup, exportselection=False, activestyle="dotbox")
                sb = ttk.Scrollbar(self.popup, command=self.lb.yview)
                self.lb.configure(yscrollcommand=sb.set)
                self.lb.pack(side="left", fill="both", expand=True)
                sb.pack(side="left", fill="y")
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
            exact = [v for v in self.values if v.lower() == text.lower()]
            found = exact or (self.matches(text) if len(self.matches(text)) == 1 else [])
            if found:
                self.commit(found[0])
            else:
                self.query.set(self.var.get())

    class TestWizard(tk.Toplevel):
        """Add or edit one comparison in three steps: the question, the details, which loans. Result is
        {'name':..., 'spec': {...}} in self.result, or None."""

        STEPS = ("What do you want to find out?", "Fill in the details", "Which loans, and what to call it")

        def __init__(self, app, existing=None, taken=()):
            super().__init__(app.root)
            self.app, self.result, self.taken, self.step = app, None, list(taken), 0
            self.title("Add a comparison")
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
            self.terms: list[str] = []
            if existing:
                k = spec_kind(spec)
                if k == "split":
                    self.var_a.set(spec["split_date"])
                elif k in ("cutoffs", "category"):
                    self.var_a.set(spec["column"])
                    self.var_b.set(spec.get("cutoffs", ""))
                elif k == "model":
                    self.terms = [model_term(*t) for t in split_model(spec["model"])]

            outer = ttk.Frame(self, padding=16)
            outer.pack(fill="both", expand=True)
            self.lbl_step = ttk.Label(outer, font=("", app.text_size, "bold"))
            self.lbl_step.pack(anchor="w")
            self.lbl_head = ttk.Label(outer, font=("", app.text_size + 2, "bold"))
            self.lbl_head.pack(anchor="w", pady=(2, 10))
            self.body = ttk.Frame(outer)
            self.body.pack(fill="both", expand=True)
            self.summary = ttk.Label(outer, wraplength=640, justify="left", foreground=MUTED)
            self.summary.pack(anchor="w", pady=(10, 0), fill="x")
            self.msg = ttk.Label(outer, foreground="#a00", wraplength=640, justify="left")
            self.msg.pack(anchor="w", pady=(6, 0), fill="x")
            bt = ttk.Frame(outer)
            bt.pack(fill="x", pady=(12, 0))
            self.btn_back = ttk.Button(bt, text="← Back", command=self.back)
            self.btn_back.pack(side="left")
            ttk.Button(bt, text="Cancel", command=self.destroy).pack(side="right")
            self.btn_next = ttk.Button(bt, text="Next →", command=self.next)
            self.btn_next.pack(side="right", padx=8)
            self.show_step()
            self.grab_set()
            self.wait_visibility()

        # ---- navigation
        def show_step(self):
            for w in self.body.winfo_children():
                w.destroy()
            self.lbl_step.config(text=f"Step {self.step + 1} of 3")
            self.lbl_head.config(text=self.STEPS[self.step])
            self.btn_back.state(["!disabled"] if self.step else ["disabled"])
            self.btn_next.config(text="Add this comparison" if self.step == 2 else "Next →")
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
                    self.window_choice.set("seasoned" if self.kind.get() in ("cutoffs", "category", "model") and self.app.v_asof.get().strip() else "all")
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

        # ---- step 1: the question
        def build_question(self):
            for key, question, help_ in KIND_QUESTIONS:
                ttk.Radiobutton(self.body, text=question, value=key, variable=self.kind, command=self.update_summary).pack(anchor="w", pady=(8, 0))
                ttk.Label(self.body, text=help_, wraplength=620, justify="left", foreground=MUTED).pack(anchor="w", padx=26)

        # ---- step 2: the details for that question
        def build_details(self):
            k, b = self.kind.get(), self.body
            note = lambda t: ttk.Label(b, text=t, wraplength=620, justify="left", foreground=MUTED)
            if k == "vintage":
                ttk.Label(b, text="Nothing to fill in.", font=("", self.app.text_size, "bold")).pack(anchor="w")
                note("Loans are grouped by the year they were opened. Each year is followed month by month after opening, "
                     "so a young group is never compared with an old one at a later age.").pack(anchor="w", pady=4)
            elif k == "split":
                ttk.Label(b, text="On what date did things change?").pack(anchor="w")
                e = ttk.Entry(b, textvariable=self.var_a, width=34)
                e.pack(anchor="w", pady=4)
                e.bind("<KeyRelease>", lambda _e: self.update_summary())
                note("Write it like 2024-01-01. To check more than one change, put dates side by side with a comma.").pack(anchor="w")
            elif k == "cutoffs":
                ttk.Label(b, text="Which column of numbers?").pack(anchor="w")
                self.picker = ColumnPicker(b, self.var_a, on_change=self.on_column, width=36)
                self.picker.set_values(self.num_cols)
                self.picker.pack(anchor="w", pady=4)
                self.lbl_range = note("")
                self.lbl_range.pack(anchor="w")
                ttk.Label(b, text="Which cutoffs do you want to try?").pack(anchor="w", pady=(10, 0))
                e = ttk.Entry(b, textvariable=self.var_b, width=34)
                e.pack(anchor="w", pady=4)
                e.bind("<KeyRelease>", lambda _e: self.update_summary())
                note("Separate cutoffs with commas, like 10, 20, 30. Each one splits loans into 'below' and 'at or above', "
                     "and the tool shows how each side performed.").pack(anchor="w")
                self.on_column()
            elif k == "category":
                ttk.Label(b, text="Which column?").pack(anchor="w")
                self.picker = ColumnPicker(b, self.var_a, on_change=self.on_column, width=36)
                self.picker.set_values(self.cat_cols)
                self.picker.pack(anchor="w", pady=4)
                self.lbl_range = note("")
                self.lbl_range.pack(anchor="w")
                note("Only columns with 15 different values or fewer are listed.").pack(anchor="w", pady=(6, 0))
                self.on_column()
            else:
                ttk.Label(b, text="Add the columns you want to look at, one at a time.").pack(anchor="w")
                row = ttk.Frame(b)
                row.pack(anchor="w", pady=6)
                self.picker = ColumnPicker(row, self.var_a, width=28)
                self.picker.set_values(self.mod_cols)
                self.picker.grid(row=0, column=0, columnspan=4, sticky="w")
                ttk.Label(row, text="Measure the effect per").grid(row=1, column=0, sticky="w", pady=(6, 0))
                ttk.Entry(row, textvariable=self.var_scale, width=8).grid(row=1, column=1, padx=4, pady=(6, 0))
                ttk.Combobox(row, textvariable=self.var_dir, values=["lower", "higher"], state="readonly", width=8).grid(row=1, column=2, pady=(6, 0))
                ttk.Button(row, text="Add this column", command=self.add_term).grid(row=1, column=3, padx=8, pady=(6, 0))
                note("Leave the 'per' box empty for a yes/no column. For a number, say how big a change to measure: "
                     "'per 50 lower' shows the effect of a value 50 lower, 'per 10 higher' the effect of a value 10 higher.").pack(anchor="w")
                ttk.Label(b, text="Columns in this comparison:").pack(anchor="w", pady=(10, 2))
                self.lb = tk.Listbox(b, height=5, width=56)
                self.lb.pack(anchor="w")
                for t in self.terms:
                    self.lb.insert("end", t)
                ttk.Button(b, text="Remove the selected column", command=self.del_term).pack(anchor="w", pady=4)

        def on_column(self):
            col = self.var_a.get()
            if not hasattr(self, "lbl_range") or not self.lbl_range.winfo_exists():
                return
            text, df = "", self.app.df
            if col and df is not None and col in df.columns:
                if self.kind.get() == "cutoffs":
                    v = pd.to_numeric(df[col], errors="coerce").dropna()
                    if len(v):
                        text = f"Values in {col} run from {v.min():g} to {v.max():g}; the middle value is {v.median():g}."
                else:
                    vals = sorted(df[col].dropna().astype(str).unique())[:15]
                    text = "Values found: " + ", ".join(vals)
            self.lbl_range.config(text=text)
            self.update_summary()

        def add_term(self):
            if not self.var_a.get():
                self.msg.config(text="Pick a column first.")
                return
            try:
                t = model_term(self.var_a.get(), self.var_scale.get(), self.var_dir.get())
            except ValueError as e:
                self.msg.config(text=str(e) if "positive" in str(e) else "The size of change must be a number, like 50.")
                return
            if model_has_column(self.terms, self.var_a.get()):
                self.msg.config(text="That column is already in the list.")
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

        # ---- step 3: which loans, and a name
        def build_loans(self):
            b = self.body
            horizon = self.app.v_set["early_read_horizon"].get()
            seasoned_to = ""
            try:
                if self.app.v_asof.get().strip():
                    seasoned_to = seasoned_orig_to(self.app.v_asof.get().strip(), int(float(horizon)))
            except (ValueError, TypeError):
                pass
            self.seasoned_to = seasoned_to
            ttk.Radiobutton(b, text="All loans", value="all", variable=self.window_choice, command=self.update_summary).pack(anchor="w", pady=(4, 0))
            ttk.Label(b, text="Includes loans opened recently, which have not had time to go bad yet.",
                      foreground=MUTED, wraplength=620, justify="left").pack(anchor="w", padx=26)
            rb = ttk.Radiobutton(b, text=f"Only loans old enough to judge (opened by {seasoned_to or '...'})  — recommended for cutoffs and columns",
                                 value="seasoned", variable=self.window_choice, command=self.update_summary)
            rb.pack(anchor="w", pady=(8, 0))
            if not seasoned_to:
                rb.state(["disabled"])
            ttk.Label(b, text=f"Every loan in this group has had at least {horizon} months to go bad, so recent loans do not make a rule look better than it is.",
                      foreground=MUTED, wraplength=620, justify="left").pack(anchor="w", padx=26)
            ttk.Radiobutton(b, text="I'll choose the dates", value="dates", variable=self.window_choice, command=self.update_summary).pack(anchor="w", pady=(8, 0))
            row = ttk.Frame(b)
            row.pack(anchor="w", padx=26, pady=4)
            ttk.Label(row, text="Opened from").grid(row=0, column=0)
            e1 = ttk.Entry(row, textvariable=self.orig_from, width=12)
            e1.grid(row=0, column=1, padx=6)
            ttk.Label(row, text="to").grid(row=0, column=2)
            e2 = ttk.Entry(row, textvariable=self.orig_to, width=12)
            e2.grid(row=0, column=3, padx=6)
            ttk.Label(row, text="like 2023-12-31, either one can be left empty", foreground=MUTED).grid(row=0, column=4)
            for e in (e1, e2):
                e.bind("<KeyRelease>", lambda _e: (self.window_choice.set("dates"), self.update_summary()))
            ttk.Label(b, text="Name this comparison (optional)").pack(anchor="w", pady=(14, 0))
            ttk.Entry(b, textvariable=self.name, width=44).pack(anchor="w", pady=4)
            ttk.Label(b, text="Leave it empty and the tool picks a name.", foreground=MUTED).pack(anchor="w")

        # ---- what the choices add up to
        def build_spec(self, upto: int):
            """(spec, error). Checks each step up to `upto`; the error is a sentence for the person."""
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
                        return spec, "Write the date like 2024-01-01."
                    spec["split_date"] = ", ".join(cuts)
                elif k == "cutoffs":
                    try:
                        cuts = [float(x) for x in self.var_b.get().split(",") if x.strip()]
                    except ValueError:
                        cuts = []
                    if not self.var_a.get() or not cuts:
                        return spec, "Pick a column of numbers and write at least one cutoff, like 10, 20."
                    spec["column"], spec["cutoffs"] = self.var_a.get(), self.var_b.get().replace(" ", "")
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
                                return spec, f"'{v}' is not a date. Write it like 2023-12-31."
                            spec[key] = v
            return spec, ""

        def update_summary(self):
            if not self.summary.winfo_exists():
                return
            spec, err = self.build_spec(1 if self.step < 2 else 2)
            if err:
                self.summary.config(text="In plain words: (fill in the details above to see it)")
            else:
                self.summary.config(text="In plain words: " + describe_test(spec))

    class App:
        def __init__(self, root):
            self.root = root
            root.title("Loan survival")
            root.geometry("1180x800")
            root.minsize(900, 620)
            self.df: pd.DataFrame | None = None
            self.path: Path | None = None
            self.tests: list[dict] = []
            self.last_out: Path | None = None
            self._asof_auto = ""
            self._busy = False
            self._worker: threading.Thread | None = None
            self._wrappers: list = []
            self._selections_loaded = False  # File > Load selections was used: choosing a file must not reset them
            self.v_asof = tk.StringVar()
            self.v_cols = {role: tk.StringVar() for role, _l, _r in ROLES}
            self.v_set = {k: tk.StringVar(value=v) for k, v in DEFAULT_SETTINGS.items()}
            self.v_file = tk.StringVar(value="No file chosen yet")
            self.style = ttk.Style(root)
            if sys.platform.startswith("linux"):
                self.style.theme_use("clam")
            self.text_size = int(load_memory().get("text_size", DEFAULT_TEXT_SIZE))
            self.apply_text_size(self.text_size, save=False)

            menu = tk.Menu(root)
            fm = tk.Menu(menu, tearoff=0)
            fm.add_command(label="Open data file...", command=self.pick_file)
            fm.add_command(label="Save selections...", command=self.save_selections)
            fm.add_command(label="Load selections...", command=self.load_selections)
            fm.add_separator()
            fm.add_command(label="Quit", command=self.close)
            menu.add_cascade(label="File", menu=fm)
            vm = tk.Menu(menu, tearoff=0)
            vm.add_command(label="Bigger text   Ctrl +", command=lambda: self.apply_text_size(self.text_size + 1))
            vm.add_command(label="Smaller text   Ctrl -", command=lambda: self.apply_text_size(self.text_size - 1))
            vm.add_command(label="Reset text size   Ctrl 0", command=lambda: self.apply_text_size(DEFAULT_TEXT_SIZE))
            menu.add_cascade(label="View", menu=vm)
            root.config(menu=menu)
            root.protocol("WM_DELETE_WINDOW", self.close)
            for seq, delta in (("<Control-plus>", 1), ("<Control-equal>", 1), ("<Control-minus>", -1)):
                root.bind(seq, lambda _e, d=delta: self.apply_text_size(self.text_size + d))
            root.bind("<Control-0>", lambda _e: self.apply_text_size(DEFAULT_TEXT_SIZE))

            self.nb = ttk.Notebook(root)
            self.nb.pack(fill="both", expand=True, padx=10, pady=10)
            self.tab_data, self.tab_cols = ttk.Frame(self.nb, padding=14), ttk.Frame(self.nb, padding=14)
            self.tab_set, self.tab_tests = ttk.Frame(self.nb, padding=14), ttk.Frame(self.nb, padding=14)
            self.tab_run = ttk.Frame(self.nb, padding=14)
            for t, label in ((self.tab_data, "1  Data"), (self.tab_cols, "2  Columns"), (self.tab_set, "3  Settings"),
                             (self.tab_tests, "4  Comparisons"), (self.tab_run, "5  Run")):
                self.nb.add(t, text=label)
            self.build_data()
            self.build_cols()
            self.build_settings()
            self.build_tests()
            self.build_run()
            self.nb.bind("<<NotebookTabChanged>>", lambda _e: self.update_ready())
            root.bind("<Configure>", self._rewrap, add="+")

        # ---- look and feel
        def apply_text_size(self, size: int, save: bool = True):
            size = max(9, min(24, int(size)))
            self.text_size = size
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont", "TkFixedFont"):
                try:
                    tkfont.nametofont(name).configure(size=size)
                except tk.TclError:
                    pass
            self.style.configure("Treeview", rowheight=int(size * 2.2))
            self.style.configure("Treeview.Heading", font=("", size, "bold"))
            self.style.configure("TNotebook.Tab", padding=(size, size // 3))
            if save:
                remember_text_size(size)
            self._rewrap()

        def wrap(self, parent, text="", **kw):
            """A label whose lines re-wrap to the window width."""
            lb = ttk.Label(parent, text=text, justify="left", **kw)
            self._wrappers.append(lb)
            return lb

        def _rewrap(self, _e=None):
            try:
                width = max(360, self.root.winfo_width() - 120)
                for lb in self._wrappers:
                    if lb.winfo_exists():
                        lb.configure(wraplength=width)
            except tk.TclError:
                pass

        def next_button(self, parent, text, target):
            ttk.Button(parent, text=text, command=lambda: self.nb.select(target)).pack(side="bottom", anchor="e", pady=(10, 0))

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

        # ---- tab 1
        def build_data(self):
            f = self.tab_data
            self.next_button(f, "Next: Columns →", self.tab_cols)
            self.wrap(f, "Choose the file with one row per loan (Excel or CSV). Nothing leaves this computer.").pack(anchor="w")
            row = ttk.Frame(f)
            row.pack(fill="x", pady=8)
            ttk.Button(row, text="Choose file...", command=self.pick_file).pack(side="left")
            self.wrap(row, textvariable=self.v_file).pack(side="left", padx=10, fill="x", expand=True)
            self.lbl_rows = ttk.Label(f, text="")
            self.lbl_rows.pack(anchor="w", pady=(0, 6))
            r2 = ttk.Frame(f)
            r2.pack(anchor="w", fill="x")
            ttk.Label(r2, text="As-of date").pack(side="left")
            ttk.Entry(r2, textvariable=self.v_asof, width=14).pack(side="left", padx=8)
            self.wrap(r2, "Anything dated after this is treated as not yet happened. It starts as the latest date in your file.",
                      foreground=MUTED).pack(side="left", fill="x", expand=True)
            holder = ttk.Frame(f)
            holder.pack(fill="both", expand=True, pady=(10, 0))
            self.tree = ttk.Treeview(holder, show="headings", height=10)
            sx = ttk.Scrollbar(holder, orient="horizontal", command=self.tree.xview)
            sy = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
            self.tree.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
            sx.pack(side="bottom", fill="x")
            sy.pack(side="right", fill="y")
            self.tree.pack(side="left", fill="both", expand=True)

        # ---- tab 2
        def build_cols(self):
            f = self.tab_cols
            self.next_button(f, "Next: Settings →", self.tab_set)
            self.wrap(f, "Tell the tool which column is which. Click a box and type part of a name to find it, or press the arrow "
                         "for the whole list (A to Z). The tool remembers the names you pick, so the next file is guessed better.").pack(anchor="w")
            self.pickers, self.lbl_dates = {}, {}
            canvas = tk.Canvas(f, highlightthickness=0, borderwidth=0)
            bar = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=bar.set)
            bar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            inner = ttk.Frame(canvas)
            win = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
            for seq, d in (("<MouseWheel>", None), ("<Button-4>", -1), ("<Button-5>", 1)):
                canvas.bind_all(seq, lambda e, d=d: canvas.yview_scroll(d if d else int(-e.delta / 120), "units") if canvas.winfo_ismapped() else None)
            self.cols_canvas = canvas

            def section(title, roles, hint):
                box = ttk.LabelFrame(inner, text=title, padding=12)
                box.pack(fill="x", pady=(12, 0), padx=(0, 8))
                if hint:
                    self.wrap(box, hint, foreground=MUTED).pack(anchor="w", pady=(0, 6))
                for role in roles:
                    label = dict((r, l) for r, l, _q in ROLES)[role]
                    row = ttk.Frame(box)
                    row.pack(fill="x", pady=(8, 0))
                    ttk.Label(row, text=label, width=24).grid(row=0, column=0, sticky="nw", padx=(0, 12))
                    pk = ColumnPicker(row, self.v_cols[role], on_change=lambda r=role: self.on_map(r), optional=role not in REQUIRED_ROLES, width=34)
                    pk.grid(row=0, column=1, sticky="w")
                    self.pickers[role] = pk
                    ttk.Label(row, text=ROLE_HELP[role], foreground=MUTED, wraplength=640, justify="left").grid(row=1, column=1, sticky="w")
                    lb = self.wrap(row, "", foreground=MUTED)
                    lb.grid(row=2, column=1, sticky="w")
                    self.lbl_dates[role] = lb
            section("Required", REQUIRED_ROLES, "These two are all the tool needs. Everything else only adds detail.")
            section("Optional: leave blank if you do not have them", [r for r, _l, q in ROLES if r not in REQUIRED_ROLES], "")
            f = inner
            ttk.Button(f, text="Guess from names again", command=self.reguess).pack(anchor="w", pady=(12, 0))

        # ---- tab 3
        def build_settings(self):
            f = self.tab_set
            self.next_button(f, "Next: Comparisons →", self.tab_tests)
            ttk.Label(f, text="What counts as a bad loan?", font=("", self.text_size + 1, "bold")).pack(anchor="w")
            for key, label, expl in BAD_EVENT_CHOICES:
                ttk.Radiobutton(f, text=label, value=key, variable=self.v_set["bad_event"]).pack(anchor="w", pady=(10, 0))
                self.wrap(f, expl, foreground=MUTED).pack(anchor="w", padx=28)
            r = ttk.Frame(f)
            r.pack(anchor="w", pady=16)
            ttk.Label(r, text="Months on book to report").pack(side="left")
            ttk.Entry(r, textvariable=self.v_set["checkpoints"], width=22).pack(side="left", padx=8)
            self.wrap(r, "separate with commas", foreground=MUTED).pack(side="left")
            self.adv_open = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, text="Advanced (policy thresholds)", variable=self.adv_open, command=self.toggle_adv,
                            style="Toolbutton").pack(anchor="w")
            self.adv = ttk.Frame(f, padding=(24, 8))
            for i, (key, label) in enumerate(ADVANCED):
                ttk.Entry(self.adv, textvariable=self.v_set[key], width=8).grid(row=i, column=0, pady=3)
                ttk.Label(self.adv, text=label).grid(row=i, column=1, sticky="w", padx=10)

        def toggle_adv(self):
            self.adv.pack(anchor="w") if self.adv_open.get() else self.adv.pack_forget()

        # ---- tab 4
        def build_tests(self):
            f = self.tab_tests
            self.next_button(f, "Next: Run →", self.tab_run)
            self.wrap(f, "A comparison asks one question about your loans. Press Add and the tool walks you through it, step by step. "
                         "With none added, the run compares loans by the year they were opened.").pack(anchor="w")
            row = ttk.Frame(f)
            row.pack(anchor="w", pady=10)
            ttk.Button(row, text="Add a comparison...", command=self.add_test).pack(side="left", padx=(0, 8))
            for text, cmd in (("Edit", self.edit_test), ("Copy", self.dup_test), ("Remove", self.del_test)):
                ttk.Button(row, text=text, command=cmd).pack(side="left", padx=(0, 8))
            holder = ttk.Frame(f)
            holder.pack(fill="both", expand=True)
            self.tt = ttk.Treeview(holder, columns=("name", "plain"), show="headings", height=10)
            for c, text, w in (("name", "Name", 240), ("plain", "What it does", 760)):
                self.tt.heading(c, text=text)
                self.tt.column(c, width=w)
            self.tt.column("plain", stretch=True)
            self.tt.pack(fill="both", expand=True)
            self.tt.bind("<Double-1>", lambda _e: self.edit_test())
            self.tt.bind("<<TreeviewSelect>>", lambda _e: self.show_full())
            self.lbl_full = self.wrap(f, "Click a comparison to read all of it here.", foreground=MUTED)
            self.lbl_full.pack(anchor="w", fill="x", pady=(8, 0))

        def show_full(self):
            i = self.sel_index()
            if hasattr(self, "lbl_full") and i is not None and i < len(self.tests):
                self.lbl_full.config(text=describe_test(self.tests[i]["spec"]))

        def refresh_tests(self):
            self.tt.delete(*self.tt.get_children())
            for i, t in enumerate(self.tests):
                self.tt.insert("", "end", iid=str(i), values=(t["name"], describe_test(t["spec"])))

        def sel_index(self):
            s = self.tt.selection()
            return int(s[0]) if s else None

        def new_wizard(self, existing=None):
            return TestWizard(self, existing=existing, taken=[t["name"] for t in self.tests])

        def add_test(self):
            if self.df is None:
                messagebox.showinfo("Loan survival", "Choose a data file first (tab 1).")
                return
            d = self.new_wizard()
            self.root.wait_window(d)
            if d.result:
                self.tests.append(d.result)
                self.refresh_tests()

        def edit_test(self):
            i = self.sel_index()
            if i is None:
                messagebox.showinfo("Loan survival", "Click a comparison in the list first.")
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

        # ---- tab 5
        def build_run(self):
            f = self.tab_run
            self.lbl_ready = self.wrap(f, "", font=("", self.text_size, "bold"))
            self.lbl_ready.pack(anchor="w")
            ttk.Label(f, text="The workbook will be saved as").pack(anchor="w", pady=(12, 0))
            self.v_out = tk.StringVar()
            r = ttk.Frame(f)
            r.pack(fill="x")
            ttk.Entry(r, textvariable=self.v_out).pack(side="left", fill="x", expand=True)
            ttk.Button(r, text="Change...", command=self.pick_out).pack(side="left", padx=6)
            self.btn_run = ttk.Button(f, text="Run", command=self.start_run)
            self.btn_run.pack(anchor="w", pady=12)
            self.status = tk.Text(f, height=12, wrap="word", state="disabled")
            self.status.pack(fill="both", expand=True)
            r2 = ttk.Frame(f)
            r2.pack(anchor="w", pady=10)
            self.btn_open = ttk.Button(r2, text="Open workbook", command=lambda: open_path(self.last_out), state="disabled")
            self.btn_open.pack(side="left", padx=(0, 8))
            self.btn_folder = ttk.Button(r2, text="Open folder", command=lambda: open_path(self.last_out.parent), state="disabled")
            self.btn_folder.pack(side="left")

        def ready_text(self) -> str:
            if self.path is None:
                return "Not ready: choose a data file on the Data tab."
            state = self.get_state()
            problems = validate_state(state)
            if problems:
                return "Not ready yet:\n- " + "\n- ".join(problems)
            n = len(state["tests"])
            return (f"Ready. {len(self.df):,} loans, as of {state['as_of'] or 'the latest date in the file'}, "
                    f"{n} comparison{'s' if n != 1 else ''}" + ("" if n else " (the run will compare loans by the year they were opened)") + ".")

        def update_ready(self):
            if hasattr(self, "lbl_ready") and self.nb.select() == str(self.tab_run):
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
                messagebox.showerror("Loan survival", plain_error(e))
                return False
            self.path, self.df = path, df
            self.v_file.set(str(path))
            self.lbl_rows.config(text=f"{len(df):,} rows, {len(df.columns)} columns. The first rows are below.")
            heads, rows, widths = preview_rows(df)
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = heads
            cw = max(8, int(self.text_size * 0.9))
            for c, w in zip(heads, widths):
                self.tree.heading(c, text=c)
                self.tree.column(c, width=w * cw, stretch=False)
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
            if keep_state:
                missing = [v.get() for v in self.v_cols.values() if v.get() and v.get() not in df.columns]
                if missing:
                    messagebox.showwarning("Loan survival", "These saved columns are not in this file: " + ", ".join(missing))
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
                messagebox.showerror("Loan survival", f"That settings file could not be read: {e}")
                return
            self.apply_state(state)
            if self.df is not None:
                missing = [v for v in state["cols"].values() if v not in self.df.columns]
                if missing:
                    messagebox.showwarning("Loan survival", "These saved columns are not in the current file: " + ", ".join(missing))

        # ---- run
        def pick_out(self):
            p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile=Path(self.v_out.get() or "out.xlsx").name)
            if p:
                self.v_out.set(p)

        def start_run(self, wait: bool = False):
            if self._busy:
                return
            self.nb.select(self.tab_run)
            if self.path is None:
                self.say("Choose a data file first (tab 1).", clear=True)
                return
            state = self.get_state()
            problems = validate_state(state)
            if problems:
                self.say("Not ready to run:\n- " + "\n- ".join(problems), clear=True)
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
            lines = [f"Done. {r['out']}", "", f"As-of {r['as_of']:%Y-%m-%d}. Rows used {r['rows_used']:,} of {r['rows_read']:,}; left out {r['rows_excluded']:,} (listed on the Excluded sheet).",
                     f"Bad event used: {r['bad_event']}", f"{r['verdict']}"]
            self.say("\n".join(lines), clear=True)
            self.btn_open.config(state="normal")
            self.btn_folder.config(state="normal")

    root = tk.Tk()
    app = App(root)
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        app.load_file(Path(argv[0]))
    root.app = app  # lets tests/gui_check.py drive the same window
    return root


if __name__ == "__main__":
    main().mainloop()
