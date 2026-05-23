# Tax Packet QA v0.1

Tax Packet QA is a **local-first, rule-based Python QA layer** that runs on top of an already-sorted client tax document folder.

It is intentionally separate from the sorter and does **not** replace or modify sorter behavior.

## Outputs
Given a sorted client folder, Tax Packet QA writes:
- `inventory.json`
- `inventory.xlsx`
- `inventory_report.html`
- `missing_items_report.html`
- `client_follow_up_questions.txt`
- `preparer_notes.txt`

## What it does
- Builds an inventory from sorted folders and filenames (recursive scan).
- Infers document type, possible tax year, and entity hints from filenames/folders.
- Detects likely tax situations/modules from config-driven triggers.
- Flags checklist items as `Found`, `Needs Review`, or `Missing` conservatively.
- Generates concise client follow-up questions and preparer-facing notes.
- Writes all artifacts to a separate output folder for auditability.

## What it does not do
- No AI and no cloud APIs.
- No paid OCR.
- No Drake Tax integration.
- No tax advice or automatic tax-position conclusions.
- No file deletion, moving, or source document modification.

> Tax Packet QA is a preparer-assist tool. It does not provide tax advice and does not finalize tax positions.

## Run
```bash
python tax_packet_qa.py "path/to/sorted/client/folder"
python tax_packet_qa.py "path/to/sorted/client/folder" --client-metadata client.json --config config/tax_modules.json --output outputs/client_name
```

## Sample run
```bash
python tax_packet_qa.py sample_client/sorted_documents --output outputs/sample_client
```

## Tests
```bash
pytest -q
```
