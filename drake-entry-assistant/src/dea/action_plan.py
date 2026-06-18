"""Action-plan generation from validated data."""

from __future__ import annotations

from decimal import Decimal

from dea.masking import mask_value
from dea.models import ActionPlan, ActionStep, Client, ScreenMap, SourceCellRef, W2


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _resolve_screen_map(screen_maps: dict[str, ScreenMap], *, key_candidates: list[str], code: str) -> ScreenMap:
    for key in key_candidates:
        map_obj = screen_maps.get(key.lower())
        if map_obj is not None:
            return map_obj
    for map_obj in screen_maps.values():
        if map_obj.screen_code == code:
            return map_obj
    raise ValueError(f"Missing required screen map for {code}")


def _get_client_value(client: Client, field_path: str) -> object:
    parts = field_path.split(".")
    if parts[0] == "taxpayer":
        return getattr(client.taxpayer, parts[1])
    if parts[0] == "filing_status":
        return client.filing_status
    if parts[0] == "address":
        return getattr(client.address, parts[1])
    if parts[0] == "spouse":
        if client.spouse is None:
            return ""
        return getattr(client.spouse, parts[1])
    raise ValueError(f"Unsupported Screen 1 field path: {field_path}")


def _get_w2_value(w2: W2, field_path: str) -> object:
    if not field_path.startswith("w2."):
        raise ValueError(f"Unsupported W-2 field path: {field_path}")
    path = field_path[3:]
    if path.startswith("employer."):
        return getattr(w2.employer, path.split(".", 1)[1])
    if path == "box_1_wages":
        return w2.box_1_wages
    if path == "box_2_federal_withholding":
        return w2.box_2_federal_withholding
    if path == "box_3_social_security_wages":
        return w2.box_3_social_security_wages
    if path == "box_4_social_security_tax":
        return w2.box_4_social_security_tax
    if path == "box_5_medicare_wages":
        return w2.box_5_medicare_wages
    if path == "box_6_medicare_tax":
        return w2.box_6_medicare_tax
    return ""


def _source_ref(
    source_cells: dict[str, SourceCellRef] | None,
    key: str,
) -> tuple[str | None, str | None]:
    if source_cells is None:
        return None, None
    ref = source_cells.get(key)
    if ref is None:
        return None, None
    return ref.sheet, ref.cell


def _step_for_field(
    *,
    screen: str,
    field_path: str,
    support_status: str,
    value: object,
    source_sheet: str | None,
    source_cell: str | None,
    field_locator: str | None,
) -> ActionStep:
    text_value = _stringify(value)
    # Drake enters SSNs and EINs as raw digits; strip any formatting characters
    # (dashes, spaces) so Drake's own field validator accepts the input.
    if "ssn" in field_path.lower() or "ein" in field_path.lower():
        text_value = "".join(c for c in text_value if c.isdigit())
    masked = mask_value(field_path, text_value)

    if support_status in {"SUPPORTED", "CONDITIONALLY_SUPPORTED"}:
        action = "ENTER_FIELD"
    elif support_status == "MANUAL_REVIEW":
        action = "SKIP_MANUAL_REVIEW"
    else:
        action = "SKIP_UNSUPPORTED"

    return ActionStep(
        action=action,
        screen=screen,
        field=field_path,
        value=text_value,
        masked_value=masked,
        source_sheet=source_sheet,
        source_cell=source_cell,
        support_status=support_status,  # type: ignore[arg-type]
        field_locator=field_locator,
    )


def generate_action_plan(
    client: Client,
    screen_maps: dict[str, ScreenMap],
    source_cells: dict[str, SourceCellRef] | None = None,
) -> ActionPlan:
    """Generate a deterministic, masked action plan for Screen 1 and W-2 screens."""
    screen1_map = _resolve_screen_map(
        screen_maps,
        key_candidates=["screen1", "screen_1", "scrn1", "screen 1", "screen1 - taxpayer information"],
        code="SCRN1",
    )
    w2_map = _resolve_screen_map(
        screen_maps,
        key_candidates=["w2", "w2in", "w-2", "w2 input"],
        code="W2IN",
    )

    steps: list[ActionStep] = [
        ActionStep(
            action="OPEN_SCREEN",
            screen=screen1_map.screen_code,
            field="",
            value=screen1_map.screen_code,
            masked_value="",
            source_sheet=None,
            source_cell=None,
            support_status="SUPPORTED",
            field_locator=None,
        )
    ]

    for field_cfg in screen1_map.fields:
        source_key = f"clients.{client.client_id}.{field_cfg.field_path}"
        source_sheet, source_cell = _source_ref(source_cells, source_key)
        value = _get_client_value(client, field_cfg.field_path)
        locator = field_cfg.locator or field_cfg.position
        steps.append(
            _step_for_field(
                screen=screen1_map.screen_code,
                field_path=field_cfg.field_path,
                support_status=field_cfg.support_status,
                value=value,
                source_sheet=source_sheet,
                source_cell=source_cell,
                field_locator=locator,
            )
        )

    for w2 in client.w2s:
        steps.append(
            ActionStep(
                action="OPEN_SCREEN",
                screen=w2_map.screen_code,
                field="",
                value=w2_map.screen_code,
                masked_value="",
                source_sheet=None,
                source_cell=None,
                support_status="SUPPORTED",
                field_locator=None,
            )
        )
        for field_cfg in w2_map.fields:
            source_field = field_cfg.field_path[3:] if field_cfg.field_path.startswith("w2.") else field_cfg.field_path
            source_key = f"clients.{client.client_id}.w2s.{w2.w2_id}.{source_field}"
            source_sheet, source_cell = _source_ref(source_cells, source_key)
            value = _get_w2_value(w2, field_cfg.field_path)
            locator = field_cfg.locator or field_cfg.position
            steps.append(
                _step_for_field(
                    screen=w2_map.screen_code,
                    field_path=field_cfg.field_path,
                    support_status=field_cfg.support_status,
                    value=value,
                    source_sheet=source_sheet,
                    source_cell=source_cell,
                    field_locator=locator,
                )
            )

    return ActionPlan(client_id=client.client_id, tax_year=client.tax_year, steps=steps)
