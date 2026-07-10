"""Output layer: auditable CSV of raw per-company-year data + readable summary.

Two artifacts per run:
  * CSV  : one row per company / fiscal year with every raw line item, the
           reconstructed EBITDA (+ method), the assigned tier, and all computed
           metrics. This is the audit trail — the underlying data, not summaries.
  * .md  : a human-readable summary PER SIC code with per-tier percentile
           tables (current norms + through-cycle), sample sizes, the 2020 shock,
           cross-tier size trend, a data-quality report, and the STANDING
           CAVEATS block printed every time.
"""

from __future__ import annotations

import csv
from typing import Dict, List, Optional, TextIO

from .aggregate import MetricDist, TierResult, cross_tier_trend
from .metrics import (
    ALL_METRICS,
    METRIC_FAMILIES,
    METRIC_LABELS,
    PERCENT_METRICS,
    CompanyYear,
    compute_metrics,
)

CAVEATS = """\
## Standing caveats — read before using these numbers

These benchmarks are derived from SEC public-company filings and are a
*calibrated reference*, NOT a standard a private borrower must meet. Three
biases push them toward health relative to private middle-market names:

1. SIZE DISTORTION — public companies are larger, better-capitalized, and
   access cheaper capital. Metrics are reported BY REVENUE TIER so this is
   visible: watch how leverage tolerance, margins, and volatility shift as
   size drops, then extrapolate *below* the smallest public tier toward your
   borrower. Even the smallest public tier skews healthier than private MM.
2. SURVIVORSHIP BIAS — public companies cleared a quality bar private names
   did not. The distribution is conditioned on survival; weak names are absent.
3. ACCOUNTING DIFFERENCES — public GAAP is cleaner and more consistent than
   private / owner-operated financials (add-backs, related-party items, tax-
   driven structuring). Reported margins and coverage are not like-for-like.

Use these as a sanity-check range, not a hurdle. Trust the cross-tier TREND
more than any single tier's level.
"""

# Raw CSV columns: identity + raw line items + provenance + metrics.
_RAW_FIELDS = [
    "sic",
    "cik",
    "name",
    "ticker",
    "fiscal_year",
    "tier",
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "interest_expense",
    "income_tax",
    "dep_amort",
    "capex",
    "assets",
    "assets_current",
    "liabilities_current",
    "cash",
    "inventory",
    "receivables",
    "payables",
    "total_debt",
    "debt_method",
    "ebitda",
    "ebitda_method",
    "notes",
]
_CSV_FIELDS = _RAW_FIELDS + ALL_METRICS


def _fmt_num(v: Optional[float]) -> str:
    if v is None:
        return ""
    return repr(round(float(v), 6))  # deterministic, audit-friendly


