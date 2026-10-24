"""One window that builds the consumer credit workbook: pick a folder, get the
FDIC data, build, and Excel opens it. Shipped as one file,
``Consumer credit thresholds.pyzw`` (``tools/make_app.py``), which carries
this package, ``openpyxl`` and the consumer book; double-clicking it runs this
module with Python and no console.

The analyst, 15 Oct 2026: *"i am looking for a single script that can be
executed with its gui that selects files or something"*.

Everything the window does is the ``book`` and ``peers pull`` commands; the
window only writes the book's files into the folder picked, with the folder's
own paths, the latest quarter typed and the internal file chosen, and says
what each step printed. The settings in the book are the book's; nothing here
supplies a value the book does not state, except the two below, which the
window shows as it uses them:

- the FDIC pull starts at the book's first quarter and records mergers from
  2005-01-01, as ``books/README.md`` does;
- an internal file's net and gross charge-off rates are mapped to the book's
  Net and Gross charge-offs (both are calculated as the public series are,
  ``docs/INTERNAL-IMPORT.md``); its past-due measures stay on the Internal
  tab, because whether an internal 30+ includes nonaccrual loans is not known.
"""
import json
import os
import pkgutil
import queue
import re
import sys
import threading
import traceback
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
#: The book's files, as shipped: (name in the bundle, file in the repository).
BUNDLE = (("consumer-public.json", ROOT / "books" / "consumer-public.json"),
          ("consumer-public-series.csv", ROOT / "books" / "consumer-public-series.csv"),
          ("peers.json", ROOT / "config" / "peers.json"),
          ("peer-loan-classes.json", ROOT / "config" / "peer-loan-classes.json"),
          ("reporting-changes.json", ROOT / "config" / "reporting-changes.json")) + tuple(
    # The industry from 1990 (peers industry-long): committed series, not rebuilt on site. The series
    # list reaches them as ../data/industry/<file> from the Book folder, so prepare writes them there.
    ("%s_industry-from-1990_%s.csv" % (slug_, kind), ROOT / "data" / "industry" / ("%s_industry-from-1990_%s.csv" % (slug_, kind)))
    for slug_ in ("credit-card", "home-equity", "other-consumer") for kind in ("net", "gross"))
LONG_INDUSTRY = Path("data") / "industry"
BUNDLE = BUNDLE + (("nmdb.json", ROOT / "data" / "signals" / "nmdb.json"),
                   ("fico-under-660.json", ROOT / "data" / "signals" / "fico-under-660.json"))
QUARTER = re.compile(r"^(19|20)\d\dQ[1-4]$")
MERGERS_SINCE = "2005-01-01"
INTERNAL_SOURCE = "KeyBank internal"
INTERNAL_MEASURES = {"net-charge-off-rate": "Net charge-offs", "gross-charge-off-rate": "Gross charge-offs"}
CACHE, BOOK, SEC = "FDIC data", "Book", "SEC filings"


def bundled(name: str) -> bytes:
    """A book file: from inside the one-file app, or the repository."""
    try:
        data = pkgutil.get_data("threshold_engine", "bundle/" + name)
    except (OSError, ValueError):
        data = None
    if data is None:
        data = dict(BUNDLE)[name].read_bytes()
    return data


