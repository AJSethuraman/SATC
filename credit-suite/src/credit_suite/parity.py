"""Output-parity harness: snapshot a shipped workbook, diff a rebuilt one.

Consolidation is only safe if it provably changes nothing a KeyBank reviewer
sees. This module captures that "nothing" as a committed golden file and gives
the regression a diff that names any drift.

Two things must be captured, not one:

* **values** -- everything the runner writes into the raw blocks, the config
  panel and the labels; and
* **statuses** -- OK / WATCH / ALERT, which are *formula-driven* (contract
  section 2: dashboards are formula panels, no native charts). A raw-cell
  snapshot would read the formula text and miss a status that silently moved,
  which is exactly the failure carried lesson L8 describes. So every formula
  cell is recomputed with the ``formulas`` engine and the *computed* value is
  what the golden stores.

The golden is therefore a flat, ordered map::

    "Sheet!A1": [value]              # literal cell
    "Sheet!A4": [computed, formula]  # formula cell: value first, then source

serialised one cell per line so a git diff of a golden reads as a list of
changed cells.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import os
import shutil
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA = "credit-suite/parity-golden@1"

#: Stored in place of a formula cell the recalc engine did not produce a value
#: for. It is deliberately shaped like an Excel error so it can never be
#: mistaken for real content, and so a golden full of them is obvious.
UNCOMPUTED = "#UNCOMPUTED!"

#: Excel functions the ``formulas`` engine does not implement. A cell using one
#: resolves to ``#NAME?`` in the golden where real Excel would show a value.
#: That costs parity nothing -- the result is deterministic, so it is identical
#: on both sides of a comparison, and the cell's *formula text* is compared too,
#: so a changed URL inside a HYPERLINK is still caught. What must not happen is
#: this list growing silently, so ``unevaluated()`` exists to check it.
UNSUPPORTED_FUNCTIONS: tuple[str, ...] = ("HYPERLINK",)

#: What a formula cell resolving to one of these means: no value was pinned.
EXCEL_ERRORS: frozenset[str] = frozenset({
    UNCOMPUTED, "#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!",
    "#N/A", "#GETTING_DATA",
})

#: The M1 spine: the two monitors whose current behaviour is the parity
#: baseline. Paths are relative to the repo root.
#:
#: Two goldens per monitor, because the shipped ``.xlsm`` is an *unpopulated*
#: template -- built, never run. It pins the template shape (formulas, config,
#: labels, defined names); it cannot pin a status, because every raw block in it
#: is empty. So the demo golden -- the same monitor built and run ``--demo`` at
#: a fixed ``--asof`` -- is what actually pins values and statuses, and it is
#: the one a migrated monitor must reproduce cell for cell.
SPINE_BASELINES: dict[str, dict[str, str]] = {
    "fdic": {
        "workbook": "fdic-peer-monitor/Bank_Peer_Monitor.xlsm",
        "shipped_golden": "credit-suite/tests/goldens/fdic-shipped.json",
        "demo_golden": "credit-suite/tests/goldens/fdic-demo.json",
        "asof": "2026-03-31",
    },
    "fred": {
        "workbook": "fred-credit-risk-dashboard/FRED_Credit_Risk_Dashboard.xlsm",
        "shipped_golden": "credit-suite/tests/goldens/fred-shipped.json",
        "demo_golden": "credit-suite/tests/goldens/fred-demo.json",
        "asof": "2026-03-01",
    },
}

#: The one tab a migrated monitor is *expected* to change: ``_code_py`` carries
#: the runner source, and after consolidation that source is the inlined engine
#: rather than a hand-copied per-monitor runner (contract section 11). Parity is
#: about the numbers and statuses a reviewer reads, so this tab -- and only this
#: tab -- is excluded when a migrated build is checked against a legacy golden.
#: ``_readme`` and ``_code_vba`` are NOT excluded: those the migration must keep.
MIGRATION_IGNORE: tuple[str, ...] = ("_code_py!*",)


def repo_root(start: Path | None = None) -> Path:
    """The SATC monorepo root -- the directory holding ``TEMPLATE_CONTRACT.md``."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "TEMPLATE_CONTRACT.md").is_file():
            return candidate
    raise RuntimeError(f"no repo root (TEMPLATE_CONTRACT.md) above {here}")


