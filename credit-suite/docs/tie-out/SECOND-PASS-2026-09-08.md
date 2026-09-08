# Second pass — 8 September 2026

A different session, reading the delivered files cold. The first session built
this feed and then audited itself; this is the stranger's pass the brief asked
for.

Order below is the order the brief set: **the claims I decided to doubt, written
before I read `BACKLOG.md`**, then what came of them, then where I differ from
what the first session found.

---

## The answer first

**Nine findings. Eight of them are sentences, and one is 63 numbers.**

| | | where |
|---|---|---|
| F1 | 63 values published as impossible to check are on the filing, and **all 63 tie**. The verifier could not follow its own citation and published that as the bank not filing the line. The correct citation was already in the seed. | `verify_bank_history.py:66` |
| F2 | **A second disagreement with a filing, published as verified** — same bank and quarter as the one admitted DIFFERS, hidden by a tolerance. It decomposes into a $76.5m move in risk-weighted assets alongside the known $945k, with Tier 1 untouched. | Huntington, 2026-03-31 |
| F3 | **0 of 1,520 capital-ratio rows are exactly equal** to the filing; all tie on an undisclosed half-basis-point tolerance. | `verify_bank_history.py:330` |
| F4 | The identity fix reports 17 of 19 same-name banks. It is **16** — Fifth Third's name changed and the comparison normalised it away. | `config/peers.json` |
| F5 | "15 of the **33** merger quarters" — the backlog correctly says 31. The qualifier died on the way into the deliverable. | covering PDF p.7 |
| F6 | All 177 "not on that filing" rows carry a `note` that **contradicts their own verdict**; 114 are a 2017 form change across all 19 banks, not a bank omission. | `bank-values.csv` |
| F7 | The published "check any number yourself" recipe works as written on **37%** of bank rows. | covering PDF p.6 |
| F8 | The schedule label points at the wrong item on **532** filings — RC-R was renumbered in 2020Q1. | `bank-values.csv` |
| F9 | "Nothing in this feed is calculated by our software" — a delivered CSV ships a computed quarter-on-quarter change. | covering PDF p.1 |

**Everything I could throw at the numbers themselves came back clean**: seven
cross-field identities at 760 of 760, no missing merger, delivered-equals-checked
re-executed at 77,184 of 77,184, and a full rebuild that reproduces every
delivered CSV byte-for-byte. My strongest suspicion — that the macro half stamps
a series-level verdict onto every row — was **wrong**; all 65,844 have their own
comparison record.

---

## Part 1 — What I chose to attack, and why

I read only the three things the brief allows: the covering PDF, the workbook,
and the four CSVs. Everything in this section was picked from those.

Two of the brief's own suggested targets I deliberately did **not** take
(the four unchecked ratios, and re-sourcing the 11,237 macro observations):
both are already named in the document as open, so finding them open again
proves nothing. I went for claims the document makes **affirmatively**.

### T1 · The 177 "not on that filing" rows are the softest number in the feed

The brief says they were taken on the verifier's word. Reading the rows makes it
worse than that: **each of the 177 carries a `note` that contradicts its own
`verified_meaning`.** The verdict column says *"the bank did not report this line
in this quarter, so there is nothing on the filing to check it against"*; the
note column on the same row says *"read straight off the filing"* or *"this
filing's year-to-date less the previous quarter's"*.

And the shape of the population is wrong for the explanation given. The covering
document explains these as *"the bank did not report that line in that quarter;
forms change"* — a per-bank, per-quarter accident. What is actually there:

| field | rows | shape |
|---|---|---|
| `NCLNLS`, `P3LNLS`, `RSLNLTOT` | 114 | **all 19 banks**, in exactly 2016Q3 and 2016Q4 |
| `NTCIQ` | 63 | **4 banks**, one of them (Zions) in **38 of its 40 quarters** |

Neither of those is "a bank did not report a line". The first is our reader
meeting the pre-2017 form. The second is one bank being told, across a decade,
that it did not report its C&I charge-offs. **Doubt: these are our failures to
find the line, published as the bank's failure to file it.**

