"""A match you watch: the board, the bodies on it, and what happens to them.

Reads a replay bundle (``python run.py replay <match_id> --output x.json``)
and writes one HTML page that plays the match back on a drawn map: the five
rooms to the engine's own grids (``arena.grid.ROOM_GRIDS``, doors, props),
the eight characters and three monsters as tokens on their tiles, every
move, step, swing, hit, seal, sealing room and Crown transfer shown where it
happened, and every line spoken shown beside the speaker. Play, pause, step,
scrub by round. No private notes anywhere on it: the firm, 13 Sep 2026,
"I want to literally see the replay not read the text".

The page is not a second referee. It carries a timeline of state changes
derived from the bundle's events, and the only place a change is *computed*
rather than read is the tile a body lands on after a room move, which the
event does not record; that uses the engine's own ``grid.free_tile_near`` on
the same inputs. ``verify`` then checks the derived state against every
round-end snapshot the referee wrote (room, tile, HP and status of every
character; tile and HP of every monster) and the build refuses on the first
mismatch. Tests prove it on a mock match.

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

from arena import grid  # noqa: E402

E = html.escape

# Events that carry nothing a viewer watches: dice, token spend, and the
# private notes, which are deliberately absent from this page.
SKIP = {"dice_roll", "agent_resource_update", "note_written"}

# How long the player dwells on an event at 1x, in milliseconds. Speech and
# narration scale with length so a long line can be read.
DWELL = {
    "agent_speech": (2600, 42, 9500), "round_narration": (3200, 38, 12000),
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


def dwell_ms(event: dict) -> int:
    base, per_char, cap = DWELL.get(event["event_type"], DEFAULT_DWELL)
    if per_char:
        text = (event.get("payload") or {}).get("speech") or event.get("public_text") or ""
        return min(cap, base + per_char * len(text))
    return base


# ---------------------------------------------------------------------------
# the timeline: state changes per event, derived from the bundle
# ---------------------------------------------------------------------------

def initial_state(bundle: dict) -> dict:
    """The board before round 1, from the referee's first snapshot."""
    first = bundle["snapshots"][0]["state"]
    agents = {}
    for aid, a in first["agents"].items():
        agents[aid] = {"id": aid, "name": a["name"], "build": a.get("build", ""), "room": a["room"],
                       "tile": list(a["tile"]), "hp": a["hp"], "max_hp": a["max_hp"], "status": a["status"], "guard": 0}
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


