"""Credit Review OS — config-driven loan-review workpaper builder.

Two-layer config (portable per-LOB program + thin engagement overlay) in,
bank-committee-grade KeyBank-styled workbook out. See docs/prd-credit-review-os.md.
"""

from credit_review.config import (
    ConfigError,
    Engagement,
    Loan,
    Program,
    load_engagement,
    load_loans,
    load_program,
)
from credit_review.ingest import (
    DeIdentifiedMart,
    PortfolioFindings,
    ingest_workbook,
)
from credit_review.workbook import (
    build_demo_workbook,
    build_engagement_workbook,
    workbook_bytes,
)

__all__ = [
    "ConfigError", "Engagement", "Loan", "Program",
    "load_engagement", "load_loans", "load_program",
    "build_demo_workbook", "build_engagement_workbook", "workbook_bytes",
    "DeIdentifiedMart", "PortfolioFindings", "ingest_workbook",
]
