"""The cube file: load it, check it, and refuse with the line to add.

Nothing in here knows what a column means. The file names the bank's columns
in each slot, so the file *is* the mapping. It replaces the VBA workbook's
Config sheet, and removes the class of bug that sheet had: settings found at
fixed row numbers (finding 5) and decisions stored against a row rather than a
column name (the D56 stamp). Here every setting is found by its key and every
decision is written against a column's name.

Refuse, never default (finding 8). A line that changes what the grid says is
required, and its absence is a refusal that prints the line to add. A key the
file does not recognise is refused too: a misspelled `worse_at` that was
quietly ignored would be exactly the silent fallback this file exists to stop.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
#: The marker a person must replace. A file still carrying one is refused,
#: naming each (the VBA's "undecided REVIEW row stops the run", finding 3).
CONFIRM = "[CONFIRM:"

RATE_MODES = ("flagwt", "sumnum")
MODES = RATE_MODES + ("count", "median")
MODE_KEYS = {
    "flagwt": {"required": ("flag", "per", "higher_is"), "allowed": ("optional",)},
    "sumnum": {"required": ("value", "per", "higher_is"), "allowed": ("optional",)},
    "count": {"required": (), "allowed": ()},
    "median": {"required": ("value",), "allowed": ("optional",)},
}
TOP_KEYS = {"name", "schema_version", "key", "booked", "outcome", "gco", "ranr", "columns", "columns_confirmed",
            "missing", "bands", "dimensions", "measures", "benchmark", "questions", "min_age_months",
            "origination_date", "as_of"}
#: The firm, 25 Sep 2026: "this analysis only works if we have, at a minimum, an
#: output binary ... the GCO amount and RANR amount ... the booked amount ... and a
#: loan number or app number or some other Key or we cannot perform the remapping
#: exercise." So each of those is a required line, and the core rates are built
#: from them on every run; `measures:` holds only extras.
CORE = ("key", "booked", "outcome", "gco", "ranr")
#: The required columns are said either as five top-level lines (a file written
#: by hand) or as meanings in `columns:` (a file written by `cube init`, which
#: lists every column). Never both: one place to say it.
REQUIRED_TOP = ("name", "schema_version", "bands", "dimensions", "benchmark", "min_age_months")
#: `per: each_loan` divides by the number of loans rather than a column: a
#: straight share or average, beside the booked-weighted one reporting uses.
EACH_LOAN = "each_loan"
CORE_NAMES = ("outcome_loans", "outcome_booked", "gco_rate", "ranr_rate")
MISSING_KEYS = {"below", "above", "values"}
BENCHMARK_KEYS = ("min_units", "min_events", "worse_at", "better_at", "confidence", "power", "compare_to",
                  "many_tests", "materiality")
COMPARE_TO = ("peers", "topline")
MANY_TESTS = ("none", "bh", "bonferroni")
HIGHER_IS = ("worse", "better")
CUTS = ("equal_loans", "round")
ANSWERS = ("real", "missing")


class ConfigError(Exception):
    """One or more problems with the cube file, one per line."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class MissingRule:
    """Values in one column that mean "missing" (ruling OC-2): a bureau score
    under -1000, say, is the bureau saying it has no score. Applied before
    anything else reads the column, and every value it catches is counted."""
    below: float | None = None
    above: float | None = None
    values: tuple[Any, ...] = ()


@dataclass(frozen=True)
class Band:
    """A number column cut into ranges. Either the cut points are given
    (`edges`), or how many bands and how to place them (`count` and `cut`),
    in which case the engine works the edges out from the data and reports
    them, so more or fewer bands is one number in the file."""
    name: str
    field: str
    edges: tuple[float, ...] = ()
    count: int | None = None
    cut: str | None = None           # equal_loans | round


@dataclass(frozen=True)
class Dimension:
    name: str
    field: str


