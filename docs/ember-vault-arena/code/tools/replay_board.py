"""A match you watch: the board, the bodies on it, and what happens to them.

Reads a replay bundle (``python run.py replay <match_id> --output x.json``)
and writes one HTML page that plays the match back on a drawn map: the five
rooms to the engine's own grids (``arena.grid.ROOM_GRIDS``, doors, props),
the eight characters and three monsters as tokens on their tiles, every
move, step, swing, hit, seal, sealing room and Crown transfer shown where it
happened, every line spoken shown beside the speaker. Play, pause, step,
scrub by round.

One round reads as one sequence in one panel, the way the engine runs it
(firm, 14 Sep 2026: "Don't they think at the same time? Can't you just show
me that in the play by play? And you can have their goal and such show up
in the same space?"):

    1. everyone thinks     ONE moment: all eight private plans side by side,
                           written before anyone moves (``note_written``)
    2. they speak          each line, with the speaker's plan under it
    3. they act            in initiative order, each action with the
                           actor's plan under it, so what they did can be
                           read against what they meant to do
    4. monsters, referee, narration

The panel always shows, for whoever is acting, their plan for this round,
who they trust, and the secret aim they carry. Nothing to switch on and
nothing to scroll to.

The page is not a second referee. It carries a timeline of state changes
derived from the bundle's events, and the only place a change is *computed*
rather than read is the tile a body lands on after a room move, which the
event does not record; that uses the engine's own ``grid.free_tile_near`` on
the same inputs. ``verify`` then checks the derived state against every
round-end snapshot the referee wrote (room, tile, HP and status of every
character; tile and HP of every monster; who holds the Crown) and the build
refuses on the first mismatch. Tests prove it on a mock match.

    python3 tools/replay_board.py ../runs/ember-7-830ff8da.replay.json out.html
"""
from __future__ import annotations

import argparse
import copy
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena import grid, scoring  # noqa: E402

E = html.escape

# Events that carry nothing a viewer watches: dice and token spend.
SKIP = {"dice_roll", "agent_resource_update"}

# How long the player dwells on a frame at 1x, in milliseconds. Text frames
# scale with length so a line can be read.
DWELL = {
    "agent_speech": (2600, 42, 9500), "round_narration": (3200, 38, 12000), "everyone_thinks": (3500, 22, 16000),
    "move": (950, 0, 0), "step": (900, 0, 0), "monster_step": (1000, 0, 0), "agent_force_moved": (1400, 0, 0),
    "attack_hit": (1500, 0, 0), "attack_miss": (1300, 0, 0), "wild_swing_self_damage": (1500, 0, 0),
    "wild_swing_bystander": (1600, 0, 0), "wild_swing_room_reaction": (1600, 0, 0), "hazard_burn": (1300, 0, 0),
    "agent_eliminated": (2200, 0, 0), "monster_defeated": (2000, 0, 0),
    "round_started": (1300, 0, 0), "act_started": (2600, 0, 0), "initiative_order": (1800, 0, 0), "match_started": (2600, 0, 0),
    "crown_unlocked": (2200, 0, 0), "crown_taken": (2000, 0, 0), "crown_dropped": (2000, 0, 0), "crown_attuned": (1500, 0, 0),
    "crown_extracted": (3200, 0, 0), "seal_activated": (1800, 0, 0), "cache_found": (1800, 0, 0), "vault_gate_opened": (2400, 0, 0),
    "room_contracting": (1800, 0, 0), "room_sealing": (1600, 0, 0), "room_sealed": (1800, 0, 0),
    "final_scores": (4500, 0, 0), "objective_reveal": (1600, 0, 0), "act_two_survival": (2000, 0, 0),
}
DEFAULT_DWELL = (1200, 0, 0)

# Where each room sits on the board, in tiles. Doors line up: the vault's
# egress door (3,0) under the egress door (1,1); the vault's gate doors (0,4)
# and (6,4) above the gates' vault doors (2,0); the gates' threshold doors
# (2,3) above the threshold's gate doors (0,1) and (4,1), joined by corridors.
LAYOUT = {
    "egress": (7.5, 0.0),
    "vault": (5.5, 3.0),
    "ironwood_gate": (3.5, 9.0),
    "ossuary_gate": (9.5, 9.0),
    "threshold": (6.5, 14.5),
}
TILE = 44
MARGIN = 26

TOKEN_COLOURS = ["#e0b48a", "#f0ede8", "#4fd1c5", "#ffd166", "#ff8fa3", "#c48cff", "#5fb3ff", "#b5e07a"]
MONSTER_LABELS = {"ironwood_guardian": "IG", "ossuary_guardian": "OG", "crown_warden": "W"}


def dwell_for(kind: str, text: str = "") -> int:
    base, per_char, cap = DWELL.get(kind, DEFAULT_DWELL)
    return min(cap, base + per_char * len(text)) if per_char else base


# ---------------------------------------------------------------------------
# the timeline: state changes per event, derived from the bundle
# ---------------------------------------------------------------------------

def initial_state(bundle: dict) -> dict:
    """The board before round 1, from the referee's first snapshot, plus the
    secret aim each character carries (from its manifest, worded by the
    engine's own scoring table)."""
    first = bundle["snapshots"][0]["state"]
    secrets = {p["manifest"]["id"]: p["manifest"].get("secret_objective") or "" for p in bundle.get("participants", [])}
    agents = {}
    for aid, a in first["agents"].items():
        secret = secrets.get(aid, "")
        agents[aid] = {"id": aid, "name": a["name"], "build": a.get("build", ""), "room": a["room"],
                       "tile": list(a["tile"]), "hp": a["hp"], "max_hp": a["max_hp"], "status": a["status"], "guard": 0,
                       "note": {"objective": "", "reads": []},
                       "secret": secret.replace("_", " "),
                       "secret_text": scoring.OBJECTIVE_DEFS[secret]["description"] if secret in scoring.OBJECTIVE_DEFS else "",
                       "secret_done": None}
    monsters = {}
    for mid, m in first["monsters"].items():
        monsters[mid] = {"id": mid, "name": m["name"], "room": m["room"], "tile": list(m["tile"]),
                         "hp": m["hp"], "max_hp": m["max_hp"]}
    crown = first.get("crown") or {}
    return {
        "agents": agents, "monsters": monsters,
        "crown": {"status": crown.get("status", "locked"), "carrier": crown.get("carrier_id"),
                  "room": crown.get("room") or "vault", "tile": list(grid.feature_tile("vault", "pedestal") or (3, 2)),
                  "attunement": crown.get("attunement_rounds", 0)},
        "seals": dict(first.get("seals") or {}),
        "sealed": list((first.get("contraction") or {}).get("sealed") or []),
        "contracting": list((first.get("contraction") or {}).get("contracting") or []),
        "caches": {room: bool(c.get("found")) for room, c in (first.get("caches") or {}).items()},
        "vault_open": False,
    }


def _hp_owner(state: dict, ev: dict) -> str | None:
    """Whose HP a ``changes.hp`` belongs to: the target when there is one, else
    the actor. Matches the engine: a hit names its victim as target; a burn,
    a rest, a tonic and a self-inflicted swing name only the actor."""
    for who in (ev.get("target_id"), ev.get("actor_id")):
        if who and (who in state["agents"] or who in state["monsters"]):
            return who
    return None


def _place(state: dict, aid: str, room: str, origin: str) -> list[int]:
    """The engine's own arrival rule: the doorway you came through, or the
    nearest free tile to it."""
    door = grid.door_tile(room, origin) or grid.spawn_tile(room, 0)
    return list(grid.free_tile_near(state, room, door, mover_id=aid))


