"""Configuration loading for adapter and screen-map metadata.

Drake-specific details remain in YAML configs and adapter layers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dea.models import ScreenField, ScreenMap


_VALID_SUPPORT_STATUSES = {
    "SUPPORTED",
    "CONDITIONALLY_SUPPORTED",
    "MANUAL_REVIEW",
    "UNSUPPORTED",
    "DEPRECATED",
}
_VALID_METHODS = {"tab_order", "control_locator", "manual"}


class ConfigLoadError(Exception):
    """Raised when screen-map config files are missing or malformed."""


def _as_non_empty_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigLoadError(f"{label} must be a non-empty string")
    return value.strip()


def _coerce_tax_year(data: dict[str, Any]) -> int | None:
    raw = data.get("tax_year")
    if raw is None:
        raw = data.get("version")
    if raw is None:
        return None
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    return None


def _parse_fields(raw_fields: Any, path: Path) -> list[ScreenField]:
    if isinstance(raw_fields, dict):
        items: list[tuple[str, Any]] = list(raw_fields.items())
    elif isinstance(raw_fields, list):
        items = []
        for idx, item in enumerate(raw_fields, start=1):
            if not isinstance(item, dict):
                raise ConfigLoadError(f"fields[{idx}] must be an object in {path}")
            field_path = item.get("field_path")
            items.append((str(field_path or "").strip(), item))
    else:
        raise ConfigLoadError(f"fields must be a mapping or list in {path}")

    if not items:
        raise ConfigLoadError(f"fields must be non-empty in {path}")

    parsed: list[ScreenField] = []
    for idx, (field_path, cfg) in enumerate(items, start=1):
        if not field_path:
            raise ConfigLoadError(f"fields entry {idx} is missing field path in {path}")
        if not isinstance(cfg, dict):
            raise ConfigLoadError(f"fields.{field_path} must be an object in {path}")

        support_status = cfg.get("support_status")
        method = cfg.get("method")

        if support_status not in _VALID_SUPPORT_STATUSES:
            raise ConfigLoadError(
                f"fields.{field_path}.support_status must be one of "
                f"{sorted(_VALID_SUPPORT_STATUSES)} in {path}"
            )
        if method not in _VALID_METHODS:
            raise ConfigLoadError(
                f"fields.{field_path}.method must be one of {sorted(_VALID_METHODS)} in {path}"
            )

        position = cfg.get("position")
        locator = cfg.get("locator")
        if method == "tab_order" and (not isinstance(position, str) or not position.strip()):
            raise ConfigLoadError(f"fields.{field_path} with method tab_order requires position in {path}")
        if method == "control_locator" and (not isinstance(locator, str) or not locator.strip()):
            raise ConfigLoadError(
                f"fields.{field_path} with method control_locator requires locator in {path}"
            )

        parsed.append(
            ScreenField(
                field_path=field_path,
                label=str(cfg.get("label") or field_path),
                source=str(cfg.get("source") or ""),
                support_status=support_status,
                method=method,
                position=position.strip() if isinstance(position, str) and position.strip() else None,
                locator=locator.strip() if isinstance(locator, str) and locator.strip() else None,
                mask_in_log=bool(cfg.get("mask_in_log", False)),
            )
        )

    return parsed


def load_screen_map(path: str | Path) -> ScreenMap:
    """Load and validate a single YAML screen map file."""
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigLoadError(f"Screen map not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except OSError as exc:
        raise ConfigLoadError(f"Unable to read screen map {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigLoadError(f"Screen map root must be an object in {config_path}")

    screen_name = raw.get("screen_name")
    screen_key = raw.get("screen")
    if not screen_key and not screen_name:
        raise ConfigLoadError(f"screen or screen_name is required in {config_path}")

    resolved_screen = str(screen_key or screen_name).strip()
    resolved_name = str(screen_name or screen_key).strip()
    if not resolved_screen:
        raise ConfigLoadError(f"screen or screen_name is required in {config_path}")

    screen_code = _as_non_empty_str(raw.get("screen_code"), "screen_code")

    markers = raw.get("expected_markers")
    if not isinstance(markers, list) or not markers or not all(isinstance(m, str) and m.strip() for m in markers):
        raise ConfigLoadError(f"expected_markers must be a non-empty list of strings in {config_path}")

    fields = _parse_fields(raw.get("fields"), config_path)

    return ScreenMap(
        screen=resolved_screen,
        screen_name=resolved_name,
        screen_code=screen_code,
        tax_year=_coerce_tax_year(raw),
        version=str(raw.get("version")).strip() if raw.get("version") is not None else None,
        expected_markers=[m.strip() for m in markers],
        fields=fields,
    )


def load_screen_maps(config_dir: str | Path) -> dict[str, ScreenMap]:
    """Load all YAML screen maps from a configuration directory."""
    root = Path(config_dir)
    if not root.exists() or not root.is_dir():
        raise ConfigLoadError(f"Config directory not found: {root}")

    files = sorted(root.glob("*.yaml"))
    if not files:
        raise ConfigLoadError(f"No YAML screen maps found in: {root}")

    maps: dict[str, ScreenMap] = {}
    for file_path in files:
        screen_map = load_screen_map(file_path)
        maps[screen_map.screen.lower()] = screen_map
    return maps
