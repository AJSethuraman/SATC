#!/usr/bin/env python3
"""Credit-Risk Template Control Center -- one place to run any template.

Every template workbook carries its own data-path runner inside itself (the
_code_py tab -- the same bytes the in-Excel Extract button writes out). This
tool discovers those workbooks, lets you pick ONE, extracts that workbook's
OWN embedded runner next to it, and runs it against the closed workbook.
Nothing template-specific lives here: any workbook that follows
TEMPLATE_CONTRACT.md is supported automatically, now and in the future.

GUI (default):   python control_center.py
                 (Tkinter -- ships with standard Python on Windows; no extra
                 installs beyond what the runners already need.)
CLI (headless):  python control_center.py --list
                 python control_center.py --run <name-or-path> --demo
                 python control_center.py --extract <name-or-path>

Needs: python 3.8+, openpyxl, pandas (the runners' own requirements).
Close the workbook in Excel before refreshing -- the runner writes the file.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading

APP_TITLE = "Credit-Risk Template Control Center"
SKIP_DIRS = {".git", "build", "__pycache__", ".pytest_cache", "node_modules"}
MAX_DEPTH = 2                    # repo root -> template dir -> workbook


class Template:
    def __init__(self, xlsm_path):
        self.xlsm_path = os.path.abspath(xlsm_path)
        self.folder = os.path.dirname(self.xlsm_path)
        self.name = os.path.splitext(os.path.basename(self.xlsm_path))[0]

    def __repr__(self):
        return f"Template({self.name})"


# --------------------------------------------------------------------------
# Discovery: any .xlsm carrying a _code_py tab is a template workbook.
# --------------------------------------------------------------------------
def _has_code_tab(path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        ok = "_code_py" in wb.sheetnames
        wb.close()
        return ok
    except Exception:
        return False


def discover(root=".") -> list:
    root = os.path.abspath(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and depth < MAX_DEPTH]
        for fn in filenames:
            if fn.lower().endswith(".xlsm") and not fn.startswith("~$"):
                p = os.path.join(dirpath, fn)
                if _has_code_tab(p):
                    found.append(Template(p))
    return sorted(found, key=lambda t: t.name.lower())


# --------------------------------------------------------------------------
# Extraction: mirror the VBA button (one _code_py cell per line, UTF-8).
# --------------------------------------------------------------------------
def extract_runner(t: Template) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(t.xlsm_path, read_only=True)
    ws = wb["_code_py"]
    lines = []
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        lines.append("" if v is None else str(v))
    wb.close()
    dest = os.path.join(t.folder, "runner.py")
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return dest


# --------------------------------------------------------------------------
# Run: drive the workbook's OWN runner against the closed workbook.
# --------------------------------------------------------------------------
def build_command(t: Template, runner_path: str, demo: bool) -> list:
    with open(runner_path, "r", encoding="utf-8") as fh:
        src = fh.read()
    cmd = [sys.executable, runner_path, "--workbook", t.xlsm_path]
    if demo:
        cmd.append("--demo")
    if "--backend" in src:               # grandfathered FRED runner
        cmd += ["--backend", "openpyxl"]
    return cmd


def run_refresh(t: Template, demo: bool, log=print) -> int:
    log(f"[{t.name}] extracting embedded runner from _code_py ...")
    runner_path = extract_runner(t)
    log(f"[{t.name}] runner.py written next to the workbook")
    cmd = build_command(t, runner_path, demo)
    log(f"[{t.name}] running: {' '.join(os.path.basename(c) if i < 2 else c for i, c in enumerate(cmd))}")
    log(f"[{t.name}] mode: {'DEMO (offline, deterministic)' if demo else 'LIVE'}")
    proc = subprocess.Popen(cmd, cwd=t.folder, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        log(line.rstrip())
    proc.wait()
    log(f"[{t.name}] {'DONE -- reopen the workbook to see the dashboards' if proc.returncode == 0 else f'FAILED (exit {proc.returncode})'}")
    return proc.returncode


# --------------------------------------------------------------------------
# CLI mode (headless / scripting / CI)
# --------------------------------------------------------------------------
def _resolve(arg, templates):
    if os.path.exists(arg):
        return Template(arg)
    matches = [t for t in templates if arg.lower() in t.name.lower()]
    if len(matches) == 1:
        return matches[0]
    sys.stderr.write(f"'{arg}' matches {len(matches)} templates; be more specific.\n")
    raise SystemExit(2)


def cli(argv):
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--root", default=".", help="folder to scan for template workbooks")
    ap.add_argument("--list", action="store_true", help="list discovered templates")
    ap.add_argument("--run", metavar="NAME", help="refresh one template (name substring or path)")
    ap.add_argument("--extract", metavar="NAME", help="extract a template's runner.py and exit")
    ap.add_argument("--demo", action="store_true", help="offline deterministic demo data")
    args = ap.parse_args(argv)

    templates = discover(args.root)
    if args.list:
        if not templates:
            print("no template workbooks found (looking for .xlsm files with a _code_py tab)")
        for t in templates:
            print(f"{t.name}    {os.path.relpath(t.xlsm_path, args.root)}")
        return 0
    if args.extract:
        t = _resolve(args.extract, templates)
        print(extract_runner(t))
        return 0
    if args.run:
        t = _resolve(args.run, templates)
        return run_refresh(t, demo=args.demo)
    return gui(templates, args.root)


# --------------------------------------------------------------------------
# GUI mode (Tkinter -- one template at a time)
# --------------------------------------------------------------------------
def gui(templates, root):
    try:
        import tkinter as tk
        from tkinter import scrolledtext, messagebox
    except ImportError:
        sys.stderr.write("Tkinter is not available here -- use --list/--run "
                         "(see --help), or run this on a machine with a "
                         "standard Python install.\n")
        return 3

    # House palette (mirrors keybank_style tokens; hardcoding here is OK --
    # this tool lives OUTSIDE the workbooks and must stay stdlib-only).
    INK, CANVAS, KEY_RED, SLATE = "#0A0908", "#F4F1EC", "#CC0000", "#57534B"

    win = tk.Tk()
    win.title(APP_TITLE)
    win.geometry("860x560")
    win.configure(bg=CANVAS)

    tk.Label(win, text=APP_TITLE, bg=INK, fg="white",
             font=("Arial", 14, "bold"), anchor="w", padx=14, pady=10
             ).pack(fill="x")
    tk.Frame(win, bg=KEY_RED, height=3).pack(fill="x")

    body = tk.Frame(win, bg=CANVAS)
    body.pack(fill="both", expand=True, padx=12, pady=10)

    left = tk.Frame(body, bg=CANVAS)
    left.pack(side="left", fill="y")
    tk.Label(left, text="Templates (pick one)", bg=CANVAS, fg=SLATE,
             font=("Arial", 9, "bold")).pack(anchor="w")
    lb = tk.Listbox(left, width=42, height=14, font=("Consolas", 10),
                    selectmode="browse", exportselection=False)
    lb.pack(fill="y", expand=True, pady=(2, 8))
    for t in templates:
        lb.insert("end", t.name)
    if templates:
        lb.selection_set(0)

    log_box = scrolledtext.ScrolledText(body, font=("Consolas", 9), bg="white",
                                        fg=INK, state="disabled", wrap="word")
    log_box.pack(side="right", fill="both", expand=True, padx=(12, 0))

    def log(msg):
        log_box.configure(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    buttons = []

    def set_busy(busy):
        for b in buttons:
            b.configure(state="disabled" if busy else "normal")

    def selected():
        sel = lb.curselection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Pick a template first.")
            return None
        return templates[sel[0]]

    def do_run(demo):
        t = selected()
        if not t:
            return
        set_busy(True)          # one template at a time

        def work():
            try:
                run_refresh(t, demo=demo, log=lambda m: win.after(0, log, m))
            except Exception as exc:
                win.after(0, log, f"ERROR: {exc}")
            finally:
                win.after(0, set_busy, False)
        threading.Thread(target=work, daemon=True).start()

    def do_extract():
        t = selected()
        if not t:
            return
        try:
            log(f"[{t.name}] extracted: {extract_runner(t)}")
        except Exception as exc:
            log(f"ERROR: {exc}")

    def do_open():
        t = selected()
        if not t:
            return
        if sys.platform == "win32":
            os.startfile(t.folder)                       # noqa: S606
        else:
            subprocess.Popen(["xdg-open" if sys.platform.startswith("linux")
                              else "open", t.folder])

    btns = tk.Frame(left, bg=CANVAS)
    btns.pack(fill="x")
    for label, cmd, accent in [
            ("Refresh (Demo)", lambda: do_run(True), INK),
            ("Refresh (Live)", lambda: do_run(False), KEY_RED),
            ("Extract runner.py", do_extract, SLATE),
            ("Open folder", do_open, SLATE)]:
        b = tk.Button(btns, text=label, command=cmd, bg=accent, fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=10, pady=6)
        b.pack(fill="x", pady=3)
        buttons.append(b)

    log(f"Scanned: {os.path.abspath(root)}")
    log(f"Found {len(templates)} template workbook(s). "
        "Close a workbook in Excel before refreshing it.")
    if not templates:
        log("Nothing found -- put this file in the folder that holds your "
            "template .xlsm files (or a parent of it) and restart.")
    win.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv[1:]))
