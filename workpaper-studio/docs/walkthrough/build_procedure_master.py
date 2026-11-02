"""Build the second procedure: from the master database's work list to the data mart. Same builder as the first.

    python3 workpaper-studio/docs/walkthrough/build_procedure_master.py
"""
import build_procedure as b

HERE = b.HERE
SHOTS = HERE / "master-to-datamart-2026-11-02"
STEPS = [
    ("Set who can do what", "Admin (M. Okafor)", "Read or change the access levels",
     "Go to **Access**. Each column is one of this organization's levels; tick what it may do. Add a level or a person in the last column or row, then **Save as a new version**.",
     "The levels and people as the organization set them, the extra rules (such as a second person for limits), and what is always true whatever is ticked: "
     "nobody reviews work they entered or approves a tool they proposed, and every action is logged.",
     ["step-01-access-zoom.png"]),
    ("Load the work", "Admin", "Load the work list from the master database",
     "On **Cases**, under *Work from the master database*, click **Load the work list** on the tool's row.",
     "A green banner counts what happened: loaded, already here, refused. Open *Why each was refused* to read each refused line's reason, in words. "
     "Here one line names a facility type the tool's list does not have, and one names a preparer nobody has heard of. The master database is only read.",
     ["step-02-work-from-master-zoom.png", "step-03-loaded.png"]),
    ("Do the work", "Preparer (A. Rivera)", "Pick a case from Assigned to me",
     "Sign in as the preparer. **Assigned to me** lists the lines the master database gave you, with the line number it uses.",
     "Only your own cases. Filter by tool, status, or search by line, case, subject or person.",
     ["step-04-assigned-to-me-zoom.png"]),
    ("Do the work", "Preparer", "Open it: what the database knew is already filled in",
     "Click the case.",
     "Tester, reviewer, quarter, borrower, security and the facilities are already there, and the strip counts only what is left (12 here). Everything else is the same as a case started by hand.",
     ["step-05-prefilled-case-zoom.png"]),
    ("Do the work", "Preparer", "Correct a value the master database got wrong",
     "Type over it, like any entry.",
     "The new value is kept and logged old → new. It stays marked as changed from the master database, all the way to the data mart (see step 8). Nothing is overwritten quietly.",
     ["step-06-corrected-master-value-zoom.png"]),
    ("Release", "Preparer, then reviewer", "Finish, review, approve and release as before",
     "Complete the questions and analysis, record the exception, submit. The reviewer acknowledges it, approves and releases (the first procedure covers each step).",
     "Outputs now lists four released files: the data feed (JSON and CSV), the workbook, and **answers-row.csv**, every answer of the case in one row, the shape a master table loads.",
     ["step-07-released-files-zoom.png"]),
    ("See the results", "Anyone with access", "Read the results across cases",
     "Click **Results**.",
     "From the data mart, across released cases: how each question was answered; every partially or not effective answer with its comment (the root-cause list); "
     "results against limits; exceptions by reason; every answer that differs from what the master database sent. **Take the data** downloads each table as CSV.",
     ["step-08-results.png"]),
    ("See the results", "Anyone", "Trace where each value came from",
     "Open the case's **History**.",
     "The oldest entries, at the foot of the list, are *loaded*: one per value, each naming the master database and the line. Every change after that is someone's, with old and new.",
     ["step-09-history-loaded.png"]),
]
ROUTE = [("Access", "levels · people"), ("Load", "master database → cases"), ("Assigned to me", "pick a line"),
         ("Case", "pre-filled · correct"), ("Release", "files · data mart"), ("Results", "answers · why · limits")]
if __name__ == "__main__":
    b.build(STEPS, ROUTE, SHOTS, HERE.parent / "PROCEDURE-master-to-datamart.md", SHOTS / "PROCEDURE-master-to-datamart-2026-11-02.html",
            SHOTS / "PROCEDURE-master-to-datamart-2026-11-02.pdf", "From the master database's work list to the data mart",
            "The master database says what to test. Studio opens each line as a case, already filled with what the database knows. People do the work, "
            "and every released case, every answer with its state, lands in a data mart where results can be read across cases.",
            who=[("Admin", 0, 2), ("Preparer", 2, 4), ("Preparer, reviewer", 4, 5), ("Anyone", 5, 6)])
    print("built")