### T2 · The "check any number yourself" recipe on page 6

The document gives a reader a three-step procedure — open `filing_url`, search
for `cited_line`, read the number beside it — and says the number printed there
is the number in the workbook. I doubt that for a large minority of rows,
because `cited_line` is often not a code at all:

- `RIAD5411+RIADC234+RIADC235-RIAD5412-RIADC217-RIADC218` — six codes, three added
  and three subtracted. Nothing on the page is that number.
- `F164+F165`, `HK25`, `2150`, `3814` — no `RCFD`/`RCON`/`RIAD` prefix, in a
  document that has just taught the reader that the prefix is what picks the column.
- 5,462 rows are *this quarter's* figure minus *last quarter's*, and last
  quarter's filing is a different URL from the `filing_url` in the row.

**Doubt: the reader who follows the published instructions on one of those rows
lands on a different number and concludes the feed is wrong.**

### T3 · Is the merger list complete? Test it from the other end

The document reports that 15 of the 33 merger quarters move total assets 10% or
more. Nobody appears to have asked the converse: **how many 10%+ quarter steps
are NOT merger quarters?** If the merger list has a hole, that scan finds it; if
it doesn't, the scan is the first evidence the list is complete rather than
merely plausible. Either answer is worth having.

### T4 · `same_name_throughout` — the identity check checking itself

The document says 17 of 19 banks carry the same legal name on the oldest filing
as on the newest, and names Truist and Zions as the two exceptions. That is a
claim about string equality over data sitting in `config/peers.json`, so it can
be checked in one line. **Doubt: the comparison normalises something, and a real
name change is being normalised away.**

### T5 · Do the delivered numbers agree with each other?

Every check in this feed is vertical — one value against one filed line. Nobody
has run a **horizontal** check: does `LNLSNET` equal `LNLSGR − LNATRES` in the
delivered file? Does `EQV` equal `100 × EQ ÷ ASSET`? Does `NARERES` exceed
`NARELOC`? These identities are the FDIC's own definitions, so a break means a
field does not mean what the dictionary says it means — which is exactly the
"value right, citation wrong" class the brief warns about, and the only way to
catch it without opening 66,120 pages.

### T6 · "2,964 of 2,964" — check the denominator, not the numerator

Four FDIC-computed ratios over 760 filings is **3,040**, not 2,964. The document
reports the smaller number as if it were the whole population. **Doubt: 76 rows
were dropped from the denominator and the reason was not published.** (The repo's
own standing behaviour is *report the denominator*.)

### T7 · Does "verified = yes" on a macro row mean *that row* was compared?

The bank half compares every value. The macro half publishes 65,844 rows marked
`verified = yes` against a handful of named sources. **Doubt: a series-level
verdict was stamped onto every observation in the series**, and page 1's headline
"CHECKED AGAINST AN OUTSIDE DOCUMENT — 125,388" adds 66,120 individually-checked
bank values to a macro number of a completely different kind.

### T8 · Does TIED mean equal?

The bank example on page 2 ends *"agree to the dollar"* and prints
`difference 0`. **Doubt: somewhere in the macro half a tolerance exists, TIED
means "close enough", and no page says so.**

### T9 · `call_report_schedule` is constant per field across ten years

Every row for `ASSET` says `RC 12`; every row for `RBC1AAJ` says
`RC-R Part I line 31`. RC-R was re-laid-out inside this window. **Doubt: the
human-readable half of the citation is a static label, right for the newest
filing and quietly wrong for the oldest** — the MDRM code survives a re-lay-out,
the line number does not, which is the document's own argument for MDRM codes.

### T10 · "Nothing in this feed is calculated by our software"

Page 1, largest claim on the page. `not-comparable-periods.csv` ships a column
called `change_in_total_assets_pct`, and page 7 quotes a statistic computed from
it. **Doubt: the claim is true of the values and false as written.**

---

## Part 2 — What came of it

Environment: `SATC-cs` on `credit-suite-followups`, workdir on the Forge.
**629 tests pass** (4m 51s). `tieout_on_run.py` on a fresh seed: 3,933 ties,
16 of 16 planted controls caught. `run_and_tie_out.py`: 5 of 5 stages.

