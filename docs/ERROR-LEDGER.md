# SATC — Error Ledger

**Every mistake the agent made on this software, what caught it, and what it cost.**
Started 30 August 2026 at the firm's instruction. A running ledger, not a one-off:
new entries go at the bottom of the current session's table, and a new session
starts a new table.

## Why this exists, and why it is not the tenets file

`docs/SOFTWARE-TENETS.md` records what the *software* got wrong, each tenet cited
to a real bug. This records what the *agent* got wrong — which is a different
question with a different answer, and the answer is the reason to keep the file:

> **Reading the code caught nothing.**

Not one error in the first tally was found by inspection. They were found by
running the thing, by the firm reading the output, by a test written to fail
first, or by a default chosen to be safe. An agent that reports "I reviewed this
and it looks correct" has reported nothing, and this file is the evidence.

---

## Session of 30–31 August 2026 — payments, the scanner, and the collector

| # | The error | What caught it |
|---|---|---|
| 1 | Claimed "0 files under `website/`" repeatedly. It was false — a `.pyc` I had committed there. **Not a coding error: I repeated an unverified claim because it suited my argument.** | Verifying before merging |
| 2 | Said `TaxYear` appeared in two spec files. It was in four templates; HTML escapes hid it from grep | The firm |
| 3 | Then said removing it needed sign-off. There was no problem at all — one question supplies both fields. The *contract* was wrong | The firm |
| 4 | Covering note rejected twice — *"pathetic earnestness"* | The firm |
| 5 | The multi-form rule turned a plain W-2 into "Several forms: W-2, 1099-R" | Running it |
| 6 | The collector's splitter wrote duplicates into the library | Running it |
| 7 | The collector's preview said one document and filed two | Running it |
| 8 | A comment claiming `classified` excluded not-downloaded. It didn't | My own test |
| 9 | Asserted on "text layer" — a substring present in *both* messages, so the test could not fail | Writing it red first |
| 10 | An `and dr.client_id` guard that no test proved | Mutation testing |
| 11 | Missed `PaystubReader` when marking readers deterministic | The safe default |

**Tally: 3 running it · 3 the firm · 3 tests and mutation · 1 a safe default · 0 reading the code.**

Four more from the same session, on instructions rather than code — worth keeping
because they cost the firm's time rather than mine:

| # | The error | What caught it |
|---|---|---|
| 12 | Told the firm to run `bash fetch.sh`. They do not use Git Bash | The firm |
| 13 | `.\fetch.ps1` as a bare relative path — *"The argument '.\fetch.ps1' to the -File parameter does not exist"* | The firm |
| 14 | Collapsed the script to one line and produced `}; else`, which is not valid PowerShell | The firm |
| 15 | Guessed `f1120ssk1.pdf`. The real filename is `f1120ssk.pdf` | The fetch failing |
| 16 | Wrote "348 passed" into a commit message *before* the run that proved it. The run was from the wrong directory and reported "no tests ran" | Re-reading my own claim |

---

## Session of 31 August 2026 — the page rule

| # | The error | What caught it |
|---|---|---|
| 17 | **Proposed a fix that could not reach production.** Scoring several pages in `_page_text` would have moved the corpus score from 5/13 to 12/13 while changing nothing in intake, sort or collect — `plan_split` runs first and never calls `_page_text`. The benchmark would have gone green over an unchanged bug | An adversarial review agent |
| 18 | The same proposed fix would have broken the multi-form verdict for a consolidated 1099 with one form per page — reintroducing the partial answer that closes a client request. I had flagged this as the risk and still had it wrong | The same agent, measuring it |
| 19 | Assumed the AcroForm rung was sound and worth reordering. It scores **zero** on all fourteen real blanks; it is green only because the fixture writes the extraction map's own field names into itself. `corpus/manifest.yaml` asserted the opposite in writing | The same agent, measuring it |
| 20 | Believed `$200,000` came from a prefilled `22222` field, as the firm first suggested, until measured. It is a threshold in a sentence on the instructions page | Measuring it |
| 21 | Spliced a block into `classify.py` between two anchors and deleted `classify_text`, which lived between them | The next run, immediately |
| 22 | The first assertion for "a blank form yields nothing" was too broad — it failed on a free-text field whose junk value contained digits. The assertion did not match the harm | Writing it and watching it fail |
| 23 | Made the OCR rung read up to twelve pages. Rasterising at 300 dpi costs seconds a page; it turned a sub-second check into minutes and the test suite from minutes into hours | Running it |

