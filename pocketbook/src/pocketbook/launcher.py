"""The launcher: the window a person double-clicks. Five steps down the left.

The firm's redesign (docs/redesign-2026-09-26/README.md, "Launcher"), and the
firm on why, 26 Sep 2026: *"just select the workbook first, configure what you
can, and then do the workbook config items so that there are suggestions to be
made … it's just a re-order of screens more or less"*.

    1. Extract              pick the loan file, and the two limits Set up reads its columns with
    2. Set up               read it: what each column is (book.read_extract; nothing is written)
    3. Choose tests         what runs, and on which columns; Next writes the workbook (book.set_up)
    4. Answer in workbook   the professional calls, in Excel; the suggested values are already there
    5. Run                  book.run; a refusal lists each cell still to answer, with Open at

Everything the window says and allows is decided by `Flow`, which knows
nothing of Tk, so a test can drive every state (L1 to L5 in the spec) without
a display. `build()` draws a Flow; tools/shoot_launcher.py photographs it.

Tkinter ships with standard Python on Windows. The cube's add-ons (numpy,
openpyxl, PyYAML) are checked first, without loading them (ruling OC-34):
while any is missing, a banner says which and offers Install now, and Set up
and Run stay off. So nothing at the top of this file may import them; `book`
is imported inside the steps that use it. Anything that goes wrong inside is
said on the page in words, never a traceback: what PocketBook didn't expect
shows its type and message there too, with Copy details for the traceback
(Crash; the bank, 30 Sep 2026).
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import choices as ch
from . import deps, house, places

TITLE = "PocketBook"
SUFFIX = f" - {TITLE}.xlsx"
STEPS = ("Extract", "Set up", "Choose tests", "Answer in workbook", "Run")
START = ["1. Pick the extract, and press Set up: it reads what each column is.",
         "2. Choose the tests, and press Next: the workbook is written beside the extract.",
         "3. In the workbook, fill in the shaded cells, save and close it.",
         "4. Press Run. The results land in the workbook."]
PREFS: Path | None = None   # the launcher's last choices; None: launcher.json in the tool's folder (places.py)
MODES = {"bleed": "Where the book bleeds", "new": "Test new variables"}
FEW = (12, 6, 24)          # the options settings.yaml offers for the two limits, first the recommended one
MANY = (50, 25, 100)


def book_for(extract: str | Path) -> Path:
    """Where the workbook for an extract lives: beside it, named after it (book.book_for, without numpy)."""
    p = Path(extract)
    return p.with_name(f"{p.stem}{SUFFIX}")


def _on(yes: bool) -> str:
    return "normal" if yes else "disabled"


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _s(n: int, word: str) -> str:
    return f"{n:,} {word}" + ("" if n == 1 else "s")


class AddOns:
    """What the window says and allows about the add-ons (OC-34), kept apart
    from Tk so a test can drive it. Set up and Run stay off while anything the
    cube needs is missing, and come on only when a fresh check finds it all."""

    def __init__(self) -> None:
        self.missing = deps.missing()
        self.optional = deps.missing_optional()     # scikit-learn: only finding new variables needs it
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
        """The banner's first line; empty once nothing is missing."""
        if not self.missing:
            return ""
        if self.said and not self.installing:
            return f"Couldn't install {_names(self.missing)} from here. Press Copy for IT and send them the note below."
        return deps.message(self.missing)

    def lines(self) -> list[str]:
        """What the banner says under its first line, or the window once all is in."""
        if self.installing:
            took = int(time.monotonic() - self.began)
            return [f"Installing {_names(self.installing)}... {took // 60}:{took % 60:02d} so far.",
                    "This can take a few minutes. This line says when it's done."]
        if not self.missing:
            return ([f"Installed {_names(self.got)}. Everything PocketBook needs is here.", ""] if self.got else []) + START
        if self.said:
            tail = [ln.strip() for ln in self.said.splitlines() if ln.strip()][-6:]
            return [deps.ask_it(self.missing), "", "What the installer said last:", *("    " + ln for ln in tail)]
        them, theyre = ("it", "it's") if len(self.missing) == 1 else ("them", "they're")
        return [f"Install now downloads {them} from the internet. It takes a minute or two.",
                f"Set up and Run switch on once {theyre} in."]

    def start(self, optional: bool = False) -> list[str]:
        """Mark an install begun, and return the names to hand to deps.install: what the cube needs, or with
        `optional` the optional add-ons that aren't here (scikit-learn, for finding new variables)."""
        names = list(self.optional) if optional and not self.missing else list(self.missing)
        self.installing, self.began, self.said = names, time.monotonic(), ""
        return list(self.installing)

    def finish(self, ok: bool, output: str) -> None:
        """Take the install's answer, and look again for what is still missing."""
        tried, self.installing = self.installing, []
        self.missing = deps.missing()
        self.optional = deps.missing_optional()
        still = [n for n in tried if n in self.missing or n in self.optional]
        self.got = [n for n in tried if n not in still]
        self.said = "" if not still else (output.strip() or "The installer said nothing.")


def waiting_words(missing: list[str]) -> str:
    """The line under the extract box while add-ons are missing. It said "while the add-on installs" with three
    missing and nothing installing yet (walk of 27 Sep 2026)."""
    them = "it is" if len(missing) == 1 else "they are"
    return f"Until {them} in, you can still pick the extract and open a workbook written before."


#: The words the window uses before the workbook explains them, each with its meaning in a line (F, the firm, 27 Sep
#: 2026: "worse at 1.34x", "GCO dollars" and "scouting" were first read on the window, with the meaning only on a
#: tab). A multiple is filled in from the words around it.
TERMS = (("GCO dollars", "GCO dollars: what a loan charged off, in dollars."),
         ("RANR dollars", "RANR dollars: what a loan earned after its losses, in dollars."),
         ("grid", "A grid: every band of one column against every segment of another."),
         ("measures", "Five measures: bad loans, bad dollars, GCOs ($), RANR, and RANR + GCOs."),
         ("worse at", "worse at {x}x: losing {x} times as much as the rest counts as worse."),
         ("better at", "better at {x}x: losing {x} times as much as the rest counts as better."),
         ("scouting", "Scouting: the tree's first look at loans before the cutoff, to pick what to test."))


def plain_words(said: str) -> list[str]:
    """The meaning of each term in `said`, once each."""
    out = []
    for term, meaning in TERMS:
        if term in ("worse at", "better at"):
            m = re.search(term + r" ([0-9.]+)x", said)
            if m:
                out.append(meaning.format(x=m.group(1)))
        elif re.search(r"\b" + term + r"s?\b", said):
            out.append(meaning)
    return out


def banner_clock(widgets: dict, gate: AddOns, optional: bool) -> None:
    """Move the black bar's clock on while the add-ons the cube needs install. An optional add-on's install has no
    bar: the one an earlier install used is gone, and setting its dead line raised inside the loop that waits for
    pip, which then stopped, so the window said "Installing scikit-learn..." for ever (the walk's second run,
    27 Sep 2026)."""
    line = widgets.get("status")
    if optional or line is None or not line.winfo_exists():
        return
    line.configure(text="\n".join(gate.lines()))


def do_set_up(extract: str, choices: ch.Choices | None = None) -> list[str]:
    """Write the workbook (the Next button), in words."""
    from . import book
    if not extract or not Path(extract).exists():
        return ["Pick the extract first (the loan file from the bank: .csv or .xlsx)."]
    try:
        return book.set_up(extract, choices=choices).lines
    except Exception:
        return _crash("Set up stopped").lines()


def do_run(extract: str) -> list[str]:
    """Run the cube (the Run button), in words."""
    return _run(extract).lines


def elapsed_words(seconds: float) -> str:
    """How long a step has taken, as the progress line says it: "12 s", "1 min 40 s"."""
    s = int(seconds)
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60} s"


def _run(extract: str, progress=None):
    from . import book
    target = book_for(extract) if extract else None
    if not extract:
        return book.Outcome(False, Path(), ["Pick the extract first."])
    if book.workbook_picked(extract):
        return book.Outcome(False, Path(extract), [book.workbook_picked(extract)])
    if not target.exists():
        return book.Outcome(False, target, [f"There's no workbook for {Path(extract).name} yet. Choose the tests "
                                            f"and press Next first."])
    from .engine import TieOutError
    try:
        return book.run(target, extract, **({"progress": progress} if progress else {}))
    except TieOutError as exc:
        # walk of 27 Sep 2026: the one check the finished screen shows, when it failed, read "Something went wrong"
        crash = _crash("Run stopped")
        out = book.Outcome(False, target, [f"Run stopped: the grids didn't add up to the book, so nothing was "
                                           f"written. {exc}.", "That is a fault in PocketBook, not in your answers. "
                                           "Press Copy details and send what it copies, to get it fixed."])
    except Exception:
        crash = _crash("Run stopped")
        out = book.Outcome(False, target, crash.lines())
    out.crash = crash           # the window's Copy details reads it; book.Outcome itself knows nothing of the window
    return out


#: The first line an unexpected error shows (the firm, 30 Sep 2026: "It would be a lot easier if these kinds of
#: errors just displayed on screen in the huge white space allotted").
UNEXPECTED = "Something went wrong that PocketBook didn't expect."


@dataclass
class Crash:
    """Something PocketBook didn't expect, as the window shows it: a heading, the error's type and message, and
    the full traceback for Copy details. It used to be a sentence pointing at last-error.txt, which the analyst
    opened in Notepad (at the bank, 30 Sep 2026); the file is still written, but the window says it all."""
    heading: str            # "Run stopped", "Set up stopped"
    kind: str               # the exception's type, e.g. PermissionError
    said: str               # its message
    details: str            # the full traceback: what Copy details puts on the clipboard
    log: Path | None        # where a copy was written, or None when it couldn't be

    def lines(self) -> list[str]:
        out = [UNEXPECTED, f"{self.kind}: {self.said}" if self.said else self.kind,
               "Press Copy details and send what it copies, to get it fixed."]
        if self.log is not None:
            out.append(f"A copy is kept in {self.log}.")
        return out


def _crash(heading: str) -> Crash:
    """The exception being handled, as the window shows it. A copy of the traceback goes to last-error.txt."""
    kind, exc, _ = sys.exc_info()
    detail = traceback.format_exc()
    log: Path | None = places.folder() / "last-error.txt"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(detail, encoding="utf-8")
    except OSError:
        log = None
    return Crash(heading, kind.__name__ if kind else "Error", str(exc) if exc is not None else "", detail, log)


