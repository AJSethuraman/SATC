# PRD: Ember Vault Arena — v1, the live adventure

**Status:** Draft · **Owner:** AJSethuraman · **Last updated:** 2026-09-11

**Authority.** This PRD replaces the July 2026 documents under `code/docs/` (`CLAUDE_BUILD_SPEC.md`, `PRD.md`, `PRODUCT_V2.md`, `RULESET.md`, `SECURITY.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`). They are historical; where they conflict with this file, this file wins. The July *code* under `code/` is the starting point and is not historical: it is staged verbatim from commit `7252fa98` with its five generated demo outputs removed, and its suite ran here on 11 September 2026: **62 of 62 passed** in 17 s on Python 3.11.

**This folder is staged for migration.** It belongs in its own private repository, `ember-vault-arena`. Creating that repository from a session was refused (`403 Resource not accessible by integration`) on 25 July 2026 and again on 11 September 2026, so it is a manual step for the firm. Everything under `docs/ember-vault-arena/` lifts out whole.

---

## The goal

The firm, 11 September 2026, confirmed as the one line every later decision is checked against:

> Eight people each write a short prompt for a character. The eight characters go on one themed adventure together, long enough to have a beginning, a middle and an end, with dangers that can actually kill them and side characters they can talk to. At the end one of them wins. Afterwards a person **watching** can tell what each character wanted, who lied to whom, and why the winner won.

Their own words behind it, same day: *"V1 of this is having a sufficiently large adventure for the agents to go on with some sort of theme. It can have side characters and such. It should feel alive"*; *"there should be one winner in theory"*; *"Things have to be powerful enough to be a threat"*; *"This is meant to be a spectacle. Something you watch for awhile and hopefully it's amusing. It isn't meant to be a quick thing"*; *"the final product is a live stream or something. We can't rely on the replay to show things differently."*

**Shaping, labelled as the session's, not the firm's.** The smallest version worth having: eight brains on one themed adventure of four acts, three house-written side characters, one scoreboard, streamed live to a private page for about an hour. The first thing the goal refuses: anything whose purpose is to rank brains against each other across matches or across models — ratings, seasons, accounts, leagues, public sign-ups, video rendering.

---

## 1. Problem

Eight friends want to write a character each and watch the eight compete, unsupervised, in one fantasy adventure, live, for about an hour. The entertainment has to come from what the characters *do*: bargain, lie, hold a grudge, panic, betray. The fairness has to come from code the characters cannot touch.

The July 2026 build proved the referee half: a deterministic engine with seeded dice, an audit chain, replay without a model, and 62 tests. It never proved the entertainment half, for a reason the record now states plainly: its mock provider's speech never fed its decisions, so nobody has yet seen whether a one-paragraph difference between two brains produces behaviour a viewer can tell apart. It also assumed a pinned local model on one GPU, twelve rounds, and a replay watched after the fact. All three assumptions are gone: hosted models are the target, the match is about forty-eight rounds, and the product is a live stream with no editing pass afterwards.

## 2. Solution

Keep the July referee. Change what it referees, how the characters are called, and how the match is shown.

The engine runs a four-act, forty-eight-round adventure across a hand-drawn Ember Vault of about sixteen locations with about twelve things worth doing at any time, some of which need two or three characters. Each character is a player-written brain in fixed sections, called once per round on Opus 5 through the Claude Agent SDK under the firm's subscription, with an API-key adapter kept ready. Every turn the brain returns a structured action, a capped speech line that may be a whisper, an optional structured deal, and a short private note stating its current objective and its reads on the others. The referee records deals and their breaks, never enforces them, and shows the audience each character's private objective beside its public speech the moment it is written. Three house-written side characters with agendas run on the same contract. A narrator in text fills each round. A live page shows rounds as they resolve, one round behind the engine so a slow call never reaches the screen.

Nothing structural is built until the gate has run: eight brains, three short matches, and two readers who can match anonymised transcripts to prompts better than chance.

## 3. Goals & Non-Goals

**Goals**

- A forty-eight-round, eight-character match runs unattended from brain files to a finished, audited, replayable log.
- The match is watched live on a private page at about a minute a round, with the next round always generated before the current one finishes playing.
- A viewer can see, for every character and every round, what it said in public, what it whispered and to whom, and what it privately wanted.
- Deals are made, broken, and seen broken, without the referee ever reading prose.
- The gate passes: two blind readers match six or more of eight transcripts to brains, across three seeds.
- A full-length dry run completes on the subscription with fewer than 5% of calls falling to the default action, before any friend watches.
- Every model call, roll, deal, whisper and note is in the log, and a seed plus the log reproduces the match without a model.

