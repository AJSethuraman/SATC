---
name: tdd
description: Test-driven development — red → green in vertical slices, with tests written at the right seam and confirmed with the user first. Use when building a feature or fixing a bug test-first, when the user mentions "red-green-refactor" or "TDD", or when a change is correctness-critical. Pairs with the testing seams named in the PRD.
---

# TDD

Cycle **red → green** in vertical slices. Refactoring is a code-review concern,
not part of the red-green cycle.

## What makes a good test

- Verifies **behavior through public interfaces**, not implementation.
- Reads like a specification ("user can checkout with a valid cart").
- Survives refactors because it ignores internal structure.

## Seams (do this first)

- Tests live at **public boundaries** where you can observe behavior without
  reaching into internals.
- **Critical first step:** write down the seam(s) under test and **confirm with
  the user before writing any test code**. (If a PRD exists, use the seams it
  already names.)
- Focus on critical paths and complex logic — not exhaustive edge cases.

## The loop

1. Write **one** failing test at the seam (red).
2. Implement the **minimum** to make it pass (green).
3. One seam, one test, one minimal implementation per cycle. Move to the next
   slice.

## Anti-patterns to avoid

- **Implementation-coupled:** mocking internals, testing private methods, or
  asserting against the database instead of the interface.
- **Tautological:** the assertion recomputes the expected value the same way the
  code does. Expected values must come from an **independent** source.
- **Horizontal slicing:** writing all tests up front. Go vertical — one test →
  one implementation per cycle.

## SATC note

For money/tax/PII code, expected values should come from hand-worked examples or
cited authority, and fixtures must be **synthetic/masked**.
