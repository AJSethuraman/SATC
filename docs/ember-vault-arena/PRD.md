# PRD: Ember Vault Arena — v0.2 Playable Build

**Status:** Draft · **Owner:** AJSethuraman · **Last updated:** 2026-07-25

**Authority:** `docs/CLAUDE_BUILD_SPEC.md` is the sole product authority. `docs/PRD.md`,
`docs/PRODUCT_V2.md`, and `docs/IMPLEMENTATION_PLAN.md` are **historical** — where they
conflict, the build spec wins. This PRD records the four places we deliberately
override the build spec itself (§10, below).

---

## 1. Problem

Eight people submit "brains" for fantasy contestants and watch them compete. The
entertainment comes from AI behaviour — bargaining, grudges, panic, betrayal — while
fairness has to come from ordinary deterministic code. The v0.1 prototype proves the
skeleton works, but it is not yet the product:

- **Agents play half-blind.** Items arrive as bare ID strings (`"healing_tonic"`). The
  engine knows a Veteran Blade grants +1 Power and applies it silently during attacks;
  the model is never told. A real model must *infer undocumented mechanics from item
  names*, so model quality partly measures rule-guessing rather than strategy. The mock
  provider only looks competent because the rules are hardcoded into it.
- **Agents forget.** The build spec's §12 defines three memory layers. Layer 2 —
  deterministic engine episodic memory — **does not exist**. An agent's entire recall is
  three self-authored 160-character notes, so it cannot remember who struck it, who
  opened which seal, or who it watched die unless it wrote that down itself.
- **The match has no third act.** The map is a hub-and-spoke with two levers and no
  attunement: take the Crown, walk to the exit, win. There is no route split, no
  convergence, no chase, and no reason for a leader not to hide.
- **Combat has no texture.** Every attack automatically hits. There are no misses, so
  there are no accidents, and nothing surprising happens between decisions.
- **A submitted prompt sits inside the platform system message**, which the build spec's
  own §6 and §10 forbid.

## 2. Solution

Take the working v0.1 referee and make it the game the spec describes: a twelve-round,
three-act, eight-agent dungeon with two routes, two seals, a Crown that must be attuned
before it can be carried out, and a map that closes in on the survivors. Give agents an
observation they can actually plan against — self-describing items, real public state,
enumerated legal actions, and a deterministic memory of what happened to them. Make
combat miss, and make every miss *do something*: hurt you, hurt a bystander, or hurt the
room. Then wire a pinned local model behind a provider-neutral gateway so the whole thing
runs unattended on one desktop GPU, with every prompt, roll, and referee decision
auditable and replayable without a model call.

## 3. Goals & Non-Goals

**Goals**

- A full eight-agent match runs start to finish with no human intervention.
- Nothing an agent needs to play well is hidden from it: item effects, public state, map,
  legal actions, and its own history.
- Every miss produces a visible consequence; ~40% of attacks generate a mishap.
- Act III is reached in most matches, and the Crown changes hands often enough to create a
  chase.
- Provider failure never strands a match — deterministic fallback on every path.
- Mock mode stays free, deterministic, and offline.
- Stored intents plus the seed reproduce the final state and event hashes exactly.

**Non-Goals / Out of scope**

- **Cross-match memory of any kind** — no carryover of state, relationships, or reputation
  between matches. Each match starts clean. (Confirmed override candidate rejected; §3 and
  §23 of the build spec stand.)
- Vector databases, embeddings, or semantic memory retrieval.
- An agent framework, Kubernetes, Kafka, or a general-purpose RPG rules package.
- LLM adjudication of any kind. Models never mutate state.
- User-authored spells, items, maps, or executable tools.
- Open-world exploration; a D&D implementation; a second dungeon.
- Real-money prizes, wagering, tradable items, or an economy.
- Hosted alpha, accounts, PostgreSQL, ranked seasons, TTS, and video rendering — build-spec
  Phases 4–7, explicitly deferred (see §9).
- Porting the referee to TypeScript (`IMPLEMENTATION_PLAN.md` Phase 1) — superseded.
- Bit-for-bit reproducibility of *fresh model inference*. Only stored-intents-plus-seed
  replay is guaranteed.

## 4. User Stories

**Contestant (the agent, as served by the engine)**

1. As an agent, I want each item I hold to state its own effect, so that I can decide
   whether to drink the tonic without guessing what a "tonic" does.
