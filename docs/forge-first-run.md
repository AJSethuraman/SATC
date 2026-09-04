# First run on the Forge

The checklist for the first Claude Code session that connects to the firm's own
machine over Remote Control. Written in the cloud, before anybody had touched
the hardware, so that the first session **measures** rather than assumes.

`docs/satc-forge.md` records what the machine is *said* to be. Everything there
came from the firm in conversation on 26 August 2026 and none of it has been
checked. This document is how that section stops being hearsay.

**Report what you did not check as not checked.** A survey that quietly skipped
half the machine and printed a tick is the failure this repository has thirty-five
tenets about.

---

## 0 · Before anything: what is on this machine

Real client data lives here — the firm confirmed it on 3 September 2026. So
before running anything that walks a directory:

- `client-documents/leads.xlsx` is the firm's real leads workbook: real names,
  emails, phone numbers.
- `client-documents/engagements/` holds real engagements.
- Both are gitignored, and both must stay out of every commit, fixture, sample,
  artifact, screenshot and commit message.

**Any test run must be pointed at a temporary store.** Several commands take
`--store`; the suite builds its own. Check before running anything that does not.

---

## 1 · Survey — say what the machine actually is

Detect, do not assume. The forge doc says Ryzen 5600X / RTX 2070 / Hyper-V /
Storage Spaces / Tailscale / Ollama. The Claude Code sandbox may be Windows or a
Linux guest inside Hyper-V, and that decides half of what follows.

Establish and write down:

| | Why it matters |
|---|---|
| OS and shell of the session | Decides every command below. The firm works in PowerShell |
| Whether this is the host or a Hyper-V guest | A guest may not see the GPU, the mirror, or Ollama |
| CPU, RAM, free disk | The suite writes PDFs and screenshots; disk is the one that bites |
| GPU visible to this session, and its VRAM | 8 GB caps local inference at a quantised 7–8B model |
| Python version | The suite targets 3.11 |
| A browser Playwright can drive | `renders` tests and the walkthrough open real documents |
| Tesseract | The OCR path in `satc_system` |
| Ollama: reachable, and which models are pulled | The paystub reader's local rung has never met a real model |
| Where the client vault and the mirror are mounted | And whether this session can see them at all |
| Tailscale state | How the machine is reached, and from where |

Then **update `docs/satc-forge.md` with what was measured**, replacing the
reported figures. Note every difference from what was reported — a machine that
is not what the notes say is the single most useful thing this survey can find.

---

## 2 · Get the code

```
git clone https://github.com/AJSethuraman/SATC.git
cd SATC
git checkout claude/satc-handoff-batches-2-4-n2qrl9-b7-fee-estimate
```

The branch matters: the payment check, the redesign and the stage bar are all on
it and not yet on `main`.

**GitHub stays the backup for the code.** Nothing about running on the Forge
changes the workflow: branch, commit, push, draft PR. If anything, it matters
more here, because this is now the machine with the irreplaceable data on it.

---

## 3 · Run the suite — the firm's chosen first job

```
cd client-documents
python -m pytest -q
```

Expect **1,358 passed, 2 skipped**, around 11–13 minutes. That is the number
from the cloud container on 3 September 2026; a different number is news either
way.

Nine of those tests open a real document in a real browser. If they fail, the
machine is missing a browser and the suite is measuring less than it looks like
it is — which is exactly what `make fast` exists to say out loud.

Also run:

```
python -m pytest -q          # the whole thing. never trust `make fast` here
python exercise.py           # 29 scenarios, 190 documents, every one opened
python cli.py doctor         # what blocks a real render
```

And the other projects, which have never run on this machine either:

```
cd ../satc_system  && PYTHONPATH=src python -m pytest -q ; python -m satc.cli doctor
cd ../invoice-generator && python -m pytest -q
```

**Report the denominator.** "The suite passes" is not a result. "1,358 passed, 2
skipped, 11m40s, nine render tests among them" is.

---

## 4 · What to say at the end

Three lists, and the third is the one that earns trust:

1. **What was measured**, against what the notes claimed — every difference named.
2. **What passed**, with numbers and times.
3. **What was not checked, and why.** A GPU this session cannot see, a mount
   that is not there, a model not pulled, a test skipped. Say it.

Then commit the updated `docs/satc-forge.md`, push, and say what the machine
still needs before it can be trusted with the work it now holds.

---

## Two standing rules for working on this machine

**One session writes at a time.** A cloud session and a Remote Control session
editing the same tree will collide — that happened on 3 September when a
background agent and the main session were both in `web.py`. Whichever session
is working commits before handing over.

**The backup gap is open and the data is real.** Recorded in
`docs/satc-forge.md`. Nothing on this machine is backed up except the code, and
the code is the part that was never at risk.