def problems(folder: str, quarter: str, internal: str, contact: Optional[str] = None) -> List[str]:
    """What stops a step, in words; empty when nothing does. ``contact`` is
    checked only for the step that asks SEC (None: not that step)."""
    out = []
    if contact is not None and not re.search(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", contact):
        out.append("Type a name and a contact email for SEC, for example \"Your Name you@yourbank.com\": SEC "
                   "refuses requests without one. It is not stored.")
    if not folder.strip():
        out.append("Choose a folder for the data and the workbook.")
    if not QUARTER.match(quarter.strip()):
        out.append("Type the latest quarter as YYYYQn, for example 2026Q2.")
    if internal.strip() and not Path(internal.strip()).is_file():
        out.append("The internal file %s does not exist." % internal.strip())
    return out


def prepare(folder, quarter: str, internal: Optional[str], segments: bool) -> Path:
    """Write the book into ``folder/Book`` with this folder's paths, the
    latest quarter and the internal file (or none); return the book's path."""
    folder = Path(folder)
    book_dir = folder / BOOK
    book_dir.mkdir(parents=True, exist_ok=True)
    (folder / CACHE).mkdir(exist_ok=True)
    raw = json.loads(bundled("consumer-public.json").decode("utf-8"))
    for name, _ in BUNDLE[1:]:
        target = ((folder / LONG_INDUSTRY / name) if "_industry-from-" in name
                  else (folder / "data" / "signals" / name) if name in ("nmdb.json", "fico-under-660.json")
                  else (book_dir / name))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundled(name))
    cache = folder / CACHE
    raw["peers"].update(cache=str(cache), mergers=str(cache / "mergers.json"),
                        absorptions=str(cache / "absorptions.json"), roster="peers.json", last=quarter)
    if raw.get("loan_classes") is not None:
        raw["loan_classes"] = {"file": "peer-loan-classes.json", "cache": str(folder / SEC)}
    if raw.get("reporting_changes") is not None:
        raw["reporting_changes"] = "reporting-changes.json"
    if raw.get("large_banks") is not None:
        from .peers import large_banks as LB
        raw["large_banks"] = {"file": str(folder / CACHE / LB.FOLDER / LB.file_name(quarter))}
    if raw.get("signals") is not None:
        from .peers import large_banks as LB
        from . import signals_data as SD
        sig = folder / CACHE / SD.FOLDER
        raw["signals"] = {"balances": str(sig / LB.file_name(quarter)),
                          "originations": str(sig / LB.file_name(quarter).replace("Balances", "Originations")),
                          "survey": str(sig / ("%s.csv" % SD.SURVEY)),
                          "nmdb": str(folder / "data" / "signals" / "nmdb.json"),
                          "fico": str(folder / "data" / "signals" / "fico-under-660.json")}
    raw["internal"] = None if not internal else {
        "file": str(Path(internal).resolve()), "source": INTERNAL_SOURCE, "segments": bool(segments),
        "measures": dict(INTERNAL_MEASURES), "call_report_source": "KeyBank"}
    path = book_dir / "consumer-public.json"
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def pull(folder, quarter: str, say: Callable[[str], None] = print, contact: Optional[str] = None) -> None:
    """Fetch the FDIC quarters the folder does not hold yet, and, when the
    book has a Peer books tab, each peer's filing for the quarter the
    classes file states (its judgements are about those filings)."""
    from .peers import run as peers_run
    book = json.loads(bundled("consumer-public.json").decode("utf-8"))
    raw = book["peers"]
    peers_run.pull(cache=str(Path(folder) / CACHE), first=raw["first"], last=quarter, products=raw["products"],
                   delinquency=bool(raw["delinquency"]), mergers_since=MERGERS_SINCE, refresh=False, say=say)
    if book.get("large_banks") is not None:
        from .peers import large_banks as LB
        LB.pull(Path(folder) / CACHE, quarter, say=say)
    if book.get("signals") is not None:
        from . import signals_data as SD
        SD.pull(Path(folder) / CACHE, quarter, say=say)
    if book.get("loan_classes") is not None:
        from .peers import classes, loan_classes_tab
        tmp = Path(folder) / BOOK
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "peer-loan-classes.json").write_bytes(bundled("peer-loan-classes.json"))
        spec = loan_classes_tab.load(tmp / "peer-loan-classes.json")
        say("SEC filings for %s, as the loan classes file states:" % spec["quarter"])
        classes.pull(Path(folder) / SEC, spec["banks"], spec["quarter"], contact or "", say=say)


def build(folder, quarter: str, internal: Optional[str], segments: bool,
          say: Callable[[str], None] = print) -> Path:
    """Build ``folder/consumer-credit-QUARTER.xlsx`` from the book."""
    from . import book as B
    path = prepare(folder, quarter, internal, segments)
    out = Path(folder) / ("consumer-credit-%s.xlsx" % quarter)
    B.build(path, out, say=say)
    return out


def default_folder() -> str:
    return str(Path.home() / "Documents" / "Consumer credit thresholds")


