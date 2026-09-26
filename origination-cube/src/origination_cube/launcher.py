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
a sentence with where to look, never a traceback.
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
from . import deps, house

TITLE = "PocketBook"
SUFFIX = f" - {TITLE}.xlsx"
STEPS = ("Extract", "Set up", "Choose tests", "Answer in workbook", "Run")
START = ["1. Pick the extract, and press Set up: it reads what each column is.",
         "2. Choose the tests, and press Next: the workbook is written beside the extract.",
         "3. In the workbook, fill in the shaded cells, save and close it.",
         "4. Press Run. The results land in the workbook."]
PREFS = Path.home() / ".origination-cube" / "launcher.json"
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


def do_set_up(extract: str, choices: ch.Choices | None = None) -> list[str]:
    """Write the workbook (the Next button), in words."""
    from . import book
    if not extract or not Path(extract).exists():
        return ["Pick the extract first (the loan file from the bank: .csv or .xlsx)."]
    try:
        return book.set_up(extract, choices=choices).lines
    except Exception:
        return _crash("setting up")


def do_run(extract: str) -> list[str]:
    """Run the cube (the Run button), in words."""
    return _run(extract).lines


def _run(extract: str):
    from . import book
    target = book_for(extract) if extract else None
    if not extract:
        return book.Outcome(False, Path(), ["Pick the extract first."])
    if book.workbook_picked(extract):
        return book.Outcome(False, Path(extract), [book.workbook_picked(extract)])
    if not target.exists():
        return book.Outcome(False, target, [f"There's no workbook for {Path(extract).name} yet. Choose the tests "
                                            f"and press Next first."])
    try:
        return book.run(target, extract)
    except Exception:
        return book.Outcome(False, target, _crash("running"))


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
        self.outcome: str | None = None
        self.test: list[str] = []
        self.hold: list[str] = []
        self.share = 0.7
        self.shortlist: str | None = None
        self.spec = None              # the saved shortlist, loaded: its column and strata
        self.spec_problem: str | None = None
        self.written = None           # book.Outcome of the last Next
        self.needs: list[Need] = []
        self.finished = None          # book.Outcome of the last Run that finished
        self.finished_at, self.took = "", 0.0
        self.book_open = False
        self.message: list[str] = []  # a line or two for the current page: what went wrong, or what was done
        self.busy = ""

    # ---- where things stand

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
        return {"setup": _on(ready and bool(self.extract) and Path(self.extract).is_file()),
                "next": _on(ready and self.read is not None and ok),
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
                subs[3] = f"{len(self.needs)} left"
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
            self.page, self.message = "extract", []

    def set_up(self) -> None:
        """Read the extract: what each column is. Nothing is written."""
        from . import book
        if not self.extract or not Path(self.extract).is_file():
            self.message = ["Pick the extract first (the loan file from the bank: .csv or .xlsx)."]
            return
        got = book.read_extract(self.extract, self.few, self.many)
        if got.problem:
            self.message = [got.problem]
            return
        self.read, self.message = got, []
        self._defaults(got.chosen)
        self.page = "choose"

    def _kind(self) -> dict[str, str]:
        return {c.name: c.kind for c in self.read.columns} if self.read else {}

    def _defaults(self, chosen: ch.Choices | None) -> None:
        """What the table starts on: what the workbook beside the extract already
        shows, or every column its meaning cuts and nothing split."""
        kind = self._kind()
        nums = {c for c, k in kind.items() if k == "num"}
        cats = {c for c, k in kind.items() if k == "cat"}
        outs = [c for c, k in kind.items() if k == "out"]
        self.cut, self.seg, self.split = set(nums), set(cats), None
        self.outcome, self.test, self.hold, self.shortlist, self.spec = (outs[0] if outs else None), [], [], None, None
        if chosen is None:
            return
        self.mode = "new" if chosen.run_kind == ch.NEW_VARIABLE else "bleed"
        if self.mode == "bleed":
            self.cut = nums if chosen.bands is None else set(chosen.bands) & nums
            self.seg = cats if chosen.segments is None else set(chosen.segments) & cats
            self.split = chosen.split if chosen.split in kind else None
        else:
            self.outcome = chosen.outcome if chosen.outcome in kind else self.outcome
            self.test = [c for c in chosen.test if c in kind]
            self.hold = [c for c in chosen.hold if c in kind]
            self.share = chosen.find_share
        if chosen.shortlist:
            self.pick_shortlist(chosen.shortlist)

    # ---- step 3: the table

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def rows(self) -> list[dict]:
        """The Choose tests table. Each control is None (none on that row) or
        {"on", "radio"}; key and date rows are greyed and carry none."""
        out = []
        locked = self.mode == "new" and self.spec is not None      # the saved shortlist decides
        for c in self.read.columns if self.read else ():
            k = c.kind
            row = {"name": c.name, "what": c.what, "grey": k in ("key", "date", "other"), "a": None, "b": None,
                   "c": None, "locked": locked}
            if self.mode == "bleed":
                if k in ("out", "outd"):
                    row["every"] = True                     # it goes into every measure; no box to tick
                if k == "num":
                    row["a"] = {"on": c.name in self.cut and self.split != c.name, "radio": False}
                    row["c"] = {"on": self.split == c.name, "radio": True}
                if k == "cat":
                    row["b"] = {"on": c.name in self.seg, "radio": False}
            else:
                if k == "out":
                    row["a"] = {"on": self.outcome == c.name, "radio": True}
                if k in ("num", "cat"):
                    row["b"] = {"on": c.name in self.test, "radio": False}
                    row["c"] = {"on": c.name in self.hold, "radio": False}
            out.append(row)
        return out

    def heads(self) -> tuple[str, str, str]:
        return ("Outcome", "Test it", "Hold fixed") if self.mode == "new" else \
            ("Cut into bands", "Segment by", "Split by")

    def click(self, name: str, which: str) -> None:
        """A box ticked or a radio picked on the row for `name` (which: a, b or c)."""
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
            else:
                self.split = None if self.split == name else name     # one column splits, or none
                self.cut.discard(name)
        else:
            if which == "a":
                self.outcome = name
            elif which == "b":
                self.test = [c for c in self.test if c != name] if name in self.test else self.test + [name]
                self.hold = [c for c in self.hold if c != name]       # tested or held fixed, never both
            else:
                self.hold = [c for c in self.hold if c != name] if name in self.hold else self.hold + [name]
                self.test = [c for c in self.test if c != name]

    def pick_shortlist(self, path: str | None) -> None:
        """Confirm a saved shortlist (a pre-spec file) instead of finding one: it names
        the input and what is held fixed, so those boxes follow it."""
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
        self.test, self.hold = [self.spec.column], list(self.spec.strata)

    def choices(self) -> ch.Choices:
        """The table as the workbook gets it."""
        order = [c.name for c in self.read.columns] if self.read else []
        kind = self._kind()
        base = dict(few_values=self.few, many_values=self.many)
        if self.mode == "bleed":
            return ch.Choices(run_kind=ch.BLEED, bands=tuple(c for c in order if c in self.cut and c != self.split),
                              segments=tuple(c for c in order if c in self.seg), split=self.split, **base)
        test = [c for c in self.test]
        # the pockets hold the held-fixed columns fixed; one input splits every pocket, as a pre-spec tests it
        return ch.Choices(run_kind=ch.NEW_VARIABLE,
                          bands=tuple(c for c in self.hold if kind.get(c, "num") == "num"),
                          segments=tuple(c for c in self.hold if kind.get(c) == "cat"),
                          split=test[0] if len(test) == 1 else None, outcome=self.outcome, test=tuple(test),
                          hold=tuple(self.hold), find_share=self.share, shortlist=self.shortlist, **base)

    def summary(self) -> tuple[bool, str]:
        """The "This will run:" box, and whether Next can be pressed."""
        if self.read is None:
            return False, ""
        if self.mode == "bleed":
            got = self.choices()
            nb, ns = len(got.bands), len(got.segments)
            g = nb * ns
            if not g:
                return False, "Tick at least one band column and one segment column."
            return True, (f"{_s(nb, 'band column')} × {_s(ns, 'segment column')} = {_s(g, 'grid')}, five measures "
                          f"each" + (f"; split by {self.split} adds {g} more." if self.split else "."))
        if self.shortlist:
            if self.spec is None:
                return False, self.spec_problem or ""
            held = f", with {_names(list(self.spec.strata))} held fixed" if self.spec.strata else ""
            return True, (f"the saved shortlist {Path(self.shortlist).name}: {self.spec.column} against "
                          f"{self.outcome or 'the outcome'}{held}, confirmed on the loans it held back.")
        if not self.outcome:
            return False, "Mark a yes/no outcome column on Columns, then pick it here."
        if not self.test:
            return False, "Tick at least one input to test."
        n = len(self.test)
        found, rest = ch.pct(self.share), ch.pct(1 - self.share)
        if self.hold:
            return True, (f"{_s(n, 'input')} ({', '.join(self.test)}) against {self.outcome}, each with and without "
                          f"{_names(self.hold)} held fixed: {_s(2 * n, 'test')}, found on {found} and confirmed on "
                          f"{rest}.")
        return True, (f"{_s(n, 'input')} ({', '.join(self.test)}) against {self.outcome}: {_s(n, 'test')}, found "
                      f"on {found} and confirmed on {rest}.")

    def next(self) -> None:
        """Write the workbook with these choices (book.set_up keeps any answers already given)."""
        from . import book
        out = book.set_up(self.extract, choices=self.choices())
        if not out.ok:
            self.message = out.lines
            return
        self.written, self.message, self.needs, self.finished = out, [], [], None
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

    def run(self) -> None:
        began = time.monotonic()
        out = _run(self.extract)
        if out.ok:
            self.finished, self.took = out, time.monotonic() - began
            self.finished_at = datetime.now().strftime("%H:%M")
            self.needs, self.message, self.page = [], [], "done"
        else:
            self.needs = needs_of(out.problems) if out.problems else [Need(None, None, x) for x in out.lines]
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
        open_file(b)
        return "" if moved else f"Go to {sheet} {cell}: the workbook was already open, so it opened where it was."

    def go(self, index: int) -> None:
        """A done step on the rail, pressed: back to that step."""
        page = {0: "extract", 1: "choose", 2: "choose", 3: "answer"}.get(index)
        if page == "choose" and self.read is None:
            return
        if page == "answer" and not (self.book() and self.book().exists()):
            return
        if page:
            self.page, self.message = page, []

    def headline(self) -> dict:
        """The Run-finished tiles."""
        return (self.finished.summary or {}) if self.finished else {}


# --------------------------------------------------------------------------
# The window


def _money(v: float) -> str:
    a = abs(v)
    if a >= 1e9:
        return f"${v / 1e9:.2f}B"
    if a >= 1e6:
        return f"${v / 1e6:.2f}M"
    if a >= 1e4:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.0f}"


