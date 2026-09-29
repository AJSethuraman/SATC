# PocketBook on public loan data: the rehearsal of 29 Sep 2026

PocketBook was run end to end, headlessly, through the workbook route the analyst uses (Set up, answers written
into Control and Columns, Run), on three public loan files: the SBA's 7(a) FOIA file for FY2000–FY2009 (604,573 loans
with a known outcome), `SBAnational.csv` from Li, Mickel & Taylor (2018) (897,167), and LendingClub's 36-month
loans issued 2008–2011 (30,931). Everything below is an aggregate. No loan-level row is in git. The data, the
extracts, the workbooks and each run's timings sit in `C:\Users\ajish\SATC-evidence\public-loans-2026-09-29\`,
which can be purged (its `README.md` gives the sources, licences and SHA-256s).

Tools, all in this branch:

- `tools/public_extract.py`: raw file to extract, plus a manifest of every filter and derived column. The manifest
  also carries the term check (below) and labels each column not known when the loan is booked.
- `tools/rehearse.py`: the headless workbook route, with timings, peak memory and a workbook check.
- `tools/rehearsal_effects.py`: margins and pocket verdicts read out of a written workbook.
- `tools/rehearsal_answer_key.py`: the answer key, in plain Python without PocketBook.
- `tools/rehearsal_timing.py`: where a bleed Run's time goes.

The answers given to every workbook, and the pre-registered pre-spec, are in `docs/rehearsal-public-data-2026-09/`.

**This report was corrected after two reviews on 29 Sep 2026.** The largest correction is the first section. Every
other change is listed in section 6.

## 0. Read this first: on both SBA files the term depends on the outcome

The term as recorded does not behave like a fact fixed when the loan was made. Most paid loans' terms are whole
years (a multiple of 12 months). Most charged-off loans' terms are not (counted from the extracts,
`tools/rehearsal_answer_key.py --review`, and now in each manifest's `term_check`):

| File | Paid: terms that are whole years | Charged off: terms that are whole years | At exactly 84 months |
|---|---|---|---|
| SBAnational | 86.6% of 739,609 | 10.6% of 157,558 | 226,972 paid, 1,948 charged off |
| SBA FOIA FY2000–09 | 82.0% of 460,222 | 8.9% of 144,351 | 176,438 paid, 957 charged off (0.54% bad, against 23.9% for the file) |

On the FOIA file the gap holds inside every processing method, every approval year and both revolver statuses (the
second review, reading the raw file), so loan mix does not explain it. Charged-off loans' terms run nearly flat from
39 to 64 months, at about 1,800 to 2,500 loans for each month of term on each file. The builder's own test, whether
a charged-off loan's term equals its months to charge-off, found only 0.8%. It was too narrow to see this, and the
builder's conclusion from it ("the simple leakage test is negative") was wrong.

What it means:

- Everything cut on the term is **circular** on these files: `REAL_ESTATE` (a term of 240 months or more),
  `RECESSION` (the disbursement date plus the term), the Term and TermInMonths bands, the "term under 60 months"
  result on the confirmatory test, and scouting's choice of TermInMonths with AUC 0.93 built and 0.92 unseen.
- PocketBook reproduces the paper's arithmetic on these columns, and the paper's real-estate and recession effects
  inherit the same dependence. Those rows are **not** evidence of a known effect surfacing.
- Whether SBA's recorded term is the term approved is not known.

The converter now counts this on every extract it writes (`term_check` in the manifest) and labels the term, and the
two columns built from it, as depending on the outcome. The PocketBook runs were **not** redone without the term:
the pre-spec and scouting results that use it stand only as software exercises (decision 7).

## 1. Findings

### Defects found and fixed (3), each with a regression test on a tiny synthetic book

All three tests are in `tests/test_rehearsal_2026_09_29.py`, which holds 9 tests in all. Each failed before its fix.
Each fix has a planted bug in `tools/mutation_check.py`, and each of those 4 planted bugs was run alone and caught.

1. **A category limit that isn't on the launcher's list could not be run** (`control.write_choices`). Take
   `Choices(many_values=60)`, which State needs (51 values and a blank). The 60 was written into Control's pick cell,
   where only a listed option is read.
   - Set up used 60.
   - The Run then refused with *"Control!C43: 60 is not an option"*. That row is the launcher's own, and the
     analyst can't edit it.
   - Reading the block back (Set up again, or the launcher) took the usual 50, with no message.

   Now a limit that isn't on the list goes in the setting's own-value cell (D). Control already checks that cell as a
   whole number from 2 to 1,000. The Tk launcher offers only the listed values, so the window never hit this.
   `set_up(choices=...)` did.
