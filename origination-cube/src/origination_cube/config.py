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

from . import perm
from .perm import SHUFFLES

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
    "median": {"required": ("value",), "allowed": ("optional", "show")},
}
TOP_KEYS = {"name", "schema_version", "key", "booked", "outcome", "gco", "ranr", "columns", "columns_confirmed",
            "missing", "bands", "dimensions", "measures", "benchmark", "questions", "min_age_months",
            "origination_date", "as_of", "split", "window_months", "outcome_date", "derived"}
#: The dates a run can be told about, as meanings in `columns:`: each names at most one column.
DATE_ROLES = ("origination_date", "outcome_date", "as_of_date")
#: `as_of: latest` - the latest origination or outcome date in the extract (fix 3.13). Only when picked.
AS_OF_LATEST = "latest"
#: What an amount column is over (fix 3.10): said on Columns, recorded in what ran, never used to rescale.
PERIODS = ("per_year", "per_month", "one_time")
PERIOD_WORDS = {"per_year": "per year", "per_month": "per month", "one_time": "one-time"}
#: The meanings that are amounts, so can have a period.
AMOUNT_MEANINGS = ("booked", "gco", "ranr", "amount")
DERIVED_KEYS = ("name", "top", "bottom")
SPLIT_HOW = ("own_median", "each_value")
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
# Optional. revenue_line: when revenue counts as more or less than its comparison
# (ruling OC-26), on every tab; absent, the loss lines are used, and the tabs say so.
# shuffles: how many times the shuffle test deals out the pocket labels for a dollar
# rate (docs/statistics.md B2); absent, perm.SHUFFLES (10,000). It changes no reading
# a person chooses, only how finely a p-value can print (1 in B + 1 at the smallest).
BENCHMARK_OPTIONAL = ("revenue_line", "shuffles")
REVENUE_LINES = ("luck", "losses")
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
    show: str = "median"          # median: which figure a median-mode measure shows, median or average

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

    def words(self) -> str:
        """The same arithmetic, said the way the workbook says things (second
        walk, defect 14: the grid headings read as formulas)."""
        if self.mode == "flagwt":
            yes = f"{self.flag} is {_fmt_num(self.flag_is)}" if self.flag_is is not None else f"{self.flag} is 1"
            if self.per == EACH_LOAN:
                return f"Loans where {yes}, as a share of all loans."
            return f"{self.per} on loans where {yes}, as a share of all {self.per}."
        if self.mode == "sumnum":
            if self.per == EACH_LOAN:
                return f"Total {self.value} over the number of loans."
            return f"Total {self.value} over total {self.per}."
        if self.mode == "count":
            return "Loans."
        return f"The {self.show} {self.value} in each pocket. Medians and averages don't add up across pockets."


@dataclass(frozen=True)
class Benchmark:
    """Every call that decides what a pocket's word is. All required, none
    defaulted: the Control tab or the person writes each one."""
    min_units: int                   # below this the outcome's share of loans gets the exact test, not the z test
    min_events: int                  # a loss rate resting on fewer losses than this is not tested
    worse_at: float
    better_at: float
    confidence: float
    power: float
    compare_to: str                  # peers | topline: which comparison decides the flag
    many_tests: str                  # none | bh | bonferroni
    materiality: tuple               # ("share", 0.01) | ("dollars", 250000.0) | ("none", 0.0)
    revenue_line: Any = None         # None | "luck" | "losses" | a share such as 0.1 (RANR on every tab)
    shuffles: int = SHUFFLES         # the shuffle test's B (docs/statistics.md B2); 0 runs no shuffle test


@dataclass(frozen=True)
class Derived:
    """A new column, one column divided by another (fix 3.9): `name` = `top` / `bottom` on each loan,
    blank where the bottom is zero or blank. Made before anything else reads the extract, so it is cut,
    split and looked at like any number column."""
    name: str
    top: str
    bottom: str

    def text(self) -> str:
        return f"{self.top} ÷ {self.bottom}"


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
    split: tuple | None = None                        # (column, own_median | each_value): the third layer
    columns: dict = field(default_factory=dict)       # column -> (meaning, is-value); from `columns:`
    not_cut: dict = field(default_factory=dict)       # column -> meaning, for meanings never cut by
    window_months: int = 0                            # bad = bad in the first N months on book; 0, no window
    outcome_date: str | None = None                   # the column holding the date each loan went bad
    derived: tuple = ()                               # Derived columns, made in this order
    periods: dict = field(default_factory=dict)       # column -> per_year | per_month | one_time
    definitions: dict = field(default_factory=dict)   # column -> what it measures, in the person's words
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
    text = p.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError([f"{p}: not readable as YAML: {exc}"]) from exc
    except ValueError as exc:
        # an unquoted date that isn't a real day (as_of: 2026-13-01): YAML reads it as a date and fails
        # with Python's own words (found by another agent, 26 Sep 2026: it came out as a bare ValueError)
        raise ConfigError([_bad_date_line(p, text, exc)]) from exc
    return parse(raw, source_path=str(p))


