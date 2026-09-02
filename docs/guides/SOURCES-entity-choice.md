# Sources for the entity-choice guide

Every factual claim in `entity-choice.md`, with where it came from. Claims of
practice — the shape of the trade-off, what a decision costs in time — are
listed too, marked as practice, so that nobody later mistakes one for a rule.

> **The pages can now be reached.** This file used to open by saying no primary
> page had been opened at all — `irs.gov`, `tax.ohio.gov` and `ohiosos.gov` were
> blocked by this container's network egress, and every citation was a canonical
> URL found through search with wording taken from a search extract. The firm
> opened the allow-list on 2 September 2026 and the rows are being worked through
> against the pages themselves.
>
> **`ohiosos.gov` is still the exception.** Both Form 610 PDF links return an
> 853-byte "official State of Ohio government website" wrapper rather than the
> document, so nothing on either was ever read. Those citations have been removed
> rather than left looking checked; the Ohio claims now rest on the [Ohio Revised
> Code](https://codes.ohio.gov/ohio-revised-code/section-1706.16), which is
> reachable and states both of them outright.
>
> This page still carries more risk than the two records guides. Those describe
> what a document is and when it arrives. This one describes an election that is
> hard to reverse, so a wrong sentence here costs a reader more. One already did:
> the draft disqualified an owner "living abroad" from holding S corporation
> stock, where the rule is about non-resident aliens. A US citizen in Berlin is
> not one. Both places are corrected.

---

## 01 · An LLC is a state filing

| Claim in the draft | Source |
|---|---|
| An Ohio LLC is formed with the Ohio Secretary of State | [Ohio Revised Code 1706.16](https://codes.ohio.gov/ohio-revised-code/section-1706.16) — "In order to form a limited liability company, one or more persons shall execute articles of organization and deliver the articles to the secretary of state for filing." **THE FORM NUMBER IS OUT OF THE GUIDE, AND THE SOS PDFS NEVER DOWNLOADED.** The row named Form 610; the firm's C048 note asked for this to be generic, so the guide now says only that you form one on the Secretary of State's website. The two `ohiosos.gov` PDF links both come back as an 853-byte "official State of Ohio government website" wrapper rather than the document, so **nothing on either was ever read** — they are removed rather than left looking checked. The claim that survives is the statutory one, below |
| The filing names a statutory agent, at an Ohio address, who takes legal mail for the business | [Ohio Revised Code 1706.16](https://codes.ohio.gov/ohio-revised-code/section-1706.16), which requires the articles to set forth "The name and street address of the limited liability company's statutory agent and a written acceptance of the appointment that is signed by the agent". The row used to quote "upon whom any process, notice or demand" from the Form 610 PDF; that PDF cannot be fetched from here, so the statute is cited instead. Ohio says *statutory agent*, not *registered agent* |
| The LLC exists when the articles are filed | [Ohio Revised Code 1706.16(B)](https://codes.ohio.gov/ohio-revised-code/section-1706.16), verbatim: "A limited liability company is formed when the articles of organization are filed by the secretary of state or at any later date or time specified in the articles of organization." The firm asked on C050 whether this was simply true. It is, and that is the sentence that says so. *Double quotes in this file mean the cited page carries those words; anyone else's wording goes in italics, so the checker never mistakes it for evidence.* |
| An LLC is a state-law structure, and there is no LLC box on a federal return | [Limited liability company (LLC)](https://www.irs.gov/businesses/small-businesses-self-employed/limited-liability-company-llc) — "a business structure allowed by state statute"; the IRS treats an LLC as a corporation, a partnership, or part of the owner's return, depending on members and elections |
| How far the liability protection reaches is a lawyer's question | **Deliberate non-claim.** The guide says what the filing settles and stops. Nothing about the scope of the protection is asserted |
| The state filing does not by itself change the federal return | Same IRS LLC page. Practice for the plain wording |

## 02 · What you already are, if you have never filed anything

| Claim in the draft | Source |
|---|---|
| A one-member LLC is not treated as separate from its owner unless it elects otherwise | [Single member limited liability companies](https://www.irs.gov/businesses/small-businesses-self-employed/single-member-limited-liability-companies), verbatim: an LLC "with only one member is treated as an entity disregarded as separate from its owner, unless it files Form 8832 and affirmatively elects to be treated as a corporation". The page adds the exception the guide does not carry: "for purposes of employment tax and certain excise taxes, an LLC with only one member is still considered a separate entity" |
| A two-or-more-member LLC is a partnership unless it elects otherwise | [LLC filing as a corporation or partnership](https://www.irs.gov/businesses/small-businesses-self-employed/llc-filing-as-a-corporation-or-partnership) — a domestic LLC with at least two members "is classified as a partnership for federal income tax purposes unless it files Form 8832 and elects to be treated as a corporation" |
| A partnership files its own return and sends each owner a K-1 | [Partnerships](https://www.irs.gov/businesses/partnerships); [Instructions for Form 1065](https://www.irs.gov/instructions/i1065) |
| The profit is taxed to the owners whether or not any of it was taken out | [Publication 541, Partnerships](https://www.irs.gov/publications/p541) — a partnership passes profits through to its partners, who include the items on their own returns. **Half-verified.** The pass-through half is on the page. The *whether or not distributed* half is the distributive-share rule and was not confirmed from a primary page here |
| An owner working in the business pays self-employment tax on the profit, both halves of Social Security and Medicare | [Self-employment tax (Social Security and Medicare taxes)](https://www.irs.gov/businesses/small-businesses-self-employed/self-employment-tax-social-security-and-medicare-taxes); [Topic no. 554](https://www.irs.gov/taxtopics/tc554) — the rate covers both the employee and the employer share |

**Figures deliberately absent.** The 15.3% rate, the 92.35% multiplier, the
$400 filing floor and the additional Medicare thresholds are all on those pages
and none of them is in the guide. They date a page and none is needed to make
the point.

## 03 · "S corp" is an election, not a kind of company

| Claim in the draft | Source |
|---|---|
| The election is made on Form 2553 | [About Form 2553](https://www.irs.gov/forms-pubs/about-form-2553); [Instructions for Form 2553](https://www.irs.gov/instructions/i2553) |
| The deadline is two months and fifteen days into the tax year the election is to start from | [Instructions for Form 2553](https://www.irs.gov/instructions/i2553), verbatim: file "No more than 2 months and 15 days after the beginning of the tax year the election is to take effect, or At any time during the tax year preceding the tax year it is to take effect" |
| An LLC filing Form 2553 does not need a second form to be treated as a corporation | [Instructions for Form 2553](https://www.irs.gov/instructions/i2553) — such an entity "is deemed to have made an election to be classified as an association taxable as a corporation as of the effective date of the S corporation election and doesn't need to file Form 8832, Entity Classification Election" |
| No more than 100 owners | [S corporations](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporations) — the requirements list reads "Have no more than 100 shareholders" and "Have only one class of stock" |
| Owners must be individuals, certain trusts or estates — not another company, and not someone who is not a US citizen or resident | **THE GUIDE SAID SOMETHING DIFFERENT FROM THE RULE, AND IT MATTERED.** [S corporations](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporations) lists allowable shareholders as "May be individuals, certain trusts, and estates and May not be partnerships, corporations or non-resident alien shareholders". The draft rendered that last item as "living abroad" in two places. **Those are not the same test.** A US citizen living in Berlin is not a non-resident alien and may hold S corporation stock; the disqualifier is the person's status, not their address. Both places now say "not a US citizen or resident" |
| One class of stock | Same |

**Not claimed.** Late-election relief under Rev. Proc. 2013-30 exists and is
not on the page. A reader who has missed the deadline needs a person, not a
paragraph, and naming relief invites treating the deadline as soft.

## 04 · What changes on the day it starts

| Claim in the draft | Source |
|---|---|
| The business files Form 1120-S and every owner gets a K-1 | [About Form 1120-S](https://www.irs.gov/forms-pubs/about-form-1120-s); [Instructions for Form 1120-S](https://www.irs.gov/instructions/i1120s) |
| An owner who works in the business goes on the payroll and gets a W-2 | [S corporation compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues) — a shareholder who provides services is an employee, and the corporation must treat the payments as wages |
| Payroll brings an EIN, deposits through the year, a quarterly return, an annual one, and W-2s each January | [Employment taxes](https://www.irs.gov/businesses/small-businesses-self-employed/employment-taxes); [About Form 941](https://www.irs.gov/forms-pubs/about-form-941) (quarterly); [Topic no. 759, Form 940](https://www.irs.gov/taxtopics/tc759) (annual, FUTA); [Topic no. 757, deposit requirements](https://www.irs.gov/taxtopics/tc757); [Topic no. 758](https://www.irs.gov/taxtopics/tc758) |
| Ohio wants the wage side — a registration and returns | [Employer withholding](https://tax.ohio.gov/business/employer-withholding); [Employer withholding — registration](https://tax.ohio.gov/help-center/faqs/employer-withholding-registration) — register for a withholding account, then Ohio IT 501 payments and an IT 941 annual reconciliation |
| A city wants it too | [RITA — employer withholding](https://www.ritaohio.com/Businesses) for the RITA municipalities. **Scope not settled — see the open list.** Ohio has hundreds of municipal jurisdictions and three administrations (RITA, CCA, self-administering cities) |
| A late business return is charged a penalty per owner, per month, whether or not tax was owed | [Instructions for Form 1120-S](https://www.irs.gov/instructions/i1120s), verbatim: "For returns on which no tax is due, the penalty is $255 for each month or part of a month (up to 12 months) the return is late or doesn't include the required information, multiplied by the total number of persons who were shareholders in the corporation during any part of the corporation's tax year for which the return is due." That sentence carries all three parts of the claim — per owner, per month, and owed on a return with no tax due. **The figure stays out of the guide**: it is inflation-adjusted annually, so naming it dates the page within twelve months |

## 05 · Reasonable compensation

| Claim in the draft | Source |
|---|---|
| An S corporation must pay a working owner a reasonable wage before paying that owner anything else | [S corporation compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues) — reasonable compensation must be paid to a shareholder-employee for services before non-wage distributions may be made |
| Reasonable means what the same work would cost from someone else, in a business like yours | Same page, which carries the standard from Treas. Reg. 1.162-7(b)(3) — the amount that would ordinarily be paid for like services by like enterprises under like circumstances |
| Set it too low and the IRS can treat what was taken out as wages and charge the payroll tax on it | Same page — the IRS may reclassify non-wage distributions as wages subject to employment taxes, and case law supports it |
| Somebody has to reach the figure, record how, and keep the record | Practice. The IRS page names the factors an examiner weighs; it does not require a memo. Keeping one is the firm's advice, not a rule |
| Nothing on this page sets one | **Practice, and a deliberate non-claim** — a statement about our own page rather than about any source. `assumed.officer_compensation` in `client-documents/registry/fee-schedule.yaml` puts setting or reviewing the figure outside the flat engagement |

**Not claimed.** Widely repeated secondary sources say reasonable compensation
is examined in *every* S corporation audit. That could not be verified from a
primary page and is not on the guide. An earlier draft carried it and it was
cut.

**Not claimed, and it belongs to the other guide.** More-than-2% shareholder
health insurance in W-2 wages is in `good-records-business.md` section 06,
sourced in `SOURCES.md`. Repeating it here would be tenet 5 across pages, which
`tenets.spec.py` now checks over every pair of guides.

## 06 · Where the saving is, and what eats it

| Claim in the draft | Source |
|---|---|
| Only the wage carries Social Security and Medicare tax; what is left after it does not | [S corporation compensation and medical insurance issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues) — distributions are not wages and are not subject to employment taxes |
| A wage is not business profit, so the deduction that applies to business profit does not reach it | [Qualified business income deduction](https://www.irs.gov/newsroom/qualified-business-income-deduction), resting on IRC 199A(c)(4)(A) — reasonable compensation paid to the taxpayer is excluded from qualified business income |
| That deduction is still there to be reduced | **STILL UNVERIFIED, AND SAYING SO.** The claim is that the qualified business income deduction survived past 2025. The [IRS newsroom page](https://www.irs.gov/newsroom/qualified-business-income-deduction) was fetched and does not carry the words that would settle it either way. **Secondary sources only** — see the open list. The guide never names the deduction, a section, or a percentage, so it survives a change in the rate; it would not survive repeal |
| Social Security tax stops at an amount of wages reset every year | [Self-employment tax](https://www.irs.gov/businesses/small-businesses-self-employed/self-employment-tax-social-security-and-medicare-taxes) — the maximum amount of net earnings subject to the Social Security part changes annually. **The figure is deliberately absent** |
| Payroll every pay period, a second return each year, a K-1 per owner | Practice, and it follows from section 04 |

## 07 · When it is the wrong answer

| Claim in the draft | Source |
|---|---|
| A reasonable wage can absorb most of a small profit, leaving little to save on | Practice. It is arithmetic on the two rules above, not a separate rule |
| One owner with no payroll and no March deadline is a real answer | Practice, and a deliberate counterweight. A page that lists only reasons to elect is marketing |
| A fund, another company or someone who is not a US citizen or resident cannot hold the stock | [S corporations](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporations) — "May not be partnerships, corporations or non-resident alien shareholders". A fund is named in the guide because the common ones are partnerships; the page's own category is the partnership, not the fund. **Corrected from "living abroad"** — see the row above |
| One class of stock leaves no room for investor terms | Same. The rule is that outstanding shares must confer identical rights to distribution and liquidation proceeds; differences in voting rights alone are allowed. **The voting carve-out is not in the guide** — it is a term of art and it does not change the answer for a reader raising money |
| Rental profit carries no self-employment tax to start with | [Instructions for Schedule SE](https://www.irs.gov/instructions/i1040sse); [Instructions for Schedule E](https://www.irs.gov/instructions/i1040se), resting on IRC 1402(a)(1) — rentals from real estate are generally excluded from net earnings from self-employment |
| Taking a property back out of a corporation later is taxed as though it had been sold | [LB&I practice unit, Property Distribution](https://www.irs.gov/pub/fatca/int_practice_units/sco_t_010.pdf) — an S corporation distributing appreciated property recognizes gain as if it had sold the property at fair market value, and the gain passes through to the shareholders |
| Money the company borrows gives a shareholder no room to deduct losses; in a partnership it does | [S corporation stock and debt basis](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-stock-and-debt-basis) — basis comes from stock and from loans the shareholder makes to the corporation, not from corporate borrowing, and a guarantee does not create basis. The partnership contrast rests on IRC 752 and [Publication 541](https://www.irs.gov/publications/p541) |

## 08 · Undoing it is slow

| Claim in the draft | Source |
|---|---|
| After the election ends, a new one generally cannot be made for five years without the IRS agreeing | **CITATION MOVED TO A PAGE THAT CAN ACTUALLY BE READ.** It cited `uscode.house.gov`, which is the only source in either file that still cannot be fetched from here — so it was never checked. The same rule is stated in the [Instructions for Form 2553](https://www.irs.gov/instructions/i2553): the IRS generally will not consent to an election effective for "any tax year before the 5th tax year after the first tax year in which the termination or revocation took effect". "See Regulations section 1.1362-5 for details" is the page's own pointer |
| It is a decision about several years | Practice, and it is the sentence the section exists for |

---

## Open — things a person has to answer

1. **`[CONFIRM: no primary page was opened.]`** The blanket caveat at the top.
   Five domains are blocked from this container, `ohiosos.gov` included, so
   every link here was located through search and quoted from extracts. Each
   one needs opening once against the claim beside it. This is the same block
   that gates the two records guides, and it gates this page harder.

2. **`[CONFIRM: does the guide point at the fact that setting an owner's wage
   is hourly work?]`** Section 05 ends "Nothing on this page sets one" and goes
   no further. The price page already carries the line *"Setting what an S
   corporation owner pays themselves."* Marked in the draft.

3. **`[CONFIRM: Ohio's cities.]`** Section 04 says a city wants the wage side,
   which is safe. What a city does with an S corporation owner's *share of the
   profit* is not on the page: Ohio municipal law reaches net profit at the
   business, and the treatment of a shareholder's distributive share turns on
   the municipality. Verified for nothing here. Either confirm the silence or
   supply the treatment for the firm's own catchment. Marked in the draft.

4. **`[CONFIRM: the closing not-advice line.]`** The firm settled that there
   should be one and how it should read — *"it should not be taken as advice on
   a particular return, sure... this is a particular time we can deflect legal
   assurance - it is just helpful free advice. make the wording fairly
   generic."* No sentence was supplied, so one was written: **"This is general
   information, not advice about a particular business."** Two questions on it.
   Are those the words? And do the other two guides now carry the same sentence,
   worded identically — tenet 4 says two things doing the same job look the
   same, and open item 4 in `SOURCES.md` is the same question left open there.
   Marked in the draft.

5. **`[CONFIRM: the deduction on business profit is still permanent.]`** Section
   06 leans on the fact that a wage does not qualify for it. The exclusion of
   reasonable compensation is statutory and verified. Its permanence past 2025
   rests on secondary reporting of the July 2025 act and was not confirmed from
   a primary page. The guide names no section, rate or threshold, so a rate
   change leaves it true; repeal would not.

6. **`[CONFIRM: the whether-or-not-distributed half of section 02.]`** The
   pass-through half is on Publication 541. That a partner is taxed on their
   share whether or not cash came out is the distributive-share rule and was
   not confirmed from a primary page here.

7. **`[CONFIRM: the link target.]`** The draft ends with `/#intake`, which is
   the anchor `website/index.html` carries today. The page has no URL of its
   own; whoever builds it sets one, and adds it to `sitemap.xml`.

---

## Deliberately absent

Recorded here because each was considered and dropped, and a later drafter
should not have to rediscover why.

- **Every figure that resets.** The self-employment rate, the Social Security
  wage cap, the late-filing penalty per owner, the Ohio filing fee. The guide
  describes the mechanism in each case. Nothing on the page goes stale on
  1 January.
- **Any price of ours.** No package price, no hourly rate, not a range. The
  price page owns those.
- **A number anyone should pay themselves**, and any way of arriving at one.
- **C corporations.** Priced on the Businesses tab and absent here. The page
  exists to separate two things a reader has already tangled; a third would
  re-tangle them.
- **Late-election relief**, per section 03 above.
- **The voting-rights carve-out** to the one-class-of-stock rule, per section 07.
- **State-level entity taxes and the pass-through entity election.** Real, and
  a different page's worth of material. Naming it half-way would be worse than
  silence.
- **What the S corporation health insurance rule does to a W-2.** It is in the
  business guide, and repeating it here would break the cross-page check.

---

## Automated pass, 27 August 2026

`docs/guides/verify_sources.py` fetched every page cited here and searched it
for the claim's own load-bearing strings. Two notes specific to this file.

**The Ohio Secretary of State PDFs do not fetch.** `610.pdf` returns 403 to a
script, and the instructions URL returns the site's HTML shell rather than the
document. So **"an Ohio LLC is formed on Form 610" is still unverified** — not
contradicted, just unchecked. A person with a browser can settle it in a
minute, or the form number can come out of the guide, which would cost the
reader little.

**`uscode.house.gov` redirects and returns nothing to the script.** The rows
citing it for the S-election rules are unverified for the same reason. The
same rules are on `irs.gov/instructions/i2553`, which does fetch — repointing
those citations would be better than leaving them on a host that will not
answer.
