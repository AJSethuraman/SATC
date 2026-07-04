---
name: research
description: Investigate a question against high-trust primary sources and document findings as a cited Markdown file in the repo. Use when a decision needs grounding in authoritative facts (tax rules, a library's real API, a spec) rather than guesses. For heavy multi-source web research, the built-in deep-research skill is the deeper tool; use this for focused, repo-anchored investigation whose result should live in the codebase.
---

# Research

Answer a question from **primary sources** and leave a cited artifact behind.

## Process

1. **Go to first-party sources**, not secondary summaries: official docs, source
   code, specifications, first-party APIs. For tax questions, prefer the IRS /
   state DOR primary text and cite the section — this codebase requires sourced
   citations on tax parameters.
2. **Trace every claim** back to its authoritative source. If you can't source
   it, mark it explicitly as unverified.
3. **Document findings in a single Markdown file** with a citation for each
   claim. Save it following repo conventions (e.g. alongside `PLAN.md` or under a
   `docs/research/` folder); pick a sensible location if none exists.
4. For long-running digging, you may run it in the background while other work
   continues, then write up the result.

## Output

- One Markdown file, each claim cited to its primary source (link or section
  reference), saved in the repo so it persists across sessions.
- A short "confidence / open questions" note at the end.
