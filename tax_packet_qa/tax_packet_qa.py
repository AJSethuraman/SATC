from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


DOC_TYPE_RULES: dict[str, list[str]] = {
    "w-2": ["w2", "w-2"],
    "1099-nec": ["1099-nec", "1099_nec", "1099 nec"],
    "1099-int": ["1099-int", "1099_int", "1099 int"],
    "1099-div": ["1099-div", "1099_div", "1099 div"],
    "1099-b": ["1099-b", "1099_b", "1099 b", "brokerage", "consolidated 1099"],
    "1098 mortgage": ["1098", "mortgage", "mortgage interest"],
    "rent ledger": ["rent ledger", "rental income summary"],
    "schedule c support": ["schedule c", "business receipts", "business bank", "1099-nec"],
    "property tax": ["property tax"],
    "rental insurance": ["rental insurance"],
    "repair receipts": ["repair", "maintenance"],
}

SATC_THEME = {
    "navy": "#0B1F3A",
    "paper": "#FBF9F4",
    "ink": "#0E1726",
    "hairline": "#D9CFB8",
    "navy_soft": "#173361",
    "navy_deep": "#061A35",
}


@dataclass
class InventoryItem:
    original_file_path: str
    filename: str
    parent_folder: str
    inferred_document_type: str
    inferred_tax_year: str
    inferred_entity_name: str
    confidence: float
    evidence: str
    duplicate_flag: bool
    notes: str = ""


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("YAML config requires PyYAML. Use JSON config or install PyYAML.")
        return yaml.safe_load(text)
    return json.loads(text)


def infer_year(text: str) -> str:
    match = re.search(r"\b(20\d{2})\b", text)
    return match.group(1) if match else ""


def infer_entity_name(filename: str) -> str:
    stem = Path(filename).stem
    parts = [p for p in re.split(r"[_\- ]+", stem) if p]
    filtered = [p for p in parts if not re.match(r"^(20\d{2}|w2|w-2|1098|1099|nec|div|int|b)$", p.lower())]
    return filtered[0] if filtered else ""


def infer_document_type(path_text: str) -> tuple[str, float, str]:
    low = path_text.lower()
    for doc_type, keywords in DOC_TYPE_RULES.items():
        hits = [keyword for keyword in keywords if keyword in low]
        if hits:
            return doc_type, round(min(0.6 + 0.1 * len(hits), 0.95), 2), f"keyword match: {', '.join(hits)}"
    return "unknown", 0.35, "no known keyword match"


def _normalize_text(value: str) -> str:
    return re.sub(r"[_-]+", " ", value.lower())


def build_inventory(input_folder: Path) -> list[InventoryItem]:
    files = [path for path in input_folder.rglob("*") if path.is_file()]
    seen_names = Counter(path.name.lower() for path in files)

    inventory: list[InventoryItem] = []
    for item_path in files:
        rel_path = str(item_path.relative_to(input_folder)).replace("\\", "/")
        doc_type, confidence, evidence = infer_document_type(rel_path)
        inventory.append(
            InventoryItem(
                original_file_path=str(item_path.resolve()),
                filename=item_path.name,
                parent_folder=item_path.parent.name,
                inferred_document_type=doc_type,
                inferred_tax_year=infer_year(rel_path),
                inferred_entity_name=infer_entity_name(item_path.name),
                confidence=confidence,
                evidence=evidence,
                duplicate_flag=seen_names[item_path.name.lower()] > 1,
            )
        )
    return inventory