@dataclass(frozen=True)
class Measure:
    """One figure per cell.

    flagwt  SUM(per WHERE flag = 1) / SUM(per)
    sumnum  SUM(value) / SUM(per)       - signed values pass through (D47)
    count   rows in the cell
    median  MEDIAN(value) per cell      - positional, does not add up

    `per` is named on every rate, so a ratio of any two columns is a file
    line rather than code: GCO per booked balance, RANR per booked balance,
    GCO per RANR.
    """
    name: str
    mode: str
    value: str | None = None      # sumnum, median
    flag: str | None = None       # flagwt
    per: str | None = None        # flagwt, sumnum: a column, or each_loan
    optional: bool = False        # absent column -> skipped with a warning (D55)
    flag_is: Any = None           # flagwt: the value that means yes, when the flag is not 0/1 already
    core: bool = False            # built from the required lines, never optional
    higher_is: str = "worse"      # worse for a loss (GCO, a bad-loan rate); better for revenue (RANR)

    @property
    def is_rate(self) -> bool:
        return self.mode in RATE_MODES

    @property
    def reconciles(self) -> bool:
        """Median is positional: cell medians do not add up to a portfolio
        median, so it is labelled rather than put through the tie-out."""
        return self.mode != "median"

    @property
    def title(self) -> str:
        """The measure as a person names it, on every screen a person reads."""
        return {"outcome_loans": "Outcome, share of loans", "outcome_booked": "Outcome, share of booked dollars",
                "gco_rate": "GCO per booked dollar", "ranr_rate": "RANR per booked dollar"}.get(self.name, self.name)

    def columns(self) -> tuple[str, ...]:
        return tuple(c for c in (self.value, self.flag, self.per) if c and c != EACH_LOAN)

    def _yes(self) -> str:
        return f"{self.flag} = {self.flag_is!r}" if self.flag_is is not None else f"{self.flag} = 1"

    def numerator(self) -> str:
        """What the excess is counted in, in the file's own column names."""
        if self.mode == "flagwt":
            return f"loans where {self._yes()}" if self.per == EACH_LOAN else f"{self.per} on loans where {self._yes()}"
        return self.value or ""

    def label(self) -> str:
        """The grid states its own arithmetic."""
        if self.mode == "flagwt":
            if self.per == EACH_LOAN:
                return f"COUNT(loans where {self._yes()}) / COUNT(loans)"
            return f"SUM({self.per} where {self._yes()}) / SUM({self.per})"
        if self.mode == "sumnum":
            if self.per == EACH_LOAN:
                return f"SUM({self.value}) / COUNT(loans)"
            return f"SUM({self.value}) / SUM({self.per})"
        if self.mode == "count":
            return "Loans (rows)"
        return f"MEDIAN({self.value}) per cell - positional, does not add up"


@dataclass(frozen=True)
class Benchmark:
    """Every call that decides what a pocket's word is. All required, none
    defaulted: the Control tab or the person writes each one."""
    min_units: int                   # below this a pocket is shown but not tested
    min_events: int                  # a loss rate resting on fewer losses than this is not tested
    worse_at: float
    better_at: float
    confidence: float
    power: float
    compare_to: str                  # peers | topline: which comparison decides the flag
    many_tests: str                  # none | bh | bonferroni
    materiality: tuple               # ("share", 0.01) | ("dollars", 250000.0) | ("none", 0.0)


@dataclass(frozen=True)
class Question:
    """Something odd in a column that the engine will not decide about
    (ruling OC-7). Unanswered, the values are used as recorded and every
    output says the question is open. `missing` turns it into a rule;
    `real` closes it."""
    column: str
    pattern: str                      # "repeated_value" | "negatives"
    value: float | None
    rows: int
    answer: str | None                # None | "real" | "missing"

    def as_rule(self) -> "MissingRule | None":
        if self.answer != "missing":
            return None
        if self.pattern == "negatives":
            return MissingRule(below=0.0)
        return MissingRule(values=(self.value,))

    def text(self) -> str:
        what = ("negative values in a column that is mostly positive" if self.pattern == "negatives"
                else f"the value {_fmt_num(self.value)} repeated far more than any other")
        return f"`{self.column}`: {what} ({self.rows:,} rows)"


def _fmt_num(x) -> str:
    return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)


