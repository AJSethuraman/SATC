from __future__ import annotations

from pathlib import Path

from tax_packet_qa import build_inventory, detect_modules, generate_missing_items, load_config, run


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder", encoding="utf-8")


def _execute_case(tmp_path: Path, case_name: str, rel_files: list[str]):
    input_root = tmp_path / case_name / "sorted"
    for rel in rel_files:
        _touch(input_root / rel)

    before = {p: p.stat().st_mtime_ns for p in input_root.rglob("*") if p.is_file()}

    base = Path(__file__).resolve().parents[1]
    cfg_path = base / "config" / "tax_modules.yaml"
    out_dir = tmp_path / case_name / "outputs"

    run(input_root, cfg_path, out_dir)

    for p, ts in before.items():
        assert p.stat().st_mtime_ns == ts

    inv = build_inventory(input_root)
    cfg = load_config(cfg_path)
    det = detect_modules(inv, cfg["modules"])
    missing = generate_missing_items(det, cfg["modules"], inv)

    for f in [
        "inventory.json",
        "inventory.xlsx",
        "inventory_report.html",
        "missing_items_report.html",
        "client_follow_up_questions.txt",
        "preparer_notes.txt",
    ]:
        assert (out_dir / f).exists()

    return inv, det, missing, out_dir


def test_stress_scenarios(tmp_path: Path):
    # 1) clean simple
    inv, det, missing, _ = _execute_case(
        tmp_path,
        "clean_simple",
        [
            "01_W2/W2_Acme_2025.pdf",
            "03_1099_INT/1099_INT_Bank_2025.pdf",
            "06_1098_Mortgage/1098_Mortgage_Chase_2025.pdf",
        ],
    )
    ids = {d["module_id"] for d in det}
    assert "w2_wages" in ids and "homeowner_mortgage" in ids

    # 2) self-employed missing expense summary
    _, det, missing, _ = _execute_case(
        tmp_path,
        "self_employed",
        ["02_1099_NEC/1099_NEC_ClientWork_2025.pdf", "Business/Business_Bank_2025.csv"],
    )
    sched_c = [r for r in missing if r["module"] == "Schedule C / Self-Employed"]
    assert sched_c
    assert any(r["status"] in {"Missing", "Needs Review"} for r in sched_c)

    # 3) rental missing mortgage interest if financed => Needs Review
    _, det, missing, _ = _execute_case(
        tmp_path,
        "rental",
        ["Rental/Rent_Ledger_2025.pdf", "Rental/Property_Tax_2025.pdf", "Rental/Repair_Receipts_2025.pdf"],
    )
    rental = [r for r in missing if r["module"] == "Rental Property"]
    mortgage_if_financed = [r for r in rental if r["item_id"] == "mortgage_interest_if_financed"]
    assert mortgage_if_financed and mortgage_if_financed[0]["status"] == "Needs Review"

    # 4) investments aliases
    _, det, missing, _ = _execute_case(
        tmp_path,
        "investments",
        [
            "09_Brokerage/Fidelity_Consolidated_1099_2025.pdf",
            "09_Brokerage/1099-B_Trades_2025.pdf",
            "09_Brokerage/1099-DIV_2025.pdf",
        ],
    )
    inv_mod = [d for d in det if d["module_id"] == "investments"]
    assert inv_mod
    chk = [r for r in missing if r["module"] == "Investments" and r["item_id"] == "consolidated_brokerage_1099"]
    assert chk and chk[0]["status"] == "Found"

    # 5) education/homeowner edge
    _, det, _, _ = _execute_case(tmp_path, "education_edge", ["Education/1098-T_StateU_2025.pdf"])
    ids = {d["module_id"] for d in det}
    assert "homeowner_mortgage" not in ids

    # 6) ambiguous property tax should not strongly trigger rental by itself
    _, det, _, _ = _execute_case(tmp_path, "ambiguous_property_tax", ["Taxes/Property_Tax_2025.pdf"])
    rental = [d for d in det if d["module_id"] == "rental_property"]
    assert not rental

    # 7) mixed years visible
    inv, _, _, _ = _execute_case(tmp_path, "mixed_year", ["01_W2/W2_Acme_2024.pdf", "01_W2/W2_Acme_2025.pdf"])
    years = {i.inferred_tax_year for i in inv}
    assert "2024" in years and "2025" in years

    # 8) duplicate filenames
    inv, _, _, _ = _execute_case(tmp_path, "duplicates", ["A/W2_Acme_2025.pdf", "B/W2_Acme_2025.pdf"])
    assert all(i.duplicate_flag for i in inv)

    # 9) noisy unknown should not create confident modules
    _, det, _, _ = _execute_case(tmp_path, "noisy", ["Misc/IMG_1234.pdf", "Misc/scan.pdf", "Misc/receipt.pdf"])
    assert det == []

    # 10) special chars escaped in html
    _, _, _, out = _execute_case(tmp_path, "special_chars", ['Misc/Rent & Repair <Final> "2025".pdf'])
    html_text = (out / "inventory_report.html").read_text(encoding="utf-8")
    assert "&lt;Final&gt;" in html_text and "&amp;" in html_text
