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
the window itself. The cube's add-ons (numpy, openpyxl, PyYAML) are checked
first, without loading them (ruling OC-34): while any is missing, the window
says which, offers Install now, and keeps Set up and Run switched off. So
nothing at the top of this file may import them; `book` is imported inside
the buttons that use it.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

from . import deps

TITLE = "Origination Cube"
START = ["1. Pick the extract.",
         "2. Press Set up: this writes the workbook beside the extract.",
         "3. In the workbook, fill in the shaded cells, save and close it.",
         "4. Press Run the cube. The results land in the workbook."]
PREFS = Path.home() / ".origination-cube" / "launcher.json"


def book_for(extract: str | Path) -> Path:
    """Where the workbook for an extract lives: beside it, named after it."""
    p = Path(extract)
    return p.with_name(f"{p.stem} - Origination Cube.xlsx")


def _on(yes: bool) -> str:
    return "normal" if yes else "disabled"


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


class AddOns:
    """What the window says and allows about the add-ons (OC-34), kept apart
    from Tk so a test can drive it. Set up and Run stay off while anything the
    cube needs is missing, and come on only when a fresh check finds it all."""

    def __init__(self) -> None:
        self.missing = deps.missing()
        self.installing: list[str] = []
        self.began = 0.0
        self.said = ""              # what the installer said, when the last try didn't work
        self.got: list[str] = []    # what the last install added

    def states(self) -> dict[str, str]:
        """Each button's state, by the name build() gives it."""
        ready = not self.missing
        return {"setup": _on(ready), "run": _on(ready), "open": "normal",
                "install": _on(not ready and not self.installing)}

    def headline(self) -> str:
        """The one line above the buttons; empty once nothing is missing."""
        if not self.missing:
            return ""
        if self.said and not self.installing:
            return f"Couldn't install {_names(self.missing)} from here. Press Copy for IT and send them the note below."
        return deps.message(self.missing)

    def lines(self) -> list[str]:
        """What the box underneath says."""
        if self.installing:
            took = int(time.monotonic() - self.began)
            return [f"Installing {_names(self.installing)}... {took // 60}:{took % 60:02d} so far.",
                    "This can take a few minutes. This box says when it's done."]
        if not self.missing:
            return ([f"Installed {_names(self.got)}. Everything the cube needs is here.", ""] if self.got else []) + START
        if self.said:
            tail = [ln.strip() for ln in self.said.splitlines() if ln.strip()][-6:]
            return [deps.ask_it(self.missing), "", "What the installer said last:", *("    " + ln for ln in tail)]
        them, theyre = ("it", "it's") if len(self.missing) == 1 else ("them", "they're")
        return [f"Install now downloads {them} from the internet. It takes a minute or two.",
                f"Set up and Run switch on once {theyre} in."]

    def start(self) -> list[str]:
        """Mark an install begun, and return the names to hand to deps.install."""
        self.installing, self.began, self.said = list(self.missing), time.monotonic(), ""
        return list(self.installing)

    def finish(self, ok: bool, output: str) -> None:
        """Take the install's answer, and look again for what is still missing."""
        tried, self.installing = self.installing, []
        self.missing = deps.missing()
        self.got = [n for n in tried if n not in self.missing]
        self.said = "" if not self.missing else (output.strip() or "The installer said nothing.")


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
    if Path(extract).name.endswith(" - Origination Cube.xlsx"):
        return [f"{Path(extract).name} is the workbook, not the loan file. Pick the extract beside it."]
    target = book_for(extract)
    if not target.exists():
        return [f"There's no workbook for {Path(extract).name} yet. Press 1. Set up from this extract first."]
    try:
        return book.run(target, extract).lines
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
    root.geometry("720x560")
    root.minsize(560, 440)
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=TITLE, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w",
                                                                    pady=(0, 12))

    # Row 1 is there only while an add-on is missing (OC-34): what, why, and Install now.
    gate = AddOns()
    fix = ttk.Frame(frame)
    fix.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))
    headline = ttk.Label(fix, font=("Segoe UI", 10, "bold"), wraplength=640, justify="left")
    headline.pack(anchor="w")
    fix.bind("<Configure>", lambda e: headline.configure(wraplength=max(200, e.width - 8)))
    fix_row = ttk.Frame(fix)
    fix_row.pack(anchor="w", pady=(8, 0))

    ttk.Label(frame, text="Extract:").grid(row=2, column=0, sticky="w")
    extract = tk.StringVar(value=_prefs().get("extract", ""))
    box = ttk.Entry(frame, textvariable=extract, width=60)
    box.grid(row=2, column=1, sticky="ew", padx=6)
    box.xview_moveto(1)          # the file name, not the front of a long folder path, is what shows

    def browse():
        p = filedialog.askopenfilename(title="Pick the loan extract",
                                       filetypes=[("Extracts", "*.csv *.xlsx"), ("All files", "*.*")])
        if p:
            extract.set(p)
            box.icursor("end")
            box.xview_moveto(1)
            _save_prefs({"extract": p})

    ttk.Button(frame, text="Browse...", command=browse).grid(row=2, column=2)

    buttons = ttk.Frame(frame)
    buttons.grid(row=3, column=0, columnspan=3, sticky="w", pady=12)
    status = tk.Text(frame, height=18, wrap="word", relief="solid", borderwidth=1, font=("Segoe UI", 10))
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

    def apply() -> None:
        """Buttons and row 1 as the add-ons stand. Every state comes from AddOns.states()."""
        for name, state in gate.states().items():
            widgets[name].configure(state=state)
        headline.configure(text=gate.headline())
        if gate.missing:
            fix.grid()
        else:
            fix.grid_remove()
        if gate.said and not gate.installing:
            b_copy.pack(side="left", padx=(0, 8), before=b_close)
            b_install.configure(text="Try again")
        else:
            b_copy.pack_forget()
            b_install.configure(text="Install now")

    def busy(on: bool, what: str = "") -> None:
        if on:
            for b in (b_setup, b_run, b_open):
                b.configure(state="disabled")
            show([f"{what}... this can take a minute on a large extract."])
        else:
            apply()

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

    def install() -> None:
        # pip runs in a thread so the window keeps answering; the clock in the box shows it hasn't hung.
        names = gate.start()
        apply()
        show(gate.lines())
        done: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: done.put(deps.install(names)), daemon=True).start()

        def poll():
            try:
                ok, said = done.get_nowait()
            except queue.Empty:
                show(gate.lines())
                root.after(500, poll)
                return
            gate.finish(ok, said)
            apply()
            show(gate.lines())
        root.after(500, poll)

    def copy_for_it() -> None:
        root.clipboard_clear()
        root.clipboard_append(deps.ask_it(gate.missing))
        b_copy.configure(text="Copied")
        root.after(2000, lambda: b_copy.configure(text="Copy for IT"))

    b_install = ttk.Button(fix_row, text="Install now", command=install)
    b_copy = ttk.Button(fix_row, text="Copy for IT", command=copy_for_it)
    b_close = ttk.Button(fix_row, text="Close", command=root.destroy)
    b_install.pack(side="left", padx=(0, 8))
    b_close.pack(side="left")

    widgets = {"extract": extract, "setup": b_setup, "run": b_run, "open": b_open, "status": status,
               "install": b_install, "copy": b_copy, "close": b_close, "headline": headline, "gate": gate}
    apply()
    show(gate.lines())
    return widgets


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    build(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
