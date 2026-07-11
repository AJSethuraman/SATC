// UI for Bloodrune — the SURVIVORS model. Reads engine state, renders it; owns no
// rules. Phases: prep(class+difficulty) -> arena(one big real-time map: move,
// survive ramping waves, grab dropped loot, level up your tree, kill the boss) ->
// victory | dead. Meta (difficulty ladder + telemetry) persists in localStorage.

import { createGame } from '../engine/game.js';
import { SLOTS, SLOT_LABEL, CLASSES, ACT1 } from '../engine/content.js';
import { DT, ARENA_W, ARENA_H } from '../engine/arena.js';
import { RASTER_SPRITES } from './sprites.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const ov = document.getElementById('overlay');

const DIFFS = ['Normal', 'Nightmare', 'Hell'];
const CLASS_LIST = ['barbarian', 'amazon', 'necromancer', 'sorceress'];
let game, combat, difficulty = 'Normal', classId = 'barbarian';
let invOpen = false, treeOpen = false, focusUid = null, countedTerminal = false;
window.__bloodrune = {};

function meta() { try { const m = JSON.parse(localStorage.getItem('bloodrune.meta')) || {}; return { unlocked: m.unlocked || ['Normal'], wins: m.wins || 0, deaths: m.deaths || 0 }; } catch { return { unlocked: ['Normal'], wins: 0, deaths: 0 }; } }
function saveMeta(m) { try { localStorage.setItem('bloodrune.meta', JSON.stringify(m)); } catch {} }
// The STASH is the only thing that carries between runs (tier-capped gear + runes).
const STASH_KEY = 'bloodrune.stash';
function loadStash() { try { return JSON.parse(localStorage.getItem(STASH_KEY)) || []; } catch { return []; } }
function saveStash() { try { if (game) localStorage.setItem(STASH_KEY, JSON.stringify(game.getStash())); } catch {} }

// ---- Telemetry: log what actually happens, unbiased, so balance is data-driven.
// Everything persists in localStorage; view via the Stats screen or export the JSON.
const TKEY = 'bloodrune.telemetry';
function blankTel() { return { v: 1, runs: 0, wins: 0, deaths: 0, byClass: {}, skills: {}, nodes: {},
  potions: { life: 0, mana: 0 }, combat: { fights: 0, fled: 0, hits: 0, misses: 0, evades: 0, kills: 0, dmgDealt: 0, dmgTaken: 0, turns: 0, moveDist: 0, idleT: 0, moveT: 0 }, deathLog: [], events: [] }; }
let TEL; try { TEL = JSON.parse(localStorage.getItem(TKEY)) || blankTel(); } catch { TEL = blankTel(); }
function saveTel() { try { if (TEL.events.length > 400) TEL.events = TEL.events.slice(-400); localStorage.setItem(TKEY, JSON.stringify(TEL)); } catch {} }
function tel(event, data) { TEL.events.push({ t: Date.now(), event, ...(data || {}) }); saveTel(); }
function telClass(c) { return TEL.byClass[c] || (TEL.byClass[c] = { runs: 0, wins: 0, deaths: 0, deepestStep: 0, maxLevel: 0 }); }

function newRun(diff, cls) {
  difficulty = diff || difficulty; if (cls) classId = cls;
  game = createGame('run-' + (window.__seed || 'ashes') + '-' + difficulty + '-' + classId, { classId, difficulty, stash: loadStash() });
  combat = null; invOpen = false; treeOpen = false; focusUid = null; countedTerminal = false;
  TEL.runs++; telClass(classId).runs++; tel('run_start', { class: classId, difficulty });
  render();
}
function expose() { const r = game.getRun(); window.__bloodrune.run = r; window.__bloodrune.state = combat ? combat.getState() : null; window.__bloodrune.phase = r.phase; window.__bloodrune.game = game; window.__bloodrune.telemetry = TEL; }
function pv(a, b) { return b > 0 ? Math.max(0, Math.min(100, a / b * 100)) : 0; }

function render() {
  const r0 = game.getRun();
  if (r0.phase === 'arena') combat = game.getCombat();
  expose();
  const r = game.getRun();
  if (r.phase === 'arena') renderArena();
  else if (r.phase === 'dead') renderDead(r);
  else if (r.phase === 'victory') renderVictory(r);
  else renderTown(r);
  renderOverlay();
}

