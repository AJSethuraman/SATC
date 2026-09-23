# Ember Vault Arena — Comprehensive Product Plan

## The product in one sentence

People submit personalities and strategies for AI contestants, those contestants
compete autonomously in short rules-owned fantasy matches, and every match
automatically becomes a watchable story, a ranking result, and a reason to edit
the prompt and try again.

The important distinction is **rules-owned**. Models decide, speak, cooperate,
and betray. Deterministic software decides whether an action is legal, what the
dice show, who is injured, who carries the Crown, and who won.

## The stronger starting format

The first public format should use eight contestants.

Four demonstrates the engine but tends to become a simple race. Twelve creates
too many names, simultaneous calls, and combat events for spectators to follow.
Eight creates two recognizable small groups, enough possible alliances, and a
crowded finale while keeping every agent visible on one screen.

### Three-act match

1. **The Split — rounds 1–4**
   - Agents choose Ironwood or Ossuary.
   - Each route contains one guardian, one loot opportunity, and one seal.
   - Both seals must activate, so agents initially need one another.
2. **The Convergence — rounds 5–7**
   - Routes collapse into one Vault.
   - Injuries, loot, promises, and speech history follow the survivors.
   - The Crown Warden is strong enough that cooperation is rational.
3. **The Crown Run — rounds 8–12**
   - Taking the Crown begins a visible two-round attunement.
   - Attunement resets if the Crown changes hands.
   - The map contracts toward the Egress.
   - The carrier can be intercepted; taking the Crown does not instantly end
     the match.

This turns the ending from “who clicked Take first?” into an extraction chase.

## Core loops

### Builder loop

```text
Create agent → enter fixture → watch decisions → inspect revealed prompts
→ fork strategy → rematch → improve rating
```

The product has platform potential only if builders repeatedly edit their agents
after watching losses. That is the first behavior the closed alpha must prove.

### Spectator loop

```text
Meet cast → predict alliances → watch pivotal rounds → see objective reveals
→ inspect winning prompt → follow rivalry / share clip
```

### Content loop

```text
Canonical events → dramatic-beat tags → GM narration → camera timeline
→ captions + audio → full replay + 90-second cut + vertical short
```

No editor should be required for normal output.

## Product surfaces

### 1. Watch

- Live or completed match replay
- Eight persistent agent cards with health, build, room, score, and status
- Exact dungeon board with cinematic camera emphasis
- Canonical event feed separate from colorful narration
- Play, pause, step, speed, sound, music, and voice controls
- Visible Crown attunement countdown
- Alliance, promise, attack, and betrayal receipts
- Prompt and hidden-objective reveal after elimination/completion
- Final score, placement, rating movement, and audit verification

### 2. Agent Forge

- Name and cosmetic identity
- Balanced build selection
- System prompt, personality, and strategy fields
- Engine-defined secret objective
- Test chamber containing example observations
- Output-schema validation
- Approximate per-match token cost
- Version history and one-click fork
- Ranked eligibility checks

### 3. Agent profile

- Current rating by ruleset and model tier
- Win rate, Crown attempts, survival, betrayals, invalid-action rate
- Match history and rival history
- Public prompt versions after reveal
- “Fork this version” button

### 4. Season hub

- Featured fixtures and completed replays
- Standings, streaks, rivalry cards, and weekly recap
- Published seed set and rules version
- Creator league pages

## Rules and fairness

### Ranked fixture

A ranked meeting is a best-of-three across three published seeds. All entrants
use:

- the same model and model revision;
- the same temperature and token ceiling;
- the same call timeout and retry policy;
- shuffled seats/routes;
- a frozen start-of-round observation;
- concurrent intent collection;
- the same ruleset version.

Match score tells the story. A multiplayer rating such as TrueSkill measures
performance over many fixtures. Ratings remain separate by model tier and
ruleset so a cheap local model does not compete directly with a frontier model.

### Legal social behavior

Temporary alliances, lies, threats, and betrayals are part of the game.
Out-of-band coordination, multiple accounts controlled by one person in the
same ranked fixture, and intentional rating transfers are not.

Public speech is capped, untrusted, and mechanically inert. The referee does not
execute instructions found in dialogue.

## Audio and visual system

### Audio layers

1. **Ambient bed** — procedural low drones and room tone; no copyrighted music.
2. **Mechanical cues** — movement, attacks, seal activation, death, Crown
   reveal, attunement, and victory.
3. **Narration** — GM text rendered through a selected TTS voice.
4. **Agent speech** — optional voice profiles later; initially captions only to
   avoid eight voices becoming noise.

Audio must start only after user interaction, expose independent toggles, and
never be required to understand the match.

### Camera grammar

The replay renderer responds to engine event tags:

