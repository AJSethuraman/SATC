"""Configurable expectation/threshold layer.

Each metric in a product's battery declares :class:`~ucpa.products.base.
ThresholdCheck` entries binding one of its summary values to a limit in the
thresholds config.  Defaults live in ``configs/default_thresholds.json``
(the firm's standard methodology); a per-client JSON file deep-merges over
the defaults so engagements can adjust individual limits without restating
the whole methodology.

Severity convention:
* ``EXCEPTION`` -- the observed value breaches the limit.
* ``WATCH`` -- the observed value is compliant but within 10% of the limit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Optional

from ucpa.metrics.results import MetricResult, ThresholdException
from ucpa.products.base import ThresholdCheck

WATCH_MARGIN = 0.10

_DEFAULTS_RESOURCE = Path(__file__).resolve().parents[2] / "configs" / "default_thresholds.json"


def load_default_thresholds() -> dict:
    """Load the firm-standard threshold defaults shipped with the package."""
    with open(_DEFAULTS_RESOURCE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def deep_merge(base: Mapping, override: Mapping) -> dict:
    """Recursively merge ``override`` onto ``base`` (override wins)."""
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], Mapping) and isinstance(value, Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_thresholds(client_config_path: Optional[str | Path] = None) -> dict:
    """Defaults, optionally overridden by a client JSON config file."""
    config = load_default_thresholds()
    if client_config_path is not None:
        with open(client_config_path, "r", encoding="utf-8") as fh:
            config = deep_merge(config, json.load(fh))
    return config


def get_limit(config: Mapping, dotted_key: str) -> Optional[float]:
    """Resolve ``"section.limit_name"`` in the config; None when absent."""
    node: object = config
    for part in dotted_key.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    return float(node) if isinstance(node, (int, float)) else None


def _fmt(value: float, fmt: str) -> str:
    return f"{value:.2%}" if fmt == "pct" else f"{value:,.2f}"


def evaluate_checks(
    result: MetricResult, checks: Iterable[ThresholdCheck], config: Mapping
) -> list[ThresholdException]:
    """Evaluate a metric result's threshold checks against the config.

    Checks whose limit is absent from the config, or whose summary value is
    missing/None/NaN (e.g. blocked by a data gap), are skipped.
    """
    exceptions: list[ThresholdException] = []
    for check in checks:
        limit = get_limit(config, check.config_key)
        observed = result.summary.get(check.summary_key)
        if limit is None or observed is None:
            continue
        observed = float(observed)
        if math.isnan(observed):
            continue

        if check.direction == "max":
            breached = observed > limit
            watch = not breached and observed >= limit * (1.0 - WATCH_MARGIN)
        elif check.direction == "min":
            breached = observed < limit
            watch = not breached and observed <= limit * (1.0 + WATCH_MARGIN)
        else:  # pragma: no cover - guarded by spec construction
            raise ValueError(f"Unknown threshold direction: {check.direction}")

        if not (breached or watch):
            continue
        severity = "EXCEPTION" if breached else "WATCH"
        relation = ">" if check.direction == "max" else "<"
        message = (
            f"{check.label}: observed {_fmt(observed, check.format)} vs "
            f"{check.direction} limit {_fmt(limit, check.format)}"
            + (f" (breach: observed {relation} limit)" if breached else " (within 10% of limit)")
        )
        exceptions.append(
            ThresholdException(
                metric=result.metric,
                check=check.label,
                summary_key=check.summary_key,
                observed=observed,
                limit=limit,
                direction=check.direction,
                severity=severity,
                message=message,
                format=check.format,
            )
        )
    return exceptions
