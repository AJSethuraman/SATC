"""Loaders for the YAML configs that drive the system (line sheets, etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"


class ConfigError(Exception):
    """Raised when a config file is missing or malformed."""


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return data


def load_line_sheet(return_type: str, config_root: Path | None = None) -> dict[str, Any]:
    """Load a line-sheet config (``configs/line_sheets/<RETURN>.yaml``)."""
    root = config_root or CONFIG_ROOT
    return _load_yaml(root / "line_sheets" / f"{return_type}.yaml")


def load_extraction_map(doc_key: str, config_root: Path | None = None) -> dict[str, Any]:
    """Load a document extraction field map (``configs/extraction/<doc>.yaml``)."""
    root = config_root or CONFIG_ROOT
    return _load_yaml(root / "extraction" / f"{doc_key}.yaml")


def templatize(config: dict[str, Any], replacements: dict[str, str]) -> dict[str, Any]:
    """Replace ``{{TOKEN}}`` placeholders throughout a config (e.g. the resident state)."""
    def walk(node: Any) -> Any:
        if isinstance(node, str):
            out = node
            for token, value in replacements.items():
                out = out.replace("{{" + token + "}}", value)
            return out
        if isinstance(node, list):
            return [walk(n) for n in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return walk(config)
