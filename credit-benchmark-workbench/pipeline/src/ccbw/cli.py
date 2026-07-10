"""ccbw command line.

Commands:
  demo-snapshot   Build the demonstration snapshot from the synthetic corpus
                  (no network needed) + validation report, optionally baking
                  into the workbench JSX.
  build-live      Build a snapshot from live EDGAR (requires network access
                  to data.sec.gov and a --user-agent 'Name email').
  bake            Re-bake an existing snapshot JSON into the workbench JSX.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .snapshot import (assemble, bake_into_jsx, build_demo_inputs,
                       render_validation_md, write_snapshot)


def cmd_demo_snapshot(args: argparse.Namespace) -> int:
    panels, sics = build_demo_inputs(seed=args.seed)
    notes = [
        "SYNTHETIC DEMONSTRATION DATA: this snapshot was generated from a "
        "deterministic synthetic corpus shaped like EDGAR CompanyFacts, "
        "because the build environment had no network access to "
        "data.sec.gov. All distributions are illustrative of the machinery, "
        "NOT sourced market statistics. Refresh against live EDGAR before "
        "any production use (see meta.refresh).",
        f"Synthetic corpus: {len(panels)} companies, FY2012-FY2024, "
        "deterministic seed; includes engineered messiness (tag variants, "
        "amendments/restatements, missing items, off-calendar FYEs) and a "
        "~16% deterioration cohort for backtesting.",
    ]
    snapshot, bt = assemble(panels, sics, data_source="SYNTHETIC_DEMO",
                            source_notes=notes)
    write_snapshot(snapshot, args.out)
    print(f"snapshot -> {args.out}")
    if args.validation_out:
        Path(args.validation_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.validation_out).write_text(
            render_validation_md(bt, "SYNTHETIC_DEMO"))
        with open(str(Path(args.validation_out).with_suffix(".json")), "w") as fh:
            json.dump(bt, fh, indent=1, default=str)
        print(f"validation -> {args.validation_out}")
    if args.bake:
        bake_into_jsx(snapshot, args.bake)
        print(f"baked into -> {args.bake}")
    return 0


def cmd_build_live(args: argparse.Namespace) -> int:
    """Live EDGAR build. Universe: CIKs with SIC codes from the submissions
    endpoint, filtered into segments; CompanyFacts per CIK."""
    from .edgar_client import EdgarClient
    from .panel import build_company_panel
    from .segments import SEGMENTS, sic_in_segment

    client = EdgarClient(user_agent=args.user_agent, cache_dir=args.cache_dir)
    ciks: list[int] = []
    if args.ciks:
        ciks = [int(c) for c in args.ciks.split(",")]
    else:
        print("No --ciks provided: resolving universe from the bulk ticker "
              "file (this enumerates all registrants; expect a long run).",
              file=sys.stderr)
        tickers = client.company_tickers()
        ciks = sorted({int(v["cik_str"]) for v in tickers.values()})
        if args.limit:
            ciks = ciks[: args.limit]

    panels, sics = {}, {}
    for cik in ciks:
        try:
            subs = client.get_json(
                f"{client.DATA_BASE}/submissions/CIK{client.cik10(cik)}.json")
            sic = int(subs.get("sic") or 0)
        except Exception as exc:  # noqa: BLE001 -- log and continue the pull
            print(f"CIK {cik}: submissions failed ({exc}); skipped",
                  file=sys.stderr)
            continue
        if not any(s.screen is None and sic_in_segment(sic, s)
                   for s in SEGMENTS.values()):
            continue
        try:
            cf = client.company_facts(cik)
            rows = build_company_panel(cf, sic=sic)
        except Exception as exc:  # noqa: BLE001
            print(f"CIK {cik}: companyfacts failed ({exc}); skipped",
                  file=sys.stderr)
            continue
        if rows:
            panels[cik] = rows
            sics[cik] = sic
    notes = [f"Live EDGAR pull: {len(panels)} companies with usable panels.",
             "Per-datapoint provenance (CIK, accession, tag, form, filed) "
             "carried in the pipeline panel; aggregate sources noted per "
             "benchmark cell."]
    snapshot, bt = assemble(panels, sics, data_source="EDGAR_LIVE",
                            source_notes=notes)
    write_snapshot(snapshot, args.out)
    print(f"snapshot -> {args.out}")
    if args.validation_out:
        Path(args.validation_out).write_text(
            render_validation_md(bt, "EDGAR_LIVE"))
    if args.bake:
        bake_into_jsx(snapshot, args.bake)
    return 0


def cmd_bake(args: argparse.Namespace) -> int:
    with open(args.snapshot) as fh:
        snapshot = json.load(fh)
    bake_into_jsx(snapshot, args.jsx)
    print(f"baked {args.snapshot} -> {args.jsx}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ccbw")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo-snapshot", help="synthetic demo snapshot")
    d.add_argument("--out", default="data/benchmark_snapshot_v1.json")
    d.add_argument("--validation-out", default=None)
    d.add_argument("--bake", default=None, help="path to workbench JSX")
    d.add_argument("--seed", type=int, default=20260609)
    d.set_defaults(func=cmd_demo_snapshot)

    l = sub.add_parser("build-live", help="live EDGAR snapshot")
    l.add_argument("--user-agent", required=True,
                   help='"Name email@domain" (SEC requirement)')
    l.add_argument("--ciks", default=None, help="comma-separated CIK list")
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--cache-dir", default=".edgar_cache")
    l.add_argument("--out", default="data/benchmark_snapshot_live.json")
    l.add_argument("--validation-out", default=None)
    l.add_argument("--bake", default=None)
    l.set_defaults(func=cmd_build_live)

    b = sub.add_parser("bake", help="bake snapshot JSON into workbench JSX")
    b.add_argument("--snapshot", required=True)
    b.add_argument("--jsx", required=True)
    b.set_defaults(func=cmd_bake)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
