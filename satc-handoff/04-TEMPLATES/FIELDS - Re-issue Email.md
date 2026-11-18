# Re-issue email — required variables

Companion to `SATC Re-issue Email.html`.

The email sent when a return changes after it has gone to the client, with the revised returns attached. It says what changed, where the client now stands on each return, and what they still need to do: sign, and pay. It is the follow-up to the delivery letter.

It is an **email, not a PDF letter**. `python cli.py reissue` merges it and writes an unsent `.eml` (`X-Unsent: 1`, To left blank, HTML with a plain-text alternative, nothing attached). The preparer attaches the revised returns and sends it.

The firm, 13 Oct 2026: *"we should have a re-issue email template - it reminds them to sign and pay if they have not already and explains what we changed. some will have to be freehand but this is not - you can figure out what changed on results then you can summarize what we did"* and *"it should remind about the password as well"*.

## Syntax

| Syntax | Does |
|---|---|
| `<<FieldName>>` | Substitutes a value |
| `[[IF Flag]]` … `[[END IF]]` | Keeps or drops a block, or an inline run |
| `[[EACH List]]` … `[[END EACH]]` | Repeats what is between them, once per item |
| `<<Item.Field>>` | A field inside an EACH block — dotted |

**Fail the render on any unresolved `<<` or `[[`.** The merge engine cannot nest `[[IF]]` blocks, so each opening and each signing branch is its own flag; see the flags below.

---

## Fields

### Shared with other documents (1 field + 1 list)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<TaxYear>>` | Yes | 2026 | The bare year, from the same interview answer as `PeriodLabel`. Subject line and two sentences. |
| `[[EACH ReturnsDelivered]]` | List | one or more | The updated summary, in the same form as the delivery letter: one line per return. |
| `<<Item.Return>>` | Yes | Federal | As Drake's results table names it |
| `<<Item.Detail>>` | Yes | $520 refund, by direct deposit to the account ending 4417 | From `registry/results-wording.yaml`. Never typed. |

### Specific to this email (5 fields + 4 lists + 9 flags)

| Field | Required | Example | Notes |
|---|---|---|---|
| `<<ContactFirstName>>` | Yes | Daniel | The contact person's first name, from `TaxpayerName`. One person, never both spouses. |
| `<<IssueRaised>>` | When raised | the early-withdrawal penalty question | Follows "Thanks for catching" / "Thanks for asking about". Empty when the firm found the change. |
| `<<FreehandNote>>` | When freehand | — | The preparer's own explanation, for a re-issue the results comparison cannot describe. Printed under "What changed" as written. |
| `<<FilingDeadline>>` | Yes | October 15, 2027 | The date the returns are due; the extended date when an extension was filed. A real date. |
| `<<PreparerFirstName>>` | Yes | Arjun | The sign-off. From `firm-settings.yaml` (`preparer.first_name`). |
| `[[EACH ResultChanges]]` | List | zero or more — a re-issue may change only things that move no result, which `OtherChanges` carries | One item per return whose result moved, found by comparing the two summaries. |
| `<<Item.Return>>` | Yes | Federal | |
| `<<Item.Reason>>` | Yes | The 10% early-withdrawal penalty no longer applies, because the distribution qualifies for an exception. | The preparer's, one per changed return. The build refuses a changed return with no reason. |
| `<<Item.Before>>` + `<<Item.After>>` | Yes | $220 refund · $520 refund | Short form from `results-wording.yaml`. When only the method changed (a new account), the full summary lines. |
| `[[EACH OtherChanges]]` | List | zero or more — many re-issues move a result and change nothing else | Changes that move no result. |
| `<<Item.Label>>` | Yes | Form 8801 | |
| `<<Item.Detail>>` | Yes | The carryforward was entered from the wrong year. It's now correct, and it doesn't change this year's tax. | What was wrong, what it is now, whether it changes the tax. The preparer's. |
| `[[EACH ChecksDue]]` | List | zero or more — empty when nothing is owed, or every balance is withdrawn | One per balance paid by mailing a check. |
| `<<Item.Amount>>` | Yes | $85 | Pre-formatted. |
| `<<Item.PayTo>>` | Yes | RITA | Who the check is made out to. |
| `<<Item.DueDate>>` | Yes | October 15, 2027 | |
| `[[EACH WithdrawalsDue]]` | List | zero or more — empty unless a balance is paid by electronic withdrawal | One per balance Drake withdraws. |
| `<<Item.Account>>` | Yes | 4417 | Last four of the account it comes out of. |
| `[[IF RaisedAndRight]]` | Flag | Boolean | The client raised it and was right. |
| `[[IF RaisedAndNotRight]]` | Flag | Boolean | The client raised it and the earlier return had it right. |
| `[[IF NotRaised]]` | Flag | Boolean | The firm found the change. **Exactly one of these three is true**, derived from `client_raised` and `client_was_right`. |
| `[[IF AlsoUpdated]]` | Flag | Boolean | The client raised it and there is more than one change. |
| `[[IF FreehandExplanation]]` | Flag | Boolean | `FreehandNote` is set. |
| `[[IF ResignBoth]]` | Flag | Boolean | New signature needed; joint return. |
| `[[IF ResignOne]]` | Flag | Boolean | New signature needed; one signer. |
| `[[IF SignIfNotYetBoth]]` | Flag | Boolean | No new signature needed; joint return. |
| `[[IF SignIfNotYetOne]]` | Flag | Boolean | No new signature needed; one signer. **Exactly one of these four is true.** |

