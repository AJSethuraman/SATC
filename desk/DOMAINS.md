# Domains — which body of authority governs a question, and who publishes it

**THIS FILE EXISTS BECAUSE A SEARCH WENT TO THE IRS FOR AN ACCOUNTING QUESTION.**
On 7 September 2026 the firm asked *"how do i know if a lease should be booked as
an asset"*. Every desk refused `authority_absent`, the searcher ran, and it came
back with four passages off irs.gov that **tied out** — re-fetched, matched
character for character, one occurrence each — and proposed admitting them. Every
one was about the TAX question, deduct-as-rent versus capitalise. The firm asked
the BOOK question. The firm:

> *"you don't check the IRS website for coding tips"*

Nothing in the machinery noticed. `authority_absent` reads *"we do not have the
rule yet, go and find it"*, and the truthful refusal was *"this is not a tax
question."* A desk knew its subjects and its sources and never knew which **body
of authority** it spoke for.

---

## What this replaces, and why it is one file

**A source is no longer admitted one at a time.** `SOURCES.md` on each desk says
"eCFR, primary, admitted" — a decision the firm makes per source, which is what
forces a desk per subject and a curator per desk. The firm, 7 September 2026:

> *"i'm trying to avoid a million desk creations which means i always don't want
> to have to personally find every possible source"*

**Tier is not a research finding. It is a property of the publisher.** The body
with authority over a domain publishing its own text is primary; that same body
explaining itself in plain language is secondary; everyone else is tertiary,
however good they are. That rule is written once, here, and the engine applies
it — so a source nobody has seen before gets a tier without anybody being asked.

**The firm still decides two things** and they are not these: which domains the
practice answers in at all, and what the firm does where the authority permits a
choice. The second is a position and lives on a desk. Neither is a source list.

---

## How an entry is read

`Publishes:` are hosts, matched on the registered domain and its subdomains, so
`fasb.org` covers `asc.fasb.org`. A host in no domain's list is **tertiary
everywhere** — usable to FIND authority, never to answer from.

`Explains itself at:` are hosts of the same body's plain-language material.
Secondary: the body's own explanation, which is not the thing that governs.

`Fires on:` puts a question in this domain. Whole words only, same rule as
`SUBJECTS.md`, and for the same reason — substring matching once made
*"extension"* fire on *"extensive"*.

**A question that fires on nothing gets no domain, and that is a refusal rather
than a default.** Guessing the domain is the failure this file exists to stop.

---

## federal-tax · What a taxpayer owes the United States, and when

**Body:** the Internal Revenue Service and the Department of the Treasury, under
Title 26

**Publishes:** irs.gov, ecfr.gov, uscode.house.gov, govinfo.gov, federalregister.gov, ustaxcourt.gov

**Explains itself at:** irs.gov



**ONE INCOME-SIDE PHRASE WAS MISSING, AND THE FIRST FIX ADDED NINETEEN WORDS.**
Found on the fourth question of the first live close, 8 September 2026 — asked
only because the firm challenged the doer with *"Did you ask the desk?"* about
the largest figure in the books. One pair isolated it: *"is an unexplained bank
deposit taxable income?"* reached `federal-tax` on `taxable`, already in this
list; *"are unidentified deposits gross receipts?"* reached **nothing**.

**So `gross receipts` is added, and that is the whole of it.** The first attempt
added eighteen more — `revenue`, `income`, `sales`, `proceeds`, `draw`,
`refund`, `contribution`, `distribution` and the rest of the ordinary nouns of
the income side — and a review of that commit caught what they cost. Measured
on six plain bookkeeping questions, every one classified `federal-tax` **with no
straddle flagged**:

| Question | Fired on |
|---|---|
| Should loan proceeds be recorded as revenue? | `revenue`, `proceeds` |
| How do we record sales in the books? | `sales` |
| Is the owner draw recorded as an expense? | `draw` |
| Which account does the customer refund go to? | `refund` |
| Do we recognise revenue when the invoice is raised? | `revenue` |
| Does that go on the **income statement**? | `income` |

A desk would have answered a balance-sheet question from IRS authority and said
nothing about it. **That is the failure this whole file exists to stop**, and the
`us-gaap` section below already warns about it from the other side: it excludes
`book`, `books` and `accrual` because *"a domain that claims the ordinary words
of accounting swallows every bookkeeping question in the practice."* Six hours
after the firm said *"the point of this is to have it look for sources and
convey and if it is not directly authoritative it would run the opinion by me"*,
the fix pointed the other way.