def _bad_date_line(p: Path, text: str, exc: Exception) -> str:
    """Which line holds the date that isn't a real day, in words."""
    from datetime import date as _date
    for i, line in enumerate(text.splitlines(), start=1):
        for m in re.finditer(r"(?<![\w.-])(\d{4})-(\d{1,2})-(\d{1,2})(?![\w.-])", line.split("#", 1)[0]):
            try:
                _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return (f"{p}, line {i}: {m.group(0)} isn't a real date ({exc}). Write it as year-month-day, "
                        f"such as 2026-06-30")
    return f"{p}: a date in it isn't a real date ({exc}). Write dates as year-month-day, such as 2026-06-30"


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

    columns, not_cut, periods, definitions = {}, {}, {}, {}
    if "columns" in raw:
        columns, not_cut, periods, definitions = _parse_columns(raw.get("columns"), problems)
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
    window, out_date = _parse_window(raw, columns, age, orig_col, as_of, problems)
    derived = _parse_derived(raw.get("derived"), problems) if raw.get("derived") is not None else ()
    split = None
    if raw.get("split") is not None:
        sp = raw["split"]
        if not isinstance(sp, dict) or not isinstance(sp.get("field"), str) or sp.get("how") not in SPLIT_HOW:
            problems.append("`split:` must be {field: COLUMN, how: own_median} for a number column, or "
                            "{field: COLUMN, how: each_value} for a category")
        else:
            split = (sp["field"], sp["how"])
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
                  min_age_months=age, origination_date=orig_col, as_of=as_of, split=split,
                  columns=columns, not_cut=not_cut, window_months=window, outcome_date=out_date, derived=derived,
                  periods=periods, definitions=definitions, source_path=source_path, raw=raw)


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


