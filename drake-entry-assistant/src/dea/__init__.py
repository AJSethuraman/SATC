"""Drake Entry Assistant package.

This package provides local-first tooling for validated tax data entry workflows.
Core tax-data logic is intentionally separated from Drake-specific adapters and
configuration.
"""

__all__ = [
    "models",
    "validation",
    "excel_loader",
    "action_plan",
    "logging_utils",
    "masking",
    "config_loader",
    "output",
    "demo",
    "cli",
]
