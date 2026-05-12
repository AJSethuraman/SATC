# Workflow Task Checklists

A simple local web app for generating client task checklists from predefined accounting and tax workflows. The app runs in the browser and stores checklist data in browser local storage, so no backend or database is required.

## Included workflows

- New tax client onboarding
- Monthly bookkeeping
- Year-end cleanup
- Rental property tax prep

## Features

- Enter a client name, due date, and workflow to generate a checklist.
- Each generated task includes a suggested date based on the final due date.
- Answer optional intake questions for any workflow to add matching conditional tasks.
- Review generated tasks grouped by category, with badges for internal work versus client-facing document requests or follow-up.
- Copy a client request email, print a client-facing request list, or print a full internal checklist for each saved checklist.
- Mark tasks complete as work progresses.
- Add notes to individual tasks for questions, follow-up items, or status updates.
- Save all checklist data, intake answers, task completion, and notes in browser local storage.
- Delete individual checklists or clear all saved browser data.

## Setup instructions

1. Start the local development server:

   ```bash
   npm start
   ```

2. Open <http://127.0.0.1:5173/> in your browser.

No build step or backend service is required.

## Testing

Run the workflow unit tests with:

```bash
npm test
```

## Data storage note

Checklist data is saved only in the current browser's local storage. Clearing browser site data, using a different browser, or using a different device will not preserve existing checklists.