**THE CAUSE WAS THE TEST, NOT THE LIST.** The desk reported ONE pair. The test
written from it invented five more sentences — *"is this deposit revenue?"*,
*"is a customer refund income to us?"*, *"are loan proceeds receipts?"* — and
then the vocabulary was widened until the inventions passed. A test built from
imagined phrasings is a specification nobody agreed to, and the code obliged it.

**AND THOSE INVENTED SENTENCES REACHING NOTHING IS THE RIGHT ANSWER.** *"Is this
deposit revenue?"* genuinely straddles book and tax; no vocabulary can place it,
and guessing is the original defect. A question that reaches no domain is now
filed by `ask.consult_or_file` and the firm is notified — so narrowing is safe
in a way it was not before the escalation path existed.

**A term of art is added when a real question needs it. Not before.**
`gross income` and `taxable income` are perfectly good tax terms and are
deliberately absent: no measured question required them, and adding vocabulary
nothing asked for is how the list got to nineteen.

**THE PAST PARTICIPLE IS THE FORM A CLOSE IS WRITTEN IN, and it was missing.**
Found in the first live close, 8 September 2026. `"do we deduct or capitalize
them?"` reached `federal-tax`; `"are those deducted or capitalized?"` reached
**nothing**, and two of the three questions that night came back `domain: None`.
Somebody classifying a transaction that has already happened writes the past
tense — every line in a close is something that already happened. With no
domain the wrong-body-of-authority gate is not watching at all, and it did no
harm that night only because every desk reached happened to be a tax desk. The
gate was off and the room happened to be empty.

**Fires on:** deduct, deducted, deducting, deductible, deduction, expense, expensed, expensing, depreciate, depreciated, depreciation, capitalize, capitalized, capitalise, capitalised, capitalizing, capitalising, capitalization, capitalisation, taxable, taxpayer, gross receipts, return, filing, 1099, w-2, schedule c, section 179, safe harbour, safe harbor, de minimis, basis, amortize, amortized, amortizing, amortization, withholding, estimated tax, irs, treasury, revenue ruling, lease, leases, leased, rent, rental

**Why these hosts:** each is the United States Government publishing its own
text, so 17 U.S.C. § 105 puts it in the public domain and it is storable in full.
`irs.gov` appears twice deliberately: the Service publishes both the regulations
it administers and its own plain-language explanations of them, and the second
kind is secondary however official the domain looks. An IRS publication is not
authority a taxpayer may rely on.

---

## us-gaap · What the books say, and what goes on the balance sheet

**Body:** the Financial Accounting Standards Board, through the Accounting
Standards Codification

**Publishes:** fasb.org

**Explains itself at:** fasb.org

**Fires on:** gaap, asc, codification, balance sheet, booked as an asset, book as an asset, book value, right-of-use, operating lease, finance lease, lessee, lessor, impairment, fair value, revenue recognition, lease, leases, leased, disclosure

**Why these hosts:** FASB is the standard-setter the SEC recognises for US GAAP,
so the Codification is the thing that governs and everything written about it is
commentary. **The Codification is licensed**, which is a separate question from
authority and must not be confused with it: it is PRIMARY and it may be
unreadable to a given environment. What a desk may do with it is `access` and
`may_store` on the source; that it governs is settled here.

**WORDS THIS DOMAIN DELIBERATELY DOES NOT CLAIM.** `book`, `books`,
`bookkeeping`, `accrual`, `financial statement` and `financial statements` were
in this list for about an hour, and they put ELEVEN of the desks' own recorded
problems into `us-gaap` — every bank reconciliation on the cash desk, and every
de minimis problem that mentions the books. They are shared vocabulary, not GAAP
vocabulary: *applicable financial statement* is a defined term of
§ 1.263(a)-1(f), a Treasury regulation, and a taxpayer keeps books for tax
purposes too. A domain that claims the ordinary words of accounting swallows
every bookkeeping question in the practice.

**So this list holds terms of art and recognition phrases, not the vocabulary of
the work.** `booked as an asset` is here and `booked` is not, for that reason.

**THE FIRM ON READING RATHER THAN STORING, 7 September 2026:** *"storage does not
matter if we can search for it in the browser... you don't need to store stuff if
you look it up, you can look it up again. if you are allowed to store, all the
better."* So an unstorable primary is not an absent one.
