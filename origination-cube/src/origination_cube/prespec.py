"""The pre-spec: what the confirmatory run will test, written down and committed
before anyone looks at the holdout.

Why it exists. A derived column (income / sales, say) is scouted on development
loans: the forest ranks it, the shape shows where the rate bends, and bins are
drawn there (`docs/statistics.md` B7; `docs/scout-vs-measure.py`, whose edges
were "written down after looking at" the scouting). Bins chosen because of what
the development loans showed prove nothing on those same loans. The evidence is
the identical test - same bins, strata, confidence and reference group -
run on loans the scouting never saw: the holdout (B5, B6). The pre-spec is that
promise, and it only binds once git holds it, dated, before the holdout run.

THE FILE (YAML). Every line is required and none has a default. A shortlist (Goal 2
item 3, the lean pre-spec: "an outcome plus a shortlist of inputs"; the firm, 26 Sep
2026: "it cannot be one column, but a shortlist whatever"):

    prespec: 1                          # this format's version
    written: 2026-09-25                 # the day it was written
    outcome: BAD_FLAG                   # the yes/no column every input is tested against
    inputs:                             # the shortlist: each input with its bins and reference group
      - column: income_to_sales         # the derived or split column being tested
        bins: [0.1, 0.25, 0.5, 1.0, 2.0]  # its cut points, chosen on development data
        reference: "0.25 - 0.49"        # the group every other group is compared with
      - column: DTI
        bins: [0.2, 0.35, 0.45]
        reference: 0
    strata: [FICO, CHANNEL]             # the columns held fixed; each input is reported with and without them
    confidence: 0.95                    # how sure a difference must be, as a share
    holdout: {from: 2024-01-01, to: 2024-12-31}       # origination range kept back
    development: {from: 2022-01-01, to: 2023-12-31}   # origination range the bins came from

The one-column pre-spec written before the shortlist (`column:`, `bins:` and
`reference:` at the top, and no `outcome:`) is still read, as a shortlist of one.
It names no outcome, so it is tested against the outcome the run marks, as it
always was; an `outcome:` line may be added to it. A file with both `inputs:` and
a top-level `column:`, `bins:` or `reference:` is refused: which one is meant?

Line by line:

- `prespec` is 1.
- `written` and every `from` / `to` is a date written 2024-01-01, quoted or not. A
  `written` date after the day of the run is said on Check, and the run goes on.
- `outcome` names one column: the yes/no outcome the run marks. A run tested
  against another says so on Record.
- `inputs` is a list of one or more inputs, each exactly `column`, `bins` and
  `reference`, every one required. No column is listed twice.
- `column` names one column.
- `bins` is a list of numbers, each above the one before. N cut points make N + 1
  groups. A group holds its first number and stops short of the next cut point, so a
  ratio of exactly 0.25 is in "0.25 - 0.49". The groups are named the way the grids
  name bands (`engine.band_labels`): between the cut points above, "0.10 - 0.24",
  "0.25 - 0.49", "0.50 - 0.99", "1.00 - 1.99". The lowest and highest groups take
  their names from the data once it is read, as a grid's do: if the ratio runs from
  0.03 to 7.40, they are "0.03 - 0.09" and "2.00 - 7.40", and the workbook names them
  so wherever it names a group (`named`).
- `reference` is one of those names, or the group's number counting from 0 at the
  lowest (2 is "0.25 - 0.49" above, as `ref = 2` is in scout-vs-measure.py). The file
  is written before the data is read, so the lowest and highest groups may be written
  with any range, "0.01 - 0.09", "2.00 - 7.40", or as "up to 0.09" and "2.00 and up".
- `strata` lists column names, each once, never a tested column. `strata: []` says
  explicitly that the whole book is one pocket. Which columns to hold fixed is the
  analyst's call: anything PocketBook writes suggests them and leaves the value blank
  (OC-13; the firm's answer on the 26 Sep docket).
- `confidence` is a share from 0.5 up to, not including, 1 (as the cube file's).
- `holdout` and `development` are origination ranges, `{from: DATE, to: DATE}`, and
  BOTH ENDS ARE INCLUSIVE: `{from: 2024-01-01, to: 2024-12-31}` holds a loan made on
  1 January 2024 and one made on 31 December 2024. `from` may not be after `to`, and
  the two ranges may not share a single day: a loan in both would be tested on the
  very loans its bins were chosen on.

As with the cube file (`config.py`), a line the file does not recognise is refused,
since a misspelled `confidense` that was quietly ignored is the silent fallback this
exists to stop. So is `window_months`, which an older pre-spec carried: the outcome
window was removed, and a run shows every loan as the extract has it (the firm, 26
Sep 2026). The refusal says so by name, rather than calling the line unknown. A value still reading `[CONFIRM: ...]` is refused, naming it. Every
problem is listed at once, one per line.

`docs/prespec-example.yaml` is the same example, committed, and a test loads it.

WHAT IS HERE. Each returns data; nothing writes to the workbook. Check echoing the
file and its commit, and the Log counting holdout runs, are wired in elsewhere
(`docs/NEXT-GOAL.md` 3.15).

- `load(path) -> PreSpec`, or `PreSpecError` listing every problem.
- `named(prespec, lo, hi) -> PreSpec`: its groups named from the tested column's
  smallest and largest value in a run, as that run's tabs name them; for a
  shortlist, `named(prespec, ranges={column: (lo, hi)})` names every input's.
- `provenance(path) -> {commit, committed_at, dirty, reason}`: the commit the file
  was last committed in, and whether it has changed since. Never raises.
- `deviations(prespec, in_use) -> [str]`: each place the run disagrees with the
  pre-spec, in words. A key the run did not set is a deviation, not a pass. A
  shortlist's inputs are compared one by one (`in_use["inputs"]`).
- `holdout_touch(prespec, dates) -> (count, first, last)`: how many loans were made
  inside the holdout range, ends inclusive.
"""

