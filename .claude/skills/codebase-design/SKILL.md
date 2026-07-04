---
name: codebase-design
description: Apply deep-module discipline when designing or restructuring a module's interface — maximize behavior behind a minimal interface at a clean seam, verifiable through that interface alone. Use when designing a new module, restructuring an interface, deciding where a testing seam goes, improving testability, or reducing how much a caller must know.
---

# Codebase Design

Design **deep modules**: substantial behavior reached through a **minimal**
interface, positioned at a clean **seam**, verifiable through that interface
alone. Depth is measured against the *interface*, not the size of the code.

## Terms

- **Interface** — everything a caller must know: signatures, invariants,
  constraints, error modes, config, performance.
- **Depth** — behavior-per-unit-of-interface. Deep = large behavior, small
  surface.
- **Seam** — where the interface exists; where behavior can change without
  editing callers.
- **Adapter** — a concrete implementation satisfying an interface at a seam.

## Design checks

**Reduce surface area:** fewer methods? simpler parameters? hide more internally?

**Testability:**
1. **Accept dependencies, don't construct them** (inject).
2. **Return results instead of producing side effects** where you can.
3. Keep the surface small — the interface *is* the test surface.

## Rules

- **Deletion test:** if removing the module spreads its complexity across N
  callers, the module earned its place.
- If you find yourself testing *past* the interface (reaching internals), the
  module shape is wrong — fix the shape, don't widen the test.
- **One adapter = a hypothetical seam; two or more = a real seam.** Don't
  introduce a seam/abstraction prematurely.
- Distinguish internal (private) seams from external (caller-facing) ones.

## SATC note

The identity-vault / data-mart split is a load-bearing seam here — keep PII
behind the vault interface; the mart must be satisfiable with masked values only.
