# Workpaper Studio: Credit File Review Procedure

| | |
|---|---|
| Document | Procedure for completing, reviewing and releasing a credit file review in Workpaper Studio |
| Effective date | [CONFIRM: effective date] |
| Owner | [CONFIRM: procedure owner] |
| Applies to | Credit file review, version 1.1 |
| Data | Synthetic. The debt-to-income (DTI) limit and method are fictional demonstrations. |

## Purpose

This procedure explains how a credit file review is set up, completed, reviewed and released in Workpaper Studio. It is written so that a third party can follow what each person did and why.

## Scope

It covers publishing the tool, confirming the organization's limit, completing a case, recording an exception for a result above the limit, review points, approval and release. Loading cases from the master database is covered in a separate procedure.

## Before you start

| System | Access needed |
|---|---|
| Workpaper Studio | A name set up on the Access screen |
| Tool designer | Propose tools |
| Tool approver | Approve tools, and not the person who proposed the tool |
| Admin | Set limits |
| Preparer | Start cases, Edit case entries, Submit for review |
| Reviewer | Approve cases and Release cases, and not the preparer of the case |

## Route

Tools → Settings → Workpaper → Analysis → Check → Review → Answer → Approve → Release

## Steps

### A. Sign in
*Everyone*

- Open Workpaper Studio.
- Select your name.

**Expected result.** Cases opens. The menu shows only what your access allows.

(i) ![Sign in](walkthrough/credit-review-2026-11-02/step-01-sign-in.png)

### B. Propose the tool
*Tool designer*

- Select **Tools**.
- On the Credit file review row, select **Propose for publishing**.

**Expected result.** Status reads *Proposed by M. Okafor · awaiting approval*.

**Note:** The person who proposes a tool cannot approve it, so no Approve button appears for them.

(i) ![Propose the tool](walkthrough/credit-review-2026-11-02/step-02-tools-not-proposed-zoom.png)
(ii) ![Propose the tool](walkthrough/credit-review-2026-11-02/step-03-proposed.png)

### C. Review and approve the tool
*Tool approver*

- Select the tool name to review its sections, fields and calculations.
- Select **Preview** to see the tool completed with example data.
- Return to **Tools** and select **Approve**.

**Expected result.** Status reads *Published*, with who proposed and who approved it. New cases use this version.

(i) ![Review and approve the tool](walkthrough/credit-review-2026-11-02/step-04b-approver-previews.png)
(ii) ![Review and approve the tool](walkthrough/credit-review-2026-11-02/step-05-approve-zoom.png)

### D. Confirm the limit
*Admin*

- Select **Settings**.
- Enter the organization's limit for Highest debt-to-income (40 for this demonstration).
- Select **Confirm**.

**Expected result.** Status reads *Confirmed by M. Okafor* with the date, and the change is added to Limit history.

**Note:** A result is not tested until its limit is confirmed. A case keeps the limits in force when it was started.

(i) ![Confirm the limit](walkthrough/credit-review-2026-11-02/step-07-settings-unconfirmed-zoom.png)
(ii) ![Confirm the limit](walkthrough/credit-review-2026-11-02/step-08-limit-confirmed.png)

### E. Start the case
*Preparer*

- On **Cases**, under New case, select **Credit file review**.

**Expected result.** The case opens with every required field highlighted. The status strip shows Ready for review: No and the number of missing items.

(i) ![Start the case](walkthrough/credit-review-2026-11-02/step-09-cases-start-zoom.png)
(ii) ![Start the case](walkthrough/credit-review-2026-11-02/step-10-new-case-zoom.png)

### F. Complete the details
*Preparer*

- Complete Tester details, Reviewer details, Scope and Borrower details.
- Use **N/A** beside a field only where it does not apply, and give the reason.

**Expected result.** Each panel shows *Complete* when its required fields are filled. Entries save when you leave each field.

**Note:** The Tester must be the person signed in. A different name stops the case at approval.

(i) ![Complete the details](walkthrough/credit-review-2026-11-02/step-11-details-filled-zoom.png)

### G. Enter the facilities
*Preparer*

- Enter each facility on its own row: type, rating, commitment and outstanding.
- Use **Exclude** to leave a row out, and give the reason.

**Expected result.** An incomplete row highlights its missing cell, and the column total reads *Not calculated* until it is complete.

(i) ![Enter the facilities](walkthrough/credit-review-2026-11-02/step-12-facility-row-incomplete-zoom.png)
(ii) ![Enter the facilities](walkthrough/credit-review-2026-11-02/step-13-facilities-complete-zoom.png)

