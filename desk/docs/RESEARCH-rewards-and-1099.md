# Q9/Q29 and Q12 — what was found, and what could not be reached

**Two questions from the close, answered against fetched authority on
5 September 2026.** Q9/Q29: are credit-card rewards income? Q12: do payments to
individuals create a Form 1099-NEC obligation?

Everything quoted anywhere in this work is a literal slice of a document that was
fetched on that date; `tools/build_rewards_desk.py` cuts each stored passage
between two anchors and refuses when either is missing, so nothing was retyped.
The desk built from it is `desks/rewards-and-information-returns/` — 12 sources,
47 stored passages, 19 problems, of which **10 grade correct and 9 escalate**.

**This file exists for the other half: what could NOT be reached.** A written
COULD NOT is a result. What follows names every door that was closed, so a person
knows exactly what to open themselves rather than assuming it was covered.

---

## The short answers

### Q9 / Q29 — are credit-card rewards income?

**A reward earned by spending is not income. It is a reduction of the price
paid.** The IRS states it in its own words:

> A rebate received by a buyer from the party to whom the buyer directly or
> indirectly paid the purchase price for an item is an adjustment in purchase
> price, not an accession to wealth, and is not includible in the buyer's gross
> income.
>
> — PLR 201027015, LAW AND ANALYSIS (released 9 July 2010), citing Rev. Rul.
> 76-96, 1976-1 C.B. 23, as modified by Rev. Rul. 2005-28, 2005-1 C.B. 997

**The firm's belief holds. Their phrasing does not.** They said *"card points are
not income they're not taxed they are rebates and you get to just take those
rebates."* The first three clauses are right. **"You get to just take those
rebates" is wrong**, and it is the clause that changes the books: not one source
found treats a rebate as a free-standing amount. Every one makes it a reduction
of what was paid — basis, in Publication 525; the cost recorded in inventory, in
Publication 334. The close booked the rewards to a **Credit Card Rewards income
account**, and that overstates income by the whole of the rewards.

**And there is nothing "for sure" to hand them, which is what they asked for.**
There is **no primary authority** on this at all:

| Where you would look | What is actually there |
|---|---|
| The Code (26 U.S.C. § 61) | Defines gross income. Silent on rebates. |
| Treas. Reg. § 1.61-1 | Same. Silent on rebates, discounts and rewards. |
| Rev. Rul. 76-96 (1976) | The source everyone cites. **Not reachable** — see below. |
| Rev. Rul. 2005-28 | Restates 76-96's holding, and suspends only its *other* half. Secondary. |
| Announcement 2002-18 | A non-assertion, not a holding — and it carves out cash. Secondary. |
| Pub. 525 (2025), Pub. 334 (2025) | Plain-language explanation. Secondary, and written for 2025 returns. |
| PLR 201027015 | The only document applying the rule to a **credit card**. Tertiary — *"may not be used or cited as precedent"*. |

That is why every rewards problem on the desk escalates. The desk is not failing;
it is reporting that this is a call for the firm, and `positions/POS1` is the
proposal waiting for their yes.

**Three limits on the general answer, all of them real:**

1. **It only covers rewards earned by spending.** The rule turns on a rebate
   "from the party to whom the buyer directly or indirectly paid the purchase
   price". A sign-up bonus for opening an account, a referral bonus, or a reward
   for something that is not a purchase does not obviously fit that sentence.
   **Nothing was found that addresses any of them.**
2. **Announcement 2002-18 carves out cash.** The nearest thing the IRS has
   published about benefits earned by spending says only that it "will not
   assert" — and then: *"This relief does not apply to travel or other
   promotional benefits that are converted to cash, to compensation that is paid
   in the form of travel or other promotional benefits, or in other circumstances
   where these benefits are used for tax avoidance purposes."* It is an
   announcement about in-kind travel benefits, not about cash back, so it does
   not decide cash back either way — but anyone reaching for it as proof should
   read that paragraph.
3. **The Tax Court has tested this and the opinion could not be read.** See the
   COULD NOT list.

### Q12 — do payments to individuals create a 1099-NEC obligation?

Every figure below is from a source fetched on 5 September 2026, with the page's
own currency statement given.