# --------------------------------------------------------------------------
# value normalisation
# --------------------------------------------------------------------------

def _round(value: float) -> Any:
    """12 significant digits -- below Excel's 15, above float-repr noise.

    Significant digits, not decimal places: raw Call Report figures run to the
    billions and percentages to the units, and both must survive the round trip
    between what openpyxl read and what the recalc engine computed.
    """
    if value != value or value in (float("inf"), float("-inf")):
        return str(value)
    out = float(f"{value:.12g}")
    return 0.0 if out == 0 else out


def normalise(value: Any) -> Any:
    """Any cell value -> a JSON-stable scalar."""
    if value is None:
        return None
    # Subclasses are coerced to the plain builtin: the recalc engine hands back
    # str subclasses for Excel errors, and a golden must hold JSON types only --
    # otherwise ``"#NAME?" in EXCEL_ERRORS`` depends on whose __eq__ runs.
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return _round(float(value))
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    # numpy scalars and anything else the recalc engine hands back
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return normalise(item())
        except (ValueError, TypeError):
            pass
    return str(value)


def _formula_text(value: Any) -> str | None:
    """The formula source of a cell, or ``None`` if it holds a literal."""
    text = getattr(value, "text", None)  # openpyxl ArrayFormula
    if isinstance(text, str) and text.startswith("="):
        return text
    if isinstance(value, str) and value.startswith("="):
        return value
    return None


# --------------------------------------------------------------------------
# recalc
# --------------------------------------------------------------------------

def _unwrap(cell: Any) -> Any:
    """A ``formulas`` solution entry -> a scalar."""
    value = getattr(cell, "value", cell)
    if getattr(value, "shape", None) is not None:
        if value.size == 0:
            return None
        value = value.ravel()[0]
    # the engine's Empty singleton means "blank cell"
    if type(value).__name__ == "Empty":
        return ""
    return normalise(value)


def recalc(path: str | os.PathLike[str]) -> dict[tuple[str, str], Any]:
    """Evaluate a workbook's formulas -> ``{(SHEET_UPPER, 'A1'): value}``.

    The workbook is copied to a fixed temp name first: ``formulas`` embeds the
    file name in every solution key, and parity must not depend on where the
    file happened to live.
    """
    import formulas  # imported lazily: only parity capture needs the engine

    tmpdir = tempfile.mkdtemp(prefix="credit-suite-parity-")
    try:
        staged = Path(tmpdir) / ("wb" + Path(path).suffix.lower())
        shutil.copyfile(path, staged)
        solution = formulas.ExcelModel().loads(str(staged)).finish().calculate()

        # the engine's key case follows the file name, so compare upper-cased
        prefix = "'[%s]" % staged.name.upper()
        out: dict[tuple[str, str], Any] = {}
        for key, cell in solution.items():
            key = key.upper()
            if not key.startswith(prefix) or "'!" not in key:
                continue
            sheet, _, coord = key[len(prefix):].partition("'!")
            if "!" in coord or ":" in coord or not coord:
                continue  # a range key, not a single cell
            out[(sheet, coord)] = _unwrap(cell)
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------
# snapshot
# --------------------------------------------------------------------------

