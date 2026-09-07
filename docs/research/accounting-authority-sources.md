# What a standards record may lawfully hold

**Question:** an agent builds a record of accounting authority and it is stored
in a git repository and shipped as a plugin. May that record hold the *text* of
the authority, or only *citations* to it?

**Researched:** 4 September 2026 · for the standards-desk design
**Re-tested:** 4 September 2026 — automated-access and eCFR questions closed; the
FASB copyright wording is *still* unread, but for a different reason than before:
the allow-list was added and FASB's own origin refuses us anyway (see
"Correction" below)
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

### eCFR: terms for automated access

Checked 4 September 2026. The API is open and needs no key — both
`https://www.ecfr.gov/api/versioner/v1/titles.json` and
`https://www.ecfr.gov/api/admin/v1/agencies.json` return HTTP 200 to a plain
request, and neither carries a rate-limit header or an in-band terms notice.

`https://www.ecfr.gov/robots.txt` reads, in full:

```
# See http://www.robotstxt.org/robotstxt.html for documentation on how to use the robots.txt file

User-agent: *

  Sitemap: https://www.ecfr.gov/sitemaps/sitemap.xml.gz
  Disallow: /search
  Disallow: /recent-changes
  Disallow: /on/
  Disallow: /compare/
  Disallow: /my/
  Disallow: /auth/ofr
  Disallow: /auth/sign_in

  # Don't index developer tool links
  Disallow: /api/renderer/v1/content/
  Disallow: /api/versioner/v1/full/
```

**Read this precisely, because it is easy to over-read.** The two `Disallow`
lines cover the bulk full-text endpoints — including
`/api/versioner/v1/full/`, which is the natural way to pull 26 CFR text. But
they sit under the comment *"Don't index developer tool links"*, and
`robots.txt` binds *crawlers deciding what to index*, not a client calling a
documented API for a specific citation. The endpoints answer direct requests
normally. So this is **not** a prohibition on using the API; it is eCFR saying
it does not want those URLs in search indexes.

The practical rule it does support: **fetch the citations the record needs, do
not crawl the corpus.** Pulling `§ 1.263(a)-3(k)` on demand is ordinary API use;
walking `/api/versioner/v1/full/` across a whole title to build a local mirror is
the behaviour these lines are aimed at.

**Rate limiting exists; its numbers were not readable from here.** Both
developer-documentation pages —
`https://www.ecfr.gov/developers/documentation/api/v1` and
`https://www.ecfr.gov/reader-aids/understanding-the-ecfr/developer-resources` —
answer with `302 Found` to `https://unblock.federalregister.gov/`, the Federal
Register's bot-mitigation landing page. That redirect is itself evidence that
automated clients are throttled and diverted, but **this environment's egress
proxy blocks `unblock.federalregister.gov`, so the page stating the actual
limits could not be opened.** The numeric policy therefore remains unread — see
the not-checked list.

Note the asymmetry, which is useful: eCFR bot-blocks its *HTML documentation*
while serving its *JSON API* normally. The data path the record would actually
use is the one that works.

## AICPA: same posture as FASB