**The build reproduces the delivery.** After a full rebuild, all five delivered
CSVs and `verification-summary.json` are **byte-identical** to what is
committed; only the workbook (zip timestamps) and the tie-out's own seed file
moved. So everything below is a live property of the code, not an artefact of a
stale file.

---

### F1 · 63 values are reported as impossible to check. They are on the filing, and all 63 tie. *(target T1)*

`NTCIQ` — quarterly C&I net charge-offs — is cited as
`RIAD4645+RIAD4646-RIAD4617-RIAD4618`. Those are the **FFIEC 031** codes, where
C&I is split into 4.a U.S. addressees and 4.b non-U.S. A bank filing the **041**
reports the same thing as one line: `RIAD4638` charge-offs, `RIAD4608`
recoveries. The 031 codes are simply not on its form, so the check finds
nothing and the row is published as:

> *the bank did not report this line in this quarter, so there is nothing on the
> filing to check it against*

**Zions Bancorporation is told this in 38 of its 40 quarters.** First-Citizens
in 14, Morgan Stanley in 8, Huntington in 3.

I recomputed all 63 from the 041 codes, against the filings already in the
workdir, using the feed's own rule (this filing's year-to-date less the previous
quarter's; Q1 is the year-to-date):

```
63 rows recomputed — 63 tie, 0 differ, 0 unresolvable
Zions 2024-06-30   delivered 3,755    filed 3,755    difference 0
Zions 2020-09-30   delivered 50,391   filed 50,391   difference 0
```

**The correct citation was already written down.** `provenance_seed.py:232`
carries `RIAD4638-RIAD4608 (031: RIAD4645+RIAD4646-RIAD4617-RIAD4618)` with a
comment explaining this exact problem, and `filing.py`'s resolver handles it —
I called it directly and it returns `RIAD4638-RIAD4608` for Zions and the split
form for JPMorgan.

The delivered file does not go through that resolver. `verify_bank_history.py:66`
holds a **second citation table**, `FLOW_EXPR`, with the 031 expression
hard-coded, and a **second evaluator**, `evaluate()`, which does a literal
`facts.get(code)` with no form-variant handling. Ten quarterly-flow fields are
cited from that table. `BACKLOG.md` records *"There is now one comparison,
`sources/fdic/tieout.py`"* — that is true of balances and not of flows.

**Two things follow that are worse than the 63 rows.**

- The verifier's failure to resolve a citation is published as **a statement
  about the bank**. Nothing in the row says the software could not follow its
  own citation; it says the bank did not file the line.
- **The standing tie-out cannot catch it.** Those rows land in
  *"not claimed as verified"* (489 this run) and quarterly flows land in
  *"checked by the full run"*. The check that would find this is skipped, with a
  stated reason, in both directions.

The other nine flow fields in `FLOW_EXPR` should be read the same way before
this is called closed.

---

### F2 · There is a second disagreement with a filing, and it is published as verified

The document names *"the one number in 66,120 that does not agree"*. There is
another, on the same bank and the same quarter, and it is inside a tolerance.

`RBC1AAJ` and `RBCRWAJ` are checked with `tol = 0.005` percentage points
(`verify_bank_history.py:330`). Over all 1,520 capital-ratio rows:

| gap between delivered and filed | rows |
|---|---|
| exactly 0 | **0** |
| ≤ 0.00005 (the filing prints 6 decimals, the FDIC 4) | 1,519 |
| **0.00475** | **1** — Huntington National Bank, 2026-03-31, `RBCRWAJ` |

That one gap is **95 times the next largest in the feed**, and it consumes 95%
of the tolerance that lets it pass as TIED. It is the same bank-quarter as the
one published DIFFERS.

**And it decomposes into something the feed does not carry.** Backing the
risk-weighted assets out of each side:

```
FDIC    total capital 29,147,082   ratio 14.092446%   implied RWA 206,827,694
filing  total capital 29,148,027   ratio 14.087700%   filed   RWA 206,904,227
                            -945                                    -76,533

leverage ratio     FDIC 10.235659%   filing 10.235700%   gap -0.000041 (rounding)
```

So **two RC-R quantities moved together — total capital by $945 thousand and
risk-weighted assets by $76.5 million — while Tier 1 capital and average assets
did not move at all.** That is a real narrowing of the open question. An
amendment that touched risk-weighting and Tier 2 and left Tier 1 alone fits; a
transcription slip in one line does not. The first session's amendment
hypothesis gains a second, independent leg — and the $945 stops looking like the
whole of the disagreement.

**None of that is visible to a reader.** The feed carries no RWA field, and the
ratio row that carries the discrepancy says `verified = yes`.

---

### F3 · Every capital ratio in the feed ties on a tolerance, and no delivered page says so

Following from F2: **0 of 1,520** capital-ratio rows are exactly equal to the
filing. The covering document's worked example ends *"TIED. The delivered file
and the filed form agree to the dollar"* and prints `difference 0`; page 5
defines TIED as *"checked against a document published by somebody outside this
firm"*. Neither says that for one field pair, TIED means "within half a basis
point".

For 1,519 rows the gap is the publisher's own rounding and nothing is wrong with
the number. What is wrong is that a reader cannot tell those from the 1,520th.

The macro half has the same shape at smaller scale: **3,080 macro observations
carry TIED with a non-zero difference** — all publisher rounding, worst case
0.087% (`CDSP`, where the Fed prints two decimals and FRED carries six) — and
again no page mentions a tolerance.

The bank side's balance checks are genuinely exact: `tol = 0.51` on integers in
thousands means equal or nothing. It is only the ratios.

---

### F4 · The identity check's fix is still one bank short *(target T4)*

`BACKLOG.md` fault 4 fixed the string-sorted filing dates and reports **"17 of
19 carry the same legal name in 2016 as today"**, and the covering document
publishes that. In `config/peers.json`:

```
6672  same_name_throughout = True
      start 'FIFTH THIRD BANK'
      now   'FIFTH THIRD BANK, NATIONAL ASSOCIATION'    <== not the same string
```

It is **16 of 19**, with three exceptions. I read all 40 of Fifth Third's filed
front pages: the name changes at 2019-12-31, which is the state-to-national
charter conversion. So it belongs with Zions — a rename, not a Truist — and the
document's *"one is a rename and nothing else, the other is not"* becomes *two
renames and one that is not*. Nothing downstream is wrong; the count is.

Worth saying plainly: **a comparison that normalises is not the check that was
described.** The stated check is "the same legal name on the oldest filing as on
the newest". Whatever strips `, NATIONAL ASSOCIATION` was not stated, and it is
the difference between a right answer and a right-looking one.

*(Aside, same family: `filing-<cert>-MMDDYYYY.pdf` still string-sorts wrongly —
`glob` plus `sorted` on that name puts 2020 before 2017. The consumer that was
biting got fixed; the filename that causes it did not. I hit it in this session.)*

---

### F5 · "15 of the 33 merger quarters" — the denominator was lost in transit

`not-comparable-periods.csv` holds 33 rows, of which **31** have a computable
step (First-Citizens and Huntington at 2016-09-30 fall outside the window on the
prior side). 15 of those 31 move total assets by 10% or more.

`BACKLOG.md` says *"15 of the 31 measurable merger quarters"* — right. The
delivered PDF says *"15 of the 33 merger quarters move total assets by 10% or
more"* — wrong, and it is the client-facing half. The qualifier survived the
finding and died in the document.

---

### F6 · The 177 rows contradict themselves, and 114 of them are a form change, not a bank *(target T1)*

Every one of the 177 carries a `note` that its own `verified_meaning` denies:

| verified_meaning | note on the same row |
|---|---|
| the bank did not report this line in this quarter, so there is **nothing on the filing to check it against** | **read straight off the filing** (114) |
| " | this filing's year-to-date less the previous quarter's (47), first quarter: year-to-date IS the quarter (16) |

