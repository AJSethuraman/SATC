"""Pin the golden replay (PRD §5.40): the mock match on seed 52, as a sequence
of snapshot state hashes plus its placements. CI verifies a fresh run against
this file with no model call. Regenerate ONLY when a rule change is meant to
move the match, and say so in the commit; the diff of this file is the diff of
the match.

    python3 tools/write_golden.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena.demo import load_manifests  # noqa: E402
from arena.engine import ArenaEngine  # noqa: E402
from arena.models import ACTION_SCHEMA_VERSION, RULESET_VERSION  # noqa: E402
from arena.providers import MockDecisionProvider, PROMPT_VERSION  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "seed52.json"
SEED = 52


def golden_record() -> dict:
    with tempfile.TemporaryDirectory() as d:
        store = ArenaStore(Path(d) / "golden.db")
        match_id = ArenaEngine(store, MockDecisionProvider(), parallel_agents=True).run(
            load_manifests(), SEED
        )
        bundle = store.replay_bundle(match_id)
        audit = store.verify_audit(match_id)
        store.close()
    return {
        "seed": SEED,
        "ruleset_version": RULESET_VERSION,
        "action_schema_version": ACTION_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "rounds": bundle["match"]["max_rounds"],
        "winner": bundle["match"]["winner_agent_id"],
        "status": bundle["match"]["status"],
        "placements": {p["manifest"]["id"]: p["placement"] for p in bundle["participants"]},
        "final_scores": {p["manifest"]["id"]: p["final_score"] for p in bundle["participants"]},
        "snapshot_hashes": [s["state_hash"] for s in bundle["snapshots"]],
        "event_count": len(bundle["events"]),
        "audit_valid": audit["valid"],
    }


def main() -> int:
    record = golden_record()
    GOLDEN.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {GOLDEN.relative_to(ROOT)}: {len(record['snapshot_hashes'])} snapshots, "
          f"winner {record['winner']}, {record['event_count']} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
