# Sources — what this desk is allowed to rely on

Each entry records **what the source is**, how binding it is, how it may be
reached, and what may be copied here from it. `Checked` is the date a person last
confirmed the entry against the source; a citation with no date is a claim about
the present that nobody re-examines.

**Nothing here is a default.** A source missing any field is a parse error rather
than a guess, because a field that was never read and a field that was empty look
identical downstream. Where a source permits storing, `Why` carries the term that
was read to establish it — not a summary of it.

---

## S1 · Treasury Regulation § 1.446-1 — General rule for methods of accounting

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.446-1

**Url:** https://www.ecfr.gov/current/title-26/section-1.446-1

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. IT DEFERS RATHER THAN DECIDES, and that is why it is here: (a)(2) treats a method as clearly reflecting income where it applies GAAP “in accordance with accepted conditions or practices in that trade or business”, and (a)(4) requires the records including “a reconciliation of any differences”. The tax law points at the trade's practice and says nothing about which side of a reconciliation an item belongs on.

---

## S2 · IRS Publication 583 (12/2024) — Starting a Business and Keeping Records

**Tier:** secondary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** IRS Pub. 583

**Url:** https://www.irs.gov/publications/p583

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. SECONDARY, and doubly so. An IRS publication is the Service's own plain-language explanation, not authority a taxpayer may rely on — and this is a TAX publication about an ACCOUNTING convention, so it illustrates the treatment without being the thing that settles it. It is stored because it is what can be reached, not because it governs: the literature that governs is FASB ASC, which is human_only, and every other accounting-side source (fasab.gov, tfm.fiscal.treasury.gov, ffiec.gov, pcaobus.org, gao.gov) is refused by this environment's network policy. That gap is why POS1 exists.
