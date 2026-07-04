---
name: to-issues
description: Break a plan, spec, or PRD into independently-buildable GitHub issues as vertical slices ("tracer bullets") — each a thin but complete path through every layer, shippable on its own, ordered by dependency. Use when the user says "to issues", "break this into issues", "split the PRD into tasks", or after a PRD is written. Publishes to the GitHub issue tracker after confirmation.
---

# To Issues

Turn a PRD/plan into issues an agent (or person) can pick up one at a time. The
core idea: **vertical slices, not horizontal layers.**

## What a vertical slice is

Each issue is a **tracer bullet** — a narrow but *complete* path through every
layer it needs (data/schema → logic/API → UI → tests). A finished slice is
**independently demoable and verifiable**, and does not depend on other
in-flight slices to be shippable. The opposite (and what to avoid) is slicing by
layer — "build all the models", then "build all the endpoints" — which produces
nothing demoable until the end.

## Process

1. **Gather context.** Use the PRD/plan in the conversation. If it references
   existing issues, read them.

2. **Explore the codebase (optional).** Understand current state. Look for
   *prefactoring*: "make the change easy, then make the easy change" — if a small
   refactor would make the slices cleaner, note it as its own early slice.

3. **Draft the slices.** Break the work into tracer-bullet issues. For each,
   draft: a title, what it delivers end-to-end, its acceptance criteria, and what
   (if anything) blocks it. Keep each slice small enough to build and verify in
   one sitting.

4. **Quiz the user.** Present the proposed breakdown — titles, blockers, and the
   user story each slice serves — and iterate on granularity and dependencies
   before creating anything. Don't publish until the shape is agreed.

5. **Publish to the tracker.** Create GitHub issues (via the GitHub tools) in
   **dependency order**, each using the template below. Confirm the target repo
   first. Label each fully-specified, unblocked issue `ready-for-agent` — that
   label is the handoff signal that an agent can pick it up and build it (see the
   `triage` skill). Issues still missing detail get `needs-info` instead. If the
   user prefers not to use GitHub Issues, write the same content to a markdown
   checklist file instead.

## Issue template

```
**Parent:** <link to source PRD/issue, or "—">

**What to build:** <concise end-to-end description of the slice — behavior, not
file paths>

**Acceptance criteria:**
- [ ] <verifiable condition>
- [ ] <verifiable condition>
- [ ] Tests pass at the seam named in the PRD

**Blocked by:** <issue refs, or "None — can start immediately">
```

## Rules

- Order matters: publish so that anything with no blockers can start immediately,
  and dependents reference their blockers.
- No file paths in "what to build" — describe the outcome; let the builder find
  the files.
- Every slice must be independently verifiable, or it isn't a vertical slice —
  reslice it.