@dataclass(frozen=True)
class Config:
    name: str
    key: str
    missing: dict[str, MissingRule]
    bands: tuple[Band, ...]
    dimensions: tuple[Dimension, ...]
    measures: tuple[Measure, ...]
    benchmark: Benchmark | None      # None only when the file says `benchmark: none`
    questions: tuple[Question, ...] = ()
    booked: str = ""
    outcome: str = ""
    min_age_months: int = 0
    origination_date: str | None = None
    as_of: Any = None                                 # a date, or the name of a column holding it
    columns: dict = field(default_factory=dict)       # column -> (meaning, is-value); from `columns:`
    not_cut: dict = field(default_factory=dict)       # column -> meaning, for meanings never cut by
    source_path: str = ""
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def referenced_columns(self) -> list[str]:
        cols = [b.field for b in self.bands] + [d.field for d in self.dimensions]
        for m in self.measures:
            cols += list(m.columns())
        seen: list[str] = []
        for c in cols:
            if c not in seen:
                seen.append(c)
        return seen


# --------------------------------------------------------------------------

def load(path: str | Path) -> Config:
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError([f"{p}: not readable as YAML: {exc}"]) from exc
    return parse(raw, source_path=str(p))


def parse(raw: Any, source_path: str = "") -> Config:
    if not isinstance(raw, dict):
        raise ConfigError(["the cube file must be a mapping of `key: value` lines"])
    problems: list[str] = []

    markers = list(_confirm_markers(raw))
    for where, text in markers:
        problems.append(f"`{where}` still reads {text!r}: replace it with your answer")

    for k in raw:
        if k not in TOP_KEYS:
            problems.append(f"unknown line `{k}:` (known: {', '.join(sorted(TOP_KEYS))})")
    for k in REQUIRED_TOP:
        if k not in raw:
            problems.append(_missing_line(k))

    if "schema_version" in raw and raw["schema_version"] != SCHEMA_VERSION:
        problems.append(f"schema_version is {raw['schema_version']!r}; this engine reads {SCHEMA_VERSION}")

    columns, not_cut = {}, {}
    if "columns" in raw:
        columns, not_cut = _parse_columns(raw.get("columns"), problems)
        both = [k for k in CORE if k in raw]
        if both:
            problems.append(f"{', '.join('`' + k + ':`' for k in both)} and `columns:` both say which column is "
                            f"which; keep `columns:` and delete the other lines")
        if raw.get("columns_confirmed") is not True:
            named = ", ".join(f"{m}: {', '.join(c for c, (mm, _) in columns.items() if mm == m) or '(none)'}"
                              for m in CORE)
            problems.append(f"the column meanings were suggested by `cube init` and are not confirmed yet "
                            f"({named}). Check each; change `means:` on any that is wrong; then set "
                            f"`columns_confirmed: yes`")
        raw = dict(raw)
        for m in CORE:
            hits = [c for c, (mm, _) in columns.items() if mm == m]
            if len(hits) != 1:
                problems.append(f"`columns:` needs exactly one column that means {m}; found "
                                f"{len(hits)}{': ' + ', '.join(hits) if hits else ''}")
                continue
            raw[m] = hits[0] if m != "outcome" or columns[hits[0]][1] is None else \
                {"field": hits[0], "is": columns[hits[0]][1]}
    else:
        for k in CORE:
            if k not in raw:
                problems.append(_missing_line(k))
    cols = {}
    for k in ("key", "booked", "gco", "ranr"):
        v = raw.get(k)
        if k in raw and (not isinstance(v, str) or not v.strip()):
            problems.append(f"`{k}:` must name a column")
        cols[k] = v.strip() if isinstance(v, str) else ""
    out_field, out_is, out_label = _parse_outcome(raw.get("outcome"), problems) if "outcome" in raw else ("", None, "")
    key = cols["key"]

    missing = _parse_missing(raw.get("missing") or {}, problems)
    bands = _parse_bands(raw.get("bands"), problems) if "bands" in raw else ()
    dims = _parse_dims(raw.get("dimensions"), problems) if "dimensions" in raw else ()
    extras = _parse_measures(raw.get("measures"), problems) if raw.get("measures") else ()
    for m in extras:
        if m.name in CORE_NAMES:
            problems.append(f"measure name `{m.name}` is taken by a core rate; call it something else")
    core = ()
    if out_field and cols["booked"] and cols["gco"] and cols["ranr"]:
        # RANR is revenue: bigger is better (the firm, 25 Sep 2026). Its bleed is a shortfall.
        core = (Measure(name="outcome_loans", mode="flagwt", flag=out_field, per=EACH_LOAN, flag_is=out_is, core=True),
                Measure(name="outcome_booked", mode="flagwt", flag=out_field, per=cols["booked"], flag_is=out_is,
                        core=True),
                Measure(name="gco_rate", mode="sumnum", value=cols["gco"], per=cols["booked"], core=True),
                Measure(name="ranr_rate", mode="sumnum", value=cols["ranr"], per=cols["booked"], core=True,
                        higher_is="better"))
    age, orig_col, as_of = _parse_age(raw, columns, problems)
    measures = core + extras
    bench = _parse_benchmark(raw.get("benchmark"), problems) if "benchmark" in raw else None
    questions = _parse_questions(raw.get("questions") or [], problems)
    for q in questions:
        rule = q.as_rule()
        if rule is not None:
            old = missing.get(q.column, MissingRule())
            missing[q.column] = MissingRule(below=rule.below if rule.below is not None else old.below,
                                            above=old.above, values=old.values + rule.values)

    names = [b.name for b in bands] + [d.name for d in dims] + [m.name for m in measures]
    dupes = sorted({n for n in names if names.count(n) > 1})
    for n in dupes:
        problems.append(f"the name `{n}` is used more than once; every band, dimension and measure needs its own")

    if problems:
        raise ConfigError(problems)
    return Config(name=str(raw["name"]), key=key, missing=missing, bands=bands, dimensions=dims,
                  measures=measures, benchmark=bench, questions=questions, booked=cols["booked"], outcome=out_field,
                  min_age_months=age, origination_date=orig_col, as_of=as_of,
                  columns=columns, not_cut=not_cut, source_path=source_path, raw=raw)


