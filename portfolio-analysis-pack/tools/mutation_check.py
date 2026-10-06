#!/usr/bin/env python3
"""Check the checker: every guard in the suite must be able to go red.

A test that stays green when the code it covers is broken is decoration, and
a check-tab that says "agree" whatever Python computed is worse than none.
So each mutation below edits exactly one behaviour in the working tree, names
the tests that must fail because of it, runs them, and puts the file back
byte for byte in a ``finally``. The run demands a green baseline first.

    python tools/mutation_check.py            # every mutation
    python tools/mutation_check.py mh-swap    # just one
    python tools/mutation_check.py --list

Prior art: credit-suite/tools/mutation_check.py. Exit 0 when every mutation
was caught by its named tests, 2 when one survived (the tests stayed green
against broken code), 1 when the baseline itself is red.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRC = PKG / "src" / "analysis_pack"


@dataclasses.dataclass(frozen=True)
class Mutation:
    id: str
    path: Path
    old: str
    new: str
    must_fail: tuple[str, ...]
    kills: str


G = "tests/test_gradient.py::"
S3 = "tests/test_slice3.py::"
S4 = "tests/test_slice4.py::"
S5 = "tests/test_slice5.py::"
S9 = "tests/test_slice9.py::"
CLI = "tests/test_cli.py::"
GU = "tests/test_guards.py::"

MUTATIONS: list[Mutation] = [
    Mutation(
        "wilson-z-one", SRC / "stats.py",
        "    return norm_s_inv(1.0 - (1.0 - confidence) / 2.0)",
        "    return 1.0",
        (G + "test_every_check_row_agrees_and_the_cover_counts_them",),
        "Python's z is the same quantile Excel's NORM.S.INV gives; the check tab compares them",
    ),
    Mutation(
        "cp-alpha", SRC / "stats.py",
        "    alpha = 1.0 - confidence\n    lo = 0.0 if events == 0 else beta_inv(alpha / 2.0, events, n - events + 1)",
        "    alpha = confidence\n    lo = 0.0 if events == 0 else beta_inv(alpha / 2.0, events, n - events + 1)",
        (S3 + "test_switching_the_method_moves_the_prevalence_intervals_and_the_checks_still_agree",),
        "the Clopper-Pearson twin uses the same tail as the BETA.INV formula",
    ),
    Mutation(
        "mh-swap", SRC / "stats.py",
        "    o = R / S\n    var = PR",
        "    o = S / R\n    var = PR",
        (S4 + "test_the_confounded_book_collapses_on_the_confounder_and_only_there",),
        "the pooled odds ratio is sum(ad/n) over sum(bc/n), the same way round as the sheet",
    ),
    Mutation(
        "seasoning-off", SRC / "population.py",
        "        seasoned = mob >= cfg.window_months",
        "        seasoned = True",
        (G + "test_a_23_month_loan_is_unseasoned_at_a_24_month_window",
         S3 + "test_the_23_month_loan_is_in_its_quarters_unseasoned_count"),
        "a loan younger than the window enters no rate",
    ),
    Mutation(
        "leakage-allowed", SRC / "config.py",
        "        if f.known == \"later\" and col in non_outcome_slots:",
        "        if False:",
        (CLI + "test_a_later_column_used_as_a_control_is_refused_naming_the_column",),
        "a column known only after origination is refused anywhere but the outcome",
    ),
    Mutation(
        "fires-inverted", SRC / "population.py",
        "            fires = compare(cfg.rule.fires_op, rv, cfg.rule.fires_value)",
        "            fires = not compare(cfg.rule.fires_op, rv, cfg.rule.fires_value)",
        (G + "test_the_planted_odds_ratio_is_visible_in_the_flagged_versus_base_rates",),
        "the flag fires on the side of the line the question file names",
    ),
    Mutation(
        "xlfn-prefix-dropped", SRC / "workbook.py",
        'CP_LO = "IF({X}=0,0,_xlfn.BETA.INV((1-CONF)/2,{X},{N}-{X}+1))"',
        'CP_LO = "IF({X}=0,0,BETA.INV((1-CONF)/2,{X},{N}-{X}+1))"',
        (GU + "test_every_newer_function_in_a_written_formula_carries_the_xlfn_prefix",),
        "a newer Excel function is written with the prefix Excel needs (the engine accepts both, so only the guard sees it)",
    ),
    Mutation(
        "check-tolerance-huge", SRC / "workbook.py",
        "TOL_INTERVAL = 1e-6      # absolute: BETA.INV differs a little between engines",
        "TOL_INTERVAL = 1e6       # absolute: BETA.INV differs a little between engines",
        (S9 + "test_every_check_row_tolerance_is_tight",),
        "the check tab cannot be made to agree by widening its tolerance",
    ),
    Mutation(
        "sort-off", SRC / "ladder.py",
        "        rows.sort(key=lambda r: (-r.flagged.events, r.label))",
        "        pass",
        (S5 + "test_a_level_holding_every_flagged_event_is_the_first_row_with_share_one",),
        "decomposition rows are sorted most-flagged-events first, so concentration reads off the top",
    ),
]


def _run(tests: tuple[str, ...]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(PKG / "src"), str(PKG / "tests"), env.get("PYTHONPATH", "")) if p)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                          cwd=PKG, capture_output=True, text=True, env=env, timeout=1800)


def apply(m: Mutation) -> bytes:
    original = m.path.read_bytes()
    text = original.decode("utf-8")
    if text.count(m.old) != 1:
        raise SystemExit(f"{m.id}: the anchor text occurs {text.count(m.old)} times in {m.path.name}; the mutation is stale")
    m.path.write_text(text.replace(m.old, m.new), encoding="utf-8")
    return original


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="mutation ids to run (default: all)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    chosen = [m for m in MUTATIONS if not a.only or m.id in a.only]
    if a.list:
        for m in MUTATIONS:
            print(f"{m.id:22s} {m.path.name:16s} kills: {m.kills}")
        return 0
    all_tests = tuple(sorted({t for m in chosen for t in m.must_fail}))
    print(f"baseline: {len(all_tests)} named tests must be green before any mutation")
    base = _run(all_tests)
    if base.returncode != 0:
        print(base.stdout[-3000:])
        print("BASELINE RED — fix the suite before checking the checker")
        return 1
    print("baseline green")
    survived = []
    for m in chosen:
        original = apply(m)
        try:
            r = _run(m.must_fail)
        finally:
            m.path.write_bytes(original)
            assert m.path.read_bytes() == original, f"{m.path} was not restored"
        caught = r.returncode != 0
        print(f"{'caught  ' if caught else 'SURVIVED'} {m.id:22s} ({len(m.must_fail)} test{'s' if len(m.must_fail) != 1 else ''}) — {m.kills}")
        if not caught:
            survived.append(m.id)
    print(f"\n{len(chosen) - len(survived)} of {len(chosen)} mutations caught by their named tests")
    if survived:
        print("SURVIVED: " + ", ".join(survived) + " — a test that stays green against broken code is validating nothing")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
