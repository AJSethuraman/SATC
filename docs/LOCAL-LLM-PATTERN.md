# Making a small local model do real work — the pattern proven on Occam

How this box gets an 8B model (Ollama, `qwen3:8b`) to run a bookkeeping engine
end-to-end, measured at full marks. The model is the driver; every control is
deterministic. If you give the SATC app AI features, use this playbook — every
rule here was paid for with a measured failure.

## The one-sentence architecture

**The model proposes; a deterministic engine verifies, refuses, or executes.**
The model never computes a number that matters, never writes state directly,
and cannot widen its own permissions. It chooses *what to do next*; code decides
*whether that's allowed* and *what actually happens*.

## The ten rules, each earned by a failure

1. **Fit the window or nothing else matters.** 8 GB VRAM = 8,192-token context.
   Loading every tool schema (~11k tokens) silently truncates the model's own
   instructions — it then "ignores" rules it never received. Skills declare a
   minimal `tools:` list; every tool result is small. We twice misdiagnosed a
   missing frontmatter line as a "model capability ceiling."

2. **Aggregate server-side; hand the model something small.** 84 rows of JSON
   killed runs mid-parse. >20 rows now come back grouped (84 rows → 9 merchants,
   25k chars → 1.5k). The model works categories, not lists.

3. **Errors are the interface.** On an 8B, a refusal that only says "no" ends
   the run; a refusal that names the right next step self-corrects it. Every
   error names what would have been right: wrong account code → "this chart uses
   1110 Operating Checking"; wrong tool → "use occam_decide_merchant instead."

4. **Idempotent writes.** "Create X" when X already exists exactly as requested
   returns success + "nothing to do; next step is Y" — never a 409. A bare
   "already exists" sent the model into retry walls that burned whole runs.

5. **Name the criterion; the engine selects the rows.** Never let the model
   assemble ID lists for bulk actions — it widens them (told to approve 55, it
   once approved all 138). `decide_by_confidence("suggest")` = the model states
   the *rule*, code computes the *set*.

6. **Policy lives at the engine choke point, not in prompts.** "Every guess gets
   flagged for review" was obeyed 100%, 4%, 0% of runs as skill prose; as an
   API-level requirement (approve-without-rule needs a memo, memo becomes the
   flag) it is obeyed always, from every path. Prompt policy is policy 1 run in 3.

7. **Permissions are server-side roles, not tool lists.** The model runs as a
   principal (`ai_staff`, assigned specific data) set by the *launcher*, enforced
   by middleware on every write. Omitting a dangerous tool from a skill is a
   convention; a 403 is a gate. An eval once switched onto a real client's books
   because only convention stood in the way.

8. **Shrink the problem before asking the model to be smarter.** Deterministic
   priors/rules do the bulk (83 unmatched rows → 23) so the model spends its
   tiny budget only on judgment calls. Never coach the model to grind; remove
   the grind.

9. **Accept the give-up tail; make it harmless.** Small models abandon long
   tasks (~1 in 6–9 runs, worse under VRAM pressure). No prompt fixes this.
   Instead: half-finished runs are *inert by construction* (nothing committed,
   nothing postable), and re-running is safe (rule 4) and cheap — so the wrapper
   retries instead of the model persisting. Also: never restate the full task
   mid-run ("create X…" restated = the model starts over); progress reminders
   must lead with "work above is DONE, continue with the NEXT step."

10. **Measure against reality, never the model's prose — and prove every check
    can fail.** Every score reads engine state (the workbook, the API), never
    the model's claims. Pre-conditions are captured *before* the run (the run
    itself moves the denominators). Seven of our check bugs produced false
    passes; a check that has only ever passed is not evidence.

## What this buys

A replaceable brain in a permanent machine: all learned knowledge (rules,
priors, gates, audit) lives in deterministic files, so upgrading the model is
`ollama pull` + re-running the scoreboard — no retraining, ever. Correctness is
enforced, throughput is wrapped, and the model's only real job is judgment at
the margins — which is the only thing it's actually good at.

*Full history with measurements: `C:\Users\ajish\Documents\Main\Claude\FORGE-EVAL-STATE.md`
(local only — do not commit its contents here; it references client data).*
