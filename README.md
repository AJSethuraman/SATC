# Local Tax Document Sorter Prototype

This repository contains a simple, local-only Python prototype for sorting obvious tax documents from a client upload folder. It uses rule-based keyword matching, PDF text extraction, and Tesseract OCR. It does **not** use AI, machine learning, paid APIs, or cloud services.

## What it does

Run `sort_tax_docs.py` against a folder of uploads and it will:

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
   - `99_Needs_Review`
3. Process common file types: PDF, JPG, JPEG, PNG, TIFF, and TIF.
4. Try selectable PDF text first, then OCR scanned PDFs when little or no text is found.
5. OCR image files using local Tesseract via `pytesseract`.
6. Copy files by default into the best matching category folder.
7. Rename files with the detected type prefix, such as `W2_scan001.pdf` or `NeedsReview_IMG_2231.jpg`.
8. Avoid overwriting existing files by appending `_2`, `_3`, and so on.
9. Create `Document_Inventory.xlsx` and `processing_log.txt` in the output folder.

## Important safety notes

- The default behavior is to **copy**, not move.
- Use `--move` only when you intentionally want to move files from the upload folder.
- The script never deletes original files separately.
- If a file fails, the error is logged and the script continues with the remaining files.
- This is a prototype and should not replace human review. Anything uncertain goes to `99_Needs_Review`.

## Classification rules

The sorter uses simple keyword matching only:

| Category | Keywords |
| --- | --- |
| W2 | `Form W-2`, `Wage and Tax Statement` |
| 1099_NEC | `1099-NEC`, `Nonemployee Compensation` |
| 1099_MISC | `1099-MISC` |
| 1099_INT_DIV | `1099-INT`, `1099-DIV` |
| 1099_R | `1099-R`, `Distributions From Pensions` |
| 1098_Mortgage | `Mortgage Interest Statement`, `Form 1098` |
| 1095_A | `1095-A`, `Health Insurance Marketplace Statement` |
| K1 | `Schedule K-1` |
| Brokerage_1099B | `Consolidated 1099`, `1099-B`, `Proceeds From Broker`, `Cost Basis` |
| ID | `Driver License`, `Driver's License`, `State ID`, `Identification Card` |
| NeedsReview | No supported keyword found |

Exact form keywords are marked `High` confidence. Supporting descriptive phrases are marked `Medium` confidence. `NeedsReview` is marked `Low` confidence.

## Easy setup

Python 3.10 or newer is recommended. The easiest path is to create a virtual environment, then run the setup helper. It installs the Python packages from `requirements.txt` and tries to install the Tesseract OCR application with a common package manager when one is available.

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# On Windows PowerShell: .venv\Scripts\Activate.ps1
python sort_tax_docs.py --install-dependencies
python sort_tax_docs.py --check-dependencies
```

You can also run `python setup_tax_doc_sorter.py` directly. The setup helper is best-effort for system software:

- Windows: tries `winget install --id UB-Mannheim.TesseractOCR -e` when `winget` is available.
- macOS: tries `brew install tesseract` when Homebrew is available.
- Linux: tries a supported package manager such as `apt-get`, `dnf`, `yum`, or `pacman`.

If you only want the Python packages and prefer to install Tesseract yourself, run:

```bash
python sort_tax_docs.py --install-dependencies --skip-system-install
```

## Manual setup fallback

If automatic setup cannot install Tesseract, install it manually and make sure the `tesseract` command is on your `PATH`. `pytesseract` is only a Python wrapper; the Tesseract OCR application must also be installed.

### Windows

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

If needed, add the install folder to your Windows `PATH`. It is commonly:
`C:\Program Files\Tesseract-OCR\`

### macOS

```bash
brew install tesseract
```

### Ubuntu/Debian Linux

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

## Manual Python-only install

If you do not want to use the setup helper, install the Python packages directly:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python sort_tax_docs.py --check-dependencies
```

## Usage

Copy mode is the default and safest option:

```bash
python sort_tax_docs.py "C:\Tax Clients\John Smith\Uploads"
```

On macOS/Linux:

```bash
python sort_tax_docs.py "/home/user/Tax Clients/John Smith/Uploads"
```

To move files instead of copying them:

```bash
python sort_tax_docs.py "C:\Tax Clients\John Smith\Uploads" --move
```

## Test on a sample folder

1. Create a sample upload folder.
2. Add a few PDFs or images containing clear tax-form text, such as `Form W-2`, `1099-NEC`, or `Mortgage Interest Statement`.
3. Run:

```bash
python sort_tax_docs.py "/path/to/sample_uploads"
```

4. Review:
   - `/path/to/sample_uploads/Organized_Tax_Documents/`
   - `/path/to/sample_uploads/Organized_Tax_Documents/Document_Inventory.xlsx`
   - `/path/to/sample_uploads/Organized_Tax_Documents/processing_log.txt`

## Limitations in this first version

- It does not split combined PDFs.
- It does not extract dollar amounts or taxpayer details.
- It does not connect to Drake Tax or any other tax software.
- It does not use APIs, paid services, AI, or machine learning.
- OCR quality depends on scan quality and the local Tesseract installation.
