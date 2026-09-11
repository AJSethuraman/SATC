# Ember Vault Arena — running log

The durable log for this project. It migrates with the folder to the
`ember-vault-arena` repository. Newest entry first. The canon record
(`canon/CONVICTIONS.md`, *Rulings by project*) holds the rulings on which
convictions apply here; this file holds everything else.

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