2. **The confirmatory test's conditional likelihood did not scale** (`kgroups.pocket_terms`).
   - **What happened.** The pre-registered test on the FOIA file held BusinessType fixed. Each set of loans is tested
     on its own, so a pocket held up to 333,786 loans (the whole development range, with one BusinessType). The run
     was stopped after 10.5 minutes of Run (914 s of CPU), still inside its first conditional fit. py-spy put it in
     `np.convolve`, called from `_prod`.
   - **The measured cost.** One evaluation of a 217,800-loan pocket took **191 s** (202.7 s and 220.0 s when the two
     reviewers reverted the fix). A 79,200-loan pocket took 23.8 s, and a 19,800-loan pocket 0.08 s (both measured
     once, by the builder). A fit needs several evaluations per pocket per Newton step.
   - **Why.** The code multiplied every group's polynomial out in full, although a tilted binomial's coefficients
     underflow to exactly 0.0 away from its middle, and only the coefficient at *m* is ever read.
   - **The fix.** Each polynomial now carries only its nonzero coefficients, with an offset. A coefficient that is read
     once is now one dot product, not a whole convolution. No approximation is made.
   - **Results.** The same 217,800-loan pocket now takes **0.25 s**. The pre-spec Run on the full file took 128.2 s
     for the builder and 89.7 s on the final code. The old implementation is kept in the test as the reference, on
     four pockets (a group at its boundary, an empty group, and *b* at zero and away from it). The test holds the
     log-likelihood equal to 1e-12, the gradient to 1e-10 and the Hessian to 1e-9 (relative). On the 217,800-loan
     pocket a reviewer measured a log-likelihood difference of 0.0, gradient 2.7e-12 and Hessian 2.5e-11 relative.
   - **A second test since review.** The planted bug that multiplies every coefficient out again gives the same
     numbers, so only a 20-second limit caught it, with little room (34–35 s on this machine). A new test spies on
     the polynomials a pocket multiplies and requires that none carries an underflowed zero at either end. It catches
     that planted bug in half a second, on any machine.
3. **scikit-learn that is installed but won't load crashed the Run** (`scout.run`).
   - **What happened.** On this machine, Windows' Smart App Control blocked scikit-learn's newly installed compiled
     files at first load: *"DLL load failed while importing _loss: An Application Control policy has blocked this
     file."* The Code Integrity log shows 6 blocks (each a 3033/3077 event pair), the last at 09:07.
   - **It is not tied to a version.** The builder moved to scikit-learn 1.5.2 because 1.9.1 was blocked. A reviewer
     then found 1.9.1 loading in a fresh environment by 09:34, with the whole suite and a scouting rerun passing on
     it. The final runs here used a fresh install of 1.9.1, which loaded at its first import (10:44) with no block
     event. The block is Smart App Control's reputation check on newly written files, and it cleared.
   - **Why it crashed.** `scout.missing()` looks for the add-on without loading it (deps.py's rule), so the add-on
     read as installed. A scouting Run then died on the forest's import.
   - **The fix.** `scout.run` now loads `sklearn.ensemble` and `sklearn.metrics` before finding anything. A failed
     load becomes the refusal in words that a missing add-on already gets, and a saved shortlist still confirms.

### Also fixed: the suite and its checkers

The full suite on this machine first read **2 failed, 703 passed, 115 skipped**. Neither failure was in PocketBook's
product, and both are fixed in the tests and the checker:

- **The mutation checker read in the platform's encoding.** `tools/mutation_check.py` opened files that way:
  cp1252 on Windows, UTF-8 on CI's Linux. Four planted bugs whose line holds a character outside cp1252 were never
  found here, so a Windows run of the checker died on the first of them. `tests/test_mutation_tool.py` read the same
  way. Both now read and write UTF-8. A test parses them and requires every text open to name its encoding; a
  planted file shows that check can fail.
- **The checklist test needed a symlink.** `tests/test_bank_checklist.py` symlinked `src`, which Windows refuses
  without Developer Mode (WinError 1314). It now copies `src` when the link is refused, so it runs here. Its printed
  paths and MD5s matched.

Found in review and fixed after the builder's report:

- **The mutation checker counted any failed pytest run as a catch.** Any exit but 0 or 5 read CAUGHT. So a machine
  whose temp folder pytest can't write (a reviewer hit WinError 5), where every `tmp_path` test ERRORS, reported
  planted bugs as caught that no test had failed on. The rule was older than this branch. Now a planted bug is
  CAUGHT only when a test fails. Errors with no failure are settled by running the same tests on the file without
  the bug: caught if those pass, NOT CHECKED if they error too. A run that is killed, matches nothing or only skips
  reads NOT CHECKED. Six new tests; three of them fail on the old rule. The builder's and a reviewer's runs of 76
  planted bugs were re-read: every one of the 68 lines reading CAUGHT reads "*N* failed", none only errors.
- **`--files`** on the checker puts back only the planted bugs in the files named, and refuses a file with none. It
  replaces the scratch script the 76-bug run used.
- **`tools/rehearsal_effects.py` counted a pocket alone in its band like the others.** Such a pocket has no rest of
  band, so it is judged against the book. Its count now says so ("worse 3 (1 alone in its band, so against the
  book)").

### The suite on the final code

On the final code (this branch with origin/main at ab7ddde0 merged in), in a fresh environment built with CI's recipe
(`pip install -e ".[test,scout]"`, scikit-learn 1.9.1): **1 failed, 734 passed, 115 skipped, of 850**. All 115 skips
are tests that need LibreOffice.

The one failure is not this branch's. `test_choose_tests_window_draws_the_rows_in_order_with_a_quiet_gap_and_no_every_measure`
(`tests/test_firm_answers_2026_09_27.py`) came with main's #405. It needs a display, so CI's Linux job runs it under
xvfb. On this Windows machine it fails the same way on main's own code, taken with `git archive origin/main`
(2 of 2 runs): at 1180 × 628, the size the window opens at on a 1366 × 768 laptop, the Choose tests table is 215
pixels high and its last row ends at 248, so the ten rows do not fit without scrolling. That may matter on the
bank's laptop. It is recorded for main's launcher work and is not changed here.

### Open: decisions for the firm, recorded and not decided

1. **SBA's RANR.** The extract sets revenue to zero for every loan (`RANR = −GCO`; the converter refuses to run until
   `--ranr neg-gco` is named). That zero is an invented value. Consequences:
   - Contribution before losses is 0 for every loan. Both SBA bleed Runs said *"Nothing is worse for Contribution
     before losses"*, which is correct and empty.
   - Profit after losses is the charge-off rate turned over: its worst pocket is the GCO worst pocket on both SBA
     files.
   - The profit tabs on the SBA workbooks are **not evidence**, and the workbooks carry no mark saying so. Only this
     report and the manifest do.

   The FOIA file does carry `InitialInterestRate` (the rate at approval), on 36,633 of 41,288 FY2009 rows. An interest
   proxy from it (`GrossApproval × rate × years × ½ − GCO`, FY2009 and later only) was not built.
