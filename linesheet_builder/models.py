from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class LoanRecord(BaseModel):
    loan_record_id: Optional[int] = None
    engagement_id: Optional[int] = None
    import_batch_id: Optional[int] = None
    loan_id: Optional[str] = None
    borrower_name: Optional[str] = None
    product_type: Optional[str] = None
    commitment_amount: Optional[float] = None
    outstanding_balance: Optional[float] = None
    origination_date: Optional[Any] = None
    maturity_date: Optional[Any] = None
    risk_rating: Optional[Any] = None
    officer: Optional[str] = None
    collateral_type: Optional[str] = None
    guarantor_name: Optional[str] = None
    approval_date: Optional[Any] = None
    approval_authority: Optional[str] = None
    financial_statement_date: Optional[Any] = None
    dscr: Optional[float] = None
    ltv: Optional[float] = None
    covenant_status: Optional[str] = None
    past_due_days: Optional[int] = None
    nonaccrual_flag: Optional[Any] = None
    policy_exception_flag: Optional[Any] = None
    review_sample_id: Optional[str] = None
    raw_payload_json: Optional[str] = None
    validation_status: str = "Needs Review"

class ValidationIssue(BaseModel):
    loan_record_id: Optional[int] = None
    severity: str
    status: str
    issue_code: str
    issue_message: str
    field_name: Optional[str] = None

class TemplateQuestion(BaseModel):
    display_order: int
    question_id: str
    question_text: str
    answer_type: str
    required: bool = False
    source_field: Optional[str] = None
    help_text: Optional[str] = None
    applies_if: Optional[str] = None
    exception_if: Optional[str] = None
    warning_if: Optional[str] = None
    severity: str = "Warning"
    evidence_required_if: Optional[str] = None
    data_mart_field: Optional[str] = None
    export_label: Optional[str] = None
    options: List[str] = Field(default_factory=list)

class TemplateSection(BaseModel):
    section_id: str
    section_name: str
    display_order: int
    questions: List[TemplateQuestion]

class Template(BaseModel):
    template_id: str
    template_name: str
    version: str
    sections: List[TemplateSection]
    modules: List[str] = Field(default_factory=list)  # calc tabs; empty = all

class ReviewCase(BaseModel):
    review_case_id: Optional[int] = None
    engagement_id: int
    loan_record_id: int
    status: str = "Not Started"
    assigned_reviewer: Optional[str] = None
    qc_reviewer: Optional[str] = None

class ReviewAnswer(BaseModel):
    review_case_id: int
    question_id: str
    section_id: str
    answer_value: Optional[str] = None
    source_field: Optional[str] = None
    source_value: Optional[str] = None
    answer_status: str = "Incomplete"
    severity: Optional[str] = None
    reviewer_comment: Optional[str] = None
    evidence_required: bool = False
    evidence_status: str = "Not Required"
    answered_by: Optional[str] = None

class ExceptionRecord(BaseModel):
    review_case_id: int
    loan_record_id: int
    question_id: str
    section_id: str
    issue_text: str
    severity: str
    status: str = "Open"
    reviewer_comment: Optional[str] = None
    evidence_status: str = "Not Required"

class ExportResult(BaseModel):
    export_type: str
    file_path: str
    export_status: str
    message: str = ""
