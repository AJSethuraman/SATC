"""Shared read queries used by reports, signal history, UI, and API."""

from datetime import date

from sqlmodel import Session, select

from stock_helper.normalization.facts import FactPoint, MetricSeries, select_annual_series
from stock_helper.storage.models import Company, CompanyFact, SecurityIdentifier


class CompanyNotFetchedError(LookupError):
    pass


def find_company(session: Session, ticker: str) -> Company:
    ticker = ticker.upper()
    identifier = session.exec(
        select(SecurityIdentifier).where(SecurityIdentifier.ticker == ticker)
    ).first()
    if identifier is None:
        raise CompanyNotFetchedError(
            f"No data for {ticker!r}. Run: stock-helper fetch-sec {ticker}"
        )
    return session.get(Company, identifier.company_id)


def load_series(
    session: Session, company: Company, as_of: date | None = None
) -> dict[str, MetricSeries]:
    """Rebuild canonical annual series from stored CompanyFact rows.

    ``as_of`` gives the point-in-time view: facts filed after that date are
    excluded and originally-filed values win over later restatements."""
    rows = session.exec(
        select(CompanyFact).where(CompanyFact.company_id == company.id)
    ).all()
    points = [
        FactPoint(
            metric_key=row.metric_key,
            taxonomy=row.taxonomy,
            tag=row.tag,
            unit=row.unit,
            value=row.value,
            period_start=row.period_start,
            period_end=row.period_end,
            fiscal_year=row.fiscal_year,
            fiscal_period=row.fiscal_period,
            form=row.form,
            accession=row.accession,
            filed=row.filed_date,
        )
        for row in rows
    ]
    return select_annual_series(points, as_of=as_of)
