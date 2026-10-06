# Product Requirements — Ember Vault Arena

## Product thesis

People will care about agent competitions when they can understand the stakes,
recognize each contestant's personality, argue about its decisions, and trust
that the result was not improvised by a narrator. The product is therefore a
spectator game with a prompt laboratory inside it—not a virtual tabletop and
not an open-ended role-playing simulator.

The narrowest entertaining MVP is a repeatable 10–16 round dungeon called **The
Ember Vault**:

- four to eight prompt-defined agents, with eight as the featured format;
- one small branching map and one Crown;
- four fixed character builds;
- eight legal action types;
- four engine-scored hidden objectives;
- simultaneous decisions followed by deterministic resolution;
- permanent death, dropped inventory, betrayal, and one winner;
- persistent agent profiles, match history, and rankings across runs;
- prompt reveal after elimination or match completion.

“Persistent campaign” in v0 means the agents, ratings, replays, and season
story persist. Dungeon state does not carry between matches. Open-world state,
character leveling, user-authored spells, and human intervention during a run
are explicit non-goals.

## Target users

1. **Prompt builders** want to prove their agent is clever, funny, or ruthless.
2. **Spectators** want a short match with clear stakes and surprising turns.
3. **Creators** want replay assets they can turn into clips without editing a
   raw transcript.

## Core promise and success criteria

The user can paste an agent manifest, select four contestants, press Run, walk
away, and return to a completed, scored, verified replay.

MVP acceptance criteria:

- 95% of model-provider matches finish without human action.
- A match lasts 8–15 minutes live and 3–6 minutes as an edited replay.
- The same seed plus captured agent outputs reproduces the same state hashes.
- A zero-cost local run completes in under five seconds.
- Invalid outputs never corrupt match state.
- Spectators can identify the winner, pivotal betrayal, and objective reveal
  without reading raw logs.
- Median live cost stays below a configurable ceiling; default design budget is
  64 agent calls plus 32 small GM calls at the absolute 16-round maximum.

## Submission contract

Each agent provides:

| Field | Purpose | Bound |
| --- | --- | --- |
| `id` | Stable roster identifier | 3–40 safe characters |
| `name` | Spectator-facing name | 2–40 characters |
| `system_prompt` | Behavioral identity | 10–2,000 characters |
| `personality` | Voice and temperament | 3–500 characters |
| `strategy` | Tactical preferences | 3–1,000 characters |
| `build` | Engine-balanced stats | one of four enums |
| `secret_objective` | Private scoring incentive | one engine-defined enum |

The objective is selected, not freeform. Freeform objectives are entertaining
but not objectively scoreable and invite reward hacking. A later “creator
mode” can permit unranked custom objectives reviewed by an objective judge.

## Hands-off match loop

1. Load the immutable rules version, seed, four to eight manifests, and token budgets.
2. Freeze a canonical start-of-round snapshot.
3. Derive a private observation for each living agent.
4. Call all living agents concurrently. No agent sees another's current intent.
5. Validate syntax and action legality against the frozen observation.
6. Roll initiative using the version-stable hash RNG.
7. Resolve actions in initiative order. A now-impossible but formerly legal
   action becomes a no-effect stale action; it is not penalized.
8. Ask the AI GM for one legal intent per active monster. The referee validates
   and resolves those intents.
9. Give only canonical events to the AI GM for narration.
10. Persist end state, scores, narration, and audit hashes.
11. Continue until the Crown escapes, all agents die, or the round cap is hit.
12. Reveal objectives/prompts, assign placement, update ratings, and enqueue
    content rendering.

Automatic fallbacks cover provider timeouts, malformed output, exhausted
budgets, invalid NPC intents, and narration failure. A match never pauses to ask
a human what to do.

## Product requirements

### Agent competition

- The platform must strictly validate manifests and outputs.
- All agent decisions in a round must use the same starting state.
- Each agent gets equal input/output ceilings and the same model class in ranked
  play.
- A per-agent private memory contains at most three 160-character notes.
- Public character speech is capped at 120 characters and is mechanically inert.
- PvP is disabled before round four to reduce spawn griefing.

### Deterministic referee

- The referee exclusively owns state mutation.
- Every roll must be labeled and reproducible from seed plus counter.
- All rules must be versioned.
- A referee event must identify the submitted intent, legality result, effect,
  score change, and resulting state hash where applicable.
- Narration cannot call mutation functions.

### Spectator experience

- Show all four health, score, room, inventory status, and elimination state.
- Animate movement across a compact map.
- Provide autoplay, round stepping, and a scrubber.
- Separate cinematic narration from the canonical event feed.
- Reveal prompts and hidden objectives only when permitted.
- Display audit validity without making the user inspect hashes.

### Administration

- Save or replace a roster entry from a validated JSON manifest.
- Start a match from four IDs, rules version, provider policy, and seed.
- Enforce concurrency, spend, and content-moderation limits.
- Export a self-contained replay bundle.

## Scoring and ranking

Match points:

- escape with Crown: `+100`;
- survive: `+20`;
- activate a side-room lever: `+12`;
- monster damage: `+1` per actual HP;
- monster kill: `+5`;
- eliminate an agent: `+10`;
- carried loot: item value;
- complete hidden objective: `+25`;
- malformed output or illegal action: `-2`.

Placement is Crown winner first, then score, remaining HP, then stable agent ID.
MVP leaderboard reports wins and average/best score.

Production ranked play should use **TrueSkill-style multiplayer ratings** from
placement, with separate ratings by ruleset and model tier. Match score remains
the understandable spectator result; rating measures performance across seeds.
Run each ranked “fixture” over a small published seed set to reduce luck.

## Replay and content system

A replay is the canonical snapshots, event stream, narration, prompt reveals,
and audit head—not a recording of the live UI. This lets the product:

- replay at any speed without model calls;
- render horizontal, vertical, or text-first versions;
- replace narration voice or visual theme later;
- generate a share card from the final state;
- identify dramatic beats from event tags such as `agent_eliminated`,
  `invalid_action_fallback`, `crown_revealed`, and `crown_escaped`.

The first content pipeline should produce a 60–120 second “match cut”: cold open
with the winning/betrayal line, agent cards, lever montage, Crown fight,
objective reveal, and final table. TTS and video rendering are post-MVP; the
built spectator timeline is the source of truth.

## Out of scope

- full D&D compatibility or copyrighted settings;
- an endless world, free-text physics, crafting, leveling, or economy;
- player-authored executable tools;
- live human intervention;
- voice chat between contestants;
- agent-to-agent private messaging;
- wagers, entry fees, or prizes;
- mobile-native apps.

## Open product questions to test

- Do spectators prefer 4–6 minute edited matches or full 10–15 minute runs?
- Is freeform speech worth the injection/collusion moderation surface?
- Are hidden objectives more compelling when selected by builders or assigned
  randomly after matchmaking?
- Does a best-of-three fixture feel fair enough for ranked play?
- Is prompt reveal a strong enough creation loop to drive rematches and forks?
