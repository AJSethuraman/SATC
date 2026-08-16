"""Assemble a company tear-sheet report from stored data, render Markdown,
and persist the run (ReportRun + SignalResult + EvidenceReference rows).

Reads only from the database — no network. `fetch-sec` must run first.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlmodel import Session, select

import stock_helper
from stock_helper.core.config import Settings, get_settings
from stock_helper.core.format import money, multiple, pct, ratio, shares
from stock_helper.core.logging import get_logger
from stock_helper.features.context import build_all_extras
from stock_helper.features.metrics import METRICS_VERSION, DerivedMetric, compute_derived_metrics
from stock_helper.industry.sic_buckets import peer_group_label
from stock_helper.signals.base import SIGNALS_VERSION
from stock_helper.signals.engine import (
    DataConfidence,
    EvaluatedSignal,
    assess_data_confidence,
    evaluate_signals,
)
from stock_helper.storage.models import (
    Company,
    EvidenceReference,
    Filing,
    FilingSection,
    FinancialMetric,
    QualityComponent,
    QualityFactorRow,
    ReportRun,
    SignalResult,
    Valuation,
    ValuationAssumption,
    ValuationMultiple,
)
from stock_helper.storage.queries import (
    CompanyNotFetchedError,
    find_company,
    load_series,
)
from stock_helper.valuation import VALUATION_VERSION
from stock_helper.valuation.types import ValuationResult

log = get_logger(__name__)


# Re-exported for backward compatibility; canonical home is storage/queries.py.
__all__ = ["CompanyNotFetchedError", "find_company", "load_series", "Report",
           "build_report", "render_markdown", "write_report", "record_output_path"]


@dataclass
class Report:
    ticker: str
    company: Company
    filings: list[Filing]
    derived: dict[str, DerivedMetric]
    signals: list[EvaluatedSignal]
    confidence: DataConfidence
    sections_available: list[str]
    peer_note: str
    generated_at: datetime
    as_of: date | None = None  # point-in-time view date; None = current view
    caveats: list[str] = field(default_factory=list)
    next_questions: list[str] = field(default_factory=list)
    # Composed valuation packet; only built for the current view (as_of is None),
    # since prices/peers cannot be honestly reconstructed for a past as-of date.
    valuation: ValuationResult | None = None
    run_id: int | None = None


def build_report(
    session: Session,
    ticker: str,
    settings: Settings | None = None,
    as_of: date | None = None,
) -> Report:
    settings = settings or get_settings()
    ticker = ticker.upper()
    company = find_company(session, ticker)

    series = load_series(session, company, as_of=as_of)
    derived = compute_derived_metrics(series)
    # Context extras (market/peers/text) only exist for the current view: we
    # cannot honestly reconstruct "prices as of" or "peers as of" yet, so
    # point-in-time reports mark those signals unavailable instead of leaking
    # present-day data.
    extras = (
        build_all_extras(session, company, ticker, series, derived, settings)
        if as_of is None else None
    )
    signals = evaluate_signals(company.industry_bucket, derived, extras)

    filings_query = select(Filing).where(Filing.company_id == company.id)
    if as_of is not None:
        filings_query = filings_query.where(Filing.filed_date <= as_of)
    filings = session.exec(
        filings_query.order_by(Filing.filed_date.desc()).limit(15)  # type: ignore[attr-defined]
    ).all()
    latest_filed = filings[0].filed_date if filings else None
    confidence = assess_data_confidence(company.industry_bucket, series, latest_filed)

    section_names = sorted(
        {
            row
            for row in session.exec(
                select(FilingSection.section_name)
                .join(Filing, Filing.id == FilingSection.filing_id)  # type: ignore[arg-type]
                .where(Filing.company_id == company.id)
            ).all()
        }
    )

    report = Report(
        ticker=ticker,
        company=company,
        filings=list(filings),
        derived=derived,
        signals=signals,
        confidence=confidence,
        sections_available=list(section_names),
        peer_note=peer_group_label(company.sic, company.sic_description),
        generated_at=datetime.now(UTC),
        as_of=as_of,
        caveats=_report_caveats(company, confidence),
        next_questions=_next_questions(company, signals),
        # extras is None in point-in-time replay -> no valuation (honest).
        valuation=(extras.get("valuation") if extras else None),  # type: ignore[union-attr]
    )
    _persist_run(session, report, settings)
    return report


def _report_caveats(company: Company, confidence: DataConfidence) -> list[str]:
    caveats = [
        "This is a research aid, not investment advice. No signal here is backtested; "
        "no predictive accuracy is claimed or implied.",
        "XBRL values are as filed by the registrant; restatements and custom tags can "
        "affect comparability.",
    ]
    caveats.extend(confidence.notes)
    if company.industry_bucket == "banking":
        caveats.append(
            "Banking metrics beyond deposits/allowance (NIM, NCOs, NPLs, CET1) are "
            "declared placeholders — see the scorecard."
        )
    return caveats


def _next_questions(company: Company, signals: list[EvaluatedSignal]) -> list[str]:
    """Research prompts derived from what the scorecard flagged or couldn't see."""
    questions = []
    for evaluated in signals:
        outcome = evaluated.outcome
        if outcome.status == "OK" and (outcome.score or 0) <= -1:
            questions.append(
                f"Why is '{evaluated.definition.name}' deteriorating? Check MD&A and "
                "segment notes in the latest 10-K/10-Q."
            )
        elif outcome.status == "UNAVAILABLE":
            questions.append(
                f"'{evaluated.definition.name}' could not be computed — inspect the "
                "filing directly for the underlying disclosure."
            )
    if not questions:
        questions.append(
            "No rule-level flags. Read the latest MD&A and risk factors for context "
            "the rules cannot see."
        )
    return questions[:6]


