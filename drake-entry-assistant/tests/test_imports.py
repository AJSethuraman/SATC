"""Basic import smoke tests for project skeleton."""

import importlib


MODULES = [
    "dea.models",
    "dea.validation",
    "dea.excel_loader",
    "dea.action_plan",
    "dea.logging_utils",
    "dea.masking",
    "dea.config_loader",
    "dea.output",
    "dea.demo",
    "dea.cli",
    "dea.adapters.base",
    "dea.adapters.fake",
    "dea.adapters.real",
]


def test_module_imports() -> None:
    """All public skeleton modules should import cleanly."""
    for module in MODULES:
        importlib.import_module(module)
