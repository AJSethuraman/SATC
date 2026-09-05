"""A field is checked against what it may hold, not only against how sure we were.

D9, FROM THE WALK OF 5 SEPTEMBER 2026.

Reading a W-2 line

    Box 17   State income tax   2,679.00

put the string **"income tax"** into **Box 15 — State**, a field whose only
legal values are the two-letter codes.

It was caught. It was staged LOW and left for review, so nothing reached a
return. **But it was caught by confidence, not by validity** — the read happened
to come back uncertain. Nothing on the row knew a state field cannot hold a verb
phrase, so the identical mistake at HIGH confidence would have auto-confirmed,
gone into the Drake input as `box15_state`, and from there onto a filed return.

Confidence answers *how sure was the reader*. A shape answers *could this be
right at all*. They are different questions and only one of them was being
asked — and the one that was missing is the one that catches a reader which is
confidently wrong, which is the only case nothing else stops.

BOTH DOORS, because `edit()` is the more dangerous one: it sets a value AND
confirms it in a single move, marks the result PREPARER_ENTRY at HIGH, and
clears every model taint. A check on the reader alone would leave the correction
screen as the way around it.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.ingest import shapes
from satc.ingest.extractors.base import make_staged_field
from satc.ingest.extractors.mapping import MapExtractor
from satc.ingest.staging_gate import StagingGate
from satc.models.actor import Actor


def _field(raw, *, shape="state", confidence="HIGH"):
    return make_staged_field(
        field_id="doc:w2.box15_state", document_id="doc", client_id="SATC-001000",
        tax_year=2025, field_path="w2.box15_state", label="Box 15 - State",
        raw_value=raw, is_money=False, extractor="test", shape=shape,
        base_confidence=confidence)


# ── the shape itself ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("good", ["OH", "oh", " PA ", "DC", "PR", "VI"])
def test_a_state_code_fits(good):
    assert shapes.fits("state", good)


@pytest.mark.parametrize("bad", ["income tax", "Ohio", "O", "OHH", "12", "XX"])
def test_a_thing_that_is_not_a_state_code_does_not(bad):
    assert not shapes.fits("state", bad)


def test_an_empty_value_fits_anything():
    """A box the reader found nothing in is an ordinary state of a document.
    Failing it would bury the real failures under the routine ones."""
    assert shapes.fits("state", "")
    assert shapes.fits("state", "   ")


def test_an_undeclared_shape_fits_anything():
    """A field nobody has described has no rule to break, and inventing one
    would reject values on a guess."""
    assert shapes.fits("", "income tax")
    assert shapes.fits("employer_name", "income tax")


def test_the_refusal_says_what_was_expected():
    """"not a state" tells a preparer nothing they had not already worked out."""
    said = shapes.refusal("state", "income tax")
    assert "income tax" in said
    assert "two-letter" in said


# ── the reader ────────────────────────────────────────────────────────────────

def test_a_confident_read_of_the_wrong_thing_no_longer_auto_confirms():
    """THE DEFECT, at the confidence that made it dangerous."""
    f = _field("income tax", confidence="HIGH")
    assert f.status == "NEEDS_REVIEW", (
        "a confidently-read verb phrase is still eligible for auto-confirmation "
        "as the state on a W-2")
    assert f.provenance.confidence == "UNCERTAIN"


def test_the_value_is_kept_rather_than_blanked():
    """The preparer has to see what the document actually said to decide, and a
    cleared field loses the evidence that the reader went wrong."""
    assert _field("income tax").value_text == "income tax"


def test_the_note_says_why():
    f = _field("income tax")
    assert "two-letter" in f.note
    assert "income tax" in f.note


def test_a_real_state_still_passes_straight_through():
    """The control. A check that fails everything is not a check."""
    f = _field("OH", confidence="HIGH")
    assert f.status == "STAGED"
    assert f.provenance.confidence == "HIGH"
    assert not f.note


def test_a_field_with_no_declared_shape_is_untouched():
    """The other control -- this must not start second-guessing employer names."""
    f = make_staged_field(
        field_id="doc:w2.employer_name", document_id="doc", client_id="SATC-001000",
        tax_year=2025, field_path="w2.employer_name", label="Employer name",
        raw_value="Meridian Logistics & Co", is_money=False, extractor="test")
    assert f.status == "STAGED"
    assert f.provenance.confidence == "HIGH"


# ── the declaration reaches the reader ────────────────────────────────────────

def test_the_w2_config_declares_the_shape():
    """The denominator. Without the declaration the check never runs on a real
    document, and every assertion above is about a parameter nobody passes."""
    import yaml
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = yaml.safe_load((root / "configs" / "extraction" / "w2.yaml").read_text())
    box15 = next(f for f in spec["fields"] if f["field_path"] == "w2.box15_state")
    assert box15.get("shape") == "state", "Box 15 does not declare what it may hold"


def test_reading_a_real_w2_flags_the_bad_state():
    """Through `MapExtractor` on the REAL config, which is the path a document
    takes. The unit tests above pass `shape=` by hand and would keep passing if
    the declaration never reached the extractor."""
    import yaml
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs" / "extraction" / "w2.yaml").read_text())
    extractor = MapExtractor(config)
    staged = extractor.extract(
        labeled_fields={"Box 15 - State": "income tax", "Box 1 - Wages, tips, other comp": "92,400.00"},
        document_id="doc", client_id="SATC-001000", tax_year=2025)

    state = next(f for f in staged.fields if f.field_path == "w2.box15_state")
    assert state.status == "NEEDS_REVIEW", "the config's shape never reached the field"
    wages = next(f for f in staged.fields if f.field_path == "w2.box1_wages")
    assert wages.status == "STAGED", "a good money field was caught in the net"


# ── the correction screen ─────────────────────────────────────────────────────

def _gate_with(field):
    from satc.models.staging import StagedDocument

    doc = StagedDocument(document_id="doc", client_id="SATC-001000", tax_year=2025,
                         doc_type="W-2", source_path="", fields=[field])
    return StagingGate([doc])


OWNER = Actor(kind="human", name="owner")


def test_a_hand_correction_must_meet_the_same_rule():
    """`edit` sets AND confirms, marks the result HIGH, and clears every taint --
    so without this it is simply the way around the reader's check."""
    f = _field("income tax")
    gate = _gate_with(f)
    assert not gate.edit(f.field_id, OWNER, value_text="Ohio"), (
        "the correction screen accepted a value the reader would have been "
        "refused for")
    assert f.status == "NEEDS_REVIEW", "the refused edit confirmed the field anyway"


def test_a_correct_hand_correction_goes_through():
    """The control. The preparer fixing the read is the whole point of the screen."""
    f = _field("income tax")
    gate = _gate_with(f)
    assert gate.edit(f.field_id, OWNER, value_text="OH")
    assert f.status == "CONFIRMED"
    assert f.effective_text() == "OH"


def test_a_money_correction_is_unaffected():
    """The other control -- D2's refusal and this one must not collide."""
    money = make_staged_field(
        field_id="doc:w2.box1_wages", document_id="doc", client_id="SATC-001000",
        tax_year=2025, field_path="w2.box1_wages", label="Box 1 - Wages",
        raw_value="92,400.00", is_money=True, extractor="test")
    gate = _gate_with(money)
    assert gate.edit(money.field_id, OWNER, value_text="88,000.00",
                     value_amount=Decimal("88000.00"))
    assert money.effective_amount() == Decimal("88000.00")
