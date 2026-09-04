# What a standards record may lawfully hold

**Question:** an agent builds a record of accounting authority and it is stored
in a git repository and shipped as a plugin. May that record hold the *text* of
the authority, or only *citations* to it?

**Researched:** 4 September 2026 · for the standards-desk design
**Short answer:** **citations only for FASB and AICPA; full text for anything
federal.** The line is not "free vs paid" — it is who wrote it.

---

## The finding that decides the shape of the record

FASB's copyright notice on the Codification prohibits exactly what a repository
does:

> Content copyrighted by Financial Accounting Foundation, or any third parties
> who have not provided specific permission, **may not be reproduced, stored in
> a retrieval system, or transmitted, in any form or by any means, electronic,
> mechanical, photocopying, recording, or otherwise**, without the prior written
> permission of Financial Accounting Foundation or such applicable third party.

— [FASB ASC copyright notice](https://asc.fasb.org/copyright)

**"Stored in a retrieval system" is the operative phrase.** A git repository is
a retrieval system; so is a vector index, a local cache, and a model context
assembled from either. Copying ASC paragraph text into the record is the
prohibited act on the face of the notice, whether or not anyone would notice.

The same notice carves out the one exception that matters here:

> Financial Accounting Foundation claims **no copyright in any portion hereof
> that constitutes a work of the United States Government.**

A **citation is not the text.** "ASC 360-10-35-4" is a reference — a fact about
where a rule lives — and references are not copyrightable subject matter. The
record can carry the citation, the firm's own words about what it means for the
practice, and the date it was checked. It cannot carry the paragraph.

---

## Federal sources: public domain, storable in full

> Copyright protection under this title **is not available for any work of the
> United States Government**, but the United States Government is not precluded
> from receiving and holding copyrights transferred to it by assignment,
> bequest, or otherwise.

— [17 U.S.C. § 105](https://uscode.house.gov/view.xhtml?req=%28title%3A17+section%3A105+edition%3Aprelim%29)

The legislative intent is explicit that this places such works **in the public
domain**, published or unpublished, where the work was "prepared by an officer
or employee of the United States Government as part of that person's official
duties"
([§ 101 definition, per the ARL issue brief](https://www.arl.org/wp-content/uploads/2015/06/copyright-status-of-government-works.pdf)).

That covers, in full text:

| Source | Status | Where to fetch |
|---|---|---|
| Internal Revenue Code (26 U.S.C.) | Public domain | [uscode.house.gov](https://uscode.house.gov/) |
| Treasury Regulations (26 CFR) | Public domain | [eCFR JSON API](https://www.ecfr.gov/developers/documentation/api/v1) — base `https://www.ecfr.gov`, metadata + content + search, JSON |
| IRS publications, Rev. Ruls., Rev. Procs., notices | Public domain | [irs.gov](https://www.irs.gov/) |
| Federal Register / govinfo | Public domain | [govinfo copyright policy](https://ask.gpo.gov/s/article/What-are-the-copyright-and-use-policies-of-govinfo-content) |

**The one exception to watch:** § 105 bars the government from *originating*
copyright, not from *holding* it by assignment. A federal document that
incorporates third-party copyrighted material by reference (a standard adopted
into a regulation, a table licensed from a publisher) does not launder that
material into the public domain. The carve-out is narrow and rarely bites on
IRC/Treas. Reg. text, but the record should not assume a `.gov` URL is
self-certifying.

## AICPA: same posture as FASB

The Code of Professional Conduct and AICPA frameworks are copyrighted, all
rights reserved, with reproduction handled through a permissions desk
(`copyright-permissions@aicpa-cima.com`)
([AICPA Code of Professional Conduct](https://www.aicpa-cima.com/topic/ethics/code-of-professional-conduct)).
Treat as citation-only, same as FASB, absent written permission.

---

## What this means for the record's shape

Each entry holds four things and never a fifth:

1. **The citation** — `ASC 360-10-35-4`, `Treas. Reg. § 1.263(a)-3(k)`.
2. **The firm's own words** on what position they take and why. This is the
   firm's copyright, not FASB's, and it is the part that is actually useful:
   authority text alone never answers "what do we do here."
3. **The date it was checked**, because standards move and a citation with no
   date is a claim about the present that nobody re-examines.
4. **A link**, so a human can read the source at the source.

For federal authority, the entry *may* additionally quote the text — and quoting
it is worth doing where a phrase is load-bearing, because it removes a
round-trip.

**This also constrains the agent.** A standards desk that fetches ASC text to
answer a question is fine at the moment of answering; one that *caches* it into
the record is the prohibited act. The distinction is storage, not reading.

---

## Confidence, and what was not checked

**High confidence:** 17 U.S.C. § 105 and the public-domain status of IRC,
Treasury Regulations and IRS publications. Read from the statute itself.

**Medium confidence, and the reason:** the FASB restriction language above was
recovered through a search index rather than by fetching
`asc.fasb.org` directly — **this session's network egress proxy blocks
`asc.fasb.org`**, so the copyright page could not be opened and read. The quoted
sentence is consistent across sources and is standard "all rights reserved"
boilerplate, but **it has not been read at its source by this session.** Before
anything is built on it, open <https://asc.fasb.org/copyright> and
<https://asc.fasb.org/help> in a browser and confirm the wording.

**Not checked at all:**

- **The Basic View vs Professional View tiers** — what registration requires, and
  whether the free Basic View's terms differ from the general copyright notice.
  Blocked by the same egress restriction.
- **Whether automated access is separately prohibited.** `asc.fasb.org/robots.txt`
  was not readable from here. Copyright and scraping are different questions and
  a site may permit one and forbid the other.
- **eCFR rate limits and terms.** The API is documented and public; the specific
  request-rate policy was not read (the developer docs redirected through
  `unblock.federalregister.gov`, which suggests rate limiting exists).
- **State-level authority** entirely — no state DOR or state board material was
  researched.
- **FRF for SMEs specifically.** Inferred from AICPA's general posture, not
  confirmed against its own terms.
