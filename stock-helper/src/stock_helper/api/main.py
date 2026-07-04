"""FastAPI layer: read-only JSON views over stored data.

Thin by design in v0.1 — the Streamlit UI reads the DB directly; this API
exists so other tools (or a future web UI) can consume the same data.
"""

from fastapi import FastAPI, HTTPException
from sqlmodel import select

import stock_helper
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import (
    Company,
    Filing,
    FinancialMetric,
    ReportRun,
    SecurityIdentifier,
    SignalResult,
)

api = FastAPI(
    title="stock-helper API",
    version=stock_helper.__version__,
    description="Evidence-backed stock research data. Research aid — not investment advice.",
)


@api.on_event("startup")
def _startup() -> None:
    init_db()


def _company_or_404(session, ticker: str) -> Company:
    identifier = session.exec(
        select(SecurityIdentifier).where(SecurityIdentifier.ticker == ticker.upper())
    ).first()
    if identifier is None:
        raise HTTPException(404, f"No data for {ticker!r}; run stock-helper fetch-sec {ticker}")
    return session.get(Company, identifier.company_id)


@api.get("/health")
def health() -> dict:
    return {"status": "ok", "version": stock_helper.__version__}


@api.get("/companies")
def companies() -> list[dict]:
    with get_session() as session:
        rows = session.exec(select(SecurityIdentifier, Company).join(Company)).all()
        return [
            {
                "ticker": identifier.ticker,
                "name": company.name,
                "cik": company.cik,
                "industry_bucket": company.industry_bucket,
            }
            for identifier, company in rows
        ]


@api.get("/companies/{ticker}")
def company(ticker: str) -> dict:
    with get_session() as session:
        row = _company_or_404(session, ticker)
        return row.model_dump()


@api.get("/companies/{ticker}/filings")
def filings(ticker: str) -> list[dict]:
    with get_session() as session:
        row = _company_or_404(session, ticker)
        items = session.exec(
            select(Filing)
            .where(Filing.company_id == row.id)
            .order_by(Filing.filed_date.desc())  # type: ignore[attr-defined]
            .limit(50)
        ).all()
        return [f.model_dump() for f in items]


@api.get("/companies/{ticker}/metrics")
def metrics(ticker: str) -> list[dict]:
    with get_session() as session:
        row = _company_or_404(session, ticker)
        items = session.exec(
            select(FinancialMetric).where(FinancialMetric.company_id == row.id)
        ).all()
        return [m.model_dump() for m in items]


@api.get("/companies/{ticker}/signals")
def signals(ticker: str) -> dict:
    """Signal results from the latest report run."""
    with get_session() as session:
        row = _company_or_404(session, ticker)
        run = session.exec(
            select(ReportRun)
            .where(ReportRun.company_id == row.id)
            .order_by(ReportRun.created_at.desc())  # type: ignore[attr-defined]
        ).first()
        if run is None:
            raise HTTPException(404, f"No report run yet; run stock-helper build-report {ticker}")
        results = session.exec(
            select(SignalResult).where(SignalResult.report_run_id == run.id)
        ).all()
        return {
            "run": run.model_dump(),
            "disclaimer": "Research aid, not investment advice. Signals are descriptive rules, not predictions.",
            "signals": [s.model_dump() for s in results],
        }
