// UI for Bloodrune — the abilities/surrounded model in the full run. Reads engine
// state, renders it; owns no rules. Phases: prep(class+difficulty) -> map(blind)
// -> combat(arena) -> reward(loot + skill tree) -> ... -> victory | dead. Meta
// (difficulty ladder + tallies) persists in localStorage.

import { createGame } from '../engine/game.js';
import { SLOTS, SLOT_LABEL, CLASSES } from '../engine/content.js';
import { DT, ARENA_W, ARENA_H } from '../engine/arena.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const ov = document.getElementById('overlay');

const DIFFS = ['Normal', 'Nightmare', 'Hell'];
const CLASS_LIST = ['barbarian', 'amazon', 'necromancer'];
let game, combat, difficulty = 'Normal', classId = 'barbarian';
let invOpen = false, treeOpen = false, focusUid = null, countedTerminal = false;
window.__bloodrune = {};

function meta() { try { const m = JSON.parse(localStorage.getItem('bloodrune.meta')) || {}; return { unlocked: m.unlocked || ['Normal'], wins: m.wins || 0, deaths: m.deaths || 0 }; } catch { return { unlocked: ['Normal'], wins: 0, deaths: 0 }; } }
function saveMeta(m) { try { localStorage.setItem('bloodrune.meta', JSON.stringify(m)); } catch {} }

// ---- Telemetry: log what actually happens, unbiased, so balance is data-driven.
// Everything persists in localStorage; view via the Stats screen or export the JSON.
const TKEY = 'bloodrune.telemetry';
function blankTel() { return { v: 1, runs: 0, wins: 0, deaths: 0, byClass: {}, skills: {}, nodes: {},
  potions: { life: 0, mana: 0 }, combat: { fights: 0, fled: 0, hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0, turns: 0 }, deathLog: [], events: [] }; }
let TEL; try { TEL = JSON.parse(localStorage.getItem(TKEY)) || blankTel(); } catch { TEL = blankTel(); }
function saveTel() { try { if (TEL.events.length > 400) TEL.events = TEL.events.slice(-400); localStorage.setItem(TKEY, JSON.stringify(TEL)); } catch {} }
function tel(event, data) { TEL.events.push({ t: Date.now(), event, ...(data || {}) }); saveTel(); }
function telClass(c) { return TEL.byClass[c] || (TEL.byClass[c] = { runs: 0, wins: 0, deaths: 0, deepestStep: 0, maxLevel: 0 }); }

function newRun(diff, cls) {
  difficulty = diff || difficulty; if (cls) classId = cls;
  game = createGame('run-' + (window.__seed || 'ashes') + '-' + difficulty + '-' + classId, { classId, difficulty });
  combat = null; invOpen = false; treeOpen = false; focusUid = null; countedTerminal = false;
  TEL.runs++; telClass(classId).runs++; tel('run_start', { class: classId, difficulty });
  render();
}
function expose() { const r = game.getRun(); window.__bloodrune.run = r; window.__bloodrune.state = combat ? combat.getState() : null; window.__bloodrune.phase = r.phase; window.__bloodrune.game = game; window.__bloodrune.telemetry = TEL; }
function pv(a, b) { return b > 0 ? Math.max(0, Math.min(100, a / b * 100)) : 0; }

function render() {
  const r0 = game.getRun();
  if (r0.phase === 'combat') combat = game.getCombat();
  expose();
  const r = game.getRun();
  if (r.phase === 'combat') renderCombat();
  else if (r.phase === 'map') renderMap(r);
  else if (r.phase === 'shop') renderShop(r);
  else if (r.phase === 'reward') renderReward(r);
  else if (r.phase === 'dead') renderDead(r);
  else if (r.phase === 'victory') renderVictory(r);
  else renderPrep(r);
  renderOverlay();
}