2. **LendingClub's licence, and figures already public.** The CC0 labels on the Hugging Face and Kaggle copies are
   the re-uploaders' (the Hugging Face README, https://huggingface.co/datasets/codesignal/lending-club-loan-accepted,
   reads in full `license: cc0-1.0`). LendingClub's own terms are unknown. The builder called this "internal
   rehearsal only", but it is not: the repository is **public**, and this report and BACKLOG §6d, carrying
   LendingClub-derived rates, were pushed on this branch before the firm answered. Keep them, or remove them? Removing
   them from the branch's history would need a force-push, which this session has not done.
3. **Reading the live cells.** The verdicts on every result tab are Excel formulas. Nothing here calculated them:
   LibreOffice is not installed, and Excel was not opened, because the recon brief records the firm saying *no Excel
   check until they say so*. The two ways to read them are installing LibreOffice (which the tests assume) or opening
   a copy in Excel through COM.
4. **The confirmatory test's "Excess $" rewards big loans.** `confirmatory.excess` compares a group's GCO dollars on
   the holdout with the group's share of the holdout's **loans**. When the candidate is loan size, the large-loan
   group always carries excess dollars, even when it loses less:
   - On the FOIA pre-spec, GrossApproval 350,000 and up has an odds ratio of 0.79 against 50,000–149,999 (better),
     and reads **+$6.06 billion** excess.
   - The small-loan groups read −$2.9 billion and −$2.4 billion.
   - An alternative is to compare against the share of **booked dollars**.

   Which share is meant is the firm's call. The code does what its docstring says.
5. **Equal-loan bands next to a lump of equal values leave a sliver band.** TermInMonths, 5 bands "each holding about
   the same number of loans", came out as 0–48, 49–81, **82–83**, 84–119 and 120 and up. The 82–83 band holds 6,351
   loans; the others hold about 120,000 each. The cause:
   - The 40% quantile lands at 82, just below 84 months, which alone holds 29% of loans.
   - `cut_edges` only allows for *fewer* bands than asked.

   The analyst can type edges on Columns. Whether a sliver should be merged is a design choice.
6. **Application control on the bank's machine.** Defect 3 now says a blocked add-on in words, but a blocked add-on
   still can't scout. On this machine the block was Smart App Control's check of newly installed files, it cleared
   within the morning, and it was not tied to a scikit-learn version. The question for the bank is whether its
   machine runs an application-control policy, and whether IT will allow the add-on wheels made by
   `tools/bank_kit.py --add-ons`. If not, the firm confirms saved shortlists only.
