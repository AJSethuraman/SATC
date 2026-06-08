# Local Tax Tools Prototype

This is a local-only Python prototype that bundles small tax tools you can run individually or in sequence from one PySide6 desktop app. It uses rule-based keyword scoring, PDF text extraction, and local Tesseract OCR. It does **not** use AI, machine learning, paid APIs, cloud services, Drake Tax integration, a database, PDF splitting, or bookkeeping categories.

## Tools in the suite

Pick one or more tools in the desktop app (they run top to bottom):

0. **Validate Config** — a read-only pre-flight check of `clients.json` and the config files (firm, fee schedule, intake fields, checklist map) that flags problems before a run.
0b. **Import Clients** — import an existing CSV or Excel client list into `clients.json`, mapping common columns automatically (overridable via `import_map.json`) and appending only clients not already present.
1. **Client Intake** — generate a dynamic fillable intake form from an editable field schema, and compile returned responses into `clients.json` (appending only new clients). Feeds every tool below.
2. **Sort Documents** — classify uploads and copy (or move) them into category folders with an inventory workbook. When a single PDF contains more than one form type, it is **split** into one filed PDF per form (see below).
3. **Extract Form Data** — read key fields from **W-2**, **1099-NEC**, **1099-INT/DIV**, **1099-R**, **1099-G**, **1099-K**, **SSA-1099**, **1098 (Mortgage)**, **1098-T**, **1099-B**, and **Schedule K-1**. Output is written two ways: a human-readable `Extracted_Form_Data.xlsx` (one sheet per form type) and machine-readable per-form CSVs in `Drake_Export/` for feeding a downstream entry script.
3b. **Data Diagnostics** — sanity-check the extracted data (federal withholding exceeding wages, no primary amount read, possible duplicates, rows flagged at extraction) to `Diagnostics/`.
4. **Document Checklist** — compare each client's expected documents (from intake) against the sorted categories that have files, and write per-client checklists plus a summary CSV.
5. **Calculate Invoices** — compute invoice line items from an editable fee schedule and write them into `clients.json` for the generator to render.
6. **Generate Documents** — fill editable HTML/Word templates (engagement letter, invoice, extension/cover letter, client organizer letter) from a `clients.json`/`clients.csv` data file and write finished documents to `Generated_Documents/`.
7. **Sign Documents** — stamp your signature image onto PDFs that carry a signature anchor phrase, writing signed copies to `Signed_Documents/`.
7b. **Certificate Sign (PAdES)** — apply a tamper-evident digital signature to PDFs using a PKCS#12 certificate, writing certified copies to `Cert_Signed/`.
8. **Engagement Letter / Form 8879 / Filing Trackers** — report which clients have a signed engagement letter, a signed Form 8879, or a filed/accepted return on file vs. outstanding, to `Status/`.
8b. **Send Reminders** — draft reminder `.eml`s for clients with outstanding signatures or missing documents, to `Reminders/`.
11b. **Payments & AR** — track invoice payments and build an accounts-receivable aging report (0-30 / 31-60 / 61-90 / 90+ days) in `Payments/`.
11c. **Year Rollover** — create a `<year>/` subfolder that carries each client's static details forward, resets the prior year's status (totals, payments, signed flags), and copies your config so next season starts pre-filled. Non-destructive; excluded from the "Full pipeline" preset.
11d. **PDF Merge/Split** — drop PDFs in `PDF_Tools/merge/` to combine them into one file, or in `PDF_Tools/split/` to split each into one PDF per page; output goes to `PDF_Tools/output/`. A manual utility, excluded from the "Full pipeline" preset.
12. **Practice Dashboard** — one HTML page showing where every client stands across the whole pipeline (email, documents, invoice, generated, engagement, 8879, Encyro, archived) with a summary bar.

Before a run, the app performs **pre-run input checks** and warns (without blocking) if a selected tool is missing what it needs — for example a client-data tool with no `clients.json`, the Sign tool with no signature image, or PDF Merge/Split with nothing in `PDF_Tools/`. You can fix it or proceed anyway. The CLI prints the same notes.

