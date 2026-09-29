# PocketBook on public loan data: the rehearsal of 29 Sep 2026

PocketBook was run end to end, headlessly, through the workbook route the analyst uses (Set up, answers written
into Control and Columns, Run), on three public loan files: the SBA's 7(a) FOIA file for FY2000–FY2009 (604,573 loans
with a known outcome), `SBAnational.csv` from Li, Mickel & Taylor (2018) (897,167), and LendingClub's 36-month
loans issued 2008–2011 (30,931). Everything below is an aggregate. No loan-level row is in git. The data, the
extracts, the workbooks and each run's timings sit in `C:\Users\ajish\SATC-evidence\public-loans-2026-09-29\`,
which can be purged (its `README.md` gives the sources, licences and SHA-256s).

Tools, all in this branch: `tools/public_extract.py` (raw file to extract plus a manifest of every filter and derived
column), `tools/rehearse.py` (the headless workbook route, with timings, peak memory and a workbook check),
`tools/rehearsal_effects.py` (margins and pocket verdicts read out of a written workbook). The answers given to
every workbook, and the pre-registered pre-spec, are in `docs/rehearsal-public-data-2026-09/`.

## 1. Findings

### Defects found and fixed (3), each with a regression test on a tiny synthetic book

All three tests are in `tests/test_rehearsal_2026_09_29.py`. Each failed before its fix. Each fix has a planted bug
in `tools/mutation_check.py`, and each of those 4 planted bugs was run alone and caught.

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
   - **What happened.** The pre-registered test on the FOIA file held BusinessType fixed, so its pockets held up to
     about 400,000 loans. The run was stopped after 10.5 minutes of Run (914 s of CPU), still inside its first
     conditional fit. py-spy put it in `np.convolve`, called from `_prod`.
   - **The measured cost.** One evaluation of a 217,800-loan pocket took **191 s**. A 79,200-loan pocket took 23.8 s,
     and a 19,800-loan pocket 0.08 s. A fit needs several evaluations per pocket per Newton step.
   - **Why.** The code multiplied every group's polynomial out in full, although a tilted binomial's coefficients
     underflow to exactly 0.0 away from its middle, and only the coefficient at *m* is ever read.
   - **The fix.** Each polynomial now carries only its nonzero coefficients, with an offset. A coefficient that is read
     once is now one dot product, not a whole convolution. No approximation is made.
   - **Results.** The same 217,800-loan pocket now takes **0.25 s**. The same pre-spec run on the full file finished in
     128 s. The old implementation is kept in the test as a reference. The new one equals it to 1e-12 on four pockets:
     a group at its boundary, an empty group, and *b* at zero and away from it.
3. **scikit-learn that is installed but won't load crashed the Run** (`scout.run`).
   - **What happened.** On this machine, Windows Application Control blocked scikit-learn 1.9.1's compiled files:
     *"DLL load failed while importing _loss: An Application Control policy has blocked this file."*
   - **Why it crashed.** `scout.missing()` looks for the add-on without loading it (deps.py's rule), so the add-on
     read as installed. A scouting Run then died on the forest's import.
   - **The fix.** `scout.run` now loads `sklearn.ensemble` and `sklearn.metrics` before finding anything. A failed
     load becomes the refusal in words that a missing add-on already gets, and a saved shortlist still confirms.
   - **How the rehearsal ran scouting.** scikit-learn 1.5.2, also within pyproject's `>=1.4`, loads here. The
     rehearsal's scouting ran on it. A bank machine is the likeliest place for such a policy (decision 6 below).

### Also fixed: the suite on Windows

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

**After every fix, the full suite here reads 707 passed, 115 skipped, 0 failed (822 collected).** All 115 skips are
tests that need LibreOffice to calculate the workbook. `~/.pocketbook` was never created: every run set its memory
file in the data folder, and the suite sets its own.

### Open: decisions for the firm, recorded and not decided

1. **SBA's RANR.** The SBA files carry no revenue. The extract uses `RANR = −GCO` (revenue treated as zero; the
   converter refuses to run until `--ranr neg-gco` is named). Consequences:
   - Contribution before losses is 0 for every loan. Both SBA bleed Runs said *"Nothing is worse for Contribution
     before losses"*, which is correct and empty.
   - Profit after losses is the charge-off rate turned over: its worst pocket is the GCO worst pocket on both SBA
     files.
   - The profit tabs on the SBA workbooks are **not evidence**.

   The alternative is an interest proxy (`GrossApproval × rate × years × ½ − GCO`, FY2009 and later only). It was not
   built.