def apply_event(state: dict, ev: dict) -> dict:
    """Mutate ``state`` for one event and return the delta the page applies.
    The delta names only what changed; the page keeps its own copy of the
    state and folds deltas in, so scrubbing is a replay of deltas."""
    t = ev["event_type"]
    p = ev.get("payload") or {}
    ch = p.get("changes") or {}
    d: dict = {}
    agents, monsters = state["agents"], state["monsters"]

    def agent_delta(aid: str, **fields):
        agents[aid].update(fields)
        d.setdefault("agents", {}).setdefault(aid, {}).update(fields)

    def monster_delta(mid: str, **fields):
        monsters[mid].update(fields)
        d.setdefault("monsters", {}).setdefault(mid, {}).update(fields)

    if t in ("move", "agent_force_moved"):
        aid = ev["actor_id"]
        before, after = ch.get("room") or (agents[aid]["room"], p.get("to"))
        tile = _place(state, aid, after, before)
        agent_delta(aid, room=after, tile=tile)
    elif t == "step":
        aid = ev["actor_id"]
        agent_delta(aid, tile=list(ch["tile"][1]))
    elif t == "monster_step":
        monster_delta(ev["actor_id"], tile=list(ch["tile"][1]))
    elif t == "crown_extracted":
        aid = ev["actor_id"]
        before = agents[aid]["room"]
        agent_delta(aid, room="egress", status="escaped")
        agent_delta(aid, tile=_place(state, aid, "egress", before))
        state["crown"].update({"status": "escaped", "carrier": aid, "room": "egress"})
        d["crown"] = dict(state["crown"])
    elif t == "agent_eliminated":
        aid = ev["target_id"] if ev.get("target_id") in agents else ev["actor_id"]
        agent_delta(aid, status="eliminated")
    elif t == "monster_defeated":
        mid = p.get("monster_id") or ev.get("target_id")
        if mid in monsters:
            monster_delta(mid, hp=0)
    elif t == "guard":
        agent_delta(ev["actor_id"], guard=int((ch.get("guard") or [0, 0])[1]))
    elif t == "note_written":
        note = p.get("note") or {}
        names = {a["id"]: a["name"] for a in agents.values()}
        agent_delta(ev["actor_id"], note={
            "objective": note.get("objective") or "",
            "reads": [{"who": names.get(r.get("who"), r.get("who") or ""), "stance": r.get("stance") or "unknown", "why": r.get("why") or ""}
                      for r in (note.get("reads") or [])]})
    elif t == "objective_reveal":
        agent_delta(ev["actor_id"], secret_done=bool(p.get("completed")))
    elif t == "round_started":
        for aid, a in agents.items():
            if a.get("guard"):
                agent_delta(aid, guard=0)
    elif t == "crown_unlocked":
        state["crown"].update({"status": "floor", "carrier": None, "room": p.get("room") or "vault",
                               "tile": list(grid.feature_tile("vault", "pedestal") or (3, 2))})
        d["crown"] = dict(state["crown"])
    elif t == "crown_taken":
        aid = p.get("agent_id") or ev["actor_id"]
        state["crown"].update({"status": "carried", "carrier": aid, "room": agents[aid]["room"],
                               "tile": list(agents[aid]["tile"]), "attunement": 0})
        d["crown"] = dict(state["crown"])
    elif t == "crown_dropped":
        prev = p.get("previous_carrier") or state["crown"].get("carrier")
        where = agents[prev] if prev in agents else None
        state["crown"].update({"status": "floor", "carrier": None,
                               "room": p.get("room") or (where["room"] if where else state["crown"]["room"]),
                               "tile": list(where["tile"]) if where else state["crown"]["tile"], "attunement": 0})
        d["crown"] = dict(state["crown"])
    elif t == "crown_attuned":
        state["crown"]["attunement"] = int(p.get("attunement_rounds") or 0)
        d["crown"] = dict(state["crown"])
    elif t == "seal_activated":
        room = p.get("room")
        if room:
            state["seals"][room] = "active"
            d["seals"] = dict(state["seals"])
    elif t == "cache_found":
        for key in ch:
            if key.startswith("caches.") and key.endswith(".found"):
                room = key.split(".")[1]
                state["caches"][room] = True
                d["caches"] = dict(state["caches"])
    elif t == "vault_gate_opened":
        state["vault_open"] = True
        d["vault_open"] = True
    elif t == "room_contracting":
        room = p.get("room")
        if room and room not in state["contracting"]:
            state["contracting"].append(room)
            d["contracting"] = list(state["contracting"])
    elif t == "room_sealed":
        room = p.get("room")
        if room:
            if room not in state["sealed"]:
                state["sealed"].append(room)
            state["contracting"] = [r for r in state["contracting"] if r != room]
            d["sealed"] = list(state["sealed"])
            d["contracting"] = list(state["contracting"])
            for mid in p.get("monsters_entombed") or []:
                if mid in monsters:
                    monster_delta(mid, hp=0)

    # any HP change rides on whichever body the event names
    if "hp" in ch:
        who = _hp_owner(state, ev)
        if who in agents:
            agent_delta(who, hp=int(ch["hp"][1]))
        elif who in monsters:
            monster_delta(who, hp=int(ch["hp"][1]))
    return d


def _merge(into: dict, delta: dict) -> None:
    for aid, fields in (delta.get("agents") or {}).items():
        into.setdefault("agents", {}).setdefault(aid, {}).update(fields)
    for mid, fields in (delta.get("monsters") or {}).items():
        into.setdefault("monsters", {}).setdefault(mid, {}).update(fields)
    for key, val in delta.items():
        if key not in ("agents", "monsters"):
            into[key] = val


def build_timeline(bundle: dict) -> tuple[dict, list[dict]]:
    """Initial state plus one frame per watched moment, in seq order.

    A round's private notes are logged one per character as each decision
    returns, interleaved with the lines spoken; the engine collected them all
    in one decision phase before anything resolved. They become ONE
    ``everyone_thinks`` frame at the first note's position, carrying every
    plan of the round, and the individual note events fold into it."""
    state = initial_state(bundle)
    start = copy.deepcopy(state)
    frames = []
    names = {**{a["id"]: a["name"] for a in state["agents"].values()},
             **{m["id"]: m["name"] for m in state["monsters"].values()}}
    events = sorted(bundle["events"], key=lambda e: e["seq"])
    notes_by_round: dict[int, list[dict]] = {}
    for ev in events:
        if ev["event_type"] == "note_written":
            notes_by_round.setdefault(ev["round_no"], []).append(ev)
    thought_rounds: set[int] = set()
    for ev in events:
        t = ev["event_type"]
        if t in SKIP:
            continue
        if t == "item_taken" and ev.get("target_id") == "ember_crown":
            continue  # the crown_taken event that follows says the same thing
        p = ev.get("payload") or {}
        if t == "note_written":
            rnd = ev["round_no"]
            if rnd in thought_rounds:
                continue
            thought_rounds.add(rnd)
            delta: dict = {}
            thoughts = []
            for n in notes_by_round[rnd]:
                _merge(delta, apply_event(state, n))
                a = state["agents"][n["actor_id"]]
                thoughts.append({"who": n["actor_id"], "name": a["name"], "objective": a["note"]["objective"], "reads": a["note"]["reads"]})
            frames.append({
                "seq": ev["seq"], "round": rnd, "type": "everyone_thinks", "actor": None, "target": None,
                "text": "Everyone writes their plan for the round at the same time, before anyone moves.",
                "thoughts": thoughts, "dwell": dwell_for("everyone_thinks", "".join(x["objective"] for x in thoughts)),
                "delta": delta, "room": None,
            })
            continue
        frame = {
            "seq": ev["seq"], "round": ev["round_no"], "type": t,
            "actor": ev.get("actor_id"), "target": ev.get("target_id"),
            "text": ev.get("public_text") or "",
        }
        if t == "agent_speech":
            frame["speech"] = p.get("speech") or ""
            frame["mode"] = p.get("mode") or "say"
            to = p.get("addressed_ids") or ([p["to"]] if p.get("to") else [])
            frame["to"] = [names.get(x, x) for x in to]
        if t in ("attack_hit", "wild_swing_bystander", "wild_swing_self_damage", "hazard_burn", "wild_swing_room_reaction"):
            frame["amount"] = int(p.get("applied") or p.get("amount") or 0)
        if t in ("rest", "item_used") and "hp" in (p.get("changes") or {}):
            frame["amount"] = int(p["changes"]["hp"][1]) - int(p["changes"]["hp"][0])
        if t == "final_scores":
            frame["placements"] = p.get("placements") or {}
            frame["scores"] = p.get("scores") or {}
        if t == "round_narration":
            frame["narration"] = True
        if t == "stale_action":
            frame["text"] = frame["text"] + " " + ((p.get("reason") or "").capitalize() + "." if p.get("reason") else "")
        frame["dwell"] = dwell_for(t, frame.get("speech") or frame["text"])
        frame["delta"] = apply_event(state, ev)
        who = ev.get("actor_id") or ev.get("target_id")
        body = state["agents"].get(who) or state["monsters"].get(who)
        frame["room"] = body["room"] if body else (p.get("room") if p.get("room") in grid.ROOM_GRIDS else None)
        frames.append(frame)
    return start, frames


# Frames that are the actor's own doing, for the followed character's card.
DID = {"move", "step", "attack_hit", "attack_miss", "wild_swing_self_damage", "wild_swing_bystander", "wild_swing_room_reaction",
       "guard", "rest", "search_failure", "cache_found", "seal_activated", "stale_action", "item_used", "item_taken", "give",
       "crown_taken", "crown_extracted", "action_skipped", "invalid_action", "interact", "search_success"}
# Frames that land on a character from outside: another body's swing, the
# floor, the referee sweeping a room, the Crown leaving their hands.
HAPPENED = {"attack_hit", "attack_miss", "wild_swing_bystander", "hazard_burn", "agent_eliminated", "agent_force_moved",
            "crown_dropped", "monster_step"}


def build_turns(start: dict, frames: list[dict]) -> dict[str, list[dict]]:
    """One card per character per round: thought, said, did, happened to them,
    and the frame the board should stand at when the card shows (the round's
    last frame). Built by folding the same deltas the page folds, so the HP
    on the card is the HP the referee recorded (verify() checks that).

    The firm, 14 Sep 2026: "I want to see one character's words, thoughts,
    and action. It is too much to take in at once when seeing all 8
    thoughts. Additionally it's easier to detect when they're lying"."""
    state = copy.deepcopy(start)
    rounds = sorted({f["round"] for f in frames if f["round"] >= 1})
    by_round: dict[int, list[tuple[int, dict]]] = {}
    for i, f in enumerate(frames):
        by_round.setdefault(f["round"], []).append((i, f))
    turns: dict[str, list[dict]] = {aid: [] for aid in start["agents"]}
    hp_before = {aid: a["hp"] for aid, a in start["agents"].items()}
    status_before = {aid: a["status"] for aid, a in start["agents"].items()}
    for i, f in by_round.get(0, []):
        _fold(state, f["delta"])
    for rnd in rounds:
        items = by_round.get(rnd, [])
        cards = {aid: {"round": rnd, "who": aid, "thought": "", "reads": [], "said": None, "mode": None, "to": [],
                       "did": [], "happened": [], "narration": "", "end": items[-1][0] if items else 0,
                       "hp_before": hp_before[aid], "out_before": status_before[aid] != "active"}
                 for aid in start["agents"]}
        for i, f in items:
            t = f["type"]
            if t == "everyone_thinks":
                for th in f["thoughts"]:
                    cards[th["who"]]["thought"] = th["objective"]
                    cards[th["who"]]["reads"] = th["reads"]
            elif t == "agent_speech" and f["actor"] in cards:
                c = cards[f["actor"]]
                c["said"], c["mode"], c["to"] = f["speech"], f["mode"], f.get("to") or []
            elif t == "round_narration":
                for c in cards.values():
                    c["narration"] = f["text"]
            else:
                actor, target = f.get("actor"), f.get("target")
                if actor in cards and t in DID:
                    cards[actor]["did"].append(f["text"])
                if t in HAPPENED:
                    victim = target if target in cards else (actor if actor in cards and t in ("hazard_burn", "agent_force_moved") else None)
                    if t == "crown_dropped" and actor in cards:
                        victim = actor
                    if t == "agent_eliminated" and target in cards:
                        victim = target
                    if victim and not (t == "attack_hit" and actor == victim) and not (victim == actor and t in ("attack_miss",)):
                        cards[victim]["happened"].append(f["text"])
            _fold(state, f["delta"])
        for aid, c in cards.items():
            a = state["agents"][aid]
            c["hp_after"], c["status_after"], c["room_after"] = a["hp"], a["status"], a["room"]
            hp_before[aid], status_before[aid] = a["hp"], a["status"]
            text = c["thought"] + (c["said"] or "") + " ".join(c["did"]) + " ".join(c["happened"])
            c["dwell"] = min(18000, 3000 + 30 * len(text))
            turns[aid].append(c)
    return turns