7. **The SBA term.** Section 0. Rerun the pre-spec and scouting without the term (a new pre-spec, written knowing this
   file), or leave them standing as software exercises only, as this report does?

### Observations that are not defects

- **A band-level effect never makes a pocket worse when pockets are judged against their band.** This is Control's
  *The rest of its band* (OC-44), and it is by design. Loan size is the paper's Table 4 effect. It shows on the band
  margins and on Grids' *against the book* block, and it is flagged on no pocket.
- **The "confound in a published effect" is withdrawn.** The builder reported that, inside Term bands, recession loans
  charge off less in 3 of 4 bands, so the paper's recession effect is "largely term mix". Both columns are built from
  the term, which depends on the outcome (section 0), and the band that went the other way was not quoted: under 60
  months, 71.70% against 54.09% (26,614 recession loans, 37% of them). The comparison is **not interpretable**. A
  recession measure known when the loan is made, such as the approval vintage, would be needed.
- **Columns recorded after booking went into the extracts.** Each is now labelled in the manifest (`after_booking`):
  - SBAnational's `DisbursementGross`, used as the booked amount and the loan-size bands, is the amount disbursed.
    On revolving lines it passes the approved amount for 83.9% of charged-off loans against 66.5% of paid ones; on
    term loans, 4.9% against 0.3%. It pushes against the smaller-loans result, so it does not make that result.
  - FOIA's `SoldSecMrktInd` is set when the loan is sold on the secondary market (data dictionary). It was passed
    through as a category but never used as a segment, so no result is affected.
- **PocketBook's servicing guard, by name, was wrong both ways here.** Its "status" hint read `RevolverStatus` (term
  loan or revolver, known when the loan is made) as servicing: the pre-spec's *what ran* shows
  `RevolverStatus: servicing`, on the final code too. It did not flag `SoldSecMrktInd`. Neither changed a result
  here, and the guard is not changed on this branch.

### Mapping caveats: every derived column is a rehearsal approximation, with the manifest saying so

- **SBA FOIA.** The file has no loan number, so `ROW_KEY` is made from the file and its row.
- **Booked amount.** It is `GrossApproval`: approved, not drawn. That overstates a revolving line.
- **Kept loans.** Only P I F and CHGOFF are kept. Left out: 82,276 CANCLD (never disbursed) and 3,484 EXEMPT
  (disbursed and still open, status withheld). The data writes `P I F`; its dictionary says `PIF`.
- **Derived columns.** `NAICS2` is the first two digits. `REAL_ESTATE` is a term of 240 months or more, the paper's
  proxy. `RECESSION` is the paper's SAS, as written. Both depend on the term (section 0).
- **SBAnational.** 1,997 loans with no MIS_Status are left out. `APPROVAL_DATE` is the two-digit year settled by
  ApprovalFY; 70 dates it can't settle are blank and counted. NAICS 0 is blank (201,667 loans), not an industry.
- **LendingClub.**
  - `GCO_APPROX` is funded minus principal received, on charged-off loans.
  - `RANR_APPROX` is total paid minus funded minus the collection fee. That is before LendingClub's servicing fee and
    any cost of funds, so it overstates a bank's RANR.
  - `ISSUE_DATE` puts every loan on the 1st of its month.
  - The subset keeps 2,086 "Does not meet the credit policy" loans. The paper's N is 24,449 and this subset's is
    30,931 (28,845 without those loans), so the LendingClub comparison is directional, not exact. The difference is
    **not explained**.
- **Populations.** SBA FOIA FY2000–09 includes vintages whose outcomes were still open for years (FY2009 loans run to
  2019 and beyond). Keeping only terminal loans tilts late vintages toward early outcomes, which is the paper's own
  warning.

## 2. Known effects: what PocketBook surfaced

"Worse" and "better" mean a pocket (band × segment) reads 1.25× or more, or 0.8× or less, against the rest of its
band, at 95% after Benjamini-Hochberg. The 1.25×, 0.8× and 95% are the answers given (`answers-*.yaml`). The
Benjamini-Hochberg allowance is not in any answers file: it is Control's recommended preset, left as it was (each
Run's *what ran* records `many_tests: bh`).

The workbook's own verdicts are formulas and were not calculated. These counts apply the same rule in Python to the
multiples and p-values the Run stored on `_pockets` (`tools/rehearsal_effects.py`). A pocket alone in its band has no
rest of band and is judged against the book; the counts below name where that happens. The rates are the Run's own
margins, from `_views`.

The comparison figures are the answer key (`tools/rehearsal_answer_key.py`, saved as `extracts/answer-key.txt`). It
is plain Python without PocketBook, but it reads the converter's **extracts**, so it is not independent of the
converter. A reviewer's key read from the raw files, without the converter, reproduced every figure checked.

