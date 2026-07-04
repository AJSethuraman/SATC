---
name: domain-modeling
description: Actively build and sharpen the project's domain model — challenge fuzzy terminology, force precise definitions, and capture the shared language in a glossary (CONTEXT.md) plus ADRs. Use when terms are ambiguous or overloaded, when the same concept has conflicting names, or when starting a subsystem whose vocabulary isn't nailed down. This skill *changes* the model, it doesn't just read it.
---

# Domain Modeling

Sharpen the ubiquitous language of the domain so code and conversation use the
same precise terms. In a tax practice, imprecise vocabulary (client vs. taxpayer
vs. return vs. engagement; vault vs. mart) causes real bugs — pin it down.

## Process

- **Challenge terms actively** — question conflicting or fuzzy definitions and
  force precision. When the user's language contradicts the existing glossary,
  flag it immediately.
- **Stress-test with scenarios** — invent edge cases that expose where a term's
  boundary really is.
- **Cross-reference the code** — surface contradictions between stated meaning
  and how the code actually uses the term.
- **Capture decisions immediately** — update `CONTEXT.md` as terms crystallize;
  don't batch it.

## Files

- **Single context:** `CONTEXT.md` (glossary) + `docs/adr/` for decisions.
- **Multiple bounded contexts:** a `CONTEXT-MAP.md` pointing at each context's
  own `CONTEXT.md` + ADR folder.
- Create these **lazily** — only when needed.

## Discipline

- `CONTEXT.md` is **purely a glossary** — "totally devoid of implementation
  details." Never a spec, scratchpad, or implementation log.
- Offer an **ADR** only when all three hold: the decision is hard to reverse,
  surprising without context, and the result of genuine trade-offs.