def build_timeline(bundle: dict) -> tuple[dict, list[dict]]:
    """Initial state plus one frame per watched event, in seq order."""
    state = initial_state(bundle)
    start = copy.deepcopy(state)
    frames = []
    names = {**{a["id"]: a["name"] for a in state["agents"].values()},
             **{m["id"]: m["name"] for m in state["monsters"].values()}}
    for ev in sorted(bundle["events"], key=lambda e: e["seq"]):
        t = ev["event_type"]
        if t in SKIP:
            continue
        if t == "item_taken" and ev.get("target_id") == "ember_crown":
            continue  # the crown_taken event that follows says the same thing
        p = ev.get("payload") or {}
        frame = {
            "seq": ev["seq"], "round": ev["round_no"], "type": t,
            "actor": ev.get("actor_id"), "target": ev.get("target_id"),
            "text": ev.get("public_text") or "", "dwell": dwell_ms(ev),
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
        frame["delta"] = apply_event(state, ev)
        # where the camera looks: the actor's room
        who = ev.get("actor_id") or ev.get("target_id")
        body = state["agents"].get(who) or state["monsters"].get(who)
        frame["room"] = body["room"] if body else (p.get("room") if p.get("room") in grid.ROOM_GRIDS else None)
        frames.append(frame)
    return start, frames


def verify(bundle: dict, start: dict, frames: list[dict]) -> list[str]:
    """Replay the deltas and compare with every round-end snapshot the
    referee wrote. Returns the mismatches; empty means the board is the
    referee's board."""
    state = copy.deepcopy(start)
    by_round_end = {s["round_no"]: s["state"] for s in bundle["snapshots"] if s["phase"] == "end"}
    problems: list[str] = []
    i = 0
    frames_by_round: dict[int, list[dict]] = {}
    for f in frames:
        frames_by_round.setdefault(f["round"], []).append(f)
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
    --ink: #efe4d6; --muted: #a8968a; --faint: #6f6058;
    --ember: #e8632a; --ember-soft: rgba(232, 99, 42, .18); --gold: #e9b44c; --moon: #9fc4d8;
    --blood: #c0392b; --heal: #6fae6a;
    --display: "Cinzel", "Times New Roman", serif; --sans: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
    --serif: "IBM Plex Serif", Georgia, serif;
  }
  html { color-scheme: dark; }
  body { margin: 0; background: var(--ground); color: var(--ink); font: 400 1rem/1.5 var(--sans); padding: 1rem 1rem 3rem; }
  .page { max-width: 1180px; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 0 1.4rem; }
  header.top { display: flex; flex-wrap: wrap; align-items: baseline; gap: .4rem 1.2rem; margin-bottom: .8rem; grid-column: 1 / -1; }
  .side { min-width: 0; }
  @media (min-width: 960px) {
    .page { grid-template-columns: minmax(0, 1.15fr) minmax(320px, 1fr); }
    .side { position: sticky; top: 1rem; align-self: start; }
    .stage { margin-top: 0; }
  }
  h1 { font: 700 1.35rem/1.2 var(--display); letter-spacing: .04em; margin: 0; color: var(--ink); }
  .sub { color: var(--muted); font-size: .92rem; margin: 0; }
  .board-wrap { position: relative; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  svg.board { display: block; width: 100%; height: auto; }
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
  .bubble[hidden] { display: none; }
  .stage { margin-top: .9rem; background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--line-2); border-radius: 6px; padding: .9rem 1.1rem; min-height: 5.4rem; display: grid; gap: .35rem; }
  .stage.speech { border-left-color: var(--ink); }
  .stage.narration { border-left-color: var(--ember); }
  .stage.blow { border-left-color: var(--blood); }
  .stage.crown { border-left-color: var(--gold); }
  .who { display: inline-flex; align-items: center; gap: .5rem; font-size: .82rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  .who .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--faint); border: 1px solid #0e0b0a; }
  .who .dot.monster { background: var(--blood); border-color: #4a0f0c; }
  .who b { color: var(--ink); letter-spacing: .02em; text-transform: none; font-size: .95rem; }
  .what { font-size: 1.15rem; line-height: 1.45; margin: 0; max-width: 70ch; }
  .stage.speech .what { font-size: 1.3rem; }
  .stage.narration .what { font-family: var(--serif); font-style: italic; color: #e4d6c4; }
  .meta { font-size: .8rem; color: var(--faint); }
  .transport { margin-top: .9rem; display: flex; flex-wrap: wrap; align-items: center; gap: .6rem .9rem; }
  .transport button { font: 600 .9rem var(--sans); color: var(--ink); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 6px; padding: .5rem .8rem; cursor: pointer; min-width: 2.8rem; }
  .transport button:hover { border-color: var(--muted); }
  .transport button.play { background: var(--ember); border-color: var(--ember); color: #1a0e08; min-width: 6.2rem; font-size: 1rem; }
  .transport button:focus-visible, .transport select:focus-visible, .transport input:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  .transport select { font: 500 .9rem var(--sans); color: var(--ink); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 6px; padding: .45rem .5rem; }
  .transport label { font-size: .85rem; color: var(--muted); display: inline-flex; align-items: center; gap: .4rem; }
  .scrub { display: grid; grid-template-columns: auto 1fr auto; gap: .8rem; align-items: center; margin-top: .7rem; font-variant-numeric: tabular-nums; }
  .scrub input[type=range] { width: 100%; accent-color: var(--ember); }
  .scrub .lbl { font-size: .85rem; color: var(--muted); white-space: nowrap; }
  .scrub .lbl b { color: var(--ink); font-weight: 600; }
  .roster { margin-top: 1rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(215px, 1fr)); gap: .5rem; }
  .card { display: grid; grid-template-columns: 22px 1fr auto; gap: .2rem .55rem; align-items: center; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: .5rem .65rem; font-size: .85rem; }
  .card .dot { width: 16px; height: 16px; border-radius: 50%; border: 1px solid #0e0b0a; }
  .card .name { font-weight: 600; }
  .card .build { color: var(--muted); font-size: .78rem; text-transform: capitalize; }
  .card .num { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .8rem; text-align: right; }
  .card .bar { grid-column: 2 / 4; height: 5px; background: #0e0b0a; border-radius: 3px; overflow: hidden; }
  .card .bar i { display: block; height: 100%; background: var(--heal); transition: width .3s; }
  .card .bar i.low { background: var(--gold); } .card .bar i.crit { background: var(--blood); }
  .card.out { opacity: .5; } .card.out .name::after { content: " · out"; color: var(--muted); font-weight: 400; }
  .card.escaped .name::after { content: " · escaped"; color: var(--moon); font-weight: 400; }
  .card.crown .name::before { content: "♛ "; color: var(--gold); }
  .legend { margin-top: .9rem; display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; font-size: .78rem; color: var(--muted); }
  .legend span { display: inline-flex; align-items: center; gap: .35rem; }
  .legend i { display: inline-block; width: 14px; height: 14px; border: 1px solid #55443a; }
  .legend i.b { background: #120e0c; } .legend i.c { background: repeating-linear-gradient(45deg, #2a211c 0 3px, #55443a 3px 4px); }
  .legend i.h { background: var(--ember-soft); border-color: rgba(232,99,42,.6); } .legend i.d { border: 0; border-top: 2px solid var(--muted); height: 0; margin-top: 6px; }
  .legend i.m { background: var(--blood); border-color: #4a0f0c; border-radius: 50%; }
  .main { min-width: 0; }
  .final { margin-top: 1rem; background: var(--panel); border: 1px solid var(--gold); border-radius: 6px; padding: .9rem 1.1rem; }
  .final[hidden] { display: none; }
  .final h2 { font: 700 1rem var(--display); letter-spacing: .06em; margin: 0 0 .5rem; color: var(--gold); }
  .final table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .9rem; }
  .final td, .final th { text-align: left; padding: .25rem .5rem .25rem 0; border-bottom: 1px solid var(--line); }
  .final th { color: var(--muted); font-weight: 500; font-size: .78rem; letter-spacing: .06em; text-transform: uppercase; }
  .final td.n { text-align: right; }
  .foot { margin-top: 1.4rem; color: var(--faint); font-size: .8rem; max-width: 70ch; }
  @keyframes rise { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-26px); } }
  @keyframes ring { from { r: 14; opacity: 1; } to { r: 30; opacity: 0; } }
  @keyframes fade { from { opacity: 1; } to { opacity: 0; } }
  @keyframes pulse { 0%, 100% { stroke-opacity: 1; } 50% { stroke-opacity: .35; } }
  @media (max-width: 560px) {
    body { padding-inline: .8rem; }
    .stage .what { font-size: 1.02rem; } .stage.speech .what { font-size: 1.1rem; }
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
        # an elbow: vertical from the upper door, then horizontal, then vertical into the lower door
        midy = (ay + by) / 2
        out.append(f'<path class="corridor" data-from="{c["from"]}" data-to="{c["to"]}" d="M{ax:.1f} {ay:.1f} V{midy:.1f} H{bx:.1f} V{by:.1f}"/>')
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
        name = start and {"egress": "The Moonlit Egress", "vault": "The Ember Vault", "ironwood_gate": "The Ironwood Gate",
                          "ossuary_gate": "The Ossuary Gate", "threshold": "The Threshold"}[rid]
        out.append(f'<text class="room-name" id="name-{rid}" x="{x + 6:.1f}" y="{y - 6:.1f}">{E(name)}</text>')
        out.append('</g>')
    out.append('<g id="crown" class="crown hidden"><path d="' + _crown_path() + '"/><text id="crown-att" y="3"></text></g>')
    out.append('<g id="bodies">')
    for i, (mid, m) in enumerate(start["monsters"].items()):
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
  var geo = D.geo, frames = D.frames, T = geo.tile;
  var state, idx = -1, playing = false, timer = null, speed = 1;
  var $ = function (s) { return document.querySelector(s); };
  var svg = $("svg.board"), fx = $("#fx"), bubble = $("#bubble"), wrap = $(".board-wrap");
  var colours = D.colours;

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
  function px(room, tile) {
    var r = geo.rooms[room];
    return [r.x + (tile[0] + .5) * T, r.y + (tile[1] + .5) * T];
  }
  function hpClass(hp, max) { var f = hp / max; return f <= .25 ? "crit" : f <= .5 ? "low" : ""; }

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
      card.querySelector(".num").textContent = a.hp + " / " + a.max_hp;
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
    document.querySelectorAll(".token").forEach(function (t) { t.classList.remove("speaking", "acting"); });
    if (frame && frame.actor) { var t = document.getElementById("tok-" + frame.actor); if (t) t.classList.add(frame.type === "agent_speech" ? "speaking" : "acting"); }
  }

  function who(id) {
    if (!id) return null;
    if (state.agents[id]) return { name: state.agents[id].name, colour: colours[id], kind: "agent", build: state.agents[id].build };
    if (state.monsters[id]) return { name: state.monsters[id].name, colour: null, kind: "monster" };
    return null;
  }
  var BLOWS = { attack_hit: 1, attack_miss: 1, wild_swing_self_damage: 1, wild_swing_bystander: 1, wild_swing_room_reaction: 1, hazard_burn: 1, agent_eliminated: 1, monster_defeated: 1 };
  var CROWN = { crown_unlocked: 1, crown_taken: 1, crown_dropped: 1, crown_attuned: 1, crown_extracted: 1, vault_gate_opened: 1 };

  function caption(f) {
    var st = $("#stage"), w = who(f.actor);
    var kind = f.type === "agent_speech" ? "speech" : f.narration ? "narration" : BLOWS[f.type] ? "blow" : CROWN[f.type] ? "crown" : "";
    st.className = "stage " + kind;
    var whoEl = $("#who"), what = $("#what"), meta = $("#meta");
    if (w) {
      whoEl.innerHTML = '<span class="dot' + (w.kind === "monster" ? " monster" : "") + '" style="' + (w.colour ? "background:" + w.colour : "") + '"></span><b></b><span class="role"></span>';
      whoEl.querySelector("b").textContent = w.name;
      whoEl.querySelector(".role").textContent = w.kind === "agent" ? (w.build + " · " + roomName(state.agents[f.actor].room)) : roomName(state.monsters[f.actor].room);
    } else if (f.narration) { whoEl.innerHTML = '<span class="dot" style="background:var(--ember)"></span><b>Narrator</b>'; }
    else { whoEl.innerHTML = '<span class="dot"></span><b>Referee</b>'; }
    if (f.type === "agent_speech") {
      what.textContent = (f.mode === "whisper" ? "whispers" + (f.to && f.to.length ? " to " + f.to.join(", ") : "") + ": " : "") + "“" + f.speech + "”";
    } else what.textContent = f.text;
    meta.textContent = "Round " + f.round + " · " + (idx + 1) + " of " + frames.length;
  }
  function roomName(r) { var n = document.getElementById("name-" + r); return n ? n.textContent : r; }

  function effects(f) {
    var tgt = f.target && (state.agents[f.target] || state.monsters[f.target]) ? f.target : (f.actor && (state.agents[f.actor] || state.monsters[f.actor]) ? f.actor : null);
    if (f.type === "agent_speech" && f.actor && state.agents[f.actor]) {
      var a = state.agents[f.actor], p = px(a.room, a.tile);
      var below = p[1] < geo.height * .22;
      bubble.className = "bubble" + (f.mode === "whisper" ? " whisper" : "") + (below ? " below" : "");
      bubble.textContent = f.speech.length > 110 ? f.speech.slice(0, 107) + "…" : f.speech;
      var bx = Math.max(geo.width * .18, Math.min(geo.width * .82, p[0]));
      bubble.style.left = (100 * bx / geo.width) + "%"; bubble.style.top = (100 * (p[1] + (below ? 14 : -14)) / geo.height) + "%";
      bubble.hidden = false;
    } else bubble.hidden = true;
    if (!tgt) return;
    var b = state.agents[tgt] || state.monsters[tgt], p = px(b.room, b.tile);
    var ns = "http://www.w3.org/2000/svg";
    function text(cls, s) { var t = document.createElementNS(ns, "text"); t.setAttribute("class", cls); t.setAttribute("x", p[0]); t.setAttribute("y", p[1] - 20); t.textContent = s; fx.appendChild(t); setTimeout(function () { t.remove(); }, 1400); }
    if (f.type === "attack_hit" || f.type === "wild_swing_bystander" || f.type === "wild_swing_self_damage" || f.type === "hazard_burn" || f.type === "wild_swing_room_reaction") {
      var ring = document.createElementNS(ns, "circle"); ring.setAttribute("class", "ring"); ring.setAttribute("cx", p[0]); ring.setAttribute("cy", p[1]); fx.appendChild(ring); setTimeout(function () { ring.remove(); }, 900);
      text("dmg", "−" + f.amount);
      swing(f, p);
    } else if (f.type === "attack_miss") { text("miss", "miss"); swing(f, p); }
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

  function goto(n, animate) {
    n = Math.max(0, Math.min(frames.length - 1, n));
    if (n < idx || idx < 0) { state = clone(D.start); for (var i = 0; i <= n; i++) fold(state, frames[i].delta); }
    else { for (var j = idx + 1; j <= n; j++) fold(state, frames[j].delta); }
    idx = n;
    var f = frames[idx];
    render(f); caption(f);
    if (animate !== false) effects(f); else bubble.hidden = true;
    $("#scrub").value = idx;
    $("#final").hidden = f.type !== "final_scores";
    if (f.type === "final_scores") showFinal(f);
  }
  function showFinal(f) {
    var rows = Object.keys(f.placements).sort(function (a, b) { return f.placements[a] - f.placements[b]; });
    var tb = $("#final tbody"); tb.innerHTML = "";
    rows.forEach(function (id) {
      var a = state.agents[id], tr = document.createElement("tr");
      tr.innerHTML = '<td class="n"></td><td><span class="dot" style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.4rem;background:' + colours[id] + '"></span><span class="nm"></span></td><td></td><td class="n"></td>';
      tr.children[0].textContent = f.placements[id]; tr.querySelector(".nm").textContent = a.name;
      tr.children[2].textContent = a.status === "escaped" ? "escaped with the Crown" : a.status === "eliminated" ? "eliminated" : "standing";
      tr.children[3].textContent = f.scores[id];
      tb.appendChild(tr);
    });
  }
  function step(dir) { pause(); goto(idx + dir, dir > 0); }
  function jumpRound(dir) {
    pause();
    var r = frames[idx].round, target = null;
    for (var i = 0; i < frames.length; i++) if (frames[i].type === "round_started" && ((dir > 0 && frames[i].round > r) || (dir < 0 && frames[i].round < r))) { target = i; if (dir > 0) break; }
    if (target === null) target = dir > 0 ? frames.length - 1 : 0;
    goto(target, false);
  }
  function tick() {
    if (!playing) return;
    if (idx >= frames.length - 1) { pause(); return; }
    goto(idx + 1, true);
    timer = setTimeout(tick, frames[idx].dwell / speed);
  }
  function play() { if (idx >= frames.length - 1) goto(0, true); playing = true; $("#play").textContent = "Pause"; $("#play").setAttribute("aria-pressed", "true"); timer = setTimeout(tick, frames[idx].dwell / speed); }
  function pause() { playing = false; clearTimeout(timer); $("#play").textContent = "Play"; $("#play").setAttribute("aria-pressed", "false"); }

  $("#play").addEventListener("click", function () { playing ? pause() : play(); });
  $("#next").addEventListener("click", function () { step(1); });
  $("#prev").addEventListener("click", function () { step(-1); });
  $("#nextr").addEventListener("click", function () { jumpRound(1); });
  $("#prevr").addEventListener("click", function () { jumpRound(-1); });
  $("#speed").addEventListener("change", function (e) { speed = parseFloat(e.target.value) || 1; });
  $("#scrub").addEventListener("input", function (e) { pause(); goto(parseInt(e.target.value, 10), false); });
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.key === " ") { e.preventDefault(); playing ? pause() : play(); }
    else if (e.key === "ArrowRight") { step(1); } else if (e.key === "ArrowLeft") { step(-1); }
  });
  goto(0, false);
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
    data = {"geo": geo, "start": start, "frames": frames, "colours": colours}
    roster = "\n".join(
        f'<div class="card" id="card-{E(aid)}"><span class="dot" style="background:{colours[aid]}"></span>'
        f'<span class="name">{E(a["name"])}</span><span class="num">{a["hp"]} / {a["max_hp"]}</span>'
        f'<span class="build" style="grid-column:2/4">{E(a["build"])}</span><span class="bar"><i style="width:100%"></i></span></div>'
        for aid, a in start["agents"].items())
    sub = (f"Match {E(str(m.get('id', '')))}, seed {E(str(m.get('seed', '')))}. {len(rounds)} rounds of {E(str(m.get('max_rounds', '')))} played; "
           f"winner {E(winner)}. {len(frames)} things happen. Press Play, or step with the arrows." + (f" {E(note)}" if note else ""))
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
  <div class="legend">
    <span><i class="b"></i> not floor</span><span><i class="c"></i> cover (+1 armour)</span><span><i class="h"></i> hazard (1 damage to end a step on)</span>
    <span><i class="d"></i> door</span><span>♛ the Crown, with attunement</span><span><i class="m"></i> a monster</span>
  </div>
  </div>
  <aside class="side">
  <section class="stage" id="stage" aria-live="polite">
    <div class="who" id="who"></div>
    <p class="what" id="what"></p>
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
  <div class="roster">
{roster}
  </div>
  <section class="final" id="final" hidden>
    <h2>How it ended</h2>
    <table><thead><tr><th>Place</th><th>Character</th><th>Fate</th><th>Score</th></tr></thead><tbody></tbody></table>
  </section>
  <p class="foot">Drawn to the referee's own grids: rooms, doors, cover, hazards and the tile each body stood on, checked against every round-end record the referee kept. Space plays and pauses; the arrow keys step.</p>
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
