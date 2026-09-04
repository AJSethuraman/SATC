"""Command-line front door.

``credit-suite parity capture <workbook> -o <golden.json>``
``credit-suite parity capture --spine``     -> recapture the FDIC + FRED baselines
``credit-suite parity diff <golden.json> <workbook>``

Exit codes follow the runner contract (TEMPLATE_CONTRACT section 4):
0 OK, 1 run error, 2 gate error. A parity difference is a gate error -- a
number headed for KeyBank moved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from credit_suite import parity


def _cmd_parity_capture(args: argparse.Namespace) -> int:
    if args.spine:
        root = parity.repo_root()
        for name, spec in parity.SPINE_BASELINES.items():
            workbook = root / spec["workbook"]
            snapshot = parity.snapshot_workbook(workbook, source=spec["workbook"])
            out = parity.write_golden(root / spec["golden"], snapshot)
            print("%s: %d cells -> %s" % (name, len(snapshot["cells"]), out))
        return 0

    if not args.workbook:
        print("parity capture: give a workbook, or --spine", file=sys.stderr)
        return 1
    snapshot = parity.snapshot_workbook(args.workbook, source=args.source)
    if args.output:
        out = parity.write_golden(args.output, snapshot)
        print("%d cells -> %s" % (len(snapshot["cells"]), out))
    else:
        sys.stdout.write(parity.dumps(snapshot))
    return 0


def _cmd_parity_diff(args: argparse.Namespace) -> int:
    golden = parity.read_golden(args.golden)
    current = parity.snapshot_workbook(args.workbook, source=golden["source"])
    diffs = parity.diff_snapshots(golden, current, ignore=args.ignore or ())
    if not diffs:
        print("parity OK: %s matches %s"
              % (Path(args.workbook).name, Path(args.golden).name))
        return 0
    print(parity.describe(diffs, limit=args.limit), file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="credit-suite", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    par = sub.add_parser("parity", help="output-parity goldens for the spine")
    par_sub = par.add_subparsers(dest="parity_command", required=True)

    cap = par_sub.add_parser("capture", help="snapshot a workbook into a golden")
    cap.add_argument("workbook", nargs="?")
    cap.add_argument("-o", "--output", help="golden file to write (default: stdout)")
    cap.add_argument("--source", help="label stored in the golden (default: file name)")
    cap.add_argument("--spine", action="store_true",
                     help="recapture the committed FDIC + FRED baselines")
    cap.set_defaults(func=_cmd_parity_capture)

    dif = par_sub.add_parser("diff", help="diff a workbook against a golden")
    dif.add_argument("golden")
    dif.add_argument("workbook")
    dif.add_argument("--ignore", action="append", metavar="PATTERN",
                     help="fnmatch pattern over Sheet!A1 keys; repeatable")
    dif.add_argument("--limit", type=int, default=25)
    dif.set_defaults(func=_cmd_parity_diff)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
