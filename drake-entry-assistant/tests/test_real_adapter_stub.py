from __future__ import annotations

from pathlib import Path

from dea.adapters.real import RealDrakeAdapter
from dea.models import ActionPlan, ActionStep


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def _plan() -> ActionPlan:
    ssn = _id_from_parts("123", "45", "6789")
    step = ActionStep(
        action="ENTER_FIELD",
        screen="SCRN1",
        field="taxpayer.ssn",
        value=ssn,
        masked_value="***-**-6789",
        source_sheet="Clients",
        source_cell="F2",
        support_status="CONDITIONALLY_SUPPORTED",
        field_locator="name:taxpayer_ssn",
    )
    return ActionPlan(client_id="C-001", tax_year=2025, steps=[step])


def test_real_adapter_refuses_when_live_disabled() -> None:
    adapter = RealDrakeAdapter(live_enabled=False)
    result = adapter.execute_action_plan(_plan(), {})
    assert result.success is False
    assert "disabled" in (result.error_message or "").lower()


def test_real_adapter_refuses_when_live_enabled_but_not_implemented() -> None:
    adapter = RealDrakeAdapter(live_enabled=True)
    result = adapter.execute_action_plan(_plan(), {})
    assert result.success is False
    assert "not implemented" in (result.error_message or "").lower()


def test_real_adapter_source_has_no_ui_automation_imports() -> None:
    source = Path("src/dea/adapters/real.py").read_text(encoding="utf-8")
    assert "pyautogui" not in source
    assert "pywinauto" not in source


def test_refusal_result_does_not_expose_raw_sensitive_values() -> None:
    raw_ssn = _id_from_parts("123", "45", "6789")
    adapter = RealDrakeAdapter(live_enabled=True)
    result = adapter.execute_action_plan(_plan(), {})

    payload = "\n".join(
        [
            result.error_message or "",
            *(f"{rec.masked_value}|{rec.error_message or ''}" for rec in result.records),
        ]
    )
    assert raw_ssn not in payload
