# Statistics in the Origination Cube

What each test asks, the arithmetic, what it gives back, what the cube uses it for, and what breaks it.
Written 25 Sep 2026 against the test-design write-up of the same date. Part A is what the cube runs today
(as the write-up describes it; the audit in the next prompt confirms file and line). Part B is what the
next prompt adds. Every number in a worked example was computed by `statistics-examples.py`, kept beside
this file; run it and the numbers must match.

Conventions used throughout:

- **p-value** is the number the write-up calls *Luck alone*: the probability of a gap at least this big
  arising by chance if there were no real difference. Small means hard to get by chance. The reading is
  **significant** (p-value below the bar) or **not significant**; the cube's "worse, but could be luck"
  becomes "worse, not significant."
- **Confidence** 95% means the bar is a p-value below 5%. The 5% is called **α** (alpha).
- **Standard error** is the technical word for the write-up's *wobble*: how far a rate or count computed
  from a sample typically lands from its true value. For a count of rare events it is close to the square
  root of the expected count. 1.96 standard errors is the 95% line, and **z** is a gap measured in
  standard errors. (**Standard deviation** is the spread of a column's values across loans, as on the
  Look tab; standard error is the spread of an estimate, roughly standard deviation ÷ √n.)
- **Two-sided** means the test looks for a gap in either direction. The cube reads both *worse* and
  *better*, so its p-values should be two-sided.
- The **Test 1 book** is the hand-checkable book in the write-up: 4,000 loans in four pockets of 1,000
  (FICO 600 / 700 × Broker / Branch), 50 bad in each pocket except Broker 600 with 150. Book bad rate 7.5%.

---

## Part A — what the cube runs today

### A1. Two-proportion z test — the p-value for a yes/no rate

**Asks.** Is the pocket's bad rate different from the rest's, beyond its standard error?

**Arithmetic.** Pocket: `x1` bad of `n1` loans, rate `p1 = x1/n1`. Rest: `x2` of `n2`, rate `p2`.
If there were no real difference, both would share the pooled rate `p̄ = (x1 + x2) / (n1 + n2)`.

```
SE = √( p̄ (1 − p̄) (1/n1 + 1/n2) )        the standard deviation of the gap under "no difference"
z  = (p1 − p2) / SE                        the gap in standard deviations
p-value = 2 · P(Z > |z|)                   two-sided, from the normal curve
```

**Gives.** `z` and the p-value. |z| ≥ 1.96 is the 95% line.

**For.** Every pocket-versus-rest reading on *Where it bleeds* and the *Grids* for the count rate, before
the many-tests allowance (A2). Also the *loans needed* arithmetic (A3).

**Breaks when.** Two cases.

*Too few expected bad loans.* The formula pretends the count of bad loans lands on a smooth bell curve.
With five or more expected, that is close enough. With one expected, the count can only be 0, 1, 2, 3 —
lumpy, not bell-shaped — and the bell-curve formula hands back p-values that are too small, so it calls
things significant that are not. In B1's example the formula said 0.0015 where the exact answer is 0.012:
eight times too confident. Below the floor, use the exact test (B1).

*A dollar-weighted outcome.* The formula counts loans: `n1` of them, `n2` of them, `x` bad. "Share of
booked dollars that went bad" is not a count of loans. One $400,000 loan going bad moves it as much as
forty $10,000 loans, and the formula would treat that as forty separate pieces of evidence. So it
overstates how sure it can be. The dollar-weighted rates need a test that never counts loans as equal
units — the shuffle test (B2), which only asks how often a dollar gap this big appears when the loans are
dealt out at random. The audit should say what runs there today.