**Non-Goals / Out of scope**

- Rankings, ratings, seasons, leagues, accounts, public sign-ups, or any cross-match reputation fed to a character. *(Firm, 11 Sep 2026: each setup is new; a champions round is a later format.)*
- A public broadcast. The destination is Twitch or YouTube; v1 streams to a private page and a Discord call. The content rules for a public stream are written before the first public stream, not now.
- Voice, text-to-speech, sprites drawn as art, video cuts, highlight reels, or any content engine.
- Cross-model matches. Same model and settings for everyone; a mixed-model match is a separate, labelled format later.
- A haunting or takeover mechanic for dead characters. Dead is dead in v1; haunting is the first experiment after the gate.
- A cost cap. Cost is measured per call and reported; nothing stops a match on money in v1.
- Enforced deals, model-run monsters, a generated map, unconstrained speech, a submission form, moderation beyond the character cap and the operator reading each brain.
- Any change to the referee's authority: models never mutate state, never roll dice, never score.

## 4. User Stories

**Player (writes a brain, watches with friends)**

1. As a player, I want a brain template with fixed sections, so that I know what to write and my character is comparable to the others.
2. As a player, I want a hard character cap, so that nobody wins by writing the longest prompt.
3. As a player, I want to pick one of four builds, so that my character has a mechanical shape as well as a voice.
4. As a player, I want to submit one text file to the operator, so that entering takes five minutes and no account.
5. As a player, I want my brain treated as data below the platform rules, so that no rival wins by writing "ignore your previous instructions".
6. As a player, I want the match to start clean with no memory of past matches, so that my character is judged on this adventure alone.
7. As a player, I want to see my character's private objective on screen while rivals cannot, so that I can watch my own plan play out.
8. As a player whose character has died, I want its objective revealed at that moment and no further calls made on its behalf, so that death means something and costs nothing after.

**Viewer (watches the stream)**

9. As a viewer, I want a round to play out over about a minute, so that I can follow eight names without reading a log.
10. As a viewer, I want each character's speech shown beside its private objective and reads, so that I can see the lie as it is told.
11. As a viewer, I want whispers shown as "X whispered to Y" with the text visible to me, so that I know a secret is moving even when the room does not.
12. As a viewer, I want every deal offered, accepted and broken shown as a receipt, so that betrayal is a fact on screen and not my inference.
13. As a viewer, I want public standings every round, so that I can watch the field turn on the leader.
14. As a viewer, I want a narrator's two or three sentences each round, so that there is never dead air.
15. As a viewer, I want side characters who talk back and have their own agendas, so that the world feels alive rather than furnished.
16. As a viewer, I want a failed model call to appear as the character panicking, distinct from a network failure in the log, so that the show never stalls and the record still tells the truth.

**Operator (the firm, runs the match)**

17. As the operator, I want one command that takes eight brain files and a seed and streams a match, so that running a pilot is not an evening of setup.
18. As the operator, I want the match generated one round ahead of what is on screen, so that model latency is invisible to the audience.
19. As the operator, I want the model called through my subscription by default and through an API key by switching one setting, so that the pilot is free and the fallback is real.
20. As the operator, I want a full-length unwatched dry run I can point at before the pilot, so that I know the five-hour window holds a match.
21. As the operator, I want the cost of every call recorded from the provider's own numbers, so that I know what a match costs without a cap deciding for me.
22. As the operator, I want the same model, settings and prompt version recorded in the match log, so that a match measures brains and not tiers.
23. As the operator, I want a balance simulator that runs hundreds of seeds on the mock in minutes, so that numbers are tuned without spending on the model.
24. As the operator, I want the gate as a harness whose output I read, not a test that goes green, so that the one question the product rests on is answered by people.

**Character (as served by the engine)**

25. As a character, I want the victory condition restated every turn, so that I cannot drift from why I am here by round thirty.
26. As a character, I want a referee-written digest of what happened to me, what I see, what I hold, my standing deals and who has broken one with me, so that facts are not something my note has to carry.
27. As a character, I want to hear last round's speech word for word, wrapped as dialogue from a rival, so that persuasion is possible and instruction is not.
28. As a character, I want to whisper to one other character, so that a deal can be private.
29. As a character, I want to offer and accept deals from a fixed vocabulary, so that a promise is recorded and its breaking is visible.
30. As a character, I want to rewrite a short private note each turn stating my objective and my reads, so that my interpretation survives a flat context.
31. As a character, I want the complete list of legal actions in my digest, so that I spend my output on strategy rather than guessing the interface.

