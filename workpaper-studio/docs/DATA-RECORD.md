# The data record: where work comes from and where it goes

*Proposal, 2 November 2026, answering the owner, and **built the same day** (status at the end):*

> *"in my work version employees choose a linesheet from a list created by the master database loading into that excel sheet"*
>
> *"this would also be the method for feeding any associated "datamart" with it"*

**One route in and one route out, the same for every tool.** The master database says what is to be tested. People do the testing in Studio, or in the workbook. The finished record goes back as a file the master database and any data mart load. Nothing connects live to another system until somebody decides it should, so this works behind the same boundaries the workbook does today.

```
master database ──(1) work list──▶ Studio: one unstarted case per line, pre-filled
                                       │  a preparer picks from "Assigned to me" (or downloads it as a workbook)
                                       ▼
                                 completed, reviewed, released
                                       │
master database / data mart ◀──(3) record files── (2) the released record
```

## 1 · In: the work list

- **What arrives.** The master database exports the lines to be tested as a file (CSV or Excel). This is the same list that today becomes "choose a linesheet". Each line carries:
  - its own **line id** from the master database. This is the key that ties everything back;
  - whatever the database already knows, such as entity, quarter, borrower, facilities, and the assigned tester and reviewer.
- **The pack says how to read it.** Each tool pack gets an `intake` section mapping the list's columns to the tool's fields and table rows, for example `"Borrower" -> borrower` and `"Facility 1 type" -> facilities row 1, type`.
- **A list that does not fit is refused, line by line, with the reason.** An unknown column, a value that is not in a dropdown list, a duplicate line id: each is refused and named, not half-loaded (the same rule as packs).
- **Each line becomes an unstarted case**, pinned to the current tool and limits versions, like any case.
- **Loaded values carry their source**: "from master list `Q3-sample.csv`, loaded 2 Nov by M. Okafor". A preparer can correct a loaded value. The correction is logged old → new, and it reaches the record as *changed from the master database*. The master database stays authoritative until the change is reviewed; nothing is overwritten quietly.
- **Choosing a linesheet** becomes the worklist:
  - **Assigned to me**, **Unassigned** and **All**, filtered by entity, quarter and subject.
  - Open a line and it is the case.
  - Reopen it later and it is exactly as saved, under its pinned versions.

## 2 · The record itself

- **The event log is the record.** Every entry, correction, point, exception and sign-off is kept, append-only.
- **Released files** are derived from it, written once and fingerprinted. Each carries the master database's line id, the case id, the tool version and fingerprint, and the limits version.

## 3 · Out: what the master database and a data mart load

Every format below has one column per field, question and result, and its shape is generated from the pack, so a new question becomes a new column with no development. A version number on each format means a loader can tell a format change from bad data.

| File | Shape | For |
|---|---|---|
| **Wide row** | One row per case: line id, every field, every question's rating and comment, every result and verdict, status, and who prepared, approved and released it | The master table, as the work version's feed does today |
| **Values** | One row per value: path, label, **state** (entered, zero, missing, not applicable, excluded, calculated), value, reason, source | A data mart. The state column is what a flat row cannot say: why a value is empty |
| **Events** | One row per action: who, when, what, old, new | Audit, and rebuilding anything downstream |
| **Exceptions and review points** | One row each | Reporting on where policy is being exceeded and why |

- **Personal fields are masked in all of them by default.** Unmasked values leave only through an explicit, logged export, and only if the organization's access levels allow it (R17).
- **Delivery.** At first the files are dropped into a folder the loader watches, one batch per release or per day. A direct database write or an API comes later, and only once the receiving system's owner agrees the format (D7).

## 4 · People who stay in Excel

From the same work list, **Download as workbook** gives the generated workbook, pre-filled from the master line. **Upload** reads a filled workbook back. Each cell becomes a logged entry, the engine re-checks everything, and anything the workbook changed that it should not have (a formula, a locked cell) is refused and named. Studio stays the record either way.

## What is built and what is not

| | |
|---|---|
| Built (2 Nov 2026) | **In:** the work list read from the master database (a read-only SQLite connection, standing in for any SQL database, or CSV files), mapped by each pack's `intake`, refused line by line with reasons, each line a case pinned and assigned, every loaded value logged as *loaded* with its source, corrections logged and carried as changed-from-master. **Worklist:** Assigned to me / Waiting for review / Everything I can see, filtered by tool, status and text. **Out:** every answer (every question, answered or not, with its state); the one-row `answers-row.csv` at release; the **data mart** (`datamart.db`: cases, answers, results, exceptions, review points, actions, plus one generated wide view per tool version), append-only and de-identified; a **Results** screen reading it, with CSV downloads of every table and view |
| Not built | A live connection to a server database (the reader is SQLite and CSV; another driver is one function); noticing a master line that changed after it was loaded; a screen for `sources.json`; workbook upload |

## Answers from the owner, 2 Nov 2026

1. *"the excel file queries the db, which is simple to understand as excel but it does not to be in excel. i understand that excel is not necessarily the best for multiple users"*. Studio now reads the master database itself, read-only, and nobody has to open a workbook to get their list.
2. *"The feed has to return all answers - the point is to easily see results and it also allows for checks on the outside stuff is done in addition to route cause analysis"*. Every answer is returned, with its state and where it came from. The Results screen shows the root-cause list (every partially or not effective answer, with its comment).
3. On the data mart: *"this is what we are deciding. it does not need to work exactly like work it should work better if possible"*. **Recommended and built:** Studio holds the record and publishes into a separate mart. The master table's one-row-per-case shape is a **view** generated from the pack, so it cannot drift from the answers. A loader can take the CSVs anywhere.

## Questions the owner has answered (above), kept for the record

1. **What does the master database hand over today?** A file export the sheet opens, or does the sheet query the database itself? This decides whether "in" is a file Studio reads or something that has to be connected.
2. **What goes back, and in what shape?** Is it the wide row the feed tabs build? The real column list (the feed-schema tab, which was not in the photos) is the format to match.
3. **Is the data mart fed from the master table, or separately?** If it is fed from the master table, the wide row is enough. If separately, the values file with states is the one it should take.