**Worked example, Test 1 book.** Broker 600 (150 of 1,000) against the rest of its band, Branch 600
(50 of 1,000): `p̄ = 200/2000 = 0.10`, `SE = √(0.10 · 0.90 · (1/1000 + 1/1000)) = 0.013416`,
`z = (0.15 − 0.05) / 0.013416 = 7.45`, p-value ≈ 9 × 10⁻¹⁴. Against the rest of the book
(150 of 3,000): `p̄ = 0.075`, `SE = 0.009618`, `z = 10.40`.

### A2. Benjamini–Hochberg — the allowance for many tests

**Asks.** Of the pockets called significant, how many are expected to be chance? Keeps that share at α.

**Arithmetic.** `m` tests in one family. Sort their p-values ascending: `p(1) ≤ p(2) ≤ … ≤ p(m)`.
Find the largest `i` with `p(i) ≤ (i/m) · α`; that test and every smaller p-value are called real.
Equivalently, the adjusted p-value is

```
p_adj(i) = min over j ≥ i of  (m / j) · p(j),   capped at 1
```

and a pocket is called real when `p_adj ≤ α`. The smallest p-value is scaled by `m`, the largest by 1.

**Gives.** The adjusted p-value shown on the tabs.

**For.** Applied within one **family** — one grid, one rate, one comparison. The guarantee (about 5% of
the reds in that family are false) holds per family, so a run with 24 families expects more chance reds
run-wide than one family would. *Check* should print the family count (B9).

**Breaks when.** Not really; it tolerates the ordinary dependence between pockets that share a rest.
A stricter variant (Benjamini–Yekutieli) exists for arbitrary dependence and is more conservative.

**Worked example.** Five p-values 0.001, 0.008, 0.02, 0.04, 0.30 at α = 0.05. Thresholds `(i/5)·0.05`
are 0.01, 0.02, 0.03, 0.04, 0.05. The largest `i` with `p(i) ≤ threshold` is 4 (0.04 ≤ 0.04), so four
are called real. Adjusted: 0.005, 0.020, 0.033, 0.050, 0.300.

### A3. Power — "smallest gap it could show" and "loans needed"

**Asks.** How big a real gap would this pocket catch four times out of five?

**Arithmetic.** Two mistakes are possible: calling a chance gap real (rate α, set by Confidence) and missing a
real gap (rate β). **Power** is `1 − β`, the catch rate; 80% is the usual setting. For a pocket of `n1`
against a rest of `n2` at rate `p2`, the chance of catching a true pocket rate `p1` is

```
power(p1) = Φ( ( |p1 − p2| − 1.96 · SE0 ) / SE1 )
SE0 = √( p̄(1−p̄)(1/n1 + 1/n2) )                 spread under "no difference"
SE1 = √( p1(1−p1)/n1 + p2(1−p2)/n2 )             spread when the gap is real
```

where Φ is the normal curve's cumulative probability. The **smallest gap it could show** (the minimum
detectable effect, MDE) is the smallest `p1` with `power(p1) ≥ 0.80`, found by search; the cube reports it
as the multiple `p1/p2`. **Loans needed** inverts the same formula for `n1` given a target multiple.

**Gives.** A multiple per pocket, and a loan count per target. Never flags anything.

**For.** Reading a clean pocket honestly: "in line" at a small pocket means "not more than X times," not
"fine." Also the suggested *How much worse* line (the median MDE across testable pockets).

**Worked example.** A pocket of 71 loans at the synthetic book's 7.13% rate (expected 5.06 bad) against
the rest of 7,929: the smallest rate caught at 80% power is 16.9%, **2.37×** the rest. The smallest rate
that merely clears the 1.96 line (caught only half the time) is 13.2%, 1.85×. Doubling the pocket to 140
loans brings the MDE to 1.95×; 280 loans, 1.67×.

### A4. The floor — five expected losses

**Not a test**; the validity condition of A1. The textbook rule is that the normal curve describes a count
well enough once the expected count is at least 5 in each group (some texts say 10). Hence *fewest loans* =
5 ÷ book bad rate, and *fewest losses* checks the pocket's own count.

