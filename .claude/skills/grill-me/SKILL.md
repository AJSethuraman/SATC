---
name: grill-me
description: A relentless, one-question-at-a-time interview that resolves every decision branch before any code or document is written, then captures the shared understanding as an agent-ready PRD. Use when the user wants to spec out new work, stress-test a plan or design before building, start a new project, write a PRD, or says "grill me" / "grill". Reaches genuine alignment first; produces the PRD only once the user confirms.
---

# Grill Me

The failure this fixes: agents (and plan mode) produce a plan or document **too
early**, before real alignment exists — so the build drifts from what the user
actually wanted. Grilling forces the conversation *first*. You produce **no
artifact** until the user confirms you've reached shared understanding. Only
then do you write the PRD.

Two phases, in order. Do not skip or reorder them.

---

## Phase 1 — Grill (reach shared understanding, write nothing)

Conduct a relentless interview that walks down **each branch of the design
tree**, resolving dependencies between decisions **one at a time**.

### Rules of the interview

1. **One question at a time.** Ask a single question, wait for the answer, then
   ask the next. Asking several at once is bewildering and produces shallow
   answers. (Only batch when two sub-questions are so tightly coupled they can't
   be answered apart.) Use the `AskUserQuestion` tool.

2. **Always recommend an answer.** For every question, put your recommended
   option **first** and mark it `(Recommended)`, with a one-line reason. The user
   should be able to just accept your default and move on. You are doing the
   thinking, not offloading it back onto them.

3. **Follow the dependency chain.** Order questions so earlier answers unlock
   later ones. Start at the root (what problem, for whom), and only descend into
   a branch once its parent decision is made. Track which branches are still
   open; don't leave one dangling.

4. **Ground answers in the codebase, don't speculate.** Before asking about how
   something should fit, look. Read `CLAUDE.md`, then grep/read the relevant
   existing code (e.g. how `satc_system/`, `invoice-generator/`, or a sibling
   module already does the thing). Prefer "I see X already does Y — should this
   match, or differ because Z?" over an abstract question.

5. **Cover the branches that matter most.** At minimum resolve: the real problem
   and who has it; **what's explicitly out of scope** (non-goals — this is where
   agent builds balloon); the must-have vs nice-to-have requirements; **data
   sensitivity** (if it touches tax data, financials, or client PII, nail the
   masking/handling rules to the bar set by DEA's safety boundaries and
   Invoicer's payment handling — no PII in artifacts); constraints (stack, deploy
   target, must/must-not-use); and what "done and verified" concretely means.

6. **Push on vagueness.** "Fast" → under what, on what? "Handle documents" →
   which formats, how many, what happens on a bad file? Surface unstated
   assumptions and get a ruling on each.

7. **Do not write the plan or PRD yet.** Keep going until the branches are
   resolved. Then **stop and summarize** the shared understanding in a few
   sentences and ask: *"Have we reached shared understanding — should I capture
   this as a PRD?"* Do not proceed until the user confirms.

---

## Phase 2 — Capture as PRD (only after confirmation)

Once the user confirms alignment:

1. Read `PRD_TEMPLATE.md` at the repo root — that's the output shape.
2. Copy it to a sensible path — `docs/prd-<name>.md` inside the relevant project
   folder, or a new top-level folder for a brand-new project.
3. Fill every section from what the grilling established. Number requirements and
   tag priority (`[P0]`/`[P1]`/`[P2]`). Drop optional sections that don't apply.
   The **Non-Goals** and **Done Criteria** sections are load-bearing — never
   leave them empty. Use **Open Questions** only for things genuinely deferred,
   not things you failed to ask.
4. Hand off: tell the user the PRD is ready, that a coding agent (a fresh session
   or you) can build from it with no follow-up questions, and offer to commit it
   so it persists across sessions. Offer to start building.

---

## The bar for success

An agent could execute the resulting PRD with **zero follow-up questions**. If
any section would force an agent to guess, Phase 1 wasn't finished — go back and
grill the gap. A short, unambiguous spec beats a long, hedged one.
