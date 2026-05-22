# Workflow Task Checklists

A local SAT-C LLP web app for maintaining a reusable client index, linking people and businesses, and generating relationship-aware client engagement checklists. The app runs in the browser and stores clients, relationships, engagements, tasks, notes, and intake answers in browser local storage, so no backend or database is required.

## Included engagement workflows

- Personal 1040 core
- Personal Schedule C
- Personal rental Schedule E
- Business monthly bookkeeping
- Business year-end cleanup
- Business S corporation tax
- Business partnership tax

## Features

- Create reusable person and business client records.
- Link people and businesses with relationship types such as owner, shareholder, partner, officer, authorized contact, payroll contact, and bookkeeper.
- Filter engagement workflows by client type so personal work stays under people and business/entity work stays under businesses.
- Generate engagements with risk flags, relationship-generated K-1 reminders, precise client-facing request text, and internal instructions.
- Review generated tasks grouped by category, with text badges for internal work, client-facing requests, risk flags, and relationship-generated reminders.
- Copy a client request email, print a client-facing request list, or print a full internal checklist for each engagement.
- Mark tasks complete, add notes, duplicate engagements, delete engagements, and clear all local data.
- Save clients, relationships, engagements, intake answers, task completion, and notes in browser localStorage.

## Setup instructions

1. Open `index.html` directly in your browser by double-clicking it.

You can also start a local development server if preferred:

```bash
npm start
```

Then open <http://127.0.0.1:5173/> in your browser. The app remains browser-only and stores data in localStorage.

## Development

The browser uses `src/browser-app.js`, a classic script generated from the organized source files so `index.html` works from `file://`. After changing files in `src/app.js`, `src/workflows.js`, or `src/outputs.js`, rebuild the browser script:

```bash
npm run build
```

## Testing

Run the workflow unit tests with:

```bash
npm test
```

## Data storage note

Client, relationship, and engagement data is saved only in the current browser's localStorage. Clearing browser site data, using a different browser, or using a different device will not preserve existing records.
