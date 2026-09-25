"""What each column means: the catalog, the value tests, and the suggestions.

The catalog lives in settings.yaml (`meanings:`), so a bank's own column
names are added there, not here. This module only knows how to test values
against a meaning and how to rank what fits.

A suggestion is made in this order, and says which reason it rests on:
  1. remembered   the same column name was confirmed before (memory.py). Wins,
                  but if the values no longer fit, it says so.
  2. name + values  a hint in the column name, and the values pass the test
  3. values alone  only for tests specific enough to stand without a name:
                  a 300-850 score, one date on every row, a 0/1 column
  4. structure    band-like numbers become `amount`, short lists `category`,
                  anything else `unknown`, which is never cut by
The firm: "it won't and should not be able to guess them all off the bat -
but some are obvious." A custom score on the FICO scale will be suggested as
FICO until someone confirms it as `score`; after that, the memory has it.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from .ingest import Bad, Table, detect_date_format, is_blank, parse_number

REQUIRED = ("key", "booked", "outcome", "gco", "ranr")


@dataclass(frozen=True)
class Meaning:
    means: str
    says: str
    cut: str                      # band | dimension | none
    required: bool
    hints: tuple[str, ...]
    test: Any


def catalog(path: str | Path | None = None) -> dict[str, Meaning]:
    text = (Path(path).read_text(encoding="utf-8") if path
            else resources.files("origination_cube").joinpath("settings.yaml").read_text(encoding="utf-8"))
    out = {}
    for m in yaml.safe_load(text)["meanings"]:
        out[m["means"]] = Meaning(means=m["means"], says=str(m["says"]), cut=m["cut"],
                                  required=bool(m.get("required", False)),
                                  hints=tuple(str(h) for h in m.get("hints", [])), test=m.get("test", "any"))
    return out


def norm(name: str) -> str:
    return re.sub(r"[^0-9a-z]", "", str(name).lower())


def hint_in(name: str, hints: tuple[str, ...]) -> str | None:
    n = norm(name)
    for h in hints:
        if norm(h) and norm(h) in n:
            return h
    return None


# --------------------------------------------------------------------------
# What a column's values look like, worked out once


@dataclass
class Facts:
    name: str
    rows: int
    nonblank: int
    distinct: int
    numbers: list[float]
    texts: list[str]
    dates: int                   # values that read as dates
    one_value: bool

    @property
    def numeric(self) -> bool:
        return self.nonblank > 0 and len(self.numbers) >= 0.99 * self.nonblank


def facts(table: Table, col: str) -> Facts:
    raw = [r.get(col) for r in table.rows]
    nonblank = [v for v in raw if not is_blank(v)]
    nums = []
    for v in nonblank:
        p = parse_number(v)
        if not isinstance(p, Bad):
            nums.append(p)
    texts = [str(v).strip() for v in nonblank]
    det = detect_date_format(col, raw)
    dates = det.typed + max(det.fits.values(), default=0)
    if nums and len(nums) == len(nonblank) and not det.typed:
        # all numbers: a date only when every value is an 8-digit YYYYMMDD, the way a mainframe writes one
        eight = all(len(t) == 8 for t in (str(v).strip() for v in nonblank))
        dates = len(nonblank) if eight and det.fits.get("%Y%m%d") == len(nonblank) else 0
    return Facts(col, len(raw), len(nonblank), len(set(texts)), nums, texts, dates, len(set(texts)) == 1)


def _ratio_scale(v: list[float]) -> list[float]:
    """Ratios come as fractions (0.36) or percentages (36): read both the same."""
    if not v:
        return v
    med = statistics.median(v)
    return [x / 100 for x in v] if med > 3 else v


def passes(test: Any, f: Facts) -> tuple[bool, str]:
    """(fits, what was seen) for one meaning's test."""
    if f.nonblank == 0:
        return (test == "any"), "empty"
    if test == "any":
        return True, ""
    if test == "unique":
        return f.distinct == f.nonblank and f.nonblank > 1, "a different value on every row"
    if test == "category":
        return not f.numeric or f.distinct <= 24, f"{f.distinct} different values"
    if test == "dates":
        return f.dates >= 0.9 * f.nonblank and not f.one_value, "dates"
    if test == "one_date":
        return f.dates >= 0.9 * f.nonblank and f.one_value, "one date on every row"
    if not f.numeric:
        return False, "not numbers"
    v = f.numbers
    if test == "numbers":
        return True, "numbers"
    if test == "positive":
        return min(v) > 0 and len(v) >= 0.99 * f.rows, "positive on every loan"
    if test == "binary":
        yes, no = sum(1 for x in v if x == 1.0), sum(1 for x in v if x == 0.0)
        other = len(v) - yes - no
        ok = yes > 0 and no > 0 and other <= 0.01 * len(v)
        return ok, f"0 and 1 ({yes / max(yes + no, 1):.1%} are 1)"
    if test == "mostly_zero":
        zeros = sum(1 for x in v if x == 0)
        return min(v) >= 0 and zeros >= 0.5 * len(v) and len(set(v)) > 2, \
            f"zero on {zeros / len(v):.0%} of loans, never negative"
    if test == "term":
        ints = [x for x in v if float(x).is_integer()]
        ok = len(ints) == len(v) and len(set(v)) <= 24 and all(3 <= x <= 480 for x in v) \
            and sum(1 for x in v if x % 6 == 0) >= 0.8 * len(v)
        return ok, f"whole months from {min(v):g} to {max(v):g}"
    if isinstance(test, dict) and "range" in test:
        lo, hi = test["range"]
        inside = [x for x in v if lo <= x <= hi]
        ok = len(inside) >= 0.95 * len(v) and len(set(inside)) > 50 and all(float(x).is_integer() for x in inside)
        return ok, f"{len(inside) / len(v):.0%} of values between {lo:g} and {hi:g}"
    if isinstance(test, dict) and "ratio_median" in test:
        lo, hi = test["ratio_median"]
        r = _ratio_scale(v)
        med = statistics.median(r)
        ok = lo <= med <= hi and min(r) >= 0 and len(set(v)) > 10
        return ok, f"a ratio with median {med:.0%}"
    return False, ""