def verify(bundle: dict, start: dict, frames: list[dict]) -> list[str]:
    """Replay the deltas and compare with every round-end snapshot the
    referee wrote. Returns the mismatches; empty means the board is the
    referee's board."""
    state = copy.deepcopy(start)
    by_round_end = {s["round_no"]: s["state"] for s in bundle["snapshots"] if s["phase"] == "end"}
    problems: list[str] = []
    i = 0
    for rnd in sorted(by_round_end):
        for f in frames:
            if f["round"] <= rnd and f["seq"] > i:
                _fold(state, f["delta"])
                i = f["seq"]
        snap = by_round_end[rnd]
        for aid, a in snap["agents"].items():
            mine = state["agents"][aid]
            for key in ("room", "hp", "status"):
                if mine[key] != a[key]:
                    problems.append(f"round {rnd} {aid} {key}: board {mine[key]!r} referee {a[key]!r}")
            if a["status"] == "active" and list(mine["tile"]) != list(a["tile"]):
                problems.append(f"round {rnd} {aid} tile: board {mine['tile']} referee {a['tile']}")
        for mid, m in snap["monsters"].items():
            mine = state["monsters"][mid]
            if mine["hp"] != m["hp"]:
                problems.append(f"round {rnd} {mid} hp: board {mine['hp']} referee {m['hp']}")
            if m["hp"] > 0 and list(mine["tile"]) != list(m["tile"]):
                problems.append(f"round {rnd} {mid} tile: board {mine['tile']} referee {m['tile']}")
        crown = snap.get("crown") or {}
        if crown.get("carrier_id") != state["crown"]["carrier"]:
            problems.append(f"round {rnd} crown carrier: board {state['crown']['carrier']!r} referee {crown.get('carrier_id')!r}")
    return problems


def _fold(state: dict, delta: dict) -> None:
    for aid, fields in (delta.get("agents") or {}).items():
        state["agents"][aid].update(fields)
    for mid, fields in (delta.get("monsters") or {}).items():
        state["monsters"][mid].update(fields)
    if "crown" in delta:
        state["crown"].update(delta["crown"])
    for key in ("seals", "caches"):
        if key in delta:
            state[key].update(delta[key])
    for key in ("sealed", "contracting", "vault_open"):
        if key in delta:
            state[key] = delta[key]


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------

def board_geometry() -> dict:
    """Rooms, tiles, props, doors and corridors in board pixels."""
    rooms = {}
    for rid, (tx, ty) in LAYOUT.items():
        g = grid.ROOM_GRIDS[rid]
        rooms[rid] = {"x": MARGIN + tx * TILE, "y": MARGIN + ty * TILE, "w": g["w"] * TILE, "h": g["h"] * TILE,
                      "cols": g["w"], "rows": g["h"],
                      "doors": {to: list(t) for to, t in g["doors"].items()},
                      "features": {k: list(t) for k, t in g["features"].items()},
                      "props": {k: dict(v) for k, v in grid.props_for(rid).items()}}
    width = MARGIN * 2 + TILE * max(tx + grid.ROOM_GRIDS[r]["w"] for r, (tx, _) in LAYOUT.items())
    height = MARGIN * 2 + TILE * max(ty + grid.ROOM_GRIDS[r]["h"] for r, (_, ty) in LAYOUT.items())
    corridors = []
    seen = set()
    for rid, room in rooms.items():
        for to, tile in room["doors"].items():
            if to not in rooms or (to, rid) in seen:
                continue
            seen.add((rid, to))
            back = rooms[to]["doors"].get(rid)
            if not back:
                continue
            a = (room["x"] + (tile[0] + .5) * TILE, room["y"] + (tile[1] + .5) * TILE)
            b = (rooms[to]["x"] + (back[0] + .5) * TILE, rooms[to]["y"] + (back[1] + .5) * TILE)
            corridors.append({"from": rid, "to": to, "a": a, "b": b})
    return {"tile": TILE, "width": width, "height": height, "rooms": rooms, "corridors": corridors}


