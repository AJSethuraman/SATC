// Bloodrune — Option B positional-combat PROTOTYPE (separate from the main run).
// A lane of range bands: the hero at position 0, enemies at positions 1..N that
// ADVANCE toward you each turn. You spend a Move to maneuver (advance to reach
// melee, or retreat to kite). Melee needs the enemy within reach; RANGED can
// fire at any distance but the NEAREST occupied band intercepts it (a mob on the
// way body-blocks the shot). Skills SCALE by level in their own way, D2-style
// (Zeal +1 hit/level, Charged Bolt +1 bolt/level); +Skills raises every skill's
// level. Pure engine — no DOM, seeded rng.
//
// See docs/research-d2-skills.md for the scaling model.

import { makeRng } from '../engine/rng.js';

export const LANE = 6; // positions 0..6; hero starts at 0, enemies at >=1

// Skill/card scaling. `scale` picks the per-skill scaling function.
// level = 1 (base) + hard points + plusSkills(gear/soft).
export const SKILLS = {
  bash: { id: 'bash', name: 'Bash', type: 'melee', reach: 1, cost: 2, scale: 'damage', base: 6, grow: 2, block: 3 },
  cleave: { id: 'cleave', name: 'Cleave', type: 'melee', reach: 1, cost: 3, scale: 'damage', base: 5, grow: 2, aoe: true },
  zeal: { id: 'zeal', name: 'Zeal', type: 'melee', reach: 1, cost: 3, scale: 'hits', base: 4, hitCap: 5 },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 2, scale: 'block', base: 6, grow: 2 },
  shoot: { id: 'shoot', name: 'Arrow', type: 'ranged', cost: 2, scale: 'damage', base: 5, grow: 2 },
  charged_bolt: { id: 'charged_bolt', name: 'Charged Bolt', type: 'ranged', cost: 3, scale: 'bolts', base: 3 },
  fireball: { id: 'fireball', name: 'Fireball', type: 'ranged', cost: 4, scale: 'damage', base: 6, grow: 3, aoe: true },
};

export const ENEMIES = {
  grunt: { id: 'grunt', name: 'Fallen', hp: 10, attack: 4, glyph: '👺', ranged: false },
  brute: { id: 'brute', name: 'Goatman', hp: 18, attack: 6, glyph: '🐐', ranged: false },
  archer: { id: 'archer', name: 'Dark Archer', hp: 8, attack: 5, glyph: '🏹', ranged: true },
};

// Effective level of a skill for this hero.
export function skillLevel(hero, id) {
  return 1 + (hero.hard[id] || 0) + (hero.plusSkills || 0);
}

// Human-readable, LEVEL-SCALED description — this is what makes "+1 to Skills"
// visibly change each skill in its own way.
export function skillEffect(hero, id) {
  const s = SKILLS[id];
  const lvl = skillLevel(hero, id);
  if (s.scale === 'damage') return { lvl, damage: s.base + s.grow * (lvl - 1), text: `Deal ${s.base + s.grow * (lvl - 1)}${s.aoe ? ' to the whole band' : ''}${s.block ? `, gain ${s.block} Block` : ''}.` };
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, damage: s.base, text: `Strike ${hits}× for ${s.base} (hits scale with level).` }; }
  if (s.scale === 'bolts') { const bolts = lvl; return { lvl, bolts, damage: s.base, text: `Fire ${bolts} bolts (×${s.base}) into the nearest band (bolts scale with level).` }; }
  if (s.scale === 'block') return { lvl, block: s.base + s.grow * (lvl - 1), text: `Gain ${s.base + s.grow * (lvl - 1)} Block.` };
  return { lvl, text: '' };
}

