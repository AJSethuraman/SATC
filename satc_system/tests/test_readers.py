"""Tests for the document-reader front end (PDF form-field + Claude vision).

The vision backend is exercised with an INJECTED fake Anthropic client, so these
run with no API key and no network. They prove the key guarantees: clean fields
flow through, sensitive TINs are masked, and anything the reader flags uncertain
(or that doesn't parse) is held for review rather than auto-confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path

from satc.config import load_extraction_map
from satc.ingest import StagingGate, read_and_stage
from satc.ingest.readers import PdfFormReader, VisionDocumentReader


def test_pdf_form_reader_maps_named_fields():
    cfg = load_extraction_map("w2")
    reader = PdfFormReader(cfg)
    result = reader.read_fields({
        "Box 1 - Wages, tips, other comp": "98000",
        "Employer EIN": "31-0009999",
        "Totally Unknown Field": "ignore me",
    })
    # Mapped to the spec labels; unknown field dropped (conservative).
    assert "Box 1 - Wages, tips, other comp" in result.labeled_fields
    assert "Employer EIN" in result.labeled_fields
    assert "Totally Unknown Field" not in result.labeled_fields


# --- a tiny fake Anthropic client ------------------------------------------
class _FakeBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _FakeResp:
    def __init__(self, text: str):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, payload: dict):
        self._payload = payload

    def create(self, **kwargs):  # mirrors client.messages.create(...)
        return _FakeResp(json.dumps(self._payload))


class _FakeClient:
    def __init__(self, payload: dict):
        self.messages = _FakeMessages(payload)


def _png(tmp_path) -> str:
    # The fake client ignores the image, so any bytes in a .png file suffice.
    p = Path(tmp_path) / "w2.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n fake image bytes")
    return str(p)


def test_vision_reader_flags_uncertain_and_masks_tin(tmp_path):
    cfg = load_extraction_map("w2")
    payload = {
        "w2.box1_wages": "98,000.00",
        "w2.box2_fed_wh": "12,500.00",
        "w2.box3_ss_wages": "98,000.00",
        "w2.box17_state_wh": "see W-2 stub",   # malformed money
        "w2.employer_name": "Buckeye Manufacturing LLC",
        "w2.employer_ein": "31-0009999",
        "uncertain_fields": ["w2.box3_ss_wages", "w2.box17_state_wh"],
    }
    reader = VisionDocumentReader(cfg, client=_FakeClient(payload))
    staged = read_and_stage(
        reader, _png(tmp_path), config=cfg,
        document_id="DOC-VIS-1", client_id="SATC-001000", tax_year=2024)

    by_path = {f.field_path: f for f in staged.fields}
    # Sensitive EIN masked to last-4 — never the full value.
    assert by_path["w2.employer_ein"].value_text == "**-***9999"
    # Malformed money routed to review, no amount guessed.
    assert by_path["w2.box17_state_wh"].status == "NEEDS_REVIEW"
    assert by_path["w2.box17_state_wh"].value_amount is None

    gate = StagingGate().add(staged)
    gate.auto_confirm_high()
    confirmed = {f.field_path for f in gate.confirmed()}
    # A clean, confident field auto-confirms…
    assert "w2.box1_wages" in confirmed
    # …but a field the model flagged uncertain does NOT, even though it parses.
    assert "w2.box3_ss_wages" not in confirmed
    assert any(f.field_path == "w2.box3_ss_wages" for f in gate.needs_review())