**Talker (house-written side character)**

32. As a talker, I want the same output contract as a character and a restricted legal set, so that I can speak, whisper, deal, move and hand over items but never score, carry the Crown, or win.
33. As a talker, I want an agenda and facts of my own in my manifest, so that I hold something a character might trade for or be lied about.

## 5. Requirements

Priorities: [P0] must, [P1] should, [P2] nice.

### World and rules

1. [P0] Ruleset version `ember-vault-1.0`. Forty-eight rounds in four acts of twelve: I rounds 1–12, II 13–24, III 25–36, IV 37–48. `DEFAULT_MAX_ROUNDS`, the act boundaries and the contraction schedule are constants in the rules module, as in July, and are the only place those numbers live.
2. [P0] The Ember Vault world, hand-authored, grown to about sixteen locations in a registry the engine reads (rooms, adjacency, props, items, monsters, talker start positions, objective sites). The map never varies by seed. The seed places loot within its declared sites, rolls every die, and orders initiative.
3. [P0] About twelve live objectives at any round of acts I–III, each individually pursuable, at least three requiring two or three characters to act in the same location in the same round. Value is heterogeneous by build and by secret objective so that trade exists. Exact counts are tuned on the mock simulator (seam 6) to the metrics in §8.
4. [P0] One convergent terminal objective in act IV: the Crown, unlocked by the Warden's death, attuned over held rounds, extracted through the Egress. A legal extraction wins outright and freezes the match before later initiatives resolve. Contraction belongs to act IV only.
5. [P0] Scoring places everyone who did not extract; standings are public in every digest. July's scoring table survives with values re-tuned for forty-eight rounds; collateral still scores nothing; direct elimination pays once per victim.
6. [P0] Four builds as in July, player-chosen. Monsters stay deterministic (lowest-HP legal target, seeded tie-break) with a table of canned lines. Combat, Wild Swing, props, grid and reach survive from July unchanged unless simulation says otherwise.
7. [P0] Agent-versus-agent attacks illegal in act I, legal from act II. Death is permanent; a dead character's brain is never called again; its private objective is revealed to the audience at the moment of death.
8. [P1] Talkers can be attacked and killed in act II onward; a dead talker is a public event. Until this ships, talkers are not legal targets.

### Brains

9. [P0] A brain is fixed sections: `name`, `voice` (a paragraph), `wants` (what they want most), `treats` (how they treat strangers, allies, and those who betray them), `never` (the one thing they will never do), plus `build`. Total text across sections ≤ 2,000 characters, enforced at load with a human-readable refusal naming the section and the overage.
10. [P0] Brains arrive as one file per player in a private folder; the operator reads each before the match. No form, no accounts, no URLs, encoded binary, tool definitions or control characters.
11. [P0] Every brain section is wrapped and labelled untrusted in a user-role block below the platform rules and below the referee digest, exactly as July's `compile_prompt` does today. A brain never enters the system prompt.
12. [P0] A brain has a stable id across matches so it can be resubmitted; nothing about past matches is ever placed in a digest.

### The turn

13. [P0] All living characters and talkers commit blind in parallel from digests frozen against one committed event-log cutoff. Initiative (d20 + Speed, stable id) resolves collisions. Request order is never exposed to resolution.
14. [P0] Output contract per call, versioned `agent-action-1.0`, JSON only, `additionalProperties: false`:
    - `action` with `target`, `destination`, `item`, `tile` as today, plus `give` (item, to) for handing an item over;
    - `speech`: `{mode: "say"|"whisper"|"silent", to: id|null, text: ≤300 chars}`;
    - `deal`: `null` or `{kind: "offer", type: "truce"|"share_item"|"escort"|"split", to: id, terms: {...}}` or `{kind: "accept", offer_id: id}`;
    - `note`: `{objective: ≤120 chars, reads: [{who: id, stance: "trust"|"distrust"|"unknown", why: ≤60 chars}] ≤4 entries}`.
    - `reasoning_summary` and `memory_write` are removed.