### SBAnational: the paper's own file

The industry rates and the recession-Y rate tie out. Other rates differ from the paper by up to 0.35 points (the
paper's Table 5 covers 877,428 loans and this file 897,167; not explained).

| Effect (paper) | Paper | PocketBook (margin) | Answer key | Pockets | Verdict |
|---|---|---|---|---|---|
| Industry, 2-digit NAICS (Table 3) | 21: 8, 11: 9, 55: 10, 62: 10 … 52: 28, 53: 29 | 21: 8.48, 11: 9.03, 55: 10.16, 62: 10.38 … 52: 28.43, 53: 28.73 | same to 0.01 pt | on the loan-size grid: 53 worse in 4 of 5 bands, 48 and 51 in 4, 52 in 3 (and better in 1); 62 better in 5, 11 and 21 in 4; 55 (256 loans) none flagged | **Hit.** All 24 codes round to Table 3 |
| Backed by real estate, term ≥ 240 (Table 5) | 1.64% vs 21.16% | 1.63% vs 20.81% | same | on the loan-size grid: Y better in 5 of 5, N worse in 5 of 5 | **Arithmetic reproduced, not evidence.** Built from the term (section 0) |
| "Active in" the Great Recession (§4.1.6) | 31.21% vs 16.63% | 31.21% vs 16.38% | same | on the loan-size grid: Y worse in 5 of 5 | **Arithmetic reproduced, not evidence.** Built from the term |
| Smaller loans default more (Table 4) | median $61,962.5 vs $100,000 | bands $4,000–34,999: 25.32% … $300,000+: 9.26%, monotone | medians $61,500 vs $100,000 | a band effect: no pocket flagged against its band, by design | **Hit** on the margins. The bands are cut on the amount disbursed (section 1) |
| New vs existing, "relatively negligible" | 18.98% vs 17.36% | 18.75% vs 17.11% (1.10×) | same | on the loan-size grid: new worse in 2 of 5, better in 1 | **Hit** at the book: under the line. A few pockets clear 1.25× |
| Florida high (text) | — | FL 27.37%, the highest state | same | on the loan-size grid: worse in 5 of 5 | **Hit** |

The Term grids are left out of this table: the term depends on the outcome. For the record, a pocket alone in its
band is judged against the book. On `Term x REAL_ESTATE`, N reads worse in 3 bands and better in 1, but in 3 of those
4 bands N is the whole band, so only one of them is a comparison with the rest of a band.

### SBA 7(a) FOIA FY2000–FY2009, as of 30 Jun 2026 (same direction and ordering expected, not the same figures)

- **Industry: hit.** 53 is the highest industry of any size (30.78%). 21 (13.06%), 62 (14.39%) and 11 (17.39%) are
  the lowest, and 62 reads better in 5 of 5 loan-size bands. The middle order moves (48 at 27.84%, 51 at 26.32%), and
  fewer pockets are flagged than on SBAnational (53 worse in 2 of 5).
- **Real estate and recession: arithmetic reproduced, not evidence** (section 0). Y 5.62% against N 25.61%; Y 38.15%
  against N 22.36%.
- **Loan size: hit, flatter.** $55–23,999: 26.47%; $24,000–49,999: 27.23%; $50,000–99,999: 25.47%;
  $100,000–239,999: 20.60%; $240,000 and up: 19.83%.
- **Florida: hit.** 34.98%, second to NV (34.99%) among states with more than 11 loans.
- **Vintage.** FY2007 37.00%, FY2006 32.34%, FY2008 30.64%, against 13.48–14.91% for FY2000–02. The recon brief had
  "the 2006–2008 vintages lose more" as an *unverified* hypothesis with no primary source. PocketBook shows it here
  (worse in 4–5 of 5 loan-size bands), and it stays an observation, not a tie-out.
- **BusinessAge.** The FOIA file's categories are not the paper's NewExist. 293,130 loans (48%) read "Less than 4
  years old but at least 3", which looks like a coding default. It is not compared.

**The pre-registered confirmatory test** (`prespec-sba-foia-loan-size-term.yaml`) was committed at 727b5ea7
(06:32:07) before any PocketBook run on this file (the first began at 06:45:28). Record reads *"Follows pre-spec …
(commit 727b5ea75971)"*, with one touch of the holdout. Development was FY2000–05 (333,786 loans), holdout FY2006–09
(270,787). The pre-spec states five expected directions, and all five are reported here. "Holds up" is the workbook's
rule (the holdout's odds ratio on the same side of 1 as development's, and significant after the allowance), applied
in Python to the stored numbers:

| Pre-registered | Development | Holdout | BusinessType held fixed | Result |
|---|---|---|---|---|
| GrossApproval group 0 (up to 24,999) worse | 1.12× | 0.99× (p 0.45) | 0.95× | **Miss** |
| GrossApproval group 1 (25,000–49,999) worse | 1.02× (p 0.19) | 1.09× (p 4.9e-15) | 1.07× | **Holds up on the workbook's rule**, but under the 1.25× worse line: worse, not by much |
| GrossApproval group 3 (150,000–349,999) better | 0.79× | 0.72× | 0.73× | **Hit** |
| GrossApproval group 4 (350,000 and up) better | 0.77× | 0.79× | 0.81× | **Hit** |
| TermInMonths group 4 (240 and up) far better | 0.75× | 1.38× | 1.40× | **Miss**, and the term depends on the outcome |

All against 50,000–149,999 for loan size and 84–119 months for term.

- **Not pre-registered: the other term groups.** The builder reported "term under 60 months: hit (23×)". The pre-spec
  states no expectation for it. On the holdout 0–59 months reads 23.2× and 60–83 reads 7.2×; both are cut on the term,
  which depends on the outcome, so neither is evidence.
- **Why the 240-month group missed is not settled.** The builder wrote "my hypotheses failing, not PocketBook". Two
  other causes are open:
  - Censoring. 1,766 EXEMPT loans (disbursed, still open, left out of the extract) are in the holdout's 240-month
    group, against 14,562 kept. If every one performed, its 12.10% would read 10.79%.
  - The term itself: 90% of the charged-off terms in that group are not whole years (1,593 of 1,762; the second
    review had 89%).

  From the loans: 12.10% against 9.06% for FY2006–09 approvals, and 3.13% against 4.13% for FY2000–05. Per booked
  dollar the 240-month loans still lost less (8.39% against 21.16%).

**Scouting**, on the same file with the cutoff "the month start nearest 70% of the loans", **stands as a software
exercise only**: its main proposal is the term.
- **Split.** It gave 2006-11-01: 426,772 development loans, with 177,801 held back and not read while finding.
- **Proposed.** TermInMonths (importance 0.44; bins 12, 14, 24, 48, 60) and GrossApproval (0.035; bin 254,000).
- **Not proposed.** JobsSupported (0.004, "no bend to cut at"). The noise floor was 0.0035.
- **Pre-spec.** It wrote the pre-spec, then confirmed on the held-back loans. 254,000 and up reads 0.79× (0.82× held
  fixed). The term groups read up to 14.9×, and the AUC was 0.93 built and 0.92 unseen; with the term depending on
  the outcome, none of that is evidence.
- The builder ran scouting on scikit-learn 1.5.2, a reviewer and the final run on 1.9.1. All three wrote the same
  pre-spec, byte for byte, with the same AUCs.

### LendingClub, 36-month loans issued 2008–2011 (directional: the population differs from the paper's)

The pocket counts are from the loan-size grid (`funded_amnt` × the segment) unless the row says otherwise.

| Effect (Serrano-Cinca et al. 2015) | Paper | PocketBook (margin) | Pockets | Verdict |
|---|---|---|---|---|
| Grade, monotone | A 5.6 … G 38.2 | A 5.89, B 10.96, C 15.32, D 19.17, E 21.98, F 29.36, G 33.51 | A better in 5 of 5; C–G worse in 2–5 of 5 each | **Hit** |
| Purpose | small business 21.9 highest; wedding 7.2, credit card 7.6, car 7.9 lowest | small business 23.31 highest; credit card 8.50, wedding 8.60, car 8.76 (major purchase 8.26) | small business worse in 4 of 5; credit card better in 5 of 5 | **Hit** |
| Housing | rent 11.7, mortgage 9.9 (significant) | rent 12.93, own 11.48, mortgage 10.94 | none on the loan-size grid (1.18× at the book is under the 1.25× line). Across all seven grids, rent reads worse in 5 pockets (dti 2, revol_util 2, int_rate 1) and mortgage better in 6 | **Hit in direction**; flagged on some grids, not on loan size |
| DTI, revolving utilisation, inquiries, income, rate (means) | higher for defaults (income lower) | every banded margin moves that way: DTI 10.16→13.74; utilisation 8.38→16.46; inquiries 9.23→16.68; income 15.87→8.97; rate 4.96→19.79 | band effects, as above | **Hit** |
| Nulls: loan amount, employment length | not significant | amount 10.70–13.25, no order; employment 10.21–12.52 (blank 19.76) | none, but blank employment worse in 3 of 5 | **Hit** |

**No known effect was missed because of a PocketBook defect.** What did not come out as expected:

- two of the five pre-registered directions (the smallest loans, and 240 months and up), for reasons not settled;
- every SBA finding cut on the term, which cannot be read either way (section 0).

## 3. Performance

This machine: 12 cores, 32 GB, Windows 11, Python 3.12, numpy 2.5.3. It was shared with the Forge's live services
and with the sessions' own reads. Peak memory is the largest resident set sampled every 0.2 s, for the main process
and for it plus the shuffle test's workers.

**The times are single samples on a shared machine, and they move a lot.** The same five Runs were timed three times:
by the builder, by a reviewer at the builder's last commit, and on the final code (after main was merged in, which
changed Set up's outcome handling and nothing in the engine). Set up and Run, in seconds:

| Run | Loans | What ran | Builder | Reviewer | Final | Peak, main / with workers (final) |
|---|---|---|---|---|---|---|
| SBAnational, bleed | 897,167 | 2 bands × 7 segments = 14 grids, 10,000 shuffles | 68.4 / 826.8 | 103.7 / 877.9 | 69.3 / 825.9 | 2.72 / 3.88 GB |
| SBA FOIA, bleed | 604,573 | 2 × 8 = 16 grids, 10,000 shuffles | 53.6 / 547.0 | 89.7 / 669.2 | 55.9 / 537.5 | 2.09 / 3.13 GB |
| LendingClub, bleed | 30,931 | 7 × 5 = 35 grids, 10,000 shuffles | 3.4 / 34.5 | 4.3 / 47.8 | 3.5 / 36.2 | 0.39 / 1.25 GB |
| SBA FOIA, pre-spec | 604,573 | 2 inputs, BusinessType held fixed | 76.8 / 128.2 | 84.5 / 143.8 | 57.2 / 89.7 | 1.09 / 1.09 GB |
| SBA FOIA, scouting | 604,573 | 3 candidates, BusinessType held fixed | 81.1 / 622.9 | 54.4 / 512.9 | 55.7 / 512.8 | 4.24 / 4.24 GB |

Across the three samples of each Run, the slowest took up to 1.67 times the fastest for Set up and up to 1.60
times for Run, so read any one time as rough. Peak memory reproduced to within 0.03 GB each time. Before fix 2, the pre-spec Run was stopped after
10.5 minutes in its first fit, at 0.85 GB.

**Where a bleed Run's time goes.** On the FOIA file, measured once by the builder with the Run's recorded cube
(`tools/rehearsal_timing.py`; not rerun on the final code, whose engine is unchanged):
- reading the extract: 2.5 s;
- the pure-Python pass over 16 grids without the shuffle test (as `book.run` builds its first pass): 86.4 s;
- the same with the 10,000 shuffles: 608.1 s. So about 520 s is the shuffle test for the dollar rates, spread over
  8 workers.

That separate measurement ran longer than the builder's whole Run had (547.0 s), another sign of how much the times
move here. The shuffle test's cost is the README's own extrapolation borne out (about 3 minutes at 200,000 loans, so
about 9 at 600,000). It is not a defect: Control's *shuffles* sets it (100 to 1,000,000; 10,000 by default), and the
bad-loan rate's verdicts don't use it.

The scouting Run's peak is the forest's, on the main process: scikit-learn grows its trees in threads. Every run fit
in memory with room to spare.

The converter reads the files one row at a time: the 318 MB FOIA file took 13.9 s (the other two were not timed).
PocketBook itself reads the extract whole, as `ingest.read_table` does: every row and column as strings. The brief
warned that the whole LendingClub file (151 columns, 2.26 million rows) would need tens of GB. That was not
tried. The columns and rows were cut before PocketBook read anything.

## 4. The written workbooks

Every workbook opened with openpyxl. Every formula, defined name and dropdown was searched for `#REF!` and the other
error tokens, and for a sheet it points at that doesn't exist (`rehearse.check_workbook`; its own test plants all
three and finds them). The figures are the final run's:

