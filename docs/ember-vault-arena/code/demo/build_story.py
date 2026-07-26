"""Project demo/summary.json into a cinematic, beat-by-beat story viewer.

The first viewer was an audit surface: eight cards, a scrolling log, and every
roll at once.  That is the right tool for verifying a match and the wrong one
for reading it.  This builds the other thing -- one beat on screen at a time,
with a deterministic camera that follows whoever the beat is about, mirroring
the camera grammar in the build spec (pan on move, focus attacker and target,
hold the roll, desaturate on elimination, freeze on extraction).

Everything rendered comes from the replay.  This script authors no facts: it
selects which canonical events are story beats, assigns each a shot type, and
writes the narration line that the engine already produced.

Usage:
    python3 demo/build_story.py [--summary demo/summary.json] [--out demo/story.html]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

# Event types that carry the story.  Everything else (dice_roll,
# agent_resource_update, initiative_order, guard, stale_action, action_skipped)
# is bookkeeping and belongs in the audit view, not on stage.
SHOT_KIND = {
    "act_started": "chapter",
    "agent_speech": "dialogue",
    "attack_hit": "strike",
    "attack_miss": "strike",
    "wild_swing_self_damage": "mishap",
    "wild_swing_bystander": "mishap",
    "wild_swing_room_reaction": "mishap",
    "monster_defeated": "world",
    "agent_eliminated": "death",
    "seal_activated": "world",
    "vault_gate_opened": "world",
    "cache_found": "world",
    "item_taken": "minor",
    "crown_unlocked": "crown",
    "crown_taken": "crown",
    "crown_dropped": "crown",
    "crown_attuned": "crown",
    "crown_extracted": "finale",
    "room_contracting": "closing",
    "room_sealing": "closing",
    "room_sealed": "closing",
    "floor_items_relocated": "minor",
    "move": "move",
}

# Shots that always earn a full-stage hold, regardless of round pacing.
MAJOR = {"chapter", "crown", "death", "finale"}

ROOM_ORDER = ["threshold", "ironwood_gate", "ossuary_gate", "vault", "egress"]
ROOM_LABEL = {
    "threshold": "The Threshold",
    "ironwood_gate": "Ironwood Gate",
    "ossuary_gate": "Ossuary Gate",
    "vault": "The Ember Vault",
    "egress": "Moonlit Egress",
}


def build_beats(summary: dict) -> list[dict]:
    by_id = {a["id"]: a for a in summary["roster"]}
    beats: list[dict] = []

    # Live position per agent, advanced event by event.  The round's state_after
    # snapshot is the *end* of the round, so driving sprites from it would
    # teleport everyone to their final room on the round's first beat.  Everyone
    # starts at the Threshold, per new_match_state.
    pos = {a["id"]: "threshold" for a in summary["roster"]}

    for rnd in summary["timeline"]:
        round_no = rnd["round"]
        act = rnd.get("act")
        act_name = rnd.get("act_name") or ""
        state = rnd.get("state_after") or {}

        # The engine emits every agent's speech up front, during intent
        # collection, before any action resolves.  Shown as its own shot that is
        # eight "X says Y" cards per round -- noise that buries the story.  Film
        # convention instead: the line lands *with* the action.  So pull each
        # speaker's line aside and attach it to that agent's next action beat in
        # the same round.
        pending_speech: dict[str, str] = {}
        for ev in rnd.get("events", []):
            if ev["type"] == "agent_speech" and ev.get("actor"):
                said = (ev.get("payload") or {}).get("speech")
                if said:
                    pending_speech.setdefault(ev["actor"], said)

        for ev in rnd.get("events", []):
            if ev["type"] == "agent_speech":
                continue

            # Advance positions from *every* move, including the ones that never
            # become their own shot, plus the forced relocations a collapsing
            # room produces.
            ev_payload = ev.get("payload") or {}
            # Any event that records a room change relocates its actor -- ordinary
            # movement, but also the extraction, which is a crown_extracted event
            # rather than a move and would otherwise leave the winner standing in
            # the Vault as they escape.
            if ev.get("actor") and isinstance(ev_payload.get("changes"), dict):
                dest = (ev_payload["changes"].get("room") or [None, None])[-1]
                if dest:
                    pos[ev["actor"]] = dest
            if ev["type"] == "room_sealed":
                for moved in ev_payload.get("agents_moved") or []:
                    aid = moved if isinstance(moved, str) else moved.get("agent_id")
                    if aid:
                        pos[aid] = "vault"

            kind = SHOT_KIND.get(ev["type"])
            if not kind:
                continue

            actor = ev.get("actor")
            target = ev.get("target")
            payload = ev.get("payload") or {}

            # Movement is only worth a shot when it changes the picture: entering
            # the vault, reaching the egress, or being forced out by a seal.
            if kind == "move":
                dest = payload.get("changes", {}).get("room", [None, None])[-1]
                if dest not in ("vault", "egress"):
                    continue

            roll = None
            tohit = payload.get("tohit")
            if isinstance(tohit, dict):
                roll = {
                    "die": tohit.get("roll") or tohit.get("d20"),
                    "power": tohit.get("effective_power", tohit.get("base_power")),
                    "dc": (tohit.get("dc") or {}).get("value"),
                    "hit": bool(tohit.get("hit")),
                }
            face = payload.get("face_id") or payload.get("face")

            beats.append(
                {
                    "round": round_no,
                    "act": act,
                    "act_name": act_name,
                    "kind": kind,
                    "type": ev["type"],
                    "actor": actor,
                    "actor_name": (by_id.get(actor) or {}).get("name", actor),
                    "target": target,
                    "target_name": (by_id.get(target) or {}).get("name", target),
                    "text": ev.get("text") or "",
                    "speech": pending_speech.pop(actor, None) if actor else None,
                    "room": payload.get("room"),
                    "roll": roll,
                    "face": face,
                    "amount": payload.get("amount") or payload.get("applied"),
                    "accident": bool(payload.get("accident")),
                    "pos": dict(pos),
                    "state": {
                        "agents": {
                            a["id"]: {
                                "hp": a.get("hp"),
                                "max_hp": a.get("max_hp"),
                                "room": a.get("room"),
                                "score": a.get("score"),
                                "status": a.get("status"),
                            }
                            for a in (state.get("agents") or [])
                        },
                        "seals": state.get("seals") or {},
                        "crown": state.get("crown") or {},
                        "sealed": state.get("sealed_rooms") or [],
                        "contracting": state.get("contracting_rooms") or [],
                    },
                }
            )
    return beats


TEMPLATE = """<title>Ember Vault Arena — The Chronicle of Seed 52</title>
<style>
/* A deliberately single-world design: this is a lit stage in a dark room, and
   inverting it would defeat the point.  Tokens still respond to the theme
   toggle so a light-theme viewer gets a warmer, less punishing ground rather
   than a broken one. */
