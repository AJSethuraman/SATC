# Local Tax Document Sorter Prototype

This is a simple, local-only Python prototype for sorting obvious tax documents from a client upload folder. It uses rule-based keyword matching, PDF text extraction, and local Tesseract OCR. It does **not** use AI, machine learning, paid APIs, cloud services, Drake Tax integration, a database, a web app, or a desktop GUI.

## Easiest way to use it

### First-time setup

From this project folder, run:

```bash
python setup_tax_doc_sorter.py
```

The setup helper installs Python packages from `requirements.txt`, tries to install the Tesseract OCR application when a common package manager is available, then runs the same dependency check used by the sorter.

### Normal use

1. Put client files in the `Uploads` folder next to these scripts. If the folder does not exist yet, `run_sorter.py` creates it for you.
2. Run:

```bash
python run_sorter.py
```

3. When asked, press Enter to use the default `Uploads` folder, or type/paste a custom folder path.
4. Review:

```text
Uploads/Organized_Tax_Documents/
```

The launcher runs the sorter in safe copy mode by default, so original files are not moved or deleted.

## What it does

Run the sorter against a folder of uploads and it will:

1. Create an `Organized_Tax_Documents` folder inside the input folder.
2. Create these category folders:
   - `01_W2`
   - `02_1099_NEC`
   - `03_1099_MISC`
   - `04_1099_INT_DIV`
   - `05_1099_R`
   - `06_1098_Mortgage`
   - `07_1095_A`
   - `08_K1`
   - `09_Brokerage_1099B`
   - `10_ID`
   - `11_1098_Tuition`
   - `99_Needs_Review`
3. Process common file types: PDF, JPG, JPEG, PNG, TIFF, and TIF.
4. Try selectable PDF text first; if it does not produce a high-confidence classification, OCR the PDF and classify combined selectable + OCR text.
5. OCR image files using local Tesseract through `pytesseract`, with simple Pillow grayscale/contrast/sharpening preprocessing.
6. Copy files by default into the best matching category folder.
7. Rename files with the detected type prefix, such as `W2_scan001.pdf`, `1099_NEC_upload4.pdf`, or `NeedsReview_IMG_2231.jpg`.
8. Avoid overwriting existing files by appending `_2`, `_3`, and so on.
9. Create `Document_Inventory.xlsx` and `processing_log.txt` in the output folder.
10. Add scoring details and manual-review notes when classification is weak or multiple document categories are possible.

## Important safety notes

- The default behavior is to **copy**, not move.
- Use `--move` only when you intentionally want to move files from the upload folder.
- The script never deletes original files separately.
- If a file fails, the error is logged and the script continues with the remaining files.
- This is a prototype and should not replace human review. Anything uncertain goes to `99_Needs_Review`.
- Combined PDFs are not split yet. If multiple document types appear to match one file, the inventory flags it for manual review.

## Classification rules

The sorter uses conservative rule-based scoring only. Strong official identifiers carry the most weight, generic tax words do not classify a document by themselves, and uncertain files go to `NeedsReview`.

| Category | Keywords |
| --- | --- |
| W2 | `Form W-2`, `Wage and Tax Statement`, or at least 4 W-2 box/field indicators such as `Employee's social security number`, `Employer identification number`, `Wages, tips, other compensation`, and `Federal income tax withheld` |
| 1099_NEC | `1099-NEC`, `Nonemployee Compensation` |
| 1099_MISC | `1099-MISC` |
| Brokerage_1099B | `Consolidated 1099`, `1099-B`, `Proceeds From Broker`, `Cost Basis` |
| 1099_INT_DIV | `1099-INT`, `1099-DIV` |
| 1099_R | `1099-R`, `Distributions From Pensions` |
| 1098_Mortgage | `Form 1098 Mortgage Interest Statement`, `Mortgage Interest Statement`, `Mortgage Interest` |
| 1098_Tuition | `1098-T`, `Tuition Statement` |
| 1095_A | `1095-A`, `Health Insurance Marketplace Statement` |
| K1 | `Schedule K-1` |
| ID | `Driver License`, `Driver's License`, `State ID`, `Identification Card` |
| NeedsReview | No supported keyword found |

