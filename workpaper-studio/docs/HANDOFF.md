# Handoff — Workpaper Studio

*1 November 2026. Branch `claude/magical-brown-1pcsrn`. Stopped deliberately at the design-review checkpoint.*

## State in one paragraph
Design is written and a clickable prototype exists. **No product code.** The firm has not yet answered D1–D5. Until they do, do not start slice 0 (it depends on D3 and D4) and do not pick a stack.

## Read, in order
0. Open `prototype/journey.html` first. It walks the whole intention: build, package, list, install, use, update. Then read `docs/REFERENCE-WORKBOOK.md` (what the owner's real workbook showed) and `docs/MARKET-AND-PACKS.md`. `index.html` is one polished instance, a credit review, and reads as specific for that reason. Added after the firm said the first prototype looked "highly specific" and hid the point.
1. `docs/DESIGN-REVIEW.md` (argument and plan) → 2. `docs/DECISIONS.md` (what is confirmed and open) → 3. open `prototype/index.html` and `prototype/directions.html`.

## Run the prototype
Open `prototype/index.html` in a browser. Nothing to install. It stores edits in the browser; "Prototype controls → Reset" clears them. Switch **Viewing as** to see each role. Verify with `node prototype/check.js` and `node prototype/check-builder.js` and `node prototype/check-journey.js` (needs Playwright; prints PASS/FAIL per check).

## Do not redo
- Inspecting the repo: the relevant parts are in `DESIGN-REVIEW.md` §1.
- The visual-direction choice, unless the firm objects: A recommended with reasons.
- Reading `credit-review-os`: its program YAML is the starting template and its token grammar a reference; it is not imported.

## First moves after answers arrive
1. Record the answers in `DECISIONS.md` (status and date).
2. If D3 and D4 stand: run the short engine-language spike (`DESIGN-REVIEW.md` §8.4) and record the result.
3. Then slice 0 (`DESIGN-REVIEW.md` §11). `tdd` skill; tests at the engine's interface.
4. Update `docs/DESIGN-PRINCIPLES.md` in the same commit if a principle changes (§10 lists what this strains: nothing so far).

## What is not true yet
Anything about the user's real workbook, the real feed, accessibility beyond the checks listed, printing, or performance.

## Added 1 Nov 2026 (after the photographs)
- The core building block is a table of **test questions**; calculations are supporting. Built. Gaps still open are listed in `REFERENCE-WORKBOOK.md` (grid blocks for owners × periods, record retrieval, admin screens, sampling).
- The photographs stay out of the repo. D15 is closed by the owner (original work).
- The photographs sit at `/tmp/.../scratchpad/ref-linesheet/` in the session that received them; they are gone with it. Ask the owner to re-share if needed.

## Added later, 1 Nov 2026: one table primitive (read before adding any "block")
The owner rejected ranking block types as "counter to the spirit". `table` and `questions` were replaced by one `grid` primitive with configurable axes (P16 in `DECISIONS.md`). **Do not add new block kinds for new table shapes.** Add a pattern (`ORG.patterns` in `journey.html`) or, if a shape cannot be expressed, add an axis option and a test. `check-journey.js` holds ten checks for the primitive.
