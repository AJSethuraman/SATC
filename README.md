# FileReviewScanner

FileReviewScanner is a **read-only** Python desktop utility for backup-cleanup review projects (including mounted QNAP/NAS shares). It inventories files, finds exact duplicates (optional), and exports a client-friendly Excel workbook.

## What it does
- Recursively scans a selected folder.
- Collects file metadata (size, timestamps, category, path context, etc.).
- Supports file type filtering: all / include / exclude extension list.
- Optionally detects exact duplicates by size + SHA-256 hash.
- Exports a single Excel workbook with these sheets:
  - `Review`
  - `Duplicate Groups`
  - `Summary`
  - `Errors`

## What it does NOT do
- Does **not** delete files.
- Does **not** move files.
- Does **not** rename files.
- Does **not** modify file contents or permissions.

It only reads files and writes the output workbook at your selected path.

## Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Build Windows executable
```bat
build_windows.bat
```
This runs PyInstaller and creates:
- `dist\FileReviewScanner.exe`

## QNAP / network share scanning
You can scan:
- mapped drives (example `Z:\Backups`)
- UNC paths (example `\\QNAP-NAME\Backups`)

## Recommended workflow
1. Start with a small local test folder.
2. Test a small QNAP subfolder.
3. Run broader scans after output validation.

## Exact duplicate detection
When enabled:
1. Metadata is scanned first.
2. Files are grouped by size.
3. Only size groups with 2+ files are hashed.
4. Exact duplicates require same size and same SHA-256 hash.

## File type filtering
- `Scan all file types`
- `Include only selected extensions`
- `Exclude selected extensions`

Input accepts comma/semicolon/space separators and optional leading dots. Example:
- `.xlsx, xlsm; pdf txt`

## Workbook overview
- **Review**: one row per file with recommendation and client decision dropdown.
- **Duplicate Groups**: one row per confirmed duplicate hash group with potential recoverable size.
- **Summary**: scan metadata and category totals.
- **Errors**: non-fatal file-level errors (metadata/hash/export).

## Troubleshooting
- **Permission denied**: run with sufficient access and confirm share permissions.
- **Network path unavailable**: verify mapped drive or UNC availability.
- **Excel file already open**: close workbook and run again.
- **Slow scans on large shares**: narrow scope and run in batches.
- **Antivirus slow hashing**: AV may add IO overhead during hashing.

## Demo data + tests
Generate demo data:
```bash
python create_demo_data.py
```

Run automated tests:
```bash
pytest -q
```

Tests validate duplicate grouping, filters, workbook creation, and required sheet presence.
