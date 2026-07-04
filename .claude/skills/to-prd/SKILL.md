---
name: to-prd
description: Synthesize the current conversation (typically after a /grill-me session) into a complete, agent-ready PRD — with user stories and identified testing seams — without conducting a fresh interview. Use when the user says "to prd", "write the PRD", "capture this as a spec", or once grilling has reached shared understanding. Fills in PRD_TEMPLATE.md.
---

# To PRD

Capture the understanding already reached in this conversation as a PRD an agent
can build from. **Do not re-interview** — if major questions are still open, say
so and recommend running `/grill-me` first. Assume alignment exists; your job is
to write it down rigorously.

## Process

1. **Analyze the codebase for real.** Explore the area this feature touches.
   Reuse the codebase's existing vocabulary and respect how sibling modules are
   structured (`satc_system/`, `invoice-generator/`, etc.). Ground the spec in
   what's actually there, not assumptions.

2. **Identify testing seams — and confirm them.** Before writing, work out
   *where* this feature will be tested. Rules:
   - Prefer **existing** test seams over inventing new ones.
   - Aim for the **highest** seam in the architecture (test behavior, not
     internals) and the **fewest** seams possible (ideally one).
   - Name the seam(s) explicitly and **confirm with the user** that they match
     expectations before finalizing. This is the single biggest lever on whether
     an agent's build is verifiable.

3. **Write the PRD.** Read `PRD_TEMPLATE.md` at the repo root and fill every
   applicable section. Emphasis:
   - **Problem** and **Solution**: user-centric, plain language.
   - **User Stories**: an extensive numbered list, "As a <actor>, I want
     <capability>, so that <benefit>." These are the backbone.
   - **Implementation Decisions**: modules, interfaces, schemas, API contracts —
     describe shape and behavior, avoid pinning exact file paths; small snippets
     are fine when they encode a decision.
   - **Testing Decisions**: the seam(s) from step 2 and what a good test proves.
   - **Non-Goals / Out of scope** and **Done Criteria**: never leave empty.
   - If it touches tax data / financials / client PII, state masking + handling
     rules explicitly.

4. **Save it** to a sensible path — `docs/prd-<name>.md` in the relevant project
   folder, or a new top-level folder for a new project.

5. **Hand off.** Tell the user the PRD is ready and that the next step is
   `/to-issues` to break it into buildable slices — or that an agent can build
   from the PRD directly. Offer to commit it so it persists across sessions.

## The bar

Zero follow-up questions needed to build. If a section would force an agent to
guess, either resolve it now or list it under **Open Questions** — don't paper
over it. **Before parking anything as an Open Question, check whether it's a
researchable external fact** (a tax rule, a statutory value, an API's real
behavior); if so, invoke the `research` skill to settle it from primary sources
and cite it in the PRD — Open Questions are for genuine product decisions still
owed, not for facts nobody looked up.
