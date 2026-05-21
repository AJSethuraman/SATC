from __future__ import annotations

from decimal import Decimal

from dea.action_plan import generate_action_plan
from dea.config_loader import load_screen_maps
from dea.models import Address, Client, Employer, SourceCellRef, Spouse, Taxpayer, W2


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def _build_client(two_w2s: bool = False) -> Client:
    taxpayer = Taxpayer("Alex", "Rivera", _id_from_parts("123", "45", "6789"), "1988-04-14", "Engineer")
    spouse = Spouse("Jordan", "Rivera", _id_from_parts("111", "22", "3333"), "1990-11-30", "Teacher")
    address = Address("100 Main St", "Springfield", "IL", "62701")

    w2a = W2(
        w2_id="W2-001",
        client_id="C-001",
        employee=taxpayer,
        employer=Employer(_id_from_parts("12", "345", "6789"), "Acme", "500 Market", "Springfield", "IL", "62702"),
        box_1_wages=Decimal("72000"),
        box_2_federal_withholding=Decimal("8500"),
        box_3_social_security_wages=Decimal("72000"),
        box_4_social_security_tax=Decimal("4464"),
        box_5_medicare_wages=Decimal("72000"),
        box_6_medicare_tax=Decimal("1044"),
        box_1_raw="72000",
        box_2_raw="8500",
        box_3_raw="72000",
        box_4_raw="4464",
        box_5_raw="72000",
        box_6_raw="1044",
    )
    w2s = [w2a]
    if two_w2s:
        w2s.append(
            W2(
                w2_id="W2-002",
                client_id="C-001",
                employee=spouse,
                employer=Employer(_id_from_parts("98", "765", "4321"), "Beta", "900 State", "Springfield", "IL", "62703"),
                box_1_wages=Decimal("12000"),
                box_2_federal_withholding=Decimal("1000"),
                box_3_social_security_wages=Decimal("12000"),
                box_4_social_security_tax=Decimal("744"),
                box_5_medicare_wages=Decimal("12000"),
                box_6_medicare_tax=Decimal("174"),
                box_1_raw="12000",
                box_2_raw="1000",
                box_3_raw="12000",
                box_4_raw="744",
                box_5_raw="12000",
                box_6_raw="174",
            )
        )

    return Client("C-001", 2025, "MFJ", taxpayer, spouse, address, w2s)


def test_creates_screen1_action_plan_for_one_client() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    plan = generate_action_plan(_build_client(), screen_maps)

    assert plan.client_id == "C-001"
    assert plan.steps[0].action == "OPEN_SCREEN"
    assert plan.steps[0].screen == "SCRN1"
    fields = [s.field for s in plan.steps if s.screen == "SCRN1" and s.action != "OPEN_SCREEN"]
    assert fields[0:5] == [
        "taxpayer.first_name",
        "taxpayer.last_name",
        "taxpayer.ssn",
        "taxpayer.dob",
        "filing_status",
    ]


def test_creates_w2_action_steps_for_one_w2() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    plan = generate_action_plan(_build_client(), screen_maps)
    w2_steps = [s for s in plan.steps if s.screen == "W2IN"]

    assert w2_steps[0].action == "OPEN_SCREEN"
    assert any(step.field == "w2.employer.ein" for step in w2_steps)
    assert any(step.field == "w2.box_1_wages" for step in w2_steps)


def test_creates_repeated_w2_steps_for_multiple_w2s() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    plan = generate_action_plan(_build_client(two_w2s=True), screen_maps)
    w2_open_count = sum(1 for step in plan.steps if step.action == "OPEN_SCREEN" and step.screen == "W2IN")
    assert w2_open_count == 2


def test_masks_ssn_and_ein_and_does_not_expose_full_values() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    ssn = _id_from_parts("123", "45", "6789")
    ein = _id_from_parts("12", "345", "6789")
    plan = generate_action_plan(_build_client(), screen_maps)

    ssn_step = next(step for step in plan.steps if step.field == "taxpayer.ssn")
    ein_step = next(step for step in plan.steps if step.field == "w2.employer.ein")

    assert ssn_step.masked_value == "***-**-6789"
    assert ein_step.masked_value == "**-***6789"
    assert ssn not in ssn_step.masked_value
    assert ein not in ein_step.masked_value


def test_skips_manual_review_unsupported_and_deprecated_fields() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    plan = generate_action_plan(_build_client(), screen_maps)

    actions = {step.field: step.action for step in plan.steps if step.field}
    assert actions["w2.box_3_social_security_wages"] == "SKIP_MANUAL_REVIEW"
    assert actions["w2.box_4_social_security_tax"] == "SKIP_UNSUPPORTED"
    assert actions["w2.box_12_codes"] == "SKIP_UNSUPPORTED"


def test_preserves_source_refs_and_order() -> None:
    screen_maps = load_screen_maps("configs/drake/2025")
    refs = {
        "clients.C-001.taxpayer.first_name": SourceCellRef(sheet="Clients", cell="D2"),
        "clients.C-001.w2s.W2-001.employer.ein": SourceCellRef(sheet="W2s", cell="D2"),
    }

    plan = generate_action_plan(_build_client(), screen_maps, source_cells=refs)
    first_name = next(step for step in plan.steps if step.field == "taxpayer.first_name")
    ein = next(step for step in plan.steps if step.field == "w2.employer.ein")

    assert (first_name.source_sheet, first_name.source_cell) == ("Clients", "D2")
    assert (ein.source_sheet, ein.source_cell) == ("W2s", "D2")

    w2_fields = [s.field for s in plan.steps if s.screen == "W2IN" and s.field]
    assert w2_fields[0:4] == [
        "w2.employer.ein",
        "w2.employer.name",
        "w2.box_1_wages",
        "w2.box_2_federal_withholding",
    ]
