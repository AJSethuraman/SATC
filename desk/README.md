# desk — expert desks

A **desk** is an expert an agent consults so a question does not reach the firm.
It answers only from authority it can cite, states how binding that authority is,
and **escalates rather than guesses**.

Installing `desk` brings `canon` with it: this plugin declares it as a dependency
because it uses canon's selector for routing and inherits Bassy's challenge duty.
Canon uses nothing from here, and must not — it has to lift out whole.

## The one rule

**An answer with no resolvable citation never counts as correct**, and that is
enforced in `engine.py` rather than asked for in a prompt. The difference was
measured: the same policy written as skill prose was obeyed *"100%, 4%, 0% of
runs"*; at the API choke point it *"is obeyed always, from every path"*
(`docs/LOCAL-LLM-PATTERN.md`, rule 6).

## How you actually reach one

```python
import os, sys
sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"])
import ask

for desk, brief in ask.consult("the statement shows a $10 service charge and "
                               "nothing for it is in the books"):
    ...                                     # read `brief`, then answer from it

ask.answer(question, desk, position="an entry in the books",
           citation="...", working="why that paragraph settles it")
```

**Tell it what your own file already says.** Some rules cannot be applied
without a fact the engagement should have recorded — what the client does, whose
return it is. It is passed in and never worked out: a desk that inferred the
trade from the vendor would be running the exact reasoning its own position
forbids.

```python
ask.consult("they bought clothing at that store — is it a personal expense?",
            context=record.Context(facts={"trade": "general contractor"}))
```

A desk declares what it expects on a `Records:` line in its `SUBJECTS.md`, and a
position declares what it cannot be applied without on a `Needs:` line. Unmet, it
refuses `context_not_on_file` — a third kind of missing thing, resolved by
reading our own file rather than by asking the client or chasing a document.

### When a fact cannot be supplied

There is no file to create. The caller passes what it already has, and the facts
live wherever the firm keeps them — Occam's workbook, the engagement folder, the
interview. A desk that went looking would be inferring.

Not supplying one is an answer, and there are two of them:

| | Meaning | Who fixes it |
|---|---|---|
| `context_not_on_file` | there IS somewhere to record this and it is not recorded | a preparer fills it in |
| `no_field_for_this_fact` | there is **nowhere** to record it, anywhere | the firm decides the fact exists at all |

The second is a hole in what the firm tracks. `python3 tools/holes.py` reads both
out of the refusal queue, holes first — see `docs/WHERE-FACTS-LIVE.md`.

**And a served answer can be handed in with its evidence.** Pass `ask.answer` a
transport and it fetches the publisher's own page, compares it with the passage
being served, and hands the answer over with the tie-out attached — the URL, the
moment, the digest, how much matched. Where the publisher no longer carries the
text the answer is withdrawn; where the publisher could not be reached the answer
stands and says so, because a client's answer must not depend on a government
website being up.

**And a citation no desk holds is not the end of the road.** Hand `ask.answer`
the URL you found the rule at and the exact words you are resting on, alongside
a transport, and it fetches that page and serves only if those words are on it
right now. Two checks run *before* anything is fetched: the publisher must be
competent to settle the question, and a licence the firm has not accepted stays
a wall. The answer arrives saying it is not from the record — and **never
binding**, because `binding` means the firm treats it as authority that binds
their own work, and nobody has looked at the document. `candidates.py`.

**And no desk serves an answer nobody read.** The firm, asked which desks may
not serve unjudged: *"The judge can look at it all I guess?"* — all seven. A
second reader is handed the paragraph and the conclusion and says whether one
carries the other; the engine checks only that the words they quote are really
in what they read, and where a tie-out was taken they read **the fetched page**
rather than our copy of it. It does not make a wrong answer impossible — it
makes one attributable. The requirement is declared in each desk's own
`SUBJECTS.md` (`**Judged:** required`), so lifting it from a desk is one line of
that file. Cost, measured rather than estimated: **92 of the 98 recorded
problems** serve today, and every one now takes a second model call.

**Every attempt is written down, whatever it did.** The firm, 8 September 2026:
*"It should state what happened when trying to tie it out. I need info to make
decisions down the line."* One unreachable source is a shrug; forty against the
same host is a source to retire, and that decision cannot be made from the one
answer in front of you. `python3 tools/tieouts.py` reads them out, counted by
publisher, naming what it read them from.

