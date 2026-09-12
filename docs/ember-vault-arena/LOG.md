# Ember Vault Arena — running log

The durable log for this project. It migrates with the folder to the
`ember-vault-arena` repository. Newest entry first. The canon record
(`canon/CONVICTIONS.md`, *Rulings by project*) holds the rulings on which
convictions apply here; this file holds everything else.

## 12 September 2026, 03:10Z — docket issued; the next goal on record

Docket published as a form the firm fills in:
<https://claude.ai/code/artifact/33468545-8341-4cf4-a4e3-d40f88271339>.
Answers save to the artifact's store (`decisions/d1` … `d6`) and are read
back from there into this log; nothing is decided by the session.

**Next, unless the firm says otherwise:** hold PR #359 green and watched
until it is merged; the moment a gate pack or a full-match ledger lands under
`runs/`, read it, record what the token counts say about the cost, and score
the gate once both reader sheets exist. Ends when the PR is merged and the
house gate has a score. Distance: milestones 2 of 5; M2 built and waiting on
one run and two readers. Silence approves only that. Merging stays the
firm's (C2/C5); nothing enters canon without a yes; the readers score the
gate, not the session (C6); nothing from M3 on until the gate has been read.

**Asked (D1–D6):** run the gate in a plain terminal or approve it in the
forge session (recommended: terminal); merge PR #359 now or hold
(recommended: now); who the two blind readers are; run one twelve-round
match on the subscription after the gate, or wait (recommended: after the
gate, from the forge session); create the private repository after the
merge (recommended: after); who the eight players are and by when.

**State read at issue, from the repository:** PR #359 head `decfc9d3`,
10 of 10 checks green, mergeable, no review threads; arena suite 91 of 91
(15.8 s); canon 190 of 190 (25.9 s); forge session idle at `need_input`
since 20:21Z, rate-limit status "allowed, not in overage"; gate not run on
a model; no push under `runs/` since 20:15Z.

## 11 September 2026, 20:15Z — the subscription route works: 8 of 8 on the forge

The hands session on the forge (`ajish-5a`, Windows 11, Python 3.12,
claude-agent-sdk 0.2.152) ran the smoke test and pushed
`runs/20260911T201514Z-agent-sdk.md`:

- **answered by the model: 8 of 8**, `agent_sdk/opus`, 7.9–10.5 s per call,
  eight concurrent, 17.6 s wall clock, no API key anywhere. **The
  subscription route is real.**
- **Defect found by the run:** the ledger showed 0 tokens in and out against
  a recorded cost of $0.58. The adapter read `usage_metadata`; the SDK's
  result message carries `usage` (a dict). Inspected the installed SDK here
  (`ResultMessage` fields: subtype, duration_ms, duration_api_ms, is_error,
  num_turns, session_id, stop_reason, total_cost_usd, usage, result,
  structured_output, model_usage, errors, api_error_status, …) and fixed the
  read; the `errors` list now rides into the reason column. The fake in the
  tests is reshaped to the real message.
- **The cost figure is the SDK's own estimate at API rates.** On the
  subscription nothing is charged per call; the number is what it *would*
  cost on a key, and at ~$0.07 a call it is above the PRD's $0.02–0.03
  estimate. The token counts the fix now records will say why.
- **The gate did not run.** The forge session's auto-mode permission
  classifier refused `tools/gate.py` with "[Create Unsafe Agents]" while
  allowing the identical adapter through `run.py demo`. The session did not
  route around it, correctly. Open with the firm: approve the command in
  that session, or run it in a plain terminal from
  `C:\Users\ajish\SATC-eva\docs\ember-vault-arena\code`.
- Forge → cloud messaging: the forge cannot see `satc-6c`; git is the return
  channel. Cloud → forge: **did not land after the forge's first turn.** A
  routine bound to the forge session fired at 20:13Z while it was mid-run (its
  results file does not mention receiving it); fires at 20:21Z, 20:27Z and
  20:31Z, and an interrupt in between, left it IDLE at `need_input` with no
  new push as of 20:42Z. Stopped firing at that point rather than keep
  knocking. Recorded as a finding: a Routine bound to a Remote Control
  session is not a reliable inbound channel while that session sits at its
  prompt, whatever the July incident suggested about triggers.
  `ListAgents` from the cloud lists no Remote Control session. Open with the
  firm: the next instruction (pull, re-run the smoke test for real token
  counts, one full twelve-round match, push the ledgers) is written in this
  log and in the routine's text; paste it into that session by hand if it
  never arrived.

