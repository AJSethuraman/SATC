# Ember Vault Arena — running log

The durable log for this project. It migrates with the folder to the
`ember-vault-arena` repository. Newest entry first. The canon record
(`canon/CONVICTIONS.md`, *Rulings by project*) holds the rulings on which
convictions apply here; this file holds everything else.

## 12 September 2026, 09:05Z — a correction to this log's clock

The four entries below dated 08:20Z, 08:35Z, 08:50Z and FORGE.md's 08:52Z,
08:15Z and 08:06Z sections were first written with headings about an hour
ahead of the clock (09:05Z, 09:40Z, 10:05Z, 10:10Z, 08:50Z, 08:20Z). The
git commit times are the truth and the headings now match them. The forge's
files that cite "the 08:50Z orders" mean the section now headed 08:15Z.

## 12 September 2026, 08:50Z — the cost gap found: the SDK bills counts the ledger never saw

The forge's probe (`runs/20260912T083032Z-sdk-probe.md`) and ledger reprint
(`runs/20260912T082930Z-ledger-reprint.md`), read here:

- **One model.** `model_usage` has one key, `claude-opus-5`; the alias
  `opus` resolves to it and no helper model is billed.
- **The SDK prices list rates on the counts it believes it sent, to the
  cent:** 457 in × $5/M + 4 out × $25/M = $0.002385 = `total_cost_usd`.
  So the 5.5× gap on arena calls is not a rate card. The top-level `usage`
  on a schema-constrained arena call (2 uncached + 2,060 cached + 341 out,
  $0.0096 at list) describes a fraction of what was billed ($0.0525): about
  8,600 uncached input tokens a call go unrecorded, close to the first ~10k
  guess and about three times the compiled prompt. The forge withdrew its
  earlier "wrong in the useful direction" reading; both readings stand
  together.
- **Where the divergence lives**, from the SDK's own shape: `usage` carries
  an `iterations` array (one entry on the trivial probe), and
  `model_usage[model]` carries its own counts and `costUSD`. On the probe all
  three agree; on an arena call they cannot, since `costUSD` is list price
  on `model_usage`'s counts.
- **Fixed on the branch:** `sdk_counts()` reads `model_usage` first, then the
  sum of `iterations`, then the top-level fields; the ledger now records the
  counts the cost is priced on. Test per rung; the `model_usage` read goes
  red under mutation. `AgentSDKProvider.raw_result()` exposes the raw
  message, and `tools/probe_sdk.py --match <id>` replays a stored arena
  prompt with the schema attached and prints the three prices side by side.
  FORGE.md asks the forge to run that once, then a fresh one-round smoke,
  which together say whether the recorded counts now reproduce the cost.
- **What it means for the estimate:** if ~8,600 uncached tokens a call is
  real, the cost is what the prompt weighs at list, not a fault, and the
  PRD's per-call estimate (~2,000 input) was three times too light. The
  next question is why a ~3,000-token compiled prompt bills as ~8,600, and
  whether it is cacheable; the arena probe's `iterations` answers the first.
- Suite 99 → **100**. Two commits held locally until the forge has merged
  PR #359, so CI stops restarting under it.
- The `KEY.json` in the pushed gate pack stays tracked and in history; the
  decision is recorded rather than rewritten: that pack's readers take it
  from a checkout, the firm is not a reader for it, and every later key
  stays off the branch.

## 12 September 2026, 08:35Z — a full match on the subscription: won at round 16

The firm answered D4 in the forge's session (*"Do all 48 rounds."*; to the
cloud: *"48 is the new number. You guys hash this out I gave them my spec."*).
The forge ran `--rounds 48` at HEAD `7534d45d` and pushed
`runs/20260912T082658Z-agent-sdk-full.md` (`cd5dcddf`, merged in at
`4b11aadc`). Read here:

- **106 of 106 answered**, no network fallback, no panic, no rate-limit or
  overage message. **4 min 56 s** wall clock: about 18 s a round with eight
  callers in parallel. The five-hour window carried it without complaint.
- **The match ended at round 16 because it was won.** Grael extracted the
  Ember Crown (`crown_extracted`, `ended_reason: extraction`); `--rounds` is a
  ceiling, the Crown is the clock. Attrition: 8 alive for rounds 1–5, 7 for
  6–9, 6 for 10–13, 5 for 14–15, 4 at 16. The builders report three acts,
  because acts are a function of round number.
