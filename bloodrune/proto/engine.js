// Bloodrune — SURROUNDED arena prototype. You stand in the middle of a ring of
// enemies (a D2 mob). You may FREELY target anyone — but the optimal target (a
// caster/elite) is GUARDED by its escorts: while a guardian lives, that target
// takes heavily reduced damage. You can punch through *now* with a BREAKTHROUGH
// skill (Charge) that ignores the guard — but it leaves you EXPOSED (your Block
// won't hold that turn). Every living enemy hits you each turn (the surround),
// so deleting the caster means eating the ring's damage. Real choice, no waves.
// Skills SCALE by level (D2). Pure engine, seeded rng.

import { makeRng } from '../engine/rng.js';

export const GUARD_MITIGATION = 0.6; // guarded targets take 40% damage while guarded

export const SKILLS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', target: 'single', cost: 2, scale: 'damage', base: 6, grow: 2 },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', target: 'aoe', cost: 3, scale: 'damage', base: 5, grow: 2 },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', target: 'single', cost: 3, scale: 'hits', base: 4, hitCap: 5 },
  smite: { id: 'smite', name: 'Smite', type: 'attack', target: 'single', cost: 3, scale: 'damage', base: 9, grow: 3 },
  charge: { id: 'charge', name: 'Charge', type: 'breakthrough', target: 'single', cost: 3, scale: 'damage', base: 7, grow: 2 },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 2, scale: 'block', base: 7, grow: 2 },
};

// ring: 0 = inner (the melee bodies on top of you), 1 = outer (support/back-line
// you want dead — casters, archers — sitting behind their escorts).
export const ENEMIES = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 8, attack: 3, glyph: '👺', role: 'grunt', ring: 0 },
  guardian: { id: 'guardian', name: 'Fallen Champion', hp: 15, attack: 4, glyph: '🛡️', role: 'guardian', ring: 0 },
  goatman: { id: 'goatman', name: 'Goatman', hp: 18, attack: 6, glyph: '🐐', role: 'grunt', ring: 0 },
  shaman: { id: 'shaman', name: 'Fallen Shaman', hp: 16, attack: 3, glyph: '🧙', role: 'caster', heal: 5, ring: 1 },
  archer: { id: 'archer', name: 'Dark Archer', hp: 9, attack: 5, glyph: '🏹', role: 'archer', ring: 1 },
};
const GUARDABLE = new Set(['caster', 'elite']);

export function skillLevel(hero, id) { return 1 + (hero.hard[id] || 0) + (hero.plusSkills || 0); }

export function skillEffect(hero, id) {
  const s = SKILLS[id]; const lvl = skillLevel(hero, id);
  if (s.scale === 'damage') return { lvl, damage: s.base + s.grow * (lvl - 1), text: `Deal ${s.base + s.grow * (lvl - 1)}${s.aoe || s.target === 'aoe' ? ' to ALL' : ''}.` };
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, damage: s.base, text: `Strike ${hits}× for ${s.base} (hits scale with level).` }; }
  if (s.scale === 'block') return { lvl, block: s.base + s.grow * (lvl - 1), text: `Gain ${s.base + s.grow * (lvl - 1)} Block.` };
  return { lvl, text: '' };
}