2. **LendingClub's licence.** The CC0 labels on the Hugging Face and Kaggle copies are the re-uploaders'.
   LendingClub's own terms are unknown. The data was used here for internal rehearsal evidence only.
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
6. **Which scikit-learn to carry to the bank.** Defect 3 now says a blocked add-on in words, but it still can't run
   there. If the bank's machine enforces application control, the add-on wheels made by `tools/bank_kit.py
   --add-ons` may need a version IT will allow, or the firm may confirm saved shortlists only.

### Observations that are not defects

- **A band-level effect never makes a pocket worse when pockets are judged against their band.** This is Control's
  *The rest of its band* (OC-44), and it is by design. Loan size is the paper's Table 4 effect. It shows on the band
  margins and on Grids' *against the book* block, and it is flagged on no pocket.
- **Pocketing found a confound in a published effect.** The paper's "Recession" is the scheduled end date (its SAS,
  footnote 6), not "active during". Across the book it reads 31.21% against 16.38%. Inside Term bands, recession
  loans charge off *less* in 3 of 4 bands. Checked from the loans without PocketBook: 60–83 months, 15.66% against
  21.76%; under 60 months, 71.70% against 54.09%. PocketBook reported it correctly. The published effect is largely
  term mix.
- **The term effect on SBA is very strong.** On the FOIA file the tree scores AUC 0.93 on development loans and 0.92
  on loans it never saw, mostly from TermInMonths. The data dictionary says only "Length of loan term". That is not
  evidence the term was recorded after the fact:
  - Only 0.8% of charged-off loans have a term equal to the months from first disbursement to charge-off.
  - 48.5% charged off after their term had ended.

  Whether the term is the one approved is **not verified**.

### Mapping caveats: every derived column is a rehearsal approximation, with the manifest saying so

- **SBA FOIA.** The file has no loan number, so `ROW_KEY` is made from the file and its row.
- **Booked amount.** It is `GrossApproval`: approved, not drawn. That overstates a revolving line.
- **Kept loans.** Only P I F and CHGOFF are kept. Left out: 82,276 CANCLD (never disbursed) and 3,484 EXEMPT (active,
  status withheld). The data writes `P I F`; its dictionary says `PIF`.
- **Derived columns.** `NAICS2` is the first two digits. `REAL_ESTATE` is a term of 240 months or more, the paper's
  proxy. `RECESSION` is the paper's SAS, as written.
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

"Worse" and "better" mean a pocket (band × segment) reads 1.25× or more, or 0.8× or less, against the
rest of its band, at 95% after Benjamini-Hochberg. That is the Control answers given
(`answers-*.yaml`). The workbook's own verdicts are formulas and were not calculated. These counts apply the same
rule in Python to the multiples and p-values the Run stored on `_pockets` (`tools/rehearsal_effects.py`). The rates
are the Run's own margins, from `_views`. The independent figures are plain Python over the extract, kept in
`extracts/answer-key.txt`.

### SBAnational: the paper's own file (exact tie-out expected)

| Effect (paper) | Paper | PocketBook (margin) | Independent | Pockets | Verdict |
|---|---|---|---|---|---|
| Industry, 2-digit NAICS (Table 3) | 21: 8, 11: 9, 55: 10, 62: 10 … 52: 28, 53: 29 | 21: 8.48, 11: 9.03, 55: 10.16, 62: 10.38 … 52: 28.43, 53: 28.73 | same to 0.01 pt | 53 worse in 4 of 5 bands, 48 and 51 in 4, 52 in 3 (and better in 1); 62 better in 5, 11 and 21 in 4; 55 (256 loans) none flagged | **Hit.** All 24 codes round to Table 3 |
| Backed by real estate, term ≥ 240 (Table 5) | 1.64% vs 21.16% | 1.63% vs 20.81% | same | Y better in 5 of 5, N worse in 5 of 5 | **Hit.** The not-RE rate is 0.35 pt off: the paper's Table 5 covers 877,428 loans, this file 897,167 (not explained) |
| Active in the Great Recession (§4.1.6) | 31.21% vs 16.63% | 31.21% vs 16.38% | same | Y worse in 5 of 5 loan-size bands; better in 3 of 4 Term bands (above) | **Hit**, with the confound found |
| Smaller loans default more (Table 4) | median $61,962.5 vs $100,000 | bands $4,000–34,999: 25.32% … $300,000+: 9.26%, monotone | medians $61,500 vs $100,000 | a band effect: no pocket flagged against its band, by design | **Hit** on the margins |
| New vs existing, "relatively negligible" | 18.98% vs 17.36% | 18.75% vs 17.11% (1.10×) | same | New worse in 2 of 5 loan-size bands and 2 of 4 Term bands; better in 1 | **Hit** at the book: under the line. A few pockets clear 1.25× |
| Florida high (text) | — | FL 27.37%, the highest state | same | worse in 5 of 5 | **Hit** |

### SBA 7(a) FOIA FY2000–FY2009, as of 30 Jun 2026 (same direction and ordering expected, not the same figures)

- **Industry: hit.** 53 is the highest industry of any size (30.78%). 21 (13.06%), 62 (14.39%) and 11 (17.39%) are
  the lowest, and 62 reads better in 5 of 5 bands. The middle order moves (48 at 27.84%, 51 at 26.32%), and fewer
  pockets are flagged than on SBAnational (53 worse in 2 of 5).
- **Real estate: hit.** Y 5.62% against N 25.61%. Y is better in 4 of 5 bands, N worse in 5 of 5.
- **Recession: hit.** Y 38.15% against N 22.36%, worse in 5 of 5.
- **Loan size: hit, flatter.** $55–23,999: 26.47%; $24,000–49,999: 27.23%; $50,000–99,999: 25.47%;
  $100,000–239,999: 20.60%; $240,000 and up: 19.83%.
- **Florida: hit.** 34.98%, second to NV (34.99%) among states with more than 11 loans.
- **Vintage.** FY2007 37.00%, FY2006 32.34%, FY2008 30.64%, against 13.48–14.91% for FY2000–02. The recon brief had
  "the 2006–2008 vintages lose more" as an *unverified* hypothesis with no primary source. PocketBook shows it here
  (worse in 4–5 of 5 bands), and it stays an observation, not a tie-out.
- **BusinessAge.** The FOIA file's categories are not the paper's NewExist. 293,130 loans (48%) read "Less than 4
  years old but at least 3", which looks like a coding default. It is not compared.

**The pre-registered confirmatory test** (`prespec-sba-foia-loan-size-term.yaml`) was committed before any run on
this file, at 727b5ea7. Record reads *"Follows pre-spec … (commit 727b5ea75971)"*, with one touch of the holdout.
Development was FY2000–05 (333,786 loans), holdout FY2006–09 (270,787):

- **Larger loans charge off less: hit.** On the holdout, 150,000–349,999 reads 0.72× and 350,000 and up 0.79×,
  against 50,000–149,999 (0.73× and 0.81× with BusinessType held fixed). Both are significant after the allowance.
- **The smallest loans charge off more: miss.** It was 1.12× on development and 0.99× on the holdout (not
  significant). With BusinessType held fixed it reads 0.95×, significant the other way.
- **Term under 60 months: hit.** 0–59 months reads 23.2× and 60–83 reads 7.2× against 84–119 on the holdout.
- **240 months and up far better: miss.** It was 0.75× on development and **1.38×** on the holdout. Checked from the
  loans: 12.10% against 9.06% for FY2006–09 approvals, and 3.13% against 4.13% for FY2000–05. Per booked dollar the
  240-month loans still lost less (8.39% against 21.16%).

The misses are my hypotheses failing on 2006–09 vintages, not PocketBook. Every figure was reproduced without it.

**Scouting**, on the same file with the cutoff "the month start nearest 70% of the loans", worked as follows.
- **Split.** It gave 2006-11-01: 426,772 development loans, with 177,801 held back and not read while finding.
- **Proposed.** TermInMonths (importance 0.44; bins 12, 14, 24, 48, 60) and GrossApproval (0.035; bin 254,000).
- **Not proposed.** JobsSupported (0.004, "no bend to cut at"). The noise floor was 0.0035.
- **Pre-spec.** It wrote the pre-spec, then confirmed on the held-back loans. Under 12 months and 14–59 months read
  9.3–14.9× the 60-month-and-up group, and 12–13 months 1.22×. 254,000 and up reads 0.79× (0.82× held fixed).

### LendingClub, 36-month loans issued 2008–2011 (directional: the population differs from the paper's)

| Effect (Serrano-Cinca et al. 2015) | Paper | PocketBook (margin) | Pockets | Verdict |
|---|---|---|---|---|
| Grade, monotone | A 5.6 … G 38.2 | A 5.89, B 10.96, C 15.32, D 19.17, E 21.98, F 29.36, G 33.51 | A better in 5 of 5; C–G worse in 2–5 of 5 each | **Hit** |
| Purpose | small business 21.9 highest; wedding 7.2, credit card 7.6, car 7.9 lowest | small business 23.31 highest; credit card 8.50, wedding 8.60, car 8.76 (major purchase 8.26) | small business worse in 4 of 5; credit card better in 5 of 5 | **Hit** |
| Housing | rent 11.7, mortgage 9.9 (significant) | rent 12.93, own 11.48, mortgage 10.94 | none: 1.18× is under the 1.25× line | **Direction hit; not flagged at these settings** |
| DTI, revolving utilisation, inquiries, income, rate (means) | higher for defaults (income lower) | every banded margin moves that way: DTI 10.16→13.74; utilisation 8.38→16.46; inquiries 9.23→16.68; income 15.87→8.97; rate 4.96→19.79 | band effects, as above | **Hit** |
| Nulls: loan amount, employment length | not significant | amount 10.70–13.25, no order; employment 10.21–12.52 (blank 19.76) | none, but blank employment worse in 3 of 5 | **Hit** |

**No known effect was missed because of a PocketBook defect.** Two things were missed:

- the two pre-registered hypotheses above, which failed on the data, as checked independently;
- the housing effect, which sits under the worse-at line the answers chose.

## 3. Performance

This machine: 12 cores, 32 GB, Windows 11, Python 3.12, numpy 2.5.3. It was shared with the Forge's live services
and with this session's own reads. Peak memory is the largest resident set sampled every 0.2 s, for the main process
and for it plus the shuffle test's workers.

| Run | Loans | What ran | Set up | Run | Peak, main | Peak, with workers |
|---|---|---|---|---|---|---|
| SBAnational, bleed | 897,167 | 2 bands × 7 segments = 14 grids, 10,000 shuffles | 68.4 s | 826.8 s | 2.71 GB | 3.87 GB |
| SBA FOIA, bleed | 604,573 | 2 × 8 = 16 grids, 10,000 shuffles | 53.6 s | 547.0 s | 2.09 GB | 3.13 GB |
| LendingClub, bleed | 30,931 | 7 × 5 = 35 grids, 10,000 shuffles | 3.4 s | 34.5 s | 0.39 GB | 1.25 GB |
| SBA FOIA, pre-spec, **before fix 2** | 604,573 | 2 inputs, BusinessType held fixed | 54.3 s | stopped after 10.5 min in the first fit | 0.85 GB when stopped | — |
| SBA FOIA, pre-spec, after fix 2 | 604,573 | the same | 76.8 s | 128.2 s | 1.09 GB | 1.09 GB |
| SBA FOIA, scouting | 604,573 | 3 candidates, BusinessType held fixed | 81.1 s | 622.9 s (about 8 min finding) | 4.21 GB | 4.21 GB |

**Where a bleed Run's time goes.** On the FOIA file, measured separately with the Run's recorded cube:
- reading the extract: 2.5 s;
- the pure-Python pass over 16 grids without the shuffle test (as `book.run` builds its first pass): 86.4 s;
- the same with the 10,000 shuffles: 608.1 s. So about 520 s is the shuffle test for the dollar rates, spread over
  8 workers.

That separate measurement ran longer than the whole Run had (547.0 s), so timings on this shared machine vary by
about 10%. The shuffle test's cost is the README's own extrapolation borne out (about 3 minutes at 200,000 loans,
so about 9 at 600,000). It is not a defect: Control's *shuffles* sets it (100 to 1,000,000; 10,000 by default), and
the bad-loan rate's verdicts don't use it.

The scouting Run's peak (4.21 GB) is the forest's, on the main process: scikit-learn grows its trees in threads.
Every run fit in memory with room to spare. The largest, 897,167 loans by 17 columns, peaked at 3.87 GB with its
workers.

The converter reads the files one row at a time: the 318 MB FOIA file took 13.9 s (the other two were not timed).
PocketBook itself reads the extract whole, as `ingest.read_table` does: every row and column as strings. The brief
warned that the whole LendingClub file (151 columns, 2.26 million rows) would need tens of GB. That was not
tried. The columns and rows were cut before PocketBook read anything.

## 4. The written workbooks

Every workbook opened with openpyxl. Every formula, defined name and dropdown was searched for `#REF!` and the other
error tokens, and for a sheet it points at that doesn't exist (`rehearse.check_workbook`; its own test plants all
three and finds them):