**Total: 6 fields + 5 repeating lists + 9 flags.**

Not variables: the password sentence, the "set the earlier copies aside" sentence, both headings, the summary's lead-in, the signing and payment wording, and the closing line.

---

## The re-sign rule — computed, never typed

IRS Pub 1345: taxpayers must sign a new e-file authorization (Form 8879) if, after they signed, the return changes by more than **$50** to total income or AGI, or by more than **$14** to total tax, federal income tax withheld, the refund or the amount owed.

`reissue.needs_new_signature` compares the earlier and new federal figures:

1. A change of more than $14 in the federal refund or amount owed decides it on its own: a new signature.
2. Otherwise every figure is needed — total income, AGI, total tax, withholding — because a missing one could be the one that crossed the line. **The build refuses and asks for them** rather than guessing.

The rule is federal. A state's own authorization rules are not evaluated here.

## Input — `python cli.py reissue`

```
python cli.py reissue --engagement 2027-0114 --changes samples/reissue-changes.json --out out/reissue.eml
```

`--changes` is a JSON file: the results summary as it went out (`before`), the summary now (`after`), the federal figures for each, a reason for each changed return, any other changes, and whether the client raised it. See `client-documents/samples/reissue-changes.json`. Each return is `{return, result: refund|balance|none, amount, method, account, pay_to, due_date}`, using Drake's results table.

---

## Example payload

Produced by `reissue.build()` from `samples/reissue-changes.json`; also `client-documents/samples/reissue-email.json`. Invented.

```json
{
  "TaxYear": "2026",
  "ContactFirstName": "Daniel",
  "IssueRaised": "the early-withdrawal penalty question",
  "FreehandNote": "",
  "FilingDeadline": "October 15, 2027",
  "PreparerFirstName": "Arjun",
  "ResultChanges": [
    { "Return": "Federal", "Reason": "The 10% early-withdrawal penalty no longer applies, because the distribution qualifies for an exception.", "Before": "$220 refund", "After": "$520 refund" }
  ],
  "OtherChanges": [
    { "Label": "Form 8801", "Detail": "The prior-year minimum tax credit carryforward was entered from the wrong year. It's now correct, and it doesn't change this year's tax." }
  ],
  "ReturnsDelivered": [
    { "Return": "Federal", "Detail": "$520 refund, by direct deposit to the account ending 4417" },
    { "Return": "Ohio", "Detail": "$640 refund, by direct deposit to the account ending 4417" },
    { "Return": "Solon", "Detail": "nothing due" },
    { "Return": "RITA", "Detail": "$85 balance due, by check" }
  ],
  "ChecksDue": [
    { "Amount": "$85", "PayTo": "RITA", "DueDate": "October 15, 2027" }
  ],
  "WithdrawalsDue": [],
  "RaisedAndRight": true,
  "RaisedAndNotRight": false,
  "NotRaised": false,
  "AlsoUpdated": true,
  "FreehandExplanation": false,
  "ResignBoth": true,
  "ResignOne": false,
  "SignIfNotYetBoth": false,
  "SignIfNotYetOne": false
}
```

The other states are exercised in `tests/test_reissue.py`: no new signature needed, one signer, not raised, raised and not right, freehand only, and a balance paid by withdrawal (`WithdrawalsDue` with an `Account`).

---

## Deliberately not here

1. **No attachments inside the email.** The preparer attaches the revised returns; the email refers to them.
2. **No password.** It says the password is unchanged and never carries any part of it.
3. **No fee.** The invoice owns it.
4. **No masthead or legal footer.** An email from a person, signed with a first name, like the firm's other client emails.
5. **No auto-send.** The firm opened the door to sending *certain* emails automatically after the first live run; which ones is the firm's decision, and this one is not built to send.

## Notes for the software

1. `ResultChanges`, `ReturnsDelivered`, `ChecksDue` and `WithdrawalsDue` are built from the two results summaries. **A human never types a tax figure into this email.**
2. Every result phrase comes from `registry/results-wording.yaml`; change a word there and every email follows.
3. The build refuses rather than guessing: a changed return with no reason, a balance with no payee or due date, a deposit with no account, a re-sign decision the figures cannot settle, or nothing changed at all.
4. Write the `.eml` with CRLF line endings and base64 bodies. A quoted-printable file with LF endings was mis-read by Outlook on 13 Oct 2026.
