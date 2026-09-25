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
    "flagwt": {"required": ("flag", "per"), "allowed": ("optional",)},
    "sumnum": {"required": ("value", "per"), "allowed": ("optional",)},
    "count": {"required": (), "allowed": ()},
    "median": {"required": ("value",), "allowed": ("optional",)},
}
TOP_KEYS = {"name", "schema_version", "key", "missing", "bands", "dimensions", "measures", "benchmark"}
REQUIRED_TOP = ("name", "schema_version", "bands", "dimensions", "measures", "benchmark")
MISSING_KEYS = {"below", "above", "values"}
BENCHMARK_KEYS = ("min_units", "worse_at", "better_at")


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
    name: str
    field: str
    edges: tuple[float, ...]


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
    per: str | None = None        # flagwt, sumnum
    optional: bool = False        # absent column -> skipped with a warning (D55)

    @property
    def is_rate(self) -> bool:
        return self.mode in RATE_MODES

    @property
    def reconciles(self) -> bool:
        """Median is positional: cell medians do not add up to a portfolio
        median, so it is labelled rather than put through the tie-out."""
        return self.mode != "median"

    def columns(self) -> tuple[str, ...]:
        return tuple(c for c in (self.value, self.flag, self.per) if c)

    def numerator(self) -> str:
        """What the excess is counted in, in the file's own column names."""
        if self.mode == "flagwt":
            return f"{self.per} on loans where {self.flag} = 1"
        return self.value or ""

    def label(self) -> str:
        """The grid states its own arithmetic."""
        if self.mode == "flagwt":
            return f"SUM({self.per} where {self.flag} = 1) / SUM({self.per})"
        if self.mode == "sumnum":
            return f"SUM({self.value}) / SUM({self.per})"
        if self.mode == "count":
            return "Loans (rows)"
        return f"MEDIAN({self.value}) per cell - positional, does not add up"


@dataclass(frozen=True)
class Benchmark:
    min_units: int
    worse_at: float
    better_at: float


@dataclass(frozen=True)
class Config:
    name: str
    key: str | None
    missing: dict[str, MissingRule]
    bands: tuple[Band, ...]
    dimensions: tuple[Dimension, ...]
    measures: tuple[Measure, ...]
    benchmark: Benchmark | None      # None only when the file says `benchmark: none`
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

    key = raw.get("key")
    if key is not None and (not isinstance(key, str) or not key.strip()):
        problems.append("`key:` must name the loan number column, or be left out")
    key = key.strip() if isinstance(key, str) and key.strip() else None

    missing = _parse_missing(raw.get("missing") or {}, problems)
    bands = _parse_bands(raw.get("bands"), problems) if "bands" in raw else ()
    dims = _parse_dims(raw.get("dimensions"), problems) if "dimensions" in raw else ()
    measures = _parse_measures(raw.get("measures"), problems) if "measures" in raw else ()
    bench = _parse_benchmark(raw.get("benchmark"), problems) if "benchmark" in raw else None

    names = [b.name for b in bands] + [d.name for d in dims] + [m.name for m in measures]
    dupes = sorted({n for n in names if names.count(n) > 1})
    for n in dupes:
        problems.append(f"the name `{n}` is used more than once; every band, dimension and measure needs its own")

    if problems:
        raise ConfigError(problems)
    return Config(name=str(raw["name"]), key=key, missing=missing, bands=bands, dimensions=dims,
                  measures=measures, benchmark=bench, source_path=source_path, raw=raw)


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


def _missing_line(k: str) -> str:
    lines = {
        "name": "name: my_cube",
        "schema_version": f"schema_version: {SCHEMA_VERSION}",
        "bands": "bands:\n  - {name: score_band, field: SCORE_COLUMN, edges: [620, 680, 740]}",
        "dimensions": "dimensions:\n  - {name: channel, field: CHANNEL_COLUMN}",
        "measures": "measures:\n  - {name: gco_rate, mode: sumnum, value: GCO_COLUMN, per: BALANCE_COLUMN}",
        "benchmark": ("benchmark:\n  min_units: 30      # cells with fewer loans are not read\n"
                      "  worse_at: 1.25     # index at or above this reads WORSE\n"
                      "  better_at: 0.8     # index at or below this reads BETTER\n"
                      "# or, to build without comparisons:  benchmark: none"),
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
        _unknown(e, {"name", "field", "edges"}, where, problems)
        name, fld = _name_field(e, where, problems)
        edges = e.get("edges")
        if not isinstance(edges, list) or not edges or not all(_num(x) for x in edges):
            problems.append(f"{where}: needs `edges:`, a list of cut points, e.g. [620, 680, 740]")
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
            if not isinstance(v, str) or not v.strip():
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
    absent = [k for k in BENCHMARK_KEYS if k not in node]
    if absent:
        problems.append(f"benchmark is missing {', '.join(absent)}; none of the three has a default. "
                        + _missing_line("benchmark").split("\n", 1)[1])
        return None
    mu, worse, better = node["min_units"], node["worse_at"], node["better_at"]
    ok = True
    if not isinstance(mu, int) or isinstance(mu, bool) or mu < 1:
        problems.append(f"benchmark.min_units must be a whole number of loans, 1 or more; got {mu!r}")
        ok = False
    for k, v in (("worse_at", worse), ("better_at", better)):
        if not _num(v) or v <= 0:
            problems.append(f"benchmark.{k} must be a positive number; got {v!r}")
            ok = False
    if ok and better >= worse:
        problems.append(f"benchmark.better_at ({better}) must be below worse_at ({worse})")
        ok = False
    return Benchmark(min_units=mu, worse_at=float(worse), better_at=float(better)) if ok else None
