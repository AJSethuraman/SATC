"""End-to-end self-test against a couple of known CIKs.

Verifies the fetch -> extract -> metric pipeline produces sane numbers before
committing to a full (slow) industry scan. Uses the same throttled, cached
client, so after the first run it is fully offline-reproducible.

Default CIKs:
  * 0000096021  SYSCO CORP        — large-cap food distributor (SIC 5140)
  * 0000793074  THE ANDERSONS INC — mid-cap ag distributor   (SIC 5150)
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from .aggregate import build_series
from .fetch import EdgarClient
from .metrics import ALL_METRICS, METRIC_LABELS, compute_metrics, extract_annual_financials

SELF_TEST_CIKS: List[Tuple[int, str]] = [
    (96021, "SYSCO CORP"),
    (793074, "THE ANDERSONS INC"),
]


def run_self_test(client: EdgarClient, years: int, log: Callable[[str], None]) -> bool:
    """Return True if the pipeline produced usable metrics for every CIK."""
    ok = True
    log("=== SELF-TEST ===")
    for cik, hint in SELF_TEST_CIKS:
        log(f"\n[{cik}] {hint}")
        try:
            facts = client.get_companyfacts(cik)
        except Exception as exc:  # network/parse problems should fail loudly
            log(f"  FAIL: could not fetch companyfacts: {exc}")
            ok = False
            continue
        if not facts:
            log("  FAIL: no companyfacts returned (404?)")
            ok = False
            continue

        name = facts.get("entityName", hint)
        records = extract_annual_financials(facts, cik, name, "")
        series = build_series(records, years)
        if series is None or not series.records:
            log("  FAIL: no in-window fiscal years extracted")
            ok = False
            continue

        latest = series.records[-1]
        metrics = compute_metrics(latest)
        computed = [k for k in ALL_METRICS if metrics.get(k) is not None]
        log(f"  fiscal years extracted: "
            f"{[r.fiscal_year for r in series.records]}")
        log(f"  latest FY {latest.fiscal_year}: revenue={latest.revenue}, "
            f"ebitda={latest.ebitda} (method={latest.ebitda_method or 'n/a'})")
        log(f"  metrics computed: {len(computed)}/{len(ALL_METRICS)}")
        for k in ("debt_to_ebitda", "ebitda_margin", "current_ratio"):
            v = metrics.get(k)
            log(f"    {METRIC_LABELS[k]}: {v}")

        # Sanity gates: EBITDA must reconstruct and a reasonable share of
        # metrics must compute, or the pipeline is broken for this name.
        if latest.ebitda is None:
            log("  FAIL: EBITDA did not reconstruct for latest year")
            ok = False
        if len(computed) < len(ALL_METRICS) // 2:
            log("  FAIL: fewer than half of metrics computed")
            ok = False

    log("\n=== SELF-TEST " + ("PASSED ===" if ok else "FAILED ===") )
    return ok
