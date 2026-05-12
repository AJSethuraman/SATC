# Process Builder

Process Builder is a local-first browser app for documenting, improving, and systematizing recurring small-business workflows. It is intended for consultants, service providers, and owner-led businesses that need a practical process document after a client conversation or internal operations review.

The app turns a rough plain-English process description into an editable, client-ready process document with SOP steps, roles, handoffs, required inputs and outputs, quality control checks, common failure points, automation opportunities, and an internal checklist.

This version is intentionally simple and rule-based. It does **not** use AI, external APIs, a backend, login, a database, or third-party dependencies.

## Who it is for

Process Builder is designed for general small-business operations, including businesses such as:

- Contractors and home service companies
- Landscapers and cleaning companies
- Salons and local service businesses
- Agencies and consultants
- Property managers
- Professional services firms
- Accountants, bookkeepers, and tax firms
- Other owner-led small businesses

Tax and bookkeeping examples are included only as starter templates under broader process categories. They do not define the product.

## Features

- Create a new process from rough notes.
- Capture process name, optional business/client name, optional industry/business type, category, status, and raw description.
- Generate an editable process document with all required sections:
  - Process summary
  - Objective
  - Trigger event
  - Frequency
  - Required inputs
  - Expected outputs
  - Tools/systems used
  - Roles and responsibilities
  - Step-by-step SOP
  - Decision points
  - Handoffs
  - Quality control checks
  - Common exceptions
  - Risks or failure points
  - Client/customer/vendor communication points
  - Internal checklist
  - Automation opportunities
  - Recommended next improvement
- Edit every generated process section.
- Manage internal checklist items:
  - Add checklist item
  - Edit checklist item
  - Mark complete or incomplete
  - Delete checklist item
  - Add notes to a checklist item
- Save process documents in browser local storage.
- Reopen saved processes from the process library.
- Change process status from the library or editor.
- Duplicate and delete saved processes.
- Export a full client-ready process document as Markdown.
- Export the internal checklist only as Markdown.
- Copy full Markdown or checklist Markdown to the clipboard.
- Export all saved processes as a JSON backup.
- Import a JSON backup.
- See visible user-facing messages for common errors such as missing required process name, invalid category, local storage load/save failures, and invalid backup imports.

## Process categories

The app uses general small-business categories:

- Client/customer onboarding
- Customer follow-up
- Billing and collections
- Monthly admin
- Field/service operations
- Employee onboarding
- Vendor management
- Document collection
- Sales pipeline
- Quality control
- Reporting
- Finance/bookkeeping
- Professional services
- Custom process

## Starter templates

The app includes general starter templates so it is useful immediately:

- New customer onboarding
- Customer estimate follow-up
- Invoice collection follow-up
- Monthly admin close
- Employee onboarding
- Vendor bill approval
- Field service job closeout
- Document collection process
- Sales lead follow-up
- Customer complaint resolution
- Monthly bookkeeping close
- New tax client onboarding

## How generation works

Generation is deterministic and rule-based. The generator uses:

- Selected process category
- Optional industry/business type
- Rough process description
- Keyword matching
- Starter templates and category defaults

Examples of keyword-based suggestions:

- Mentions of invoices, payments, overdue balances, or collections add billing/collections risks and follow-up steps.
- Mentions of customers, leads, estimates, or proposals add sales and customer follow-up handoffs.
- Mentions of field work, crews, jobs, photos, or service calls add field/service controls.
- Mentions of documents, forms, signatures, or missing information add document collection controls.
- Mentions of reports, spreadsheets, dashboards, or monthly tasks add reporting/monthly admin checks.
- Mentions of QuickBooks, bank statements, receipts, payroll, or reconciliation add finance/bookkeeping controls.
- Mentions of approvals, managers, owners, vendors, or bills add approval and handoff checkpoints.

The goal is not perfect intelligence. The output is a useful first draft that a human should review and clean up.

## Setup and run instructions

No install step is required for the app itself.

From the repository root, start any static file server and open the printed local URL.

### Option 1: Python

```bash
python3 -m http.server 4173
```

Then open <http://localhost:4173>.

### Option 2: Node

```bash
npx serve .
```

Then open the local URL shown by `serve`.

### Option 3: Direct file open

You can open `index.html` directly in a browser. A local server is recommended because it mirrors normal browser module loading behavior.

## Usage

1. Click **New process** or choose a starter template.
2. Enter a process name.
3. Optionally enter business/client name and industry/business type.
4. Choose a process category and status.
5. Paste the rough process description.
6. Click **Generate Process Document**.
7. Edit the generated sections and checklist items.
8. Save, duplicate, delete, export, copy, or back up the process as needed.

## Export and backup

- **Export process Markdown** downloads the full process document.
- **Copy full Markdown** copies the full process document to the clipboard when supported by the browser.
- **Export checklist** downloads only the internal checklist.
- **Copy checklist** copies only the internal checklist to the clipboard when supported by the browser.
- **Export JSON backup** downloads all saved process documents for safekeeping or transfer.
- **Import JSON backup** replaces the current browser library with the imported processes after validating the backup shape.

## Data storage and limitations

Processes are stored in browser local storage under the key `process-builder-processes-v2`. Data stays on the user's machine and is not transmitted anywhere by the app.

Local storage can be cleared by the browser, browser profile cleanup, private browsing sessions, or device changes. Export a JSON backup regularly if the process library matters.

## Development notes

- `index.html` contains the app shell and templates.
- `styles.css` contains the responsive business-professional UI styles.
- `processGenerator.js` contains process categories, starter templates, keyword rules, validation, checklist helpers, and rule-based generation.
- `markdownExport.js` contains Markdown export and JSON backup parsing logic.
- `processStorage.js` contains local-storage save/load helpers.
- `app.js` contains browser DOM and UI event handling.
- `tests/process-builder.test.js` contains Node test coverage for generation, validation, checklist behavior, Markdown, duplication, storage, and backup import/export.

## Testing

```bash
npm test
```

Syntax checks:

```bash
npm run check
```
