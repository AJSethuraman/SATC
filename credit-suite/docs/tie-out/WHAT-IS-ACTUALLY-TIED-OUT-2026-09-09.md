# What is actually tied out

**For the session that built this feed.** Two independent verifiers went through
it on 9 September 2026, one per half, each forbidden to import, call or copy
`credit_suite.sources.fdic.filing`, `…tieout` or anything under `tools/tieout/`.
Both wrote their own citation parser, prefix resolver, arithmetic evaluator and
year-to-date differencer from scratch, and the macro verifier downloaded every
publisher's own file and built its own crosswalks rather than reusing ours.

Neither had built any of it. That is the point: this repository has now twice
found that its numbers hold and its *sentences* do not, and a self-review is
worst at exactly that.

---

## 1 · The number

The feed claims **137,424** values checked against a document published by
somebody outside this firm. Independently re-derived:

| | rows |
|---|---|
| **Exactly equal** to the source, no tolerance used | **135,580** |
| Agree to the limit of the publisher's own printed precision | **1,775** |
| **Do not match the publisher's file as it stands today** | **69** |
| | **137,424** |

**The claim holds.** Nothing is overstated. The three lines break down as:

- **Bank, 71,580 of 71,580.** Every row marked `verified = yes` reproduces from
  the bank's own filed Call Report. 70,061 of them to the exact dollar, with no
  rounding slack needed anywhere. The 1,519 capital-ratio rows agree to within a
  residual whose maximum is **exactly 5.00e-5** — half a rounding step of a
  6-decimal filed fraction, a distribution that is itself evidence the gap is
  rounding and nothing else. *For those two fields, "verified" means agreement
  to four decimal places of a percent; an error smaller than that is
  undetectable from the filing, and no delivered page says so.*
- **Macro, 65,844 of 65,844 located and compared** in the publisher's own file —
  every observation, no sampling. 65,519 exact; 256 agree to the publisher's
  printed precision.
- **The 69** are G.19 consumer credit between 2024-10 and 2026-06, inside the
  Federal Reserve's own revision window. A vintage effect, not a copying error —
  and the feed has no `as_of` on any macro row, so a reader who rechecks one
  today gets a mismatch with no way to tell why. The covering document already
  says *"the macro side has no such stamp"*; this is what that costs.

**And it is not circular.** 400 of 400 delivered values across 20 randomly
sampled bank-quarters match the live FDIC API, so the `ours` side really is the
FDIC's published figure and not something re-derived from the filing we then
"check" it against. 1,171 of 1,171 cited codes agree between the printed
facsimile and the machine-readable copy, across 12 sampled bank-quarters, plus
36 of 36 traced end to end from numbers read off the page.

---

## 2 · The feed understates itself by 5,028 rows

This is the finding neither pass reached. **5,028 of the 8,220 rows published as
unverifiable are in fact verifiable, exactly, from the filings.**

| what it says | rows | what the verifier found |
|---|---|---|
| the form does not carry this line | 114 | **All 114 check out.** True that the 2016 form has no RC-N total row — false that there is nothing to check against. Items 1–8 are printed. Method: derive the composition from 2017Q1 *where the total IS printed*, control-test it (**2,644 of 2,644**), apply it backwards. |
| the FDIC calculates this | 6,080 | **3,800 reproduce at full published precision from filed lines alone.** `EQV`, `LNATRESR`, `NCLNLSR`, `LNRESNCR` at 760 of 760 each — and **`EEFFR` at 760 of 760**. |
| an average the FDIC computes | 760 | **`LNLSGR5`: 704 of 760.** It is a 2-to-5 point average of quarter-end `RCFD5369+RCFDB528`, not an RC-K construction at all. |
| spans a merger | 496 | **410 reproduce arithmetically.** `usable_for_trend = no` is right; `verified = no` claims something stronger than the comparability point it means. Only 86 are genuine FDIC merger restatements. |

Two of these are worth the original session's attention specifically:

**`EEFFR`'s published citation is wrong, not merely incomplete.** It reads
`4093,C232 / 4074,4079`. The formula that reproduces is
`(RIAD4093 − RIADC216 − RIADC232) / (RIAD4074 + RIAD4079)` — it omits
**`RIADC216`, goodwill impairment**. With `C232` alone you get 745 of 760, and
the fifteen failures are exactly the quarters carrying a goodwill impairment
(Truist 2023-12-31: 60.12 published against 86.94 without the term). A reader
following the citation as printed does not land on the number.

**`NTLNLSQR`'s citation names a denominator that does not reproduce it.**
`4635,4605 / 3360` gets 229 of 760; the feed's own `LNLSGR5` gets 544.

---

## 3 · Both DIFFERS confirmed, and they are one event

Huntington National Bank, cert 6560, 2026-03-31 — independently confirmed from
the filing and the live API:

```
                        the filing        FDIC publishes        gap
RBC   (3792)            29,148,027            29,147,082       -945
RWAJ                   206,904,227           206,827,694    -76,533
RBCRWAJ (7205)            14.087690         14.092446440   +0.004746
```

