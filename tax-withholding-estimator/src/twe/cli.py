"""Command-line interface for the Tax Withholding Estimator.

Two ways to provide inputs:

* ``--input scenario.json`` -- a JSON file describing the full scenario (best
  for anything with extra income, adjustments, or credits).
* Individual flags -- quick estimates straight from a paystub.

Examples::

    twe estimate --input examples/sample_input.json
    twe estimate --filing-status single --pay-frequency biweekly \\
        --gross 3200 --withheld 410 --periods-remaining 14 \\
        --ytd-wages 36000 --ytd-withheld 4500
    twe sample --output scenario.json
    twe years
    twe serve
    twe serve --port 9000 --no-browser
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from twe.engine import estimate
from twe.models import EstimatorInput
from twe.report import render_text, result_to_dict
from twe.tax_data import TaxDataError, available_years


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twe",
        description="Estimate federal tax and recommend per-paycheck withholding.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    est = sub.add_parser("estimate", help="Run a withholding estimate")
    est.add_argument("--input", type=Path, help="JSON scenario file")
    est.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    est.add_argument("--output", type=Path, help="Write the report/JSON to this file too")

    # Quick-flag inputs (used when --input is not given).
    est.add_argument("--filing-status", choices=[
        "single", "married_jointly", "married_separately", "head_of_household",
    ])
    est.add_argument("--tax-year", type=int)
    est.add_argument("--pay-frequency", choices=[
        "weekly", "biweekly", "semimonthly", "monthly", "annual",
    ])
    est.add_argument("--gross", type=float, help="Gross pay per period")
    est.add_argument("--withheld", type=float, help="Federal tax withheld per period")
    est.add_argument("--pretax-retirement", type=float, default=0.0, help="Pre-tax 401k/403b per period")
    est.add_argument("--pretax-other", type=float, default=0.0, help="Other pre-tax (health/HSA/FSA) per period")
    est.add_argument("--ytd-wages", type=float, help="Year-to-date taxable (Box 1) wages")
    est.add_argument("--ytd-withheld", type=float, help="Year-to-date federal tax withheld")
    est.add_argument("--periods-remaining", type=int, help="Pay periods left this year")
    est.add_argument("--other-income", type=float, default=0.0, help="Misc. other taxable income")
    est.add_argument("--ira-distributions", type=float, default=0.0, help="Taxable retirement/IRA distributions")
    est.add_argument("--interest", type=float, default=0.0)
    est.add_argument("--dividends", type=float, default=0.0, help="Ordinary dividends (incl. qualified)")
    est.add_argument("--qualified-dividends", type=float, default=0.0)
    est.add_argument("--ltcg", type=float, default=0.0, help="Net long-term capital gains")
    est.add_argument("--self-employment", type=float, default=0.0, help="Net self-employment income")
    est.add_argument("--itemized", type=float, help="Itemized deductions total (else standard)")
    est.add_argument("--child-tax-credit", type=float, default=0.0)
    est.add_argument("--other-credits", type=float, default=0.0, help="Other nonrefundable credits")
    est.add_argument("--estimated-payments", type=float, default=0.0, help="Estimated tax already paid")
    est.add_argument("--target-refund", type=float, default=0.0, help="Desired refund (default break even)")
    est.add_argument("--prior-year-tax", type=float, help="Prior-year total tax (enables safe-harbor calc)")
    est.add_argument("--prior-year-agi", type=float, help="Prior-year AGI (for safe-harbor 100%/110% test)")

    samp = sub.add_parser("sample", help="Write a sample scenario JSON file")
    samp.add_argument("--output", type=Path, default=Path("scenario.json"))

    sub.add_parser("years", help="List bundled tax years")

    srv = sub.add_parser("serve", help="Open the web UI in a browser")
    srv.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    srv.add_argument("--port", type=int, default=8765, help="Port (default 8765)")
    srv.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")

    return parser


def _input_from_flags(args: argparse.Namespace) -> EstimatorInput:
    if not args.filing_status:
        raise ValueError("--filing-status is required when --input is not given")
    if not args.pay_frequency:
        raise ValueError("--pay-frequency is required when --input is not given")
    if args.gross is None:
        raise ValueError("--gross is required when --input is not given")

    data: dict[str, Any] = {
        "filing_status": args.filing_status,
        "tax_year": args.tax_year,
        "paystub": {
            "pay_frequency": args.pay_frequency,
            "gross_pay_per_period": args.gross,
            "federal_tax_withheld_per_period": args.withheld or 0.0,
            "retirement_pretax_per_period": args.pretax_retirement,
            "other_pretax_per_period": args.pretax_other,
            "ytd_taxable_wages": args.ytd_wages,
            "ytd_federal_tax_withheld": args.ytd_withheld,
            "pay_periods_remaining": args.periods_remaining,
        },
        "other_income": {
            "interest": args.interest,
            "ordinary_dividends": args.dividends,
            "qualified_dividends": args.qualified_dividends,
            "taxable_retirement_distributions": args.ira_distributions,
            "long_term_capital_gains": args.ltcg,
            "self_employment_net": args.self_employment,
            "other_taxable_income": args.other_income,
        },
        "deductions": {"itemized_total": args.itemized},
        "credits": {
            "child_tax_credit": args.child_tax_credit,
            "other_nonrefundable_credits": args.other_credits,
        },
        "other_payments": {"estimated_tax_payments": args.estimated_payments},
        "target_refund": args.target_refund,
        "prior_year_tax": args.prior_year_tax,
        "prior_year_agi": args.prior_year_agi,
    }
    return EstimatorInput.from_dict(data)


def _command_estimate(args: argparse.Namespace) -> int:
    try:
        if args.input is not None:
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            inp = EstimatorInput.from_dict(raw)
        else:
            inp = _input_from_flags(args)
        result = estimate(inp)
    except FileNotFoundError:
        print(f"input file not found: {args.input}")
        return 1
    except (ValueError, TaxDataError, json.JSONDecodeError) as exc:
        print(f"estimate failed: {exc}")
        return 1

    if args.json:
        output = json.dumps(result_to_dict(result), indent=2)
    else:
        output = render_text(result)

    print(output)
    if args.output is not None:
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"\nwritten to {args.output}")
    return 0


def _command_serve(args: argparse.Namespace) -> int:
    from twe.server import serve  # imported lazily so CLI stays fast for other commands

    serve(host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def _command_sample(args: argparse.Namespace) -> int:
    args.output.write_text(json.dumps(_SAMPLE_SCENARIO, indent=2) + "\n", encoding="utf-8")
    print(f"sample scenario written to {args.output}")
    return 0


def _command_years(_: argparse.Namespace) -> int:
    years = available_years()
    print("Bundled tax years: " + ", ".join(str(y) for y in years))
    return 0


_SAMPLE_SCENARIO: dict[str, Any] = {
    "filing_status": "married_jointly",
    "tax_year": 2025,
    "paystub": {
        "pay_frequency": "biweekly",
        "gross_pay_per_period": 3800,
        "federal_tax_withheld_per_period": 420,
        "retirement_pretax_per_period": 200,
        "other_pretax_per_period": 150,
        "ytd_taxable_wages": 45000,
        "ytd_federal_tax_withheld": 5040,
        "pay_periods_remaining": 14
    },
    "other_income": {
        "interest": 600,
        "ordinary_dividends": 1500,
        "qualified_dividends": 1200,
        "taxable_retirement_distributions": 8000,
        "long_term_capital_gains": 3000,
        "spouse_taxable_wages": 52000,
        "spouse_federal_tax_withheld": 6200
    },
    "adjustments": {
        "hsa_deduction": 3000,
        "student_loan_interest": 1500
    },
    "deductions": {
        "itemized_total": None,
        "extra_standard_deductions": 0
    },
    "credits": {
        "child_tax_credit": 2000
    },
    "other_payments": {
        "estimated_tax_payments": 0
    },
    "target_refund": 0,
    "prior_year_tax": 14500,
    "prior_year_agi": 162000
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "estimate":
        return _command_estimate(args)
    if args.command == "sample":
        return _command_sample(args)
    if args.command == "years":
        return _command_years(args)
    if args.command == "serve":
        return _command_serve(args)

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