| Workbook | Size | Formulas | Error tokens | Missing sheets |
|---|---|---|---|---|
| SBAnational, bleed | 2.6 MB | 95,385 | 0 | 0 |
| SBA FOIA, bleed | 3.6 MB | 131,732 | 0 | 0 |
| LendingClub, bleed | 8.5 MB | 290,050 | 0 | 0 |
| SBA FOIA, pre-spec | 0.11 MB | 2,215 | 0 | 0 |
| SBA FOIA, scouting | 0.12 MB | 2,183 | 0 | 0 |

The formulas sit where the design says:

- On SBAnational's Pockets, Worse? and Material? are formulas in 604 of 604 rows. They read `_list`, which reads the
  formulas on `_pockets`.
- On the pre-spec's New variables, Holds up?, Still holds?, Material? and In words are formulas in 8 of 8 rows.
- Scouting holds no formulas, as its As-of line says ("Nothing here follows Control").

Nothing was **calculated**, so a formula that would evaluate to an error is not caught here (decision 3).

## 5. What was not checked

- **Recalculation.** No Excel or LibreOffice recalculation of any workbook (decision 3). The verdict counts in
  section 2 apply the Control rule in Python to the stored numbers.
- **The Tk launcher.** It was not driven. Set up and Run were called as the launcher calls them.
- **The CLI route** (`pocketbook run`) was not run on the full files.
- **Other files and proxies.** Not run: the 504 files, the other 7(a) vintages, the whole LendingClub file and the
  Prosper file. The RANR interest proxy (R2) was not built.
- **The full mutation run.** 76 of 446 planted bugs were run: every one aimed at a file this branch changed
  (control.py, kgroups.py, scout.py, confirmatory.py), including the 4 added here.
  - 68 were caught.
  - 8 were not checked here: each is caught only by tests that need LibreOffice, and those skip on this machine,
    so no test ran.
  - The other 370 were not run on this machine. CI runs them all.
- **Two gaps not explained:** the paper's Table 5 population (877,428 loans against 897,167 in the file), and the
  LendingClub N (24,449 against 30,931).
- **The term.** Whether TermInMonths is the term as approved.
- **The bank machine.** Real Excel and the bank's machine are still not met.
