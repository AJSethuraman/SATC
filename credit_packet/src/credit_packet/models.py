from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class CompanyIdentity:
    ticker: str
    cik: str
    name: str

@dataclass
class FilingRecord:
    accession_number: str
    form: str
    filing_date: str | None = None
    report_date: str | None = None
    primary_document: str | None = None
    filing_url: str | None = None
    source: str = ""

@dataclass
class FinancialPeriod:
    fiscal_year: int
    period: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    cash_and_equivalents: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    stockholders_equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    shares_outstanding: float | None = None
    tag_map: dict[str, str] = field(default_factory=dict)

@dataclass
class CalculatedMetric:
    fiscal_year: int
    revenue_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    current_ratio: float | None = None
    debt_to_equity: float | None = None
    operating_cash_flow_margin: float | None = None
    free_cash_flow: float | None = None
    free_cash_flow_margin: float | None = None
    cash_change_pct: float | None = None
    debt_change_pct: float | None = None

@dataclass
class WatchlistFlag:
    code: str
    severity: Literal["info", "low", "medium", "high"]
    description: str
    metric: str
    threshold: str
    observed_value: str
    period: str
    source: str
    requires_manual_review: bool = True
    evidence_id: str | None = None
    excerpt_preview: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    filing: str | None = None
    section: str | None = None
    source_url: str | None = None

@dataclass
class Excerpt:
    filing: str
    section: str
    category: str
    text: str
    matched_keywords: list[str]
    source_url: str
    accession_number: str
    filing_date: str
    start_offset: int | None = None
    end_offset: int | None = None

@dataclass
class FilingChange:
    section: str
    category: str
    old_excerpt: str
    new_excerpt: str
    change_type: Literal["added", "removed", "modified"]
    similarity_score: float
    source_old: str
    source_new: str



@dataclass
class BriefPoint:
    text: str
    sources: list[str] = field(default_factory=list)

@dataclass
class ReviewTheme:
    theme: str
    why_it_matters: str
    sources: list[str] = field(default_factory=list)

@dataclass
class ReviewQuestionItem:
    question: str
    based_on: list[str] = field(default_factory=list)

@dataclass
class MissingInformation:
    item: str
    reason: str

@dataclass
class SourceBoundBrief:
    summary_points: list[BriefPoint] = field(default_factory=list)
    review_themes: list[ReviewTheme] = field(default_factory=list)
    review_questions: list[ReviewQuestionItem] = field(default_factory=list)
    missing_information: list[MissingInformation] = field(default_factory=list)
    generation_mode: str = 'deterministic'
    validation_status: str = 'ok'
    validation_notes: list[str] = field(default_factory=list)

@dataclass
class ResearchPacket:
    company: CompanyIdentity
    filings: list[FilingRecord] = field(default_factory=list)
    financial_periods: list[FinancialPeriod] = field(default_factory=list)
    calculated_metrics: list[CalculatedMetric] = field(default_factory=list)
    watchlist_flags: list[WatchlistFlag] = field(default_factory=list)
    excerpts: list[Excerpt] = field(default_factory=list)
    filing_changes: list[FilingChange] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)
    memo_draft: str = ""
    audit_log: list[str] = field(default_factory=list)
    source_bound_brief: SourceBoundBrief | None = None
    evidence_bundle: dict | None = None
