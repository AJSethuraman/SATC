// UI layer for the M1 tracer bullet. Reads engine state and renders it; owns no
// rules. All game logic lives in ../engine/. This file is the ONLY place the DOM
// is touched. (localStorage / persistence arrives in a later slice.)

import { createGame } from '../engine/game.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const overlay = document.getElementById('overlay');

let game, combat;
// Expose for the headless Playwright smoke to assert against engine truth.
window.__bloodrune = {};

function newRun() {
  // A fresh seed each session; deterministic within a run for testing/sharing.
  const seed = 'run-' + (window.__seed || 'ashes');
  game = createGame(seed);
  combat = game.startFight();
  overlay.classList.add('hidden');
  render();
}

function pct(a, b) { return b > 0 ? Math.max(0, Math.min(100, (a / b) * 100)) : 0; }

function render() {
  const s = combat.getState();
  window.__bloodrune.state = s;
  window.__bloodrune.run = game.getRun();

  const h = s.hero;
  board.innerHTML = `
    <div class="hero-bar">
      <div class="hero-name">${h.glyph} ${h.name}</div>
      <div class="lifebar"><i style="width:${pct(h.life, h.maxLife)}%"></i></div>
      <div class="stat"><span class="k">Life</span><span class="v life">${h.life}/${h.maxLife}</span></div>
      <div class="stat"><span class="k">Mana</span><span class="v mana">${h.mana}/${h.maxMana}</span></div>
      <div class="stat"><span class="k">Block</span><span class="v block">${h.block}</span></div>
      <div class="stat"><span class="k">Turn</span><span class="v">${s.turn}</span></div>
    </div>

    <div class="lane">
      ${s.lane.map(renderMonster).join('')}
    </div>

    <div class="hand" id="hand">
      ${s.hand.map(renderCard).join('')}
    </div>

    <div class="controls">
      <div class="piles">Draw ${s.drawCount} · Discard ${s.discardCount}</div>
      <button class="act" id="endTurn">END TURN</button>
    </div>
  `;

  logEl.innerHTML = s.log.slice(-8).map((l) => `<div>${l}</div>`).join('');
  logEl.scrollTop = logEl.scrollHeight;

  // wire cards
  document.querySelectorAll('.card').forEach((btn) => {
    btn.addEventListener('click', () => {
      const i = Number(btn.dataset.i);
      combat.playCard(i);
      afterAction();
    });
  });
  document.getElementById('endTurn').addEventListener('click', () => {
    combat.endTurn();
    afterAction();
  });
}

function renderMonster(m) {
  const dead = m.hp <= 0;
  const intent = dead || !m.intent ? '<div class="intent none">—</div>'
    : `<div class="intent">⚔️ ${m.intent.value}</div>`;
  return `
    <div class="monster ${dead ? 'dead' : ''}">
      <div class="glyph">${m.glyph}</div>
      <div class="mname">${m.name}</div>
      <div class="mhp"><i style="width:${pct(m.hp, m.maxHp)}%"></i></div>
      <div class="hpnum">${m.hp}/${m.maxHp}</div>
      ${intent}
    </div>`;
}

function renderCard(c, i) {
  const s = combat.getState();
  const affordable = c.cost <= s.hero.mana;
  return `
    <button class="card ${c.type}" data-i="${i}" ${affordable ? '' : 'disabled'}>
      <div class="cname"><span>${c.name}</span><span class="cost">${c.cost}⬡</span></div>
      <div class="ctype">${c.type}</div>
      <div class="ctext">${c.text}</div>
    </button>`;
}

function afterAction() {
  const s = combat.getState();
  // Keep the exposed state fresh even on terminal transitions (loot/death),
  // where we return before render() — the smoke/tests read this.
  window.__bloodrune.state = s;
  window.__bloodrune.run = game.getRun();
  if (s.over) {
    const phase = game.resolveCombat();
    if (phase === 'loot') return showLoot();
    if (phase === 'dead') return showDead();
  }
  render();
}

function showLoot() {
  const run = game.getRun();
  const item = run.pendingLoot;
  const deckBefore = run.deck.length;
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <h2 class="win">VICTORY</h2>
    <div class="deck-note">The pack lies broken. Something glints in the gore.</div>
    <div class="loot-card">
      <div class="lname">${item.name}</div>
      <div class="ltext">${item.text}</div>
    </div>
    <div class="deck-note">Your deck holds <b>${deckBefore}</b> cards. Equipping this weapon rebuilds it.</div>
    <div style="display:flex; gap:12px; margin-top:6px">
      <button class="act" id="equip">EQUIP</button>
      <button class="act ghost" id="skip">LEAVE IT</button>
    </div>
  `;
  document.getElementById('equip').addEventListener('click', () => {
    const res = game.equipPendingLoot();
    window.__bloodrune.run = game.getRun();
    showWon(res.deck, deckBefore, item);
  });
  document.getElementById('skip').addEventListener('click', () => {
    game.skipLoot();
    showWon(game.getRun().deck, deckBefore, null);
  });
}

function showWon(deck, deckBefore, equipped) {
  const changed = equipped
    ? `You equipped <b>${equipped.name}</b>. Your deck is now <b>${deck.length}</b> cards, with ${equipped.grants.cards.map((c) => `<b>${c}</b>`).join(' + ')} added.`
    : `You left the weapon behind. Deck unchanged at <b>${deck.length}</b> cards.`;
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <h2 class="win">RUN CLEARED</h2>
    <div class="deck-note">${changed}</div>
    <div class="deck-note" style="color:#6f6357">This is the M1 slice — one fight. Later slices add the map, town, the full loot ladder, runewords, the other classes, and the difficulty ladder.</div>
    <button class="act" id="again">DESCEND AGAIN</button>
  `;
  window.__bloodrune.won = true;
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(); });
}

function showDead() {
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <h2 class="dead">YOU HAVE DIED</h2>
    <div class="deck-note">The dark takes another. Permadeath ends the run — but what you learned persists (in later slices).</div>
    <button class="act" id="again">TRY AGAIN</button>
  `;
  window.__bloodrune.dead = true;
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newRun(); });
}

newRun();
