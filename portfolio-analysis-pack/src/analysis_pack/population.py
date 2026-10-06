"""From typed rows to the population the ladder runs on.

Seasoning, the outcome(s), the rule value, the flag and the bucket, per loan.
The as-of date is injected by the caller; nothing here reads a clock.

Months on book (PRD §6.4): whole calendar months from origination to as-of,
one fewer when the as-of day of month is earlier than the origination day.
A loan is seasoned when it has at least `window_months` on book. Only
seasoned loans enter a rate; the unseasoned are counted, by quarter.

Dates (PRD §6.2): a typed cell needs nothing; text is parsed with the
declared pattern, or with the one common pattern that fits every value in
the column. Two patterns fitting every value is ambiguous and refuses the
build with both readings of a sample; none fitting every value leaves the
best pattern's failures as unparseable dirt.

Outcomes: one question file yields one or more binary outcomes. An event
date, a bank-windowed flag, or a measure at as-of with a single cut give
one; a measure with `edges` gives one per edge (loan at or above that
share), so nobody has to pick a single line.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .config import Config
from .ingest import (BLANK, Bad, DateDetection, best_pattern, cell_text, detect_date_format, is_blank,
                     parse_date, parse_number)


class PopulationError(Exception):
    """Dirt the build refuses on. `rows` carries (loan id, column, value,
    reason) for the refusal file."""

    def __init__(self, rows: list[tuple[str, str, Any, str]]):
        self.rows = rows
        counts: dict[str, int] = {}
        for _, _, _, reason in rows:
            counts[reason] = counts.get(reason, 0) + 1
        summary = "; ".join(f"{n} x {r}" for r, n in sorted(counts.items()))
        super().__init__(f"the extract has values the pack will not accept: {summary}")


class AmbiguousDates(Exception):
    """Two or more patterns fit every value in a date column. The build
    refuses rather than guess; the message shows the sample both ways and
    names the line to add."""

    def __init__(self, det: DateDetection):
        self.detection = det
        readings = "; ".join(f"{pat} reads it as {plain}" for pat, plain in det.readings())
        super().__init__(
            f"column `{det.column}`: {len(det.ambiguous)} date patterns fit every value, so the pack cannot tell "
            f"which is meant. Sample {det.sample!r}: {readings}. Add under population:\n"
            f"  date_format: \"{det.ambiguous[0]}\"   # or one of {list(det.ambiguous)}")


def months_between(origination: date, asof: date) -> int:
    m = (asof.year - origination.year) * 12 + (asof.month - origination.month)
    if asof.day < origination.day:
        m -= 1
    return m


def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def quarter_label(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def compare(op: str, left: float, right: float) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    raise ValueError(op)


def bucket_index(value: float, edges: tuple[float, ...]) -> int:
    """Left-closed buckets: index 0 below the first edge, len(edges) at or
    above the last."""
    i = 0
    for e in edges:
        if value >= e:
            i += 1
        else:
            break
    return i


def fmt_edge(x: float) -> str:
    """An edge as a person would write it: 150,000 not 1.5e+05; 0.5 stays 0.5."""
    if float(x).is_integer():
        return f"{int(x):,}"
    return f"{x:g}"


def bucket_labels(edges: tuple[float, ...]) -> list[str]:
    def fmt(x: float) -> str:
        return fmt_edge(x)
    labels = [f"< {fmt(edges[0])}"]
    for i in range(len(edges) - 1):
        labels.append(f"{fmt(edges[i])} – {fmt(edges[i + 1])}")
    labels.append(f"≥ {fmt(edges[-1])}")
    return labels


@dataclass(frozen=True)
class OutcomeDef:
    key: str          # short, safe for a cube block id
    label: str        # what the tabs call it
    form: str         # event_date | flag | snapshot
    op: str | None = None
    value: float | None = None


@dataclass
class Loan:
    loan_id: str
    origination: date
    quarter: str
    year: int
    months_on_book: int
    seasoned: bool
    a: Any                       # float | BLANK
    b: Any                       # float | BLANK
    rule_value: float | None     # None when either side is blank
    fires: bool | None
    bucket: int | None
    events: dict[str, bool]      # outcome key -> event
    measure: float | None = None # the snapshot measure at as-of, when that form is used
    values: dict[str, Any] = field(default_factory=dict)   # confounder/control field -> float | str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Population:
    asof: date
    rows_read: int
    rows_after_filter: int
    loans: list[Loan]            # every loan after filter, seasoned or not
    bucket_labels: list[str]
    outcomes: list[OutcomeDef]
    date_formats: dict[str, str]         # column -> pattern used, or "typed date cells"
    date_parsed: dict[str, int]          # column -> non-blank values parsed
    range_checked: dict[str, bool]       # field -> whether a plausible range was applied
    measure_edges: tuple[float, ...] = ()   # for the graded snapshot form

    @property
    def seasoned(self) -> list[Loan]:
        return [l for l in self.loans if l.seasoned]

    @property
    def unseasoned(self) -> list[Loan]:
        return [l for l in self.loans if not l.seasoned]


def _rule_value(kind: str, a: float, b: float) -> float | Bad:
    if kind == "ratio":
        if b == 0.0:
            return Bad("zero in the denominator field", b)
        return a / b
    return a - b


def derive_value(steps: tuple, text: str) -> str | Bad:
    """Apply the field's grouping steps in order (PRD §6.15). A code shorter
    than a prefix length is malformed; a value in no group takes the `other`
    label, and with no `other` label it is refused, never invented."""
    v = text
    for step in steps:
        if step["kind"] == "prefix":
            if len(v) < step["length"]:
                return Bad(f"malformed code (shorter than the {step['length']}-character prefix)", text)
            v = v[:step["length"]]
        else:
            if v in step["lookup"]:
                v = step["lookup"][v]
            elif step["other"] is not None:
                v = step["other"]
            else:
                return Bad("value in no group and the map has no `other` label", v)
    return v


def outcome_defs(cfg: Config) -> list[OutcomeDef]:
    o = cfg.outcome
    if o.form == "event_date":
        return [OutcomeDef(key="o1", label=o.label, form="event_date")]
    if o.form == "flag":
        return [OutcomeDef(key="o1", label=o.label, form="flag", op=o.op, value=o.value)]
    if o.edges:
        return [OutcomeDef(key=f"o{i + 1}", label=f"{o.label} ≥ {e:g}", form="snapshot", op=">=", value=e)
                for i, e in enumerate(o.edges)]
    return [OutcomeDef(key="o1", label=o.label, form="snapshot", op=o.op, value=o.value)]


def _resolve_date_format(cfg: Config, column: str, rows: list[dict[str, Any]]) -> tuple[str | None, str, int, bool]:
    """(pattern to parse with, what to record, non-blank count, strict).
    `strict` False means failures of the best pattern are hygiene dirt."""
    values = [r.get(column) for r in rows]
    det = detect_date_format(column, values)
    if cfg.date_format:
        return cfg.date_format, cfg.date_format, det.total, True
    if det.total == det.typed:
        return None, "typed date cells", det.total, True
    if det.resolved:
        return det.resolved, det.resolved, det.total, True
    if det.ambiguous:
        raise AmbiguousDates(det)
    bp = best_pattern(det)
    return bp, (bp or "none fits"), det.total, False


def build_population(cfg: Config, rows: list[dict[str, Any]], asof: date) -> Population:
    """Type every row, apply the filter, season, and evaluate the rule and
    the outcome(s). Refuses (PopulationError) on dirt in any field the pack
    reads, and (AmbiguousDates) when a date column reads two ways."""
    dirt: list[tuple[str, str, Any, str]] = []
    seen_ids: set[str] = set()
    loans: list[Loan] = []
    outcomes = outcome_defs(cfg)
    o = cfg.outcome
    measure_edges = tuple(o.edges) if (o.form == "snapshot" and o.edges) else ()

    # the filter first, so dates are detected on the population that matters
    kept_rows: list[dict[str, Any]] = []
    for r in rows:
        keep = True
        for col, allowed in cfg.filter.items():
            if cell_text(r.get(col)) not in allowed:
                keep = False
                break
        if keep:
            kept_rows.append(r)

    date_cols = [cfg.origination_date] + ([o.date_field] if o.form == "event_date" else [])
    fmts: dict[str, str | None] = {}
    date_formats: dict[str, str] = {}
    date_parsed: dict[str, int] = {}
    for col in date_cols:
        fmt, record, n, _strict = _resolve_date_format(cfg, col, kept_rows)
        fmts[col] = fmt
        date_formats[col] = record
        date_parsed[col] = n

    plausible_fields = {name: f.plausible for name, f in cfg.fields.items() if f.plausible is not None}
    # sorted, so the order of the hygiene file's rows never depends on how a
    # set happens to iterate (adversarial pass, 19 Sep 2026)
    numeric_fields = sorted(set(c.field for c in cfg.confounders if c.schemes)
                            | set(c.field for c in cfg.controls if c.field and c.as_ in ("log", "linear", "bands")))
    log_fields = set(c.field for c in cfg.controls if c.field and c.as_ == "log")
    text_fields = sorted(set(c.field for c in cfg.confounders if not c.schemes)
                         | set(c.field for c in cfg.controls if c.field and c.as_ == "categorical"))
    rule_fields = (cfg.rule.field_a, cfg.rule.field_b)
    range_checked = {name: (f.plausible is not None) for name, f in cfg.fields.items()}

    for r in kept_rows:
        lid = cell_text(r.get(cfg.loan_id))
        if lid == "(blank)":
            dirt.append((lid, cfg.loan_id, r.get(cfg.loan_id), "blank loan id"))
            continue
        if lid in seen_ids:
            dirt.append((lid, cfg.loan_id, lid, "duplicate loan id"))
            continue
        seen_ids.add(lid)
        orig = parse_date(r.get(cfg.origination_date), fmts[cfg.origination_date])
        if orig is BLANK:
            dirt.append((lid, cfg.origination_date, r.get(cfg.origination_date), "blank origination date"))
            continue
        if isinstance(orig, Bad):
            dirt.append((lid, cfg.origination_date, orig.value, orig.reason))
            continue
        if orig > asof:
            dirt.append((lid, cfg.origination_date, orig.isoformat(), "origination after as-of"))
            continue
        bad = False
        for col, (lo, hi) in plausible_fields.items():
            v = parse_number(r.get(col))
            if isinstance(v, Bad):
                dirt.append((lid, col, v.value, v.reason)); bad = True
            elif v is not BLANK and not (lo <= v <= hi):
                dirt.append((lid, col, v, "outside the plausible range")); bad = True
        a = parse_number(r.get(cfg.rule.field_a))
        b = parse_number(r.get(cfg.rule.field_b))
        for col, v in ((cfg.rule.field_a, a), (cfg.rule.field_b, b)):
            if isinstance(v, Bad):
                if col not in plausible_fields:
                    dirt.append((lid, col, v.value, v.reason))
                bad = True
            elif v is not BLANK and v <= 0.0:
                dirt.append((lid, col, v, "zero or negative in a rule field")); bad = True
        values: dict[str, Any] = {}
        for col in numeric_fields:
            # a column that is also a rule field was parsed and, if bad, reported
            # just above; one bad value is one row (adversarial finding 9)
            v = a if col == cfg.rule.field_a else b if col == cfg.rule.field_b else parse_number(r.get(col))
            if isinstance(v, Bad):
                if col not in plausible_fields and col not in rule_fields:
                    dirt.append((lid, col, v.value, v.reason))
                bad = True
            else:
                if v is not BLANK and col in log_fields and v <= 0.0:
                    dirt.append((lid, col, v, "zero or negative in a log-scaled control")); bad = True
                values[col] = None if v is BLANK else v
        for col in text_fields:
            raw_text = None if is_blank(r.get(col)) else cell_text(r.get(col))
            if raw_text is not None and cfg.fields[col].derive:
                dv = derive_value(cfg.fields[col].derive, raw_text)
                if isinstance(dv, Bad):
                    dirt.append((lid, col, dv.value, dv.reason)); bad = True
                    continue
                raw_text = dv
            values[col] = raw_text
        if bad:
            continue
        rule_value: float | None = None
        fires: bool | None = None
        bucket: int | None = None
        if a is not BLANK and b is not BLANK:
            rv = _rule_value(cfg.rule.kind, a, b)
            if isinstance(rv, Bad):
                dirt.append((lid, cfg.rule.field_b, rv.value, rv.reason))
                continue
            rule_value = rv
            fires = compare(cfg.rule.fires_op, rv, cfg.rule.fires_value)
            bucket = bucket_index(rv, cfg.rule.buckets)
        mob = months_between(orig, asof)
        seasoned = mob >= cfg.window_months
        events: dict[str, bool] = {}
        measure: float | None = None
        if o.form == "event_date":
            ed = parse_date(r.get(o.date_field), fmts[o.date_field])
            if isinstance(ed, Bad):
                dirt.append((lid, o.date_field, ed.value, ed.reason))
                continue
            ev = False
            if ed is not BLANK:
                if ed < orig:
                    dirt.append((lid, o.date_field, ed.isoformat(), "outcome date before origination"))
                    continue
                ev = ed <= add_months(orig, cfg.window_months)
            events[outcomes[0].key] = ev
        elif o.form == "flag":
            v = parse_number(r.get(o.field))
            if isinstance(v, Bad):
                dirt.append((lid, o.field, v.value, v.reason))
                continue
            events[outcomes[0].key] = (v is not BLANK) and compare(o.op, v, o.value)
        else:  # snapshot
            m = o.measure or {}
            if "field" in m:
                v = parse_number(r.get(m["field"]))
                if isinstance(v, Bad):
                    dirt.append((lid, m["field"], v.value, v.reason)); continue
                measure = None if v is BLANK else v
            else:
                va = parse_number(r.get(m["field_a"])); vb = parse_number(r.get(m["field_b"]))
                if isinstance(va, Bad):
                    dirt.append((lid, m["field_a"], va.value, va.reason)); continue
                if isinstance(vb, Bad):
                    dirt.append((lid, m["field_b"], vb.value, vb.reason)); continue
                if va is BLANK or vb is BLANK:
                    measure = None
                else:
                    rv2 = _rule_value(m.get("kind", "ratio"), va, vb)
                    if isinstance(rv2, Bad):
                        dirt.append((lid, m["field_b"], rv2.value, rv2.reason)); continue
                    measure = rv2
            for od in outcomes:
                events[od.key] = measure is not None and compare(od.op, measure, od.value)
        loans.append(Loan(loan_id=lid, origination=orig, quarter=quarter_label(orig), year=orig.year,
                          months_on_book=mob, seasoned=seasoned, a=a, b=b, rule_value=rule_value,
                          fires=fires, bucket=bucket, events=events, measure=measure, values=values, raw=r))
    if dirt:
        raise PopulationError(dirt)
    loans.sort(key=lambda l: l.loan_id)
    return Population(asof=asof, rows_read=len(rows), rows_after_filter=len(kept_rows),
                      loans=loans, bucket_labels=bucket_labels(cfg.rule.buckets), outcomes=outcomes,
                      date_formats=date_formats, date_parsed=date_parsed, range_checked=range_checked,
                      measure_edges=measure_edges)
