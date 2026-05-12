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
- Answer optional intake questions for workflows that support conditional tasks.
- Rental property tax prep adds extra tasks when intake answers identify purchases, sales, improvements, personal use, short-term rental activity, out-of-state property, property manager use, refinancing or new mortgages, or casualty and insurance claim activity.
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
