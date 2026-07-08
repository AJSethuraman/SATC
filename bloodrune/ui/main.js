// UI layer for the full run. Reads engine state and renders it; owns no rules.
// Phases: prep -> map (pick a direction) -> combat (+flee) -> reward/levelup/
// camp -> ... -> victory | dead. Meta (difficulty ladder + tallies) persists in
// localStorage. The ONLY place the DOM is touched.

import { createGame } from '../engine/game.js';
import { SLOTS, SLOT_LABEL } from '../engine/content.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const overlay = document.getElementById('overlay');

const DIFFS = ['Normal', 'Nightmare', 'Hell'];
let game, combat, invOpen = false, focus = null, difficulty = 'Normal';
let countedTerminal = false;
window.__bloodrune = {};

// ---- meta (localStorage) ----
function loadMeta() {
  try { return JSON.parse(localStorage.getItem('bloodrune.meta')) || {}; } catch { return {}; }
}
function saveMeta(m) { try { localStorage.setItem('bloodrune.meta', JSON.stringify(m)); } catch {} }
function meta() { const m = loadMeta(); return { unlocked: m.unlocked || ['Normal'], wins: m.wins || 0, deaths: m.deaths || 0 }; }

function newRun(diff) {
  difficulty = diff || difficulty || 'Normal';
  const seed = 'run-' + (window.__seed || 'ashes') + '-' + difficulty;
  game = createGame(seed, { difficulty });
  combat = null; invOpen = false; focus = null; countedTerminal = false;
  render();
}

function expose() {
  window.__bloodrune.run = game.getRun();
  window.__bloodrune.state = combat ? combat.getState() : null;
  window.__bloodrune.phase = game.getRun().phase;
}

function pct(a, b) { return b > 0 ? Math.max(0, Math.min(100, (a / b) * 100)) : 0; }
function firstLiving(lane) { const m = lane.find((x) => x.hp > 0); return m ? m.index : null; }

function render() {
  const run0 = game.getRun();
  if (run0.phase === 'combat') combat = game.getCombat(); // sync the active fight
  expose();
  const run = game.getRun();
  const p = run.phase;
  if (p === 'combat') renderCombat();
  else if (p === 'map') renderMap(run);
  else if (p === 'levelup') { renderResting(run); renderLevelup(run); return; }
  else if (p === 'reward' || p === 'camp' || p === 'treasure') renderReward(run);
  else if (p === 'dead') renderDead(run);
  else if (p === 'victory') renderVictory(run);
  else renderPrep(run);
  renderOverlay();
}