// ---------- town (the checkpoint hub — start of run AND between quests) ----------
const ATTR_LABEL = { str: 'Strength', dex: 'Dexterity', vit: 'Vitality', energy: 'Energy' };
function renderTown(r) {
  const m = meta(); const st = r.stats; const a = r.attr || {};
  const fresh = r.level === 1 && r.questIdx === 0 && !r.quests.some((q) => q.done); // start of a run: pick class/difficulty
  const q = r.quest || {};
  const questRow = r.quests.map((qq, i) => `<span class="qpip ${qq.done ? 'done' : i === r.questIdx ? 'cur' : ''}" title="${qq.name}">${qq.done ? '✓' : i === r.questIdx ? '◆' : '○'}</span>`).join('');
  const attrRow = ['str', 'dex', 'vit', 'energy'].map((k) => `<div class="attr-row"><span class="k">${ATTR_LABEL[k]}</span> <b>${a[k] || 0}</b>${r.attrPoints > 0 ? `<button class="attr-plus" data-attr="${k}">＋</button>` : ''}</div>`).join('');
  board.innerHTML = `<div class="prep town">
    <div class="prep-title">${fresh ? 'THE BLEEDING DARK' : 'ROGUE ENCAMPMENT'}</div>
    <div class="prep-sub">${fresh ? 'Choose a bloodline and descend. You begin with almost nothing — bank your finds in town between quests, or lose them in the dark.' : `Act ${r.act} · rest, bank your spoils, spend your points, then descend.`}</div>
    <div class="quest-track">${questRow}</div>
    <div class="quest-now">✦ <b>${q.name || 'Act 1'}</b> — ${q.questText || ''}</div>
    ${fresh ? `<div class="meta-row">Class: ${CLASS_LIST.map((c) => `<button class="pill ${c === classId ? 'on' : ''}" data-class="${c}">${CLASSES[c].glyph} ${CLASSES[c].name}</button>`).join('')}</div>
    <div class="meta-row">Difficulty: ${DIFFS.map((d) => `<button class="pill ${d === difficulty ? 'on' : ''} ${m.unlocked.includes(d) ? '' : 'locked'}" data-diff="${d}" ${m.unlocked.includes(d) ? '' : 'disabled'}>${d}</button>`).join('')}<span class="tally">wins ${m.wins} · deaths ${m.deaths}</span></div>` : ''}
    <div class="char"><div class="char-glyph">${RASTER[HERO_SPRITE[r.glyph]] ? `<img src="${RASTER[HERO_SPRITE[r.glyph]]}" width="78" height="92" style="object-fit:contain">` : ((SPRITE_SVG[HERO_SPRITE[r.glyph]] || '').replace('<svg ', '<svg width="70" height="80" ') || r.glyph)}</div>
      <div class="char-stats">
        <div><span class="k">Class</span> <b>${r.className}</b> <span class="k">Lv</span> <b>${r.level}</b></div>
        <div><span class="k">Life</span> <b class="life">${Math.round(r.life)}/${st.maxLife}</b> <span class="k">Mana</span> <b class="mana">${st.maxMana}</b></div>
        <div><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b>${st.fcr ? ` <span class="k">FCR</span> <b style="color:#9ab6ff">+${st.fcr}%</b>` : ''}${st.penetration ? ` <span class="k">Pierce</span> <b style="color:#c58">-${Math.round(st.penetration * 100)}%</b>` : ''}</div>
        <div><span class="k">Gold</span> <b style="color:var(--gold)">${r.gold}</b> <span class="k">Shards</span> <b style="color:#d98b3a">${r.shards}</b> <span class="k">Potions</span> <b>🩹${r.potions.life} 🔷${r.potions.mana}</b></div>
      </div>
      <div class="char-attrs"><div class="attr-h">Attributes ${r.attrPoints > 0 ? `<span class="pts">${r.attrPoints} pts</span>` : ''}</div>${attrRow}</div>
    </div>
    <div class="prep-actions">
      <button class="act ghost" id="openInv">🎒 STASH & GEAR</button>
      <button class="act ghost" id="openTree">⚔ SKILLS${r.skillPoints ? ' ·' + r.skillPoints : ''}</button>
      ${r.canRespec ? '<button class="act ghost small" id="respec">↺ RESPEC</button>' : ''}
      <button class="act ghost small" id="openStats">📊 STATS</button>
      <button class="act" id="descend">DESCEND ▸</button>
    </div>
  </div>`;
  logEl.innerHTML = '';
  if (fresh) {
    board.querySelectorAll('.pill[data-class]').forEach((b) => b.addEventListener('click', () => newRun(difficulty, b.dataset.class)));
    board.querySelectorAll('.pill[data-diff]').forEach((b) => b.addEventListener('click', () => { if (!b.disabled) newRun(b.dataset.diff, classId); }));
  }
  board.querySelectorAll('[data-attr]').forEach((b) => b.addEventListener('click', () => { game.investAttr(b.dataset.attr); expose(); renderTown(game.getRun()); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  document.getElementById('openTree').addEventListener('click', () => { treeOpen = true; renderOverlay(); });
  document.getElementById('openStats').addEventListener('click', () => renderStats());
  const rb = document.getElementById('respec'); if (rb) rb.addEventListener('click', () => { game.respec(); expose(); renderTown(game.getRun()); });
  document.getElementById('descend').addEventListener('click', () => { const res = game.descend(); if (res.ok) render(); });
}

// ---- Stats screen (reads the telemetry aggregates; export shares them with the dev) ----
function renderStats() {
  const c = TEL.combat; const pct = (a, b) => b > 0 ? Math.round(a / b * 100) : 0;
  const topSkills = Object.entries(TEL.skills).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const classRows = Object.entries(TEL.byClass).map(([k, v]) => `<tr><td>${k}</td><td>${v.runs}</td><td>${v.wins}</td><td>${v.deaths}</td><td>${v.maxLevel}</td><td>${v.bestArea || 0}/8</td></tr>`).join('');
  const deaths = TEL.deathLog.slice(-8).reverse().map((d) => `${d.class} · L${d.level} · Area ${d.area || '?'}${d.areaName ? ' (' + d.areaName + ')' : ''}${d.diff ? ' · ' + d.diff : ''}`).join('<br>') || '—';
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">📊 Play Statistics</div><button class="inv-close" id="cx">✕</button></div>
    <div class="sk-sub">Unbiased log of what actually happens — so balance is driven by data, not vibes. Runs: <b>${TEL.runs}</b> · Wins: <b>${TEL.wins}</b> · Deaths: <b>${TEL.deaths}</b></div>
    <table class="stt"><tr><th>Class</th><th>Runs</th><th>W</th><th>D</th><th>Max Lv</th><th>Best Area</th></tr>${classRows || '<tr><td colspan=6>no runs yet</td></tr>'}</table>
    <div class="stblk"><b>Combat</b> — runs ${c.fights} · hit rate ${pct(c.hits, c.hits + c.misses)}% · evades ${c.evades} · kills ${c.kills}<br>dmg dealt ${c.dmgDealt} · dmg taken ${c.dmgTaken} · avg run length ${c.fights ? (c.turns / c.fights).toFixed(0) + 's' : '0s'}</div>
    <div class="stblk"><b>Movement</b> — moving <b>${pct(c.moveT, c.moveT + c.idleT)}%</b> of the time · idle ${Math.round(c.idleT)}s · traveled ${Math.round(c.moveDist / 100)} screens<br><span style="color:#6f6357">low %? standing still shouldn't work — that's the balance signal</span></div>
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


// ---------- the SURVIVAL arena (real-time, one big map) ----------
// You are a token in a big arena and MOVE (WASD / arrows / drag); the camera follows
// you. Abilities auto-fire on cooldown when Mana allows. Waves ramp, monsters drop
// loot you walk over, and The Smith lands at the 5-min mark — kill it to clear the
// tier. We drive our own rAF loop (not render()): engine ticks at fixed DT, canvas paints.
const keys = new Set();
let touchVec = null, joy = null;
let arenaActive = false, arenaPaused = false, raf = 0, lastT = 0, tacc = 0;
let rtCanvas = null, rtCtx = null, rtSkillEls = {};
let lootToast = null, levelToast = null, questToast = null, lastArena = null;
const clampN = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const KEYMAP = { arrowup: 'up', w: 'up', arrowdown: 'down', s: 'down', arrowleft: 'left', a: 'left', arrowright: 'right', d: 'right' };
window.addEventListener('keydown', (e) => { if (!arenaActive || arenaPaused) return; const m = KEYMAP[e.key.toLowerCase()]; if (m) { keys.add(m); e.preventDefault(); } });
window.addEventListener('keyup', (e) => { const m = KEYMAP[e.key.toLowerCase()]; if (m) keys.delete(m); });
function inputVector() {
  if (touchVec) return touchVec;
  let x = 0, y = 0; if (keys.has('left')) x -= 1; if (keys.has('right')) x += 1; if (keys.has('up')) y -= 1; if (keys.has('down')) y += 1;
  const l = Math.hypot(x, y); return l > 0 ? { x: x / l, y: y / l } : { x: 0, y: 0 };
}
function potionBtn(kind, count, full) { const label = kind === 'life' ? '🩹 Life' : '🔷 Mana';
  return `<button class="pot ${kind}" data-quaff="${kind}" ${count <= 0 || full ? 'disabled' : ''}>${label} <span class="pn">×${count}</span></button>`; }

function renderArena() {
  if (arenaActive) return; // the loop owns the DOM once it's up
  const s = combat.getState(); const h = s.hero; const pot = game.getRun().potions;
  lootToast = levelToast = questToast = null;
  particles.length = 0; prevHeroLife = null; shakeMag = 0; prevHeroX = null; prevHeroY = null; // fresh render state per segment
  board.innerHTML = `<div class="rt">
    <div class="area-head"><span class="ah-name" id="rtAreaName"></span><span class="ah-prog" id="rtAreaProg"></span></div>
    <div class="area-quest" id="rtQuest"></div>
    <div class="boss-bar" id="rtBossWrap" style="display:none"><i id="rtBoss"></i><span id="rtBossT"></span></div>
    <div class="rt-hud">
      <div class="rt-bars">
        <div class="rt-bar life"><i id="rtLife"></i><span id="rtLifeT"></span></div>
        <div class="rt-bar mana"><i id="rtMana"></i><span id="rtManaT"></span></div>
        <div class="rt-bar xp"><i id="rtXp"></i><span id="rtXpT"></span></div>
      </div>
      <div class="rt-meta"><span>Lv <b id="rtLvl">${game.getRun().level}</b></span><span>Foes <b id="rtFoes"></b></span><span id="rtTimeWrap">⏱ <b id="rtTime"></b></span></div>
    </div>
    <div class="rt-canvas-wrap"><canvas id="rtCanvas" width="${ARENA_W}" height="${ARENA_H}"></canvas><div class="loot-toast" id="rtLoot"></div><div class="arena-banner" id="rtBanner"></div></div>
    <div class="rt-skills" id="rtSkills">${skillChipsHTML(h.abilities)}</div>
    <div class="belt">${potionBtn('life', pot.life, h.life >= h.maxLife)}${potionBtn('mana', pot.mana, h.mana >= h.maxMana)}
      <button class="act ghost small" id="aInv">🎒</button><button class="act ghost small" id="aTree">⚔<span id="aTreePts"></span></button></div>
    <div class="rt-hint">Move: <b>WASD / arrows</b> or <b>drag</b>. Skills auto-fire — <b>tap one to toggle it off</b>. Monsters <b>drop loot</b> — walk over it. Outlast the timer, then kill the <b>gate</b> to clear the area.</div>
    <div class="controls" style="display:flex;gap:12px;justify-content:center"><button class="act ghost small" id="abandon">ABANDON</button></div>
  </div>`;
  logEl.innerHTML = '';
  rtCanvas = document.getElementById('rtCanvas'); rtCtx = rtCanvas.getContext('2d');
  bindSkillChips();
  bindArenaPointer();
  board.querySelectorAll('[data-quaff]').forEach((b) => b.addEventListener('click', (ev) => { ev.preventDefault(); const r = game.quaff(b.dataset.quaff); if (r && r.ok) { TEL.potions[b.dataset.quaff]++; tel('quaff', { kind: b.dataset.quaff }); } }));
  document.getElementById('aInv').addEventListener('click', () => { invOpen = true; pauseArena(); renderOverlay(); });
  document.getElementById('aTree').addEventListener('click', () => { treeOpen = true; pauseArena(); renderOverlay(); });
  document.getElementById('abandon').addEventListener('click', () => { if (!arenaActive) return; game.flee(); endArena(combat.getState()); });
  arenaActive = true; arenaPaused = false; lastT = performance.now(); tacc = 0; raf = requestAnimationFrame(arenaFrame);
}

// Skill chips: tap to toggle a skill's auto-fire off/on (e.g. Whirlwind, not Cleave).
function skillChipsHTML(abilities) { return abilities.map((a) => `<div class="rt-skill ${a.type}${a.off ? ' off' : ''}" data-id="${a.id}"><div class="rs-n">${a.name}</div><div class="rs-c">${a.cost ? a.cost + '⬡' : 'free'}</div><div class="rs-cd"></div></div>`).join(''); }
function bindSkillChips() { rtSkillEls = {}; board.querySelectorAll('.rt-skill').forEach((el) => { rtSkillEls[el.dataset.id] = el;
  el.addEventListener('click', () => { const on = combat.toggleAbility(el.dataset.id); el.classList.toggle('off', !on); tel('toggle_skill', { id: el.dataset.id, on }); }); }); }
function rebuildSkillChips(h) { const wrap = document.getElementById('rtSkills'); if (!wrap) return; wrap.innerHTML = skillChipsHTML(h.abilities); bindSkillChips(); }

function pauseArena() { arenaPaused = true; cancelAnimationFrame(raf); keys.clear(); touchVec = null; joy = null; }
function resumeArena() { if (!arenaActive || !arenaPaused) return; arenaPaused = false; lastT = performance.now(); tacc = 0; raf = requestAnimationFrame(arenaFrame); }

function bindArenaPointer() {
  const toCanvas = (ev) => { const r = rtCanvas.getBoundingClientRect(); return { x: (ev.clientX - r.left) / r.width * ARENA_W, y: (ev.clientY - r.top) / r.height * ARENA_H }; };
  rtCanvas.addEventListener('pointerdown', (ev) => { ev.preventDefault(); rtCanvas.setPointerCapture(ev.pointerId); const p = toCanvas(ev); joy = { ox: p.x, oy: p.y, cx: p.x, cy: p.y }; touchVec = { x: 0, y: 0 }; });
  rtCanvas.addEventListener('pointermove', (ev) => { if (!joy) return; const p = toCanvas(ev); joy.cx = p.x; joy.cy = p.y; const dx = p.x - joy.ox, dy = p.y - joy.oy; const l = Math.hypot(dx, dy); if (l < 8) { touchVec = { x: 0, y: 0 }; } else { const m = Math.min(1, l / 70); touchVec = { x: dx / l * m, y: dy / l * m }; } });
  const end = () => { joy = null; touchVec = null; };
  rtCanvas.addEventListener('pointerup', end); rtCanvas.addEventListener('pointercancel', end);
}

function arenaFrame(now) {
  if (!arenaActive || arenaPaused) return;
  let dt = (now - lastT) / 1000; lastT = now; if (dt > 0.05) dt = 0.05; tacc += dt * (window.__timescale || 1);
  const input = window.__autopilot ? combat.autoInput() : inputVector();
  const cap = window.__timescale ? 400 : 6;
  let guard = 0; while (tacc >= DT && guard < cap) { combat.tick(input); tacc -= DT; guard++; if (combat.getState().over) break; }
  const s = combat.getState();   // capture BEFORE syncArena — it may resolve the segment and null combat
  const sync = game.syncArena(); // fold earned XP -> levels, collected drops -> bag, quest clear -> town
  if (sync.loot && sync.loot.length) { const it = sync.loot[sync.loot.length - 1];
    const up = !it.isRune && game.compareItem && game.compareItem(it); const isUp = up && up.isUpgrade && up.wearable;
    lootToast = { name: (isUp ? '▲ ' : '') + it.name, color: isUp ? '#7ee27e' : (it.color || '#c8a24a'), t: isUp ? 2.4 : 1.6 }; tel('loot', { name: it.name }); }
  if (sync.leveled) { levelToast = { t: 1.4, lvl: game.getRun().level }; tel('level', { level: game.getRun().level }); } // banks points, no pause
  drawArena(s); updateHUD(s, dt);
  window.__bloodrune.state = s; window.__bloodrune.phase = game.getRun().phase; window.__bloodrune.run = game.getRun();
  if (s.over || game.getRun().phase !== 'arena') { endArena(s); return; } // died, fled, or cleared the quest -> leave the field
  raf = requestAnimationFrame(arenaFrame);
}

function endArena(s) {
  arenaActive = false; arenaPaused = false; cancelAnimationFrame(raf); touchVec = null; joy = null; keys.clear(); lastArena = s;
  recordCombatEnd(s); game.resolveArena(); afterTerminal(); render();
}

// ---- canvas painting (camera follows the hero across the big world) ----
// ---- procedural "graphics": atmospheric lighting, drawn creature bodies with
// depth (ground shadow + top highlight), glowing elemental spells, a particle
// system, and screen shake. No sprite assets — everything is drawn in code.
const ROLE_BODY = { grunt: '#3a1f2c', guardian: '#22304f', archer: '#1d2f4a', caster: '#331d46', elite: '#4a1a1a', archer_alt: '#243a24' };
const ELEM_COLOR = { fire: '#ff7a3a', cold: '#8fc4ff', lightning: '#d6a6ff', poison: '#8fe07a' };
let camX = 0, camY = 0, shakeMag = 0, prevHeroLife = null, ambientT = 0, prevHeroX = null, prevHeroY = null, heroFaceLeft = false;
const particles = []; // {x,y,vx,vy,life,maxLife,r,color,grav}
function spawnParticle(x, y, vx, vy, life, r, color, grav) { if (particles.length > 340) return; particles.push({ x, y, vx, vy, life, maxLife: life, r, color, grav: grav || 0 }); }
function burst(x, y, n, spd, color, life) { for (let i = 0; i < n; i++) { const a = Math.random() * 7, s2 = spd * (0.4 + Math.random() * 0.8); spawnParticle(x, y, Math.cos(a) * s2, Math.sin(a) * s2, life * (0.6 + Math.random() * 0.6), 1.5 + Math.random() * 2.5, color, 40); } }
function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }

// ---- SVG SPRITES (hand-drawn vector art, embedded as data-URIs — CSP-safe) ----
// Each is a small viewBox drawn as layered shapes; rendered to the canvas over the
// unit's shadow, with the procedural body as fallback for anything not spritted.
const SPRITE_SVG = {
  // heroes (mapped by class glyph)
  sorceress: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M8 42 Q6 22 20 16 Q34 22 32 42Z" fill="#33306a"/><path d="M20 16 Q34 22 32 42 L24 42 Q26 26 20 20Z" fill="#25234d"/><path d="M10 21 Q20 3 30 21 Q25 12 20 12 Q15 12 10 21Z" fill="#463f86"/><circle cx="20" cy="19" r="5.2" fill="#ecdcc6"/><circle cx="18" cy="19" r="1.1" fill="#2e2450"/><circle cx="22" cy="19" r="1.1" fill="#2e2450"/><path d="M10 21 Q20 3 30 21 Q24 10 20 10 Q16 10 10 21Z" fill="none" stroke="#5a52a4" stroke-width="1.4" opacity=".7"/><circle cx="32" cy="31" r="4.6" fill="#7fe3ff" opacity=".5"/><circle cx="32" cy="31" r="2.6" fill="#e6fbff"/></svg>`,
  barbarian: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M12 44 L11 26 Q20 22 29 26 L28 44Z" fill="#6a4a30"/><path d="M11 27 Q20 30 29 27 L28 34 Q20 37 12 34Z" fill="#7d3a2a"/><circle cx="20" cy="16" r="6" fill="#d8b088"/><path d="M14 12 Q20 4 26 12 Q24 8 20 8 Q16 8 14 12Z" fill="#5a3a22"/><path d="M13 12 Q10 6 8 9 M27 12 Q30 6 32 9" stroke="#e8ddc8" stroke-width="2" fill="none"/><circle cx="18" cy="16" r="1" fill="#3a2416"/><circle cx="22" cy="16" r="1" fill="#3a2416"/><rect x="30" y="10" width="3" height="30" rx="1" fill="#7a6250" transform="rotate(18 31 25)"/><path d="M31 8 L40 14 L33 18Z" fill="#b8bcc4" transform="rotate(18 31 25)"/></svg>`,
  amazon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M12 44 L12 26 Q20 22 28 26 L28 44Z" fill="#3f5540"/><path d="M12 27 Q20 30 28 27 L27 33 Q20 36 13 33Z" fill="#5a7a4e"/><circle cx="20" cy="16" r="5.6" fill="#e0b892"/><path d="M15 12 Q20 5 25 12 L26 22 Q20 15 14 22Z" fill="#6b4a2a"/><circle cx="18" cy="16" r="1" fill="#3a2416"/><circle cx="22" cy="16" r="1" fill="#3a2416"/><path d="M31 8 Q37 20 31 34" stroke="#8a6a44" stroke-width="2" fill="none"/><line x1="31" y1="8" x2="31" y2="34" stroke="#e8ddc8" stroke-width="1"/></svg>`,
  necromancer: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M8 42 Q7 22 20 16 Q33 22 32 42Z" fill="#2a2e34"/><path d="M20 16 Q33 22 32 42 L25 42 Q26 26 20 20Z" fill="#1c2024"/><path d="M11 21 Q20 4 29 21 Q24 11 20 11 Q16 11 11 21Z" fill="#3a4046"/><circle cx="20" cy="19" r="5" fill="#dfe4e0"/><circle cx="17.6" cy="19" r="1.4" fill="#1a1a1a"/><circle cx="22.4" cy="19" r="1.4" fill="#1a1a1a"/><path d="M18 23 L22 23" stroke="#8a8a8a" stroke-width="1"/><line x1="32" y1="8" x2="32" y2="40" stroke="#c9bfa8" stroke-width="2"/><circle cx="32" cy="9" r="3" fill="#e6ddc8"/></svg>`,
  // monsters (mapped by enemy id)
  fallen: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M14 42 Q12 28 20 26 Q28 28 26 42Z" fill="#7a2f24"/><circle cx="20" cy="20" r="8" fill="#9a3a2a"/><path d="M13 15 Q8 8 6 14 M27 15 Q32 8 34 14" stroke="#c85a3a" stroke-width="2.2" fill="none"/><path d="M12 18 Q4 18 3 22 Q9 22 12 21Z M28 18 Q36 18 37 22 Q31 22 28 21Z" fill="#8a3326"/><circle cx="16.5" cy="20" r="2" fill="#ffd23a"/><circle cx="23.5" cy="20" r="2" fill="#ffd23a"/><circle cx="16.5" cy="20" r=".8" fill="#3a1a00"/><circle cx="23.5" cy="20" r=".8" fill="#3a1a00"/><path d="M16 25 Q20 28 24 25" stroke="#3a1400" stroke-width="1.3" fill="none"/></svg>`,
  zombie: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M13 43 Q11 26 20 22 Q29 26 27 43Z" fill="#4a5e3a"/><path d="M6 30 Q10 26 14 30 M34 30 Q30 26 26 30" stroke="#5a6e46" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="20" cy="16" r="6.5" fill="#7a8a5a"/><path d="M14 15 L26 15" stroke="#3a4a2a" stroke-width="1" opacity=".6"/><circle cx="17.5" cy="16" r="1.6" fill="#1a1a10"/><circle cx="22.5" cy="16" r="1.6" fill="#c8c8a0"/><path d="M16 20 L24 20" stroke="#2a1a10" stroke-width="1.4"/><path d="M18 26 Q20 30 22 26" fill="#6a1a1a"/></svg>`,
  quill_rat: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M8 34 Q20 20 34 34 Q30 40 20 40 Q10 40 8 34Z" fill="#6a4a30"/><path d="M12 30 L8 20 M17 27 L15 16 M22 27 L24 16 M27 30 L31 20" stroke="#8a6a44" stroke-width="2.4" stroke-linecap="round"/><circle cx="30" cy="34" r="6" fill="#7d5636"/><circle cx="32" cy="33" r="1.6" fill="#2a0a00"/><path d="M35 31 Q40 30 40 33" stroke="#d89a7a" stroke-width="1.4" fill="none"/><path d="M8 36 Q2 38 3 42" stroke="#5a3a22" stroke-width="2" fill="none"/></svg>`,
  goatman: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M13 44 L12 24 Q20 20 28 24 L27 44Z" fill="#5a4632"/><path d="M12 25 Q20 28 28 25 L27 33 Q20 36 13 33Z" fill="#6e5a40"/><circle cx="20" cy="16" r="6.5" fill="#8a7458"/><path d="M14 12 Q7 4 5 12 Q9 9 13 12Z M26 12 Q33 4 35 12 Q31 9 27 12Z" fill="#d8cdb8"/><path d="M18 22 Q20 25 22 22" fill="#3a2a1a"/><circle cx="17.5" cy="16" r="1.2" fill="#c0102a"/><circle cx="22.5" cy="16" r="1.2" fill="#c0102a"/><rect x="30" y="14" width="2.6" height="26" rx="1" fill="#5a4432" transform="rotate(14 31 27)"/></svg>`,
  archer: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 46"><path d="M10 42 Q9 22 20 16 Q31 22 30 42Z" fill="#243626"/><path d="M20 16 Q31 22 30 42 L24 42 Q25 26 20 20Z" fill="#182619"/><path d="M11 21 Q20 6 29 21 Q24 13 20 13 Q16 13 11 21Z" fill="#2e4230"/><circle cx="20" cy="19" r="4.6" fill="#c8a882"/><circle cx="18.4" cy="19" r="1" fill="#1a2a10"/><circle cx="21.6" cy="19" r="1" fill="#1a2a10"/><path d="M9 8 Q3 23 9 38" stroke="#7a5a34" stroke-width="2.2" fill="none"/><line x1="9" y1="8" x2="9" y2="38" stroke="#d8cdb0" stroke-width="1"/><line x1="9" y1="23" x2="26" y2="23" stroke="#e8ddc8" stroke-width="1.4"/><path d="M26 23 L22 21 M26 23 L22 25" stroke="#e8ddc8" stroke-width="1.4" fill="none"/></svg>`,
};
const RASTER = (typeof RASTER_SPRITES !== 'undefined') ? RASTER_SPRITES : {};
const spriteCache = {};
function getSprite(id) {
  if (!id) return null;
  if (id in spriteCache) return spriteCache[id];
  // painted art first; hand-drawn SVG as fallback (e.g. the zombie placeholder)
  const src = RASTER[id] || (SPRITE_SVG[id] ? 'data:image/svg+xml;utf8,' + encodeURIComponent(SPRITE_SVG[id]) : null);
  if (!src) { spriteCache[id] = null; return null; }
  const img = new Image(); img.src = src; spriteCache[id] = img; return img;
}
const HERO_SPRITE = { '🔮': 'sorceress', '🪓': 'barbarian', '🏹': 'amazon', '💀': 'necromancer' };
// Sprites come alive in CODE (no extra art): flip to face travel, a walk-bob, a
// lean into movement, and a squash-pop on hit. Anchored at the feet so scaling
// keeps them planted. opt: { faceLeft, bob, lean, squash }.
function drawSprite(c, id, x, y, r, opt) {
  const img = getSprite(id); if (!img || !img.complete || !img.naturalWidth) return false;
  opt = opt || {}; const s = r * 2.9;
  c.save();
  c.translate(x, y + r);                     // anchor at the feet
  if (opt.lean) c.rotate(opt.lean);
  const sq = opt.squash || 0;                // hit pop: a SUBTLE flatten (realistic art, not cartoon rubber)
  c.scale((opt.faceLeft ? -1 : 1) * (1 + sq * 0.09), 1 - sq * 0.12);
  c.drawImage(img, -s / 2, -s * 0.96 + (opt.bob || 0), s, s);
  c.restore();
  return true;
}

function drawArena(s) {
  const c = rtCtx; const h = s.hero; const w = s.world || { w: ARENA_W, h: ARENA_H }; const dt = 1 / 30;
  ambientT += dt;
  // screen shake when the hero takes a hit
  if (prevHeroLife != null && h.life < prevHeroLife - 0.5) shakeMag = Math.min(11, shakeMag + Math.min(9, (prevHeroLife - h.life) * 0.25 + 2));
  prevHeroLife = h.life; shakeMag *= 0.86;
  const shx = shakeMag ? (Math.random() - 0.5) * shakeMag : 0, shy = shakeMag ? (Math.random() - 0.5) * shakeMag : 0;
  // ZOOM the camera in so the painted sprites read BIG — the viewport shows fewer
  // world units, and everything is drawn scaled up.
  const ZOOM = 1.55; const viewW = ARENA_W / ZOOM, viewH = ARENA_H / ZOOM;
  camX = clampN(h.x - viewW / 2, 0, Math.max(0, w.w - viewW));
  camY = clampN(h.y - viewH / 2, 0, Math.max(0, w.h - viewH));
  const vis = (x, y, r) => x + r > camX - 40 && x - r < camX + viewW + 40 && y + r > camY - 40 && y - r < camY + viewH + 40;
  // ground base
  c.fillStyle = '#0b0709'; c.fillRect(0, 0, ARENA_W, ARENA_H);
  c.save(); c.scale(ZOOM, ZOOM); c.translate(-camX + shx / ZOOM, -camY + shy / ZOOM);

  // --- ground: torch-lit stone with a drifting warm pool under the hero ---
  const gpool = c.createRadialGradient(h.x, h.y, 20, h.x, h.y, 460);
  gpool.addColorStop(0, 'rgba(60,34,26,0.55)'); gpool.addColorStop(0.5, 'rgba(30,18,20,0.28)'); gpool.addColorStop(1, 'rgba(10,7,9,0)');
  c.fillStyle = gpool; c.fillRect(camX, camY, viewW, viewH);
  c.strokeStyle = 'rgba(70,50,55,0.10)'; c.lineWidth = 1; // faint flagstone seams
  const gx0 = Math.floor(camX / 120) * 120, gy0 = Math.floor(camY / 120) * 120;
  for (let x = gx0; x <= camX + viewW; x += 120) { c.beginPath(); c.moveTo(x, camY); c.lineTo(x, camY + viewH); c.stroke(); }
  for (let y = gy0; y <= camY + viewH; y += 120) { c.beginPath(); c.moveTo(camX, y); c.lineTo(camX + viewW, y); c.stroke(); }
  // ruined, blood-lit world border
  c.strokeStyle = 'rgba(150,30,30,0.55)'; c.lineWidth = 6; c.strokeRect(0, 0, w.w, w.h);
  c.strokeStyle = 'rgba(255,90,70,0.18)'; c.lineWidth = 16; c.strokeRect(0, 0, w.w, w.h);

  // gems (xp motes) — drifting cyan sparks
  for (const g of s.gems) { if (!vis(g.x, g.y, 4)) continue; c.fillStyle = 'rgba(130,210,225,0.55)'; c.beginPath(); c.arc(g.x, g.y, 2.4, 0, 7); c.fill(); }
  // dropped loot — a glowing gem in its rarity color, bobbing
  for (const p of (s.pickups || [])) { if (!vis(p.x, p.y, 20)) continue; const bob = Math.sin(ambientT * 3 + p.x) * 2;
    c.fillStyle = hexA(p.color, 0.22); c.beginPath(); c.arc(p.x, p.y + bob, 16, 0, 7); c.fill();
    c.save(); c.translate(p.x, p.y + bob); c.rotate(Math.PI / 4); c.fillStyle = p.color; c.strokeStyle = 'rgba(255,255,255,.85)'; c.lineWidth = 1.5;
    c.beginPath(); c.rect(-6, -6, 12, 12); c.fill(); c.stroke(); c.restore(); }

  // fx UNDER units (cast rings, sweeps, ground bursts)
  for (const f of s.fx) if (f.type !== 'dmg' && f.type !== 'miss' && f.type !== 'evade' && f.type !== 'immune' && f.type !== 'chain' && vis(f.x, f.y, (f.r || 24) + 24)) drawFx(c, f);

  // minions (undead allies)
  for (const m of s.minions) { if (!vis(m.x, m.y, m.r)) continue; drawShadow(c, m.x, m.y, m.r); drawBody(c, m.x, m.y, m.r, '#1a2038', '#7a80a0', 0); glyph(c, m.glyph, m.x, m.y - 1, m.r * 1.5); }

  // enemies — drawn creature bodies with depth, threat-tinted rim + aura, hp bar
  for (const e of s.enemies) { if (e.hp <= 0 || !vis(e.x, e.y, e.r + 6)) continue;
    const tier = e.boss ? '#ff3b3b' : e.unique ? '#c8a24a' : e.elite ? '#e0484a' : e.raised ? '#8fbf8f' : '#5a4450';
    if (e.boss || e.unique || e.elite) { c.fillStyle = hexA(tier, 0.16); c.beginPath(); c.arc(e.x, e.y, e.r + 10 + Math.sin(ambientT * 4) * 2, 0, 7); c.fill(); }
    drawShadow(c, e.x, e.y, e.r);
    const eopt = { faceLeft: e.x > h.x + 4, bob: Math.sin(ambientT * 7 + e.x * 0.25) * 1.0, // shamble toward you
      lean: clampN((h.x - e.x) * 0.0004, -0.06, 0.06), squash: e.flash > 0 ? 0.7 : 0 };
    if (!drawSprite(c, e.id, e.x, e.y, e.r, eopt)) { // hand-drawn sprite, else procedural body+glyph
      const body = e.flash > 0 ? '#ffffff' : (ROLE_BODY[e.role] || '#2a1721');
      drawBody(c, e.x, e.y, e.r, body, tier, (e.boss || e.unique || e.elite) ? 2.5 : 1.5);
      glyph(c, e.glyph, e.x, e.y - 1, e.r * 1.7);
    } else if (e.flash > 0) { c.save(); c.globalAlpha = 0.5; c.fillStyle = '#fff'; c.beginPath(); c.arc(e.x, e.y - e.r * 0.25, e.r * 1.05, 0, 7); c.fill(); c.restore(); }
    const bw = e.r * 2.2, hpf = Math.max(0, e.hp / e.maxHp); c.fillStyle = 'rgba(20,6,6,0.85)'; c.fillRect(e.x - bw / 2, e.y - e.r - 9, bw, 3.6);
    c.fillStyle = e.unique || e.boss ? '#e6c24a' : '#d23a3a'; c.fillRect(e.x - bw / 2, e.y - e.r - 9, bw * hpf, 3.6); }

  // projectiles — glowing elemental orbs with a trail
  for (const p of s.projectiles) { if (!vis(p.x, p.y, p.r + 8)) continue;
    const col = p.hostile ? '#ff5a4a' : (ELEM_COLOR[p.element] || '#ffd98a');
    if (Math.random() < 0.7) spawnParticle(p.x, p.y, (p.vx || 0) * -0.05, (p.vy || 0) * -0.05, 0.35, p.r * 0.9, col, 0);
    c.fillStyle = hexA(col, 0.25); c.beginPath(); c.arc(p.x, p.y, p.r + 5, 0, 7); c.fill();
    c.fillStyle = col; c.beginPath(); c.arc(p.x, p.y, p.r, 0, 7); c.fill();
    c.fillStyle = 'rgba(255,255,255,0.85)'; c.beginPath(); c.arc(p.x - p.r * 0.3, p.y - p.r * 0.3, p.r * 0.4, 0, 7); c.fill(); }

  // the hero — a lit figure with a facing weapon-glint, aura, shield/invuln
  const hx = h.x, hy = h.y; const dir = h.dir || { x: 0, y: -1 };
  c.fillStyle = 'rgba(255,210,140,0.10)'; c.beginPath(); c.arc(hx, hy, 40, 0, 7); c.fill(); // torch aura
  drawShadow(c, hx, hy, h.r);
  if (h.shield > 0) { c.strokeStyle = `rgba(210,175,90,${0.5 + Math.sin(ambientT * 8) * 0.2})`; c.lineWidth = 2.5; c.beginPath(); c.arc(hx, hy, h.r + 7, 0, 7); c.stroke(); }
  const moved = prevHeroX != null && (Math.abs(hx - prevHeroX) + Math.abs(hy - prevHeroY)) > 0.6;
  prevHeroX = hx; prevHeroY = hy;
  if (dir.x < -0.15) heroFaceLeft = true; else if (dir.x > 0.15) heroFaceLeft = false;
  const hopt = { faceLeft: heroFaceLeft, lean: moved ? clampN(dir.x, -1, 1) * 0.05 : 0,
    bob: moved ? Math.sin(ambientT * 10) * 1.3 : Math.sin(ambientT * 3) * 0.6, squash: 0 }; // hero hit-feedback is the i-frame flicker, not a squash
  c.globalAlpha = h.invuln ? 0.5 : 1;
  if (!drawSprite(c, HERO_SPRITE[h.glyph], hx, hy, h.r, hopt)) { // class sprite, else procedural
    drawBody(c, hx, hy, h.r, '#3a2616', '#e6c24a', 2.5);
    c.strokeStyle = 'rgba(240,220,160,0.9)'; c.lineWidth = 3; c.beginPath(); c.moveTo(hx + dir.x * h.r * 0.7, hy + dir.y * h.r * 0.7); c.lineTo(hx + dir.x * (h.r + 9), hy + dir.y * (h.r + 9)); c.stroke();
    glyph(c, h.glyph, hx, hy - 1, h.r * 2);
  }
  c.globalAlpha = 1;

  // particles (additive glow)
  c.globalCompositeOperation = 'lighter';
  for (let i = particles.length - 1; i >= 0; i--) { const pt = particles[i]; pt.life -= dt; if (pt.life <= 0) { particles.splice(i, 1); continue; }
    pt.x += pt.vx * dt; pt.y += pt.vy * dt; pt.vy += pt.grav * dt; pt.vx *= 0.94; pt.vy *= 0.94;
    if (!vis(pt.x, pt.y, pt.r + 2)) continue; const a = Math.max(0, pt.life / pt.maxLife);
    c.fillStyle = hexA(pt.color, a * 0.8); c.beginPath(); c.arc(pt.x, pt.y, pt.r * (0.4 + a * 0.6), 0, 7); c.fill(); }
  c.globalCompositeOperation = 'source-over';

  // floating text fx OVER everything (damage / miss / dodge / immune)
  for (const f of s.fx) if ((f.type === 'dmg' || f.type === 'miss' || f.type === 'evade' || f.type === 'immune' || f.type === 'chain') && vis(f.x, f.y, 200)) drawFx(c, f);
  c.restore();

  // --- lighting: vignette darkens the edges so the torch-lit centre pops ---
  const vg = c.createRadialGradient(ARENA_W / 2, ARENA_H / 2, ARENA_H * 0.35, ARENA_W / 2, ARENA_H / 2, ARENA_H * 0.85);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.62)');
  c.fillStyle = vg; c.fillRect(0, 0, ARENA_W, ARENA_H);

  if (joy) { c.strokeStyle = 'rgba(210,185,150,.35)'; c.lineWidth = 2; c.beginPath(); c.arc(joy.ox, joy.oy, 40, 0, 7); c.stroke();
    c.fillStyle = 'rgba(210,185,150,.55)'; c.beginPath(); c.arc(joy.cx, joy.cy, 14, 0, 7); c.fill(); }
}
// a soft ground shadow gives every unit weight
function drawShadow(c, x, y, r) { c.fillStyle = 'rgba(0,0,0,0.38)'; c.beginPath(); c.ellipse(x, y + r * 0.72, r * 0.95, r * 0.42, 0, 0, 7); c.fill(); }
// a body disc lit from top-left (cheap fake lighting: dark base + offset highlight)
function drawBody(c, x, y, r, base, rim, rimW) {
  c.fillStyle = base; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill();
  c.fillStyle = 'rgba(255,255,255,0.12)'; c.beginPath(); c.arc(x - r * 0.28, y - r * 0.32, r * 0.62, 0, 7); c.fill();
  if (rimW) { c.strokeStyle = rim; c.lineWidth = rimW; c.beginPath(); c.arc(x, y, r, 0, 7); c.stroke(); }
}
function glyph(c, g, x, y, size) { c.font = `${Math.round(size)}px serif`; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillStyle = 'rgba(0,0,0,0.5)'; c.fillText(g, x + 1, y + 1.5); c.fillStyle = '#fff'; c.fillText(g, x, y); }
function drawFx(c, f) {
  const t = f.life / f.maxLife;
  if (f.type === 'sweep') { c.strokeStyle = `rgba(240,210,160,${0.55 * t})`; c.lineWidth = 3.5; c.beginPath(); c.arc(f.x, f.y, f.r * (1.15 - t * 0.25), 0, 7); c.stroke(); }
  else if (f.type === 'cast') { const col = f.color || '#c8a24a';
    c.strokeStyle = hexA(col, 0.7 * t); c.lineWidth = 3; c.beginPath(); c.arc(f.x, f.y, f.r * (1.4 - t * 0.5), 0, 7); c.stroke();
    c.fillStyle = hexA(col, 0.10 * t); c.beginPath(); c.arc(f.x, f.y, f.r * (1.4 - t * 0.5), 0, 7); c.fill();
    if (t > 0.94) burst(f.x, f.y, 6, 120, col, 0.5); } // one-time spark when the ring is born
  else if (f.type === 'dash') { c.fillStyle = `rgba(210,175,90,${0.4 * t})`; c.beginPath(); c.arc(f.x, f.y, 22 * (1.2 - t), 0, 7); c.fill(); }
  else if (f.type === 'ring') { const rr = (f.r || 130) * (0.35 + (1 - t) * 0.85); // Nova / Frost Nova / Static Field — an expanding burst-ring
    c.strokeStyle = hexA(f.color || '#c8a24a', 0.75 * t); c.lineWidth = 3 + (1 - t) * 4; c.beginPath(); c.arc(f.x, f.y, rr, 0, 7); c.stroke();
    c.fillStyle = hexA(f.color || '#c8a24a', 0.08 * t); c.beginPath(); c.arc(f.x, f.y, rr, 0, 7); c.fill(); }
  else if (f.type === 'telegraph') { const pulse = 0.45 + 0.4 * Math.abs(Math.sin(f.life * 24)); // ground warning before a strike lands
    c.strokeStyle = hexA(f.color || '#ff5a4a', pulse); c.lineWidth = 2.5; c.setLineDash([7, 6]); c.beginPath(); c.arc(f.x, f.y, f.r || 120, 0, 7); c.stroke(); c.setLineDash([]);
    c.fillStyle = hexA(f.color || '#ff5a4a', 0.12); c.beginPath(); c.arc(f.x, f.y, (f.r || 120) * (1 - t * 0.25), 0, 7); c.fill(); }
  else if (f.type === 'impact') { const rr = (f.r || 130) * (0.5 + (1 - t) * 0.7); // Meteor / Glacial Spike landing
    c.fillStyle = hexA(f.color || '#ff7a3a', 0.4 * t); c.beginPath(); c.arc(f.x, f.y, rr, 0, 7); c.fill();
    c.strokeStyle = `rgba(255,255,255,${0.6 * t})`; c.lineWidth = 3; c.beginPath(); c.arc(f.x, f.y, rr, 0, 7); c.stroke();
    if (t > 0.86) burst(f.x, f.y, 12, 200, f.color || '#ff7a3a', 0.55); }
  else if (f.type === 'chain') { // Chain Lightning — a jagged bolt leaping between foes
    const col = f.color || '#d6a6ff'; const seg = 7;
    c.strokeStyle = hexA(col, 0.9 * t); c.lineWidth = 3; c.beginPath(); c.moveTo(f.x, f.y);
    for (let i = 1; i < seg; i++) { const u = i / seg; c.lineTo(f.x + (f.x2 - f.x) * u + (Math.random() - 0.5) * 11, f.y + (f.y2 - f.y) * u + (Math.random() - 0.5) * 11); }
    c.lineTo(f.x2, f.y2); c.stroke();
    c.strokeStyle = `rgba(255,255,255,${0.85 * t})`; c.lineWidth = 1.2; c.stroke(); }
  else if (f.type === 'beam') { // Lightning — a straight lance of current down a lane
    const col = f.color || '#d6a6ff'; c.lineCap = 'round';
    c.strokeStyle = hexA(col, 0.85 * t); c.lineWidth = 10; c.beginPath(); c.moveTo(f.x, f.y); c.lineTo(f.x2, f.y2); c.stroke();
    c.strokeStyle = `rgba(255,255,255,${0.92 * t})`; c.lineWidth = 2.6; c.stroke();
    for (let i = 0; i < 4; i++) { const u = 0.2 + 0.2 * i; burst(f.x + (f.x2 - f.x) * u, f.y + (f.y2 - f.y) * u, 1, 40, col, 0.3); }
    c.lineCap = 'butt'; }
  else if (f.type === 'cone') { // Inferno — a wedge of flame poured out in front
    const col = f.color || '#ff7a3a';
    const g = c.createRadialGradient(f.x, f.y, 0, f.x, f.y, f.range);
    g.addColorStop(0, hexA(col, 0.55 * t)); g.addColorStop(0.6, hexA(col, 0.28 * t)); g.addColorStop(1, hexA(col, 0));
    c.fillStyle = g; c.beginPath(); c.moveTo(f.x, f.y); c.arc(f.x, f.y, f.range, f.ang - f.half, f.ang + f.half); c.closePath(); c.fill(); }
  else if (f.type === 'hurt') { c.strokeStyle = `rgba(230,40,40,${0.55 * t})`; c.lineWidth = 3.5; c.beginPath(); c.arc(f.x, f.y, 22 * (1.4 - t), 0, 7); c.stroke();
    if (t > 0.9) burst(f.x, f.y, 5, 90, '#c62828', 0.45); }
  else if (f.type === 'dmg') { const rise = (1 - t) * 16; c.font = 'bold 15px sans-serif'; c.textAlign = 'center';
    c.fillStyle = `rgba(0,0,0,${0.5 * Math.min(1, t * 1.5)})`; c.fillText(f.val, f.x + 1, f.y - rise + 1);
    c.fillStyle = `rgba(255,232,190,${Math.min(1, t * 1.5)})`; c.fillText(f.val, f.x, f.y - rise); }
  else if (f.type === 'miss') { c.fillStyle = `rgba(160,160,170,${t})`; c.font = '11px sans-serif'; c.textAlign = 'center'; c.fillText('miss', f.x, f.y); }
  else if (f.type === 'evade') { c.fillStyle = `rgba(150,200,255,${t})`; c.font = '11px sans-serif'; c.textAlign = 'center'; c.fillText('dodge', f.x, f.y); }
  else if (f.type === 'immune') { c.fillStyle = `rgba(190,190,200,${t})`; c.font = 'bold 11px sans-serif'; c.textAlign = 'center'; c.fillText('IMMUNE', f.x, f.y); }
}

function updateHUD(s, dt) {
  const h = s.hero; const r = game.getRun(); const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const wl = document.getElementById('rtLife'), wm = document.getElementById('rtMana'), wx = document.getElementById('rtXp');
  if (wl) wl.style.width = pv(h.life, h.maxLife) + '%'; if (wm) wm.style.width = pv(h.mana, h.maxMana) + '%';
  if (wx) wx.style.width = pv(r.xp, r.xpToNext) + '%';
  set('rtLifeT', `${Math.ceil(h.life)}/${h.maxLife}`); set('rtManaT', `${Math.floor(h.mana)}/${h.maxMana}`); set('rtXpT', `XP ${r.xp}/${r.xpToNext}`);
  set('rtFoes', s.aliveCount != null ? s.aliveCount : s.enemies.length); set('rtLvl', r.level);
  // area header + quest + gate timer
  const ar = s.area;
  if (ar) { set('rtAreaName', ar.name); set('rtAreaProg', `Area ${ar.idx + 1}/${ar.total}`);
    const q = document.getElementById('rtQuest'); if (q) q.textContent = (ar.quest ? '✦ ' + ar.quest + ' — ' : '') + ar.questText;
    set('rtTime', ar.gateSpawned ? '⚔ GATE' : `gate ${Math.ceil(ar.timeLeft)}s`);
    const tw = document.getElementById('rtTimeWrap'); if (tw) tw.classList.toggle('gate', ar.gateSpawned); }
  else { const mm = Math.floor(s.time / 60), ss = String(Math.floor(s.time % 60)).padStart(2, '0'); set('rtTime', `${mm}:${ss}`); }
  // gate/boss bar
  const bw = document.getElementById('rtBossWrap');
  if (bw) { if (s.boss) { bw.style.display = ''; const bi = document.getElementById('rtBoss'); if (bi) bi.style.width = pv(s.boss.hp, s.boss.maxHp) + '%'; set('rtBossT', `☠ ${s.boss.name}`); } else bw.style.display = 'none'; }
  // transient banner: area-clear / level-up flourish (no pause)
  const bn = document.getElementById('rtBanner');
  if (bn) { let txt = '', cls = 'arena-banner';
    if (questToast && questToast.t > 0) { questToast.t -= dt; txt = `<div class="ab-big">${questToast.text}</div><div class="ab-sub">${questToast.reward}</div>`; cls += ' show gold'; }
    else if (levelToast && levelToast.t > 0) { levelToast.t -= dt; txt = `<div class="ab-big">LEVEL ${levelToast.lvl}</div>`; cls += ' show'; }
    bn.innerHTML = txt; bn.className = cls; }
  if (h.abilities.length !== Object.keys(rtSkillEls).length || h.abilities.some((a) => !rtSkillEls[a.id])) rebuildSkillChips(h); // a newly-learned skill grew the kit
  for (const a of h.abilities) { const el = rtSkillEls[a.id]; if (!el) continue;
    el.classList.toggle('ready', a.ready); el.classList.toggle('off', !!a.off); const bar = el.querySelector('.rs-cd'); if (bar) bar.style.height = Math.min(100, (a.cd / 1.8) * 100) + '%'; }
  const pot = r.potions;
  const lb = board.querySelector('[data-quaff="life"]'), mb = board.querySelector('[data-quaff="mana"]');
  if (lb) { lb.disabled = pot.life <= 0 || h.life >= h.maxLife; lb.querySelector('.pn').textContent = '×' + pot.life; }
  if (mb) { mb.disabled = pot.mana <= 0 || h.mana >= h.maxMana; mb.querySelector('.pn').textContent = '×' + pot.mana; }
  const pts = document.getElementById('aTreePts'); if (pts) pts.textContent = r.skillPoints ? ' ' + r.skillPoints : '';
  const treeBtn = document.getElementById('aTree'); if (treeBtn) treeBtn.classList.toggle('pulse', r.skillPoints > 0);
  // loot toast
  const lt = document.getElementById('rtLoot');
  if (lt) { if (lootToast && lootToast.t > 0) { lootToast.t -= dt; lt.textContent = '＋ ' + lootToast.name; lt.style.color = lootToast.color; lt.style.opacity = Math.min(1, lootToast.t); } else lt.style.opacity = 0; }
}

let lastRecorded = null;
function recordCombatEnd(s) { if (!s || !s.over || s === lastRecorded) return; lastRecorded = s; const ty = s.tally; const c = TEL.combat;
  c.fights++; if (s.result === 'fled') c.fled++; c.hits += ty.hits; c.misses += ty.misses; c.evades += ty.evades; c.kills += ty.kills; c.dmgDealt += ty.dmgDealt; c.dmgTaken += ty.dmgTaken; c.turns += Math.round(s.time || 0);
  c.moveDist += ty.moveDist || 0; c.idleT += ty.idleT || 0; c.moveT += ty.moveT || 0;
  const movePct = (ty.moveT + ty.idleT) > 0 ? Math.round(ty.moveT / (ty.moveT + ty.idleT) * 100) : 0;
  tel('combat', { result: s.result, secs: Math.round(s.time || 0), level: game.getRun().level, movePct, moveDist: Math.round(ty.moveDist || 0), tally: ty }); }
function afterTerminal() { const p = game.getRun().phase; if (!countedTerminal && (p === 'dead' || p === 'victory')) { countedTerminal = true; const m = meta(); if (p === 'dead') m.deaths++; if (p === 'victory') { m.wins++; const ni = DIFFS.indexOf(game.getRun().difficulty) + 1; if (DIFFS[ni] && !m.unlocked.includes(DIFFS[ni])) m.unlocked.push(DIFFS[ni]); } saveMeta(m);
    // Persist the stash: on victory you keep the final quest's unbanked spoils too; on death only what was already banked survives.
    try { if (p === 'victory') localStorage.setItem(STASH_KEY, JSON.stringify(game.getStash().concat(game.getRun().bag).slice(-40))); else saveStash(); } catch {}
    const run = game.getRun(); const secs = Math.round((lastArena && lastArena.time) || 0);
    const area = (lastArena && lastArena.area) ? lastArena.area.idx + 1 : (p === 'victory' ? 8 : 1); const areaName = (lastArena && lastArena.area) ? lastArena.area.name : (p === 'victory' ? 'Catacombs' : '?');
    const bc = telClass(classId); bc.maxLevel = Math.max(bc.maxLevel, run.level); bc.deepestStep = Math.max(bc.deepestStep, secs); bc.bestArea = Math.max(bc.bestArea || 0, area);
    if (p === 'dead') { TEL.deaths++; bc.deaths++; TEL.deathLog.push({ class: classId, level: run.level, secs, area, areaName, diff: run.difficulty }); if (TEL.deathLog.length > 100) TEL.deathLog = TEL.deathLog.slice(-100); }
    else { TEL.wins++; bc.wins++; }
    const mt = lastArena && lastArena.tally; const movePct = mt && (mt.moveT + mt.idleT) > 0 ? Math.round(mt.moveT / (mt.moveT + mt.idleT) * 100) : 0;
    tel('run_end', { result: p, class: classId, level: run.level, secs, area, difficulty: run.difficulty, movePct }); } }


// ---------- dead / victory ----------
function renderDead(r) { const m = meta(); const secs = Math.round((lastArena && lastArena.time) || 0); const mm = Math.floor(secs / 60), ss = String(secs % 60).padStart(2, '0');
  ov.className = 'overlay'; ov.innerHTML = `<h2 class="dead">YOU HAVE DIED</h2><div class="deck-note">You fell at level ${r.level} after ${mm}:${ss}, on ${r.difficulty}.</div><div class="deck-note" style="color:#6f6357">${m.wins} cleared · ${m.deaths} lost</div><button class="act" id="again">NEW DESCENT</button>`; board.innerHTML = ''; logEl.innerHTML = ''; document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun('Normal', classId); }); }