def detect_modules(inventory: list[InventoryItem], modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searchable_lines = [_normalize_text(f"{i.filename} {i.parent_folder} {i.inferred_document_type}") for i in inventory]
    detected: list[dict[str, Any]] = []

    for module in modules:
        matches: list[dict[str, str]] = []
        for idx, line in enumerate(searchable_lines):
            trigger_hits = [str(trigger) for trigger in module.get("trigger_docs", []) if _normalize_text(str(trigger)) in line]
            if trigger_hits:
                matches.append({"file": inventory[idx].filename, "evidence": ", ".join(trigger_hits)})

        if matches:
            confidence = round(min(0.5 + 0.1 * len(matches), 0.95), 2)
            detected.append(
                {
                    "module_id": module["module_id"],
                    "display_name": module["display_name"],
                    "confidence": confidence,
                    "triggering_documents": matches,
                    "evidence": f"Likely {module['display_name']} activity detected based on trigger documents.",
                    "notes": "Conservative inference for preparer review.",
                }
            )
    return detected


def generate_missing_items(detected_modules: list[dict[str, Any]], modules: list[dict[str, Any]], inventory: list[InventoryItem]) -> list[dict[str, Any]]:
    inventory_blob = " ".join(_normalize_text(f"{i.filename} {i.parent_folder} {i.inferred_document_type}") for i in inventory)
    module_by_id = {m["module_id"]: m for m in modules}
    results: list[dict[str, Any]] = []

    for detected in detected_modules:
        module = module_by_id[detected["module_id"]]
        weak_signal = detected["confidence"] < 0.7
        question = (module.get("client_questions") or [""])[0]

        for item in module.get("expected_critical_docs", []):
            found = _normalize_text(item) in inventory_blob
            results.append(
                {
                    "module": module["display_name"],
                    "item": item,
                    "status": "Found" if found else ("Needs Review" if weak_signal else "Missing"),
                    "reason": "Matched in inventory" if found else "Expected from detected module triggers",
                    "evidence": detected["evidence"],
                    "confidence": detected["confidence"],
                    "suggested_client_question": question,
                }
            )

        for item in module.get("review_needed_docs", []):
            found = _normalize_text(item) in inventory_blob
            results.append(
                {
                    "module": module["display_name"],
                    "item": item,
                    "status": "Found" if found else "Needs Review",
                    "reason": "Review-needed checklist item",
                    "evidence": f"Checklist driven review for {module['display_name']}",
                    "confidence": round(max(detected["confidence"] - 0.1, 0.4), 2),
                    "suggested_client_question": question,
                }
            )
    return results


def _write_minimal_xlsx(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0].keys()) if rows else []

    def cell(value: Any) -> str:
        safe = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<c t="inlineStr"><is><t>{safe}</t></is></c>'

    sheet_rows = ["<row r=\"1\">" + "".join(cell(h) for h in headers) + "</row>"]
    for row_num, row in enumerate(rows, start=2):
        sheet_rows.append(f"<row r=\"{row_num}\">" + "".join(cell(row[h]) for h in headers) + "</row>")

    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>")
        zf.writestr("_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>")
        zf.writestr("xl/workbook.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"Inventory\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>")
        zf.writestr("xl/_rels/workbook.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>")
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def write_outputs(output_dir: Path, inventory: list[InventoryItem], detected: list[dict[str, Any]], missing: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_records = [asdict(item) for item in inventory]

    (output_dir / "inventory.json").write_text(json.dumps(inventory_records, indent=2), encoding="utf-8")
    _write_minimal_xlsx(output_dir / "inventory.xlsx", inventory_records)

    grouped_questions: dict[str, list[str]] = defaultdict(list)
    for row in missing:
        if row["status"] in {"Missing", "Needs Review"} and row["suggested_client_question"]:
            grouped_questions[row["module"]].append(row["suggested_client_question"])

    lines = ["Additional Items / Questions Needed", ""]
    for module_name, questions in grouped_questions.items():
        lines.append(module_name)
        for index, question in enumerate(dict.fromkeys(questions), start=1):
            lines.append(f"{index}. {question}")
        lines.append("")
    (output_dir / "client_follow_up_questions.txt").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    notes_lines = ["Tax Packet QA - Preparer Notes", "", "Detected Modules:"]
    for module in detected:
        notes_lines.append(f"- {module['display_name']} (confidence {module['confidence']}): {module['evidence']}")
    notes_lines.append("\nMissing/Review Items:")
    for row in missing:
        if row["status"] != "Found":
            notes_lines.append(f"- [{row['status']}] {row['module']}: {row['item']} | reason: {row['reason']} | confidence: {row['confidence']}")
    notes_lines.append("\nNotes: This output is a preparer-assist review aid and does not finalize tax positions.")
    (output_dir / "preparer_notes.txt").write_text("\n".join(notes_lines) + "\n", encoding="utf-8")


def _render_html_table(headers: list[str], rows: list[list[str]], header_bg: str) -> str:
    thead = "".join(f"<th>{h}</th>" for h in headers)
    tbody = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead style='background:{header_bg};color:#fff'><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def render_reports(output_dir: Path, inventory: list[InventoryItem], detected: list[dict[str, Any]], missing: list[dict[str, Any]], client_name: str) -> None:
    ts = datetime.now(UTC).isoformat()
    type_counts = Counter(item.inferred_document_type for item in inventory)

    inv_rows = [[i.filename, i.parent_folder, i.inferred_document_type, i.inferred_tax_year, i.inferred_entity_name, str(i.confidence), i.evidence, str(i.duplicate_flag)] for i in inventory]
    inv_table = _render_html_table(["Filename", "Parent Folder", "Type", "Year", "Entity", "Confidence", "Evidence", "Duplicate"], inv_rows, SATC_THEME["navy_soft"])

    inventory_html = f"""<html><body style='font-family:Arial;background:{SATC_THEME['paper']};color:{SATC_THEME['ink']};margin:24px'>
    <h1 style='color:{SATC_THEME['navy']}'>Tax Packet QA - Inventory Report</h1>
    <p><b>Client/Folder:</b> {client_name}<br><b>Run Timestamp:</b> {ts}<br><b>File Count:</b> {len(inventory)}</p>
    <h3>Document Type Counts</h3><ul>{''.join(f'<li>{k}: {v}</li>' for k,v in type_counts.items())}</ul>{inv_table}</body></html>"""
    (output_dir / "inventory_report.html").write_text(inventory_html, encoding="utf-8")

    missing_rows = [[r["module"], r["item"], r["status"], r["reason"], r["evidence"], str(r["confidence"])] for r in missing if r["status"] != "Found"]
    missing_table = _render_html_table(["Module", "Item", "Status", "Reason", "Evidence", "Confidence"], missing_rows, SATC_THEME["navy_deep"])
    detected_list = "".join(f"<li>{d['display_name']} ({d['confidence']}): {d['evidence']}</li>" for d in detected)

    missing_html = f"""<html><body style='font-family:Arial;background:{SATC_THEME['paper']};color:{SATC_THEME['ink']};margin:24px'>
    <h1 style='color:{SATC_THEME['navy']}'>Tax Packet QA - Missing/Review Items</h1>
    <p><b>Client/Folder:</b> {client_name}<br><b>Run Timestamp:</b> {ts}</p>
    <h3>Detected Modules</h3><ul>{detected_list}</ul>{missing_table}</body></html>"""
    (output_dir / "missing_items_report.html").write_text(missing_html, encoding="utf-8")


def run(input_folder: Path, config_path: Path, output_dir: Path, metadata_path: Path | None = None) -> None:
    config = load_config(config_path)
    metadata = load_config(metadata_path) if metadata_path else {}

    inventory = build_inventory(input_folder)
    modules = config.get("modules", [])
    detected = detect_modules(inventory, modules)
    missing = generate_missing_items(detected, modules, inventory)

    write_outputs(output_dir, inventory, detected, missing)
    render_reports(output_dir, inventory, detected, missing, metadata.get("client_name", input_folder.name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Tax Packet QA v0.1")
    parser.add_argument("input_folder")
    parser.add_argument("--client-metadata", default=None)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config" / "tax_modules.json"))
    parser.add_argument("--output", default=str(Path(__file__).parent / "outputs" / "run_output"))
    args = parser.parse_args()

    run(Path(args.input_folder), Path(args.config), Path(args.output), Path(args.client_metadata) if args.client_metadata else None)


if __name__ == "__main__":
    main()
