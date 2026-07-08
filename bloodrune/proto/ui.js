// UI for the de-clunked positional prototype. Melee lands on the front band;
// ranged can be aimed at any enemy but the front mob absorbs a shot aimed past
// it; Backstep (free, once/turn) shoves the swarm back. No reach-gating.
import { createFight, SKILLS, skillEffect, LANE } from './engine.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const ov = document.getElementById('ov');
let fight, skillsOpen = false, aimUid = null;
window.__proto = {};

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, skillPoints: 5,
  hard: { bash: 0, cleave: 0, guard: 0, shoot: 0 } };
const DECK = ['bash', 'cleave', 'guard', 'shoot', 'zeal', 'shoot', 'cleave'];
const PACK = [{ id: 'grunt', pos: 2 }, { id: 'grunt', pos: 2 }, { id: 'grunt', pos: 3 },
  { id: 'brute', pos: 4 }, { id: 'archer', pos: 5 }];

function newFight() {
  fight = createFight({ deck: [...DECK], hero: JSON.parse(JSON.stringify(HERO)), pack: PACK.map((e) => ({ ...e })), seed: 'proto-' + (window.__seed || 'a') });
  skillsOpen = false; aimUid = null; render();
}
function expose() { window.__proto.state = fight.getState(); }
function pv(a, b) { return b > 0 ? Math.max(0, Math.min(100, a / b * 100)) : 0; }

function render() {
  expose();
  const s = fight.getState();
  if (s.over) return renderEnd(s);
  const h = s.hero;
  const fp = s.frontPos;

  const cells = [];
  for (let p = 1; p <= LANE; p++) {
    const here = s.enemies.filter((e) => e.hp > 0 && e.pos === p);
    const isFront = p === fp;
    cells.push(`<div class="cell ${isFront ? 'front' : ''}">
      <div class="pos">${p === 1 ? 'ADJACENT' : 'd' + p}${isFront ? ' · FRONT' : ''}</div>
      ${here.map((e) => `<div class="mob ${e.ranged ? 'ranged' : ''} ${e.uid === aimUid ? 'aim' : ''}" data-uid="${e.uid}">
        ${e.uid === aimUid ? '<div class="aimtag">🎯 aim</div>' : ''}
        <div class="g">${e.glyph}</div><div class="n">${e.name}</div>
        <div class="hp"><i style="width:${pv(e.hp, e.maxHp)}%"></i></div>
        <div class="in ${e.intent && e.intent.type === 'advance' ? 'adv' : ''}">${e.intent ? (e.intent.type === 'attack' ? '⚔️ ' + e.intent.value : '👣') : ''}</div>
      </div>`).join('')}
    </div>`);
  }

  board.innerHTML = `
    <div class="bar">
      <div class="name">${h.plusSkills ? '🏹' : '🪓'} You</div>
      <div class="stat"><span class="k">Life</span><span class="v life">${h.life}/${h.maxLife}</span></div>
      <div class="stat"><span class="k">Mana</span><span class="v mana">${h.mana}/${h.maxMana}</span></div>
      <div class="stat"><span class="k">Block</span><span class="v block">${h.block}</span></div>
      <div class="stat"><span class="k">+Skills</span><span class="v sk">${h.plusSkills}</span></div>
      <div class="stat"><span class="k">Turn</span><span class="v">${s.turn}</span></div>
    </div>
    <div class="lane">${cells.join('')}</div>
    <div class="reachline">Melee hits the FRONT band · tap an enemy to aim ranged (the front mob soaks shots aimed past it) · the swarm closes in each turn</div>
    <div class="moves">
      <button class="act ghost" id="back" ${s.canBackstep ? '' : 'disabled'}>↩ BACKSTEP (shove the swarm back)</button>
    </div>
    <div class="hand">${s.hand.map(cardHTML).join('')}</div>
    <div class="controls">
      <div>
        <button class="act ghost" id="skills">⚔ SKILLS (pts ${h.skillPoints})</button>
        <button class="act ghost" id="amu">${h.plusSkills ? 'DROP +Skills GEAR' : 'LOOT +2 SKILLS AMULET'}</button>
      </div>
      <button class="act" id="end">END TURN</button>
    </div>`;

  logEl.innerHTML = s.log.slice(-7).map((l) => `<div>${l}</div>`).join('');
  logEl.scrollTop = logEl.scrollHeight;

  s.enemies.forEach((e) => { if (e.hp > 0) { const n = board.querySelector(`.mob[data-uid="${e.uid}"]`); if (n) n.addEventListener('click', () => { aimUid = e.uid; render(); }); } });
  document.getElementById('back').addEventListener('click', () => { fight.backstep(); render(); });
  document.getElementById('end').addEventListener('click', () => { fight.endTurn(); render(); });
  document.getElementById('skills').addEventListener('click', () => { skillsOpen = true; renderSkills(); });
  document.getElementById('amu').addEventListener('click', () => { fight.addPlusSkills(fight.getState().hero.plusSkills ? -2 : 2); render(); });
  document.querySelectorAll('.card').forEach((b) => b.addEventListener('click', () => {
    const i = Number(b.dataset.i); const c = s.hand[i];
    fight.playCard(i, c.type === 'ranged' ? aimUid : undefined); render();
  }));
  renderOverlay();
}

