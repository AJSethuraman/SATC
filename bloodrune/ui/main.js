// UI for Bloodrune — the abilities/surrounded model in the full run. Reads engine
// state, renders it; owns no rules. Phases: prep(class+difficulty) -> map(blind)
// -> combat(arena) -> reward(loot + skill tree) -> ... -> victory | dead. Meta
// (difficulty ladder + tallies) persists in localStorage.

import { createGame } from '../engine/game.js';
import { SLOTS, SLOT_LABEL, CLASSES } from '../engine/content.js';

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

function newRun(diff, cls) {
  difficulty = diff || difficulty; if (cls) classId = cls;
  game = createGame('run-' + (window.__seed || 'ashes') + '-' + difficulty + '-' + classId, { classId, difficulty });
  combat = null; invOpen = false; treeOpen = false; focusUid = null; countedTerminal = false;
  render();
}
function expose() { const r = game.getRun(); window.__bloodrune.run = r; window.__bloodrune.state = combat ? combat.getState() : null; window.__bloodrune.phase = r.phase; window.__bloodrune.game = game; }
function pv(a, b) { return b > 0 ? Math.max(0, Math.min(100, a / b * 100)) : 0; }

function render() {
  const r0 = game.getRun();
  if (r0.phase === 'combat') combat = game.getCombat();
  expose();
  const r = game.getRun();
  if (r.phase === 'combat') renderCombat();
  else if (r.phase === 'map') renderMap(r);
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
        <div><span class="k">Skills</span> <b>${r.abilities.length}</b></div>
      </div></div>
    <div class="meta-row">Difficulty: ${DIFFS.map((d) => `<button class="pill ${d === difficulty ? 'on' : ''} ${m.unlocked.includes(d) ? '' : 'locked'}" data-diff="${d}" ${m.unlocked.includes(d) ? '' : 'disabled'}>${d}</button>`).join('')}<span class="tally">wins ${m.wins} · deaths ${m.deaths}</span></div>
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button><button class="act" id="descend">DESCEND</button></div>
  </div>`;
  logEl.innerHTML = '';
  board.querySelectorAll('.pill[data-class]').forEach((b) => b.addEventListener('click', () => newRun(difficulty, b.dataset.class)));
  board.querySelectorAll('.pill[data-diff]').forEach((b) => b.addEventListener('click', () => { if (!b.disabled) newRun(b.dataset.diff, classId); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  document.getElementById('descend').addEventListener('click', () => { game.beginDescent(); render(); });
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
  board.querySelectorAll('.path').forEach((b) => b.addEventListener('click', () => { game.chooseDirection(Number(b.dataset.i)); render(); }));
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  const t = document.getElementById('openTree'); if (t) t.addEventListener('click', () => { treeOpen = true; renderOverlay(); });
}
function runHeader(r) { return `<div class="run-header"><span class="rh-diff">${r.difficulty}</span><span>Depth ${Math.min(r.mapStep + 1, r.mapLength + 1)}/${r.mapLength + 1}</span><span class="rh-life">❤ ${r.life}/${r.maxLife}</span><span class="rh-xp">Lv ${r.level} · XP ${r.xp}/${r.xpToNext}</span>${r.skillPoints ? `<span style="color:var(--gold)">● ${r.skillPoints} pts</span>` : ''}</div>`; }

// ---------- combat (arena) ----------
function renderCombat() {
  const s = combat.getState(); const h = s.hero;
  const living = s.enemies.filter((e) => e.hp > 0);
  if (focusUid == null || !living.find((e) => e.uid === focusUid)) focusUid = living[0] ? living[0].uid : null;
  const pos = {};
  [0, 1].forEach((ring) => { const grp = living.filter((e) => (e.ring || 0) === ring); const R = ring === 0 ? 30 : 47;
    grp.forEach((e, i) => { const a = -Math.PI / 2 + (i / grp.length) * Math.PI * 2 + (ring === 1 ? Math.PI / (grp.length || 1) : 0); pos[e.uid] = { x: 50 + R * Math.cos(a), y: 50 + R * Math.sin(a) }; }); });
  const lines = s.enemies.filter((e) => e.hp > 0 && e.role === 'guardian' && e.guardsUid != null).map((g) => { const t = s.enemies.find((e) => e.uid === g.guardsUid && e.hp > 0); if (!t || !pos[g.uid] || !pos[t.uid]) return ''; const a = pos[g.uid], b = pos[t.uid]; return `<line x1="${a.x}%" y1="${a.y}%" x2="${b.x}%" y2="${b.y}%" stroke="#4a7bff" stroke-opacity="0.5" stroke-width="1.5" stroke-dasharray="3 3"/>`; }).join('');
  const frontRing = Math.min(...living.map((e) => e.ring || 0));
  const mobs = living.map((e) => { const p = pos[e.uid];
    const intent = e.intent ? (e.intent.type === 'support' ? '<div class="in heal">🌀 channels</div>' : e.intent.type === 'wait' ? '<div class="in wait">⏳ waiting</div>' : `<div class="in">⚔️ ${e.intent.value}${e.intent.times > 1 ? '×' + e.intent.times : ''}</div>`) : '';
    const screened = (e.ring || 0) > frontRing; // held safe behind the front rank — melee can't reach it yet
    return `<div class="mob ${e.role === 'guardian' ? 'guardian' : e.role === 'caster' ? 'caster' : ''} ${e.unique ? 'unique' : e.elite ? 'elite' : ''} ${screened ? 'screened' : ''} ${e.uid === focusUid ? 'focus' : ''}" data-uid="${e.uid}" style="left:${p.x}%;top:${p.y}%">
      ${e.unique ? '<div class="badge unique2">☠ SUPER UNIQUE</div>' : e.guarded ? `<div class="badge guarded">🛡 ×${e.guardianCount}</div>` : screened ? '<div class="badge screened">out of reach</div>' : e.elite ? `<div class="badge elite2">ELITE</div>` : ''}
      <div class="card2"><div class="g">${e.glyph}</div><div class="n">${e.name}</div><div class="hp"><i style="width:${pv(e.hp, e.maxHp)}%"></i></div>${intent}</div>
      ${e.uid === focusUid ? '<div class="focus-tag">🎯</div>' : ''}</div>`; }).join('');
  board.innerHTML = `
    <div class="bar ${h.exposed ? 'exposed' : ''}">
      <div class="stat"><span class="k">Life</span><span class="v life">${h.life}/${h.maxLife}</span></div>
      <div class="stat"><span class="k">Mana</span><span class="v mana">${h.mana}/${h.maxMana}</span><span class="regen">+${h.manaRegen}/t</span></div>
      <div class="stat"><span class="k">Block</span><span class="v block">${h.block}</span></div>
      <div class="stat"><span class="k">Acc</span><span class="v">${h.accuracy}</span></div>
      ${h.evade > 0 ? `<div class="stat"><span class="k">Eva</span><span class="v">${h.evade}</span></div>` : ''}
      <div class="stat"><span class="k">Lv</span><span class="v">${game.getRun().level}</span></div>
      ${h.exposed ? '<span class="expo">⚠ EXPOSED</span>' : ''}
      <div class="stat"><span class="k">Turn</span><span class="v">${s.turn}</span></div>
    </div>
    <div class="arena"><svg viewBox="0 0 100 100" preserveAspectRatio="none">${lines}</svg>
      <div class="hero-tok"><div class="ring"></div><div class="g">${h.glyph}</div>${h.summons.length ? `<div class="summons">${h.summons.map((x) => x.glyph).join('')}</div>` : ''}</div>${mobs}</div>
    <div class="hint">Surrounded — only the front rank can reach you each turn (the rest ⏳ wait). Ranged foes hold the back (“out of reach”); thin the front to pin them, or strike past with a ranged skill / Charge / Summons. A Shaman raises the Fallen — kill it first.</div>
    <div class="hand">${h.abilities.map(abilityHTML).join('')}</div>
    <div class="controls"><button class="act ghost small" id="flee">FLEE</button><button class="act" id="end">END TURN</button></div>`;
  logEl.innerHTML = s.log.slice(-6).map((l) => `<div>${l}</div>`).join(''); logEl.scrollTop = logEl.scrollHeight;
  board.querySelectorAll('.mob').forEach((mb) => mb.addEventListener('click', () => { focusUid = Number(mb.dataset.uid); combat.setFocus(focusUid); render(); }));
  document.querySelectorAll('.card').forEach((b) => b.addEventListener('click', () => { combat.useSkill(Number(b.dataset.i), focusUid); afterCombat(); }));
  document.getElementById('end').addEventListener('click', () => { combat.endTurn(); afterCombat(); });
  document.getElementById('flee').addEventListener('click', () => { game.flee(); combat = game.getCombat(); afterTerminal(); render(); });
}
function abilityHTML(c, i) {
  const s = combat.getState(); const h = s.hero; const affordable = c.cost <= h.mana;
  const tag = c.type === 'breakthrough' ? 'reach · EXPOSES' : c.type === 'summon' ? 'summon · each turn' : c.target === 'aoe' ? (`×${c.maxTargets || 3}` + (c.reach ? ' · reaches outer' : ' · inner')) : c.type === 'skill' ? 'skill' : (c.reach ? 'reaches outer' : 'inner ring');
  // physical attacks roll to-hit; show the chance vs the focused foe so accuracy reads
  let hit = '';
  if ((c.type === 'attack' || c.type === 'breakthrough') && c.weapon !== 'spell') {
    const f = s.enemies.find((e) => e.uid === h.focusUid && e.hp > 0);
    if (f) { const p = Math.round(Math.max(0.35, Math.min(0.95, 0.75 + (h.accuracy - (f.eva || 0)) * 0.04)) * 100); hit = ` <span class="hitc">${p}% hit</span>`; }
  } else if (c.weapon === 'spell' && (c.type === 'attack')) { hit = ' <span class="hitc">always hits</span>'; }
  return `<button class="card ${c.type === 'skill' ? 'skill' : c.type === 'summon' ? 'summon' : c.type === 'breakthrough' ? 'breakthrough' : 'attack'}" data-i="${i}" ${affordable ? '' : 'disabled'}>
    <div class="cn"><span>${c.name} <span class="lv">Lv ${c.eff.lvl}</span></span><span>${c.cost}⬡</span></div>
    <div class="ct">${tag}${hit}</div><div class="cx">${c.eff.text}</div></button>`;
}
function afterCombat() { const s = combat.getState(); if (s.over) { game.resolveCombat(); afterTerminal(); } render(); }
function afterTerminal() { const p = game.getRun().phase; if (!countedTerminal && (p === 'dead' || p === 'victory')) { countedTerminal = true; const m = meta(); if (p === 'dead') m.deaths++; if (p === 'victory') { m.wins++; const ni = DIFFS.indexOf(game.getRun().difficulty) + 1; if (DIFFS[ni] && !m.unlocked.includes(DIFFS[ni])) m.unlocked.push(DIFFS[ni]); } saveMeta(m); } }

// ---------- reward ----------
function renderReward(r) {
  let title, body;
  if (r.lastResult === 'camp') { title = '🔥 BLOODFIRE CAMP'; body = 'You bind your wounds and steel yourself.'; }
  else if (r.lastResult === 'fled') { title = 'YOU BREAK AWAY'; body = 'You escape with your life — and nothing else.'; }
  else if (r.node && r.node.type === 'treasure') { title = '📦 A CACHE'; body = 'Spoils, unguarded.'; }
  else { title = 'THE RING BREAKS'; body = 'Loot falls among the corpses.'; }
  const gained = r.gained && (r.gained.levels || r.gained.points) ? `<div class="deck-note" style="color:var(--gold)">${r.gained.levels ? `Level up! Now level ${r.level}. ` : ''}${r.gained.points ? `+${r.gained.points} skill point${r.gained.points > 1 ? 's' : ''}.` : ''}</div>` : '';
  const loot = r.pendingLoot.length ? `<div class="loot-list">${r.pendingLoot.map(lootChip).join('')}</div>` : '<div class="deck-note">No spoils.</div>';
  board.innerHTML = `<div class="prep">${runHeader(r)}<div class="prep-title" style="font-size:26px">${title}</div><div class="prep-sub">${body}</div>${gained}${loot}
    <div class="prep-actions"><button class="act ghost" id="openInv">🎒 INVENTORY</button>${r.skillPoints ? `<button class="act" id="openTree">⚔ SKILLS ● ${r.skillPoints}</button>` : ''}<button class="act" id="cont">PRESS ON</button></div></div>`;
  logEl.innerHTML = '';
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
  const t = document.getElementById('openTree'); if (t) t.addEventListener('click', () => { treeOpen = true; renderOverlay(); });
  document.getElementById('cont').addEventListener('click', () => { game.continueFromReward(); render(); });
}
function lootChip(it) { return `<div class="loot-chip" style="border-color:${it.color || 'var(--gold)'}"><div class="lc-name" style="color:${it.color || 'var(--gold)'}">${it.name}</div><div class="lc-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants && it.grants.skill ? ' · grants a skill' : ''}</div><div class="lc-text">${it.text || ''}</div></div>`; }

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
  const bag = r.bag.length ? r.bag.map((it) => `<button class="bag-item" data-id="${it.id}" style="${it.color ? `border-color:${it.color}` : ''}"><div class="bi-name" style="${it.color ? `color:${it.color}` : ''}">${it.name}</div><div class="bi-slot">${SLOT_LABEL[it.slot] || it.slot}${it.grants && it.grants.skill ? ' · grants a skill' : ''}</div><div class="bi-text">${it.text || ''}</div></button>`).join('') : '<div class="bag-empty">Your bag is empty.</div>';
  ov.className = 'overlay inv';
  ov.innerHTML = `<div class="inv-panel"><div class="inv-head"><div class="inv-title">🎒 Inventory</div><button class="inv-close" id="cx">✕</button></div>
    <div class="inv-stats"><span><span class="k">Life</span> <b class="life">${r.life}/${st.maxLife}</b></span><span><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></span><span><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></span><span><span class="k">Block/turn</span> <b class="block">${st.startBlock}</b></span></div>
    <div class="inv-cols"><div class="paperdoll">${cells}</div><div class="bag"><div class="bag-head">Bag (${r.bag.length})</div><div class="bag-list">${bag}</div></div></div></div>`;
  document.getElementById('cx').addEventListener('click', () => { invOpen = false; render(); });
  ov.querySelectorAll('.slot.filled').forEach((el) => el.addEventListener('click', () => { game.unequip(el.dataset.slot); expose(); renderInventory(); }));
  ov.querySelectorAll('.bag-item').forEach((el) => el.addEventListener('click', () => { game.equipFromBag(el.dataset.id); expose(); renderInventory(); }));
}

newRun('Normal', 'barbarian');