:root {
  --void:#0a0908; --stone:#15110d; --stone-lit:#211a14; --edge:#2e251c;
  --bone:#f0e7d9; --ash:#8a7d6d; --ash-dim:#5b5148;
  --ember:#ff8320; --ember-deep:#c2560c; --ember-glow:rgba(255,131,32,.16);
  --kiln:#d9432f; --kiln-glow:rgba(217,67,47,.15);
  --verd:#4dbb99; --verd-glow:rgba(77,187,153,.14);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:"Avenir Next","Segoe UI",Roboto,system-ui,-apple-system,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
:root[data-theme="light"] {
  --void:#1c1712; --stone:#241d16; --stone-lit:#2f261d; --edge:#3d3226;
  --bone:#f6efe4; --ash:#a4978a; --ash-dim:#7a6e62;
}
*,*::before,*::after{box-sizing:border-box;}
.ev{
  background:var(--void); color:var(--bone); font-family:var(--sans);
  min-height:100vh; padding:clamp(12px,2.4vw,28px);
  display:flex; flex-direction:column; gap:clamp(10px,1.6vw,18px);
  max-width:1180px; margin:0 auto; overflow-x:hidden;
}
.ev :focus-visible{outline:2px solid var(--ember); outline-offset:2px; border-radius:3px;}

/* ---------- chapter bar ---------- */
.chapterbar{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  border-bottom:1px solid var(--edge); padding-bottom:10px;}
.chapterbar h1{font-family:var(--serif); font-size:clamp(17px,2.2vw,23px); margin:0;
  font-weight:600; letter-spacing:.01em; text-wrap:balance;}
.chapterbar .sub{font-size:12px; color:var(--ash); letter-spacing:.11em;
  text-transform:uppercase;}
.acts{display:flex; gap:6px; margin-left:auto;}
.actpip{font-size:11px; letter-spacing:.13em; text-transform:uppercase;
  color:var(--ash-dim); padding:3px 10px; border:1px solid var(--edge);
  border-radius:2px; transition:color .35s, border-color .35s, background .35s;}
.actpip.on{color:var(--ember); border-color:var(--ember-deep); background:var(--ember-glow);}

/* ---------- the stage ---------- */
.stage{
  position:relative; min-height:clamp(280px,42vh,400px);
  background:
    radial-gradient(120% 90% at 50% 0%, var(--stone-lit) 0%, var(--stone) 55%, var(--void) 100%);
  border:1px solid var(--edge); border-radius:4px;
  padding:clamp(18px,3.4vw,40px);
  display:flex; flex-direction:column; justify-content:center; align-items:center;
  gap:clamp(10px,1.6vw,18px); text-align:center; overflow:hidden;
}
.stage::after{ /* ember floor wash, keyed to the shot */
  content:""; position:absolute; inset:auto -20% -55% -20%; height:70%;
  background:radial-gradient(60% 100% at 50% 100%, var(--wash,transparent) 0%, transparent 72%);
  pointer-events:none; transition:background .6s ease;
}
.stage>*{position:relative; z-index:1;}
.locus{font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--ash);}
.line{font-family:var(--serif); font-size:clamp(21px,3.6vw,36px); line-height:1.24;
  margin:0; text-wrap:balance; max-width:22ch;}