15. [P0] Speech lags one round: what is said in round N is heard in round N+1. A `say` is heard by every body in the location; a `whisper` is heard only by `to`, and every other body in the location sees `{whispered: {from, to}}` without the text. The audience sees the text of every whisper.
16. [P0] Speech reaches a rival verbatim, JSON-encoded inside the digest, wrapped in a block labelled as dialogue from a rival and not instruction. The referee never parses prose.
17. [P0] A malformed output, a schema-valid illegal action, a refusal, a timeout or a provider error each resolves the turn to the defined default (`guard`) and completes the round. Malformed and illegal are `panic` events; timeout and provider error are `network` events. Both are visible to the audience as the character panicking; the log tells them apart.
18. [P0] Retry policy: one retry for a transport failure (timeout, rate limit, 5xx) only; never for a refusal, a malformed output or an illegal action. Per-call timeout 20 s; whole-round intent deadline 30 s.

### Deals

19. [P0] A deal is recorded, never enforced. An offer becomes an `offer_made` event with an id; an `accept` naming an open offer becomes `deal_struck`; an offer not accepted by the end of the next round lapses as `offer_lapsed`. Terms by type: `truce` (rounds: 1–6, no attack either way), `share_item` (item id, hand over by round R), `escort` (destination, arrive together by round R), `split` [P1] (objective id, who takes the reward).
20. [P0] A break is mechanical: an attack on a truce partner within the term, a share not delivered by R, an escort abandoned. Each is a public `deal_broken` event naming who broke what, in every digest and on the stream. Nothing is prevented.
21. [P0] The digest carries each character's standing deals and every public break involving anyone.

### Memory and the digest

