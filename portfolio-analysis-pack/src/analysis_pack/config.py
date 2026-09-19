"""The question file: load it, check it, and refuse with the line to add.

Nothing in here knows what a column means. The file names the bank's columns
in each slot, so the config *is* the mapping (PRD §6.1). Three lines the six
original slots left to inference are required and never defaulted: the flag
line (`rule.fires_when`), each column's `known:` (at origination or later),
and `existing_control`.

A refusal prints the missing line in the file's own syntax, so the fix is a
paste rather than a search.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
RULE_TYPES = ("contradiction", "threshold", "missingness", "hunch")
BUILT_RULE_TYPES = ("contradiction",)
RULE_KINDS = ("ratio", "difference")
OPS = (">", ">=", "<", "<=", "==", "!=")
KNOWN = ("at_origination", "later")
INTERVAL_METHODS = {"wilson": "Wilson", "clopper_pearson": "Clopper-Pearson"}


class ConfigError(Exception):
    """One or more problems with the question file. `problems` is the list;
    `str()` renders them one per line, each ending with the line to add
    where there is one."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class Field:
    name: str
    known: str                         # "at_origination" | "later"
    plausible: tuple[float, float] | None = None
    derive: tuple[dict[str, Any], ...] = ()   # parsed now, applied from slice 5


@dataclass(frozen=True)
class Rule:
    kind: str
    field_a: str
    field_b: str
    fires_op: str
    fires_value: float
    buckets: tuple[float, ...]


@dataclass(frozen=True)
class Outcome:
    label: str
    form: str                          # "event_date" | "flag" | "snapshot"
    date_field: str | None = None
    field: str | None = None
    op: str | None = None
    value: float | None = None
    measure: dict[str, Any] | None = None
    basis: str | None = None
    edges: tuple[float, ...] | None = None     # a measure outcome cut at several shares, one outcome per edge

    def columns(self) -> tuple[str, ...]:
        if self.form == "event_date":
            return (self.date_field,)
        if self.form == "flag":
            return (self.field,)
        m = self.measure or {}
        if "field" in m:
            return (m["field"],)
        return (m.get("field_a"), m.get("field_b"))


@dataclass(frozen=True)
class Confounder:
    name: str
    field: str
    schemes: dict[str, tuple[float, ...]]   # empty => categorical column


@dataclass(frozen=True)
class Control:
    name: str
    field: str | None = None
    derived: str | None = None
    as_: str = "categorical"           # log | linear | categorical | bands
    edges: tuple[float, ...] = ()      # for as: bands


@dataclass(frozen=True)
class Config:
    name: str
    rule_type: str
    loan_id: str
    origination_date: str
    date_format: str | None
    filter: dict[str, tuple[str, ...]]
    fields: dict[str, Field]
    rule: Rule
    outcome: Outcome
    window_months: int
    confounders: tuple[Confounder, ...]
    controls: tuple[Control, ...]
    decompose_by: tuple[str, ...]
    existing_control: str              # "none" or the text
    drives: dict[str, str]
    model: dict[str, int]
    confidence: float
    method: str                        # "Wilson" | "Clopper-Pearson"
    survives_threshold: float
    source_path: str
    source_sha256: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def referenced_columns(self) -> list[str]:
        cols = [self.loan_id, self.origination_date, self.rule.field_a, self.rule.field_b]
        cols += [c for c in self.outcome.columns() if c]
        cols += [c.field for c in self.confounders]
        cols += [c.field for c in self.controls if c.field]
        cols += list(self.filter.keys())
        seen: list[str] = []
        for c in cols:
            if c not in seen:
                seen.append(c)
        return seen


# --------------------------------------------------------------------------

