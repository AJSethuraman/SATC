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


# HOW MUCH CONTEXT THE VISION RUNG ASKS FOR, and why it is pinned low.
#
# Measured on the Forge (RTX 2070 SUPER, 8 GB) on 3 September 2026:
#
#   qwen3:8b       @ 8192  ->  100% GPU
#   qwen2.5vl:7b   @ 8192  ->  15%/85% CPU/GPU     spilled
#   qwen2.5vl:7b   @ 6144  ->  13%/87% CPU/GPU     spilled
#   qwen2.5vl:7b   @ 5120  ->  100% GPU
#
# The machine notes said 8192 was the ceiling. That was measured against
# `qwen3:8b`, a text model, and does not transfer: the VISION models spill at
# 6144. Once any layer moves to the CPU, throughput collapses.
#
# 4096 rather than the measured 5120, deliberately. Every one of those numbers
# was taken with a TEXT-only prompt, and a real page makes the model allocate
# for the image as well -- at 5120 there was under 900 MB of headroom on the
# card. 4096 is the setting with margin, and the difference between 4096 and
# 5120 is far smaller than the difference between "on the card" and "not".
#
# Before this existed the payload sent no `options` at all, so the value was
# whatever the model's own default happened to be and there was nowhere to pin
# it. That is why the stale note went unnoticed for as long as it did.
OLLAMA_NUM_CTX_DEFAULT = 4096


def ollama_num_ctx() -> int:
    """Context window for the local vision rung. ``SATC_OLLAMA_NUM_CTX`` overrides."""
    raw = os.environ.get("SATC_OLLAMA_NUM_CTX", "").strip()
    if not raw:
        return OLLAMA_NUM_CTX_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return OLLAMA_NUM_CTX_DEFAULT
    return value if value > 0 else OLLAMA_NUM_CTX_DEFAULT