def _parse_columns(node: Any, problems: list[str]) -> tuple[dict, dict, dict, dict]:
    """`columns:` maps each column to what it means: `COL: fico` or
    `COL: {means: outcome, is: AUTO}`. The meanings are the catalog in
    settings.yaml; an unknown one is refused with the list. An amount can say
    what period it is over (`period: per_year`, fix 3.10) and what it measures
    in the person's words (`definition: household income`, fix 3.11); both are
    recorded, and neither changes a number."""
    from .meanings import catalog
    cat = catalog()
    if not isinstance(node, dict) or not node:
        problems.append("`columns:` must list each column and what it means, e.g.  FICO: {means: fico}")
        return {}, {}, {}, {}
    out, not_cut, periods, definitions = {}, {}, {}, {}
    for col, v in node.items():
        means, is_value = (v, None) if isinstance(v, str) else ((v or {}).get("means"), (v or {}).get("is")) \
            if isinstance(v, dict) else (None, None)
        if isinstance(v, dict):
            _unknown(v, {"means", "is", "period", "definition"}, f"columns.{col}", problems)
        if means not in cat:
            problems.append(f"columns.{col}: `means: {means}` is not a meaning this tool knows. "
                            f"Use one of: {', '.join(cat)}")
            continue
        out[str(col)] = (means, is_value)
        if cat[means].cut == "none":
            not_cut[str(col)] = means
        if isinstance(v, dict) and v.get("period") is not None:
            per = v["period"]
            if per not in PERIODS:
                problems.append(f"columns.{col}.period must be one of {', '.join(PERIODS)}; got {per!r}")
            elif means not in AMOUNT_MEANINGS:
                problems.append(f"columns.{col}: a period is for an amount; `{col}` means {means}, so it has none")
            else:
                periods[str(col)] = per
        if isinstance(v, dict) and v.get("definition") is not None:
            d = v["definition"]
            if not isinstance(d, str) or not d.strip():
                problems.append(f"columns.{col}.definition must be words saying what the column measures")
            else:
                definitions[str(col)] = " ".join(d.split())
    for role in DATE_ROLES:
        hits = [c for c, (m, _) in out.items() if m == role]
        if len(hits) > 1:
            # one column each: which of two origination dates the window counts from is not a guess to make
            problems.append(f"`columns:` needs at most one column that means {role}; found {len(hits)}: "
                            f"{', '.join(hits)}")
    return out, not_cut, periods, definitions


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
        "benchmark": ("benchmark:\n  min_units: 30          # below this the exact test runs instead of the z test\n"
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
        show = e.get("show", "median")
        if show not in ("median", "average"):
            problems.append(f"{where}.show must be median or average; got {show!r}")
        optional = e.get("optional", False)
        if not isinstance(optional, bool):
            problems.append(f"{where}.optional must be true or false")
            optional = False
        if len(cols) == len(spec["required"]):
            out.append(Measure(name=name.strip(), mode=mode, optional=optional,
                               show=show if mode == "median" else "median", **cols))
    return tuple(out)


def _parse_benchmark(node: Any, problems: list[str]) -> Benchmark | None:
    if isinstance(node, str) and node.strip().lower() == "none":
        return None
    if not isinstance(node, dict):
        problems.append(_missing_line("benchmark"))
        return None
    _unknown(node, set(BENCHMARK_KEYS) | set(BENCHMARK_OPTIONAL), "benchmark", problems)
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
    rl = node.get("revenue_line")
    if rl is not None and rl not in REVENUE_LINES and not (_num(rl) and 0 < rl < 1):
        problems.append(f"benchmark.revenue_line must be luck, losses, or a share such as 0.1; got {rl!r}")
        ok = False
    sh = node.get("shuffles", perm.SHUFFLES)
    if not isinstance(sh, int) or isinstance(sh, bool) or not 100 <= sh <= 1_000_000:
        problems.append(f"benchmark.shuffles must be a whole number from 100 to 1,000,000; got {sh!r}")
        ok = False
    if ok and better >= worse:
        problems.append(f"benchmark.better_at ({better}) must be below worse_at ({worse})")
        ok = False
    if ok and worse <= 1:
        problems.append(f"benchmark.worse_at ({worse}) must be above 1: it is how many times worse counts as worse")
        ok = False
    return (Benchmark(min_units=mu, min_events=me, worse_at=float(worse), better_at=float(better),
                      confidence=float(conf), power=float(power), compare_to=node["compare_to"],
                      many_tests=node["many_tests"], materiality=mat,
                      revenue_line=float(rl) if _num(rl) else rl, shuffles=sh) if ok else None)


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
    orig = raw.get("origination_date") or next((c for c, (m, _) in columns.items() if m == "origination_date"), None)
    as_of = _parse_as_of(raw["as_of"], problems) if raw.get("as_of") is not None else \
        next((c for c, (m, _) in columns.items() if m == "as_of_date"), None)
    age = raw.get("min_age_months")
    if "min_age_months" not in raw:
        return 0, orig, as_of
    if not isinstance(age, int) or isinstance(age, bool) or age < 0:
        if not (isinstance(age, str) and CONFIRM in age):
            problems.append(f"`min_age_months:` must be a whole number of months, 0 for every loan; got {age!r}")
        return 0, orig, as_of
    if age > 0 and not orig:
        problems.append(f"loan age of {age} months needs to know when each loan was made: mark a column "
                        f"`means: origination_date`, or add `origination_date: COLUMN`")
    if age > 0 and not as_of:
        problems.append(f"loan age of {age} months needs the as-of date: mark a column `means: as_of_date`, "
                        f"or add `as_of: 2026-06-30`, or `as_of: {AS_OF_LATEST}` for the latest date in the extract")
    return age, orig, as_of


def _parse_as_of(v: Any, problems: list[str]):
    """The as-of date: a date, `latest` (the latest origination or outcome date
    in the extract, only when someone picks it), or the name of a column holding
    one date. A string that looks like a date but isn't a real day is refused
    here, never read as a column name."""
    from datetime import date as _date, datetime as _datetime
    if isinstance(v, _datetime):
        return v.date()
    if isinstance(v, _date):
        return v
    if isinstance(v, str) and v.strip():
        t = v.strip()
        if t == AS_OF_LATEST:
            return t
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", t):
            try:
                y, m, d = (int(x) for x in t.split("-"))
                return _date(y, m, d)
            except ValueError:
                problems.append(f"`as_of: {t}` isn't a real date. Write it as year-month-day, such as 2026-06-30")
                return None
        return t                                            # a column's name; the run checks it is there
    problems.append(f"`as_of:` must be a date such as 2026-06-30, `{AS_OF_LATEST}`, or the column holding the "
                    f"date the data was taken; got {v!r}")
    return None


def _parse_window(raw: dict, columns: dict, age: int, orig, as_of, problems: list[str]):
    """The outcome window (fix 3.14): bad means bad in a loan's first N months
    on book, and a loan under N months on book is left out. It needs when each
    loan was made, when each bad loan went bad, and when the data was taken; a
    window without any of them is refused, naming it. Where an outcome date is
    marked, the line is required: bad as the extract has it (0) and bad within
    a window are different questions, and which one is asked is our call."""
    out_date = raw.get("outcome_date") or next((c for c, (m, _) in columns.items() if m == "outcome_date"), None)
    if "window_months" not in raw:
        if out_date:
            problems.append(f"an outcome date (`{out_date}`) is marked, so say what bad means: add "
                            f"`window_months: 0` for bad as the extract has it, or `window_months: 18` for bad "
                            f"in the first 18 months on book")
        return 0, out_date
    n = raw["window_months"]
    if isinstance(n, str) and CONFIRM in n:
        return 0, out_date
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 360:
        problems.append(f"`window_months:` must be a whole number of months from 0 (no window) to 360; got {n!r}")
        return 0, out_date
    if n > 0 and not out_date:
        problems.append(f"an outcome window of {n} months needs the date each loan went bad: mark that column "
                        f"`means: outcome_date`, or add `outcome_date: COLUMN`")
    if n > 0 and not orig:
        problems.append(f"an outcome window of {n} months needs to know when each loan was made: mark a column "
                        f"`means: origination_date`, or add `origination_date: COLUMN`")
    if n > 0 and not as_of:
        problems.append(f"an outcome window of {n} months needs the as-of date: mark a column `means: as_of_date`, "
                        f"or add `as_of: 2026-06-30`, or `as_of: {AS_OF_LATEST}` for the latest date in the extract")
    if n > 0 and age > 0:
        problems.append(f"`min_age_months: {age}` and `window_months: {n}` both leave out young loans. Keep one: the "
                        f"window already leaves out loans under {n} months on book, so set min_age_months: 0")
    return n, out_date


def _parse_derived(node: Any, problems: list[str]) -> tuple[Derived, ...]:
    """`derived:` - new columns, each one column divided by another (fix 3.9):
    `- {name: INCOME_TO_SALES, top: INCOME, bottom: SALES}`."""
    if not isinstance(node, list):
        problems.append("`derived:` must be a list, e.g.  - {name: INCOME_TO_SALES, top: INCOME, bottom: SALES}")
        return ()
    out: list[Derived] = []
    for i, e in enumerate(node):
        where = f"derived[{i}]"
        if not isinstance(e, dict):
            problems.append(f"{where} must be a mapping like {{name: INCOME_TO_SALES, top: INCOME, bottom: SALES}}")
            continue
        _unknown(e, set(DERIVED_KEYS), where, problems)
        got = {k: e.get(k).strip() if isinstance(e.get(k), str) else "" for k in DERIVED_KEYS}
        lacking = [k for k in DERIVED_KEYS if not got[k]]
        if lacking:
            problems.append(f"{where}: needs {', '.join('`' + k + ':`' for k in lacking)}: a new column is a name, "
                            f"a top and a bottom, each a column's name")
            continue
        if got["top"] == got["bottom"]:
            problems.append(f"{where} ({got['name']}): `{got['top']}` over itself is 1 on every loan. Pick two "
                            f"different columns")
            continue
        if got["name"] in (got["top"], got["bottom"]) or got["name"] in [d.name for d in out]:
            problems.append(f"{where}: the name `{got['name']}` is taken. Give the new column a name of its own")
            continue
        out.append(Derived(got["name"], got["top"], got["bottom"]))
    return tuple(out)


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
