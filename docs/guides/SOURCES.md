# Sources for the records guides

Every factual claim in `good-records-individuals.md` and
`good-records-business.md`, with where it came from. Claims of practice — how
to send a file, what to write on a receipt — are listed too, marked as
practice, so that nobody later mistakes one for a rule.

> **The pages can now be reached, and are being read.** This file used to open
> by warning that `irs.gov`, `tax.ohio.gov` and `ritaohio.com` were all blocked
> by this container's network egress, so every citation was a URL found through
> search with wording taken from a search extract. The firm opened the egress
> allow-list on 2 September 2026. Every claim below is now being worked through
> against the page itself.
>
> **A row is only checked once its note QUOTES the page.** A paraphrase looks
> like evidence and is not one: `verify_sources.py` reports a row with no quoted
> wording as `UNTESTED`, never as a pass. That distinction exists because the
> first version of the checker did not draw it, called thirty-seven rows verified
> on the strength of a matching year or form number, and passed a claim about
> crypto basis that the cited page contradicts. **The firm caught that, not the
> tool.** Run the checker for the current count; do not trust a remembered one.
>
> **Corrections are recorded in the row, in capitals, not quietly fixed.** Six
> citations have failed against their own page so far, and each one says so
> where a reader will meet it.

---

## `good-records-individuals.md`

### 01 · The forms that come to you

