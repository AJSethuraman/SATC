# Sources — what this desk is allowed to rely on

Each entry records **what the source is**, how binding it is, how it may be
reached, and what may be copied here from it. `Checked` is the date a person last
confirmed the entry against the source; a citation with no date is a claim about
the present that nobody re-examines.

**Nothing here is a default.** A source missing any field is a parse error rather
than a guess, because a field that was never read and a field that was empty look
identical downstream. Where a source permits storing, `Why` carries the term that
was read to establish it — not a summary of it.

**Two prefixes end in an open parenthesis, on purpose.** `26 CFR 1.274-5` is a
character-for-character prefix of `26 CFR 1.274-5T`, so a citation into the
temporary regulation would resolve to two sources and `record.load` would refuse
the desk. Every citation on this desk names a paragraph, so ending the prefix at
the `(` separates them exactly rather than by which block happens to be read
first.

---

## S1 · Treasury Regulation § 1.274-12 — Limitation on deductions for certain food or beverage expenses paid or incurred after December 31, 2017

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.274-12

**Url:** https://www.ecfr.gov/current/title-26/section-1.274-12

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. THIS IS THE SECTION THAT DECIDES THE PERCENTAGE. (a)(1) sets the three conditions a food or beverage expense must meet at all, (a)(2) caps it at 50 percent, and (c)(2) lists the exceptions that take it back to 100. It is also the paragraph that kills the shortcut: (b)(1) defines food or beverages to cover every item "regardless of whether the food and beverages are treated as de minimis fringes under section 132(e)", so calling something de minimis does not move it off the 50 percent line.

---

## S2 · Treasury Regulation § 1.274-11 — Disallowance of deductions for certain entertainment, amusement, or recreation expenditures paid or incurred after December 31, 2017

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.274-11

**Url:** https://www.ecfr.gov/current/title-26/section-1.274-11

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. This is the 2017 Act disallowance as the regulation actually writes it, and the reason a "meals and entertainment" account cannot answer anything: (b)(1)(ii) says food or beverages are NOT entertainment unless provided at or during an entertainment activity, and that if they are, the separate statement of their cost on the bill is what decides between 50 percent and nothing.

---

## S3 · Treasury Regulation § 1.162-2 — Traveling expenses

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.162-2

**Url:** https://www.ecfr.gov/current/title-26/section-1.162-2

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. § 274 limits a travel cost that is already deductible; this is the section that decides whether it is deductible at all. (a) makes the fares personal where the trip was not undertaken for business, (b)(1) makes the fares turn on whether the trip is primarily business, and (e) disposes of commuting in one sentence.

---

## S4 · Treasury Regulation § 1.274-5 — Substantiation requirements

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.274-5

**Url:** https://www.ecfr.gov/current/title-26/section-1.274-5

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. MOST OF THIS SECTION IS RESERVED to § 1.274-5T and that is why S5 exists beside it, but the part that is live here is the one a bookkeeper actually hits: (c)(2)(iii) is the documentary-evidence rule, including the $75 floor and what a restaurant receipt has to show.

---

## S5 · Treasury Regulation § 1.274-5T — Substantiation requirements (temporary)

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.274-5T

**Url:** https://www.ecfr.gov/current/title-26/section-1.274-5T

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. It carries the element lists that § 1.274-5 reserves to it, and they are the whole of what a bank feed does not have: amount, time, place and business purpose for travel; those plus business relationship for entertainment. (a) is also where the regulation says outright that § 274(d) supersedes Cohan, so an approximation is not a fallback.

---

## S6 · IRS Publication 463 (2025) — Travel, Gift, and Car Expenses

**Tier:** secondary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** IRS Pub. 463 (2025)

**Url:** https://www.irs.gov/publications/p463

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. SECONDARY, and the desk needs it to be. An IRS publication is the Service's own plain-language explanation and not authority a taxpayer may rely on, so an answer resting only on it is the case where authority permits a choice and the choice is the firm's. It is here because it states two things the regulations do not: the 80 percent figure for taxpayers under the Department of Transportation's hours-of-service limits, and the rule that a group taking turns picking up each other's checks for personal reasons deducts nothing. The page reads "Publication 463 (2025), Travel, Gift, and Car Expenses" and "For use in preparing 2025 Returns"; that is the revision actually fetched on 5 September 2026, and it is the newest the site serves.

---

## What was reached and deliberately not stored

`26 CFR 1.132-6` (de minimis fringes) and `26 CFR 1.132-7` (employer-operated
eating facilities) were both fetched clean on 5 September 2026 and are not
sources here. Reachable is not a reason to store. They govern what an employee
excludes from **income**, and this desk answers what the employer **deducts** —
and § 1.274-12(b)(1) has already said that the de minimis characterisation does
not move the deduction. Adding them would have read as thorough and answered a
different question.

`26 CFR 1.274-2` (the pre-2017 entertainment regulation) was not fetched or
stored. § 1.274-11 is the section written for expenditures paid or incurred after
31 December 2017, which is every year this desk will be asked about.
