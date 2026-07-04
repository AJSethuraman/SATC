"""Assemble a company tear-sheet report from stored data, render Markdown,
and persist the run (ReportRun + SignalResult + EvidenceReference rows).

Reads only from the database — no network. `fetch-sec` must run first.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlmodel import Session, select

import stock_helper
from stock_helper.core.config import Settings, get_settings
from stock_helper.core.format import money, pct, ratio, shares
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
    ReportRun,
    SignalResult,
)
from stock_helper.storage.queries import (
    CompanyNotFetchedError,
    find_company,
    load_series,
)

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
        parser_version=f"{METRICS_VERSION};{SIGNALS_VERSION}",
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

    session.commit()
    report.run_id = run.id
    return run


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
    path.write_text(render_markdown(report))
    return str(path)
