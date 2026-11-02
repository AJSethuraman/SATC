# Procedure: from the master database's work list to the data mart

*Walked through the screens on 2 November 2026. Synthetic people and data; the limit and the method are fictional demonstrations.*
*Rendered copy with every screenshot embedded: `walkthrough/credit-review-2026-11-02/PROCEDURE-credit-review-2026-11-02.pdf`.*

**The route:** Access (levels · people) → Load (master database → cases) → Assigned to me (pick a line) → Case (pre-filled · correct) → Release (files · data mart) → Results (answers · why · limits)

## Set who can do what

### 1. Read or change the access levels
*Admin (M. Okafor)*

**Do.** Go to **Access**. Each column is one of this organization's levels; tick what it may do. Add a level or a person in the last column or row, then **Save**.

**A correct screen.** The levels and people as the organization set them, additional controls (such as a second approver for limits), and the fixed controls: nobody reviews work they entered or approves a tool they proposed, and every action is logged.

![Read or change the access levels](walkthrough/credit-review-2026-11-02/step-01-access-zoom.png)

## Load the work

### 2. Load the work list from the master database
*Admin*

**Do.** On **Cases**, under *Work list*, click **Load work list** on the tool's row.

**A correct screen.** A green banner counts what happened: loaded, already here, refused. Open *Refused lines* for each line's reason. Here one line names a facility type the tool's list does not have, and one names a preparer nobody has heard of. The master database is only read.

![Load the work list from the master database](walkthrough/credit-review-2026-11-02/step-02-work-from-master-zoom.png)
![Load the work list from the master database](walkthrough/credit-review-2026-11-02/step-03-loaded.png)

## Do the work

### 3. Pick a case from Assigned to me
*Preparer (A. Rivera)*

**Do.** Sign in as the preparer. **Assigned to me** lists the lines the master database gave you, with the line number it uses.

**A correct screen.** Only your own cases. Filter by tool, status, or search by line, case, subject or person.

![Pick a case from Assigned to me](walkthrough/credit-review-2026-11-02/step-04-assigned-to-me-zoom.png)

### 4. Open it: what the database knew is already filled in
*Preparer*

**Do.** Click the case.

**A correct screen.** Tester, reviewer, quarter, borrower, security and the facilities are already there, and the strip counts only what is left (12 here). Everything else is the same as a case started by hand.

![Open it: what the database knew is already filled in](walkthrough/credit-review-2026-11-02/step-05-prefilled-case-zoom.png)

### 5. Correct a value the master database got wrong
*Preparer*

**Do.** Type over it, like any entry.

**A correct screen.** The new value is kept and logged old → new. It stays marked as changed from the master database, all the way to the data mart (see step 8). Nothing is overwritten quietly.

![Correct a value the master database got wrong](walkthrough/credit-review-2026-11-02/step-06-corrected-master-value-zoom.png)

## Release

### 6. Finish, review, approve and release as before
*Preparer, then reviewer*

**Do.** Complete the questions and analysis, record the exception, submit. The reviewer acknowledges it, approves and releases (the first procedure covers each step).

**A correct screen.** Outputs now lists four released files: the data feed (JSON and CSV), the workbook, and **answers-row.csv**, every answer of the case in one row, the shape a master table loads.

![Finish, review, approve and release as before](walkthrough/credit-review-2026-11-02/step-07-released-files-zoom.png)

## See the results

### 7. Read the results across cases
*Anyone with access*

**Do.** Click **Results**.

**A correct screen.** From the data mart, across released cases: ratings by question; every ineffective or partially effective rating with its comment; limit tests; exceptions by reason; changes to master data. **Downloads (CSV)** gives each table.

![Read the results across cases](walkthrough/credit-review-2026-11-02/step-08-results.png)

### 8. Trace where each value came from
*Anyone*

**Do.** Open the case's **History**.

**A correct screen.** The oldest entries, at the foot of the list, are *loaded*: one per value, each naming the master database and the line. Every change after that is someone's, with old and new.

![Trace where each value came from](walkthrough/credit-review-2026-11-02/step-09-history-loaded.png)