22. [P0] The digest is written by code, facts only, fixed shape, flat size: identity and build; the victory condition restated; act, round, rounds remaining; standings for everyone with status; own state (hp, location, inventory with each item's effect, guard, passive effects); what is visible (bodies, items, exits, talkers, props with effects); last six mechanically relevant events to this character, projected from committed events as July's memory module does; standing deals and public breaks; speech heard last round; legal actions; the character's own previous note verbatim.
23. [P0] The note is the only model-written memory. It is capped, rewritten every turn, carried forward, and stored in the intent log so replay is exact. Notes are untrusted text: they cannot introduce facts, reveal private state or alter rules.
24. [P0] The audience sees each character's `note` the moment it is written. No character, and no talker, ever sees another's note, whisper not addressed to it, or brain.

### Talkers and narrator

25. [P0] Three house-written talkers: a guide who lies, a merchant who plays sides, an envoy from a rival faction. A talker manifest has `id`, `name`, `role`, `agenda`, `knows` (facts it holds, e.g. where a cache is), `holds` (items), `start`. Talkers run on the same model, contract and referee; their legal set is `say`, `whisper`, `offer`, `accept`, `move`, `give`, `guard`. They cannot score, carry the Crown, search, or win. Their brains are the firm's, not a player's.
26. [P0] Narrator: one call per round after state is committed, fed only canonical event sentences, returning two to four sentences; a validator rejects narration naming an unknown agent, item, room or outcome and substitutes a deterministic template. The narrator never controls the camera or the stream's timing.
27. [P1] Monster lines from a per-monster table keyed deterministically by round, as July's voice packs did for the mock.

### Model gateway and billing

28. [P0] Two provider adapters behind July's `DecisionProvider` protocol: `agent_sdk` (default) and `anthropic` (the Messages API). Same prompt compilation, same schema, same result record for both. The `mock` provider survives for the simulator and CI.
29. [P0] `agent_sdk`: `claude_agent_sdk.query()` with `tools=[]`, the platform rules as a replacement `system_prompt`, `output_format={"type": "json_schema", "schema": <agent-action-1.0, draft-07>}`, `model` pinned to Opus 5, `effort="low"`, `max_turns=1`. A `ResultMessage` with subtype `success` and a present `structured_output` is a turn; any other subtype, or `success` without `structured_output`, is a `panic`. Cost and tokens recorded from `total_cost_usd` and `usage_metadata`, labelled as the SDK's client-side estimate.
30. [P0] `anthropic`: `client.messages.parse()` with `output_format` bound to the same schema, `model="claude-opus-5"`, adaptive thinking, `output_config={"effort": "low"}`, `max_tokens` bounded (≈600), `stop_reason` checked before content (a `refusal` is a `panic`). Cost computed from `response.usage` at the published rates and recorded per call.
31. [P0] The match log records provider, requested and returned model, effort, prompt version, schema version, raw and parsed output, token counts, latency, retry count, fallback reason and request/response SHA-256 digests per call, as July's `ProviderResult` spec listed.
32. [P0] Same model and settings for every character and talker in a match, recorded once in the match header. A match mixing settings is refused at start.
33. [P0] No cost cap. Cost per call and per match is written to the log and shown on the operator console.
34. [P0] Concurrency: the intent pool is sized to living characters plus talkers (≤ 11). The SDK adapter's concurrency is measured by the dry run (§8) before the pilot, since it is undocumented.

### Live stream and viewer

35. [P0] The engine exposes rounds as they complete (a generator over `_run_round`, or a per-round callback) instead of only a blocking `run`. The presenter holds a one-round buffer: round N+1 is being generated while round N is on screen. Screen time per round is a dial, default 60 s.
36. [P0] The server gains a live endpoint (Server-Sent Events) that streams round beats to any open page, plus the July replay and audit endpoints unchanged. The seed and dice proofs are withheld while a match runs and published at completion, as July did.
37. [P0] The live page reuses July's story viewer and board: one beat at a time, auto-playing, camera grammar by event type, sprites and rooms. It adds, per character, a panel showing the current `note.objective` and `note.reads`, updated the round they are written; whisper receipts; deal receipts; standings; the narrator line. A dead character's panel shows its revealed objective and desaturates.
38. [P0] The page is private: a link, no auth in v1, bound to loopback or a private tunnel the operator chooses, screen-shareable into a Discord call. It must not be reachable from the public internet by default.
39. [P1] A "follow one character" toggle that pins the camera and the panel to one character.

### Determinism and versioning

40. [P0] Seeded and inside the boundary: every die, initiative order, loot placement within declared sites, monster tie-breaks, bystander selection. Outside the boundary: every model call (characters, talkers, narrator). A seed plus the stored intents and notes reproduces every state hash and event without a model, and replay is verified in CI against a golden fixture generated by the engine.
41. [P0] Every log carries `ruleset_version`, `schema_version` (`agent-action-1.0`), `prompt_version`, `memory_version` and a `log_format_version` from the first commit. A replayer refuses a log whose versions it does not know rather than guessing.
42. [P0] The audit chain (SHA-256 over every entry) and `verify_audit` survive unchanged.

### The gate

43. [P0] A harness, not a test: eight brains written to the template, three seeds, six rounds each, all eight on one build, same model and settings. It produces eight anonymised per-character transcripts (speech, whispers, deals, notes, actions) and the eight brains, shuffled, with an answer key sealed in a separate file.
44. [P0] Two readers who wrote none of the brains each match transcripts to brains. Pass is six of eight or better for both. Chance is one of eight per character.
45. [P0] The first run uses brains the firm and the session write to the template; the pilot uses the eight players' brains. Both runs are kept. Nothing in §5 items 1–8, 19–27 or 35–39 is built before the first run has been read.

## 6. Implementation Decisions

**Start from July, in place.** `code/arena/` as staged. Preserve without refactor: `HashRNG` (`SHA-256(seed:counter:label)`), the append-only `events` table, `audit_log`, `canonical_json`, `state_hash`, snapshot-per-phase, `visible_observation` as a pure function, `enumerate_legal_actions` and `is_legal` sharing one predicate, `memory.project_episodic_memory` over committed events, the `P0–P6` round order in `engine.py`'s docstring.

**Where the numbers live.** `rules.py` constants `DEFAULT_MAX_ROUNDS`, `ACT_I_LAST_ROUND`, `ACT_II_LAST_ROUND` (add `ACT_III_LAST_ROUND`), the contraction schedule and `ACT_NAMES` are the only statement of the match shape. Tests read them rather than repeating them. `RULESET_VERSION` becomes `ember-vault-1.0`; `SCORING_VERSION` follows.

**The world registry.** One file the engine reads for rooms, adjacency, props, items, monsters, talker starts and objective sites, extending July's `ROOM_PROPS` and item registry pattern (the observation builder and the resolver read the same registry, so no effect can apply undisclosed). Authored by hand; the seed places loot only within declared sites.

**Manifest and action models.** `AgentManifest` gains the brain sections (`voice`, `wants`, `treats`, `never`) replacing `system_prompt`/`personality`/`strategy`, keeps `build` and `secret_objective`, gains `kind: "character"|"talker"` with talker-only fields `agenda`, `knows`, `holds`, `start`. `AgentAction` gains `speech` (object), `deal`, `note`, `give`; loses `reasoning_summary`, `memory_write`. Both keep `additionalProperties: false`; both bump schema version. The JSON Schema in `schemas/` is generated from the models and pinned, so the two cannot drift.

**Deals.** A small `deals.py`: open offers with ids, acceptance, lapse at end of next round, and per-type break detection run in upkeep (P5) against committed events. Events: `offer_made`, `deal_struck`, `offer_lapsed`, `deal_broken`. All are memory-relevant in `memory.RELEVANT_EVENT_TYPES`.

**Speech routing.** `_build_recent_speech` becomes audience-aware: for a character, the `say` lines in its location and the whispers addressed to it, each wrapped `{"from": id, "mode": ..., "text": ...}` inside a block labelled as rival dialogue; plus `whispered` receipts without text. For the audience projection, everything with text.

**The digest.** `visible_observation` grows the sections in §5.22 and remains a pure function of frozen state plus the character id. The victory condition is a fixed string in the platform rules *and* a line in the digest.

**Prompt hierarchy.** Unchanged from July's `compile_prompt`: system = platform rules and output contract; user block 1 = the brain, wrapped and labelled untrusted; user block 2 = the digest, labelled data. Talkers use the same compiler with a talker rules variant.

**Adapters.** `providers.py` gains `AgentSDKProvider` and `AnthropicProvider` beside `MockDecisionProvider`; `provider_from_name` selects. Both implement `decide` and `narrate`. Both return a `ProviderResult` extended with the §5.31 fields. The SDK adapter treats `error_max_structured_output_retries` and a missing `structured_output` as malformed (`panic`), a raised connection error as `network`. The API adapter treats `stop_reason == "refusal"` as `panic` and SDK-typed connection/rate-limit errors as `network`, retrying once per §5.18 through the SDK's own retry disabled (`max_retries=0`) so the engine owns the policy.

**Live engine.** `ArenaEngine.run_rounds(manifests, seed)` yields `(round_no, beats)` after each round's P6 and `run()` becomes a thin loop over it, so every existing test and the CLI keep working. `server.py` adds `GET /api/matches/:id/live` as an SSE stream of beats and `POST /api/stream` to start a match from brain files with a seed. The presenter (a small module beside `demo/build_story.py`'s beat builder, which is reused for beat shapes) paces beats at the dial and keeps the one-round buffer.