## 11 September 2026, later — golden replay pinned, suite in CI, hands on the firm's machine

- **Golden replay (PRD §5.40).** `tests/golden/seed52.json` pins the seed-52
  mock match: 26 snapshot hashes, placements, scores, winner, event count.
  `tests/test_golden.py` re-runs it with no model and compares; regenerate
  with `tools/write_golden.py` only when a rule change is meant to move the
  match, and say so in the commit. Suite 89 → 91.
- **CI.** `.github/workflows/test.yml` gains `docs/ember-vault-arena/code` as a
  matrix project (`pip install pytest`, `pytest -q`); a one-line `conftest.py`
  puts the folder on `sys.path` so plain pytest finds `arena`.
- **The hands.** The firm started a Remote Control session on their machine
  (`Ember Vault Arena smoke test`) with the checklist prompt. `SendMessage` by
  name could not reach it from the cloud; a Routine bound to its session id
  (`trig_01BMtQXYkyZ2FMQzSLr6UPNq`) delivered a message on the first fire. Its
  results come back as pushes under `docs/ember-vault-arena/runs/`.

## 11 September 2026, night — M0 and M1 built, M2's harness built and run on the mock

The firm went to bed with *"just kind of trust you can start getting this
together without me"* and *"For anything that requires a sprite I want a stand
in"* (July's inline SVG silhouettes are the stand-ins; nothing new was drawn).

**Built, and proven at the seams the PRD names.** Suite 62 → **89, all green**.

- `agent-action-1.0` and brain manifest v1 (`models.py`): speech as an object
  with say/whisper/silent, the private note, `give`, and `deal` accepted but
  **null only** until M3 opens it. Old `reasoning_summary`/`memory_write` gone.
  Schemas generated from the constants and pinned; a test compares (S8).
- Brain template and loader: five headed sections, 2,000-character cap with a
  refusal naming the section and the overage, links and blobs refused.
- Engine: the note round-trips (written round N is `your_note` in round N+1;
  audience sees it via `note_written`; rivals never); whispers reach one and
  the room sees only that it happened; `give` moves an item; one transport
  retry then `guard`, logged as `network_fallback` or `panic_fallback`; a
  call ledger on every decision (latency, retries, cached tokens, cost and its
  source, stop reason, request id, error kind, effort, digests).
- Adapters: `agent_sdk` (subscription, `tools=[]`, replacement system prompt,
  JSON schema draft-07, one turn, empty cwd, `setting_sources=[]`) and
  `anthropic` (Messages API, structured output, `max_retries=0` so the engine
  owns retries, refusal → panic). Both lazily imported; both stub-tested.
- Gate harness `tools/gate.py` + `tools/score_gate.py`; eight house brains
  written to the template by a separate agent (each build twice).

**Checked the checkers.** Three wires cut one at a time, each turned a test
red: no transport retry (2 tests), whisper heard by the whole room (1), note
in the mid-match projection (1). Restored; suite green.

**Opened the artifacts.** `run.py demo --seed 52` on the new contract completes
and audits; the July story viewer built from it renders in Chromium with no
page or console errors (screenshot taken). The gate harness ran on the mock:
142 calls, pack written, no real name or id in it. The first mock run leaked
the key — the anonymiser wrote each character's letter into its own brain —
caught by reading the pack, fixed, rerun.

**Re-aimed one July test** (`test_replay_needs_no_model_call`): it asserted a
dead provider reproduced the mock's hashes, because July fell back to the mock
itself. The PRD's default is `guard`, so the test now asserts a dead provider
yields the same match every time, completes, and says `network` on every
decision, with exactly one retry.

**Decided in the build, worth knowing:**
- The July 18,000-token per-agent budget was a cost cap by another name and
  would have flipped agents to autopilot mid-match on a real model; raised to
  10,000,000 under the firm's no-cap ruling. The ledger measures instead.
- The Crown cannot be handed over with `give`; it changes hands only by being
  taken. A gift would be a transfer that resets attunement, which M3 decides.
- The mock's note is deterministic and carries no judgement; the README says
  a mock gate run proves the pipeline and nothing about brains.

**Not done, and why:** the gate has not run on a model — it needs the firm's
login (subscription) or key. Nothing from M3 on was touched, per the PRD.

**Not checked:** `claude-agent-sdk` was never installed or exercised here;
the adapter is proven only through fakes shaped to the documented result
message. The morning checklist's first step is the real call.

## 11 September 2026 — ground-up rebuild grilled; PRD written

