#!/usr/bin/env python3
"""Build demo/viewer.html: enrich summary.json, attribute the score ledger to
individual events, verify the reconstruction, and inline the result into the
single-file viewer template.

Run:  python3 demo/build_viewer.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY = os.path.join(HERE, "summary.json")
REPLAY = os.path.join(HERE, "replay.json")
TEMPLATE = os.path.join(HERE, "viewer_template.html")
OUT = os.path.join(HERE, "viewer.html")

FINISHERS = {"guardian_finishing_blow", "warden_finishing_blow"}


def load():
    with open(SUMMARY) as fh:
        summary = json.load(fh)
    with open(REPLAY) as fh:
        replay = json.load(fh)
    return summary, replay


def agent_stats(replay):
    """Power/armor/speed/search per agent, from the first snapshot."""
    snap = replay["snapshots"][0]["state"]
    if isinstance(snap, str):
        snap = json.loads(snap)
    out = {}
    for aid, a in snap["agents"].items():
        out[aid] = {
            "power": a["power"],
            "armor": a["armor"],
            "speed": a["speed"],
            "search": a["search"],
            "max_hp": a["max_hp"],
        }
    return out


def build_roster(summary, replay):
    stats = agent_stats(replay)
    manifests = {p["manifest"]["id"]: p["manifest"] for p in replay["participants"]}
    roster = []
    for entry in summary["roster"]:
        aid = entry["id"]
        m = manifests.get(aid, {})
        row = dict(entry)
        row.update(stats.get(aid, {}))
        row["personality"] = m.get("personality", "")
        row["secret_objective"] = m.get("secret_objective", "")
        roster.append(row)
    roster.sort(key=lambda r: r["placement"])
    return roster


def attribute_scores(summary, replay):
    """Map every ledger row onto (round, event_index). Returns awards keyed by
    'round:event_index' -> [{agent_id, points, category, detail}]."""
    ledger = replay["scores"]
    by_round = {}
    for row in ledger:
        by_round.setdefault(row["round_no"], []).append(row)

    awards = {}
    unattributed = []

    for frame in summary["timeline"]:
        rnd = frame["round"]
        rows = list(by_round.get(rnd, []))
        events = frame["events"]

        def claim(pred):
            for i, row in enumerate(rows):
                if pred(row):
                    return rows.pop(i)
            return None

        for idx, ev in enumerate(events):
            etype = ev["type"]
            payload = ev.get("payload") or {}
            actor = ev.get("actor")
            claims = []

            if etype == "seal_activated":
                claims.append(claim(lambda r: r["category"] == "seal_activated" and r["agent_id"] == actor))
            elif etype == "cache_found":
                claims.append(claim(lambda r: r["category"] == "cache_first_find" and r["agent_id"] == actor))
            elif etype == "crown_taken":
                aid = payload.get("agent_id", actor)
                claims.append(claim(lambda r: r["category"] == "crown_taken" and r["agent_id"] == aid))
            elif etype == "crown_attuned":
                aid = payload.get("agent_id", actor)
                claims.append(claim(lambda r: r["category"] == "attunement_round" and r["agent_id"] == aid))
            elif etype == "monster_defeated":
                credited = payload.get("credited_to")
                if credited:
                    claims.append(claim(lambda r: r["category"] in FINISHERS and r["agent_id"] == credited))
            elif etype == "agent_eliminated":
                credited = payload.get("credited_to")
                if credited:
                    claims.append(claim(lambda r: r["category"] == "direct_elimination" and r["agent_id"] == credited))
            elif etype == "crown_extracted":
                aid = payload.get("agent_id", actor)
                claims.append(claim(lambda r: r["category"] == "extraction" and r["agent_id"] == aid))
            elif etype == "objective_reveal":
                if payload.get("completed"):
                    claims.append(claim(lambda r: r["category"] == "secret_objective" and r["agent_id"] == actor))
            elif etype == "act_two_survival":
                for aid in payload.get("survivors", []):
                    claims.append(claim(lambda r, a=aid: r["category"] == "survived_act_ii" and r["agent_id"] == a))
            elif etype == "attack_hit":
                if payload.get("attacker_kind") == "agent" and payload.get("target_kind") == "monster":
                    claims.append(claim(lambda r: r["category"] == "monster_hit" and r["agent_id"] == actor))

            got = [c for c in claims if c]
            if got:
                awards["%d:%d" % (rnd, idx)] = [
                    {
                        "agent_id": c["agent_id"],
                        "points": c["points"],
                        "category": c["category"],
                        "detail": c["detail"],
                    }
                    for c in got
                ]

        for leftover in rows:
            unattributed.append(leftover)

    return awards, unattributed


def verify(summary, awards):
    """Replay awards round by round; totals must equal the authoritative
    per-round snapshot scores.

    The final round's snapshot is written *before* secret objectives are
    scored, so the last frame reconciles against final_state instead.
    """
    totals = {a["id"]: 0 for a in summary["timeline"][0]["state_after"]["agents"]}
    problems = []
    last = len(summary["timeline"]) - 1
    for i, frame in enumerate(summary["timeline"]):
        rnd = frame["round"]
        for idx in range(len(frame["events"])):
            for aw in awards.get("%d:%d" % (rnd, idx), []):
                totals[aw["agent_id"]] += aw["points"]
        truth = summary["final_state"] if i == last else frame["state_after"]
        for a in truth["agents"]:
            if totals[a["id"]] != a["score"]:
                problems.append((rnd, a["id"], totals[a["id"]], a["score"]))
    return problems


def verify_state(summary):
    """Re-derive per-event state deltas and reconcile against each round's
    authoritative state_after."""
    tl = summary["timeline"]
    state = copy.deepcopy(tl[0]["state_after"])
    agent_ids = {a["id"] for a in state["agents"]}
    monster_ids = set(state["monsters"])
    problems = []

    def find(st, aid):
        for a in st["agents"]:
            if a["id"] == aid:
                return a
        return None

    for frame in tl[1:]:
        st = copy.deepcopy(state)
        for ev in frame["events"]:
            payload = ev.get("payload") or {}
            changes = payload.get("changes") or {}
            actor, target = ev.get("actor"), ev.get("target")
            subject = target if (target in agent_ids or target in monster_ids) else actor
            for key, val in changes.items():
                if key == "hp":
                    if subject in monster_ids:
                        mon = st["monsters"][subject]
                        mon["hp"] = val[1]
                        mon["alive"] = val[1] > 0
                    else:
                        a = find(st, subject)
                        if a:
                            a["hp"] = val[1]
                elif key == "room":
                    a = find(st, actor if actor in agent_ids else subject)
                    if a:
                        a["room"] = val[1]
                elif key == "status":
                    a = find(st, subject if subject in agent_ids else actor)
                    if a:
                        a["status"] = val[1]
            if ev["type"] == "monster_defeated":
                mon = st["monsters"][payload["monster_id"]]
                mon["hp"] = 0
                mon["alive"] = False
            elif ev["type"] == "seal_activated":
                st["seals"][payload["room"]] = "active"
            elif ev["type"] == "room_sealed":
                for room in payload.get("sealed", []):
                    if room not in st["sealed_rooms"]:
                        st["sealed_rooms"].append(room)
        exp = frame["state_after"]
        for a in exp["agents"]:
            got = find(st, a["id"])
            for key in ("hp", "room", "status"):
                if got[key] != a[key]:
                    problems.append((frame["round"], a["id"], key, got[key], a[key]))
        for mid, mon in exp["monsters"].items():
            if st["monsters"][mid]["hp"] != mon["hp"]:
                problems.append((frame["round"], mid, "hp"))
        state = copy.deepcopy(exp)
    return problems


ROOMS = [
    {"id": "egress", "name": "Egress", "kind": "exit",
     "blurb": "Open sky. Only the attuned Crown-bearer may walk out.",
     "neighbors": ["vault"], "col": 2, "row": 1},
    {"id": "vault", "name": "The Ember Vault", "kind": "vault",
     "blurb": "The plinth, the ember-glass, and the Crown Warden.",
     "neighbors": ["ironwood_gate", "ossuary_gate", "egress"], "col": 2, "row": 2},
    {"id": "ironwood_gate", "name": "The Ironwood Gate", "kind": "gate",
     "blurb": "Seal, cache and the Ironwood Guardian.",
     "neighbors": ["threshold", "vault"], "col": 1, "row": 3},
    {"id": "ossuary_gate", "name": "The Ossuary Gate", "kind": "gate",
     "blurb": "Seal, cache and the Ossuary Guardian.",
     "neighbors": ["threshold", "vault"], "col": 3, "row": 3},
    {"id": "threshold", "name": "The Threshold", "kind": "start",
     "blurb": "Where every rival started. Seals at the end of round 9.",
     "neighbors": ["ironwood_gate", "ossuary_gate"], "col": 2, "row": 4},
]

EDGES = [
    ["egress", "vault"],
    ["vault", "ironwood_gate"],
    ["vault", "ossuary_gate"],
    ["ironwood_gate", "threshold"],
    ["ossuary_gate", "threshold"],
]


def main():
    summary, replay = load()

    state_problems = verify_state(summary)
    awards, unattributed = attribute_scores(summary, replay)
    score_problems = verify(summary, awards)

    print("state reconciliation problems: %d" % len(state_problems))
    for p in state_problems[:10]:
        print("   ", p)
    print("unattributed ledger rows: %d" % len(unattributed))
    for row in unattributed[:10]:
        print("   ", row)
    print("score reconciliation problems: %d" % len(score_problems))
    for p in score_problems[:10]:
        print("   ", p)
    if state_problems or unattributed or score_problems:
        print("REFUSING TO BUILD: data does not reconcile", file=sys.stderr)
        return 1

    data = {
        "seed": summary["seed"],
        "match_id": summary["match_id"],
        "ruleset_version": summary["ruleset_version"],
        "ended_reason": summary["ended_reason"],
        "winner": summary["winner"],
        "rounds": summary["rounds"],
        "max_rounds": summary["max_rounds"],
        "roster": build_roster(summary, replay),
        "timeline": summary["timeline"],
        "highlights": summary["highlights"],
        "final_state": summary["final_state"],
        "awards": awards,
        "ledger": replay["scores"],
        "rooms": ROOMS,
        "edges": EDGES,
        "audit": {
            "events": len(replay["events"]),
            "snapshots": len(replay["snapshots"]),
            "decisions": len(replay["decisions"]),
        },
    }

    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # Guard against breaking out of the <script> element.
    blob = blob.replace("</", "<\\/")

    with open(TEMPLATE, encoding="utf-8") as fh:
        template = fh.read()
    marker = "/*__MATCH_DATA__*/null"
    if marker not in template:
        print("template marker missing", file=sys.stderr)
        return 1
    html = template.replace(marker, blob)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    print("wrote %s (%.1f KB), data %.1f KB" % (OUT, len(html) / 1024.0, len(blob) / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
