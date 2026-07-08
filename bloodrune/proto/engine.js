// Bloodrune — Option B positional PROTOTYPE, "de-clunk" pass. Removes the
// movement tax: melee always lands on the front band (you lunge implicitly),
// ranged fires from anywhere but is ABSORBED by the front mob if you aim past
// it, and repositioning is one optional free Backstep (push the swarm back to
// buy a turn) rather than a mandatory move. Enemies still close in for pressure.
// Skills SCALE by level, D2-style. Pure engine, seeded rng.

import { makeRng } from '../engine/rng.js';

export const LANE = 6; // enemy bands at distance 1..LANE (1 = adjacent)

export const SKILLS = {
  bash: { id: 'bash', name: 'Bash', type: 'melee', cost: 2, scale: 'damage', base: 6, grow: 2, block: 3 },
  cleave: { id: 'cleave', name: 'Cleave', type: 'melee', cost: 3, scale: 'damage', base: 5, grow: 2, aoe: true },
  zeal: { id: 'zeal', name: 'Zeal', type: 'melee', cost: 3, scale: 'hits', base: 4, hitCap: 5 },
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

export function skillLevel(hero, id) { return 1 + (hero.hard[id] || 0) + (hero.plusSkills || 0); }

export function skillEffect(hero, id) {
  const s = SKILLS[id];
  const lvl = skillLevel(hero, id);
  if (s.scale === 'damage') return { lvl, damage: s.base + s.grow * (lvl - 1), text: `Deal ${s.base + s.grow * (lvl - 1)}${s.aoe ? ' to the whole band' : ''}${s.block ? `, gain ${s.block} Block` : ''}.` };
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, damage: s.base, text: `Strike ${hits}× for ${s.base} (hits scale with level).` }; }
  if (s.scale === 'bolts') { const bolts = lvl; return { lvl, bolts, damage: s.base, text: `Fire ${bolts} bolts (×${s.base}) into the front band (bolts scale with level).` }; }
  if (s.scale === 'block') return { lvl, block: s.base + s.grow * (lvl - 1), text: `Gain ${s.base + s.grow * (lvl - 1)} Block.` };
  return { lvl, text: '' };
}

export function createFight({ deck, hero, pack, seed = 'proto' } = {}) {
  const rng = makeRng(seed);
  const state = {
    hero: { life: hero.maxLife, maxLife: hero.maxLife, block: 0, mana: hero.maxMana, maxMana: hero.maxMana,
      handSize: hero.handSize || 5, plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) },
      backstepped: false, skillPoints: hero.skillPoints || 0 },
    enemies: pack.map((e, i) => ({ uid: i, ...ENEMIES[e.id], hp: ENEMIES[e.id].hp, maxHp: ENEMIES[e.id].hp, pos: e.pos, intent: null })),
    drawPile: rng.shuffle(deck), hand: [], discardPile: [],
    turn: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const frontPos = () => (alive().length ? Math.min(...alive().map((e) => e.pos)) : null);
  const bandAt = (pos) => alive().filter((e) => e.pos === pos);

  function draw() { if (!state.drawPile.length) { if (!state.discardPile.length) return; state.drawPile = rng.shuffle(state.discardPile); state.discardPile = []; } state.hand.push(state.drawPile.pop()); }

  function telegraph() {
    for (const e of state.enemies) {
      if (e.hp <= 0) { e.intent = null; continue; }
      if (e.ranged || e.pos <= 1) e.intent = { type: 'attack', value: e.attack };
      else e.intent = { type: 'advance' };
    }
  }

  function startTurn() {
    state.turn += 1; state.hero.block = 0; state.hero.mana = state.hero.maxMana; state.hero.backstepped = false;
    while (state.hand.length < state.hero.handSize && (state.drawPile.length || state.discardPile.length)) draw();
    telegraph();
    state.log.push(`— Turn ${state.turn} —`);
  }

  function hurt(e, dmg) { e.hp = Math.max(0, e.hp - dmg); if (e.hp === 0) { e.intent = null; state.log.push(`${e.name} dies.`); } }

  // Backstep: free, once per turn — shove the whole swarm back a band to buy time.
  function backstep() {
    if (state.over || state.hero.backstepped) return { ok: false };
    for (const e of alive()) e.pos = Math.min(LANE, e.pos + 1);
    state.hero.backstepped = true;
    telegraph();
    state.log.push('You give ground — the swarm falls back a step.');
    return { ok: true };
  }

  // targetUid (optional): the enemy you TRIED to hit with a ranged shot. If it
  // isn't in the front band, the front mob absorbs the shot.
  function playCard(handIndex, targetUid) {
    if (state.over) return { ok: false };
    const id = state.hand[handIndex];
    if (id == null) return { ok: false };
    const s = SKILLS[id];
    if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    const eff = skillEffect(state.hero, id);
    const fp = frontPos();

    state.hero.mana -= s.cost;
    if (s.type === 'skill') { if (eff.block) state.hero.block += eff.block; }
    else if (fp != null) {
      // ranged aimed past the front is absorbed by the front mob
      if (s.type === 'ranged' && targetUid != null) {
        const tgt = state.enemies.find((e) => e.uid === targetUid && e.hp > 0);
        if (tgt && tgt.pos > fp) state.log.push(`Your shot is absorbed by the ${bandAt(fp)[0].name} in front.`);
      }
      const band = bandAt(fp);
      if (s.scale === 'hits') { for (let h = 0; h < eff.hits && band[0].hp > 0; h++) hurt(band[0], eff.damage); }
      else if (s.scale === 'bolts') { for (let b = 0; b < eff.bolts; b++) { const living = band.filter((e) => e.hp > 0); if (!living.length) break; hurt(living[b % living.length], eff.damage); } }
      else if (s.aoe) { for (const e of band) hurt(e, eff.damage); }
      else { hurt(band[0], eff.damage); if (s.block) state.hero.block += s.block; }
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
      } else e.pos = Math.max(1, e.pos - 1);
    }
    if (state.hero.life <= 0) { finish('lose'); return; }
    startTurn();
  }

  function spendSkillPoint(id, { learn = false } = {}) {
    if (state.hero.skillPoints <= 0) return { ok: false };
    state.hero.skillPoints -= 1;
    state.hero.hard[id] = (state.hero.hard[id] || 0) + 1;
    if (learn) state.drawPile.push(id);
    state.log.push(`${learn ? 'Learn' : 'Improve'} ${SKILLS[id].name} (Lv ${skillLevel(state.hero, id)}).`);
    return { ok: true };
  }

  function addPlusSkills(n) { state.hero.plusSkills = Math.max(0, state.hero.plusSkills + n); }
  function finish(r) { state.over = true; state.result = r; state.log.push(r === 'win' ? 'Cleared.' : 'You have died.'); }

  function getState() {
    return {
      hero: { ...state.hero, hard: { ...state.hero.hard } },
      lane: LANE, frontPos: frontPos(),
      enemies: state.enemies.map((e) => ({ ...e })),
      hand: state.hand.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })),
      drawCount: state.drawPile.length, discardCount: state.discardPile.length,
      deckSkills: [...new Set([...state.drawPile, ...state.hand, ...state.discardPile])],
      turn: state.turn, over: state.over, result: state.result, log: state.log.slice(),
      canBackstep: !state.hero.backstepped && !state.over,
    };
  }

  startTurn();
  return { playCard, endTurn, backstep, spendSkillPoint, addPlusSkills, getState };
}
