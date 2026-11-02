"""Work list to data mart procedure. Screenshots: master-to-datamart-2026-11-02/."""
from procedure import HERE, build

SHOTS = HERE / "master-to-datamart-2026-11-02"
DOC = {
    "title": "Workpaper Studio: Work List and Results Procedure",
    "header": [("Document", "Procedure for loading the work list from the master database, completing assigned cases, and reviewing results"),
               ("Effective date", "[CONFIRM: effective date]"),
               ("Owner", "[CONFIRM: procedure owner]"),
               ("Applies to", "Credit file review, version 1.1"),
               ("Data", "Synthetic master database. Names, borrowers and limits are fictional.")],
    "purpose": "This procedure explains how cases are created from the master database, how a preparer completes an assigned case, "
               "and how released results are reviewed across cases.",
    "scope": "It covers access levels, loading the work list, working an assigned case, correcting master data, and the Results screen. "
             "Completing, reviewing and releasing a case is covered in the Credit File Review Procedure.",
    "before": [("Workpaper Studio", "A name set up on the Access screen"),
               ("Admin", "Manage access and Load work lists"), ("Preparer", "Edit case entries"),
               ("Reviewer", "Approve cases and Release cases"), ("Master database", "Configured for the tool by the installation")],
    "route": [("Access", "levels · people"), ("Load", "work list"), ("Assigned to me", "select a case"),
              ("Case", "pre-filled · correct"), ("Release", "files · data mart"), ("Results", "ratings · exceptions")],
    "who": [("Admin", 0, 2), ("Preparer", 2, 4), ("Preparer, reviewer", 4, 5), ("Anyone", 5, 6)],
    "steps": [
        {"title": "Review access levels", "role": "Admin",
         "do": ["Select **Access**.", "Review the permissions for each level and the levels each person holds.",
                "Make any change, enter a change note, and select **Save**."],
         "see": "The change is saved as a new version under Access history.",
         "note": "The fixed controls apply whatever is selected: a preparer cannot review or approve a case they prepared or entered, "
                 "a tool cannot be approved by the person who proposed it, and the case history cannot be changed.",
         "images": ["step-01-access-zoom.png"]},
        {"title": "Load the work list", "role": "Admin",
         "do": ["On **Cases**, under Work list, select **Load work list** on the tool's row.", "Open **Refused lines** to review each refused line."],
         "see": "The banner reads *Work list loaded* with the number of new, existing and refused lines. Each refused line shows its reason.",
         "note": "A line is refused when a value does not match the tool, such as a facility type that is not on its list, "
                 "or when the assigned preparer is not set up in Access. Correct it in the master database and load again.",
         "images": ["step-02-work-from-master-zoom.png", "step-03-loaded.png"]},
        {"title": "Select an assigned case", "role": "Preparer",
         "do": ["On **Cases**, select **Assigned to me**.", "Filter by tool or status, or search, as needed."],
         "see": "The cases assigned to you, each with its master database line number.",
         "images": ["step-04-assigned-to-me-zoom.png"]},
        {"title": "Verify the pre-filled values", "role": "Preparer",
         "do": ["Open the case.", "Verify the values loaded from the master database against the file."],
         "see": "Tester, reviewer, quarter, borrower, security and the facilities are already entered. The status strip counts only what is left.",
         "images": ["step-05-prefilled-case-zoom.png"]},
        {"title": "Correct master data where it is wrong", "role": "Preparer",
         "do": ["Enter the correct value over the loaded value."],
         "see": "The new value is kept. The case history shows the loaded value and the change, and Results lists the case under Changes to master data.",
         "images": ["step-06-corrected-master-value-zoom.png"]},
        {"title": "Complete, review and release the case", "role": "Preparer and reviewer",
         "do": ["Follow steps F to O of the Credit File Review Procedure."],
         "see": "Outputs lists four released files: the data feed (JSON and CSV), the workbook, and the answers file with every answer in one row.",
         "images": ["step-07-released-files-zoom.png"]},
        {"title": "Review results across cases", "role": "Anyone with access",
         "do": ["Select **Results**.", "Use **Downloads (CSV)** to take any table for further analysis."],
         "see": "Results shows ratings by question, each ineffective or partially effective rating with its comment, limit tests, "
                "exceptions by reason, and changes to master data, for every released case.",
         "note": "Results includes released cases only. Personal fields, such as the borrower name, are masked.",
         "images": ["step-08-results.png"]},
        {"title": "Trace a value to its source", "role": "Anyone with access to the case",
         "do": ["Open the case and select **History**."],
         "see": "The first entries, at the foot of the list, are the values loaded from the master database, each with its line number. "
                "Every change after that shows who made it, when, and the old and new value.",
         "images": ["step-09-history-loaded.png"]},
    ],
    "practices": ["Correct master data in the case, so the change is recorded, rather than editing the master database mid-review.",
                  "Review refused lines after every load; a refused line is not tested until it is corrected and loaded again."],
}

if __name__ == "__main__":
    for p in build(DOC, SHOTS, HERE.parent / "PROCEDURE-master-to-datamart.md", SHOTS / "PROCEDURE-master-to-datamart-2026-11-02.html",
                   SHOTS / "PROCEDURE-master-to-datamart-2026-11-02.pdf"):
        print(p)
