"""Fetch SEC data for a ticker and persist it with provenance.

Acquisition + storage only; no metric math happens here (that's build-report).
Raw JSON stays on disk under data/raw/sec/; the DB holds structured rows.
"""

from datetime import UTC, date, datetime

from sqlmodel import Session, select

from stock_helper.connectors.sec import (
    COMPANY_FACTS_URL,
    SUBMISSIONS_URL,
    SecClient,
    archive_document_url,
    filing_index_url,
)
from stock_helper.core.logging import get_logger
from stock_helper.industry.sic_buckets import sic_to_bucket
from stock_helper.normalization.facts import extract_annual_points
from stock_helper.parsing.filing_sections import (
    PARSER_VERSION,
    chunk_section,
    extract_8k_items,
    extract_sections,
    html_to_text,
)
from stock_helper.storage.models import (
    Company,
    CompanyFact,
    Filing,
    FilingDocument,
    FilingSection,
    SecurityIdentifier,
)
from stock_helper.storage.search import rebuild_fts

log = get_logger(__name__)

# Forms worth storing as filing metadata for the MVP.
_INTERESTING_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "DEF 14A", "20-F"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_and_store(
    ticker: str,
    session: Session,
    client: SecClient,
    with_documents: bool = False,
) -> Company:
    """Full fetch for one ticker: identity, filings, selected XBRL facts."""
    ticker = ticker.upper()
    cik = client.ticker_to_cik(ticker)
    now = datetime.now(UTC)

    submissions = client.fetch_submissions(cik)
    company = _upsert_company(session, cik, submissions, now)
    _upsert_ticker(session, company, ticker, submissions, now)
    filings = _upsert_filings(session, company, cik, submissions, now)
    log.info("stored filings ticker=%s count=%d", ticker, len(filings))

    facts_json = client.fetch_company_facts(cik)
    n_facts = _store_selected_facts(session, company, cik, facts_json, now)
    log.info("stored facts ticker=%s rows=%d", ticker, n_facts)

    if with_documents:
        _fetch_primary_documents(session, client, company, cik, now)

    session.commit()
    return company


def _upsert_company(session: Session, cik: int, submissions: dict, now: datetime) -> Company:
    company = session.exec(select(Company).where(Company.cik == cik)).first()
    sic = str(submissions.get("sic") or "") or None
    if company is None:
        company = Company(cik=cik, name=submissions.get("name", ""))
        session.add(company)
    company.name = submissions.get("name", company.name)
    company.sic = sic
    company.sic_description = submissions.get("sicDescription")
    company.industry_bucket = sic_to_bucket(sic)
    company.fiscal_year_end = submissions.get("fiscalYearEnd")
    company.entity_type = submissions.get("entityType")
    company.state_of_incorporation = submissions.get("stateOfIncorporation")
    company.source_url = SUBMISSIONS_URL.format(cik=cik)
    company.retrieved_at = now
    session.flush()
    return company


def _upsert_ticker(
    session: Session, company: Company, ticker: str, submissions: dict, now: datetime
) -> None:
    existing = session.exec(
        select(SecurityIdentifier).where(
            SecurityIdentifier.company_id == company.id,
            SecurityIdentifier.ticker == ticker,
        )
    ).first()
    exchanges = submissions.get("exchanges") or []
    tickers = [t.upper() for t in (submissions.get("tickers") or [])]
    exchange = None
    if ticker in tickers and len(exchanges) > tickers.index(ticker):
        exchange = exchanges[tickers.index(ticker)]
    if existing is None:
        session.add(
            SecurityIdentifier(
                company_id=company.id,
                ticker=ticker,
                exchange=exchange,
                retrieved_at=now,
            )
        )
    else:
        existing.exchange = exchange or existing.exchange
        existing.retrieved_at = now


