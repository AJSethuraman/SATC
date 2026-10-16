#!/usr/bin/env python3
"""
gui_check.py - proves the GUI writes settings the engine reads the same way the command line does.

Part A (always runs): the plain functions behind the window.
Part B (runs if tkinter and a display exist, e.g. `xvfb-run python tests/gui_check.py` on Linux):
        drives the real window, and checks its Tests and Models sheets equal the CLI's cell for cell.

Prints ALL PASSED or the failures. Part B reports SKIP, not PASS, when it could not run.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import loan_survival as ls  # noqa: E402
import loan_survival_gui as g  # noqa: E402

FAIL = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


book = ROOT / "sample" / "fake_book.csv"
example = (ROOT / "sample" / "settings_example.ini").read_text()
raw = pd.read_csv(book)

# ---- A1 auto-match finds every role on the sample, and never uses a header twice
m = g.auto_match(list(raw.columns))
check("auto-match: all 8 roles on the sample", len(m) == 8 and len(set(m.values())) == 8, str(len(m)))
alt = g.auto_match(["Loan Number", "Origination Date", "Charge-Off Date", "First 90 DPD Date", "Orig Amount", "Days Past Due"])
check("auto-match: bank-style headers", alt == {"orig_date": "Origination Date", "chargeoff_date": "Charge-Off Date",
                                                 "first_90_date": "First 90 DPD Date", "dpd_asof": "Days Past Due",
                                                 "amount": "Orig Amount", "loan_id": "Loan Number"}, str(alt))
check("auto-match: nothing invented for unrelated headers", g.auto_match(["foo", "bar"]) == {})

# ---- A2 ini round trip: example -> state -> text -> state is the same state
s1 = g.parse_settings_text(example)
s2 = g.parse_settings_text(g.build_settings_text(s1))
check("settings round trip", s1 == s2)
check("round trip keeps all 5 tests", [t["name"] for t in s2["tests"]] == [t["name"] for t in s1["tests"]] and len(s2["tests"]) == 5)

# ---- A3 engine reads the GUI text as the same Settings as the example
a, b = ls.Settings(example), ls.Settings(g.build_settings_text(s1))
same = (a.as_of, a.cols, a.bad_event, a.checkpoints, a.min_at_risk, a.dq_window, a.proxy_min_co_share,
        a.proxy_min_lead, a.horizon, a.tests) == (b.as_of, b.cols, b.bad_event, b.checkpoints, b.min_at_risk,
                                                  b.dq_window, b.proxy_min_co_share, b.proxy_min_lead, b.horizon, b.tests)
check("engine reads GUI text as the example's settings", same)

# ---- A4 model terms
check("model term lower", g.model_term("fico", "50", "lower") == "fico per -50")
check("model term higher", g.model_term("age", "10", "higher") == "age per 10")
check("model term plain", g.model_term("flag", "", "lower") == "flag")
check("model split round trip", g.split_model("fico per -50, flag, age per 10") ==
      [("fico", "50", "lower"), ("flag", "", "higher"), ("age", "10", "higher")])

# ---- A5 seasoned shortcut: as-of minus horizon, end-of-month safe
check("seasoned = as-of minus horizon", g.seasoned_orig_to("2026-09-30", 36) == "2023-09-30")
check("seasoned month-end clamps", g.seasoned_orig_to("2026-03-31", 1) == "2026-02-28")

# ---- A6 column filters
check("numeric columns offered for cutoffs", set(g.numeric_columns(raw)) >= {"fico", "amount", "net_revenue"} and "income_gt_sales" not in g.numeric_columns(raw))
check("category columns respect the 15-value limit", "income_gt_sales" in g.category_columns(raw) and "loan_id" not in g.category_columns(raw))
check("model columns: numeric or Y/N", {"fico", "income_gt_sales", "new_business"} <= set(g.model_columns(raw)) and "loan_id" not in g.model_columns(raw))

# ---- A7 date problems are counted, not hidden
s = pd.Series(["2024-01-05", "not a date", "", None, "2024-02-30"])
check("unparseable dates counted", g.date_problems(s) == (2, 3, 2), str(g.date_problems(s)))

# ---- A8 validation says what to do
bad = g.new_state()
probs = g.validate_state(bad)
check("validation names missing required columns", len(probs) == 2 and all("Columns tab" in p for p in probs), str(probs))
bad["cols"] = {"orig_date": "a", "chargeoff_date": "b"}
bad["settings"]["bad_event"] = "earliest"
check("validation: earliest needs first 90+", any("first 90+" in p for p in g.validate_state(bad)))
bad["as_of"] = "tomorrow-ish"
check("validation: bad as-of", any("as-of" in p for p in g.validate_state(bad)))

# ---- A9 duplicate test names can't break the ini
check("unique names", g.unique_name("vintage", ["Vintage"]) == "vintage 2" and g.unique_name("a]b", []) == "a b")

# ---- A10 errors become words
check("engine error passes through", g.plain_error(ls.UserError("Test column 'x' not found in file.")) == "Test column 'x' not found in file.")
check("permission error is explained", "Excel" in g.plain_error(PermissionError()))

# ---- A11 memory file is best effort
with tempfile.TemporaryDirectory() as tmp:
    mem = Path(tmp) / "m.json"
    g.remember_columns(["a", "b"], {"orig_date": "a"}, mem)
    check("memory remembers by header signature", g.load_memory(mem).get(g.header_signature(["b", "a"])) == {"orig_date": "a"})
    g.remember_columns(["a"], {}, Path(tmp) / "no" / "such" / "dir.json")
    check("memory failure is silent", True)

# ---- A12 a bad test the GUI can build is refused by the engine in words, not a traceback
try:
    st = g.parse_settings_text(example)
    st["tests"] = [{"name": "bad", "spec": {"column": "nope", "cutoffs": "1"}}]
    ls.run(book, g.build_settings_text(st), Path(tempfile.gettempdir()) / "gui_check_bad.xlsx")
    check("engine refuses unknown column", False)
except ls.UserError as e:
    check("engine refuses unknown column in words", "not found" in str(e), str(e))

# ---- B the real window
try:
    import tkinter  # noqa: F401
    have_tk = True
except ImportError:
    have_tk = False
if not have_tk or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")):
    print("[SKIP] window drive: no tkinter or no display (run under xvfb-run); NOT proven by this run")
else:
    with tempfile.TemporaryDirectory() as tmp:
        cli_out, gui_out = Path(tmp) / "cli.xlsx", Path(tmp) / "gui.xlsx"
        r = subprocess.run([sys.executable, str(ROOT / "loan_survival.py"), str(book), "--settings",
                            str(ROOT / "sample" / "settings_example.ini"), "--out", str(cli_out)], capture_output=True, text=True)
        check("CLI run for comparison", r.returncode == 0, r.stderr[-300:])

        root = g.main([str(book)])
        app = root.app
        check("window: columns auto-matched on open", len(app.get_state()["cols"]) == 8)
        check("window: as-of defaults to latest date in file", app.v_asof.get() == f"{g.latest_date(raw, g.auto_match(list(raw.columns))):%Y-%m-%d}", app.v_asof.get())
        check("window: unparseable-date line shown", "read as dates" in app.lbl_dates["orig_date"].cget("text"), app.lbl_dates["orig_date"].cget("text"))
        # Load selections = apply the example, then rebuild every test through the window's own state
        app.apply_state(g.parse_settings_text(example))
        app.v_out.set(str(gui_out))
        app.start_run(wait=True)
        shown = app.status.get("1.0", "end")
        check("window: run finished and says where", gui_out.exists() and "Done." in shown, shown[:200])
        for sheet in ("Tests", "Models"):
            a, b = pd.read_excel(cli_out, sheet_name=sheet), pd.read_excel(gui_out, sheet_name=sheet)
            check(f"GUI {sheet} sheet == CLI {sheet} sheet", a.equals(b) and len(a) > 0, f"{len(a)} rows")
        log = pd.read_excel(gui_out, sheet_name="RunLog")
        check("RunLog records the settings the GUI used", "[test: what drives losses]" in "\n".join(log["value"].fillna("").astype(str)))

        # an unready window says what to do instead of running
        app.v_cols["orig_date"].set("")
        app.start_run(wait=True)
        check("window: missing required column is explained", "Columns tab" in app.status.get("1.0", "end"))
        # a bad file is explained
        app.apply_state(g.parse_settings_text(example))
        app.tests = [{"name": "bad", "spec": {"column": "nope", "cutoffs": "1"}}]
        app.start_run(wait=True)
        check("window: engine error shown in words", "not found" in app.status.get("1.0", "end") and "Traceback" not in app.status.get("1.0", "end"))
        root.destroy()

print("\nALL PASSED" if not FAIL else f"\nFAILED: {FAIL}")
sys.exit(1 if FAIL else 0)
