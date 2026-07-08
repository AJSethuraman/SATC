// UI for the SURROUNDED arena. Hero centered; the mob rings you (placed by
// angle); SVG lines link guardians to the caster they protect. Tap any enemy to
// target it — but a guarded caster is shielded until you clear its escorts or
// break through (Charge) at the cost of being Exposed.
import { createFight, SKILLS, skillEffect } from './engine.js';

const board = document.getElementById('board');
const logEl = document.getElementById('log');
const ov = document.getElementById('ov');
let fight, skillsOpen = false, focusUid = null;
window.__proto = {};

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, skillPoints: 5, hard: { strike: 0, cleave: 0, guard: 0 } };
const DECK = ['strike', 'cleave', 'guard', 'zeal', 'smite', 'charge', 'cleave'];
// A Fallen camp: a Shaman (caster) guarded by two Champions, plus grunts + a goatman.
const PACK = [{ id: 'shaman' }, { id: 'archer' }, { id: 'guardian', guards: 0 }, { id: 'guardian', guards: 0 },
  { id: 'fallen' }, { id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }];

function newFight() {
  fight = createFight({ deck: [...DECK], hero: JSON.parse(JSON.stringify(HERO)), pack: PACK.map((e) => ({ ...e })), seed: 'arena-' + (window.__seed || 'a') });
  skillsOpen = false; focusUid = null; render();
}
function expose() { window.__proto.state = fight.getState(); }
function pv(a, b) { return b > 0 ? Math.max(0, Math.min(100, a / b * 100)) : 0; }

