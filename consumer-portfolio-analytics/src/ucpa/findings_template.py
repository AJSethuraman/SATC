"""Narrative findings document -- STRUCTURED TEMPLATE STUB.

Generates a Markdown findings *template*: every computed number, flagged
exception, and data-gap finding is laid out section by section for an
analyst to interpret.  The engine deliberately does NOT write interpretive
conclusions -- every section carries an explicit ``[ANALYST TO COMPLETE]``
placeholder.  Analytical opinions are supplied by a human reviewer, never
generated.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ucpa.metrics.results import ReviewResult

PLACEHOLDER = "> **[ANALYST TO COMPLETE]** _Interpretation, root-cause discussion, and conclusion._"


def _fmt(value: object, pct: bool = True) -> str:
    if value is None:
        return "n/a (data gap)"
    if isinstance(value, float):
        return f"{value:.2%}" if pct else f"{value:,.2f}"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m")
    return str(value)


def _summary_table(summary: dict[str, object], pct_keys: set[str]) -> list[str]:
    lines = ["| Measure | Value |", "| --- | --- |"]
    for key, value in summary.items():
        lines.append(f"| {key} | {_fmt(value, pct=key in pct_keys)} |")
    return lines


_PCT_KEYS = {
    "dpd30plus_balance_rate", "dpd90plus_balance_rate", "dpd30plus_account_rate",
    "current_to_dpd30", "dpd30_to_dpd60", "dpd60_to_dpd90", "dpd30_cure_rate",
    "current_to_dpd30_accounts", "max_cum_loss_mob12", "gross_co_rate_t12",
    "net_co_rate_t12", "cumulative_recovery_rate", "recovery_rate_t12",
    "portfolio_utilization", "high_util_balance_share", "subprime_balance_share",
    "below_prime_balance_share", "max_vintage_year_share", "max_line_size_share",
    "increase_share_below_prime", "increases_gone_bad_rate",
}


def write_findings_template(review: ReviewResult, path: str | Path) -> Path:
    """Write the analyst findings template for ``review`` to ``path``."""
    det = review.tier_detection
    lines: list[str] = [
        f"# Asset-Quality Review Findings -- {review.product_type} (TEMPLATE)",
        "",
        "_All figures below are computed deterministically by the UCPA engine._",
        "_Interpretive text is intentionally left to the human reviewer._",
        "",
        "## 1. Executive summary",
        "",
        PLACEHOLDER,
        "",
        "## 2. Scope and data maturity",
        "",
        f"- Detected data tier: **Tier {det.detected_tier}**",
        f"- Longitudinal monthly panel: **{'yes' if det.is_panel else 'no (snapshot)'}**",
        f"- Accounts: {det.n_accounts:,} | Rows: {det.n_rows:,} | As-of months: {det.n_months}",
        f"- Missing for next tier: {', '.join(det.missing_for_next_tier) if det.missing_for_next_tier else 'none -- highest tier reached'}",
        "",
        PLACEHOLDER,
        "",
        "## 3. Threshold exceptions",
        "",
    ]
    if review.exceptions:
        lines += ["| Severity | Metric | Check | Observed | Limit |", "| --- | --- | --- | --- | --- |"]
        for e in review.exceptions:
            pct = e.format == "pct"
            lines.append(
                f"| {e.severity} | {e.metric} | {e.check} | {_fmt(e.observed, pct)} | {_fmt(e.limit, pct)} |"
            )
    else:
        lines.append("No thresholds breached.")
    lines += ["", PLACEHOLDER, ""]

    lines += ["## 4. Metric results", ""]
    for i, result in enumerate(review.metric_results, start=1):
        lines.append(f"### 4.{i} {result.metric} -- status: {result.status}")
        lines.append("")
        if result.summary:
            lines += _summary_table(result.summary, _PCT_KEYS)
            lines.append("")
        if result.status == "blocked":
            for gap in result.gaps:
                lines.append(f"- BLOCKED: {gap.description}")
            lines.append("")
        lines += [PLACEHOLDER, ""]

    lines += [
        "## 5. Data-maturity gap assessment",
        "",
        "The following analytics could not be produced from the tape as",
        "delivered.  Each row is a concrete data-roadmap item for the client.",
        "",
    ]
    if review.gaps:
        lines += [
            "| Metric | Scope | Tier required | Missing fields |",
            "| --- | --- | --- | --- |",
        ]
        for g in review.gaps:
            lines.append(
                f"| {g.metric} | {g.scope} | Tier {g.tier_required} | {', '.join(g.missing_fields)} |"
            )
    else:
        lines.append("None -- the tape supports the full metric battery.")
    lines += ["", PLACEHOLDER, ""]

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
