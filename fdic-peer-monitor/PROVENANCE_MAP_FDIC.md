# Provenance Map — FDIC API fields -> Call Report schedule/line (tie-out)

The contract-s12 tie-out artifact: where each workbook value appears in the
bank's actual filed Call Report. Verified against the FFIEC's OWN CDR
bulk-data files (2023Q1: header row = MDRM code, row 2 = FFIEC caption; one
file per schedule) plus the Fed MDRM dictionary and observed per-form
reporting across all 4,724 filers. Flags: [V] = code verified against FFIEC
captions; [~] = line NUMBER from the 041 layout, match by caption on the
facsimile; UNVERIFIED = stated. **No public FDIC field->MDRM crosswalk
exists — this table is assembled from the FFIEC forms + MDRM dictionary and
is the citation of record.**

**Open the filed document (keyed by CERT, which the template already uses):**
```
https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&idType=fdiccert&id={CERT}&date={MMDDYYYY}
```
UBPR cross-check: `...ViewFacsimileDirect.aspx?ds=ubpr&reptype=1&idType=fdiccert&id={CERT}`.
Interactive fallback: cdr.ffiec.gov/public/ManageFacsimiles.aspx.
Two-step tie-out: API value <-> BankFind institution page (pull check) <->
CDR facsimile schedule/line (filing check). MDRM prefixes: RCON (domestic) /
RCFD (consolidated, 031 filers) / RIAD (income) / RCOA-RCFA (RC-R).

## A. Balances (Schedule RC and related)

| Field | Schedule / line | Caption | MDRM | Note |
|---|---|---|---|---|
| ASSET | RC 12 | Total assets | RCON2170 [V] (RCFD2170 031) | |
| DEP | RC 13.a (+13.b 031) | Deposits in domestic (+foreign) offices | RCON2200 [V] (+RCFN2200 031) | FDIC DEP includes foreign for 031 |
| LNLSGR | RC-C Pt I 12 | Total loans & leases HFI+HFS, net of unearned | RCON2122 [V] | = RC 4.a + 4.b |
| LNLSNET | RC 4.a+4.b-4.c | HFS (5369) + HFI (B528) - allowance (3123) | components [V] | FDIC-computed; no single line |
| EQ | RC 27.a | Total bank equity capital | RCON3210 [V] | excludes minority int. (28/G105) |
| LNATRES | RC 4.c | Allowance for credit losses on L&L | RCON3123 [V] | legacy transfer-risk add-on UNVERIFIED; 3123 is the tie-out line |
| BRO | RC-E Mem 1.b | Total brokered deposits | RCON2365 [V] | |
| DEPUNINS | RC-O Mem 2 | Estimated uninsured deposits | RCON5597 [V] | FILED only by banks >= $1B (961/4,724 in 2023Q1); below that the API value is an FDIC ESTIMATE — not tie-able |
| DEPINS | RC-O Mem 1 | Insured-deposit components | F049,F045,F051/F052,F047/F048 [V] | FDIC-computed estimate; formula UNVERIFIED, components verified |
| OTHBFHLB | RC-M 5.a.(1)(a)-(d) | FHLB advances by maturity | F055+F056+F057+F058 [V] | sum of four lines; F059 structured is of-which — do NOT add |

## B. Loan categories (Schedule RC-C Part I, $ outstanding)

| Field | Line | Caption | MDRM |
|---|---|---|---|
| LNRECONS | 1.a.(1)+(2) | 1-4 fam constr + other constr/land | F158+F159 [V] |
| LNRENRES | 1.e.(1)+(2) | Owner-occ + other nonfarm nonres | F160+F161 [V] |
| LNREMULT | 1.d | Multifamily (5+) | RCON1460 [V] |
| LNRERES | 1.c.(1)+(2)(a)+(2)(b) | HELOC + 1st lien + junior lien | 1797+5367+5368 [V] |
| LNCI | 4 | Commercial & industrial | RCON1766 [V] (031: RCFD1763+1764) |
| LNCRCD | 6.a | Credit cards | RCONB538 [V] |
| LNAUTO | 6.c | Automobile loans | RCONK137 [V] |
| LNCONOTH | 6.d | Other consumer | RCONK207 [V] (6.b B539 is separate) |

## C. Past-due / nonaccrual (Schedule RC-N)

