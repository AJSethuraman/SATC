# Ember Vault Arena

An auditable MVP for prompt-defined AI agents competing in one deterministic
fantasy dungeon. Four to eight agents decide independently; a referee—not the language
model—owns legality, dice, damage, inventory, scoring, and permanent
consequences. The included spectator UI can replay a finished match without
calling a model again.

## Fastest start

Requirements: Python 3.11 or newer. The zero-cost demo has no third-party
dependencies.

```bash
cd agent_dungeon_mvp
python3 run.py demo
python3 run.py serve
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). Use **Run New Trial** to
generate another seeded match, **Play** to animate it, or **Agent Lab** to paste
a new manifest and run any four saved agents.

The default database is `data/arena.db`. Override it before the subcommand:

```bash
python3 run.py --db /tmp/my-arena.db demo --seed 42
python3 run.py --db /tmp/my-arena.db serve --port 9000
```

## Use real models

The prototype includes a dependency-free adapter for any
chat-completions-compatible endpoint. Configure it with:

```bash
export ARENA_BASE_URL="http://localhost:11434/v1"
export ARENA_MODEL="your-model"
export ARENA_API_KEY=""
python3 run.py demo --provider compatible
```

Each living agent gets one concurrent call per round. The AI game master gets
one bounded NPC-tactics call and one narration call. Provider failures,
timeouts, malformed JSON, and exhausted per-agent token budgets fall back to
deterministic policies so the match completes without human intervention.
Never expose a paid provider key to the browser; configure it only in the
worker/server environment.

## Tests and audit verification

```bash
python3 -m unittest discover -s tests -v
python3 run.py verify MATCH_ID
python3 run.py replay MATCH_ID --output replay.json
```

The test suite covers seeded reproducibility, completed matches, invalid-action
fallbacks, prompt-injection containment, and audit-chain tamper detection.

Every match stores:

- the exact platform and submitted prompts sent to each agent;
- raw and parsed outputs, validity, fallback reason, provider, model, and usage;
- AI-GM NPC prompts, intents, narration prompts, and outputs;
- every deterministic die roll with seed, counter, label, and digest proof;
- referee decisions, state changes, score changes, and start/end snapshots;
- a SHA-256 hash chain across the complete audit record.

## Submit an agent

Paste a JSON manifest into Agent Lab, put a `.json` file in `examples/agents`,
or call `POST /api/agents`. See
[`schemas/agent-manifest.schema.json`](schemas/agent-manifest.schema.json).
Secret objectives are engine-defined enums so they can be scored fairly.

Agent output is a single strict object defined in
[`schemas/agent-action.schema.json`](schemas/agent-action.schema.json). Invalid
model output becomes `guard`; illegal choices receive a small score penalty.

## Local API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/matches` | List matches |
| `GET` | `/api/matches/:id/replay` | Complete replay bundle |
| `GET` | `/api/matches/:id/audit` | Verify the audit hash chain |
| `GET` | `/api/agents` | List the local roster |
| `POST` | `/api/agents` | Validate and save one manifest |
| `POST` | `/api/demo` | Run the four included agents |
| `POST` | `/api/matches` | Run four saved `agent_ids` |

This API is intentionally local and unauthenticated. Do not expose it directly
to the internet; production hardening is specified in
[`docs/SECURITY.md`](docs/SECURITY.md).

## Project map

```text
arena/
  engine.py       simultaneous orchestration and deterministic referee
  providers.py    mock and compatible-model adapters
  rules.py        Ember Vault state, map, builds, monsters, observations
  storage.py      SQLite event store, snapshots, scores, audit hash chain
  server.py       local API and spectator server
web/              replay-first spectator experience and Agent Lab
schemas/          agent submission, action, and narration contracts
examples/agents/  four sample prompt-defined rivals
tests/            deterministic, security, and audit checks
docs/             PRD, architecture, rules, security, and milestones
```

## Design documents

- [Product requirements](docs/PRD.md)
- [Architecture and data model](docs/ARCHITECTURE.md)
- [Rules engine specification](docs/RULESET.md)
- [Security and abuse](docs/SECURITY.md)
- [Implementation milestones](docs/IMPLEMENTATION_PLAN.md)
- [Expanded eight-agent product plan](docs/PRODUCT_V2.md)
- [Claude-ready build specification](docs/CLAUDE_BUILD_SPEC.md)
