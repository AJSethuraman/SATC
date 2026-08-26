# The SATC Forge

The firm's own hardware, and the intended home for SATC workloads. Written
down on 26 August 2026 because it appeared nowhere in this repository and an
agent searching for it found only four hits, all about email forgery.

**It is not up right now.** The firm: *"we can get more info later when i have
it back up and running."* Everything below is the firm's description, recorded
as given. Nothing here has been verified against a running machine.

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

## What is still unknown

- Whether the Forge is meant to **serve** the software to the firm's own
  machines, or just to **host** the agent sandbox and the vault.
- Whether client documents are meant to live there, or only the vault.
- What the backup story is beyond the Storage Spaces mirror — a mirror
  survives a disk, not a fire or a mistake.
- Whether anything is expected to be reachable from outside Tailscale.

Ask before designing against any of these.