| Workbook | Size | Formulas | Error tokens | Missing sheets |
|---|---|---|---|---|
| SBAnational, bleed | 2.6 MB | 95,385 | 0 | 0 |
| SBA FOIA, bleed | 3.6 MB | 131,732 | 0 | 0 |
| LendingClub, bleed | 8.5 MB | 290,050 | 0 | 0 |
| SBA FOIA, pre-spec | 0.11 MB | 2,215 | 0 | 0 |
| SBA FOIA, scouting | 0.12 MB | 2,183 | 0 | 0 |

521,565 formulas in all, the same counts as the builder's workbooks. Every cell of the five final workbooks was
compared with the builder's (1,989,397 cells). What differs:

- in every workbook, the last Run's time, the folder path, and the two launcher-limit questions on Control, whose
  wording main changed;
- LendingClub's `_look`, 22 bar counts: main's fix to count a loan on a bar's edge in that bar (#404);
- the pre-spec and scouting Columns row for the outcome, which now reads "picked and confirmed in the launcher"
  (main's #405);
- scouting's forest figures, in the third or fourth decimal (scikit-learn 1.9.1 against the builder's 1.5.2), and
  its Record tab, whose rows shift by one where the longer folder path wraps.

No pocket's multiple or p-value, no margin and no New variables figure differs.