.quote{font-family:var(--serif); font-style:italic; color:var(--ash);
  font-size:clamp(14px,1.9vw,19px); line-height:1.35; margin:0; max-width:34ch;
  text-wrap:balance;}
.who{display:flex; align-items:center; gap:9px; font-size:13px; letter-spacing:.05em;}
.who .dot{width:9px; height:9px; border-radius:50%; flex:none;}
.chapter .line{font-size:clamp(30px,6.4vw,62px); letter-spacing:.02em; text-transform:uppercase;}
.chapter .locus{color:var(--ember);}
.mishap .line{color:var(--bone);}
.mishap .tagline{color:var(--kiln);}
.death .line{color:var(--kiln);}
.crown .line{color:var(--ember);}
.finale .line{color:var(--ember);}
.tagline{font-size:11px; letter-spacing:.2em; text-transform:uppercase; color:var(--ash);}
.tagline.hot{color:var(--ember);}

/* the roll, held on screen for combat shots */
.roll{display:inline-flex; align-items:stretch; gap:0; font-family:var(--mono);
  font-variant-numeric:tabular-nums; border:1px solid var(--edge); border-radius:3px;
  overflow:hidden; font-size:13px;}
.roll span{padding:6px 11px; background:var(--stone);}
.roll .d{background:var(--stone-lit); font-size:17px; font-weight:600; min-width:44px;}
.roll .verdict{font-weight:600; letter-spacing:.08em;}
.roll .verdict.hit{color:var(--verd); background:var(--verd-glow);}
.roll .verdict.miss{color:var(--kiln); background:var(--kiln-glow);}

/* ---------- map ---------- */
.mapstrip{display:flex; gap:6px; align-items:stretch; overflow-x:auto; padding-bottom:2px;}
.node{flex:1 1 0; min-width:104px; border:1px solid var(--edge); border-radius:3px;
  background:var(--stone); padding:8px 9px; transition:border-color .4s, background .4s, opacity .4s;}
.node.here{border-color:var(--ember); background:var(--ember-glow);}
.node.sealed{opacity:.32;}
.node.closing{border-color:var(--kiln);}
.node .nm{font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ash);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.node .occ{display:flex; gap:3px; flex-wrap:wrap; margin-top:6px; min-height:9px;}
.node .occ i{width:8px; height:8px; border-radius:50%; display:block;}
.node .flag{font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; margin-top:5px;}
.node .flag.lit{color:var(--verd);} .node .flag.shut{color:var(--kiln);}

/* ---------- cast ---------- */
.cast{display:grid; grid-template-columns:repeat(auto-fit,minmax(122px,1fr)); gap:6px;}
.card{border:1px solid var(--edge); border-radius:3px; background:var(--stone);
  padding:8px 9px; transition:opacity .5s, filter .5s, border-color .4s, transform .4s;}
.card.focus{border-color:var(--ember); transform:translateY(-2px);}
.card.out{opacity:.34; filter:grayscale(1);}
.card .nm{font-size:12px; font-weight:600; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis;}
.card .bd{font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:var(--ash-dim);}
.hp{height:3px; background:var(--edge); border-radius:2px; margin:6px 0 4px; overflow:hidden;}
.hp i{display:block; height:100%; background:var(--verd); transition:width .5s ease, background .5s;}
.hp i.hurt{background:var(--ember);} .hp i.dire{background:var(--kiln);}
.card .row{display:flex; justify-content:space-between; font-size:10.5px; color:var(--ash);
  font-family:var(--mono); font-variant-numeric:tabular-nums;}
