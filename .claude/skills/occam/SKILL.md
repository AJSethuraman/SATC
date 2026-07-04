---
name: occam
description: The one-command front door to the Occam build pipeline — turns a raw idea into a spec and buildable issues. Use when the user types "/occam <idea>" or asks to spec out / start / scope any new project, feature, or tool. Runs grill → PRD → issues end to end, pausing at each gate for confirmation.
---

# Occam

The single entry point for turning an idea into something an agent can build.
"Occam" = strip it to the essential, agreed shape *before* writing code. This
skill just **orchestrates the pipeline** — the real work lives in the stage
skills; run them in order and honor the gates between them.

## What to do

Take the user's idea (the text after `/occam`, or ask for a one-liner if they
gave none), then drive the pipeline:

1. **Grill** — run the `grill-me` skill on the idea. It interviews one question
   at a time, researches external facts, reads the codebase, and runs the
   assumption audit. **Gate:** it stops at shared understanding and asks the user
   to confirm. Do not proceed until they do.
2. **Spec** — once confirmed, run the `to-prd` skill to capture the understanding
   as an agent-ready PRD (user stories, testing seams, closed assumptions).
   **Gate:** show the user where the PRD landed; offer to commit it.
3. **Slice** — run the `to-issues` skill to break the PRD into vertical-slice,
   `ready-for-agent` issues in dependency order. **Gate:** quiz the user on the
   breakdown before publishing.
4. **Hand off** — the issues are ready to build (by an agent or by you, on the
   user's go-ahead).

## Rules

- **Keep the gates.** The whole value is stopping to align before each step — do
  not silently run all the way to issues. Pause and confirm between stages.
- **Enter mid-pipeline when asked.** If the user already has a spec, skip to
  `to-issues`; if they already aligned, skip to `to-prd`. `/occam` is the default
  full run, not a mandatory one.
- **One idea per run.** If the user names several, grill them on which to spec
  first.
