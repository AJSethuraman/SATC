// UI layer (M1.5). Reads engine state and renders it; owns no rules. The ONLY
// place the DOM is touched. Adds: target focus (tap a monster), an inventory
// paper-doll (open between fights to equip found gear), and the Mana pool.

import { createGame } from '../engine/game.js';
import { SLOTS, SLOT_LABEL } from '../engine/content.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const overlay = document.getElementById('overlay');

let game, combat;
let screen = 'prep';   // 'prep' | 'combat' | 'won' | 'dead'
let invOpen = false;
let focus = null;      // focused monster lane index for single-target cards
window.__bloodrune = {};

function newRun() {
  const seed = 'run-' + (window.__seed || 'ashes');
  game = createGame(seed);
  combat = null;
  screen = 'prep';
  invOpen = false;
  focus = null;
  expose();
  render();
}

function enterFray() {
  combat = game.startFight();
  screen = 'combat';
  focus = null;
  expose();
  render();
}

function expose() {
  window.__bloodrune.run = game.getRun();
  window.__bloodrune.state = combat ? combat.getState() : null;
  window.__bloodrune.screen = screen;
}

function pct(a, b) { return b > 0 ? Math.max(0, Math.min(100, (a / b) * 100)) : 0; }
function firstLiving(lane) { const m = lane.find((x) => x.hp > 0); return m ? m.index : null; }

// ---------------------------------------------------------------- rendering
function render() {
  expose();
  if (screen === 'combat') renderCombat();
  else renderCharacterScreen();
  renderOverlay();
}

function renderCombat() {
  const s = combat.getState();
  if (focus == null || (s.lane[focus] && s.lane[focus].hp <= 0)) focus = firstLiving(s.lane);
  const h = s.hero;

  board.innerHTML = `
    ${heroBar(h, s.turn)}
    <div class="lane">${s.lane.map((m) => monsterCard(m)).join('')}</div>
    <div class="hand" id="hand">${s.hand.map((c, i) => cardBtn(c, i, h)).join('')}</div>
    <div class="controls">
      <div class="piles">Draw ${s.drawCount} · Discard ${s.discardCount}</div>
      <button class="act" id="endTurn">END TURN</button>
    </div>`;

  logEl.innerHTML = s.log.slice(-7).map((l) => `<div>${l}</div>`).join('');
  logEl.scrollTop = logEl.scrollHeight;

  s.lane.forEach((m) => {
    if (m.hp <= 0) return;
    const node = document.querySelector(`.monster[data-i="${m.index}"]`);
    if (node) node.addEventListener('click', () => { focus = m.index; render(); });
  });
  document.querySelectorAll('.card').forEach((btn) => {
    btn.addEventListener('click', () => {
      const i = Number(btn.dataset.i);
      const c = s.hand[i];
      combat.playCard(i, c.target === 'single' ? focus : undefined);
      afterAction();
    });
  });
  document.getElementById('endTurn').addEventListener('click', () => { combat.endTurn(); afterAction(); });
}

function heroBar(h, turn) {
  const skills = h.plusSkills ? `<div class="stat"><span class="k">+Skills</span><span class="v skills">${h.plusSkills}</span></div>` : '';
  const evade = h.evasion ? `<div class="stat"><span class="k">Evade</span><span class="v evade">${h.evasion}%</span></div>` : '';
  return `
    <div class="hero-bar">
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
    intent = m.intent.type === 'mend'
      ? `<div class="intent heal">✚ ${m.intent.value}</div>`
      : `<div class="intent">⚔️ ${m.intent.value}</div>`;
  }
  return `
    <div class="monster ${dead ? 'dead' : ''} ${focused ? 'focused' : ''}" data-i="${m.index}">
      ${focused ? '<div class="tgt">🎯 target</div>' : ''}
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
  const hit = c.type === 'attack'
    ? ` · ~${Math.max(5, Math.min(100, h.accuracy + (c.acc || 0)))}% hit` : '';
  return `
    <button class="card ${c.type}" data-i="${i}" ${affordable ? '' : 'disabled'}>
      <div class="cname"><span>${c.name}</span><span class="cost">${c.cost}⬡</span></div>
      <div class="ctype">${c.type}${tag ? ` · ${tag}` : ''}${hit}</div>
      <div class="ctext">${c.text}</div>
    </button>`;
}