**29,147,082 ÷ 206,827,694 = 14.092446439982066 exactly.** The published ratio
is the published capital over the published risk-weighted assets, and the filing
is internally consistent on its own side. This is **one coherent restatement of
three figures**, not two loose disagreements — which materially strengthens the
amendment hypothesis the row already offers. `RBC1AAJ` is correctly still
verified: the leverage ratio's denominator is average assets, untouched.

`RWAJ` is not among the feed's 105 fields, so the third leg ships unflagged.

---

## 4 · What the second pass broke, and what it inherited

Seven defects were introduced or left open on 8 September by the pass that fixed
the previous nine. Recorded plainly, because the pattern is the point.

**Introduced on 8 September:**

1. **The covering document's roster does not add up.** It prints **0** where
   **114** belongs, and the column sums to 156,767 against a headline of
   156,881 — off by exactly 114. Cause: the delivered wording was changed and
   `build_covering_document.py:76` still counts the *old* string
   (`"did not report this line"`). The workbook's own WHAT WAS PROVEN tab has
   114; only the PDF is wrong. **This is on `main`.**
2. **"Eight of the 87 fields"** — the denominator is now 105, and 10 fields are
   not filed lines (8 ratios + 2 averages). Hard-coded literals at
   `build_covering_document.py:680-688`, unlike every other figure on the page.
3. **The verdict split created a contradiction.** 1,520 `NIMY`/`NTLNLSQR` rows
   say *"the FDIC calculates this from filed lines that are verified here"*
   while the same file declares their denominators *"not lines any bank files"*.
4. **Page 6 misdescribes at least 2,995 rows.** The classifier routes anything
   unmatched into "arithmetic", so 1,520 rows whose entire citation is the
   sentence *"the FDIC's own average; no filed line carries it"* are described
   as *"find each code on the page and do what the signs say"*. Pages 5 and 6
   classify those same 1,520 rows two different ways.
5. **`ERNAST`/`LNLSGR5`'s note records a search of the wrong space** —
   *"every subset of Schedule RC-K was tried"*. `LNLSGR5` is not an RC-K
   construction, and 704 of 760 reproduce once you look where it actually lives.
6. **`EEFFR` was reported as not reproducing.** It reproduces 760 of 760.
7. **The 114 were reported as COULD NOT after being attacked once.** They were
   closeable; the attack was aimed at the facsimile instead of at 2017.

**Inherited, from before:**

- **56 first-quarter rows carry the wrong operation.** Seven `NT*Q` fields across
  8 merger Q1 bank-quarters say *"this filing's year-to-date less the previous
  quarter's"* — in a quarter where the year-to-date **is** the quarter, and
  where their nine sibling flow fields in the *same* row-group correctly say so.
  **46 of the 56 reproduce with no subtraction**; following the note produces
  negative nonsense (First-Citizens 2017Q1 `NTCIQ`: −4,380 by the note's method,
  2,960 correctly, which is the published value).
- **`NTLNLS`** note says *"the filed lines the FDIC adds, summed"*; the citation
  is a subtraction.
- Two spellings of the same first-quarter note, split by field.

---

## 5 · The macro half's own findings

- **The workbook's THE SOURCES tab ships an unfilled template.** Verbatim, for
  FHFA — the second-largest publisher in the feed: *"**0** observations here were
  checked against those files, back to **-**."* 14,160 were checked, and the
  verifier re-derived all 14,160.
- **BLS is never mentioned.** 31,244 rows — 47% of all verified macro
  observations, the single largest publisher — appear nowhere in "who publishes
  what". The tab's own arithmetic confirms the hole: it accounts for 92,020 of
  the 137,424 it claims two tabs earlier, and the missing 45,404 is exactly
  FHFA 14,160 + BLS 31,244.
- **A macro tolerance exists and no delivered document discloses it.**
  `verify_fred_history.py:385` — 0.005, and 0.02 for `TOTALNS`. The covering
  document discusses a tolerance exactly once, the bank capital-ratio one, and
  confesses that it had hidden a real difference. The production diagram on
  page 1 reads **"= difference 0"**. And unlike `bank-values.csv`,
  `macro-observations.csv` carries no source value and no difference column, so
  a reader cannot see the gap even in principle.
- **2,825 macro observations carry TIED with a non-zero difference**; 408 are
  real rather than float noise. The largest relative gap is `CDSP` 2020-01-01 at
  **99.2% of the tolerance** — the same shape as the bank-side failure the
  document confesses on page 4. Defensible here (0.005 is the half-digit of a
  2-decimal publisher), but undisclosed and unaudited.
- **`TOTALNS`'s widened tolerance is avoidable.** The checker reconstructs the
  unadjusted total as revolving + nonrevolving and widens to 0.02 to absorb two
  separately-rounded columns. The Board publishes the NSA total **directly**;
  against that column, **981 of 1,002 exact, no tolerance needed**.