**What it buys.** A p-value from A1 that means what it says.

**What it does not buy.** Detection. A red at the floor is a legitimate red — the 95% line is 1.96
standard deviations whatever the size. But a *clean* reading at the floor only says "not more than about
1.85×," and a real 1.5× pocket is usually missed (A3). The floor's cost is blindness, not false alarms.

**Below it.** The floor is the limit of the *approximate* test, not of testing. B1 (Fisher) and B2
(permutation) need no minimum; the next prompt switches to B1 below *fewest loans* instead of refusing.

### A5. Mantel–Haenszel odds ratio — the split's pooled effect

**Asks.** Across all pockets, how much more often does the high half go bad than the low half, comparing
only within pockets so no loan is ever set against a loan from a different pocket?

**Arithmetic.** Each pocket `h` is a 2 × 2 table:

```
                bad    good
high half       a_h    b_h
low half        c_h    d_h          n_h = a_h + b_h + c_h + d_h

OR_MH = Σ_h (a_h · d_h / n_h)  /  Σ_h (b_h · c_h / n_h)
```

**Odds** are bad ÷ good (7% bad → odds 0.075). An **odds ratio** is the high half's odds divided by the low
half's. When bad rates are small, the odds ratio is close to the plain rate ratio (2.0× rate ≈ 2.1× odds).
Each pocket contributes in proportion to its size; a pocket with a zero cell simply adds nothing to one sum.
Its 95% interval comes from the Robins–Breslow–Greenland variance formula.

**Gives.** One pooled odds ratio with an interval.

**For.** The *Split* tab's headline ("the split finds about 1.84×").

**Breaks when.** The effect is genuinely different across pockets — one number then hides a spread (A8).

**Worked example.** Pocket A: high 8 bad of 100, low 4 of 100 (OR 2.09). Pocket B: high 20 of 200, low
12 of 200 (OR 1.74). `OR_MH = 13.24 / 7.24 = 1.829`. A logistic regression with a pocket dummy (B5) on the
same 600 loans gives 1.828 — the two are the same estimate by different arithmetic.

### A6. Cochran–Mantel–Haenszel test — is the pooled effect significant?

**Asks.** Could an odds ratio this far from 1 come from shuffling within pockets?

**Arithmetic.** In each pocket, the high half's expected bad count if the halves were alike, and its
variance:

```
E_h = (a_h + b_h) · (a_h + c_h) / n_h
V_h = (a_h + b_h)(c_h + d_h)(a_h + c_h)(b_h + d_h) / ( n_h² (n_h − 1) )

CMH = ( Σ_h a_h − Σ_h E_h )²  /  Σ_h V_h        compared to χ² with 1 degree of freedom
```

That is `z²` for the pooled count — the 1.96-standard-errors test again, summed across pockets. The original
1959 test subtracts ½ from the numerator before squaring (continuity correction); the audit should say
which the cube does, and *Check* should name it.

**Gives.** The p-value beside the pooled odds ratio.

**Worked example.** Pockets A and B above: `Σa = 28`, `ΣE = 6 + 16 = 22`, `ΣV = 2.83 + 7.38 = 10.21`,
`CMH = 36 / 10.21 = 3.53`, p-value 0.060.

### A7. Actual against expected — the split's "with a range"

**Asks.** Pooling the high halves, how many bad loans did they have against how many the pockets' own
rates predicted?

**Arithmetic.** `O = Σ_h a_h`, `E = Σ_h E_h` as in A6, ratio `O/E`, range `(O ± 1.96·√ΣV_h) / E`.

**One thing to audit.** If `E_h` uses the pocket's *pooled* rate (both halves together, as in A6), the
high half is partly read against itself and `O/E` understates the gap: in the toy, `O/E = 28/22 = 1.27`
while the rate ratio is about 1.8. Reading the high half against the *low half's* rate
(`E'_h = (a_h + b_h) · c_h / (c_h + d_h)`) gives `28/16 = 1.75`, consistent with the odds ratio. The
write-up's "about 1.84× for a planted 1.8×" suggests the cube already does the latter or prints A5; the
audit should confirm which number sits under which label.