The 114 are `NCLNLS`, `P3LNLS` and `RSLNLTOT`, for **all nineteen banks**, in
**exactly 2016Q3 and 2016Q4**. I read the 2016 form: Schedule RC-N ends at item 8
(lease financing receivables) with no total line — `RCFD1406/1407/1403` and
`HK25` were added effective 2017Q1. So the verdict is true and its wording is
not: *the form did not carry the line*, and no bank omitted anything.

**What I could not close.** All the components (RC-N items 1–8, all three
columns) *are* on the 2016 filing, and the feed already checks 3,933 other
values as *"the filed lines the FDIC adds, summed"*. So "there is nothing on the
filing to check it against" is likely too strong. I tried to prove it by
reconstructing the total from the components, validating on 2017 where the filed
total exists — my parse of the facsimile's three-column layout recovered only 10
of about 22 items and the sums did not close. **COULD NOT, after attacking it
once.** It is worth one more attempt from the XBRL rather than from the PDF.

---

### F7 · The "check any number yourself" recipe works on 37% of the rows *(target T2)*

Page 6 tells a reader: open `filing_url`, search for `cited_line`, and *"the
number printed beside it is the number in the workbook"*. Graded over all 66,120
bank rows:

| what `cited_line` actually is | rows | does the recipe work? |
|---|---|---|
| one prefixed code (`RCFD2170`) | 24,568 (37%) | yes, as written |
| a sum of codes (`RCONF158+RCONF159`) | 17,227 (26%) | only if the reader adds them; the page never says to |
| codes with no prefix (`F164+F165`, `HK25`, `2150`) | 9,785 (15%) | in practice yes — I checked seven and the code appears once on the page — but the page has just taught that the prefix picks the column |
| an expression with subtraction | 6,809 (10%) | no |
| a ratio (`4340 / 3368`) | 6,080 (9%) | there is no line |
| a code plus a form-variant parenthetical | 1,651 (2%) | partly |

And separately: **5,679 rows (8.6%) are this quarter's figure minus last
quarter's, and last quarter's filing is a different URL from the `filing_url` in
the row.** A reader who follows the instructions on a net-charge-off row lands on
a year-to-date figure, sees it disagree, and has been given no way to know they
are looking at the wrong thing.

Page 1 claims this feed lets you *"put your finger on where"*. On three rows in
five, the finger lands somewhere the page did not prepare you for.

---

### F8 · The schedule label points at the wrong line on 532 filings *(target T9)*

`call_report_schedule` is one fixed string per field for all forty quarters. I
took the 32 fields whose citation is a single prefixed code, found each code's
printed item number on JPMorgan's 2016Q3 and 2026Q2 filings, and compared:
**none of the 32 moved.** The two capital ratios, which my filter excluded
because their citation carries a form variant, did:

| | labelled | 2016Q3 – 2019Q4 | 2020Q1 – 2026Q2 |
|---|---|---|---|
| `RBC1AAJ` (7204) | RC-R Part I **line 31** | item **44** | item 31 ✓ |
| `RBCRWAJ` (7205) | RC-R Part I **line 51** | item **43** | item 51 ✓ |

RC-R Part I was renumbered effective 2020Q1. **14 of the 40 quarters × 19 banks
× 2 fields = 532 rows** carry a label that is wrong for the filing they link to.
On a 2016 filing, RC-R Part I item 31 is *"Unrealized gains on available-for-sale
preferred stock classified as an equity security under GAAP"* — a dollar amount,
not a ratio.

The MDRM code is right in every case, which is the document's own argument for
MDRM codes. But the workbook publishes the line number too, and that is the half
a person navigates by.

**Related, and not disclosed anywhere:** the capital-ratio check takes `min()`
of whatever framework columns the bank filed (`verify_bank_history.py:238`).
293 of the 1,520 rows had more than one column, so the minimum was a real
choice. Taking the binding ratio is right; the delivered note says only *"filed
as a fraction; ×100 to the published percent"*. The `RBC` field's note does say
*"filed under N framework(s); this is the one that binds, chosen on its capital
ratio"* — so the wording exists in this codebase and did not reach these rows.