| | | |
|---|---|---|
| **Threshold** | **$2,000 or more in any calendar year**, per payee | 26 U.S.C. § 6041(a) — page read 5 Sep 2026, stamped *"Text contains those laws in effect on September 4, 2026"* |
| Effective from | payments made after 31 December 2025 | Pub. L. 119-21 § 70433(a), (f), as noted at 26 U.S.C. § 6041 |
| Indexed | for calendar years after 2026, rounded to $100 | 26 U.S.C. § 6041(h) |
| Same figure for services | § 6041A ties to "the dollar amount in effect … under section 6041(a)" | 26 U.S.C. § 6041A(a)(2) |
| IRS's own statement | *"For tax years beginning after 2025, the minimum threshold amount … increased to $2,000"* | Instructions for Forms 1099-MISC and 1099-NEC (Rev. December 2026) |
| **File with the IRS by** | **January 31** of the following year | 26 U.S.C. § 6071(c); Treas. Reg. § 1.6041-6(b) |
| **Give the payee a statement by** | **January 31** of the following year | 26 U.S.C. § 6041(d) |

> **IT IS NOT $600 ANY MORE, AND THE REGULATION STILL SAYS $600.** Treas. Reg.
> § 1.6041-1 is still titled *"Return of information as to payments of $600 or
> more"* and paragraph (a)(1)(i)(A) still reads $600 — three times in the eCFR
> text as of **2026-09-03**, the most recent issue date the eCFR would serve. The
> regulation has not been conformed to the amended statute. **Read the threshold
> from § 6041(a).** Anybody who checks the regulation and stops gets last year's
> number.