def _open(path: Path) -> str:
    """Open the workbook; what to say when it can't be opened from here (no program for .xlsx, say), else "".
    Walk of 27 Sep 2026: Open at... raised inside the window and the window said nothing."""
    try:
        open_file(path)
    except OSError as exc:
        return (f"Couldn't open {Path(path).name} from here ({exc.strerror or exc}). Open it yourself: it is in "
                f"{Path(path).parent}.")
    return ""


def open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _prefs() -> dict:
    try:
        return json.loads((PREFS or places.kept("launcher.json")).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_prefs(d: dict) -> None:
    try:
        p = PREFS or places.folder() / "launcher.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


# --------------------------------------------------------------------------
# What the window shows, without the window


@dataclass
class Step:
    name: str
    mark: str           # done, current, todo, blocked
    sub: str = ""


@dataclass
class Need:
    """One answer a refused Run is waiting for."""
    sheet: str | None   # the tab, when the refusal names one
    cell: str | None    # the cell, when it names one
    says: str           # the question, in words

    @property
    def tag(self) -> str:
        return " ".join(x for x in (self.sheet, self.cell) if x).upper()


_CELL = re.compile(r"^(?P<sheet>[A-Z][A-Za-z ]*?)!(?P<cell>[A-Z]{1,3}\d+)(?: and [^:]*)?: (?P<rest>.+)$", re.S)
_TAB = re.compile(r"^(?P<sheet>Control|Columns|Odd values|Look): (?P<rest>.+)$", re.S)


def needs_of(problems: list[str]) -> list[Need]:
    """A refused Run's problems as the list L3 shows: the tab and cell, and the
    question in as few words as it takes."""
    out = []
    for p in problems:
        m = _CELL.match(p) or _TAB.match(p)
        if not m:
            out.append(Need(None, None, p))
            continue
        rest = m.group("rest").strip()
        q = re.match(r'^"(.+?)" (needs an answer|is chosen in the launcher)', rest)
        if q:
            says = q.group(1) + (": choose it in the launcher" if q.group(2).startswith("is chosen") else "")
        elif m.groupdict().get("cell") == "C3" and m.group("sheet") == "Columns":
            says = "Checked every column? Set it to Yes once you have."
        else:
            says = rest
        out.append(Need(m.group("sheet"), m.groupdict().get("cell"), says))
    return out


#: the tabs a refused Run names, in the workbook's own order
TAB_ORDER = ("Control", "Columns", "Look")


def in_order(needs: list[Need]) -> list[Need]:
    """The needs top to bottom as the workbook shows them: Control's rows first, then Columns', each by its row, then
    anything that names no cell, as it came. The walk of 27 Sep 2026 read C15, C18, C19, C16, C17, C20."""
    def key(n: Need):
        tab = TAB_ORDER.index(n.sheet) if n.sheet in TAB_ORDER else len(TAB_ORDER)
        row = int(re.sub(r"\D", "", n.cell)) if n.cell else 0
        return (tab, row) if n.sheet else (len(TAB_ORDER) + 1, 0)
    return sorted(needs, key=key)


# the Choose tests table's groups, top to bottom: what can be cut into bands (and split), what can segment, what is
# measured; the key, the date and anything else, greyed, last
GROUP = {"num": 0, "cat": 1, "year": 1, "out": 2, "outd": 2}
LAST = 3
ROW_H = 22          # px a table row is tall; each is ruled off below by 1 px
NO_OUTCOME = "Pick the outcome: the yes/no column where 1 means the loan went bad. Nothing is picked for you."
BASE_W = (104, 128, 84, 84, 70, 70, 70)  # px the Choose tests columns start at; the word columns take any width more
GAP = 6             # px between two groups



def window_size(screen_w: int, screen_h: int) -> tuple[int, int]:
    """The window's first size: as much of the screen as leaves room for the taskbar, 720 x 560 at the least and
    1180 x 860 at the most."""
    return max(720, min(1180, screen_w - 120)), max(560, min(860, screen_h - 140))


def table_height(rows: list[dict]) -> int:
    """How tall the Choose tests table draws: each row and its rule, and a gap where a group starts."""
    return sum(ROW_H + 1 + (GAP if r["gap_before"] else 0) for r in rows)

class Flow:
    """The launcher's state and every rule about it. The window draws what this
    says; a test drives it the way a person would."""

    def __init__(self, gate: AddOns | None = None, extract: str = "", few: int = FEW[0], many: int = MANY[0]):
        self.gate = gate or AddOns()
        self.extract = extract
        self.few, self.many = few, many
        self.page = "extract"         # extract, choose, answer, needs, done
        self.read = None              # book.Read, once Set up has read the extract
        self.mode = "bleed"
        self.cut: set[str] = set()
        self.seg: set[str] = set()
        self.split: str | None = None
        self.filter: str | None = None   # Filter by: the Grids' Only loans where column (the firm, 30 Sep 2026)
        self.filter2: str | None = None  # Filter 2: "and <column> is" (the firm, 30 Sep 2026: two filters)
        self.outcome: str | None = None
        self.asking: str | None = None  # a column picked as the outcome, waiting for the analyst's yes
        self.test: list[str] = []
        self.hold: list[str] = []
        self.shortlist: str | None = None
        self.spec = None              # the saved shortlist, loaded: its column and strata
        self.spec_problem: str | None = None
        self.written = None           # book.Outcome of the last Next
        self.needs: list[Need] = []
        self.answers = True           # the needs are answers the workbook is waiting for; False: the Run stopped
        self.note: list[str] = []     # good news for the current page (an install that worked), never in red
        self.finished = None          # book.Outcome of the last Run that finished
        self.finished_at, self.took = "", 0.0
        self.book_open = False
        self.message: list[str] = []  # a line or two for the current page: what went wrong, or what was done
        self.crash: Crash | None = None   # something PocketBook didn't expect: shown in the page's own space
        self.busy = ""
        self.stage, self.began = "", 0.0     # the progress line while busy: what is being done, since when

    # ---- where things stand

    def progress(self, stage: str) -> None:
        """What Set up or Run is doing now. Called from the worker thread: it only sets a string the window reads."""
        self.stage = stage

    def progress_line(self, now: float | None = None) -> str:
        """The line under a busy page: "Running the shuffle test… 1 min 40 s", the time since the button was
        pressed (the firm, 30 Sep 2026: "it seemed pocketbook hanging")."""
        if not self.busy:
            return ""
        took = (time.monotonic() if now is None else now) - self.began
        return f"{self.stage or self.busy}… {elapsed_words(took)}"

    def book(self) -> Path | None:
        return book_for(self.extract) if self.extract else None

    def screen(self) -> str:
        if self.gate.missing:
            return "L4"
        return {"extract": "L1", "choose": "L2", "answer": "L2b", "needs": "L3", "done": "L5"}[self.page]

    def states(self) -> dict[str, str]:
        """Each button's state, by the name build() gives it."""
        ready = not self.gate.missing and not self.busy
        b = self.book()
        ok, _ = self.summary()
        finding = self.mode == "new" and not self.shortlist and self.read is not None
        return {"setup": _on(ready and bool(self.extract) and Path(self.extract).is_file()),
                "next": _on(ready and self.read is not None and ok),
                "install_optional": _on(ready and finding and bool(self.gate.optional) and not self.gate.installing),
                "run": _on(ready and b is not None and b.exists() and not self.book_open),
                "open": _on(not self.busy and b is not None and b.exists()),
                "install": self.gate.states()["install"]}

    def steps(self) -> list[Step]:
        """The rail: each step's marker and the line under it."""
        if self.gate.missing:
            return [Step(n, "todo") for n in STEPS]
        order = ["extract", "choose", "answer", "needs", "done"]
        at = order.index(self.page)
        r = self.read
        subs = ["Pick the loan file" if r is None else f"{r.extract.name} · {r.loans:,} loans",
                "" if r is None else f"{len(r.columns)} columns read",
                MODES[self.mode] if at >= 1 else "",
                "", ""]
        marks = ["todo"] * 5
        if at == 0:
            marks[0] = "current"
        else:
            marks[:2] = ["done", "done"]
            marks[2] = "current" if at == 1 else "done"
            if at >= 2:
                marks[3] = "current"
                subs[3] = "Fill in the shaded cells"
            if at == 3:
                marks[3] = "blocked"
                subs[3] = f"{len(self.needs)} left" if self.answers else "Run stopped"
            if at == 4:
                marks[3:] = ["done", "done"]
                subs[3] = "All answered"
                subs[4] = f"{self.finished_at} · {_s(round(self.took), 'second')}"
        return [Step(n, m, s) for n, m, s in zip(STEPS, marks, subs)]

    # ---- step 1 and 2

    def pick(self, path: str) -> None:
        if path != self.extract:
            self.extract = path
            self.read, self.written, self.finished, self.needs = None, None, None, []
            self.page, self.message, self.crash = "extract", [], None

    def set_up(self) -> None:
        """Read the extract: what each column is. Nothing is written."""
        from . import book
        self.crash = None
        if not self.extract:
            self.message = ["Pick the extract first (the loan file from the bank: .csv or .xlsx)."]
            return
        if not Path(self.extract).is_file():
            self.message = [book.cant_read(self.extract, FileNotFoundError(), "Set up")]
            return
        try:
            got = book.read_extract(self.extract, self.few, self.many)
        except Exception:
            self._stopped("Set up stopped")
            return
        if got.problem:
            self.message = [got.problem]
            return
        self.read, self.message, self.note = got, [], []
        self._defaults(got.chosen)
        self.page = "choose"

    def _kind(self) -> dict[str, str]:
        return {c.name: c.kind for c in self.read.columns} if self.read else {}

    def _columns(self) -> list:
        """The table's columns: the extract's, and ORIG_YEAR when a column is marked Origination date."""
        if self.read is None:
            return []
        return list(self.read.columns) + ([self.read.year] if getattr(self.read, "year", None) else [])

    def _year(self) -> bool:
        """Whether ORIG_YEAR can be picked: a column is marked Origination date and its dates read."""
        y = getattr(self.read, "year", None) if self.read else None
        return y is not None and y.kind == "year"

    def _defaults(self, chosen: ch.Choices | None) -> None:
        """What the table starts on: what the workbook beside the extract already
        shows, or every column its meaning cuts and nothing split."""
        kind = self._kind()
        nums = {c for c, k in kind.items() if k == "num"}
        cats = {c for c, k in kind.items() if k == "cat"}
        self.cut, self.seg, self.split, self.filter, self.filter2 = set(nums), set(cats), None, None, None
        # never picked for the analyst, not even from a workbook an earlier build wrote (the firm, 29 Sep 2026:
        # "there's no reason for it to automatically assign something, especially when it's just wrong")
        self.outcome, self.asking = None, None
        self.test, self.hold, self.shortlist, self.spec = [], [], None, None
        if chosen is None:
            return
        self.mode = "new" if chosen.run_kind == ch.NEW_VARIABLE else "bleed"
        if self.mode == "bleed":
            self.cut = nums if chosen.bands is None else set(chosen.bands) & nums
            self.seg = cats if chosen.segments is None else set(chosen.segments) & cats
            year = {ch.ORIG_YEAR} if self._year() else set()
            self.split = chosen.split if chosen.split in set(kind) | year else None
            self.seg.discard(self.split)                  # a category that splits isn't a segment too
            self.filter = chosen.filter if chosen.filter in cats | year else None
            self.filter2 = chosen.filter2 if chosen.filter2 in cats | year else None
        else:
            self.test = [c for c in chosen.test if c in kind]
            self.hold = [c for c in chosen.hold if c in kind]
        if chosen.shortlist:
            self.pick_shortlist(chosen.shortlist)

    # ---- step 3: the table

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def rows(self) -> list[dict]:
        """The Choose tests table. Each control is None (none on that row) or
        {"on", "radio"}; key and date rows are greyed and carry none; an outcome row in a
        bleed run carries none either, and says nothing about it.

        In the order the analyst works down it, not the extract's (the firm, 27 Sep 2026: "i would prefer that
        screens are ordered more sensibly- this one seems all over the place"): the number columns, then the
        categories, then the outcomes, then the key and date, each group in the extract's order. The same order
        in both run kinds, so the toggle never reshuffles the table."""
        out = []
        locked = self.mode == "new" and self.spec is not None      # the saved shortlist decides
        for c in sorted(self._columns(), key=lambda c: GROUP.get(c.kind, LAST)):
            k = c.kind
            what = c.what
            if c.yes is not None:                  # said as what it holds, never as a guess at what it means
                share = f"1 on {c.yes / max(c.yes + c.no + c.other, 1):.1%} of loans"
                what = f"The outcome · {share}" if c.name == self.outcome else f"Yes/no · {share}"
            row = {"name": c.name, "what": what, "grey": k in ("key", "date", "other", "none"), "a": None,
                   "b": None, "c": None, "d": None, "e": None, "locked": locked, "group": GROUP.get(k, LAST)}
            row["gap_before"] = bool(out) and out[-1]["group"] != row["group"]     # a new group starts here
            if c.name == self.outcome:
                pass                                                  # the outcome is neither tested nor held
            elif self.mode == "bleed":
                if k == "num":
                    row["a"] = {"on": c.name in self.cut and self.split != c.name, "radio": False}
                    row["c"] = {"on": self.split == c.name, "radio": True}
                if k == "cat":
                    # a category splits too (the firm, 29 Sep 2026: "system flag and origination FICO and asset
                    # segment"); it segments or splits, never both
                    row["b"] = {"on": c.name in self.seg and self.split != c.name, "radio": False}
                    row["c"] = {"on": self.split == c.name, "radio": True}
                if k == "year":
                    row["c"] = {"on": self.split == c.name, "radio": True}          # the years split too
                if k in ("cat", "year"):
                    # Filter by (the firm, 30 Sep 2026): the Grids' Only loans where, apart from the split
                    row["d"] = {"on": self.filter == c.name, "radio": True}
                    # Filter 2 (the firm, 30 Sep 2026: "independently and in conjunction with each other")
                    row["e"] = {"on": self.filter2 == c.name, "radio": True}
            else:
                if k in ("num", "cat"):
                    row["b"] = {"on": c.name in self.test, "radio": False}
                    row["c"] = {"on": c.name in self.hold, "radio": False}
            if self.mode == "new" and c.yes is not None:
                row["a"] = {"on": self.outcome == c.name, "radio": True}
            out.append(row)
        return out

    def heads(self) -> tuple[str, str, str, str, str]:
        return ("Outcome", "Test it", "Hold fixed", "", "") if self.mode == "new" else \
            ("Cut into bands", "Segment by", "Split by", "Filter 1", "Filter 2")

    def click(self, name: str, which: str) -> None:
        """A box ticked or a radio picked on the row for `name` (which: a, b, c, d or e)."""
        row = next((r for r in self.rows() if r["name"] == name), None)
        if row is None or row[which] is None or (row["locked"] and which != "a"):
            return
        if self.mode == "bleed":
            if which == "a":
                self.cut ^= {name}
                if self.split == name:
                    self.split = None
            elif which == "b":
                self.seg ^= {name}
                if self.split == name:
                    self.split = None
            elif which == "d":
                self.filter = None if self.filter == name else name   # one column filters, or none; the split stays
            elif which == "e":
                self.filter2 = None if self.filter2 == name else name     # Filter 2: another column, or none
            else:
                self.split = None if self.split == name else name     # one column splits, or none
                self.cut.discard(name)
                self.seg.discard(name)
        else:
            if which == "a":
                self.pick_outcome(name)
            elif which == "b":
                self.test = [c for c in self.test if c != name] if name in self.test else self.test + [name]
                self.hold = [c for c in self.hold if c != name]       # tested or held fixed, never both
            else:
                self.hold = [c for c in self.hold if c != name] if name in self.hold else self.hold + [name]
                self.test = [c for c in self.test if c != name]

    # ---- the outcome: offered, never picked for you, and confirmed in words

    def outcome_choices(self) -> list:
        """Every column that could be the outcome (book.Column with yes set), in the extract's order."""
        return [c for c in (self.read.columns if self.read else ()) if c.yes is not None]

    def outcome_rule(self, name: str) -> str:
        """How a column is read as the outcome, in counts: what the analyst says yes to."""
        c = next((c for c in self.outcome_choices() if c.name == name), None)
        if c is None:
            return ""
        n = c.yes + c.no + c.other
        rest = "nothing else" if not c.other else \
            f"{_s(c.other, 'loan')} with anything else (blanks too) left out of the outcome rates, and counted"
        return (f"1 means the loan went bad: {c.yes:,} loans ({c.yes / max(n, 1):.1%}). 0 means it didn't: "
                f"{c.no:,}. {rest[0].upper() + rest[1:]}.")

    def pick_outcome(self, name: str | None) -> None:
        """A column picked as the outcome: asked about before it counts (the firm: "it should be a pop-up to
        say explicitly this is going to be what our outcome is")."""
        if name is None or name == self.outcome or (self.mode == "new" and self.spec is not None
                                                    and self.spec.outcome and name != self.spec.outcome):
            return
        if any(c.name == name for c in self.outcome_choices()):
            self.asking = name

    def outcome_question(self) -> str:
        if not self.asking:
            return ""
        return (f"Use {self.asking} as the outcome?\n\n{self.outcome_rule(self.asking)}\n\nEvery bad rate and "
                f"every test is measured against it.")

    def answer_outcome(self, yes: bool) -> None:
        name, self.asking = self.asking, None
        if yes and name:
            self.outcome = name
            self.test = [c for c in self.test if c != name]
            self.hold = [c for c in self.hold if c != name]

    def test_every(self, on: bool) -> None:
        """All or None for Test it: every column that can be tested, in the table's order, or none. All leaves
        a column already held fixed as it is (it can't be both)."""
        if self.mode != "new" or self.spec is not None:
            return
        if not on:
            self.test = []
            return
        more = [r["name"] for r in self.rows() if r["b"] is not None and r["name"] not in self.hold]
        self.test = self.test + [c for c in more if c not in self.test]

    def pick_every(self, which: str, on: bool) -> None:
        """All or None for one column of boxes: Test it for a new variable (test_every), or Cut into bands and
        Segment by for the bleed (the firm, 29 Sep 2026: "Yes"). The split stays as it is, and is never cut too."""
        if self.mode == "new":
            if which == "b":
                self.test_every(on)
            return
        if which not in ("a", "b"):
            return
        names = {r["name"] for r in self.rows() if r[which] is not None} - {self.split}
        if which == "a":
            self.cut = set(names) if on else set()
        else:
            self.seg = set(names) if on else set()

    def pick_shortlist(self, path: str | None) -> None:
        """Confirm a saved shortlist (a pre-spec file) instead of finding one: it names
        the inputs, what is held fixed and, when it says, the outcome, so those boxes
        follow it: Test it ticks every input on the list, in its order, and Hold fixed
        its strata (Goal 2 item 3). Its outcome is picked when the extract has that column."""
        self.shortlist, self.spec, self.spec_problem = path or None, None, None
        if not path:
            return
        from . import prespec
        try:
            self.spec = prespec.load(path)
        except prespec.PreSpecError as exc:
            self.spec_problem = f"{Path(path).name} can't be used: {exc.problems[0]}"
            return
        except OSError as exc:
            self.spec_problem = f"Couldn't read {Path(path).name}: {exc}"
            return
        self.test, self.hold = list(self.spec.columns), list(self.spec.strata)
        if self.spec.outcome and self.spec.outcome != self.outcome:
            self.outcome = None
            self.pick_outcome(self.spec.outcome)             # the file names it; the analyst still says yes

    def choices(self) -> ch.Choices:
        """The table as the workbook gets it."""
        order = [c.name for c in self.read.columns] if self.read else []
        kind = self._kind()
        base = dict(few_values=self.few, many_values=self.many)
        if self.mode == "bleed":
            o = self.outcome
            return ch.Choices(run_kind=ch.BLEED, bands=tuple(c for c in order if c in self.cut and c not in
                                                             (self.split, o)),
                              segments=tuple(c for c in order if c in self.seg and c != o), split=self.split,
                              filter=self.filter or self.filter2, filter2=self.filter2 if self.filter else None,
                              outcome=self.outcome, **base)
        test = [c for c in self.test]
        # the pockets hold the held-fixed columns fixed; one input splits every pocket, as a pre-spec tests it
        return ch.Choices(run_kind=ch.NEW_VARIABLE,
                          bands=tuple(c for c in self.hold if kind.get(c, "num") == "num"),
                          segments=tuple(c for c in self.hold if kind.get(c) == "cat"),
                          split=test[0] if len(test) == 1 else None, outcome=self.outcome, test=tuple(test),
                          hold=tuple(self.hold), shortlist=self.shortlist, **base)

    def split_refused(self) -> str | None:
        """A category picked to split with more values than a split takes: the refusal, in the Run's words."""
        c = next((c for c in self._columns() if c.name == self.split), None)
        if c is None or c.kind not in ("cat", "year") or c.values is None:
            return None
        return ch.too_many_values(c.name, c.values)

    def filter_refused(self) -> str | None:
        """A Filter by with more values than the Grids' filter takes, the same column picked twice, or two filters
        making more views than a grid may have: the refusal, in the Run's words."""
        if self.filter and self.filter == self.filter2:
            return ch.same_filter_twice(self.filter)
        picked = []
        for name in (self.filter, self.filter2):
            c = next((c for c in self._columns() if c.name == name), None)
            if c is None or c.values is None:
                continue
            said = ch.too_many_to_filter(c.name, c.values)
            if said:
                return said
            picked.append((c.name, c.values + getattr(c, "parts", 0)))
        if len(picked) == 2:
            return ch.too_many_views(picked[0][0], picked[0][1], picked[1][0], picked[1][1])
        return None

    def summary(self) -> tuple[bool, str]:
        """The "This will run:" box, and whether Next can be pressed."""
        if self.read is None:
            return False, ""
        if self.mode == "bleed":
            if not self.outcome:
                return False, NO_OUTCOME
            got = self.choices()
            nb, ns = len(got.bands), len(got.segments)
            g = nb * ns
            if not g:
                return False, "Tick at least one band column and one segment column."
            too_many = self.split_refused() or self.filter_refused()
            if too_many:
                return False, too_many
            return True, (f"{_s(nb, 'band column')} × {_s(ns, 'segment column')} = {_s(g, 'grid')}, five measures "
                          f"each" + (f"; split by {self.split} adds {g} more." if self.split else ".")
                          + (f" Grids can show only the loans of one {got.filter}"
                             + (f", one {got.filter2}, or both at once." if got.filter2 else ".")
                             if got.filter else ""))
        if self.shortlist:
            if self.spec is None:
                return False, self.spec_problem or ""
            if not self.outcome:
                return False, NO_OUTCOME
            held = f", with {_names(list(self.spec.strata))} held fixed" if self.spec.strata else ""
            cols = list(self.spec.columns)
            what = cols[0] if len(cols) == 1 else f"{_s(len(cols), 'input')} ({', '.join(cols)})"
            return True, (f"the saved shortlist {Path(self.shortlist).name}: {what} against "
                          f"{self.outcome or 'the outcome'}{held}, confirmed on the loans it held back.")
        if "scikit-learn" in self.gate.optional:
            # Goal 2 item 9: finding needs the forest; confirming a saved shortlist doesn't
            return False, (f"{deps.message(['scikit-learn'])} Press Install scikit-learn, or confirm a saved "
                           f"shortlist instead.")
        if not self.outcome:
            return False, NO_OUTCOME
        if not self.test:
            return False, "Tick at least one input to test."
        # OC-51: the tree is built on the loans before the cutoff picked on Control, and checked on the rest
        n = len(self.test)
        held = f", with and without {_names(self.hold)} held fixed" if self.hold else ""
        return True, (f"{_s(n, 'input')} ({', '.join(self.test)}) against {self.outcome}{held}: found on the loans "
                      f"made before the cutoff you pick on Control, then tested together and one by one on the rest.")

    def next(self) -> None:
        """Write the workbook with these choices (book.set_up keeps any answers already given)."""
        from . import book
        self.crash = None
        try:
            out = book.set_up(self.extract, choices=self.choices(), progress=self.progress)
        except Exception:
            self._stopped("Writing the workbook stopped")
            return
        if not out.ok:
            self.message = out.lines
            return
        self.written, self.message, self.needs, self.finished, self.note = out, [], [], None, []
        self.page = "answer"
        self.refresh()

    def suggested_line(self) -> str:
        """The suggested values Set up worked out, as the answer page says them."""
        got = (self.written.summary or {}) if self.written else {}
        vals, fb = got.get("suggested") or {}, got.get("fallback") or set()
        said = {"min_loans": "fewest loans {:,.0f}", "worse_at": "worse at {:.2f}x", "better_at": "better at {:.2f}x"}
        parts = [said[k].format(v) for k, v in vals.items() if k in said and k not in fb]
        if not parts:
            return ""
        return (f"Worked out from this extract: {'; '.join(parts)}. Each sits beside its setting on Control, "
                f"for you to take or not.")

    # ---- steps 4 and 5

    def refresh(self) -> bool:
        """Look again at whether the workbook is open in Excel. True when that changed."""
        from . import book
        b = self.book()
        now = bool(b and book.is_open(b))
        changed, self.book_open = now != self.book_open, now
        return changed

    def _stopped(self, heading: str) -> None:
        """The exception being handled, on the current page: in the page's own space, never in Notepad."""
        self.crash = _crash(heading)
        self.message = self.crash.lines()

    def run(self) -> None:
        began = time.monotonic()
        self.crash = None
        out = _run(self.extract, self.progress)
        self.crash = getattr(out, "crash", None)
        if out.ok:
            self.finished, self.took = out, time.monotonic() - began
            self.finished_at = datetime.now().strftime("%H:%M")
            self.needs, self.message, self.page = [], [], "done"
        else:
            self.answers = bool(out.problems)
            self.needs = in_order(needs_of(out.problems)) if out.problems else [Need(None, None, x) for x in out.lines]
            self.message, self.page = [], "needs"
        self.refresh()

    def open_at(self, need: Need | None = None, sheet: str = "Start here", cell: str = "A1") -> str:
        """Open the workbook at a cell. Returns what to say when the cell couldn't be picked
        for it (the workbook is already open): which cell to go to."""
        from . import book
        b = self.book()
        if need is not None:
            sheet, cell = need.sheet or "Start here", need.cell or "A1"
        moved = book.open_at(b, sheet, cell)
        said = _open(b)
        if said:
            return said + f" Then go to {sheet} {cell}."
        return "" if moved else f"Go to {sheet} {cell}: the workbook was already open, so it opened where it was."

    def open_book(self) -> str:
        """The Open the workbook button: what to say, or "" once it is opening."""
        b = self.book()
        if not (b and b.exists()):
            return "There's no workbook yet. Choose the tests and press Next first."
        return _open(b)

    def go(self, index: int) -> None:
        """A done step on the rail, pressed: back to that step."""
        page = {0: "extract", 1: "choose", 2: "choose", 3: "answer"}.get(index)
        if page == "choose" and self.read is None:
            return
        if page == "answer" and not (self.book() and self.book().exists()):
            return
        if page:
            self.page, self.message, self.crash = page, [], None

    def needs_head(self) -> tuple[str, str]:
        """The L3 page's title and the line under it. A Run that stopped for a reason other than an answer (a
        fault, a file it couldn't write) is not "1 answer needed", which is what it said on the walk of 27 Sep."""
        if not self.answers:
            return "Run stopped", "Nothing was written. Your answers so far are kept."
        return (f"{_s(len(self.needs), 'answer')} needed before Run",
                "Each one opens the workbook at its cell. Nothing ran; your answers so far are kept.")

    def after_install(self, optional: bool) -> None:
        """What the page says once an install ends and nothing the cube needs is missing: an optional add-on that
        didn't install is the note for IT, in red; one that did is good news, never in the red of a refusal."""
        if optional and self.gate.optional:
            self.message = [f"Couldn't install {_names(self.gate.optional)} from here.", deps.ask_it(self.gate.optional)]
            self.note = []
        else:
            self.note, self.message = self.gate.lines()[:1], []

    def headline(self) -> dict:
        """The Run-finished tiles."""
        return (self.finished.summary or {}) if self.finished else {}

    def first_lines(self) -> list[str]:
        """The Run's first two lines, under the finished screen's tiles (J, the firm, 27 Sep 2026): where to start
        reading, and a pre-spec changed after a held-back run when there is one. They were built and never shown."""
        return list(self.headline().get("first") or [])[:2]

    def meanings(self) -> list[str]:
        """A plain meaning for each term the window uses first on this page (F, the firm, 27 Sep 2026), one line
        each, in the order the page shows them."""
        if self.page == "choose" and self.read is not None:
            said = [r["what"] for r in self.rows()] + [self.summary()[1]]
        elif self.page == "answer":
            said = [self.suggested_line()]
        else:
            return []
        return plain_words(" ".join(said))


# --------------------------------------------------------------------------
# The window


def finished_tiles(h: dict) -> tuple:
    """The Run-finished tiles: (head, value, under it, rule colour, value colour). There is no tie-out tile: a Run
    whose grids don't add up stops and writes nothing, so "702 / 702" could never read anything else (B, the firm,
    27 Sep 2026: "It is the slowest way to communicate a check figure. If it didn't tie out what would happen now")."""
    if h.get("kind") == "confirm":
        return confirm_tiles(h)
    gco = h.get("gco")
    worse = h.get("worse", 0)
    what = "GCOs" if gco else (h.get("measure") or "the outcome").lower()
    # Borderline (the firm, 29 Sep 2026): how many of them turn on a shuffled p-value that near the bar
    near = h.get("borderline", 0)
    return (("Pockets worse and material", f"{worse:,}", f"{what}, of {h.get('pockets', 0):,}"
             + (f" · {near:,} borderline" if near else ""), "KEY_RED", "INK"),
            ("GCOs above their share" if gco else "Losses above their share",
             _money(h.get("dollars", 0)) if gco else f"{h.get('dollars', 0):,.1f}",
             f"in those {_s(worse, 'pocket')}", "KEY_RED", "INK"))


def confirm_tiles(h: dict) -> tuple:
    """The Run-finished tiles for a test of a new variable (OC-42), from confirmatory.headline: it builds no
    pocket, so the tiles are the confirmation's, on the holdout. (head, value, under it, rule colour, value colour)"""
    if h.get("problem"):
        return (("Confirmatory test", "Not run", h["problem"], "KEY_RED", "INK"),)
    from .confirmatory import follows_words
    said, under, clean = follows_words(h)
    follows = ("Follows the pre-spec", said, under, "INK", "POSITIVE" if clean else "CRIMSON" if h.get("changed")
               else "INK")
    n = len(h.get("candidates") or [h.get("column")])
    if n > 1:
        # several candidates' groups hold the same loans, so their shares of bad loans don't add up: count the
        # candidates with a group worse instead (Goal 2 item 3)
        return (("Groups worse than their reference", f"{h['worse']:,} of {h['groups']:,}",
                 f"on the holdout, {h['confidence']:.0%} sure", "KEY_RED", "INK"),
                ("Candidates with a group worse", f"{h['holding']:,} of {n:,}", "on the holdout", "KEY_RED", "INK"),
                follows)
    # the column named: "Groups worse than 11,000 - 14,999" alone didn't say whose groups (walk of 27 Sep 2026)
    return ((f"{h['column']} groups worse than {h['reference']}", f"{h['worse']:,} of {h['groups']:,}",
             f"on the holdout, {h['confidence']:.0%} sure", "KEY_RED", "INK"),
            ("Their share of bad loans", f"{h['capture']:.0%}", "on the holdout", "KEY_RED", "INK"),
            follows)


def _money(v: float) -> str:
    a = abs(v)
    if a >= 1e9:
        return f"${v / 1e9:.2f}B"
    if a >= 1e6:
        return f"${v / 1e6:.2f}M"
    if a >= 1e4:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.0f}"


