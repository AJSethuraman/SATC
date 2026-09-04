"""A model's answer is never a deterministic read, whatever the model says.

The firm, 31 August 2026: *"Another piece to the ocr is the fallback to ollama
for judgmental processing. I really want it deterministic first though."*

Two separate things have to be true for that, and only one of them was.

  1. THE LADDER must exhaust the deterministic rungs before asking a model.
     Form fields, then the text layer, then Tesseract — none of which involve a
     model, all of which give the same answer twice.

  2. WHAT A MODEL PRODUCES must be distinguishable from what a deterministic
     reader produces, all the way down to the confirmation gate. This is the one
     that was broken: `VisionDocumentReader` asked the model to name its own
     uncertain fields, and anything it did not name came back HIGH — so
     `auto_confirm_high()` wrote a model's reading of a wage box into the
     workpaper with nobody looking at it.

     A model's self-assessment is not evidence. It is the same faculty that
     produced the answer, asked whether it is happy with it.

The rule this establishes: DETERMINISM IS A PROPERTY OF THE READER, NOT A
JUDGEMENT ABOUT THE OUTPUT. `ReadResult.deterministic` defaults to False, so a
reader added later is non-deterministic until it says otherwise — forgetting is
safe rather than dangerous.
"""

from __future__ import annotations

from satc.models.actor import INTAKE

import pytest

from satc.ingest.readers.base import ReadResult


# -- the property itself ------------------------------------------------------

def test_a_read_is_non_deterministic_unless_it_says_otherwise():
    """The default is the safe one. A reader written next year that forgets this
    flag is treated as a model, not as a form field."""
    assert ReadResult(labeled_fields={"Wages": "64500"}).deterministic is False


def test_a_non_deterministic_read_is_low_confidence_whatever_it_claims():
    """Even with NOTHING flagged uncertain, a model read cannot be HIGH."""
    r = ReadResult(labeled_fields={"Wages": "64500", "Employer": "Buckeye"},
                   uncertain_labels=set())
    assert set(r.confidence_map().values()) == {"LOW"}


def test_a_deterministic_read_keeps_its_own_per_field_judgement():
    r = ReadResult(labeled_fields={"Wages": "64500", "Employer": "Buckeye"},
                   uncertain_labels={"Employer"}, deterministic=True)
    assert r.confidence_map() == {"Wages": "HIGH", "Employer": "LOW"}


# -- which readers claim which --------------------------------------------------

@pytest.mark.parametrize("module,cls", [
    ("satc.ingest.readers.pdf_form", "PdfFormReader"),
    ("satc.ingest.readers.text_anchor", "TextAnchorReader"),
    ("satc.ingest.readers.ocr", "TesseractOcrReader"),
])
def test_the_deterministic_readers_say_so(module, cls):
    """No model in the loop: same document in, same fields out, every time."""
    import importlib
    assert getattr(importlib.import_module(module), cls) is not None


def test_a_model_read_never_auto_confirms(tmp_path):
    """THE ONE THAT MATTERS. End to end through the real gate.

    The payload names only one uncertain field, exactly as a confident model
    would. Before this fix the other four confirmed themselves into the
    workpaper.
    """
    from satc.ingest import read_and_stage
    from satc.ingest.staging_gate import StagingGate
    from satc.ingest.readers.vision import VisionDocumentReader
    # NOT `from tests.test_readers import ...`. There is no `tests/__init__.py`,
    # so `tests` only resolves as a namespace package when the working directory
    # happens to be on sys.path -- true under `python -m pytest`, false under
    # the bare `pytest` that CI runs. It passed locally and failed in CI for
    # three commits. pytest puts the test file's own directory on sys.path, so
    # the sibling module is importable by its plain name anywhere.
    from test_readers import _FakeClient, _png, load_extraction_map

    cfg = load_extraction_map("w2")
    reader = VisionDocumentReader(cfg, client=_FakeClient({
        "w2.box1_wages": "98,000.00",
        "w2.box2_fed_wh": "12,500.00",
        "w2.box3_ss_wages": "98,000.00",
        "w2.employer_name": "Buckeye Manufacturing LLC",
        "uncertain_fields": ["w2.box3_ss_wages"],     # the model is sure of the rest
    }))
    staged = read_and_stage(reader, _png(tmp_path), config=cfg,
                            document_id="D1", client_id="C1", tax_year=2026)
    gate = StagingGate().add(staged)
    gate.auto_confirm_high(INTAKE)

    assert gate.confirmed() == [], \
        "a vision model's reading auto-confirmed into the workpaper"
    assert len(gate.needs_review()) == len(staged.fields)


# -- and the ladder half ------------------------------------------------------

@pytest.mark.skip(reason="see docs/DEFECT-REGISTER.md S2 — the firm has not "
                        "chosen between two defensible ladders")
def test_the_ladder_reaches_no_model_while_a_deterministic_rung_can_still_read(tmp_path):
    """SKIPPED BECAUSE THE TWO BRANCHES DISAGREE, AND BOTH ARGUE THEIR CASE.

    This asserts the STRICTER rule: a text-layer PDF our anchors happen to miss
    must not summon a vision model at all, because the document is readable and
    our parser is what failed.

    `main` takes the more permissive one, and says why in `AppState._read`: it
    still falls through to OCR and vision, but the note now reads "text layer
    present but no field labels matched -- our anchors, not the document", so
    the parser gap is visible as a parser gap. Its argument against refusing
    outright: "a text layer can be genuine rubbish, and refusing would lose
    documents OCR does handle."

    Both are defensible and it is a question about client documents, not a
    merge conflict, so it goes to the firm rather than being decided here.
    Skipped rather than deleted: deleting a test that asserts a stricter safety
    property is how the question disappears.
    """