def main() -> None:                                              # pragma: no cover - the window itself
    import tkinter as tk
    from tkinter import filedialog, ttk

    root = tk.Tk()
    root.title("Consumer credit thresholds")
    root.geometry("860x620")
    pad = dict(padx=10, pady=4)
    lines: "queue.Queue[str]" = queue.Queue()
    busy = {"on": False}

    folder = tk.StringVar(value=default_folder())
    quarter = tk.StringVar(value=json.loads(bundled("consumer-public.json").decode("utf-8"))["peers"]["last"])
    internal = tk.StringVar(value="")
    segments = tk.BooleanVar(value=False)
    contact = tk.StringVar(value="")

    tk.Label(root, text="Consumer credit thresholds", font=("Arial", 16, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", **pad)
    tk.Label(root, justify="left", fg="#57534B", wraplength=820, text=(
        "Builds the workbook from the FDIC's public Call Report data, and the bank's internal file if you "
        "choose one, and each peer's own SEC filing for the Peer books tab. Step 1 downloads only "
        "what the folder does not hold yet. Step 2 takes about "
        "eight minutes, then Excel opens the workbook.")).grid(row=1, column=0, columnspan=3, sticky="w", **pad)

    def row(r, label, var, choose):
        tk.Label(root, text=label, font=("Arial", 10, "bold")).grid(row=r, column=0, sticky="w", **pad)
        tk.Entry(root, textvariable=var, width=78).grid(row=r, column=1, sticky="we", **pad)
        if choose:
            tk.Button(root, text="Choose...", command=choose).grid(row=r, column=2, sticky="w", **pad)

    row(2, "Folder", folder, lambda: folder.set(filedialog.askdirectory(initialdir=folder.get()) or folder.get()))
    row(3, "Latest quarter", quarter, None)
    row(4, "SEC contact", contact, None)
    row(5, "Internal file", internal, lambda: internal.set(filedialog.askopenfilename(
        filetypes=[("CSV", "*.csv"), ("All files", "*.*")]) or internal.get()))
    tk.Checkbutton(root, variable=segments, text="Also add each internal segment as its own series").grid(
        row=6, column=1, sticky="w", **pad)
    tk.Label(root, justify="left", fg="#57534B", wraplength=820, text=(
        "Optional: the bank's file in the internal import layout (docs/INTERNAL-IMPORT.md). Its net and gross "
        "charge-off rates join the workbook as \"KeyBank internal\"; its past-due measures show on the "
        "Internal tab only. Leave it blank for public data only. SEC contact: a name and an email; SEC "
        "refuses requests without one. It is sent to SEC only and not stored.")).grid(row=7, column=0, columnspan=3,
                                                                          sticky="w", **pad)
    buttons = tk.Frame(root)
    buttons.grid(row=8, column=0, columnspan=3, sticky="w", **pad)
    log = tk.Text(root, height=18, wrap="word", font=("Consolas", 9))
    log.grid(row=9, column=0, columnspan=3, sticky="nsew", **pad)
    root.grid_rowconfigure(9, weight=1)
    root.grid_columnconfigure(1, weight=1)
    bar = ttk.Progressbar(root, mode="indeterminate")
    bar.grid(row=10, column=0, columnspan=3, sticky="we", **pad)

    def say(text):
        lines.put(str(text))

    def drain():
        while not lines.empty():
            log.insert("end", lines.get() + "\n")
            log.see("end")
        root.after(200, drain)

    def run(name, fn, asks_sec=False):
        if busy["on"]:
            say("Wait: a step is still running.")
            return
        stop = problems(folder.get(), quarter.get(), internal.get(), contact.get() if asks_sec else None)
        if stop:
            for p in stop:
                say(p)
            return
        busy["on"] = True
        bar.start(12)
        say("== %s" % name)

        def work():
            try:
                fn()
            except Exception as e:                               # every failure is shown, never swallowed
                say("Stopped: %s" % e)
                say(traceback.format_exc())
            finally:
                busy["on"] = False
                root.after(0, bar.stop)
        threading.Thread(target=work, daemon=True).start()

    def do_pull():
        pull(folder.get().strip(), quarter.get().strip(), say=say, contact=contact.get().strip())
        say("Done: the FDIC data is in %s and the SEC filings in %s"
            % (Path(folder.get().strip()) / CACHE, Path(folder.get().strip()) / SEC))

    def do_build():
        out = build(folder.get().strip(), quarter.get().strip(), internal.get().strip() or None, segments.get(),
                    say=say)
        say("Done: %s. Opening it in Excel. If a yellow bar says Protected View, click Enable Editing." % out)
        os.startfile(str(out))

    def open_folder():
        Path(folder.get()).mkdir(parents=True, exist_ok=True)
        os.startfile(folder.get())

    tk.Button(buttons, text="1. Get the data", width=22, command=lambda: run("Getting the data", do_pull, asks_sec=True)
              ).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="2. Build the workbook", width=22,
              command=lambda: run("Building the workbook", do_build)).pack(side="left", padx=(0, 8))
    tk.Button(buttons, text="Open the folder", width=16, command=open_folder).pack(side="left")
    drain()
    root.mainloop()


if __name__ == "__main__":                                       # pragma: no cover
    sys.exit(main())