def _line(*parts: str) -> str:
    return "\n".join(parts)


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def load_config(path: str | Path) -> Config:
    """Read and validate a question file. Raises ConfigError listing every
    problem in the first failing group (schema, then required lines, then
    column declarations, then value checks)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:              # pragma: no cover - yaml's own message is the finding
        raise ConfigError([f"{p}: not valid YAML: {exc}"])
    if not isinstance(raw, dict):
        raise ConfigError([f"{p}: the question file must be a mapping of slot: value"])
    problems: list[str] = []

    # -- group 1: shape and required slots ---------------------------------
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(_line("`name` is missing. Add:", "name: my_question"))
    version = raw.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        problems.append(f"`schema_version` is {version!r}; this build reads {SCHEMA_VERSION}")
    rule_type = raw.get("rule_type")
    if rule_type not in RULE_TYPES:
        problems.append(_line("`rule_type` is missing or not one of contradiction | threshold | missingness | hunch. Add:",
                              "rule_type: contradiction"))
    pop = raw.get("population")
    if not isinstance(pop, dict):
        problems.append(_line("`population` is missing. Add:",
                              "population:", "  loan_id: <the loan number column>",
                              "  origination_date: <the origination date column>"))
        pop = {}
    for key, hint in (("loan_id", "<the loan number column>"),
                      ("origination_date", "<the origination date column>")):
        if not isinstance(pop.get(key), str) or not pop.get(key).strip():
            problems.append(_line(f"`population.{key}` is missing. Add under population:",
                                  f"  {key}: {hint}"))
    fields_raw = raw.get("fields")
    if not isinstance(fields_raw, dict) or not fields_raw:
        problems.append(_line("`fields` is missing. Every column the pack touches is declared there, with when it was known. Add:",
                              "fields:", "  <COLUMN>: {known: at_origination}",
                              "  <OUTCOME COLUMN>: {known: later}"))
        fields_raw = {}
    rule_raw = raw.get("rule")
    if not isinstance(rule_raw, dict):
        problems.append(_line("`rule` is missing. Add:", "rule:", "  kind: ratio",
                              "  field_a: <column>", "  field_b: <column>",
                              "  fires_when: {op: '>', value: 1.0}",
                              "  buckets: [0.5, 1.0, 2.0, 5.0]"))
        rule_raw = {}
    else:
        if rule_raw.get("kind") not in RULE_KINDS:
            problems.append(_line("`rule.kind` must be ratio or difference. Add under rule:", "  kind: ratio"))
        for key in ("field_a", "field_b"):
            if not isinstance(rule_raw.get(key), str):
                problems.append(_line(f"`rule.{key}` is missing. Add under rule:", f"  {key}: <column>"))
        fw = rule_raw.get("fires_when")
        if not isinstance(fw, dict) or fw.get("op") not in OPS or _num(fw.get("value")) is None:
            problems.append(_line("`rule.fires_when` is missing: the buckets say how far apart the fields are, not where the flag line is. Add under rule:",
                                  "  fires_when: {op: '>', value: 1.0}"))
        b = rule_raw.get("buckets")
        if not isinstance(b, list) or not b or any(_num(x) is None for x in b):
            problems.append(_line("`rule.buckets` must be a list of numeric edges. Add under rule:",
                                  "  buckets: [0.5, 1.0, 2.0, 5.0]"))
    out_raw = raw.get("outcome")
    if not isinstance(out_raw, dict):
        problems.append(_line("`outcome` is missing. Add one of:",
                              "outcome: {label: <word for the event>, date_field: <event date column>}",
                              "outcome: {label: <word>, field: <flag column>, op: '==', value: 1, basis: windowed_by_bank}",
                              "outcome: {label: <word>, measure: {kind: ratio, field_a: <col>, field_b: <col>}, op: '>=', value: 0.9, basis: snapshot_at_asof}"))
        out_raw = {}
    else:
        if not isinstance(out_raw.get("label"), str):
            problems.append(_line("`outcome.label` is missing: the word every tab uses for the event. Add under outcome:",
                                  "  label: <word for the event>"))
        forms = [k for k in ("date_field", "field", "measure") if k in out_raw]
        if len(forms) != 1:
            problems.append(_line("`outcome` must take exactly one form: date_field, or field, or measure. Found: "
                                  + (", ".join(forms) or "none")))
        if "field" in out_raw or "measure" in out_raw:
            has_cut = out_raw.get("op") in OPS and _num(out_raw.get("value")) is not None
            edges_raw = out_raw.get("edges")
            has_edges = ("measure" in out_raw and isinstance(edges_raw, list) and edges_raw
                         and all(_num(x) is not None for x in edges_raw))
            if has_cut == bool(has_edges):
                problems.append(_line("a flag or measure outcome takes either one cut (`op` and `value`) or, for a measure, "
                                      "a list of `edges` (one outcome per edge, at or above). Add under outcome one of:",
                                      "  op: '>='", "  value: 0.9", "  # or", "  edges: [0.5, 0.75, 0.9]"))
            if has_edges and any(edges_raw[i] >= edges_raw[i + 1] for i in range(len(edges_raw) - 1)):
                problems.append("`outcome.edges` must strictly increase")
            basis = out_raw.get("basis")
            want = "windowed_by_bank" if "field" in out_raw else "snapshot_at_asof"
            if basis != want:
                problems.append(_line(f"`outcome.basis` must say how the outcome was measured. For this form add under outcome:",
                                      f"  basis: {want}"))
    wm = raw.get("window_months")
    if not isinstance(wm, int) or isinstance(wm, bool) or wm <= 0:
        problems.append(_line("`window_months` is missing or not a positive whole number. Add:", "window_months: 24"))
    ec = raw.get("existing_control")
    if ec is None or (isinstance(ec, str) and not ec.strip()):
        problems.append(_line("`existing_control` is missing. The tool can count the contradiction; it cannot know whether anything at the bank reacts to it. Add:",
                              "existing_control: none   # or the control that reacts today"))
    if problems:
        raise ConfigError(problems)

    # -- group 2: fields declared, with timing --------------------------------
    fields: dict[str, Field] = {}
    for col, spec in fields_raw.items():
        if not isinstance(col, str):
            problems.append(f"a `fields` key is not text: {col!r}")
            continue
        if not isinstance(spec, dict):
            problems.append(_line(f"`fields.{col}` must be a mapping. Replace with:", f"  {col}: {{known: at_origination}}"))
            continue
        known = spec.get("known")
        if known not in KNOWN:
            problems.append(_line(f"`fields.{col}.known` is missing: was this column known when the loan was made? Add under fields:",
                                  f"  {col}: {{known: at_origination}}   # or known: later"))
            continue
        plausible = None
        pl = spec.get("plausible")
        if pl is not None:
            if (not isinstance(pl, list) or len(pl) != 2 or _num(pl[0]) is None
                    or _num(pl[1]) is None or _num(pl[0]) >= _num(pl[1])):
                problems.append(f"`fields.{col}.plausible` must be [low, high] with low < high")
            else:
                plausible = (float(pl[0]), float(pl[1]))
        derive = spec.get("derive", ())
        if isinstance(derive, dict):
            derive = (derive,)
        steps = []
        for d in derive:
            step, why = _parse_derive(d, p.parent)
            if why:
                problems.append(f"`fields.{col}.derive`: {why}")
            else:
                steps.append(step)
        fields[col] = Field(name=col, known=known, plausible=plausible, derive=tuple(steps))

    # build the typed pieces so referenced columns can be listed
    filt: dict[str, tuple[str, ...]] = {}
    for k, v in (pop.get("filter") or {}).items():
        vals = v if isinstance(v, list) else [v]
        filt[str(k)] = tuple(str(x) for x in vals)
    rule = Rule(kind=rule_raw["kind"], field_a=rule_raw["field_a"], field_b=rule_raw["field_b"],
                fires_op=rule_raw["fires_when"]["op"], fires_value=float(rule_raw["fires_when"]["value"]),
                buckets=tuple(float(x) for x in rule_raw["buckets"]))
    if "date_field" in out_raw:
        outcome = Outcome(label=out_raw["label"], form="event_date", date_field=out_raw["date_field"])
    elif "field" in out_raw:
        outcome = Outcome(label=out_raw["label"], form="flag", field=out_raw["field"], op=out_raw["op"],
                          value=float(out_raw["value"]), basis=out_raw["basis"])
    else:
        edges_raw = out_raw.get("edges")
        outcome = Outcome(label=out_raw["label"], form="snapshot", measure=dict(out_raw["measure"]),
                          op=out_raw.get("op"), value=(float(out_raw["value"]) if "value" in out_raw else None),
                          basis=out_raw["basis"],
                          edges=(tuple(float(x) for x in edges_raw) if edges_raw else None))
    confounders: list[Confounder] = []
    for c in raw.get("confounders") or []:
        if not isinstance(c, dict) or "name" not in c or "field" not in c:
            problems.append("each confounder needs `name` and `field`")
            continue
        schemes: dict[str, tuple[float, ...]] = {}
        if "edges" in c:
            schemes["edges"] = tuple(float(x) for x in c["edges"])
        for sname, edges in (c.get("schemes") or {}).items():
            schemes[str(sname)] = tuple(float(x) for x in edges)
        for sname, edges in schemes.items():
            if any(edges[i] >= edges[i + 1] for i in range(len(edges) - 1)):
                problems.append(f"confounder `{c['name']}` scheme `{sname}` edges must strictly increase")
        confounders.append(Confounder(name=str(c["name"]), field=str(c["field"]), schemes=schemes))
    controls: list[Control] = []
    for c in raw.get("controls") or []:
        if not isinstance(c, dict) or "name" not in c or ("field" not in c and "derived" not in c):
            problems.append("each control needs `name` and either `field` or `derived`")
            continue
        as_ = str(c.get("as", "categorical"))
        if as_ not in ("log", "linear", "categorical", "bands"):
            problems.append(f"control `{c['name']}`: `as` must be log, linear, categorical or bands")
        edges_c = tuple(float(x) for x in (c.get("edges") or []))
        if as_ == "bands" and not edges_c:
            problems.append(f"control `{c['name']}`: `as: bands` needs `edges: [...]`")
        controls.append(Control(name=str(c["name"]), field=c.get("field"), derived=c.get("derived"),
                                as_=as_, edges=edges_c))
    decompose_by = tuple(str(x) for x in (raw.get("decompose_by") or []))

    edges = rule.buckets
    if any(edges[i] >= edges[i + 1] for i in range(len(edges) - 1)):
        problems.append("`rule.buckets` edges must strictly increase")
    dims = {c.name for c in confounders} | {c.name for c in controls if c.derived == "origination_year" or c.as_ == "categorical"}
    dims.add("origination_year")
    for dim in decompose_by:                      # not `name`: that is the question file's own name
        if dim not in dims:
            problems.append(f"`decompose_by` names `{dim}`, which is not a confounder, a categorical control, or origination_year")
    numeric_use = {rule.field_a, rule.field_b} | {c.field for c in confounders if c.schemes}
    numeric_use |= {c.field for c in controls if c.field and c.as_ in ("log", "linear", "bands")}
    for col, f in fields.items():
        if f.derive and col in numeric_use:
            problems.append(f"`fields.{col}.derive` groups a code read as text, but `{col}` is used as a number")

    cfg_no_fields = Config(
        name=name, rule_type=rule_type, loan_id=pop["loan_id"], origination_date=pop["origination_date"],
        date_format=pop.get("date_format"), filter=filt, fields=fields, rule=rule, outcome=outcome,
        window_months=int(wm), confounders=tuple(confounders), controls=tuple(controls),
        decompose_by=decompose_by, existing_control=str(ec).strip(), drives=dict(raw.get("drives") or {}),
        model={"tree_depth": int((raw.get("model") or {}).get("tree_depth", 3)),
               "min_leaf_events": int((raw.get("model") or {}).get("min_leaf_events", 10)),
               "min_leaf_loans": int((raw.get("model") or {}).get("min_leaf_loans", 100))},
        confidence=float((raw.get("intervals") or {}).get("confidence", 0.95)),
        method=INTERVAL_METHODS.get(str((raw.get("intervals") or {}).get("method", "wilson")), ""),
        survives_threshold=float(raw.get("survives_threshold", 0.5)),
        source_path=str(p), source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), raw=raw)

    for col in cfg_no_fields.referenced_columns():
        if col not in fields:
            problems.append(_line(f"column `{col}` is used but not declared under `fields`. Add under fields:",
                                  f"  {col}: {{known: at_origination}}   # or known: later"))
    non_outcome_slots = [pop["loan_id"], pop["origination_date"], rule.field_a, rule.field_b]
    non_outcome_slots += [c.field for c in confounders] + [c.field for c in controls if c.field] + list(filt.keys())
    for col, f in fields.items():
        if f.known == "later" and col in non_outcome_slots:
            problems.append(f"column `{col}` is declared `known: later` (it describes what happened after origination) "
                            f"and is used somewhere other than the outcome. That would leak the outcome into the analysis; "
                            f"remove it from that slot or mark it at_origination if that is true.")
    if problems:
        raise ConfigError(problems)

    # -- group 3: value checks -------------------------------------------------
    if not cfg_no_fields.method:
        problems.append("`intervals.method` must be wilson or clopper_pearson")
    if not (0.5 <= cfg_no_fields.confidence < 1.0):
        problems.append("`intervals.confidence` must be between 0.5 and 1 (e.g. 0.95)")
    if not (0.0 < cfg_no_fields.survives_threshold < 1.0):
        problems.append("`survives_threshold` must be between 0 and 1")
    if cfg_no_fields.model["tree_depth"] not in (2, 3):
        problems.append("`model.tree_depth` must be 2 or 3")
    if problems:
        raise ConfigError(problems)
    return cfg_no_fields


def _parse_derive(d: Any, base: Path) -> tuple[dict[str, Any] | None, str | None]:
    """A generic grouping step (PRD §6.15). The tool ships no list: a `map`
    is the config's own, inline or in a two-column file beside it."""
    if not isinstance(d, dict) or d.get("kind") not in ("prefix", "map"):
        return None, "each step is {kind: prefix, length: N} or {kind: map, groups: {...} | groups_file: path, other: label}"
    if d["kind"] == "prefix":
        n = d.get("length")
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            return None, "prefix needs a positive whole `length`"
        return {"kind": "prefix", "length": n}, None
    groups_raw = d.get("groups")
    path = d.get("groups_file")
    if (groups_raw is None) == (path is None):
        return None, "map needs exactly one of `groups` (inline) or `groups_file` (a two-column file: value, group)"
    groups: dict[str, list[str]] = {}
    source = "inline"
    if path is not None:
        fp = (base / str(path)) if not Path(str(path)).is_absolute() else Path(str(path))
        if not fp.exists():
            return None, f"groups_file `{path}` was not found beside the question file"
        import csv as _csv
        with fp.open(encoding="utf-8-sig", newline="") as fh:
            for row in _csv.reader(fh):
                if len(row) < 2 or not row[0].strip():
                    continue
                if row[0].strip().lower() == "value" and row[1].strip().lower() == "group":
                    continue
                groups.setdefault(row[1].strip(), []).append(row[0].strip())
        source = str(fp)
    else:
        if not isinstance(groups_raw, dict) or not groups_raw:
            return None, "`groups` must be a mapping of label: [values]"
        for label, vals in groups_raw.items():
            vals = vals if isinstance(vals, list) else [vals]
            groups[str(label)] = [str(v) for v in vals]
    lookup: dict[str, str] = {}
    for label, vals in groups.items():
        for v in vals:
            if v in lookup and lookup[v] != label:
                return None, f"value `{v}` is in two groups ({lookup[v]}, {label})"
            lookup[v] = label
    other = d.get("other")
    return {"kind": "map", "lookup": lookup, "labels": list(groups), "other": (str(other) if other is not None else None),
            "source": source}, None


def check_columns_present(cfg: Config, columns: list[str]) -> list[str]:
    """Problems for every declared column the data does not carry."""
    have = set(columns)
    out = []
    for col in cfg.fields:
        if col not in have:
            out.append(f"column `{col}` is declared in the question file but the data has no column of that name")
    return out


def buildable(cfg: Config) -> str | None:
    """None when this build can produce the pack; otherwise the refusal."""
    if cfg.rule_type in BUILT_RULE_TYPES:
        return None
    return (f"rule_type `{cfg.rule_type}` is not built in this version: v1 builds `contradiction` only. "
            f"The slot is reserved so the file is valid; the door is logged in BACKLOG.md §6c.")
