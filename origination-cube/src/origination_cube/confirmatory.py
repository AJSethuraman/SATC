"""A run held to a pre-spec (fix 3.15): prespec.py read at Run, echoed on
Check, compared with what the run used, and the holdout's use counted in the
Log.

prespec.py reads the file and returns data; this is where a Run meets it.

- The file is named in one cell on Control, under the new columns
  (control.write_prespec). Blank means no pre-spec. A file that is not there,
  or that prespec.load refuses, stops the Run, each problem named by that cell.
- Check echoes what the file says, and the git commit it was read from, or why
  there is none (prespec.provenance). A pre-spec edited since its commit says so,
  and so does one dated after the day of the run. Its groups are named as the
  tabs name them, the lowest and highest from the tested column's smallest and
  largest value among the loans run (prespec.named), so one group has one name.
- Check says, one line each, every place the run differs from the pre-spec
  (prespec.deviations), and the Log labels the run "Deviates from pre-spec".
- The holdout: how many of the extract's loans were made inside the pre-spec's
  holdout range (prespec.holdout_touch). A run that touched it says so in the
  Log, on a line starting "Touched the holdout:", and Check counts those lines,
  so how many runs have looked at the holdout stays visible.

What the run used, as the pre-spec's keys (`in_use`):
- column: the column that splits the pockets; with no split, the pre-spec's
  column if the run cuts it into bands; otherwise not set.
- bins: for a band column, the edges it was cut at; for the split column, the
  edges typed for it on Columns (the Prevalence tab's bands). The Split tab
  itself tests each pocket's halves, not bins.
- reference: what each group was compared with. The split's is the low half of
  each pocket; a band's is the rest of its band, or of the book. None of those
  is one of the pre-spec's groups, so today's cube always differs here: it has
  no test of groups against a reference group yet (docs/NEXT-GOAL.md 4b).
- strata: the band and segment columns, the tested column left out.
- window_months and confidence: as Control has them. No window is not set.
- holdout: the origination range of the loans the run used. When every one of
  them was made inside the pre-spec's holdout, the run used the holdout;
  otherwise the range it used is reported, since a confirmatory run on loans
  outside the holdout is not the one pre-specified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import control, engine, prespec

HOLDOUT_MARK = "Touched the holdout:"       # how a Log line says a run touched the holdout; Check counts them
DEVIATES = "Deviates from pre-spec"          # how a Log line labels a run that differs from its pre-spec
LOW_HALF = "the low half of each pocket"


@dataclass
class State:
    spec: prespec.PreSpec
    path: Path
    cell: str
    provenance: dict
    deviations: list[str] = field(default_factory=list)
    touched: int | None = None               # extract loans made in the holdout; None when it couldn't be checked
    first: date | None = None                # the first and last origination date among them
    last: date | None = None
    undated: int = 0                         # extract loans with no readable origination date
    unchecked: str | None = None             # why the holdout couldn't be checked
    runs_before: int = 0                     # Log lines already saying a run touched the holdout
    failed: str | None = None                # something went wrong working the state out, in words
    ran_on: date = field(default_factory=date.today)     # the day of the run, which the pre-spec can't postdate

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def runs(self) -> int:
        """Runs in this workbook's Log that touched the holdout, this one included."""
        return self.runs_before + (1 if self.touched else 0)


# --------------------------------------------------------------------------
# Reading the cell and the file (book.read_book)


def read(wb, book: Path, problems: list[str]) -> dict | None:
    """The pre-spec named on Control, loaded, as {spec, path, cell}; None when
    the cell is blank. Every problem is added to `problems`, named by the cell."""
    if control.SHEET not in wb.sheetnames:
        return None
    text, cell = control.read_prespec(wb[control.SHEET])
    if text is None:
        return None
    p = Path(text).expanduser()
    if not p.is_absolute():
        p = Path(book).resolve().parent / p
    if not p.is_file():
        problems.append(f"{cell}: there's no pre-spec file at {p}. Fix the path, or clear the cell for a run "
                        f"without a pre-spec.")
        return None
    try:
        spec = prespec.load(p)
    except prespec.PreSpecError as exc:
        for x in exc.problems:
            x = x.removeprefix(f"{p}: ")
            problems.append(f"{cell}: in the pre-spec {p.name}, {_plain(x)}")
        return None
    return {"spec": spec, "path": p, "cell": cell}


def _plain(text: str) -> str:
    return text.replace("`", '"')


# --------------------------------------------------------------------------
# After the engine has run (checks.attach)


