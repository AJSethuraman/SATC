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

5. **Update the running log (recommend it — don't make the operator remember).**
   If the run produced any **roadmap / deferred / decided-against / cross-cutting
   principle** items (the `[LOG]`-tagged ones from grilling, or any you can see),
   **recommend appending them to the durable running log** — not only to the
   PRD's own Milestones/Non-Goals, which is easy to lose track of. Use this
   repo's existing log, matched to the project area — never a new file:
   - **`PLAN.md`** (SATC / practice-ops): a roadmap phase → `## Recommended
     roadmap`; a decided-against item → `### Explicitly deferred (decided against
     for now)`; a durable decision/principle → a dated entry at the top of
     `## Decisions log`.
   - **`BACKLOG.md`** (credit-risk suite): open items into the numbered sections;
     finished ones into `## Done log`.
   **Offer to make the edit and commit it** in the same breath (sessions are
   ephemeral — an uncommitted log note is lost). Skip this on trivial one-off runs
   with nothing durable.

6. **Hand off.** Tell the user the PRD is ready and that the next step is
   `/to-issues` to break it into buildable slices — or that an agent can build
   from the PRD directly. Offer to commit it so it persists across sessions.

## The bar — close every gap that isn't the user's

Zero follow-up questions needed to build. Run an **assumption audit** over the
draft: for every assumption or gap, sort it into one bucket and act:

- **(A) Researchable external fact** (tax rule, statutory date, holiday calendar,
  API behavior) → settle it with the `research` skill and **cite it** in the PRD.
- **(B) Codebase-answerable** (how a value is stored, a field's exact name, an
  existing convention, whether a path exists) → **read the code and pin it** in
  Implementation Decisions. Call out silent mismatches (a concept stored two
  different ways in two modules) — those are latent bugs, not footnotes.
- **(C) Genuinely the user's** (a preference, a scope/business call, or something
  only they can do — run it on their machine, confirm against real data) → this
  is the *only* bucket allowed under **Open Questions**.

An A or B item in Open Questions means the PRD isn't done — resolve it, don't
park it. Open Questions is for decisions genuinely owed to the user, never for
facts nobody looked up.