def snapshot_workbook(
    path: str | os.PathLike[str],
    *,
    source: str | None = None,
    recompute: bool = True,
) -> dict[str, Any]:
    """Capture every populated cell of a workbook, statuses recomputed.

    ``recompute=False`` stores formula text with a ``None`` value -- only for
    the harness's own fast unit tests; a golden is always captured with the
    recalc on, because a status that moved is the drift worth catching.
    """
    import openpyxl

    path = Path(path)
    computed = recalc(path) if recompute else {}

    wb = openpyxl.load_workbook(path, keep_vba=path.suffix.lower() == ".xlsm")
    try:
        sheets = [ws.title for ws in wb.worksheets]
        upper = [s.upper() for s in sheets]
        if len(set(upper)) != len(upper):
            raise ValueError(
                "%s: sheet names collide when upper-cased, so recalc keys are "
                "ambiguous: %s" % (path.name, sheets)
            )

        cells: dict[str, Any] = {}
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    raw = cell.value
                    if raw is None:
                        continue
                    formula = _formula_text(raw)
                    key = "%s!%s" % (ws.title, cell.coordinate)
                    if formula is None:
                        cells[key] = [normalise(raw)]
                    elif not recompute:
                        cells[key] = [None, formula]
                    else:
                        value = computed.get(
                            (ws.title.upper(), cell.coordinate.upper()), UNCOMPUTED
                        )
                        cells[key] = [value, formula]

        defined = {
            name: normalise(getattr(dn, "value", dn))
            for name, dn in sorted(wb.defined_names.items())
        }
    finally:
        wb.close()

    return {
        "schema": SCHEMA,
        "source": source if source is not None else path.name,
        "recomputed": bool(recompute),
        "sheets": sheets,
        "defined_names": defined,
        "cells": cells,
    }


# --------------------------------------------------------------------------
# serialisation -- one cell per line, so a golden's git diff is readable
# --------------------------------------------------------------------------

def _compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(", ", ": "), allow_nan=False)


def dumps(snapshot: dict[str, Any]) -> str:
    """Deterministic text for a snapshot. No clock, no host, no dict-order luck."""
    lines = [
        "{",
        '  "schema": %s,' % _compact(snapshot["schema"]),
        '  "source": %s,' % _compact(snapshot["source"]),
        '  "recomputed": %s,' % _compact(snapshot["recomputed"]),
        '  "sheets": %s,' % _compact(snapshot["sheets"]),
        '  "defined_names": %s,' % _compact(snapshot["defined_names"]),
        '  "cells": {',
    ]
    items = list(snapshot["cells"].items())
    for index, (key, payload) in enumerate(items):
        comma = "" if index == len(items) - 1 else ","
        lines.append("    %s: %s%s" % (_compact(key), _compact(payload), comma))
    lines += ["  }", "}", ""]
    return "\n".join(lines)


def loads(text: str) -> dict[str, Any]:
    snapshot = json.loads(text)
    if snapshot.get("schema") != SCHEMA:
        raise ValueError("not a %s golden: schema=%r" % (SCHEMA, snapshot.get("schema")))
    return snapshot


