# Workpaper Studio voice

How the product's own words read: every heading, column, button, banner, note and message on its screens, and the
same words in the workbooks it generates. It does not cover the words an organization writes into its own tools
(questions, field labels, guidance). Those are theirs.

## Why this file exists

The firm, 2 Nov 2026, on the Results heading *"Why: every partially or not effective answer, with its comment"*:

> *"in no world do you say things like this in a final version of a usable product - you expect your employees and
> such to be able to understand what the field is based on a title card"*

And, asked for the second time, *"i really need you to use my voice … i just hate how some of this looks."*

The cause was the same as PocketBook's (`pocketbook/VOICE.md`): text written to explain the software, put on the
software. A heading that defends or narrates the design (*"Nothing here can be changed or removed: the case on
screen is rebuilt from this list"*) belongs in the docs, not on the screen. The people using Studio are reviewers,
testers, auditors and their managers. They read a title and know what the section holds.

## The register

**A finished product's labels.** Headings, columns and buttons are names: short noun phrases, the way a competent
firm titles a workpaper section. They are never sentences, questions or explanations.

| Before | After |
|---|---|
| Why: every partially or not effective answer, with its comment | Ineffective and partially effective ratings |
| How each question was answered | Ratings by question |
| Answers that differ from the master database | Changes to master data |
| Work from the master database | Work list |
| Who is working? | Sign in |
| What each level can do | Permissions by level |
| Always true, whatever is ticked | Fixed controls |
| Every version ever proposed | Version history |
| Take the data | Downloads (CSV) |
| Results against limits | Limit tests |
| Enter and change a case's answers | Edit case entries |

**Status words, not narration.** A state reads as a state: *Pending acknowledgment*, *Not confirmed*, *Awaiting
approval*, *Not applicable*, *None*. Not *"Waiting for the reviewer to acknowledge it."*

**Messages say what happened or what is needed, once.** *Released.* *Work list loaded: 4 new, 0 existing, 2
refused.* *Permission required: Approve cases. Granted to D. Patel, K. Owens.*

## What does not go on a screen

- **Explaining the design.** For example, *"A limit belongs to this organization, not to the method"*, or *"The
  master database is read, never written."* True, and documented in `DATA-RECORD.md` and `DECISIONS.md`. Not
  screen copy.
- **Reassurance and self-protection.** For example, *"It is not a password check"*, *"Nothing here is saved or
  becomes a case"*, *"These are the record."* The rules are enforced in the software. The screen does not need to
  promise them.
- **Instructions a professional does not need**, such as *"Tick what each may do."*
- **Filler**: anything that would be true on every screen.

## What stays

- **The profession's vocabulary**: exception, acknowledgment, release, limit, reviewer, preparer, master data,
  fingerprint.
- **Full sentences where a sentence is the content**: a refusal that names the reason, a load that says why a line
  was refused.
- **American spelling**, as the firm set for PocketBook.

## How it is held

`tests/test_voice.py` renders every screen as every kind of user and checks every heading the application writes
(`h2`, table headers, section bars, summaries). Each one must be six words or fewer, must not end like a sentence,
must contain no colon, and must not open with *Why*, *How*, *What*, *Every*, *Nothing*, *This*, *Here* or *Each*.
Those are the mechanical rules. The others are not mechanical, and they are broken more often: use the label a
reviewer would write, and leave the explanation in the docs.