function cardHTML(c, i) {
  const s = fight.getState();
  const playable = c.cost <= s.hero.mana;
  const tag = c.type === 'melee' ? 'melee · front band' : c.type === 'ranged' ? 'ranged · aim' : 'skill';
  return `<button class="card ${c.type}" data-i="${i}" ${playable ? '' : 'disabled'}>
    <div class="cn"><span>${c.name} <span class="lv">Lv ${c.eff.lvl}</span></span><span>${c.cost}⬡</span></div>
    <div class="ct">${tag}</div>
    <div class="cx">${c.eff.text}</div>
  </button>`;
}

function renderOverlay() { if (skillsOpen) renderSkills(); else { ov.className = 'ov hidden'; ov.innerHTML = ''; } }

function renderSkills() {
  const s = fight.getState();
  const h = s.hero;
  const rows = Object.keys(SKILLS).map((id) => {
    const eff = skillEffect(h, id);
    const can = h.skillPoints > 0;
    const known = s.deckSkills.includes(id);
    return `<div class="sk-row">
      <div class="sk-info"><div class="sn">${SKILLS[id].name} <span style="color:var(--gold)">Lv ${eff.lvl}</span></div><div class="se">${eff.text}</div></div>
      <div class="sk-btns">${known ? `<button data-imp="${id}" ${can ? '' : 'disabled'}>Improve ▲</button>` : `<button data-learn="${id}" ${can ? '' : 'disabled'}>Learn +Deck</button>`}</div>
    </div>`;
  }).join('');
  ov.className = 'ov';
  ov.innerHTML = `<div class="sk-panel">
    <div class="sk-head"><div class="sk-title">⚔ Skill Tree — ${h.skillPoints} pts</div><button class="sk-close" id="skx">✕</button></div>
    <div class="sk-sub"><b>Learn</b> a skill (it enters your deck) or <b>Improve</b> its level. Each scales its own way — Zeal gains hits, Charged Bolt gains bolts. Try the <b>+2 Skills Amulet</b> to raise everything at once.</div>
    ${rows}
  </div>`;
  document.getElementById('skx').addEventListener('click', () => { skillsOpen = false; render(); });
  ov.querySelectorAll('[data-imp]').forEach((b) => b.addEventListener('click', () => { fight.spendSkillPoint(b.dataset.imp, {}); renderSkills(); expose(); }));
  ov.querySelectorAll('[data-learn]').forEach((b) => b.addEventListener('click', () => { fight.spendSkillPoint(b.dataset.learn, { learn: true }); renderSkills(); expose(); }));
}

function renderEnd(s) {
  window.__proto.result = s.result;
  ov.className = 'ov';
  ov.innerHTML = `<div class="end"><h2 class="${s.result === 'win' ? 'win' : 'lose'}">${s.result === 'win' ? 'BAND CLEARED' : 'YOU HAVE DIED'}</h2>
    <div style="color:var(--muted);max-width:420px;margin:0 auto 14px">${s.result === 'win' ? 'The swarm broke on you.' : 'The swarm overran you.'}</div>
    <button class="act" id="again">FIGHT AGAIN</button></div>`;
  board.innerHTML = ''; logEl.innerHTML = '';
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newFight(); });
}

newFight();
