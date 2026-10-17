---
name: voice
description: Draft anything the firm will send, sign or publish so it reads like they wrote it, and talk to the firm the way they talk. Use whenever you draft an email, a reply, a message, a memo, a comment, a procedure, a methodology or guidance document, a write-up or a summary for the firm, or when the firm says it doesn't sound like them. Picks the register by who will read it, checks the draft against a sentence the firm actually wrote, and runs the mechanical tells before they see it.
---

# Voice

The firm, 14 October 2026:

> *I want you to talk to me like me and I want things drafted for me to sound like me*

## Where the voice is, and where it is not

```
${CLAUDE_PLUGIN_ROOT}/VOICE.md     how the firm talks and writes, with their sentences
${CLAUDE_PLUGIN_ROOT}/voice.py     the mechanical tells, each with its source
```

**Read from there, always, not from a copy you happened to find.** A machine
with the canon repository checked out has a second copy at `canon/`, and that
one is whatever branch or half-finished edit is sitting on that working tree.

**Never write there.** The plugin directory is replaced on every update. A new
before-and-after goes into `VOICE.md` in the **canon repository**, through a
pull request, and reaches other machines with
`claude plugin marketplace update satc` and then
`claude plugin update canon@satc`. The first only refreshes the listing; the second is what installs
the new version.

## Drafting something for the firm

1. **Name who reads it.** A client, a colleague by email, a quick chat reply, a
   technical explanation, a procedure, or an analyst reading a tool's output.
   Each one reads differently, and `VOICE.md` has the table.
2. **If it's for a client, the project's client-copy rules win.** This skill
   never overrides them. In SATC that's *Client-facing copy* in the root
   `CLAUDE.md` and `website/TENETS.md`.
3. **Find a sentence of theirs in the same register,** under *Their sentences*
   in `VOICE.md` or in the project's own files. Write yours to sit next to it.
4. **Draft it.** Purpose first, enough context to follow, one concrete example
   if the logic needs one, what's known kept apart from what's assumed, and an
   ending that says what happens next.
5. **Run the tells:**

   ```
   python "${CLAUDE_PLUGIN_ROOT}/voice.py" draft.md
   ```

   Fix anything it finds. It can't tell a word you used from one you're
   quoting, so a hit inside a quotation is yours to judge. A clean run means
   only that those particular tells weren't found, so read it once more next to
   their sentence.
6. **Hand it over as a draft,** with one line saying who you wrote it for. If
   you had to guess at a fact, leave `[CONFIRM: …]` in place rather than
   inventing it.
7. **When they rewrite it, that's the best evidence there is.** Offer to add
   the before and after to *Their rewrites* in `VOICE.md`, quoting exactly what
   they wrote. Nothing goes in without their yes.

## Talking to the firm

This applies to every reply, not only drafts. The rules are under *Talking to
the firm* in `VOICE.md`, and canon prints them at the start of every session.

## What you never do

- Copy their typos, lowercase or jokes to sound like them.
- Put a colleague's name, a figure, a system name, a customer detail or
  anything marked internal into `VOICE.md`. Their own procedures say it:
  "Avoid referencing actual names."
- Treat Copilot's profile as the firm's words. It's another AI's reading,
  labeled as one. Where it and a sentence of theirs disagree, the sentence wins.
- Add a tell to `voice.py` without a source the firm or the profile gave. A
  tell with no source is a session's taste.
