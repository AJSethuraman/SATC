# The SATC Forge

The firm's own hardware, and the intended home for SATC workloads. Written
down on 26 August 2026 because it appeared nowhere in this repository and an
agent searching for it found only four hits, all about email forgery.

**Surveyed on the machine itself, 3 September 2026**, by the first Claude Code
session ever to run on it rather than in a cloud container.
`docs/forge-first-run.md` is the checklist that was followed. Everything below
was measured unless a row says otherwise.

The headline: **the hardware is as described and the isolation is not.** Two of
the four arrangement claims — the Hyper-V sandbox and the Storage Spaces mirror
— do not exist on this machine at all.

---

## The machine — measured

| | Reported 26 Aug | Measured 3 Sep | |
|---|---|---|---|
| CPU | Ryzen 5600X | **AMD Ryzen 5 5600X**, 6 cores / 12 threads, 3.70 GHz | ✅ |
| GPU | RTX 2070 | **RTX 2070 SUPER**, **8192 MiB**, driver 610.88 | ✅ 8 GB confirmed |
| Platform | AM4 | AM4 — board is an **ASUS PRIME B550-PLUS AC** | ✅ |
| RAM | — | **32 GB**, 4 × 8 GB Corsair `CMW16GX4M2Z3600C18`, **running at 2666 MT/s** | ⚠️ below rating |
| Disk | — | **One** NVMe: Crucial `CT1000E100SSD8`, 931.5 GB, Healthy. **C: only — 930.5 GB total, 833.3 GB free** | ⚠️ single disk |
| OS | unknown | **Windows 11 Pro, 10.0.26200**, 64-bit. Shell is PowerShell | answered |
| Power | UPS on the line | **not checked** — not measurable from software | unverified |

**The memory runs at 2666, not its rated 3600.** Both `Speed` and
`ConfiguredClockSpeed` report 2666, the JEDEC fallback, so no DOCP/XMP profile is
applied. Four single-rank sticks on AM4 is the configuration that most often
refuses to train at rated speed. Recorded as a fact, not a recommendation —
nothing in this repository is memory-bandwidth-bound, and the machine notes
elsewhere say not to touch memory settings.

## How it is arranged — two of these were not true

| Claimed 26 Aug | Measured 3 Sep |
|---|---|
| **Hyper-V isolation for a Claude Code sandbox** | ❌ **Does not exist.** `HypervisorPresent: False`; the `vmms` service does not exist; every Hyper-V optional feature reads `InstallState 2 = Disabled`; `Get-VM` is unavailable. There is no VM, and there could not be one without installing the role first. |
| **Storage Spaces mirror for the client vault** | ❌ **Does not exist.** The only storage pool is `Primordial`; `Get-VirtualDisk` returns nothing; there is exactly one physical disk. A mirror is not merely absent, it is **impossible** on one disk. |
| **Tailscale for remote access** | ✅ 1.98.10, service Running. Node `satc-forge` / `satc-forge.tail189451.ts.net`, **100.125.166.122**, Online. **3 devices, one account.** Funnel **off**, no exit node. `serve` proxies :5051, :8000, :8765 — tailnet-only. |
| **Ollama running on the host** | ✅ 0.32.5, bound **`127.0.0.1:11434`** (loopback only, not `0.0.0.0`), API answers. |

**The sandbox claim mattered and it was wrong.** This session runs directly on
the host, as the owner's own user, with the owner's own filesystem in reach —
including the live client vault. Everything an agent does on this machine is
done to the real machine. That is not an argument for building the VM; it is an
argument for knowing which of the two you are in, because the safety story the
notes told was the VM's.

**The mirror claim mattered more.** The backup section below was written when
the mirror was believed to exist. It does not, and a disk is not a backup of
itself.

## Ollama — the open question, answered

Four models are pulled, all Q4_K_M, all modified 29 July 2026:

| Tag | Size | Native ctx | Use |
|---|---|---|---|
| `qwen3:8b` | 5.2 GB | 40960 | completion, **tools**, thinking |
| `qwen2.5vl:7b` | 6.0 GB | 128000 | **vision** |
| `SATC-Assistant:latest` | 5.2 GB | 40960 | Modelfile derivative of `qwen3:8b` |
| `SATC-DocReader:latest` | 6.0 GB | 128000 | Modelfile derivative of `qwen2.5vl:7b`, **vision** |

