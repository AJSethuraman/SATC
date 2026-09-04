#!/usr/bin/env python3
"""Mutation proof: every parity test must be able to fail.

A test that stays green when the code it covers is broken is not a test, it is
decoration -- and a *parity* test that cannot fail is worse than none, because
the whole point of the golden harness is to be the thing that says "a number
moved". So each mutation below deletes or neuters exactly one behaviour and
names the tests that must go red because of it.

    python tools/mutation_check.py            # every mutation
    python tools/mutation_check.py recalc-off # just one
    python tools/mutation_check.py --list

A mutation is applied to the working tree and undone in a ``finally``; the run
starts by demanding a green baseline and ends by re-checking the file is back
byte-for-byte as it was.
"""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRC = PKG / "src" / "credit_suite"
GOLDENS = PKG / "tests" / "goldens"


@dataclasses.dataclass(frozen=True)
class Mutation:
    id: str
    path: Path
    old: str
    new: str
    must_fail: tuple[str, ...]
    kills: str
    count: int = 1


T = "tests/test_parity.py::"

MUTATIONS: list[Mutation] = [
    Mutation(
        "recalc-off", SRC / "parity.py",
        "computed = recalc(path) if recompute else {}",
        "computed = {}",
        (T + "test_snapshot_stores_the_computed_status_not_the_formula_text",
         T + "test_a_planted_status_change_is_detected_and_named",
         T + "test_a_band_that_turns_from_number_to_text_is_caught_as_a_status_move",
         T + "test_shipped_golden_matches_the_committed_workbook"),
        "statuses are recomputed rather than read as formula text",
    ),
    Mutation(
        "formula-text-blind", SRC / "parity.py",
        '    if isinstance(value, str) and value.startswith("="):\n        return value\n',
        '    if False:\n        return value\n',
        (T + "test_snapshot_stores_the_computed_status_not_the_formula_text",
         T + "test_a_rewritten_formula_is_detected_even_when_the_value_holds",
         T + "test_shipped_golden_matches_the_committed_workbook"),
        "a formula cell is recorded as a formula, not as a literal string",
    ),
    Mutation(
        "value-diff-blind", SRC / "parity.py",
        "            if want[0] != got[0]:",
        "            if False:",
        (T + "test_a_planted_value_change_is_detected_and_named",
         T + "test_a_planted_status_change_is_detected_and_named",
         T + "test_assert_parity_raises_naming_the_cell",
         T + "test_a_band_that_turns_from_number_to_text_is_caught_as_a_status_move"),
        "a moved value or status is reported",
    ),
    Mutation(
        "formula-diff-blind", SRC / "parity.py",
        "            if want_formula != got_formula:",
        "            if False:",
        (T + "test_a_rewritten_formula_is_detected_even_when_the_value_holds",
         T + "test_a_formula_the_engine_cannot_run_is_still_pinned_by_its_source"),
        "a rewritten rule is reported even when its answer holds",
    ),
    Mutation(
        "sheet-diff-blind", SRC / "parity.py",
        'diffs.append(Difference("sheet_removed", sheet, "present", "absent"))',
        "pass",
        (T + "test_a_dropped_tab_is_named",),
        "a tab that vanished is reported",
    ),
    Mutation(
        "defined-name-diff-blind", SRC / "parity.py",
        "        if want != got:\n            diffs.append(Difference(\"defined_name\"",
        "        if False:\n            diffs.append(Difference(\"defined_name\"",
        (T + "test_a_moved_defined_name_is_named",),
        "a threshold band that was re-pointed is reported (L8 territory)",
    ),
    Mutation(
        "ignore-everything", SRC / "parity.py",
        "return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)",
        "return True",
        (T + "test_ignore_forgives_the_named_cell_and_nothing_else",
         T + "test_a_planted_value_change_is_detected_and_named"),
        "--ignore forgives only the cells it names",
    ),
    Mutation(
        "ignore-nothing", SRC / "parity.py",
        "return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)",
        "return False",
        (T + "test_ignore_forgives_the_named_cell_and_nothing_else",),
        "--ignore forgives the cells it names",
    ),
    Mutation(
        "rounding-off", SRC / "parity.py",
        'out = float(f"{value:.12g}")',
        "out = value",
        (T + "test_float_noise_normalises_away_but_a_real_move_does_not",),
        "float noise between openpyxl and the recalc engine is normalised away",
    ),
    Mutation(
        "rounding-too-coarse", SRC / "parity.py",
        'out = float(f"{value:.12g}")',
        'out = float(f"{value:.3g}")',
        (T + "test_float_noise_normalises_away_but_a_real_move_does_not",),
        "rounding is not so coarse that a real move disappears",
    ),
    Mutation(
        "diff-order-alphabetical", SRC / "parity.py",
        "    return (index, row, column, key)",
        "    return (key,)",
        (T + "test_differences_are_reported_in_workbook_reading_order",),
        "differences are listed in the order the workbook reads",
    ),
    Mutation(
        "golden-not-ascii", SRC / "parity.py",
        "ensure_ascii=True",
        "ensure_ascii=False",
        (T + "test_dumps_is_ascii_and_one_cell_per_line_even_for_unicode_content",),
        "the golden is pure ASCII (contract section 11)",
    ),
    Mutation(
        "golden-carries-a-clock", SRC / "parity.py",
        '        \'  "source": %s,\' % _compact(snapshot["source"]),',
        '        \'  "source": %s,\' % _compact(str(__import__("time").time())),',
        (T + "test_snapshot_of_an_unchanged_workbook_is_byte_identical_twice",),
        "a golden carries no clock or host noise",
    ),
    Mutation(
        "capture-order-scrambled", SRC / "parity.py",
        "        for ws in wb.worksheets:\n            for row in ws.iter_rows():",
        "        for ws in reversed(wb.worksheets):\n            for row in reversed(list(ws.iter_rows())):",
        (T + "test_cells_are_ordered_by_sheet_then_row_then_column",),
        "cells are captured in workbook order, not whatever order they came in",
    ),
    # --- the baselines themselves: tamper with the committed data ------------
    Mutation(
        "golden-tampered-value", GOLDENS / "fdic-shipped.json",
        '"Dashboard_AssetQuality!A1": ["Asset Quality Dashboard"]',
        '"Dashboard_AssetQuality!A1": ["Asset Quality Dashbord"]',
        (T + "test_shipped_golden_matches_the_committed_workbook",),
        "the committed baseline still describes the real shipped workbook",
    ),
    Mutation(
        "golden-flags-blanked", GOLDENS / "fred-demo.json",
        '["\\u26a0 ALERT", ', '["", ',
        (T + "test_demo_golden_is_populated_and_its_flags_discriminate",),
        "the demo baseline is not vacuous -- a flag is actually lit in it",
        count=19,
    ),
    Mutation(
        "golden-hides-an-unpinned-cell", GOLDENS / "fdic-demo.json",
        '"Dashboard_AssetQuality!A4": [2, ',
        '"Dashboard_AssetQuality!A4": ["#DIV/0!", ',
        (T + "test_every_unpinned_formula_is_one_the_engine_documents_it_cannot_run",),
        "a formula that stopped resolving is named, not shrugged at",
    ),
]


