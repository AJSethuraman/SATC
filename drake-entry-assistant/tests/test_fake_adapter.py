from __future__ import annotations

from decimal import Decimal

from dea.action_plan import generate_action_plan
from dea.adapters.fake import FakeDrakeAdapter
from dea.config_loader import load_screen_maps
from dea.models import Address, Client, Employer, Spouse, Taxpayer, W2


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def _build_client() -> Client:
    taxpayer = Taxpayer("Alex", "Rivera", _id_from_parts("123", "45", "6789"), "1988-04-14", "Engineer")
    spouse = Spouse("Jordan", "Rivera", _id_from_parts("111", "22", "3333"), "1990-11-30", "Teacher")
    address = Address("100 Main St", "Springfield", "IL", "62701")
    w2 = W2(
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
    return Client("C-001", 2025, "MFJ", taxpayer, spouse, address, [w2])


def _plan_and_maps():
    maps = load_screen_maps("configs/drake/2025")
    plan = generate_action_plan(_build_client(), maps)
    return plan, maps


def test_successful_fake_execution_enters_planned_fields() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter()
    result = adapter.execute_action_plan(plan, maps)

    assert result.success is True
    entered = [r for r in result.records if r.status == "ENTERED"]
    assert any(r.action == "ENTER_FIELD" for r in entered)


def test_missing_app_stops_safely() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter(app_available=False)
    result = adapter.execute_action_plan(plan, maps)

    assert result.success is False
    assert result.records[-1].status == "FAILED_SCREEN_CHECK"


def test_missing_screen_stops_safely() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter(missing_screens={"W2IN"})
    result = adapter.execute_action_plan(plan, maps)

    assert result.success is False
    assert result.records[-1].status == "FAILED_SCREEN_CHECK"


def test_missing_field_stops_safely() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter(missing_fields={"w2.employer.name"})
    result = adapter.execute_action_plan(plan, maps)

    assert result.success is False
    assert result.records[-1].status == "FAILED_FIELD_ENTRY"


def test_unexpected_popup_stops_safely() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter(unexpected_popup=True)
    result = adapter.execute_action_plan(plan, maps)

    assert result.success is False
    assert result.records[-1].status == "FAILED_SCREEN_CHECK"


def test_skip_statuses_are_preserved_in_execution_logs() -> None:
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter()
    result = adapter.execute_action_plan(plan, maps)

    statuses = {(r.field, r.status) for r in result.records}
    assert ("w2.box_3_social_security_wages", "SKIPPED_MANUAL_REVIEW") in statuses
    assert ("w2.box_4_social_security_tax", "SKIPPED_UNSUPPORTED") in statuses


def test_execution_logs_do_not_expose_full_ssn_or_ein() -> None:
    ssn = _id_from_parts("123", "45", "6789")
    ein = _id_from_parts("12", "345", "6789")
    plan, maps = _plan_and_maps()
    adapter = FakeDrakeAdapter()
    result = adapter.execute_action_plan(plan, maps)

    payload = "\n".join(
        f"{rec.field}|{rec.masked_value}|{rec.error_message or ''}" for rec in result.records
    )
    assert ssn not in payload
    assert ein not in payload
