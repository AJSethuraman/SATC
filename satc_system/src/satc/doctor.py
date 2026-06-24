"""Readiness checks — powers ``satc doctor`` and the in-app Setup screen.

Tells the user — who is a tax preparer, not a developer — exactly what is ready
and, in plain language, what to do about anything that isn't. It is read-only:
it never installs or changes anything.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass

_ICONS = {"ok": "✅", "warn": "⚠️", "info": "•"}


@dataclass(slots=True)
class Check:
    name: str
    status: str          # "ok" | "warn" | "info"
    detail: str
    fix: str = ""

    @property
    def icon(self) -> str:
        return _ICONS.get(self.status, "•")


def _have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _ollama_reachable() -> bool:
    import urllib.request

    from satc.settings import ollama_host

    try:
        with urllib.request.urlopen(ollama_host().rstrip("/") + "/api/tags", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def run_checks() -> list[Check]:
    """Inspect the environment and return a readiness report (no side effects)."""
    from satc.ingest.ocr import tesseract_available
    from satc.persistence.store import DEFAULT_DIR
    from satc.settings import cloud_allowed, ollama_enabled

    checks: list[Check] = []

    v = sys.version_info
    checks.append(Check("Python", "ok" if v >= (3, 10) else "warn",
                        f"{v.major}.{v.minor}.{v.micro}",
                        "" if v >= (3, 10) else "SATC needs Python 3.10 or newer."))

    store = os.environ.get("SATC_DATA_DIR") or str(DEFAULT_DIR)
    checks.append(Check("Data store", "ok", store))

    checks.append(Check("PDF reading", "ok" if _have("pypdf") else "warn",
                        "ready" if _have("pypdf") else "missing",
                        "" if _have("pypdf") else "pip install -e '.[pdf]'"))
    checks.append(Check("Web app", "ok" if _have("flask") else "warn",
                        "ready" if _have("flask") else "missing",
                        "" if _have("flask") else "pip install -e '.[app]'"))

    if tesseract_available():
        checks.append(Check("Local OCR (Tesseract)", "ok", "ready — scans are read on this machine"))
    else:
        checks.append(Check("Local OCR (Tesseract)", "warn", "not installed",
                            "Install Tesseract for Windows "
                            "(github.com/UB-Mannheim/tesseract/wiki), then pip install -e '.[ocr]'"))

    if ollama_enabled():
        ok = _ollama_reachable()
        checks.append(Check("Local vision (Ollama)", "ok" if ok else "warn",
                            "enabled and reachable" if ok else "enabled but not reachable",
                            "" if ok else "Start it with 'ollama serve' and 'ollama pull llama3.2-vision'."))
    else:
        checks.append(Check("Local vision (Ollama)", "info", "off (optional)",
                            "To use a local vision model: set SATC_OLLAMA=1 (needs Ollama installed)."))

    if cloud_allowed():
        checks.append(Check("Cloud vision", "info", "ENABLED (opt-in)",
                            "Documents may be sent to the cloud. Unset SATC_ALLOW_CLOUD to keep everything local."))
    else:
        checks.append(Check("Cloud vision", "ok", "OFF — documents never leave this machine",
                            "Only if you ever need it: set SATC_ALLOW_CLOUD=1 (plus an API key)."))

    return checks


def format_report(checks: list[Check] | None = None) -> str:
    checks = checks if checks is not None else run_checks()
    lines = ["", "  SATC readiness", "  " + "-" * 48]
    for c in checks:
        lines.append(f"  {c.icon}  {c.name:<24} {c.detail}")
        if c.fix:
            lines.append(f"        ↳ {c.fix}")
    ready = all(c.status != "warn" for c in checks)
    lines += ["  " + "-" * 48,
              "  All set — run 'satc app' to start." if ready else
              "  Address the ⚠️ items above, then run 'satc app'.", ""]
    return "\n".join(lines)