### H. Answer the test questions
*Preparer*

- Rate each question. Open **Test steps** under a question for the steps to perform.
- Comment on every rating of Partially effective or Not effective.

**Expected result.** A rating of Partially effective or Not effective highlights the comment box until a comment is entered. A question that depends on another answer shows the condition under its number.

(i) ![Answer the test questions](walkthrough/credit-review-2026-11-02/step-14-question-needs-comment-zoom.png)

### I. Complete the supporting analysis
*Preparer*

- Select **Analysis**.
- Enter income sources, existing debts and the proposed monthly payment.

**Expected result.** Debt-to-income reads *Not calculated* until every input is entered, with each missing input listed. When complete, the ratio and its result against the limit are shown, and any zero amount is listed under Disclosures.

(i) ![Complete the supporting analysis](walkthrough/credit-review-2026-11-02/step-15-analysis-empty-zoom.png)
(ii) ![Complete the supporting analysis](walkthrough/credit-review-2026-11-02/step-16-dti-not-calculated-zoom.png)
(iii) ![Complete the supporting analysis](walkthrough/credit-review-2026-11-02/step-17-dti-above-limit-zoom.png)

### J. Record the exception
*Preparer*

- Where the result is *Above limit*, select a reason, enter an explanation, and select **Record exception**.

**Expected result.** The exception is listed under the result as *Pending acknowledgment*. The calculated result does not change.

(i) ![Record the exception](walkthrough/credit-review-2026-11-02/step-18-record-exception-zoom.png)
(ii) ![Record the exception](walkthrough/credit-review-2026-11-02/step-19-exception-recorded-zoom.png)

### K. Submit for review
*Preparer*

- Select **Submit for review**.
- If the release check lists missing items, select **Open** on each, complete it, and submit again.

**Expected result.** Status reads *In review* and the case's fields are locked for the preparer.

(i) ![Submit for review](walkthrough/credit-review-2026-11-02/step-20-submit-refused-zoom.png)
(ii) ![Submit for review](walkthrough/credit-review-2026-11-02/step-23-submitted.png)

### L. Raise review points
*Reviewer*

- Open the case from **For review**.
- Under the section concerned, enter the point and select **Raise point**.

**Expected result.** The point is listed as Open with the reviewer's name and time. The reviewer cannot change the preparer's entries.

(i) ![Raise review points](walkthrough/credit-review-2026-11-02/step-24-reviewer-home-zoom.png)
(ii) ![Raise review points](walkthrough/credit-review-2026-11-02/step-27-point-raised-zoom.png)

### M. Acknowledge the exception
*Reviewer*

- Select **Analysis**.
- Select **Acknowledge** on the exception.

**Expected result.** The exception reads *Acknowledged by D. Patel* with the time.

**Note:** Approval is refused while a point is open or an exception is unacknowledged, and the message lists each one.

(i) ![Acknowledge the exception](walkthrough/credit-review-2026-11-02/step-28-approve-refused-zoom.png)
(ii) ![Acknowledge the exception](walkthrough/credit-review-2026-11-02/step-29-acknowledge-zoom.png)

### N. Answer the review point
*Preparer*

- Open the case. Cases shows the open point under Open points.
- Enter the answer under the point and select **Answer**.

**Expected result.** The answer is listed under the point with the preparer's name and time.

(i) ![Answer the review point](walkthrough/credit-review-2026-11-02/step-30-preparer-home-zoom.png)
(ii) ![Answer the review point](walkthrough/credit-review-2026-11-02/step-31-answer-point-zoom.png)

### O. Clear, approve and release
*Reviewer*

- Select **Clear point**.
- Select **Approve**.
- Select **Release**.

**Expected result.** Status reads *Released*. Outputs lists the released files with their SHA-256 fingerprints: the data feed (JSON and CSV), the one-row answers file and the workbook.

(i) ![Clear, approve and release](walkthrough/credit-review-2026-11-02/step-32-point-cleared-zoom.png)
(ii) ![Clear, approve and release](walkthrough/credit-review-2026-11-02/step-35-outputs-zoom.png)

### P. Review the history
*Anyone with access to the case*

- Select **History**.

**Expected result.** Every entry and action is listed with who and when, newest first.

(i) ![Review the history](walkthrough/credit-review-2026-11-02/step-36-history.png)

## Best practices

- Comment on every Partially effective or Not effective rating, with enough detail for a third party to follow.
- Record an exception rather than changing entries to bring a result within its limit.
- Answer review points in the case, so the answer stays with the record.
