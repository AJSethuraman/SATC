# PRD: <Project / Feature Name>

> Copy this to start a new PRD (e.g. `docs/prd-<name>.md` inside the relevant
> project folder, or a new top-level folder for a new project). Delete the
> italic prompts as you fill each section. **Optional** sections can be removed
> if they don't apply — keep the doc as short as the work allows. The bar: a
> coding agent could build from this with **zero follow-up questions**.

**Status:** Draft · **Owner:** <name> · **Last updated:** <YYYY-MM-DD>

---

## 1. Problem
*User-centric. What problem, for whom, and what's painful today? Why now?*

## 2. Solution
*User-centric one-paragraph overview of what we're building and how it helps.*

## 3. Goals & Non-Goals
**Goals** — what success looks like:
- 

**Non-Goals / Out of scope** — explicitly excluded (this section prevents an
agent's build from ballooning; never leave it empty):
- 

## 4. User Stories
*Numbered, in "As a <actor>, I want <capability>, so that <benefit>" form. Be
extensive — these are the backbone an agent builds against.*
1. As a <actor>, I want <capability>, so that <benefit>.
2. 

## 5. Requirements
*Number them so they're referenceable; tag priority [P0]=must, [P1]=should,
[P2]=nice-to-have.*
1. [P0] 
2. [P1] 

## 6. Implementation Decisions *(optional but recommended)*
*The technical clarifications an agent shouldn't have to guess: key modules and
their interfaces, data schemas, API contracts, important architecture choices.
Describe behavior and shape — avoid pinning exact file paths. Small code
snippets are fine when they encode a decision.*
- 

## 7. Testing Decisions
*Where does this get tested, and how do we know a test is good? Prefer the
**highest, fewest testing seams** already in the codebase over inventing new
ones — name the seam(s). Reference prior art (how a sibling module is tested).*
- **Seam(s):** 
- **What a good test proves:** 

> **If this touches tax data, financials, or client PII:** state the
> data-handling and masking rules here explicitly — no PII in artifacts. (Match
> the bar set elsewhere in the codebase for sensitive data.)

## 8. Success Metrics
*Concrete, measurable criteria — not vibes.*
- 

## 9. Milestones / Rollout *(optional)*
*Phased plan if large. What ships first (MVP)?*
- **M1 (MVP):** 

## 10. Risks & Open Questions
*Open Questions are **only** for things genuinely owed to the user — a preference,
a scope/business call, or something only they can do (test on their machine,
confirm against real data). Researchable facts and codebase details must already
be closed above, not parked here.*
- **Risk:** 
- **Open question (needs your decision):** 

## 11. Done Criteria
*A concrete checklist meaning "finished and verified." Never leave empty.*
- [ ] Requirements + user stories met
- [ ] Tests added/passing at the named seam(s)
- [ ] Verified by running the real flow, not just tests
- [ ] Docs / README updated
