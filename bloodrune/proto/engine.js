// Bloodrune — SURROUNDED arena prototype, with REACH + SUMMONS. You stand in a
// ring of enemies: an INNER ring (melee bodies on top of you) and an OUTER ring
// (the casters/archers you want dead, behind their escorts). Your basic melee
// only reaches the inner ring. To hit the outer ring you need REACH (a ranged
// skill), a CHARGE (break in for full damage, but you're left EXPOSED), or
// SUMMONS — skeletons that attack out of your immediate circle every turn (even
// past the guard). Casters are also GUARDED (reduced damage while an escort
// lives) unless you break through or flank with summons. Skills SCALE by level.
// Pure engine, seeded rng.

import { makeRng } from '../engine/rng.js';

export const GUARD_MITIGATION = 0.6; // guarded casters take 40% from ordinary hits

export const SKILLS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', target: 'single', reach: 0, cost: 2, scale: 'damage', base: 6, grow: 2 },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', target: 'aoe', reach: 0, cost: 3, scale: 'damage', base: 5, grow: 2 },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'hits', base: 4, hitCap: 5 },
  smite: { id: 'smite', name: 'Smite', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'damage', base: 9, grow: 3 },
  shoot: { id: 'shoot', name: 'Arrow', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', base: 5, grow: 2 },
  charge: { id: 'charge', name: 'Charge', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', base: 7, grow: 2 },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 2, scale: 'block', base: 7, grow: 2 },
  raise_skeleton: { id: 'raise_skeleton', name: 'Raise Skeleton', type: 'summon', cost: 3, scale: 'summons' },
};

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
  if (s.scale === 'damage') return { lvl, damage: s.base + s.grow * (lvl - 1), text: `Deal ${s.base + s.grow * (lvl - 1)}${s.target === 'aoe' ? ' to the inner ring' : ''}${s.reach ? ' (reaches the outer ring)' : ''}.` };
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, damage: s.base, text: `Strike ${hits}× for ${s.base} (hits scale with level).` }; }
  if (s.scale === 'block') return { lvl, block: s.base + s.grow * (lvl - 1), text: `Gain ${s.base + s.grow * (lvl - 1)} Block.` };
  if (s.scale === 'summons') { const count = 1 + Math.floor((lvl - 1) / 2); const atk = 3 + (lvl - 1); return { lvl, count, attack: atk, text: `Raise ${count} skeleton${count > 1 ? 's' : ''} (atk ${atk}). They strike your target each turn — even the outer ring, past the guard.` }; }
  return { lvl, text: '' };
}

