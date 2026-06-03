# Local Tax Tools Prototype

This is a local-only Python prototype that bundles small tax tools you can run individually or in sequence from one PySide6 desktop app. It uses rule-based keyword scoring, PDF text extraction, and local Tesseract OCR. It does **not** use AI, machine learning, paid APIs, cloud services, Drake Tax integration, a database, PDF splitting, or bookkeeping categories.

## Tools in the suite

Pick one or more tools in the desktop app (they run top to bottom):

1. **Sort Documents** — classify uploads and copy (or move) them into category folders with an inventory workbook. When a single PDF contains more than one form type, it is **split** into one filed PDF per form (see below).
2. **Extract Form Data** — read key fields from **W-2**, **1099-NEC**, **1099-INT/DIV**, **1099-R**, **1099-G**, **1099-K**, **SSA-1099**, **1098 (Mortgage)**, **1098-T**, **1099-B**, and **Schedule K-1**. Output is written two ways: a human-readable `Extracted_Form_Data.xlsx` (one sheet per form type) and machine-readable per-form CSVs in `Drake_Export/` for feeding a downstream entry script.
3. **Generate Documents** — fill editable templates (engagement letter, invoice, extension/cover letter, client organizer letter) from a `clients.json`/`clients.csv` data file and write finished HTML to `Generated_Documents/`.
4. **Sign Documents** — stamp your signature image onto PDFs that carry a signature anchor phrase, writing signed copies to `Signed_Documents/`.
5. **Compose Email Drafts** — build a review-ready `.eml` per client (subject/body from a template, that client's generated and signed files attached) in `Email_Drafts/`. Nothing is sent automatically and no credentials are stored.
6. **Export for Encyro** — convert each client's letters to PDF, gather their signed PDFs/attachments, and merge an upload-ready `<client>_packet.pdf` (plus `UPLOAD_NOTES.txt`) under `Encyro_Ready/<client>/`.

Extraction is local and rule-based: it uses label-anchored regular expressions over the same selectable-text/OCR pipeline as the sorter. It is **assistive only** — every value should be verified against the source document, and anything the rules cannot read confidently is left blank with the row flagged for manual entry. 1099-B is transactional and is always flagged for manual review.

### Feeding a Drake (or other) entry script

The extractor writes `Organized_Tax_Documents/Drake_Export/<FORM_TYPE>.csv` (for example `W2.csv`, `1099_NEC.csv`) using **stable machine field keys** and **typed values**, designed to be read by a downstream Python entry script:

- Every CSV starts with metadata columns: `form_type`, `source_file`, `page` (blank for single-form files; the page number for a form pulled from a combined PDF), `needs_review`, and ends with `notes`.
- Between them are the form's fields using snake_case keys such as `employer_ein`, `box1_wages`, `box1_nonemployee_compensation`, `box1_gross_distribution`, `box7_distribution_code`.
- Dollar amounts are written as plain numbers (`52000.0`), so `pandas`/`csv` parse them as floats. Identifiers like EIN/SSN keep their hyphens as strings (`12-3456789`). Missing values are blank.

The keys are intentionally **generic**; map them to your Drake input fields inside your entry script. Example consumer:

```python
import csv
from pathlib import Path

export = Path("Uploads/Organized_Tax_Documents/Drake_Export")
for row in csv.DictReader((export / "W2.csv").open()):
    if row["needs_review"] == "True":
        continue  # send to manual entry instead
    wages = float(row["box1_wages"]) if row["box1_wages"] else 0.0
    # map row["employer_ein"], wages, ... onto your Drake fields here
```

### Splitting combined PDFs

When "Split combined PDFs" is on (the default), the sorter classifies each page of a PDF, groups consecutive pages into forms, and writes one filed PDF per form (for example `W2_clientupload_p1.pdf` and `1099_R_clientupload_p2-3.pdf`). Instruction/continuation pages stay attached to the form they follow, and pages of the same form type are kept together. Splitting always **copies** segments and leaves the original PDF untouched, even in move mode, so nothing is lost. The Extract Form Data tool also reads PDFs page by page, so a combined upload yields one extracted row per form. Turn this off with the desktop "Split combined PDFs" checkbox or the `--no-split` CLI flag.

## Easiest way to use it on Windows

### First-time setup

1. Double-click `Setup Tax Document Sorter.bat`.
2. Wait for setup to finish.
3. If prompted, install Tesseract OCR.

The setup helper installs Python packages from `requirements.txt`, tries to install the Tesseract OCR application when a common package manager is available, then runs the same dependency check used by the sorter.

### Normal use

1. Double-click `Start Tax Document Sorter.vbs`.
2. The desktop app opens without a Command Prompt window.
3. Click **Choose Folder**.
4. Select the client upload folder, or use the default `Uploads` folder.
5. Click **Run Sorter**.
6. Review results in the app.
7. Click **Open Organized Folder** or **Open Inventory**.

The desktop app uses safe copy mode by default, so original files are not moved or deleted.

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
   - `12_1099_G`
   - `13_1099_K`
   - `14_SSA_1099`
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
- Combined PDFs that contain multiple form types are split into one filed PDF per form. Splitting always copies and never deletes the original. Two of the same form type on consecutive pages are kept together, so verify split output when several of one form are combined.

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
| 1099_G | `Form 1099-G`, `1099-G`, `Certain Government Payments` (`Unemployment Compensation` alone is not enough) |
| 1099_K | `Form 1099-K`, `1099-K`, `Payment Card and Third Party Network Transactions` |
| SSA_1099 | `Form SSA-1099`, `SSA-1099`, `Social Security Benefit Statement` |
| NeedsReview | No supported keyword found |

Brokerage scoring is designed to beat 1099-INT/DIV when consolidated brokerage evidence is present. W-2 requires `Form W-2`, `Wage and Tax Statement`, or a cluster of at least 4 W-2 structural field labels; generic words such as `wages`, `withholding`, `employer`, or `employee` are not enough. 1099-MISC requires `1099-MISC`; mortgage classification does **not** rely on generic `Form 1098`, `lender`, or `interest` alone.

## PowerShell and CLI fallback

If the double-click launcher is not available, use these commands from the project folder:

```powershell
py -3.12 setup_tax_doc_sorter.py
py -3.12 tax_doc_sorter_app.pyw
py -3.12 run_sorter.py
py -3.12 sort_tax_docs.py --check-dependencies
```

### Run tools from the command line

`tax_tools.py` runs any combination of tools on a folder, in order:

```bash
python tax_tools.py "/path/to/Uploads"                  # runs sort, extract, generate
python tax_tools.py "/path/to/Uploads" --tools sort     # just the sorter
python tax_tools.py "/path/to/Uploads" --tools extract  # just the extractor
python tax_tools.py "/path/to/Uploads" --tools generate # just document generation
python tax_tools.py "/path/to/Uploads" --tools sign --signature sig.png
python tax_tools.py "/path/to/Uploads" --tools email    # compose .eml drafts
python extract_form_data.py "/path/to/Uploads"          # extractor directly
python generate_documents.py "/path/to/Uploads"         # generator directly
python sign_documents.py "/path/to/Uploads" --signature sig.png
python compose_emails.py "/path/to/Uploads"             # email drafts directly
python tax_tools.py "/path/to/Uploads" --tools encyro   # build Encyro packets
python export_encyro.py "/path/to/Uploads"              # Encyro export directly
```

The CLI workflows remain available for troubleshooting and automation. The older Flask browser app (`app.py`) is still present as optional legacy tooling, but the primary workflow is the PySide6 desktop app.

### Generating client documents

The **Generate Documents** tool fills templates from a client data file in the input folder and writes one HTML file per client per template to `Organized_Tax_Documents/Generated_Documents/`. Open the HTML in any browser and print or save it as PDF.

1. Put a `clients.json` (or `clients.csv`) in the folder. JSON supports nested lists like invoice `line_items` and organizer `requested_items`; CSV is fine for the letters and simple fields. A worked example ships at `document_templates/clients.sample.json` — copy it to your folder as `clients.json` and edit.
2. The templates live in `document_templates/`. To use your own without touching the repo, drop a `document_templates/` folder inside your input folder and it is used instead.
3. Run the tool. Each client record produces `<ClientName>_<template>`. Fields that a template references but the data does not provide are left blank and reported as a warning, so nothing fails silently.

#### Adding a template is just dropping a file in the folder

The folder *is* the list of templates — there is no list to edit in code. Any file in `document_templates/` becomes a template, keyed by its file name. Two kinds are supported:

- **HTML** (`*.html`) — use `{{ field }}` for values and `{{#line_items}}…{{/line_items}}` for repeating rows. The four shipped letters are HTML. Output is `.html` (open in a browser, print to PDF).
- **Word** (`*.docx`) — author the document in Microsoft Word exactly how you want it to look, typing `{{ client_name }}`, `{{ tax_year }}`, etc. where values go (and `{% for item in line_items %}…{% endfor %}` in a table row for lists). Output is a filled `.docx`. This uses `docxtpl`, which is included in `requirements.txt`.

So to add, say, a privacy-policy letter: write it in Word, drop `privacy_policy.docx` into `document_templates/`, and it appears automatically — in the desktop **Advanced Options** template list and on the CLI as `--templates privacy_policy`. The placeholder names are just the keys in your `clients.json`/`clients.csv`, so any field you put in the data is available to any template.

In the desktop app, expand **Advanced Options** to choose which templates to generate (the list refreshes from the selected folder), set the signature image path and anchor for the Sign tool, and toggle move/split/debug.

Templates use a tiny Mustache-style syntax:

- `{{field}}` inserts a value from the client record (HTML-escaped). Single braces such as CSS rules are left alone.
- `{{#line_items}} ... {{/line_items}}` repeats the block once per item in a list; inside it, `{{description}}`/`{{amount}}` refer to each item's fields.
- The invoice `total` is computed automatically from the line-item amounts when not supplied, and `generated_date` defaults to today.

### Signing documents

The **Sign Documents** tool stamps a signature image onto PDFs locally. Put a `signature.png` in the folder (or pass `--signature path`) and the tool searches each PDF for an anchor phrase (default `Preparer Signature`) and places the signature just above it, saving a copy to `Signed_Documents/Signed_<name>.pdf`. Use `--anchor "..."` to match the phrase on your forms.

This is a **visual stamp** of your own signature to save repetitive manual signing — it is not a cryptographic signature and not a client e-signature:

- For tamper-evident signing, a certificate-based (PAdES) digital signature is the next step; it needs a signing certificate (`.p12`/`.pfx`) and an extra library.
- For **binding client e-signatures** (for example Form 8879), use a compliant service such as Encyro. That space is regulated (identity verification/KBA and an audit trail) and should not be home-rolled; this tool deliberately stays a local preparer-side stamp.

### Exporting to Encyro

Encyro has no public developer API, so its e-sign flow is driven through its web app / Outlook add-in. The **Export for Encyro** tool meets it halfway: for each client it builds `Encyro_Ready/<client>/` containing the client's letters converted to PDF (text stays selectable), copies of their signed PDFs and attachments, a single merged `<client>_packet.pdf`, and an `UPLOAD_NOTES.txt` with the recipient email and a signing checklist. You upload the packet to Encyro and place the signature fields there. PDF conversion uses the same PyMuPDF dependency as the rest of the suite — no extra install.

### Emailing documents

The **Compose Email Drafts** tool turns each client record (that has an `email`) into a `.eml` file in `Email_Drafts/`, with the subject and body rendered from `document_templates/email_template.txt` and the client's generated/signed files attached. Open the `.eml` in your mail app, review it, and send it yourself — nothing is sent automatically and no email passwords are stored. Because tax documents contain PII, prefer a secure portal (such as Encyro) for sensitive delivery. Add an `attachments` list to a client record to attach extra files (paths relative to the folder).

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

The desktop app is easiest, but you can also run the sorter directly.

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
python test_extract_form_data.py
python test_generate_documents.py
python test_email_and_sign.py
python test_export_encyro.py
python test_integration.py
```

`test_integration.py` generates fake text PDFs with PyMuPDF and runs the real sort + extract pipeline end to end (including combined-PDF splitting and per-page extraction). It requires the runtime dependencies and skips automatically when they are not installed.

`test_sort_tax_docs.py` also covers combined-PDF page segmentation. `test_extract_form_data.py` covers field extraction for every supported form (W-2, 1099-NEC, 1099-INT, 1099-DIV, 1099-R, 1099-G, 1099-K, SSA-1099, 1098 Mortgage, 1098-T, 1099-B, K-1) using fake form text, including the case where a form title repeats a box label and the amount-format rules that ignore bare box numbers and years.

These tests do not use real taxpayer data. They cover exact W-2 text, W-2 structural indicators, PDF OCR fallback behavior, 1099-NEC vs W-2, brokerage priority, 1099-MISC strictness, 1098-T, mortgage 1098, 1099-G, 1099-K, SSA-1099, OCR hyphen recovery, generic tax statements, and random receipts.

## Simple fake manual test with no real client data

After setup, create a few harmless test PDFs or images that contain only fake text, such as:

- `Form W-2 Wage and Tax Statement`
- `Employee's social security number Employer identification number Wages, tips, other compensation Federal income tax withheld`
- `1099-NEC Nonemployee Compensation`
- `Consolidated 1099 1099-B Proceeds From Broker`
- `1098-T Tuition Statement`
- `Mortgage Interest Statement`

Put those files in the `Uploads` folder, run `python run_sorter.py`, press Enter, and review `Uploads/Organized_Tax_Documents/`, `Document_Inventory.xlsx`, and `processing_log.txt`. The inventory includes winning score, runner-up score, matched keywords, category scores, OCR status, and notes.

## Optional future packaging

You can later package the desktop app into a windowed executable with PyInstaller:

```powershell
py -3.12 -m pip install pyinstaller
py -3.12 -m PyInstaller --onefile --windowed tax_doc_sorter_app.pyw --name "Tax Document Sorter"
```

Packaging is optional and is not required to run the prototype.

## Limitations in this prototype

- Combined-PDF splitting groups by form type; it does not separate two of the same form type on adjacent pages into different files.
- Form data extraction is best-effort and assistive. It reads common labeled boxes with local regex rules; layouts vary, so always verify extracted values and fill blanks by hand. Amounts must include cents or a thousands separator to be captured (this avoids mistaking box numbers and years for dollar values).
- It does not connect to Drake Tax or any other tax software.
- It does not use APIs, paid services, AI, or machine learning.
- OCR quality depends on scan quality and the local Tesseract installation.
- Rule-based sorting is intentionally conservative; uncertain documents should be reviewed manually.