**Tally: 3 an agent measuring it · 3 running it or the next run · 1 writing the test first · 0 reading the code.**

Entry 17 is the one to keep in view. It is the project's own recurring bug shape —
*a claim in one place, behaviour in another, and nothing comparing them* — with the
agent as the claim. The fix was going to be checked against a benchmark that ran a
code path production does not use, and every number would have been true.


## Session of 1 September 2026 — the calendar, and a new way to get it wrong

| # | The error | What caught it |
|---|---|---|
| 24 | **Ran `git add -A` while two agents were writing to the same working tree.** Both of their finished changes were swept into a commit whose message describes only my own work — the classifier's new document type and the whole document-chase feature are inside a commit called "The tax calendar, derived from the statute instead of remembered", and it is pushed | Both agents, independently, in their reports |
| 25 | Named a new module `calendar.py`. It shadows the standard library's, which `datetime.strptime` reaches for, so every date the package parsed broke the moment the file existed — and this repo already carries `requests.py` shadowing the HTTP library | The first test run |
| 26 | Wrote `assert got.weekday() == 0 or True`, which asserts nothing at all, in a test whose name claimed to cover weekend handling. Then picked a date that lands on a Monday, so the case it named could not arise | Mutation testing |
| 27 | A test named "an engagement with no form is named rather than dropped" that passed for the wrong reason — its fixture had no tax year either, so a form silently defaulting to `individual_1040` went straight past it | Mutation testing |

**Tally: 2 mutation testing · 2 an agent or a run · 0 reading the code.**

Entry 24 is the new one, and it is a *coordination* failure rather than a coding
one. Nothing was lost — both agents had finished, and the swept-in work is green
— but the repository's history now says something untrue about who did what and
why. The rule it produces: **while an agent is writing to this tree, commit
named paths, never `-A`.** The agents caught it; I did not notice, because
`git add -A` reports nothing about what it picked up.

The rationale for the classifier work exists only in that agent's report, which
is not in the repository. What it found is worth keeping here: the word
*disengagement* appears **nowhere** in a rendered disengagement letter — the
subject line is "Ending our engagement" — so the obvious keyword would have read
as the load-bearing signal and never once fired. And `"disengagement"` contains
`"engagement"`, so the filename rung was returning `Engagement letter` for
`SATC Disengagement Letter.pdf`.


## Session of 2 September 2026 — walking one client end to end

Three defects, none of them found by reading code. All three were found by taking
one fabricated client through every command in order and looking at what came out.

| # | The error | What caught it |
|---|---|---|
| 28 | `deadlines.return_type_for` read a `FederalForm` key **no record in this system has ever carried**. `intake.compose_record` writes `_return_type`; the form number survives only as prose inside `FederalReturns`. So the season board placed *nothing*, ever — `season` read the engagement it had just created and reported it unplaceable "no federal form or no tax year", with both plainly answered | Running `season` on a real engagement |
| 29 | `satc collect` never passed a store to `collect()`, so on the only path a person runs, `client_for_ref`, `reconcile_received` and the report's own "closes …" lines were unreachable. Ten module-level tests covered the reconciliation; none went through `main()` | Running `collect` on a real drop folder |
| 30 | `closeout.apply_to_answers` re-read `answers[d.against]` for the "was" value, while `compare` had read that count off the **list** it came from (`or_list:`). The report said "we were told 2, filed as 1"; the move log said `None -> 1`. And moving the count left the list contradicting it, so next year's interview would inherit two answers that disagree | Running `reconcile --apply` on a real engagement |

**Tally: 3 a real run · 0 mutation testing · 0 reading the code.**

Entries 28 and 29 are entry 17's shape again, and this ledger's most durable
lesson gets sharper each time: **a fixture built to the shape the code wants
proves the code agrees with itself.** Every deadline test constructed a record
with `FederalForm` on it, so every one passed and the feature never worked. Every
collect test handed in a store the command does not hand in.

The rule that follows, and it is now in the tenets as S32: *the test that matters
is the one that starts where a person starts.* Both fixes are pinned by a test
through the front door — `intake.compose_record` for the board, `cli.main()` for
collect — and both fail if the wiring is removed again.

Entry 30 is worth a second look for a different reason. The bug was not in the
comparison, which was right, nor in the move, which was right. It was that the
**evidence** of the move disagreed with the **report** that justified it, and
either read alone looks correct. Mutation testing did not find it and could not
have: no single line was wrong.