In the desktop app the tools are grouped into collapsible phase cards (Onboarding & Documents, Preparation, Signing, Tracking & Reminders, Delivery & Records, Practice Management) inside a scroll area, with **Select all / Clear** and one-click **Presets** (Full pipeline, Intake & documents, Prepare & generate, Sign & deliver, Status & reminders).
9. **Compose Email Drafts** — build a review-ready `.eml` per client (subject/body from a template, that client's generated and signed files attached) in `Email_Drafts/`. Nothing is sent automatically and no credentials are stored.
10. **Export for Encyro** — convert each client's letters to PDF, gather their signed PDFs/attachments, and merge an upload-ready `<client>_packet.pdf` (plus `UPLOAD_NOTES.txt`) under `Encyro_Ready/<client>/`.
11. **Records Retention** — archive each client's complete package into a dated `Retention/<client>_<year>.zip` with a manifest and a keep-until date.

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

### Firm settings (enter once)

Put a `firm.json` in the folder with your firm-wide details and they are merged into every document, email, and reminder automatically — no need to repeat them on each client record. A client record can still override any field. A starting point ships at `document_templates/firm.sample.json`:

```json
{ "firm_name": "Sample Tax & Accounting LLC", "firm_phone": "(217) 555-0100",
  "firm_email": "office@sampletax.example", "preparer_name": "Alex Preparer, EA",
  "payment_terms": "Payment is due within 15 days of the invoice date." }
```

### Practice dashboard

The **Practice Dashboard** tool writes a single `Dashboard/dashboard.html` — one row per client, one column per stage (email on file, documents received, invoice, documents generated, engagement letter, Form 8879, Encyro packet, archived), each shown as a colour-coded pill, with a summary bar of the counts that matter (missing documents, outstanding signatures, not invoiced, not archived). It reads what the other tools already produced, so run it any time for a live "where is everyone" snapshot.

### Editing clients (no JSON)

In the desktop app, **Edit Clients** opens a table to add, edit, or remove clients
without touching `clients.json` by hand. Documents and Services are entered
comma-separated; any fields the table doesn't show (invoice totals, signed status,
custom fields) are preserved when you save, and the previous `clients.json` is
backed up to `clients.backup.json` first. This is the friendly alternative to the
Import Clients and Client Intake tools for day-to-day edits.

### Collecting client intake

The **Client Intake** tool builds a fillable form and turns returned answers into your `clients.json`:

1. On first run it writes `intake_fields.json` to the folder — an editable list of questions (this is the **dynamic** part: add, remove, or reorder fields and the form follows). Field types include text, email, tel, number, date, textarea, dropdown (`select`), and multi-select (`checkboxes`).
2. It generates `Intake/intake_form.html`. Send it to a client (or fill it yourself). The form runs entirely in the browser; **Download my answers** saves a `<name>_intake.json` — nothing is uploaded from the page.
3. Drop the returned `*_intake.json` files in the folder and run the tool again. It compiles them into `clients.json`, appending only clients not already present (matched by email, else name), so hand-edited records are never overwritten.

The default schema includes an **"expected documents"** checklist (W-2, 1099s, K-1, …) — those answers drive the upcoming Checklist tool.

### Reading filed return packets

Tax software exports little, so the **Read Filed Forms** tool works from the finished
return packet PDF instead. It reads each client's packet, matches it to a client by
the name on it, and detects which form numbers are present (Form 1040, the schedules,
state and local returns). It then writes back **what was filed**:

- `services` — the billable forms detected, so the invoice bills exactly what was
  prepared (two state/local returns bill as quantity 2);
- `returns` / `efiled_returns` — the returns by name (Federal / Ohio / RITA …);
- `return_filed: true` — which lights up the Filing Tracker and dashboard.

Detection is deterministic substring matching on standard form numbers, configured by
an editable `form_signatures.json` (add your states/locals there). It records *which*
forms were filed, not the refund/balance amounts (those still come from your records
or the results table). Needs PyMuPDF; assistive — verify against the packet.

### Checking documents received

The **Document Checklist** tool compares each client's `expected_documents` (collected at intake) against the sorter categories that actually contain files, and writes `Checklists/<client>_checklist.html` (printable / sendable) plus an aggregate `checklist_summary.csv`. Each expected item shows as **Received**, **Missing**, or **Manual check** (for labels with no automatic mapping, like "Other"), and any received-but-unexpected categories are noted.

Run **Sort Documents** first so there is something to check against. The intake-label → sorter-category mapping is **dynamic**: a `checklist_map.json` is written to the folder on first run, so you can change how labels map (for example, point "1099-INT" and "1099-DIV" at different categories) without touching code.

