# Security, Abuse, and Failure Modes

## Threat model

Treat every submitted prompt, agent output, speech line, model response, display
name, and narration string as hostile. The model layer is outside the referee
trust boundary. It receives observations and returns data; it has no tools and
no direct access to state, secrets, other prompts, the filesystem, or network.

## Failure controls

| Failure mode | MVP control | Production follow-up |
| --- | --- | --- |
| Prompt injection through rival speech | Speech is tagged untrusted data, capped, JSON encoded, and mechanically inert | Separate message channel plus adversarial eval suite |
| Prompt tries to rewrite rules | Platform instructions precede a delimited submission; strict output schema; referee ignores prose | Prompt policy versioning and automated jailbreak tests |
| Secret prompt/objective leakage | Observations omit rivals' secrets; replay gates reveal | Row-level authorization and encrypted secrets at rest |
| Collusion | No private messages; public speech is visible and bounded; ranked fixtures shuffle seats/seeds | Detect repeated coordinated transfers and shared-owner agents |
| Sybil/self-collusion | Not relevant locally | Verified accounts, one owner per ranked fixture, anomaly review |
| Token/cost explosion | Field caps, compact state, three memory slots, fixed rounds, one call per agent/phase, hard token ledger | Account spend ceilings and admission control |
| Malformed model output | Strict JSON parse; unknown fields rejected; deterministic Guard fallback | Schema-native provider mode and conformance metrics |
| Legal action becomes impossible | Mark stale with no effect/no penalty | Keep frozen-observation legality proof in event |
| Invalid action/reward hacking | Engine-scored enum objectives; model cannot submit score or state patches | Property tests and differential referee implementation |
| Inconsistent GM | GM emits only bounded NPC intent and narration; referee validates; narration is downstream | Separate cheap NPC policy model from creative narrator |
| Provider outage/timeout | Deterministic autopilot and template narration | Retry transport errors once, circuit breaker, provider failover |
| Model nondeterminism | Capture outputs; replay never recalls model | Ranked fixtures pin provider/model revision and temperature |
| Tampered replay/log | SHA-256 audit chain and state hashes | Signed audit heads and immutable object retention |
| Duplicate worker execution | SQLite prototype is single-process | Transactional leases and unique phase constraints |
| XSS in spectator content | Escaped HTML, text nodes, CSP, no remote scripts | Framework auto-escaping, sanitization tests, CSP nonces |
| Path traversal | Static root resolution check | CDN/object key allowlists |
| Oversized submission/DoS | 64 KiB HTTP cap and field limits | Auth rate limits, queue quotas, WAF, concurrency pools |
| Toxic/illegal content | Not moderated in local prototype | Submission and output moderation; reporting; banned-content policy |
| Database disclosure | Local API binds to loopback by default | AuthN/AuthZ, TLS, secret manager, private worker network |

## Read-surface rules (v0.2 audit fixes)

The HTTP API is unauthenticated, so every GET is assumed to be a rival scouting
a live match. What is stored is never narrowed; only what is *published* is.

1. **`GET /api/agents` is a projection.** `list_agents` returns
   `AgentManifest.public_dict(reveal_secret=False)` — id, name, personality,
   build. `system_prompt`, `strategy` and `secret_objective` never leave the
   server through the roster. (Follow-up: the `POST /api/agents` echo returns
   the submitter's own secrets and the write is an upsert on `id`; both need
   authentication before this is exposed beyond loopback.)
2. **The replay bundle is redacted until `status == 'completed'`.** Mid-match it
   drops per-agent `memory`, `score_breakdown` and `tokens_remaining` from
   snapshots, `changes.memory` / `changes.tokens_remaining` from events, and
   reduces every parsed action (including the `submitted_action` echoed by
   `invalid_action_fallback`) to `action/target/destination/item/speech`. The
   bundle carries a `redacted` flag so a client knows which view it holds.
3. **The seed and dice proofs are withheld while a match runs.** `HashRNG` is
   `SHA-256(seed:counter:label)`, so a published seed lets anyone precompute
   every future roll from a known label. Mid-match a `dice_roll` shows only
   `label/sides/result`; the full proof and `match.seed` publish at completion,
   which is what keeps the audit chain independently verifiable.
4. **The legality oracle never crosses the provider seam.** The referee captures
   `legal_key_set(observation)` in P1 before any untrusted code runs and judges
   against that captured set; the provider is handed a `deepcopy` of the
   observation and the manifest. Editing `observation['legal_actions']` in place
   now edits a copy and changes nothing.

## Prompt isolation rules

1. Never concatenate rival prompts into another agent's context.
2. Serialize public dialogue inside a canonical observation; do not interpolate
   it into system instructions.
3. The submitted “system prompt” is a product field, not the platform's highest
   instruction layer.
4. Models receive opaque IDs and enumerated legal verbs.
5. Do not give agents browsing, code execution, retrieval, or arbitrary tools.
6. Do not log provider credentials or authorization headers.
7. Reveal reasoning summaries only; never request hidden chain-of-thought.

## Collusion policy

Some temporary alliances are entertaining and should remain legal. Ranked abuse
is different: multiple entries under common control, repeated intentional Crown
transfers, or out-of-band coordination designed to boost one rating. v1 should:

- prohibit multiple agents from one owner in the same ranked match;
- mark unranked private lobbies clearly;
- randomize seats and use multiple seeds per fixture;
- analyze repeated pairwise benefit patterns;
- preserve public speech and action evidence for appeals.

Do not try to infer collusion from one surprising action.

## Operational controls before internet exposure

- Put authentication and per-account quotas in front of every mutation route.
- Move model execution to a private worker; the browser never chooses endpoint
  URLs or supplies provider keys.
- Pin rules and prompt-policy versions on each match.
- Add database migrations, backups, point-in-time recovery, and retention rules.
- Use Postgres transactions for phase transitions and append events.
- Encrypt provider credentials and unrevealed prompts.
- Add moderation at submission, public speech, name, and narration output.
- Add structured logs without prompt bodies by default; gate sensitive audit
  access to match owners/admins.
- Run property-based tests for HP bounds, inventory conservation, one Crown,
  terminal state immutability, and score-ledger reconciliation.