CSS = """
  :root {
    --ground: #15110f; --panel: #201916; --panel-2: #2a211c; --line: #3d3029; --line-2: #55443a;
    --ink: #efe4d6; --muted: #a8968a; --faint: #6f6058; --thought: #d9cbb9;
    --ember: #e8632a; --ember-soft: rgba(232, 99, 42, .18); --gold: #e9b44c; --moon: #9fc4d8;
    --blood: #c0392b; --heal: #6fae6a;
    --display: "Cinzel", "Times New Roman", serif; --sans: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
    --serif: "IBM Plex Serif", Georgia, serif;
  }
  html { color-scheme: dark; }
  body { margin: 0; background: var(--ground); color: var(--ink); font: 400 1rem/1.5 var(--sans); padding: .8rem 1rem 2rem; }
  .page { max-width: 1240px; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 0 1.2rem; }
  header.top { display: flex; flex-wrap: wrap; align-items: baseline; gap: .3rem 1.2rem; margin-bottom: .6rem; grid-column: 1 / -1; }
  h1 { font: 700 1.25rem/1.2 var(--display); letter-spacing: .04em; margin: 0; color: var(--ink); }
  .sub { color: var(--muted); font-size: .88rem; margin: 0; }
  .main, .side { min-width: 0; }
  @media (min-width: 960px) {
    .page { grid-template-columns: minmax(0, 1fr) minmax(360px, 1.05fr); }
    .side { position: sticky; top: .6rem; align-self: start; }
    svg.board { max-height: calc(100vh - 12rem); }
  }
  .board-wrap { position: relative; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  svg.board { display: block; width: 100%; height: auto; margin: 0 auto; }
  .room-floor { fill: #2a211c; stroke: var(--line-2); stroke-width: 1.5; }
  .room-floor.sealed { fill: #1a1512; stroke: #2c2420; }
  .room-floor.contracting { stroke: var(--ember); stroke-dasharray: 6 4; animation: pulse 1.4s ease-in-out infinite; }
  .room-name { font: 600 .74rem var(--display); letter-spacing: .08em; text-transform: uppercase; fill: var(--muted); }
  .room-name.sealed { fill: var(--faint); }
  .tile { fill: none; stroke: #352a24; stroke-width: 1; }
  .blocking { fill: #120e0c; stroke: #3d3029; }
  .cover { fill: url(#hatch); stroke: #55443a; }
  .hazard { fill: var(--ember-soft); stroke: rgba(232,99,42,.45); }
  .door { fill: none; stroke: var(--muted); stroke-width: 2; }
  .door.open { stroke: var(--gold); }
  .corridor { stroke: #4a3b32; stroke-width: 10; stroke-linecap: round; fill: none; }
  .corridor.cut { stroke: #221b17; }
  .feature { font: 600 .62rem var(--sans); fill: var(--muted); text-anchor: middle; }
  .seal-mark { fill: none; stroke: var(--faint); stroke-width: 2; }
  .seal-mark.active { stroke: var(--gold); filter: drop-shadow(0 0 4px var(--gold)); }
  .cache-mark { fill: #6f6058; }
  .cache-mark.found { fill: #3d3029; }
  .pedestal { fill: none; stroke: var(--faint); stroke-width: 1.5; stroke-dasharray: 3 3; }
  .token { transition: transform .45s cubic-bezier(.2,.7,.2,1); }
  .token circle.body { stroke: #0e0b0a; stroke-width: 2; }
  .token text.ini { font: 700 .72rem var(--sans); fill: #14100d; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
  .token .hpbg { fill: #0e0b0a; }
  .token .hp { fill: var(--heal); transition: width .3s; }
  .token .hp.low { fill: var(--gold); }
  .token .hp.crit { fill: var(--blood); }
  .token.out circle.body { fill: #3d3029 !important; stroke: #2c2420; }
  .token.out text.ini { fill: #7a6a60; }
  .token.out .hpbar { display: none; }
  .token.escaped circle.body { stroke: var(--moon); filter: drop-shadow(0 0 6px var(--moon)); }
  .token.speaking circle.body { stroke: #fff; filter: drop-shadow(0 0 5px rgba(255,255,255,.7)); }
  .token.acting circle.body { stroke: var(--ink); }
  .token.thinking circle.body { stroke: var(--thought); stroke-dasharray: 3 2; }
  .token .guard { fill: none; stroke: var(--moon); stroke-width: 2; stroke-dasharray: 4 3; }
  .monster circle.body { fill: var(--blood); stroke: #4a0f0c; stroke-width: 2; }
  .monster text.ini { fill: #fbe9e6; }
  .monster.dead { opacity: .18; }
  .crown { transition: transform .45s cubic-bezier(.2,.7,.2,1); }
  .crown path { fill: var(--gold); stroke: #6b4c0a; stroke-width: .8; filter: drop-shadow(0 0 4px rgba(233,180,76,.8)); }
  .crown text { font: 700 .58rem var(--sans); fill: #14100d; text-anchor: middle; }
  .crown.hidden { display: none; }
  .fx { pointer-events: none; }
  .fx text { font: 700 .95rem var(--sans); text-anchor: middle; animation: rise 1.3s ease-out forwards; }
  .fx text.dmg { fill: #ff7b6b; }
  .fx text.heal { fill: var(--heal); }
  .fx text.miss { fill: var(--muted); font-weight: 500; }
  .fx circle.ring { fill: none; stroke: #ff7b6b; stroke-width: 2; animation: ring .8s ease-out forwards; }
  .fx line.swing { stroke: #ffb59f; stroke-width: 2.5; stroke-linecap: round; animation: fade 1s ease-out forwards; }
  .bubble { position: absolute; max-width: 240px; background: #f4ece0; color: #1a1411; border-radius: 10px; padding: .45rem .65rem; font-size: .86rem; line-height: 1.3;
            transform: translate(-50%, calc(-100% - 22px)); box-shadow: 0 6px 18px rgba(0,0,0,.5); pointer-events: none; }
  .bubble::after { content: ""; position: absolute; left: 50%; bottom: -8px; margin-left: -8px; border: 8px solid transparent; border-top-color: #f4ece0; border-bottom: 0; }
  .bubble.whisper { background: #d9d3e6; font-style: italic; }
  .bubble.whisper::after { border-top-color: #d9d3e6; }
  .bubble.below { transform: translate(-50%, 22px); }
  .bubble.below::after { top: -8px; bottom: auto; border: 8px solid transparent; border-bottom-color: #f4ece0; border-top: 0; }
  .bubble.below.whisper::after { border-bottom-color: #d9d3e6; }
  /* anchored from the right when the speaker stands in the right half, so the
     bubble has room to be as wide as its text instead of shrinking to the edge */
  .bubble.rt { transform: translate(50%, calc(-100% - 22px)); }
  .bubble.rt.below { transform: translate(50%, 22px); }
  .bubble[hidden] { display: none; }
  /* the eight, compact, under the board: HP at a glance, nothing to read */
  .roster { margin-top: .5rem; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .3rem; }
  .card { display: grid; grid-template-columns: 14px 1fr auto; gap: .1rem .4rem; align-items: center; background: var(--panel); border: 1px solid var(--line); border-radius: 5px; padding: .3rem .45rem; font-size: .76rem; }
  .card .dot { width: 12px; height: 12px; border-radius: 50%; border: 1px solid #0e0b0a; }
  .card .name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card .num { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .72rem; }
  .card .bar { grid-column: 1 / 4; height: 4px; background: #0e0b0a; border-radius: 3px; overflow: hidden; }
  .card .bar i { display: block; height: 100%; background: var(--heal); transition: width .3s; }
  .card .bar i.low { background: var(--gold); } .card .bar i.crit { background: var(--blood); }
  .card.out { opacity: .45; } .card.out .name::after { content: " · out"; color: var(--muted); font-weight: 400; }
  .card.escaped .name::after { content: " · escaped"; color: var(--moon); font-weight: 400; }
  .card.crown .name::before { content: "♛ "; color: var(--gold); }
  .legend { margin-top: .5rem; display: flex; flex-wrap: wrap; gap: .3rem .9rem; font-size: .74rem; color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: .3rem; }
  .legend i { display: inline-block; width: 12px; height: 12px; border: 1px solid #55443a; }
  .legend i.b { background: #120e0c; } .legend i.c { background: repeating-linear-gradient(45deg, #2a211c 0 3px, #55443a 3px 4px); }
  .legend i.h { background: var(--ember-soft); border-color: rgba(232,99,42,.6); } .legend i.d { border: 0; border-top: 2px solid var(--muted); height: 0; margin-top: 6px; }
  .legend i.m { background: var(--blood); border-color: #4a0f0c; border-radius: 50%; }
  /* the panel: one round, one sequence, one place */
  .round-bar { display: flex; align-items: baseline; justify-content: space-between; gap: .8rem; font-family: var(--display); letter-spacing: .06em; font-size: .9rem; color: var(--gold); margin-bottom: .45rem; }
  .round-bar .n { color: var(--muted); font: 500 .78rem var(--sans); letter-spacing: 0; font-variant-numeric: tabular-nums; }
  .stage { background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--line-2); border-radius: 6px; padding: .8rem 1rem .85rem; min-height: 9rem; display: grid; gap: .4rem; }
  .stage.speech { border-left-color: var(--ink); }
  .stage.narration { border-left-color: var(--ember); }
  .stage.blow { border-left-color: var(--blood); }
  .stage.crown { border-left-color: var(--gold); }
  .stage.thinks { border-left: 4px dashed var(--thought); }
  .who { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem; font-size: .8rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
  .who .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--faint); border: 1px solid #0e0b0a; flex: none; }
  .who .dot.monster { background: var(--blood); border-color: #4a0f0c; }
  .who b { color: var(--ink); letter-spacing: .02em; text-transform: none; font-size: .98rem; }
  .who .phase { margin-left: auto; color: var(--faint); font-size: .72rem; }
  .what { font-size: 1.1rem; line-height: 1.45; margin: 0; max-width: 70ch; }
  .stage.speech .what { font-size: 1.22rem; }
  .stage.narration .what { font-family: var(--serif); font-style: italic; color: #e4d6c4; }
  .goal { margin: 0; padding: .5rem .7rem; background: #1b1613; border: 1px dashed var(--line-2); border-radius: 4px; font-size: .86rem; line-height: 1.4; color: var(--thought); display: grid; gap: .15rem; }
  .goal .lbl { font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; color: var(--faint); }
  .goal .plan { font-style: italic; }
  .goal .plan:empty::before { content: "no plan written yet this round"; color: var(--faint); font-style: normal; }
  .goal .reads { color: var(--muted); font-size: .8rem; }
  .goal .reads:empty { display: none; }
  .goal .secret { color: var(--muted); font-size: .8rem; }
  .goal .secret b { color: var(--gold); font-weight: 500; }
  .goal .secret .done { color: var(--heal); } .goal .secret .failed { color: var(--muted); }
  .goal[hidden] { display: none; }
  .thoughts { list-style: none; margin: 0; padding: 0; display: grid; gap: .3rem; }
  .thoughts li { display: grid; grid-template-columns: 12px 1fr; gap: .15rem .5rem; align-items: baseline; font-size: .86rem; line-height: 1.35; }
  .thoughts .dot { width: 12px; height: 12px; border-radius: 50%; border: 1px solid #0e0b0a; position: relative; top: 1px; }
  .thoughts b { font-weight: 600; color: var(--ink); }
  .thoughts .plan { font-style: italic; color: var(--thought); }
  .thoughts .plan:empty::before { content: "wrote no plan"; color: var(--faint); font-style: normal; }
  .thoughts .reads { grid-column: 2; color: var(--muted); font-size: .76rem; }
  .thoughts .reads:empty { display: none; }
  .thoughts[hidden] { display: none; }
  .meta { font-size: .76rem; color: var(--faint); }
  /* follow one character */
  .follow { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; margin-bottom: .55rem; }
  .follow .lbl { font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; color: var(--faint); margin-right: .2rem; }
  .chip { display: inline-flex; align-items: center; gap: .35rem; font: 500 .8rem var(--sans); color: var(--ink); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 999px; padding: .28rem .7rem; cursor: pointer; }
  .chip .dot { width: 10px; height: 10px; border-radius: 50%; border: 1px solid #0e0b0a; }
  .chip:hover { border-color: var(--muted); }
  .chip[aria-pressed="true"] { background: var(--ink); color: #1a0e08; border-color: var(--ink); }
  .chip:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  .stage.turnview { border-left-color: var(--ink); }
  .turn { display: grid; gap: .55rem; }
  .turn[hidden] { display: none; }
  .turn .row { display: grid; grid-template-columns: 7.2rem 1fr; gap: .6rem; align-items: baseline; }
  .turn .row .lbl { font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; color: var(--faint); padding-top: .2rem; }
  .turn .val { font-size: .98rem; line-height: 1.45; min-width: 0; }
  .turn .val.said { font-size: 1.12rem; }
  .turn .thought { font-style: italic; color: var(--thought); display: block; }
  .turn .thought:empty::before { content: "wrote no plan"; color: var(--faint); font-style: normal; }
  .turn .reads { display: block; color: var(--muted); font-size: .8rem; }
  .turn .reads:empty { display: none; }
  .turn .val.said .none, .turn .val .none { color: var(--faint); font-style: italic; }
  .turn .val.said .to { color: var(--muted); font-size: .8rem; font-style: italic; display: block; }
  .turn .val.narr { font-family: var(--serif); font-style: italic; color: #cbbba8; font-size: .9rem; }
  .turn .narr-fold { margin: 0; } .turn .narr-fold[hidden] { display: none; }
  .turn .narr-fold summary { cursor: pointer; font-size: .74rem; letter-spacing: .06em; text-transform: uppercase; color: var(--faint); }
  .turn .narr-fold summary::marker { color: var(--ember); }
  .turn .narr-fold .val { margin-top: .35rem; }
  .turn .secret { color: var(--muted); font-size: .8rem; border-top: 1px dashed var(--line); padding-top: .45rem; }
  .turn .secret b { color: var(--gold); font-weight: 500; }
  .turn .secret .done { color: var(--heal); } .turn .secret .failed { color: var(--muted); }
  .turn .val ul { margin: 0; padding-left: 1.1rem; } .turn .val li { margin: .1rem 0; }
  .hpline { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .8rem; margin-left: auto; }
  .hpline b { color: var(--ink); font-weight: 600; }
  .hpline .down { color: #ff7b6b; } .hpline .up { color: var(--heal); }
  body.following #prevr, body.following #nextr { display: none; }
  @media (max-width: 560px) { .turn .row { grid-template-columns: 1fr; gap: .1rem; } }
  .transport { margin-top: .7rem; display: flex; flex-wrap: wrap; align-items: center; gap: .5rem .7rem; }
  .transport button { font: 600 .88rem var(--sans); color: var(--ink); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 6px; padding: .45rem .75rem; cursor: pointer; min-width: 2.6rem; }
  .transport button:hover { border-color: var(--muted); }
  .transport button.play { background: var(--ember); border-color: var(--ember); color: #1a0e08; min-width: 6rem; font-size: 1rem; }
  .transport button:focus-visible, .transport select:focus-visible, .transport input:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  .transport select { font: 500 .88rem var(--sans); color: var(--ink); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 6px; padding: .4rem .5rem; }
  .transport label { font-size: .82rem; color: var(--muted); display: inline-flex; align-items: center; gap: .4rem; }
  .scrub { display: grid; grid-template-columns: auto 1fr auto; gap: .7rem; align-items: center; margin-top: .55rem; font-variant-numeric: tabular-nums; }
  .scrub input[type=range] { width: 100%; accent-color: var(--ember); }
  .scrub .lbl { font-size: .8rem; color: var(--muted); white-space: nowrap; }
  .final { margin-top: .8rem; background: var(--panel); border: 1px solid var(--gold); border-radius: 6px; padding: .8rem 1rem; }
  .final[hidden] { display: none; }
  .final h2 { font: 700 .95rem var(--display); letter-spacing: .06em; margin: 0 0 .4rem; color: var(--gold); }
  .final table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .86rem; }
  .final td, .final th { text-align: left; padding: .2rem .5rem .2rem 0; border-bottom: 1px solid var(--line); }
  .final th { color: var(--muted); font-weight: 500; font-size: .74rem; letter-spacing: .06em; text-transform: uppercase; }
  .final td.n { text-align: right; }
  .foot { margin-top: .9rem; color: var(--faint); font-size: .76rem; max-width: 70ch; }
  @keyframes rise { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-26px); } }
  @keyframes ring { from { r: 14; opacity: 1; } to { r: 30; opacity: 0; } }
  @keyframes fade { from { opacity: 1; } to { opacity: 0; } }
  @keyframes pulse { 0%, 100% { stroke-opacity: 1; } 50% { stroke-opacity: .35; } }
  @media (max-width: 560px) {
    body { padding-inline: .8rem; }
    .roster { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .what { font-size: 1rem; } .stage.speech .what { font-size: 1.08rem; }
    .bubble { max-width: 170px; font-size: .74rem; }
    .scrub { grid-template-columns: 1fr; gap: .3rem; }
    .transport button.play { min-width: 5rem; }
  }
  @media (prefers-reduced-motion: reduce) {
    .token, .crown, .token .hp, .card .bar i { transition: none; }
    .fx text, .fx circle.ring, .fx line.swing, .room-floor.contracting { animation: none; }
  }
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital@1&display=swap">')


def _crown_path() -> str:
    return "M-9 5 L-11 -5 L-5 0 L0 -8 L5 0 L11 -5 L9 5 Z"


def render_board_svg(geo: dict, start: dict) -> str:
    T = geo["tile"]
    out = [f'<svg class="board" viewBox="0 0 {geo["width"]:.0f} {geo["height"]:.0f}" role="img" aria-label="The Ember Vault, five rooms, with every character and monster on its tile">',
           '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<rect width="6" height="6" fill="#2a211c"/><line x1="0" y1="0" x2="0" y2="6" stroke="#55443a" stroke-width="2"/></pattern></defs>']
    for c in geo["corridors"]:
        (ax, ay), (bx, by) = c["a"], c["b"]
        midy = (ay + by) / 2
        out.append(f'<path class="corridor" data-from="{c["from"]}" data-to="{c["to"]}" d="M{ax:.1f} {ay:.1f} V{midy:.1f} H{bx:.1f} V{by:.1f}"/>')
    names = {"egress": "The Moonlit Egress", "vault": "The Ember Vault", "ironwood_gate": "The Ironwood Gate",
             "ossuary_gate": "The Ossuary Gate", "threshold": "The Threshold"}
    for rid, r in geo["rooms"].items():
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        out.append(f'<g class="room" data-room="{rid}">')
        out.append(f'<rect class="room-floor" id="floor-{rid}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4"/>')
        for cx in range(r["cols"]):
            for cy in range(r["rows"]):
                prop = r["props"].get(f"{cx},{cy}")
                cls = "tile" + (f" {prop['kind']}" if prop else "")
                title = f"<title>{E(prop['name'])}</title>" if prop else ""
                out.append(f'<rect class="{cls}" x="{x + cx * T + 1:.1f}" y="{y + cy * T + 1:.1f}" width="{T - 2}" height="{T - 2}">{title}</rect>')
        for to, (dx, dy) in r["doors"].items():
            px, py = x + (dx + .5) * T, y + (dy + .5) * T
            out.append(f'<circle class="door" id="door-{rid}-{to}" cx="{px:.1f}" cy="{py:.1f}" r="{T * .36:.1f}"><title>Door to {E(to.replace("_", " "))}</title></circle>')
        for feat, (fx, fy) in r["features"].items():
            px, py = x + (fx + .5) * T, y + (fy + .5) * T
            if feat == "seal":
                out.append(f'<circle class="seal-mark" id="seal-{rid}" cx="{px:.1f}" cy="{py:.1f}" r="{T * .3:.1f}"/>'
                           f'<text class="feature" x="{px:.1f}" y="{py + T * .5 + 9:.1f}">seal</text>')
            elif feat == "cache":
                out.append(f'<rect class="cache-mark" id="cache-{rid}" x="{px - 8:.1f}" y="{py - 6:.1f}" width="16" height="12" rx="2"/>'
                           f'<text class="feature" x="{px:.1f}" y="{py + T * .5 + 9:.1f}">cache</text>')
            elif feat == "pedestal":
                out.append(f'<circle class="pedestal" cx="{px:.1f}" cy="{py:.1f}" r="{T * .38:.1f}"/>')
        out.append(f'<text class="room-name" id="name-{rid}" x="{x + 6:.1f}" y="{y - 6:.1f}">{E(names[rid])}</text>')
        out.append('</g>')
    out.append('<g id="crown" class="crown hidden"><path d="' + _crown_path() + '"/><text id="crown-att" y="3"></text></g>')
    out.append('<g id="bodies">')
    for mid, m in start["monsters"].items():
        out.append(f'<g class="token monster" id="tok-{mid}" data-name="{E(m["name"])}">'
                   f'<circle class="body" r="14"/><text class="ini">{MONSTER_LABELS.get(mid, "M")}</text>'
                   f'<g class="hpbar"><rect class="hpbg" x="-14" y="17" width="28" height="4" rx="1"/><rect class="hp" x="-14" y="17" width="28" height="4" rx="1"/></g></g>')
    for i, (aid, a) in enumerate(start["agents"].items()):
        ini = "".join(w[0] for w in a["name"].split()[:2]) or aid[:2].title()
        out.append(f'<g class="token agent" id="tok-{aid}" data-name="{E(a["name"])}">'
                   f'<circle class="guard" r="19" style="display:none"/>'
                   f'<circle class="body" r="14" fill="{TOKEN_COLOURS[i % len(TOKEN_COLOURS)]}"/><text class="ini">{E(ini)}</text>'
                   f'<g class="hpbar"><rect class="hpbg" x="-14" y="17" width="28" height="4" rx="1"/><rect class="hp" x="-14" y="17" width="28" height="4" rx="1"/></g></g>')
    out.append('</g><g id="fx" class="fx"></g></svg>')
    return "\n".join(out)


SCRIPT = r"""
(function () {
  var D = window.__REPLAY__;
  var geo = D.geo, frames = D.frames, T = geo.tile, colours = D.colours;
  var state, idx = -1, playing = false, timer = null, speed = 1;
  var $ = function (s) { return document.querySelector(s); };
  var fx = $("#fx"), bubble = $("#bubble");
  var follow = "", turns = D.turns, ti = -1;   // follow: "" for everyone, else an agent id; ti: index into turns[follow]

  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function fold(s, d) {
    var k;
    for (k in (d.agents || {})) Object.assign(s.agents[k], d.agents[k]);
    for (k in (d.monsters || {})) Object.assign(s.monsters[k], d.monsters[k]);
    if (d.crown) Object.assign(s.crown, d.crown);
    if (d.seals) Object.assign(s.seals, d.seals);
    if (d.caches) Object.assign(s.caches, d.caches);
    if (d.sealed) s.sealed = d.sealed.slice();
    if (d.contracting) s.contracting = d.contracting.slice();
    if (d.vault_open) s.vault_open = true;
  }
  function px(room, tile) { var r = geo.rooms[room]; return [r.x + (tile[0] + .5) * T, r.y + (tile[1] + .5) * T]; }
  function hpClass(hp, max) { var f = hp / max; return f <= .25 ? "crit" : f <= .5 ? "low" : ""; }
  function roomName(r) { var n = document.getElementById("name-" + r); return n ? n.textContent : r; }
  function readsLine(reads) {
    if (!reads || !reads.length) return "";
    var by = { trust: [], distrust: [], unknown: [] };
    reads.forEach(function (r) { (by[r.stance] || by.unknown).push(r.who); });
    var parts = [];
    if (by.trust.length) parts.push("trusts " + by.trust.join(", "));
    if (by.distrust.length) parts.push("distrusts " + by.distrust.join(", "));
    if (by.unknown.length) parts.push("unsure of " + by.unknown.join(", "));
    return parts.join(" · ");
  }

  function render(frame) {
    var k, a, el, p;
    for (k in state.agents) {
      a = state.agents[k]; el = document.getElementById("tok-" + k);
      p = px(a.room, a.tile);
      el.style.transform = "translate(" + p[0] + "px," + p[1] + "px)";
      el.classList.toggle("out", a.status === "eliminated");
      el.classList.toggle("escaped", a.status === "escaped");
      el.querySelector(".guard").style.display = a.guard > 0 ? "" : "none";
      var bar = el.querySelector(".hp"); bar.setAttribute("width", Math.max(0, 28 * a.hp / a.max_hp)); bar.setAttribute("class", "hp " + hpClass(a.hp, a.max_hp));
      var card = document.getElementById("card-" + k);
      card.className = "card" + (a.status === "eliminated" ? " out" : "") + (a.status === "escaped" ? " escaped" : "") + (state.crown.carrier === k ? " crown" : "");
      card.querySelector(".num").textContent = a.hp + "/" + a.max_hp;
      card.querySelector(".bar i").style.width = Math.max(0, 100 * a.hp / a.max_hp) + "%";
      card.querySelector(".bar i").className = hpClass(a.hp, a.max_hp);
    }
    for (k in state.monsters) {
      a = state.monsters[k]; el = document.getElementById("tok-" + k);
      p = px(a.room, a.tile);
      el.style.transform = "translate(" + p[0] + "px," + p[1] + "px)";
      el.classList.toggle("dead", a.hp <= 0);
      var mb = el.querySelector(".hp"); mb.setAttribute("width", Math.max(0, 28 * a.hp / a.max_hp)); mb.setAttribute("class", "hp " + hpClass(a.hp, a.max_hp));
    }
    var crown = $("#crown");
    if (state.crown.status === "locked") crown.classList.add("hidden");
    else {
      crown.classList.remove("hidden");
      var cp;
      if (state.crown.carrier && state.agents[state.crown.carrier]) { var c = state.agents[state.crown.carrier]; cp = px(c.room, c.tile); cp = [cp[0], cp[1] - 24]; }
      else cp = px(state.crown.room, state.crown.tile);
      crown.style.transform = "translate(" + cp[0] + "px," + cp[1] + "px)";
      $("#crown-att").textContent = state.crown.attunement ? String(state.crown.attunement) : "";
    }
    for (k in geo.rooms) {
      var floor = document.getElementById("floor-" + k), nm = document.getElementById("name-" + k);
      var sealed = state.sealed.indexOf(k) >= 0, contracting = state.contracting.indexOf(k) >= 0;
      floor.setAttribute("class", "room-floor" + (sealed ? " sealed" : contracting ? " contracting" : ""));
      nm.setAttribute("class", "room-name" + (sealed ? " sealed" : ""));
    }
    document.querySelectorAll(".corridor").forEach(function (c) {
      var cut = state.sealed.indexOf(c.getAttribute("data-from")) >= 0 || state.sealed.indexOf(c.getAttribute("data-to")) >= 0;
      c.setAttribute("class", "corridor" + (cut ? " cut" : ""));
    });
    for (k in state.seals) { var sm = document.getElementById("seal-" + k); if (sm) sm.setAttribute("class", "seal-mark" + (state.seals[k] === "active" ? " active" : "")); }
    for (k in state.caches) { var cm = document.getElementById("cache-" + k); if (cm) cm.setAttribute("class", "cache-mark" + (state.caches[k] ? " found" : "")); }
    document.querySelectorAll(".door").forEach(function (d) { d.setAttribute("class", "door" + (state.vault_open && d.id.indexOf("vault") >= 0 ? " open" : "")); });
    document.querySelectorAll(".token").forEach(function (t) { t.classList.remove("speaking", "acting", "thinking"); });
    if (frame && frame.type === "everyone_thinks") {
      for (k in state.agents) if (state.agents[k].status === "active") document.getElementById("tok-" + k).classList.add("thinking");
    } else if (frame && frame.actor) { var t = document.getElementById("tok-" + frame.actor); if (t) t.classList.add(frame.type === "agent_speech" ? "speaking" : "acting"); }
  }

  var BLOWS = { attack_hit: 1, attack_miss: 1, wild_swing_self_damage: 1, wild_swing_bystander: 1, wild_swing_room_reaction: 1, hazard_burn: 1, agent_eliminated: 1, monster_defeated: 1 };
  var CROWN = { crown_unlocked: 1, crown_taken: 1, crown_dropped: 1, crown_attuned: 1, crown_extracted: 1, vault_gate_opened: 1 };
  var PHASE = { everyone_thinks: "1 · they think", agent_speech: "2 · they speak", initiative_order: "3 · they act", move: "3 · they act", step: "3 · they act", attack_hit: "3 · they act", attack_miss: "3 · they act", guard: "3 · they act", rest: "3 · they act", search_failure: "3 · they act", cache_found: "3 · they act", seal_activated: "3 · they act", stale_action: "3 · they act", item_used: "3 · they act", wild_swing_self_damage: "3 · they act", wild_swing_bystander: "3 · they act", wild_swing_room_reaction: "3 · they act", monster_step: "4 · the vault", round_narration: "end of round" };

  function actOf(f) { return f.actor && state.agents[f.actor] ? f.actor : (f.target && state.agents[f.target] && !(f.actor && state.monsters[f.actor]) ? f.target : null); }
  function setGoal(aid) {
    var g = $("#goal");
    if (!aid) { g.hidden = true; return; }
    var a = state.agents[aid];
    g.hidden = false;
    $("#goal-plan").textContent = a.note && a.note.objective ? a.note.objective : "";
    $("#goal-reads").textContent = readsLine(a.note && a.note.reads);
    var sec = $("#goal-secret");
    if (a.secret) {
      sec.innerHTML = 'Secret aim: <b></b> <span class="d"></span>';
      sec.querySelector("b").textContent = a.secret + " (" + a.secret_text.replace(/\.$/, "").toLowerCase() + ")";
      var dEl = sec.querySelector(".d"); dEl.className = a.secret_done === true ? "done" : a.secret_done === false ? "failed" : "";
      dEl.textContent = a.secret_done === true ? "· done" : a.secret_done === false ? "· not done" : "";
    } else sec.textContent = "";
  }

  function caption(f) {
    var st = $("#stage"), whoEl = $("#who"), what = $("#what"), meta = $("#meta"), th = $("#thoughts");
    var kind = f.type === "everyone_thinks" ? "thinks" : f.type === "agent_speech" ? "speech" : f.narration ? "narration" : BLOWS[f.type] ? "blow" : CROWN[f.type] ? "crown" : "";
    st.className = "stage " + kind;
    $("#turn").hidden = true; what.hidden = false;
    $("#round-no").textContent = f.round >= 1 ? "Round " + f.round : "Before round 1";
    $("#round-n").textContent = (idx + 1) + " of " + frames.length;
    var phase = PHASE[f.type] ? '<span class="phase">' + PHASE[f.type] + "</span>" : "";
    th.hidden = true; th.innerHTML = "";
    if (f.type === "everyone_thinks") {
      whoEl.innerHTML = '<span class="dot" style="background:var(--thought)"></span><b>All eight, privately</b>' + phase;
      what.textContent = f.text;
      f.thoughts.forEach(function (t) {
        var li = document.createElement("li");
        li.innerHTML = '<span class="dot"></span><span><b></b> <span class="plan"></span></span><span class="reads"></span>';
        li.querySelector(".dot").style.background = colours[t.who];
        li.querySelector("b").textContent = t.name + ":";
        li.querySelector(".plan").textContent = t.objective;
        li.querySelector(".reads").textContent = readsLine(t.reads);
        th.appendChild(li);
      });
      th.hidden = false;
      setGoal(null);
      meta.textContent = "Written before anyone moves. Never said aloud.";
      return;
    }
    var aid = actOf(f);
    if (f.actor && state.agents[f.actor]) {
      var a = state.agents[f.actor];
      whoEl.innerHTML = '<span class="dot"></span><b></b><span class="role"></span>' + phase;
      whoEl.querySelector(".dot").style.background = colours[f.actor];
      whoEl.querySelector("b").textContent = a.name;
      whoEl.querySelector(".role").textContent = a.build + " · " + roomName(a.room);
    } else if (f.actor && state.monsters[f.actor]) {
      var m = state.monsters[f.actor];
      whoEl.innerHTML = '<span class="dot monster"></span><b></b><span class="role"></span>' + phase;
      whoEl.querySelector("b").textContent = m.name;
      whoEl.querySelector(".role").textContent = roomName(m.room);
    } else if (f.narration) { whoEl.innerHTML = '<span class="dot" style="background:var(--ember)"></span><b>Narrator</b>' + phase; }
    else { whoEl.innerHTML = '<span class="dot"></span><b>Referee</b>' + phase; }
    if (f.type === "agent_speech") {
      what.textContent = (f.mode === "whisper" ? "whispers" + (f.to && f.to.length ? " to " + f.to.join(", ") : "") + ": " : "") + "“" + f.speech + "”";
    } else what.textContent = f.text;
    setGoal(aid);
    meta.textContent = aid ? (f.type === "agent_speech" ? "Said aloud. Under it, what they privately meant to do this round." : "What they did. Under it, what they privately meant to do.") : "";
  }

  function effects(f) {
    var tgt = f.target && (state.agents[f.target] || state.monsters[f.target]) ? f.target : (f.actor && (state.agents[f.actor] || state.monsters[f.actor]) ? f.actor : null);
    if (f.type === "agent_speech" && f.actor && state.agents[f.actor]) {
      var a = state.agents[f.actor], p = px(a.room, a.tile);
      var below = p[1] < geo.height * .22, right = p[0] > geo.width / 2;
      bubble.className = "bubble" + (f.mode === "whisper" ? " whisper" : "") + (below ? " below" : "") + (right ? " rt" : "");
      bubble.textContent = f.speech.length > 110 ? f.speech.slice(0, 107) + "…" : f.speech;
      var pct = 100 * Math.max(geo.width * .16, Math.min(geo.width * .84, p[0])) / geo.width;
      if (right) { bubble.style.left = "auto"; bubble.style.right = (100 - pct) + "%"; }
      else { bubble.style.right = "auto"; bubble.style.left = pct + "%"; }
      bubble.style.top = (100 * (p[1] + (below ? 14 : -14)) / geo.height) + "%";
      bubble.hidden = false;
    } else bubble.hidden = true;
    if (!tgt) return;
    var b = state.agents[tgt] || state.monsters[tgt], p2 = px(b.room, b.tile);
    var ns = "http://www.w3.org/2000/svg";
    function text(cls, s) { var t = document.createElementNS(ns, "text"); t.setAttribute("class", cls); t.setAttribute("x", p2[0]); t.setAttribute("y", p2[1] - 20); t.textContent = s; fx.appendChild(t); setTimeout(function () { t.remove(); }, 1400); }
    if (f.type === "attack_hit" || f.type === "wild_swing_bystander" || f.type === "wild_swing_self_damage" || f.type === "hazard_burn" || f.type === "wild_swing_room_reaction") {
      var ring = document.createElementNS(ns, "circle"); ring.setAttribute("class", "ring"); ring.setAttribute("cx", p2[0]); ring.setAttribute("cy", p2[1]); fx.appendChild(ring); setTimeout(function () { ring.remove(); }, 900);
      text("dmg", "−" + f.amount);
      swing(f, p2);
    } else if (f.type === "attack_miss") { text("miss", "miss"); swing(f, p2); }
    else if (f.type === "rest" || f.type === "item_used") { if (f.amount) text("heal", "+" + f.amount); }
    else if (f.type === "agent_eliminated") { text("dmg", "out"); }
    else if (f.type === "monster_defeated") { text("dmg", "falls"); }
  }
  function swing(f, p) {
    var at = f.actor && (state.agents[f.actor] || state.monsters[f.actor]);
    if (!at || f.actor === f.target) return;
    var q = px(at.room, at.tile);
    var l = document.createElementNS("http://www.w3.org/2000/svg", "line");
    l.setAttribute("class", "swing"); l.setAttribute("x1", q[0]); l.setAttribute("y1", q[1]); l.setAttribute("x2", p[0]); l.setAttribute("y2", p[1]);
    fx.appendChild(l); setTimeout(function () { l.remove(); }, 1100);
  }

  function goto(n, animate, quiet) {
    n = Math.max(0, Math.min(frames.length - 1, n));
    if (n < idx || idx < 0) { state = clone(D.start); for (var i = 0; i <= n; i++) fold(state, frames[i].delta); }
    else { for (var j = idx + 1; j <= n; j++) fold(state, frames[j].delta); }
    idx = n;
    var f = frames[idx];
    render(quiet ? null : f);
    if (!quiet) {
      caption(f);
      if (animate !== false) effects(f); else bubble.hidden = true;
      $("#scrub").value = idx;
    }
    $("#final").hidden = f.type !== "final_scores";
    if (f.type === "final_scores") showFinal(f);
  }

  // ---- following one character: one card per round ----
  function list(el, items, none) {
    el.innerHTML = "";
    if (!items || !items.length) { var s = document.createElement("span"); s.className = "none"; s.textContent = none; el.appendChild(s); return; }
    if (items.length === 1) { el.textContent = items[0]; return; }
    var ul = document.createElement("ul");
    items.forEach(function (t) { var li = document.createElement("li"); li.textContent = t; ul.appendChild(li); });
    el.appendChild(ul);
  }
  function showTurn(k, animate) {
    var cards = turns[follow];
    k = Math.max(0, Math.min(cards.length - 1, k));
    var c = cards[k];
    ti = k;
    goto(c.end, false, true);                       // the board stands at the end of this round
    var a = state.agents[follow];
    document.querySelectorAll(".token").forEach(function (t) { t.classList.remove("speaking", "acting", "thinking"); });
    var tok = document.getElementById("tok-" + follow); if (tok) tok.classList.add(c.said ? "speaking" : "acting");
    var st = $("#stage"); st.className = "stage turnview";
    $("#what").hidden = true; $("#thoughts").hidden = true; $("#goal").hidden = true; $("#turn").hidden = false;
    $("#round-no").textContent = "Round " + c.round;
    $("#round-n").textContent = (k + 1) + " of " + cards.length + " rounds";
    var whoEl = $("#who");
    whoEl.innerHTML = '<span class="dot"></span><b></b><span class="role"></span><span class="hpline"></span>';
    whoEl.querySelector(".dot").style.background = colours[follow];
    whoEl.querySelector("b").textContent = a.name;
    whoEl.querySelector(".role").textContent = a.build + " · " + roomName(c.room_after);
    var hp = whoEl.querySelector(".hpline");
    if (c.out_before) hp.innerHTML = "out of the match";
    else {
      var cls = c.hp_after < c.hp_before ? "down" : c.hp_after > c.hp_before ? "up" : "";
      hp.innerHTML = 'HP <b>' + c.hp_before + '</b> → <b class="' + cls + '">' + c.hp_after + '</b> / ' + a.max_hp + (c.status_after === "eliminated" ? " · <span class=\"down\">out</span>" : c.status_after === "escaped" ? " · escaped" : "");
    }
    $("#t-thought").textContent = c.thought || "";
    $("#t-reads").textContent = readsLine(c.reads);
    var said = $("#t-said"); said.innerHTML = "";
    if (c.said) {
      said.appendChild(document.createTextNode("“" + c.said + "”"));
      if (c.mode === "whisper" || (c.to && c.to.length)) {
        var to = document.createElement("span"); to.className = "to";
        to.textContent = (c.mode === "whisper" ? "whispered" : "said") + (c.to && c.to.length ? " to " + c.to.join(", ") : "") + (c.mode === "whisper" ? ", heard by nobody else" : ", in front of the room");
        said.appendChild(to);
      }
    } else { var none = document.createElement("span"); none.className = "none"; none.textContent = c.out_before ? "—" : "said nothing"; said.appendChild(none); }
    list($("#t-did"), c.did, c.out_before ? "—" : "nothing");
    list($("#t-happened"), c.happened, c.out_before ? "—" : "nothing");
    $("#t-narr-row").hidden = !c.narration; $("#t-narr").textContent = c.narration || "";
    var sec = $("#t-secret");
    sec.innerHTML = 'Secret aim: <b></b> <span class="d"></span>';
    sec.querySelector("b").textContent = a.secret + " (" + a.secret_text.replace(/\.$/, "").toLowerCase() + ")";
    var dEl = sec.querySelector(".d"); dEl.className = a.secret_done === true ? "done" : a.secret_done === false ? "failed" : "";
    dEl.textContent = a.secret_done === true ? "· done" : a.secret_done === false ? "· not done" : "";
    $("#meta").textContent = "Thought is private and written before the round. Said is what the others heard. The board shows the end of the round.";
    $("#scrub").value = k;
    if (animate !== false && c.said && a) {
      var p = px(a.room, a.tile), below = p[1] < geo.height * .22, right = p[0] > geo.width / 2;
      bubble.className = "bubble" + (c.mode === "whisper" ? " whisper" : "") + (below ? " below" : "") + (right ? " rt" : "");
      bubble.textContent = c.said.length > 110 ? c.said.slice(0, 107) + "…" : c.said;
      var pct = 100 * Math.max(geo.width * .16, Math.min(geo.width * .84, p[0])) / geo.width;
      if (right) { bubble.style.left = "auto"; bubble.style.right = (100 - pct) + "%"; } else { bubble.style.right = "auto"; bubble.style.left = pct + "%"; }
      bubble.style.top = (100 * (p[1] + (below ? 14 : -14)) / geo.height) + "%";
      bubble.hidden = false;
    } else bubble.hidden = true;
  }
  function setFollow(id) {
    follow = turns[id] ? id : "";
    document.body.classList.toggle("following", !!follow);
    document.querySelectorAll(".chip").forEach(function (ch) { ch.setAttribute("aria-pressed", String(ch.getAttribute("data-follow") === follow)); });
    pause();
    if (follow) {
      $("#scrub").max = turns[follow].length - 1;
      var r = idx >= 0 ? frames[idx].round : 1, k = 0;
      turns[follow].forEach(function (c, i) { if (c.round <= Math.max(1, r)) k = i; });
      showTurn(k, true);
    } else {
      $("#scrub").max = frames.length - 1;
      goto(idx >= 0 ? idx : 0, false);
    }
  }
  function showFinal(f) {
    var rows = Object.keys(f.placements).sort(function (a, b) { return f.placements[a] - f.placements[b]; });
    var tb = $("#final tbody"); tb.innerHTML = "";
    rows.forEach(function (id) {
      var a = state.agents[id], tr = document.createElement("tr");
      tr.innerHTML = '<td class="n"></td><td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.4rem;background:' + colours[id] + '"></span><span class="nm"></span></td><td></td><td class="n"></td>';
      tr.children[0].textContent = f.placements[id]; tr.querySelector(".nm").textContent = a.name;
      tr.children[2].textContent = a.status === "escaped" ? "escaped with the Crown" : a.status === "eliminated" ? "eliminated" : "standing";
      tr.children[3].textContent = f.scores[id];
      tb.appendChild(tr);
    });
  }
  function step(dir) { pause(); if (follow) showTurn(ti + dir, dir > 0); else goto(idx + dir, dir > 0); }
  function jumpRound(dir) {
    pause();
    if (follow) { showTurn(ti + dir, dir > 0); return; }
    var r = frames[idx].round, target = null;
    for (var i = 0; i < frames.length; i++) if (frames[i].type === "round_started" && ((dir > 0 && frames[i].round > r) || (dir < 0 && frames[i].round < r))) { target = i; if (dir > 0) break; }
    if (target === null) target = dir > 0 ? frames.length - 1 : 0;
    goto(target, false);
  }
  function tick() {
    if (!playing) return;
    if (follow) {
      if (ti >= turns[follow].length - 1) { pause(); return; }
      showTurn(ti + 1, true);
      timer = setTimeout(tick, turns[follow][ti].dwell / speed);
      return;
    }
    if (idx >= frames.length - 1) { pause(); return; }
    goto(idx + 1, true);
    timer = setTimeout(tick, frames[idx].dwell / speed);
  }
  function play() {
    playing = true; $("#play").textContent = "Pause"; $("#play").setAttribute("aria-pressed", "true");
    if (follow) { if (ti >= turns[follow].length - 1) showTurn(0, true); timer = setTimeout(tick, turns[follow][ti].dwell / speed); return; }
    if (idx >= frames.length - 1) goto(0, true);
    timer = setTimeout(tick, frames[idx].dwell / speed);
  }
  function pause() { playing = false; clearTimeout(timer); $("#play").textContent = "Play"; $("#play").setAttribute("aria-pressed", "false"); }

  $("#play").addEventListener("click", function () { playing ? pause() : play(); });
  $("#next").addEventListener("click", function () { step(1); });
  $("#prev").addEventListener("click", function () { step(-1); });
  $("#nextr").addEventListener("click", function () { jumpRound(1); });
  $("#prevr").addEventListener("click", function () { jumpRound(-1); });
  $("#speed").addEventListener("change", function (e) { speed = parseFloat(e.target.value) || 1; });
  $("#scrub").addEventListener("input", function (e) { pause(); var v = parseInt(e.target.value, 10); if (follow) showTurn(v, false); else goto(v, false); });
  document.querySelectorAll(".chip").forEach(function (ch) { ch.addEventListener("click", function () { setFollow(ch.getAttribute("data-follow")); }); });
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.key === " ") { e.preventDefault(); playing ? pause() : play(); }
    else if (e.key === "ArrowRight") { step(1); } else if (e.key === "ArrowLeft") { step(-1); }
  });
  goto(0, false);
  setFollow(Object.keys(D.start.agents)[0]);   // opens on one character; "Everyone" is a chip away
})();
"""


def build(bundle: dict, note: str = "") -> str:
    start, frames = build_timeline(bundle)
    problems = verify(bundle, start, frames)
    if problems:
        raise ValueError("board disagrees with the referee's snapshots:\n  " + "\n  ".join(problems[:20]))
    geo = board_geometry()
    m = bundle.get("match", {})
    rounds = sorted({f["round"] for f in frames if f["round"] >= 1})
    winner = start["agents"].get(m.get("winner_agent_id"), {}).get("name") or "nobody"
    colours = {aid: TOKEN_COLOURS[i % len(TOKEN_COLOURS)] for i, aid in enumerate(start["agents"])}
    turns = build_turns(start, frames)
    data = {"geo": geo, "start": start, "frames": frames, "colours": colours, "turns": turns}
    chips = '<button type="button" class="chip" data-follow="" aria-pressed="false">Everyone</button>\n' + "\n".join(
        f'<button type="button" class="chip" data-follow="{E(aid)}" aria-pressed="false"><span class="dot" style="background:{colours[aid]}"></span>{E(a["name"].split()[0])}</button>'
        for aid, a in start["agents"].items())
    roster = "\n".join(
        f'<div class="card" id="card-{E(aid)}"><span class="dot" style="background:{colours[aid]}"></span>'
        f'<span class="name" title="{E(a["name"])}, {E(a["build"])}">{E(a["name"].split()[0])}</span><span class="num">{a["hp"]}/{a["max_hp"]}</span>'
        f'<span class="bar"><i style="width:100%"></i></span></div>'
        for aid, a in start["agents"].items())
    sub = (f"Match {E(str(m.get('id', '')))}, seed {E(str(m.get('seed', '')))}. {len(rounds)} rounds of {E(str(m.get('max_rounds', '')))} played; "
           f"winner {E(winner)}. Each round: all eight think at once, then speak, then act in initiative order. Press Play." + (f" {E(note)}" if note else ""))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<title>Ember Vault Board</title>
{FONTS}
<style>{CSS}</style>
<div class="page">
  <header class="top">
    <h1>Ember Vault, watched</h1>
    <p class="sub">{sub}</p>
  </header>
  <div class="main">
  <div class="board-wrap">
{render_board_svg(geo, start)}
    <div class="bubble" id="bubble" hidden></div>
  </div>
  <div class="roster">
{roster}
  </div>
  <div class="legend">
    <span><i class="b"></i> not floor</span><span><i class="c"></i> cover (+1 armour)</span><span><i class="h"></i> hazard (1 damage to end a step on)</span>
    <span><i class="d"></i> door</span><span>♛ the Crown, with attunement</span><span><i class="m"></i> a monster</span>
  </div>
  </div>
  <aside class="side">
  <div class="follow" role="group" aria-label="Who to follow">
    <span class="lbl">Follow</span>
{chips}
  </div>
  <div class="round-bar"><span id="round-no">Round 1</span><span class="n" id="round-n"></span></div>
  <section class="stage" id="stage" aria-live="polite">
    <div class="who" id="who"></div>
    <p class="what" id="what"></p>
    <ul class="thoughts" id="thoughts" hidden></ul>
    <div class="goal" id="goal" hidden>
      <span class="lbl">Their plan this round, written privately</span>
      <span class="plan" id="goal-plan"></span>
      <span class="reads" id="goal-reads"></span>
      <span class="secret" id="goal-secret"></span>
    </div>
    <div class="turn" id="turn" hidden>
      <div class="row"><span class="lbl">Thought</span><div class="val"><span class="thought" id="t-thought"></span><span class="reads" id="t-reads"></span></div></div>
      <div class="row"><span class="lbl">Said</span><div class="val said" id="t-said"></div></div>
      <div class="row"><span class="lbl">Did</span><div class="val" id="t-did"></div></div>
      <div class="row"><span class="lbl">Happened to them</span><div class="val" id="t-happened"></div></div>
      <details class="narr-fold" id="t-narr-row"><summary>The narrator's account of the round</summary><div class="val narr" id="t-narr"></div></details>
      <span class="secret" id="t-secret"></span>
    </div>
    <div class="meta" id="meta"></div>
  </section>
  <div class="transport">
    <button type="button" id="prevr" title="Previous round">&#171; round</button>
    <button type="button" id="prev" title="Back one">&#8249;</button>
    <button type="button" id="play" class="play" aria-pressed="false">Play</button>
    <button type="button" id="next" title="Forward one">&#8250;</button>
    <button type="button" id="nextr" title="Next round">round &#187;</button>
    <label for="speed">Speed <select id="speed"><option value="0.6">slow</option><option value="1" selected>normal</option><option value="2">fast</option><option value="4">very fast</option></select></label>
  </div>
  <div class="scrub">
    <span class="lbl">Start</span>
    <input type="range" id="scrub" min="0" max="{len(frames) - 1}" value="0" step="1" aria-label="Position in the match">
    <span class="lbl">End</span>
  </div>
  <section class="final" id="final" hidden>
    <h2>How it ended</h2>
    <table><thead><tr><th>Place</th><th>Character</th><th>Fate</th><th>Score</th></tr></thead><tbody></tbody></table>
  </section>
  <p class="foot">Following one character, each step is one round: what they thought, said and did, and what happened to them, with the board standing at the end of that round. "Everyone" plays every moment in order. Drawn to the referee's own grids and checked against every round-end record the referee kept. Space plays and pauses; the arrow keys step. The Crown is the objective everyone plays for; the secret aim is the side objective their brain file carries, worth points at the end.</p>
  </aside>
</div>
<script>window.__REPLAY__ = {payload};</script>
<script>{SCRIPT}</script>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", type=Path, help="a replay bundle .json")
    ap.add_argument("out", type=Path)
    ap.add_argument("--note", default="", help="one sentence added under the title, e.g. which ending rule the match was played under")
    a = ap.parse_args(argv)
    bundle = json.loads(a.bundle.read_text(encoding="utf-8"))
    try:
        page = build(bundle, a.note)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    a.out.write_text(page, encoding="utf-8")
    print(f"wrote {a.out} ({len(page.encode())} bytes) from {a.bundle.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