### A8. Cochran's Q — is the gap the same size in every pocket?

**Asks.** Is one pooled number a fair summary, or does the effect differ by pocket?

**Arithmetic.** Per pocket the log odds ratio and its variance, then a weighted spread:

```
θ_h = ln( a_h d_h / b_h c_h )          v_h = 1/a_h + 1/b_h + 1/c_h + 1/d_h        w_h = 1/v_h
θ̄  = Σ w_h θ_h / Σ w_h
Q   = Σ w_h (θ_h − θ̄)²                 compared to χ² with (pockets − 1) degrees of freedom
```

A zero cell needs ½ added to every cell of that pocket before taking logs (Haldane's correction).
`I² = (Q − df) / Q`, floored at 0, is the share of the spread that is more than chance.

**Gives.** A p-value for *disagreement between pockets*. Small: the pockets disagree — the pooled 1.8×
is an average of, say, 3× in some pockets and 1× in others, so show the pocket table, not the single
number. Large: the test could not tell the pockets apart. That happens either because they truly agree,
or because each pocket is too small for the test to see a disagreement. So "not significant" here means
"no evidence the pockets disagree," never "proof they agree" — the same reading as a clean pocket at the
floor (A4).

**Worked example.** Pockets A and B: `Q = 0.061` on 1 df, p-value 0.81. The pooled log odds ratio
0.603 is OR 1.827, matching A5.

### A9. Pearson correlation — is the split column the band in disguise?

**Asks.** Does the split column move with the band column?

**Arithmetic.** `r = Σ(x − x̄)(y − ȳ) / √( Σ(x − x̄)² · Σ(y − ȳ)² )`, from −1 to 1.

**For.** The warning on the *Split* tab (Test 6: a column that is only FICO plus noise).

**Breaks when.** The relationship is not a straight line: a U reads near 0. Spearman's version (the same
formula on ranks) catches any steadily rising or falling relation; neither catches a U. A scatter on the
*Look* tab is the honest check.

### A10. The dollar-rate test — unnamed today

The write-up does not say what test sits behind the p-value for GCO per booked dollar and RANR per booked
dollar; the audit's first job is to find it. If it is a t-test on per-loan ratios, two things are wrong
with it: most loans have GCO of exactly 0 and a few have a large one, so the average's standard error
formula needs far more than 71 loans to be trustworthy; and the cube's rate is a ratio of totals
(`ΣGCO / Σbalance`), which a test on per-loan ratios does not test. B2 replaces it.

### Not tests

The **multiple** (share of losses ÷ share of volume), **excess dollars** (pocket's dollars minus what it
would have at the reference rate), the **materiality ladder**, and the **tie-out** are arithmetic with no
p-value attached. They say how big; the tests above say whether chance could do it.

---

## Part B — what the next prompt adds

### B1. Fisher's exact test — below the floor

**Asks.** The same question as A1, with no approximation.

**Arithmetic.** Fix what is known: `N` loans in pocket + rest, `K` bad among them, `n1` in the pocket.
If the pocket were no different, its bad count `k` would follow the **hypergeometric** distribution —
the odds of drawing `k` bad when you draw `n1` loans at random from `N` of which `K` are bad:

```
P(k) = C(K, k) · C(N − K, n1 − k) / C(N, n1)         C(a, b) = "a choose b"
p-value (two-sided) = Σ P(k) over every k whose P(k) ≤ P(observed k)
```

**Gives.** An exact p-value at any size. It runs a little high (conservative) at tiny sizes; that is the
safe direction.

**For.** Pockets under *fewest loans* — walk 6 defect 8's 50-loan pocket with 29 bad gets a verdict.
Also a cross-check on A1 anywhere.

