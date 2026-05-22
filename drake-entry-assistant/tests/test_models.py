"""Model relationship and instantiation tests."""

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

from dea.models import (
    ActionPlan,
    ActionStep,
    Address,
    Client,
    ClientBatch,
    Employer,
    EntryLogRecord,
    Spouse,
    Taxpayer,
    ValidationIssue,
    W2,
    W2Box12Item,
    W2StateLine,
)


def _build_taxpayer() -> Taxpayer:
    return Taxpayer(
        first_name="Alex",
        last_name="Rivera",
        ssn="***-**-1234",
        dob="1988-04-14",
        occupation="Engineer",
    )


def _build_spouse() -> Spouse:
    return Spouse(
        first_name="Jordan",
        last_name="Rivera",
        ssn="***-**-5678",
        dob="1990-11-30",
        occupation="Teacher",
    )


def _build_address() -> Address:
    return Address(
        street="100 Main St",
        city="Springfield",
        state="IL",
        zip="62701",
    )


def _build_employer() -> Employer:
    return Employer(
        ein="**-***6789",
        name="Acme Fabrication LLC",
        street="500 Market Ave",
        city="Springfield",
        state="IL",
        zip="62702",
    )


def _build_w2(client_id: str, employee: Taxpayer | Spouse) -> W2:
    return W2(
        w2_id="W2-001",
        client_id=client_id,
        employee=employee,
        employer=_build_employer(),
        box_1_wages=Decimal("72000.00"),
        box_2_federal_withholding=Decimal("8500.00"),
        box_3_social_security_wages=Decimal("72000.00"),
        box_4_social_security_tax=Decimal("4464.00"),
        box_5_medicare_wages=Decimal("72000.00"),
        box_6_medicare_tax=Decimal("1044.00"),
        box_12_items=[W2Box12Item(code="D", amount=Decimal("3000.00"))],
        state_lines=[
            W2StateLine(
                state="IL",
                employer_state_id="IL-STATE-ID",
                state_wages=Decimal("72000.00"),
                state_withholding=Decimal("3200.00"),
            )
        ],
        manual_review_notes=["Verify local tax not present."],
    )


def test_client_batch_can_contain_one_client() -> None:
    taxpayer = _build_taxpayer()
    client = Client(
        client_id="C-001",
        tax_year=2025,
        filing_status="MFJ",
        taxpayer=taxpayer,
        spouse=None,
        address=_build_address(),
        w2s=[_build_w2("C-001", taxpayer)],
    )
    batch = ClientBatch(clients=[client])

    assert len(batch.clients) == 1
    assert batch.clients[0].client_id == "C-001"


def test_client_relationships_with_optional_spouse_and_w2s() -> None:
    taxpayer = _build_taxpayer()
    spouse = _build_spouse()
    w2_primary = _build_w2("C-002", taxpayer)
    w2_spouse = _build_w2("C-002", spouse)

    client = Client(
        client_id="C-002",
        tax_year=2025,
        filing_status="MFJ",
        taxpayer=taxpayer,
        spouse=spouse,
        address=_build_address(),
        w2s=[w2_primary, w2_spouse],
    )

    assert client.spouse is not None
    assert client.address.city == "Springfield"
    assert len(client.w2s) >= 1


def test_w2_contains_employer_box12_and_state_lines() -> None:
    taxpayer = _build_taxpayer()
    w2 = _build_w2("C-003", taxpayer)

    assert w2.employer.name == "Acme Fabrication LLC"
    assert len(w2.box_12_items) == 1
    assert w2.box_12_items[0].code == "D"
    assert len(w2.state_lines) == 1
    assert w2.state_lines[0].state == "IL"


def test_validation_issue_supports_all_required_severities() -> None:
    severities = ["ERROR", "WARNING", "INFO"]
    issues = [
        ValidationIssue(
            severity=severity,  # type: ignore[arg-type]
            client_id="C-004",
            field="taxpayer.ssn",
            message="Example issue",
            source_sheet="Intake",
            source_cell="B2",
        )
        for severity in severities
    ]

    assert [issue.severity for issue in issues] == severities


def test_action_plan_contains_ordered_steps() -> None:
    step1 = ActionStep(
        action="ENTER_FIELD",
        screen="SCRN1",
        field="taxpayer.first_name",
        value="Alex",
        masked_value="Alex",
        source_sheet="Taxpayer",
        source_cell="A2",
        support_status="SUPPORTED",
    )
    step2 = ActionStep(
        action="ENTER_FIELD",
        screen="SCRN1",
        field="taxpayer.ssn",
        value="***-**-1234",
        masked_value="***-**-1234",
        source_sheet="Taxpayer",
        source_cell="A3",
        support_status="CONDITIONALLY_SUPPORTED",
    )

    plan = ActionPlan(client_id="C-005", tax_year=2025, steps=[step1, step2])

    assert [step.field for step in plan.steps] == [
        "taxpayer.first_name",
        "taxpayer.ssn",
    ]


def test_entry_log_record_uses_masked_value_for_recording() -> None:
    record = EntryLogRecord(
        timestamp=datetime(2026, 1, 15, 9, 0, tzinfo=UTC),
        client_id="C-006",
        tax_year=2025,
        mode="planned",
        screen="W2IN",
        field="w2.employer.ein",
        source_sheet="W2",
        source_cell="C10",
        masked_value="**-***6789",
        action="ENTER_FIELD",
        status="PLANNED",
        error_message=None,
    )

    assert record.masked_value == "**-***6789"
    assert record.action == "ENTER_FIELD"
