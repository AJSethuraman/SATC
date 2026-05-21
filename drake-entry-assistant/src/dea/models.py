"""Domain models for normalized taxpayer and W-2 data.

This module defines stable internal data structures for client-level tax-entry
workflows. These models are intentionally UI-agnostic and avoid embedding Drake
screen-label dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal


Severity = Literal["ERROR", "WARNING", "INFO"]
SupportStatus = Literal[
    "SUPPORTED",
    "CONDITIONALLY_SUPPORTED",
    "MANUAL_REVIEW",
    "UNSUPPORTED",
    "DEPRECATED",
]
FieldMethod = Literal["tab_order", "control_locator", "manual"]
ActionName = Literal["OPEN_SCREEN", "ENTER_FIELD", "SKIP_MANUAL_REVIEW", "SKIP_UNSUPPORTED"]
EntryStatus = Literal[
    "PLANNED",
    "ENTERED",
    "SKIPPED_MANUAL_REVIEW",
    "SKIPPED_UNSUPPORTED",
    "FAILED_VALIDATION",
    "FAILED_SCREEN_CHECK",
    "FAILED_FIELD_ENTRY",
]


@dataclass(slots=True)
class SourceCellRef:
    sheet: str
    cell: str


@dataclass(slots=True)
class Taxpayer:
    first_name: str
    last_name: str
    ssn: str
    dob: str
    occupation: str | None = None


@dataclass(slots=True)
class Spouse:
    first_name: str
    last_name: str
    ssn: str
    dob: str
    occupation: str | None = None


@dataclass(slots=True)
class Address:
    street: str
    city: str
    state: str
    zip: str


@dataclass(slots=True)
class Employer:
    ein: str
    name: str
    street: str
    city: str
    state: str
    zip: str


@dataclass(slots=True)
class W2Box12Item:
    code: str
    amount: Decimal


@dataclass(slots=True)
class W2StateLine:
    state: str
    employer_state_id: str
    state_wages: Decimal
    state_withholding: Decimal


@dataclass(slots=True)
class W2:
    w2_id: str
    client_id: str
    employee: Taxpayer | Spouse
    employer: Employer
    box_1_wages: Decimal
    box_2_federal_withholding: Decimal
    box_3_social_security_wages: Decimal
    box_4_social_security_tax: Decimal
    box_5_medicare_wages: Decimal
    box_6_medicare_tax: Decimal
    box_1_raw: str = ""
    box_2_raw: str = ""
    box_3_raw: str = ""
    box_4_raw: str = ""
    box_5_raw: str = ""
    box_6_raw: str = ""
    box_12_items: list[W2Box12Item] = field(default_factory=list)
    state_lines: list[W2StateLine] = field(default_factory=list)
    manual_review_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Client:
    client_id: str
    tax_year: int
    filing_status: str
    taxpayer: Taxpayer
    spouse: Spouse | None
    address: Address
    w2s: list[W2] = field(default_factory=list)


@dataclass(slots=True)
class ClientBatch:
    clients: list[Client] = field(default_factory=list)


@dataclass(slots=True)
class LoadedWorkbook:
    client_batch: ClientBatch
    source_cells: dict[str, SourceCellRef] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIssue:
    severity: Severity
    client_id: str
    field: str
    message: str
    source_sheet: str | None = None
    source_cell: str | None = None


@dataclass(slots=True)
class ScreenField:
    field_path: str
    label: str
    source: str
    support_status: SupportStatus
    method: FieldMethod
    position: str | None = None
    locator: str | None = None
    mask_in_log: bool = False


@dataclass(slots=True)
class ScreenMap:
    screen: str
    screen_name: str
    screen_code: str
    tax_year: int | None
    version: str | None
    expected_markers: list[str]
    fields: list[ScreenField] = field(default_factory=list)


@dataclass(slots=True)
class ActionStep:
    action: ActionName
    screen: str
    field: str
    value: str
    masked_value: str
    source_sheet: str | None
    source_cell: str | None
    support_status: SupportStatus
    field_locator: str | None = None


@dataclass(slots=True)
class ActionPlan:
    client_id: str
    tax_year: int
    steps: list[ActionStep] = field(default_factory=list)


@dataclass(slots=True)
class EntryLogRecord:
    timestamp: datetime
    client_id: str
    tax_year: int
    mode: str
    screen: str
    field: str
    source_sheet: str | None
    source_cell: str | None
    masked_value: str
    action: str
    status: EntryStatus
    error_message: str | None = None


@dataclass(slots=True)
class ExecutionResult:
    success: bool
    records: list[EntryLogRecord] = field(default_factory=list)
    error_message: str | None = None