def _upsert_filings(
    session: Session, company: Company, cik: int, submissions: dict, now: datetime
) -> list[Filing]:
    """Store recent filings of interesting forms. The submissions API inlines
    ~1000 recent filings; older history is behind pagination files (deferred)."""
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    stored: list[Filing] = []
    existing_accessions = set(
        session.exec(select(Filing.accession).where(Filing.company_id == company.id)).all()
    )
    for i, accession in enumerate(accessions):
        form = recent.get("form", [""] * len(accessions))[i]
        if form not in _INTERESTING_FORMS:
            continue
        if accession in existing_accessions:
            continue
        primary_doc = _get(recent, "primaryDocument", i)
        filing = Filing(
            company_id=company.id,
            accession=accession,
            form=form,
            filed_date=_parse_date(_get(recent, "filingDate", i)) or date.min,
            acceptance_datetime=_parse_datetime(_get(recent, "acceptanceDateTime", i)),
            period_end=_parse_date(_get(recent, "reportDate", i)),
            primary_document=primary_doc,
            primary_doc_description=_get(recent, "primaryDocDescription", i),
            is_xbrl=bool(_get(recent, "isXBRL", i)),
            is_amendment=form.endswith("/A"),
            index_url=filing_index_url(cik, accession),
            primary_document_url=(
                archive_document_url(cik, accession, primary_doc) if primary_doc else None
            ),
            retrieved_at=now,
        )
        session.add(filing)
        stored.append(filing)
    session.flush()
    return stored


def _get(recent: dict, key: str, i: int):
    values = recent.get(key)
    return values[i] if values and i < len(values) else None


def _store_selected_facts(
    session: Session, company: Company, cik: int, facts_json: dict, now: datetime
) -> int:
    """Replace this company's fact rows with the current extraction output.

    Stores ALL annual facts for all candidate tags — including superseded
    values from earlier filings — so point-in-time (as-of) replay can later
    reconstruct originally-filed views from the database alone. Tag selection
    and dedupe happen at read time (normalization.facts.select_annual_series).
    Full raw JSON remains cached on disk for re-parsing."""
    points = extract_annual_points(facts_json)
    for row in session.exec(
        select(CompanyFact).where(CompanyFact.company_id == company.id)
    ).all():
        session.delete(row)
    source_url = COMPANY_FACTS_URL.format(cik=cik)
    for point in points:
        session.add(
            CompanyFact(
                company_id=company.id,
                metric_key=point.metric_key,
                taxonomy=point.taxonomy,
                tag=point.tag,
                unit=point.unit,
                value=point.value,
                period_start=point.period_start,
                period_end=point.period_end,
                fiscal_year=point.fiscal_year,
                fiscal_period=point.fiscal_period,
                form=point.form,
                accession=point.accession,
                filed_date=point.filed,
                source_url=source_url,
                retrieved_at=now,
            )
        )
    return len(points)


def _fetch_primary_documents(
    session: Session, client: SecClient, company: Company, cik: int, now: datetime
) -> None:
    """Download recent primary documents and extract sections.

    Two most recent 10-Ks (so risk-factor novelty can compare year over year),
    the latest 10-Q, and the latest 8-K (item extraction)."""
    targets: list[Filing] = []
    for form, count in (("10-K", 2), ("10-Q", 1), ("8-K", 1)):
        targets.extend(
            session.exec(
                select(Filing)
                .where(Filing.company_id == company.id, Filing.form == form)
                .order_by(Filing.filed_date.desc())  # type: ignore[attr-defined]
                .limit(count)
            ).all()
        )
    for filing in targets:
        if not filing.primary_document:
            continue
        try:
            html = client.fetch_archive_document(cik, filing.accession, filing.primary_document)
        except Exception as exc:
            log.warning("document fetch failed accession=%s err=%s", filing.accession, exc)
            continue
        document = session.exec(
            select(FilingDocument).where(
                FilingDocument.filing_id == filing.id,
                FilingDocument.filename == filing.primary_document,
            )
        ).first()
        if document is None:
            document = FilingDocument(
                filing_id=filing.id,
                filename=filing.primary_document,
                description=filing.primary_doc_description,
                doc_type=filing.form,
                url=filing.primary_document_url or "",
                retrieved_at=now,
            )
            session.add(document)
            session.flush()
        # Re-extract: drop this filing's old sections (parser may have changed).
        for old in session.exec(
            select(FilingSection).where(FilingSection.filing_id == filing.id)
        ).all():
            session.delete(old)
        text = html_to_text(html)
        sections = (
            extract_8k_items(text) if filing.form.startswith("8-K") else extract_sections(text)
        )
        for section in sections:
            for chunk in chunk_section(section, filing.accession):
                session.add(
                    FilingSection(
                        filing_id=filing.id,
                        document_id=document.id,
                        section_name=chunk.section_name,
                        chunk_id=chunk.chunk_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        parser_version=PARSER_VERSION,
                        created_at=now,
                    )
                )
        log.info(
            "sections extracted accession=%s form=%s found=%s",
            filing.accession, filing.form, [s.section_name for s in sections] or "none",
        )
    session.flush()
    rebuild_fts(session)