**Goal, in the firm's words** (confirmed as the one line every decision is
checked against): eight people each write a short prompt for a character; the
eight characters go on one themed adventure together, long enough to have a
beginning, a middle and an end, with dangers that can actually kill them and
side characters they can talk to; at the end one of them wins; afterwards a
person watching can tell what each character wanted, who lied to whom, and why
the winner won. *"The final product is a live stream or something."*

**Decided today** (details in `PRD.md`): live stream, private pilot in a Discord
call; 48 rounds in four acts, about an hour; Ember Vault world grown by hand to
~16 locations and ~12 live objectives; one Crown-style win, score places the
rest, public standings; four builds in play, one build for the gate; brains as
fixed sections under 2,000 characters, one file per player; three house talkers
on the model (lying guide, side-playing merchant, rival envoy), monsters in code;
deals structured, recorded, never enforced, breaks public; speech capped ~300
chars, one-round lag, verbatim and quarantined, with whispers; private objective
shown to the audience live; dead is dead; Opus 5 for everyone, same settings,
recorded; narrator in text with template fallback; one-round buffer; 20 s per
call, one retry, 30 s per round, then the default, logged as `panic` or
`network`; subscription via the Agent SDK first with an API-key adapter kept
ready and an unwatched full-length dry run before the pilot; no cost cap, cost
measured; new private repo (creation refused from the session, 403, manual);
Python + stdlib + SDK, July's engine reused (62 of 62 tests passed here).

**Verified rather than trusted:** July's suite run in this container, 62/62 in
17 s. July's server serves finished replays only; its round loop blocks; its
intent pool is four workers. July's provider adapter speaks the chat-completions
shape, not the Anthropic API, and is rewritten.

**Facts looked up, not recalled:** first-party pricing (bundled reference,
cached 24 Jun 2026); a Max plan excludes the API but the Agent SDK draws from
subscription limits, the separate monthly credit having been paused 15 Jun 2026
(support articles 15036540 and 9876003, read through summaries because the
domain is proxy-blocked here — **re-read once in a browser before the pilot**);
Agent SDK options and result fields (Python reference; structured-outputs page).

### Roadmap `[LOG]`

- **Public broadcast** on Twitch or YouTube is the destination. Before the first
  public stream: the content rules for player-written brains and model speech,
  moderation at submission and on speech, and the publication check (canon C5:
  the rule is publication, not the branch name).
- **Haunting**: a dead character keeps one whisper a round and no actions. The
  first experiment after the gate; the live reframe makes it more attractive
  because the player stays in the show.
- **Champions round**: resubmitted brains meet again. A later format; identity is
  kept from v1 so it is possible.
- **Cross-model matches** as a separate, labelled format.
- **Follow-one-character** camera toggle (P1 in the PRD).
- **Talkers as legal targets** (P1 in the PRD).

### Explicitly deferred (decided against for now) `[LOG]`

- **A cost cap.** *"I'm not trying to these dollar limits yet."* Cost is measured
  per call and reported; nothing stops a match on money.
- **A submission form or accounts.** One text file per player to the operator.
- **Moderation beyond the character cap and the operator reading each brain**,
  while the audience is private.
- **Reputation across matches fed to a character.** Each setup is new.

### Decisions log

- **2026-09-11 · Canon applies case by case, ruled once.** The firm: *"Case by
  case on a permanent basis. We strike it done or uphold it once then move on
  unless something held re-conflicts."* Rulings live in `canon/CONVICTIONS.md`.
- **2026-09-11 · C10 struck for this project.** Hosted models are the target;
  the provider seam stays.
- **2026-09-11 · Each match starts clean; a brain keeps its id.** Resolves C11
  against the July non-goal.
- **2026-09-11 · The gate is a harness with a score.** Two blind readers match
  eight anonymised transcripts to eight brains over three seeds; pass is six of
  eight for both. First run on house brains written to the template, then on
  the players' brains.
- **2026-09-11 · Balance on the mock, divergence on the model.** Two gates, two
  tools; a 500-seed run on the model would cost thousands.
- **2026-09-11 · Deals are structured because the referee reads no prose.** The
  brief's "unenforced but recorded" is only possible with offer/accept fields.

### Open with the firm

- Create the private repository `ember-vault-arena` and say when.
- Who the eight players are and when their brains arrive.
- Who the two blind readers are for each gate run.
- One browser read of the two support articles before relying on the
  subscription route.

### What this session did not check

- The July engine source beyond its interfaces, docstrings and test names.
- The July build spec beyond five sections.
- Whether `claude-agent-sdk` installs and runs eleven concurrent queries here.
  That is the dry run's job, not this session's.
