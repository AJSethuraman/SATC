# Setting up the Forge to run down questions

**What this is for.** Four of the close's questions reached a desk that holds
nothing on the point. The searcher exists, it has been run once by hand, and it
has never run unattended. This is how you point a session at the open gaps and
let it work them.

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

`desk` should read **0.5.0**. Anything lower and the searcher, the engagement
file and the reader fixes are not there.

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

**Two of the refusals are not search work at all.** Q18 at the cash desk and Q12
at the rewards desk are a routing defect: the desk holds the right authority and
per-subject narrowing refuses it. It has been found twice, is recorded, and has
deliberately not been worked around.
