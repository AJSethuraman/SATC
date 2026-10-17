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

# role -> (label, required?, hint)
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


# ============================================================================ pure helpers (no window)

def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def auto_match(headers: list[str]) -> dict[str, str]:
    """Guess role -> header from common names. Each header is used at most once; unmatched roles are left out."""
    by_norm = {}
    for h in headers:
        by_norm.setdefault(norm(h), h)
    used, out = set(), {}
    for role, _label, _req in ROLES:
        for alias in ALIASES[role]:
            h = by_norm.get(alias)
            if h is not None and h not in used:
                out[role] = h
                used.add(h)
                break
    return out


def header_signature(headers: list[str]) -> str:
    return hashlib.sha1("\x1f".join(sorted(str(h) for h in headers)).encode()).hexdigest()


def load_memory(path: Path = MEMORY_FILE) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def remember_columns(headers: list[str], cols: dict[str, str], path: Path = MEMORY_FILE) -> None:
    """Best effort: a locked-down folder must never stop a run."""
    try:
        mem = load_memory(path)
        mem[header_signature(headers)] = cols
        path.write_text(json.dumps(mem, indent=1))
    except OSError:
        pass


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

    class TestDialog(tk.Toplevel):
        """Add / Edit one test. Result is {'name':..., 'spec': {...}} in self.result, or None."""

        def __init__(self, app, existing=None, taken=()):
            super().__init__(app.root)
            self.app, self.result, self.taken = app, None, list(taken)
            self.title("Test")
            self.transient(app.root)
            self.resizable(False, False)
            df = app.df
            self.num_cols = numeric_columns(df) if df is not None else []
            self.cat_cols = category_columns(df) if df is not None else []
            self.mod_cols = model_columns(df) if df is not None else []

            spec = existing["spec"] if existing else {}
            self.kind = tk.StringVar(value=KIND_LABEL[spec_kind(spec)] if existing else KIND_LABEL["vintage"])
            self.name = tk.StringVar(value=existing["name"] if existing else "")
            self.old_name = existing["name"] if existing else None
            self.var_a, self.var_b, self.var_scale = tk.StringVar(), tk.StringVar(), tk.StringVar()
            self.var_dir = tk.StringVar(value="lower")
            self.orig_from = tk.StringVar(value=spec.get("orig_from", ""))
            self.orig_to = tk.StringVar(value=spec.get("orig_to", ""))
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

            top = ttk.Frame(self, padding=12)
            top.grid()
            ttk.Label(top, text="Kind of test").grid(row=0, column=0, sticky="w")
            kc = ttk.Combobox(top, textvariable=self.kind, values=[l for _k, l in TEST_KINDS], state="readonly", width=42)
            kc.grid(row=0, column=1, sticky="w", pady=2)
            kc.bind("<<ComboboxSelected>>", lambda _e: self.rebuild())
            ttk.Label(top, text="Name").grid(row=1, column=0, sticky="w")
            ttk.Entry(top, textvariable=self.name, width=45).grid(row=1, column=1, sticky="w", pady=2)
            self.body = ttk.Frame(top)
            self.body.grid(row=2, column=0, columnspan=2, sticky="w", pady=8)
            win = ttk.LabelFrame(top, text="Only loans opened in this window (optional)", padding=8)
            win.grid(row=3, column=0, columnspan=2, sticky="we")
            ttk.Label(win, text="From").grid(row=0, column=0)
            ttk.Entry(win, textvariable=self.orig_from, width=12).grid(row=0, column=1, padx=4)
            ttk.Label(win, text="To").grid(row=0, column=2)
            ttk.Entry(win, textvariable=self.orig_to, width=12).grid(row=0, column=3, padx=4)
            ttk.Button(win, text="Seasoned loans only", command=self.seasoned).grid(row=0, column=4, padx=8)
            ttk.Label(win, text="Dates like 2023-12-31. 'Seasoned' stops the window at as-of minus the early-read horizon,\n"
                                "so every loan in it has had time to go bad.", foreground="#555").grid(
                row=1, column=0, columnspan=5, sticky="w", pady=(4, 0))
            self.msg = ttk.Label(top, foreground="#a00", wraplength=520)
            self.msg.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
            bt = ttk.Frame(top)
            bt.grid(row=5, column=0, columnspan=2, sticky="e", pady=(8, 0))
            ttk.Button(bt, text="OK", command=self.ok).pack(side="left", padx=4)
            ttk.Button(bt, text="Cancel", command=self.destroy).pack(side="left")
            self.rebuild()
            self.grab_set()
            self.wait_visibility()

        def kind_key(self) -> str:
            return next(k for k, l in TEST_KINDS if l == self.kind.get())

        def rebuild(self):
            for w in self.body.winfo_children():
                w.destroy()
            k, b = self.kind_key(), self.body
            if k == "vintage":
                ttk.Label(b, text="Groups loans by the year they were opened and compares them at the same month on book.",
                          wraplength=520).grid(sticky="w")
            elif k == "split":
                ttk.Label(b, text="Split date(s), like 2024-01-01 (several allowed, separated by commas)").grid(sticky="w")
                ttk.Entry(b, textvariable=self.var_a, width=30).grid(sticky="w")
            elif k == "cutoffs":
                ttk.Label(b, text="Number column (numbers only)").grid(row=0, column=0, sticky="w")
                ttk.Combobox(b, textvariable=self.var_a, values=self.num_cols, state="readonly", width=28).grid(row=0, column=1, sticky="w")
                ttk.Label(b, text="Cutoffs, like 640,660,680").grid(row=1, column=0, sticky="w")
                ttk.Entry(b, textvariable=self.var_b, width=30).grid(row=1, column=1, sticky="w")
            elif k == "category":
                ttk.Label(b, text="Column (15 values or fewer)").grid(row=0, column=0, sticky="w")
                ttk.Combobox(b, textvariable=self.var_a, values=self.cat_cols, state="readonly", width=28).grid(row=0, column=1, sticky="w")
            else:
                ttk.Label(b, text="Add each factor. 'Step' says how big a change the hazard ratio is for\n"
                                  "(for FICO: step 50, lower = ratio per 50 points lower).").grid(row=0, column=0, columnspan=5, sticky="w")
                ttk.Combobox(b, textvariable=self.var_a, values=self.mod_cols, state="readonly", width=20).grid(row=1, column=0)
                ttk.Label(b, text="Step").grid(row=1, column=1)
                ttk.Entry(b, textvariable=self.var_scale, width=6).grid(row=1, column=2)
                ttk.Combobox(b, textvariable=self.var_dir, values=["lower", "higher"], state="readonly", width=8).grid(row=1, column=3)
                ttk.Button(b, text="Add", command=self.add_term).grid(row=1, column=4, padx=4)
                self.lb = tk.Listbox(b, height=5, width=48)
                self.lb.grid(row=2, column=0, columnspan=4, sticky="w", pady=4)
                ttk.Button(b, text="Remove", command=self.del_term).grid(row=2, column=4, sticky="n")
                for t in self.terms:
                    self.lb.insert("end", t)

        def add_term(self):
            if not self.var_a.get():
                return
            try:
                t = model_term(self.var_a.get(), self.var_scale.get(), self.var_dir.get())
            except ValueError as e:
                self.msg.config(text=str(e) if "positive" in str(e) else "The step must be a number, like 50.")
                return
            if model_has_column(self.terms, self.var_a.get()):
                self.msg.config(text="That factor is already in the list.")
                return
            self.msg.config(text="")
            self.terms.append(t)
            self.lb.insert("end", t)
            self.var_scale.set("")

        def del_term(self):
            for i in reversed(self.lb.curselection()):
                self.lb.delete(i)
                del self.terms[i]

        def seasoned(self):
            as_of = self.app.v_asof.get().strip()
            if not as_of:
                self.msg.config(text="Set the as-of date on the Data tab first.")
                return
            try:
                self.orig_to.set(seasoned_orig_to(as_of, int(float(self.app.v_set["early_read_horizon"].get()))))
                self.msg.config(text="")
            except (ValueError, TypeError):
                self.msg.config(text="The as-of date or the early-read horizon is not valid.")

        def ok(self):
            k = self.kind_key()
            spec: dict = {}
            if k == "vintage":
                spec["group_by"] = "year"
            elif k == "split":
                try:
                    cuts = [x.strip() for x in self.var_a.get().split(",") if x.strip()]
                    [pd.Timestamp(x) for x in cuts]
                except (ValueError, TypeError):
                    cuts = []
                if not cuts:
                    self.msg.config(text="Write the split date like 2024-01-01.")
                    return
                spec["split_date"] = ", ".join(cuts)
            elif k == "cutoffs":
                try:
                    cuts = [float(x) for x in self.var_b.get().split(",") if x.strip()]
                except ValueError:
                    cuts = []
                if not self.var_a.get() or not cuts:
                    self.msg.config(text="Pick a number column and write at least one cutoff, like 640,660.")
                    return
                spec["column"], spec["cutoffs"] = self.var_a.get(), self.var_b.get().replace(" ", "")
            elif k == "category":
                if not self.var_a.get():
                    self.msg.config(text="Pick a column.")
                    return
                spec["column"] = self.var_a.get()
            else:
                if len(self.terms) < 1:
                    self.msg.config(text="Add at least one factor.")
                    return
                spec["model"] = ", ".join(self.terms)
            for key, var in (("orig_from", self.orig_from), ("orig_to", self.orig_to)):
                v = var.get().strip()
                if v:
                    try:
                        pd.Timestamp(v)
                    except (ValueError, TypeError):
                        self.msg.config(text=f"'{v}' is not a date. Write it like 2023-12-31.")
                        return
                    spec[key] = v
            taken = [t for t in self.taken if t != self.old_name]
            name = unique_name(self.name.get().strip() or default_test_name(k, spec), taken)
            self.result = {"name": name, "spec": spec}
            self.destroy()

    class App:
        def __init__(self, root):
            self.root = root
            root.title("Loan survival")
            root.geometry("900x640")
            self.df: pd.DataFrame | None = None
            self.path: Path | None = None
            self.tests: list[dict] = []
            self.last_out: Path | None = None
            self._asof_auto = ""
            self._busy = False
            self._worker: threading.Thread | None = None
            self._selections_loaded = False  # File > Load selections was used: choosing a file must not reset them
            self.v_asof = tk.StringVar()
            self.v_cols = {role: tk.StringVar() for role, _l, _r in ROLES}
            self.v_set = {k: tk.StringVar(value=v) for k, v in DEFAULT_SETTINGS.items()}
            self.v_file = tk.StringVar(value="No file chosen")

            menu = tk.Menu(root)
            fm = tk.Menu(menu, tearoff=0)
            fm.add_command(label="Open data file...", command=self.pick_file)
            fm.add_command(label="Save selections...", command=self.save_selections)
            fm.add_command(label="Load selections...", command=self.load_selections)
            fm.add_separator()
            fm.add_command(label="Quit", command=self.close)
            menu.add_cascade(label="File", menu=fm)
            root.config(menu=menu)
            root.protocol("WM_DELETE_WINDOW", self.close)

            self.nb = ttk.Notebook(root)
            self.nb.pack(fill="both", expand=True, padx=8, pady=8)
            self.tab_data, self.tab_cols = ttk.Frame(self.nb, padding=10), ttk.Frame(self.nb, padding=10)
            self.tab_set, self.tab_tests = ttk.Frame(self.nb, padding=10), ttk.Frame(self.nb, padding=10)
            self.tab_run = ttk.Frame(self.nb, padding=10)
            for t, label in ((self.tab_data, "1 Data"), (self.tab_cols, "2 Columns"), (self.tab_set, "3 Settings"),
                             (self.tab_tests, "4 Tests"), (self.tab_run, "5 Run")):
                self.nb.add(t, text=label)
            self.build_data()
            self.build_cols()
            self.build_settings()
            self.build_tests()
            self.build_run()

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
            row = ttk.Frame(f)
            row.pack(fill="x")
            ttk.Button(row, text="Choose file...", command=self.pick_file).pack(side="left")
            ttk.Label(row, textvariable=self.v_file).pack(side="left", padx=10)
            self.lbl_rows = ttk.Label(f, text="")
            self.lbl_rows.pack(anchor="w", pady=6)
            r2 = ttk.Frame(f)
            r2.pack(anchor="w")
            ttk.Label(r2, text="As-of date").pack(side="left")
            ttk.Entry(r2, textvariable=self.v_asof, width=14).pack(side="left", padx=6)
            ttk.Label(r2, text="Everything after this date is treated as not yet happened. Starts as the latest date in the file.",
                      foreground="#555").pack(side="left")
            self.tree = ttk.Treeview(f, show="headings", height=14)
            sx = ttk.Scrollbar(f, orient="horizontal", command=self.tree.xview)
            self.tree.configure(xscrollcommand=sx.set)
            self.tree.pack(fill="both", expand=True, pady=(8, 0))
            sx.pack(fill="x")

        # ---- tab 2
        def build_cols(self):
            f = self.tab_cols
            ttk.Label(f, text="Tell the tool which column is which. * = required. Leave the rest blank if you don't have them.",
                      wraplength=800).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
            self.cbs, self.lbl_dates = {}, {}
            for i, (role, label, req) in enumerate(ROLES, start=1):
                ttk.Label(f, text=label + (" *" if req else "")).grid(row=i, column=0, sticky="w", pady=3)
                cb = ttk.Combobox(f, textvariable=self.v_cols[role], values=[""], state="readonly", width=30)
                cb.grid(row=i, column=1, padx=8)
                cb.bind("<<ComboboxSelected>>", lambda _e, r=role: self.on_map(r))
                self.cbs[role] = cb
                lb = ttk.Label(f, text="", foreground="#555", wraplength=420)
                lb.grid(row=i, column=2, sticky="w")
                self.lbl_dates[role] = lb
            ttk.Button(f, text="Guess from names again", command=self.reguess).grid(row=len(ROLES) + 1, column=1, sticky="w", pady=10)

        # ---- tab 3
        def build_settings(self):
            f = self.tab_set
            ttk.Label(f, text="What counts as a bad loan?", font=("", 10, "bold")).pack(anchor="w")
            for key, label, expl in BAD_EVENT_CHOICES:
                ttk.Radiobutton(f, text=label, value=key, variable=self.v_set["bad_event"]).pack(anchor="w", pady=(6, 0))
                ttk.Label(f, text=expl, wraplength=780, foreground="#555").pack(anchor="w", padx=24)
            r = ttk.Frame(f)
            r.pack(anchor="w", pady=14)
            ttk.Label(r, text="Checkpoints (months on book to report)").pack(side="left")
            ttk.Entry(r, textvariable=self.v_set["checkpoints"], width=22).pack(side="left", padx=6)
            self.adv_open = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, text="Advanced (policy thresholds)", variable=self.adv_open, command=self.toggle_adv,
                            style="Toolbutton").pack(anchor="w")
            self.adv = ttk.Frame(f, padding=(20, 6))
            for i, (key, label) in enumerate(ADVANCED):
                ttk.Entry(self.adv, textvariable=self.v_set[key], width=8).grid(row=i, column=0, pady=2)
                ttk.Label(self.adv, text=label).grid(row=i, column=1, sticky="w", padx=8)

        def toggle_adv(self):
            self.adv.pack(anchor="w") if self.adv_open.get() else self.adv.pack_forget()

        # ---- tab 4
        def build_tests(self):
            f = self.tab_tests
            ttk.Label(f, text="Each test compares groups of loans at the same month on book. With none listed, the run does a vintage comparison.",
                      wraplength=800).pack(anchor="w")
            self.tt = ttk.Treeview(f, columns=("name", "kind", "detail"), show="headings", height=12)
            for c, text, w in (("name", "Test", 230), ("kind", "Kind", 150), ("detail", "What it does", 400)):
                self.tt.heading(c, text=text)
                self.tt.column(c, width=w)
            self.tt.pack(fill="both", expand=True, pady=8)
            self.tt.bind("<Double-1>", lambda _e: self.edit_test())
            row = ttk.Frame(f)
            row.pack(anchor="w")
            for text, cmd in (("Add", self.add_test), ("Edit", self.edit_test), ("Duplicate", self.dup_test), ("Remove", self.del_test)):
                ttk.Button(row, text=text, command=cmd).pack(side="left", padx=(0, 6))

        def refresh_tests(self):
            self.tt.delete(*self.tt.get_children())
            for i, t in enumerate(self.tests):
                detail = "; ".join(f"{k} = {v}" for k, v in t["spec"].items())
                self.tt.insert("", "end", iid=str(i), values=(t["name"], KIND_LABEL[spec_kind(t["spec"])].split(" (")[0], detail))

        def sel_index(self):
            s = self.tt.selection()
            return int(s[0]) if s else None

        def add_test(self):
            if self.df is None:
                messagebox.showinfo("Loan survival", "Choose a data file first (tab 1).")
                return
            d = TestDialog(self, taken=[t["name"] for t in self.tests])
            self.root.wait_window(d)
            if d.result:
                self.tests.append(d.result)
                self.refresh_tests()

        def edit_test(self):
            i = self.sel_index()
            if i is None:
                return
            d = TestDialog(self, existing=self.tests[i], taken=[t["name"] for t in self.tests])
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
            ttk.Label(f, text="Workbook will be saved to").pack(anchor="w")
            self.v_out = tk.StringVar()
            r = ttk.Frame(f)
            r.pack(fill="x")
            ttk.Entry(r, textvariable=self.v_out).pack(side="left", fill="x", expand=True)
            ttk.Button(r, text="Change...", command=self.pick_out).pack(side="left", padx=6)
            self.btn_run = ttk.Button(f, text="Run", command=self.start_run)
            self.btn_run.pack(anchor="w", pady=10)
            self.status = tk.Text(f, height=16, wrap="word", state="disabled")
            self.status.pack(fill="both", expand=True)
            r2 = ttk.Frame(f)
            r2.pack(anchor="w", pady=8)
            self.btn_open = ttk.Button(r2, text="Open workbook", command=lambda: open_path(self.last_out), state="disabled")
            self.btn_open.pack(side="left", padx=(0, 6))
            self.btn_folder = ttk.Button(r2, text="Open folder", command=lambda: open_path(self.last_out.parent), state="disabled")
            self.btn_folder.pack(side="left")

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
            self.lbl_rows.config(text=f"{len(df):,} rows, {len(df.columns)} columns. First rows below.")
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = list(df.columns)
            for c in df.columns:
                self.tree.heading(c, text=str(c))
                self.tree.column(c, width=110, stretch=False)
            for _, r in df.head(12).iterrows():
                self.tree.insert("", "end", values=["" if pd.isna(v) else str(v) for v in r])
            heads = [""] + [str(c) for c in df.columns]
            for cb in self.cbs.values():
                cb.config(values=heads)
            self.v_out.set(str(default_out_path(path)))
            if not keep_state:
                remembered = load_memory().get(header_signature(list(df.columns)))
                self.set_cols(remembered if remembered and all(v in df.columns for v in remembered.values()) else auto_match(list(df.columns)))
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
                self.set_cols(auto_match(list(self.df.columns)))
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
