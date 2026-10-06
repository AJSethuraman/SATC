"""Scan candidate seeds and score each finished match for DRAMA.

Every number here comes from a real executed match: the engine is run for each
seed against the deterministic mock provider, and the metrics are read back out
of the committed event log and the final snapshot.  Nothing is synthesised.

Usage:
    python3 demo/scan_seeds.py --count 120 --workers 8
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from arena.demo import load_manifests  # noqa: E402
from arena.engine import ArenaEngine  # noqa: E402
from arena.providers import MockDecisionProvider  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402


WILD_SWING_TYPES = {
    "wild_swing_self_drop",
    "wild_swing_self_damage",
    "wild_swing_bystander",
    "wild_swing_no_bystander",
    "wild_swing_room_reaction",
}


def measure(seed: int) -> dict:
    """Run one full match for `seed` and return its drama metrics."""
    handle, db_path = tempfile.mkstemp(prefix=f"scan-{seed}-", suffix=".db")
    os.close(handle)
    store = ArenaStore(db_path)
    try:
        manifests = load_manifests()
        match_id = ArenaEngine(store, MockDecisionProvider()).run(manifests, seed)
        bundle = store.replay_bundle(match_id)
    finally:
        store.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(db_path + suffix)
            if candidate.exists():
                candidate.unlink()

    events = bundle["events"]
    final = [s for s in bundle["snapshots"] if s["phase"] == "final"][-1]["state"]
    crown = final["crown"]

    def of(*types: str) -> list[dict]:
        return [e for e in events if e["event_type"] in types]

    collateral_on_agents = [
        e
        for e in of("wild_swing_bystander")
        if e["payload"].get("bystander_kind") == "agent"
    ]
    collateral_on_monsters = [
        e
        for e in of("wild_swing_bystander")
        if e["payload"].get("bystander_kind") == "monster"
    ]
    wild_swings = [e for e in events if e["event_type"] in WILD_SWING_TYPES]
    eliminations = of("agent_eliminated")
    accidental_elims = [
        e for e in eliminations if e["payload"].get("collateral") or e["payload"].get("accident")
    ]
    force_moves = of("agent_force_moved")
    extracted = of("crown_extracted")
    seal_events = of("seal_activated")
    warden = final["monsters"].get("crown_warden", {})

    scores = sorted(
        (p["final_score"] for p in bundle["participants"]), reverse=True
    )
    gap = (scores[0] - scores[1]) if len(scores) > 1 else 99

    rounds = final["round"]
    ended_reason = final["ended_reason"]
    escape_round = extracted[0]["round_no"] if extracted else None
    # transfers counts the initial pickup too; possession CHANGES after that.
    possession_changes = max(0, crown["transfers"] - 1)
    distinct_holders = len(set(crown["taken_by"]))

    m = {
        "seed": seed,
        "match_id": match_id,
        "rounds": rounds,
        "ended_reason": ended_reason,
        "escape_round": escape_round,
        "winner": final["winner_agent_id"],
        "reached_act3": rounds >= 8,
        "crown_transfers": possession_changes,
        "crown_distinct_holders": distinct_holders,
        "crown_takes": crown["transfers"],
        "collateral_agent_hits": len(collateral_on_agents),
        "collateral_monster_hits": len(collateral_on_monsters),
        "wild_swings": len(wild_swings),
        "eliminations": len(eliminations),
        "accidental_eliminations": len(accidental_elims),
        "force_moves": len(force_moves),
        "seals_activated": len(seal_events),
        "warden_dead": warden.get("hp", 1) <= 0,
        "score_gap": gap,
        "top_score": scores[0] if scores else 0,
    }

    drama = 0.0
    if m["ended_reason"] == "extraction":
        drama += 25
        drama += 2.0 * (escape_round or 0)          # later escape = more tension
    if m["reached_act3"]:
        drama += 12
    drama += 10 * min(m["crown_transfers"], 4)
    drama += 6 * (m["crown_distinct_holders"] - 1 if m["crown_distinct_holders"] else 0)
    drama += 9 * min(m["collateral_agent_hits"], 4)
    drama += 3 * min(m["collateral_monster_hits"], 4)
    drama += 1.5 * min(m["wild_swings"], 10)
    drama += 7 * min(m["eliminations"], 4)
    drama += 5 * min(m["accidental_eliminations"], 2)
    drama += 4 * min(m["force_moves"], 4)
    drama += 2 * m["seals_activated"]
    drama += 5 if m["warden_dead"] else 0
    drama += max(0, 12 - m["score_gap"])            # close finish
    m["drama"] = round(drama, 2)
    m["meets_all_preferences"] = bool(
        m["reached_act3"]
        and m["crown_transfers"] >= 1
        and m["collateral_agent_hits"] >= 1
        and m["ended_reason"] == "extraction"
    )
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=120)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "seed_scan.json"),
    )
    args = ap.parse_args()

    seeds = list(range(args.start, args.start + args.count))
    with mp.Pool(args.workers) as pool:
        results = pool.map(measure, seeds)

    results.sort(key=lambda r: (-r["drama"], r["seed"]))
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")

    preferred = [r for r in results if r["meets_all_preferences"]]
    print(f"scanned {len(results)} seeds; {len(preferred)} meet every preference")
    print()
    header = (
        f"{'seed':>6} {'drama':>7} {'rnds':>4} {'end':>12} {'xfer':>4} "
        f"{'hold':>4} {'colA':>4} {'wild':>4} {'elim':>4} {'fmv':>3} "
        f"{'gap':>3}  winner  pref"
    )
    print(header)
    for r in (preferred or results)[:15]:
        print(
            f"{r['seed']:>6} {r['drama']:>7.1f} {r['rounds']:>4} "
            f"{r['ended_reason']:>12} {r['crown_transfers']:>4} "
            f"{r['crown_distinct_holders']:>4} {r['collateral_agent_hits']:>4} "
            f"{r['wild_swings']:>4} {r['eliminations']:>4} {r['force_moves']:>3} "
            f"{r['score_gap']:>3}  {r['winner']}  {r['meets_all_preferences']}"
        )


if __name__ == "__main__":
    main()
