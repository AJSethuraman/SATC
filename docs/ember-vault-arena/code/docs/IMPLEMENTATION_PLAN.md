# Implementation Milestones

## Phase 0 — Product proof (completed in this prototype)

Deliver one repeatable dungeon with four agents, deterministic mock policies,
optional live-model calls, strict schemas, SQLite event storage, seeded hash
RNG, NPC intents, narration, audit chain, automated tests, and replay UI.

Exit: one command produces a completed match and the browser can replay it.

## Phase 1 — Closed alpha (1–2 weeks)

- Port contracts and pure referee to a TypeScript package.
- Add property-based tests and 500-seed balance simulations.
- Add Postgres schema/migrations and durable `pg-boss` match jobs.
- Build account login, roster ownership, private/unranked lobbies, and quotas.
- Add SSE live updates and explicit provider/model policies.
- Add moderation and secure prompt-reveal authorization.
- Run 20 hand-authored agent archetypes against 100 seeds.

Exit: 95% unattended completion, reproducible referee, and a measured cost per
match.

## Phase 2 — Entertaining public beta (2–3 weeks)

- Tune builds, monster damage, objectives, and round count from simulations.
- Add match cards, shareable replay URLs, bookmarks, and dramatic event markers.
- Add season leaderboard with multiplayer rating and best-of-three fixtures.
- Add agent fork/remix flow after prompt reveal.
- Add template narration fallback styles and model-quality A/B tests.
- Add admin tools for stuck jobs, spend, moderation, and audit export.

Exit: strangers understand and share matches without a creator explaining the
rules.

## Phase 3 — Content engine (2 weeks)

- Convert replay frames to 16:9 and 9:16 render scenes.
- Add TTS, captions, music-safe audio bed, and deterministic camera timing.
- Auto-cut cold open, setup, pivotal events, Crown resolution, and final table.
- Produce poster, thumbnail, and short description from canonical metadata.
- Human review remains optional; bad renders do not block match completion.

Exit: every completed match can generate a watchable short with no manual edit.

## Phase 4 — Persistent season (only after retention)

- Carry typed relationships and reputation—not arbitrary free-text state—across
  matches.
- Add a second dungeon only after the first has stable balance and repeat play.
- Introduce season events, rivalries, limited injuries, and agent record pages.
- Allow community-authored unranked scenarios through a declarative rules DSL.

Exit: persistence creates return behavior without turning the system into an
unbounded open-world simulator.

## Recommended build order

1. Preserve the referee and audit invariants.
2. Measure entertainment and match cost with seeded simulations.
3. Make replay sharing excellent.
4. Add rankings only after fixture fairness is defensible.
5. Add content automation.
6. Expand rules/world last.

The most important near-term experiment is not another room. It is whether
prompt reveal plus one-click rematch makes builders iterate on agents after
watching a loss.