// ---------- prep ----------
function renderPrep(r) {
  const m = meta(); const st = r.stats;
  board.innerHTML = `<div class="prep">
    <div class="prep-title">THE BLEEDING DARK</div>
    <div class="prep-sub">Choose a bloodline and descend. You begin with almost nothing — kill, level, and loot your way into power, or die in the dark.</div>
    <div class="meta-row">Class: ${CLASS_LIST.map((c) => `<button class="pill ${c === classId ? 'on' : ''}" data-class="${c}">${CLASSES[c].glyph} ${CLASSES[c].name}</button>`).join('')}</div>
    <div class="char"><div class="char-glyph">${r.glyph}</div>
      <div class="char-stats">
        <div><span class="k">Class</span> <b>${r.className}</b></div>
        <div><span class="k">Life</span> <b class="life">${r.life}/${st.maxLife}</b></div>
        <div><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></div>
        <div><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></div>
        <div><span class="k">Level</span> <b>${r.level}</b></div>
        <div><span class="k">Potions</span> <b>🩹${r.potions.life} 🔷${r.potions.mana}</b></div>
      </div></div>
    <div class="meta-row">Difficulty: ${DIFFS.map((d) => `<button class="pill ${d === difficulty ? 'on' : ''} ${m.unlocked.includes(d) ? '' : 'locked'}" data-diff="${d}" ${m.unlocked.includes(d) ? '' : 'disabled'}>${d}</button>`).join('')}<span class="tally">wins ${m.wins} · deaths ${m.deaths}</span></div>
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button><button class="act ghost small" id="openStats">📊 STATS</button><button class="act" id="descend">DESCEND</button></div>
  </div>`;
  logEl.innerHTML = '';
  board.querySelectorAll('.pill[data-class]').forEach((b) => b.addEventListener('click', () => newRun(difficulty, b.dataset.class)));
  board.querySelectorAll('.pill[data-diff]').forEach((b) => b.addEventListener('click', () => { if (!b.disabled) newRun(b.dataset.diff, classId); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  document.getElementById('openStats').addEventListener('click', () => renderStats());
  document.getElementById('descend').addEventListener('click', () => { game.beginDescent(); render(); });
}

// ---- Stats screen (reads the telemetry aggregates; export shares them with the dev) ----
function renderStats() {
  const c = TEL.combat; const pct = (a, b) => b > 0 ? Math.round(a / b * 100) : 0;
  const topSkills = Object.entries(TEL.skills).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const classRows = Object.entries(TEL.byClass).map(([k, v]) => `<tr><td>${k}</td><td>${v.runs}</td><td>${v.wins}</td><td>${v.deaths}</td><td>${v.maxLevel}</td><td>${v.deepestStep}</td></tr>`).join('');
  const deaths = TEL.deathLog.slice(-8).reverse().map((d) => `${d.class} · L${d.level} · step ${d.step}${d.node ? ' (' + d.node + ')' : ''}`).join('<br>') || '—';
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">📊 Play Statistics</div><button class="inv-close" id="cx">✕</button></div>
    <div class="sk-sub">Unbiased log of what actually happens — so balance is driven by data, not vibes. Runs: <b>${TEL.runs}</b> · Wins: <b>${TEL.wins}</b> · Deaths: <b>${TEL.deaths}</b></div>
    <table class="stt"><tr><th>Class</th><th>Runs</th><th>W</th><th>D</th><th>Max Lv</th><th>Deepest</th></tr>${classRows || '<tr><td colspan=6>no runs yet</td></tr>'}</table>
    <div class="stblk"><b>Combat</b> — fights ${c.fights} (fled ${c.fled}) · hit rate ${pct(c.hits, c.hits + c.misses)}% · evades ${c.evades} · kills ${c.kills}<br>dmg dealt ${c.dmgDealt} · dmg taken ${c.dmgTaken} · avg turns/fight ${c.fights ? (c.turns / c.fights).toFixed(1) : 0}</div>
    <div class="stblk"><b>Potions used</b> — 🩹 ${TEL.potions.life} · 🔷 ${TEL.potions.mana}</div>
    <div class="stblk"><b>Most-used skills</b><br>${topSkills.map(([k, v]) => `${k} ×${v}`).join(' · ') || '—'}</div>
    <div class="stblk"><b>Recent deaths</b><br>${deaths}</div>
    <textarea id="telBox" class="export-ta" readonly onclick="this.select()"></textarea>
    <div class="prep-actions"><button class="act ghost small" id="telExport">COPY DATA</button><button class="act ghost small" id="telReset">RESET</button></div></div>`;
  document.getElementById('telBox').value = JSON.stringify(TEL); // fallback: always here to select + Ctrl/Cmd+C
  document.getElementById('cx').addEventListener('click', () => { ov.className = 'overlay hidden'; ov.innerHTML = ''; });
  document.getElementById('telExport').addEventListener('click', () => {
    const box = document.getElementById('telBox'); box.focus(); box.select(); box.setSelectionRange(0, box.value.length);
    let ok = false; try { ok = document.execCommand('copy'); } catch {}
    if (!ok && navigator.clipboard) { try { navigator.clipboard.writeText(box.value); ok = true; } catch {} }
    document.getElementById('telExport').textContent = ok ? 'COPIED ✓' : 'SELECTED — press Ctrl/Cmd+C';
  });
  document.getElementById('telReset').addEventListener('click', () => { TEL = blankTel(); saveTel(); renderStats(); });
}

// ---------- map (blind) ----------
const BLIND = [['🕳️', 'A Yawning Dark', 'The path drops into black.'], ['🚪', 'An Unlit Passage', 'Cold air breathes from the tunnel.'], ['🩸', 'A Blood-Slick Trail', 'Something dragged itself down here.']];
function renderMap(r) {
  const boss = r.choices.length === 1 && r.choices[0].type === 'boss';
  const cards = r.choices.map((c, i) => boss
    ? `<button class="path boss" data-i="${i}"><div class="path-glyph">${c.glyph}</div><div class="path-name">${c.name}</div><div class="path-desc">${c.desc}</div></button>`
    : (() => { const f = BLIND[i % BLIND.length]; return `<button class="path blind" data-i="${i}"><div class="path-glyph">${f[0]}</div><div class="path-name">${f[1]}</div><div class="path-desc">${f[2]}</div></button>`; })()).join('');
  board.innerHTML = `${runHeader(r)}<div class="prep-sub" style="text-align:center;margin:6px 0">${boss ? 'The way ends here.' : 'Choose a path into the dark — you cannot see what waits, and cannot turn back.'}</div>
    <div class="paths">${cards}</div>
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button>${r.skillPoints ? `<button class="act" id="openTree">⚔ SKILLS ● ${r.skillPoints}</button>` : ''}</div>`;
  logEl.innerHTML = '';
  board.querySelectorAll('.path').forEach((b) => b.addEventListener('click', () => { const r = game.getRun(); const t = r.choices && r.choices[Number(b.dataset.i)] ? r.choices[Number(b.dataset.i)].type : '?'; TEL.nodes[t] = (TEL.nodes[t] || 0) + 1; tel('node', { type: t, step: r.mapStep }); game.chooseDirection(Number(b.dataset.i)); render(); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  const t = document.getElementById('openTree'); if (t) t.addEventListener('click', () => { treeOpen = true; renderOverlay(); });
}
function runHeader(r) { return `<div class="run-header"><span class="rh-diff">${r.difficulty}</span><span>Depth ${Math.min(r.mapStep + 1, r.mapLength + 1)}/${r.mapLength + 1}</span><span class="rh-life">❤ ${r.life}/${r.maxLife}</span><span style="color:var(--gold)">◉ ${r.gold}g</span><span class="rh-xp">Lv ${r.level} · XP ${r.xp}/${r.xpToNext}</span>${r.skillPoints ? `<span style="color:var(--gold)">● ${r.skillPoints} pts</span>` : ''}</div>`; }

// ---------- combat (REAL-TIME arena) ----------
// You are a token in an arena and MOVE (WASD / arrows / drag). Abilities auto-fire
// on cooldown when Mana allows — positioning is the whole game. We drive our own
// rAF loop here (not render()): the engine ticks at a fixed DT, the canvas paints.
const keys = new Set();
let touchVec = null, joy = null;               // joy = {ox,oy,cx,cy} for the on-canvas stick
let arenaActive = false, raf = 0, lastT = 0, tacc = 0;
let rtCanvas = null, rtCtx = null, rtSkillEls = {};
const KEYMAP = { arrowup: 'up', w: 'up', arrowdown: 'down', s: 'down', arrowleft: 'left', a: 'left', arrowright: 'right', d: 'right' };
window.addEventListener('keydown', (e) => { if (!arenaActive) return; const m = KEYMAP[e.key.toLowerCase()]; if (m) { keys.add(m); e.preventDefault(); } });
window.addEventListener('keyup', (e) => { if (!arenaActive) return; const m = KEYMAP[e.key.toLowerCase()]; if (m) { keys.delete(m); } });
function inputVector() {
  if (touchVec) return touchVec;
  let x = 0, y = 0; if (keys.has('left')) x -= 1; if (keys.has('right')) x += 1; if (keys.has('up')) y -= 1; if (keys.has('down')) y += 1;
  const l = Math.hypot(x, y); return l > 0 ? { x: x / l, y: y / l } : { x: 0, y: 0 };
}
function potionBtn(kind, count, full) { const label = kind === 'life' ? '🩹 Life' : '🔷 Mana';
  return `<button class="pot ${kind}" data-quaff="${kind}" ${count <= 0 || full ? 'disabled' : ''}>${label} <span class="pn">×${count}</span></button>`; }

function renderCombat() {
  if (arenaActive) return; // the loop owns the DOM once it's up; don't rebuild mid-fight
  const s = combat.getState(); const h = s.hero; const pot = game.getRun().potions;
  board.innerHTML = `<div class="rt">
    <div class="rt-hud">
      <div class="rt-bars">
        <div class="rt-bar life"><i id="rtLife"></i><span id="rtLifeT"></span></div>
        <div class="rt-bar mana"><i id="rtMana"></i><span id="rtManaT"></span></div>
      </div>
      <div class="rt-meta"><span>Lv <b id="rtLvl">${game.getRun().level}</b></span><span>Foes <b id="rtFoes"></b></span><span>⏱ <b id="rtTime"></b></span></div>
    </div>
    <div class="rt-canvas-wrap"><canvas id="rtCanvas" width="${ARENA_W}" height="${ARENA_H}"></canvas></div>
    <div class="rt-skills" id="rtSkills">${h.abilities.map((a) => `<div class="rt-skill ${a.type}" data-id="${a.id}"><div class="rs-n">${a.name}</div><div class="rs-c">${a.cost ? a.cost + '⬡' : 'free'}</div><div class="rs-cd"></div></div>`).join('')}</div>
    <div class="belt">${potionBtn('life', pot.life, h.life >= h.maxLife)}${potionBtn('mana', pot.mana, h.mana >= h.maxMana)}</div>
    <div class="rt-hint">Move: <b>WASD / arrows</b> on a keyboard, or <b>drag</b> anywhere on the arena. Your skills fire on their own — kite the swarm, line up a swing, back off to regen Mana. Kill the caster (🧙) fast: it raises the dead.</div>
    <div class="controls" style="display:flex;gap:12px;justify-content:center"><button class="act ghost small" id="flee">FLEE</button></div>
  </div>`;
  logEl.innerHTML = '';
  rtCanvas = document.getElementById('rtCanvas'); rtCtx = rtCanvas.getContext('2d');
  rtSkillEls = {}; board.querySelectorAll('.rt-skill').forEach((el) => { rtSkillEls[el.dataset.id] = el; });
  bindArenaPointer();
  board.querySelectorAll('[data-quaff]').forEach((b) => b.addEventListener('click', (ev) => { ev.preventDefault(); const r = game.quaff(b.dataset.quaff); if (r && r.ok) { TEL.potions[b.dataset.quaff]++; tel('quaff', { kind: b.dataset.quaff }); } }));
  document.getElementById('flee').addEventListener('click', () => { if (!arenaActive) return; game.flee(); endArena(combat.getState()); });
  arenaActive = true; lastT = performance.now(); tacc = 0; raf = requestAnimationFrame(arenaFrame);
}

function bindArenaPointer() {
  const toArena = (ev) => { const r = rtCanvas.getBoundingClientRect(); return { x: (ev.clientX - r.left) / r.width * ARENA_W, y: (ev.clientY - r.top) / r.height * ARENA_H }; };
  rtCanvas.addEventListener('pointerdown', (ev) => { ev.preventDefault(); rtCanvas.setPointerCapture(ev.pointerId); const p = toArena(ev); joy = { ox: p.x, oy: p.y, cx: p.x, cy: p.y }; touchVec = { x: 0, y: 0 }; });
  rtCanvas.addEventListener('pointermove', (ev) => { if (!joy) return; const p = toArena(ev); joy.cx = p.x; joy.cy = p.y; let dx = p.x - joy.ox, dy = p.y - joy.oy; const l = Math.hypot(dx, dy); const dead = 8; if (l < dead) { touchVec = { x: 0, y: 0 }; } else { const m = Math.min(1, l / 70); touchVec = { x: dx / l * m, y: dy / l * m }; } });
  const end = () => { joy = null; touchVec = null; };
  rtCanvas.addEventListener('pointerup', end); rtCanvas.addEventListener('pointercancel', end); rtCanvas.addEventListener('pointerleave', () => { if (joy) { /* keep moving if captured */ } });
}

function arenaFrame(now) {
  if (!arenaActive) return;
  let dt = (now - lastT) / 1000; lastT = now; if (dt > 0.05) dt = 0.05; tacc += dt * (window.__timescale || 1); // __timescale: headless fast-forward
  const input = window.__autopilot ? combat.autoInput() : inputVector(); // __autopilot: headless-test movement driver
  const cap = window.__timescale ? 400 : 6;
  let guard = 0; while (tacc >= DT && guard < cap) { combat.tick(input); tacc -= DT; guard++; if (combat.getState().over) break; }
  const s = combat.getState();
  drawArena(s); updateHUD(s);
  window.__bloodrune.state = s; window.__bloodrune.phase = 'combat';
  if (s.over) { endArena(s); return; }
  raf = requestAnimationFrame(arenaFrame);
}

function endArena(s) {
  arenaActive = false; cancelAnimationFrame(raf); touchVec = null; joy = null; keys.clear();
  recordCombatEnd(s); game.resolveCombat(); afterTerminal(); render();
}

// ---- canvas painting ----
const ROLE_FILL = { grunt: '#2a1622', guardian: '#1c2542', archer: '#16233f', caster: '#2a183a', elite: '#3a1414' };
function drawArena(s) {
  const c = rtCtx; c.clearRect(0, 0, ARENA_W, ARENA_H);
  // gems (spent XP motes) + fx underlay
  for (const g of s.gems) { c.fillStyle = 'rgba(120,200,220,0.5)'; c.beginPath(); c.arc(g.x, g.y, 2.5, 0, 7); c.fill(); }
  for (const f of s.fx) drawFx(c, f);
  // minions
  for (const m of s.minions) { c.fillStyle = '#1a2038'; c.strokeStyle = '#6a6f8a'; c.lineWidth = 1.5; disc(c, m.x, m.y, m.r); glyph(c, m.glyph, m.x, m.y, m.r * 1.5); }
  // projectiles
  for (const p of s.projectiles) { c.fillStyle = p.hostile ? '#ff6a5a' : '#e7cf8a'; c.beginPath(); c.arc(p.x, p.y, p.r, 0, 7); c.fill();
    if (p.hostile) { c.strokeStyle = 'rgba(255,90,70,.4)'; c.lineWidth = 1; c.stroke(); } }
  // enemies
  for (const e of s.enemies) { if (e.hp <= 0) continue;
    const flash = e.flash > 0; c.fillStyle = flash ? '#ffffff' : (ROLE_FILL[e.role] || '#241521');
    c.strokeStyle = e.unique ? '#c8a24a' : e.elite ? '#c62828' : e.raised ? '#6f8a6f' : '#4a3a4a'; c.lineWidth = e.unique || e.elite ? 2.5 : 1.5;
    disc(c, e.x, e.y, e.r); glyph(c, e.glyph, e.x, e.y - 1, e.r * 1.7);
    // hp bar
    const w = e.r * 2.2, hpf = Math.max(0, e.hp / e.maxHp); c.fillStyle = '#320c0c'; c.fillRect(e.x - w / 2, e.y - e.r - 8, w, 3.5);
    c.fillStyle = e.unique ? '#c8a24a' : '#c62828'; c.fillRect(e.x - w / 2, e.y - e.r - 8, w * hpf, 3.5);
  }
  // hero
  const h = s.hero; if (h.shield > 0) { c.strokeStyle = 'rgba(200,162,74,.7)'; c.lineWidth = 2.5; c.beginPath(); c.arc(h.x, h.y, h.r + 6, 0, 7); c.stroke(); }
  c.globalAlpha = h.invuln ? 0.55 : 1; c.fillStyle = '#2a1a10'; c.strokeStyle = '#c8a24a'; c.lineWidth = 2.5; disc(c, h.x, h.y, h.r); glyph(c, h.glyph, h.x, h.y - 1, h.r * 2); c.globalAlpha = 1;
  // aim reticle toward last move dir
  // joystick
  if (joy) { c.strokeStyle = 'rgba(200,180,150,.35)'; c.lineWidth = 2; c.beginPath(); c.arc(joy.ox, joy.oy, 40, 0, 7); c.stroke();
    c.fillStyle = 'rgba(200,180,150,.55)'; c.beginPath(); c.arc(joy.cx, joy.cy, 14, 0, 7); c.fill(); }
}
function disc(c, x, y, r) { c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.stroke(); }
function glyph(c, g, x, y, size) { c.font = `${Math.round(size)}px serif`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(g, x, y); }
function drawFx(c, f) {
  const t = f.life / f.maxLife;
  if (f.type === 'sweep') { c.strokeStyle = `rgba(230,200,150,${0.5 * t})`; c.lineWidth = 3; c.beginPath(); c.arc(f.x, f.y, f.r * (1.2 - t * 0.3), 0, 7); c.stroke(); }
  else if (f.type === 'cast') { c.strokeStyle = hexA(f.color || '#c8a24a', 0.6 * t); c.lineWidth = 2.5; c.beginPath(); c.arc(f.x, f.y, f.r * (1.4 - t * 0.5), 0, 7); c.stroke(); }
  else if (f.type === 'dash') { c.fillStyle = `rgba(200,162,74,${0.4 * t})`; c.beginPath(); c.arc(f.x, f.y, 22 * (1.2 - t), 0, 7); c.fill(); }
  else if (f.type === 'dmg') { c.fillStyle = `rgba(255,225,180,${Math.min(1, t * 1.5)})`; c.font = 'bold 14px sans-serif'; c.textAlign = 'center'; c.fillText(f.val, f.x, f.y); }
  else if (f.type === 'miss') { c.fillStyle = `rgba(150,150,160,${t})`; c.font = '11px sans-serif'; c.textAlign = 'center'; c.fillText('miss', f.x, f.y); }
  else if (f.type === 'evade') { c.fillStyle = `rgba(150,200,255,${t})`; c.font = '11px sans-serif'; c.textAlign = 'center'; c.fillText('dodge', f.x, f.y); }
  else if (f.type === 'hurt') { c.strokeStyle = `rgba(220,40,40,${0.5 * t})`; c.lineWidth = 3; c.beginPath(); c.arc(f.x, f.y, 20 * (1.4 - t), 0, 7); c.stroke(); }
}
function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }

function updateHUD(s) {
  const h = s.hero; const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const wl = document.getElementById('rtLife'), wm = document.getElementById('rtMana');
  if (wl) wl.style.width = pv(h.life, h.maxLife) + '%'; if (wm) wm.style.width = pv(h.mana, h.maxMana) + '%';
  set('rtLifeT', `${Math.ceil(h.life)}/${h.maxLife}`); set('rtManaT', `${Math.floor(h.mana)}/${h.maxMana}`);
  set('rtFoes', s.enemies.filter((e) => e.hp > 0).length); set('rtTime', s.turn + 's'); set('rtLvl', game.getRun().level);
  for (const a of h.abilities) { const el = rtSkillEls[a.id]; if (!el) continue;
    el.classList.toggle('ready', a.ready); const bar = el.querySelector('.rs-cd'); if (bar) bar.style.height = Math.min(100, (a.cd / 1.8) * 100) + '%'; }
  // potion buttons reflect the belt
  const pot = game.getRun().potions;
  const lb = board.querySelector('[data-quaff="life"]'), mb = board.querySelector('[data-quaff="mana"]');
  if (lb) { lb.disabled = pot.life <= 0 || h.life >= h.maxLife; lb.querySelector('.pn').textContent = '×' + pot.life; }
  if (mb) { mb.disabled = pot.mana <= 0 || h.mana >= h.maxMana; mb.querySelector('.pn').textContent = '×' + pot.mana; }
}

let lastRecorded = null;
function recordCombatEnd(s) { if (!s || !s.over || s === lastRecorded) return; lastRecorded = s; const ty = s.tally; const c = TEL.combat;
  c.fights++; if (s.result === 'fled') c.fled++; c.hits += ty.hits; c.misses += ty.misses; c.evades += ty.evades; c.kills += ty.kills; c.dmgDealt += ty.dmgDealt; c.dmgTaken += ty.dmgTaken; c.turns += s.turn;
  tel('combat', { result: s.result, node: game.getRun().node ? game.getRun().node.type : null, secs: s.turn, tally: ty }); }
function afterTerminal() { const p = game.getRun().phase; if (!countedTerminal && (p === 'dead' || p === 'victory')) { countedTerminal = true; const m = meta(); if (p === 'dead') m.deaths++; if (p === 'victory') { m.wins++; const ni = DIFFS.indexOf(game.getRun().difficulty) + 1; if (DIFFS[ni] && !m.unlocked.includes(DIFFS[ni])) m.unlocked.push(DIFFS[ni]); } saveMeta(m);
    const run = game.getRun(); const bc = telClass(classId); bc.maxLevel = Math.max(bc.maxLevel, run.level); bc.deepestStep = Math.max(bc.deepestStep, run.mapStep);
    if (p === 'dead') { TEL.deaths++; bc.deaths++; TEL.deathLog.push({ class: classId, level: run.level, step: run.mapStep, node: run.node ? run.node.type : null }); if (TEL.deathLog.length > 100) TEL.deathLog = TEL.deathLog.slice(-100); }
    else { TEL.wins++; bc.wins++; }
    tel('run_end', { result: p, class: classId, level: run.level, step: run.mapStep }); } }

// ---------- reward ----------
function renderReward(r) {
  let title, body;
  if (r.lastResult === 'camp') { title = '🔥 BLOODFIRE CAMP'; body = 'You bind your wounds and steel yourself.'; }
  else if (r.lastResult === 'fled') { title = 'YOU BREAK AWAY'; body = 'You escape with your life — and nothing else.'; }
  else if (r.node && r.node.type === 'treasure') { title = '📦 A CACHE'; body = 'Spoils, unguarded.'; }
  else { title = 'THE RING BREAKS'; body = 'Loot falls among the corpses.'; }
  const gained = r.gained && (r.gained.levels || r.gained.points) ? `<div class="deck-note" style="color:var(--gold)">${r.gained.levels ? `Level up! Now level ${r.level}. ` : ''}${r.gained.points ? `+${r.gained.points} skill point${r.gained.points > 1 ? 's' : ''}.` : ''}</div>` : '';
  const full = r.bag.length >= r.bagCap;
  const loot = r.pendingLoot.length ? `<div class="prep-sub" style="margin:6px 0 2px">On the ground — take what you can carry (Bag <b>${r.bag.length}/${r.bagCap}</b>${full ? ', <span style="color:var(--blood-bright)">full — drop something</span>' : ''}). What you leave is lost.</div><div class="loot-list">${r.pendingLoot.map((it) => lootChip(it, full)).join('')}</div>` : '<div class="deck-note">No spoils.</div>';
  board.innerHTML = `<div class="prep">${runHeader(r)}<div class="prep-title" style="font-size:26px">${title}</div><div class="prep-sub">${body}</div>${gained}${loot}
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button>${r.skillPoints ? `<button class="act" id="openTree">⚔ SKILLS ● ${r.skillPoints}</button>` : ''}<button class="act" id="cont">PRESS ON</button></div></div>`;
  logEl.innerHTML = '';
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  const t = document.getElementById('openTree'); if (t) t.addEventListener('click', () => { treeOpen = true; renderOverlay(); });
  board.querySelectorAll('[data-take]').forEach((b) => b.addEventListener('click', () => { game.takeLoot(b.dataset.take); render(); }));
  document.getElementById('cont').addEventListener('click', () => { game.continueFromReward(); render(); });
}
function lootChip(it, bagFull) { return `<div class="loot-chip" style="border-color:${it.color || 'var(--gold)'}"><div class="lc-name" style="color:${it.color || 'var(--gold)'}">${it.name}</div><div class="lc-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants && it.grants.skill ? ' · grants a skill' : ''}</div><div class="lc-text">${it.text || ''}</div><button class="act ghost small" data-take="${it.id}" ${bagFull ? 'disabled' : ''} style="margin-top:4px">${bagFull ? 'BAG FULL' : 'TAKE'}</button></div>`; }

// ---------- shop ----------
function renderShop(r) {
  board.innerHTML = `<div class="prep">${runHeader(r)}<div class="prep-title" style="font-size:26px">🛒 WANDERING TRADER</div>
    <div class="prep-sub">Sell your spoils, restock the belt. Bag <b>${r.bag.length}/${r.bagCap}</b> · Belt 🩹${r.potions.life} 🔷${r.potions.mana}</div>
    <div class="shop-buy"><button class="act ghost small" id="buyLife">Buy 🩹 Life (12g)</button><button class="act ghost small" id="buyMana">Buy 🔷 Mana (12g)</button></div>
    <div class="loot-list">${r.bag.length ? r.bag.map(shopSellChip).join('') : '<div class="deck-note">Bag empty — nothing to sell.</div>'}</div>
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button><button class="act" id="cont">LEAVE</button></div></div>`;
  logEl.innerHTML = '';
  document.getElementById('buyLife').addEventListener('click', () => { game.buyPotion('life'); render(); });
  document.getElementById('buyMana').addEventListener('click', () => { game.buyPotion('mana'); render(); });
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  board.querySelectorAll('[data-sell]').forEach((b) => b.addEventListener('click', () => { game.sellFromBag(b.dataset.sell); render(); }));
  document.getElementById('cont').addEventListener('click', () => { game.continueFromReward(); render(); });
}
function shopSellChip(it) { const val = it.grants ? 12 : ({ normal: 3, magic: 8, rare: 18 }[it.rarity] || 4); return `<div class="loot-chip" style="border-color:${it.color || 'var(--gold)'}"><div class="lc-name" style="color:${it.color || 'var(--gold)'}">${it.name}</div><div class="lc-slot">${SLOT_LABEL[it.slot] || it.slot}</div><button class="act ghost small" data-sell="${it.id}" style="margin-top:4px">SELL ${val}g</button></div>`; }

// ---------- dead / victory ----------
function renderDead(r) { const m = meta(); ov.className = 'overlay'; ov.innerHTML = `<h2 class="dead">YOU HAVE DIED</h2><div class="deck-note">You fell at depth ${r.mapStep + 1}, level ${r.level}, on ${r.difficulty}.</div><div class="deck-note" style="color:#6f6357">${m.wins} cleared · ${m.deaths} lost</div><button class="act" id="again">NEW DESCENT</button>`; board.innerHTML = ''; logEl.innerHTML = ''; document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun('Normal', classId); }); }
function renderVictory(r) { const cur = DIFFS.indexOf(r.difficulty); const next = DIFFS[cur + 1]; ov.className = 'overlay'; ov.innerHTML = `<h2 class="win">THE SMITH FALLS</h2><div class="deck-note">You cleared the act on <b>${r.difficulty}</b> at level ${r.level}.</div>${next ? `<div class="deck-note" style="color:var(--gold)">${next} unlocked.</div>` : '<div class="deck-note" style="color:var(--gold)">You have conquered Hell.</div>'}<div style="display:flex;gap:12px;margin-top:6px">${next ? `<button class="act" id="next">DESCEND ${next.toUpperCase()}</button>` : ''}<button class="act ghost" id="again">NEW DESCENT</button></div>`; board.innerHTML = ''; logEl.innerHTML = ''; const nb = document.getElementById('next'); if (nb) nb.addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(next, classId); }); document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun('Normal', classId); }); }

