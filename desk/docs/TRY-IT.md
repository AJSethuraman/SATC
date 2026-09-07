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

`desk` must read **0.5.0**. If it reads 0.4.0 the searcher's skill and the
engagement file are not there.

---

## 2. Ask a desk something, and watch it answer

In a Claude Code session, say:

> Ask a desk: the bank statement shows a $10 service charge and nothing for it
> is in the books. What do I do with it?

The agent loads the `ask-desk` skill and consults. **What to look for:** it comes
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

## 4. Give it an engagement, and watch refusals turn into answers

> **⚠ Read this before step 4.** The file below is a **stand-in I invented**, and
> the firm has said so: *"we dont have a method for creating an engagement file
> — also we wouldn't have an engagement file so much as the occam processer
> (which is our accounting software) has workbooks for clients."*
>
> **Three real containers exist and this is not one of them:** Occam's workbook
> (one Excel workbook per client, the bookkeeping source of record),
> `client-documents/engagements/` (one folder per engagement, ref `YYYY-NNNN`),
> and the interview. Checked on 7 September:
>
> | Fact a desk asks for | Where it really is |
> |---|---|
> | `taxpayer` | **already recorded** — the engagement record's `EntityType` and `_return_type` |
> | `trade` | not in the document store; Occam or the interview holds it |
> | `capitalization_rule` | **nowhere** — which is a field request, not a missing file |
>
> So step 4 exercises the *mechanism* and nothing else. **Do not start keeping
> client facts in it.** The adapters over the real containers are not built, and
> Occam is a separate repository this session cannot read — guessing its schema
> would be the same mistake again. `docs/WHERE-FACTS-LIVE.md` records what is
> established and what is still unknown.

Some rules cannot be applied without knowing what the client does. The desk will
not work that out from the vendor — deliberately.

```
python3 ~/.claude/plugins/cache/satc/desk/0.5.0/tools/engagement.py new alpha-2026 > ~/engagements/alpha-2026.md
```

Open that file. It has a stub for every fact the desks ask for, each naming the
desk that asks. Fill in what you know and **delete the rest** — a fact with no
value is refused, which is right: a half-written record reads exactly like a
recorded one.

```
python3 ~/.claude/plugins/cache/satc/desk/0.5.0/tools/engagement.py check ~/engagements/alpha-2026.md
```

It prints what the file holds **and what it does not**, with the desk that will
refuse without each one. Then ask the same question again with the file:

> Ask a desk, using ~/engagements/alpha-2026.md as the engagement: they bought
> clothing at that store — is that a personal expense?

**What to look for:** the same question that refused `context_not_on_file` now
gets answered. Measured on the close's own questions: five refusals became five
answers.

**The file is yours and does not live in the plugin.** `load` refuses a path
inside it — the plugin is a checkout that gets pushed, and a client's affairs in
it are one `git add` from being published. Nothing with a name, an SSN or an EIN
belongs in it either; the reader refuses anything shaped like a taxpayer number.

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