// ---------- prep ----------
function renderPrep(run) {
  const m = meta();
  const st = run.stats;
  board.innerHTML = `
    <div class="prep">
      <div class="prep-title">THE BLEEDING DARK</div>
      <div class="prep-sub">Descend the act. Commit to a direction — there is no turning back. Fall, and the dark keeps you.</div>
      ${charCard(run)}
      <div class="meta-row">Difficulty: ${DIFFS.map((d) => `<button class="pill ${d === difficulty ? 'on' : ''} ${m.unlocked.includes(d) ? '' : 'locked'}" data-diff="${d}" ${m.unlocked.includes(d) ? '' : 'disabled'}>${d}</button>`).join('')}
        <span class="tally">wins ${m.wins} · deaths ${m.deaths}</span></div>
      <div class="prep-actions">
        <button class="act ghost" id="openInv">🎒 INVENTORY (${run.bag.length})</button>
        <button class="act" id="descend">DESCEND</button>
      </div>
    </div>`;
  logEl.innerHTML = '';
  board.querySelectorAll('.pill[data-diff]').forEach((b) => b.addEventListener('click', () => { if (!b.disabled) { difficulty = b.dataset.diff; newRun(difficulty); } }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  document.getElementById('descend').addEventListener('click', () => { game.beginDescent(); render(); });
}

function charCard(run) {
  const st = run.stats;
  return `<div class="char">
    <div class="char-glyph">${run.glyph}</div>
    <div class="char-stats">
      <div><span class="k">Class</span> <b>${run.className}</b></div>
      <div><span class="k">Life</span> <b class="life">${run.life}/${st.maxLife}</b></div>
      <div><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></div>
      <div><span class="k">Accuracy</span> <b class="acc">${st.accuracy}%</b></div>
      <div><span class="k">Block/turn</span> <b class="block">${st.startBlock}</b></div>
      <div><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></div>
      <div><span class="k">Level</span> <b>${run.level}</b></div>
      <div><span class="k">Deck</span> <b>${run.deck.length} cards</b></div>
    </div>
  </div>`;
}

// ---------- map ----------
function renderMap(run) {
  board.innerHTML = `
    ${runHeader(run)}
    <div class="prep-sub" style="text-align:center;margin:6px 0 2px">Choose your path — you cannot turn back.</div>
    <div class="paths">${run.choices.map((c, i) => `
      <button class="path ${c.type}" data-i="${i}">
        <div class="path-glyph">${c.glyph}</div>
        <div class="path-name">${c.name}</div>
        <div class="path-desc">${c.desc}</div>
      </button>`).join('')}</div>
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY (${run.bag.length})</button></div>`;
  logEl.innerHTML = '';
  board.querySelectorAll('.path').forEach((b) => b.addEventListener('click', () => { game.chooseDirection(Number(b.dataset.i)); render(); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
}

function runHeader(run) {
  return `<div class="run-header">
    <span class="rh-diff">${run.difficulty}</span>
    <span class="rh-prog">Depth ${Math.min(run.mapStep + 1, run.mapLength + 1)} / ${run.mapLength + 1}</span>
    <span class="rh-life">❤ ${run.life}/${run.maxLife}</span>
    <span class="rh-xp">Lv ${run.level} · XP ${run.xp}/${run.xpToNext}</span>
  </div>`;
}

// ---------- combat ----------
function renderCombat() {
  const s = combat.getState();
  if (focus == null || (s.lane[focus] && s.lane[focus].hp <= 0)) focus = firstLiving(s.lane);
  const h = s.hero;
  board.innerHTML = `
    ${heroBar(h, s.turn)}
    <div class="lane">${s.lane.map(monsterCard).join('')}</div>
    <div class="hand">${s.hand.map((c, i) => cardBtn(c, i, h)).join('')}</div>
    <div class="controls">
      <div class="piles">Draw ${s.drawCount} · Discard ${s.discardCount}</div>
      <div style="display:flex;gap:10px">
        <button class="act ghost small" id="flee" title="Every enemy gets a parting swing; you gain nothing">FLEE</button>
        <button class="act" id="endTurn">END TURN</button>
      </div>
    </div>`;
  logEl.innerHTML = s.log.slice(-7).map((l) => `<div>${l}</div>`).join('');
  logEl.scrollTop = logEl.scrollHeight;

  s.lane.forEach((m) => { if (m.hp > 0) { const n = document.querySelector(`.monster[data-i="${m.index}"]`); if (n) n.addEventListener('click', () => { focus = m.index; render(); }); } });
  document.querySelectorAll('.card').forEach((btn) => btn.addEventListener('click', () => {
    const i = Number(btn.dataset.i); const c = s.hand[i];
    combat.playCard(i, c.target === 'single' ? focus : undefined); afterCombat();
  }));
  document.getElementById('endTurn').addEventListener('click', () => { combat.endTurn(); afterCombat(); });
  document.getElementById('flee').addEventListener('click', () => { game.flee(); combat = game.getCombat(); afterTerminalCheck(); render(); });
}

function heroBar(h, turn) {
  const evade = h.evasion ? `<div class="stat"><span class="k">Evade</span><span class="v evade">${h.evasion}%</span></div>` : '';
  const skills = h.plusSkills ? `<div class="stat"><span class="k">+Sk</span><span class="v skills">${h.plusSkills}</span></div>` : '';
  return `<div class="hero-bar">
    <div class="hero-name">${h.glyph} ${h.name}</div>
    <div class="lifebar"><i style="width:${pct(h.life, h.maxLife)}%"></i></div>
    <div class="stat"><span class="k">Life</span><span class="v life">${h.life}/${h.maxLife}</span></div>
    <div class="stat"><span class="k">Mana</span><span class="v mana">${h.mana}/${h.maxMana}</span></div>
    <div class="stat"><span class="k">Block</span><span class="v block">${h.block}</span></div>
    <div class="stat"><span class="k">Acc</span><span class="v acc">${h.accuracy}%</span></div>
    ${evade}${skills}
    <div class="stat"><span class="k">Turn</span><span class="v">${turn}</span></div>
  </div>`;
}

function monsterCard(m) {
  const dead = m.hp <= 0;
  const focused = !dead && m.index === focus;
  let intent = '<div class="intent none">—</div>';
  if (!dead && m.intent) {
    if (m.intent.type === 'mend') intent = `<div class="intent heal">✚ ${m.intent.value}</div>`;
    else intent = `<div class="intent">⚔️ ${m.intent.value}${m.intent.times > 1 ? `×${m.intent.times}` : ''}</div>`;
  }
  const eliteTag = m.elite ? `<div class="elite-tag">ELITE ${m.affixes.map((a) => a).join(' · ')}</div>` : '';
  return `<div class="monster ${dead ? 'dead' : ''} ${focused ? 'focused' : ''} ${m.elite ? 'elite' : ''}" data-i="${m.index}">
    ${focused ? '<div class="tgt">🎯 target</div>' : ''}
    ${eliteTag}
    <div class="glyph">${m.glyph}</div>
    <div class="mname">${m.name}</div>
    <div class="mhp"><i style="width:${pct(m.hp, m.maxHp)}%"></i></div>
    <div class="hpnum">${m.hp}/${m.maxHp}</div>
    ${intent}
  </div>`;
}

function cardBtn(c, i, h) {
  const affordable = c.cost <= h.mana;
  const tag = c.target === 'aoe' ? 'ALL' : c.target === 'single' ? '→ target' : '';
  const hit = c.type === 'attack' ? ` · ~${Math.max(5, Math.min(100, h.accuracy + (c.acc || 0)))}% hit` : '';
  return `<button class="card ${c.type}" data-i="${i}" ${affordable ? '' : 'disabled'}>
    <div class="cname"><span>${c.name}</span><span class="cost">${c.cost}⬡</span></div>
    <div class="ctype">${c.type}${tag ? ` · ${tag}` : ''}${hit}</div>
    <div class="ctext">${c.text}</div>
  </button>`;
}

function afterCombat() {
  const s = combat.getState();
  if (s.over) { game.resolveCombat(); afterTerminalCheck(); }
  render();
}
function afterTerminalCheck() {
  const p = game.getRun().phase;
  if (!countedTerminal && (p === 'dead' || p === 'victory')) {
    countedTerminal = true;
    const m = meta();
    if (p === 'dead') m.deaths += 1;
    if (p === 'victory') {
      m.wins += 1;
      const cur = DIFFS.indexOf(game.getRun().difficulty);
      const next = DIFFS[cur + 1];
      if (next && !m.unlocked.includes(next)) m.unlocked.push(next);
    }
    saveMeta(m);
  }
}

// ---------- reward / camp / treasure ----------
function renderReward(run) {
  const kind = run.phase === 'camp' ? 'camp' : run.lastResult;
  let title, body;
  if (run.phase === 'camp') { title = '🔥 BLOODFIRE CAMP'; body = 'You bind your wounds by the fire and steel yourself.'; }
  else if (kind === 'fled') { title = 'YOU BREAK AWAY'; body = 'You escape with your life — and nothing else.'; }
  else if (run.node && run.node.type === 'treasure') { title = '📦 A CACHE'; body = 'Spoils, unguarded.'; }
  else { title = 'THE PACK BREAKS'; body = 'Loot falls among the corpses.'; }

  const loot = run.pendingLoot.length
    ? `<div class="loot-list">${run.pendingLoot.map(lootChip).join('')}</div>`
    : '<div class="deck-note">No spoils this time.</div>';

  board.innerHTML = `
    <div class="prep">
      ${runHeader(run)}
      <div class="prep-title" style="font-size:28px">${title}</div>
      <div class="prep-sub">${body}</div>
      ${loot}
      <div class="prep-actions">
        <button class="act ghost" id="openInv">🎒 INVENTORY (${run.bag.length})</button>
        <button class="act" id="cont">PRESS ON</button>
      </div>
    </div>`;
  logEl.innerHTML = '';
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  document.getElementById('cont').addEventListener('click', () => { game.continueFromReward(); render(); });
}

function lootChip(it) {
  return `<div class="loot-chip" style="border-color:${it.color || '#3a2a22'}">
    <div class="lc-name" style="color:${it.color || 'var(--gold)'}">${it.name}</div>
    <div class="lc-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants ? ' · grants a card' : ''}</div>
    <div class="lc-text">${it.text}</div>
  </div>`;
}

// ---------- level up ----------
function renderResting(run) {
  board.innerHTML = `<div class="prep">${runHeader(run)}<div class="prep-title" style="font-size:26px">LEVEL ${run.level}</div>
    <div class="prep-sub">Power stirs. Choose how you grow.</div></div>`;
  logEl.innerHTML = '';
}
function renderLevelup(run) {
  overlay.className = 'overlay';
  overlay.innerHTML = `<h2 class="win" style="font-size:30px">CHOOSE A BOON</h2>
    <div class="lvl-opts">${run.levelupOptions.map((o) => `
      <button class="lvl-opt" data-id="${o.id}">
        <div class="lo-name">${o.name}</div>
        <div class="lo-text">${o.text}</div>
      </button>`).join('')}</div>`;
  overlay.querySelectorAll('.lvl-opt').forEach((b) => b.addEventListener('click', () => { game.pickLevelup(b.dataset.id); render(); }));
}

// ---------- dead / victory ----------
function renderDead(run) {
  const m = meta();
  overlay.className = 'overlay';
  overlay.innerHTML = `<h2 class="dead">YOU HAVE DIED</h2>
    <div class="deck-note">You fell at depth ${run.mapStep + 1}, level ${run.level}, on ${run.difficulty}. The dark keeps what you carried.</div>
    <div class="deck-note" style="color:#6f6357">Runs: ${m.wins} cleared · ${m.deaths} lost</div>
    <button class="act" id="again">NEW DESCENT</button>`;
  board.innerHTML = ''; logEl.innerHTML = '';
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(difficulty); });
}
function renderVictory(run) {
  const m = meta();
  const cur = DIFFS.indexOf(run.difficulty);
  const next = DIFFS[cur + 1];
  overlay.className = 'overlay';
  overlay.innerHTML = `<h2 class="win">THE SMITH FALLS</h2>
    <div class="deck-note">You cleared the act on <b>${run.difficulty}</b> at level ${run.level}.</div>
    ${next ? `<div class="deck-note" style="color:var(--gold)">${next} difficulty unlocked — deadlier foes, richer loot.</div>` : '<div class="deck-note" style="color:var(--gold)">You have conquered Hell. For now.</div>'}
    <div style="display:flex;gap:12px;margin-top:6px">
      ${next ? `<button class="act" id="next">DESCEND ${next.toUpperCase()}</button>` : ''}
      <button class="act ghost" id="again">NEW DESCENT</button>
    </div>`;
  board.innerHTML = ''; logEl.innerHTML = '';
  const nb = document.getElementById('next'); if (nb) nb.addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(next); });
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun('Normal'); });
}