2. As an agent, I want an enumerated list of my legal actions, so that I spend my output
   on strategy rather than on interface compliance.
3. As an agent, I want a deterministic record of the last six things that mattered to me,
   so that I remember who hurt me and who kept their word.
4. As an agent, I want the public state — seals, Warden, Crown carrier, attunement — so
   that I can tell whether the Vault is open and who is about to win.
5. As an agent, I want the room graph and my visited rooms, so that I can plan a route
   instead of wandering.
6. As an agent, I want to know which rooms are about to seal, so that I am not trapped by
   a rule I could not see coming.
7. As an agent, I want my own score breakdown, so that I understand how I am being judged.
8. As an eliminated agent, I want no further model calls made on my behalf, so that my
   budget is not spent after I am dead.

**Builder**

9. As a builder, I want to submit an agent as one small JSON document, so that entering is
   trivial.
10. As a builder, I want the winning agent's prompt revealed after the match, so that I can
    learn what beat me.
11. As a builder, I want to edit my agent and immediately rerun the same seed, so that I can
    test whether my change actually helped.
12. As a builder, I want my prompt treated as untrusted data and never as a platform
    instruction, so that no entrant can win by jailbreaking the referee.

**Spectator**

13. As a spectator, I want to watch a completed match with no model calls, so that replay is
    instant, free, and works offline.
14. As a spectator, I want to see the exact roll behind every attack, so that I can trust the
    outcome.
15. As a spectator, I want misses to be entertaining, so that combat is fun to watch rather
    than a damage spreadsheet.
16. As a spectator, I want a visible two-round attunement meter, so that I know how close the
    carrier is to escaping.
17. As a spectator, I want secrets to stay hidden until their reveal trigger, so that the
    match is not spoiled.

**Operator**

18. As the operator, I want one eight-agent match to complete unattended on an RTX 2080, so
    that I can run the format on hardware I own.
19. As the operator, I want every prompt, response, roll, and referee decision recorded in a
    tamper-evident chain, so that any disputed outcome can be audited.
20. As the operator, I want a provider failure to degrade to deterministic autopilot, so that
    a match never hangs.
21. As the operator, I want a seeded balance simulator, so that I can prove no build or seat
    dominates before locking numbers.

## 5. Requirements

### Observation & memory *(the "agents can see and remember" work)*

1. **[P0]** Items are self-describing everywhere they appear — inventory, floor items, and
   other agents' visible inventories: `{id, name, effect, consumed_on_use}`. No bare ID
   strings reach a model.