**Two skills, because there are two sides.** `skills/be-the-desk` is for the
session that HOLDS the desks and answers from them; `skills/ask-desk` is for the
agent doing the work, which holds none of the record and sends its question to
that session instead. The split is `docs/THE-DESK-IS-A-SESSION.md`, and `relay.py`
is the wire between them.

**The split is the mechanism.** A model does not choose the desk — routing is a
comparison, not a judgement. A model does not decide whether its own citation
holds — the engine does, and refuses. What the model does is the one thing it is
good at: reading the authority it was handed and proposing a conclusion from it.

**`consult` shows the sources, the firm's RATIFIED positions and the stored
authority.** Never `PROBLEMS.md`, which is the answer key. Never a PROPOSED
position, which is one agent's suggestion nobody has said yes to — shown, it
would let a guess become the next agent's premise.

**Every refusal is kept**, in that desk's `unsupported/` queue with the caller's
reasoning intact. That queue is the only thing that says what authority is
missing, so a refusal thrown away is a finding destroyed.

## Four outcomes, and the order they are reported in

```
wrongly absorbed   wrong, uncatchable, would have shipped   ← first. always.
correct
wrong (caught)     wrong, and the engine stopped it
escalated          the desk knew it did not know — a SUCCESS
```

`wrongly_absorbed` is the only one that costs anything: every other outcome costs
a little time, that one costs the reason to trust the rest. **Never summed into a
single figure** — a percentage hides exactly the number worth reading.

**And `escalated` is two things, so the run reports which.** `_check` refuses
`authority_permits_choice` before any conclusion is compared, so a desk that
answered confidently and one that knew it did not know land in the same cell —
the first was stopped by the record's tier, the second made the call. `Result`
carries `escalated_by`, and without it a run measures the record's tiers rather
than the brain.

**Escalation cannot be forced through the record.** This said a problem resting
on a secondary source could *only* grade escalated, and the third scoreboard
disproved it: the tier gate keys off what the brain **cites**, not what the
question is about. qwen3:8b cited a primary paragraph about inventory on all
four cash problems, by explicit "extension", and never reached the gate. A desk
can make declining *possible*; it cannot make a brain decline.

## What is in a desk

```
desks/<name>/
  SUBJECTS.md   what brings it into play — whole-word subjects, deliberately
  SOURCES.md    what it may rely on: tier, access, may_store, checked
  PROBLEMS.md   the denominator — worked examples whose answers are not ours
  extracted/    public-domain authority text — the RULES, never the examples.
                an agent may write this.
  positions/    what the firm decided. an agent only PROPOSES here.
```

The two stores have different gates on purpose. Every line in `extracted/` is
checkable against a public source, so a large diff can be skimmed. `positions/`
holds judgement, so its diffs are read. **The pull request is the firm's yes.**

## A second desk is built by interview, not by hand

`skills/desk-factory` asks ten questions and opens a pull request containing the
desk. Every question carries the thing that taught us to ask it — what building
`fixed-assets` by hand actually required — and a test refuses one that does not.

**It proposes and never writes.** `factory.emit` writes into a git checkout on a
branch that is not `main` and refuses everything else, then runs `guards.check`
over what it wrote and **deletes it on failure**. A factory-built desk passes
exactly the gates the shipped one passes, or it does not exist; there is
deliberately no weaker path for generated records.

Two of the ten questions decide whether the desk is worth building at all:

- **Tier.** `authority_permits_choice` fires only on secondary or tertiary
  authority. A desk built entirely on binding primary sources cannot escalate —
  measured on `fixed-assets`, where that half of the design could not trigger
  once across 42 answers.
- **The corpus.** If the stored authority is the same text the answers are read
  from, citing correctly is an assignment puzzle and the citation score measures
  nothing. Measured on `fixed-assets`, 4 September 2026: 21 problems, 21 stored
  passages, a bijection between them. `guards.authority_is_more_than_the_answer_key`
  now fails the build on it.

Nothing in the factory is accounting-specific. `fixed-assets` is where the
questions came from, not what they are limited to.

## Why Markdown and not YAML

This plugin installs with `pip install pytest` and nothing else, because a plugin
that lifts out whole is worth more than one with conveniences. Python has no YAML
in its standard library. Canon already parses this shape, so the choice was
between reusing a format that works and adding a parser beside it — and a record
ratified by reading a diff should read like prose in that diff.

## Running it

```
cd desk && pytest -q
```

The suite is offline by construction: `conftest.py` replaces the socket layer, and
a test proves that guard itself can fail. Verification reads stored text; freshness
is a separate job, so a government website being down never turns CI red.