**Structure (verified): col A = 30-89 days still accruing (P3*), col B = 90+
still accruing (P9*), col C = nonaccrual (NA*). Each API triple = one row
read across. P9* EXCLUDES nonaccrual (disjoint columns).**

| Triple | Line | Caption | A / B / C |
|---|---|---|---|
| *LNLS | 9 | Total loans & leases | 1406 / 1407 / 1403 [V] |
| *RECONS | 1.a.(1)+(2) | Construction (2 rows) | (F172+F173)/(F174+F175)/(F176+F177) [V] |
| *RENRES | 1.e.(1)+(2) | Nonfarm nonres (2 rows) | (F178+F179)/(F180+F181)/(F182+F183) [V] |
| *REMULT | 1.d | Multifamily | 3499 / 3500 / 3501 [V] |
| *RERES | 1.c.(1)+(2)(a)+(b) | Residential (3 rows) | (5398+C236+C238)/(5399+C237+C239)/(5400+C229+C230) [V] |
| *CI | 4 | C&I | 1606 / 1607 / 1608 [V] (031 splits 4.a/4.b) |
| *CRCD | 5.a | Credit cards | B575 / B576 / B577 [V] |
| *AUTO | 5.b | Automobile | K213 / K214 / K215 [V] |

051 printed item numbers [~] — all 3,524 051 filers report these codes;
match by caption.

## D. Charge-offs / recoveries (Schedule RI-B Part I; col A = YTD
charge-offs = DR*, col B = YTD recoveries = CR*; NT* = FDIC-computed DR-CR)

| Fields | Line | Caption | A / B |
|---|---|---|---|
| *LNLS | 9 | Total | 4635 / 4605 [V] |
| *RECONS | 1.a.(1)+(2) | Construction | (C891+C893)/(C892+C894) [V] |
| *CI | 4 | C&I | 4638 / 4608 [V] (031: 4645+4646 / 4617+4618) |
| *CRCD | 5.a | Credit cards | B514 / B515 [V] |
| *AUTO | 5.b | Automobile | K129 / K133 [V] |

RIAD amounts are calendar-YTD: FDIC's quarterly variants are differenced —
Q2-Q4 workbook values tie to (this quarter's YTD minus prior quarter's YTD).

## E. Securities (Schedule RC-B line 8, four columns)

SCHA = col A HTM amortized (1754 [V]) · SCHF = col B HTM fair (1771 [V]) ·
SCAA = col C AFS amortized (1772 [V]) · SCAF = col D AFS fair (1773 [V];
= RC 2.b). Tie SCHA to RC-B (RC 2.a JJ34 is net of ACL post-CECL — differs).
Equity securities excluded (RC 2.c JA22).

## F. Ratios (FDIC-computed unless "filed directly")

| Field | Tie-out |
|---|---|
| RBC1AAJ | FILED: RC-R Pt I line 31 Leverage ratio, RCOA7204 [V] (all banks incl. CBLR) |
| RBCT1CER | FILED: RC-R Pt I ~49 CET1 ratio, RCOAP793 [V] — BLANK for CBLR electors |
| RBCRWAJ | FILED: RC-R Pt I ~51 Total capital ratio, RCOA7205 [V] — CBLR caveat (Tier1 = 7206) |
| NCLNLSR | 100 x (1407+1403)/2122 — all filed |
| NTLNLSQR | 100 x annualized qtr (4635-4605 differenced) / RC-K avg loans (3360 [V]) |
| LNATRESR | 100 x 3123/2122 |
| LNRESNCR | 100 x 3123/(1407+1403) |
| EQV | 100 x 3210/2170 |
| ROAQ | 100 x annualized qtr RIAD4340 (RI 14 [V], differenced) / RC-K avg assets (3368 [V]) |
| ROEQ | numerator filed; avg equity FDIC-computed (no filed line) |
| NIMY | 100 x annualized RIAD4074 / avg earning assets (FDIC-computed from RC-K) |
| EEFFR | 100 x (4093 - C232 [RI 7.c.(2) ~]) / (4074 + 4079) — all components filed |

Ratio recomputations tie to ~rounding (FDIC annualization/differencing).

## Citations of record (for the _provenance tab header)

FFIEC 031/041/051 forms (schedule + item + MDRM printed per field) · Fed
MDRM dictionary (federalreserve.gov/apps/mdrm/) · FFIEC UBPR User's Guide
(ratio concepts) · facsimile URL pattern above. Honesty flags carried per
row; nothing invented — [~] rows match by caption.
