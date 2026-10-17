#!/usr/bin/env python3
"""
gui_check.py - proves the GUI writes settings the engine reads the same way the command line does.

Part A (always runs): the plain functions behind the window.
Part B (runs if tkinter and a display exist, e.g. `xvfb-run python tests/gui_check.py` on Linux):
        drives the real window, and checks its Tests and Models sheets equal the CLI's cell for cell.

Prints ALL PASSED or the failures. Part B reports SKIP, not PASS, when it could not run.
"""
import gc
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
check("model term: odd number spellings are written the way the engine reads them",
      [g.model_term("s", v, "lower") for v in ("1e2", ".5", "50.", "+50")] == ["s per -100", "s per -0.5", "s per -50", "s per -50"],
      str([g.model_term("s", v, "lower") for v in ("1e2", ".5", "50.", "+50")]))
check("model term: the engine finds the column in what the GUI wrote", ls.parse_model_term(g.model_term("score", "1e2", "lower")) == ("score", -100.0))
for _bad in ("nan", "inf", "-5", "0", "abc", "1e-12"):
    try:
        g.model_term("s", _bad, "lower")
        check(f"model term refuses {_bad!r}", False)
    except ValueError:
        check(f"model term refuses {_bad!r}", True)
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
    check("memory remembers by header signature", g.load_memory(mem)["files"].get(g.header_signature(["b", "a"])) == {"orig_date": "a"})
    g.remember_columns(["Booked On", "x"], {"orig_date": "Booked On"}, mem)
    learned = g.load_memory(mem)["aliases"]
    check("a picked column name is guessed next time", g.auto_match(["Booked On", "zzz"], learned).get("orig_date") == "Booked On")
    check("...and was not guessed before", "orig_date" not in g.auto_match(["Booked On", "zzz"]))
    g.remember_text_size(16, mem)
    check("text size is remembered", g.load_memory(mem)["text_size"] == 16 and g.load_memory(Path(tmp) / "none.json")["text_size"] == g.DEFAULT_TEXT_SIZE)
    g.remember_columns(["a"], {}, Path(tmp) / "no" / "such" / "dir.json")
    check("memory failure is silent", True)

# ---- A11b typeable alphabetical pickers, readable previews, plain-words comparisons
check("headers sorted ignoring case", g.sorted_headers(["b", "A", "c"]) == ["A", "b", "c"])
check("typing narrows: starts first then contains", g.filter_matches(["x_fico", "fico", "amount"], "fic") == ["fico", "x_fico"])
check("empty query shows everything", g.filter_matches(["a", "b"], "  ") == ["a", "b"])
hd, rows, widths = g.preview_rows(pd.DataFrame({"a_very_long_column_name": ["x"], "d": [pd.Timestamp("2024-01-05 13:00")]}))
check("preview: column wide enough for its header, dates have no time",
      widths[0] >= len("a_very_long_column_name") and rows[0][1] == "2024-01-05", str(widths))
check("describe: vintage", g.describe_test({"group_by": "year"}) == "Survival by origination year")
check("describe: cutoffs", g.describe_test({"column": "score", "cutoffs": "1,2"}) == "Survival below / at or above score cutoffs 1, 2")
check("describe: model with a window", g.describe_test({"model": "fico per -50, flag", "orig_to": "2023-09-30"}) ==
      "Hazard ratio, alone and together: fico per 50 lower, flag; loans opened up to 2023-09-30", g.describe_test({"model": "fico per -50, flag", "orig_to": "2023-09-30"}))
check("example labels: flag uses the person's own choices", g.example_labels("flag", "fico", ">=", "700") == ["fico >= 700 = Yes", "fico >= 700 = No"])
check("example labels: split", g.example_labels("split", "2024-01-01") == ["Before 2024-01-01", "2024-01-01 on"])
check("example labels: cutoffs use the first cutoff", g.example_labels("cutoffs", "FICO", cuts="640, 660") == ["FICO below 640", "FICO 640+"])
check("example labels: nothing chosen yet still names something", g.example_labels("category") == ["Value A", "Value B"] and g.example_labels("vintage") == ["Earlier year", "Later year"])
check("example labels: vintage uses the years", g.example_labels("vintage", years=[2021, 2022, 2023]) == ["2021", "2022", "2023"])
check("flag text", g.flag_text("fico", ">=", " 700 ") == "fico >= 700")
check("flag parse: column against column", g.parse_flag("net_revenue > amount", raw.columns) == ("net_revenue", ">", "amount"))
check("flag parse: against a number", g.parse_flag("fico >= 700", raw.columns) == ("fico", ">=", "700"))
check("flag parse: not a flag", g.parse_flag("fico", raw.columns) is None and g.parse_flag("nope > 3", raw.columns) is None)
_fc = g.flag_counts(raw, "fico >= 700")
check("flag counts equal pandas", _fc == {"Yes": int((raw["fico"] >= 700).sum()), "No": int((raw["fico"] < 700).sum()), "blank": 0}, str(_fc))
check("flag counts: not a flag", g.flag_counts(raw, "nope > 3") is None)
check("describe: window", g.describe_window({"orig_to": "2023-09-30"}) == "loans opened up to 2023-09-30")
import ast
_tree = ast.parse(Path(g.__file__).read_text())
_doc = {id(n.body[0].value) for n in ast.walk(_tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
        and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant)}