export function createFight({ deck, hero, pack, seed = 'proto' } = {}) {
  const rng = makeRng(seed);
  const state = {
    hero: { life: hero.maxLife, maxLife: hero.maxLife, block: 0, mana: hero.maxMana, maxMana: hero.maxMana,
      handSize: hero.handSize || 5, plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) },
      exposed: false, skillPoints: hero.skillPoints || 0 },
    enemies: pack.map((e, i) => ({ uid: i, ...ENEMIES[e.id], hp: ENEMIES[e.id].hp, maxHp: ENEMIES[e.id].hp,
      guardsUid: e.guards != null ? e.guards : null, intent: null })),
    drawPile: rng.shuffle(deck), hand: [], discardPile: [],
    turn: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const byUid = (uid) => state.enemies.find((e) => e.uid === uid);
  function livingGuardians(target) { return alive().filter((g) => g.role === 'guardian' && g.guardsUid === target.uid); }
  function isGuarded(e) { return GUARDABLE.has(e.role) && livingGuardians(e).length > 0; }

  function draw() { if (!state.drawPile.length) { if (!state.discardPile.length) return; state.drawPile = rng.shuffle(state.discardPile); state.discardPile = []; } state.hand.push(state.drawPile.pop()); }
  const woundedAllies = (self) => alive().filter((a) => a !== self && a.hp < a.maxHp);

  function telegraph() {
    for (const e of state.enemies) {
      if (e.hp <= 0) { e.intent = null; continue; }
      if (e.role === 'caster' && woundedAllies(e).length > 0) e.intent = { type: 'mend', value: e.heal };
      else e.intent = { type: 'attack', value: e.attack };
    }
  }

  function startTurn() {
    state.turn += 1; state.hero.block = 0; state.hero.mana = state.hero.maxMana; state.hero.exposed = false;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) draw();
    telegraph(); state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(e, dmg) { e.hp = Math.max(0, e.hp - dmg); if (e.hp === 0) { e.intent = null; state.log.push(`${e.name} dies.`); } }

  // Apply damage, honoring guard mitigation unless this is a breakthrough.
  function applyHit(e, dmg, breakthrough) {
    let d = dmg;
    if (!breakthrough && isGuarded(e)) { d = Math.max(1, Math.round(dmg * (1 - GUARD_MITIGATION))); state.log.push(`${e.name} is guarded — only ${d} gets through.`); }
    hurt(e, d);
  }

  function playCard(handIndex, targetUid) {
    if (state.over) return { ok: false };
    const id = state.hand[handIndex]; if (id == null) return { ok: false };
    const s = SKILLS[id]; if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    const eff = skillEffect(state.hero, id);
    // single/breakthrough need a living target
    let target = null;
    if (s.target === 'single') { target = byUid(targetUid); if (!target || target.hp <= 0) target = alive()[0]; if (!target) return { ok: false, reason: 'no target' }; }

    state.hero.mana -= s.cost;
    if (s.type === 'skill') { if (eff.block) state.hero.block += eff.block; }
    else if (s.type === 'breakthrough') { applyHit(target, eff.damage, true); state.hero.exposed = true; state.log.push('You break through the guard — and drop your guard.'); }
    else if (s.target === 'aoe') { for (const e of alive()) applyHit(e, eff.damage, false); }
    else if (s.scale === 'hits') { for (let h = 0; h < eff.hits && target.hp > 0; h++) applyHit(target, eff.damage, false); }
    else { applyHit(target, eff.damage, false); }

    state.log.push(`Play ${s.name}.`);
    state.hand.splice(handIndex, 1); state.discardPile.push(id);
    if (!alive().length) finish('win');
    return { ok: true };
  }

  function endTurn() {
    if (state.over) return;
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    const exposed = state.hero.exposed; // your Block won't hold if you broke through
    for (const e of state.enemies) {
      if (e.hp <= 0 || !e.intent) continue;
      if (e.intent.type === 'attack') {
        const absorbed = exposed ? 0 : Math.min(state.hero.block, e.attack); state.hero.block -= absorbed;
        const dmg = e.attack - absorbed; state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${e.name} hits you for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}${exposed ? ' (exposed!)' : ''}.`);
      } else if (e.intent.type === 'mend') {
        const allies = woundedAllies(e).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
        if (allies.length) { const t = allies[0]; const before = t.hp; t.hp = Math.min(t.maxHp, t.hp + e.intent.value); state.log.push(`${e.name} mends ${t.name} +${t.hp - before}.`); }
      }
    }
    if (state.hero.life <= 0) { finish('lose'); return; }
    startTurn();
  }

  function spendSkillPoint(id, { learn = false } = {}) {
    if (state.hero.skillPoints <= 0) return { ok: false };
    state.hero.skillPoints -= 1; state.hero.hard[id] = (state.hero.hard[id] || 0) + 1;
    if (learn) state.drawPile.push(id);
    state.log.push(`${learn ? 'Learn' : 'Improve'} ${SKILLS[id].name} (Lv ${skillLevel(state.hero, id)}).`);
    return { ok: true };
  }
  function addPlusSkills(n) { state.hero.plusSkills = Math.max(0, state.hero.plusSkills + n); }
  function finish(r) { state.over = true; state.result = r; state.log.push(r === 'win' ? 'The ring breaks.' : 'You have died.'); }

  function getState() {
    return {
      hero: { ...state.hero, hard: { ...state.hero.hard } },
      enemies: state.enemies.map((e) => ({ ...e, ring: ENEMIES[e.id].ring || 0, guarded: isGuarded(e), guardianCount: livingGuardians(e).length })),
      hand: state.hand.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })),
      drawCount: state.drawPile.length, discardCount: state.discardPile.length,
      deckSkills: [...new Set([...state.drawPile, ...state.hand, ...state.discardPile])],
      turn: state.turn, over: state.over, result: state.result, log: state.log.slice(),
    };
  }

  startTurn();
  return { playCard, endTurn, spendSkillPoint, addPlusSkills, getState };
}
