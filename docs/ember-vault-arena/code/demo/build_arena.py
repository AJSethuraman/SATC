"""Render the replay as a top-down dungeon board with sprites that walk it.

The story viewer fixed the pacing but kept an abstract room strip, so nothing
ever visibly *moved*.  This lays the five rooms out spatially -- Threshold at the
bottom, the Ironwood and Ossuary routes branching left and right, the Vault above
them, the Egress at the top -- and puts a sprite on the board for every
contestant and monster.  When an agent changes room the sprite walks there;
when a seal lights the chamber changes colour; when the map contracts the
chamber collapses with everyone still inside shoved toward the Vault.

Every sprite is inline SVG built from a small pixel grid, because the artifact
CSP blocks external images and a silent broken-image is worse than no art.

Usage:
    python3 demo/build_arena.py [--summary demo/summary.json] [--out demo/arena.html]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_story import build_beats  # noqa: E402
from arena import grid as arena_grid  # noqa: E402
from arena import rules as arena_rules  # noqa: E402

# Board geometry: a diamond that matches the real adjacency graph.
#   egress            (top, the way out)
#   vault             (the Warden, the Crown)
#   ironwood / ossuary  (the two routes, side by side)
#   threshold         (bottom, where everyone starts)
LAYOUT = {
    "threshold":     {"x": 500, "y": 596, "w": 210, "h": 132, "label": "The Threshold"},
    "ironwood_gate": {"x": 196, "y": 392, "w": 210, "h": 172, "label": "Ironwood Gate"},
    "ossuary_gate":  {"x": 804, "y": 392, "w": 210, "h": 172, "label": "Ossuary Gate"},
    "vault":         {"x": 500, "y": 214, "w": 294, "h": 214, "label": "The Ember Vault"},
    "egress":        {"x": 500, "y": 58,  "w": 132, "h": 92,  "label": "Moonlit Egress"},
}
CORRIDORS = [
    ("threshold", "ironwood_gate"), ("threshold", "ossuary_gate"),
    ("ironwood_gate", "vault"), ("ossuary_gate", "vault"), ("vault", "egress"),
]
MONSTER_ROOM = {
    "ironwood_guardian": "ironwood_gate",
    "ossuary_guardian": "ossuary_gate",
    "crown_warden": "vault",
}

TEMPLATE = """<title>Ember Vault Arena — The Board</title>
<style>
:root{
  --void:#080706; --stone:#141009; --floor:#1e1810; --floor-lit:#2a2116;
  --edge:#3a2e20; --bone:#f2e9d8; --ash:#8e8071; --ash-dim:#5d5347;
  --ember:#ff8a24; --ember-deep:#b4550a; --ember-glow:rgba(255,138,36,.18);
  --kiln:#e0442c; --verd:#4fc79f; --gold:#ffd166;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:"Avenir Next","Segoe UI",Roboto,system-ui,-apple-system,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
:root[data-theme="light"]{ --void:#191309; --stone:#221a10; --floor:#2b2116; --bone:#f8f1e4; }
*,*::before,*::after{box-sizing:border-box;}
.ar{background:var(--void); color:var(--bone); font-family:var(--sans);
  min-height:100vh; padding:clamp(10px,2vw,22px); max-width:1220px; margin:0 auto;
  display:flex; flex-direction:column; gap:10px; overflow-x:hidden;}
.ar :focus-visible{outline:2px solid var(--ember); outline-offset:2px;}

.hdr{display:flex; align-items:baseline; gap:12px; flex-wrap:wrap;
  border-bottom:1px solid var(--edge); padding-bottom:8px;}
.hdr h1{font-family:var(--serif); font-size:clamp(16px,2vw,21px); margin:0; font-weight:600;}
.hdr .sub{font-size:11.5px; color:var(--ash); letter-spacing:.08em; text-transform:uppercase;}
.hdr .act{margin-left:auto; font-size:11.5px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ember); border:1px solid var(--ember-deep); background:var(--ember-glow);
  padding:3px 11px; border-radius:2px;}

.boardwrap{position:relative; border:1px solid var(--edge); border-radius:4px;
  background:radial-gradient(90% 70% at 50% 12%, var(--stone) 0%, var(--void) 78%);
  overflow:hidden;}
svg.board{display:block; width:100%; height:auto;}

.chamber{transition:opacity .5s ease;}
.chamber rect.floor{fill:var(--floor); stroke:var(--edge); stroke-width:2;
  transition:fill .5s ease, stroke .5s ease;}
.chamber.active rect.floor{fill:var(--floor-lit); stroke:var(--ember);}
.chamber.sealed{opacity:.24;}
.chamber.closing rect.floor{stroke:var(--kiln); stroke-dasharray:7 5;}
.chamber text.rn{fill:var(--ash); font-size:12px; letter-spacing:.14em;
  text-transform:uppercase; font-family:var(--sans);}
.chamber.active text.rn{fill:var(--ember);}
.cell{fill:rgba(255,255,255,.022); stroke:rgba(255,255,255,.05); stroke-width:.7;}
.prop .pshape{stroke-width:1;}
.prop.blocking .pshape{fill:#3b3128; stroke:#54463a;}
.prop.cover .pshape{fill:rgba(79,199,159,.20); stroke:var(--verd);}
.prop.hazard .pshape{fill:rgba(224,68,44,.14); stroke:var(--kiln);}
.prop.hazard .pcore{fill:var(--kiln); opacity:.85;}
.legend{display:flex; gap:14px; flex-wrap:wrap; font-size:11px; color:var(--ash);
  align-items:center;}
.legend i{width:9px; height:9px; display:inline-block; margin-right:5px;
  vertical-align:-1px; border:1px solid;}
.legend i.blk{background:#3b3128; border-color:#54463a;}
.legend i.cov{background:rgba(79,199,159,.20); border-color:var(--verd); border-radius:50% 50% 2px 2px;}
.legend i.haz{background:rgba(224,68,44,.30); border-color:var(--kiln); border-radius:50%;}
.cell.door{fill:rgba(255,138,36,.10); stroke:rgba(255,138,36,.30);}
.cell.feat{fill:rgba(79,199,159,.11); stroke:rgba(79,199,159,.30);}
.corridor{stroke:var(--edge); stroke-width:9; stroke-linecap:round; fill:none;
  transition:stroke .5s;}
.corridor.dead{stroke:#1a140e;}

.sprite{transition:transform .62s cubic-bezier(.5,.05,.3,1), opacity .5s;}
.sprite.gone{opacity:.18; filter:grayscale(1);}
.sprite .nameplate{font-size:9.5px; font-family:var(--sans); text-anchor:middle;}
.sprite.act .ring{opacity:1;} .sprite .ring{opacity:0; transition:opacity .3s;}
.hpbar rect.bg{fill:#000; opacity:.55;} .hpbar rect.fg{transition:width .45s ease;}

.bubble rect{fill:#f6efe0; stroke:#0a0806; stroke-width:1.5;}
.bubble text{fill:#14100b; font-family:var(--sans); font-size:11.5px;}
.fx{font-family:var(--mono); font-weight:700; font-size:17px; text-anchor:middle;}

.crownicon{filter:drop-shadow(0 0 6px var(--ember));}

.caption{min-height:56px; display:flex; flex-direction:column; justify-content:center;
  gap:4px; padding:9px 13px; border:1px solid var(--edge); border-radius:4px;
  background:var(--stone);}
.caption .ln{font-family:var(--serif); font-size:clamp(15px,2vw,20px); line-height:1.28;
  text-wrap:balance;}
.caption .meta{font-size:11px; color:var(--ash); letter-spacing:.1em; text-transform:uppercase;
  display:flex; gap:10px; align-items:center; flex-wrap:wrap;}
.caption .meta .roll{font-family:var(--mono); letter-spacing:0; text-transform:none;
  border:1px solid var(--edge); padding:1px 7px; border-radius:2px;}
.caption .meta .roll.hit{color:var(--verd);} .caption .meta .roll.miss{color:var(--kiln);}
.caption.mishap{border-color:var(--kiln);} .caption.crown,.caption.finale{border-color:var(--ember);}
.caption.death{border-color:var(--kiln); background:#1a0f0c;}

.tray{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
button.b{background:var(--stone); color:var(--bone); border:1px solid var(--edge);
  border-radius:3px; padding:6px 13px; font:inherit; font-size:12.5px; cursor:pointer;}
button.b:hover{border-color:var(--ember);}
button.b[aria-pressed="true"]{border-color:var(--ember); color:var(--ember);}
.prog{flex:1 1 140px; min-width:110px; height:3px; background:var(--edge); border-radius:2px;}
.prog i{display:block; height:100%; background:var(--ember); width:0; transition:width .3s;}
.cnt{font-family:var(--mono); font-size:11.5px; color:var(--ash);
  font-variant-numeric:tabular-nums;}
.hint{font-size:11px; color:var(--ash-dim);}

.final{display:none; border:1px solid var(--ember-deep); border-radius:4px;
  background:var(--stone); padding:13px;}
.final.show{display:block;}
.final h2{font-family:var(--serif); margin:0 0 8px; font-size:18px;}
.pl{display:flex; align-items:center; gap:9px; font-size:12.5px; padding:4px 7px;
  border-radius:2px; background:var(--void); margin-bottom:3px;}
.pl .n{font-family:var(--mono); color:var(--ash); width:2ch;}
.pl .s{margin-left:auto; font-family:var(--mono); font-variant-numeric:tabular-nums;}
.pl.win{background:var(--ember-glow); color:var(--ember);}
@media (prefers-reduced-motion: reduce){ .ar *{transition:none !important;} }
</style>

<div class="ar">
  <div class="hdr">
    <h1 id="ttl"></h1><div class="sub" id="sub"></div><div class="act" id="actlbl"></div>
  </div>
  <div class="boardwrap">
    <svg class="board" id="board" viewBox="0 0 1000 680" role="img"
         aria-label="Top-down dungeon board showing contestants moving between five chambers"></svg>
  </div>
  <div class="caption" id="cap">
    <div class="ln" id="capline"></div>
    <div class="meta" id="capmeta"></div>
  </div>
  <div class="tray">
    <button class="b" id="play" type="button">Pause</button>
    <button class="b" id="prev" type="button" aria-label="Previous beat">&larr;</button>
    <button class="b" id="next" type="button" aria-label="Next beat">&rarr;</button>
    <button class="b" id="rst" type="button">Restart</button>
    <div class="prog"><i id="bar"></i></div><div class="cnt" id="cnt"></div>
  </div>
  <div class="legend">
    <span><i class="blk"></i>impassable</span>
    <span><i class="cov"></i>cover &mdash; +1 Armor</span>
    <span><i class="haz"></i>hazard &mdash; 1 damage on entry</span>
  </div>
  <div class="hint">Space plays and pauses &middot; arrows step &middot; sprites walk the same rooms the referee recorded</div>
  <div class="final" id="final"><h2>Final Standing</h2><div id="places"></div></div>
</div>

<script>
const DATA = __DATA__;
const B = DATA.beats, ROSTER = DATA.roster, L = DATA.layout, CORR = DATA.corridors;
const MROOM = DATA.monster_rooms;
const byId = Object.fromEntries(ROSTER.map(a => [a.id, a]));
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
const el = (n, at) => { const e = document.createElementNS(NS, n);
  for (const k in (at||{})) e.setAttribute(k, at[k]); return e; };
const T = (e, s) => { e.textContent = s == null ? "" : String(s); };

/* ---- pixel sprites -------------------------------------------------------
   Each build is a list of [x,y,w,h,role] cells on a 12x16 grid. Roles resolve
   against the contestant's own colour so eight rivals stay tellable apart. */
const SPRITES = {
  vanguard: [[3,1,6,3,"met"],[4,3,4,2,"skin"],[2,5,8,6,"main"],[1,5,2,2,"met"],[9,5,2,2,"met"],
             [0,5,2,6,"met"],[3,11,2,5,"dark"],[7,11,2,5,"dark"],[10,2,1,9,"met"]],
  scout:    [[4,1,5,3,"main"],[5,4,3,2,"skin"],[4,6,4,5,"main"],[3,6,1,7,"dark"],
             [4,11,2,5,"dark"],[7,11,2,5,"dark"],[8,7,2,1,"met"]],
  mystic:   [[3,0,7,2,"main"],[2,2,9,1,"main"],[4,3,4,2,"skin"],[3,5,6,6,"main"],
             [2,11,8,5,"main"],[10,1,1,14,"dark"],[9,0,3,2,"accent"]],
  scoundrel:[[3,1,6,3,"dark"],[4,4,4,2,"skin"],[3,6,6,5,"main"],[2,5,1,8,"dark"],
             [9,5,1,8,"dark"],[4,11,2,5,"dark"],[7,11,2,5,"dark"]],
};
const MONSTER_SPRITE = [[2,2,10,4,"main"],[1,6,12,7,"main"],[0,6,2,5,"dark"],[12,6,2,5,"dark"],
  [3,13,3,3,"dark"],[8,13,3,3,"dark"],[4,3,2,2,"eye"],[8,3,2,2,"eye"]];

function shade(hex, f){
  const n = parseInt(hex.slice(1), 16);
  const r = Math.round(((n>>16)&255)*f), g = Math.round(((n>>8)&255)*f), b = Math.round((n&255)*f);
  return "rgb(" + Math.min(255,r) + "," + Math.min(255,g) + "," + Math.min(255,b) + ")";
}
function drawSprite(parent, cells, color, px, opts){
  const pal = { main: color, dark: shade(color,.5), met:"#9aa4ad", skin:"#e8c9a4",
    accent:"var(--gold)", eye:"#ffe27a" };
  for (const [x,y,w,h,role] of cells){
    parent.appendChild(el("rect", { x:x*px, y:y*px, width:w*px, height:h*px,
      fill: pal[role] || color, "shape-rendering":"crispEdges" }));
  }
}

/* ---- board ---------------------------------------------------------------- */
/* A tile's centre in board coordinates. Cells are inset from the chamber wall
   so a sprite standing on the edge still reads as inside the room. */
const PAD = 15, HEAD = 15;
function cellSize(room){
  const r = L[room], g = DATA.grids[room];
  if (!r || !g) return { cw: 20, ch: 20, x0: (r||{}).x || 0, y0: (r||{}).y || 0 };
  const usableW = r.w - PAD*2, usableH = r.h - PAD*2 - HEAD;
  return {
    cw: usableW / g.w, ch: usableH / g.h,
    x0: r.x - r.w/2 + PAD, y0: r.y - r.h/2 + PAD + HEAD,
  };
}
function tileXY(room, tile){
  const g = DATA.grids[room], r = L[room];
  if (!g || !r) return { x: 500, y: 660 };
  const t = (tile && tile.length === 2) ? tile : [Math.floor(g.w/2), g.h-1];
  const { cw, ch, x0, y0 } = cellSize(room);
  return { x: x0 + (t[0] + .5) * cw, y: y0 + (t[1] + .5) * ch };
}

function buildBoard(){
  const svg = $("board"); svg.replaceChildren();
  const gC = el("g"), gR = el("g"), gP = el("g"), gM = el("g"), gA = el("g"), gF = el("g");
  gF.setAttribute("id","fxlayer");
  for (const [a,b] of CORR){
    const p = el("line", { x1:L[a].x, y1:L[a].y, x2:L[b].x, y2:L[b].y, class:"corridor" });
    p.dataset.a = a; p.dataset.b = b; gC.appendChild(p);
  }
  for (const rid in L){
    const r = L[rid];
    const g = el("g", { class:"chamber" }); g.dataset.room = rid;
    g.appendChild(el("rect", { class:"floor", x:r.x-r.w/2, y:r.y-r.h/2,
      width:r.w, height:r.h, rx:5 }));
    const t = el("text", { class:"rn", x:r.x-r.w/2+9, y:r.y-r.h/2+18 });
    T(t, r.label); g.appendChild(t);
    // The tactical grid: the spaces bodies actually stand on and move between.
    const gd = DATA.grids[rid];
    if (gd){
      const { cw, ch, x0, y0 } = cellSize(rid);
      const cells = el("g", { class:"cells" });
      for (let cx = 0; cx < gd.w; cx++){
        for (let cy = 0; cy < gd.h; cy++){
          const isDoor = Object.values(gd.doors || {})
            .some(d => d[0] === cx && d[1] === cy);
          const feat = Object.entries(gd.features || {})
            .find(([, f]) => f[0] === cx && f[1] === cy);
          const cell = el("rect", {
            class: "cell" + (isDoor ? " door" : "") + (feat ? " feat" : ""),
            x: x0 + cx*cw + 1, y: y0 + cy*ch + 1,
            width: Math.max(1, cw-2), height: Math.max(1, ch-2), rx: 1.5,
          });
          cell.dataset.room = rid; cell.dataset.tile = cx + "," + cy;
          cells.appendChild(cell);
        }
      }
      // Props: terrain the rules actually read, drawn so the board explains
      // itself without a legend lookup.
      for (const pr of (gd.props || [])){
        const c = tileXY(rid, pr.tile);
        const pg = el("g", { class:"prop " + pr.kind });
        const s2 = Math.min(cw, ch) * .42;
        if (pr.kind === "blocking"){
          pg.appendChild(el("rect", { x:c.x-s2, y:c.y-s2, width:s2*2, height:s2*2,
            rx:1.5, class:"pshape" }));
        } else if (pr.kind === "cover"){
          pg.appendChild(el("path", {
            d:"M"+(c.x-s2)+","+(c.y+s2)+" L"+(c.x-s2)+","+(c.y-s2*.2)+" L"+c.x+","+(c.y-s2)
              +" L"+(c.x+s2)+","+(c.y-s2*.2)+" L"+(c.x+s2)+","+(c.y+s2)+" Z",
            class:"pshape" }));
        } else {
          pg.appendChild(el("circle", { cx:c.x, cy:c.y, r:s2*.8, class:"pshape" }));
          pg.appendChild(el("circle", { cx:c.x, cy:c.y, r:s2*.38, class:"pcore" }));
        }
        const ttl = el("title"); ttl.textContent = pr.name; pg.appendChild(ttl);
        cells.appendChild(pg);
      }
      g.appendChild(cells);
    }
    gR.appendChild(g);
  }
  // props: seal glyphs on the two routes, pedestal in the vault, arch at the egress
  for (const rid of ["ironwood_gate","ossuary_gate"]){
    const r = L[rid];
    const g = el("g", { class:"seal" }); g.dataset.seal = rid;
    g.appendChild(el("circle", { cx:r.x+r.w/2-24, cy:r.y-r.h/2+22, r:9,
      fill:"none", stroke:"var(--ash-dim)", "stroke-width":2.5 }));
    gP.appendChild(g);
  }
  const vr = L["vault"];
  const ped = el("g", { id:"pedestal" });
  ped.appendChild(el("rect", { x:vr.x-13, y:vr.y-vr.h/2+16, width:26, height:9,
    fill:"var(--edge)" }));
  gP.appendChild(ped);
  svg.append(gC, gR, gP, gM, gA, gF);
  window.__layers = { corridors:gC, rooms:gR, props:gP, monsters:gM, agents:gA, fx:gF };

  // monsters
  for (const mid in MROOM){
    const g = el("g", { class:"sprite" }); g.dataset.mon = mid;
    const inner = el("g");
    const big = mid === "crown_warden";
    drawSprite(inner, MONSTER_SPRITE, big ? "#8d2f22" : "#6d4530", big ? 2.6 : 2.1);
    inner.setAttribute("transform", "translate(" + (big?-18:-15) + ",-" + (big?34:28) + ")");
    g.appendChild(inner);
    if (big){
      const c = el("g", { class:"crownicon" });
      c.appendChild(el("path", { d:"M-11,-46 L-7,-56 L0,-49 L7,-56 L11,-46 Z", fill:"var(--gold)" }));
      g.appendChild(c);
    }
    gM.appendChild(g);
  }
  // agents
  ROSTER.forEach(a => {
    const g = el("g", { class:"sprite" }); g.dataset.agent = a.id;
    g.appendChild(el("ellipse", { class:"ring", cx:0, cy:2, rx:17, ry:7,
      fill:"none", stroke:a.color, "stroke-width":2 }));
    const inner = el("g", { transform:"translate(-7.5,-19)" });
    drawSprite(inner, SPRITES[a.build] || SPRITES.scout, a.color, 1.25);
    g.appendChild(inner);
    const hp = el("g", { class:"hpbar", transform:"translate(-9,-25)" });
    hp.appendChild(el("rect", { class:"bg", x:-1, y:-1, width:20, height:4.5, rx:1 }));
    const fg = el("rect", { class:"fg", x:0, y:0, width:18, height:2.5, fill:"var(--verd)" });
    hp.appendChild(fg); g.appendChild(hp);
    const nm = el("text", { class:"nameplate", y:16, fill:a.color });
    T(nm, a.name.split(" ")[0]); g.appendChild(nm);
    gA.appendChild(g);
  });
}

/* ---- per-beat render ------------------------------------------------------ */
let i = 0, playing = true, timer = null;
const MAJOR = new Set(["chapter","crown","death","finale"]);

function render(prev){
  const b = B[i]; if (!b) return;
  const st = b.state, agents = st.agents || {};

  // chambers
  for (const g of window.__layers.rooms.children){
    const rid = g.dataset.room;
    g.classList.toggle("active", b.room === rid);
    g.classList.toggle("sealed", (st.sealed||[]).includes(rid));
    g.classList.toggle("closing", (st.contracting||[]).includes(rid));
  }
  for (const c of window.__layers.corridors.children){
    const dead = (st.sealed||[]).includes(c.dataset.a) || (st.sealed||[]).includes(c.dataset.b);
    c.classList.toggle("dead", dead);
  }
  for (const g of window.__layers.props.children){
    if (!g.dataset.seal) continue;
    const lit = (st.seals||{})[g.dataset.seal];
    const circ = g.querySelector("circle");
    circ.setAttribute("stroke", lit ? "var(--verd)" : "var(--ash-dim)");
    circ.setAttribute("fill", lit ? "rgba(79,199,159,.28)" : "none");
  }

  // Live positions, advanced move-by-move, not the end-of-round snapshot --
  // otherwise every sprite jumps to its final room on the round's first beat.
  const where = b.pos || {};
  const occupancy = {};
  ROSTER.forEach(a => { const r = where[a.id]; if (r) (occupancy[r] ||= []).push(a.id); });

  for (const g of window.__layers.agents.children){
    const id = g.dataset.agent, s = agents[id] || {};
    const dead = s.status === "eliminated";
    g.classList.toggle("gone", dead);
    g.classList.toggle("act", b.actor === id || b.target === id);
    const room = where[id];
    const p = tileXY(room, (b.tiles || {})[id]);
    g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
    const fg = g.querySelector(".hpbar .fg");
    const pct = s.max_hp ? Math.max(0, s.hp)/s.max_hp : 0;
    fg.setAttribute("width", (18*pct).toFixed(1));
    fg.setAttribute("fill", pct <= .25 ? "var(--kiln)" : (pct <= .55 ? "var(--ember)" : "var(--verd)"));
  }
  for (const g of window.__layers.monsters.children){
    const room = MROOM[g.dataset.mon];
    const alive = (st.monsters_alive || []).includes(g.dataset.mon);
    g.classList.toggle("gone", !alive);
    const mt = (DATA.monster_tiles || {})[g.dataset.mon];
    const p = tileXY(room, mt);
    g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
  }

  // caption
  const cap = $("cap"); cap.className = "caption " + b.kind;
  T($("capline"), b.kind === "chapter" ? b.act_name : b.text);
  const meta = $("capmeta"); meta.replaceChildren();
  const add = (cls, txt) => { const s = document.createElement("span");
    if (cls) s.className = cls; T(s, txt); meta.appendChild(s); };
  add("", "Round " + b.round);
  if (b.room && L[b.room]) add("", L[b.room].label);
  if (b.roll && b.roll.die != null){
    add("roll " + (b.roll.hit ? "hit" : "miss"),
      "d20 " + b.roll.die + (b.roll.power != null ? " +" + b.roll.power : "")
      + (b.roll.dc != null ? " vs " + b.roll.dc : "") + (b.roll.hit ? "  HIT" : "  MISS"));
  }
  T($("actlbl"), b.act_name || ("Act " + b.act));

  if (b.speech && b.actor) speechBubble(b.actor, b.speech);
  if (b.kind === "mishap" || b.kind === "death" || (b.roll && b.roll.hit)){
    const who = b.target && agents[b.target] ? b.target : b.actor;
    if (who && agents[who]) floatFx(who, b.kind === "death" ? "OUT" : (b.amount ? "-" + b.amount : "hit"),
      b.kind === "death" ? "var(--kiln)" : "var(--ember)");
  }

  $("bar").style.width = ((i+1)/B.length*100) + "%";
  T($("cnt"), (i+1) + " / " + B.length);
  $("final").classList.toggle("show", i >= B.length - 1);
}

function agentPos(id){
  const g = window.__layers.agents.querySelector('[data-agent="' + id + '"]');
  if (!g) return null;
  const m = /translate\\(([-\\d.]+),([-\\d.]+)\\)/.exec(g.getAttribute("transform") || "");
  return m ? { x: +m[1], y: +m[2] } : null;
}
function speechBubble(id, text){
  const p = agentPos(id); if (!p) return;
  const fx = window.__layers.fx;
  const g = el("g", { class:"bubble" });
  const t = text.length > 46 ? text.slice(0,44) + "…" : text;
  const w = Math.max(70, t.length * 6.2 + 16);
  const x = Math.min(940 - w/2, Math.max(60 + w/2, p.x));
  g.appendChild(el("rect", { x:x-w/2, y:p.y-64, width:w, height:24, rx:4 }));
  g.appendChild(el("path", { d:"M"+(x-5)+","+(p.y-40)+" L"+x+","+(p.y-33)+" L"+(x+5)+","+(p.y-40)+" Z",
    fill:"#f6efe0", stroke:"#0a0806", "stroke-width":1.5 }));
  const tx = el("text", { x:x, y:p.y-48, "text-anchor":"middle" }); T(tx, t);
  g.appendChild(tx); fx.appendChild(g);
  setTimeout(() => g.remove(), 2100);
}
function floatFx(id, label, color){
  const p = agentPos(id); if (!p) return;
  const t = el("text", { class:"fx", x:p.x, y:p.y-36, fill:color });
  T(t, label); window.__layers.fx.appendChild(t);
  let y = p.y-36, o = 1;
  const iv = setInterval(() => { y -= 1.4; o -= .045;
    t.setAttribute("y", y); t.setAttribute("opacity", Math.max(0,o).toFixed(2));
    if (o <= 0){ clearInterval(iv); t.remove(); } }, 26);
}

function dur(b){ return (MAJOR.has(b.kind) ? 2700 : 1850) + (b.speech ? 650 : 0); }
function sched(){ clearTimeout(timer);
  if (i >= B.length-1){ setPlay(false); return; }
  timer = setTimeout(() => { i++; render(); sched(); }, dur(B[i])); }
function setPlay(p){ playing = p; T($("play"), p ? "Pause" : "Play");
  $("play").setAttribute("aria-pressed", String(p)); clearTimeout(timer); if (p) sched(); }
function step(n){ i = Math.min(B.length-1, Math.max(0, i+n)); render(); }

$("play").addEventListener("click", () => setPlay(!playing));
$("next").addEventListener("click", () => { setPlay(false); step(1); });
$("prev").addEventListener("click", () => { setPlay(false); step(-1); });
$("rst").addEventListener("click", () => { i = 0; render(); setPlay(true); });
document.addEventListener("keydown", e => {
  if (e.key === " "){ e.preventDefault(); setPlay(!playing); }
  else if (e.key === "ArrowRight"){ setPlay(false); step(1); }
  else if (e.key === "ArrowLeft"){ setPlay(false); step(-1); }
});

(function(){
  T($("ttl"), DATA.title); T($("sub"), DATA.subtitle);
  buildBoard();
  const pl = $("places");
  for (const a of DATA.standing){
    const row = document.createElement("div");
    row.className = "pl" + (a.placement === 1 ? " win" : "");
    const n = document.createElement("span"); n.className = "n"; T(n, a.placement); row.appendChild(n);
    const d = document.createElement("span");
    d.style.cssText = "width:8px;height:8px;border-radius:50%;background:" + a.color; row.appendChild(d);
    const nm = document.createElement("span");
    T(nm, a.name + (a.status === "escaped" ? " — escaped with the Crown" : "")); row.appendChild(nm);
    const s = document.createElement("span"); s.className = "s"; T(s, a.final_score + " pts");
    row.appendChild(s); pl.appendChild(row);
  }
  render(); setPlay(true);
})();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="demo/summary.json")
    ap.add_argument("--out", default="demo/arena.html")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    summary = json.loads((root / args.summary).read_text(encoding="utf-8"))
    beats = build_beats(summary)

    # Which monsters are still standing at each beat, so a corpse stops being drawn.
    alive = set(MONSTER_ROOM)
    for b in beats:
        if b["type"] == "monster_defeated":
            alive.discard(b.get("target") or "")
        b["state"]["monsters_alive"] = sorted(alive)

    standing = sorted(summary["roster"], key=lambda a: a.get("placement") or 99)
    winner = next((a for a in standing if a.get("placement") == 1), None)

    data = {
        "title": "Ember Vault Arena — The Board",
        "subtitle": f"{summary['match_id']} · seed {summary['seed']} · "
        f"won by {winner['name'] if winner else 'nobody'}",
        "beats": beats,
        "roster": summary["roster"],
        "standing": standing,
        "layout": LAYOUT,
        "corridors": CORRIDORS,
        "monster_rooms": MONSTER_ROOM,
        "monster_tiles": {
            mid: list(m.get("tile") or [])
            for mid, m in arena_rules.MONSTER_TEMPLATES.items()
        },
        # The authoritative grid, imported from the engine so the board can
        # never disagree with the rules about where a tile is.
        "grids": {
            rid: {
                "w": g["w"], "h": g["h"],
                "doors": {n: list(t) for n, t in g["doors"].items()},
                "features": {k: list(v) for k, v in g["features"].items()},
                "props": [
                    {
                        "tile": [int(k.split(",")[0]), int(k.split(",")[1])],
                        "kind": pr["kind"], "id": pr["id"], "name": pr["name"],
                    }
                    for k, pr in sorted(arena_grid.ROOM_PROPS.get(rid, {}).items())
                ],
            }
            for rid, g in arena_grid.ROOM_GRIDS.items()
        },
    }
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    out = root / args.out
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {args.out}: {len(beats)} beats, {out.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