def _persist_run(session: Session, report: Report, settings: Settings) -> ReportRun:
    now = report.generated_at
    run = ReportRun(
        company_id=report.company.id,
        ticker=report.ticker,
        created_at=now,
        as_of_date=report.as_of,
        app_version=stock_helper.__version__,
        parser_version=f"{METRICS_VERSION};{SIGNALS_VERSION};{VALUATION_VERSION}",
    )
    session.add(run)
    session.flush()

    # Refresh derived-metric rows for this company (idempotent per run).
    for old in session.exec(
        select(FinancialMetric).where(FinancialMetric.company_id == report.company.id)
    ).all():
        session.delete(old)
    for metric in report.derived.values():
        for period_end, value in metric.points:
            session.add(
                FinancialMetric(
                    company_id=report.company.id,
                    metric_key=metric.key,
                    period_end=period_end,
                    value=value,
                    unit=metric.unit,
                    formula=metric.formula,
                    input_tags=",".join(metric.input_tags),
                    input_accessions=",".join(metric.input_accessions),
                    parser_version=METRICS_VERSION,
                    created_at=now,
                )
            )

    for evaluated in report.signals:
        outcome = evaluated.outcome
        result = SignalResult(
            report_run_id=run.id,
            company_id=report.company.id,
            signal_key=evaluated.definition.key,
            category=evaluated.definition.category,
            status=outcome.status,
            value_text=outcome.value_text,
            numeric_value=outcome.numeric_value,
            direction=outcome.direction,
            score=outcome.score,
            interpretation=outcome.interpretation,
            confidence=outcome.confidence,
            caveat=outcome.caveat,
            created_at=now,
        )
        session.add(result)
        session.flush()
        for evidence in outcome.evidence:
            session.add(
                EvidenceReference(
                    signal_result_id=result.id,
                    kind=evidence.kind,
                    reference=evidence.reference,
                    description=evidence.description,
                    source_url=evidence.source_url,
                )
            )

    if report.valuation is not None:
        _persist_valuation(session, run, report, now)

    session.commit()
    report.run_id = run.id
    return run