The formulas sit where the design says:

- On SBAnational's Pockets, Worse? and Material? are formulas in 604 of 604 rows. They read `_list`, which reads the
  formulas on `_pockets`.
- On the pre-spec's New variables, Holds up?, Still holds?, Material? and In words are formulas in 8 of 8 rows.
- Scouting holds no formulas, as its As-of line says ("Nothing here follows Control").

Nothing was **calculated**, so a formula that would evaluate to an error is not caught here (decision 3).

## 5. What was not checked

- **Recalculation.** No Excel or LibreOffice recalculation of any workbook (decision 3). The verdict counts in
  section 2 apply the Control rule in Python to the stored numbers.
- **CI has not run on this branch.** `test.yml` runs on pushes to main and on pull requests, and the draft pull
  request is what starts it. Until it finishes, the 115 LibreOffice tests and the planted bugs only they catch have
  run nowhere against this code. The risk is largest for fix 1, which changes what is written into Control's cells
  that the live formulas read. By inspection only: `answers_needed` covers Control J15:J30, and the launcher's Status
  formulas read D before C.
- **The Tk launcher.** It was not driven. Set up and Run were called as the launcher calls them.
- **The CLI route** (`pocketbook run`) was not run on the full files.
- **Other files and proxies.** Not run: the 504 files, the other 7(a) vintages, the whole LendingClub file and the
  Prosper file. The RANR interest proxy (R2) was not built. No run was redone without the SBA term.
