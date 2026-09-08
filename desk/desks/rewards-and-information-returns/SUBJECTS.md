# Subjects — what brings this desk into play

`Answered from <source id>` is what makes routing deterministic AND what makes a
citation checkable: it names the subjects that bring a desk into play, and which
source answers each of them. Their union is what routing fires on, so there is no
second list to drift. It matches **whole words only** — substring matching once made
*"extension"* fire on *"extensive"*.

**A subject may be answered from more than one source, and several here are.**
`rebate` is answered from the ruling, from the publication and from the letter
ruling, because all three speak to it; the engine allows a citation from any
source declared for a subject the question touches, so declaring the overlap is
what stops a right answer from a second source being refused. Declaring it
narrowly would have been a lie about the record and a refusal in practice.

**Three brand names are on this list on purpose.** `Venmo`, `PayPal` and
`Cash App` appear in no source this desk holds, and they are not what the
regulation calls anything. They are what the firm calls it — *"I just assume when
the client accepts A Venmo payment that it was revenue"* — and a desk that does
not fire on the word the question is actually asked in is a desk nobody reaches.
What they are declared to answer FROM is § 1.6050W-1, which is the section that
decides whether such a transfer is a third party network transaction at all.

**It under-fires, and that is worth knowing.** The list matches a question's
subject, not its shape, so an inflected form is missed: `defer` does not fire on
`deferring`. Add the inflections that matter rather than loosening the rule.

---

## rewards-and-information-returns · Whether a rebate earned by spending is income, and when a payment to someone creates a Form 1099-NEC obligation

**Records:** taxpayer

*Whose return this is — an individual or a business. Anikeev is a personal return and nothing in this desk said so structurally, which is why the firm held POS1: "we should probably be specifying. Hey this is the individual desk. This is the business desk."*


**Answered from S1:** gross income, accession to wealth, income from whatever source derived

**Answered from S2:** information return, information returns, section 6041, written statement, payee statement, reporting threshold, calendar year, nonemployee compensation

**Answered from S13:** information return, information returns, section 6041A, nonemployee compensation, remuneration, direct sales, calendar year

**Answered from S14:** section 6050W, third party settlement organization, third party network transactions, participating payee, payment card, calendar year

**Answered from S15:** section 6071, nonemployee compensation, calendar year, filing date, filing dates, time for filing, information return, information returns

**Answered from S3:** 1.6041-1, payor, payment card, credit card, credit cards, third party payment network, payment app, payment apps, peer-to-peer, repairman, information return, information returns

**Answered from S4:** 1.6041-3, corporation, corporations, attorneys, attorney, legal services, medical and health care services, merchandise, return of information, information return, information returns

**Answered from S5:** 1.6041-6, form 1099, nonemployee compensation, filing date, filing dates

**Answered from S6:** 1.6050W-1, participating payee, payment settlement entity, third party network transaction, third party network transactions, third party settlement organization, third party payment network, payment card, payment app, payment apps, peer-to-peer, Venmo, PayPal, Cash App

**`peer-to-peer` WAS REGISTERED TO S3 AND NOT TO S6, AND THAT REFUSED THE FIRM'S
OWN RATIFIED POSITION.** POS3 sits on § 1.6050W-1(c)(3) — S6 — and says what to
do when a payment for services shows no evidence of settling through a third
party payment network. On 7 September the close's own question, *"do payments to
individuals create a 1099-NEC obligation? Peer-to-peer payments to individuals
for services can"*, matched only `peer-to-peer` and `1099-nec`, which route to S3
and S11. The desk cited POS3 — correctly, and quoting the firm — and
`engine.serve` refused it `citation_does_not_support`, because no source
answering this question's subjects covers that citation.

**Ratifying a position and not routing to its source is ratifying nothing**, and
that is the same sentence this repository already wrote about admitting a
publisher and not routing to it. A peer-to-peer payment is precisely the case
§ 1.6050W-1(c)(3) decides; the word belongs on both sources, because both are
genuinely on point and the desk should see them together.

**Answered from S7:** rebate, rebates, purchase price, purchase price adjustment, kickbacks, Medicaid, gross receipts, discounts

**Answered from S8:** frequent flyer miles, miles, promotional benefits, promotional items, in-kind, business travel

**Answered from S9:** rebate, rebates, cash rebate, basis, reward, rewards

**Answered from S10:** trade discount, trade discounts, cash discount, cash discounts, discount, discounts, inventory, cost of goods sold

**Answered from S11:** Form 1099-NEC, Form 1099-MISC, Form 1099-K, 1099-NEC, 1099-MISC, 1099-K, box 1a, legal services, attorneys, corporation, corporations

**Answered from S12:** credit card, credit cards, rebate, rebates, reward, rewards, points, cash back

**Judged:** required

*This desk does not serve an answer no second reader has looked at. The firm, on
the docket, 8 September 2026, asked which desks may not serve unjudged:* "The
judge can look at it all I guess?" *— all seven. It is declared here rather than
in the code so lifting it is one line of this file. The engine checks only that
the words the judge quotes are really in what they read; whether those words
carry the conclusion is the judge's call and is recorded, not recomputed.*
