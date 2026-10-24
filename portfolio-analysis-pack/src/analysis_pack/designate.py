"""Designation at the desk: `pack init EXTRACT` writes a question-file
skeleton from the extract's own columns, so whoever holds the file says what
each column is, there, and nothing comes back to whoever built the tool.

The firm, 20 September 2026: "we design a tool that we can put anything into
and designate it to be something that the tool can work with. The point is it
isn't key specific." Until this module the bundle carried one fixed question
file, so the only place a column could be designated was where the bundle
was made. Now the bundle takes a question file beside it, and writes the
skeleton for one on request.

Every slot the person must choose carries a "[CONFIRM: ...]" marker. The
loader refuses a file that still has one and names each; the tool never
fills a slot on someone's behalf (refuse rather than default). The skeleton
is a file template, not a sentence: the only text it takes from the extract
is its column names and what `pack inspect` found in them.
"""

from __future__ import annotations

import re

from .config import CONFIRM
from .ingest import Table

_PLAIN_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _marker(text: str) -> str:
    return f'"{CONFIRM} {text}]"'


def _key(col: str) -> str:
    """A YAML mapping key for a column name, quoted when it needs to be."""
    if _PLAIN_KEY.match(col):
        return col
    return '"' + col.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _clean(text: str, limit: int = 32) -> str:
    """Sample text safe inside a YAML comment: one line, no longer than `limit`."""
    one = " ".join(str(text).split())
    return one if len(one) <= limit else one[: limit - 1] + "…"


def _column_line(entry: dict) -> str:
    kind = entry["kind"]
    blank = "blank n/a" if entry["null_share"] is None else f"blank {entry['null_share']:.0%}"
    samples = ", ".join(_clean(s) for s in entry["samples"][:3])
    dates = entry.get("dates") or {}
    if dates.get("resolved"):
        kind = f"{kind}, reads as dates ({dates['resolved']})"
    elif dates.get("ambiguous"):
        kind = f"{kind}, two date patterns fit"
    comment = f"# {kind}, {blank}" + (f", e.g. {samples}" if samples else "")
    return f"  {_key(entry['column'])}: {{known: {_marker('at_origination or later')}}}   {comment}"


def skeleton(table: Table, report: list[dict]) -> str:
    """The question file to fill in, as text. `report` is `inspect_columns(table)`."""
    source = table.path.replace("\\", "/").split("/")[-1]
    head = [
        f"# Question file written by `pack init` from {source}.",
        "# Every value marked CONFIRM is yours to fill in; the tool refuses the file",
        "# until none is left, and names each one. Column names are spelled",
        "# exactly as the extract spells them. Delete the line of any column the",
        "# pack should not read: only the columns declared under `fields` are read.",
        "",
        f"name: {_marker('a short name for this question, letters and underscores')}",
        "schema_version: 1",
        "rule_type: contradiction",
        "",
        "population:",
        f"  loan_id: {_marker('the column that numbers the loans')}",
        f"  origination_date: {_marker('the column with the date the loan was made')}",
        "  # filter: {COLUMN: [value, value]}    # optional: keep only rows with these values",
        "",
        "fields:",
        "  # For each column the pack reads: was it known when the loan was made",
        "  # (at_origination), or only afterwards (later)? A `later` column can be",
        "  # the outcome and nothing else; that is how leakage is refused.",
        "  # Optional per column: plausible: [low, high]  (values outside are refused)",
        "  #                      derive: {kind: prefix, length: 2}  (group a code column)",
    ]
    columns = [_column_line(e) for e in report]
    tail = [
        "",
        "rule:",
        "  kind: ratio                          # ratio = field_a / field_b; difference = field_a - field_b",
        f"  field_a: {_marker('the column on top of the ratio')}",
        f"  field_b: {_marker('the column underneath')}",
        "  fires_when: {op: '>', value: 1.0}    # the flag: ratio above 1",
        "  buckets: [0.5, 1.0, 2.0, 5.0]        # edges of the gradient over the ratio",
        "",
        "outcome:",
        f"  label: {_marker('the word every tab uses for the event, e.g. the loan went bad')}",
        f"  date_field: {_marker('the column with the date of the event; declare it known: later above')}",
        "  # Instead of date_field, a flag the bank already windowed:",
        "  #   field: FLAG_COLUMN",
        "  #   op: '=='",
        "  #   value: 1",
        "  #   basis: how and over what window the flag was set",
        "  # Or a measure at the as-of date, with one cut or with percentage bands:",
        "  #   measure: {kind: ratio, field_a: NUMERATOR_COLUMN, field_b: DENOMINATOR_COLUMN}",
        "  #   edges: [0.5, 0.8, 0.9]",
        "  #   basis: snapshot_at_asof",
        "",
        "window_months: 24                      # a loan needs this many months on book to count",
        "",
        f"confounders: {_marker('what the effect might be hiding in: list columns as the examples below show, or write [] for none')}",
        "  # Things the effect might be in disguise as. Each is a column, banded by",
        "  # edges you choose (ask `pack suggest`), or a text column taken level by level:",
        "  # - name: size_band",
        "  #   field: AMOUNT_COLUMN",
        "  #   edges: [100000, 250000, 1000000]",
        "  # - name: product",
        "  #   field: PRODUCT_COLUMN",
        "",
        "controls:",
        "  - {name: origination_year, derived: origination_year}",
        "  # - {name: amount_log, field: AMOUNT_COLUMN, as: log}",
        "  # - {name: product, field: PRODUCT_COLUMN, as: categorical}",
        "",
        "decompose_by: [origination_year]       # step 5 shows where the flagged events sit",
        "",
        f"existing_control: {_marker('none, or what at the bank reacts to this contradiction today')}",
        "# drives:                              # optional: what decision each field feeds",
        "#   field_a: what field_a drives",
        "#   field_b: what field_b drives",
        "",
        "model: {tree_depth: 3, min_leaf_events: 10, min_leaf_loans: 100}",
        "intervals: {confidence: 0.95, method: wilson}",
        "survives_threshold: 0.5",
        "",
    ]
    return "\n".join(head + columns + tail)


def count_markers(text: str) -> int:
    return text.count(CONFIRM)