// The prep / won / dead "character" screen (also the home for the inventory).
function renderCharacterScreen() {
  const run = game.getRun();
  const st = run.stats;
  let title, sub, primary;
  if (screen === 'prep') {
    title = 'THE BLEEDING DARK'; sub = 'Gear up, then descend. Open your inventory to equip what you’ve found.';
    primary = '<button class="act" id="enter">ENTER THE FRAY</button>';
  } else if (screen === 'won') {
    title = 'PACK BROKEN'; sub = 'Loot fell into your bag. Equip it, then press on.';
    primary = '<button class="act" id="enter">DESCEND AGAIN</button>';
  } else { title = ''; sub = ''; primary = ''; }

  board.innerHTML = `
    <div class="prep">
      <div class="prep-title">${title}</div>
      <div class="prep-sub">${sub}</div>
      <div class="char">
        <div class="char-glyph">${run.className === 'Barbarian' ? '🪓' : '❔'}</div>
        <div class="char-stats">
          <div><span class="k">Class</span> <b>${run.className}</b></div>
          <div><span class="k">Life</span> <b class="life">${st.maxLife}</b></div>
          <div><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></div>
          <div><span class="k">Block/turn</span> <b class="block">${st.startBlock}</b></div>
          <div><span class="k">Accuracy</span> <b class="acc">${st.accuracy}%</b></div>
          <div><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></div>
          <div><span class="k">Deck</span> <b>${run.deck.length} cards</b></div>
        </div>
      </div>
      <div class="prep-actions">
        <button class="act ghost" id="openInv">🎒 INVENTORY (${run.bag.length})</button>
        ${primary}
      </div>
    </div>`;
  logEl.innerHTML = '';

  const enterBtn = document.getElementById('enter');
  if (enterBtn) enterBtn.addEventListener('click', enterFray);
  document.getElementById('openInv').addEventListener('click', () => { invOpen = true; renderOverlay(); });
}

// ------------------------------------------------------------- the overlay
function renderOverlay() {
  if (invOpen) return renderInventory();
  if (screen === 'dead') return showDead();
  overlay.className = 'overlay hidden';
  overlay.innerHTML = '';
}

function renderInventory() {
  const run = game.getRun();
  const st = run.stats;
  const slotCells = SLOTS.map((slot) => {
    const it = run.equipment[slot];
    return `
      <div class="slot ${it ? 'filled' : ''}" data-slot="${slot}">
        <div class="slot-k">${SLOT_LABEL[slot]}</div>
        <div class="slot-v">${it ? it.name : '<span class="empty">— empty —</span>'}</div>
        ${it ? `<div class="slot-t">${it.text}</div><div class="slot-x">tap to unequip</div>` : ''}
      </div>`;
  }).join('');

  const bag = run.bag.length
    ? run.bag.map((it) => `
        <button class="bag-item" data-id="${it.id}">
          <div class="bi-name">${it.name}</div>
          <div class="bi-slot">${SLOT_LABEL[it.slot] || it.slot}</div>
          <div class="bi-text">${it.text}</div>
        </button>`).join('')
    : '<div class="bag-empty">Your bag is empty. Win fights to find gear.</div>';

  overlay.className = 'overlay inv';
  overlay.innerHTML = `
    <div class="inv-panel">
      <div class="inv-head">
        <div class="inv-title">🎒 Inventory</div>
        <button class="inv-close" id="closeInv">✕</button>
      </div>
      <div class="inv-stats">
        <span><span class="k">Life</span> <b class="life">${st.maxLife}</b></span>
        <span><span class="k">Mana</span> <b class="mana">${st.maxMana}</b></span>
        <span><span class="k">Block/turn</span> <b class="block">${st.startBlock}</b></span>
        <span><span class="k">Accuracy</span> <b class="acc">${st.accuracy}%</b></span>
        <span><span class="k">+Skills</span> <b class="skills">${st.plusSkills}</b></span>
        <span><span class="k">Deck</span> <b>${run.deck.length}</b></span>
      </div>
      <div class="inv-cols">
        <div class="paperdoll">${slotCells}</div>
        <div class="bag">
          <div class="bag-head">Bag (${run.bag.length})</div>
          <div class="bag-list">${bag}</div>
        </div>
      </div>
    </div>`;

  document.getElementById('closeInv').addEventListener('click', () => { invOpen = false; render(); });
  overlay.querySelectorAll('.slot.filled').forEach((el) => {
    el.addEventListener('click', () => { game.unequip(el.dataset.slot); renderInventory(); expose(); });
  });
  overlay.querySelectorAll('.bag-item').forEach((el) => {
    el.addEventListener('click', () => { game.equipFromBag(el.dataset.id); renderInventory(); expose(); });
  });
}

function showDead() {
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <h2 class="dead">YOU HAVE DIED</h2>
    <div class="deck-note">The dark takes another. Permadeath ends the run — what you learned persists (in later slices).</div>
    <button class="act" id="again">TRY AGAIN</button>`;
  window.__bloodrune.dead = true;
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(); });
}

function afterAction() {
  const s = combat.getState();
  window.__bloodrune.state = s;
  window.__bloodrune.run = game.getRun();
  if (s.over) {
    const phase = game.resolveCombat();
    if (phase === 'loot') { game.ackLoot(); screen = 'won'; window.__bloodrune.won = true; return render(); }
    if (phase === 'dead') { screen = 'dead'; return render(); }
  }
  render();
}

newRun();