- **First design input for M4, and a decision for the firm on the next
  docket:** the show promises about an hour and 48 rounds; July's world lets a
  match end at 16. Either the world grown at M4 makes 48 the norm (more
  ground between the Crown and the exit, later act boundaries), or the rule
  changes so an extraction does not end the match. The grill's decision was
  "one winner, everyone else placed by score"; which of those two reaches it
  is the firm's call. Also: 18 s a round is far faster than the ~1 min a
  round the stream wants, so M4's pacing is a deliberate slow-down, not a
  speed problem.
- **Secret objectives:** eight characters drew three distinct objectives,
  four of them `lorekeeper`. The manifest's default objective is derived from
  the id over July's small pool. The gate is about brains, not objectives,
  but half the field privately chasing one goal is worth widening at M3/M4.
- **Cost per call climbs with the round** ($0.052 at round 1 to ~$0.10 by
  round 13) while the ledger's `in` stays 2 on every row, and one call
  (round 12, perrin, 649 tokens out) cost $0.0266, a third of its
  neighbours. Hypothesis, to be settled by the probe and by the reprint with
  the cached column: with `output_format` the CLI makes more than one API
  step per query, `ResultMessage.usage` reports the last small step (2
  uncached + a cached prefix) while `total_cost_usd` sums every step,
  including the first, which reads the whole growing prompt and pays cache
  *creation* on it; the cheap outlier would be a call whose first step hit the
  cache. If that is right, the SDK's cost is the honest number and the
  ledger's token counts are the wrong step's. The probe prints `model_usage`
  and `num_turns`, which decides it.
- The replay export and all three builders ran clean on a real-model match
  (0.5 s), closing one "not checked" item from the docket.

Total recorded $7.67 for the match, the SDK's estimate at API rates; nothing
charged on the subscription.

## 12 September 2026, 08:20Z — the gate key moves out of the readers' folder

Done rather than left proposed: `tools/gate.py` now writes the key to
`gate/<run>.key.json`, beside the pack and outside source control
(`.gitignore`), and prints where it went; `tools/score_gate.py` reads the key
beside the pack first and falls back to `KEY.json` inside, so the pack already
on the branch (`20260912-034624-agent_sdk`) still scores. Consequence for the
firm: the key of every future run lives only on the machine that ran the gate;
lose it and the run is rerun, not recovered. `tests/test_gate.py` (new, 3)
pins: no `KEY.json` inside a pack and a key beside it; no house name or id in
any transcript or brain a reader receives (the check done by hand at 08:05Z);
the scorer on both layouts. Suite 96 → **99**.

The firm, 08:18Z, on the measurement match: *"Oh I'll do 48 then."* FORGE.md
carries the 48-round command; the forge runs it on the firm's word in its own
session.

## 12 September 2026, 08:50Z — tokens are real; three ledger defects fixed

The forge's smoke re-run on the fixed adapter (`c248f882`,
`runs/20260912T080438Z-agent-sdk-smoke-tokens.md`, addendum `7534d45d`):
8 of 8, 16.6 s; output 341–501 tokens a call; input **2 uncached + 2,060
read from cache** on every call. Its findings, checked here against the
code, and what they caused:

- **The ledger printed the uncached count alone** (`in 2` for a 2,062-token
  prompt). `cli.py` now prints `in`, `cached`, `wrote`, `out` and a totals
  line. Test: the cached count appears on the row; totals sum every count.
- **Cache creation was never read.** `cache_creation_input_tokens` is now
  read by both adapters and stored in a new `cache_creation_tokens` column;
  `ArenaStore` migrates a database that predates it on open (the forge's
  does). Test: an old-schema database gains the column.
- **The SDK route recorded the alias, not the model.** The ledger said
  `opus`; `RATES` is keyed by id, so a cross-check found nothing. The adapter
  now records the keys of `ResultMessage.model_usage` (the ids the CLI
  billed, joined with `+` if more than one). Test: the fake's `model_usage`
  key lands in `result.model`.
- **A money bug of mine.** `cost_of` did `input_tokens - cached`, treating
  the API's `input_tokens` as inclusive of cached tokens. It is not: the API
  reports uncached, cache-read and cache-written as three counts that do not
  overlap, so every cached call had its full-rate tokens zeroed. Fixed and
  tested with the forge's own numbers: 2 in, 341 out, 2,060 cached →
  $0.009565 at the table's rates. Mutation: dropping the cache-write term
  turns the test red.
