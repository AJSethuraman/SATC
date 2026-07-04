"""Local OCR + local Ollama readers, and the opt-in cloud posture.

Both readers are exercised with injected backends, so these tests need neither
Tesseract nor a running Ollama — they verify the wiring, not the model accuracy
(which is validated on a real machine against real documents).
"""

from __future__ import annotations

import json

import pytest

from satc.config import load_extraction_map
from satc.fixtures.sample_docs import TEXT_W2
from satc.ingest.readers import OllamaVisionReader, TesseractOcrReader

W2 = load_extraction_map("w2")


# -- local OCR reader ---------------------------------------------------------

def test_ocr_reader_extracts_via_injected_text():
    # Pretend Tesseract returned this text; the reader anchors values out of it.
    reader = TesseractOcrReader(W2, text_provider=lambda _src: "\n".join(TEXT_W2))
    result = reader.read("scan.png")
    assert result.labeled_fields["Box 1 - Wages, tips, other comp"] == "98000.00"
    assert result.backend == "TesseractOcrReader"


def test_ocr_values_are_all_flagged_for_review():
    reader = TesseractOcrReader(W2, text_provider=lambda _src: "\n".join(TEXT_W2))
    result = reader.read("scan.png")
    # OCR is noisy: nothing auto-confirms — every read is uncertain (LOW).
    assert result.uncertain_labels == set(result.labeled_fields)
    assert set(result.confidence_map().values()) == {"LOW"}


# -- local Ollama vision reader ----------------------------------------------

def _fake_ollama(canned: dict):
    return lambda _payload: {"message": {"content": json.dumps(canned)}}


def test_ollama_reader_maps_json_to_labeled_fields(tmp_path):
    img = tmp_path / "w2.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n fake image bytes")
    reader = OllamaVisionReader(W2, transport=_fake_ollama(
        {"w2.box1_wages": "98000.00", "w2.employer_ein": "31-0009999"}))
    result = reader.read(str(img))
    assert result.labeled_fields["Box 1 - Wages, tips, other comp"] == "98000.00"
    assert "OllamaVisionReader" in result.backend
    assert result.uncertain_labels == set(result.labeled_fields)   # local model: review all


def test_ollama_reader_ignores_nulls(tmp_path):
    img = tmp_path / "w2.png"
    img.write_bytes(b"fake")
    reader = OllamaVisionReader(W2, transport=_fake_ollama(
        {"w2.box1_wages": "50000.00", "w2.box2_fed_wh": None}))
    fields = reader.read(str(img)).labeled_fields
    assert "Box 1 - Wages, tips, other comp" in fields
    assert "Box 2 - Federal income tax withheld" not in fields    # null dropped, never guessed


# -- cloud posture ------------------------------------------------------------

def test_cloud_is_off_without_explicit_opt_in(monkeypatch):
    from satc import settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")     # a key alone is not enough
    monkeypatch.delenv("SATC_ALLOW_CLOUD", raising=False)
    assert settings.cloud_vision_enabled() is False
    monkeypatch.setenv("SATC_ALLOW_CLOUD", "1")
    assert settings.cloud_vision_enabled() is True


def test_ollama_is_opt_in(monkeypatch):
    from satc import settings
    monkeypatch.delenv("SATC_OLLAMA", raising=False)
    assert settings.ollama_enabled() is False
    monkeypatch.setenv("SATC_OLLAMA", "yes")
    assert settings.ollama_enabled() is True


# -- classifier OCR fallback --------------------------------------------------

def test_classifier_types_a_scan_via_injected_ocr():
    from satc.ingest import load_classifier
    clf = load_classifier(has_key=False)
    clf.ocr_text_provider = lambda _p: "\n".join(TEXT_W2)   # pretend Tesseract read the scan
    c = clf.classify_path("/tmp/IMG_9999.png")             # no form fields, no text layer
    assert c.label == "W-2"
    assert c.method == "ocr"