---

### F9 · "Nothing in this feed is calculated by our software" *(target T10)*

Page 1, the largest claim on the page: *"Nothing in this feed is calculated by
our software. No ratios, no quarter-on-quarter changes, no scores."*

`not-comparable-periods.csv` ships a column called `change_in_total_assets_pct`,
which is a quarter-on-quarter change computed here, and page 7 quotes a statistic
derived from it. It is a small thing and it is on the page that asks to be
trusted about everything else. The claim is true of the 143,201 values and false
as written; *"no value in this feed is calculated by our software"* would be
both.

---

## Part 3 — What I checked and found sound

Reported because a check nobody ran is not a check that passed, and because
three of these were where I most expected to find something.

- **Merger-list completeness, tested from the other end.** The document counts
  merger quarters that move assets by 10% or more. I ran the converse: every
  quarter-on-quarter step of 10% or more in `ASSET`, `DEP` and `LNLSGR` that is
  **not** in `not-comparable-periods.csv`. 18, 26 and 18 of them. Every one is
  explicable without a merger — the March and June 2020 deposit surge, and the
  custody and dealer banks whose balance sheets move like that normally. **I
  found no missing merger.** Against the ten known deals in this window, that is
  now evidence rather than assumption.

  *But it exposes a framing gap.* The LIMITS page treats discontinuity as a
  property of mergers. The largest unflagged single-quarter step in the feed is
  **Morgan Stanley Bank NA, +54.5% total assets at 2026-03-31**, bigger than 18
  of the 33 flagged ones, and it carries no flag because nothing was acquired. A
  reader told "NOT COMPARABLE carries the size of every step" will read the
  absence of a flag as an assurance it never gave.

- **Cross-field identities in the delivered file.** `LNLSNET = LNLSGR − LNATRES`,
  `EQV = 100·EQ/ASSET`, `LNATRESR = 100·LNATRES/LNLSGR`, `NCLNLSR`, `LNRESNCR`,
  `NARERES ≥ NARELOC`, `ASSET ≥ LNLSGR` — **760 of 760 on each, no breaks.** This
  was my main bet for finding a mis-citation like the nine total-loans rows. It
  found nothing, which is worth something: the 87 fields are mutually consistent,
  not merely individually matched.

- **T7 was wrong, and it was my strongest suspicion.** I expected the macro half
  to stamp a series-level verdict onto every row, because the result files
  (`fred_fhfa_results.json` and its siblings) hold exactly one comparison per
  series. Those are the exhibit set. Behind them, `fred_deep_rows.json`,
  `fred_history_rows.json` and `macro_new_rows.json` hold **90,922
  per-observation comparison records**. I joined them to the delivered CSV: **all
  65,844 rows marked `verified = yes` have a matching per-observation record —
  none inherited its verdict.** Page 1's 125,388 is honest.

- **Delivered = checked on the macro side, re-executed rather than trusted.** I
  compared `macro-observations.csv` against every comparison record
  independently of `prove_delivered_is_what_was_checked.py`: **77,184 records,
  0 where the delivered value differs from the value that was checked.**

- **The Huntington difference, reproduced from the filing store.** `RCFA3792` =
  29,148,027; delivered 29,147,082; −945. Only one 3792 column exists in the
  machine-readable filing, so the document's "the second column reads NR" holds.
  The filing's own ratio times its own RWA gives 29,148,047 — internally
  consistent.

- **Reproducibility.** A full rebuild reproduces all five CSVs and the summary
  byte-for-byte.

- **Bare-code citations are cosmetic, not ambiguous.** I feared `2150` with no
  prefix left the column open. On seven tested rows across three banks only one
  column exists on the filing. Untidy; not a correctness problem.

- **629 tests pass. 16 of 16 planted controls caught.**

---

## Part 4 — Where I differ from the first session

**What it found that I would not have.** The Case-Shiller finding — a verdict
that was computed and never reached the file — is invisible from outside the
codebase; I would have read those 22 as honestly unverified and moved on. The
string-sorted filing dates, likewise. And the vintage work — 442 of 760 filings
amended more than 90 days out — is the best thing in the file: it is the only
part that turns *"we compared two documents"* into *"we know which version of the
document we compared"*. I would not have got there from the deliverable.

