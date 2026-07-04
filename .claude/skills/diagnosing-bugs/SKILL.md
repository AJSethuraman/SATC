---
name: diagnosing-bugs
description: A structured debugging loop — build a red-capable feedback loop, reproduce and minimize, hypothesize, instrument, fix with a regression test, then clean up. Use when something is broken, failing, throwing, flaky, or slow, or the user asks to "debug" or "diagnose". Especially for money/tax/PII correctness bugs, where guessing is not acceptable.
---

# Diagnosing Bugs

Do not guess-and-patch. Work the loop. **No red-capable command, no hypothesizing.**

## Phase 1 — Build a feedback loop (the critical skill)

Construct a tight pass/fail signal that reproduces the bug. Prefer, in order: a
failing test → a curl/HTTP script → a CLI run with fixtures → headless browser →
trace replay → throwaway harness → property/fuzz loop → bisection → differential
loop → a human-in-the-loop bash script. **Done when:** one runnable command goes
**red** on the bug, deterministically, fast, unattended.

## Phase 2 — Reproduce + minimize

Confirm the loop catches the user's exact symptom across runs. Strip inputs,
callers, and config one at a time until every remaining element is load-bearing.

## Phase 3 — Hypothesize

Generate **3–5 ranked, falsifiable** hypotheses *before* testing any. State each
as: "If X is the cause, then changing Y makes the bug disappear." Share the list
with the user before probing.

## Phase 4 — Instrument

Map each probe to a specific Phase 3 prediction. Prefer debugger/REPL → targeted
logs; avoid "log everything". Tag debug logs uniquely (e.g. `[DEBUG-a4f2]`) so
they're easy to remove. For performance bugs: measure baseline → bisect → measure
again.

## Phase 5 — Fix + regression test

Write the test at the correct **seam** (exercises the real pattern at the call
site). Failing test → apply fix → passing test → re-run the original scenario.

## Phase 6 — Cleanup + post-mortem

Verify the original repro is gone, the regression test passes, and **all** debug
instrumentation is removed. Record the confirmed root cause in the commit
message. If the bug points at an architectural weakness, flag it (see
`codebase-design`) rather than fixing it inline.

## SATC note

For correctness-critical areas (invoice math, Stripe webhooks, withholding, tax
line-sheets), the regression test is mandatory, and repro fixtures must use
**synthetic/masked** data — never real taxpayer PII.