def wheel_target(table, exists: bool, delta: int = 0, num=None) -> tuple[object | None, int]:
    """What one turn of the mouse wheel scrolls, and by how many rows: the table on the page shown now, or nothing
    when that page has none or has gone (at the bank, 30 Sep 2026: a wheel bound to Choose tests' own table raised
    "invalid command name ...!canvas" after Next). `num` 4 and 5 are X11's wheel; `delta` Windows' (120 a notch)."""
    if table is None or not exists:
        return None, 0
    if num in (4, 5):
        return table, -1 if num == 4 else 1
    return table, int(-delta / 120) or (-1 if delta > 0 else 1 if delta < 0 else 0)


def relight(lit: str | None, hover: str | None, picked: str | None) -> tuple[str | None, dict[str, bool]]:
    """The Choose table's tinted row: the one pointed at, else the one last clicked. Returns that row and the rows
    to repaint, each True to tint it or False to put it back to white."""
    want = hover or picked
    return want, {n: n == want for n in {lit, want} - {None}}


def build(root) -> dict:
    """The window's widgets on `root`, drawn from a Flow. Split from main() so the
    harness in tools/shoot_launcher.py can press the buttons and photograph each state."""
    import tkinter as tk
    from tkinter import filedialog, font as tkfont, ttk

    C = {k: house.tk(v) for k, v in house.PALETTE.items()}
    C.update(DISABLED=house.tk(house.DISABLED_TEXT), RULE=house.tk(house.ROW_RULE), WHITE=house.tk(house.PAPER))
    root.title(TITLE)
    # as much of the screen as is comfortable, not a fixed 720 x 560 (the firm, 29 Sep 2026: "there's a lot of
    # white space to use, and it should really use it so that I can see everything")
    root.geometry("{}x{}".format(*window_size(root.winfo_screenwidth(), root.winfo_screenheight())))
    root.minsize(640, 500)
    root.configure(bg=C["WHITE"])

    prefs = _prefs()
    flow = Flow(extract=prefs.get("extract", ""), few=prefs.get("few", FEW[0]), many=prefs.get("many", MANY[0]))
    extract = tk.StringVar(value=flow.extract)
    widgets: dict = {"extract": extract, "flow": flow, "gate": flow.gate}
    # sizes in pixels, as the spec gives them (Tk reads a negative size as pixels)
    F = {"title": ("Arial", -18, "bold"), "body": ("Arial", -13), "small": ("Arial", -12),
         "bold": ("Arial", -13, "bold"), "step": ("Arial", -13, "bold"), "sub": ("Arial", -11),
         "tag": ("Arial", -11, "bold"), "tile": ("Arial", -22, "bold"), "app": ("Arial", -15, "bold"),
         "head": ("Arial", -11, "bold"), "name": ("Arial", -12, "bold"), "cell": ("Arial", -12),
         "toggle": ("Arial", -11, "bold"), "h2": ("Arial", -17, "bold")}

    class Button(tk.Canvas):
        """A button with rounded corners (radius 6): primary is Key Red, secondary white with a Stone border,
        disabled Mist with grey text. `state` is the canvas's own option, so cget("state") reads it."""

        def __init__(self, master, text, command, kind="secondary"):
            self._text, self._cmd, self._kind = text, command, kind
            self._font = tkfont.Font(family="Arial", size=-13, weight="bold")
            super().__init__(master, height=30, width=self._font.measure(text) + 28, highlightthickness=0, bd=0,
                             bg=master.cget("bg"), cursor="hand2")
            self.bind("<Button-1>", lambda e: self.invoke())
            self._draw()

        def invoke(self):
            if str(self.cget("state")) != "disabled" and self._cmd:
                return self._cmd()

        def configure(self, cnf=None, **kw):
            if "text" in kw:
                self._text = kw.pop("text")
                kw["width"] = self._font.measure(self._text) + 28
            got = super().configure(cnf, **kw)
            self._draw()
            return got

        config = configure

        def cget(self, key):
            return self._text if key == "text" else super().cget(key)

        def _draw(self):
            if not hasattr(self, "_font"):
                return
            self.delete("all")
            w, h = int(super().cget("width")), int(super().cget("height"))
            off = str(super().cget("state")) == "disabled"
            fill, line, fg = ((C["MIST"], C["MIST"], C["DISABLED"]) if off else
                              (C["KEY_RED"], C["KEY_RED"], C["WHITE"]) if self._kind == "primary" else
                              (C["WHITE"], C["STONE"], C["INK"]))
            r = 6
            x1, y1, x2, y2 = 1, 1, w - 2, h - 2
            pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2,
                   x1, y2 - r, x1, y1 + r, x1, y1]
            self.create_polygon(pts, smooth=True, fill=fill, outline=line)
            self.create_text(w // 2, h // 2, text=self._text, fill=fg, font=self._font)

    def box(master, on, radio, command, enabled=True):
        """A tick box or radio button, 16 px: Ink when on, a Stone outline when off. Its click always goes to
        `command`, which may ignore it; paint() redraws it in place."""
        c = tk.Canvas(master, width=18, height=18, highlightthickness=0, bd=0, bg=master.cget("bg"))
        c.bind("<Button-1>", lambda e: command() if c.enabled else None)
        paint(c, on, radio, enabled)
        return c

    def paint(c, on, radio, enabled=True):
        c.delete("all")
        c.enabled = enabled
        c.configure(cursor="hand2" if enabled else "")
        col = C["INK"] if on else C["STONE"]
        if not enabled:
            col = C["STONE"]
        if radio:
            c.create_oval(2, 2, 16, 16, outline=col, width=1.5, fill=(C["INK"] if on and enabled else
                                                                       C["STONE"] if on else C["WHITE"]))
            if on:
                c.create_oval(6, 6, 12, 12, fill=C["WHITE"], outline="")
        else:
            c.create_rectangle(2, 2, 16, 16, outline=col, width=1.5,
                               fill=(C["INK"] if on and enabled else C["STONE"] if on else C["WHITE"]))
            if on:
                c.create_line(5, 9, 8, 12, 13, 5, fill=C["WHITE"], width=2)

    def row_light(line, name):
        """The firm, 30 Sep 2026: "it would be nice if it highlighted the row you're clicking in when the button is
        far away from the column names". Pointing at any part of a row tints all of it, name through boxes; a click
        keeps it tinted after the pointer leaves, until another row is clicked."""
        def over(on):
            widgets["hover_row"] = name if on else None
            light_rows()

        def click(e):
            widgets["picked_row"] = name
            light_rows()
        todo = [line]
        while todo:
            w = todo.pop()
            todo.extend(w.winfo_children())
            w.bind("<Enter>", lambda e: over(True), add="+")
            w.bind("<Leave>", lambda e: over(False), add="+")
            w.bind("<Button-1>", click, add="+")

    def light_rows():
        want, paint_ = relight(widgets.get("lit_row"), widgets.get("hover_row"), widgets.get("picked_row"))
        for name, on in paint_.items():
            line = widgets.get(f"row_{name}")
            if line is None or not line.winfo_exists():
                continue
            todo, bg = [line], C["CANVAS"] if on else C["WHITE"]
            while todo:
                w = todo.pop()
                todo.extend(w.winfo_children())
                w.configure(bg=bg)
        widgets["lit_row"] = want

    # ---- the frame: banner (L4 only), then the rail and the page
    banner = tk.Frame(root, bg=C["INK"])
    body = tk.Frame(root, bg=C["WHITE"])
    body.pack(fill="both", expand=True, side="bottom")
    rail = tk.Frame(body, bg=C["CANVAS"], width=196)
    rail.pack(side="left", fill="y")
    rail.pack_propagate(False)
    tk.Frame(body, bg=C["MIST"], width=1).pack(side="left", fill="y")
    page = tk.Frame(body, bg=C["WHITE"], padx=20, pady=18)
    page.pack(side="left", fill="both", expand=True)

    def clear(w):
        for child in w.winfo_children():
            child.destroy()

    def label(master, text, font="body", fg="INK", bg=None, wrap=0, **kw):
        return tk.Label(master, text=text, font=F[font], fg=C[fg], bg=bg or master.cget("bg"), anchor="w",
                        justify="left", wraplength=wrap, **kw)

    def fit(lab, less=4):
        """A label's lines wrap at the width it is given, not a fixed one (the firm: use the window)."""
        lab.bind("<Configure>", lambda e: lab.configure(wraplength=max(e.width - less, 120)))
        return lab

    def draw_rail():
        clear(rail)
        faded = bool(flow.gate.missing)
        ink = C["STONE"] if faded else C["INK"]
        label(rail, TITLE, "app", bg=C["CANVAS"], fg="STONE" if faded else "INK").pack(anchor="w", padx=16,
                                                                                      pady=(18, 6))
        tk.Frame(rail, bg=C["STONE"] if faded else C["KEY_RED"], height=3, width=160).pack(anchor="w", padx=16,
                                                                                            pady=(0, 14))
        for i, st in enumerate(flow.steps()):
            row = tk.Frame(rail, bg=C["CANVAS"])
            row.pack(anchor="w", fill="x", padx=14, pady=5)
            m = tk.Canvas(row, width=23, height=23, highlightthickness=0, bd=0, bg=C["CANVAS"])
            m.pack(side="left", anchor="n")
            if st.mark == "done":
                m.create_oval(1, 1, 22, 22, fill=ink, outline=ink)
                m.create_text(11, 12, text="✓", fill=C["WHITE"], font=("Arial", -11, "bold"))
            elif st.mark in ("current", "blocked"):
                m.create_oval(1, 1, 22, 22, fill=C["KEY_RED"], outline=C["KEY_RED"])
                m.create_text(11, 12, text="!" if st.mark == "blocked" else str(i + 1), fill=C["WHITE"],
                              font=("Arial", -11, "bold"))
            else:
                m.create_oval(2, 2, 21, 21, outline=C["STONE"], width=1.5)
                m.create_text(11, 12, text=str(i + 1), fill=C["STONE"], font=("Arial", -11))
            words = tk.Frame(row, bg=C["CANVAS"])
            words.pack(side="left", padx=(8, 0), fill="x")
            name = label(words, st.name, "step", bg=C["CANVAS"],
                         fg="STONE" if faded or st.mark == "todo" else "INK")
            name.pack(anchor="w")
            if st.sub:
                label(words, st.sub, "sub", bg=C["CANVAS"], fg="CRIMSON" if st.mark == "blocked" else "SLATE",
                      wrap=140).pack(anchor="w")
            if st.mark == "done" and not faded:
                for w in (row, m, words, name):
                    w.bind("<Button-1>", lambda e, i=i: (flow.go(i), render()))
                    w.configure(cursor="hand2")

    def draw_banner():
        clear(banner)
        if not flow.gate.missing:
            banner.pack_forget()
            return
        banner.pack(fill="x", side="top", before=body)
        inner = tk.Frame(banner, bg=C["INK"], padx=16, pady=10)
        inner.pack(fill="x")
        words = tk.Frame(inner, bg=C["INK"])
        words.pack(side="left", fill="x", expand=True)
        widgets["headline"] = label(words, flow.gate.headline(), "bold", fg="WHITE", bg=C["INK"], wrap=500)
        widgets["headline"].pack(anchor="w")
        widgets["status"] = label(words, "\n".join(flow.gate.lines()), "small", fg="STONE", bg=C["INK"], wrap=500)
        widgets["status"].pack(anchor="w")
        buttons = tk.Frame(inner, bg=C["INK"])
        buttons.pack(side="right", anchor="n")
        failed = flow.gate.said and not flow.gate.installing
        widgets["install"] = Button(buttons, "Try again" if failed else "Install now", install, "primary")
        widgets["install"].pack(side="right")
        widgets["copy"] = Button(buttons, "Copy for IT", copy_for_it)
        if failed:
            widgets["copy"].pack(side="right", padx=(0, 8))
        tk.Frame(banner, bg=C["KEY_RED"], height=3).pack(fill="x")

    def footer(*made, note=""):
        """The buttons along the bottom, right to left. Each is (name, text, command, kind); the bar is made
        first and the buttons inside it, since a widget packed into a frame made after it is hidden behind it."""
        bar = tk.Frame(page, bg=C["WHITE"])
        bar.pack(side="bottom", fill="x", pady=(10, 0))
        if note:
            label(bar, note, "small", fg="SLATE").pack(side="left")
        for name, text, command, kind in reversed(made):
            widgets[name] = Button(bar, text, command, kind)
            widgets[name].pack(side="right", padx=(8, 0))

    def message_lines(master, lines, fg="CRIMSON"):
        if lines and flow.crash is not None and lines == flow.crash.lines():
            stopped(master, flow.crash.heading, lines)        # something unexpected: the panel, not a red line
        elif lines:
            label(master, "\n".join(lines), "small", fg=fg, wrap=470).pack(anchor="w", pady=(8, 0))

    def stopped(master, heading, lines):
        """What stopped, in the page's own white space (the firm, 30 Sep 2026: "It would be a lot easier if these
        kinds of errors just displayed on screen in the huge white space allotted"): a heading, the reason, and
        Copy details, which puts the traceback on the clipboard to send. Never Notepad."""
        panel = tk.Frame(master, bg=C["WHITE"], highlightbackground=C["KEY_RED"], highlightthickness=1, padx=12,
                         pady=10)
        panel.pack(fill="x", pady=(10, 0))
        if heading:
            label(panel, heading, "h2", fg="CRIMSON").pack(anchor="w")
        widgets["crash"] = fit(label(panel, "\n".join(lines), "body"), 8)
        widgets["crash"].pack(fill="x", anchor="w", pady=(6, 10))
        if flow.crash is not None:
            b = Button(panel, "Copy details", lambda: copy_details(b))
            b.pack(anchor="w")
            widgets["copy_details"] = b

    def page_extract():
        label(page, "Pick the loan extract", "title").pack(anchor="w")
        if flow.gate.missing:
            pass
        else:
            label(page, "One row per loan, as a .csv or .xlsx. Set up reads it and guesses what each column "
                        "means. The workbook is written beside it once you've chosen the tests. The extract "
                        "itself is never changed.", "body", fg="SLATE", wrap=470).pack(anchor="w", pady=(8, 12))
        row = tk.Frame(page, bg=C["WHITE"])
        row.pack(fill="x", pady=(8 if flow.gate.missing else 0, 0))
        entry = tk.Entry(row, textvariable=extract, font=F["body"], relief="solid", bd=1,
                         highlightthickness=0, fg=C["INK"])
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        entry.xview_moveto(1)        # the file name, not the front of a long folder path, is what shows
        widgets["browse"] = Button(row, "Browse…", browse)
        widgets["browse"].pack(side="left", padx=(8, 0))
        if flow.gate.missing:
            label(page, waiting_words(flow.gate.missing),
                  "body", fg="SLATE", wrap=470).pack(anchor="w", pady=(10, 0))
        else:
            how = tk.Frame(page, bg=C["WHITE"], highlightbackground=C["MIST"], highlightthickness=1)
            how.pack(fill="x", pady=(14, 0))
            label(how, "▾ How Set up recognises columns", "bold", bg=C["CANVAS"]).pack(fill="x", ipady=4, ipadx=8)
            # the firm, 29 Sep 2026: side by side, 12 and 50 read like one scale; they are for different columns
            for text, key, opts in (("Number columns: this many values or fewer is a category; more is cut into "
                                     "bands", "few", FEW),
                                    ("Text columns: more values than this is too many to cut by (text is never "
                                     "cut into bands)", "many", MANY)):
                line = tk.Frame(how, bg=C["WHITE"])
                line.pack(fill="x", padx=8, pady=4)
                label(line, text, "body", wrap=320).pack(side="left")
                var = tk.StringVar(value=f"{getattr(flow, key)} values")
                pickb = ttk.Combobox(line, textvariable=var, values=[f"{o} values" for o in opts], width=11,
                                     state="readonly", font=F["body"])
                pickb.pack(side="right")

                def chosen(e, key=key, var=var):
                    setattr(flow, key, int(var.get().split()[0]))
                    _save_prefs({"extract": extract.get(), "few": flow.few, "many": flow.many})
                pickb.bind("<<ComboboxSelected>>", chosen)
                widgets[key] = pickb
        message_lines(page, flow.note, fg="INK")
        message_lines(page, flow.message)
        setup = ("setup", "Set up from this extract", lambda: background(flow.set_up, "Reading the extract"),
                 "primary")
        if flow.gate.missing:
            footer(("open", "Open the workbook", open_book, "secondary"), setup)
        else:
            footer(setup)

    def page_choose():
        # The firm, 29 Sep 2026: a click "blinks, scroll[s] all the way up and then I have to find where I was
        # again", and "there's a lot of white space to use". So a click repaints its own boxes in place, a redraw
        # keeps the table where it was scrolled, and the table takes the window's height and width.
        top = tk.Frame(page, bg=C["WHITE"])
        top.pack(fill="x")
        label(top, "What are you running?", "h2").pack(side="left")
        toggle = tk.Frame(top, bg=C["WHITE"], highlightbackground=C["INK"], highlightthickness=1)
        toggle.pack(side="right")
        for mode, text in MODES.items():
            on = flow.mode == mode
            t = tk.Label(toggle, text=text, font=F["toggle"], fg=C["WHITE"] if on else C["INK"],
                         bg=C["INK"] if on else C["WHITE"], padx=8, pady=4, cursor="hand2")
            t.pack(side="left")
            t.bind("<Button-1>", lambda e, m=mode: (flow.set_mode(m), render()))
            widgets[f"mode_{mode}"] = t
        # the outcome: offered, never picked for you, and asked about before it counts
        pick = tk.Frame(page, bg=C["WHITE"])
        pick.pack(fill="x", pady=(10, 0))
        label(pick, "Outcome", "bold").pack(side="left")
        names_ = [c.name for c in flow.outcome_choices()]
        var = tk.StringVar(value=flow.outcome or "Pick the outcome")
        combo = ttk.Combobox(pick, textvariable=var, values=names_, state="readonly", font=F["body"],
                             width=max([16] + [len(n) + 2 for n in names_]))
        combo.pack(side="left", padx=(8, 0))
        combo.bind("<<ComboboxSelected>>", lambda e: (flow.pick_outcome(var.get()), ask_outcome()))
        widgets["outcome"] = combo
        rule = label(pick, flow.outcome_rule(flow.outcome) if flow.outcome else
                     ("No column holds only 0 and 1. Fix the extract, or mark one as the outcome on Columns."
                      if not names_ else "The yes/no column where 1 means the loan went bad."), "small",
                     fg="SLATE")
        rule.pack(side="left", padx=(8, 0), fill="x", expand=True)
        fit(rule)
        widgets["outcome_rule"] = rule

        # the bottom first, so the table takes whatever height is left
        footer(("next", "Next: answer in the workbook →", lambda: background(flow.next, "Writing the workbook"),
                "primary"), note="Saved to Control, read-only.")
        lower = tk.Frame(page, bg=C["WHITE"])
        lower.pack(side="bottom", fill="x")
        if flow.mode == "new":
            under = tk.Frame(lower, bg=C["WHITE"])
            under.pack(fill="x", pady=(6, 0))
            # OC-51: scouting is the main path; a saved shortlist is the other way in
            label(under, "Confirming a saved shortlist" if flow.shortlist else "Scout first", "small").pack(
                side="left")
            widgets["shortlist"] = Button(under, "Clear" if flow.shortlist else "Browse…", pick_shortlist)
            widgets["shortlist"].pack(side="right")
            label(under, Path(flow.shortlist).name if flow.shortlist else "Or confirm a saved shortlist instead",
                  "small", fg="SLATE").pack(side="right", padx=6)
            if flow.states()["install_optional"] == "normal":
                # Goal 2 item 9: finding needs scikit-learn, an optional add-on (deps.OPTIONAL)
                more = tk.Frame(lower, bg=C["WHITE"])
                more.pack(fill="x", pady=(6, 0))
                widgets["install_optional"] = Button(more, "Install scikit-learn", lambda: install(optional=True),
                                                     "primary")
                widgets["install_optional"].pack(side="right")
        ok, said = flow.summary()
        sumbox = tk.Frame(lower, bg=C["CANVAS"])
        sumbox.pack(fill="x", pady=(10, 0))
        tk.Frame(sumbox, bg=C["KEY_RED"], height=3).pack(fill="x")
        text = tk.Frame(sumbox, bg=C["CANVAS"], padx=10, pady=6)
        text.pack(fill="x")
        widgets["summary"] = label(text, ("This will run: " + said) if ok else said, "small", bg=C["CANVAS"])
        widgets["summary"].pack(fill="x")
        fit(widgets["summary"])
        words_under(sumbox, C["CANVAS"], padx=10)
        message_lines(lower, flow.note, fg="INK")
        message_lines(lower, flow.message)

        # the table: a header band, then one row per column, scrolling only when the window can't hold it
        table = tk.Frame(page, bg=C["WHITE"])
        table.pack(fill="both", expand=True, pady=(10, 0))
        heads = ("Column", "What it is") + flow.heads()
        cols_ = {"cells": [], "base": BASE_W}
        head = tk.Frame(table, bg=C["INK"])
        head.pack(fill="x")
        for i, (text_, w) in enumerate(zip(heads, BASE_W)):
            cell = tk.Frame(head, bg=C["INK"], width=w, height=22)
            cell.pack(side="left")
            cell.pack_propagate(False)
            cols_["cells"].append((i, cell))
            tk.Label(cell, text=text_, font=F["head"], fg=C["WHITE"], bg=C["INK"],
                     anchor="w" if i < 2 else "center").pack(fill="both", expand=True, padx=(6, 0) if i < 2 else 0)
        rows = flow.rows()
        if not any(r["locked"] for r in rows):
            # All or None for a column of boxes (the firm: "select everything or not by the press of a button"):
            # Test it for a new variable; Cut into bands and Segment by for the bleed
            quick = tk.Frame(table, bg=C["CANVAS"])
            quick.pack(fill="x")
            cols_with = {3: "b"} if flow.mode == "new" else {2: "a", 3: "b"}
            for i, w in enumerate(BASE_W):
                cell = tk.Frame(quick, bg=C["CANVAS"], width=w, height=20)
                cell.pack(side="left")
                cell.pack_propagate(False)
                cols_["cells"].append((i, cell))
                if i in cols_with:
                    which = cols_with[i]
                    for word, on in (("All", True), ("None", False)):
                        b = tk.Label(cell, text=word, font=F["sub"], fg=C["INK"], bg=C["CANVAS"], cursor="hand2")
                        b.pack(side="left", expand=True)
                        b.bind("<Button-1>", lambda e, on=on, which=which: (flow.pick_every(which, on), repaint()))
                        name = "test" if flow.mode == "new" else {"a": "cut", "b": "seg"}[which]
                        widgets[f"{name}_{word.lower()}"] = b
        body_ = tk.Frame(table, bg=C["WHITE"])
        body_.pack(fill="both", expand=True)
        holder = tk.Canvas(body_, bg=C["WHITE"], highlightthickness=0, bd=0, height=40)
        scroll = ttk.Scrollbar(body_, orient="vertical", command=holder.yview)
        inner = tk.Frame(holder, bg=C["WHITE"])
        holder.create_window((0, 0), window=inner, anchor="nw")
        holder.configure(yscrollcommand=scroll.set)
        widgets["gaps"] = []
        boxes = {}
        for r in rows:
            if r["gap_before"]:
                gap = tk.Frame(inner, bg=C["WHITE"], height=GAP)         # between two groups: a gap, no words
                gap.pack(fill="x")
                widgets["gaps"].append(gap)
            line = tk.Frame(inner, bg=C["WHITE"])
            line.pack(fill="x")
            widgets[f"row_{r['name']}"] = line
            for i, w in enumerate(BASE_W):
                cell = tk.Frame(line, bg=C["WHITE"], width=w, height=ROW_H)
                cell.pack(side="left")
                cell.pack_propagate(False)
                cols_["cells"].append((i, cell))
                if i < 2:
                    text_ = r["name"] if i == 0 else r["what"]
                    lab = tk.Label(cell, text=text_, anchor="w", bg=C["WHITE"],
                                   font=F["name"] if i == 0 and not r["grey"] else F["cell"],
                                   fg=C["STONE"] if r["grey"] else C["INK"] if i == 0 else C["SLATE"])
                    lab.pack(fill="both", expand=True, padx=(6, 0))
                    if i == 1:
                        widgets[f"what_{r['name']}"] = lab
                else:
                    which = "abcde"[i - 2]
                    b = box(cell, False, False, lambda n=r["name"], w_=which: choose_click(n, w_))
                    b.place(relx=0.5, rely=0.5, anchor="center")
                    boxes[(r["name"], which)] = b
                    widgets[f"box_{r['name']}_{which}"] = b
            row_light(line, r["name"])
            tk.Frame(inner, bg=C["RULE"], height=1).pack(fill="x")
        widgets["boxes"] = boxes
        widgets["lit_row"] = widgets["hover_row"] = None        # a fresh table is all white; the clicked row stays
        light_rows()
        inner.update_idletasks()
        need = inner.winfo_reqheight()
        holder.pack(side="left", fill="both", expand=True)
        widgets["table"] = holder
        widgets["table_need"] = need

        def fitted(e=None):
            # widths: the two word columns take any width the window has beyond the three boxes' columns
            w = holder.winfo_width() or sum(BASE_W)
            extra = max(0, w - sum(BASE_W))
            ws_ = (BASE_W[0] + extra * 2 // 5, BASE_W[1] + extra - extra * 2 // 5) + BASE_W[2:]
            for i, cell in cols_["cells"]:
                if cell.winfo_exists():
                    cell.configure(width=ws_[i])
            holder.configure(scrollregion=(0, 0, sum(ws_), need))
            if need > holder.winfo_height() > 1:
                if not scroll.winfo_ismapped():
                    scroll.pack(side="right", fill="y", before=holder)
            elif scroll.winfo_ismapped():
                scroll.pack_forget()
                holder.yview_moveto(0)
        holder.bind("<Configure>", fitted)
        # the wheel is bound once, in build(), to whichever table is on screen: bound here to this canvas, it
        # outlived the page and a scroll after Next raised "invalid command name ...!canvas" (at the bank, 30 Sep)
        repaint()
        at = widgets.pop("keep_scroll", None)
        if at:
            root.after_idle(lambda: holder.winfo_exists() and holder.yview_moveto(at))

    def repaint():
        """The Choose tests boxes, the outcome line and the summary, changed where they stand: no redraw, so the
        table stays where it was scrolled. A row whose boxes appear or go needs the whole table drawn again."""
        rows = flow.rows()
        boxes = widgets.get("boxes") or {}
        for r in rows:
            if f"what_{r['name']}" in widgets:
                widgets[f"what_{r['name']}"].configure(text=r["what"])
            for which in "abcde":
                b = boxes.get((r["name"], which))
                ctl = r[which]
                if b is None:
                    continue
                if ctl is None:
                    b.place_forget()
                else:
                    b.place(relx=0.5, rely=0.5, anchor="center")
                    paint(b, ctl["on"], ctl["radio"], enabled=not r["locked"] or which == "a")
        if "outcome" in widgets:
            widgets["outcome"].set(flow.outcome or "Pick the outcome")
            widgets["outcome_rule"].configure(text=flow.outcome_rule(flow.outcome) if flow.outcome else
                                              "The yes/no column where 1 means the loan went bad.")
        ok, said = flow.summary()
        if "summary" in widgets:
            widgets["summary"].configure(text=("This will run: " + said) if ok else said)
        if "next" in widgets:
            widgets["next"].configure(state=flow.states()["next"])

    def choose_click(name, which):
        flow.click(name, which)
        ask_outcome()
        repaint()

    def ask_outcome():
        """The pop-up the firm asked for: the column, and how it will be read, before it becomes the outcome."""
        if not flow.asking:
            return
        from tkinter import messagebox
        flow.answer_outcome(messagebox.askyesno("Use this as the outcome?", flow.outcome_question(), parent=root))
        repaint()

    def page_answer():
        b = flow.book()
        label(page, "Answer in the workbook", "title").pack(anchor="w")
        label(page, f"{b.name} is written beside the extract. Fill in the shaded cells, save and close it, then "
                    f"press Run.", "body", fg="SLATE", wrap=470).pack(anchor="w", pady=(8, 8))
        if flow.book_open:
            open_banner()
        said = flow.suggested_line()
        if said:
            tile = tk.Frame(page, bg=C["CANVAS"])
            tile.pack(fill="x", pady=(4, 8))
            tk.Frame(tile, bg=C["KEY_RED"], height=3).pack(fill="x")
            label(tile, said, "small", bg=C["CANVAS"], wrap=460).pack(anchor="w", padx=10, pady=(6, 0))
            words_under(tile, C["CANVAS"], padx=10)
        lines = (flow.written.lines[1:] if flow.written else [])
        if lines:
            label(page, "\n".join(lines), "small", fg="INK", wrap=470).pack(anchor="w")
        message_lines(page, flow.message)
        buttons()

    def words_under(master, bg, padx=0):
        """The plain meaning of each term this page uses first (Flow.meanings), in slate under what uses it."""
        lines = flow.meanings()
        widgets["meanings"] = label(master, "\n".join(lines), "sub", fg="SLATE", bg=bg, wrap=460)
        if lines:
            widgets["meanings"].pack(anchor="w", padx=padx, pady=(2, 6))

    def open_banner():
        warn = tk.Frame(page, bg=C["ALERT_FG"], padx=10, pady=6)
        warn.pack(fill="x", pady=(0, 8))
        line = tk.Frame(warn, bg=C["ALERT_FG"])
        line.pack(anchor="w")
        label(line, "The workbook is open in Excel.", "bold", fg="CRIMSON", bg=C["ALERT_FG"]).pack(side="left")
        label(warn, "Save and close it first, so Run reads your latest answers.", "small", fg="INK",
              bg=C["ALERT_FG"], wrap=440).pack(anchor="w")
        widgets["open_banner"] = warn

    def buttons():
        footer(("open", "Open the workbook", open_book, "secondary"),
               ("run", "Run", lambda: background(flow.run, "Running"), "primary"))

    def page_needs():
        n = len(flow.needs)
        title, under = flow.needs_head()
        label(page, title, "title").pack(anchor="w")
        label(page, under, "body", fg="SLATE", wrap=470).pack(anchor="w", pady=(6, 8))
        if flow.book_open:
            open_banner()
        if flow.crash is not None or not flow.answers:
            # a Run that stopped for a reason other than an answer (the extract open in Excel, or something
            # PocketBook didn't expect): the reason across the page's space, not squeezed into a list row
            stopped(page, "", [nd.says for nd in flow.needs])
            buttons()
            return
        box_ = tk.Frame(page, bg=C["WHITE"], highlightbackground=C["MIST"], highlightthickness=1)
        box_.pack(fill="x")
        holder = tk.Canvas(box_, bg=C["WHITE"], highlightthickness=0, bd=0)
        inner = tk.Frame(holder, bg=C["WHITE"])
        holder.create_window((0, 0), window=inner, anchor="nw", width=478)
        for i, need in enumerate(flow.needs):
            row = tk.Frame(inner, bg=C["WHITE"], padx=8, pady=6)
            row.pack(fill="x")
            label(row, need.tag, "tag", fg="CRIMSON", width=13).pack(side="left", anchor="n")
            if need.sheet:
                where = need.cell or need.sheet
                b = Button(row, f"Open at {where}", lambda nd=need: say(flow.open_at(nd)))
                b.pack(side="right", anchor="n")
                widgets[f"open_at_{i}"] = b
            label(row, need.says, "small", wrap=250 if need.sheet else 360).pack(side="left", fill="x", padx=6)
            if i < n - 1:
                tk.Frame(inner, bg=C["RULE"], height=1).pack(fill="x")
        inner.update_idletasks()
        need_h = inner.winfo_reqheight()
        room = 250 if flow.book_open else 300
        holder.configure(height=min(need_h, room), scrollregion=(0, 0, 478, need_h))
        holder.pack(side="left", fill="both", expand=True)
        widgets["table"] = holder
        if need_h > room:
            sc = ttk.Scrollbar(box_, orient="vertical", command=holder.yview)
            holder.configure(yscrollcommand=sc.set)
            sc.pack(side="right", fill="y")
        message_lines(page, flow.message, fg="INK")
        buttons()

    def page_done():
        h = flow.headline()
        label(page, "Run finished. Results are in the workbook.", "title").pack(anchor="w", pady=(0, 12))
        tiles = tk.Frame(page, bg=C["WHITE"])
        tiles.pack(fill="x")
        shown = finished_tiles(h)
        made = []
        for i, (head, value, sub, rule, fg) in enumerate(shown):
            t = tk.Frame(tiles, bg=C["CANVAS"], width=150, height=96)
            t.pack(side="left", anchor="n", padx=(0 if i == 0 else 10, 0))
            t.pack_propagate(False)
            tk.Frame(t, bg=C[rule], height=3).pack(fill="x")
            label(t, head, "small", fg="SLATE", bg=C["CANVAS"], wrap=134).pack(anchor="w", padx=8, pady=(6, 0))
            label(t, value, "tile", fg=fg, bg=C["CANVAS"]).pack(anchor="w", padx=8)
            label(t, sub, "small", fg="SLATE", bg=C["CANVAS"], wrap=134).pack(anchor="w", padx=8)
            made.append(t)
        # 96 px, or taller when a tile's words need it: a long column name or group cut the last line off
        tiles.update_idletasks()
        tall = max([96] + [sum(c.winfo_reqheight() for c in t.winfo_children()) + 12 for t in made])
        for t in made:
            t.configure(height=tall)
        widgets["tiles"] = made
        first = flow.first_lines()
        if first:
            widgets["first"] = label(page, "\n".join(first), "small", fg="INK", wrap=470)
            widgets["first"].pack(anchor="w", pady=(12, 0))
        qs = h.get("open") or []
        if qs:
            q = tk.Frame(page, bg=C["WHITE"], highlightbackground=C["MIST"], highlightthickness=1, padx=10, pady=8)
            q.pack(fill="x", pady=(14, 0))
            first = "One open question." if len(qs) == 1 else f"{len(qs)} open questions."
            label(q, first, "bold").pack(anchor="w")
            for x in qs[:2]:
                label(q, x["says"], "small", wrap=450).pack(anchor="w")
            if len(qs) > 2:
                label(q, f"And {len(qs) - 2} more on Columns, under Treat as.", "small", fg="SLATE").pack(anchor="w")
        message_lines(page, flow.message, fg="INK")
        footer(("run", "Run again", lambda: background(flow.run, "Running"), "secondary"),
               ("start", "Open at Start here", lambda: say(flow.open_at()), "primary"))

    def render():
        draw_banner()
        draw_rail()
        clear(page)
        for k in ("setup", "next", "run", "open", "start", "open_banner", "summary", "install_optional", "tiles",
                  "first", "meanings", "crash", "copy_details", "table", "progress"):
            widgets.pop(k, None)
        {"extract": page_extract, "choose": page_choose, "answer": page_answer, "needs": page_needs,
         "done": page_done}["extract" if flow.gate.missing else flow.page]()
        if flow.busy:
            widgets["progress"] = label(page, flow.progress_line(), "small", fg="SLATE")
            widgets["progress"].pack(side="bottom", anchor="w")
        states = flow.states()
        for name in ("setup", "next", "run", "open"):
            if name in widgets:
                widgets[name].configure(state=states[name])
        if "install" in widgets and flow.gate.missing:
            widgets["install"].configure(state=states["install"])

    def say(text):
        flow.message = [text] if text else []
        render()

    def background(fn, what):
        # Tk may only be touched from the main thread (found by tools/shoot_launcher.py: the worker read the
        # extract box itself). The Flow does the work in a thread; the window redraws when it comes back.
        flow.pick(extract.get())
        _save_prefs({"extract": flow.extract, "few": flow.few, "many": flow.many})
        flow.busy, flow.stage, flow.began = what, "", time.monotonic()
        render()
        done: queue.Queue = queue.Queue()

        def work():
            try:
                fn()
            except Exception:           # anything a step didn't catch itself: on the page, never a traceback
                flow._stopped({"Running": "Run stopped", "Reading the extract": "Set up stopped"}.get(
                    what, f"{what} stopped"))
            done.put(True)
        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                done.get_nowait()
            except queue.Empty:
                p = widgets.get("progress")
                if p is not None and p.winfo_exists():         # the stage and the seconds, live
                    p.configure(text=flow.progress_line())
                root.after(100, poll)
                return
            flow.busy = ""
            render()
        root.after(100, poll)

    def browse():
        p = filedialog.askopenfilename(title="Pick the loan extract",
                                       filetypes=[("Extracts", "*.csv *.xlsx"), ("All files", "*.*")])
        if p:
            extract.set(p)

    def pick_shortlist():
        if flow.shortlist:
            flow.pick_shortlist(None)
        else:
            p = filedialog.askopenfilename(title="Pick the saved shortlist (pre-spec file)",
                                           filetypes=[("Pre-spec", "*.yaml *.yml"), ("All files", "*.*")])
            if p:
                flow.pick_shortlist(p)
        render()

    def open_book():
        say(flow.open_book())

    def on_extract(*_):
        # redrawn only when the page changes: a redraw while someone types would take the box away from them
        before = flow.page
        flow.pick(extract.get())
        _save_prefs({"extract": flow.extract, "few": flow.few, "many": flow.many})
        if flow.page != before:
            render()
        elif "setup" in widgets:
            widgets["setup"].configure(state=flow.states()["setup"])

    extract.trace_add("write", on_extract)

    def install(optional: bool = False) -> None:
        # pip runs in a thread so the window keeps answering; the clock in the banner shows it hasn't hung.
        names = flow.gate.start(optional)
        if optional:
            flow.message = [f"Installing {_names(names)}... this can take a few minutes."]
        render()
        done: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: done.put(deps.install(names)), daemon=True).start()

        def poll():
            try:
                ok, said = done.get_nowait()
            except queue.Empty:
                banner_clock(widgets, flow.gate, optional)
                root.after(500, poll)
                return
            flow.gate.finish(ok, said)
            if not flow.gate.missing:
                flow.after_install(optional)
            render()
        root.after(500, poll)

    def copy_details(button) -> None:
        """The traceback on the clipboard, to paste into an email (the file copy stays in last-error.txt)."""
        if flow.crash is None:
            return
        root.clipboard_clear()
        root.clipboard_append(flow.crash.details)
        button.configure(text="Copied")
        root.after(2000, lambda: button.winfo_exists() and button.configure(text="Copy details"))

    def copy_for_it() -> None:
        root.clipboard_clear()
        root.clipboard_append(deps.ask_it(flow.gate.missing))
        widgets["copy"].configure(text="Copied")
        root.after(2000, lambda: widgets["copy"].winfo_exists() and widgets["copy"].configure(text="Copy for IT"))

    def watch():
        # the workbook-open banner follows Excel: looked at every two seconds on the pages that use it
        if flow.page in ("answer", "needs") and not flow.busy and not flow.gate.missing:
            try:
                if flow.refresh():
                    render()
            except Exception:
                pass
        root.after(2000, watch)

    def wheel(e):
        """The mouse wheel scrolls the table on the page shown now, if it has one; never a page that has gone."""
        t = widgets.get("table")
        try:
            t, step = wheel_target(t, t is not None and bool(t.winfo_exists()), getattr(e, "delta", 0) or 0,
                                   getattr(e, "num", None))
            if t is not None and step:
                t.yview_scroll(step, "units")
        except tk.TclError:
            pass
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_all(seq, wheel)
    widgets["wheel"] = wheel

    widgets["render"] = render
    render()
    root.after(2000, watch)
    return widgets


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    build(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
