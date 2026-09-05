# Sources — what this desk is allowed to rely on

Each entry records **what the source is**, how binding it is, how it may be
reached, and what may be copied here from it. `Checked` is the date a person last
confirmed the entry against the source; a citation with no date is a claim about
the present that nobody re-examines.

**Nothing here is a default.** A source missing any field is a parse error rather
than a guess, because a field that was never read and a field that was empty look
identical downstream. Where a source permits storing, `Why` carries the term that
was read to establish it — not a summary of it.

**Two of these three bind and one does not, and the split is the whole desk.**
The regulations settle when the safe harbour applies. They do **not** carry the
number the firm actually uses: the text still reads $500 and defers the current
figure to "published guidance". That figure lives only in S3, which is the IRS
explaining itself and is not authority a taxpayer may rely on. So the dollar
amount — the one thing Q4 asks for — reaches this desk only through non-binding
authority, and that is exactly the case the record calls a position for the firm.

---

## S1 · Treasury Regulation § 1.263(a)-1 — Capital expenditures; in general

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.263(a)-1

**Url:** https://www.ecfr.gov/current/title-26/section-1.263(a)-1

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. It is the section that creates the de minimis safe harbour election at (f), states its two ceilings, its exceptions, its anti-abuse rule and the manner of making it, and it carries eleven worked examples at (f)(7) that state their own conclusions — which is what makes this desk scoreable against answers nobody here wrote. Fetched as XML from the eCFR versioner API at the 2026-01-01 issue and sliced paragraph by paragraph, never retyped. NOTE WHAT IT DOES NOT SAY: (f)(1)(ii)(D) still reads "$500 per invoice (or per item as substantiated by the invoice) or other amount as identified in published guidance". The $2,500 figure is not in this text and must not be attributed to it.

---

## S2 · Treasury Regulation § 1.162-3 — Materials and supplies

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** 26 CFR 1.162-3

**Url:** https://www.ecfr.gov/current/title-26/section-1.162-3

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. It is here because it is the other half of the question a trade-supplier purchase actually raises: an item that is not caught by the safe harbour is not automatically an asset, and (c)(1) is where the regulation says what counts as a material or supply — a component acquired to repair, a consumable, a twelve-month item, or a unit of property costing $200 or less. (f) is the seam back to S1: elect the safe harbour and it governs these amounts instead. Fourteen worked examples at (h) state their own conclusions.

---

## S3 · IRS, "Tangible property final regulations" (irs.gov), page last reviewed or updated 04-Aug-2026

**Tier:** secondary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-05

**Citation prefix:** IRS Tangible Property Final Regulations

**Url:** https://www.irs.gov/businesses/small-businesses-self-employed/tangible-property-final-regulations

**Why:** A work of the United States Government, so 17 U.S.C. § 105 places it in the public domain and it is storable in full. SECONDARY, and deliberately kept so. It is the Service's own plain-language explanation of the final tangibles regulations — not authority a taxpayer may rely on — but it is the only source reachable from here that states the CURRENT de minimis ceiling: "If you don't have an AFS, you may use the safe harbor to deduct amounts up to $2,500 ($500 prior to Jan. 1, 2016) per invoice or item". The regulation itself defers that figure to published guidance and the guidance is Notice 2015-82, which this page cites and links but which was not itself fetched. The revision date recorded above is the one printed on the page as fetched — "Page Last Reviewed or Updated: 04-Aug-2026" — read off the page, not assumed. Because this source does not bind, every problem keyed to it escalates rather than answers, which is the record telling the firm where its decision is required.
