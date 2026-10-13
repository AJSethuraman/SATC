"""Templates for internal data: what a file must look like, and what the bank
must state about the measure. docs/V1-ROUND2-SPEC.md, section B, is the
contract.

The bank runs internal measures on site and nothing internal comes back. A
template is an empty ``date,value`` CSV whose ``#`` notes are questions, each
holding ``[STATE: ...]`` as its placeholder; none of them supplies an answer.
``check`` then refuses a filled file that does not match, before a build, and
reports every problem at once. A file that passes is an ordinary series for
the ``workbook`` command, which is unchanged.

The rules ``check`` applies:

- the ``# template: KEY (title)`` line ``write_template`` puts first is
  present and names the key being checked. The four two-book splits ask the
  same notes, so without it a filled card-rewards file would pass as
  card-non-rewards, and ``check`` is the only gate before a build;
- every required note is present as ``# key: answer``, not empty, and none
  still holds ``[STATE:``;
- every ``#`` line is one of this template's notes (``template``, ``unit``
  and the questions). The workbook skips ``#`` lines, so anything else there,
  an unknown note or a bare comment, could carry account-level rows past the
  column rule; it is refused;
- the header is exactly ``date,value`` and no row has a third field. Anything
  that could carry account-level data or personal information is refused;
- dates are quarter-ends (``YYYY-03-31``, ``YYYY-06-30``, ``YYYY-09-30``,
  ``YYYY-12-31``), oldest first, contiguous, and never repeated. The spec
  also names ``YYYYQn``; it is recognised and refused with the quarter-end
  date to write instead, because ``workbook.read_series`` reads a date by its
  characters 5-6 as a month, so ``2020Q2`` would land in 2020Q1 and the build
  would refuse the series as having gaps. A check that passes a file the
  build cannot read would be a check that lies;
- every value is a finite number; a ``%`` value lies within 0-100, and a
  ``score`` value within the scale the file states in its ``scale`` note;
- at least ``MIN_QUARTERS`` (9) quarters. ``scale.py`` refuses a series
  without two four-quarter changes, in its words: *"too little history kept
  for a typical yearly move (two four-quarter changes needed)"*. Nine quarters
  hold two four-quarter changes end to end (q1 to q5, q5 to q9), the number
  the spec sets; ``scale.typical_yearly_move`` itself would accept the
  overlapping changes of six.

A file that starts with a byte-order mark (Excel's "CSV UTF-8") is refused,
because the workbook reads plain UTF-8 and would not find the ``date`` column.

Lines are split exactly where the workbook splits them: at line feed, carriage
return and the pair, and nowhere else (``str.splitlines`` also breaks at vertical
tab, form feed, U+2028 and others, which would let check pass a file the build
cannot read). Rows are parsed by ``csv`` as the workbook parses them, and each
problem names the physical line its row starts on; blank lines are skipped,
as ``csv.DictReader`` skips them.

The two functions the command line calls:

- ``write_template(key, out) -> (csv_path, checklist_path)``
- ``check(key, path) -> list of problems``; empty means the file is OK.
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

#: The fewest quarters a template file may hold (spec B: "at least 9 quarters").
MIN_QUARTERS = 9

#: scale.py's refusal, quoted; a test holds it to scale.scale's own output.
SCALE_REFUSAL = "too little history kept for a typical yearly move (two four-quarter changes needed)"

PLACEHOLDER = "[STATE:"
HEADER = ["date", "value"]
_QUARTER_ENDS = {"03-31": 1, "06-30": 2, "09-30": 3, "12-31": 4}
_ISO = re.compile(r"^(\d{4})-(\d{2}-\d{2})$")
_LINES = re.compile(r"\r\n|\r|\n")
_YQ = re.compile(r"^(\d{4})Q([1-4])$")
_NOTE = re.compile(r"^#\s*([A-Za-z][A-Za-z0-9-]*)\s*:(.*)$")
_RANGE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*$")


@dataclass(frozen=True)
class Template:
    """One internal measure: its key, title, unit, direction, and the notes
    (``(key, question)`` pairs, in order) the bank must answer in the file."""
    key: str
    title: str
    unit: str
    direction: str
    notes: Tuple[Tuple[str, str], ...]


def _common(unit: str, extra: Tuple[Tuple[str, str], ...] = ()) -> Tuple[Tuple[str, str], ...]:
    """The notes every template asks; a rate asks numerator and denominator,
    a score asks for its scale. ``extra`` follows ``measure``."""
    if unit == "%":
        shape = (("numerator", "what is counted on top of the rate"),
                 ("denominator", "what the rate is divided by"))
    else:
        shape = (("scale", "the lowest and highest possible scores, e.g. 300-850"),)
    return ((("measure", "what is measured, in the bank's words"),) + extra + shape
            + (("as-of", "the convention, e.g. quarter-end balances"),
               ("basis", "e.g. trailing twelve months, or quarter-end"),
               ("source", "the internal system or report, by name"),
               ("prepared-by", "who prepared this file"),
               ("prepared-on", "the date it was prepared")))


_SPLIT = (("split", "which loans are in this book and which are not, and how that is decided"),)

#: Every template, by key. The four two-book splits (decided 7 Oct 2026) ask
#: which measure they carry in ``measure`` and how the book is drawn in ``split``.
TEMPLATES = {t.key: t for t in (
    Template("wapd", "Weighted average probability of default", "%", "higher_is_worse",
             _common("%", (("pd-horizon", "the period each probability of default covers, "
                                          "e.g. the next twelve months"),))),
    Template("refreshed-score", "Refreshed credit score (portfolio average)", "score", "lower_is_worse",
             _common("score", (("refresh", "how often scores are refreshed, and how the "
                                           "average is weighted"),))),
    Template("epd", "Early payment default rate", "%", "higher_is_worse",
             _common("%", (("window", "the months on book that define early"),))),
    Template("student-loans", "Other consumer: student loans only (Laurel Road)", "%", "higher_is_worse",
             _common("%", _SPLIT)),
    Template("other-consumer-ex-student", "Other consumer without student loans", "%", "higher_is_worse",
             _common("%", _SPLIT)),
    Template("card-rewards", "Credit card: rewards cards only", "%", "higher_is_worse",
             _common("%", _SPLIT)),
    Template("card-non-rewards", "Credit card: non-rewards cards only", "%", "higher_is_worse",
             _common("%", _SPLIT)),
)}


def _template(key: str) -> Template:
    if key not in TEMPLATES:
        raise ValueError("no template %r; the templates are: %s" % (key, ", ".join(TEMPLATES)))
    return TEMPLATES[key]


def checklist_path(out) -> Path:
    """``OUT.csv`` -> ``OUT.checklist.md`` beside it."""
    out = Path(out)
    return out.with_name(out.stem + ".checklist.md")


def write_template(key: str, out) -> Tuple[Path, Path]:
    """Write the empty template for ``key`` to ``out`` (a ``.csv``) and its
    checklist beside it; return both paths.

    The CSV holds one ``# key: [STATE: question]`` line per required note,
    then the ``date,value`` header and no rows. Neither file is written over:
    an existing file may be a filled template, and an empty one written on
    top of it would lose the bank's answers, so it is refused (``ValueError``)
    and nothing is written."""
    t = _template(key)
    out = Path(out)
    if out.suffix.lower() != ".csv":
        raise ValueError("the template is a CSV: name it OUT.csv, not %s" % out.name)
    md = checklist_path(out)
    for p in (out, md):
        if p.exists():
            raise ValueError("%s already exists; it is not written over, so a filled template "
                             "cannot be lost. Choose another name or move it." % p)
    lines = ["# template: %s (%s)" % (t.key, t.title),
             "# unit: %s; %s" % (t.unit, "higher is worse" if t.direction == "higher_is_worse"
                                 else "lower is worse")]
    lines += ["# %s: %s %s]" % (k, PLACEHOLDER, q) for k, q in t.notes]
    lines.append(",".join(HEADER))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    md.write_text(_checklist(t, out.name), encoding="utf-8")
    return out, md


def _checklist(t: Template, name: str) -> str:
    """The steps in plain words."""
    rng = ("between 0 and 100" if t.unit == "%"
           else "inside the scale you state in the scale line")
    steps = [
        "Open %s in a text editor, not Excel. Excel can change the dates and add "
        "hidden characters." % name,
        "Answer every line that starts with `#` and holds `[STATE: ...]`. Replace the "
        "whole `[STATE: ...]` with your answer and keep the part before the colon. "
        "The questions:\n\n" + "\n".join("   - `%s`: %s" % (k, q) for k, q in t.notes),
        "Under the `date,value` line, add one line per quarter, oldest first: the "
        "quarter-end date, a comma, the value. For example `2024-03-31,%s`."
        % ("1.25" if t.unit == "%" else "712"),
        "Use quarter-end dates only: March 31, June 30, September 30, December 31. "
        "Leave no quarter out and list none twice.",
        "Give at least %d quarters. The scale needs two full years of change to "
        "measure a typical move." % MIN_QUARTERS,
        "Each value is a plain number (%s), %s. No `%%` sign, no thousands "
        "separator, no blanks." % (t.unit, rng),
        "Add no other column. The file holds a date and a value and nothing else, so "
        "nothing about an account or a person can travel in it.",
        "Run `threshold-engine template check %s %s`. It lists every problem at once; "
        "fix them and run it again until it says OK." % (t.key, name),
    ]
    head = "# %s: what to do\n\n%s, measured as %s; %s.\n\n" % (
        t.title, t.title, "a percentage" if t.unit == "%" else "a score",
        "higher is worse" if t.direction == "higher_is_worse" else "lower is worse")
    return head + "\n".join("%d. %s" % (i, s) for i, s in enumerate(steps, start=1)) + "\n"


def _date(text: str):
    """A quarter-end ISO date -> (year, quarter), or a problem string."""
    m = _ISO.match(text)
    if m and m.group(2) in _QUARTER_ENDS:
        return int(m.group(1)), _QUARTER_ENDS[m.group(2)]
    m = _YQ.match(text)
    if m:
        iso = "%s-%s" % (m.group(1), ("03-31", "06-30", "09-30", "12-31")[int(m.group(2)) - 1])
        return ("date %r: write it as %s; the workbook reads YYYYQn as the wrong quarter"
                % (text, iso))
    return ("date %r is not a quarter-end (YYYY-03-31, YYYY-06-30, YYYY-09-30 or YYYY-12-31)"
            % text)


def _scale(text: str):
    """'300-850' -> (300.0, 850.0), or None when it does not read as low-high."""
    m = _RANGE.match(text)
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    return (lo, hi) if lo < hi else None


def check(key: str, path) -> List[str]:
    """Every problem with the filled template at ``path``, at once; an empty
    list means it passes. An unknown ``key`` is refused (``ValueError``); a
    file that cannot be read raises its ``OSError``. The rules are in the
    module docstring."""
    t = _template(key)
    raw = Path(path).read_bytes()
    problems: List[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("the file starts with a byte-order mark (Excel's 'CSV UTF-8'); the workbook "
                        "reads plain UTF-8: save it as plain CSV or from a text editor")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return problems + ["the file is not UTF-8 text"]

    allowed = {"template", "unit"} | {k for k, _ in t.notes}
    lines = _LINES.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    notes, body = {}, []
    for n, line in enumerate(lines, start=1):
        if line.startswith("#"):
            m = _NOTE.match(line)
            if not m:
                problems.append("line %d: a '#' line must be a note, '# key: answer'; anything else is "
                                "refused, so no account-level data or personal information can travel "
                                "in one" % n)
                continue
            k = m.group(1).lower()
            if k not in allowed:
                problems.append("line %d: note '%s' is not one this template asks; a '#' line holds only "
                                "the template's notes, so no account-level data or personal information "
                                "can travel in one" % (n, k))
                continue
            if k in notes:
                problems.append("line %d: note '%s' is given twice" % (n, k))
            notes[k] = m.group(2).strip()
        else:
            body.append((n, line))

    named = "%s (%s)" % (t.key, t.title)
    if "template" not in notes:
        problems.append("missing note: # template: %s; it names the template the file was written "
                        "from, so a file cannot be checked as another book" % named)
    else:
        given = notes["template"].split(" ", 1)[0]
        if given != t.key:
            problems.append("note 'template' says this file was written from %r, not %r; check it "
                            "as %s, or write the %s template and fill that"
                            % (given, t.key, given, t.key))
    for k, q in t.notes:
        if k not in notes:
            problems.append("missing note: # %s: %s" % (k, q))
        elif PLACEHOLDER in notes[k]:
            problems.append("note '%s' still holds its placeholder; answer it: %s" % (k, q))
        elif not notes[k]:
            problems.append("note '%s' is empty; answer it: %s" % (k, q))
    rng = None
    if t.unit == "score" and "scale" in notes and notes["scale"] and PLACEHOLDER not in notes["scale"]:
        rng = _scale(notes["scale"])
        if rng is None:
            problems.append("note 'scale' must give the lowest and highest possible scores, low "
                            "first, e.g. 300-850; found %r" % notes["scale"])

    # csv.reader joins a quoted field across lines, as the workbook's reader
    # does; each line is fed with its line feed, as a file yields it. line_num
    # says how many body lines each row used, so each row is named by the
    # physical line it starts on. Blank rows are skipped, as csv.DictReader
    # skips them.
    rows, reader, used = [], csv.reader(l + "\n" for _, l in body), 0
    for r in reader:
        start, used = body[used][0], reader.line_num
        if r:
            rows.append((start, r))
    if not rows:
        return problems + ["no header: the first line after the notes must be exactly 'date,value'"]
    n, header = rows[0]
    if header != HEADER:
        extra = [h for h in header if h.strip() not in HEADER]
        if extra and [h for h in header if h.strip() in HEADER]:
            problems.append("line %d: column(s) %s refused: a template holds date and value and "
                            "nothing else, so no account-level data or personal information can "
                            "travel in it" % (n, ", ".join(repr(h) if h.strip() else
                                                           "unnamed (a trailing comma?)"
                                                           for h in extra)))
        else:
            problems.append("line %d: the header must be exactly 'date,value'; found %r"
                            % (n, ",".join(header)))

    # Where the header names date and value among other columns, the rows are
    # still read by those columns, so the other problems are reported too.
    stripped = [h.strip() for h in header]
    # A row with more fields than the header names carries data nobody
    # declared, and is refused for that; a row too short to hold both a date
    # and a value is refused for that, and the reason given is that one.
    width, at = 2, (0, 1)
    if header != HEADER and "date" in stripped and "value" in stripped:
        width, at = len(header), (stripped.index("date"), stripped.index("value"))
    seen, prev = set(), None
    for n, r in rows[1:]:
        if len(r) > width:
            problems.append("line %d: %d fields; a row holds a date and a value and nothing else, "
                            "so no account-level data or personal information can travel in it"
                            % (n, len(r)))
            continue
        if len(r) <= max(at):
            problems.append("line %d: %d field(s); a row needs a date, a comma and a value"
                            % (n, len(r)))
            continue
        d, v = r[at[0]], r[at[1]]
        when = _date(d)
        if isinstance(when, str):
            problems.append("line %d: %s" % (n, when))
        else:
            idx = when[0] * 4 + when[1]
            if idx in seen:
                problems.append("line %d: %s is repeated" % (n, d))
            elif prev is not None and idx < prev[0]:
                problems.append("line %d: %s comes before %s; dates run oldest first" % (n, d, prev[1]))
            elif prev is not None and idx != prev[0] + 1:
                problems.append("line %d: %s follows %s; the quarters between are missing, and a gap "
                                "is refused, not filled in" % (n, d, prev[1]))
            seen.add(idx)
            if prev is None or idx > prev[0]:
                prev = (idx, d)
        try:
            x = float(v)
        except ValueError:
            problems.append("line %d: value %r is not a number" % (n, v))
            continue
        if not math.isfinite(x):
            problems.append("line %d: value %r is not a finite number" % (n, v))
        elif t.unit == "%" and not 0 <= x <= 100:
            problems.append("line %d: %s is outside 0-100, and this measure is a %%" % (n, v))
        elif rng is not None and not rng[0] <= x <= rng[1]:
            problems.append("line %d: %s is outside the stated scale %g-%g" % (n, v, rng[0], rng[1]))
    count = len(seen)
    if count < MIN_QUARTERS:
        problems.append("%d quarter(s) of history; at least %d are needed. scale.py refuses with "
                        "'%s', and nine quarters hold two four-quarter changes end to end"
                        % (count, MIN_QUARTERS, SCALE_REFUSAL))
    return problems
