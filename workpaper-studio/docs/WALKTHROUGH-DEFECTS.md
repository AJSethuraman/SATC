# Walkthrough defects: credit file review, end to end

*Walked 2 November 2026 through the screens in Chromium (Playwright, because the Chrome extension the walk skill names is not available in this cloud session). The installation started empty. Every step went through a screen; no step used the API. The route is in `PROCEDURE-credit-review.md` and its rendered copy.*

**Denominator: 73 tests passing, including a parity test that recalculates 27 exported workbooks in LibreOffice. None of them caught any of the 15 defects below.** Twelve are about what a person sees or can do, and no test asserts those. Three are about what leaves the application (1, 2 and 5). Those three were tested, but only for what the tests already expected.

The job walked: a designer proposed the credit file review tool and an approver approved it. An admin confirmed the debt-to-income limit. A preparer completed a case and recorded an exception for a result above the limit, then submitted it. A reviewer raised a point and acknowledged the exception. The preparer answered the point. The reviewer cleared it, approved the case and released it, and the released files were opened.

Ranked by what each would cost a real client. Status for each: **open** (nothing was fixed during the walk, by rule).

---

## High

### 1. The released workbook carries the borrower's full name; the feed masks it
**Did.** Released CFR-0001 and opened `CFR-0001.xlsx` in LibreOffice.
**Screen said.** On Outputs, the page says "Fields marked personal are masked in it", meaning the feed.
**Actually true.** The feed has `H••••`. The workbook's Borrower details panel shows the full name, **Harbor Millwork LLC**. Both are fingerprinted as "the record". `CLAUDE.md` says only masked values belong in artifacts.
**Fix.** Decide whether the workbook is an internal working copy, which may hold the name and should be labelled as such, or a released artifact, which must mask it. Until that is decided, mask personal fields in the released workbook and test the released files, not only the feed.

### 2. The released workbook does not record the exception, the review points or the approval
**Did.** Opened the released workbook after the reviewer acknowledged an above-limit exception and approved the case.
**Actually true.** The workbook shows debt-to-income at 51.3%, *Above limit*, and *Ready for review: Yes*. It has nothing about the recorded exception, who acknowledged it, the review point and its answer, or who approved the case. Someone who keeps only the workbook sees an approved case that fails its limit, with no reason given.
**Fix.** Add an "Exceptions and review" screen to the exported workbook: each exception with its reason, note, who recorded it and who acknowledged it; each review point with its replies; and the approval.

### 3. Pressing Tab returns focus to the field just left
**Did.** Typed into Scope and pressed Tab.
**Actually true.** Focus is back on Scope. Saving re-draws the page and then focuses the changed field, not the field the person moved to. Every field takes two Tabs. Someone typing ahead types into the field they just left: the next value overwrites the one they meant to keep, and the save that follows records it as their entry.
**Fix.** After a save, return focus to wherever it was when the save started (`document.activeElement` at send time), not to the changed field.

## Medium

### 4. A total over an incomplete column is shown as a finished number
**Did.** Entered Facility 2 with Commitment but no Outstanding.
**Screen said.** Outstanding total **$285,000**, directly beside the amber *Required* cell.
**Actually true.** The total is incomplete. The design rule is that an incomplete calculation is never shown as a number. The workbook does the same (`SUM`).
**Fix.** When any used row in the column has a required cell missing, show *Not calculated* in place of the total, in the engine and in the workbook formula alike. The parity test then covers it.

### 5. The released feed says the case is "Approved", not "Released"
**Did.** Opened `CFR-0001.feed.json` from the released files.
**Actually true.** `"status": "Approved"`. The files are written just before the release is recorded, so the record of the release describes the case as not yet released.
**Fix.** Write the outputs as the released state: add `released_by` and `released_at`, and set the status to Released.

### 6. The worklist's Subject column shows the scope, not the borrower
**Did.** Looked at the Cases list as the reviewer.
**Screen said.** Subject: *New money, secured (synthetic)*.
**Actually true.** That is the Scope field. The subject is taken from the first text field, and Borrower name comes later in the pack. With several cases open, the reviewer cannot tell them apart.
**Fix.** Let a pack name its subject field (for example `"subject": "borrower"`), masked if it is personal. Refuse a pack that names a subject field that does not exist.

### 7. Nothing tells the preparer that a review point is waiting
**Did.** Signed in as the preparer after the reviewer raised P1.
**Screen said.** The case is listed as *In review*, with no other sign.
**Actually true.** A point is open and waiting for the preparer. They find it only by opening the case and scrolling to Facilities.
**Fix.** Add an "Open points" count to the worklist, and list "Points waiting for your answer" at the top of the case.

### 8. The Tester field is not linked to who is signed in
**Did.** Chose the Tester from a list (A. Rivera, B. Chen, C. Okafor).
**Actually true.** The form can name B. Chen while the history log says A. Rivera did every entry. The two records of "who tested this" can disagree, and nothing compares them.
**Fix.** Either fill Tester from the signed-in person, or flag a disagreement on the release check.

## Low

### 9. An approver approves a tool from a text outline
The approver's only view is a list such as *"Field: Tester (list, required)"* and *"Rows entered, columns fixed"*. They cannot try the tool or open a sample case before approving. Approval is a click next to a fingerprint. **Fix:** a "Try it" case the approver can fill in without it entering the record.

### 10. One person wrote the tool and confirmed its limit
The designer is also the admin, so M. Okafor proposed the tool and confirmed the limit it is tested against. Packs need a second person; limits do not. **Fix:** decide whether limits need maker-checker too (this is a firm decision; see `DECISIONS.md`).

### 11. The limit history speaks code
The Versions table reads *"Credit file review: calc_dti confirmed at 0.4"*, while the row above it says *Highest debt-to-income, 40%*. **Fix:** use the limit's label and its displayed value.

### 12. Submit and Approve give no confirmation
Both land on the Check page silently, and only the Status chip changes. **Fix:** show a confirming banner, such as "Sent for review" or "Approved by D. Patel".

### 13. The Check page says "OK" twice on every line that passes
The Result is *OK* and the Detail is *OK*. **Fix:** leave Detail blank when the line passes.

### 14. A released case still says "Ready for review: Yes" and still offers drafts
**Fix:** after release, the strip should read *Released* and the Drafts section should be hidden.

### 15. Money inputs show no $ while totals do
Inputs show *285,000* and the total shows *$360,000*. This is cosmetic.

---

## Not walked

These are not claimed either way:
- the bank reconciliation and control test tools;
- a returned-and-resubmitted loop;
- marking a field *not applicable*, and excluding a row, through the screen (the service tests cover both);
- keyboard-only use beyond the Tab finding;
- a screen reader;
- phone width;
- printing the workpaper;
- a second person editing the same case at the same time.
