"""From typed rows to the population the ladder runs on.

Seasoning, the outcome, the rule value, the flag and the bucket, per loan.
The as-of date is injected by the caller; nothing here reads a clock.

Months on book (PRD §6.4): whole calendar months from origination to as-of,
one fewer when the as-of day of month is earlier than the origination day.
A loan is seasoned when it has at least `window_months` on book. Only
seasoned loans enter a rate; the unseasoned are counted, by quarter.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .config import Config
from .ingest import BLANK, Bad, cell_text, is_blank, parse_date, parse_number


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


def bucket_labels(edges: tuple[float, ...]) -> list[str]:
    def fmt(x: float) -> str:
        return f"{x:g}"
    labels = [f"< {fmt(edges[0])}"]
    for i in range(len(edges) - 1):
        labels.append(f"{fmt(edges[i])} – {fmt(edges[i + 1])}")
    labels.append(f"≥ {fmt(edges[-1])}")
    return labels


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
    event: bool
    event_date: date | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Population:
    asof: date
    rows_read: int
    rows_after_filter: int
    loans: list[Loan]            # every loan after filter, seasoned or not
    bucket_labels: list[str]

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


def build_population(cfg: Config, rows: list[dict[str, Any]], asof: date) -> Population:
    """Type every row, apply the filter, season, and evaluate the rule and
    the outcome. Refuses (PopulationError) on dirt in any field the pack
    reads: a non-numeric rule value, a zero or negative rule value, an
    unparseable date, a duplicate loan id, an origination after as-of, or
    an outcome date before origination."""
    dirt: list[tuple[str, str, Any, str]] = []
    seen_ids: set[str] = set()
    loans: list[Loan] = []
    rows_after_filter = 0
    fmt = cfg.date_format
    for r in rows:
        if cfg.filter:
            keep = True
            for col, allowed in cfg.filter.items():
                if cell_text(r.get(col)) not in allowed:
                    keep = False
                    break
            if not keep:
                continue
        rows_after_filter += 1
        lid = cell_text(r.get(cfg.loan_id))
        if lid == "(blank)":
            dirt.append((lid, cfg.loan_id, r.get(cfg.loan_id), "blank loan id"))
            continue
        if lid in seen_ids:
            dirt.append((lid, cfg.loan_id, lid, "duplicate loan id"))
            continue
        seen_ids.add(lid)
        orig = parse_date(r.get(cfg.origination_date), fmt)
        if orig is BLANK:
            dirt.append((lid, cfg.origination_date, r.get(cfg.origination_date), "blank origination date"))
            continue
        if isinstance(orig, Bad):
            dirt.append((lid, cfg.origination_date, orig.value, orig.reason))
            continue
        if orig > asof:
            dirt.append((lid, cfg.origination_date, orig.isoformat(), "origination after as-of"))
            continue
        a = parse_number(r.get(cfg.rule.field_a))
        b = parse_number(r.get(cfg.rule.field_b))
        bad = False
        for col, v in ((cfg.rule.field_a, a), (cfg.rule.field_b, b)):
            if isinstance(v, Bad):
                dirt.append((lid, col, v.value, v.reason)); bad = True
            elif v is not BLANK and v <= 0.0:
                dirt.append((lid, col, v, "zero or negative in a rule field")); bad = True
            elif v is not BLANK and cfg.fields[col].plausible is not None:
                lo, hi = cfg.fields[col].plausible
                if not (lo <= v <= hi):
                    dirt.append((lid, col, v, "outside the plausible range")); bad = True
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
        event = False
        event_date: date | None = None
        if cfg.outcome.form == "event_date":
            ed = parse_date(r.get(cfg.outcome.date_field), fmt)
            if isinstance(ed, Bad):
                dirt.append((lid, cfg.outcome.date_field, ed.value, ed.reason))
                continue
            if ed is not BLANK:
                if ed < orig:
                    dirt.append((lid, cfg.outcome.date_field, ed.isoformat(), "outcome date before origination"))
                    continue
                event_date = ed
                event = ed <= add_months(orig, cfg.window_months)
        elif cfg.outcome.form == "flag":
            v = parse_number(r.get(cfg.outcome.field))
            if isinstance(v, Bad):
                dirt.append((lid, cfg.outcome.field, v.value, v.reason))
                continue
            event = (v is not BLANK) and compare(cfg.outcome.op, v, cfg.outcome.value)
        else:  # snapshot
            m = cfg.outcome.measure or {}
            if "field" in m:
                v = parse_number(r.get(m["field"]))
                if isinstance(v, Bad):
                    dirt.append((lid, m["field"], v.value, v.reason)); continue
                mv = None if v is BLANK else v
            else:
                va = parse_number(r.get(m["field_a"])); vb = parse_number(r.get(m["field_b"]))
                if isinstance(va, Bad):
                    dirt.append((lid, m["field_a"], va.value, va.reason)); continue
                if isinstance(vb, Bad):
                    dirt.append((lid, m["field_b"], vb.value, vb.reason)); continue
                if va is BLANK or vb is BLANK:
                    mv = None
                else:
                    rv2 = _rule_value(m.get("kind", "ratio"), va, vb)
                    if isinstance(rv2, Bad):
                        dirt.append((lid, m["field_b"], rv2.value, rv2.reason)); continue
                    mv = rv2
            event = mv is not None and compare(cfg.outcome.op, mv, cfg.outcome.value)
        loans.append(Loan(loan_id=lid, origination=orig, quarter=quarter_label(orig), year=orig.year,
                          months_on_book=mob, seasoned=seasoned, a=a, b=b, rule_value=rule_value,
                          fires=fires, bucket=bucket, event=event, event_date=event_date, raw=r))
    if dirt:
        raise PopulationError(dirt)
    loans.sort(key=lambda l: l.loan_id)
    return Population(asof=asof, rows_read=len(rows), rows_after_filter=rows_after_filter,
                      loans=loans, bucket_labels=bucket_labels(cfg.rule.buckets))
