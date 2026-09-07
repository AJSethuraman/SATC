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

**Fires on:** deduct, deductible, deduction, depreciate, depreciation, capitalize, capitalise, capitalization, capitalisation, taxable, taxpayer, return, filing, 1099, w-2, schedule c, section 179, safe harbour, safe harbor, de minimis, basis, amortize, amortization, withholding, estimated tax, irs, treasury, revenue ruling, lease, leases, leased, rent, rental

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

**Fires on:** gaap, asc, codification, balance sheet, book, booked, books, bookkeeping, book value, lease, leases, leased, right-of-use, operating lease, finance lease, lessee, lessor, accrual, impairment, fair value, revenue recognition, financial statement, financial statements, disclosure

**Why these hosts:** FASB is the standard-setter the SEC recognises for US GAAP,
so the Codification is the thing that governs and everything written about it is
commentary. **The Codification is licensed**, which is a separate question from
authority and must not be confused with it: it is PRIMARY and it may be
unreadable to a given environment. What a desk may do with it is `access` and
`may_store` on the source; that it governs is settled here.

**THE FIRM ON READING RATHER THAN STORING, 7 September 2026:** *"storage does not
matter if we can search for it in the browser... you don't need to store stuff if
you look it up, you can look it up again. if you are allowed to store, all the
better."* So an unstorable primary is not an absent one.