**Worked example.** Pocket 4 bad of 12; rest 14 bad of 200; so `N = 212`, `K = 18`, `n1 = 12`, expected
bad in the pocket 1.02 (12 × 18 / 212, the rate this test assumes both share).
*(Corrected 26 Sep 2026, with the firm's yes: this said 0.84, which is 12 × 14 / 200, the rest's rate
alone. Either way it is far below 5.)* Hypergeometric probabilities for `k = 0 … 5` are 0.335, 0.395, 0.201, 0.058,
0.0105, 0.0013. `P(4 or more) = 0.0119`; two-sided also 0.0119 (no lower outcome is as unlikely). The
two-proportion z on the same counts says `z = 3.18`, p = 0.0015 — eight times too confident, because
expected bad was about 1, not 5.

### B2. Permutation test — dollar rates, and a cross-check for everything

**Asks.** How often does a gap this big appear when the pocket label is dealt out at random?

**Arithmetic.** Observed gap `g = rate(pocket) − rate(rest)`, each rate a ratio of totals
(`ΣGCO / Σbalance`). Then, `B` times (10,000): shuffle which loans carry the "pocket" label, keeping the
pocket's loan count, recompute `g*`. With a fixed random seed the same extract gives the same answer.

```
p-value = ( #{ |g*| ≥ |g| } + 1 ) / ( B + 1 )
```

The `+1` keeps the p-value from reading exactly 0, which no finite number of shuffles can justify.

**Gives.** "N of 10,000 shuffles," which is the p-value made literal.

**For.** GCO per dollar and RANR per dollar per pocket (replacing A10); a cross-check on A1 and B1. In the
confirmatory run, shuffle *within* pockets so the comparison stays like with like.

**Breaks when.** Resolution: with `B = 10,000` the smallest p is 0.0001, so after the many-tests
allowance a very strong pocket's adjusted p may be capped rather than tiny. That is a floor on how small
the number can print, not a wrong answer.

**Worked example.** A 40-loan pocket with GCO/$ of 2.11% against 400 loans at 5.07%, gap −2.96 points:
3,497 of 10,000 shuffles produced a gap at least that large either way, p-value 0.35. In line.

### B3. K-group Mantel–Haenszel, general association — does the ratio matter, any pattern?

**Asks.** Within pockets, does the bad rate differ across the K ratio groups, in any shape?

**Arithmetic.** Each pocket `h` is a K × 2 table: `n_hk` bad among `R_hk` loans in group `k`; `C_h` bad
and `N_h` loans in the pocket. Expected `E_hk = R_hk · C_h / N_h`. Take the first K − 1 groups:

```
d   = Σ_h ( n_h − E_h )                                           a vector of K − 1 gaps
V   = Σ_h  f_h · ( N_h · diag(R_h) − R_h R_hᵀ ),   f_h = C_h (N_h − C_h) / ( N_h² (N_h − 1) )
Q   = dᵀ V⁻¹ d                                                    compared to χ² with K − 1 degrees of freedom
```

With one pocket, `Q = (N − 1)/N × the ordinary chi-square test` of the K × 2 table — the same thing with
a small-sample factor. With two groups it collapses to A6.

**Gives.** A p-value for "something differs across the groups."

**For.** The confirmatory run's first statistic; the K-group cousin of the split.

### B4. K-group trend — is it a steady climb or fall?

**Asks.** Across the groups in order, does the bad rate go one way?

