from dataclasses import dataclass
from typing import Literal

CellKind = Literal['text','date','int','money','pct','ratio','bool','url','long_text']

@dataclass(frozen=True)
class ColumnSpec:
    key: str
    header: str
    kind: CellKind
    width: float
    wrap: bool = False
    hidden: bool = False

@dataclass(frozen=True)
class SheetSpec:
    name: str
    table_name: str | None
    columns: tuple[ColumnSpec, ...]

FILING_ACTIVITY_SPEC = SheetSpec('Filing Activity','tblFilingActivity',(
    ColumnSpec('form','Form','text',12), ColumnSpec('filing_date','Filing Date','date',14), ColumnSpec('report_date','Report Date','date',14),
    ColumnSpec('accession_number','Accession Number','text',24), ColumnSpec('primary_document','Primary Document','text',28),
    ColumnSpec('source_link','Source Link','url',14), ColumnSpec('source_url','Raw Source URL','url',60,hidden=True),
))
FINANCIAL_TRENDS_SPEC = SheetSpec('Financial Trends','tblFinancialTrends',(
    ColumnSpec('fiscal_year','Fiscal Year','int',12), ColumnSpec('revenue','Revenue','money',14), ColumnSpec('gross_profit','Gross Profit','money',14),
    ColumnSpec('operating_income','Operating Income','money',16), ColumnSpec('net_income','Net Income','money',14), ColumnSpec('cash_and_equivalents','Cash & Equivalents','money',18),
    ColumnSpec('current_assets','Current Assets','money',14), ColumnSpec('current_liabilities','Current Liabilities','money',16), ColumnSpec('total_assets','Total Assets','money',14),
    ColumnSpec('total_liabilities','Total Liabilities','money',16), ColumnSpec('stockholders_equity','Stockholders’ Equity','money',18), ColumnSpec('long_term_debt','Long-Term Debt','money',14),
    ColumnSpec('operating_cash_flow','Operating Cash Flow','money',16), ColumnSpec('capex','Capex','money',12), ColumnSpec('free_cash_flow','Free Cash Flow','money',14),
))
CALCULATED_METRICS_SPEC = SheetSpec('Calculated Metrics','tblCalculatedMetrics',(
    ColumnSpec('fiscal_year','Fiscal Year','int',12), ColumnSpec('revenue_growth','Revenue Growth %','pct',14), ColumnSpec('gross_margin','Gross Margin %','pct',14),
    ColumnSpec('operating_margin','Operating Margin %','pct',16), ColumnSpec('net_margin','Net Margin %','pct',14), ColumnSpec('cash_change_pct','Cash Change %','pct',14),
    ColumnSpec('current_ratio','Current Ratio','ratio',12), ColumnSpec('debt_change_pct','Debt Change %','pct',14), ColumnSpec('debt_to_equity','Debt / Equity','ratio',12),
    ColumnSpec('operating_cash_flow_margin','Operating Cash Flow Margin %','pct',20), ColumnSpec('free_cash_flow','Free Cash Flow','money',14), ColumnSpec('free_cash_flow_margin','Free Cash Flow Margin %','pct',20),
))
WATCHLIST_FLAGS_SPEC = SheetSpec('Watchlist Flags','tblWatchlistFlags',(
    ColumnSpec('severity','Severity','text',10), ColumnSpec('code','Flag Code','text',24), ColumnSpec('period','Period / Filing','text',16),
    ColumnSpec('description','Description','long_text',48,wrap=True), ColumnSpec('observed_value','Observed Value','text',16), ColumnSpec('threshold','Threshold','text',14),
    ColumnSpec('source','Source','text',18), ColumnSpec('requires_manual_review','Manual Review Required','bool',20),
))
EXCERPTS_SPEC = SheetSpec('Excerpts','tblExcerpts',(
    ColumnSpec('category','Category','text',14), ColumnSpec('filing','Filing Form','text',12), ColumnSpec('filing_date','Filing Date','date',14), ColumnSpec('section','Section','text',20),
    ColumnSpec('matched_keywords','Matched Keywords','text',24), ColumnSpec('excerpt_preview','Excerpt Preview','long_text',70,wrap=True), ColumnSpec('excerpt_full','Full Excerpt','long_text',90,wrap=True,hidden=True),
    ColumnSpec('source_link','Source Link','url',14), ColumnSpec('source_url','Raw Source URL','url',60,hidden=True), ColumnSpec('accession_number','Accession Number','text',24),
))
FILING_CHANGES_SPEC = SheetSpec('Filing Changes','tblFilingChanges',(
    ColumnSpec('section','Section','text',22), ColumnSpec('category','Category','text',16), ColumnSpec('change_type','Change Type','text',14), ColumnSpec('similarity_score','Similarity Score','ratio',14),
    ColumnSpec('old_preview','Old Preview','long_text',56,wrap=True), ColumnSpec('new_preview','New Preview','long_text',56,wrap=True), ColumnSpec('old_full','Old Full Text','long_text',80,wrap=True,hidden=True),
    ColumnSpec('new_full','New Full Text','long_text',80,wrap=True,hidden=True), ColumnSpec('old_source_link','Old Source Link','url',14), ColumnSpec('new_source_link','New Source Link','url',14),
    ColumnSpec('old_source','Old Source URL','url',60,hidden=True), ColumnSpec('new_source','New Source URL','url',60,hidden=True),
))
REVIEW_QUESTIONS_SPEC = SheetSpec('Review Questions','tblReviewQuestions',(
    ColumnSpec('question_no','Question #','int',12), ColumnSpec('question','Question','long_text',68,wrap=True), ColumnSpec('based_on','Based On','text',28), ColumnSpec('source_trigger','Source / Trigger','text',20), ColumnSpec('priority','Priority','text',12),
))
EVIDENCE_INDEX_SPEC = SheetSpec('Evidence Index','tblEvidenceIndex',(
    ColumnSpec('evidence_id','Evidence ID','text',34), ColumnSpec('type','Type','text',12), ColumnSpec('label','Label / Category','text',24), ColumnSpec('period_or_date','Period / Filing Date','text',18), ColumnSpec('source','Source URL / Source','text',60),
))
SOURCE_BOUND_BRIEF_SPEC = SheetSpec('Source-Bound Brief','tblSourceBoundBrief',(
    ColumnSpec('type','Type','text',18), ColumnSpec('text','Text','long_text',72,wrap=True), ColumnSpec('sources','Sources','text',40), ColumnSpec('generation_mode','Generation Mode','text',16), ColumnSpec('validation_status','Validation Status','text',16),
))
