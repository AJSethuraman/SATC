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


# ---------------------------------------------------------------------------
# ⚠️  TURNING THIS ON IS A COMPLIANCE EVENT, NOT A CONFIGURATION CHANGE.
#
# Setting SATC_ALLOW_CLOUD (or adding ANTHROPIC_API_KEY to the environment with
# it already set) sends client tax-document IMAGES to Anthropic. That makes
# Anthropic a service provider holding customer information under the FTC
# Safeguards Rule §314.4(f) -- which is NOT waived by the small-firm exemption
# in §314.6 -- and raises a separate IRS §301.7216 disclosure-consent question.
#
# The firm's decision, recorded in docs/WISP-DRAFT.md §A5 (control A5-C): the
# WISP must be updated FIRST -- provider assessment, contract with safeguards
# terms, reassessment cadence, and the §301.7216 analysis -- before either
# switch is set on any machine holding real client data.
#
# Nothing here enforces that. This comment is the whole of the gate.
# ---------------------------------------------------------------------------


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


class RemoteModelRefused(RuntimeError):
    """`SATC_OLLAMA_HOST` pointed somewhere that is not this machine."""


def _is_loopback(url: str) -> bool:
    """True only when this URL can reach nothing but this machine."""
    import ipaddress
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").strip().lower()
    if host in ("localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        # A name we cannot resolve to an address here. Refuse it: a hostname
        # that HAPPENS to resolve to loopback today is not a guarantee, and
        # this check is worth nothing if it can be satisfied by DNS.
        return False


def ollama_host() -> str:
    """Where the local model lives. LOOPBACK ONLY, and it refuses rather than warns.

    THE CLAIM THIS PROTECTS is written four lines above, in `ollama_enabled`:
    *"Ollama runs entirely on localhost -- no document leaves the machine."*
    That was asserted in a docstring and enforced nowhere. `SATC_OLLAMA_HOST`
    was returned unchecked, so one environment variable pointed the document
    reader at someone else's server and sent client tax documents to it --
    silently, because a working remote Ollama answers exactly like a local one.

    The Forge's standing rule keeps the Ollama SERVER on `127.0.0.1` so nothing
    can reach the model. It says nothing about the CLIENT, which is the other
    half of the same door, and this is that half.

    Refusing rather than falling back to the default is deliberate: a fallback
    would honour the safe behaviour while hiding that someone asked for the
    unsafe one, and a person who set this variable needs to find out they were
    wrong. If a remote model is ever genuinely wanted, that is a code change
    with a WISP line beside it -- Anthropic or anyone else receiving client
    documents is a service provider under 16 CFR 314.4(f).
    """
    url = os.environ.get("SATC_OLLAMA_HOST", "").strip()
    if not url:
        return "http://localhost:11434"
    if not _is_loopback(url):
        raise RemoteModelRefused(
            f"SATC_OLLAMA_HOST is set to {url!r}, which is not this machine. "
            "Client documents are read by the local model only. Unset it, or "
            "point it at localhost / 127.0.0.1.")
    return url


def ollama_model() -> str:
    # The vision model actually built for SATC on this box. The old default
    # (llama3.2-vision) is not installed here, so the vision rung would have
    # failed at call time rather than at configuration time.
    return os.environ.get("SATC_OLLAMA_MODEL", "SATC-DocReader:latest")


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
