# Setting up the Forge to run down questions

**What this is for.** The searcher exists, it has been run once by hand, and it
has never run unattended. This is how you point a session at the open gaps and
let it work them.

**Read the triage at the bottom before you spend a run.** The live-gap command
below currently returns four questions and only one of them is search work — the
other three are a misread brief, a question another desk already answered, and a
routing problem. Checking that first is step 1 of the skill, and it is the step
worth being pedantic about.

**It needs the internet and a model that can read a regulation.** That is the
only reason it belongs on the Forge rather than anywhere else — nothing here
depends on the local model specifically. If the Forge is busy, any Claude Code
session with network access can run it.

---

## Before you start: install the plugin

On the machine that will run it:

```
claude plugin marketplace update satc
```

```
claude plugin update desk@satc
```

**Both commands, in that order, and the second one is the one that installs.**
`marketplace update` only refreshes the listing — it looks like it worked and
changes nothing on disk. This has cost a session before.

Check it took:

```
claude plugin list
```

`desk` should read **0.5.0**.

**Verified on 7 September, and it does not yet.** The marketplace installs from
`main`, and 0.5.0 is on the branch in #316. Running the two commands today
installs **0.4.0**, which has the searcher and the desks — the gap command below
runs correctly against it, checked — but **not** `run-down-a-question`, the skill
this prompt tells the session to load, and not the engagement file. So the
install step is blocked until #316 merges. The searcher itself can be driven by
hand at 0.4.0 by anyone who reads `tools/search_run.py`.

---

## The prompt

Paste this into a Claude Code session on the Forge. It stands alone — it assumes
no memory of the sessions that built any of this.

```text
You are running down the open authority gaps for the SATC `desk` plugin.

Load the `run-down-a-question` skill from the desk plugin and follow it. It is
the specification for this work; this prompt only tells you where to start and
what to hand back.

FIRST, GET THE LIVE LIST. Do not work from any list written into a document,
including this one — it is a snapshot and the desks have moved since.

    python3 -c "
    import json, pathlib
    runs = sorted(pathlib.Path('$CLAUDE_PLUGIN_ROOT/runs').glob('asked-*'))
    d = json.loads((runs[-1] / 'served.json').read_text())
    print(runs[-1].name)
    for r in d:
        if not r['served'] and r['reason'] == 'authority_absent':
            print(' ', 'Q%s' % r['q'], r['desk'], '|', r['question'])
    "

Work them one at a time. For each one:

  1. Read the desk's brief so you know what it already holds. A gap that turns
     out to be authority the desk has is a ROUTING finding, not a search — say
     so and move on rather than searching for it.

         python3 -c "
         import sys, os; sys.path.insert(0, os.environ['CLAUDE_PLUGIN_ROOT'])
         import ask
         for desk, brief in ask.consult('<the question>'):
             print(desk); print(brief)
         "

  2. Search. Anywhere. The gate is on what gets KEPT, not on where you look —
     the skill explains why, and it is the firm's own reasoning.

  3. Read the pages. For each passage you would want the desk to hold, record
     the citation, the words EXACTLY as printed, and the URL you read them on.

  4. Put every hit and every proposal into one JSON file and run:

         python3 $CLAUDE_PLUGIN_ROOT/tools/search_run.py found.json > SEARCH-Q<n>.md

     Record hits you read nothing off. The count is the run's noise floor.

WHAT YOU MAY NOT DO

  - Do not write into any desk. `search_run.py` decides what COULD be stored;
    storing it is a pull request and admitting a publisher is the firm's.
  - Do not paraphrase a passage to make it tie out. A refusal from the tool is
    the answer, and softening it is the one failure this whole seam exists to
    prevent.
  - Do not touch `engine.py`, `searching.py`, or anything under `desks/`.
  - Do not put a client's name, a TIN, or any client fact anywhere. These are
    questions about the law; none of them needs a client.

HAND BACK, IN THIS ORDER

  1. Every gap that is now closable — the desk, the question, the citation, and
     which publisher it came off.
  2. Every publisher waiting on the firm to admit it, with what admitting it
     would buy in desks and questions.
  3. Every gap you searched and came back empty on. This is a finding and the
     next session needs it, or it searches the same ground again.
  4. Anything that turned out to be a routing problem rather than a missing
     rule. There are two known ones already and they are not yours to fix.

Do not report a gap as closed until the desk actually answers the question.
```

---

## What to expect back

**Most first finds will be waiting on you, not stored.** A passage that ties out
on a publisher the firm has not admitted comes back as *propose a source*. That
is the design: on 7 September the searcher found two good passages of
§ 1.162-3, one on eCFR and one on Cornell, and neither could be used until you
said which publisher we read. You admitted eCFR, and the desk answered the
question about ninety minutes later.

**Some gaps will come back empty, and that is a result.** A question searched
and found unanswerable by public authority is a different fact from one nobody
has looked at — it usually means the answer is a position for the firm to take
rather than a rule to be found.

---

## Triaged, 7 September 2026: one of the four is a real gap

I ran the skill's own first step against all four before publishing this — read
what the desk actually holds before searching for anything — and it changes what
is worth a run. **The command above still returns four. Three of them are not
search work.**

| | Desk | What it really is |
|---|---|---|
| **Q16** | fixed-assets | **A real gap.** The desk holds § 1.263(a)-3, which decides whether money spent on property you ALREADY OWN is an improvement. The tool-or-asset line at the moment of purchase is § 1.263(a)-2 — amounts paid to acquire tangible property — and the desk does not hold it. eCFR is already admitted here, so this is extraction, not a web search |
| Q33 | meals-and-entertainment | **Not a gap — the model misread its own brief.** It wrote *"§ 1.274-11's own text is not in this desk's record"*. It is: ten passages, including the general disallowance at (a), the definition of entertainment at (b)(1)(i) and the objective test at (b)(1)(iii). All of it was in front of it. Searching would find what the desk already has |
| Q18 | personal-or-business | **Not a gap, and already answered.** The personal/business desk correctly says the expense-or-asset line is not its authority. The same question went to fixed-assets, which served it on § 1.162-3(c)(1)(i) |
| Q12 | capitalization-and-de-minimis | **Not a search job.** A 1099 question reached the capitalisation desk. The rewards desk owns § 6041 and § 6050W; putting information-return authority onto the capitalisation desk to close this would be wrong |

**Q33 is the one worth staring at.** An `authority_absent` escalation is taken at
the engine's word — it is the model's claim about its own record, and nothing
checks it. Here the claim was false and the refusal looked exactly like the three
correct ones. That is a real hole in the seam, recorded rather than patched.

**And two other refusals in that run are a routing defect, not authority.** Q18
at the cash desk and Q12 at the rewards desk: the desk holds the right authority
and per-subject narrowing refuses it. Found twice, recorded, deliberately not
worked around.
