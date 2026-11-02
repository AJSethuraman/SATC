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

## Added: example outputs and screen proposals
The owner asked to see real outputs and how the screens work, not more of the builder. `prototype/outputs.html` shows the four outputs and five proposed screens; `examples/` holds the generator and the files. The testing screen (one question at a time, keys 1 to 4 to rate, J and K to move, comment required only when the rating calls for it, facts panel read-only) is the proposed core of daily use. The outputs come from a demonstration script, not the engine; closing that gap is part of slice 3.

## Added: what a configuration turns into (`prototype/tools.html`)
The owner did not want printed outputs ("pdf prints… i can figure out") and did not like how they looked. They wanted the tool a creator gets. `tools.html` shows three finished tools sharing one shell, with the configured shape in the middle and the buyer's brand, plus the creator's home for a published tool. This is the visual bar for the product; the earlier pages are below it.

## Added: the output in its own medium (`excel/`)
The owner, on the HTML mockups: "if you made it in excel i expect the mock up to be in excel". An example output is the real artifact in its real medium, never a picture of one. `excel/build_tool_workbook.py` turns a configuration into a working workbook; `check_tool_workbooks.py` recalculates in LibreOffice and checks 28 values (seen to fail on a broken formula). Next in this direction: the same configuration delivered as a real browser tool, built by a generator, not drawn.

## Added: the "Paper" design (2 Nov 2026)
The workbooks in the owner's linesheet style were rejected: *"better but honestly just no, thick rows, thick fonts, super blocky look"*. The owner took the brief to Claude Design, and the package that came back is in `design/paper/`. `Paper System.html` holds the screens, blocks and states, and its Build sheet gives exact fonts, fills, borders and row heights. `excel/build_tool_workbook.py` now generates to that sheet. The colour family is a config key (`family`). `check_tool_workbooks.py` checks 30 values, including that a part-built figure is withheld rather than shown as $0. The design package's README lists what it did **not** design (the Studio launcher is a flow prototype only). Still open: the files have never been opened in Microsoft Excel.

## Added: the application, first build (2 Nov 2026)
The owner said *"ok start building out the software - i am going to bed. do a walk of it when you think it's done"*. Decisions D1–D5 were still open. **The build proceeded on the recommended answer to each**, and each one is reversible:
- D1: the firm configures, and there is one organization per installation.
- D2: a sibling of `credit-review-os`.
- D3: a local application, with the workbook as an output.
- D4: a tested method library, plus rules written by the organization.
- D5: credit review first.

The register still lists them as open. **They need the owner's yes.**

**Where things are.** `src/workpaper_studio/`, `packs/`, `tests/`; the CI entry is in `.github/workflows/test.yml`. The excel demo builder now imports the generator from the package.

**What holds it together:**
- **One engine.** The engine is the only place a status or result is decided. The workbook keeps live formulas, so it is a second implementation; `tests/test_workbook_parity.py` proves the two agree on 28 cases, by every defined name. That test found a real workbook bug on its first run: side-by-side cards shared hidden helper cells.
- **A record that cannot change.** Every action is an event in a table the database refuses to update or delete. A case is only ever rebuilt by replaying its events, and it keeps the pack fingerprint and limits version it started with.
- **Rules held below the screens.** Roles come from the signed cookie, and the rules are enforced in `service.py`: a reviewer cannot edit; nobody reviews their own case; above-limit results need an acknowledged exception; release needs approval; a pack needs a second person.

**The walk.** 15 defects against 73 green tests, none of them caught by a test. 13 were fixed with tests, the walk was run again, and the procedure's screenshots come from that second walk. Still open:
- defect 10: whether limits need maker-checker, which is the firm's call;
- each field's N/A button is a Tab stop of its own.

**Not built:**
- the Studio launcher flow from the Paper package (Describe, Shape, Look);
- editing packs in the app (they are files);
- upgrading a case to a newer version;
- real sign-in (a local name picker; the rules hold whoever picks);
- the feed's real format (D7).

**Run.** `PYTHONPATH=src python -m workpaper_studio serve`, then open port 5077. Port 5060 is blocked by browsers, so do not use it.
