"""Staging-gate editing: hand-correct, un-accept, and delete a staged field."""

from __future__ import annotations

from decimal import Decimal

from satc.ingest.staging_gate import StagingGate
from satc.models.provenance import Provenance, SourceRef
from satc.models.staging import StagedDocument, StagedField


def _gate(status="STAGED", confidence="HIGH", amount=None, text=""):
    f = StagedField(
        field_id="f1", document_id="d1", client_id="c", tax_year=2024,
        field_path="w2.box1_wages", label="Wages", value_text=text,
        provenance=Provenance(source_kind="SOURCE_DOC", confidence=confidence,
                              source_ref=SourceRef()),
        value_amount=amount, status=status)
    g = StagingGate()
    g.add(StagedDocument(document_id="d1", client_id="c", tax_year=2024, doc_type="W-2", fields=[f]))
    return g, f


def test_unconfirm_sends_a_confirmed_value_back_to_review():
    g, f = _gate(status="CONFIRMED")
    f.confirmed_by = "auto"
    assert g.unconfirm("f1")
    assert f.status == "STAGED"
    assert f.confirmed_by == "" and f.confirmed_at is None


def test_delete_removes_the_field_entirely():
    g, _ = _gate()
    assert g.delete_field("f1")
    assert g.all_fields() == []
    assert g.delete_field("f1") is False


def test_edit_hand_corrects_and_confirms_with_exact_amount():
    g, _ = _gate(amount=Decimal("145000"), text="145000")
    assert g.edit("f1", value_text="145030", value_amount=Decimal("145030"))
    f = g.all_fields()[0]
    assert f.status == "CONFIRMED"
    assert f.effective_text() == "145030"
    assert f.effective_amount() == Decimal("145030")   # exact cents, no rounding
    assert "hand-corrected" in f.note
