from pathlib import Path
from tax_packet_qa import build_inventory, detect_modules, load_config


def test_detects_five_modules_from_sample():
    base = Path(__file__).resolve().parents[1]
    inventory = build_inventory(base / "sample_client" / "sorted_documents")
    config = load_config(base / "config" / "tax_modules.yaml")
    detected = detect_modules(inventory, config["modules"])
    ids = {d["module_id"] for d in detected}
    expected = {"w2_wages", "investments", "self_employed_schedule_c", "rental_property", "homeowner_mortgage"}
    assert expected.issubset(ids)


def test_brokerage_trigger_investments():
    base = Path(__file__).resolve().parents[1]
    inventory = build_inventory(base / "sample_client" / "sorted_documents")
    config = load_config(base / "config" / "tax_modules.yaml")
    detected = detect_modules(inventory, config["modules"])
    inv = [d for d in detected if d["module_id"] == "investments"][0]
    assert inv["strength"] in {"Medium", "Strong"}
