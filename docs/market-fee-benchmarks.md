# What other firms charge — a primary source, finally

Every benchmark in `docs/pricing-and-deadlines-basis.md` was read from a search
summary, because the primary pages are unreachable from the machine these notes
are written on. This one is not. The figures below were extracted from the
report itself.

**Source.** National Society of Accountants, *Income and Fees of Accountants
and Tax Preparers in Public Practice*, 2020–2021 Survey Report
([full study, PDF](https://higherlogicdownload.s3.amazonaws.com/NSACCT/725010a8-142f-4092-8b5d-077c2618c728/UploadedImages/Membership/IncomeandFeeSurvey/NSA2020-2021_IncomeandFees_FullStudy.pdf)),
pages 18–23. Figures are **average fees charged by the typical firm**, survey
year **2020**.

**The caveat that governs every number below.** This is 2020 data, read in 2026.
It is five years stale and predates the 2021–2023 inflation. Treat it as the
shape of the market, not as this season's price. Where SATC's number and the
survey's number are close, that is worth knowing; where they are far apart, the
gap is worth explaining before it is worth closing.

---

## Schedules — priced per FORM, not per item

| Schedule | NSA 2020 average | SATC today |
|---|---:|---|
| F (Farm) | $200 | inside Property & Business |
| C (Business) | $192 | $200 full / $65 gig |
| **E (Rental)** | **$145** | **$45 per property** |
| D / 8949 (Gains & losses) | $118 | $45 per statement + $95 if keyed |
| H (Household employment) | $66 | not priced |
| EIC (Earned income credit) | $65 | $150 |
| B (Interest and dividends) | $42 | inside the package |
| SE (Self-employment) | $41 | inside the package |

**The finding that matters, and it answers a question the firm asked:** the
market prices **Schedule E as one form at $145**, not per property. SATC prices
per property at $45 with three inside a package. Those are different shapes, and
the market's shape is the one the firm's own instinct reached for — "is this
resolved by having a minimum charge for rentals that include up to 3 on the
initial charge?" That is the market norm, almost exactly.

Note also **EIC at $65 against SATC's $150**. SATC is 2.3× the market on that
line. There may be a good reason — the due-diligence requirements are real and
the penalty for getting them wrong is $600+ per failure — but it is the largest
single divergence on the sheet and nobody has looked at it.

## Returns

| Return | NSA 2020 average | SATC today |
|---|---:|---|
| 1040, itemised + state | $323 | **Standard $325** |
| 1040, not itemised + state | $220 | **Essentials $200** |
| 1065 (Partnership) | $733 | not set |
| 1120-S (S corporation) | $903 | not set |
| 1120 (C corporation) | $913 | not set |
| 1041 (Fiduciary) | $576 | not offered |
| 709 (Gift) | $421 | not offered |
| 706 (Estates) | $1,289 | not offered |

**Standard at $325 against a market average of $323 is as close as this exercise
gets to a confirmation.** Essentials at $200 is 9% under the market's $220.

**The three blank entity prices now have an anchor.** The workbook's $800 sits
between the survey's $733 partnership and $903 S corporation. The survey says
the firm's instinct was in the right range and that a single price for all three
is not what the market does — it separates them by roughly $170.

## Additional fees — the ones that are not forms

From pages 24 and 26 of the same study. These matter because SATC has an
equivalent for two of them and priced them differently.

| What | Share of firms who charge | Average |
|---|---:|---:|
| Preparing 1099s | 85% | $67.72 |
| Preparing W-2s | 76% | $69.75 |
| **Disorganized or incomplete files** | **78%** | **$165.82** |
| Filing an extension | 42% | $55.94 |
| Expediting a return | 32% | $136.32 |
| Information arriving after a stated deadline | 26% | $116.97, at **16 days** before filing |

**Three things follow.**

**Disorganized files are a flat fee at most firms, and hourly at SATC.** 78%
charge, averaging $166. SATC's `assumed.cleanup` bills the overrun hourly at
$150 instead, which is the same money at 66 minutes and more than it past that.
Neither is wrong — a flat fee is easier to state up front and a meter is fairer
to the client whose file is only slightly untidy — but it is worth knowing SATC
is the minority shape here.

**The materials deadline is more conservative than the market.** SATC set three
weeks (21 days) on 26 August 2026; the firms that charge for late information
set it at 16 days on average. There is room to be stricter later without being
unusual.

**Dependents are not a line item anywhere.** Searched for, and absent: no
per-dependent charge, no Form 2441 fee, no Form 8863 fee. The only
dependent-adjacent figure in the entire study is Schedule EIC at **$65** — the
number SATC has just adopted. See below.

---

## Hourly rates

| Work | NSA 2020 average hourly |
|---|---:|
| Form 1120 (Corporation) | $181.57 |
| Form 1120-S | $179.81 |
| Form 1065 | $177.29 |
| Form 1040, itemised + state | $161.34 |
| Form 1040, not itemised | $153.74 |
| Schedule C | $151.18 |
| **Schedule E (Rental)** | **$149.52** |
| Schedule D / 8949 | $149.95 |
| Schedule B | $144.17 |

**SATC's $150 is the market rate for individual-return work**, to within a
dollar of the Schedule E and Schedule C figures. The principal called that
number soft — "we average about $150 an hour, at least for now" — and it turns
out to be squarely where the market was in 2020. The gap worth noting is at the
top: entity work bills at $177–$182, roughly 20% above the individual rate, and
SATC has one rate for everything.

---

## How the market charges for dependents — it doesn't

The firm asked, 26 August 2026: *"how do people normally charge for dependents?
is it not form based?"*

**It is form based, and more than that: nobody charges for a dependent at all.**
The survey prices sixty-odd forms and schedules and there is no per-dependent
line, no Form 2441 (child and dependent care), no Form 8863 (education
credits). The single dependent-adjacent figure in the study is **Schedule EIC
at $65**.

That makes sense on the tax law rather than on the survey. Since the personal
exemption was eliminated for 2018 and later years, a dependent by itself adds a
name, a taxpayer identification number and a checkbox. What adds *work* is the
credit the dependent unlocks and the **due diligence** the preparer owes on it
— which is Form 8867, and which is exactly the thing already priced at $65.

**The consequence for SATC's own ladder is direct, and it is a decision rather
than a correction.** Starter's gate currently excludes any client with a
dependent. On this evidence that is the wrong test: a W-2 parent claiming the
child tax credit is a Starter return with a checkbox, and the case that costs
real time — earned income credit due diligence — is already its own priced
line. Dropping `has_dependents` from Starter's gate would let that client stay
at $100.

It moves money, so it is the firm's call and not a fix to be applied quietly.

---

## What this does and does not settle

**Settles:** that $150/hour is not low; that Standard is priced at the market;
that the entity bases belong in the $730–$910 band and should differ from each
other; that rentals are normally priced as a form.

**Does not settle:** anything about 2026 prices, since this is 2020 data.
Anything about Ohio specifically — the survey reports by region and those cuts
were not extracted. And it says nothing about the one number that decides
whether any of this is profitable, which is how long the work actually takes.
That is still T-07, and it is still the biggest hole in the sheet.
