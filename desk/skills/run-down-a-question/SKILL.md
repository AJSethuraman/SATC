---
name: run-down-a-question
description: Go and find the authority a desk does not hold. Use when a desk refused with authority_absent, when the unsupported queue has gaps nobody has searched, or when the firm asks to run down open questions. Searches anywhere, verifies every find against the publisher's own page, and brings what it finds to the firm rather than storing it.
---

# Run down a question

**A desk refused because it holds nothing on the point. Your job is to go and
look.** Not to answer the question — to find the paragraph that would let the
desk answer it, prove the paragraph is real, and bring it back.

## Where you may look: anywhere

The firm killed the first design of this with one question: *"how would you know
you need to access a site not on the whitelist before being asked?"* You cannot
ask permission for a site you do not yet know you need — so a list of approved
sites can only ever find what we already have.

**So the gate is on keeping, not on looking.** Search anywhere. Read anything.
Nothing you find enters the record unless **both** of these hold:

1. the words are still on the publisher's own page **today**, checked by
   re-fetching it — not by trusting the page you read; and
2. the firm has **admitted that publisher** for that desk.

Everything else comes back to the firm as a proposal. That is not a failure
mode; it is the normal outcome the first time a publisher comes up.

## The four steps, and which two are yours

    1. turn a refused question into search queries        YOU
    2. read a page and say WHICH citation these words are YOU
    3. fetch, tie out, decide what may be stored          THE TOOL
    4. admit a publisher, ratify a position               THE FIRM

Steps 1 and 2 are judgement and cannot be anything else. Step 3 is mechanical
and **must not** be: it re-fetches, it counts occurrences, and it cannot be
talked out of a verdict however confident your reading was.

## What to run down

**Read the gaps off the latest run, not off the queue.** Both exist and they
disagree, deliberately: the queue is the durable record of every hole ever
found, and holes get filled. On 7 September the queue named eleven
`authority_absent` gaps and the desks answered six of them — a Forge run driven
off the queue would have spent most of itself searching for authority already
in the record.

```
python3 -c "
import json, pathlib, sys
runs = sorted(pathlib.Path('$CLAUDE_PLUGIN_ROOT/runs').glob('asked-*'))
d = json.loads((runs[-1] / 'served.json').read_text())
print(runs[-1].name)
for r in d:
    if not r['served'] and r['reason'] == 'authority_absent':
        print(' ', 'Q%s' % r['q'], r['desk'], '|', r['question'][:80])
"
```

The queue is still worth reading — it is where a hole found mid-close by
somebody who was not running the desks gets written down. Just check each entry
against the desks before searching for it.

**`authority_absent` is the only reason this skill acts on.** The other refusal
reasons are different holes and searching cannot close any of them:

| Reason | What it needs |
|---|---|
| `authority_absent` | **this skill** — the record is missing a rule |
| `facts_not_established` | ask the client. No amount of authority closes it |
| `document_not_requested` | request the document, through the preparer |
| `context_not_on_file` | record the fact on the engagement's file |
| `no_field_for_this_fact` | there is nowhere to write it — the field has to be built |

Running a search at one of the bottom four wastes the run and produces a find
nobody can use.

## Doing it

**Write what you found into one JSON file, then let the tool judge it.**

```json
{
  "desk": "fixed-assets",
  "question": "does a hardware-store purchase ever become an asset?",
  "reason": "authority_absent",
  "queries": ["26 CFR 1.162-3 materials and supplies definition"],
  "hits": [
    {"url": "https://www.ecfr.gov/current/title-26/section-1.162-3",
     "title": "26 CFR 1.162-3", "snippet": "...", "query": "..."}
  ],
  "proposals": [
    {"citation": "26 CFR 1.162-3(c)(1)(i)",
     "text": "the exact words, copied character for character",
     "kind": "rule",
     "found_at": "https://www.ecfr.gov/current/title-26/section-1.162-3"}
  ]
}
```

```
python3 $CLAUDE_PLUGIN_ROOT/tools/search_run.py found.json > SEARCH.md
```

**Record every hit, including the ones you read nothing off.** The count is the
run's noise floor, and a gap searched and found empty is a completely different
fact from a gap nobody has searched. Leaving them out makes an empty search look
like no search.

**Copy the words exactly.** The tool re-fetches the publisher and compares. A
paraphrase fails. Words stitched together across a paragraph number fail — mark
the gap rather than closing it up. Words the publisher has more than once come
back `AMBIGUOUS`, because a passage that could be either of two paragraphs
cannot be filed under one.

## What the report tells you, and what to do with each

| Verdict | Meaning | Next |
|---|---|---|
| **store** | ties out, and the publisher is admitted | it may go into the desk — by pull request, with `tools/add_examples.py` |
| **propose a source** | ties out, publisher not admitted | **to the firm.** They decide whether we read that publisher |
| **already held** | the desk has it | nothing. The gap was routing, not authority |
| **refuse** | did not tie out | say so. Do not soften it, do not store it |

**This tool writes nothing into a desk, ever.** A searcher that could file its
own finds would be a model ratifying its own research, which is the exact thing
the two-store split exists to stop.

## When you are done

Bring back, in this order:

1. **What the desk can now answer that it could not** — the point of the run.
2. **What is waiting on the firm** — each proposed publisher, named, with what
   admitting it would buy.
3. **What you searched and did not find.** A gap you looked at and came back
   empty on is a finding, and the next session needs it or it searches again.

Never report a gap as closed until the desk actually answers the question. The
loop only counts when it closes.