**Who is exempt from receiving one** (Treas. Reg. § 1.6041-3, "Payments for
which no return of information is required"):

- **Corporations** — § 1.6041-3(p)(1). **With two exceptions in the same
  sentence:** payments to a corporation **after 31 December 1997 for attorneys'
  fees**, and **a corporation engaged in providing medical and health care
  services** or in billing and collecting for them. Both of those are reportable.
  (The instructions put it plainly: *"The exemption from reporting payments made
  to corporations does not apply to payments for legal services."*)
- Payments of bills for **merchandise**, telegrams, telephone, freight, storage
  and similar charges — § 1.6041-3(c).
- Rent paid to **rental agents** — § 1.6041-3(d) (the agent reports to the
  landlord).
- Tax-exempt organisations, the United States, a State, a foreign government,
  an international organisation — § 1.6041-3(p)(2)–(8).
- Amounts already reported on **W-2** or under an **accountable plan** —
  § 1.6041-3(a), (h).

**What a payment app's own reporting does to the payer's obligation — it removes
it.** This is the "who cares" answer the firm suspected was there:

> Transactions that are described in paragraph (a)(1)(ii) of this section that
> otherwise would be subject to reporting under both sections 6041 and 6050W are
> reported under section 6050W and not section 6041. … Solely for purposes of
> this paragraph, the de minimis threshold for third party network transactions
> in § 1.6050W-1(c)(4) is disregarded in determining whether the transaction is
> subject to reporting under section 6050W.
>
> — Treas. Reg. § 1.6041-1(a)(1)(iv)

So the payer is relieved **whether or not the app ever issues a Form 1099-K.**
The app's own threshold — **more than $20,000 and more than 200 transactions**
(26 U.S.C. § 6050W(e); Treas. Reg. § 1.6050W-1(c)(4); Instructions for Form
1099-K (Rev. December 2026)) — is expressly irrelevant to the payer's question.
The regulation carries two worked examples on exactly this, one for a card and
one for a network, and both conclude the payor is not required to file.

**But the relief is not "I used an app".** It reaches a *third party network
transaction*, which § 1.6050W-1(c)(3) defines as settlement under an arrangement
where a substantial number of **providers of goods or services** hold accounts
and have agreed to settle for providing them. A personal peer-to-peer transfer is
not obviously settled under such an arrangement. **No source found says what a
payer should do when it cannot tell which rail a transfer went down**, and the
close's payments were peer-to-peer. `positions/POS2` proposes the conservative
reading and flags it as the firm's call.

---

## COULD NOT — named, so nobody assumes it was covered

**Every court opinion.** Five hosts were tried and all five were refused by this
environment's egress policy, with the proxy answering 403 to CONNECT:
`www.ustaxcourt.gov`, `dawson.ustaxcourt.gov`, `www.govinfo.gov`,
`www.courtlistener.com`, `law.justia.com`, `casetext.com`. Per the proxy's own
instructions a policy denial is reported and not retried.

The one that matters:

> **Anikeev v. Commissioner, T.C. Memo. 2021-23** — the Tax Court case that
> tested whether credit-card "Reward Dollars" are income. From secondary
> descriptions the case concerned rewards earned by buying **cash equivalents**
> (Visa gift cards, debit-card reloads, money orders) rather than goods, on the
> reasoning that there is no purchase price to adjust. **The opinion itself was
> not read.** Nothing about it is stored in the desk, and nothing in this file
> should be treated as a statement of what it holds. **A person should open it
> before ratifying POS1.**

**Rev. Rul. 76-96 itself, 1976-1 C.B. 23.** The foundation ruling. 1976
Cumulative Bulletins are not on irs.gov and govinfo is blocked. What is stored is
the IRS's own restatement of its holding inside Rev. Rul. 2005-28, fetched from
`irs.gov/pub/irs-drop/rr-05-28.pdf`. That restatement is precise about scope, and
it corrects a common misdescription: the IRB's finding list says 76-96 was
**"suspended in part"**, not modified in whole, and what is suspended is only the
conclusion that the *manufacturer* may deduct the rebate under § 162 — *"the
Service will not apply, and taxpayers may not rely on, this conclusion while it
is being reconsidered."* The conclusion that the rebate is **not includible in the
customer's gross income** is untouched.

**Any authority on rewards not earned by spending.** Sign-up bonuses, referral
bonuses, and bank account-opening bonuses. Searched for; nothing found on
irs.gov. Not an assertion that none exists — an assertion that none was reached.

**What happens when the purchase was deducted rather than capitalised.** Every
source found tells a *buyer* to reduce **basis** (Pub. 525) or the **cost
recorded in inventory** (Pub. 334). A business that expensed the purchase has no
basis to reduce. **No source was found that says what becomes of the reward in
that case** — whether it reduces the deduction, or is picked up under the tax
benefit rule of § 111. This is the single most practically important gap for a
bookkeeping client, and it is open.

**The 2002 Bulletin in HTML.** `irs.gov/irb/2002-10_IRB` and its article pages
answer 404. Announcement 2002-18 was read from `irs.gov/pub/irs-drop/a-02-18.pdf`
instead, which is the same text from the same site.

**No PDF library was installable**, so PDF text was extracted by a purpose-built
reader inside `tools/build_rewards_desk.py`. Its two known repairs — dropping a
soft hyphen left at a typeset line break, and turning a TJ kerning offset past a
measured threshold into a space — are documented in the source with the
measurement behind each. Every passage it produced was read before storage.

---

## Currency of everything relied on, as read on 5 September 2026

| Source | What the document itself says |
|---|---|
| 26 U.S.C. §§ 6041, 6041A, 6050W, 6071 | "Text contains those laws in effect on September 4, 2026" |
| Treas. Reg. §§ 1.61-1, 1.6041-1, 1.6041-3, 1.6041-6, 1.6050W-1 | eCFR, issue date **2026-09-03** — the latest the API would serve; 2026-09-04 answered 404 naming that date |
| Instructions, Forms 1099-MISC and 1099-NEC | "(Rev. December 2026)", file stamped 30-Jun-2026 |
| Instructions, Form 1099-K | "(Rev. December 2026)", file stamped 19-May-2026 |
| Rev. Rul. 2005-28 | 2005-19 I.R.B. 997, 9 May 2005 |
| Announcement 2002-18 | 2002-10 I.R.B. |
| PLR 201027015 | Release Date 7/9/2010 |
| IRS Pub. 525 | "Publication 525 (2025)", "For use in preparing 2025 Returns" |
| IRS Pub. 334 | "Publication 334 (2025)", "For use in preparing 2025 Returns" |

**Two of those are a year behind the change that matters.** Publications 525 and
334 are the 2025 editions and predate the $2,000 threshold. Neither is cited for
a dollar threshold anywhere in this work, and neither should be.
