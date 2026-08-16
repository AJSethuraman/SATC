"""Shared read queries used by reports, signal history, UI, and API."""

from datetime import date

from sqlmodel import Session, select

from stock_helper.normalization.facts import FactPoint, MetricSeries, select_annual_series
from stock_helper.storage.models import (
    Company,
    CompanyFact,
    QualityFactorRow,
    SecurityIdentifier,
    Valuation,
)


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


def load_valuation(
    session: Session, company: Company, as_of: date | None = None
) -> Valuation | None:
    """Most recent stored Valuation for the given view. ``as_of=None`` matches
    only current-view runs (as_of_date IS NULL); a date matches that exact
    point-in-time run — the two are never mixed."""
    stmt = select(Valuation).where(Valuation.company_id == company.id)
    if as_of is None:
        stmt = stmt.where(Valuation.as_of_date.is_(None))  # type: ignore[attr-defined]
    else:
        stmt = stmt.where(Valuation.as_of_date == as_of)
    stmt = stmt.order_by(Valuation.created_at.desc())  # type: ignore[attr-defined]
    return session.exec(stmt).first()


def load_quality_factors(
    session: Session, company: Company, as_of: date | None = None
) -> list[QualityFactorRow]:
    """All stored quality/distress factor rows for the given view, newest first.
    Same as-of matching semantics as :func:`load_valuation`."""
    stmt = select(QualityFactorRow).where(QualityFactorRow.company_id == company.id)
    if as_of is None:
        stmt = stmt.where(QualityFactorRow.as_of_date.is_(None))  # type: ignore[attr-defined]
    else:
        stmt = stmt.where(QualityFactorRow.as_of_date == as_of)
    stmt = stmt.order_by(QualityFactorRow.created_at.desc())  # type: ignore[attr-defined]
    return list(session.exec(stmt).all())