function renderVictory(r) { const cur = DIFFS.indexOf(r.difficulty); const next = DIFFS[cur + 1]; ov.className = 'overlay'; ov.innerHTML = `<h2 class="win">ANDARIEL FALLS — ACT 1 CLEARED</h2><div class="deck-note">You walked all of Act 1 on <b>${r.difficulty}</b> and slew the Maiden of Anguish at level ${r.level}.</div>${next ? `<div class="deck-note" style="color:var(--gold)">${next} unlocked.</div>` : '<div class="deck-note" style="color:var(--gold)">You have conquered Hell.</div>'}<div style="display:flex;gap:12px;margin-top:6px">${next ? `<button class="act" id="next">ENTER ${next.toUpperCase()}</button>` : ''}<button class="act ghost" id="again">NEW RUN</button></div>`; board.innerHTML = ''; logEl.innerHTML = ''; const nb = document.getElementById('next'); if (nb) nb.addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(next, classId); }); document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun('Normal', classId); }); }

// ---------- overlays ----------
function renderOverlay() { if (invOpen) return renderInventory(); if (treeOpen) return renderTree(); const p = game.getRun().phase; if (p === 'dead') return renderDead(game.getRun()); if (p === 'victory') return renderVictory(game.getRun()); ov.className = 'overlay hidden'; ov.innerHTML = ''; }