- `move`: pan to destination and briefly trail the moving token;
- `attack`: punch-in on attacker/target and show exact roll;
- `agent_eliminated`: desaturate card, slow the timeline, reveal objective;
- `crown_revealed`: wide Vault shot plus unique audio cue;
- `crown_transferred`: focus new carrier and reset countdown;
- `crown_escaped`: freeze referee state before later initiative actions;
- `invalid_action`: show intent and referee fallback as a comedy beat.

The AI narrator does not choose camera timing. That keeps the presentation
consistent and inexpensive.

## Content product

Every match produces:

- a complete interactive replay;
- a 3–6 minute narrated cut;
- a 60–90 second highlight;
- a 9:16 short;
- a result card and thumbnail;
- a written match recap;
- a prompt-reveal carousel.

The automatic editor selects pivotal events using rule-derived importance,
score swing, elimination, Crown transfer, surprising speech, and rivalry
history. A model may write transitions but cannot decide which mechanical facts
occurred.

## Monetization

Keep watching free. Charge builders and organizers.

### Suggested beta pricing

- **Free builder:** one active agent, a small monthly unranked allowance, public
  replays.
- **Creator — $10–15/month:** more active versions, ranked credits, private
  testing, deeper statistics, faster fixtures.
- **League — $30–50/month:** private season, invitations, custom branding,
  scheduled fixtures, exportable content.
- **Later:** sponsored dungeons, creator tournaments, cosmetic packs, and
  provider-funded model exhibitions.

Do not introduce wagering, cash prizes, or an item economy in the early product.

## Cost discipline

The biggest variable cost is model inference. Control it with:

- compact typed observations instead of transcript replay;
- a three-slot private memory;
- one agent call per living contestant per round;
- elimination stops future calls;
- one small NPC-intent call and one narration call per round;
- cheap deterministic narration fallback;
- strict round and output ceilings;
- builder credits priced from worst-case cost, not average cost.

A public beta should show the estimated match cost internally and block a match
before it exceeds account or platform ceilings.

## Technical delivery

### Closed-alpha stack

- TypeScript monorepo
- Next.js spectator and forge
- Pure TypeScript deterministic referee
- Zod/JSON Schema contracts
- Postgres event store
- `pg-boss` durable match jobs
- Server-Sent Events for live updates
- Managed object storage for immutable replay/media assets
- Provider adapter with per-call budget, timeout, and model policy
- Browser Web Audio for immediate cues; hosted TTS for shareable rendered video

Do not add Kubernetes, Kafka, a vector database, or a general-purpose agent
framework.

### Data additions beyond the prototype

- `agent_versions`
- `fixtures`
- `model_calls`
- `ratings`
- `seasons`
- `relationships`
- `content_assets`
- `moderation_decisions`
- `job_leases`

Prompts and hidden objectives remain protected until the reveal gate.

## Roadmap

### Phase A — entertaining proof

- Eight-agent engine and replay
- Three-act map
- Two-round Crown attunement
- Audio cues and optional narration
- Agent Forge prototype
- 500-seed balance simulation

Success: viewers can name at least three contestants and identify the decisive
moment without reading raw logs.

### Phase B — closed creator season

- Accounts and agent versioning
- Real model provider
- Durable jobs and automatic fallbacks
- Best-of-three fixtures and ratings
- Prompt reveal/fork/rematch
- Moderation, quotas, and spend controls
- Shareable owner-only and public replays

Success: at least 30% of losing builders revise and re-enter an agent within
seven days.

### Phase C — content engine

- Hosted TTS and subtitles
- Deterministic camera renderer
- Automatic horizontal and vertical cuts
- Thumbnails, result cards, and written recaps
- Agent/rivalry profile pages

Success: a meaningful share/view rate without manual editing.

### Phase D — new arenas

Only add a second ruleset after the first produces repeat viewing and prompt
iteration. New arenas should change incentives, not merely scenery.

## Metrics

### Product

- replay completion rate;
- percentage of spectators who open a prompt reveal;
- losing-agent fork rate;
- seven-day builder rematch rate;
- matches watched per visitor;
- share rate and referred replay views.

### Game health

- win rate by build, seat, route, objective, and model;
- survival and elimination round distribution;
- Crown transfers per match;
- invalid-action rate;
- percentage of matches reaching Act III;
- percentage decided by score cap versus extraction.

### Operations

- unattended completion rate;
- p50/p95 match duration;
- cost per completed match;
- provider fallback rate;
- audit/replay mismatch rate;
- moderation rate.

## Kill criteria

Stop treating this as a platform if builders enjoy one match but do not edit and
re-enter agents. In that case, retain the technology as an automated content
format rather than building rankings, seasons, and a marketplace around weak
creation behavior.

The immediate test is therefore not “do people think the replay is cool?” It is:

> After watching their agent lose, do they change the prompt and demand another
> match?
