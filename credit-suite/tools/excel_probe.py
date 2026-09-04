#!/usr/bin/env python3
"""Diagnostic: what window is actually blocking Excel? (issue #169)

The acceptance harness hung twice, and a watchdog aimed at dialog-class windows
did not clear it. Rather than guess again, this observes: it kicks the macro off
on a worker thread and, from the main thread, enumerates EVERY visible top-level
window once a second -- class, title, owning process -- until the macro returns
or the budget runs out.

It is deliberately separate from the acceptance script. Diagnostics and the
thing being diagnosed should not share a code path, or a fix to one silently
changes the other.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path


def excel_pids() -> set:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process EXCEL -ErrorAction SilentlyContinue | "
         "Select-Object -ExpandProperty Id"],
        capture_output=True, text=True, timeout=60).stdout
    return {int(x) for x in out.split() if x.strip().isdigit()}


def snapshot(only_pids=None):
    """Every visible top-level window, with enough to identify it."""
    import win32gui
    import win32process

    rows = []

    def visit(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            if only_pids and pid not in only_pids:
                return True
            if not title and cls in ("Shell_TrayWnd",):
                return True
            children = []

            def kid(child, _unused):
                text = win32gui.GetWindowText(child)
                if text:
                    children.append("%s[%s]" % (text, win32gui.GetClassName(child)))
                return True

            try:
                win32gui.EnumChildWindows(hwnd, kid, None)
            except Exception:                      # noqa: BLE001
                pass
            rows.append({"hwnd": hwnd, "class": cls, "title": title, "pid": pid,
                         "enabled": bool(win32gui.IsWindowEnabled(hwnd)),
                         "children": children[:12]})
        except Exception:                          # noqa: BLE001
            pass
        return True

    win32gui.EnumWindows(visit, None)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--macro", default="ExtractFiles")
    ap.add_argument("--visible", action="store_true")
    ap.add_argument("--budget", type=float, default=45.0)
    args = ap.parse_args(argv)

    import pythoncom
    import win32com.client as win32

    workbook = Path(args.workbook).resolve()
    before = excel_pids()

    done = threading.Event()
    outcome = {}
    handles = {}

    def drive():
        """EVERYTHING COM happens here, including Workbooks.Open.

        The first version opened the workbook on the main thread before it
        started watching -- and the block turned out to be inside Open, so the
        watcher never ran. Observation has to start before the first call that
        can block, not after the one you assumed would.
        """
        pythoncom.CoInitialize()
        try:
            excel = win32.DispatchEx("Excel.Application")
            handles["excel"] = excel
            excel.Visible = bool(args.visible)
            excel.DisplayAlerts = False
            excel.EnableEvents = False
            excel.AutomationSecurity = 1
            outcome["version"] = str(excel.Version)
            outcome["pids"] = sorted(excel_pids() - before)

            book = excel.Workbooks.Open(str(workbook))
            handles["book"] = book
            outcome["opened"] = True
            outcome["sheets"] = int(book.Sheets.Count)

            excel.Run("'%s'!%s" % (book.Name, args.macro))
            outcome["ran"] = True
        except Exception as exc:                   # noqa: BLE001
            outcome["error"] = "%s: %s" % (type(exc).__name__, exc)
        finally:
            done.set()

    worker = threading.Thread(target=drive, daemon=True)
    worker.start()

    deadline = time.time() + args.budget
    seen = []
    while not done.wait(1.0) and time.time() < deadline:
        pids = excel_pids() - before
        for row in snapshot(pids):
            key = (row["class"], row["title"])
            if key not in [(s_["class"], s_["title"]) for s_ in seen]:
                seen.append(row)
                print("WINDOW %-16s %-42r enabled=%s children=%s"
                      % (row["class"], row["title"][:42], row["enabled"],
                         row["children"][:6]), flush=True)
    if not done.is_set():
        outcome["blocked_after_seconds"] = args.budget
        print("STILL BLOCKED after %.0fs -- last known state: %s"
              % (args.budget, {k: v for k, v in outcome.items()}), flush=True)

    print(json.dumps({"outcome": outcome or {"blocked": True},
                      "windows": seen}, indent=2, default=str), flush=True)

    for step in (lambda: handles["book"].Close(SaveChanges=False),
                 lambda: handles["excel"].Quit()):
        try:
            step()
        except Exception:                          # noqa: BLE001
            pass
    time.sleep(0.5)
    strays = excel_pids() - before
    for pid in strays:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    print("killed strays: %s" % sorted(strays), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
