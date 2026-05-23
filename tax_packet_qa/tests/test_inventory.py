from pathlib import Path
from tax_packet_qa import build_inventory, infer_document_type


def test_inventory_builds_from_folder_structure():
    root = Path(__file__).resolve().parents[1] / "sample_client" / "sorted_documents"
    inventory = build_inventory(root)
    assert len(inventory) >= 6
    assert any(i.inferred_document_type == "w-2" for i in inventory)


def test_document_type_inference_known_keywords():
    doc_type, conf, _ = infer_document_type("01_W2/W2_AcmeCorp_2025.pdf")
    assert doc_type == "w-2"
    assert conf >= 0.6