**Where I think it is wrong.**

1. **Fault 4 is not closed.** Its own fix reports 17 of 19; it is 16 (F4).
2. **Finding 1's denominator did not survive into the deliverable** — 33 where
   the backlog correctly says 31 (F5).
3. ***"There is now one comparison"* is not true of quarterly flows.** F1 is the
   cost: a second citation table, a second evaluator, and 63 values published as
   unfilable that tie on the first try.
4. **"2,964 of 2,964" — the tool is honest, the document is not.**
   `check_fdic_ratios.py` prints `722 agree, 38 not comparable` on each of two
   ratios; the covering document reports 2,964 of 2,964 without saying the
   population is 3,040 or why 76 left it. And the 76 are downstream of the
   `NCLNLS` gap in F6, so they are not independent.
5. **The three "not checked" items were measured; the tolerances were not.**
   Nothing in the review asked what TIED means. It means "exactly" for 64,600
   bank values and "within half a basis point" for 1,520 — and the one value
   that uses that room is a real disagreement (F2, F3).

**Where I agree.** The data is in better shape than its documentation. Every
adversarial check I could run against the numbers themselves — identities,
merger completeness, delivered-equals-checked, reproducibility — came back clean.
**Eight of my nine findings are about sentences, labels and verdicts rather than
values.** The exception is F1, and even there the values are right; it is the
verdict on them that is wrong.

That is the same distribution the first session found — three of its five faults
were its own sentences — arrived at by a stranger, which is the useful part: it
is not a self-review artefact. **The numbers in this feed hold up. What is
written beside them is where it keeps breaking**, and the mechanism is
consistent: a claim gets written once, is true when written, and is not
re-derived when the thing it describes changes.

---

## Part 5 — What I did not do

- **The macro side's source selection.** 11,237 observations with no obtainable
  source, and 202 source choices made once by one session. I confirmed the
  plumbing is honest and did not second-guess a single source choice. Still
  unchecked by anybody.
- **`EEFFR`, `NIMY`, `NTLNLSQR`, `ROAQ`.** Still checked against nothing. I agree
  they cannot be done from the 87 fields; nobody has asked whether the feed
  should carry the four or five extra lines that would make them checkable.
- **Whether the 114 rows in F6 could be tied from components.** Attacked, did not
  close.
- **The nine other flow fields in `FLOW_EXPR`.** F1 is one of ten cited from that
  table. I checked the one whose failure was visible in the delivered file. A
  form-variant miss that happens to resolve on every bank in this set would be
  invisible in exactly the same way — until the twentieth bank.
- **Opened no exhibit PDF as an exhibit.** I read the filed Call Reports
  directly. Nobody has checked that the 209 exhibits photograph the row their
  manifest names.
- **Still nothing here checked by a second person.** I am a second model, not a
  second person.

---

## Postscript — what happened to the nine

Docket `51f34a75`, answered the same day: all four decisions took the
recommendation. The nine findings were closed, and the work of closing them
turned up a tenth nobody had asked about.

**Nine tools could not be imported at all.** `NAME = SB / "..."` sat above
`SB = workdir()` in nine of them after the move to the Forge, so each raised
`NameError` before running a line — including `verify_bank_history.py`, which
decides every bank verdict in the delivered file. It was found by trying to run
it, and nothing had caught it because the standing run starts downstream of all
nine, on rows those tools wrote before the move. That is the same shape as F1
and as everything else in this pass: a green result standing on something
nobody re-derived.

The numbers that moved: `bank_verified` **59,544 → 59,606**, `DIFFERS`
**1 → 2**, "not on that filing" **177 → 114**, tests **629 → 695**. The
covering document is reissued as
`SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-2026-09-08.pdf` and the 7 September
build is retired. Full account in `BACKLOG.md` under *What the answers caused*.

Four things stay open on purpose, and they are named there rather than closed
quietly.
