"""Database tables (SQLModel).

Provenance policy: every row that stores externally sourced data carries
``source`` (short id like "sec_submissions"), a ``source_url`` or accession,
and ``retrieved_at``. Rows derived by our own code additionally carry a
``parser_version`` / ``formula`` so results can be reproduced or invalidated
when parsers change. Facts carry both fiscal ``period_end`` and ``filed_date``
so a future backtester can replay what was knowable when (point-in-time).
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Company(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cik: int = Field(index=True, unique=True)
    name: str
    sic: str | None = None
    sic_description: str | None = None
    industry_bucket: str = "other"
    fiscal_year_end: str | None = None  # "MMDD" as reported by SEC
    entity_type: str | None = None
    state_of_incorporation: str | None = None

    source: str = "sec_submissions"
    source_url: str = ""
    retrieved_at: datetime | None = None


class SecurityIdentifier(SQLModel, table=True):
    """Ticker/exchange rows. Schema anticipates historical validity ranges;
    v0.1 only stores current SEC mappings (effective_from/to left null)."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    exchange: str | None = None
    is_primary: bool = True
    effective_from: date | None = None
    effective_to: date | None = None

    source: str = "sec_company_tickers"
    source_url: str = ""
    retrieved_at: datetime | None = None


class Filing(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    accession: str = Field(index=True, unique=True)
    form: str = Field(index=True)
    filed_date: date
    acceptance_datetime: datetime | None = None
    period_end: date | None = None
    primary_document: str | None = None
    primary_doc_description: str | None = None
    is_xbrl: bool = False
    is_amendment: bool = False
    index_url: str = ""
    primary_document_url: str | None = None

    source: str = "sec_submissions"
    retrieved_at: datetime | None = None


class FilingDocument(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filing_id: int = Field(foreign_key="filing.id", index=True)
    filename: str
    description: str | None = None
    doc_type: str | None = None
    url: str = ""
    local_path: str | None = None

    source: str = "sec_archives"
    retrieved_at: datetime | None = None


class FilingSection(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filing_id: int = Field(foreign_key="filing.id", index=True)
    document_id: int | None = Field(default=None, foreign_key="filingdocument.id")
    section_name: str = Field(index=True)  # e.g. "mdna", "risk_factors"
    chunk_id: str = Field(index=True, unique=True)  # "{accession}:{section}:{n}"
    chunk_index: int = 0
    text: str
    char_start: int = 0
    char_end: int = 0

    parser_version: str = ""
    source: str = "sec_archives"
    created_at: datetime | None = None


class CompanyFact(SQLModel, table=True):
    """Selected raw XBRL facts, near as-filed. The full raw JSON stays on disk
    under data/raw/sec/; these rows are the subset our canonical metrics use."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    metric_key: str = Field(index=True)  # canonical metric this fact was selected for
    taxonomy: str  # "us-gaap" | "dei"
    tag: str
    unit: str
    value: float
    period_start: date | None = None
    period_end: date = Field(index=True)
    fiscal_year: int | None = None
    fiscal_period: str | None = None  # "FY", "Q1"...
    form: str = ""
    accession: str = ""
    filed_date: date | None = None

    source: str = "sec_companyfacts"
    source_url: str = ""
    retrieved_at: datetime | None = None


class FinancialMetric(SQLModel, table=True):
    """Derived canonical metrics (per fiscal period), computed by features/."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    metric_key: str = Field(index=True)
    period_end: date = Field(index=True)
    value: float
    unit: str = ""
    formula: str = ""  # human-readable, e.g. "operating_income / revenue"
    input_tags: str = ""  # comma-separated source XBRL tags
    input_accessions: str = ""  # comma-separated accessions

    parser_version: str = ""
    created_at: datetime | None = None


class SignalDefinitionRow(SQLModel, table=True):
    """Audit snapshot of the code-registered signal definitions (signals/definitions.py)."""

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str
    category: str
    description: str
    formula: str = ""
    applicability: str = ""  # human-readable bucket rule
    implemented: bool = True
    version: str = ""
    created_at: datetime | None = None


class ReportRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    created_at: datetime
    # Point-in-time view date. None = current restated view; set = the report
    # was built only from facts/filings filed on or before this date.
    as_of_date: date | None = None
    app_version: str = ""
    parser_version: str = ""
    output_path: str | None = None
    notes: str = ""


class SignalResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    report_run_id: int = Field(foreign_key="reportrun.id", index=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    signal_key: str = Field(index=True)
    category: str = ""
    status: str = "OK"  # OK | NOT_APPLICABLE | INSUFFICIENT_DATA | UNAVAILABLE | PLACEHOLDER
    value_text: str = ""
    numeric_value: float | None = None
    direction: str = ""  # improving | deteriorating | stable | mixed | ""
    score: int | None = None  # -2..+2, ordering/badges only — not an expected return
    interpretation: str = ""
    confidence: str = ""  # high | medium | low
    caveat: str = ""
    created_at: datetime | None = None


class EvidenceReference(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    signal_result_id: int = Field(foreign_key="signalresult.id", index=True)
    kind: str = "fact"  # fact | filing | section | url
    reference: str = ""  # accession, chunk_id, or URL
    description: str = ""
    source_url: str | None = None


class SignalHistory(SQLModel, table=True):
    """What each signal said at a past as-of date (point-in-time replay).

    Rows are produced by `stock-helper signal-history` and are the raw material
    for Phase 7 calibration. They record signal output only — outcome labels
    live in ForwardReturn so signals and outcomes stay separable."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    as_of_date: date = Field(index=True)
    signal_key: str = Field(index=True)
    category: str = ""
    status: str = ""
    direction: str = ""
    score: int | None = None
    numeric_value: float | None = None
    value_text: str = ""
    confidence: str = ""
    engine_version: str = ""
    created_at: datetime | None = None


class ForwardReturn(SQLModel, table=True):
    """Realized price return after an as-of date (exploratory outcome label).

    Computed from the optional NON-CANONICAL price source (Stooq). Not adjusted
    for costs, dividends handling depends on the source, and no survivorship
    guarantees — usable for rough calibration exploration only, never as a
    performance claim."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    as_of_date: date = Field(index=True)
    horizon_days: int  # trading days
    entry_date: date
    exit_date: date
    ret: float  # simple return, exit close / entry close - 1
    source: str = "stooq_noncanonical"
    retrieved_at: datetime | None = None


class Valuation(SQLModel, table=True):
    """One valuation run for a company (mirrors ReportRun). Every scenario number
    is reproducible from the child ValuationAssumption rows."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    as_of_date: date | None = None
    method: str = ""  # "dcf" | "ddm+justified_pb"
    metric_set: str = ""  # "industrial" | "financial"
    fair_value_per_share: float | None = None
    equity_value: float | None = None
    enterprise_value: float | None = None
    price: float | None = None
    margin_of_safety: float | None = None
    discount_rate: float | None = None
    terminal_growth: float | None = None
    base_fcf: float | None = None
    implied_growth: float | None = None  # reverse-DCF
    caveats: str = ""  # joined
    engine_version: str = ""
    created_at: datetime | None = None


class ValuationAssumption(SQLModel, table=True):
    """Every input/assumption behind a Valuation (mirrors EvidenceReference)."""

    id: int | None = Field(default=None, primary_key=True)
    valuation_id: int = Field(foreign_key="valuation.id", index=True)
    name: str
    value: float | None = None
    text_value: str = ""
    unit: str = ""
    note: str = ""


class ValuationMultiple(SQLModel, table=True):
    """A market/relative multiple computed in a Valuation run."""

    id: int | None = Field(default=None, primary_key=True)
    valuation_id: int = Field(foreign_key="valuation.id", index=True)
    multiple_key: str  # ev_ebit, pe, p_b, earnings_yield...
    value: float | None = None
    peer_median: float | None = None
    implied_price: float | None = None
    upside_pct: float | None = None
    history_zscore: float | None = None
    undefined_reason: str = ""  # e.g. "negative EBIT"


class QualityFactorRow(SQLModel, table=True):
    """One quality/distress factor for a company at an as-of date (mirrors
    SignalHistory — replayable point-in-time)."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    ticker: str = Field(index=True)
    as_of_date: date | None = None
    factor_key: str = Field(index=True)  # piotroski_f, altman_z, gross_profitability...
    value: float | None = None
    unit: str = ""
    percentile: float | None = None  # within-bucket local percentile
    zone: str = ""  # e.g. Altman safe/grey/distress
    formula: str = ""
    detail: str = ""  # json blob of components
    engine_version: str = ""
    created_at: datetime | None = None


class QualityComponent(SQLModel, table=True):
    """A sub-component of a QualityFactorRow (e.g. one Piotroski test)."""

    id: int | None = Field(default=None, primary_key=True)
    quality_factor_row_id: int = Field(foreign_key="qualityfactorrow.id", index=True)
    name: str
    value: float | None = None
    unit: str = ""
    note: str = ""


class UserNote(SQLModel, table=True):
    """Placeholder for Phase 6+. Notes are first-party data with provenance."""

    id: int | None = Field(default=None, primary_key=True)
    company_id: int | None = Field(default=None, foreign_key="company.id", index=True)
    ticker: str | None = None
    author: str = "local"
    created_at: datetime | None = None
    text: str = ""
    tags: str = ""