The Code of Professional Conduct and AICPA frameworks are copyrighted, all
rights reserved, with reproduction handled through a permissions desk
(`copyright-permissions@aicpa-cima.com`)
([AICPA Code of Professional Conduct](https://www.aicpa-cima.com/topic/ethics/code-of-professional-conduct)).
Treat as citation-only, same as FASB, absent written permission.

---

## Automated access is a separate question, and FASB answers it at the door

Copyright and scraping are different questions; a site can permit one and forbid
the other. Checked 4 September 2026:

**Neither FASB host publishes a `robots.txt` at all.**

| URL | Result |
|---|---|
| `https://asc.fasb.org/robots.txt` | HTTP **200**, but the body is the Angular single-page-app shell (`<title>FASB Accounting Standards Codification®</title>`, `<app-root></app-root>`) — the SPA catch-all, not a robots file |
| `https://www.fasb.org/robots.txt` | HTTP **404** |

So there is no `robots.txt` directive either granting or refusing crawl
permission. **The refusal is enforced a layer up instead.** Every ASC content
path tried returns an origin-served Cloudflare block:

```
HTTP/2 403
server: cloudflare
cf-ray: a35ebfa5a855d6c9-IAD
set-cookie: __cf_bm=...; Domain=fasb.org; ...

  <title>Attention Required! | Cloudflare</title>
  <h1>Sorry, you have been blocked</h1>
  <h2>You are unable to access fasb.org</h2>
```

— observed on `asc.fasb.org/copyright`, `asc.fasb.org/help`, `asc.fasb.org/`,
`www.fasb.org/copyright` and `www.fasb.org/standards`.

**The answer to "is automated access separately prohibited" is therefore: yes in
practice, though not by `robots.txt`.** FASB runs bot management that refuses
non-browser clients on the content paths. This matters to the design
independently of copyright: **a desk that fetches ASC at answer time — the one
thing §6.3 of the PRD does permit — will be blocked from a datacenter address,**
so "fetch to answer, never cache" is sound as a legal posture but is not
something the software can rely on working unattended.

This *reinforces* the citation-only shape rather than disturbing it. There are
now two independent reasons not to build an ASC-text pipeline: the copyright
notice, and the fact that the door is shut.

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

## Flagged for the PRD — since acted on

> **Resolved in `41c3758`.** Both flags below were raised here and left for
> whoever owns the PRD; that owner acted on them the same day. §6.5 now splits
> the one reason into `source_blocked_by_us` and `source_refuses_us` with
> different fixes, and §10's open question has been rewritten to say the
> allow-list is done and was not enough. **The flags are kept below as written,
> because the reasoning is the part worth keeping** — the finding was that a
> diagnosis whose fix cannot resolve the case is worse than no diagnosis, and
> that is now a rule in the PRD rather than a note in a research file.

`docs/prd-expert-desks.md` **§6.3 stands.** Nothing found on re-test disturbs
"citation only for FASB and AICPA, full text for federal authority." The
automated-access finding *supports* it.

**But §6.5 has a defect this re-test exposed, and it is not this file's to
fix.** That table gives one fix for `source_unreachable`:

> | `source_unreachable` | yes | grant the domain in the environment's network policy |

**That fix is wrong for FASB, and FASB is the case the desk will actually hit.**
`asc.fasb.org` is *already granted and already reachable*; it fails anyway,
because the refusal is Cloudflare's at the origin. A desk that emits
`source_unreachable` and points a human at the network policy sends them to
change a setting that is already correct — and §6.5's own closing line says a
desk that keeps emitting the same fixable reason is reporting a defect in
itself. This one would emit it forever.

The two conditions are genuinely different and want different handling:

| What happened | Signature | Who can fix it |
|---|---|---|
| Egress proxy refuses the domain | structured `EGRESS_BLOCKED` error | the environment's allowed-domains list |
| Origin/CDN refuses the client | HTTP 403 + `server: cloudflare` + `cf-ray` | **nobody, from a container** — needs a human with a browser |

Whether that becomes a second escalation reason or a corrected "fix" column is a
design call for whoever owns the PRD. **Flagged, deliberately not edited.**

§6.3's new *"A failure is handled by its cause"* table makes this sharper, not
softer. It routes **"Denied — 403, blocked, terms forbid automation"** to
`source_unreachable` — correctly, and its *"Never a different client"* rule is
the reason this session stopped rather than dressing up its requests. But that
routing feeds 403s straight into the one fix that cannot resolve them.

### And §10's open question asks the firm for the wrong thing

The PRD's *"Open question (needs you, and only you)"* currently reads:

> Verified blocked by test this session: `asc.fasb.org` and `viewpoint.pwc.com`
> both return `EGRESS_BLOCKED`. Add `asc.fasb.org`, `*.fasb.org`,
> `viewpoint.pwc.com` and `*.aicpa-cima.com` … Until then the FASB restriction
> language is sourced from a search index rather than read at its source.

**Both halves are contradicted by the re-test on 4 September 2026:**

| Claim | What the re-test found |
|---|---|
| `viewpoint.pwc.com` returns `EGRESS_BLOCKED` | **Reachable.** `https://viewpoint.pwc.com/us/en.html` fetched and returned full page content — the site description, its guide catalogue, and its registration terms |
| `asc.fasb.org` returns `EGRESS_BLOCKED` | **Not egress-blocked.** `robots.txt` returned HTTP 200; content paths return a Cloudflare 403 at FASB's origin |
| Allow-listing those domains will let the FASB wording be read | **It will not.** The domain is already allowed and already reachable; the allow-list is not what is refusing |

This is the costly kind of error, because it is an action item pointed at a
human: it asks the firm to go into the network settings and make a change that
would not have the stated effect, and implies the FASB gap closes when they do.
It does not. **That gap needs a person to open the page in an ordinary browser**
— which is, notably, exactly the `signed_in_browser` access method §6.3 already
declares for FASB ASC. The PRD's own model has the right answer; only this
paragraph disagrees with it.

**Flagged, deliberately not edited** — §10 belongs to whoever owns the PRD, and
one of its sentences is addressed to the firm.

---

## Confidence, and what was not checked

**High confidence:** 17 U.S.C. § 105 and the public-domain status of IRC,
Treasury Regulations and IRS publications. Read from the statute itself.

### Correction, 4 September 2026: the reason for the FASB gap was wrong

An earlier revision of this file said the gap existed because **"this session's
network egress proxy blocks `asc.fasb.org`."** **That was true where it was
written and is not true now, and the difference is the finding.**

The original session tested `asc.fasb.org` three times and got a structured
`EGRESS_BLOCKED` on each — the distinctive shape described below. The firm then
added the domain to the environment's allowed-domains list. **A cloud
environment's network policy is loaded when the container is provisioned**, so
the re-test session picked the change up and the original session did not: asked
again at 18:05 UTC, after the re-test had already reached FASB, that first
container still returned `EGRESS_BLOCKED` for the same URL.

So both readings are correct, in different containers, and neither supersedes the
other as a matter of fact. What supersedes it is *time*: the domain is allowed
now. Everything below describes the current state, which is the one that matters.

A re-test on 4 September 2026 establishes:

- `asc.fasb.org` **is** reachable through the egress proxy.
  `https://asc.fasb.org/robots.txt` returned **HTTP 200** with FASB's own
  application shell in the body.
- `https://www.fasb.org/robots.txt` returned a genuine origin **404**.
- The failures on the content pages are **HTTP 403 served by Cloudflare at
  FASB's origin** — `server: cloudflare`, a `cf-ray` header, and a `__cf_bm`
  cookie scoped to `Domain=fasb.org`. That is FASB's bot management refusing
  this client, not the environment refusing the domain.
- The egress proxy, when it *does* block a host, says so in a completely
  different shape — a structured error, as `unblock.federalregister.gov`
  returned during this same session:
  `{"error_type":"EGRESS_BLOCKED","domain":"unblock.federalregister.gov", ...}`.
  No FASB request produced one.

**The practical consequence, so the next session does not waste an
intervention:** adding `asc.fasb.org` or `*.fasb.org` to an allowed-domains
list **will not fix this.** The domain is already allowed and already reachable.
Reading these pages needs a client Cloudflare will accept — a real browser on an
address it does not distrust — or a human opening them by hand. Driving headless
Chromium from this container was attempted and did not get through either.

**This corrects the diagnosis only. It does not disturb the legal finding**, and
at the time it was written it did not raise the confidence level either.

**Superseded within the hour** — see the next section. The firm opened
`asc.fasb.org` in their own browser and read the **License Agreement**, which is
a different and stricter document than the copyright notice, and which settles
the question outright. Confidence there is high. The copyright notice at
`/copyright` does remain unread, and no longer matters: the licence is the
instrument that governs access.

### CLOSED 4 September 2026: the firm read the licence at its source

The gap below is closed. The firm opened `asc.fasb.org` in an ordinary browser
and read the **FAF License Agreement (updated 10.10.24)** — the click-through
that gates the free Codification. It is stricter than the second-hand quote this
file was carrying, and it settles the question in a way the copyright notice
alone did not.

**Confidence: high.** Read at source by the firm, 4 September 2026.

Three operative clauses, quoted narrowly because the agreement is itself FAF's
copyright:

**§3(a)(j) — commercial use.** The licence prohibits use of the Codification
*"for commercial purposes."* **SATC holds no paid subscription** (confirmed by
the firm, 4 September 2026), so the free click-through is the only licence in
force — and it does not cover a practice using ASC in client work at all. This
alone decides the question, before any of the rest.

**§3(b)(i) — artificial intelligence.** Use of any portion of the Codification is
*"expressly prohibited… in connection with any artificial intelligence or machine
learning technology, platform, or other system, or large language models (LLMs)…
**under any circumstances**, including using any documents, content, or materials
in the Codification… **as input into** or for other training or development of
artificial intelligence."*

**§3(b)(iii) — automated means.** Access is prohibited *"via mechanical,
programmatic, robotic, scripted, or any other automated means (including… also
known as 'screen scraping')."* The section closes: *"use of the Codification and
GARS is permitted only via individual users engaged in an active user session for
personal use."*

**What this changes.** The record previously planned `citation_only` for ASC,
allowing a desk to read it live and cache nothing. **That is not available.** Not
the storing, not the reading, and not by a browser instead of a fetcher — §3(b)(i)
covers content reaching a model by any route. The design consequence is a
stricter access value, `human_only`: a source a desk may **cite by reference**
and never read.

**What it does not change, and this is the useful half.** A *citation* — the
string `ASC 360-10-35-4` — is a reference, not Codification content. And the
firm reading ASC in their own session, forming a view, and writing it in their
own words is squarely the personal use the licence contemplates; those words are
the firm's copyright, not FAF's. So `positions/` remains fully available, and it
is the only ASC-adjacent thing that can exist here. A desk answers an ASC
question from the firm's ratified position, cites the paragraph, and anyone
wanting the text opens it themselves.

That is a better artifact than an ingested one: what goes to a client should be
SATC's position with the paragraph behind it, never FASB's prose filtered through
a model.

**Also observed:** `asc.fasb.org` serves CAPTCHAs alongside the Cloudflare bot
management recorded above. Consistent with §3(b)(iii) being enforced rather than
merely stated.

**Superseded:** an earlier revision of this file quoted a FASB restriction on
content being *"reproduced, stored in a retrieval system, or transmitted"* from a
search index and flagged it as unverified. That flag was correct and is now
retired — but note the sentence above is from FASB's **copyright notice**, a
different document from the **License Agreement** quoted here. The licence is the
operative instrument for anyone accessing the Codification, and it is stricter.
The conclusion the file reached on weaker evidence holds, and then some.

**Not checked at all:**

- ~~**The FASB copyright wording, at its source.**~~ **CLOSED 4 September 2026** —
  the firm read the License Agreement at source; see above. The separate copyright
  notice at `/copyright` remains unread, but the licence supersedes it for access
  purposes.
- **The Basic View vs Professional View / academic tiers** — what registration
  requires, and whether the free Basic View's terms differ from the general
  copyright notice. `asc.fasb.org/help` is behind the same Cloudflare 403.
  Nothing about the tiers has been read, and nothing here should be assumed
  about them.
- **eCFR's numeric rate limits.** The `robots.txt` and the open API behaviour
  *were* read (see "eCFR: terms for automated access" above), but the pages
  stating the actual request-rate policy redirect to
  `unblock.federalregister.gov`, which this environment's egress proxy blocks —
  a real `EGRESS_BLOCKED`, unlike the FASB case.
- **State-level authority** entirely — no state DOR or state board material was
  researched.
- **FRF for SMEs specifically.** Inferred from AICPA's general posture, not
  confirmed against its own terms.
- **AICPA's terms at their source.** The posture recorded above came from the
  Code of Professional Conduct landing page; `aicpa-cima.com` was not re-tested
  in this session.
