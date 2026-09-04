#!/usr/bin/env python3
"""Does this monitor still produce the numbers it produced before consolidation?

The red/green light for the whole migration. Build the monitor, run it
``--demo`` at the fixed as-of date the golden was captured at, recompute every
formula, and diff cell for cell against ``tests/goldens/<name>-demo.json``.

    python tools/check_parity.py              # every spine monitor
    python tools/check_parity.py fdic         # one
    python tools/check_parity.py fdic --strict  # do not forgive _code_py either

``_code_py`` is forgiven by default and nothing else is. That tab carries the
runner source, and after consolidation the source it carries is the inlined
engine rather than a hand-copied per-monitor runner -- an expected, required
change. Values, statuses, formulas, config, provenance, readme and the macro are
all held to the letter.

Exit 0 when every monitor matches, 2 when one does not -- a parity difference is
a gate error, not a crash.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from credit_suite import parity  # noqa: E402
import monitorbuild  # noqa: E402


def check(name: str, strict: bool = False, limit: int = 25) -> bool:
    spec = parity.SPINE_BASELINES[name]
    root = parity.repo_root()
    golden_path = root / spec["demo_golden"]
    ignore = () if strict else parity.MIGRATION_IGNORE

    print("== %s ==" % name)
    print("   golden: %s" % spec["demo_golden"])
    print("   forgiving: %s" % (", ".join(ignore) if ignore else "nothing (--strict)"))

    try:
        with monitorbuild.built_monitor(name, root) as (workbook, stdout):
            current = parity.snapshot_workbook(workbook, source=spec["workbook"])
    except monitorbuild.BuildFailed as exc:
        print("   BUILD FAILED -- parity cannot be judged")
        print("   " + str(exc).replace("\n", "\n   "))
        return False

    golden = parity.read_golden(golden_path)
    diffs = parity.diff_snapshots(golden, current, ignore=ignore)

    # Report the denominator: a green result from a check that compared nothing
    # is worse than a red one.
    compared = len(set(golden["cells"]) | set(current["cells"]))
    forgiven = sum(1 for key in set(golden["cells"]) | set(current["cells"])
                   if ignore and parity._ignored(key, list(ignore)))
    print("   compared %d cells (%d forgiven), %d sheets, %d defined names"
          % (compared - forgiven, forgiven, len(current["sheets"]),
             len(current["defined_names"])))

    if not diffs:
        print("   PARITY OK")
        return True
    print("   PARITY BROKEN")
    print("   " + parity.describe(diffs, limit=limit).replace("\n", "\n   "))
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("monitors", nargs="*", choices=[*parity.SPINE_BASELINES, []])
    ap.add_argument("--strict", action="store_true",
                    help="hold _code_py to the golden as well")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args(argv)

    names = args.monitors or list(parity.SPINE_BASELINES)
    results = {n: check(n, args.strict, args.limit) for n in names}

    print()
    ok = sum(results.values())
    print("%d/%d monitor(s) at parity" % (ok, len(results)))
    broken = [n for n, good in results.items() if not good]
    if broken:
        print("BROKEN: %s" % ", ".join(broken))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