#: Extra pytest arguments (``--basetemp=...`` on a machine whose default temp
#: root is not writable). Set by ``main`` from the command line.
_EXTRA_ARGS: list[str] = []


def _pytest(node_ids: tuple[str, ...]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
         *_EXTRA_ARGS, *node_ids],
        cwd=PKG, capture_output=True, text=True,
    )


def _apply(mutation: Mutation) -> bytes:
    """Swap the target text in, byte for byte, and hand back the original bytes."""
    original = mutation.path.read_bytes()
    old = mutation.old.encode("utf-8")
    found = original.count(old)
    if found != mutation.count:
        raise SystemExit(
            "%s: expected %d occurrence(s) of the mutation target in %s, found %d "
            "-- the code moved, so the mutation no longer proves anything"
            % (mutation.id, mutation.count, mutation.path.name, found)
        )
    mutation.path.write_bytes(original.replace(old, mutation.new.encode("utf-8")))
    return original


def check(mutation: Mutation) -> tuple[bool, str]:
    original = _apply(mutation)
    try:
        result = _pytest(mutation.must_fail)
    finally:
        mutation.path.write_bytes(original)
        assert mutation.path.read_bytes() == original, \
            "failed to restore %s" % mutation.path

    if result.returncode == 0:
        tail = result.stdout.strip().splitlines()[-1:] or [""]
        return False, "SURVIVED -- tests stayed green: %s" % tail[0]
    summary = [ln for ln in result.stdout.splitlines() if "failed" in ln or "error" in ln]
    return True, summary[-1].strip() if summary else "killed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="mutation ids (default: all)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true",
                    help="do not run the full suite first (faster, less safe)")
    ap.add_argument("--basetemp", help="passed through to pytest")
    args = ap.parse_args(argv)

    if args.basetemp:
        _EXTRA_ARGS.append("--basetemp=%s" % args.basetemp)

    by_id = {m.id: m for m in MUTATIONS}
    if args.list:
        for m in MUTATIONS:
            print("%-32s %s" % (m.id, m.kills))
        return 0

    unknown = [i for i in args.ids if i not in by_id]
    if unknown:
        raise SystemExit("unknown mutation id(s): %s" % ", ".join(unknown))
    selected = [by_id[i] for i in args.ids] if args.ids else MUTATIONS

    if not args.skip_baseline:
        print("baseline: running the full suite unmutated ...")
        result = _pytest(())
        if result.returncode != 0:
            print(result.stdout[-4000:])
            raise SystemExit("baseline is not green; fix that before mutating")
        print("  " + (result.stdout.strip().splitlines() or [""])[-1])

    survived = []
    for mutation in selected:
        killed, detail = check(mutation)
        print("%-4s %-32s %s" % ("kill" if killed else "LIVE", mutation.id, detail))
        print("       proves: %s" % mutation.kills)
        if not killed:
            survived.append(mutation.id)

    print("\n%d/%d mutations killed" % (len(selected) - len(survived), len(selected)))
    if survived:
        print("SURVIVING: %s" % ", ".join(survived))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