def write_raw_csv(path: str, rows: List[Dict[str, object]]) -> None:
    """Write the auditable raw rows. ``rows`` already deterministically sorted."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def raw_rows_for_company(sic: str, rec: CompanyYear, tier_label: str) -> Dict[str, object]:
    """Flatten one CompanyYear (+ metrics) into a CSV row dict."""
    metrics = compute_metrics(rec)
    row: Dict[str, object] = {
        "sic": sic,
        "cik": rec.cik,
        "name": rec.name,
        "ticker": rec.ticker,
        "fiscal_year": rec.fiscal_year,
        "tier": tier_label,
        "debt_method": rec.debt_method,
        "ebitda_method": rec.ebitda_method,
        "notes": ";".join(rec.notes),
    }
    for f in (
        "revenue", "cost_of_revenue", "gross_profit", "operating_income",
        "net_income", "interest_expense", "income_tax", "dep_amort", "capex",
        "assets", "assets_current", "liabilities_current", "cash", "inventory",
        "receivables", "payables", "total_debt", "ebitda",
    ):
        row[f] = _fmt_num(getattr(rec, f))
    for k in ALL_METRICS:
        row[k] = _fmt_num(metrics.get(k))
    return row


# --------------------------------------------------------------------------
# Markdown summary
# --------------------------------------------------------------------------
def _fmt_metric_value(metric: str, v: Optional[float]) -> str:
    if v is None:
        return "  -  "
    if metric in PERCENT_METRICS:
        return f"{v * 100:.1f}%"
    return f"{v:.2f}"


def _dist_row(metric: str, d: MetricDist) -> str:
    label = METRIC_LABELS.get(metric, metric)
    cells = [
        _fmt_metric_value(metric, d.p10),
        _fmt_metric_value(metric, d.p25),
        _fmt_metric_value(metric, d.p50),
        _fmt_metric_value(metric, d.p75),
        _fmt_metric_value(metric, d.p90),
        str(d.n_companies),
        str(d.n_company_years),
        f"{d.median_cv:.2f}" if d.median_cv is not None else "-",
    ]
    return "| " + label + " | " + " | ".join(cells) + " |"


def _metric_table(title: str, tier: TierResult, view: str) -> List[str]:
    dists = tier.current if view == "current" else tier.through_cycle
    lines = [
        f"#### {title}",
        "",
        "| Metric | p10 | p25 | p50 | p75 | p90 | #co | #co-yrs | med CV |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for family, metrics in METRIC_FAMILIES.items():
        lines.append(f"| **{family}** | | | | | | | | |")
        for metric in metrics:
            lines.append(_dist_row(metric, dists[metric]))
    lines.append("")
    return lines


def _fmt_revenue(v: Optional[float]) -> str:
    """Compact USD revenue, e.g. 1.7B / 540.0M / 12.3K."""
    if v is None:
        return "n/a"
    a = abs(v)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{v / div:.1f}{suf}"
    return f"{v:.0f}"


def _roster_table(tier: TierResult) -> List[str]:
    """Constituent companies of a tier (largest revenue first)."""
    lines = [
        "#### Constituent companies (largest revenue first)",
        "",
        "| Ticker | Company | CIK | Latest revenue | FY span | # yrs |",
        "|---|---|---|---|---|---|",
    ]
    for e in tier.roster:
        span = (
            f"{e.first_year}-{e.last_year}"
            if e.first_year is not None and e.last_year is not None
            else "-"
        )
        ticker = e.ticker or "—"
        lines.append(
            f"| {ticker} | {e.name} | {e.cik} | "
            f"{_fmt_revenue(e.latest_revenue)} | {span} | {e.n_years} |"
        )
    lines.append("")
    return lines


def render_summary(
    fh: TextIO,
    sic: str,
    sic_description: str,
    tier_results: List[TierResult],
    quality: Dict[str, object],
    years_window: int,
    data_vintage: str,
    min_sample: int,
) -> None:
    """Write the markdown summary for one SIC code to ``fh``."""
    w = fh.write
    w(f"# Industry assumption set — SIC {sic} ({sic_description or 'description n/a'})\n\n")
    w(f"- EDGAR data vintage (date pulled): **{data_vintage}**\n")
    w(f"- Lookback window: **{years_window} fiscal years**\n")
    w(f"- Min sample per tier: **{min_sample}** companies\n")
    w(f"- Tiers (small -> large): "
      + ", ".join(tr.tier.label for tr in tier_results) + "\n\n")

    low_conf = [tr for tr in tier_results if tr.low_confidence]
    if low_conf:
        w("> **LOW CONFIDENCE** — the following tiers fell below the minimum "
          "sample and should be read as indicative only: "
          + ", ".join(f"{tr.tier.label} (n={tr.n_companies})" for tr in low_conf)
          + ".\n\n")
    if all(tr.n_companies == 0 for tr in tier_results):
        w("> **NO USABLE COMPANIES** were found for this SIC in the window. "
          "See the data-quality report below.\n\n")

    w(CAVEATS)
    w("\n")

    # Per-tier tables (small -> large so the read toward private MM is natural).
    for tr in tier_results:
        flag = "  ⚠️ LOW CONFIDENCE" if tr.low_confidence else ""
        w(f"## Revenue tier: {tr.tier.label}  (n={tr.n_companies} companies){flag}\n\n")
        if tr.n_companies == 0:
            w("_No companies assigned to this tier._\n\n")
            continue
        for line in _roster_table(tr):
            w(line + "\n")
        for line in _metric_table(
            f"Current norms (most-recent fiscal year)", tr, "current"
        ):
            w(line + "\n")
        for line in _metric_table(
            f"Through-cycle ({years_window}-yr window, with volatility)", tr, "through_cycle"
        ):
            w(line + "\n")

        shock = tr.shock_2020
        n_shock = int(shock.get("_n", 0.0)) if shock else 0
        if n_shock >= 2:
            w("#### 2020 shock (median 2019->2020 change)\n\n")
            w("| Metric | Change |\n|---|---|\n")
            for metric in ALL_METRICS:
                val = shock.get(metric)
                if val is None:
                    continue
                if metric in PERCENT_METRICS:
                    cell = f"{val * 100:+.1f} pp"
                else:
                    cell = f"{val * 100:+.1f}%"
                w(f"| {METRIC_LABELS.get(metric, metric)} | {cell} |\n")
            w("\n")
        else:
            w("_2020 shock not computed for this tier (insufficient 2019+2020 "
              "paired data)._\n\n")

    # Cross-tier size trend (a key output): use a representative metric per family.
    populated = [tr for tr in tier_results if tr.n_companies > 0]
    if len(populated) >= 2:
        w("## Cross-tier size trend (large -> small)\n\n")
        w("_How the median shifts as company size decreases — extrapolate the "
          "trend below the smallest public tier toward your borrower._\n\n")
        highlight = [
            "debt_to_ebitda",
            "ebitda_to_interest",
            "ebitda_margin",
            "net_margin",
            "current_ratio",
            "cash_conversion_cycle",
        ]
        for metric in highlight:
            trend = cross_tier_trend(metric, populated)
            w(f"- **{METRIC_LABELS.get(metric, metric)}**: {trend}\n")
        w("\n")

    # Data-quality report.
    w("## Data-quality report\n\n")
    w(f"- Companies in SIC universe attempted: **{quality.get('attempted', 0)}**\n")
    w(f"- Companies with usable XBRL facts: **{quality.get('usable', 0)}**\n")
    w(f"- Companies with no companyfacts (404) : **{quality.get('no_facts', 0)}**\n")
    w(f"- Companies dropped (no in-window revenue/assets): "
      f"**{quality.get('no_window_data', 0)}**\n")
    w(f"- Company-years emitted to CSV: **{quality.get('company_years', 0)}**\n\n")
    by_tier = quality.get("usable_by_tier", {})
    if by_tier:
        w("Usable companies by tier:\n\n")
        for label, n in by_tier.items():
            w(f"- {label}: {n}\n")
        w("\n")
    drops = quality.get("drop_reasons", {})
    if drops:
        w("Drop / quality reasons (company-year level):\n\n")
        for reason in sorted(drops):
            w(f"- `{reason}`: {drops[reason]}\n")
        w("\n")