def write_golden(path: str | os.PathLike[str], snapshot: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        handle.write(dumps(snapshot))
    return path


def read_golden(path: str | os.PathLike[str]) -> dict[str, Any]:
    return loads(Path(path).read_text(encoding="ascii"))


# --------------------------------------------------------------------------
# diff
# --------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Difference:
    """One named drift between a golden and a rebuilt workbook."""

    kind: str
    key: str
    expected: Any
    actual: Any

    def __str__(self) -> str:
        return "%s %s: expected %r, got %r" % (self.kind, self.key,
                                               self.expected, self.actual)


def _ignored(key: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)


def _cell_order(sheets: Sequence[str], key: str) -> tuple:
    """Sort diffs the way the workbook reads: sheet order, then row, then column."""
    sheet, _, coord = key.partition("!")
    index = sheets.index(sheet) if sheet in sheets else len(sheets)
    column = 0
    for ch in coord:
        if ch.isalpha():
            column = column * 26 + (ord(ch.upper()) - ord("A") + 1)
    row = int("".join(ch for ch in coord if ch.isdigit()) or 0)
    return (index, row, column, key)


def diff_snapshots(
    golden: dict[str, Any],
    current: dict[str, Any],
    *,
    ignore: Iterable[str] = (),
) -> list[Difference]:
    """Every value, status, formula, sheet and defined-name drift, named.

    ``ignore`` takes ``fnmatch`` patterns over ``Sheet!A1`` keys, for the cells
    a rebuild is *expected* to move -- the run timestamp in a status panel.
    Nothing else is forgiven.
    """
    patterns = list(ignore)
    diffs: list[Difference] = []

    golden_sheets = list(golden["sheets"])
    current_sheets = list(current["sheets"])
    if golden_sheets != current_sheets:
        missing = [s for s in golden_sheets if s not in current_sheets]
        extra = [s for s in current_sheets if s not in golden_sheets]
        for sheet in missing:
            diffs.append(Difference("sheet_removed", sheet, "present", "absent"))
        for sheet in extra:
            diffs.append(Difference("sheet_added", sheet, "absent", "present"))
        if not missing and not extra:
            diffs.append(Difference("sheet_order", "<workbook>",
                                    golden_sheets, current_sheets))

    for name in sorted(set(golden["defined_names"]) | set(current["defined_names"])):
        want = golden["defined_names"].get(name, "<absent>")
        got = current["defined_names"].get(name, "<absent>")
        if want != got:
            diffs.append(Difference("defined_name", name, want, got))

    golden_cells = golden["cells"]
    current_cells = current["cells"]
    order_sheets = golden_sheets + [s for s in current_sheets if s not in golden_sheets]
    for key in sorted(set(golden_cells) | set(current_cells),
                      key=lambda k: _cell_order(order_sheets, k)):
        if _ignored(key, patterns):
            continue
        want = golden_cells.get(key)
        got = current_cells.get(key)
        if want == got:
            continue
        if want is None:
            diffs.append(Difference("cell_added", key, "<empty>", got[0]))
        elif got is None:
            diffs.append(Difference("cell_removed", key, want[0], "<empty>"))
        else:
            if want[0] != got[0]:
                diffs.append(Difference("value", key, want[0], got[0]))
            want_formula = want[1] if len(want) > 1 else None
            got_formula = got[1] if len(got) > 1 else None
            if want_formula != got_formula:
                diffs.append(Difference("formula", key, want_formula, got_formula))
    return diffs


def unevaluated(snapshot: dict[str, Any]) -> dict[str, str]:
    """Formula cells the recalc engine could not resolve -> their formula text.

    An entry here is a hole in what the golden pins by *value*. A few are
    expected (see :data:`UNSUPPORTED_FUNCTIONS`); anything else means a formula
    stopped evaluating and should be looked at rather than shrugged off.
    """
    holes: dict[str, str] = {}
    for key, payload in snapshot["cells"].items():
        if len(payload) < 2:
            continue
        if payload[0] in EXCEL_ERRORS:
            holes[key] = payload[1]
    return holes


def describe(diffs: Sequence[Difference], limit: int = 25) -> str:
    if not diffs:
        return "no differences"
    head = "\n".join("  - %s" % d for d in diffs[:limit])
    tail = "" if len(diffs) <= limit else "\n  ... and %d more" % (len(diffs) - limit)
    return "%d difference(s):\n%s%s" % (len(diffs), head, tail)


def assert_parity(
    golden_path: str | os.PathLike[str],
    workbook: str | os.PathLike[str],
    *,
    ignore: Iterable[str] = (),
) -> None:
    """Raise unless ``workbook`` reproduces ``golden_path`` cell for cell."""
    golden = read_golden(golden_path)
    current = snapshot_workbook(workbook, source=golden["source"])
    diffs = diff_snapshots(golden, current, ignore=ignore)
    if diffs:
        raise AssertionError(
            "%s does not match %s\n%s"
            % (Path(workbook).name, Path(golden_path).name, describe(diffs))
        )
