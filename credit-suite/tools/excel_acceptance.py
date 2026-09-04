#!/usr/bin/env python3
"""Drive REAL Excel through the ExtractFiles button, safely (issue #169).

    python tools/excel_acceptance.py --workbook Bank_Peer_Monitor.xlsm

Contract section 9 asks for a real-Excel check and section 5 fixes what the
button must do. Only Excel can answer whether the embedded VBA project actually
binds and runs: openpyxl proves the bytes are present, olevba proves they
decompile, the OPC audit proves the package is well formed -- and all three pass
on a workbook Excel refuses to load cleanly. That gap is why this exists.

**Written defensively, because it hung twice before it worked.**

* Every COM call, INCLUDING ``Workbooks.Open``, runs on a worker thread while
  the main thread supervises. The first version opened the workbook before it
  started watching, and the block turned out to be inside Open -- observation
  has to start before the first call that can block, not before the one you
  assumed would.
* A **dialog responder** polls for dialogs, RECORDS their text, then answers
  them by clicking a named button. Recording first, because a dismissed dialog
  nobody read is a diagnosis thrown away.
* The main thread has a hard deadline and returns rather than blocking.
* ``finally`` closes, quits, and kills any EXCEL.EXE this script started --
  measured against a PID baseline, so a copy the user already had open is never
  touched.

Output is one JSON object on stdout, so a caller can assert on it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

POLL_SECONDS = 0.4
DIALOG_CLASS = "#32770"
WM_CLOSE = 0x0010
BM_CLICK = 0x00F5

#: Buttons to press, in order of preference. "Yes" first because the dialog
#: this actually hits -- "An error occurred while loading 'PeerMonitor'. Do you
#: want to continue loading the project?" -- needs Yes to get any further, and
#: the whole point is to find out what happens when the analyst clicks through.
PREFERRED_BUTTONS = ("&Yes", "Yes", "&OK", "OK", "&Continue")


def excel_pids() -> set:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process EXCEL -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=60).stdout
    except Exception:                              # noqa: BLE001
        return set()
    return {int(x) for x in out.split() if x.strip().isdigit()}


def kill(pids) -> List[int]:
    killed = []
    for pid in sorted(pids):
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=30)
            killed.append(pid)
        except Exception:                          # noqa: BLE001
            pass
    return killed


class DialogResponder(threading.Thread):
    """Read every dialog Excel raises, then answer it."""

    def __init__(self, baseline: set):
        super().__init__(daemon=True)
        self.baseline = baseline
        self.seen: List[Dict[str, object]] = []
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        import win32gui
        import win32process

        answered = set()
        while not self._stop.is_set():
            live = excel_pids() - self.baseline
            targets = []

            def visit(hwnd, _):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                    if win32gui.GetClassName(hwnd) != DIALOG_CLASS:
                        return True
                    _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if live and pid not in live:
                        return True            # not ours
                    targets.append(hwnd)
                except Exception:                  # noqa: BLE001
                    pass
                return True

            try:
                win32gui.EnumWindows(visit, None)
            except Exception:                      # noqa: BLE001
                pass

            for hwnd in targets:
                buttons: Dict[str, int] = {}
                statics: List[str] = []

                def kid(child, _unused):
                    try:
                        text = win32gui.GetWindowText(child)
                        cls = win32gui.GetClassName(child)
                        if not text:
                            return True
                        if cls == "Button":
                            buttons[text] = child
                        else:
                            statics.append(text)
                    except Exception:              # noqa: BLE001
                        pass
                    return True

                try:
                    win32gui.EnumChildWindows(hwnd, kid, None)
                except Exception:                  # noqa: BLE001
                    pass

                title = win32gui.GetWindowText(hwnd)
                signature = (title, " | ".join(statics))
                pressed = None
                for label in PREFERRED_BUTTONS:
                    if label in buttons:
                        pressed = label
                        try:
                            win32gui.PostMessage(buttons[label], BM_CLICK, 0, 0)
                        except Exception:          # noqa: BLE001
                            pressed = None
                        break
                if pressed is None:
                    try:
                        win32gui.PostMessage(hwnd, WM_CLOSE, 0, 0)
                        pressed = "<closed>"
                    except Exception:              # noqa: BLE001
                        pressed = "<could not answer>"

                if signature not in answered:
                    answered.add(signature)
                    self.seen.append({
                        "title": title,
                        "message": " | ".join(statics),
                        "buttons": sorted(buttons),
                        "answered": pressed,
                        "at": time.strftime("%H:%M:%S"),
                    })

            self._stop.wait(POLL_SECONDS)


def run_button(workbook: Path, macro: str, budget: float,
               visible: bool = False) -> dict:
    """Open the workbook in real Excel, run the macro, report what happened."""
    import pythoncom
    import win32com.client as win32

    baseline = excel_pids()
    result: dict = {"workbook": workbook.name, "macro": macro,
                    "dialogs": [], "error": None, "opened": False,
                    "ran": False}
    handles: Dict[str, object] = {}
    done = threading.Event()

    responder = DialogResponder(baseline)
    responder.start()

    def drive():
        pythoncom.CoInitialize()
        try:
            excel = win32.DispatchEx("Excel.Application")
            handles["excel"] = excel
            excel.Visible = bool(visible)
            excel.DisplayAlerts = False        # does NOT suppress a VBA MsgBox
            excel.EnableEvents = False
            excel.AskToUpdateLinks = False
            excel.AutomationSecurity = 1       # msoAutomationSecurityLow
            result["excel_version"] = str(excel.Version)

            started = time.time()
            book = excel.Workbooks.Open(str(workbook))
            handles["book"] = book
            result["opened"] = True
            result["open_seconds"] = round(time.time() - started, 2)
            result["sheets"] = int(book.Sheets.Count)

            started = time.time()
            excel.Run("'%s'!%s" % (book.Name, macro))
            result["macro_seconds"] = round(time.time() - started, 2)
            result["ran"] = True
        except Exception as exc:                   # noqa: BLE001
            result["error"] = "%s: %s" % (type(exc).__name__, exc)
        finally:
            done.set()

    worker = threading.Thread(target=drive, daemon=True)
    worker.start()

    finished = done.wait(budget)
    if not finished:
        result["error"] = ("blocked for %.0fs -- gave up rather than hang"
                           % budget)

    time.sleep(POLL_SECONDS * 3)                   # catch a late dialog
    responder.stop()
    result["dialogs"] = responder.seen

    for step in (lambda: handles["book"].Close(SaveChanges=False),
                 lambda: handles["excel"].Quit()):
        try:
            step()
        except Exception:                          # noqa: BLE001
            pass
    time.sleep(0.6)
    result["killed_strays"] = kill(excel_pids() - baseline)
    return result


def recalc(workbook: Path, cells: List[str], budget: float,
           visible: bool = False) -> dict:
    """Open in real Excel, force a full rebuild, read back computed cells.

    Separate from the macro path on purpose: the embedded VBA project is a
    different thing from the formulas, and one being broken must not stop the
    other being checked. This is the half of the section 9 recalc spot-check
    that only real Excel can do -- the `formulas` engine is a model of Excel,
    and a model agreeing with itself proves less than Excel agreeing with it.
    """
    import pythoncom
    import win32com.client as win32

    baseline = excel_pids()
    result: dict = {"workbook": workbook.name, "cells": {}, "error": None,
                    "dialogs": []}
    handles: Dict[str, object] = {}
    done = threading.Event()

    responder = DialogResponder(baseline)
    responder.start()

    def drive():
        pythoncom.CoInitialize()
        try:
            excel = win32.DispatchEx("Excel.Application")
            handles["excel"] = excel
            excel.Visible = bool(visible)
            excel.DisplayAlerts = False
            excel.EnableEvents = False
            excel.AskToUpdateLinks = False
            excel.AutomationSecurity = 1
            result["excel_version"] = str(excel.Version)

            book = excel.Workbooks.Open(str(workbook))
            handles["book"] = book
            result["opened"] = True

            excel.CalculateFullRebuild()
            result["recalculated"] = True

            for ref in cells:
                sheet, _, coord = ref.partition("!")
                try:
                    value = book.Sheets(sheet).Range(coord).Value
                except Exception as exc:           # noqa: BLE001
                    value = "<error: %s>" % exc
                result["cells"][ref] = value
        except Exception as exc:                   # noqa: BLE001
            result["error"] = "%s: %s" % (type(exc).__name__, exc)
        finally:
            done.set()

    threading.Thread(target=drive, daemon=True).start()
    if not done.wait(budget):
        result["error"] = "blocked for %.0fs -- gave up rather than hang" % budget

    time.sleep(POLL_SECONDS * 3)
    responder.stop()
    result["dialogs"] = responder.seen

    for step in (lambda: handles["book"].Close(SaveChanges=False),
                 lambda: handles["excel"].Quit()):
        try:
            step()
        except Exception:                          # noqa: BLE001
            pass
    time.sleep(0.6)
    result["killed_strays"] = kill(excel_pids() - baseline)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--macro", default="ExtractFiles")
    ap.add_argument("--budget", type=float, default=120.0)
    ap.add_argument("--visible", action="store_true")
    ap.add_argument("--recalc", metavar="CELL", action="append",
                    help="recalc mode: read Sheet!A1 after a full rebuild; "
                         "repeatable. Does not touch the macro.")
    args = ap.parse_args(argv)

    workbook = Path(args.workbook).resolve()
    if not workbook.is_file():
        print(json.dumps({"error": "no such workbook: %s" % workbook}))
        return 1

    if args.recalc:
        result = recalc(workbook, args.recalc, args.budget, args.visible)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("recalculated") and not result.get("error") else 2

    before = {p.name for p in workbook.parent.iterdir()}
    result = run_button(workbook, args.macro, args.budget, args.visible)
    after = {p.name for p in workbook.parent.iterdir()}
    result["written"] = sorted(after - before)

    print(json.dumps(result, indent=2))
    return 0 if (result.get("ran") and not result.get("error")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