# --------------------------------------------------------------------------

def _confirm_markers(node: Any, where: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _confirm_markers(v, f"{where}.{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _confirm_markers(v, f"{where}[{i}]")
    elif isinstance(node, str) and CONFIRM in node:
        yield where, node


def _parse_columns(node: Any, problems: list[str]) -> tuple[dict, dict]:
    """`columns:` maps each column to what it means: `COL: fico` or
    `COL: {means: outcome, is: AUTO}`. The meanings are the catalog in
    settings.yaml; an unknown one is refused with the list."""
    from .meanings import catalog
    cat = catalog()
    if not isinstance(node, dict) or not node:
        problems.append("`columns:` must list each column and what it means, e.g.  FICO: {means: fico}")
        return {}, {}
    out, not_cut = {}, {}
    for col, v in node.items():
        means, is_value = (v, None) if isinstance(v, str) else ((v or {}).get("means"), (v or {}).get("is")) \
            if isinstance(v, dict) else (None, None)
        if isinstance(v, dict):
            _unknown(v, {"means", "is"}, f"columns.{col}", problems)
        if means not in cat:
            problems.append(f"columns.{col}: `means: {means}` is not a meaning this tool knows. "
                            f"Use one of: {', '.join(cat)}")
            continue
        out[str(col)] = (means, is_value)
        if cat[means].cut == "none":
            not_cut[str(col)] = means
    return out, not_cut


def _parse_outcome(node: Any, problems: list[str]) -> tuple[str, Any, str]:
    """`outcome: COLUMN` for a 0/1 column, or `outcome: {field: COLUMN, is: VALUE}`
    to make any column yes/no: charged off, ever delinquent, decided by the system."""
    if isinstance(node, str) and node.strip():
        return node.strip(), None, ""
    if isinstance(node, dict):
        _unknown(node, {"field", "is", "label"}, "outcome", problems)
        f = node.get("field")
        if isinstance(f, str) and f.strip():
            return f.strip(), node.get("is"), str(node.get("label") or "")
    problems.append("`outcome:` must name a yes/no column (0 or 1), or be {field: COLUMN, is: VALUE}")
    return "", None, ""


def _missing_line(k: str) -> str:
    lines = {
        "key": "key: LOAN_NUMBER_COLUMN        # loan or application number: needed to map results back to loans",
        "booked": "booked: BOOKED_AMOUNT_COLUMN   # the loan amount that weights the reporting-level rates",
        "outcome": ("outcome: OUTCOME_COLUMN        # any yes/no (0/1): charged off, ever delinquent, ...\n"
                    "# or:  outcome: {field: DECISION_COLUMN, is: AUTO}"),
        "gco": "gco: GCO_AMOUNT_COLUMN          # gross charge-off dollars",
        "ranr": "ranr: RANR_AMOUNT_COLUMN        # RANR dollars (signed values are kept as they are)",
        "name": "name: my_cube",
        "schema_version": f"schema_version: {SCHEMA_VERSION}",
        "bands": "bands:\n  - {name: score_band, field: SCORE_COLUMN, edges: [620, 680, 740]}",
        "dimensions": "dimensions:\n  - {name: channel, field: CHANNEL_COLUMN}",
        "benchmark": ("benchmark:\n  min_units: 30          # below this a pocket is shown but not tested\n"
                      "  min_events: 10         # a loss rate on fewer losses than this is not tested\n"
                      "  worse_at: 1.25         # this many times worse counts as worse\n"
                      "  better_at: 0.8         # this many times better counts as better\n"
                      "  confidence: 0.95       # how sure a difference must be\n"
                      "  power: 0.8             # how often a real gap should be caught\n"
                      "  compare_to: peers      # peers (the rest of its band) or topline (the rest of the book)\n"
                      "  many_tests: bh         # none, bh or bonferroni\n"
                      "  materiality: 1% of losses   # or 5% of losses, none, or a dollar amount\n"
                      "# or, to build without comparisons:  benchmark: none"),
        "min_age_months": "min_age_months: 0    # 0 keeps every loan; 24 keeps loans two years on book or more",
    }
    return f"missing line `{k}:`. Add:\n{lines[k]}"


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _unknown(entry: dict, allowed: set[str], where: str, problems: list[str]) -> None:
    for k in entry:
        if k not in allowed:
            problems.append(f"{where}: unknown key `{k}` (known: {', '.join(sorted(allowed))})")


def _parse_missing(node: Any, problems: list[str]) -> dict[str, MissingRule]:
    if not isinstance(node, dict):
        problems.append("`missing:` must map a column name to its rule, e.g.  FICO: {below: -1000}")
        return {}
    out = {}
    for col, rule in node.items():
        where = f"missing.{col}"
        if not isinstance(rule, dict) or not rule:
            problems.append(f"{where}: give at least one of below / above / values")
            continue
        _unknown(rule, MISSING_KEYS, where, problems)
        below, above = rule.get("below"), rule.get("above")
        for k, v in (("below", below), ("above", above)):
            if v is not None and not _num(v):
                problems.append(f"{where}.{k} must be a number, not {v!r}")
        values = rule.get("values", [])
        if not isinstance(values, list):
            problems.append(f"{where}.values must be a list, e.g. [9999, \"UNK\"]")
            values = []
        out[str(col)] = MissingRule(below=float(below) if _num(below) else None,
                                    above=float(above) if _num(above) else None,
                                    values=tuple(values))
    return out


def _entries(node: Any, line: str, problems: list[str]) -> list[dict]:
    if not isinstance(node, list) or not node:
        problems.append(f"`{line}:` needs at least one entry")
        return []
    out = []
    for i, e in enumerate(node):
        if not isinstance(e, dict):
            problems.append(f"{line}[{i}] must be a mapping like {{name: ..., field: ...}}")
            continue
        out.append(e)
    return out


def _name_field(e: dict, where: str, problems: list[str]) -> tuple[str, str]:
    name, fld = e.get("name"), e.get("field")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{where}: needs `name:`")
        name = ""
    if not isinstance(fld, str) or not fld.strip():
        problems.append(f"{where}: needs `field:`, the column to read")
        fld = ""
    return name.strip(), fld.strip()


def _parse_bands(node: Any, problems: list[str]) -> tuple[Band, ...]:
    out = []
    for i, e in enumerate(_entries(node, "bands", problems)):
        where = f"bands[{i}]"
        _unknown(e, {"name", "field", "edges", "count", "cut"}, where, problems)
        name, fld = _name_field(e, where, problems)
        edges, count, cut = e.get("edges"), e.get("count"), e.get("cut")
        if edges is not None and (count is not None or cut is not None):
            problems.append(f"{where}: give `edges:` or `count:` with `cut:`, not both")
            continue
        if edges is None:
            if not isinstance(count, int) or isinstance(count, bool) or count < 2:
                problems.append(f"{where}: needs `edges:` (cut points, e.g. [620, 680, 740]) or `count:` "
                                f"(how many bands, 2 or more) with `cut:` ({' or '.join(CUTS)})")
                continue
            if cut not in CUTS:
                problems.append(f"{where}: `cut:` must be one of {', '.join(CUTS)}; got {cut!r}")
                continue
            out.append(Band(name=name, field=fld, count=count, cut=cut))
            continue
        if not isinstance(edges, list) or not edges or not all(_num(x) for x in edges):
            problems.append(f"{where}: `edges:` must be a list of cut points, e.g. [620, 680, 740]")
            continue
        if any(b <= a for a, b in zip(edges, edges[1:])):
            problems.append(f"{where}.edges must rise strictly: {edges}")
            continue
        out.append(Band(name=name, field=fld, edges=tuple(float(x) for x in edges)))
    return tuple(out)


def _parse_dims(node: Any, problems: list[str]) -> tuple[Dimension, ...]:
    out = []
    for i, e in enumerate(_entries(node, "dimensions", problems)):
        where = f"dimensions[{i}]"
        _unknown(e, {"name", "field"}, where, problems)
        name, fld = _name_field(e, where, problems)
        out.append(Dimension(name=name, field=fld))
    return tuple(out)


def _parse_measures(node: Any, problems: list[str]) -> tuple[Measure, ...]:
    out = []
    for i, e in enumerate(_entries(node, "measures", problems)):
        where = f"measures[{i}]"
        mode = str(e.get("mode", "")).strip().lower()
        if mode not in MODES:
            problems.append(f"{where}: `mode:` must be one of {', '.join(MODES)}; got {e.get('mode')!r}")
            continue
        spec = MODE_KEYS[mode]
        _unknown(e, {"name", "mode", *spec["required"], *spec["allowed"]}, where, problems)
        name = e.get("name")
        if not isinstance(name, str) or not name.strip():
            problems.append(f"{where}: needs `name:`")
            continue
        cols = {}
        for k in spec["required"]:
            v = e.get(k)
            if k == "higher_is":
                if v not in HIGHER_IS:
                    problems.append(f"{where} ({name}): needs `higher_is: worse` (a loss) or `higher_is: better` "
                                    f"(revenue); got {v!r}")
                else:
                    cols[k] = v
            elif not isinstance(v, str) or not v.strip():
                problems.append(f"{where} ({name}): mode {mode} needs `{k}:`, a column name")
            else:
                cols[k] = v.strip()
        optional = e.get("optional", False)
        if not isinstance(optional, bool):
            problems.append(f"{where}.optional must be true or false")
            optional = False
        if len(cols) == len(spec["required"]):
            out.append(Measure(name=name.strip(), mode=mode, optional=optional, **cols))
    return tuple(out)


def _parse_benchmark(node: Any, problems: list[str]) -> Benchmark | None:
    if isinstance(node, str) and node.strip().lower() == "none":
        return None
    if not isinstance(node, dict):
        problems.append(_missing_line("benchmark"))
        return None
    _unknown(node, set(BENCHMARK_KEYS), "benchmark", problems)
    if any(isinstance(v, str) and CONFIRM in v for v in node.values()):
        return None            # each unanswered line is already reported, once
    absent = [k for k in BENCHMARK_KEYS if k not in node]
    if absent:
        problems.append(f"benchmark is missing {', '.join(absent)}; none of these has a default. "
                        + _missing_line("benchmark").split("\n", 1)[1])
        return None
    mu, worse, better = node["min_units"], node["worse_at"], node["better_at"]
    conf, power, me = node["confidence"], node["power"], node["min_events"]
    ok = True
    for k, v, least in (("min_units", mu, 2), ("min_events", me, 1)):
        if not isinstance(v, int) or isinstance(v, bool) or v < least:
            problems.append(f"benchmark.{k} must be a whole number of loans, {least} or more; got {v!r}")
            ok = False
    for k, v in (("worse_at", worse), ("better_at", better)):
        if not _num(v) or v <= 0:
            problems.append(f"benchmark.{k} must be a positive number; got {v!r}")
            ok = False
    for k, v in (("confidence", conf), ("power", power)):
        if not _num(v) or not 0.5 <= v < 1:
            problems.append(f"benchmark.{k} must be a share between 0.5 and 1, such as 0.95; got {v!r}")
            ok = False
    if node["compare_to"] not in COMPARE_TO:
        problems.append(f"benchmark.compare_to must be one of {', '.join(COMPARE_TO)}; got {node['compare_to']!r}")
        ok = False
    if node["many_tests"] not in MANY_TESTS:
        problems.append(f"benchmark.many_tests must be one of {', '.join(MANY_TESTS)}; got {node['many_tests']!r}")
        ok = False
    mat = _parse_materiality(node["materiality"])
    if mat is None:
        problems.append(f"benchmark.materiality must be like \"1% of losses\", none, or a dollar amount; "
                        f"got {node['materiality']!r}")
        ok = False
    if ok and better >= worse:
        problems.append(f"benchmark.better_at ({better}) must be below worse_at ({worse})")
        ok = False
    if ok and worse <= 1:
        problems.append(f"benchmark.worse_at ({worse}) must be above 1: it is how many times worse counts as worse")
        ok = False
    return (Benchmark(min_units=mu, min_events=me, worse_at=float(worse), better_at=float(better),
                      confidence=float(conf), power=float(power), compare_to=node["compare_to"],
                      many_tests=node["many_tests"], materiality=mat) if ok else None)


def _parse_materiality(v: Any):
    if isinstance(v, str):
        t = v.strip().lower()
        if t == "none":
            return ("none", 0.0)
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*% of losses", t)
        if m:
            return ("share", float(m.group(1)) / 100)
        return None
    if _num(v) and v >= 0:
        return ("dollars", float(v))
    return None


def _parse_age(raw: dict, columns: dict, problems: list[str]):
    """Loan age (the Control tab's first call). 0 keeps every loan. Above 0
    needs to know when each loan was made and when the data was taken: from
    `columns:` (origination_date, as_of_date) or from `origination_date:` and
    `as_of:` lines. Nothing is assumed."""
    age = raw.get("min_age_months")
    if "min_age_months" not in raw:
        return 0, None, None
    if not isinstance(age, int) or isinstance(age, bool) or age < 0:
        if not (isinstance(age, str) and CONFIRM in age):
            problems.append(f"`min_age_months:` must be a whole number of months, 0 for every loan; got {age!r}")
        return 0, None, None
    orig = raw.get("origination_date") or next((c for c, (m, _) in columns.items() if m == "origination_date"), None)
    as_of = raw.get("as_of") or next((c for c, (m, _) in columns.items() if m == "as_of_date"), None)
    if age > 0 and not orig:
        problems.append(f"loan age of {age} months needs to know when each loan was made: mark a column "
                        f"`means: origination_date`, or add `origination_date: COLUMN`")
    if age > 0 and not as_of:
        problems.append(f"loan age of {age} months needs the as-of date: mark a column `means: as_of_date`, "
                        f"or add `as_of: 2026-06-30`")
    return age, orig, as_of


def _parse_questions(node: Any, problems: list[str]) -> tuple[Question, ...]:
    if not isinstance(node, list):
        problems.append("`questions:` must be a list (cube init writes it)")
        return ()
    out = []
    for i, e in enumerate(node):
        where = f"questions[{i}]"
        if not isinstance(e, dict):
            problems.append(f"{where} must be a mapping")
            continue
        _unknown(e, {"column", "pattern", "value", "rows", "answer"}, where, problems)
        ans = e.get("answer")
        if ans not in (None, *ANSWERS):
            problems.append(f"{where}.answer must be left blank, or be one of {', '.join(ANSWERS)}; got {ans!r}")
            continue
        if e.get("pattern") not in ("repeated_value", "negatives") or not isinstance(e.get("column"), str):
            problems.append(f"{where}: needs `column:` and a `pattern:` of repeated_value or negatives")
            continue
        val = e.get("value")
        out.append(Question(column=e["column"], pattern=e["pattern"], value=float(val) if _num(val) else None,
                            rows=int(e.get("rows") or 0), answer=ans))
    return tuple(out)
