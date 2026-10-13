# The desk, redone — brief for a new agent

*Written 13 October 2026, for the firm to paste into a new Claude Code session
on this repository. Everything after the line below is the brief.*

---

You are taking over **the desk**: what an agent doing a client's books consults
when it hits a tax or accounting question it can't settle itself. The firm has
judged the current version a failure, and you are free to redo it. Read this
brief, then `CLAUDE.md` at the repository root, then decide what to build. Don't
read the desk's history first. It records the approach that failed, and it will
pull you back into it.

## 1. The goal, in the firm's words

These are the firm's words. Where you're unsure what to build, they decide it.

> *"the point of this is to have it look for sources and convey and if it is
> not directly authoritative it would run the opinion by me."*
> — 8 September 2026

> *"Not only do we let it fetch but we might have to reason and figure it why it
> stopped."* — 8 September 2026

> *"the entire point of this is for the desk to work self-sufficiently and be
> able to actually help the agent answer stuff"* — 29 September 2026

> *"the final check for this for V1 will be to have Forge - Occam install the
> new plugin we are designing and run a close from start to finish on Sarcia
> Services [...] this implies that the skill is able to call for questions and
> receive back answers from Forge - Desk"* — 8 September 2026

What that means:

- **An agent asks, and the desk finds the answer itself.** When the desk
  doesn't already hold the law a question needs, it goes and gets it from the
  official source, checks it word for word, and answers from it.
- **Binding authority gets used. Anything else goes to the firm.** The Internal
  Revenue Code and Treasury regulations bind. IRS publications, rulings and
  guidance don't bind in the same way: the desk brings what it found, and how
  much it can be relied on, to the firm instead of answering from it.
- **A gap is the desk's to close.** The last version failed here. Each time the
  desk found it was missing something, a human patched it by hand in a pull
  request, and the next run found the next gap. A desk that needs a person
  between runs isn't self-sufficient.
- **It answers with a citation or not at all.** An answer must name the
  paragraph it rests on, and that paragraph must say what the answer claims.

## 2. The test that says it works

**Forge-Occam runs a month-end close on Sarcia Services from start to finish,
asking Forge-Desk whatever it can't settle, with no human changing the desk
between the start and the end of the run.**

- **What to report:** of the questions Occam asked, how many the desk answered
  correctly with a citation, how many it correctly brought to the firm, and how
  many it got wrong or couldn't handle. Give the counts, not percentages alone.
- **Who decides "correct":** the firm. If you want a grading key, write it and
  seal it (commit it before the run) so the run can't shape it.
- **For comparison:** the last run, pilot 5 on 27 September, answered 14 of 17
  questions with a citation. It needed hand-fixes to the desk before and after.
  Ledger: <https://claude.ai/artifact/MAKMAVLQ7iFqDeexSWH79H>.
- **Sarcia** is a real client engagement (an LLC, a general contractor), and
  this is its FY2025 close: 485 bank and card rows in Occam. Occam is the
  firm's bookkeeping app; it lives in its own repository, not this one.

## 3. The firm's standing rules for the desk

- **Don't prepare the desk.** *"No, you don't record anything. Why are you not
  getting this?"* (8 September 2026; the third time they had said it). No facts
  are loaded about a client before a run. If the desk needs a fact nobody has
  given it, that is a finding: it asks, the agent asks the firm, and the firm may
  step in to supply it.
- **The pilot measures the gaps, it doesn't hide them.** *"the entire point of
  this pilot is for us to test whether the desk asks for the info and whether the
  principal gives it back and if they can"* (8 September 2026). A refusal naming
  a missing fact is output, not failure.
- **Feedback on the desk goes to the firm first.** *"if the other agent sends
  you feedback on the desk ensure we discuss it first and you break down what it
  means"* (8 September 2026). When Occam or Forge-Desk reports something about
  how the desk behaved, explain it to the firm before changing anything. A
  question sent to the desk is different: answer it on the spot.
- **Fetch over HTTP, never through a browser on the firm's computers.** *"why in
  the world was my primary desktop used to go to the eCFR site and not the
  forge"* (27 September 2026). Claude in Chrome and computer use are off limits
  unless the firm names the device. eCFR and uscode.house.gov both serve text
  over plain HTTP.
- **No small-model testing.** *"We currently do not need to test against
  ollama"* (September 2026).
- **No client data in this repository.** Names, SSNs and EINs never go in code,
  logs, commits or pages; `CLAUDE.md` covers this under "Hard constraints".

## 4. What exists that is proven

