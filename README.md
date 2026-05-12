# Process Builder

Process Builder is a local-first web app for turning rough plain-English descriptions of recurring business processes into structured SOPs, checklists, and automation opportunity maps.

It is designed for tax, bookkeeping, admin, operations, sales, client onboarding, and small-business workflow consulting use cases. The first version intentionally uses a rule-based generator only. It does not call AI services, external APIs, or any backend.

## Features

- Enter a process name, rough description, process type, and status tag.
- Generate an editable SOP structure with sections for objectives, triggers, inputs, tools, roles, SOP steps, decision points, QC checks, exceptions, communications, risks, automation opportunities, and next improvements.
- Edit every generated section directly in the browser.
- Save processes to browser local storage automatically.
- Duplicate and delete saved processes.
- Export a full SOP as Markdown.
- Export checklist items as a separate Markdown file.
- Filter saved processes by name, type, or status.
- Start immediately with sample processes:
  - Monthly bookkeeping close
  - New tax client onboarding
  - Missing document follow-up
  - Invoice collection follow-up
  - Employee onboarding
  - Vendor bill approval

## Tech stack

This app uses plain HTML, CSS, and JavaScript. There is no build step and no package install required.

## Setup and run instructions

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

You can also open `index.html` directly in a browser. A local server is recommended because it mirrors normal browser module loading behavior.

## Data storage

Processes are stored in the browser's local storage under the key `process-builder-processes-v1`. Data stays on the user's machine and is not transmitted anywhere by the app.

## Development notes

- Main interface markup lives in `index.html`.
- Styling lives in `styles.css`.
- Rule-based generation, local storage, starter data, editing, duplication, deletion, and Markdown export live in `app.js`.