_aliases = {id(n) for n in ast.walk(next(x for x in _tree.body if isinstance(x, (ast.Assign, ast.AnnAssign)) and "ALIASES" in ast.dump(x)[:80]))}
_hits = [n.value for n in ast.walk(_tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
         and id(n) not in _doc and id(n) not in _aliases and ("fico" in n.value.lower() or "income" in n.value.lower())]
check("no hard-coded FICO/income wording in window text", not _hits, str(_hits))
check("only the two dates are required", [r for r, _l, req in g.ROLES if req] == ["orig_date", "chargeoff_date"])

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

        # the guided wizard builds each kind of comparison the engine accepts
        def drive(kind, fill):
            w = app.new_wizard()
            w.kind.set(kind)
            w.next()
            fill(w)
            w.next()
            w.next()
            res = w.result
            del w
            gc.collect()
            return res

        app.apply_state(g.parse_settings_text(example))
        r1 = drive("vintage", lambda w: None)
        check("wizard: vintage", r1 and r1["spec"] == {"group_by": "year"}, str(r1))
        r2 = drive("split", lambda w: w.var_a.set("2024-01-01"))
        check("wizard: before/after", r2 and r2["spec"]["split_date"] == "2024-01-01", str(r2))
        r3 = drive("cutoffs", lambda w: (w.var_a.set("fico"), w.var_b.set("640, 660")))
        check("wizard: cutoffs default to seasoned loans", r3 and r3["spec"]["column"] == "fico" and r3["spec"]["cutoffs"] == "640,660"
              and "orig_to" in r3["spec"], str(r3))
        r4 = drive("category", lambda w: w.var_a.set("income_gt_sales"))
        check("wizard: category", r4 and r4["spec"]["column"] == "income_gt_sales", str(r4))
        def model_fill(w):
            w.var_a.set("fico"); w.var_scale.set("50"); w.var_dir.set("lower"); w.add_term()
        r5 = drive("model", model_fill)
        check("wizard: model term", r5 and r5["spec"]["model"] == "fico per -50", str(r5))
        r6 = drive("flag", lambda w: (w.var_a.set("net_revenue"), w.var_op.set(">"), w.var_b.set("amount"), w.on_flag()))
        check("wizard: flag of one column against another", r6 and r6["spec"]["column"] == "net_revenue > amount", str(r6))
        r7 = drive("flag", lambda w: (w.var_a.set("fico"), w.var_op.set(">="), w.var_b.set("700"), w.on_flag()))
        check("wizard: flag of a column against a number", r7 and r7["spec"]["column"] == "fico >= 700", str(r7))
        w = app.new_wizard(); w.kind.set("flag"); w.next(); w.var_a.set("income_gt_sales"); w.var_b.set("5"); w.next()
        check("wizard: a flag on a text column is refused in words", w.step == 1 and "numeric" in w.msg.cget("text"), w.msg.cget("text"))
        w.destroy()
        w = app.new_wizard(existing=r7)
        check("wizard: editing a saved flag opens as a flag with its parts", w.kind.get() == "flag" and (w.var_a.get(), w.var_op.get(), w.var_b.get()) == ("fico", ">=", "700"))
        w.destroy()
        w = app.new_wizard(); w.kind.set("model"); w.next()
        w.fl_a.set("fico"); w.fl_op.set(">="); w.fl_b.set("700"); w.add_flag_term()
        check("wizard: a flag can be added to the model", w.terms == ["fico >= 700"] and w.lb.get(0) == "fico >= 700", str(w.terms))
        w.fl_a.set("income_gt_sales"); w.fl_b.set("5"); w.add_flag_term()
        check("wizard: a model flag on a text column is refused", len(w.terms) == 1 and "numeric" in w.msg.cget("text"), w.msg.cget("text"))
        w.destroy()
        w = app.new_wizard(); w.kind.set("cutoffs"); w.next()
        w.next()
        check("wizard: stays on the step and says why when incomplete", w.step == 1 and "cutoff" in w.msg.cget("text"), w.msg.cget("text"))
        w.destroy()
        # the whole set the wizard built runs in the engine
        r8 = {"name": "flag model", "spec": {"model": "fico >= 700, new_business", "orig_to": "2023-09-30"}}
        app.tests = [r for r in (r1, r2, r3, r4, r5, r6, r7, r8) if r]
        app.v_out.set(str(Path(tmp) / "wiz.xlsx"))
        app.start_run(wait=True)
        check("wizard-built comparisons run", (Path(tmp) / "wiz.xlsx").exists(), app.status.get("1.0", "end")[:200])
        # typeable picker
        pk = app.pickers["orig_date"]
        pk.query.set("orig")
        check("picker: typing narrows the list", pk.matches() and all("orig" in m.lower() for m in pk.matches()), str(pk.matches()))
        # text size
        app.apply_text_size(16, save=False)
        check("window: text size changes", app.text_size == 16)
        app.apply_state(g.parse_settings_text(example))
        check("window: ready line says ready", app.ready_text().startswith("Ready:"), app.ready_text())

        # an unready window says what to do instead of running
        app.v_cols["orig_date"].set("")
        app.start_run(wait=True)
        check("window: missing required column is explained", "Columns tab" in app.status.get("1.0", "end"))
        # a bad file is explained
        app.apply_state(g.parse_settings_text(example))
        app.tests = [{"name": "bad", "spec": {"column": "nope", "cutoffs": "1"}}]
        app.start_run(wait=True)
        check("window: engine error shown in words", "not found" in app.status.get("1.0", "end") and "Traceback" not in app.status.get("1.0", "end"))
        root.app.close()

        # a run must keep going if the window is closed, so the worker is not a daemon thread
        root = g.main([str(book)])
        app = root.app
        app.apply_state(g.parse_settings_text(example))
        app.v_out.set(str(Path(tmp) / "bg.xlsx"))
        app.start_run()
        worker = app._worker
        check("window: the run's worker thread is not a daemon", worker is not None and worker.daemon is False)
        worker.join()
        root.app.close()

        # closing the window in the middle of a run: the workbook must still be written whole, and the process must not abort
        root = g.main([str(book)])
        app = root.app
        app.apply_state(g.parse_settings_text(example))
        app.v_out.set(str(Path(tmp) / "closed_mid_run.xlsx"))
        app.start_run()
        worker = app._worker
        app.close()
        worker.join()
        mid = Path(tmp) / "closed_mid_run.xlsx"
        ok_book = False
        if mid.exists():
            import openpyxl
            ok_book = "Tests" in openpyxl.load_workbook(mid).sheetnames
        check("window: closing mid-run still leaves a whole workbook", ok_book)

        # File -> Load selections BEFORE choosing the data file, then choose the file: nothing may be reset
        root = g.main([])
        app = root.app
        app.apply_state(g.parse_settings_text(example))
        app.load_file(book)
        st_now = app.get_state()
        check("window: selections loaded first survive choosing the file",
              len(st_now["tests"]) == 5 and st_now["cols"] == g.parse_settings_text(example)["cols"] and st_now["as_of"] == "2026-09-30",
              f"{len(st_now['tests'])} tests")
        root.app.close()

        # Load selections with a blank as-of AFTER a file is open: the automatic date must come back
        root = g.main([str(book)])
        app = root.app
        st_blank = g.parse_settings_text(example)
        st_blank["as_of"] = ""
        app.apply_state(st_blank)
        check("window: loading selections with no as-of restores the file's latest date", app.v_asof.get() == "2026-09-30", app.v_asof.get())
        w = app.new_wizard(); w.kind.set("cutoffs"); w.next(); w.var_a.set("fico"); w.var_b.set("640"); w.next()
        check("window: ...so the wizard offers loans old enough to judge", getattr(w, "seasoned_to", "") != "", getattr(w, "seasoned_to", ""))
        w.destroy()
        root.app.close()

print("\nALL PASSED" if not FAIL else f"\nFAILED: {FAIL}")
sys.exit(1 if FAIL else 0)