**Arithmetic.** Give the groups scores `s_k` (1, 2, … K, or the bins' midpoints in log ratio):

```
T    = Σ_h Σ_k s_k ( n_hk − E_hk )
Var  = Σ_h f_h · ( N_h Σ_k s_k² R_hk − ( Σ_k s_k R_hk )² )
Q_t  = T² / Var                                                   compared to χ² with 1 degree of freedom
```

This is the Cochran–Armitage trend test pooled across pockets (Mantel's extension).

**Reading B3 and B4 together.** General says yes and trend says no → the groups differ but not in one
direction: a U or a hump, which a straight-line test would call "nothing."

**Worked example.** Five ratio groups of 100, 400, 500, 400 and 100 loans, bad rates 16%, 3.8%, 4.0%,
3.8%, 16% in one pocket and 10%, 3%, 4%, 3%, 10% in another: general `Q = 66.5` on 4 df, p-value
< 0.0001; trend `Q = 0.000`, p-value 1.00. A monotone climb (8%, 6%, 7%, 10%, 18%) lights both: general
0.0014, trend 0.0011. *(Corrected 26 Sep 2026, with the firm's yes: the group sizes were not given,
and the numbers only come out with these; and 66.47 was printed as 66.4. `statistics-examples.py`
does not compute this example; its own "U-shape planted" example, in section 7, has a trend p of
0.0069, since its U is lopsided.)*

### B5. Logistic regression with bins and strata — per-group sizes with intervals

**Asks.** The same question as B3/B4, and in addition: how much worse is each group than the reference,
with an interval.

**Arithmetic.** For each loan, the log-odds of bad:

```
ln( p / (1 − p) ) = α_pocket + Σ_k β_k · [ loan is in group k ]        reference group omitted
```

`α_pocket` is one constant per pocket (the stratum effect: it soaks up everything that differs between
pockets so that the β's are within-pocket comparisons). Then:

```
odds ratio for group k     = e^{β_k}
95% interval               = e^{β_k ± 1.96 · SE_k}
Wald z                     = β_k / SE_k
block test                 = 2 ( ℓ_with groups − ℓ_without ),   χ² with K − 1 df     (likelihood-ratio test)
```

`ℓ` is the log-likelihood, the fit's score. The block test is the regression's version of B3; the trend
version is the same model with the score `s_k` as one number instead of K − 1 dummies.

**Gives.** The chart: "the ≥ 2.00 group is 2.7× the reference, 95% sure it is between 2.1 and 3.4."

**For.** The per-group display in the confirmatory run; cross-check against B3/B4 to the ninth digit as
the cube does with A1.

**Breaks when.** Hundreds of thin pockets: estimating an `α` for each biases the β's. **Conditional**
logistic regression conditions each pocket's total out instead of estimating it, and is the fix. Also, as
with any regression, a variable entered as a plain number is fitted as a straight line — bin first.

**Worked example** (`scout-vs-measure.py`, a synthetic book with bad odds ×3 above ratio 2.0 and ×2
below 0.1, nothing between). Bins chosen on 40,000 development loans, then the identical test on 15,000
holdout loans:

| group | holdout loans | bad | odds ratio vs 0.25–0.50 | 95% interval | p-value |
|---|---:|---:|---:|---|---|
| < 0.10 | 372 | 48 | 1.77 | 1.26 – 2.49 | 0.001 |
| 0.10–0.25 | 2,583 | 196 | 1.02 | 0.85 – 1.24 | 0.81 |
| 0.25–0.50 | 4,702 | 347 | 1.00 (reference) | | |
| 0.50–1.00 | 4,512 | 322 | 0.93 | 0.79 – 1.10 | 0.39 |
| 1.00–2.00 | 2,192 | 150 | 0.89 | 0.72 – 1.09 | 0.26 |
| ≥ 2.00 | 639 | 106 | 2.66 | 2.07 – 3.42 | 2 × 10⁻¹⁴ |

Both planted values (2× and 3×) sit inside their intervals; the middle groups sit on 1. The block test on
the development set: `2 × (−9388.3 − (−9515.8)) = 255.0` on 5 df.

### B6. Concentration — how much of the stress sits in the group?

**Asks.** If the group were drawn as a line on the book, how big a slice is it and how much of the loss
sits inside it? These three numbers *are* "a pocket of stress" stated in figures; how the line of business
acts on it is theirs.

**Arithmetic**, on the holdout only:

```
flag rate  = loans in the group / all loans                          the size of the slice
capture    = bad loans in the group / all bad loans                  (and the same in GCO dollars)
lift       = bad rate in the group / bad rate overall                how concentrated the stress is
```

**Worked example** (holdout above). Group "ratio ≥ 2": 4.3% of loans carry 9.1% of the bad loans, at
2.13× the book's rate. Group "ratio ≥ 2 or < 0.1": 6.7% of loans, 13.2% of the bad loans, 1.95×. No
group on a single field will ever hold most of the book's losses — most losses sit in ordinary loans
because there are more of them — so the finding is the lift and the dollars, never the share of all
losses.

### B7. Random forest — scouting, not testing

**What it is.** A tree splits the loans wherever a cut on some column best separates bad from good, then
splits each half again, and so on. A forest grows hundreds of trees on random subsets of loans and
columns and averages their votes. It writes no formula and assumes no shape.

**Permutation importance.** On loans the forest did not train on, scramble one column and measure how much
the model's rank-ordering score drops (AUC: the probability that a random bad loan scores above a random
good one; 0.5 is a coin flip). A ranking: what the model leaned on. No direction, no size, no interval,
and biased toward columns with many distinct values.

**Partial dependence.** Set the column to a value `v` for *every* loan, average the predicted bad rate,
repeat across a grid of `v`. The **shape**: where the rate bends. This is where the confirmatory bins come
from.

**For.** Development vintages only, never the holdout. Nominates candidates and locates edges; the
tests above then measure them.

**Worked example** (`scout-vs-measure.py`). Importance: FICO 0.236, income/sales 0.015, loan size and
both noise columns ≈ 0. Partial dependence on the ratio: 11.0% at 0.05, flat at 7.1–7.6% from 0.1 to
1.0 *(corrected 26 Sep 2026, with the firm's yes: this said 7.1–7.4%; the script prints 7.64% at 0.10)*, 8.0% at 1.5, 11.9% at 2.0, 18.8% at 2.5 — two cliffs, at about 0.1 and about 2. The plain logistic
regression on the same data fitted the ratio as a gentle slope (`z = 5.6`), which spreads a 3× cliff
across the whole range and calls the low tail *safer* when it is worse.

### B8. Prevalence — not a test

Loans and dollars per group per pocket, with no p-value attached. A count of the book, so it needs no
holdout and no confidence level. It is the first finding whenever the line of business believes a pattern
is rare.

### B9. Pocket budget and family count — Check's two new lines

**Budget.** From A4: at the suggested floor a testable pocket needs 5 expected bad loans, so the most
pockets an extract can test is `expected bad loans ÷ 5` (8,000 loans at 7.13% → 114; 60,000 at 1.2% →
144), and fewer in practice because loans never spread evenly. Print it beside the pocket count Control
asks for, and the **coverage** — the share of loans and dollars that sit in testable pockets.

**Family count.** How many grid × rate × comparison families the run contains (A2), with one line saying
that a single red across many families is weak evidence.

---

## Which test, where

| Rate | Pocket at or above the floor | Pocket below the floor | Pooled across pockets |
|---|---|---|---|
| Bad, share of loans | A1, then A2 | B1 | A5 + A6 (two groups); B3 + B4 or B5 (K groups) |
| Bad, share of booked dollars | B2 | B2 | B2 within pockets |
| GCO per booked dollar | B2 | B2 | B2 within pockets |
| RANR per booked dollar | B2, on the difference in points, never a multiple | B2 | B2 within pockets |
| Effect the same in every pocket? | | | A8 |
| Split column just the band? | | | A9, and the Look tab's scatter |
| How concentrated is the stress? | | | B6 — holdout only |
| What to test in the first place? | | | B7, B8 — development only |
