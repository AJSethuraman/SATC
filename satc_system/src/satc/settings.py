"""Runtime posture — local-first by default, no document ever leaves the machine.

Client tax documents contain PII (SSNs, EINs, income). SATC processes everything
**on this machine** by default and never sends a document anywhere. The cloud
vision fallback is OFF unless the practice explicitly opts in: setting
``SATC_ALLOW_CLOUD=1`` *and* providing an API key. A key on its own is not enough
— opting in is a deliberate act, never an accident of having a key in the
environment.

This is the single switch that governs whether any document can leave the
machine. Everything else (form-field reads, text-layer extraction, keyword
classification, PDF splitting) is fully local and unaffected by it.
"""

from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on"}


def cloud_allowed() -> bool:
    """True only if the practice has explicitly opted into cloud processing."""
    return os.environ.get("SATC_ALLOW_CLOUD", "").strip().lower() in _TRUE


def cloud_vision_enabled() -> bool:
    """Cloud vision may run only with an explicit opt-in AND an API key present."""
    return cloud_allowed() and bool(os.environ.get("ANTHROPIC_API_KEY"))


def ocr_enabled() -> bool:
    """True if local OCR (Tesseract) should be used — on by default when available.

    OCR is fully local, so it needs no opt-in; it is used automatically when the
    machine has Tesseract. Set ``SATC_OCR=0`` to force it off.
    """
    if os.environ.get("SATC_OCR", "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    from satc.ingest.ocr import tesseract_available

    return tesseract_available()


def ollama_enabled() -> bool:
    """True if the local Ollama vision rung should be used (opt-in: ``SATC_OLLAMA=1``).

    Ollama runs entirely on localhost — no document leaves the machine — but it
    requires the practice to have installed Ollama and pulled a vision model, so it
    is opt-in rather than automatic.
    """
    return os.environ.get("SATC_OLLAMA", "").strip().lower() in _TRUE


def ollama_host() -> str:
    return os.environ.get("SATC_OLLAMA_HOST", "http://localhost:11434")


def ollama_model() -> str:
    return os.environ.get("SATC_OLLAMA_MODEL", "llama3.2-vision")