2. **[P0]** Any passive item effect the engine applies (e.g. Veteran Blade's +1 Power) is
   stated in the observation. An effect the engine applies but does not disclose is a bug.
3. **[P0]** Implement build-spec §12 layer 2: a deterministic per-agent episodic memory of
   the **last six** mechanically relevant events, selected by the published priority order
   (damage dealt/received; speech directed at the agent; ally/rival actions involving it;
   seal and Crown state changes; item acquisition/use; objective progress; observed
   eliminations). Selection is pure code — no model involvement — and is replayable.
4. **[P0]** Memory persists for the whole match and is never rewound. It does **not** carry
   across matches.
5. **[P0]** The observation carries a real public state block: `act`, `rounds_remaining`,
   `seals`, `warden_alive`, and `crown {status, carrier_id, attunement_rounds}`.
6. **[P0]** The observation carries the room graph, the agent's `visited` rooms, and each
   room's `contracting` flag.
7. **[P0]** `legal_actions` is present and authoritative. A schema-valid action outside it is
   illegal and falls back to `guard` with the −2 penalty.
8. **[P1]** The observation carries the agent's own `score_breakdown`.
9. **[P0]** Scratch memory stays capped at three normalised 160-character strings. Memory
   writes are untrusted text: they cannot introduce facts, reveal private state, or alter
   rules. Every before/after memory state is audited.

### Ruleset (three acts)

10. **[P0]** Two routes (Ironwood, Ossuary), each with one guardian, one loot cache, and one
    seal. Both seals must be active before the Vault opens.
11. **[P0]** Twelve rounds, three acts: I = 1–4, II = 5–7, III = 8–12.
12. **[P0]** Agent-vs-agent attacks are illegal in Act I and legal from Act II onward.
13. **[P0]** The Crown is unavailable until the Warden falls. `take` sets attunement to 0;
    each completed held round adds 1; any transfer resets it to 0; the Egress is legal only
    after two completed attunement rounds. A legal escape freezes the win before later
    initiatives resolve.
14. **[P0]** Map contraction: outer rooms seal on a published schedule at the ends of rounds
    9, 10, and 11, in a fixed documented order. A room is flagged `contracting` for one full
    round before it seals. Sealed rooms are removed from `legal_actions`.
15. **[P0]** Combat: to-hit is `d20 + Power` against `10 + Armor + guard`. A hit deals
    `d6 + Power − Armor`, minimum 1.
16. **[P0]** **Wild Swing** — every miss rolls a d6 and does exactly one thing:
    - **1–2 — you wear it:** drop one carried item to the floor; if empty-handed, take 1.
    - **3–4 — a bystander wears it:** one other body in the room (agent *or* monster) takes
      a flat **2**; with no bystander present, resolve as *the room wears it*.
    - **5–6 — the room wears it:** the room's feature reacts, resolved deterministically and
      differently per room.
    Bystander selection is seeded over a stable-sorted candidate list — never "nearest".
17. **[P0]** Collateral damage may eliminate, but scores nothing: it is tracked as
    `collateral_damage`, awards no elimination points (§8 says *directly* eliminate), and is
    marked as an accident in the replay.
18. **[P0]** Scoring is rescaled to build-spec §8 exactly: seal +5; monster damage +1 per hit
    **capped per round**; guardian finishing blow +3; Warden finishing blow +5; first to
    find a cache +2; take Crown +4; each attunement round +2; secret objective +6; survive
    Act II +2; illegal action or malformed output −2; direct elimination +2 with no repeat
    farming; extraction = first place plus +10 for display.
19. **[P0]** Placement: escaped winner first; then all agents by score; ties broken by later
    survival, then Crown hold time, then monster damage, then fewer invalid actions, then
    seeded deterministic tie-break.
20. **[P0]** Monster tactics become **deterministic code** — attack the lowest-HP legal
    target, ties broken by seeded RNG over stable IDs. The `choose_npc_actions` model call is
    removed entirely.
21. **[P1]** Engine-derived dramatic event tags for downstream highlight selection.
22. **[P1]** The engine continues to accept 4–8 agents; ranked play requires exactly 8.

### Model gateway

23. **[P0]** The submitted agent configuration moves **out** of the platform system message
    into a lower-priority user data block. Platform rules alone occupy the system
    instruction.
24. **[P0]** Provider-neutral gateway with `mock`, `compatible`, and `ollama` adapters,
    selected by `--provider`. Mock stays the default and requires no network.
25. **[P0]** `ModelResult` carries provider, requested and returned model, local model digest,
    quantization, server version, provider request ID, raw and parsed output, token counts,
    latency, finish reason, refusal data, retry count, schema validity, error and fallback
    reason, and request/response SHA-256 digests.
26. **[P0]** Strict JSON Schema output for actions. Output containing any text outside the
    JSON object is rejected.
27. **[P0]** Intents are collected **sequentially** in stable seat order from observations
    frozen before the first request. Request order is never exposed to agents or to
    resolution.
28. **[P0]** 60s per-call timeout; 480s whole-round deadline; at most one retry, and only for
    a local transport failure. No retry on refusal, schema-valid illegal action, or budget
    exhaustion.
29. **[P0]** Every failure path — timeout, refusal, malformed output, missing model, HTTP 500,
    exhausted budget — resolves to deterministic `guard` and completes the round.
30. **[P0]** Per-agent token ledger charged from *actual* provider usage where available.
    Budget that cannot cover the next request ceiling switches that agent to autopilot.
31. **[P0]** No prompt is ever sent to an external endpoint when
    `ARENA_EXTERNAL_FALLBACK_ENABLED=false` (the default).
32. **[P0]** Ranked configuration rejects an unpinned model digest.
33. **[P1]** Preflight (Ollama health, model presence, digest, quantization, context, GPU
    residency) and a benchmark command reporting tokens/sec, GPU-seconds, peak VRAM, and
    whether the model is fully GPU-resident.

### Audit, replay & safety

34. **[P0]** The append-only event log, SHA-256 audit chain, snapshots, and seeded `HashRNG`
    are preserved. Wild Swing, to-hit, and collateral rolls each get their own RNG label.
35. **[P0]** Replay requires no model call and works offline from one exported bundle.
36. **[P0]** No private state — another agent's prompt, objective, or memory — ever appears in
    an agent's observation or in the pre-reveal public replay projection.
37. **[P0]** A golden replay fixture's state and event hashes are verified in CI with no model
    call.
38. **[P1]** Feature flags for `three_act_v2`, `dossier_v1`, and `ollama_provider`.

## 6. Implementation Decisions

**Preserve.** `HashRNG` (seed:counter:label → SHA-256), the append-only `events` table, the
`audit_log` hash chain, `canonical_json`, `state_hash`, snapshot-per-phase, and the
deterministic mock provider. These are the load-bearing invariants; they are not to be
refactored.

**Observation shape.** Target the build spec's §7 schema, extended with the clarity fields
this PRD adds. `rules.visible_observation()` stays a **pure function of frozen state** —
that purity is what makes visibility snapshot-testable, so it must not acquire I/O.

```json
"you": { "inventory": [
  {"id": "healing_tonic", "name": "Healing Tonic",
   "effect": "Restore 5 HP", "consumed_on_use": true}
]},
"passive_effects": ["veteran_blade: +1 Power on attacks"],
"episodic_memory": ["r3 Nix hit you for 4", "r4 you opened the Ironwood seal"],
"public_state": {"seals": {...}, "warden_alive": true,
                 "crown": {"status": "locked", "carrier_id": null, "attunement_rounds": 0}},
"map": {"rooms": [...], "sealed": [], "contracting": ["ironwood_gate"]},
"legal_actions": [...]
```

**Wild Swing** is a typed table in the rules module, not branching inside `_attack`, so its
faces can be reweighted from simulation without touching combat resolution. It rolls on its
own RNG label and emits its own event.

**Item registry.** One source of truth for item id, name, human-readable effect, and
mechanical hook. The observation builder and the resolver read the same registry — that is
what structurally prevents the "engine applies an effect it never disclosed" class of bug.

**Episodic memory** is a deterministic projection over the agent's own event history,
computed at observation time from committed events. It is not a second mutable store.

**Prompt hierarchy.** System message = platform rules only. User message 1 = submitted
agent configuration, explicitly labelled untrusted. User message 2 = canonical observation,
explicitly labelled data.

**Migration.** Additive where possible. `AgentManifest` and `AgentAction` both reject unknown
fields today, so `cosmetics` and `invoked_fact_id` require explicit allowlist changes plus
schema-version bumps. `RULESET_VERSION` moves to `ember-vault-0.2`; v0.1 replays remain
readable.

## 7. Testing Decisions

- **Seam 1 — full match (primary).** `ArenaEngine.run(manifests, seed)` →
  `ArenaStore.replay_bundle(match_id)`, asserting on events, snapshots, and scores. This is
  the existing seam all eight current tests already use; new rules land here.
- **Seam 2 — determinism.** `rerun_state_hashes(manifests, seed, path)` already exists and
  compares snapshot hash sequences across runs. Extend, don't replace.
- **Seam 3 — audit.** `ArenaStore.verify_audit(match_id)`, including the existing tamper
  test.
- **Seam 4 — visibility (new, and the important one).** `rules.visible_observation()` is a
  pure function, so it can be snapshot-tested per audience without running a match. Every
  secret-leak requirement is proven here.
- **Seam 5 — simulator (new).** A headless N-seed runner for balance. Measured: **~1.7s per
  mock match**, so 500 seeds ≈ 14 minutes — a nightly/on-demand job, **not** a per-commit CI
  gate. The per-commit gate is the golden replay fixture.
- **Seam 6 — gateway.** A stubbed local HTTP endpoint exercising missing model, HTTP 500,
  timeout, malformed body, invalid schema, and illegal target — each asserting the round
  completes with the right fallback.

**What a good test proves:**

- A match completes, is reproducible from its seed, and its audit chain validates.
- No observation for agent A contains any private field belonging to agent B — asserted on
  the whole observation object, not spot-checked fields.
- Every failure mode of the gateway still finishes the round.
- Every effect the engine applies is disclosed in the observation (property test over the
  item registry: no mechanical hook without a stated effect).
- Wild Swing outcomes are deterministic for a given seed and each face's state change is
  correct.
- The Crown cannot leave the Vault without two completed attunement rounds — proven by
  attempting the escape at attunement 0 and 1.

*No client PII, tax data, or financial data is involved in this project.* The equivalent
sensitive-data rule here: **no provider credential may appear in browser code, a replay
bundle, an exported audit, a log line, or source control.** Test that a replay bundle and an
audit export contain no `Authorization` header, no API key, and no environment secret.

## 8. Success Metrics

- 8/8 existing tests keep passing; the new suite passes; golden replay verifies in CI.
- ≥95% of 500 seeded mock matches complete unattended.
- ≥70% of matches reach Act III.
- ≥1 Crown transfer in the median match.
- Mishap rate 35–45% of attacks (Wild Swing firing as designed).
- No build's win rate outside 25%±10pp across 500 seeds; no seat advantage outside the same
  band.
- Invalid-action rate under 5% with the pinned local model.
- One eight-agent local-model match completes unattended on an RTX 2080, with
  `run.py verify MATCH_ID` passing and the replay viewable after Ollama is shut down.

## 9. Milestones / Rollout

Deliberately resequenced from build-spec §18 — see §10.

- **M1 — Freeze & fix.** Golden replay fixture verified in CI; feature flags; prompt
  hierarchy fix (req. 23); deterministic monster tactics (req. 20); sequential collection
  (req. 27). *Ships a spec-compliant, greener baseline with no new game content.*
- **M2 — Observation & memory.** Reqs 1–9. *Agents can see and remember. Independently
  valuable even before the ruleset changes.*
- **M3 — Three acts.** Reqs 10–22, plus the simulator (Seam 5) used to tune Wild Swing face
  weights and seal rounds.
- **M4 — Local model gateway.** Reqs 23–33.
- **M5 — Campaign dossier.** Build-spec Phase 1 in full, landing on the schema M2/M3 created.

**Deferred (roadmap, not this build):** spectator polish, hosted alpha (FastAPI/PostgreSQL/
accounts), ranked creator season, hosted narration and the content/video engine — build-spec
Phases 4–7.

## 10. Risks & Open Questions

**Deliberate overrides of the build spec** (each a considered decision, not an oversight):

1. **Phase order.** The spec orders the dossier first; we build it last. Its own §7
   observation schema already assumes acts, seals, and attunement, so a dossier built first
   would have its visibility and reveal layers rewritten by Phase 3.
2. **Combat.** §8 asks for a d20 to-hit *and* says keep the existing formula; there is no
   existing to-hit roll. We add the d20 roll and the Wild Swing table, which appears nowhere
   in the spec.
3. **Observation clarity.** Self-describing items, passive-effect disclosure, room graph,
   and score breakdown go beyond §7.
4. **Contraction.** §4 requires it but never defines it; the scheduled-sealing rule is ours.

**Risks**

- **Balance.** Wild Swing adds damage the old model never produced, so matches may become
  deadlier or shorter. *Mitigation:* face weights and seal rounds are simulator-tunable; the
  hit math is not.
- **Fitting 6.6 GB on 8 GB VRAM.** `qwen3.5:9b` Q4_K_M at 4,096 context is tight.
  *Mitigation:* `qwen3.5:4b` (3.4 GB) is the documented fallback; preflight reports GPU
  residency rather than letting it silently spill to system RAM.
- **Match latency.** Sequential inference across 8 agents × 12 rounds is slow. Accepted:
  the target is quality, then smooth playback — not live speed.
- **Observation size.** The clarity fields push input tokens up against the 800–1,200 target
  and the 4,096 context cap. *Mitigation:* measure in M2; item effects are short static
  strings and the episodic log is capped at six entries.
- **Simulator runtime.** 500 seeds ≈ 14 minutes; 10,000-seed property tests must run against
  the dossier generator only, never full matches.

**Open questions (need your decision)**

- **Repo creation is blocked.** The GitHub App cannot create repositories
  (`403 Resource not accessible by integration`). An empty private `ember-vault-arena` must
  be created by hand before any of this can be pushed.
- Final Wild Swing face weights and seal-schedule rounds — proposed above, to be ratified
  against simulator output in M3.

## 11. Done Criteria

- [ ] Requirements and user stories met.
- [ ] Tests pass at all six named seams; the original 8 tests still pass.
- [ ] Golden replay fixture verifies in CI with no model call.
- [ ] 500 seeded mock matches meet the §8 metrics.
- [ ] One eight-agent match completes unattended against the pinned local model on the RTX
      2080; `run.py verify MATCH_ID` passes; the replay is viewable with Ollama stopped.
- [ ] No observation, replay bundle, or audit export leaks another agent's private state or
      any credential.
- [ ] README documents Ollama setup, model pull, local-model run, mock run, test, verify,
      replay export, and the security model.
- [ ] Verified by watching a real match replay end to end, not only by tests.