### Calculating invoices

The **Calculate Invoices** tool builds each client's invoice `line_items` from a fee schedule and writes them into `clients.json`, so **Generate Documents** then renders a finished invoice. It also writes `Invoices/fee_worksheet.csv`. Each client's bill is the sum of: a base preparation fee, a line for every document they reported at intake (`expected_documents`) that has a price, and any explicit `services` on the record (a service key, or `{"service": "state_return", "quantity": 2}`, or an inline `{"description": ..., "price": ...}`).

The fee schedule is **dynamic**: `fee_schedule.json` is created in the folder on first run with placeholder prices — edit the descriptions and amounts to match your pricing. Run this **before** Generate Documents so the invoice picks up the computed lines.

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

- For tamper-evident signing, use the **Certificate Sign (PAdES)** tool: point it at your PKCS#12 certificate (`.p12`/`.pfx`) and it embeds a cryptographic signature in each input PDF (written to `Cert_Signed/`). The certificate password is never stored — supply it via the `SATC_CERT_PASSWORD` environment variable (CLI) or the transient password field (desktop). Requires the `pyhanko` package.
- For **binding client e-signatures** (for example Form 8879), use a compliant service such as Encyro. That space is regulated (identity verification/KBA and an audit trail) and should not be home-rolled; this tool deliberately stays a local preparer-side stamp.

### Tracking signed documents

Two trackers answer "who still owes us a signature?":

- **Engagement Letter Tracker** — is a signed engagement letter on file per client?
- **Form 8879 Tracker** — is a signed Form 8879 (e-file authorization) on file per client?

Each writes `Status/<name>_status.csv` and a printable `.html` table marking every client **On file** or **Outstanding**. A document counts as on file when either the client record sets the flag (`engagement_letter_signed` / `form_8879_signed`, e.g. a date or `true`) or a matching file is found — one whose name contains the client's name and the keyword (`engagement` / `8879`) — in the folder, its subfolders, or `Signed_Documents/`. So drop returned signed PDFs in the folder (named with the client and form) and re-run to update the status.

### Sending reminders

The **Send Reminders** tool finds everything still outstanding for each client — a signed engagement letter, a signed Form 8879, and any missing documents (reusing both trackers and the checklist) — and, when a client has outstanding items and an email, writes a reminder `.eml` to `Reminders/` listing exactly what is needed. The wording comes from `document_templates/reminder_template.txt`. Like the email tool, nothing is sent: review each draft and send it yourself. Clients with nothing outstanding are skipped.

### Exporting to Encyro

Encyro has no public developer API, so its e-sign flow is driven through its web app / Outlook add-in. The **Export for Encyro** tool meets it halfway: for each client it builds `Encyro_Ready/<client>/` containing the client's letters converted to PDF (text stays selectable), copies of their signed PDFs and attachments, a single merged `<client>_packet.pdf`, and an `UPLOAD_NOTES.txt` with the recipient email and a signing checklist. You upload the packet to Encyro and place the signature fields there. PDF conversion uses the same PyMuPDF dependency as the rest of the suite — no extra install.

### Emailing documents

The **Compose Email Drafts** tool turns each client record (that has an `email`) into a `.eml` file in `Email_Drafts/`, with the subject and body rendered from `document_templates/email_template.txt` and the client's generated/signed files attached. Open the `.eml` in your mail app, review it, and send it yourself — nothing is sent automatically and no email passwords are stored. Because tax documents contain PII, prefer a secure portal (such as Encyro) for sensitive delivery. Add an `attachments` list to a client record to attach extra files (paths relative to the folder).

### Records retention

The **Records Retention** tool packages each client for your retention requirement: it collects everything produced for them — generated documents, signed PDFs, checklist, Encyro packet, and their intake response — into `Retention/<client>_<tax_year>.zip` with a `MANIFEST.txt` listing the contents and a **keep-until date** (archive year + retention period, 3 years by default; set with `--years`). When the folder holds exactly one client, the sorted source documents (their W-2s, 1099s, …) are included under `Source_Documents/`; with multiple clients those cannot be attributed automatically, so the archive holds the per-client artifacts and notes the omission. Run it last, after the other tools have produced their output.

### Per-client folders (batch) mode

