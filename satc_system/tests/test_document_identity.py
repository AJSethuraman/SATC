"""Content-hash document identity — and the wrong-field-confirm bug it kills.

``document_id`` used to be the file's basename, and a staged field's id is
``f"{document_id}:{field_path}"``. Two files called ``W2.pdf`` in different year
folders therefore produced *the same field ids*, and ``StagingGate._find``
returns the first match — so confirming a 2024 wage figure could write onto the
2023 document's field. That is a silent wrong answer in the evidentiary record.

Three properties are tested here, each of which was previously false:

  * distinct content gets distinct ids, whatever the files are called;
  * identical content gets the SAME id, so re-reading a folder is idempotent;
  * no client filename reaches an id, because ids are exported and filenames
    carry client names.
"""

from __future__ import annotations

from decimal import Decimal

from satc.ids import (
    content_document_id,
    content_document_id_for_path,
    part_document_id,
)
from satc.ingest.staging_gate import StagingGate
from satc.models.provenance import Provenance, SourceRef
from satc.models.staging import StagedDocument, StagedField


def _doc(document_id: str, *, display: str = "", value: str = "1") -> StagedDocument:
    return StagedDocument(
        document_id=document_id, client_id="C", tax_year=2024, doc_type="W-2",
        display_name=display,
        fields=[StagedField(
            field_id=f"{document_id}:w2.box1_wages", document_id=document_id,
            client_id="C", tax_year=2024, field_path="w2.box1_wages", label="Wages",
            value_text=value, value_amount=Decimal(value),
            provenance=Provenance(source_kind="SOURCE_DOC", source_ref=SourceRef()))])


# --- the id itself ------------------------------------------------------------

def test_the_same_bytes_always_give_the_same_id():
    assert content_document_id(b"W-2 content") == content_document_id(b"W-2 content")


def test_different_bytes_give_different_ids():
    assert content_document_id(b"2024 W-2") != content_document_id(b"2023 W-2")


def test_an_id_carries_no_filename():
    """Ids reach the mart and the Excel export; client filenames carry names."""
    doc_id = content_document_id(b"anything")
    assert "Maplewood" not in doc_id
    assert doc_id.startswith("doc-")
    assert doc_id[4:].isalnum()


def test_hashing_a_file_matches_hashing_its_bytes(tmp_path):
    path = tmp_path / "W2.pdf"
    path.write_bytes(b"the same content")
    assert content_document_id_for_path(path) == content_document_id(b"the same content")


def test_two_files_with_the_same_name_get_different_ids(tmp_path):
    """THE BUG. Same basename, different folders, different content."""
    (tmp_path / "2024").mkdir()
    (tmp_path / "2023").mkdir()
    a = tmp_path / "2024" / "W2.pdf"
    b = tmp_path / "2023" / "W2.pdf"
    a.write_bytes(b"2024 wages 145000")
    b.write_bytes(b"2023 wages 138000")
    assert a.name == b.name
    assert content_document_id_for_path(a) != content_document_id_for_path(b)


def test_split_parts_are_distinct_and_traceable_to_their_parent():
    parent = content_document_id(b"a combined pdf")
    p1, p2 = part_document_id(parent, 1), part_document_id(parent, 2)
    assert p1 != p2
    assert p1.startswith(parent) and p2.startswith(parent)


# --- the consequence: fields no longer collide -------------------------------

def test_same_named_documents_produce_distinct_field_ids():
    gate = StagingGate()
    gate.add(_doc(content_document_id(b"2024 W-2"), display="W2.pdf", value="145000"))
    gate.add(_doc(content_document_id(b"2023 W-2"), display="W2.pdf", value="138000"))

    field_ids = [f.field_id for f in gate.all_fields()]
    assert len(field_ids) == len(set(field_ids)), "field ids still collide"


def test_confirming_one_document_does_not_touch_the_other():
    """The bug's actual consequence, end to end."""
    from satc.models.actor import Actor

    gate = StagingGate()
    a_id = content_document_id(b"2024 W-2")
    b_id = content_document_id(b"2023 W-2")
    gate.add(_doc(a_id, display="W2.pdf", value="145000"))
    gate.add(_doc(b_id, display="W2.pdf", value="138000"))

    gate.confirm(f"{a_id}:w2.box1_wages", Actor.owner())

    confirmed = gate.confirmed()
    assert len(confirmed) == 1
    assert confirmed[0].effective_amount() == Decimal("145000")
    other = gate.find_document(b_id).fields[0]
    assert other.status == "STAGED"


# --- idempotence (doctrine rule 4) -------------------------------------------

def test_staging_the_same_document_twice_is_a_no_op():
    """An original and the copy sort_folder made hash identically."""
    gate = StagingGate()
    doc_id = content_document_id(b"identical bytes")
    gate.add(_doc(doc_id, display="W2.pdf"))
    gate.add(_doc(doc_id, display="_SATC_Sorted/W-2/W2.pdf"))
    assert len(gate.documents) == 1
    assert len(gate.all_fields()) == 1


def test_the_first_staging_wins_and_keeps_its_label():
    gate = StagingGate()
    doc_id = content_document_id(b"bytes")
    gate.add(_doc(doc_id, display="original.pdf"))
    gate.add(_doc(doc_id, display="copy.pdf"))
    assert gate.documents[0].display_name == "original.pdf"


# --- the display name stays local --------------------------------------------

def test_the_readable_label_is_available_for_the_ui():
    doc = _doc("doc-abc123", display="Maplewood_W2_2024.pdf")
    assert doc.label() == "Maplewood_W2_2024.pdf"


def test_a_document_with_no_display_name_falls_back_to_its_id():
    assert _doc("doc-abc123").label() == "doc-abc123"


def test_the_display_name_is_not_part_of_identity():
    """Renaming a file must not change which document it is."""
    a = _doc("doc-abc123", display="W2.pdf")
    b = _doc("doc-abc123", display="renamed_by_client.pdf")
    assert a.document_id == b.document_id
