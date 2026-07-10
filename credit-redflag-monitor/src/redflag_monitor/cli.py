"""Command-line entry point for the monthly run.

    python redflag_monitor.py            # live FRED run (needs FRED_API_KEY)
    python redflag_monitor.py --demo     # offline synthetic run, no key needed
"""

from __future__ import annotations

import argparse
import sys

from redflag_monitor.monitor import (
    DEFAULT_HISTORY,
    DEFAULT_WORKBOOK,
    build_fetcher,
    resolve_signals,
    run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redflag-monitor",
        description="Consumer Credit Red-Flag Monitor (External Signals v1).",
    )
    parser.add_argument(
        "--workbook", default=DEFAULT_WORKBOOK,
        help=f"Output workbook path (default: {DEFAULT_WORKBOOK})",
    )
    parser.add_argument(
        "--history", default=DEFAULT_HISTORY,
        help=f"History CSV path (default: {DEFAULT_HISTORY})",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Use deterministic synthetic data (no FRED_API_KEY / network needed).",
    )
    parser.add_argument(
        "--run-date", default=None,
        help="Override the run date (ISO YYYY-MM-DD); defaults to today.",
    )
    parser.add_argument(
        "--no-news", action="store_true",
        help="Omit the optional News (manual) stub sheet.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        signals = resolve_signals(args.workbook)
        fetcher = build_fetcher(demo=args.demo, signals=signals)
    except Exception as exc:  # noqa: BLE001 - clean message for setup errors
        print(f"error: {exc}", file=sys.stderr)
        return 2

    summary = run(
        fetcher,
        workbook_path=args.workbook,
        history_path=args.history,
        run_date=args.run_date,
        include_news=not args.no_news,
    )

    print(f"Wrote {summary.workbook}")
    print(f"  signals evaluated : {summary.n_signals}")
    print(f"  auto-flagged      : {summary.n_flagged}")
    if summary.flagged_labels:
        for label in summary.flagged_labels:
            print(f"      - {label}")
    if summary.n_errors:
        print(f"  fetch errors      : {summary.n_errors}")
    print(f"  history log       : {summary.history}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