Reuse any of it or none of it. Each of these was checked against something
outside itself; the rest of `desk/` (13,560 lines of Python, 22 modules) is the
approach that failed, and you owe it nothing.

| What | Where | Why it can be trusted |
|---|---|---|
| **The stored law.** 1,257 passages from 41 sources (30 primary, 9 secondary, 2 tertiary): Code sections, regulations, IRS publications, a few rulings | `desk/corpus/SOURCES.md` lists each source, its URL, how binding it is, and whether its text may be stored. `desk/corpus/extracted/` holds the text | Every passage was sliced from the publisher's own document by a script, none retyped. Each batch was tied out word for word against the live page when it was added; the runs are in `desk/tie-outs/` |
| **The firm's own positions.** 20 answers the firm approved: 16 read off a paragraph of law, 4 firm policy where the law leaves the choice open | `desk/corpus/positions/` | All 20 are ratified by the firm |
| **Fetching the law.** eCFR (regulations) through its API, uscode.house.gov (the Code) by page | `desk/ecfr.py`, `desk/fetch.py`, `desk/tools/extract_ecfr.py`, `desk/tools/extract_uscode.py` | They refuse anything they can't place exactly, rather than guessing |
| **The word-for-word check.** Is this stored text still on the publisher's page today? | `desk/proving.py` (`prove_passage`), `desk/comparing.py`, `desk/tools/tieout.py` | It tells "the text moved" apart from "we got a bot page instead", and never upgrades an unchecked answer to a checked one |
| **The messaging link.** Occam sends all its questions in one message to the Forge-Desk session and reads the answers back | `desk/relay.py` (`ask_many`, `batch_prompt`, `read_batch`), the `ask-desk` and `be-the-desk` skills in `desk/skills/`, `desk/docs/WHERE-THE-DESK-IS.md` | Used in five pilots; in pilots 3 and 5 every answer came back and was readable |
| **A searcher.** Looks anywhere on the web for a source the desk doesn't hold, then checks the find against the publisher | `desk/searching.py`, `desk/looking.py` | Exists and is tested, but it only runs after the desk has already refused, and nothing it finds can feed an answer until a human merges it. Judge it yourself |

The desk's tests pass on `main` (1,844 passed, 1 skipped, re-run 29 September
2026). The suite is offline by construction: `desk/conftest.py` blocks the
network, and a test proves that block can fail.

## 5. The machines, and where things stand

- **Forge** is the firm's own computer. Two long-running sessions live there:
  - **Forge - Desk** (`session_016cgnNu73t4Y3pGyMYTNExh`) answers questions.
  - **Forge - Occam** (`session_01MGioK4n8HDriSiEKkPJXbr`) does the books and
    asks.
  - A second, archived "Forge - Occam" (`session_01G7Arwi6Wa8WyWihFur8JrN`)
    exists. Don't use it.
- **Both live sessions have been disconnected since 1 October 2026**: the
  computer was unreachable. Nothing runs until the firm turns it on and the
  sessions reconnect.
- **Forge - Desk left a note the firm hasn't read.** Its last status reads
  *"found entailment gap in 0.40.0 output; awaiting prompt copy request"*. An
  **entailment gap** means the cited words don't fully support the answer given.
  Ask the firm to read it to you; per section 3, discuss it before acting.
- **Desk plugin version: 0.40.0**, on `main` and installed on the Forge. It ships
  through the repository's own plugin marketplace
  (`.claude-plugin/marketplace.json`). Bump the version in that file and in
  `desk/.claude-plugin/plugin.json` together.

## 6. Open items that aren't the desk's

Five decisions about **Sarcia's books** wait on the firm. They stand whatever
happens to the desk:

1. Let Occam post 27 rows its safety check stopped.
2. When to count the 189 job-materials rows.
3. Where card rewards go.
4. Whether to re-import Occam's corrected rules.
5. Whether to keep Occam's rename of three rules to "Merchant Fee".

They're on the docket: <https://claude.ai/artifact/LRiVL2zxYLi7dQxMKfGKZs>.
That page also holds two questions about the old desk's design; treat those as
closed by this redo.

## 7. How work lands here

`CLAUDE.md` governs; the short version:

- **Branches and PRs:** work on a branch, open a draft pull request, and merge it
  yourself once CI passes and Codex has finished reviewing. Merge with a merge
  commit pinned to the head that passed.
- **Before merging:** make sure the branch contains current `main`.
- **Talking to the firm:** message only when something is finished or you need
  them, not while you work. Write in plain English, and when you must use a term
  of art, say what it means.