- **The SDK's cost figure disagrees with its own counts** ($0.0525 reported
  against $0.0096 by the table for the same call; $0.4296 against ~$0.08 for
  the run; the identical run priced $0.5821 on the 11th). Not explained.
  Candidates: the alias resolving to a model with another rate card; a
  second model billed inside the CLI; cache creation priced but reported as
  reads. `tools/probe_sdk.py` (new) makes one trivial call and prints the raw
  `usage`, `model_usage` and `total_cost_usd`; FORGE.md asks the forge to run
  it once. **On the subscription none of this is charged**; it matters for the
  API-key fallback and for the PRD's estimate, which by token counts is now
  *above* the real cost, not below it.
- The forge measured the compiled prompt at ~11.5–12.1k characters (2,867
  system, the rest per contestant) against 2,062 tokens reported: fewer
  tokens than the characters suggest, so nothing CLI-sized rides along. The
  ~30% shortfall wants a real tokenizer; not chased.

Suite 91 → **96** here. Mock demo on a fresh database prints the new columns.

## 12 September 2026, 08:20Z — the forge reached the cloud; the cloud cannot reply

At 08:04Z the forge's session messaged this one by title (*Ember Vault Arena
rebuild*): the pack was pushed, it had read the 08:05Z entry, it was
re-running the smoke test at `c00f98e0` for token counts, and it was holding
the twelve-round match until the firm answers D4. A reply from here was
refused: *"this cloud session cannot message other sessions yet."* So the
channel is one way (forge → cloud) plus git. Standing orders for the forge
now live in `FORGE.md`, newest first; the forge reads it after `git pull`.
The firm, 08:03Z: *"I'm going to have that agent work with you. I will likely
not be checking for a bit."*

## 12 September 2026, 08:05Z — the gate has run: 136 of 136 on the subscription route

The firm approved `tools/gate.py` in the forge session (docket D1). The forge
ran it 07:46–07:52Z and pushed `62b190d7`: the pack
`code/gate/20260912-034624-agent_sdk` and
`runs/20260912T075242Z-agent-sdk-gate.md`. Read here, not trusted:

- **136 of 136 answered**, 358 s wall clock, no network fallback, no panic,
  no invalid line. **136, not 144:** C was eliminated in seed 102 round 2
  (four rounds never owed), G in seed 103 round 3 (three), H in seed 103
  round 5 (one). Dead is dead, per the PRD; the count is right.
- **Leak check, done here on the pushed pack:** a grep for the eight house
  names and ids over `transcripts/` and `brains/` finds nothing; the brain
  files are headed `Brain N`, not a letter (the leak the mock run had);
  characters refer to each other by letter, which is the anonymiser working.
- **Cost recorded $8.55**, about $0.063 a call: the SDK's estimate at API
  rates, consistent with the smoke test's $0.072, and still above the PRD's
  $0.02–0.03. The forge ran at HEAD `d539d35f`, before the token-field fix,
  so this ledger carries no token counts. Explained only by a run on the
  fixed adapter (docket D4).
- **The key is in plain text on the branch.** `KEY.json` is committed inside
  the pack, as the mock pack's was, so anyone browsing PR #359 or this
  session's output can see it. Consequence: the firm should not be a reader
  for this run; the docket's D3 recommendation now says so. Proposed for the
  next run and not done now, because the pack on the branch is the one the
  readers will use: write the key outside the readers' folder.
- The end-of-seed line reveals each character's secret objective and whether
  it was met; that is the design (the audience sees the objective), and a
  reader sees it too.
- The forge session went to RUNNING at 07:56Z; its next result arrives as a
  push. Its rate-limit status at that moment: allowed, not in overage.

Docket republished with D1 marked done, the gate row updated, and D3's steps
naming the real pack. PR #359 body updated: "the gate has not run on a
model" is replaced by what ran and what is still unscored.

## 12 September 2026, 04:18Z — docket answer: D1

Read back from the docket's store at the 05:11Z check-in (`decisions/d1`,
written 04:17:59Z, note empty):

- **D1 · Run the gate — "Approve in the session."** Not the recommended
  route; the firm's call. What it causes: the firm pastes the approval
  sentence into the forge session (the one titled *Ember Vault Arena smoke
  test*), allows the command when asked, and the session runs
  `tools/gate.py`, commits the pack under `code/gate/` and pushes it to the
  branch. Nothing for this session to run; the pack's arrival is the signal.
  As of 05:11Z the forge session had not moved (last turn 20:21Z on the
  11th) and no pack had been pushed.

D2–D6 unanswered at 05:11Z.

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