function render() {
  expose();
  const s = fight.getState();
  if (s.over) return renderEnd(s);
  const h = s.hero;
  const living = s.enemies.filter((e) => e.hp > 0);
  if (focusUid == null || !living.find((e) => e.uid === focusUid)) focusUid = living[0] ? living[0].uid : null;

  // place enemies on CONCENTRIC rings: inner (melee bodies on you) and outer
  // (casters/archers behind them). Spread each ring evenly around the hero.
  const pos = {};
  [0, 1].forEach((ring) => {
    const grp = living.filter((e) => (e.ring || 0) === ring);
    const R = ring === 0 ? 30 : 47;
    grp.forEach((e, idx) => {
      const a = -Math.PI / 2 + (idx / grp.length) * Math.PI * 2 + (ring === 1 ? Math.PI / (grp.length || 1) : 0);
      pos[e.uid] = { x: 50 + R * Math.cos(a), y: 50 + R * Math.sin(a) };
    });
  });

  // guard lines: each guardian (inner) -> the caster it protects (outer)
  const lines = s.enemies.filter((e) => e.hp > 0 && e.role === 'guardian' && e.guardsUid != null)
    .map((g) => { const t = s.enemies.find((e) => e.uid === g.guardsUid && e.hp > 0); if (!t || !pos[g.uid] || !pos[t.uid]) return ''; const a = pos[g.uid], b = pos[t.uid];
      return `<line x1="${a.x}%" y1="${a.y}%" x2="${b.x}%" y2="${b.y}%" stroke="#4a7bff" stroke-opacity="0.5" stroke-width="1.5" stroke-dasharray="3 3"/>`; }).join('');

  const mobs = s.enemies.filter((e) => e.hp > 0).map((e) => {
    const p = pos[e.uid];
    const intent = e.intent ? (e.intent.type === 'mend' ? `<div class="in heal">✚ ${e.intent.value}</div>` : `<div class="in">⚔️ ${e.intent.value}</div>`) : '';
    const badge = e.guarded ? `<div class="badge guarded">🛡 guarded ×${e.guardianCount}</div>` : '';
    const roleClass = e.role === 'guardian' ? 'guardian' : e.role === 'caster' ? 'caster' : '';
    return `<div class="mob ${roleClass} ${e.uid === focusUid ? 'focus' : ''}" data-uid="${e.uid}" style="left:${p.x}%;top:${p.y}%">
      <div class="card2">${badge}
        <div class="g">${e.glyph}</div><div class="n">${e.name}</div>
        <div class="hp"><i style="width:${pv(e.hp, e.maxHp)}%"></i></div>${intent}
      </div>${e.uid === focusUid ? '<div class="focus-tag">🎯 target</div>' : ''}
    </div>`;
  }).join('');

  board.innerHTML = `
    <div class="bar ${h.exposed ? 'exposed' : ''}">
      <div class="stat"><span class="k">Life</span><span class="v life">${h.life}/${h.maxLife}</span></div>
      <div class="stat"><span class="k">Mana</span><span class="v mana">${h.mana}/${h.maxMana}</span></div>
      <div class="stat"><span class="k">Block</span><span class="v block">${h.block}</span></div>
      <div class="stat"><span class="k">+Skills</span><span class="v sk">${h.plusSkills}</span></div>
      ${h.exposed ? '<span class="expo">⚠ EXPOSED — block won\'t hold</span>' : ''}
      <div class="stat"><span class="k">Turn</span><span class="v">${s.turn}</span></div>
    </div>
    <div class="arena">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">${lines}</svg>
      <div class="hero-tok"><div class="ring"></div><div class="g">${h.plusSkills ? '🏹' : '🪓'}</div></div>
      ${mobs}
    </div>
    <div class="hint">You're surrounded — everyone hits you each turn. Tap an enemy to target it. The <b>Shaman is guarded</b> (🛡) while its Champions live: clear them, or <b>Charge</b> to break through (but you'll be <b>Exposed</b>).</div>
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

  board.querySelectorAll('.mob').forEach((m) => m.addEventListener('click', () => { focusUid = Number(m.dataset.uid); render(); }));
  document.getElementById('end').addEventListener('click', () => { fight.endTurn(); render(); });
  document.getElementById('skills').addEventListener('click', () => { skillsOpen = true; renderSkills(); });
  document.getElementById('amu').addEventListener('click', () => { fight.addPlusSkills(fight.getState().hero.plusSkills ? -2 : 2); render(); });
  document.querySelectorAll('.card').forEach((b) => b.addEventListener('click', () => { fight.playCard(Number(b.dataset.i), focusUid); render(); }));
  renderOverlay();
}

function cardHTML(c, i) {
  const s = fight.getState();
  const playable = c.cost <= s.hero.mana;
  const tag = c.type === 'breakthrough' ? 'breakthrough · exposes you' : c.target === 'aoe' ? 'attack · ALL' : c.type === 'skill' ? 'skill' : 'attack · target';
  return `<button class="card ${c.type}" data-i="${i}" ${playable ? '' : 'disabled'}>
    <div class="cn"><span>${c.name} <span class="lv">Lv ${c.eff.lvl}</span></span><span>${c.cost}⬡</span></div>
    <div class="ct">${tag}</div><div class="cx">${c.eff.text}</div>
  </button>`;
}

function renderOverlay() { if (skillsOpen) renderSkills(); else { ov.className = 'ov hidden'; ov.innerHTML = ''; } }
function renderSkills() {
  const s = fight.getState(); const h = s.hero;
  const rows = Object.keys(SKILLS).map((id) => {
    const eff = skillEffect(h, id); const can = h.skillPoints > 0; const known = s.deckSkills.includes(id);
    return `<div class="sk-row"><div class="sk-info"><div class="sn">${SKILLS[id].name} <span style="color:var(--gold)">Lv ${eff.lvl}</span></div><div class="se">${eff.text}</div></div>
      <div class="sk-btns">${known ? `<button data-imp="${id}" ${can ? '' : 'disabled'}>Improve ▲</button>` : `<button data-learn="${id}" ${can ? '' : 'disabled'}>Learn +Deck</button>`}</div></div>`;
  }).join('');
  ov.className = 'ov';
  ov.innerHTML = `<div class="sk-panel"><div class="sk-head"><div class="sk-title">⚔ Skill Tree — ${h.skillPoints} pts</div><button class="sk-close" id="skx">✕</button></div>
    <div class="sk-sub"><b>Learn</b> a skill into your deck or <b>Improve</b> its level — each scales its own way (Zeal gains hits). Try the <b>+2 Skills Amulet</b> to raise everything at once.</div>${rows}</div>`;
  document.getElementById('skx').addEventListener('click', () => { skillsOpen = false; render(); });
  ov.querySelectorAll('[data-imp]').forEach((b) => b.addEventListener('click', () => { fight.spendSkillPoint(b.dataset.imp, {}); renderSkills(); expose(); }));
  ov.querySelectorAll('[data-learn]').forEach((b) => b.addEventListener('click', () => { fight.spendSkillPoint(b.dataset.learn, { learn: true }); renderSkills(); expose(); }));
}

function renderEnd(s) {
  window.__proto.result = s.result;
  ov.className = 'ov';
  ov.innerHTML = `<div class="end"><h2 class="${s.result === 'win' ? 'win' : 'lose'}">${s.result === 'win' ? 'THE RING BREAKS' : 'YOU HAVE DIED'}</h2>
    <div style="color:var(--muted);max-width:420px;margin:0 auto 14px">${s.result === 'win' ? 'You cut down the mob and their shaman.' : 'The surround dragged you under.'}</div>
    <button class="act" id="again">FIGHT AGAIN</button></div>`;
  board.innerHTML = ''; logEl.innerHTML = '';
  document.getElementById('again').addEventListener('click', () => { window.__seed = Math.floor(performance.now()); newFight(); });
}

newFight();
