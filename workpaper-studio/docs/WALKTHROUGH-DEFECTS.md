# Walkthrough defects: credit file review, end to end

*Walked 2 November 2026 through the screens in Chromium (Playwright, because the Chrome extension the walk skill names is not available in this cloud session). The installation started empty. Every step went through a screen; no step used the API. The route is in `PROCEDURE-credit-review.md` and its rendered copy.*

**Denominator: 73 tests passing, including a parity test that recalculates 27 exported workbooks in LibreOffice. None of them caught any of the 15 defects below.** Twelve are about what a person sees or can do, and no test asserts those. Three are about what leaves the application (1, 2 and 5). Those three were tested, but only for what the tests already expected.

The job walked: a designer proposed the credit file review tool and an approver approved it. An admin confirmed the debt-to-income limit. A preparer completed a case and recorded an exception for a result above the limit, then submitted it. A reviewer raised a point and acknowledged the exception. The preparer answered the point. The reviewer cleared it, approved the case and released it, and the released files were opened.

Ranked by what each would cost a real client. Nothing was fixed during the walk, by rule. **Each defect's status after the fixes and the second walk is in the table at the end.**

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

---

## After the fixes: second walk, same day

The same scripts were walked again against an empty installation, and the procedure's screenshots now come from that second walk. **The suite now has 82 tests: the original 73 plus tests written for these defects.**

| # | Defect | Status | Pinned by |
|---|---|---|---|
| 1 | Released workbook carried the borrower's name | **Fixed.** Personal fields are masked in the workbook, as in the feed | `test_released_files_carry_no_personal_value_and_say_released` scans every released file |
| 2 | Workbook had no exceptions, points or sign-offs | **Fixed.** New *Exceptions and review* sheet | same test reads the sheet for each recorded item |
| 3 | Tab returned focus to the field just left | **Fixed.** Focus is restored to wherever the person is now, and text typed during the save is kept | seen in the browser (`walk/focus.js`): after Tab from Borrower the focus is on the next control; a value typed ahead survives the save. *No CI test: the suite has no browser* |
| 4 | Total over an incomplete column shown as a number | **Fixed.** Engine and workbook formula both read *Not calculated* | `test_a_total_over_a_required_gap_is_withheld`; the parity test now compares every total by defined name |
| 5 | Released feed said "Approved" | **Fixed.** Files are written as Released, with `released_by` and `released_at` | the released-files test |
| 6 | Subject showed the scope | **Fixed.** A pack names its `subject`; masked when personal; a dangling subject is refused | `test_worklist_subject_is_the_named_field_masked`, `test_subject_must_be_a_field` |
| 7 | Preparer not told a point was waiting | **Fixed.** "Open points" column with *waiting for your answer*, and a banner on the case linking to each point | `test_preparer_is_told_a_point_is_waiting` |
| 8 | Tester field not tied to the signed-in preparer | **Fixed.** A field can be declared `"is": "preparer"`; a disagreement blocks approval and says who is named and who did the work | `test_the_form_cannot_name_someone_else_as_preparer` |
| 9 | Approver approved from a text outline | **Fixed.** *Preview it filled in*: the pack's own example run by the same engine, nothing saved | `test_an_approver_can_see_a_tool_working_before_approving_it` |
| 10 | One person wrote the tool and confirmed its limit | **Open. Firm decision**: should limits need a second person? | — |
| 11 | Limit history spoke code | **Fixed.** *"Highest debt-to-income confirmed at 45%"* | `test_limit_history_speaks_the_screens_words` |
| 12 | No confirmation after actions | **Fixed.** A green *Done.* banner after every action | `test_actions_confirm_what_they_did` |
| 13 | "OK" twice on the check page | **Fixed** | seen on the second walk |
| 14 | Released case said "Ready for review" and offered drafts | **Fixed.** The strip shows readiness only while the case can be edited; drafts are hidden once released | seen on the second walk |
| 15 | Money inputs lacked $ | **Fixed** | seen on the second walk |

**Found on the second walk:**
- **The release check offered *Go to it* beside lines that already read OK.** Fixed.
- **Each field's small N/A button is a Tab stop of its own**, so tabbing through a form takes two presses per field. **Open, low.** The fix is a design choice: a keyboard shortcut, or one menu per section.
- **The released workbook's admin sheets printed across several pages**, with columns split. Found while checking the Review sheet. Fixed: every admin sheet now prints one page wide, and Review rows are tall enough for their text.

Still not walked: the same list as above.
