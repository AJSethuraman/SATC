"""Project an exported replay bundle into a compact, UI-ready summary.

Reads demo/replay.json (produced by `run.py replay MATCH_ID --output ...`) and
writes demo/summary.json.  Every value is copied or aggregated from the replay;
the only thing this script authors is presentation metadata (a per-seat colour
from a fixed palette) and the deterministic highlight importance table.

Usage:
    python3 demo/build_summary.py [--replay demo/replay.json] [--out demo/summary.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from arena import items  # noqa: E402


# Presentation only: stable seat -> colour, so the UI can keep an agent's colour
# constant across the roster, the map and the timeline.
SEAT_PALETTE = [
    "#e0523f",  # 1
    "#3f8fe0",  # 2
    "#8e5fd6",  # 3
    "#d9a13b",  # 4
    "#3fb98a",  # 5
    "#d64f92",  # 6
    "#6f7b8c",  # 7
    "#b6763f",  # 8
]

ACT_NAMES = {1: "Act I — The Gates", 2: "Act II — The Long Knife", 3: "Act III — The Contraction"}

# Plumbing events: their content is already published elsewhere (dice proofs ride
# inside the acting event's `roll`, and resource updates are private token/memory
# bookkeeping). Everything else in the committed log is kept verbatim.
TIMELINE_EXCLUDED = {"dice_roll", "agent_resource_update"}

# Deterministic highlight importance. Higher wins; ties break on (round, ordinal).
IMPORTANCE = {
    "crown_extracted": 100,
    "agent_eliminated": 80,
    "crown_taken": 70,
    "crown_dropped": 65,
    "crown_unlocked": 58,
    "monster_defeated": 55,
    "wild_swing_bystander": 50,
    "score_swing": 45,
    "seal_activated": 38,
    "vault_gate_opened": 32,
    "room_sealed": 26,
    "agent_force_moved": 26,
    "act_started": 20,
    "cache_found": 16,
    "wild_swing_self_drop": 14,
}
ACCIDENT_BONUS = 12          # a collateral (accidental) kill outranks a clean one
WARDEN_BONUS = 8             # the Crown Warden outranks a gate guardian
AGENT_BYSTANDER_BONUS = 10   # collateral onto a rival outranks collateral onto a monster
SCORE_SWING_THRESHOLD = 6    # points gained by one agent in one round
HIGHLIGHT_LIMIT = 25


def act_for_round(round_no: int) -> int:
    if round_no <= 4:
        return 1
    if round_no <= 7:
        return 2
    return 3


def roll_of(event: dict) -> dict | None:
    """The salient die behind an event, or None. Copied, never recomputed."""
    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        return None
    tohit = payload.get("tohit")
    if isinstance(tohit, dict):
        out = {
            "kind": "tohit",
            "label": tohit.get("label"),
            "sides": 20,
            "result": tohit.get("roll"),
            "total": tohit.get("total"),
            "dc": (tohit.get("dc") or {}).get("value"),
            "hit": tohit.get("hit"),
        }
        damage = payload.get("damage")
        if isinstance(damage, dict):
            out["damage"] = {
                "label": damage.get("label"),
                "sides": 6,
                "result": damage.get("roll"),
                "amount": damage.get("amount"),
            }
        wild = payload.get("wild_swing")
        if isinstance(wild, dict):
            out["wild_swing"] = {
                "label": wild.get("label"),
                "sides": 6,
                "result": wild.get("roll"),
                "face_id": wild.get("face_id"),
            }
        return out
    selection = payload.get("selection")
    if isinstance(selection, dict) and selection.get("roll") is not None:
        return {
            "kind": "bystander_pick",
            "label": selection.get("label"),
            "sides": len(selection.get("candidates") or payload.get("candidates") or []) or None,
            "result": selection.get("roll"),
        }
    if "roll" in payload and isinstance(payload.get("roll"), int):
        return {
            "kind": "search",
            "sides": 20,
            "result": payload["roll"],
            "total": payload.get("total"),
        }
    proof = payload.get("proof")
    if isinstance(proof, dict):
        return {
            "kind": "proof",
            "label": proof.get("label"),
            "sides": proof.get("sides"),
            "result": proof.get("result"),
        }
    return None


def importance_of(event: dict) -> int | None:
    base = IMPORTANCE.get(event["event_type"])
    if base is None:
        return None
    payload = event.get("payload") or {}
    if event["event_type"] == "agent_eliminated" and payload.get("accident"):
        base += ACCIDENT_BONUS
    if event["event_type"] == "monster_defeated" and payload.get("monster_id") == "crown_warden":
        base += WARDEN_BONUS
    if event["event_type"] == "wild_swing_bystander":
        if payload.get("bystander_kind") == "agent":
            base += AGENT_BYSTANDER_BONUS
        else:
            base -= 20
    return base


def build(replay: dict) -> dict:
    match = replay["match"]
    participants = sorted(replay["participants"], key=lambda p: p["seat"])
    events = replay["events"]
    snapshots = {(s["round_no"], s["phase"]): s["state"] for s in replay["snapshots"]}
    final_state = last_final(replay)

    roster = []
    for participant in participants:
        manifest = participant["manifest"]
        roster.append(
            {
                "id": manifest["id"],
                "name": manifest["name"],
                "build": manifest["build"],
                "color": SEAT_PALETTE[(participant["seat"] - 1) % len(SEAT_PALETTE)],
                "final_score": participant["final_score"],
                "placement": participant["placement"],
                "status": participant["final_status"],
            }
        )

    # ---- timeline ----------------------------------------------------------
    rounds = sorted({e["round_no"] for e in events})
    by_round: dict[int, list[dict]] = {r: [] for r in rounds}
    for ordinal, event in enumerate(events):
        if event["event_type"] in TIMELINE_EXCLUDED:
            continue
        by_round[event["round_no"]].append(
            {
                "type": event["event_type"],
                "actor": event["actor_id"],
                "target": event["target_id"],
                "text": event["public_text"],
                "roll": roll_of(event),
                "payload": event["payload"],
                "_ordinal": ordinal,
            }
        )

    timeline = []
    for round_no in rounds:
        state = (
            snapshots.get((round_no, "end"))
            or snapshots.get((round_no, "final"))
            or snapshots.get((round_no, "start"))
        )
        entry = {
            "round": round_no,
            "act": act_for_round(round_no) if round_no else 0,
            "act_name": ACT_NAMES.get(act_for_round(round_no)) if round_no else "Setup",
            "events": [
                {k: v for k, v in item.items() if k != "_ordinal"}
                for item in by_round[round_no]
            ],
            "state_after": state_projection(state) if state else None,
        }
        timeline.append(entry)

    # ---- highlights --------------------------------------------------------
    candidates = []
    for round_no in rounds:
        for item in by_round[round_no]:
            weight = importance_of(
                {"event_type": item["type"], "payload": item["payload"]}
            )
            if weight is None:
                continue
            candidates.append(
                {
                    "round": round_no,
                    "type": item["type"],
                    "text": item["text"],
                    "_weight": weight,
                    "_ordinal": item["_ordinal"],
                }
            )

    # score swings come from the scores table, not from any event
    swings: dict[tuple[int, str], int] = {}
    for row in replay["scores"]:
        key = (row["round_no"], row["agent_id"])
        swings[key] = swings.get(key, 0) + row["points"]
    names = {p["manifest"]["id"]: p["manifest"]["name"] for p in participants}
    for (round_no, agent_id), points in sorted(swings.items()):
        if points >= SCORE_SWING_THRESHOLD:
            candidates.append(
                {
                    "round": round_no,
                    "type": "score_swing",
                    "text": f"{names.get(agent_id, agent_id)} banks {points:+d} points in round {round_no}.",
                    "_weight": IMPORTANCE["score_swing"] + min(points, 12),
                    "_ordinal": 10**6 + round_no,
                }
            )

    candidates.sort(key=lambda c: (-c["_weight"], c["round"], c["_ordinal"]))
    chosen = candidates[:HIGHLIGHT_LIMIT]
    chosen.sort(key=lambda c: (c["round"], c["_ordinal"]))
    highlights = [
        {"round": c["round"], "type": c["type"], "text": c["text"]} for c in chosen
    ]

    winner_id = final_state["winner_agent_id"]
    return {
        "seed": match["seed"],
        "match_id": match["id"],
        "ruleset_version": match["ruleset_version"],
        "ended_reason": final_state["ended_reason"],
        "winner": {
            "id": winner_id,
            "name": names.get(winner_id, winner_id),
            "score": final_state["agents"][winner_id]["score"],
            "status": final_state["agents"][winner_id]["status"],
        },
        "rounds": final_state["round"],
        "max_rounds": match["max_rounds"],
        "roster": roster,
        "timeline": timeline,
        "highlights": highlights,
        # The last round's ``state_after`` is that round's END snapshot, before
        # finalize awards secret objectives. This is the post-finalize state.
        "final_state": state_projection(final_state),
    }


def last_final(replay: dict) -> dict:
    finals = [s for s in replay["snapshots"] if s["phase"] == "final"]
    return finals[-1]["state"]


def state_projection(state: dict) -> dict:
    agents = []
    for agent_id in sorted(state["agents"]):
        agent = state["agents"][agent_id]
        agents.append(
            {
                "id": agent["id"],
                "hp": agent["hp"],
                "max_hp": agent["max_hp"],
                "room": agent["room"],
                "score": agent["score"],
                "status": agent["status"],
                # self-describing, exactly as the observation publishes them
                "inventory": items.describe_items(agent["inventory"]),
            }
        )
    crown = state["crown"]
    return {
        "agents": agents,
        "seals": dict(state["seals"]),
        "crown": {
            "status": crown["status"],
            "carrier_id": crown["carrier_id"],
            "room": crown["room"],
            "attunement_rounds": crown["attunement_rounds"],
            "transfers": crown["transfers"],
        },
        "sealed_rooms": list(state["contraction"]["sealed"]),
        "contracting_rooms": list(state["contraction"]["contracting"]),
        "monsters": {
            monster_id: {
                "hp": monster["hp"],
                "room": monster["room"],
                "alive": monster["hp"] > 0,
            }
            for monster_id, monster in sorted(state["monsters"].items())
        },
    }


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", default=str(here / "replay.json"))
    ap.add_argument("--out", default=str(here / "summary.json"))
    args = ap.parse_args()

    replay = json.loads(Path(args.replay).read_text(encoding="utf-8"))
    summary = build(replay)
    Path(args.out).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"wrote {args.out}: seed={summary['seed']} match={summary['match_id']} "
        f"winner={summary['winner']['id']} rounds={summary['rounds']} "
        f"highlights={len(summary['highlights'])}"
    )


if __name__ == "__main__":
    main()
