from __future__ import annotations

from .template_scanner import display_field_name, is_optional_placeholder, normalize_field_name

def build_field_records(placeholders: list[str], pool: dict[str, tuple[str, str]], overrides: dict | None = None) -> list[dict]:
    overrides = overrides or {}
    records = []
    for label in placeholders:
        key = normalize_field_name(label)
        display_name = display_field_name(label)
        optional = is_optional_placeholder(label)
        value, source = pool.get(key, ("", "Not found"))
        overridden = label in overrides and overrides[label] != value
        if label in overrides:
            value = overrides[label]
            source = "User override" if overridden else source
        status = "Filled" if str(value).strip() else ("Optional Blank" if optional else "Missing")
        if overridden:
            status = "Overridden"
        records.append({
            "field": display_name,
            "placeholder": label,
            "normalized_field": key,
            "required": not optional,
            "value": "" if value is None else str(value),
            "source": source,
            "status": status,
            "overridden": overridden,
        })
    return records

def records_to_values(records: list[dict]) -> dict[str, str]:
    values = {}
    for r in records:
        values[r["field"]] = r.get("value", "")
        values[r.get("placeholder", r["field"])] = r.get("value", "")
        values[r["normalized_field"]] = r.get("value", "")
    return values
