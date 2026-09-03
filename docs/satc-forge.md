# The SATC Forge

The firm's own hardware, and the intended home for SATC workloads. Written
down on 26 August 2026 because it appeared nowhere in this repository and an
agent searching for it found only four hits, all about email forgery.

**It is up, as of 3 September 2026.** The firm: *"the forge is up and
operational."* Everything below is still the firm's description as given on
26 August; **nothing here has been verified against the running machine yet.**
`docs/forge-first-run.md` is the survey that will replace this section with
measurements, and until it has been run, treat every specification below as
reported rather than confirmed.

---

## The machine

| | |
|---|---|
| CPU | Ryzen 5600X |
| GPU | RTX 2070 |
| Platform | AM4 |
| Power | UPS on the line — added after a surge incident |

## How it is arranged

- **Hyper-V isolation** for a Claude Code sandbox.
- **Storage Spaces mirror** for the client vault.
- **Tailscale** for remote access.
- **Ollama** running on the host.

## What it is for

- A **local-first, privacy-conscious home** for SATC workloads — client data on
  the firm's own hardware rather than in a vendor cloud.
- A **sandboxed environment** for Claude Code agent work.
- **Local LLM inference via Ollama**, for the work that should not touch a
  third-party API: document readers, intake, the estimator.
- **Redundant storage for the client vault**, reachable remotely over Tailscale.

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
those. Nothing has been built against a local model yet, and the choice of
model, the prompt contract and the accuracy bar are all unanswered.

**The vault already assumes something like this.** `CLAUDE.md`'s hard
constraint — names and TINs in an AES-256 encrypted identity vault, split from
the de-identified working data mart — is a design that wants exactly this kind
of home: mirrored local storage, reachable only over a private network.

**The GPU is a real constraint worth knowing.** An RTX 2070 is 8 GB. That
comfortably runs quantised 7–8B models and does not run large ones, so any
local-inference design has to be built for a small model rather than assume it
can fall back to a big one.

---

## Answered, 3 September 2026

**The Forge is where the practice runs.** Asked whether real client data lives
there or whether it is a test rig on synthetic data, the firm chose the first:
the real leads workbook and real engagements. That settles two of the questions
below at once — client documents live there, and the machine serves the firm
rather than merely hosting a sandbox.

What that changes for anything working on that machine:

- `client-documents/leads.xlsx` and `client-documents/engagements/` hold real
  names, emails, phone numbers and engagements. They are gitignored on purpose.
  **Never commit them, never copy a real value into a test fixture, a sample,
  an artifact or a commit message.**
- A test run that globs the engagement store will walk real clients. Point
  tests at a temporary store, never at the live one.
- The rule about masked/last-4 values in `CLAUDE.md` stops being a design
  intention on that machine and starts being the thing standing between a real
  taxpayer's TIN and a log file.

## THE BACKUP GAP, WHICH IS NOW A LIVE RISK AND NOT AN OPEN QUESTION

Asked what backs up the client data, the firm's answer was **nothing yet** —
the Storage Spaces mirror is all there is.

Written plainly because it stopped being hypothetical the moment real client
data moved onto the machine: **git backs up the code and nothing backs up the
clients.** A mirror survives a failed disk. It does not survive a fire, a
theft, a ransomware run, or somebody deleting the wrong folder — and the two
things it does not survive are the two that take the whole practice with them.

The firm has chosen to run the suite on the Forge first, which is the right
order for proving the machine works. This is recorded so that it is a decision
about sequence rather than something that quietly never happened.

What a real answer needs, when it is time: off-machine, encrypted, automatic,
and a restore that has actually been performed. A backup nobody has restored
from is a hope.

## What is still unknown

- Whether anything is expected to be reachable from outside Tailscale.
- Whether the Forge's Claude Code sandbox is Windows or a Linux guest — which
  decides half the tooling questions and is the first thing the survey answers.
- Which Ollama model is pulled, and at what quantisation.

Ask before designing against any of these.
