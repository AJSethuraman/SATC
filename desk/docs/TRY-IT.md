# Try it — twenty minutes, no client needed

Five things to do in order. Each one is a command you can paste, and each one
tells you something different about whether the desks are worth using.

**What you are testing.** A **desk** is an expert an agent asks so a question
does not reach you. It answers only from authority it can point at, says how
binding that authority is, and refuses rather than guesses. The point of this
run is to see what it hands back — including the refusals, which are most of it.

---

## 1. Install it

```
claude plugin marketplace update satc
```

```
claude plugin update desk@satc
```

**Both, in that order, and the second one is the one that installs.**
`marketplace update` only refreshes the listing — it looks like it worked and
changes nothing on disk.

```
claude plugin list
```

**Check it against the listing, not against a number written here.** A document
that states a version goes stale the moment the version moves — this one did,
twice in four hours.

```
python3 -c "import json;print(next(p['version'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']=='desk'))"
```

That number and `plugin list` must agree. If `plugin list` is lower the update
did not land, **and `plugin update` will still have said "already at the latest
version"** — content merged without a version bump reaches nobody and the
command reports success. Anything below 0.6.0 also still ships the engagement
file that was deleted.

---

## 2. Ask a desk something, and watch it answer

In a Claude Code session, say:

> Ask a desk: the bank statement shows a $10 service charge and nothing for it
> is in the books. What do I do with it?

The agent loads the `be-the-desk` skill and consults. (That is the local
shape — one session holding the desks and answering from them, which is what
this page walks. The session-to-session shape, where a doer sends the question
somewhere else, is `ask-desk` and `docs/THE-DESK-IS-A-SESSION.md`.) **What to look for:** it comes
back with a conclusion, one citation, and how binding that authority is — or it
tells you who has to be asked. It should never come back with a conclusion and
no citation, because the engine refuses that before it leaves the desk.

---

## 3. Ask one it cannot answer, and watch it refuse

> Ask a desk: does a hardware-store purchase ever become an asset?

**This is the interesting one.** Three desks have something to say and they say
different amounts. What you should see is a desk answering the part its
authority reaches and refusing the rest by name — not a desk stretching one rule
over a question it does not cover.

**Four refusals mean four different things**, and telling them apart is most of
the value here:

| It says | It means | Who fixes it |
|---|---|---|
| **authority_absent** | the record is missing a rule | search for it — step 5 |
| **facts_not_established** | the rule is clear, a fact about the client is not | ask the client |
| **document_not_requested** | a named document settles it and nobody asked | request it |
| **context_not_on_file** | the file does not record something we should already know | step 4 |

---

## 4. Watch it ask for something, and see which kind of missing it is

Some rules cannot be applied without knowing what the client does. The desk will
not work that out from the vendor — deliberately.

> Ask a desk: they bought clothing at that store — is that a personal expense?

**There is no file to make.** The caller passes what it already has; the facts
live where you already keep them — Occam's workbook, the engagement folder, the
interview. A desk that went looking for them would be inferring, which is the one
thing it must not do.

**What matters is which kind of missing you get back**, and this is the whole
point of step 4:

| | Meaning | Who fixes it |
|---|---|---|
| `context_not_on_file` | there **is** somewhere to record this and nobody has | a preparer fills it in |
| `no_field_for_this_fact` | there is **nowhere** to record it, anywhere | you decide the fact exists at all |

The second is a **hole in what the firm tracks**, and it is found by doing real
work rather than by auditing. Read them out — and note the path takes the
version from the listing rather than a number typed here, for the same reason as
above:

```
python3 ~/.claude/plugins/cache/satc/desk/$(python3 -c "import json;print(next(p['version'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']=='desk'))")/tools/holes.py
```

It opens by naming **what it read** — three places a refusal lands — then holes,
then gaps, and it never adds the filed queue to the live run.

**As of 7 September: no holes, and five gaps** on the close run — two desks
waiting on `capitalization_rule`, one on `trade`, two on `taxpayer`. Each names
the fact and the position that asked for it.

**The zero was briefly wrong, and the way it was wrong is worth knowing.** The
first version of this report read one of the three stores and printed
*"Gaps (0) — the mechanism is live and has not fired"* while those five stood in
the run. Nothing was broken; it was an unfinished read reported as a finding. A
count now says what it was counted over, so you can tell the two apart.

---

## 5. Send it looking for a rule it does not have

When a desk refuses `authority_absent`, something can go and find the rule.

> Load the run-down-a-question skill and work the open gaps.

**What comes back is a proposal, never a change.** It searches anywhere — you
cannot ask permission for a site you do not yet know you need — but nothing
enters the record unless the words are still on the publisher's own page today
**and** you have accepted that publisher. Everything else comes to you.

This has been run once by hand, on the tool-or-asset question: two paragraphs of
§ 1.263(a)-2 found, both checked back against the government's own file, both
brought to you rather than stored. You said declare it, and the desk answers that
question now.

---

## What would tell you it is not worth it

Worth naming in advance, so the test can fail:

- **A conclusion you disagree with, cited correctly.** That is the desk working
  and the position being wrong — fixable, and the interesting failure.
- **A conclusion with a citation that does not say what it claims.** That is the
  serious one. The engine checks the citation resolves; it cannot check that the
  paragraph *supports* the conclusion. If you find one, it is the most valuable
  thing you could hand back.
- **Refusals on questions you think are obvious.** Either the record is thin —
  fixable — or the desk is being asked something outside what it is for.
- **Refusals that are wrong about the record.** One was found on 7 September: a
  desk said it held nothing on a regulation it held ten paragraphs of. Those now
  arrive carrying how much the desk was actually shown, so you can see it.