def state(book, about: dict, res) -> State | None:
    got = (about or {}).get("_prespec")
    if not got:
        return None
    ps = got["spec"]
    st = State(spec=ps, path=Path(got["path"]), cell=got["cell"], provenance=prespec.provenance(got["path"]))
    try:
        ps = st.spec = prespec.named(ps, *column_range(res, ps.column))
        st.deviations = [_plain(x) for x in prespec.deviations(ps, in_use(res, ps), where="in this run")]
        dates, why = origination_dates(res)
        if dates is None:
            st.unchecked = why
        else:
            st.touched, st.first, st.last = prespec.holdout_touch(ps, dates)
            st.undated = sum(1 for d in dates if d is None)
        st.runs_before = holdout_runs(book)
    except Exception as exc:                     # a line on Check, never a failed run after the engine ran
        st.failed = f"the run couldn't be compared with the pre-spec ({exc})"
    return st


def in_use(res, ps: prespec.PreSpec) -> dict[str, Any]:
    """What the run used, as prespec.deviations reads it (the module docstring says how each is found)."""
    from .prevalence import edges_of
    cfg = res.config
    b = cfg.benchmark
    cut = [x.field for x in cfg.bands] + [x.field for x in cfg.dimensions]
    out: dict[str, Any] = {"column": None, "bins": None, "reference": None}
    if cfg.split:
        sf, how = cfg.split
        out["column"] = sf
        if how == "own_median":
            out["bins"] = list(edges_of(res, sf)[0] or ()) or None
            out["reference"] = LOW_HALF
    elif ps.column in [x.field for x in cfg.bands]:
        out["column"] = ps.column
        out["bins"] = list(edges_of(res, ps.column)[0] or ()) or None
    if out["column"] is not None and out["reference"] is None and b is not None:
        out["reference"] = "the rest of its band" if b.compare_to == "peers" else "the rest of the book"
    out["strata"] = [c for c in cut if c != out["column"]]
    out["window_months"] = cfg.window_months or None
    out["confidence"] = b.confidence if b is not None else None
    out["holdout"] = run_range(res, ps)
    return out


def column_range(res, column: str) -> tuple[float | None, float | None]:
    """A number column's smallest and largest value among the loans run, read as
    the tabs read it to name their lowest and highest bands; (None, None) when no
    loan has one."""
    from .prevalence import rows_run
    rule = res.config.missing.get(column)
    seen = [v for v, why in (engine.classify_number(r.get(column), rule) for r in rows_run(res)) if why is None]
    return (min(seen), max(seen)) if seen else (None, None)


def _reader(res):
    """How to read the origination dates, or (None, why not)."""
    col = res.config.origination_date
    table = res.table
    if not col:
        return None, "no column is marked Origination date on Columns"
    if table is None or col not in table.columns:
        return None, f"{col} isn't in the extract"
    try:
        return engine._date_reader(table, col, "when each loan was made"), None
    except engine.NothingToCut as exc:            # dates that read two ways (DataRefused)
        return None, _plain(str(exc))


def _date_or_none(v) -> date | None:
    return v if isinstance(v, date) else None


def origination_dates(res) -> tuple[list[date | None] | None, str | None]:
    """Every extract loan's origination date (None where it can't be read), or
    (None, why) when there is no date to read."""
    read, why = _reader(res)
    if read is None:
        return None, why
    col = res.config.origination_date
    return [_date_or_none(read(r.get(col))) for r in res.table.rows], None


def run_range(res, ps: prespec.PreSpec):
    """The origination range the run used, as a holdout: the pre-spec's own
    holdout when every loan run was made inside it, else the range run; None
    when the run's loans carry no readable origination date."""
    from .prevalence import rows_run
    read, _ = _reader(res)
    if read is None:
        return None
    col = res.config.origination_date
    seen = [d for d in (_date_or_none(read(r.get(col))) for r in rows_run(res)) if d is not None]
    if not seen:
        return None
    first, last = min(seen), max(seen)
    if ps.holdout.holds(first) and ps.holdout.holds(last):
        return ps.holdout
    return prespec.DateRange(first, last)