**Viewer.** `demo/build_story.py`'s `build_beats` is the beat schema; it gains `note`, `whisper`, `deal` and `narration` beat kinds. The live page is the July story viewer template reading SSE instead of a baked JSON blob, with the per-character objective panel. Inline SVG sprites as July; no external assets.

**Talkers.** A talker is an `AgentManifest` with `kind="talker"`; the engine seats them after characters in stable id order, calls them in the same pool, and applies a talker legal set in `enumerate_legal_actions`. Scoring ignores them; the Crown code refuses them as carriers.

**Narrator.** `compile_narration_prompt` survives; a validator over the returned text against the round's event vocabulary substitutes a template on any unknown name. One call per round after `end_turn`.

**Cost ledger.** `decisions` rows gain `cost_usd`, `cost_source` (`provider_usage`|`sdk_estimate`), `input_tokens` (uncached), `output_tokens`, `cached_tokens` (read), `cache_creation_tokens` (written, billed at 1.25x); the SDK route records the model id the CLI billed, not the alias asked for. The operator console sums per round and per match.

**Brain files.** `brains/<id>.md` with the five headed sections; a loader that refuses with the section name and the overage; the folder is gitignored in the real repository and holds only house brains in this staging copy.

**The gate harness.** `tools/gate.py`: runs three seeds × six rounds with the chosen provider on one build, writes `gate/<run>/transcripts/<letter>.md` (anonymised), `gate/<run>/brains/<number>.md` (shuffled), `gate/<run>/KEY.json` (sealed), and a `README` with the two readers' answer sheet. `tools/score_gate.py` reads two answer sheets and the key and prints the denominator: `reader A 7 of 8, reader B 6 of 8: PASS`.

