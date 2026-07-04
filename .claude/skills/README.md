# SATC Skills

Reusable, committed workflows for agent-driven development. Because they live in
the repo, they're available in **every** session and run the same way each time.
Invoke a skill by typing `/<name>` (e.g. `/grill-me`).

The design philosophy (adapted from Matt Pocock's skills): **small,
single-purpose skills piped together, with human gates between them** — so you
can enter at any stage and you approve each hand-off, instead of one monolith
barreling through the checkpoints that keep an agent on track.

## The spine — new work

```
/grill-me    →  /to-prd     →  /to-issues        →  build
(align)         (spec it)      (slice into issues)   (implement)
```

| Skill | Does | Hands off to |
|---|---|---|
| **grill-me** | One-question-at-a-time decision-tree interview until aligned. Writes no document. | `to-prd` |
| **to-prd** | Synthesizes the conversation into an agent-ready PRD (user stories + testing seams), filling `PRD_TEMPLATE.md`. | `to-issues` |
| **to-issues** | Breaks the PRD into vertical-slice "tracer bullet" GitHub issues, labeled `ready-for-agent`, in dependency order. | build |

## Supporting skills

| Skill | When |
|---|---|
| **handoff** | Session getting long / continuing later — compacts context into a committed handoff doc (survives the ephemeral container). |
| **diagnosing-bugs** | Something broken/flaky/slow — build a red-capable loop, hypothesize, fix with a regression test. |
| **tdd** | Building/fixing test-first — red → green in vertical slices at a confirmed seam. |
| **research** | A decision needs grounding in primary sources — produces a cited Markdown note in the repo. |
| **domain-modeling** | Terminology is fuzzy/overloaded — sharpen the glossary (`CONTEXT.md`) + ADRs. |
| **codebase-design** | Designing/restructuring a module — deep modules, minimal interfaces, clean seams. |
| **triage** | Sorting incoming issues/PRs — categorize, verify, and produce the `ready-for-agent` brief. |

## Also available (built-in)

The harness already ships `code-review`, `verify`, `deep-research`, and
`security-review`. Prefer those over re-implementing them; the skills here fill
the gaps around them.