// ---------- inventory overlay ----------
function renderOverlay() {
  if (invOpen) return renderInventory();
  const p = game.getRun().phase;
  if (p === 'levelup') return renderLevelup(game.getRun());
  if (p === 'dead') return renderDead(game.getRun());
  if (p === 'victory') return renderVictory(game.getRun());
  overlay.className = 'overlay hidden'; overlay.innerHTML = '';
}

function renderInventory() {
  const run = game.getRun();
  const st = run.stats;
  const slotCells = SLOTS.map((slot) => {
    const it = run.equipment[slot];
    return `<div class="slot ${it ? 'filled' : ''}" data-slot="${slot}">
      <div class="slot-k">${SLOT_LABEL[slot]}</div>
      <div class="slot-v" style="${it && it.color ? `color:${it.color}` : ''}">${it ? it.name : '<span class="empty">— empty —</span>'}</div>
      ${it ? `<div class="slot-t">${it.text || ''}</div><div class="slot-x">tap to unequip</div>` : ''}
    </div>`;
  }).join('');
  const bag = run.bag.length
    ? run.bag.map((it) => `<button class="bag-item" data-id="${it.id}" style="${it.color ? `border-color:${it.color}` : ''}">
        <div class="bi-name" style="${it.color ? `color:${it.color}` : ''}">${it.name}</div>
        <div class="bi-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants ? ' · grants a card' : ''}</div>
        <div class="bi-text">${it.text || ''}</div>
      </button>`).join('')
    : '<div class="bag-empty">Your bag is empty.</div>';
  overlay.className = 'overlay inv';
  overlay.innerHTML = `<div class="inv-panel">
    <div class="inv-head"><div class="inv-title">🎒 Inventory</div><button class="inv-close" id="closeInv">✕</button></div>
    <div class="inv-stats">
      <span><span class="k">Life</span> <b class="life">${run.life}/${st.maxLife}</b></span>
      <span><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></span>
      <span><span class="k">Accuracy</span> <b class="acc">${st.accuracy}%</b></span>
      <span><span class="k">Block/turn</span> <b class="block">${st.startBlock}</b></span>
      <span><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></span>
      <span><span class="k">Deck</span> <b>${run.deck.length}</b></span>
    </div>
    <div class="inv-cols">
      <div class="paperdoll">${slotCells}</div>
      <div class="bag"><div class="bag-head">Bag (${run.bag.length})</div><div class="bag-list">${bag}</div></div>
    </div>
  </div>`;
  document.getElementById('closeInv').addEventListener('click', () => { invOpen = false; render(); });
  overlay.querySelectorAll('.slot.filled').forEach((el) => el.addEventListener('click', () => { game.unequip(el.dataset.slot); expose(); renderInventory(); }));
  overlay.querySelectorAll('.bag-item').forEach((el) => el.addEventListener('click', () => { game.equipFromBag(el.dataset.id); expose(); renderInventory(); }));
}

newRun('Normal');