- **The H.8 crosswalk cannot fail.** `verify_new_macro.py:123-146` picks the
  Board series for each FRED id by *which one agrees on the most weeks*, and
  accepts at `hits >= len(common) - 2`. A mapping chosen to maximise agreement
  and then reported as agreement is circular — at most 2 weeks per series can
  ever disagree, by construction. It did not produce a wrong answer: an
  independent description-based mapping landed on the same five Board series and
  reproduced all 10,173. But the check proves less than it appears to.
- **Case-Shiller "no obtainable source" is overstated for the national index.**
  True for the 20 metro series — the feed carries seasonally-adjusted metro
  series and S&P's free release prints only NSA levels and SA percent changes.
  But `CSUSHPINSA`'s level is printed free in every monthly release, and the
  archive at `press.spglobal.com` is public: three releases were pulled without a
  subscription. The honest statement is *"the history is obtainable one release
  at a time, at each month's original vintage"*, not *"S&P sells the history"*.
  The LIMITS tab's *"behind a paywall"* is the sharper overstatement, and
  *"What is free: … That is all"* is false as written.
- **The one S&P row has no retained evidence.** `CSUSHPINSA 2026-06-01 = 336.663`
  is the sole verified S&P row; its records in all three row-files say
  `NO SOURCE FOR THIS PERIOD`, and the workdir holds no copy of the press
  release — no PDF, no HTML, no screenshot, where every Fed and FHFA source is
  retained. The value is right (confirmed against the 25 Aug 2026 release,
  Table 2, 336.66) but **our own chain is broken at that link**, and
  `spglobal.com` returns 403 to any scripted fetch, so it cannot be re-run.
- **`source_url` resolves in all 11 cases and reaches the value in one.** Ten are
  programme landing pages naming no table, column or row. 11,237 rows carry no
  URL at all. LIMITS #3 admits the link is coarser than the check; there is no
  macro equivalent of "check any number yourself".
- **Labels:** `frequency` contradicts the dates for 53 series; for 1,147 rows the
  `publisher` column holds *"no full-history source"*, which is a verification
  status, not a publisher — both series are the Federal Reserve Board's.

---

## 6 · What reproduces

Checked against the delivered files and exact: 19 banks × 40 quarters × 105
fields = 79,800 · 760 filings · 442 amended >90 days after the quarter and 289
>365 · 33 merger quarters, 31 measurable, 15 at ≥10%, largest Truist 2019-12-31
at +100.6% · largest *unflagged* step Morgan Stanley Bank NA 2026-03-31 at
+54.5% with nothing acquired · macro 77,081 across 202 series · 137,424 =
71,580 + 65,844 · 156,881 = 79,800 + 77,081 · page-6 buckets 24,568 / 40,191 /
8,961 / 6,080 · "most are Case-Shiller", 10,090 of 11,237 · all 22 Case-Shiller
checks on each series' genuinely last month · **"2,964 of 2,964 agreeing"**,
recomputed without running our script: 2,964 comparisons, 2,964 agree, 0 differ.

The delivered-equals-checked hop holds on the macro side too: 77,081 of 77,081
records carry an `ours` equal to the delivered value, zero drift.

---

## 7 · What nobody has checked

- **"16 of 19 carry the same legal name."** Not independently confirmed. The 2016
  legal names are in no delivered file and the FFIEC serves the facsimile as a
  JS shell.
- **The 209 exhibits.** Whether they photograph the row their manifest names.
  Local-only by design, so unverifiable from what ships.
- **`ERNAST`.** The averaging convention was established; the point definition
  was not. 760 rows remain genuinely unverified rather than proven unverifiable.
- **`ROAQ`, `NIMY`, `NTLNLSQR`.** Not reproduced, and the FDIC's annualisation
  conventions were not exhausted. Their published 2-decimal precision would make
  a strict tie-out weak in any case.
- **38 `LNLSGR5` rows** need the 2015-12-31 filings, which are not in the workdir.
- **The FDIC API cross-check is a sample** — 20 of 760 bank-quarters. **The PDF
  reading is a sample** — 12 of 760.
- **Whether the publishers are right.** Same limit the document states for
  itself: this proves faithful copying.

---

## The line for the original session

The numbers hold. They have now held under three passes, one of which
reconstructed the comparison from scratch on both halves and went to the
publishers' own files. **What keeps failing is the writing around them** — a
count that was true when it was typed and was not re-derived when the thing it
counted changed; a search reported over the wrong space; a template that shipped
with its placeholder in it; a sentence that was right about four ratios and was
applied to eight.

Every one of the seven defects in §4 was introduced by the pass whose entire
subject was that failure mode. That is not an argument for more care. It is an
argument that any figure a document states about itself has to be computed from
the thing it describes, at build time, or it will drift — which is what this
codebase already says in `build_covering_document.py`'s own docstring, and what
`NOLINE` on line 76 is not doing.
