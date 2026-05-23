# Tax Packet QA v0.1

Tax Packet QA is a **local-first, rule-based Python QA layer** that runs on top of an already-sorted client tax document folder.

## Positioning
- It is a separate layer from the sorter.
- It expects an already-sorted folder as input.
- It does not move, delete, or modify source files.

## YAML checklist config
Business logic is driven by `config/tax_modules.yaml`.
- Module triggers are configured in YAML.
- Checklist items support aliases and conditions.
- To tune behavior, edit aliases/labels/conditions in YAML.

## Outputs
- `inventory.json`
- `inventory.xlsx` (Inventory, Detected Modules, Missing and Review Items sheets)
- `inventory_report.html`
- `missing_items_report.html`
- `client_follow_up_questions.txt`
- `preparer_notes.txt`

## Run
```bash
python tax_packet_qa.py "path/to/sorted/client/folder"
python tax_packet_qa.py "path/to/sorted/client/folder" --client-metadata client.json --config config/tax_modules.yaml --output outputs/client_name
```

## Sample run
```bash
python tax_packet_qa.py sample_client/sorted_documents --output outputs/sample_client
```

## Tests
```bash
pytest -q
```

> Tax Packet QA is a preparer-assist QA tool. It does not provide tax advice and does not finalize tax positions.