from __future__ import annotations

import math
import os
import subprocess

from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from .engine import band_labels

VERSION = 1
CONFIRM = "[CONFIRM:"
#: The one-column pre-spec's lines, every one required (the format before the shortlist; still read)
KEYS = ("prespec", "written", "column", "bins", "reference", "strata", "confidence", "holdout", "development")
#: A shortlist's lines, every one required (Goal 2 item 3: an outcome plus a shortlist of inputs)
SHORTLIST_KEYS = ("prespec", "written", "outcome", "inputs", "strata", "confidence", "holdout", "development")
#: The lines of one input in `inputs:`, every one required
INPUT_KEYS = ("column", "bins", "reference")
#: A line an older pre-spec carried and a run no longer reads, and why (config.REMOVED says it for the cube file).
REMOVED = {"window_months": "the outcome window was removed: it left young loans out and counted late losses "
                            "as good. A run now shows every loan in the extract as the extract has it. Picking "
                            "which loans to study is done before the extract reaches PocketBook. Delete the line."}
RANGE_KEYS = ("from", "to")
#: What `deviations` compares, in the order it reports. `edges` is read for `bins`.
IN_USE_KEYS = ("column", "bins", "reference", "strata", "confidence", "holdout")
#: The git program. A module setting so a test can point it at nothing.
GIT = "git"
GIT_TIMEOUT = 15                                           # seconds, per git call
#: Variables that would make git read some other repository than the file's own.
_GIT_ELSEWHERE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")
ONLY_ONCE_COMMITTED = "a pre-spec only counts once it is committed"

#: The line to add for each missing one. Strata are the analyst's call, so the line suggests them and leaves the
#: value blank, as every judgment setting is (OC-13; the firm, 26 Sep 2026): a blank reads [CONFIRM: ...], which
#: the file refuses until it is answered.
_LINES = {
    "prespec": f"prespec: {VERSION}",
    "written": "written: 2026-09-25                 # the day this was written",
    "outcome": "outcome: BAD_FLAG                   # the yes/no column every input is tested against",
    "inputs": ("inputs:                             # the shortlist: each input, its bins and its reference group\n"
               "  - column: income_to_sales\n"
               "    bins: [0.1, 0.25, 0.5, 1.0, 2.0]\n"
               '    reference: "0.25 - 0.49"'),
    "column": "column: income_to_sales             # the column being tested",
    "bins": "bins: [0.1, 0.25, 0.5, 1.0, 2.0]    # its cut points, chosen on development data",
    "reference": 'reference: "0.25 - 0.49"           # the group the others are compared with',
    "strata": ('strata: "[CONFIRM: the columns to hold fixed, such as [FICO, CHANNEL]; [] for none]"   '
               "# held fixed; each input is reported with and without them"),
    "confidence": "confidence: 0.95                    # how sure a difference must be",
    "holdout": "holdout: {from: 2024-01-01, to: 2024-12-31}       # kept back for the confirmatory run",
    "development": "development: {from: 2022-01-01, to: 2023-12-31}   # where the bins were chosen",
}