export function createFight({ deck, hero, pack, seed = 'proto' } = {}) {
  const rng = makeRng(seed);
  const state = {
    hero: { life: hero.maxLife, maxLife: hero.maxLife, block: 0, mana: hero.maxMana, maxMana: hero.maxMana,
      handSize: hero.handSize || 5, plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) },
      exposed: false, skillPoints: hero.skillPoints || 0, summons: [], focusUid: null },
    enemies: pack.map((e, i) => ({ uid: i, ...ENEMIES[e.id], hp: ENEMIES[e.id].hp, maxHp: ENEMIES[e.id].hp,
      guardsUid: e.guards != null ? e.guards : null, intent: null })),
    drawPile: rng.shuffle(deck), hand: [], discardPile: [],
    turn: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const byUid = (uid) => state.enemies.find((e) => e.uid === uid);
  const ringOf = (e) => ENEMIES[e.id].ring || 0;
  function livingGuardians(t) { return alive().filter((g) => g.role === 'guardian' && g.guardsUid === t.uid); }
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
  function applyHit(e, dmg, pierceGuard) {
    let d = dmg;
    if (!pierceGuard && isGuarded(e)) { d = Math.max(1, Math.round(dmg * (1 - GUARD_MITIGATION))); state.log.push(`${e.name} is guarded — only ${d} gets through.`); }
    hurt(e, d);
  }

  function setFocus(uid) { state.hero.focusUid = uid; }

  // pick a target for a card given the player's focus and the card's reach
  function pickTarget(card) {
    const reach = card.reach || 0;
    const f = byUid(state.hero.focusUid);
    if (f && f.hp > 0 && ringOf(f) <= reach) return f;
    const reachable = alive().filter((e) => ringOf(e) <= reach);
    return reachable[0] || null;
  }

  function playCard(handIndex, focusUid) {
    if (state.over) return { ok: false };
    if (focusUid != null) state.hero.focusUid = focusUid;
    const id = state.hand[handIndex]; if (id == null) return { ok: false };
    const s = SKILLS[id]; if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    const eff = skillEffect(state.hero, id);

    state.hero.mana -= s.cost;
    if (s.type === 'skill') { if (eff.block) state.hero.block += eff.block; }
    else if (s.type === 'summon') { for (let i = 0; i < eff.count; i++) state.hero.summons.push({ glyph: '💀', attack: eff.attack }); state.log.push(`Raise ${eff.count} skeleton(s).`); }
    else if (s.target === 'aoe') { for (const e of alive().filter((x) => ringOf(x) <= (s.reach || 0))) applyHit(e, eff.damage, false); }
    else {
      const t = pickTarget(s); if (!t) return state.hero.mana += s.cost, { ok: false, reason: 'no target in reach' };
      if (s.type === 'breakthrough') { applyHit(t, eff.damage, true); state.hero.exposed = true; state.log.push('You break through — and drop your guard.'); }
      else if (s.scale === 'hits') { for (let h = 0; h < eff.hits && t.hp > 0; h++) applyHit(t, eff.damage, false); }
      else applyHit(t, eff.damage, false);
    }
    state.log.push(`Play ${s.name}.`);
    state.hand.splice(handIndex, 1); state.discardPile.push(id);
    if (!alive().length) finish('win');
    return { ok: true };
  }

  // summons strike at the end of your turn — they reach any ring and flank the
  // guard (ignore mitigation). They go for your focus, else a caster, else anyone.
  function summonsPhase() {
    if (!state.hero.summons.length || !alive().length) return;
    const focus = byUid(state.hero.focusUid);
    for (const sk of state.hero.summons) {
      if (!alive().length) break;
      let t = (focus && focus.hp > 0) ? focus : alive().find((e) => e.role === 'caster') || alive()[0];
      applyHit(t, sk.attack, true); // flank the guard
      state.log.push(`Skeleton strikes ${t.name} for ${sk.attack}.`);
    }
    if (!alive().length) finish('win');
  }

  function endTurn() {
    if (state.over) return;
    summonsPhase();
    if (state.over) return;
    while (state.hand.length) state.discardPile.push(state.hand.pop());
    const exposed = state.hero.exposed;
    for (const e of state.enemies) {
      if (e.hp <= 0 || !e.intent) continue;
      if (e.intent.type === 'attack') {
        const absorbed = exposed ? 0 : Math.min(state.hero.block, e.attack); state.hero.block -= absorbed;
        const dmg = e.attack - absorbed; state.hero.life = Math.max(0, state.hero.life - dmg);
        state.log.push(`${e.name} hits you for ${dmg}${absorbed ? ` (${absorbed} blocked)` : ''}${exposed ? ' (exposed!)' : ''}.`);
      } else if (e.intent.type === 'mend') {
        const al = woundedAllies(e).sort((x, y) => (y.maxHp - y.hp) - (x.maxHp - x.hp));
        if (al.length) { const t = al[0]; const b = t.hp; t.hp = Math.min(t.maxHp, t.hp + e.intent.value); state.log.push(`${e.name} mends ${t.name} +${t.hp - b}.`); }
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
      hero: { ...state.hero, hard: { ...state.hero.hard }, summons: state.hero.summons.map((s) => ({ ...s })) },
      enemies: state.enemies.map((e) => ({ ...e, ring: ringOf(e), guarded: isGuarded(e), guardianCount: livingGuardians(e).length })),
      hand: state.hand.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })),
      drawCount: state.drawPile.length, discardCount: state.discardPile.length,
      deckSkills: [...new Set([...state.drawPile, ...state.hand, ...state.discardPile])],
      turn: state.turn, over: state.over, result: state.result, log: state.log.slice(),
    };
  }

  startTurn();
  return { playCard, endTurn, setFocus, spendSkillPoint, addPlusSkills, getState };
}