| Claim in the draft | Source |
|---|---|
| W-2s are due to the employee by January 31 | **CITATION REPLACED, AND IT PROVED THE WEEKEND RULE** — the row used to cite a 2023 newsroom tax tip, which says only "The due date to file 2022 Form W-2, Form W-3, and Form 1099-NEC is January 31, 2023". That is the date the employer files with the SSA, not the date the employee gets the form, and the claim is about the employee. The right page is the [General Instructions for Forms W-2 and W-3](https://www.irs.gov/instructions/iw2w3), which says "you must furnish Copies B, C, and 2 of Form W-2 to your employees by February 1, 2027" — February 1, because 31 January 2027 is a Sunday. So the statutory date is January 31 and the current edition of the instructions already shows it moved. This is the rule the guide states rather than a fixed date, and here is the rule visibly operating in the source |
| Brokerage statements are due February 15, later than a W-2 | **READ** — [General Instructions for Certain Information Returns (2025)](https://www.irs.gov/instructions/i1099gi). The Guide to Information Returns gives a recipient date of **February 15** for Form 1099-B, and the same for 1099-DA and 1099-S. **Corrected:** this row previously also claimed the page covers 1099-MISC boxes 8 and 10 and says "including statements furnished as part of a consolidated reporting statement". Neither appears in the document. 1099-MISC is listed at **January 31** to the recipient. The date was right; the detail beside it was not on the page cited. The `**` beside 1099-B's February 15 is a different footnote: March 15 for reporting by trustees and middlemen of WHFITs |
| Form 1095-A comes from the marketplace, early in the year | **CHECKED, AND THE DRAFT WAS CHANGED** — [Health Insurance Marketplace statements](https://www.irs.gov/affordable-care-act/individuals-and-families/health-insurance-marketplace-statements), fetched 27 Aug 2026. The draft said "due to you by January 31". **The string "January 31" does not appear on that page.** What it says is "You will get this form from the Marketplace, not the IRS" and "Early in the year, you may receive one or more forms". The bullet now says what the cited page supports. A January 31 furnishing date may well be right, but it is set elsewhere and this citation does not carry it |
| Advance payments made to the insurer get settled on the return | [Reconciling your advance payments of the Premium Tax Credit](https://www.irs.gov/individuals/reconciling-your-advance-payments-of-the-premium-tax-credit) — "The Marketplace makes advance credit payments directly to the health insurance company to reduce the out-of-pocket cost of the taxpayer's premiums", and "you must file Form 8962 to reconcile the advance payments to the actual amount of the Premium Tax Credit that you are eligible for based on your actual household income and family size". Both halves of the claim are on the page in those words; [Instructions for Form 8962](https://www.irs.gov/instructions/i8962) is the mechanics |
| A partnership or S corporation owes each owner a K-1 by March 15 for a calendar year | [Instructions for Form 1065](https://www.irs.gov/instructions/i1065) — the return is due "by the 15th day of the 3rd month following the date its tax year ended", and the partnership must "prepare and give a Schedule K-1 to each person who was a partner in the partnership at any time during the year". [Instructions for Form 1120-S](https://www.irs.gov/instructions/i1120s) carries the same pair for shareholders |
| Many file for more time and send K-1s in September | **THE OBVIOUS CITATION DID NOT CARRY IT.** [Instructions for Form 1065](https://www.irs.gov/instructions/i1065) mentions only that you "File Form 7004 … to request an extension of time to file" and "by the regular due date of the partnership return" — it never states how long the extension runs, so it cannot support "September". The length is on the [Instructions for Form 7004](https://www.irs.gov/instructions/i7004): "For tax years beginning in 2026, the automatic extension period is 6 months." Six months past March 15 is September 15. The word "many" is the firm's own observation of its own clients and is not a claim about any source |
| The HSA contribution form arrives in May | **READ, AND NOW ON THE WEB PAGE TOO** — the firm supplied this as a PDF; the [HTML edition](https://www.irs.gov/instructions/i1099gi) carries the same Guide to Information Returns table, which lists "5498-SA HSA, Archer MSA, or Medicare Advantage MSA Information" with "All amounts May 31" to the IRS and May 31 to the participant |
| The IRA contribution form arrives in May | **READ — open question closed.** Same document. Form **5498**: to the IRS May 31; to the participant, "For FMV/RMD/SIMPLE IRA contributions, January 31; For all other contributions, **May 31**". The bullet is about contribution forms, so May is right. The nuance the guide does not carry, and does not need to: the account's year-end value reaches you in January, ahead of the contribution figure |

### 02 · The things no form will tell us

| Claim in the draft | Source |
|---|---|
| Older holdings arrive with the cost box empty, because reporting started after a cut-off that differs by kind of security | **CHECKED, AND THE DRAFT WAS CHANGED** — [Instructions for Form 1099-B](https://www.irs.gov/instructions/i1099b), fetched and searched 27 Aug 2026. The draft said "stock from 2011, mutual funds and reinvested dividends from 2012, bonds and options from 2014". **The string "2012" does not appear on that page at all.** What the page says is "Any person that transfers custody of a specified security to a broker after 2010 (after 2011 if the stock is in a regulated investment company and after 2014 for certain debt instruments, options, and securities futures contracts)", and elsewhere "after 2013 for debt instruments, options, and securities futures contracts" in an issuer-return context. Those are cut-offs expressed as "after year X" in two different contexts, and they do not map cleanly onto the three years the draft stated. The bullet now makes the point that is certainly true — the cut-off differs by kind of security, and older holdings arrive with the box empty — and stakes no specific year. **If the firm wants the years back, they need a source that states them in that form** |
| Older holdings arrive with the cost box empty | Same page — brokers were not required to track basis on those, and report them as noncovered |
| The 1099-DA has a cost box, but a broker only has to track cost on assets bought from 2026 onward | **THE FIRM CAUGHT THIS ONE, AND THE TOOL HAD PASSED IT.** The draft said "crypto statements for 2025 sales show what you sold for and not what you paid". [Understanding your Form 1099-DA](https://www.irs.gov/businesses/understanding-your-form-1099-da) says brokers report gross proceeds "(and in some cases, basis for)" digital assets — so the flat "not what you paid" is contradicted by the page cited for it, and the firm could see box 1g, **Cost or Other Basis**, on the form itself. The [instructions](https://www.irs.gov/instructions/i1099da) give the real shape: a digital asset "is a covered security" only if "acquired after 2025", and for "2026 and beyond" there is "mandatory reporting of basis information for digital assets that are covered securities, and voluntary reporting of basis information for digital assets that are noncovered securities". So the box exists, it may be filled in, and on anything bought before 2026 nobody was required to fill it |
| Exchanges start reporting the purchase price for 2026 sales | [Instructions for Form 1099-DA](https://www.irs.gov/instructions/i1099da) — basis reporting is required for certain transactions effected on or after 1 January 2026 |
| A home's basis is what it cost plus improvements, and repairs do not count | [Publication 523, Selling Your Home](https://www.irs.gov/publications/p523) — adjusted basis is cost plus capital improvements, "not including costs of maintenance and repairs" |
| Mileage needs a written record kept as you drive | [Publication 463](https://www.irs.gov/publications/p463) — adequate records, a written record, with the date of each trip recorded "at or near the time of the trips"; [Topic no. 305, Recordkeeping](https://www.irs.gov/taxtopics/tc305) |
| Income with no form behind it still belongs on the return and needs a trail | [Topic no. 305, Recordkeeping](https://www.irs.gov/taxtopics/tc305) — "You must keep records, such as receipts, canceled checks, and other documents that support an item of income, a deduction, or a credit appearing on a return"; [Publication 583](https://www.irs.gov/publications/p583) is the general recordkeeping authority behind it |
| A gift of $250 or more needs a letter from the charity, held before filing | **CITATION REPLACED WITH ONE THAT CARRIES IT.** [Publication 526](https://www.irs.gov/publications/p526) has the section headings but the rule is stated plainly on [Substantiating charitable contributions](https://www.irs.gov/charities-non-profits/substantiating-charitable-contributions): "A donor claiming a deduction of $250 or more is also required to obtain and keep a contemporaneous written acknowledgment for a charitable contribution", and "To be contemporaneous the written acknowledgment must generally be obtained by the donor no later than the date the donor files the return for the year the contribution is made". Both halves of the claim — the size and the timing — are in those two sentences |
| A canceled check alone does not carry a $250 gift | Same page — "The written acknowledgment must state whether the donee provides any goods or services in consideration for the contribution". A canceled check cannot state that, which is why it does not satisfy this rule even though a bank record satisfies the separate cash-contribution one |
| Foreign accounts over $10,000 in aggregate mean a separate report with its own deadline | [Report of Foreign Bank and Financial Accounts (FBAR)](https://www.irs.gov/businesses/small-businesses-self-employed/report-of-foreign-bank-and-financial-accounts-fbar) — the trigger is "if the aggregate value of those foreign financial accounts exceeded $10,000 at any time during the calendar year reported", and the separate report is that "You report the accounts by filing a Report of Foreign Bank and Financial Accounts (FBAR) on Financial Crimes Enforcement Network (FinCEN) Form 114". The April 15 / October 15 dates the row used to assert are **not quoted here**, because the guide does not state them |

### 03 · Where you lived and where you worked

| Claim in the draft | Source |
|---|---|
| Ohio adds a state return, usually a city return, and sometimes a school district one | [Ohio Department of Taxation — Income: School District Tax](https://tax.ohio.gov/help-center/faqs/income-school-district) |
| A city return can be required even when nothing is left to pay | **THE CITED PDF WAS FROM THE 2010 TAX YEAR.** The row pointed at `37Instructions.pdf`, which talks about crediting "your 2010 tax" toward "your 2011 estimate" — a sixteen-year-old document, and the phrase attributed to it is not in it. The live [RITA individual FAQ](https://www.ritaohio.com/Individuals/Faqs?category=I&subcategory=Filing&questionID=6) carries the rule in one sentence: "Residents of RITA municipalities who are 18 years of age and older must file an annual return, even if no tax is due." **Verified for RITA municipalities only** — see the open list |
| The local boxes on a W-2 are what a city return runs on | [RITA Form 37](https://www.ritaohio.com/Media/703125/2025%20FORM%2037.pdf) — wages and tax withheld are listed per municipality from the W-2 |
| Moving means we need the dates | [RITA individual FAQ — "I moved during the year"](https://www.ritaohio.com/Individuals/Faqs?category=I&subcategory=Filing&questionID=6) — the effective date of the move goes on the form; [Ohio SD 100](https://tax.ohio.gov/help-center/faqs/income-school-district) — residency dates per district |

### 04 · How to send it

**All practice, no external source.** A downloaded PDF over a photograph, whole
documents, every page, and nothing with a Social Security number in an email.
The last of these matches what `website/index.html` already tells a visitor
about the intake form.

### 05 · How long to keep it

| Claim in the draft | Source |
|---|---|
| Three years after you file covers most of it | [How long should I keep records?](https://www.irs.gov/businesses/small-businesses-self-employed/how-long-should-i-keep-records) and [Topic no. 305](https://www.irs.gov/taxtopics/tc305), which frames the whole rule as "You must keep records, such as receipts, canceled checks, and other documents that support an item of income, a deduction, or a credit appearing on a return" for as long as the period of limitations runs |
| Six years where income was left off and the amount was more than a quarter of what was reported | **NOW SOURCED — it previously cited no page at all.** [Topic no. 305](https://www.irs.gov/taxtopics/tc305), verbatim: "If you don't report income that you should have reported, and it's more than 25% of the gross income shown on the return, or it's attributable to foreign financial assets and is more than $5,000, the time to assess tax is 6 years from the date you filed the return." The guide states the first branch and not the foreign-asset one |
| Property records run for as long as you own it and three years past the sale | [How long should I keep records?](https://www.irs.gov/businesses/small-businesses-self-employed/how-long-should-i-keep-records) — "Keep records relating to property until the period of limitations expires for the year in which you dispose of the property" |

---

## `good-records-business.md`

| Claim in the draft | Source |
|---|---|
| The IRS's first instruction to a new business is a separate checking account, with every business receipt put through it | [Publication 583, Starting a Business and Keeping Records](https://www.irs.gov/publications/p583), verbatim: "One of the first things you should do when you start a business is open a business checking account", followed by "You should keep your business account separate from your personal checking account". The word "first" in the claim is the publication's own |
| A number in the books with no statement behind it has to be chased down | Practice, resting on [Publication 583](https://www.irs.gov/publications/p583) — books must be supported by documents showing amount and business purpose |
| The year-end set: financial statements, account and loan statements, payroll summary, fixed asset additions, inventory count, owner draws and loans | Practice. The individual items are what the return needs; [Publication 583](https://www.irs.gov/publications/p583) is the general recordkeeping authority behind them |
| Mileage: written, kept as you drive, with date, distance and reason | [Publication 463](https://www.irs.gov/publications/p463) |
| Standard mileage has to be picked in the first year the car is used for the business | [Topic no. 510, Business use of car](https://www.irs.gov/taxtopics/tc510); [Publication 463](https://www.irs.gov/publications/p463) — "to use the standard mileage rate for a car you own, you must choose to use it in the first year the car is available for use in your business" |
| A leased car stays on that method for the whole lease, renewals included | Same — the standard mileage rate must be used "for the entire lease period (including renewals)" |
| Home office: square footage of the room and the house, plus utility, insurance and repair bills | Practice — these are the inputs the return needs. The deduction rules themselves are Publication 587 and are deliberately not described |
| A receipt does not carry who was there or why | [Publication 463](https://www.irs.gov/publications/p463) — documentary evidence must be supported by a record of the business purpose and the business relationship |
| $600 or more to a non-employee usually means a 1099-NEC, due to them and to the IRS by January 31 | [Instructions for Forms 1099-MISC and 1099-NEC](https://www.irs.gov/instructions/i1099mec) — section 6071(c) sets January 31 for both filing and furnishing |
| Ask for a W-9 before the first payment | Practice |
| Schedule C asks on the form whether you made payments that required a 1099 | [Instructions for Schedule C (Form 1040)](https://www.irs.gov/instructions/i1040sc), Line I, verbatim: "If you made any payment in 2025 that would require you to file any Forms 1099, check the 'Yes' box. Otherwise, check the 'No' box." |
| A partnership or corporate return is due March 15 for a calendar year, with owner K-1s due on that date | [Instructions for Form 1065](https://www.irs.gov/instructions/i1065); [Instructions for Form 1120-S](https://www.irs.gov/instructions/i1120s) |
| Past a certain size the return carries a balance sheet | [Instructions for Form 1120-S](https://www.irs.gov/instructions/i1120s) — Schedule B question 11 excepts Schedules L and M-1 where total receipts **and** year-end total assets are each under $250,000. [Instructions for Form 1065](https://www.irs.gov/instructions/i1065) — Schedule B question 4 excepts Schedules L, M-1 and M-2 where total receipts are under $250,000, year-end total assets under $1,000,000, K-1s are furnished on time, and no Schedule M-3 is required. **The thresholds are deliberately not in the guide** — they are a term of art, and the fee schedule's `starting_note` already tells a client "a balance sheet, where one is required" |
| A more-than-2% S corporation shareholder's health insurance belongs in W-2 wages | [S corporation compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues); [Notice 2008-1](https://www.irs.gov/pub/irs-drop/n-08-01.pdf) — the premiums must be reported as wages on the shareholder-employee's W-2 in the same year for the deduction to be available |
| Fixing it after the W-2 has gone out means reissuing forms | Follows from the above. Practice |
| Some tax letters run on a 30-day clock from the date at the top | [Topic no. 652, Notice of underreported income — CP2000](https://www.irs.gov/taxtopics/tc652) — respond within 30 days of the date of the notice, 60 if abroad. **The guide says "some of them", not "all"**, because the window differs by notice |
| Payroll records, four years | **THE CLAIM WAS RESTATED TO MATCH THE PAGE.** The row used to say "four years from when the tax was due or paid", and the note attributed "after the date the tax becomes due or is paid, whichever is later" to this page. That wording is not on it. [Employment tax recordkeeping](https://www.irs.gov/businesses/small-businesses-self-employed/employment-tax-recordkeeping) says: "Keep all records of employment taxes for at least four years after filing the 4th quarter for the year." Four years is right; the clock the guide described starts somewhere else. The guide now says four years without naming a start |

---

## Open — things a person has to answer

Each of these is either unverifiable from here or a decision that is not a
drafter's to make.

1. **`[CONFIRM: Form 5498 for IRA contributions — is its filing deadline
   May 31, like Form 5498-SA?]`** The HSA half of that bullet is sourced. The
   IRA half is not, and the search would not confirm it. Either verify it or
   split the bullet so only the HSA claim carries a date.

2. **`[CONFIRM: does "a city return can be required even when nothing is left
   to pay" hold outside the RITA municipalities?]`** It is verified for RITA,
   which covers roughly half of the Ohio municipalities that levy an income
   tax. CCA and the self-administering cities — Columbus, Cincinnati, Toledo —
   were not checked, and the counts that appear in search results for those
   come from secondary sites rather than from CCA itself. The sentence is
   written to be true of the firm's own catchment; confirm that is the right
   scope for a public page.

3. **`[CONFIRM: does the guide name the upload route?]`** The organizer cover
   letter tells clients to use Encyro. The website has never named it. Section
   04 of the individual guide is written without it and reads fine either way.

4. **`[CONFIRM: does a page like this carry a line saying it is general and not
   advice on a particular return? If so, in whose words?]`** Both drafts are
   silent. `docs/pricing-for-website.md` §4 forbids inventing legal or
   assurance wording, so nothing was invented. This is the firm's call and the
   sentence has to be theirs.

5. **`[CONFIRM: silence on what an S corporation owner pays themselves.]`**
   `fee-schedule.yaml` puts setting or reviewing officer compensation outside
   the engagement, so the business guide says nothing about it. An S corp owner
   searching that phrase is exactly the reader this page would attract, so the
   silence is worth an explicit yes rather than an assumed one.

6. **`[CONFIRM: the link targets.]`** Both drafts end with `/#intake`, which is
   the anchor `website/index.html` actually carries today. The business guide
   also points at the individual guide's retention section. Neither guide has a
   URL of its own yet; whoever builds the pages sets both.

7. **Not claimed, on purpose.** The drafts do not say that a return missing
   Form 8962 is rejected, although that is the common outcome where advance
   payments were made. It could not be verified from a primary page here, so
   the sentence says what the return does rather than what happens if it is
   filed without it.

---

## What reading one source changed

The firm supplied the *General Instructions for Certain Information Returns
(2025)* on 27 August 2026 — the first primary page anyone actually opened. It
covers eight of the claims above. Three findings, worth recording because they
say what this whole verification pass is for.

### 1. The dates in the guide move, and the guide did not say so

The document's own rule, verbatim:

> If any filing due date in these instructions falls on a Saturday, Sunday, or
> a legal holiday, you will be considered to have timely filed if you file by
> the next day that is not a Saturday, Sunday, or a legal holiday. Legal
> holidays for this purpose are legal holidays in the District of Columbia or a
> statewide legal holiday where the return is required to be filed.

Against a calendar, **four of the six dates in section 01 move** in each of the
next two filing seasons:

| Stated | Filing in 2026 | Filing in 2027 |
|---|---|---|
| January 31 | Sat → **Feb 2** | Sun → **Feb 1** |
| February 15 | Sun, then Washington's Birthday → **Feb 17** | Washington's Birthday → **Feb 16** |
| March 15 | Sun → **Mar 16** | Mon — holds |
| May 31 | Sun → **Jun 1** | Memorial Day → **Jun 1** |

February 15 is the one that will keep moving: Washington's Birthday is the
third Monday in February, so the date collides with a weekend or that holiday
in roughly three years out of seven.

The guides now carry the rule rather than a shifted date — "These dates move.
When one falls on a weekend or a federal holiday it becomes the next working
day." A rule needs no maintenance; a hardcoded 17 February would be wrong the
following year, on a page the firm updates occasionally rather than annually.

The document also notes that a leap year does **not** extend a deadline, and
that February 28 stays February 28 rather than becoming February 29.

### 2. An open question closed

Whether Form 5498 for an IRA shares the HSA form's May 31 date. It does, for
contributions. Marked above.

### 3. A citation claimed more than its page carries

The brokerage row cited this page for the February 15 date **and** for covering
1099-MISC boxes 8 and 10 "including statements furnished as part of a
consolidated reporting statement". The date is on the page. The rest is not —
1099-MISC is listed at January 31, and the consolidated-statement phrase does
not appear at all. It came from a search extract that was not this page.

That is the failure mode this file exists to catch, and it took reading one
document to find one instance of it. It is a reason to work through the rest
rather than to trust the pattern.
