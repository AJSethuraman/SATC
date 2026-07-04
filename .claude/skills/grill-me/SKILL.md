---
name: grill-me
description: Turn a rough project or feature idea into a complete, agent-ready PRD by interrogating the user until every gap, assumption, and edge case is resolved. Use when the user wants to spec out new work, start a new project, write a PRD, or says "grill me". Produces a filled-in PRD from PRD_TEMPLATE.md that a coding agent can execute without hand-holding.
---

# Grill Me → Agent-Ready PRD

Your job is to extract a complete, unambiguous spec out of the user's head and
write it into a PRD an autonomous coding agent could pick up and build from
**without further clarification**. Do the thinking-work of finding the gaps so
the user doesn't have to. This is an interview, not a form to hand over.

## Process

1. **Read `PRD_TEMPLATE.md`** at the repo root — that's the output shape. Also
   skim `CLAUDE.md` so your questions fit this codebase's stacks and constraints.

2. **Get the one-liner.** Ask the user for the rough idea if they haven't given
   it. Restate it back in one sentence to confirm you understand before grilling.

3. **Grill in focused rounds.** Use the `AskUserQuestion` tool. Ask about the
   things that most change what gets built — a few questions at a time, not a
   wall. Prioritize by leverage:
   - **Problem & who it's for** — what's painful today, internal firm use or
     client-facing, who literally uses it.
   - **Scope boundaries** — what's explicitly *out*. Pin non-goals hard; this is
     where agent-built PRs balloon into 23k-line surprises.
   - **Requirements** — the must-haves (P0) vs nice-to-haves (P2). Force ranking.
   - **Data sensitivity** — if it touches tax data, financials, or client PII,
     nail the handling/masking rules explicitly (match the bar set by DEA's
     safety boundaries and Invoicer's payment handling).
   - **Success & done** — how we'll know it worked; concrete done-criteria.
   - **Constraints** — stack, deploy target, anything it must / must not use.

4. **Push back.** When an answer is vague ("it should be fast", "handle
   documents"), ask the sharpening follow-up ("fast = under what, on what?",
   "which formats, how many at once, what happens on a bad file?"). Surface
   assumptions the user hasn't stated and get a ruling. Keep going until you
   could hand the spec to a stranger and they'd build the same thing you would.

5. **Stop when it's tight, not when it's long.** A short PRD with no ambiguity
   beats a long one full of hedges. Don't invent scope to fill sections —
   drop optional sections that don't apply.

6. **Write the PRD.** Copy `PRD_TEMPLATE.md` to a sensible path — `docs/prd-<name>.md`
   inside the relevant project folder, or a new top-level folder for a brand-new
   project — and fill every section from the answers. Number requirements with
   priorities. Leave a short **Open Questions** list only for things genuinely
   deferred, not things you failed to ask.

7. **Hand off.** Tell the user the PRD is ready and that they can hand it to a
   coding agent (a fresh session or you) to build from. Offer to start building,
   or to commit the PRD first so it persists across sessions.

## Principles

- The measure of success: **an agent could execute this PRD with no follow-up
  questions.** If a section would make an agent guess, you're not done grilling.
- Non-goals and done-criteria are the highest-value sections — they're what keep
  an agent's output scoped and reviewable. Never skip them.
- One decision at a time is fine, but batch related questions to respect the
  user's time. Don't drag out obvious calls — recommend a default and move on.