def build(root) -> dict:
    """The window's widgets on `root`, drawn from a Flow. Split from main() so the
    harness in tools/shoot_launcher.py can press the buttons and photograph each state."""
    import tkinter as tk
    from tkinter import filedialog, font as tkfont, ttk

    C = {k: house.tk(v) for k, v in house.PALETTE.items()}
    C.update(DISABLED=house.tk(house.DISABLED_TEXT), RULE=house.tk(house.ROW_RULE), WHITE=house.tk(house.PAPER))
    root.title(TITLE)
    root.geometry("720x560")
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
        """A tick box or radio button, 16 px: Ink when on, a Stone outline when off."""
        c = tk.Canvas(master, width=18, height=18, highlightthickness=0, bd=0, bg=master.cget("bg"),
                      cursor="hand2" if enabled else "")
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
        if enabled:
            c.bind("<Button-1>", lambda e: command())
        return c

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
        if lines:
            label(master, "\n".join(lines), "small", fg=fg, wrap=470).pack(anchor="w", pady=(8, 0))

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
            label(page, "You can still pick the extract and open an existing workbook while the add-on installs.",
                  "body", fg="SLATE", wrap=470).pack(anchor="w", pady=(10, 0))
        else:
            how = tk.Frame(page, bg=C["WHITE"], highlightbackground=C["MIST"], highlightthickness=1)
            how.pack(fill="x", pady=(14, 0))
            label(how, "▾ How Set up recognises columns", "bold", bg=C["CANVAS"]).pack(fill="x", ipady=4, ipadx=8)
            for text, key, opts in (("A number column with this many values or fewer is a category", "few", FEW),
                                    ("A text column with more values than this is too fine to cut by", "many", MANY)):
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
        message_lines(page, flow.message)
        setup = ("setup", "Set up from this extract", lambda: background(flow.set_up, "Reading the extract"),
                 "primary")
        if flow.gate.missing:
            footer(("open", "Open the workbook", open_book, "secondary"), setup)
        else:
            footer(setup)

    def page_choose():
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
        # the table: a header band, then one row per column, scrolling when there are many
        table = tk.Frame(page, bg=C["WHITE"])
        table.pack(fill="both", expand=True, pady=(10, 0))
        widths = (104, 128, 84, 84, 86)
        head = tk.Frame(table, bg=C["INK"])
        head.pack(fill="x")
        for i, (text, w) in enumerate(zip(("Column", "What it is") + flow.heads(), widths)):
            cell = tk.Frame(head, bg=C["INK"], width=w, height=22)
            cell.pack(side="left")
            cell.pack_propagate(False)
            tk.Label(cell, text=text, font=F["head"], fg=C["WHITE"], bg=C["INK"],
                     anchor="w" if i < 2 else "center").pack(fill="both", expand=True, padx=(6, 0) if i < 2 else 0)
        holder = tk.Canvas(table, bg=C["WHITE"], highlightthickness=0, bd=0, height=10)
        scroll = ttk.Scrollbar(table, orient="vertical", command=holder.yview)
        inner = tk.Frame(holder, bg=C["WHITE"])
        holder.create_window((0, 0), window=inner, anchor="nw")
        holder.configure(yscrollcommand=scroll.set)
        rows = flow.rows()
        for r in rows:
            line = tk.Frame(inner, bg=C["WHITE"])
            line.pack(fill="x")
            for i, w in enumerate(widths):
                if i == 2 and r.get("every"):
                    # an outcome column goes into every measure: said once across the three boxes
                    cell = tk.Frame(line, bg=C["WHITE"], width=sum(widths[2:]), height=22)
                    cell.pack(side="left")
                    cell.pack_propagate(False)
                    tk.Label(cell, text="· every measure", anchor="w", bg=C["WHITE"], font=F["cell"],
                             fg=C["SLATE"]).pack(fill="both", expand=True, padx=(6, 0))
                    break
                cell = tk.Frame(line, bg=C["WHITE"], width=w, height=22)
                cell.pack(side="left")
                cell.pack_propagate(False)
                if i < 2:
                    text = r["name"] if i == 0 else r["what"]
                    tk.Label(cell, text=text, anchor="w", bg=C["WHITE"],
                             font=F["name"] if i == 0 and not r["grey"] else F["cell"],
                             fg=C["STONE"] if r["grey"] else C["INK"] if i == 0 else C["SLATE"]).pack(
                        fill="both", expand=True, padx=(6, 0))
                else:
                    which = "abc"[i - 2]
                    ctl = r[which]
                    if ctl is not None:
                        b = box(cell, ctl["on"], ctl["radio"], lambda n=r["name"], w_=which: (flow.click(n, w_),
                                                                                              render()),
                                enabled=not r["locked"] or which == "a")
                        b.place(relx=0.5, rely=0.5, anchor="center")
                        widgets[f"box_{r['name']}_{which}"] = b
            tk.Frame(inner, bg=C["RULE"], height=1).pack(fill="x")
        inner.update_idletasks()
        need = inner.winfo_reqheight()
        holder.configure(height=min(need, 250 if flow.mode == "new" else 280), scrollregion=(0, 0, 480, need))
        holder.pack(side="left", fill="both", expand=True)
        if need > 280:
            scroll.pack(side="right", fill="y")
        holder.bind_all("<MouseWheel>", lambda e: holder.yview_scroll(int(-e.delta / 120), "units"))
        if flow.mode == "new":
            under = tk.Frame(page, bg=C["WHITE"])
            under.pack(fill="x", pady=(6, 0))
            label(under, "Find on", "small").pack(side="left")
            share = tk.StringVar(value=ch.pct(flow.share))
            sb = ttk.Combobox(under, textvariable=share, values=[ch.pct(x) for x in ch.SHARES], width=5,
                              state="disabled" if flow.shortlist else "readonly", font=F["small"])
            sb.pack(side="left", padx=4)
            sb.bind("<<ComboboxSelected>>", lambda e: (setattr(flow, "share", int(share.get()[:-1]) / 100),
                                                      render()))
            widgets["share"] = sb
            label(under, "confirm on the rest", "small", fg="SLATE").pack(side="left")
            widgets["shortlist"] = Button(under, "Clear" if flow.shortlist else "Browse…", pick_shortlist)
            widgets["shortlist"].pack(side="right")
            label(under, Path(flow.shortlist).name if flow.shortlist else "Or confirm a saved shortlist",
                  "small").pack(side="right", padx=6)
        ok, said = flow.summary()
        sumbox = tk.Frame(page, bg=C["CANVAS"])
        sumbox.pack(fill="x", pady=(10, 0))
        tk.Frame(sumbox, bg=C["KEY_RED"], height=3).pack(fill="x")
        text = tk.Frame(sumbox, bg=C["CANVAS"], padx=10, pady=6)
        text.pack(fill="x")
        widgets["summary"] = label(text, ("This will run: " + said) if ok else said, "small", bg=C["CANVAS"],
                                   wrap=460)
        widgets["summary"].pack(anchor="w")
        message_lines(page, flow.message)
        footer(("next", "Next: answer in the workbook →", lambda: background(flow.next, "Writing the workbook"),
                "primary"), note="Saved to Control, read-only.")

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
            label(tile, said, "small", bg=C["CANVAS"], wrap=460).pack(anchor="w", padx=10, pady=6)
        lines = (flow.written.lines[1:] if flow.written else [])
        if lines:
            label(page, "\n".join(lines), "small", fg="INK", wrap=470).pack(anchor="w")
        message_lines(page, flow.message)
        buttons()

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
        label(page, f"{_s(n, 'answer')} needed before Run", "title").pack(anchor="w")
        label(page, "Each one opens the workbook at its cell. Nothing ran; your answers so far are kept.", "body",
              fg="SLATE", wrap=470).pack(anchor="w", pady=(6, 8))
        if flow.book_open:
            open_banner()
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
        gco = h.get("gco")
        worse = h.get("worse", 0)
        what = "charge-offs" if gco else (h.get("measure") or "the outcome").lower()
        n = h.get("tie_outs", 0)
        for i, (head, value, sub, rule, fg) in enumerate((
                ("Pockets worse and material", f"{worse:,}", f"{what}, of {h.get('pockets', 0):,}", "KEY_RED",
                 "INK"),
                ("Charge-offs above their share" if gco else "Losses above their share",
                 _money(h.get("dollars", 0)) if gco else f"{h.get('dollars', 0):,.1f}",
                 f"in those {_s(worse, 'pocket')}", "KEY_RED", "INK"),
                ("Tie-out checks", f"{n:,} / {n:,}", "every grid adds up to the book", "INK", "POSITIVE"))):
            t = tk.Frame(tiles, bg=C["CANVAS"], width=150, height=96)
            t.pack(side="left", padx=(0 if i == 0 else 10, 0))
            t.pack_propagate(False)
            tk.Frame(t, bg=C[rule], height=3).pack(fill="x")
            label(t, head, "small", fg="SLATE", bg=C["CANVAS"], wrap=134).pack(anchor="w", padx=8, pady=(6, 0))
            label(t, value, "tile", fg=fg, bg=C["CANVAS"]).pack(anchor="w", padx=8)
            label(t, sub, "small", fg="SLATE", bg=C["CANVAS"], wrap=134).pack(anchor="w", padx=8)
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
        for k in ("setup", "next", "run", "open", "start", "open_banner", "summary"):
            widgets.pop(k, None)
        {"extract": page_extract, "choose": page_choose, "answer": page_answer, "needs": page_needs,
         "done": page_done}["extract" if flow.gate.missing else flow.page]()
        if flow.busy:
            label(page, f"{flow.busy}... this can take a minute on a large extract.", "small",
                  fg="SLATE").pack(side="bottom", anchor="w")
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
        flow.busy = what
        render()
        done: queue.Queue = queue.Queue()

        def work():
            try:
                fn()
            except Exception:
                flow.message = _crash(what.lower())
            done.put(True)
        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                done.get_nowait()
            except queue.Empty:
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
        b = flow.book()
        if b and b.exists():
            open_file(b)
        else:
            say("There's no workbook yet. Choose the tests and press Next first.")

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

    def install() -> None:
        # pip runs in a thread so the window keeps answering; the clock in the banner shows it hasn't hung.
        names = flow.gate.start()
        render()
        done: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: done.put(deps.install(names)), daemon=True).start()

        def poll():
            try:
                ok, said = done.get_nowait()
            except queue.Empty:
                if "status" in widgets:
                    widgets["status"].configure(text="\n".join(flow.gate.lines()))
                root.after(500, poll)
                return
            flow.gate.finish(ok, said)
            if not flow.gate.missing:
                flow.message = flow.gate.lines()[:1]
            render()
        root.after(500, poll)

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