Brokerage scoring is designed to beat 1099-INT/DIV when consolidated brokerage evidence is present. W-2 requires `Form W-2`, `Wage and Tax Statement`, or a cluster of at least 4 W-2 structural field labels; generic words such as `wages`, `withholding`, `employer`, or `employee` are not enough. 1099-MISC requires `1099-MISC`; mortgage classification does **not** rely on generic `Form 1098`, `lender`, or `interest` alone.

## Detailed setup notes

Python 3.10 or newer is recommended. A virtual environment is optional but recommended.

### macOS/Linux virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
python setup_tax_doc_sorter.py
```

### Windows PowerShell virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python setup_tax_doc_sorter.py
```

The setup helper is best-effort for system software:

- Windows: tries `winget install --id UB-Mannheim.TesseractOCR -e` when `winget` is available.
- macOS: tries `brew install tesseract` when Homebrew is available.
- Linux: tries a supported package manager such as `apt-get`, `dnf`, `yum`, or `pacman`.

Check dependency status at any time:

```bash
python sort_tax_docs.py --check-dependencies
```

If you only want the Python packages and prefer to install Tesseract yourself, run:

```bash
python sort_tax_docs.py --install-dependencies --skip-system-install
```

## Manual Tesseract fallback

If automatic setup cannot install Tesseract, install it manually. The sorter checks both `PATH` and these common Windows install locations:

- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`

### Windows

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

If needed, install to `C:\Program Files\Tesseract-OCR\` and reopen your terminal.

### macOS

```bash
brew install tesseract
```

### Ubuntu/Debian Linux

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

## Manual command-line usage

The launcher is easiest, but you can also run the sorter directly.

Copy mode is the default and safest option:

```bash
python sort_tax_docs.py "C:\Tax Clients\John Smith\Uploads"
```

On macOS/Linux:

```bash
python sort_tax_docs.py "/home/user/Tax Clients/John Smith/Uploads"
```

To save extracted selectable/OCR/combined text and classification scores for troubleshooting:

```bash
py -3.12 .\sort_tax_docs.py "C:\Tax Clients\John Smith\Uploads" --save-extracted-text
```

Debug text files are written to `Organized_Tax_Documents/_extracted_text_debug/`.

To move files instead of copying them:

```bash
python sort_tax_docs.py "C:\Tax Clients\John Smith\Uploads" --move
```

## Run fake classifier tests

Run the included fake-text classifier tests with:

```bash
python test_sort_tax_docs.py
```

These tests do not use real taxpayer data. They cover exact W-2 text, W-2 structural indicators, PDF OCR fallback behavior, 1099-NEC vs W-2, brokerage priority, 1099-MISC strictness, 1098-T, mortgage 1098, generic tax statements, and random receipts.

## Simple fake manual test with no real client data

After setup, create a few harmless test PDFs or images that contain only fake text, such as:

- `Form W-2 Wage and Tax Statement`
- `Employee's social security number Employer identification number Wages, tips, other compensation Federal income tax withheld`
- `1099-NEC Nonemployee Compensation`
- `Consolidated 1099 1099-B Proceeds From Broker`
- `1098-T Tuition Statement`
- `Mortgage Interest Statement`

Put those files in the `Uploads` folder, run `python run_sorter.py`, press Enter, and review `Uploads/Organized_Tax_Documents/`, `Document_Inventory.xlsx`, and `processing_log.txt`. The inventory includes winning score, runner-up score, matched keywords, category scores, OCR status, and notes.

## Limitations in this prototype

- It does not split combined PDFs.
- It does not extract dollar amounts or taxpayer details.
- It does not connect to Drake Tax or any other tax software.
- It does not use APIs, paid services, AI, or machine learning.
- OCR quality depends on scan quality and the local Tesseract installation.
- Rule-based sorting is intentionally conservative; uncertain documents should be reviewed manually.