// ---------- overlays ----------
function renderOverlay() { if (invOpen) return renderInventory(); if (treeOpen) return renderTree(); const p = game.getRun().phase; if (p === 'dead') return renderDead(game.getRun()); if (p === 'victory') return renderVictory(game.getRun()); ov.className = 'overlay hidden'; ov.innerHTML = ''; }

function renderTree() {
  const r = game.getRun();
  const rows = r.tree.map((sk) => { const req = sk.pre && sk.pre.length ? ` · needs ${sk.pre.map((p) => (r.tree.find((t) => t.id === p) || {}).name || p).join(', ')}` : '';
    const tag = sk.learned ? '' : sk.canInvest ? ' <span style="color:var(--gold)">— can learn</span>' : ` <span style="color:#6f6357">— locked (${sk.gateReason || 'Lv ' + sk.req})</span>`;
    return `<div class="sk-row ${sk.canInvest ? '' : sk.learned ? '' : 'locked'}"><div class="sk-info"><div class="sn">${sk.name} <span style="color:var(--gold)">Lv ${sk.level}</span> <span style="color:#5f6b7a;font-size:10px">Lv${sk.req}${req}</span>${tag}</div><div class="se">${sk.eff.text}</div></div>
    <div class="sk-btns"><button data-inv="${sk.id}" ${sk.canInvest ? '' : 'disabled'}>${sk.learned ? 'Improve ▲' : 'Learn +'}</button></div></div>`; }).join('');
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">⚔ Skill Tree — ${r.skillPoints} pts</div><button class="inv-close" id="cx">✕</button></div>
    <div class="sk-sub">Skills unlock by <b>level</b> and <b>prerequisite</b> — you build toward the big ones. Each point needs a higher level than the last, so you can't dump a pile into one skill. +Skills gear raises every skill's level.</div>${rows}</div>`;
  document.getElementById('cx').addEventListener('click', () => { treeOpen = false; render(); });
  ov.querySelectorAll('[data-inv]').forEach((b) => b.addEventListener('click', () => { game.investSkill(b.dataset.inv); expose(); renderTree(); }));
}

function renderInventory() {
  const r = game.getRun(); const st = r.stats;
  const cells = SLOTS.map((slot) => { const it = r.equipment[slot]; return `<div class="slot ${it ? 'filled' : ''}" data-slot="${slot}"><div class="slot-k">${SLOT_LABEL[slot]}</div><div class="slot-v" style="${it && it.color ? `color:${it.color}` : ''}">${it ? it.name : '<span class="empty">— empty —</span>'}</div>${it ? `<div class="slot-t">${it.text || ''}</div>${slot !== 'weapon' ? '<div class="slot-x">tap to unequip</div>' : ''}` : ''}</div>`; }).join('');
  const bag = r.bag.length ? r.bag.map((it) => `<div class="bag-item" style="${it.color ? `border-color:${it.color}` : ''}"><div class="bi-name" style="${it.color ? `color:${it.color}` : ''}">${it.name}</div><div class="bi-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants && it.grants.skill ? ' · grants a skill' : ''}</div><div class="bi-text">${it.text || ''}</div><div class="bi-btns"><button class="act ghost small" data-equip="${it.id}">EQUIP</button><button class="act ghost small" data-drop="${it.id}">DROP</button></div></div>`).join('') : '<div class="bag-empty">Your bag is empty.</div>';
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">🎒 Inventory</div><button class="inv-close" id="cx">✕</button></div>
    <div class="inv-stats"><span><span class="k">Life</span> <b class="life">${r.life}/${st.maxLife}</b></span><span><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></span><span><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></span><span><span class="k">Gold</span> <b style="color:var(--gold)">${r.gold}</b></span></div>
    <div class="inv-cols"><div class="paperdoll">${cells}</div><div class="bag"><div class="bag-head">Bag (${r.bag.length}/${r.bagCap})</div><div class="bag-list">${bag}</div></div></div></div>`;
  document.getElementById('cx').addEventListener('click', () => { invOpen = false; render(); });
  ov.querySelectorAll('.slot.filled').forEach((el) => el.addEventListener('click', () => { game.unequip(el.dataset.slot); expose(); renderInventory(); }));
  ov.querySelectorAll('[data-equip]').forEach((el) => el.addEventListener('click', () => { game.equipFromBag(el.dataset.equip); expose(); renderInventory(); }));
  ov.querySelectorAll('[data-drop]').forEach((el) => el.addEventListener('click', () => { game.dropFromBag(el.dataset.drop); expose(); renderInventory(); }));
}

newRun('Normal', 'barbarian');