export function createFight({ deck, hero, pack, seed = 'proto' } = {}) {
  const rng = makeRng(seed);
  const state = {
    hero: { pos: 0, life: hero.maxLife, maxLife: hero.maxLife, block: 0, mana: hero.maxMana,
      maxMana: hero.maxMana, handSize: hero.handSize || 5, plusSkills: hero.plusSkills || 0,
      hard: { ...(hero.hard || {}) }, moved: false, skillPoints: hero.skillPoints || 0 },
    enemies: pack.map((e, i) => ({ uid: i, ...ENEMIES[e.id], hp: ENEMIES[e.id].hp, maxHp: ENEMIES[e.id].hp, pos: e.pos, intent: null })),
    drawPile: rng.shuffle(deck), hand: [], discardPile: [],
    turn: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const dist = (e) => e.pos - state.hero.pos;
  // nearest occupied band position (smallest positive-or-zero distance)
  function frontBand() {
    const living = alive();
    if (!living.length) return null;
    const minPos = Math.min(...living.map((e) => e.pos));
    return living.filter((e) => e.pos === minPos);
  }

  function draw() {
    if (!state.drawPile.length) { if (!state.discardPile.length) return; state.drawPile = rng.shuffle(state.discardPile); state.discardPile = []; }
    state.hand.push(state.drawPile.pop());
  }

  function telegraph() {
    for (const e of state.enemies) {
      if (e.hp <= 0) { e.intent = null; continue; }
      const d = dist(e);
      if (e.ranged || d <= 1) e.intent = { type: 'attack', value: e.attack };
      else e.intent = { type: 'advance' };
    }
  }

  function startTurn() {
    state.turn += 1; state.hero.block = 0; state.hero.mana = state.hero.maxMana; state.hero.moved = false;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) draw();
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(e, dmg) { e.hp = Math.max(0, e.hp - dmg); if (e.hp === 0) { e.intent = null; state.log.push(`${e.name} dies.`); } }

  // Move a Move: 'advance' (toward enemies) or 'retreat' (kite). One per turn.
  function move(dir) {
    if (state.over || state.hero.moved) return { ok: false, reason: 'already moved this turn' };
    if (dir === 'advance') state.hero.pos = Math.min(LANE - 1, state.hero.pos + 1);
    else state.hero.pos = Math.max(0, state.hero.pos - 1);
    state.hero.moved = true;
    telegraph(); // re-evaluate reach after moving
    state.log.push(`You ${dir === 'advance' ? 'advance' : 'fall back'}.`);
    return { ok: true };
  }

  function playCard(handIndex) {
    if (state.over) return { ok: false };
    const id = state.hand[handIndex];
    if (id == null) return { ok: false };
    const s = SKILLS[id];
    if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    const front = frontBand();
    if ((s.type === 'melee') && (!front || (front[0].pos - state.hero.pos) > (s.reach || 1))) {
      return { ok: false, reason: 'out of reach — move closer' };
    }
    const eff = skillEffect(state.hero, id);

    state.hero.mana -= s.cost;
    if (s.type === 'skill') { if (eff.block) state.hero.block += eff.block; }
    else if (front) {
      if (s.scale === 'hits') { // Zeal: N strikes on the nearest single enemy
        const target = front[0];
        for (let h = 0; h < eff.hits && target.hp > 0; h++) hurt(target, eff.damage);
      } else if (s.scale === 'bolts') { // Charged Bolt: N bolts spread across the front band
        for (let blt = 0; blt < eff.bolts; blt++) { const living = front.filter((e) => e.hp > 0); if (!living.length) break; hurt(living[blt % living.length], eff.damage); }
      } else if (s.aoe) { // Cleave / Fireball: whole nearest band
        for (const e of front) hurt(e, eff.damage);
      } else { // single-target damage (Bash / Arrow): nearest enemy
        hurt(front[0], eff.damage);
        if (s.block) state.hero.block += s.block;
      }
    }
    state.log.push(`Play ${s.name}.`);
    state.hand.splice(handIndex, 1); state.discardPile.push(id);
    if (!alive().length) finish('win');
    return { ok: true };
  }

  function endTurn() {
    if (state.over) return;
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    for (const e of state.enemies) {
      if (e.hp <= 0 || !e.intent) continue;
      if (e.intent.type === 'attack') {
        const absorbed = Math.min(state.hero.block, e.attack); state.hero.block -= absorbed;
        const dmg = e.attack - absorbed; state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${e.name} hits you for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}.`);
      } else { e.pos = Math.max(state.hero.pos + 1, e.pos - 1); } // advance, stop adjacent
    }
    if (state.hero.life <= 0) { finish('lose'); return; }
    startTurn();
  }

  // Skill tree: learn a skill (adds its card to the deck) or level one up.
  function spendSkillPoint(id, { learn = false } = {}) {
    if (state.hero.skillPoints <= 0) return { ok: false, reason: 'no skill points' };
    state.hero.skillPoints -= 1;
    state.hero.hard[id] = (state.hero.hard[id] || 0) + 1;
    if (learn) { state.drawPile.push(id); } // enters the deck
    state.log.push(`${learn ? 'Learn' : 'Improve'} ${SKILLS[id].name} (Lv ${skillLevel(state.hero, id)}).`);
    return { ok: true };
  }

  // Demo hook: simulate finding "+N to Skills" gear (soft points) — raises every
  // skill's level at once, each scaling in its own way.
  function addPlusSkills(n) { state.hero.plusSkills = Math.max(0, state.hero.plusSkills + n); }

  function finish(r) { state.over = true; state.result = r; state.log.push(r === 'win' ? 'Cleared.' : 'You have died.'); }

  function getState() {
    return {
      hero: { ...state.hero, hard: { ...state.hero.hard } },
      lane: LANE,
      enemies: state.enemies.map((e) => ({ ...e, dist: e.pos - state.hero.pos })),
      hand: state.hand.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })),
      drawCount: state.drawPile.length, discardCount: state.discardPile.length,
      deckSkills: [...new Set([...state.drawPile, ...state.hand, ...state.discardPile])],
      turn: state.turn, over: state.over, result: state.result, log: state.log.slice(),
      canMove: !state.hero.moved && !state.over,
    };
  }

  startTurn();
  return { playCard, endTurn, move, spendSkillPoint, addPlusSkills, getState };
}