- **The full mutation run.** On the final code, with the new checker (`--files`, in a copy of the project), the 76
  planted bugs in `control.py`, `kgroups.py`, `scout.py` and `confirmatory.py` were put back. This branch changes the
  first three; `confirmatory.py` is included because the kgroups change feeds it. The 4 added here are among them.
  - 68 were caught, each by a failed test (none by errors alone).
  - 8 read NOT CHECKED: every test that guards them needs LibreOffice and skipped. The builder and a reviewer had the
    same 8.
  - The other 383 of the 459 planted bugs were not run here. CI's mutation job runs them all once the pull request
    starts it.
- **Two gaps not explained:** the paper's Table 5 population (877,428 loans against 897,167 in the file), and the
  LendingClub N (24,449 against 30,931).
- **The term.** Whether SBA's TermInMonths is the term as approved.
- **The bank machine.** Real Excel and the bank's machine are still not met.

## 6. What the reviews changed

Two reviewers checked the builder's work on 29 Sep 2026. Both reproduced the suite (707 passed, 115 skipped, 0 failed
of 822, and 706/116 in a copy, with the one-test difference not identified), the hashes, the extracts (3 of 3 byte
for byte), and each fix failing when reverted. One reran all five Runs on the full files and matched every stored
p-value. Their findings, and what was done:

| Finding | Done |
|---|---|
| The SBA term depends on the outcome (blocker) | Section 0; results cut on the term restated; `term_check` and labels in the converter, with tests |
| The recession "confound" is not supported | Withdrawn (section 1) |
| The pre-registered test misreported | All five directions reported; term under 60 marked not pre-registered; causes of the 240+ miss left open |
| LendingClub figures already on a public repository | Wording corrected; decision 2 asks keep or remove |
| scikit-learn: not version-specific | Defect 3 and decision 6 reworded; final runs on 1.9.1 |
| Timings vary far more than "about 10%" | Three samples given (section 3) |
| "Equal to 1e-12" overstated | Each tolerance stated |
| "Up to about 400,000 loans" | 333,786 |
| "10 tests" | 8 then; 9 now |
| confirmatory.py "changed by this branch" | Corrected (section 5) |
| LendingClub housing counted on one grid, unnamed | Grid named; the other grids' counts given |
| Answer key and timing scripts not in git | `tools/rehearsal_answer_key.py`, `tools/rehearsal_timing.py`, `--files` on the checker |
| "CI runs them all" | Corrected (section 5) |
| The "every coefficient" planted bug caught by wall time alone | A structural test added |
| README counts stale | Updated |
| BH is not in any answers file | Said to be Control's preset |
| RANR stand-in "invents no revenue"; FOIA has an interest rate | Reworded in the converter and here |
| Columns recorded after booking; the guard's false positive and negative | Labelled; recorded as observations |
| Counts and overstatements ("ties out exactly"; alone-in-band pockets) | Corrected; `rehearsal_effects.py` marks them |
| The mutation checker counts errors as catches | Fixed, with tests (section 1) |
