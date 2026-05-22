from __future__ import annotations

from decimal import Decimal

from dea.models import (
    Address,
    Client,
    ClientBatch,
    Employer,
    SourceCellRef,
    Spouse,
    Taxpayer,
    W2,
    W2Box12Item,
    W2StateLine,
)
from dea.validation import validate_client_batch


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def _base_client() -> Client:
    taxpayer = Taxpayer("Alex", "Rivera", _id_from_parts("123", "45", "6789"), "1988-04-14", "Engineer")
    spouse = Spouse("Jordan", "Rivera", _id_from_parts("111", "22", "3333"), "1990-11-30", "Teacher")
    addr = Address("100 Main St", "Springfield", "IL", "62701")
    employer = Employer(_id_from_parts("12", "345", "6789"), "Acme", "500 Market Ave", "Springfield", "IL", "62702")
    w2 = W2(
        w2_id="W2-001",
        client_id="C-001",
        employee=taxpayer,
        employer=employer,
        box_1_wages=Decimal("100"),
        box_2_federal_withholding=Decimal("10"),
        box_3_social_security_wages=Decimal("100"),
        box_4_social_security_tax=Decimal("6.2"),
        box_5_medicare_wages=Decimal("100"),
        box_6_medicare_tax=Decimal("1.45"),
        box_1_raw="100",
        box_2_raw="10",
        box_3_raw="100",
        box_4_raw="6.2",
        box_5_raw="100",
        box_6_raw="1.45",
        box_12_items=[W2Box12Item(code="D", amount=Decimal("50"))],
        state_lines=[W2StateLine(state="IL", employer_state_id="IL-ID", state_wages=Decimal("100"), state_withholding=Decimal("5"))],
    )
    return Client("C-001", 2025, "MFJ", taxpayer, spouse, addr, [w2])


def _errors(batch: ClientBatch):
    return [i for i in validate_client_batch(batch) if i.severity == "ERROR"]


def test_valid_client_no_errors() -> None:
    errs = _errors(ClientBatch([_base_client()]))
    assert errs == []


def test_screen1_error_cases() -> None:
    c = _base_client(); c.taxpayer.first_name = ""; assert any(i.field == "taxpayer.first_name" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.taxpayer.ssn = "12"; assert any(i.field == "taxpayer.ssn" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.taxpayer.dob = ""; assert any(i.field == "taxpayer.dob" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.taxpayer.dob = "2025-99-99"; assert any(i.field == "taxpayer.dob" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.filing_status = "BAD"; assert any(i.field == "filing_status" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.address.state = "ZZ"; assert any(i.field == "address.state" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.address.zip = "12"; assert any(i.field == "address.zip" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.spouse = None; assert any(i.field == "spouse" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.spouse.ssn = "22"; assert any(i.field == "spouse.ssn" for i in _errors(ClientBatch([c])))
    c = _base_client(); c.spouse.dob = "bad"; assert any(i.field == "spouse.dob" for i in _errors(ClientBatch([c])))


def test_w2_error_cases_and_warnings() -> None:
    c = _base_client(); c.w2s[0].employer.ein = ""; assert any("employer.ein" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].employer.ein = "12"; assert any("employer.ein" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].employer.name = ""; assert any("employer.name" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].box_1_raw = "abc"; assert any("box_1_wages" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].box_1_wages = Decimal("10"); c.w2s[0].box_2_federal_withholding = Decimal("20"); assert any("box_2_federal_withholding" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].state_lines[0].state = ""; assert any("state_lines.state" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].state_lines[0].state_wages = Decimal("0"); assert any("state_lines.state_wages" in i.field for i in _errors(ClientBatch([c])))
    c = _base_client(); c.w2s[0].box_12_items = [W2Box12Item(code="QQ", amount=Decimal("1"))]
    issues = validate_client_batch(ClientBatch([c]))
    assert any(i.severity == "WARNING" and "box_12_items.code" in i.field for i in issues)


def test_source_cells_attached_when_provided() -> None:
    c = _base_client()
    c.taxpayer.first_name = ""
    refs = {"clients.C-001.taxpayer.first_name": SourceCellRef(sheet="Clients", cell="D2")}
    issues = validate_client_batch(ClientBatch([c]), source_cells=refs)
    issue = next(i for i in issues if i.field == "taxpayer.first_name")
    assert issue.source_sheet == "Clients"
    assert issue.source_cell == "D2"


def test_source_cells_attached_for_expected_client_and_w2_fields() -> None:
    c = _base_client()
    c.taxpayer.first_name = ""
    c.taxpayer.ssn = "12"
    c.address.zip = "12"
    c.w2s[0].employer.ein = "1"
    c.w2s[0].box_1_raw = "bad"
    c.w2s[0].box_2_raw = "bad"

    refs = {
        "clients.C-001.taxpayer.first_name": SourceCellRef(sheet="Clients", cell="D2"),
        "clients.C-001.taxpayer.ssn": SourceCellRef(sheet="Clients", cell="F2"),
        "clients.C-001.address.zip": SourceCellRef(sheet="Clients", cell="Q2"),
        "clients.C-001.w2s.W2-001.employer.ein": SourceCellRef(sheet="W2s", cell="D2"),
        "clients.C-001.w2s.W2-001.box_1_wages": SourceCellRef(sheet="W2s", cell="J2"),
        "clients.C-001.w2s.W2-001.box_2_federal_withholding": SourceCellRef(sheet="W2s", cell="K2"),
    }

    issues = validate_client_batch(ClientBatch([c]), source_cells=refs)

    first_name = next(i for i in issues if i.field == "taxpayer.first_name")
    assert (first_name.source_sheet, first_name.source_cell) == ("Clients", "D2")

    ssn = next(i for i in issues if i.field == "taxpayer.ssn")
    assert (ssn.source_sheet, ssn.source_cell) == ("Clients", "F2")

    zip_issue = next(i for i in issues if i.field == "address.zip")
    assert (zip_issue.source_sheet, zip_issue.source_cell) == ("Clients", "Q2")

    ein_issue = next(i for i in issues if i.field == "w2s.W2-001.employer.ein")
    assert (ein_issue.source_sheet, ein_issue.source_cell) == ("W2s", "D2")

    box1_issue = next(i for i in issues if i.field == "w2s.W2-001.box_1_wages")
    assert (box1_issue.source_sheet, box1_issue.source_cell) == ("W2s", "J2")

    box2_issue = next(i for i in issues if i.field == "w2s.W2-001.box_2_federal_withholding")
    assert (box2_issue.source_sheet, box2_issue.source_cell) == ("W2s", "K2")
