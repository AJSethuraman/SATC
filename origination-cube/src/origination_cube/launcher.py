"""The launcher: the window a person double-clicks. Two buttons, no commands.

Ruling OC-22 (25 Sep 2026): "i don't want this to be a technical exercise for
users to run nor me to debug." Everything is decided in the workbook; this
window only does the running:

    1. Set up from this extract   -> book.set_up (keeps any answers already given)
    2. Run the cube               -> book.run    (results land in the workbook)
    Open the workbook             -> opens it in Excel

What happened is shown in plain words in the box underneath, and written to the
workbook's Log tab. Anything that goes wrong inside is caught and shown as a
sentence with where to look, never as a Python traceback.

Tkinter ships with standard Python on Windows, so nothing extra is needed for
the window itself.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

TITLE = "Origination Cube"
PREFS = Path.home() / ".origination-cube" / "launcher.json"


def book_for(extract: str | Path) -> Path:
    """Where the workbook for an extract lives: beside it, named after it."""
    p = Path(extract)
    return p.with_name(f"{p.stem} - Origination Cube.xlsx")


def missing_addons() -> list[str]:
    out = []
    for mod, name in (("openpyxl", "openpyxl"), ("yaml", "PyYAML")):
        try:
            __import__(mod)
        except ImportError:
            out.append(name)
    return out


def do_set_up(extract: str) -> list[str]:
    from . import book
    if not extract or not Path(extract).exists():
        return ["Pick the extract first (the loan file from the bank: .csv or .xlsx)."]
    try:
        return book.set_up(extract).lines
    except Exception:
        return _crash("setting up")


def do_run(extract: str) -> list[str]:
    from . import book
    if not extract:
        return ["Pick the extract first."]
    target = book_for(extract)
    if not target.exists():
        return [f"There's no workbook for {Path(extract).name} yet. Press 1. Set up from this extract first."]
    try:
        return book.run(target).lines
    except Exception:
        return _crash("running")


def _crash(what: str) -> list[str]:
    """Something the tool did not expect. Say so plainly and keep the detail for whoever fixes it."""
    detail = traceback.format_exc()
    log = Path.home() / ".origination-cube" / "last-error.txt"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(detail, encoding="utf-8")
    except OSError:
        pass
    return [f"Something went wrong while {what}. The details are in {log}; send that file over to get it fixed."]


def open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _prefs() -> dict:
    try:
        return json.loads(PREFS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_prefs(d: dict) -> None:
    try:
        PREFS.parent.mkdir(parents=True, exist_ok=True)
        PREFS.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def build(root) -> dict:
    """The window's widgets on `root`. Split from main() so the harness in
    tools/shoot_launcher.py can press the buttons and photograph each state."""
    import tkinter as tk
    from tkinter import filedialog, ttk

    root.title(TITLE)
    root.geometry("640x420")
    root.minsize(520, 360)
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=TITLE, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w",
                                                                    pady=(0, 12))

    ttk.Label(frame, text="Extract:").grid(row=2, column=0, sticky="w")
    extract = tk.StringVar(value=_prefs().get("extract", ""))
    ttk.Entry(frame, textvariable=extract, width=60).grid(row=2, column=1, sticky="ew", padx=6)

    def browse():
        p = filedialog.askopenfilename(title="Pick the loan extract",
                                       filetypes=[("Extracts", "*.csv *.xlsx"), ("All files", "*.*")])
        if p:
            extract.set(p)
            _save_prefs({"extract": p})

    ttk.Button(frame, text="Browse...", command=browse).grid(row=2, column=2)

    buttons = ttk.Frame(frame)
    buttons.grid(row=3, column=0, columnspan=3, sticky="w", pady=12)
    status = tk.Text(frame, height=12, wrap="word", relief="solid", borderwidth=1, font=("Segoe UI", 10))
    status.grid(row=4, column=0, columnspan=3, sticky="nsew")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=status.yview)
    scroll.grid(row=4, column=3, sticky="ns")
    status.configure(yscrollcommand=scroll.set)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(4, weight=1)

    def show(lines: list[str]) -> None:
        status.configure(state="normal")
        status.delete("1.0", "end")
        status.insert("end", "\n".join(lines))
        status.configure(state="disabled")

    def busy(on: bool, what: str = "") -> None:
        for b in (b_setup, b_run, b_open):
            b.configure(state="disabled" if on else "normal")
        if on:
            show([f"{what}... this can take a minute on a large extract."])

    def in_background(fn, what):
        # Tk may only be touched from the main thread (found by tools/shoot_launcher.py:
        # the worker read the extract box itself). So the value is read here, the work
        # runs in a thread, and its answer comes back through a queue polled from here.
        value = extract.get()
        _save_prefs({"extract": value})
        busy(True, what)
        done: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: done.put(fn(value)), daemon=True).start()

        def poll():
            try:
                lines = done.get_nowait()
            except queue.Empty:
                root.after(100, poll)
                return
            busy(False)
            show(lines)
        root.after(100, poll)

    def open_book():
        b = book_for(extract.get()) if extract.get() else None
        if b and b.exists():
            open_file(b)
        else:
            show(["There's no workbook yet. Press 1. Set up from this extract first."])

    b_setup = ttk.Button(buttons, text="1. Set up from this extract",
                         command=lambda: in_background(do_set_up, "Setting up"))
    b_run = ttk.Button(buttons, text="2. Run the cube", command=lambda: in_background(do_run, "Running"))
    b_open = ttk.Button(buttons, text="Open the workbook", command=open_book)
    b_setup.pack(side="left", padx=(0, 8))
    b_run.pack(side="left", padx=(0, 8))
    b_open.pack(side="left")

    missing = missing_addons()
    if missing:
        show([f"This needs {', '.join(missing)} installed alongside Python before it can run.",
              "Double-click 'Install add-ons.bat' in this folder once, then open this window again."])
        b_setup.configure(state="disabled")
        b_run.configure(state="disabled")
    else:
        show(["1. Pick the extract.",
              "2. Press Set up: this writes the workbook beside the extract.",
              "3. In the workbook, fill in the shaded cells, save and close it.",
              "4. Press Run the cube. The results land in the workbook."])
    return {"extract": extract, "setup": b_setup, "run": b_run, "open": b_open, "status": status}


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    build(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