# --------------------------------------------------------------------------


@dataclass
class Suggestion:
    column: str
    means: str
    why: str
    source: str                   # remembered | name | values | structure
    is_value: Any = None          # for an outcome made yes/no from a value


#: meanings specific enough to suggest from the values alone
BY_VALUES_ALONE = ("fico", "as_of_date")


def suggest(table: Table, remembered: dict[str, dict] | None = None,
            cat: dict[str, Meaning] | None = None) -> dict[str, Suggestion]:
    cat = cat or catalog()
    remembered = remembered or {}
    fs = {c: facts(table, c) for c in table.columns}
    out: dict[str, Suggestion] = {}

    # 1. remembered
    for c, f in fs.items():
        hit = remembered.get(c) or next((v for k, v in remembered.items() if norm(k) == norm(c)), None)
        if hit and hit.get("means") in cat:
            ok, seen = passes(cat[hit["means"]].test, f)
            why = f"you confirmed this as {cat[hit['means']].says} on {hit.get('last', '?')}"
            if not ok:
                why += f"; CHECK: these values don't look like it ({seen or 'no values'})"
            out[c] = Suggestion(c, hit["means"], why, "remembered", hit.get("is"))

    taken_required = {s.means for s in out.values() if s.means in REQUIRED}

    # 2. required meanings: one column each, name and values both fitting, or the only fit
    for m in REQUIRED:
        if m in taken_required:
            continue
        fits = {c: passes(cat[m].test, f) for c, f in fs.items() if c not in out}
        fits = {c: seen for c, (ok, seen) in fits.items() if ok}
        named = [(cat[m].hints.index(h), c, h) for c in fits if (h := hint_in(c, cat[m].hints))]
        if named:
            _, c, h = sorted(named)[0]
            out[c] = Suggestion(c, m, f"name contains '{h}'; {fits[c]}", "name")
        elif len(fits) == 1:
            c = next(iter(fits))
            out[c] = Suggestion(c, m, f"the only column that fits: {fits[c]}", "values")

    # 3. everything else: name and values, then values alone, then structure
    optional = [m for m in cat.values() if not m.required and m.means not in ("unused", "unknown")]
    for c, f in fs.items():
        if c in out:
            continue
        if f.nonblank == 0 or (f.one_value and not passes(cat["as_of_date"].test, f)[0]):
            out[c] = Suggestion(c, "unused", "empty" if f.nonblank == 0 else f"one value only ({f.texts[0]})",
                                "structure")
            continue
        best = None
        for m in optional:
            h = hint_in(c, m.hints)
            ok, seen = passes(m.test, f)
            if h and ok:
                best = Suggestion(c, m.means, f"name contains '{h}'; {seen}", "name")
                break
        if best is None:
            h = hint_in(c, cat["fico"].hints) or hint_in(c, cat["score"].hints)
            if h and f.numeric:
                best = Suggestion(c, "score", f"name contains '{h}', but the values aren't on the FICO scale",
                                  "name")
        if best is None:
            for mname in BY_VALUES_ALONE:
                ok, seen = passes(cat[mname].test, f)
                if ok:
                    extra = (" (a custom score on the same scale looks the same: confirm it as `score` "
                             "if so, and it will be remembered)") if mname == "fico" else ""
                    best = Suggestion(c, mname, f"{seen}{extra}", "values")
                    break
        if best is None:
            dates_ok, _ = passes(cat["origination_date"].test, f)
            if dates_ok:
                best = Suggestion(c, "unknown", "dates, but which date? Say origination_date if it is when the "
                                               "loan was made", "structure")
            elif passes("unique", f)[0]:
                best = Suggestion(c, "id", "a different value on every row", "structure")
            elif f.numeric and len(set(f.numbers)) > 12:
                best = Suggestion(c, "amount", f"numbers with {len(set(f.numbers)):,} values", "structure")
            elif f.distinct <= 50:
                best = Suggestion(c, "category", f"{f.distinct} different values", "structure")
            else:
                best = Suggestion(c, "unknown", f"{f.distinct:,} different values and nothing to go on",
                                  "structure")
        out[c] = best
    return {c: out[c] for c in table.columns}