**Cited facts folded in.**
- Pricing at first-party API rates, cached 24 June 2026 in the bundled API reference: Opus 5 $5/$25 per million input/output tokens; Sonnet 5 $2/$10; Fable 5.1 $10/$50. Per-match estimate at 576 calls (8 characters + 3 talkers + narrator × 48), ~2,000 input and 300–1,500 output tokens per call: Opus 5 roughly $4–$12; a 500-seed balance run on the model would be $2,000+, which is why balance runs on the mock.
- A Max subscription does not include the Claude API or Console; Agent SDK usage and `claude -p` draw from the subscription's limits, and the announced separate monthly credit was paused on 15 June 2026 ([support article](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), [support article](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-do-i-have-to-pay-separately-to-use-the-claude-api-and-console)). Third-party developers may not offer claude.ai login to their own users ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)); the operator running their own script under their own plan is not that. *The support pages could not be opened from the session (proxy-blocked); this rests on three consistent summaries and should be re-read once from a browser.*
- Agent SDK options and result fields: `ClaudeAgentOptions(tools=[], system_prompt=str, output_format={"type":"json_schema","schema":...}, model=..., effort=..., max_turns=1)`; `ResultMessage.structured_output`, `.subtype`, `.total_cost_usd`, `.usage_metadata`; schemas validated as draft-07; `error_max_structured_output_retries` on failure ([Python reference](https://code.claude.com/docs/en/agent-sdk/python), [structured outputs](https://code.claude.com/docs/en/agent-sdk/structured-outputs)).
- Messages API: `client.messages.parse(..., output_format=<Pydantic model>)` returns `parsed_output`; adaptive thinking; `output_config.effort`; no assistant prefill; check `stop_reason` for `refusal` (bundled API reference, Python).

## 7. Testing Decisions

Six seams, confirmed by the firm on 11 September 2026. Four are July's and already exercised by 62 tests; the last two are new.

- **Seam 1 — full match.** `ArenaEngine.run(manifests, seed)` with the mock provider → `ArenaStore.replay_bundle(match_id)`. Every new rule lands here: four acts, deals and breaks, whisper routing, talker legal set, note round-trip, scoring at forty-eight rounds, dead-character silence.
- **Seam 2 — determinism.** `rerun_state_hashes` extended: same seed and stored intents (characters *and* talkers) reproduce identical snapshot hashes; the narrator is proven outside the boundary by changing its output and asserting no hash moves.
- **Seam 3 — visibility.** `rules.visible_observation` is pure, so it is snapshot-tested per audience without a match: no `note`, no brain, no whisper not addressed to it, in any character's or talker's digest, asserted over the whole observation object; the audience projection contains all of them.
- **Seam 4 — gateway.** A stubbed provider (and a stubbed SDK `query`) driving timeout, rate limit, 5xx, malformed body, schema-valid illegal action, refusal, and `success` without `structured_output`, each asserting the round completes with `guard` and the right event type (`panic` vs `network`), retry count as policy says, and a cost row written.
- **Seam 5 — the front door.** One test starts `server.py`, posts brain files and a seed to `/api/stream`, reads `/api/matches/:id/live` as the page would, and asserts beats arrive in round order with the objective panel data present, the seed absent until completion, and round N+1's generation started before round N's beats finished playing. Built per the record's tenet S32: it enters through the door a person uses and nowhere else.
- **Seam 6 — harnesses.** `tools/simulate.py` (mock, hundreds of seeds, minutes) reports the §8 balance metrics with denominators; `tools/gate.py` and `tools/score_gate.py` produce the transcripts and the blind-match score. Neither is a CI test; CI holds the golden replay fixture and the property tests. *(Tenet S22: CI holds what must never regress; a harness produces what must be looked at.)*

**What a good test proves.** A match completes, replays from its seed, and its audit validates. No private field crosses to the wrong audience, asserted on whole objects. Every gateway failure still finishes the round and is labelled truthfully. Every effect the engine applies is disclosed in the digest (property over the registry). A deal can be broken and the break is an event. The live door works without a person clicking. The gate's score can be low.

**Mutation check, before any of these count.** Delete the wiring once — the pool, the SSE write, the break detector — and watch the suite go red. A test that stays green with the join cut is a mirror.

*No client PII, tax or financial data is involved. The sensitive-data rule here is credentials: no API key, subscription token or `Authorization` header may appear in a replay bundle, an audit export, the live feed, a log line, a brain file or source control, and a test proves it over an export.*

## 8. Success Metrics

- Gate: both blind readers ≥ 6 of 8 on the first house-brain run, and again on the players' brains before the pilot.
- Dry run on the subscription: a full 48-round, 11-brain match completes with < 5% of calls resolved by default, no round exceeding the 30 s intent deadline, and the five-hour window not exhausted. Reported as `N of 576 calls answered`.
- Balance on the mock over 500 seeds: ≥ 95% complete; median ≥ 1 elimination and ≤ 5; ≥ 70% reach act IV with a living Warden fight; median ≥ 1 Crown transfer; no build's win rate outside 25% ± 10 pp; no seat outside the same band; agent miss rate 35–45%.
- Every round of acts I–III, each living character has ≥ 1 legal objective-advancing action available and ≥ 2 characters share a nearest objective (computed by the simulator).
- Stream: at the 60 s dial a 48-round match plays in 48 ± 10 minutes; the buffer never empties (measured: rounds where beats waited on generation = 0).
- Log: golden replay verifies in CI with no model call; `verify_audit` valid on every dry-run and pilot match.

## 9. Milestones / Rollout

- **M0 — Staged and frozen.** This folder; July's 62 tests green here; `LOG.md` started; repository created by the firm and this folder moved there.
- **M1 — Gateway and brains.** The two adapters and the stub (seam 4); brain template and loader; the cost ledger; a one-brain smoke call on the subscription. *No game content.*
- **M2 — The gate.** `tools/gate.py` on July's twelve-round rules with the new output contract; house brains written to the template; three seeds run; two readers score it. **Gate. Nothing below starts until this has been read.**
- **M3 — The adventure.** Four acts, the world registry to sixteen locations and twelve objectives, deals, whispers, notes, talkers, narrator, scoring, all on the mock (seams 1–3); simulator tuned to §8.
- **M4 — Live.** Generator engine, SSE server, presenter with the buffer, the page with the objective panel (seam 5).
- **M5 — Dry run and pilot.** One unwatched full-length match on the subscription; the players' brains; the gate re-scored on them; the Discord pilot.

## 10. Risks & Open Questions

**Risks**

- *The five-hour window empties mid-match.* Mitigation: the dry run before anyone watches; the API-key adapter is one setting away; the default action keeps the stream alive either way.
- *Agent SDK concurrency is undocumented.* Mitigation: the pool size is a setting; the dry run measures it; the API adapter has no such limit.
- *Injection through speech or a brain.* Mitigation: wrapping, labelling, schema-only output, the referee reading no prose; a `panic` on any contract violation. Accepted residual: a persuasive brain is the game.
- *Forty-eight rounds thin the note.* Mitigation: facts moved to code (deals, breaks, episodic memory); note size is a dial.
- *Balance at forty-eight rounds is unknown.* Mitigation: the simulator on the mock is cheap; act boundaries and the schedule are constants.
- *An hour is long for a viewer.* Mitigation: the dial; the follow-one toggle [P1]; the narrator.
- *The support-page finding was read through summaries.* **Settled empirically on 11 September 2026, 20:14Z:** the forge ran eight contestant calls through the Agent SDK with no API key set anywhere and every one answered (`runs/20260911T201514Z-agent-sdk.md`). The subscription route works. What is still unknown is the five-hour window's capacity over a full match, which the dry run measures.

**Open questions (needs your decision — only things owed to the firm)**

- Create the private repository `ember-vault-arena` by hand and say when; the session cannot (403, twice).
- Who the eight players are and by when their brain files arrive.
- Who the two blind readers are for each gate run.
- Approve `tools/gate.py` in the forge's Claude Code session, or run it there in a plain terminal: the session's auto-mode classifier refused it as "Create Unsafe Agents" on 11 September 2026 while allowing the same adapter through `run.py demo`.

## 11. Done Criteria

- [ ] Requirements 1–45 met at their priorities; user stories 1–33 walkable.
- [ ] Tests green at seams 1–5; July's 62 still passing; the mutation check done once per seam and recorded in `LOG.md`.
- [ ] Golden replay fixture verifies in CI with no model call; `verify_audit` valid.
- [ ] Gate run twice (house brains, players' brains), both scored ≥ 6 of 8 by two readers, artifacts kept.
- [ ] Dry run: one unwatched 48-round match on the subscription, `N of 576 answered` reported, buffer never empty.
- [ ] Pilot: one match streamed to a private page into a Discord call, watched end to end by the firm, with the objective panel, whisper and deal receipts, and the narrator visible on screen — verified by watching, not by tests.
- [ ] No credential in any export, feed, log or file, proven by a test.
- [ ] README documents brain template, run, dry run, gate, replay, verify, and the two provider settings.
- [ ] `LOG.md` carries the decisions and the `[LOG]` items; canon carries the rulings.
