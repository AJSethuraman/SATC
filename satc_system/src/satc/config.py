"""Loaders for the YAML configs that drive the system (line sheets, etc.)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def _config_root() -> Path:
    """Locate the ``configs/`` tree.

    In a normal (dev/test) install the configs live alongside the package at
    ``satc_system/configs``. Inside a PyInstaller bundle the source tree is gone,
    so the configs are bundled as data under ``sys._MEIPASS/configs`` instead.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "configs"
    return Path(__file__).resolve().parents[2] / "configs"


CONFIG_ROOT = _config_root()


class ConfigError(Exception):
    """Raised when a config file is missing or malformed."""


def read_yaml(path: Path) -> Any:
    """Parse a YAML file, turning a syntax error into a named refusal.

    The shape check is the caller's — some of these files are a mapping, some a
    list, some legitimately empty. What is NOT the caller's is deciding what a
    stray space should do: every config here is hand-edited, so a parse error is
    ordinary, and ten modules each letting ``yaml.YAMLError`` escape meant a
    typo surfaced as a stack trace naming a line in "<unicode string>" rather
    than as a sentence naming the file the owner just saved.
    """
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as broken:
        where = ""
        mark = getattr(broken, "problem_mark", None)
        if mark is not None:
            where = f" at line {mark.line + 1}, column {mark.column + 1}"
        detail = str(getattr(broken, "problem", "") or broken).strip()
        raise ConfigError(
            f"{path} is not readable as YAML{where}: {detail}. Nothing that "
            f"depends on it can be worked out until it parses — check the "
            f"indentation on that line, and that every quote and bracket is "
            f"closed.") from None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        try:
            data = yaml.safe_load(handle)
        except yaml.YAMLError as broken:
            # EVERY config in this system is hand-edited on purpose — prices,
            # promises, cutoffs, workflows — so a YAML syntax error is an
            # ordinary event, not an exceptional one. Letting the parser's own
            # exception escape meant a stray space took a screen down with a
            # stack trace instead of a sentence, and the raw error names a line
            # and column in an unnamed "<unicode string>" rather than the file
            # the owner just edited (principles 5 and 10).
            where = ""
            mark = getattr(broken, "problem_mark", None)
            if mark is not None:
                where = f" at line {mark.line + 1}, column {mark.column + 1}"
            detail = str(getattr(broken, "problem", "") or broken).strip()
            raise ConfigError(
                f"{path} is not readable as YAML{where}: {detail}. Nothing that "
                f"depends on it can be worked out until it parses — check the "
                f"indentation on that line, and that every quote and bracket is "
                f"closed.") from None
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


def load_classification(config_root: Path | None = None) -> dict[str, Any]:
    """Load the content-based document classification registry."""
    root = config_root or CONFIG_ROOT
    return _load_yaml(root / "classification.yaml")


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
