"""`cube init`: read an extract, say what every column is, and write the cube file.

The firm, 25 Sep 2026: "hopefully we are self-identifying instances where we
clearly have something that is a dimension as opposed to band". So every
column is classified from its own values, and only the clear cases are
decided. Anything unclear is raised as a question and left out of the cuts
until answered, which the file and every output say. Nothing stops the run.

    band        numbers with more distinct values than `few_values` (score, DTI, balance)
    dimension   text with at most `many_values` distinct values (channel, state),
                or numbers with at most `few_values` (term 36/48/60, a grade 1-10),
                or number-like codes written with leading zeros (a ZIP, a branch code)
    key         text that differs on every row, or a same-width number of 6+ digits
                that does (loan number, application number)
    date        dates (the origination date, for loan age; not cut by)
    skipped     empty, or one value only: nothing to cut by
    question    text with too many values to cut by, a mix of numbers and text,
                or any other number that differs on every row (an ID or an amount?)

The five required lines - key, booked, outcome, gco, ranr - are SUGGESTED from
column names (the hints in settings.yaml) and values, each with its reason,
and the file carries `columns_confirmed: no`: it refuses to run until a person
has checked them and set it to yes. The firm: "make assumptions for
suggestions but ultimately ask for confirmation ... and be able to fix it
easily". Fixing one is typing the right column name over it. Where nothing
fits, the line is [CONFIRM: ...] with the candidates listed. The judgment
settings (what is material, how much worse counts as worse) are never
suggested: they stay [CONFIRM: ...] unless a filled-in Control tab is passed
with `--control`.

ODD VALUES (ruling OC-7). Two patterns are raised as questions, never acted on:
  repeated_value  one value, 1% of rows or more, sitting far outside the rest
                  (a -9999 among scores of 500-850)
  negatives       some negative values in a column that is otherwise positive
                  (RANR's negatives are real; a balance's would not be)
The thresholds below only decide what gets ASKED. They never change a number.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import control
from .ingest import Bad, Table, cell_text, detect_date_format, is_blank, parse_number

#: A repeated value is asked about when it covers this share of rows or more ...
REPEAT_SHARE = 0.01
#: ... and sits further outside the rest than this share of the rest's range.
REPEAT_DISTANCE = 0.5
#: Negatives are asked about when present but fewer than this share of values.
NEGATIVE_SHARE = 0.5
#: A column this share numbers or more is a number column; its few text values
#: are counted as "not a number" wherever it is read, never guessed at. One
#: "#N/A" among 20,000 amounts must not turn GCO into a question.
NUMERIC_SHARE = 0.99

JUDGMENT_TO_FILE = {"min_loans": "min_units", "worse_at": "worse_at", "better_at": "better_at",
                    "confidence": "confidence"}


@dataclass
class Column:
    name: str
    role: str                      # band | dimension | key | date | skipped | question
    why: str
    distinct: int
    blank_share: float
    samples: list[str]
    questions: list[dict] = field(default_factory=list)


def _slug(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return s or "column"


def classify(table: Table, few_values: int, many_values: int) -> list[Column]:
    n = len(table.rows)
    out = []
    for col in table.columns:
        raw = [r.get(col) for r in table.rows]
        nonblank = [v for v in raw if not is_blank(v)]
        blank_share = (n - len(nonblank)) / n if n else 0.0
        texts = [cell_text(v) for v in nonblank]
        distinct = len(set(texts))
        samples = list(dict.fromkeys(texts))[:5]
        nums = [parse_number(v) for v in nonblank]
        numeric = [x for x in nums if not isinstance(x, Bad)]

        def make(role, why, qs=None):
            out.append(Column(col, role, why, distinct, blank_share, samples, qs or []))

        if not nonblank:
            make("skipped", "empty")
            continue
        if distinct == 1:
            make("skipped", f"one value only ({samples[0]})")
            continue
        det = detect_date_format(col, raw)
        date_like = det.typed + max(det.fits.values(), default=0)
        if det.typed == len(nonblank) or (date_like >= 0.9 * len(nonblank) and len(numeric) < len(nonblank)):
            make("date", "dates")
            continue
        if distinct == len(nonblank) and len(nonblank) > 1:
            if not numeric:
                make("key", "a different value on every row")
                continue
            widths = {len(t) for t in texts}
            if len(numeric) == len(nonblank) and all(float(x).is_integer() for x in numeric) \
                    and len(widths) == 1 and min(widths) >= 6:
                make("key", "a different fixed-width number on every row")
                continue
            if len(numeric) == len(nonblank):
                make("question", "a different number on every row: if it is a loan or application number, "
                                 "make it the key; if it is an amount, list it under bands")
                continue
        if len(numeric) >= NUMERIC_SHARE * len(nonblank):
            coded = any(isinstance(v, str) and len(v.strip()) > 1 and v.strip()[0] == "0" and v.strip().isdigit()
                        for v in nonblank)
            text = len(nonblank) - len(numeric)
            note = f"; {text:,} value(s) not a number, counted when read" if text else ""
            n_distinct = len(set(numeric))
            if coded:
                make("dimension", f"a code written with leading zeros{note}")
            elif n_distinct <= few_values:
                make("dimension", f"numbers with only {n_distinct} values: read as categories{note}")
            else:
                make("band", f"numbers with {n_distinct:,} values{note}", odd_values(col, numeric))
            continue
        if len(numeric) == 0:
            if distinct <= many_values:
                make("dimension", f"text with {distinct} values")
            else:
                make("question", f"text with {distinct:,} values: too many to cut by. Group it upstream, "
                                 f"or list it under dimensions to cut by it anyway")
            continue
        make("question", f"a mix of numbers ({len(numeric):,}) and text ({len(nonblank) - len(numeric):,})")
    return out


def odd_values(col: str, numeric: list[float]) -> list[dict]:
    qs = []
    if not numeric:
        return qs
    counts = Counter(numeric)
    value, k = counts.most_common(1)[0]
    rest = [x for x in numeric if x != value]
    repeated = None
    if rest and k >= REPEAT_SHARE * len(numeric):
        lo, hi = min(rest), max(rest)
        span = (hi - lo) or abs(hi) or 1.0
        if value < lo - REPEAT_DISTANCE * span or value > hi + REPEAT_DISTANCE * span:
            repeated = value
            qs.append({"column": col, "pattern": "repeated_value", "value": value, "rows": k})
    neg = [x for x in numeric if x < 0 and x != repeated]
    if neg and len(neg) < NEGATIVE_SHARE * len(numeric):
        qs.append({"column": col, "pattern": "negatives", "value": None, "rows": len(neg)})
    return qs


# --------------------------------------------------------------------------
# Suggesting the required columns


def _norm(name: str) -> str:
    return re.sub(r"[^0-9a-z]", "", name.lower())


def _hint(name: str, hints: list[str]) -> str | None:
    n = _norm(name)
    for h in hints:
        if _norm(h) and _norm(h) in n:
            return h
    return None


@dataclass
class Suggestion:
    role: str
    column: str | None
    why: str
    candidates: list[str]


def _numbers(table: Table, col: str) -> list[float]:
    out = []
    for r in table.rows:
        v = parse_number(r.get(col))
        if not isinstance(v, Bad) and v is not None and not is_blank(r.get(col)):
            out.append(v)
    return out


def suggest_roles(table: Table, cols: list[Column], hints: dict[str, list[str]]) -> dict[str, Suggestion]:
    """A suggested column for each required line, with the reason, or none
    and the candidates. Name and values must both fit, except for the key,
    where a different value on every row is the whole test."""
    by = {c.name: c for c in cols}
    nums = {c.name: _numbers(table, c.name) for c in cols if c.role in ("band", "dimension", "question")}
    out: dict[str, Suggestion] = {}
    taken: set[str] = set()

    def pick(role: str, fits: dict[str, str]) -> None:
        free = {k: v for k, v in fits.items() if k not in taken}
        named = [(c, why, _hint(c, hints.get(role, []))) for c, why in free.items()]
        named = [x for x in named if x[2]]
        if len(named) >= 1:
            # the earliest hint in the list is the strongest; ties go to column order
            order = hints.get(role, [])
            named.sort(key=lambda x: order.index(x[2]))
            c, why, h = named[0]
            out[role] = Suggestion(role, c, f"name contains '{h}'; {why}", list(free))
            taken.add(c)
        elif len(free) == 1:
            c, why = next(iter(free.items()))
            out[role] = Suggestion(role, c, f"the only column that fits: {why}", list(free))
            taken.add(c)
        else:
            out[role] = Suggestion(role, None, "no column's name and values both fit", list(free))

    keys = {c.name: c.why for c in cols if c.role == "key"}
    pick("key", keys)
    flags = {}
    for c, v in nums.items():
        yes, no = sum(1 for x in v if x == 1.0), sum(1 for x in v if x == 0.0)
        other = len(v) - yes - no
        if v and yes and no and other <= (1 - NUMERIC_SHARE) * len(v):
            note = f"; {other:,} other value(s), counted when read" if other else ""
            flags[c] = f"0 and 1 ({yes / (yes + no):.1%} are 1){note}"
    pick("outcome", flags)
    gco = {}
    for c, v in nums.items():
        if v and min(v) >= 0 and sum(1 for x in v if x == 0) >= 0.5 * len(v) and len(set(v)) > 2:
            gco[c] = f"zero on {sum(1 for x in v if x == 0) / len(v):.0%} of loans, never negative"
    pick("gco", gco)
    ranr = {c: "numbers" for c, v in nums.items() if v and len(set(v)) > 2}
    pick("ranr", ranr)
    booked = {}
    for c, v in nums.items():
        if v and min(v) > 0 and len(set(v)) > 2 and len(v) >= 0.99 * len(table.rows):
            booked[c] = "positive on every loan"
    pick("booked", booked)
    return out


# --------------------------------------------------------------------------


def _q(v: Any) -> str:
    if isinstance(v, str):
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            return v
        return '"' + v.replace('"', "'") + '"'
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _confirm(setting: control.Setting) -> str:
    opts = " / ".join(str(o.value) for o in setting.options)
    return _q(f"[CONFIRM: {setting.question.lower()}? Pick {opts}, or enter your own]")


def write_cube_file(table: Table, out: str | Path, settings_in_use: dict[str, Any] | None = None,
                    today: date | None = None) -> tuple[Path, list[Column]]:
    """Write a cube file for this extract. `settings_in_use` comes from a
    filled-in Control tab; without one, method settings take their
    recommended option and judgment settings are left as [CONFIRM: ...]."""
    settings = {s.key: s for s in control.load_settings()}
    use = dict(settings_in_use or {})

    def method(key):
        return use[key] if key in use else settings[key].recommended().value

    cols = classify(table, int(method("few_values")), int(method("many_values")))
    count, cut = int(method("band_count")), method("band_cut")
    by_role: dict[str, list[Column]] = {}
    for c in cols:
        by_role.setdefault(c.role, []).append(c)

    lines = [f"# Written by `cube init` from {Path(table.path).name} on {(today or date.today()).isoformat()}.",
             f"# {len(table.rows):,} rows, {len(table.columns)} columns. Every column is below, in its section",
             "# or under 'Not cut by', with the reason. Move a line to change what a column is.",
             "# Nothing marked [CONFIRM: ...] is decided for you; the run refuses until each is answered.",
             f"name: {_slug(Path(table.path).stem)}", "schema_version: 1"]
    sugg = suggest_roles(table, cols, control.role_hints())
    what = {"key": "loan or application number, to map results back to loans",
            "booked": "the booked or loan amount that weights the reporting-level rates",
            "outcome": "a yes/no column (0/1); or write {field: COLUMN, is: VALUE}",
            "gco": "gross charge-off dollars", "ranr": "RANR dollars (signed values are kept)"}
    lines += ["", "# REQUIRED COLUMNS, suggested by cube init. Check each. If one is wrong, type the right",
              "# column name over it. Then set columns_confirmed to yes; the run refuses until you do."]
    for role in ("key", "booked", "outcome", "gco", "ranr"):
        sg = sugg[role]
        if sg.column:
            lines.append(f"{role + ': ' + _q(sg.column):<30} # SUGGESTED - {sg.why}. Needed: {what[role]}")
        else:
            cands = ", ".join(sg.candidates) if sg.candidates else "none found"
            lines.append(f"{role}: {_q(f'[CONFIRM: which column is {what[role]}? candidates: {cands}]')}")
    lines.append("columns_confirmed: no")
    dates = by_role.get("date", [])
    if dates:
        lines.append(f"# dates found (for loan age, not cut by): {', '.join(d.name for d in dates)}")

    lines += ["", "missing: {}                  # answer the questions at the bottom to add rules here", "",
              "# CHECK the bands and dimensions: take out any column recorded AFTER the loan was made",
              "# (a charge-off flag, a status, days past due). Cutting by an outcome is circular, and",
              "# the tool cannot tell when a column was recorded. GCO and RANR are left out for you",
              "# once they are named under measures.",
              f"bands:                        # cut into {count}, {cut.replace('_', ' ')}"]
    names: set[str] = set()

    def uniq(n):
        base, i = n, 2
        while n in names:
            n, i = f"{base}_{i}", i + 1
        names.add(n)
        return n

    for c in by_role.get("band", []):
        lines.append(f"  - {{name: {uniq(_slug(c.name))}, field: {_q(c.name)}, count: {count}, cut: {cut}}}"
                     f"   # {c.why}")
    lines += ["", "dimensions:"]
    for c in by_role.get("dimension", []):
        lines.append(f"  - {{name: {uniq(_slug(c.name))}, field: {_q(c.name)}}}   # {c.why}")
    lines += ["", "# Not cut by:"]
    for role in ("key", "date", "skipped", "question"):
        for c in by_role.get(role, []):
            lines.append(f"#   {c.name:<24} {role}: {c.why}")

    lines += ["", "# The core rates (outcome by loans and by booked dollars, GCO and RANR per booked dollar)",
              "# are built from the required columns on every run. Extras go here; per: each_loan",
              "# divides by the number of loans instead of a column (a straight average).",
              "measures:", "  - {name: loans, mode: count}", ""]

    lines.append("benchmark:")
    for skey, fkey in JUDGMENT_TO_FILE.items():
        val = use.get(skey)
        lines.append(f"  {fkey}: {_q(val) if val is not None else _confirm(settings[skey])}")
    lines.append(f"  power: {_q(method('power'))}")

    qs = [q for c in cols for q in c.questions]
    lines += ["", "# Odd values. Each is used AS RECORDED until you answer: real, or missing.",
              "# Nothing stops the run; every output lists the questions still open."]
    if qs:
        lines.append("questions:")
        for q in qs:
            val = f", value: {_q(q['value'])}" if q["value"] is not None else ""
            lines.append(f"  - {{column: {_q(q['column'])}, pattern: {q['pattern']}{val}, rows: {q['rows']}, "
                         f"answer: }}")
    else:
        lines.append("questions: []")
    p = Path(out)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p, cols
