"""Command-line entry point: generate -> detect -> compute -> export.

Examples (from ``consumer-portfolio-analytics/``)::

    # Full Tier 2 demo run with default seed and calibrated defaults
    python -m ucpa.cli --outdir outputs

    # Simulate a low-maturity client (Tier 0 snapshot tape)
    python -m ucpa.cli --degrade-to 0 --outdir outputs

    # Client-specific thresholds and a different seed
    python -m ucpa.cli --seed 7 --config my_client.json --outdir outputs
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ucpa.engine import run_review
from ucpa.excel_report import write_workbook
from ucpa.findings_template import write_findings_template
from ucpa.generator import CardGeneratorConfig, degrade_to_tier, generate_card_portfolio
from ucpa.products import CreditCardModule
from ucpa.thresholds import load_thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ucpa-review",
        description="Unsecured consumer portfolio asset-quality review (Phase 1: credit cards).",
    )
    parser.add_argument("--seed", type=int, default=42, help="generator seed (default 42)")
    parser.add_argument("--accounts", type=int, default=4000, help="number of synthetic accounts")
    parser.add_argument("--months", type=int, default=78, help="panel length in months")
    parser.add_argument(
        "--degrade-to",
        type=int,
        choices=(0, 1, 2),
        default=2,
        help="strip the tape to this data tier before review (default 2 = full)",
    )
    parser.add_argument("--config", type=Path, default=None, help="client thresholds JSON (overrides defaults)")
    parser.add_argument("--outdir", type=Path, default=Path("outputs"), help="output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    gen_cfg = CardGeneratorConfig(
        n_accounts=args.accounts, n_months=args.months, seed=args.seed
    )
    tape = generate_card_portfolio(gen_cfg)
    tape = degrade_to_tier(tape, args.degrade_to)

    thresholds = load_thresholds(args.config)
    review = run_review(tape, CreditCardModule(), thresholds)

    suffix = f"tier{args.degrade_to}_seed{args.seed}"
    xlsx = write_workbook(review, args.outdir / f"card_review_{suffix}.xlsx")
    findings = write_findings_template(review, args.outdir / f"findings_template_{suffix}.md")

    det = review.tier_detection
    print(f"Tape: {det.n_accounts:,} accounts / {det.n_rows:,} rows / {det.n_months} months")
    print(f"Detected data tier: {det.detected_tier} (panel: {det.is_panel})")
    if det.missing_for_next_tier:
        print(f"Missing for next tier: {', '.join(det.missing_for_next_tier)}")
    print()
    computed = [r for r in review.metric_results if r.status != "blocked"]
    blocked = [r for r in review.metric_results if r.status == "blocked"]
    print(f"Metrics computed: {len(computed)}/{len(review.metric_results)}")
    for r in blocked:
        print(f"  BLOCKED: {r.metric}")
    print()
    print(f"Threshold flags: {len(review.exceptions)}")
    for e in review.exceptions:
        print(f"  [{e.severity}] {e.message}")
    print()
    print(f"Data-gap findings: {len(review.gaps)}")
    for g in review.gaps:
        print(f"  [{g.metric}/{g.scope}] missing: {', '.join(g.missing_fields)}")
    print()
    print(f"Workbook: {xlsx}")
    print(f"Findings template: {findings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