const TAB_LABEL = { fire: '🔥 Fire', cold: '❄ Cold', light: '⚡ Lightning' };
function skRow(r, sk) { const req = sk.pre && sk.pre.length ? ` · needs ${sk.pre.map((p) => (r.tree.find((t) => t.id === p) || {}).name || p).join(', ')}` : '';
  const tag = sk.learned ? '' : sk.canInvest ? ' <span style="color:var(--gold)">— can learn</span>' : ` <span style="color:#6f6357">— locked (${sk.gateReason || 'Lv ' + sk.req})</span>`;
  return `<div class="sk-row ${sk.canInvest ? '' : sk.learned ? '' : 'locked'}"><div class="sk-info"><div class="sn">${sk.name}${sk.passive ? ' <span class="sk-pass">passive</span>' : ''} <span style="color:var(--gold)">Lv ${sk.level}</span> <span style="color:#5f6b7a;font-size:10px">Lv${sk.req}${req}</span>${tag}</div><div class="se">${sk.eff.text}</div></div>
    <div class="sk-btns"><button data-inv="${sk.id}" ${sk.canInvest ? '' : 'disabled'}>${sk.learned ? 'Improve ▲' : 'Learn +'}</button></div></div>`; }
function renderTree() {
  const r = game.getRun();
  let body;
  if (r.tabs) { // Sorceress — three elemental trees, side by side
    body = `<div class="sk-tabs">${r.tabs.map((tb) => `<div class="sk-tab"><div class="sk-tab-h">${TAB_LABEL[tb] || tb}</div>${r.tree.filter((sk) => sk.tab === tb).map((sk) => skRow(r, sk)).join('')}</div>`).join('')}</div>`;
  } else { body = r.tree.map((sk) => skRow(r, sk)).join(''); }
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">⚔ Skill Tree — ${r.skillPoints} pts</div><button class="inv-close" id="cx">✕</button></div>
    <div class="sk-sub">Skills unlock by <b>level</b> and <b>prerequisite</b> — build toward the big ones. Each point needs a higher level than the last.${r.tabs ? ' <b>Masteries</b> boost all spell damage; <b>Warmth</b> speeds Mana regen.' : ''}</div>${body}</div>`;
  document.getElementById('cx').addEventListener('click', () => { treeOpen = false; render(); if (arenaActive) resumeArena(); });
  ov.querySelectorAll('[data-inv]').forEach((b) => b.addEventListener('click', () => { game.investSkill(b.dataset.inv); expose(); renderTree(); }));
}

let socketTargetId = null; // when set, the bag shows a rune-picker for this item
function cmpTag(it) { if (!it || it.isRune || it.slot === 'weapon') return ''; const c = game.compareItem(it); if (!c) return '';
  if (!c.wearable) return ' <span class="cmp locked">✗ req</span>'; if (c.isUpgrade) return ` <span class="cmp up">▲ +${c.delta}</span>`; return ' <span class="cmp dn">▽</span>'; }
// A gear item's equip requirements, spelled out: each Str/Dex/Lv gate shown green if
// you meet it, red (with how far short you are) if you don't — so it's never a mystery
// why a piece won't equip.
function reqReadout(it) {
  if (!it || it.isRune || !it.req) return '';
  const r = game.getRun(); const a = r.attr || {};
  const gates = [];
  const add = (label, need, have) => { if (!need) return; const ok = (have || 0) >= need;
    gates.push(`<span class="rq ${ok ? 'ok' : 'no'}">${label} ${need}${ok ? '' : ` <em>(${have || 0})</em>`}</span>`); };
  add('Str', it.req.str, a.str); add('Dex', it.req.dex, a.dex); add('Lv', it.req.level, r.level);
  if (!gates.length) return '';
  return `<div class="bi-req"><span class="rq-lead">Requires</span>${gates.join('')}</div>`;
}
// Aggregated skill-BEHAVIOR bonuses from gear (how your spells are reshaped), shown
// as their own chips in the character readout so the build's payoff is legible.
function skillModChips(m) {
  if (!m) return '';
  const c = [];
  if (m.spellPct) c.push(`<span><span class="k">Spell Dmg</span> <b style="color:#ffb86b">+${m.spellPct}%</b></span>`);
  if (m.aoePct) c.push(`<span><span class="k">Blast</span> <b style="color:#ff9d5c">+${m.aoePct}%</b></span>`);
  if (m.jumps) c.push(`<span><span class="k">Chain</span> <b style="color:#c9a6ff">+${m.jumps}</b></span>`);
  if (m.bolts) c.push(`<span><span class="k">Bolts</span> <b style="color:#c9a6ff">+${m.bolts}</b></span>`);
  if (m.pierce) c.push(`<span><span class="k">Pierce</span> <b style="color:#8fd0ff">+${m.pierce}</b></span>`);
  return c.join('');
}
function itemCard(it, where) {
  const isRune = it.isRune; const inField = game.getRun().phase === 'arena';
  const gate = (!isRune && game.canEquip) ? game.canEquip(it) : { ok: true };
  const wearable = gate.ok;
  const sockInfo = it.sockets ? ` <span class="bi-sock">◈${(it.socketRunes || []).length}/${it.sockets}</span>` : '';
  let btns = '';
  if (socketTargetId && isRune) { btns = `<button class="act ghost small" data-put="${it.id}">◈ SOCKET THIS</button>`; }
  else if (where === 'bag') {
    if (!isRune) btns += `<button class="act ghost small" data-equip="${it.id}" ${inField || !wearable ? 'disabled' : ''}${!wearable ? ` title="${gate.reason}"` : ''}>EQUIP</button>`;
    if (it.sockets && (it.socketRunes || []).length < it.sockets) btns += `<button class="act ghost small" data-socket="${it.id}" ${inField ? 'disabled' : ''}>◈ SOCKET</button>`;
    if (it.rarity === 'magic' || it.rarity === 'rare') btns += `<button class="act ghost small" data-reroll="${it.id}" ${inField || r0().shards < 6 ? 'disabled' : ''}>⟳ ${'6◈'}</button>`;
    btns += `<button class="act ghost small" data-bank="${it.id}" ${inField ? 'disabled' : ''}>BANK</button>`;
    btns += `<button class="act ghost small" data-salvage="${it.id}" ${inField ? 'disabled' : ''}>SALVAGE</button>`;
  } else if (where === 'stash') {
    if (!isRune) btns += `<button class="act ghost small" data-eqstash="${it.id}" ${inField || !wearable ? 'disabled' : ''}${!wearable ? ` title="${gate.reason}"` : ''}>EQUIP</button>`;
  }
  const lock = (!isRune && !wearable) ? `<div class="bi-lock">🔒 Can't equip yet — ${gate.reason}</div>` : '';
  return `<div class="bag-item${isRune ? ' rune' : ''}" style="${it.color ? `border-color:${it.color}` : ''}"><div class="bi-name" style="${it.color ? `color:${it.color}` : ''}">${it.name}${sockInfo}${where === 'bag' ? cmpTag(it) : ''}</div><div class="bi-slot">${isRune ? 'Rune' : (SLOT_LABEL[it.slot] || it.slot)}${it.grants && it.grants.skill ? ' · grants a skill' : ''}${it.itemTier && it.itemTier !== 'Normal' ? ' · ' + it.itemTier : ''}</div><div class="bi-text">${it.text || ''}</div>${reqReadout(it)}${lock}<div class="bi-btns">${btns}</div></div>`;
}
function r0() { return game.getRun(); }
function renderInventory() {
  const r = game.getRun(); const st = r.stats;
  const cells = SLOTS.map((slot) => { const it = r.equipment[slot]; const inField = r.phase === 'arena';
    return `<div class="slot ${it ? 'filled' : ''}" ${it && slot !== 'weapon' && !inField ? `data-slot="${slot}"` : ''}><div class="slot-k">${SLOT_LABEL[slot]}</div><div class="slot-v" style="${it && it.color ? `color:${it.color}` : ''}">${it ? it.name : '<span class="empty">— empty —</span>'}</div>${it ? `<div class="slot-t">${it.text || ''}</div>${slot !== 'weapon' && !inField ? '<div class="slot-x">tap to unequip</div>' : ''}` : ''}</div>`; }).join('');
  const bag = r.bag.length ? r.bag.map((it) => itemCard(it, 'bag')).join('') : '<div class="bag-empty">Your bag is empty.</div>';
  const stash = r.stash.length ? r.stash.map((it) => itemCard(it, 'stash')).join('') : '<div class="bag-empty">Stash empty — bank finds in town to keep them.</div>';
  const sockNote = socketTargetId ? '<div class="sock-note">Pick a rune to socket (◈), or ✕ to cancel.</div>' : '';
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">🎒 Stash & Gear</div><button class="inv-close" id="cx">✕</button></div>
    <div class="inv-stats"><span><span class="k">Life</span> <b class="life">${Math.round(r.life)}/${st.maxLife}</b></span><span><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></span><span><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></span>${st.fcr ? `<span><span class="k">FCR</span> <b style="color:#9ab6ff">+${st.fcr}%</b></span>` : ''}${st.penetration ? `<span><span class="k">Pierce</span> <b style="color:#c58">-${Math.round(st.penetration * 100)}%</b></span>` : ''}<span><span class="k">Gold</span> <b style="color:var(--gold)">${r.gold}</b></span>${skillModChips(st.skillMods)}<span><span class="k">Shards</span> <b style="color:#d98b3a">${r.shards}</b></span></div>
    ${sockNote}
    <div class="inv-cols"><div class="paperdoll">${cells}</div>
      <div class="bag"><div class="bag-head">Bag (${r.bag.length}/${r.bagCap})${r.bag.length && r.phase !== 'arena' ? ' <button class="act ghost xs" id="bankAll">BANK ALL</button>' : ''}</div><div class="bag-list">${bag}</div>
        <div class="bag-head" style="margin-top:10px">Stash (${r.stash.length}/${r.stashCap})</div><div class="bag-list">${stash}</div></div></div></div>`;
  const close = () => { invOpen = false; socketTargetId = null; render(); if (arenaActive) resumeArena(); };
  document.getElementById('cx').addEventListener('click', close);
  const refresh = () => { expose(); saveStash(); renderInventory(); };
  ov.querySelectorAll('.slot[data-slot]').forEach((el) => el.addEventListener('click', () => { game.unequip(el.dataset.slot); refresh(); }));
  ov.querySelectorAll('[data-equip]').forEach((el) => el.addEventListener('click', () => { game.equipFromBag(el.dataset.equip); refresh(); }));
  ov.querySelectorAll('[data-eqstash]').forEach((el) => el.addEventListener('click', () => { game.equipFromStash(el.dataset.eqstash); refresh(); }));
  ov.querySelectorAll('[data-bank]').forEach((el) => el.addEventListener('click', () => { game.bank(el.dataset.bank); refresh(); }));
  ov.querySelectorAll('[data-salvage]').forEach((el) => el.addEventListener('click', () => { game.salvage(el.dataset.salvage); refresh(); }));
  ov.querySelectorAll('[data-reroll]').forEach((el) => el.addEventListener('click', () => { game.reroll(el.dataset.reroll); refresh(); }));
  ov.querySelectorAll('[data-socket]').forEach((el) => el.addEventListener('click', () => { socketTargetId = el.dataset.socket; renderInventory(); }));
  ov.querySelectorAll('[data-put]').forEach((el) => el.addEventListener('click', () => { game.socketRune(socketTargetId, el.dataset.put); socketTargetId = null; refresh(); }));
  const ba = document.getElementById('bankAll'); if (ba) ba.addEventListener('click', () => { game.bankAll(); refresh(); });
}

newRun('Normal', 'barbarian');