def holdout_runs(book) -> int:
    """How many runs this workbook's Log already records as touching the holdout."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(book, read_only=True)
    except Exception:
        return 0
    try:
        if "Log" not in wb.sheetnames:
            return 0
        return sum(1 for (v,) in wb["Log"].iter_rows(min_col=2, max_col=2, values_only=True)
                   if isinstance(v, str) and v.startswith(HOLDOUT_MARK))
    finally:
        wb.close()


# --------------------------------------------------------------------------
# What it says: Check, the Log, the launcher and the record of what ran


def _commit_words(st: State) -> str:
    pv = st.provenance
    if not pv.get("commit"):
        return pv.get("reason") or "no commit could be read"
    when = str(pv.get("committed_at") or "").replace("T", " ")
    said = f"{pv['commit'][:12]}, committed {when}" if when else pv["commit"][:12]
    if pv.get("dirty"):
        said += "; edited since that commit, so the file read here isn't the one committed"
    elif pv.get("reason"):
        said += f"; {pv['reason']}"
    return said


def _says(ps: prespec.PreSpec) -> str:
    """The pre-spec's lines, as read."""
    strata = ", ".join(ps.strata) if ps.strata else "none (the whole book is one pocket)"
    return "\n".join([
        f"written: {ps.written.isoformat()}",
        f"column: {ps.column}",
        f"bins: {', '.join(engine._fmt(x) for x in ps.bins)} (groups: {'; '.join(ps.groups)})",
        f"reference: {ps.reference}",
        f"strata: {strata}",
        f"window_months: {ps.window_months}",
        f"confidence: {ps.confidence:g}",
        f"holdout: {ps.holdout.text()}",
        f"development: {ps.development.text()}",
    ])


def _holdout_words(st: State) -> str:
    rng = st.spec.holdout.text()
    if st.touched is None:
        return f"Couldn't be checked: {st.unchecked}. The holdout is {rng}."
    if st.touched:
        said = (f"{st.touched:,} of this extract's loans were made in the holdout ({rng}), the first on "
                f"{st.first.isoformat()} and the last on {st.last.isoformat()}. This run touched the holdout.")
    else:
        said = f"None of this extract's loans were made in the holdout ({rng})."
    if st.undated:
        said += (f" {st.undated:,} loan{'s have' if st.undated != 1 else ' has'} no readable origination date, so "
                 f"whether {'they are' if st.undated != 1 else 'it is'} in it is unknown.")
    return said


def check_rows(res) -> list[tuple[str, str]]:
    st = getattr(res, "prespec", None)
    if st is None:
        return []
    out = [("Pre-spec", str(st.path)), ("Pre-spec commit", _commit_words(st)),
           ("What the pre-spec says", _says(st.spec))]
    if st.spec.written > st.ran_on:
        out.append(("Warning", f"The pre-spec says it was written on {st.spec.written.isoformat()}, after this run."))
    if st.provenance.get("reason"):
        out.append(("Warning", "This run doesn't count as the pre-specified one until the pre-spec is committed, "
                               "unchanged."))
    if st.failed:
        out.append(("Warning", f"Pre-spec: {st.failed}."))
    elif st.deviations:
        out += [("Warning", f"{DEVIATES}: {d}") for d in st.deviations]
    else:
        out.append(("Differs from the pre-spec", "nowhere: this run used what it says"))
    out.append(("Holdout", _holdout_words(st)))
    runs = f"{st.runs:,} in this workbook's Log" + (", this one included" if st.touched else "")
    if st.touched is None:
        runs = f"{st.runs_before:,} in this workbook's Log before this one, which couldn't be checked"
    out.append(("Runs that touched the holdout", runs))
    return out


def log_lines(res) -> list[str]:
    """Lines for this run's Log entry: whether it followed its pre-spec, and whether it touched the holdout."""
    st = getattr(res, "prespec", None)
    if st is None:
        return []
    commit = st.provenance.get("commit")
    of = (f"commit {commit[:12]}" + (", edited since" if st.provenance.get("dirty") else "")) if commit \
        else "not committed"
    if st.failed:
        out = [f"Pre-spec {st.name} ({of}): {st.failed}."]
    elif st.deviations:
        k = len(st.deviations)
        out = [f"{DEVIATES} {st.name} ({of}): {k} {'place' if k == 1 else 'places'}, listed on Check."]
    else:
        out = [f"Follows pre-spec {st.name} ({of})."]
    if st.touched:
        out.append(f"{HOLDOUT_MARK} {st.touched:,} loan{'s' if st.touched != 1 else ''} made "
                   f"{st.first.isoformat()} to {st.last.isoformat()}.")
    elif st.touched is None:
        out.append(f"Holdout not checked: {st.unchecked}.")
    return out


def launcher_lines(res) -> list[str]:
    st = getattr(res, "prespec", None)
    if st is None:
        return []
    return log_lines(res) + [f"Runs that touched the holdout, in this workbook's Log: {st.runs:,}."]


def what_ran(res) -> str:
    """Comment lines for the top of the record of what ran."""
    st = getattr(res, "prespec", None)
    if st is None:
        return ""
    out = f"# pre-spec: {st.path} ({_commit_words(st)})\n"
    for d in st.deviations:
        out += f"# differs from the pre-spec: {d}\n"
    for line in log_lines(res)[1:]:
        out += f"# {line}\n"
    return out