By default the suite treats the chosen folder as one client. **Per-client folders mode** instead runs the selected tools once per client, each in their own subfolder, so sorting, extraction, the checklist, and retention are attributed correctly with no cross-client mixing. Enable it with the **"Per-client subfolders (batch)"** checkbox in Advanced Options, or `--per-client` on the CLI.

Two layouts work:

- A parent `clients.json` roster → a subfolder named for each client (created if missing); put each client's uploads in their subfolder.
- No parent `clients.json` → every immediate subfolder is treated as a client (using its own `clients.json` if present, else the folder name).

Shared config at the parent (`firm.json`, `intake_fields.json`, `checklist_map.json`, `fee_schedule.json`, `document_templates/`) is copied into each subfolder once so the same settings apply everywhere. After the run, each subfolder's `clients.json` is aggregated back into the parent — so practice-wide tools (**Practice Dashboard**, **Payments & AR**) can then be run once at the parent level over all clients.

```bash
python tax_tools.py "/path/to/Clients" --tools sort,extract,checklist --per-client
```

## Architecture (how it stays decoupled)

The suite is built as separate, loosely-coupled components so a change in one tool
can't ripple into others:

- **`core.py`** — the only shared-primitive module (HTML escaping, money parsing/
  formatting, per-client file ownership). It depends on nothing else in the suite,
  so every tool builds on one stable, tested contract instead of reaching into
  another module's internals.
- **One module per tool**, each split into **pure functions** (domain logic, no
  disk — easy to test in isolation) and a thin **`run_X(folder) -> dict`** runner
  that does the I/O. Most bugs are caught at the pure-function layer.
- **`tax_tools.py`** is the single registry that wires tools together; the desktop
  app and CLI both drive that registry, so there's one place that knows the tool
  list, order, and grouping.
- Each tool writes to its own output subfolder and reads shared data (`clients.json`,
  config files) rather than calling into other tools where avoidable.

When adding a feature, prefer a new leaf module (pure core + thin runner + tests)
over threading special cases through existing tools.

### Year-by-year fees (Fee Workbook)

The **Fee Workbook** tool keeps your fee schedule as an Excel workbook, `fee_schedule.xlsx`, with **one sheet per tax year** so prices and discounts are easy to see and adjust year over year. Running it:

- creates the workbook (and the year's sheet, seeded from the current `fee_schedule.json` or the default) if it does not exist;
- reads the year's sheet and writes it to `fee_schedule.json` — the file Calculate Invoices uses — so your edits in Excel take effect;
- copies the year to a **next-year sheet** ready to tweak (use `--no-next` to skip).

Each sheet has a **FORMS** table (Key / Description / Price / Additional) and a **DISCOUNTS** table (Key / Description / Amount / Percent). Edit a year, re-run the tool, then run Calculate Invoices. The target year defaults to the latest client `tax_year` (or `--year`). Needs the `openpyxl` package.

**Year Rollover uses it too:** when you roll clients forward into a `<year>/` folder, if the workbook has a sheet for that year, the new folder's `fee_schedule.json` is taken from it — so next year's folder starts with next year's prices, not last year's.

## Building a standalone desktop app

You can package the desktop app into a single double-click executable so it runs
without a separate Python install:

```bash
python build_app.py        # builds dist/SATC (SATC.exe on Windows) for THIS OS
```

PyInstaller builds for the operating system it runs on, so run it on Windows for a
`.exe` and on macOS for an app. To build all three at once without owning every OS,
use the included GitHub Actions workflow (**Actions → Build desktop app → Run
workflow**, or push a `v*` tag); it builds Windows/macOS/Linux and uploads each as a
downloadable artifact. The shipped `document_templates/` are bundled into the
executable, and config files are still created next to your working folder on first
run so they remain editable.

**Tesseract OCR is not bundled** (it's a separate program). Install it on the
machine if you need OCR for scanned PDFs/images; the app works without it otherwise.

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
python test_core.py
python test_preflight.py
python test_clients_editor.py
python test_validate_config.py
python test_import_clients.py
python test_year_rollover.py
python test_pdf_tools.py
python test_fee_workbook.py
python test_intake.py
python test_checklist.py
python test_invoice_calc.py
python test_status_tracker.py
python test_reminders.py
python test_cert_sign.py
python test_retention.py
python test_dashboard.py
python test_diagnostics_payments.py
python test_batch.py
python test_tax_tools.py
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