.crownmark{color:var(--ember); font-weight:700;}

/* ---------- transport ---------- */
.transport{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
button.t{background:var(--stone); color:var(--bone); border:1px solid var(--edge);
  border-radius:3px; padding:7px 14px; font:inherit; font-size:12.5px; cursor:pointer;
  transition:border-color .2s, background .2s;}
button.t:hover{border-color:var(--ember); background:var(--stone-lit);}
button.t[aria-pressed="true"]{border-color:var(--ember); color:var(--ember);}
.progress{flex:1 1 160px; height:3px; background:var(--edge); border-radius:2px;
  position:relative; overflow:hidden; min-width:120px;}
.progress i{display:block; height:100%; background:var(--ember); width:0%; transition:width .3s;}
.counter{font-family:var(--mono); font-size:12px; color:var(--ash);
  font-variant-numeric:tabular-nums;}
.hint{font-size:11px; color:var(--ash-dim);}

/* ---------- finale ---------- */
.finalcard{border:1px solid var(--ember-deep); border-radius:4px; background:var(--stone);
  padding:16px; display:none;}
.finalcard.show{display:block;}
.finalcard h2{font-family:var(--serif); margin:0 0 10px; font-size:20px;}
.places{display:flex; flex-direction:column; gap:4px;}
.place{display:flex; align-items:center; gap:10px; font-size:13px; padding:5px 8px;
  border-radius:2px; background:var(--void);}
.place .pn{font-family:var(--mono); color:var(--ash); width:2ch;}
.place .sc{margin-left:auto; font-family:var(--mono); font-variant-numeric:tabular-nums;}
.place.win{background:var(--ember-glow); color:var(--ember);}

@media (prefers-reduced-motion: reduce){
  .ev *{transition:none !important; animation:none !important;}
}
@media (max-width:560px){
  .cast{grid-template-columns:repeat(auto-fit,minmax(96px,1fr));}
  .acts{margin-left:0; width:100%;}
}
</style>

<div class="ev">
  <div class="chapterbar">
    <h1 id="title"></h1>
    <div class="sub" id="subtitle"></div>
    <div class="acts" id="acts"></div>
  </div>

  <div class="stage" id="stage">
    <div class="locus" id="locus"></div>
    <p class="line" id="line"></p>
    <p class="quote" id="quote"></p>
    <div class="who" id="who"></div>
    <div id="rollbox"></div>
    <div class="tagline" id="tagline"></div>
  </div>

  <div class="mapstrip" id="map"></div>

  <div class="transport">
    <button class="t" id="play" type="button">Pause</button>
    <button class="t" id="prev" type="button" aria-label="Previous beat">&larr;</button>
    <button class="t" id="next" type="button" aria-label="Next beat">&rarr;</button>
    <button class="t" id="restart" type="button">Restart</button>
    <div class="progress"><i id="bar"></i></div>
    <div class="counter" id="counter"></div>
  </div>
  <div class="hint">Space plays and pauses &middot; arrow keys step &middot; every line, roll and death below came from the recorded match</div>

  <div class="cast" id="cast"></div>

  <div class="finalcard" id="finale">
    <h2>Final Standing</h2>
    <div class="places" id="places"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const BEATS = DATA.beats, ROSTER = DATA.roster, ROOMS = DATA.rooms;
const byId = Object.fromEntries(ROSTER.map(a => [a.id, a]));

const $ = id => document.getElementById(id);
const T = (el, s) => { el.textContent = s == null ? "" : String(s); };

const WASH = { crown:"var(--ember-glow)", finale:"var(--ember-glow)",
  death:"var(--kiln-glow)", mishap:"var(--kiln-glow)", closing:"var(--kiln-glow)",
  world:"var(--verd-glow)", chapter:"var(--ember-glow)" };
const TAG = { mishap:"Wild Swing", death:"Eliminated", crown:"The Ember Crown",
  closing:"The dungeon closes", finale:"Extraction", chapter:"" };

let i = 0, playing = true, timer = null, speed = 1;

const MAJORKINDS = new Set(["chapter","crown","death","finale"]);
function shotDuration(b){
  // Big moments hold; ordinary beats move; a line of dialogue needs reading time.
  const base = MAJORKINDS.has(b.kind) ? 2800 : 1900;
  return (base + (b.speech ? 700 : 0)) / speed;
}

function render(){
  const b = BEATS[i];
  if (!b) return;
  const st = $("stage");
  st.className = "stage " + b.kind;
  st.style.setProperty("--wash", WASH[b.kind] || "transparent");

  T($("locus"), b.kind === "chapter" ? ("Act " + b.act) :
     (ROOMS[b.room] || "") + (b.room ? "  ·  " : "") + "Round " + b.round);

  T($("line"), b.kind === "chapter" ? b.act_name : b.text);

  const q = $("quote");
  T(q, b.speech ? "“" + b.speech + "”" : "");
  q.style.display = b.speech ? "" : "none";

  const who = $("who"); who.replaceChildren();
  const a = byId[b.actor];
  if (a && b.kind !== "chapter"){
    const dot = document.createElement("span"); dot.className = "dot";
    dot.style.background = a.color; who.appendChild(dot);
    const nm = document.createElement("span"); T(nm, a.name); who.appendChild(nm);
  }

  const rb = $("rollbox"); rb.replaceChildren();
  if (b.roll && b.roll.die != null){
    const w = document.createElement("div"); w.className = "roll";
    const mk = (cls, txt) => { const s = document.createElement("span");
      s.className = cls; T(s, txt); w.appendChild(s); };
    mk("d", "d20 " + b.roll.die);
    if (b.roll.power != null) mk("", "+" + b.roll.power + " pow");
    if (b.roll.dc != null) mk("", "vs " + b.roll.dc);
    mk("verdict " + (b.roll.hit ? "hit" : "miss"), b.roll.hit ? "HIT" : "MISS");
    rb.appendChild(w);
  }

  const tg = $("tagline");
  tg.className = "tagline" + (b.kind === "crown" || b.kind === "finale" ? " hot" : "");
  T(tg, TAG[b.kind] || "");

  drawMap(b); drawCast(b);
  $("bar").style.width = ((i + 1) / BEATS.length * 100) + "%";
  T($("counter"), (i + 1) + " / " + BEATS.length);
  $("acts").querySelectorAll(".actpip").forEach(p => {
    p.classList.toggle("on", Number(p.dataset.act) === b.act);
  });
  $("finale").classList.toggle("show", i >= BEATS.length - 1);
}

function drawMap(b){
  const m = $("map"); m.replaceChildren();
  for (const rid of DATA.room_order){
    const n = document.createElement("div");
    n.className = "node" + (b.room === rid ? " here" : "")
      + ((b.state.sealed || []).includes(rid) ? " sealed" : "")
      + ((b.state.contracting || []).includes(rid) ? " closing" : "");
    const nm = document.createElement("div"); nm.className = "nm";
    T(nm, ROOMS[rid] || rid); n.appendChild(nm);
    const occ = document.createElement("div"); occ.className = "occ";
    for (const a of ROSTER){
      const s = b.state.agents[a.id];
      if (s && s.room === rid && s.status !== "eliminated"){
        const d = document.createElement("i"); d.style.background = a.color;
        d.title = a.name; occ.appendChild(d);
      }
    }
    n.appendChild(occ);
    const seals = b.state.seals || {};
    if (rid in seals){
      const f = document.createElement("div");
      f.className = "flag " + (seals[rid] ? "lit" : "");
      T(f, seals[rid] ? "seal lit" : "seal dark"); n.appendChild(f);
    } else if ((b.state.sealed || []).includes(rid)){
      const f = document.createElement("div"); f.className = "flag shut";
      T(f, "collapsed"); n.appendChild(f);
    }
    m.appendChild(n);
  }
}

function drawCast(b){
  const c = $("cast"); c.replaceChildren();
  const crown = b.state.crown || {};
  for (const a of ROSTER){
    const s = b.state.agents[a.id] || {};
    const card = document.createElement("div");
    const involved = (b.actor === a.id || b.target === a.id);
    card.className = "card" + (involved ? " focus" : "")
      + (s.status === "eliminated" ? " out" : "");
    card.style.borderLeft = "2px solid " + a.color;
    const nm = document.createElement("div"); nm.className = "nm"; T(nm, a.name);
    card.appendChild(nm);
    const bd = document.createElement("div"); bd.className = "bd"; T(bd, a.build);
    card.appendChild(bd);
    const hp = document.createElement("div"); hp.className = "hp";
    const fill = document.createElement("i");
    const pct = s.max_hp ? Math.max(0, s.hp) / s.max_hp : 0;
    fill.style.width = (pct * 100) + "%";
    fill.className = pct <= .25 ? "dire" : (pct <= .55 ? "hurt" : "");
    hp.appendChild(fill); card.appendChild(hp);
    const row = document.createElement("div"); row.className = "row";
    const l = document.createElement("span");
    T(l, s.status === "eliminated" ? "dead" : (s.hp + "/" + s.max_hp));
    row.appendChild(l);
    const r = document.createElement("span");
    if (crown.carrier_id === a.id){
      r.className = "crownmark";
      T(r, "CROWN " + (crown.attunement_rounds || 0) + "/2");
    } else { T(r, (s.score ?? 0) + " pts"); }
    row.appendChild(r); card.appendChild(row);
    c.appendChild(card);
  }
}

function step(n){
  i = Math.min(BEATS.length - 1, Math.max(0, i + n));
  render();
  if (playing) schedule();
}
function schedule(){
  clearTimeout(timer);
  if (i >= BEATS.length - 1){ setPlaying(false); return; }
  timer = setTimeout(() => { i++; render(); schedule(); }, shotDuration(BEATS[i]));
}
function setPlaying(p){
  playing = p; T($("play"), p ? "Pause" : "Play");
  $("play").setAttribute("aria-pressed", String(p));
  clearTimeout(timer); if (p) schedule();
}

$("play").addEventListener("click", () => setPlaying(!playing));
$("next").addEventListener("click", () => { setPlaying(false); step(1); });
$("prev").addEventListener("click", () => { setPlaying(false); step(-1); });
$("restart").addEventListener("click", () => { i = 0; render(); setPlaying(true); });
document.addEventListener("keydown", e => {
  if (e.key === " "){ e.preventDefault(); setPlaying(!playing); }
  else if (e.key === "ArrowRight"){ setPlaying(false); step(1); }
  else if (e.key === "ArrowLeft"){ setPlaying(false); step(-1); }
});

(function init(){
  T($("title"), DATA.title);
  T($("subtitle"), DATA.subtitle);
  const acts = $("acts");
  for (const a of DATA.acts){
    const p = document.createElement("div"); p.className = "actpip";
    p.dataset.act = a.act; T(p, a.name); acts.appendChild(p);
  }
  const places = $("places");
  for (const a of DATA.standing){
    const row = document.createElement("div");
    row.className = "place" + (a.placement === 1 ? " win" : "");
    const pn = document.createElement("span"); pn.className = "pn"; T(pn, a.placement);
    row.appendChild(pn);
    const dot = document.createElement("span"); dot.className = "dot";
    dot.style.cssText = "width:8px;height:8px;border-radius:50%;background:" + a.color;
    row.appendChild(dot);
    const nm = document.createElement("span"); T(nm, a.name + (a.status === "escaped" ? " — escaped with the Crown" : ""));
    row.appendChild(nm);
    const sc = document.createElement("span"); sc.className = "sc"; T(sc, a.final_score + " pts");
    row.appendChild(sc);
    places.appendChild(row);
  }
  render(); setPlaying(true);
})();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="demo/summary.json")
    ap.add_argument("--out", default="demo/story.html")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    summary = json.loads((root / args.summary).read_text(encoding="utf-8"))
    beats = build_beats(summary)

    acts, seen = [], set()
    for b in beats:
        if b["act"] not in seen and b["act"] is not None:
            seen.add(b["act"])
            acts.append({"act": b["act"], "name": b["act_name"] or f"Act {b['act']}"})

    standing = sorted(summary["roster"], key=lambda a: a.get("placement") or 99)
    winner = next((a for a in standing if a.get("placement") == 1), None)

    data = {
        "title": "The Chronicle of Seed 52",
        "subtitle": f"{summary['match_id']}  ·  {summary['ruleset_version']}  ·  "
        f"{summary['rounds']} rounds  ·  won by {winner['name'] if winner else 'nobody'}",
        "beats": beats,
        "roster": summary["roster"],
        "standing": standing,
        "acts": acts,
        "rooms": ROOM_LABEL,
        "room_order": ROOM_ORDER,
    }

    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # </script> inside embedded data would close the tag early.
    payload = payload.replace("</", "<\\/")
    out = root / args.out
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {args.out}: {len(beats)} beats, {len(acts)} acts, {out.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
