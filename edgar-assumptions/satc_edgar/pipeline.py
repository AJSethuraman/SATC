"""Orchestration: SIC universe discovery -> extraction -> aggregation -> output.

Kept separate from the CLI so it is testable. All collections are sorted
deterministically before they influence output.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from . import output
from .aggregate import (
    CompanySeries,
    Tier,
    TierResult,
    aggregate_tier,
    assign_tier,
    build_series,
)
from .fetch import EdgarClient, list_ciks, ticker_for_cik
from .metrics import extract_annual_financials

Logger = Callable[[str], None]


@dataclass
class SicRun:
    """Everything needed to render one SIC code's output."""

    sic: str
    sic_description: str
    tier_results: List[TierResult]
    raw_rows: List[dict]
    quality: Dict[str, object] = field(default_factory=dict)


def discover_universe(
    client: EdgarClient,
    target_sics: List[str],
    log: Logger,
) -> Dict[str, List[Tuple[int, str, str]]]:
    """Map each target SIC -> list of (cik, company_name, ticker).

    Scans company_tickers.json, then each company's submissions to read its
    SIC. This is the cross-reference approach EDGAR supports; results are
    cached so the (slow) scan only happens once per cache.
    """
    target = {str(s).strip() for s in target_sics}
    log(f"Loading company tickers universe ...")
    tickers = client.get_company_tickers()
    ciks = list_ciks(tickers)
    tick_map = ticker_for_cik(tickers)
    log(f"  {len(ciks)} companies in tickers file; scanning SIC codes "
        f"(cached after first run) ...")

    by_sic: Dict[str, List[Tuple[int, str, str]]] = {s: [] for s in target}
    for i, cik in enumerate(ciks, 1):
        if i % 500 == 0:
            log(f"  ...scanned {i}/{len(ciks)} submissions")
        sub = client.get_submissions(cik)
        if not sub:
            continue
        sic = str(sub.get("sic", "")).strip()
        if sic in target:
            name = str(sub.get("name", "")).strip()
            ticker = tick_map.get(cik, "")
            by_sic[sic].append((cik, name, ticker))
    for s in by_sic:
        by_sic[s].sort(key=lambda t: t[0])  # deterministic by CIK
        log(f"  SIC {s}: {len(by_sic[s])} companies")
    return by_sic


def _sic_description(client: EdgarClient, cik: int) -> str:
    sub = client.get_submissions(cik)
    if sub:
        return str(sub.get("sicDescription", "")).strip()
    return ""


def run_for_sic(
    client: EdgarClient,
    sic: str,
    companies: List[Tuple[int, str, str]],
    tiers: List[Tier],
    years: int,
    min_sample: int,
    log: Logger,
) -> SicRun:
    """Fetch facts, build series, tier-assign, aggregate, and collect raw rows."""
    quality: Dict[str, object] = {
        "attempted": len(companies),
        "usable": 0,
        "no_facts": 0,
        "no_window_data": 0,
        "company_years": 0,
        "drop_reasons": {},
        "usable_by_tier": {t.label: 0 for t in tiers},
    }
    drop_reasons: Dict[str, int] = quality["drop_reasons"]  # type: ignore

    series_by_tier: Dict[str, List[CompanySeries]] = {t.label: [] for t in tiers}
    raw_rows: List[dict] = []
    sic_description = ""

    for cik, name, ticker in companies:  # already CIK-sorted
        if not sic_description:
            sic_description = _sic_description(client, cik)
        facts = client.get_companyfacts(cik)
        if not facts:
            quality["no_facts"] += 1  # type: ignore
            continue
        records = extract_annual_financials(facts, cik, name or facts.get("entityName", ""), ticker)
        series = build_series(records, years)
        if series is None:
            quality["no_window_data"] += 1  # type: ignore
            continue
        tier = assign_tier(series.latest_revenue, tiers)
        if tier is None:
            drop_reasons["no_revenue_for_tiering"] = drop_reasons.get("no_revenue_for_tiering", 0) + 1
            continue

        quality["usable"] += 1  # type: ignore
        quality["usable_by_tier"][tier.label] += 1  # type: ignore
        series_by_tier[tier.label].append(series)

        # Tally company-year quality notes and emit raw rows.
        for rec in series.records:
            for note in rec.notes:
                drop_reasons[note] = drop_reasons.get(note, 0) + 1
            raw_rows.append(output.raw_rows_for_company(sic, rec, tier.label))
            quality["company_years"] += 1  # type: ignore

    # Aggregate every tier (even empty ones, so the table is complete).
    tier_results: List[TierResult] = []
    for t in tiers:
        tr = aggregate_tier(series_by_tier[t.label], t, min_sample)
        tier_results.append(tr)

    # Deterministic ordering of raw rows: CIK then fiscal year.
    raw_rows.sort(key=lambda r: (int(r["cik"]), int(r["fiscal_year"])))

    return SicRun(
        sic=sic,
        sic_description=sic_description,
        tier_results=tier_results,
        raw_rows=raw_rows,
        quality=quality,
    )


def write_outputs(runs: List[SicRun], out_path: str, years: int, vintage: str,
                  min_sample: int, log: Logger) -> Tuple[str, str]:
    """Write the combined CSV and a markdown summary; return their paths."""
    base, ext = os.path.splitext(out_path)
    csv_path = out_path if ext.lower() == ".csv" else base + ".csv"
    md_path = base + ".summary.md"

    all_rows: List[dict] = []
    for run in sorted(runs, key=lambda r: r.sic):
        all_rows.extend(run.raw_rows)
    output.write_raw_csv(csv_path, all_rows)

    with open(md_path, "w", encoding="utf-8") as fh:
        for i, run in enumerate(sorted(runs, key=lambda r: r.sic)):
            if i:
                fh.write("\n---\n\n")
            output.render_summary(
                fh,
                sic=run.sic,
                sic_description=run.sic_description,
                tier_results=run.tier_results,
                quality=run.quality,
                years_window=years,
                data_vintage=vintage,
                min_sample=min_sample,
            )
    log(f"Wrote CSV  -> {csv_path}")
    log(f"Wrote docs -> {md_path}")
    return csv_path, md_path
