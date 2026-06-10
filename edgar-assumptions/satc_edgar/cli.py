"""Command-line interface for the EDGAR Industry Assumption-Set Tool."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .aggregate import DEFAULT_TIERS, parse_tiers
from .fetch import EdgarClient
from .pipeline import discover_universe, run_for_sic, write_outputs
from .selftest import run_self_test

DEFAULT_USER_AGENT = "SATC EDGAR assumption tool (set --user-agent with your contact email)"


def _make_logger(quiet: bool):
    def log(msg: str) -> None:
        if not quiet:
            print(msg, file=sys.stderr)
    return log


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="edgar_assumptions",
        description=(
            "Derive credit-relevant industry benchmark RANGES from SEC EDGAR "
            "public-company data, broken out by revenue tier, as a calibrated "
            "reference for private middle-market borrower analysis."
        ),
    )
    p.add_argument("--sic", nargs="+", help="One or more SIC codes (required unless --self-test).")
    p.add_argument("--years", type=int, default=5,
                   help="Lookback window in fiscal years (default 5).")
    p.add_argument("--tiers", default=DEFAULT_TIERS,
                   help=f"Revenue tier boundaries in USD (default '{DEFAULT_TIERS}'). "
                        "Companies are ASSIGNED to tiers, never screened out by size.")
    p.add_argument("--min-sample", type=int, default=10,
                   help="Per-tier minimum company count; thinner tiers are flagged "
                        "LOW CONFIDENCE (default 10).")
    p.add_argument("--out", help="Output base path; writes <out>.csv and <out>.summary.md.")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                   help="SEC-required User-Agent; MUST include a real contact email.")
    p.add_argument("--cache-dir", default=".edgar_cache",
                   help="Local cache directory for raw EDGAR responses (default .edgar_cache).")
    p.add_argument("--sleep", type=float, default=0.15,
                   help="Min seconds between EDGAR requests (throttle; default 0.15).")
    p.add_argument("--offline", action="store_true",
                   help="Use only cached data; never hit the network (errors on cache miss).")
    p.add_argument("--self-test", action="store_true",
                   help="Run the end-to-end pipeline against known CIKs and exit.")
    p.add_argument("--quiet", action="store_true", help="Suppress progress logging.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    log = _make_logger(args.quiet)

    try:
        client = EdgarClient(
            user_agent=args.user_agent,
            cache_dir=args.cache_dir,
            min_interval=args.sleep,
            offline=args.offline,
            logger=log,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.self_test:
        return 0 if run_self_test(client, args.years, log) else 1

    if not args.sic:
        print("error: --sic is required (or use --self-test)", file=sys.stderr)
        return 2
    if not args.out:
        print("error: --out is required", file=sys.stderr)
        return 2

    tiers = parse_tiers(args.tiers)
    sics = [str(s).strip() for s in args.sic]

    universe = discover_universe(client, sics, log)

    runs = []
    for sic in sics:
        companies = universe.get(sic, [])
        log(f"\nProcessing SIC {sic}: {len(companies)} companies ...")
        run = run_for_sic(client, sic, companies, tiers, args.years, args.min_sample, log)
        runs.append(run)

    vintage = client.vintage_range()
    write_outputs(runs, args.out, args.years, vintage, args.min_sample, log)

    # Console-level data-quality summary.
    log("\n=== DATA-QUALITY SUMMARY ===")
    for run in runs:
        q = run.quality
        log(f"SIC {run.sic}: attempted={q['attempted']} usable={q['usable']} "
            f"no_facts={q['no_facts']} company_years={q['company_years']}")
        for label, n in q["usable_by_tier"].items():
            flag = "  <-- LOW CONFIDENCE" if n < args.min_sample else ""
            log(f"    tier {label}: {n} usable{flag}")
    log(f"EDGAR data vintage: {vintage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
