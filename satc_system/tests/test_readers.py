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
from satc.models.actor import INTAKE


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
    gate.auto_confirm_high(INTAKE)
    confirmed = {f.field_path for f in gate.confirmed()}
    # CHANGED 31 Aug 2026. This used to assert that "a clean, confident field
    # auto-confirms" -- w2.box1_wages went straight into the workpaper because
    # the model had not named it in `uncertain_fields`.
    #
    # The firm asked for deterministic first, and the half of that which lives
    # here is: a model's self-assessment is not evidence, it is the same faculty
    # that produced the answer asked whether it is happy with it. NOTHING a
    # vision model reads auto-confirms now, flagged or not.
    assert confirmed == set(), \
        "a vision model's reading reached the workpaper without a human"
    # The per-field flag still does its own job -- it is a hint to the preparer
    # about WHICH fields to look at hardest, not a licence for the others.
    assert any(f.field_path == "w2.box3_ss_wages" for f in gate.needs_review())
    assert any(f.field_path == "w2.box1_wages" for f in gate.needs_review())


# ── the context window the vision rung asks for ────────────────────────────

def test_the_vision_reader_sends_a_context_size():
    """It used to send none, so the value was whatever the model defaulted to.

    On the Forge that is the difference between running wholly on the GPU and
    spilling to the CPU, and there was no setting to pin. Measured 3 September
    2026: `qwen2.5vl:7b` at 8192 reads `15%/85% CPU/GPU`; at 4096 it reads
    `100% GPU`, with a real page attached.
    """
    from satc.ingest.readers.ollama import OllamaVisionReader

    sent = {}
    reader = OllamaVisionReader(
        {"doc_type": "W-2", "fields": [{"field_path": "wages"}]},
        transport=lambda payload: sent.update(payload) or {"message": {"content": "{}"}})
    reader.read(str(_a_png()))

    assert "options" in sent, "no options block: num_ctx was never sent"
    assert sent["options"]["num_ctx"] == 4096


def test_the_context_size_can_be_overridden_but_never_to_nonsense():
    """`SATC_OLLAMA_NUM_CTX` is the knob. A junk value falls back rather than
    being passed to Ollama, because a bad context is a silent CPU spill."""
    import os
    from satc.settings import ollama_num_ctx, OLLAMA_NUM_CTX_DEFAULT

    for raw, expected in [("8192", 8192), ("", OLLAMA_NUM_CTX_DEFAULT),
                          ("abc", OLLAMA_NUM_CTX_DEFAULT),
                          ("0", OLLAMA_NUM_CTX_DEFAULT),
                          ("-1", OLLAMA_NUM_CTX_DEFAULT)]:
        old = os.environ.get("SATC_OLLAMA_NUM_CTX")
        os.environ["SATC_OLLAMA_NUM_CTX"] = raw
        try:
            assert ollama_num_ctx() == expected, f"{raw!r}"
        finally:
            if old is None:
                os.environ.pop("SATC_OLLAMA_NUM_CTX", None)
            else:
                os.environ["SATC_OLLAMA_NUM_CTX"] = old


def _a_png():
    """A 1x1 PNG on disk — the reader only needs something to base64."""
    import base64, tempfile
    from pathlib import Path
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    p = Path(tempfile.mkdtemp()) / "page.png"
    p.write_bytes(raw)
    return p