class PreSpecError(Exception):
    """One or more problems with the pre-spec, one per line."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class DateRange:
    """Origination dates, both ends inclusive."""
    start: date
    end: date

    def holds(self, d: date) -> bool:
        return self.start <= d <= self.end

    def overlaps(self, other: "DateRange") -> bool:
        return self.start <= other.end and other.start <= self.end

    def text(self) -> str:
        return f"{self.start.isoformat()} to {self.end.isoformat()}"


@dataclass(frozen=True)
class Input:
    """One input on the shortlist: its column, cut into groups at its bins, each compared with its reference."""
    column: str
    bins: tuple[float, ...]
    groups: tuple[str, ...]          # the groups the bins make, named as the grids name bands
    reference: str                   # the reference group's name, one of `groups`
    reference_index: int             # its place in `groups`, 0 the lowest
    lo: float | None = None          # the column's smallest and largest value in a run, once read,
    hi: float | None = None          # from which the lowest and highest groups are named (`named`)


@dataclass(frozen=True)
class PreSpec:
    written: date
    inputs: tuple[Input, ...]        # the shortlist, in the file's order; one for a one-column pre-spec
    strata: tuple[str, ...]
    confidence: float
    holdout: DateRange
    development: DateRange
    outcome: str | None = None       # None: a one-column pre-spec written before the line existed
    source_path: str = ""
    text: str = ""                   # the file exactly as read, for Check to echo
    shortlist: bool = False          # written as a shortlist (`inputs:`), not the one-column form

    # The first input's lines, as a one-column pre-spec had them. Code that handles a shortlist reads `inputs`.
    @property
    def column(self) -> str:
        return self.inputs[0].column

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(i.column for i in self.inputs)

    @property
    def bins(self) -> tuple[float, ...]:
        return self.inputs[0].bins

    @property
    def groups(self) -> tuple[str, ...]:
        return self.inputs[0].groups

    @property
    def reference(self) -> str:
        return self.inputs[0].reference

    @property
    def reference_index(self) -> int:
        return self.inputs[0].reference_index

    @property
    def lo(self) -> float | None:
        return self.inputs[0].lo

    @property
    def hi(self) -> float | None:
        return self.inputs[0].hi


def _named_input(inp: Input, lo: float | None, hi: float | None) -> Input:
    groups = tuple(band_labels(inp.bins, lo, hi))
    return replace(inp, groups=groups, reference=groups[inp.reference_index], lo=lo, hi=hi)


def named(prespec: PreSpec, lo: float | None = None, hi: float | None = None, *,
          ranges: dict | None = None) -> PreSpec:
    """The pre-spec with its groups named as a run's tabs name them, from the
    tested column's smallest and largest value in that run: "0.03 - 0.09", not
    "up to 0.09". Without a value for an end, that end is named as the bins alone
    name it, as a grid's is. `lo` and `hi` name the first input's (a one-column
    pre-spec's only one); `ranges` maps each input's column to its (lo, hi)."""
    got = dict(ranges or {})
    if ranges is None:
        got[prespec.inputs[0].column] = (lo, hi)
    return replace(prespec, inputs=tuple(_named_input(i, *got.get(i.column, (None, None))) for i in prespec.inputs))


# --------------------------------------------------------------------------
# Reading the file

def load(path: str | Path) -> PreSpec:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise PreSpecError([f"{p}: cannot be read ({exc.strerror or exc})"]) from exc
    try:
        raw = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:        # ValueError: a date like 2024-13-01
        raise PreSpecError([f"{p}: not readable as YAML: {exc}"]) from exc
    return parse(raw, source_path=str(p), text=text)


def _one_input(raw: dict, where: str, has, problems: list[str]) -> Input | None:
    """One input's column, bins and reference, read from `raw` (the file's top level for a one-column pre-spec, an
    entry of `inputs:` for a shortlist). `where` prefixes each line's name ("inputs[1]." or ""); `has(k)` says
    whether line k is there to read (a missing or unanswered one is said elsewhere)."""
    column = None
    if has("column"):
        v = raw["column"]
        if isinstance(v, str) and v.strip():
            column = v.strip()
        else:
            problems.append(f"`{where}column:` must name the column being tested, such as income_to_sales; got {v!r}")
    bins = None
    if has("bins"):
        v = raw["bins"]
        if not isinstance(v, list) or not v or not all(_finite(x) for x in v):
            problems.append(f"`{where}bins:` must be a list of cut points, such as [0.1, 0.25, 0.5, 1.0, 2.0]; "
                            f"got {v!r}")
        elif any(b <= a for a, b in zip(v, v[1:])):
            problems.append(f"`{where}bins:` must rise, each cut point above the one before; got {v}")
        else:
            bins = tuple(float(x) for x in v)
    groups, ref_index = (), None
    if bins is not None:
        groups = tuple(band_labels(bins))
        if has("reference"):
            ref_index = _group_index(raw["reference"], bins)
            if ref_index is None:
                problems.append(f"`{where}reference: {raw['reference']!r}` is not one of the groups the bins make: "
                                f"{'; '.join(groups)}. Write one of those, or its number, 0 for the lowest "
                                f"and {len(groups) - 1} for the highest")
    if column is None or ref_index is None:
        return None
    return Input(column=column, bins=bins, groups=groups, reference=groups[ref_index], reference_index=ref_index)


def parse(raw: Any, source_path: str = "", text: str = "") -> PreSpec:
    if not isinstance(raw, dict):
        raise PreSpecError([f"the pre-spec must be a list of `key: value` lines, starting `prespec: {VERSION}`"])
    problems: list[str] = []
    # a shortlist, or the one-column form: a file with no input's line at the top is read as a shortlist, so a
    # file missing its inputs is asked for them, not for the one-column form's lines
    listed = "inputs" in raw or not any(k in raw for k in INPUT_KEYS)
    own = SHORTLIST_KEYS if listed else KEYS

    marked = set()
    for where, val in _confirm_markers(raw):
        problems.append(f"`{where}` still reads {val!r}: replace it with your answer")
        marked.add(where)
        marked.add(where.split(".")[0].split("[")[0])
    for k in raw:
        if k in REMOVED:
            problems.append(f"`{k}:` is no longer read: {REMOVED[k]}")
        elif listed and k in INPUT_KEYS:
            problems.append(f"`{k}:` is written at the top as well as under `inputs:`. A shortlist names each "
                            f"input's column, bins and reference under `inputs:`; delete the top-level `{k}:`")
        elif k not in own and not (k == "outcome" and not listed):
            problems.append(f"unknown line `{k}:` (known: {', '.join(own)})")
    for k in own:
        if k not in raw:
            problems.append(f"missing line `{k}:`; no line has a default. Add:\n{_LINES[k]}")

    def has(k: str) -> bool:
        return k in raw and k not in marked                # a marked line is reported once, above

    if has("prespec") and (isinstance(raw["prespec"], bool) or raw["prespec"] != VERSION):
        problems.append(f"`prespec:` is {raw['prespec']!r}; this tool reads pre-spec version {VERSION}")

    written = _date(raw["written"], "written", problems) if has("written") else None

    outcome = None
    if has("outcome"):
        v = raw["outcome"]
        if isinstance(v, str) and v.strip():
            outcome = v.strip()
        else:
            problems.append(f"`outcome:` must name the yes/no column every input is tested against, such as "
                            f"BAD_FLAG; got {v!r}")

    inputs: list[Input | None] = []
    if not listed:
        inputs.append(_one_input(raw, "", has, problems))
    elif "inputs" in raw:
        v = raw["inputs"]
        if not isinstance(v, list) or not v or not all(isinstance(x, dict) for x in v):
            if "inputs" not in marked:
                problems.append(f"`inputs:` must list one or more inputs, each with its `column:`, `bins:` and "
                                f"`reference:`; got {v!r}")
        else:
            for i, entry in enumerate(v):
                where = f"inputs[{i}]."
                for k in entry:
                    if k not in INPUT_KEYS:
                        problems.append(f"unknown line `{where}{k}:` (an input has {', '.join(INPUT_KEYS)})")
                for k in INPUT_KEYS:
                    if k not in entry:
                        problems.append(f"missing line `{where}{k}:`; no line has a default. Each input names "
                                        f"its column, bins and reference")
                inputs.append(_one_input(entry, where, lambda k, e=entry, w=where: k in e and w + k not in marked,
                                         problems))
            names = [x.column for x in inputs if x is not None]
            twice = sorted({c for c in names if names.count(c) > 1})
            if twice:
                problems.append(f"`inputs:` lists {', '.join(twice)} more than once")
    tested = [x.column for x in inputs if x is not None]

    strata = None
    if has("strata"):
        v = raw["strata"]
        if not isinstance(v, list) or not all(isinstance(s, str) and s.strip() for s in v):
            problems.append(f"`strata:` must list the columns the pockets are cut by, such as [FICO, CHANNEL], "
                            f"or be [] to treat the whole book as one pocket; got {v!r}")
        else:
            names = [s.strip() for s in v]
            twice = sorted({s for s in names if names.count(s) > 1})
            if twice:
                problems.append(f"`strata:` names {', '.join(twice)} more than once")
            both = [c for c in tested if c in names]
            for c in both:
                problems.append(f"`strata:` includes `{c}`, the column being tested. A column cannot be "
                                f"tested and held fixed at once")
            if outcome is not None and outcome in names:
                problems.append(f"`strata:` includes `{outcome}`, the outcome. It cannot be held fixed")
            if not twice and not both and outcome not in names:
                strata = tuple(names)
    if outcome is not None and outcome in tested:
        problems.append(f"`inputs:` tests `{outcome}`, the outcome itself")

    conf = None
    if has("confidence"):
        v = raw["confidence"]
        if _num(v) and 0.5 <= v < 1:
            conf = float(v)
        else:
            problems.append(f"`confidence:` must be a share between 0.5 and 1, such as 0.95 for 95%; got {v!r}")

    holdout = _range(raw["holdout"], "holdout", problems) if has("holdout") else None
    development = _range(raw["development"], "development", problems) if has("development") else None
    if holdout is not None and development is not None and holdout.overlaps(development):
        problems.append(f"the holdout ({holdout.text()}) overlaps development ({development.text()}). The two "
                        f"ranges may not share a day: the confirmatory run would re-test loans the bins were "
                        f"chosen on")

    if problems:
        raise PreSpecError(problems)
    return PreSpec(written=written, inputs=tuple(inputs), strata=strata, confidence=conf, holdout=holdout,
                   development=development, outcome=outcome, source_path=source_path, text=text, shortlist=listed)


def _confirm_markers(node: Any, where: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _confirm_markers(v, f"{where}.{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _confirm_markers(v, f"{where}[{i}]")
    elif isinstance(node, str) and CONFIRM in node:
        yield where, node


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _finite(v: Any) -> bool:
    return _num(v) and math.isfinite(v)


def _date(v: Any, where: str, problems: list[str]) -> date | None:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            pass
    problems.append(f"`{where}:` must be a date written like 2024-01-01; got {v!r}")
    return None


def _range(v: Any, key: str, problems: list[str]) -> DateRange | None:
    if not isinstance(v, dict) or set(v) != set(RANGE_KEYS):
        problems.append(f"`{key}:` must be {{from: 2024-01-01, to: 2024-12-31}}: the first and last origination "
                        f"dates, both included; got {v!r}")
        return None
    start, end = _date(v["from"], f"{key}.from", problems), _date(v["to"], f"{key}.to", problems)
    if start is None or end is None:
        return None
    if start > end:
        problems.append(f"`{key}:` runs backwards: from {start.isoformat()} is after to {end.isoformat()}")
        return None
    return DateRange(start, end)


def _group_index(v: Any, bins: tuple[float, ...]) -> int | None:
    """Which group a reference names: its number (0 the lowest), its name as the
    grids print it without the data's range, or, for the lowest and highest
    groups, as they print it with the range ("0.01 - 0.09", "2.00 - 7.40")."""
    labels = band_labels(tuple(bins))
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 0 <= v < len(labels) else None
    if not isinstance(v, str):
        return None
    t = " ".join(v.split())
    if t in labels:
        return labels.index(t)
    low_top = " - " + labels[0].removeprefix("up to ")
    high_bottom = labels[-1].removesuffix(" and up") + " - "
    if t.endswith(low_top) and (lo := _number(t[: -len(low_top)])) is not None and lo < bins[0]:
        return 0
    if t.startswith(high_bottom) and (hi := _number(t[len(high_bottom):])) is not None and hi >= bins[-1]:
        return len(labels) - 1
    return None


def _number(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Where it came from

def provenance(path: str | Path) -> dict:
    """The git commit the file was last committed in, and whether the file on
    disk has changed since. Never raises.

    `commit`        the full hash, or None when there is no commit to name
    `committed_at`  the commit's date and time, ISO 8601 with its offset, or None
    `dirty`         True when the file differs from that commit, staged or not;
                    False when it matches; None when there is no commit to compare
    `reason`        None only when the file is committed and unchanged. Otherwise
                    why the pre-spec does not count as it stands, in words.
    """
    out = {"commit": None, "committed_at": None, "dirty": None, "reason": None}
    try:
        p = Path(path).resolve()
        if not p.is_file():
            out["reason"] = f"{p} is not a file, so it has no commit: {ONLY_ONCE_COMMITTED}"
            return out
        log = _git(["log", "-1", "--format=%H%x09%cI", "--", p.name], p.parent)
        if isinstance(log, str):
            out["reason"] = log
            return out
        if log.returncode != 0:
            err = log.stderr or ""
            if "not a git repository" in err:
                out["reason"] = f"not in a git repository, so not committed: {ONLY_ONCE_COMMITTED}"
            elif "does not have any commits yet" in err:
                out["reason"] = f"not committed: {ONLY_ONCE_COMMITTED}"
            else:
                first = err.strip().splitlines()[0] if err.strip() else f"exit code {log.returncode}"
                out["reason"] = f"git could not read the file's history ({first}): {ONLY_ONCE_COMMITTED}"
            return out
        line = log.stdout.strip()
        if not line:
            out["reason"] = f"not committed: {ONLY_ONCE_COMMITTED}"
            return out
        commit, _, when = line.partition("\t")
        out["commit"], out["committed_at"] = commit, when or None
        status = _git(["status", "--porcelain", "--", p.name], p.parent)
        if isinstance(status, str) or status.returncode != 0:
            out["reason"] = (f"committed in {commit[:12]}, but git could not say whether the file has changed "
                             f"since, so it cannot be taken as the committed pre-spec")
            return out
        dirty = bool(status.stdout.strip())
        out["dirty"] = dirty
        if dirty:
            out["reason"] = (f"changed since commit {commit[:12]}: the pre-spec read here is not the one "
                             f"committed. Commit it, or put it back as it was")
        return out
    except Exception as exc:                               # never raise to the caller
        out.update(commit=None, committed_at=None, dirty=None,
                   reason=f"the commit could not be read ({exc}): {ONLY_ONCE_COMMITTED}")
        return out


def _git(args: list[str], cwd: Path):
    """A finished git call, or a sentence saying why git could not be asked.
    The file name is read literally, never as a pattern, and on Windows no
    console window opens behind the launcher."""
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ELSEWHERE}
    try:
        return subprocess.run([GIT, "--literal-pathspecs", *args], cwd=str(cwd), env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except FileNotFoundError:
        return f"git is not installed here, so the commit cannot be read: {ONLY_ONCE_COMMITTED}"
    except subprocess.TimeoutExpired:
        return f"git did not answer within {GIT_TIMEOUT} seconds, so the commit cannot be read: {ONLY_ONCE_COMMITTED}"
    except OSError as exc:
        return f"git could not be run ({exc}): {ONLY_ONCE_COMMITTED}"


# --------------------------------------------------------------------------
# Where the run disagrees with it

_SAID = {
    "column": ("The column tested is", "The column tested is not set"),
    "bins": ("The bins are", "The bins are not set"),
    "reference": ("The reference group is", "The reference group is not set"),
    "strata": ("Pockets are cut by", "What the pockets are cut by is not set"),
    "confidence": ("Confidence is", "Confidence is not set"),
}


def deviations(prespec: PreSpec, in_use: dict, where: str = "on Control") -> list[str]:
    """Every place the run's settings disagree with the pre-spec, one sentence
    each, in the order of `IN_USE_KEYS`. An empty list means the run is the one
    that was pre-specified.

    `in_use` holds what the run used: column, bins (or edges), reference (a
    group's name or number), strata, confidence (a share) and
    holdout: the origination range of the loans it used ({from, to}, a (from, to)
    pair, or a DateRange). A key that is absent or None is reported as not set (the
    holdout's as not known): a run that never said its confidence has not matched
    the pre-spec's. Other keys,
    such as the rest of Control's settings, are not the pre-spec's business and
    are passed over. `where` says where the run's value was read, for the
    sentence; the holdout's sentence is about the loans the run used, wherever its
    settings were read, and never calls their range the holdout. Groups are named
    as `named` named them, from the data's range when it has been read.

    A shortlist (Goal 2 item 3): `in_use["inputs"]` lists each input the run
    tested as {column, bins (or edges), reference}, and each of the pre-spec's
    inputs is compared with the one of the same column, its sentences starting
    "For DTI:". An input the run didn't test, or one it tested that the pre-spec
    doesn't list, is said. Without `inputs`, the flat column, bins and reference
    are the one input's, as for a one-column pre-spec. When the pre-spec names
    its outcome, `in_use["outcome"]` is compared with it first.
    """
    ps = prespec
    got = dict(in_use)
    out: list[str] = []
    if ps.outcome is not None:
        v = got.get("outcome")
        if v is None:
            out.append(f"The outcome is not set {where}; the pre-spec says `{ps.outcome}`.")
        elif not (isinstance(v, str) and v.strip() == ps.outcome):
            out.append(f"The outcome is `{v}` {where}; the pre-spec says `{ps.outcome}`.")
    listed = got.get("inputs")
    if listed is None or (len(ps.inputs) == 1 and not ps.shortlist and not isinstance(listed, (list, tuple))):
        out += _input_deviations(ps.inputs[0], got, where, "")
    else:
        seen_cols = []
        by_col = {}
        for x in listed if isinstance(listed, (list, tuple)) else ():
            c = x.get("column") if isinstance(x, dict) else None
            if isinstance(c, str):
                by_col.setdefault(c.strip(), x)
                seen_cols.append(c.strip())
        many = len(ps.inputs) > 1 or ps.shortlist
        for inp in ps.inputs:
            x = by_col.get(inp.column)
            if x is None:
                out.append(f"`{inp.column}` isn't tested {where}; the pre-spec lists it.")
                continue
            out += _input_deviations(inp, x, where, f"For {inp.column}: " if many else "")
        for c in seen_cols:
            if c not in ps.columns:
                out.append(f"`{c}` is tested {where}; the pre-spec doesn't list it.")
    want = {"strata": _strata_text(ps.strata), "confidence": _pct(ps.confidence)}
    for key in IN_USE_KEYS[3:]:
        v = got.get(key)
        if key == "holdout":
            said = _holdout_said(ps.holdout, v)
            if said:
                out.append(said)
            continue
        says, unset = _SAID[key]
        if v is None:
            out.append(f"{unset} {where}; the pre-spec says {want[key]}.")
            continue
        seen = None                                        # what the run used, in words, when it differs
        if key == "strata":
            cols = [v] if isinstance(v, str) else v
            if not isinstance(cols, (list, tuple)) or not all(isinstance(c, str) for c in cols):
                seen = repr(v)
            elif {c.strip() for c in cols} != set(ps.strata):
                seen = _strata_text(tuple(c.strip() for c in cols))
        elif key == "confidence":
            c = _share(v)
            if c is None:
                seen = repr(v)
            elif not math.isclose(c, ps.confidence, rel_tol=1e-9, abs_tol=1e-12):
                seen = _pct(c)
                if seen == want[key]:                      # differs past the printed digits: show them all
                    seen, want[key] = repr(c), repr(ps.confidence)
        if seen is not None:
            out.append(f"{says} {seen} {where}; the pre-spec says {want[key]}.")
    return out


def _input_deviations(inp: Input, got: dict, where: str, lead: str) -> list[str]:
    """Where one input's column, bins and reference differ from what the run used (`got`), one sentence each."""
    got = dict(got)
    if got.get("bins") is None and got.get("edges") is not None:
        got["bins"] = got["edges"]
    want = {"column": f"`{inp.column}`", "bins": _bins_text(inp.bins), "reference": f"`{inp.reference}`"}
    in_bins = _as_bins(got.get("bins"))
    out = []
    for key in IN_USE_KEYS[:3]:
        v = got.get(key)
        says, unset = _SAID[key]
        if lead:
            says, unset = lead + says[0].lower() + says[1:], lead + unset[0].lower() + unset[1:]
        if v is None:
            out.append(f"{unset} {where}; the pre-spec says {want[key]}.")
            continue
        seen = None
        if key == "column":
            if not (isinstance(v, str) and v.strip() == inp.column):
                seen = f"`{v}`"
        elif key == "bins":
            if in_bins is None:
                seen = repr(v)
            elif not _same_bins(in_bins, inp.bins):
                seen = _bins_text(in_bins)
        else:
            bins = in_bins if in_bins is not None else inp.bins
            idx = _group_index(v, bins)
            names = band_labels(bins, inp.lo, inp.hi)
            if idx is None:
                seen = f"`{v}`, which is not one of its bins' groups"
            elif _same_bins(bins, inp.bins):
                if idx != inp.reference_index:
                    seen = f"`{names[idx]}`"
            elif names[idx] != inp.reference:
                seen = f"`{names[idx]}`"
        if seen is not None:
            out.append(f"{says} {seen} {where}; the pre-spec says {want[key]}.")
    return out


def _holdout_said(hold: DateRange, v: Any) -> str | None:
    """How the loans a run used differ from the holdout, or None when they are it.
    Found 26 Sep 2026: "The holdout is 2021-06-30 to 2024-12-30 in this run" named
    the range of every loan run as if it were a holdout."""
    said = f"The pre-spec's holdout is {hold.text()}; "
    if v is None:
        return said + "when this run's loans were made isn't known."
    r = _as_range(v)
    if r is None:
        return said + f"this run's loans were made {v!r}, which is not a date range."
    if r == hold:
        return None
    if not r.overlaps(hold):
        tail = "none of them in the holdout"
    elif hold.start <= r.start and r.end <= hold.end:
        tail = "only part of the holdout"
    else:
        tail = "not only the holdout"
    return said + f"this run used loans made {r.text()}, {tail}."


def _as_bins(v: Any) -> tuple[float, ...] | None:
    if not isinstance(v, (list, tuple)) or not v or not all(_finite(x) for x in v):
        return None
    if any(b <= a for a, b in zip(v, v[1:])):
        return None
    return tuple(float(x) for x in v)


def _same_bins(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return len(a) == len(b) and all(math.isclose(x, y, rel_tol=1e-12, abs_tol=0.0) for x, y in zip(a, b))


def _share(v: Any) -> float | None:
    if _num(v):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _as_range(v: Any) -> DateRange | None:
    if isinstance(v, DateRange):
        return v
    if isinstance(v, dict) and set(v) == set(RANGE_KEYS):
        a, b = v["from"], v["to"]
    elif isinstance(v, (list, tuple)) and len(v) == 2:
        a, b = v
    else:
        return None
    scratch: list[str] = []
    a, b = _date(a, "from", scratch), _date(b, "to", scratch)
    return DateRange(a, b) if a is not None and b is not None else None


def _n(x: float) -> str:
    x = float(x)
    return str(int(x)) if x.is_integer() else repr(x)


def _bins_text(bins: Iterable[float]) -> str:
    return ", ".join(_n(x) for x in bins)


def _strata_text(strata: tuple[str, ...]) -> str:
    return ", ".join(strata) if strata else "nothing (the whole book is one pocket)"


def _pct(share: float) -> str:
    return f"{round(share * 100, 6):g}%"


# --------------------------------------------------------------------------
# Whether the run touched the holdout

def holdout_touch(prespec: PreSpec, origination_dates: Iterable[date | datetime | None]
                  ) -> tuple[int, date | None, date | None]:
    """How many loans in the extract were made inside the holdout range, and
    the first and last of their origination dates: (count, first, last), or
    (0, None, None) when none were.

    Both ends of the range are inclusive: a loan made on the holdout's `from`
    date is inside, and so is one made on its `to` date. A run that touches
    the holdout is the confirmatory one, and the Log records each such run, so
    how many times the holdout has been looked at stays visible.

    A date-and-time counts as its date. None (a loan with no usable date) is
    passed over; the caller counts those, as it counts any unreadable cell.
    Anything else is a mistake in the caller and raises TypeError.
    """
    hold = prespec.holdout
    count, first, last = 0, None, None
    for d in origination_dates:
        if d is None:
            continue
        if isinstance(d, datetime):
            d = d.date()
        elif not isinstance(d, date):
            raise TypeError(f"holdout_touch reads dates or None; got {d!r}")
        if hold.holds(d):
            count += 1
            first = d if first is None or d < first else first
            last = d if last is None or d > last else last
    return count, first, last