def _finite(value) -> float | None:
    """Keep only real finite numbers; NaN/inf never reach the DB as a value."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def _persist_valuation(
    session: Session, run: ReportRun, report: Report, now: datetime
) -> Valuation:
    """Write the Valuation row and its auditable children (one assumption per
    DCF input, one multiple per computed multiple, one QualityFactorRow +
    QualityComponent per quality/distress factor). Every scenario number stays
    reproducible from these rows."""
    val = report.valuation
    dcf = val.dcf
    ev = val.enterprise_value

    valuation = Valuation(
        company_id=report.company.id,
        ticker=report.ticker,
        as_of_date=report.as_of,
        method=(dcf.method if dcf is not None else ""),
        metric_set=val.metric_set,
        fair_value_per_share=val.fair_value_per_share,
        equity_value=(dcf.equity_value if dcf is not None else None),
        enterprise_value=(
            ev.enterprise_value if ev is not None
            else (dcf.enterprise_value if dcf is not None else None)
        ),
        price=val.price,
        margin_of_safety=val.margin_of_safety,
        discount_rate=(dcf.discount_rate if dcf is not None else None),
        terminal_growth=(dcf.terminal_growth if dcf is not None else None),
        base_fcf=(dcf.base_fcf if dcf is not None else None),
        implied_growth=val.implied_growth,
        caveats=" | ".join(val.caveats),
        engine_version=val.engine_version,
        created_at=now,
    )
    session.add(valuation)
    session.flush()

    # One assumption row per DCF input (provenance for every scenario number).
    if dcf is not None:
        numeric_inputs = [
            ("discount_rate", dcf.discount_rate, "ratio", "flat cost-of-equity assumption"),
            ("terminal_growth", dcf.terminal_growth, "ratio", "long-run FCF growth"),
            ("stage1_growth", dcf.stage1_growth, "ratio", "explicit-stage growth"),
            ("stage1_years",
             float(dcf.stage1_years) if dcf.stage1_years is not None else None,
             "years", ""),
            ("base_fcf", dcf.base_fcf, "USD", f"FCF basis: {dcf.fcf_basis}"),
            ("net_debt", dcf.net_debt, "USD", "recorded; subtracted only for unlevered FCFF"),
            ("shares", dcf.shares, "shares", ""),
        ]
        for name, value, unit, note in numeric_inputs:
            session.add(ValuationAssumption(
                valuation_id=valuation.id, name=name,
                value=_finite(value) if value is not None else None,
                unit=unit, note=note))
        session.add(ValuationAssumption(
            valuation_id=valuation.id, name="fcf_basis",
            text_value=dcf.fcf_basis, note="which cash flow the DCF discounts"))
        session.add(ValuationAssumption(
            valuation_id=valuation.id, name="dcf_status", text_value=dcf.status))

    # One row per computed multiple, folding in peer-relative results by key.
    for key, m in val.multiples.items():
        pr = val.peer_relative.get(key)
        session.add(ValuationMultiple(
            valuation_id=valuation.id,
            multiple_key=key,
            value=_finite(m.value),
            peer_median=_finite(getattr(pr, "peer_median", None)) if pr else None,
            implied_price=_finite(getattr(pr, "implied_price", None)) if pr else None,
            upside_pct=_finite(getattr(pr, "upside_pct", None)) if pr else None,
            undefined_reason=m.undefined_reason or "",
        ))

    # QualityFactorRow (+ QualityComponent) per quality/distress factor.
    quality = val.quality
    if quality is not None:
        for key, fr in quality.factors.items():
            detail = fr.detail or {}
            try:
                detail_json = json.dumps(detail, default=str) if detail else ""
            except (TypeError, ValueError):
                detail_json = ""
            row = QualityFactorRow(
                company_id=report.company.id,
                ticker=report.ticker,
                as_of_date=report.as_of,
                factor_key=key,
                value=_finite(fr.value),
                zone=str(detail.get("zone", "")),
                formula=fr.formula,
                detail=detail_json,
                engine_version=fr.engine_version,
                created_at=now,
            )
            session.add(row)
            session.flush()
            for cname, cval in (fr.values_used or {}).items():
                session.add(QualityComponent(
                    quality_factor_row_id=row.id, name=cname, value=_finite(cval)))
            tests = detail.get("tests")
            if isinstance(tests, dict):
                for tname, tval in tests.items():
                    session.add(QualityComponent(
                        quality_factor_row_id=row.id,
                        name=f"test:{tname}", value=_finite(tval)))

    return valuation


def record_output_path(session: Session, run_id: int, path: str) -> None:
    run = session.get(ReportRun, run_id)
    if run is not None:
        run.output_path = path
        session.commit()


# --- Markdown rendering -------------------------------------------------------

_STATUS_BADGES = {
    "OK": "🟢",
    "NOT_APPLICABLE": "⚪ n/a",
    "INSUFFICIENT_DATA": "🟡 insufficient data",
    "UNAVAILABLE": "🟡 unavailable",
    "PLACEHOLDER": "⚫ planned",
}


def _format_metric_value(metric: DerivedMetric, value: float) -> str:
    if metric.unit == "ratio":
        return pct(value) if "margin" in metric.key or metric.key == "accrual_proxy" else ratio(value)
    if metric.unit == "USD":
        return money(value)
    if metric.unit == "shares":
        return shares(value)
    return f"{value:g}"


def _render_valuation_section(val: ValuationResult, add) -> None:
    """## Valuation — fair value, margin of safety, reverse-DCF, EV, multiples,
    peer-relative upsides. Every line carries a caveat; undefined values render
    as ``n/m`` with the reason rather than a fabricated number."""
    dcf = val.dcf
    ev = val.enterprise_value
    add("## Valuation")
    add("")
    add("*Scenario estimates from explicit, editable DCF assumptions — **not price "
        "targets**. Price-derived figures use a non-canonical source.*")
    add("")

    if dcf is not None and dcf.status == "OK":
        basis = (f" (basis {dcf.fcf_basis}, r={pct(dcf.discount_rate)}, "
                 f"g∞={pct(dcf.terminal_growth)})")
    else:
        basis = f" — DCF not computed ({dcf.status if dcf else 'unavailable'})"
    fv = val.fair_value_per_share
    add(f"- **DCF fair value / share:** "
        f"{money(fv) if fv is not None else 'n/m'}{basis if fv is not None else ''}")
    add("- **Margin of safety vs price:** "
        + (pct(val.margin_of_safety) if val.margin_of_safety is not None
           else "n/m — needs both a DCF value and a current price"))
    add("- **Reverse-DCF implied FCF growth:** "
        + (pct(val.implied_growth) if val.implied_growth is not None
           else "n/m — needs a current price"))
    add("- **Enterprise value:** "
        + (money(ev.enterprise_value) if ev is not None
           else "n/m — needs price data (ENABLE_PRICE_DATA)"))
    add("")

    coc = val.cost_of_capital
    if coc is not None:
        add("**Cost of capital** (drives the discount rate — a scenario input, not a fact):")
        add("")
        add(f"- **Cost of equity (CAPM):** {pct(coc.ke)} "
            f"= rf {pct(coc.risk_free)} + β {coc.beta:.2f} × ERP {pct(coc.erp)}")
        if coc.kd_after_tax is not None:
            add(f"- **After-tax cost of debt:** {pct(coc.kd_after_tax)} "
                f"(effective tax rate {pct(coc.tax_rate)})")
        we = f"{pct(coc.weight_equity)} equity" if coc.weight_equity is not None else "equity"
        wd = f" / {pct(coc.weight_debt)} debt" if coc.weight_debt is not None else ""
        add(f"- **WACC:** {pct(coc.wacc)} ({we}{wd}) — used for the ROIC−WACC spread")
        add("")

    ri = val.residual_income
    if ri is not None and ri.status == "OK" and ri.fair_value_per_share is not None:
        add(f"- **Residual-income (EBO) fair value / share:** {money(ri.fair_value_per_share)} "
            f"— independent cross-check on the DCF "
            f"(ROE {pct(ri.roe)} vs Ke {pct(ri.cost_of_equity)})")
    ep = val.economic_profit
    if ep is not None and ep.spread is not None:
        verdict = "creates economic value" if ep.creates_value else "destroys economic value"
        add(f"- **Economic profit (ROIC − WACC):** {pct(ep.spread)} "
            f"(ROIC {pct(ep.roic)} − WACC {pct(ep.wacc)}) — {verdict} at these inputs")
    if (ri is not None and ri.fair_value_per_share is not None) or (
        ep is not None and ep.spread is not None):
        add("")

    mc = val.monte_carlo
    if mc is not None:
        add("**Monte Carlo fair-value spread** (input-uncertainty fan — **not** a probability "
            "the stock rises, **not** a price target):")
        add("")
        add(f"- **Median:** {money(mc.median)} · **middle 80% (p10–p90):** "
            f"{money(mc.p10)} – {money(mc.p90)} · **IQR (p25–p75):** "
            f"{money(mc.p25)} – {money(mc.p75)}")
        add(f"- Simulated {mc.n_sims:,} valid draws (seed {mc.seed}), perturbing growth / "
            "discount / terminal growth around the base scenario.")
        if mc.prob_undervalued is not None:
            add(f"- **Share of draws above current price:** {pct(mc.prob_undervalued)} "
                "(a diagnostic under the assumed input spread, not a forecast).")
        add("")

    add("**Multiples** (n/m = undefined, with reason):")
    add("")
    if val.multiples:
        add("| Multiple | Value | Basis |")
        add("|---|---|---|")
        for key, m in val.multiples.items():
            if m.value is None:
                shown = f"n/m — {m.undefined_reason or 'undefined'}"
            elif key.endswith("_yield"):
                shown = pct(m.value)  # yields are percentages, not "x" multiples
            else:
                shown = multiple(m.value)
            add(f"| {m.label} | {shown} | {m.denominator_label} |")
    else:
        add("_No market multiples — price data unavailable (ENABLE_PRICE_DATA)._")
    add("")

    scored = sorted(
        (pr for pr in val.peer_relative.values()
         if getattr(pr, "upside_pct", None) is not None),
        key=lambda p: p.upside_pct, reverse=True,
    )
    if scored:
        add("**Top peer-relative implied upside** (local fetched universe, not the market):")
        add("")
        for pr in scored[:3]:
            add(f"- `{pr.key}`: {pct(pr.upside_pct)} "
                f"(peer median {ratio(pr.peer_median)}, n={pr.n_peers})")
        add("")

    for caveat in val.caveats:
        add(f"> {caveat}")
    add("")


def _render_quality_section(val: ValuationResult, add) -> None:
    """## Quality, distress & forensic screens. Screens, not verdicts — the
    forensic block says so explicitly and every line carries a caveat."""
    quality = val.quality
    add("## Quality, distress & forensic screens")
    add("")
    add("*Every screen below is a research flag — **not a rating, verdict, or "
        "accusation of fraud**. Forensic scores flag statistical resemblance only.*")
    add("")

    if quality is not None:
        def factor_line(key: str) -> None:
            fr = quality.factors.get(key)
            if fr is None:
                return
            if fr.status != "OK" or fr.value is None:
                add(f"- **{fr.label}:** n/m — {fr.reason or fr.status.lower()}")
                return
            if key == "piotroski_f":
                add(f"- **{fr.label}:** {fr.value:.0f}/9")
            elif key == "altman_z":
                add(f"- **{fr.label}:** {fr.value:.2f} — zone "
                    f"**{fr.detail.get('zone', '?')}** ({fr.detail.get('model', '')})")
            elif key == "gross_profitability":
                add(f"- **{fr.label}:** {pct(fr.value)}")
            else:
                add(f"- **{fr.label}:** {ratio(fr.value)}")

        for key in ("piotroski_f", "altman_z", "gross_profitability", "roa", "roe"):
            factor_line(key)
        if quality.composite is not None:
            add(f"- **Composite (rough research summary, not a rating):** "
                f"{quality.composite}/100 — {quality.note}")

        montier = quality.factors.get("montier_c")
        if montier is not None and montier.status == "OK" and montier.value is not None:
            add(f"- **Montier C-score:** {montier.value:.0f}/6 manipulation flags (screen)")
        else:
            add("- **Montier C-score:** not computed by the current engine")

    beneish = val.beneish
    if beneish is not None and beneish.m_score is not None:
        flag_text = ("flag: accrual/growth profile RESEMBLES manipulators (screen only)"
                     if beneish.flag else "below the -1.78 screen threshold")
        add(f"- **Beneish M-score:** {beneish.m_score:.2f} — {flag_text}")
    else:
        add("- **Beneish M-score:** n/m — needs two clean consecutive fiscal years")

    stress = val.stress
    if stress is not None and stress.stress_flags:
        add(f"- **Stress flags ({stress.flag_count}, worst: {stress.worst}):**")
        for key, reason, _value in stress.stress_flags:
            add(f"  - `{key}` — {reason}")
    else:
        add("- **Stress flags:** none fired on the latest fiscal year")
    add("")

    add("> These are SCREENS for triage, not conclusions. Beneish / stress flags are "
        "**not accusations of fraud** — investigate the filings before any inference.")
    for caveat in (quality.caveats if quality is not None else []):
        add(f"> {caveat}")
    add("")


def render_markdown(report: Report) -> str:
    company = report.company
    lines: list[str] = []
    add = lines.append

    add(f"# {company.name} ({report.ticker}) — Company Tear Sheet")
    add("")
    add(f"*Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')} by "
        f"stock-helper v{stock_helper.__version__}. Research aid — **not investment advice**.*")
    add("")
    if report.as_of is not None:
        add(f"> **Point-in-time view as of {report.as_of}.** Facts and filings filed "
            "after this date are excluded; values are as originally filed at the time, "
            "not later restatements.")
        add("")

    add("## Company overview")
    add("")
    add(f"- **CIK:** {company.cik}")
    add(f"- **SIC:** {company.sic or 'n/a'} — {company.sic_description or 'n/a'}")
    add(f"- **Industry bucket:** `{company.industry_bucket}`")
    add(f"- **Fiscal year end:** {company.fiscal_year_end or 'n/a'}")
    add(f"- **{report.peer_note}**")
    add("")

    add("## Data freshness & confidence")
    add("")
    add(f"- Latest filing ingested: {report.confidence.latest_filing or 'none'}")
    add(f"- Canonical metrics mapped: {report.confidence.metrics_mapped}/"
        f"{report.confidence.metrics_total} ({pct(report.confidence.coverage, 0)})")
    add(f"- Annual periods available: {report.confidence.annual_periods}")
    add(f"- **Data confidence: {report.confidence.level}**")
    for note in report.confidence.notes:
        add(f"- ⚠️ {note}")
    add("")

    add("## Latest filings")
    add("")
    if report.filings:
        add("| Form | Filed | Period | Accession | Link |")
        add("|---|---|---|---|---|")
        for filing in report.filings[:10]:
            add(
                f"| {filing.form} | {filing.filed_date} | {filing.period_end or ''} "
                f"| `{filing.accession}` | [index]({filing.index_url}) |"
            )
    else:
        add("_No filings stored._")
    add("")

    add("## Fundamental metrics (annual)")
    add("")
    if report.derived:
        add("| Metric | Recent values (oldest → newest) | Formula |")
        add("|---|---|---|")
        for metric in report.derived.values():
            recent = " → ".join(
                _format_metric_value(metric, v) for _, v in metric.points[-4:]
            )
            add(f"| {metric.label} | {recent} | `{metric.formula}` |")
    else:
        add("_No canonical metrics could be mapped for this filer._")
    add("")

    add("## Signal scorecard")
    add("")
    add("*Rule-based and descriptive. Scores order findings; they are not "
        "expected returns. See SIGNAL_DEFINITIONS.md.*")
    add("")
    for evaluated in report.signals:
        definition, outcome = evaluated.definition, evaluated.outcome
        badge = _STATUS_BADGES.get(outcome.status, outcome.status)
        add(f"### {definition.name} ({definition.category}) {badge}")
        add("")
        if outcome.status == "OK":
            add(f"- **Value:** {outcome.value_text}")
            add(f"- **Direction:** {outcome.direction}")
            add(f"- **Interpretation:** {outcome.interpretation}")
            add(f"- **Confidence:** {outcome.confidence}")
            add(f"- **Caveat:** {outcome.caveat}")
            for evidence in outcome.evidence:
                add(f"- **Source:** {evidence.description} — accessions: {evidence.reference}")
        else:
            add(f"- {outcome.interpretation}")
        add("")

    if report.valuation is not None:
        _render_valuation_section(report.valuation, add)
        _render_quality_section(report.valuation, add)

    add("## Filing evidence available")
    add("")
    if report.sections_available:
        add(
            "Extracted sections stored for this company: "
            + ", ".join(f"`{s}`" for s in report.sections_available)
            + " (view them in the UI → Filing Evidence)."
        )
    else:
        add("_No filing sections extracted yet. Run `stock-helper fetch-sec "
            f"{report.ticker} --with-documents`._")
    add("")

    add("## Caveats")
    add("")
    for caveat in report.caveats:
        add(f"- {caveat}")
    add("")

    add("## Next research questions")
    add("")
    for question in report.next_questions:
        add(f"- {question}")
    add("")
    return "\n".join(lines)


def write_report(report: Report, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_asof_{report.as_of.isoformat()}" if report.as_of else ""
    filename = f"{report.ticker}{suffix}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.md"
    path = settings.reports_dir / filename
    # Force UTF-8: the report contains → — ≥ etc.; Windows' default cp1252
    # raises UnicodeEncodeError on them.
    path.write_text(render_markdown(report), encoding="utf-8")
    return str(path)
