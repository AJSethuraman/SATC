# FileReviewScanner

FileReviewScanner is a **read-only** Python desktop utility for backup-cleanup review projects (including mounted QNAP/NAS shares). It inventories files, finds exact duplicates (optional), and exports a client-friendly Excel workbook.

## Safety and scope
- Reads metadata and (optionally) file contents for hashing.
- Writes only the chosen `.xlsx` report.
- Does **not** delete, move, rename, or modify scanned files.

## Progress indicators for large scans
The GUI is optimized for long QNAP/network-share scans:
- Heartbeat progress updates every ~1-2 seconds.
- Current phase: `Metadata Scan`, `Hashing`, `Export`, `Complete`.
- Visible counters:
  - files discovered
  - files included after filtering
  - files hashed
  - duplicate groups
  - errors
- Elapsed time display.
- Most recent path processed (truncated for readability).
- Indeterminate progress bar while work is ongoing.

## Cancel behavior and partial reports
- `Cancel Scan` requests graceful cancellation.
- Scanner checks cancellation during metadata traversal, hashing, and before export.
- If practical, a **partial report** is still exported.
- `Summary` sheet includes:
  - `Scan Status` (`Completed` / `Cancelled`)
  - cancellation detail note when cancelled.

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
Output: `dist\FileReviewScanner.exe`

## QNAP / network share scan workflow
1. Start with a small local test folder.
2. Test a small QNAP subfolder first.
3. Validate output workbook.
4. Run broader scans after confidence is established.

Accepted scan roots include local paths, mapped drives (e.g. `Z:\Backups`) and UNC paths (`\\QNAP-NAME\Backups`).

## Duplicate detection
When enabled:
1. Scan metadata first.
2. Group by file size.
3. Hash only groups with at least 2 files.
4. Confirm duplicates by exact SHA-256 hash match.

## File type filtering
Modes:
- scan all
- include only selected extensions
- exclude selected extensions

Extension input accepts comma/semicolon/space separators and optional leading dot.

## Workbook sheets
- `Review`
- `Duplicate Groups`
- `Summary`
- `Errors`

## Troubleshooting
- Permission denied: check access rights on share.
- Path unavailable: verify mapped/UNC path availability.
- Workbook open: close Excel report before overwrite.
- Slow network scans: scope smaller batches and run off-hours.
- Antivirus slowdown: AV may add overhead during hash reads.

## Demo and tests
```bash
python create_demo_data.py
pytest -q
```
