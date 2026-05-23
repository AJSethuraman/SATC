from pathlib import Path
from tax_packet_qa import build_inventory, detect_modules, load_config, generate_missing_items, write_outputs


def test_missing_review_and_outputs_written(tmp_path):
    base = Path(__file__).resolve().parents[1]
    inventory = build_inventory(base / "sample_client" / "sorted_documents")
    config = load_config(base / "config" / "tax_modules.json")
    detected = detect_modules(inventory, config["modules"])
    rows = generate_missing_items(detected, config["modules"], inventory)
    assert any(r["status"] in {"Missing", "Needs Review"} for r in rows)

    write_outputs(tmp_path, inventory, detected, rows)
    assert (tmp_path / "inventory.json").exists()
    assert (tmp_path / "inventory.xlsx").exists()
    assert (tmp_path / "client_follow_up_questions.txt").exists()
    assert (tmp_path / "preparer_notes.txt").exists()


def test_original_files_not_modified(tmp_path):
    src = tmp_path / "input" / "01_W2"
    src.mkdir(parents=True)
    file_path = src / "W2_Test_2025.pdf"
    file_path.write_text("placeholder", encoding="utf-8")
    before = file_path.stat().st_mtime_ns

    from tax_packet_qa import run

    base = Path(__file__).resolve().parents[1]
    run(tmp_path / "input", base / "config" / "tax_modules.json", tmp_path / "outputs")

    after = file_path.stat().st_mtime_ns
    assert before == after