Already set in the user environment: `SATC_OLLAMA=1`,
`SATC_OLLAMA_MODEL=qwen2.5vl:7b`, `OLLAMA_MAX_LOADED_MODELS=1`.
`satc doctor` reports **local vision enabled and reachable**, so the document
readers' local rung has a real model behind it for the first time.

**Not measured: whether any of them places 100% on the GPU.** `ollama ps` was
empty — nothing resident — and loading one to find out is a write the survey did
not make. It matters most for `SATC-DocReader`: a 6.0 GB model on an 8 GB card,
where the 8192-token context ceiling recorded elsewhere was measured against the
5.2 GB `qwen3:8b`, not against this. Re-measure before relying on it.

## Toolchain — measured

| | Measured | Against what was assumed |
|---|---|---|
| Python | **3.12.10, and only 3.12** (`py -0p` lists one) | The suite is described as targeting **3.11**. It passes on 3.12; nothing here needs 3.11 |
| Browser | **Chrome 151.0.7922.76**, **Edge 152.0.4191.53** | Present |
| Playwright | **Was absent machine-wide** — no pip package, no `ms-playwright` cache | Installed this session (Chrome Headless Shell 151) so the render tests could run at all |
| Tesseract | **5.4.0.20240606** at `C:\Program Files\Tesseract-OCR\` — **not on PATH** | Works; `satc doctor` auto-detects it once the `[ocr]` extra is installed |
| Node / Git | v24.18.0 / 2.55.0 | Present |
| Base interpreter | **Bare** — pytest, flask, yaml, openpyxl, playwright all `ModuleNotFoundError` | Every project needs its own venv; three were created this session |

**`LongPathsEnabled = 0`.** Windows' 260-character `MAX_PATH` limit is in force.
Not academic: redirecting pytest's temp directory to a long scratchpad path
failed with `[WinError 3] The system cannot find the path specified` on every
template copy. Anything here that builds a deep temp tree needs a short root. It
was not changed — that is a system-wide registry setting and the owner's call.

## Where the client data actually is — the notes had this wrong

`docs/forge-first-run.md` and the previous version of this document both named
`client-documents/leads.xlsx` and `client-documents/engagements/` as the real
client data on this machine. **Neither exists anywhere on it.**

- `leads.xlsx` — searched the whole user profile, unbounded depth. **Not found.**
  Leads are code (`client-documents/leads.py`) writing into a database.
- `client-documents/engagements/` — **not found.** The only `engagements`
  directory on the machine is `credit-review-os/src/credit_review/engagements/`,
  which holds 14 `demo_*` YAML fixtures for an unrelated product.
- `client-documents/` itself exists only in a fresh clone; the checkout the firm
  actually works in predates that directory.

**The real client data is one directory**, in the working checkout at
`C:\Users\ajish\Documents\Main\repos\SATC` (branch `feat/comms-templates`,
HEAD 7 Aug 2026):

| File | Size | Modified |
|---|---|---|
| `satc_system/build/data/satc_mart.db` | 200,704 B | 7 Aug 2026 |
| `satc_system/build/data/satc_vault.db` — **the encrypted identity vault** | 20,480 B | 3 Aug 2026 |
| `satc_system/build/data/vault.key` | 296 B | 1 Aug 2026 |

None were opened. Two things about that list want a decision:

1. **`vault.key` sits in the same directory as the vault it encrypts.** Whatever
   threat model AES-256 was chosen for, "someone who can read the directory" is
   not in it. Copy the folder and you have both halves.
2. **A stray copy of real client data exists outside the store:**
   `C:\Users\ajish\.claude\jobs\636d65af\tmp\sarcia-before-repair.xlsx`,
   160,585 B, left behind on 30 July 2026 by a one-off repair job. Not opened.
   It should probably not still be there.

The safety instruction in `forge-first-run.md` is still exactly right — point
tests at a temporary store, never commit client data — but it named the wrong
files, so anyone following it literally would have guarded an empty path while
the real vault sat somewhere else.

---

## What this means for the software in this repo

Recorded as consequences, not as decisions — the firm has not been asked to
sign off on any of these.

**Local-first is now a stated requirement, not an inference.** The firm has
also said: *"all software also needs an easy to use interface and such, easy to
install. ideally it can be ran locally and hosted through the SATC forge."* So
"runs on one machine, installs without ceremony" is a design constraint on
everything here, and anything that only works as a hosted service is swimming
against it.

Where each project stands against that today:

| Project | Runs locally | Notes |
|---|---|---|
| `client-documents` | yes | `python cli.py`, `make web` for the browser front door. No service dependencies |
| `invoice-generator` | yes | One command on Windows (`run.ps1`), or `docker compose up`. Also deploys to Render, which is the part that would move |
| `satc_system` | yes | Flask GUI on port 5050, SQLite. Already local-only by design |
| `website` | n/a | Public site; belongs on Cloudflare Pages, not the Forge |

**Ollama on the host is the interesting one.** Three things in this repo are
candidates for local inference rather than a hosted API, and all three are
places where client data would otherwise leave the building: the document
readers in `satc_system`, the intake, and the estimator. The firm named exactly
those. The model question is now answered above; the prompt contract and the
accuracy bar are still unanswered.

**The vault already assumes something like this.** `CLAUDE.md`'s hard
constraint — names and TINs in an AES-256 encrypted identity vault, split from
the de-identified working data mart — is a design that wants exactly this kind
of home: mirrored local storage, reachable only over a private network. **The
mirror half of that does not exist.**

**The 8 GB card is a real constraint and it is now confirmed.** 8192 MiB
measured. That comfortably runs quantised 7–8B models and does not run large
ones, so any local-inference design has to be built for a small model rather
than assume it can fall back to a big one.

---

## The software had never been run on Windows, and it did not work

The first run of `client-documents` on this machine produced **several hundred
errors**, in a suite that had been green in the cloud that morning. Neither
cause was a test being wrong; both were the software meeting Windows for the
first time.

**1 · `%-d` is a glibc extension.** Eight call sites across seven modules
formatted dates as `"%B %-d, %Y"`. On Linux that is `September 3, 2026`; on
Windows it raises `ValueError: Invalid format string`. Every test that dated a
letter, an estimate or an invoice errored. Fixed by `client-documents/dates.py`,
which builds the day from `.day` — an `int`, so there is no platform to branch
on — and guarded by `tests/test_portable.py`, which scans the source rather than
formatting a date, because a test that formatted one would only ever prove the
platform it ran on.

**2 · A default Windows console is cp1252, and this software does not speak it.**
Twenty-two modules in `client-documents` draw with characters cp1252 does not
have — the rule `─` under every heading, the `→` in a next-step line, the `←` in
the walkthrough, the real minus `−` the invoice's field doc asks for — and
`satc_system`'s readiness report prints ✅ and ⚠️ per row. Every one of those
raises `UnicodeEncodeError` at the moment it is printed.

It produced the worst-shaped failure of the three. `exercise.py` built all 190
documents, opened every one in a browser, reported **0 refusals, 0 with
something unexpected** — and then died printing its own summary table, on a `→`.
**Exit code 1.** The work was finished and correct; the only thing that failed
was saying so, and a harness that exits 1 after doing everything right reads as
a harness that found something wrong. `satc doctor` failed the same way, less
subtly: the readiness check crashed on the machine whose readiness it was
checking.

Fixed by `client-documents/console.py` (`speak_utf8()`, called first thing in
`cli.py` and `exercise.py`) and the same two lines in
`satc_system/src/satc/cli.py`. Both use `errors="replace"`: on a console that
genuinely cannot draw a glyph, a `?` in one column still leaves the sentence
around it readable. `web.py` needs no guard — its `─` characters go into HTML
responses, never to a console. The guard is in the entry points rather than at
import, so that importing a module never reconfigures somebody else's streams.

`tests/test_portable.py` covers this by forcing `PYTHONIOENCODING=cp1252` in a
subprocess, which reproduces the Windows console on any platform — verified to
exit 1 without the fix and 0 with it.

Both had been latent for about a year, for the same reason: **the target machine
had never once run the code.** That is the finding this survey exists to
produce, and it is worth more than any hardware row above.

A third problem was environmental rather than a defect: pytest's default temp
root `C:\Users\ajish\AppData\Local\Temp\pytest-of-ajish` is **unreadable** —
`os.scandir` and even `icacls` return `Access is denied` — left over from a run
under some other security context on 7 August. It was not deleted, because a
directory whose ACL cannot be read is not one to remove without asking. Runs use
`PYTEST_DEBUG_TEMPROOT=C:\Users\ajish\.pt` instead, which is also short enough
for `MAX_PATH`.

## What the suites actually do here

Measured 3 September 2026, after the fixes above. Each project has its own venv;
the base interpreter has nothing in it.

| Suite | Result | Time |
|---|---|---|
| `client-documents` | **1,362 passed, 2 skipped** | 8m05s |
| `satc_system` | **470 passed, 1 skipped** | 43s |
| `invoice-generator` | **57 passed, 1 skipped** | 20s |

**The denominator reconciles exactly.** The cloud container collected 1,360 that
morning and reported 1,358 passed / 2 skipped. This machine collects 1,364 —
those 1,360 plus the four new tests in `tests/test_portable.py` — and reports
1,362 passed / 2 skipped. The two skips are the same two: `test_editor.py`'s
"no numbered sections", which depends on template content rather than on the
machine. **Nothing is skipped here for being Windows.**

Getting there took three runs, and the first two are the interesting ones:

| Run | Result | What it was measuring |
|---|---|---|
| 1 | 1,345 passed, **15 skipped** | 13 tests skipped because they read `exercise.py` output that did not exist yet |
| 2 | 1,356 passed, **6 skipped** | after `exercise.py` ran — 3 still skipping on the hardcoded Chromium path, 1 on `capture.py` output |
| 3 | **1,362 passed, 2 skipped** | after `presend.launch_args()`, `pypdf`, and `capture.py` |

The three that skipped in run 2 are the ones worth naming, because they are the
failure this repository has thirty-five tenets about. They reported
`no Playwright/Chromium here — the render gate cannot be exercised, and is NOT
being asserted` **on a machine where `exercise.py` had just opened 190 documents
in a browser.** The message was honest and the premise was false, and a full
green run said nothing about it. One of the three, once un-skipped, **failed** —
it had been green by absence.

All nine `renders` tests — the ones that open a real document in a real browser
— ran and passed in every one of the three runs. `pytest.ini` is unchanged.

`exercise.py`: 29 scenarios, 190 documents, **0 refusals, 0 with something
unexpected**, every one opened in a browser. `capture.py`: 22 screens, 97
controls, every screen reached. `cli.py doctor`: 12/12 templates, chromium
engine, no open decisions. `satc doctor`: every row ready.

8m05s against the cloud's 11–13 minutes, on six cores, with more of the suite
actually running than ran there.

Two skips elsewhere are worth recording rather than fixing here, because both
are dependency decisions rather than defects:

- `invoice-generator` skips `test_deploy_gate.py` — `No module named 'yaml'`.
  That project declares no test dependencies at all (`pytest` itself had to be
  installed by hand), and its `requirements.txt` is what Render installs in
  production, so adding one is a call for the firm rather than a repair.
- `satc_system` skips `test_corpus_score.py` — `corpus/blanks is empty`. It
  wants sample documents that are not in the repository.

---

## Answered, 3 September 2026

**The Forge is where the practice runs.** Asked whether real client data lives
there or whether it is a test rig on synthetic data, the firm chose the first.
That settles two questions at once — client documents live there, and the
machine serves the firm rather than merely hosting a sandbox. (Measured
correction: the data is in the two SQLite databases named above, not in a
workbook and a folder.)

What that changes for anything working on that machine:

- **Never commit client data, never copy a real value into a test fixture, a
  sample, an artifact or a commit message.**
- A test run that globs the engagement store will walk real clients. Point
  tests at a temporary store, never at the live one.
- The rule about masked/last-4 values in `CLAUDE.md` stops being a design
  intention on that machine and starts being the thing standing between a real
  taxpayer's TIN and a log file.

## THE BACKUP GAP, WHICH IS NOW A LIVE RISK AND NOT AN OPEN QUESTION

Asked what backs up the client data, the firm's answer was **nothing yet** —
the Storage Spaces mirror is all there is.

**The survey found that the mirror is not there either.** One disk, one volume,
no pool, no virtual disk. So the position is worse than recorded: it is not
"mirrored but not backed up", it is **not redundant and not backed up**. A
single NVMe drive holds the vault, the key to it, and the only copy of both.

Written plainly because it stopped being hypothetical the moment real client
data moved onto the machine: **git backs up the code and nothing backs up the
clients.** A mirror survives a failed disk. It does not survive a fire, a
theft, a ransomware run, or somebody deleting the wrong folder — and the two
things it does not survive are the two that take the whole practice with them.
Without the mirror, it does not survive the failed disk either.

What a real answer needs, when it is time: off-machine, encrypted, automatic,
and a restore that has actually been performed. A backup nobody has restored
from is a hope.

### Being closed, 3 September 2026 — OneDrive

The firm chose the SATC OneDrive, which also turns out to be where the lead
intake lives — the reason the survey could not find `leads.xlsx` anywhere on
this disk. **The SATC tenant was already registered on the machine**
(`WorkplaceJoined: YES`, `Sethuraman Accounting Tax and Consulting LLP`), but
OneDrive itself had been removed in the 29 July debloat and was reinstalled for
this.

**Two decisions the firm made, and they are the whole design:**

1. **The vault syncs; `vault.key` does not.** They sit in the same directory
   today, and copying both to one cloud folder would mean the tenant holds the
   ciphertext and the key side by side — at which point AES-256 protects nothing
   the account password was not already protecting. So `satc_vault.db` and
   `satc_mart.db` go up and the key stays off-cloud.

   ⚠️ **This makes the key a single point of failure, deliberately.** If this
   disk dies and the key is not somewhere else, the backup restores a file
   nobody can read. **The key still has no second home** — that is the one thing
   left before this counts as a backup. `--check-key` says so every time it is
   asked.

2. **Live client data only** — `satc_mart.db` and `satc_vault.db`. Not the
   orphaned 2021–2024 engagement letters and tax workbooks the survey found in
   the stale personal OneDrive folder (`C:\Users\ajish\OneDrive`, 741 files,
   683 MB, untouched since the debloat, real client documents interleaved with
   game saves). Those are still backed up by nothing and are a separate job.

`satc_system/scripts/backup_client_data.py` does the work.
`install_backup_task.ps1` registers it daily at 12:30 **and at logon** — both,
because this machine starts things at logon rather than boot, so a daily-only
trigger would quietly do nothing across a reboot nobody logged back into.

It meets three of the four bars already, and is honest about the fourth:

| | |
|---|---|
| off-machine | ✅ once signed in — the SATC tenant, not the personal account, which the script enforces by reading `OneDriveCommercial` rather than `OneDriveConsumer` |
| automatic | ✅ scheduled, with output appended to `~\.satc\backup.log` so a failure is visible after the fact |
| **a restore actually performed** | ✅ **done, not asserted.** `--verify-restore` copies the backup back out, opens it, and compares every table to the live database. Measured this day: `satc_mart.db` 22 tables / 102 rows, `satc_vault.db` 3 tables / 21 rows, both identical. The scratch copy is deleted afterwards — proving a backup works is not a reason to leave a second unencrypted vault lying in a temp directory |
| encrypted | ⚠️ **the vault already is; the mart is not.** `satc_mart.db` is the de-identified working mart and goes up as-is, protected by the tenant. Whether that is good enough is a question for the firm, not an answer this document should invent |

Two guards, both verified to actually fire rather than merely exist:

- The run **refuses** if `vault.key` is found anywhere in the destination and
  exits non-zero — not "we did not copy it" but "it is not there", whoever put
  it there. Tested with a dummy file: exit 1.
- Every copy is taken with SQLite's **online backup API**, not a file copy, so a
  database being written to cannot be captured mid-transaction, and every copy
  is reopened and `PRAGMA integrity_check`ed before the run reports success.

**Still open:** sign-in. It is an interactive login and could not be done for
the firm; until it happens the job runs, fails loudly, and says why. And the
key still needs its second home.

**This is a deliberate deviation from local-first.** `CLAUDE.md` says client
data stays on the firm's own hardware rather than in a vendor cloud. Sending the
vault to Microsoft is a decision the firm made on 3 September 2026 with the
alternative — one disk, no redundancy, no backup — in front of them. Recorded
as a decision so it does not later read as drift.

## What is still unknown

- Whether anything is expected to be reachable from outside Tailscale.
  (`tailscale serve` proxies three ports, tailnet-only, and nobody wrote down
  what :5051, :8000 and :8765 are for.)
- **Whether any Ollama model places 100% on the GPU**, and what context ceiling
  the 6.0 GB vision model can hold. Not measured — it requires loading one.
- Whether the UPS is on the line. Not measurable from software.
- Whether `feat/comms-templates` — the branch the firm's working checkout sits
  on, a month of work — was ever merged. Checking needs a `git fetch` in a
  checkout this session was told not to write to.
- Whether the Hyper-V sandbox and the Storage Spaces mirror were **intended and
  never built**, or built and later removed. The notes read as intent.

Ask before designing against any of these.
