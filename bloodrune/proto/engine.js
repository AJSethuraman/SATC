// Bloodrune — SURROUNDED arena prototype, ABILITIES + RANGES model.
// No card draw: your skills (from gear + the skill tree) are ALWAYS available;
// you spend Mana on the ones you choose. The randomness lives where Diablo puts
// it — DAMAGE RANGES (Strike hits for 5-8) and (in the real game) the loot you
// hunt to fix your build's weaknesses. Combat is otherwise as before: you're
// surrounded by an inner ring (melee reach) and an outer ring (casters/archers)
// reachable only by ranged skills, a Charge (breakthrough -> Exposed), or
// Summons that strike past the guard. Skills SCALE by level. Pure engine, rng.

import { makeRng } from '../engine/rng.js';

export const GUARD_MITIGATION = 0.6;

// dmg: [min, max] base range; grow shifts both ends per level. block is fixed.
export const SKILLS = {
  strike: { id: 'strike', name: 'Strike', type: 'attack', target: 'single', reach: 0, cost: 2, scale: 'damage', dmg: [5, 8], grow: 2 },
  cleave: { id: 'cleave', name: 'Cleave', type: 'attack', target: 'aoe', reach: 0, cost: 3, scale: 'damage', dmg: [4, 7], grow: 2 },
  zeal: { id: 'zeal', name: 'Zeal', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'hits', dmg: [3, 5], hitCap: 5 },
  smite: { id: 'smite', name: 'Smite', type: 'attack', target: 'single', reach: 0, cost: 3, scale: 'damage', dmg: [8, 12], grow: 3 },
  shoot: { id: 'shoot', name: 'Arrow', type: 'attack', target: 'single', reach: 1, cost: 2, scale: 'damage', dmg: [4, 7], grow: 2 },
  charge: { id: 'charge', name: 'Charge', type: 'breakthrough', target: 'single', reach: 1, cost: 3, scale: 'damage', dmg: [6, 10], grow: 2 },
  guard: { id: 'guard', name: 'Guard', type: 'skill', cost: 2, scale: 'block', base: 7, grow: 2 },
  raise_skeleton: { id: 'raise_skeleton', name: 'Raise Skeleton', type: 'summon', cost: 3, scale: 'summons', dmg: [2, 4] },
};

export const ENEMIES = {
  fallen: { id: 'fallen', name: 'Fallen', hp: 8, attack: 3, glyph: '👺', role: 'grunt', ring: 0, xp: 3 },
  guardian: { id: 'guardian', name: 'Fallen Champion', hp: 15, attack: 4, glyph: '🛡️', role: 'guardian', ring: 0, xp: 6 },
  goatman: { id: 'goatman', name: 'Goatman', hp: 18, attack: 6, glyph: '🐐', role: 'grunt', ring: 0, xp: 7 },
  shaman: { id: 'shaman', name: 'Fallen Shaman', hp: 16, attack: 3, glyph: '🧙', role: 'caster', heal: 5, ring: 1, xp: 10 },
  archer: { id: 'archer', name: 'Dark Archer', hp: 9, attack: 5, glyph: '🏹', role: 'archer', ring: 1, xp: 6 },
};
const xpForLevel = (lvl) => 5 + lvl * 3;
const GUARDABLE = new Set(['caster', 'elite']);

export function skillLevel(hero, id) { return 1 + (hero.hard[id] || 0) + (hero.plusSkills || 0); }

export function skillEffect(hero, id) {
  const s = SKILLS[id]; const lvl = skillLevel(hero, id); const g = s.grow || 0;
  if (s.scale === 'damage') { const min = s.dmg[0] + g * (lvl - 1), max = s.dmg[1] + g * (lvl - 1);
    return { lvl, min, max, text: `Deal ${min}-${max}${s.target === 'aoe' ? ' to the inner ring' : ''}${s.reach ? ' (reaches outer)' : ''}.` }; }
  if (s.scale === 'hits') { const hits = Math.min(s.hitCap, 1 + lvl); return { lvl, hits, min: s.dmg[0], max: s.dmg[1], text: `Strike ${hits}× for ${s.dmg[0]}-${s.dmg[1]} (hits scale with level).` }; }
  if (s.scale === 'block') return { lvl, block: s.base + g * (lvl - 1), text: `Gain ${s.base + g * (lvl - 1)} Block.` };
  if (s.scale === 'summons') { const count = 1 + Math.floor((lvl - 1) / 2); const min = s.dmg[0] + (lvl - 1), max = s.dmg[1] + (lvl - 1);
    return { lvl, count, min, max, text: `Raise ${count} skeleton${count > 1 ? 's' : ''} (${min}-${max}). They strike your target each turn — even the outer ring, past the guard.` }; }
  return { lvl, text: '' };
}

export function createFight({ deck, hero, pack, seed = 'proto' } = {}) {
  const rng = makeRng(seed);
  const state = {
    hero: { life: hero.maxLife, maxLife: hero.maxLife, block: 0, mana: hero.maxMana, maxMana: hero.maxMana,
      plusSkills: hero.plusSkills || 0, hard: { ...(hero.hard || {}) }, exposed: false,
      skillPoints: hero.skillPoints || 0, summons: [], focusUid: null,
      level: 1, xp: 0, xpToNext: xpForLevel(1) },
    abilities: [...new Set(deck)], // your skills — always available (no draw)
    enemies: pack.map((e, i) => ({ uid: i, ...ENEMIES[e.id], hp: ENEMIES[e.id].hp, maxHp: ENEMIES[e.id].hp,
      guardsUid: e.guards != null ? e.guards : null, intent: null })),
    turn: 0, over: false, result: null, log: [],
  };

  const alive = () => state.enemies.filter((e) => e.hp > 0);
  const byUid = (uid) => state.enemies.find((e) => e.uid === uid);
  const ringOf = (e) => ENEMIES[e.id].ring || 0;
  const livingGuardians = (t) => alive().filter((g) => g.role === 'guardian' && g.guardsUid === t.uid);
  const isGuarded = (e) => GUARDABLE.has(e.role) && livingGuardians(e).length > 0;
  const roll = (min, max) => min + rng.int(max - min + 1);
  const woundedAllies = (self) => alive().filter((a) => a !== self && a.hp < a.maxHp);

  function telegraph() {
    for (const e of state.enemies) {
      if (e.hp <= 0) { e.intent = null; continue; }
      if (e.role === 'caster' && woundedAllies(e).length > 0) e.intent = { type: 'mend', value: e.heal };
      else e.intent = { type: 'attack', value: e.attack };
    }
  }
  function startTurn() { state.turn += 1; state.hero.block = 0; state.hero.mana = state.hero.maxMana; state.hero.exposed = false; telegraph(); state.log.push(`— Turn ${state.turn} —`); }

  function hurt(e, dmg) {
    e.hp = Math.max(0, e.hp - dmg);
    if (e.hp === 0) {
      e.intent = null; state.log.push(`${e.name} dies.`);
      const h = state.hero; h.xp += ENEMIES[e.id].xp || 0; // kills grant XP -> skill points
      while (h.xp >= h.xpToNext) { h.xp -= h.xpToNext; h.level += 1; h.skillPoints += 1; h.xpToNext = xpForLevel(h.level); state.log.push(`You grow stronger — Level ${h.level}! (+1 skill point)`); }
    }
  }
  function applyHit(e, dmg, pierceGuard) {
    let d = dmg;
    if (!pierceGuard && isGuarded(e)) { d = Math.max(1, Math.round(dmg * (1 - GUARD_MITIGATION))); state.log.push(`${e.name} is guarded — only ${d} gets through.`); }
    hurt(e, d);
  }
  function setFocus(uid) { state.hero.focusUid = uid; }
  function pickTarget(card) {
    const reach = card.reach || 0; const f = byUid(state.hero.focusUid);
    if (f && f.hp > 0 && ringOf(f) <= reach) return f;
    return alive().filter((e) => ringOf(e) <= reach)[0] || null;
  }

  // abilityIndex indexes state.abilities — skills are always available, only Mana-gated.
  function playCard(abilityIndex, focusUid) {
    if (state.over) return { ok: false };
    if (focusUid != null) state.hero.focusUid = focusUid;
    const id = state.abilities[abilityIndex]; if (id == null) return { ok: false };
    const s = SKILLS[id]; const eff = skillEffect(state.hero, id);
    if (s.cost > state.hero.mana) return { ok: false, reason: 'not enough Mana' };
    state.hero.mana -= s.cost;

    if (s.type === 'skill') { if (eff.block) state.hero.block += eff.block; }
    else if (s.type === 'summon') { for (let i = 0; i < eff.count; i++) state.hero.summons.push({ glyph: '💀', min: eff.min, max: eff.max }); state.log.push(`Raise ${eff.count} skeleton(s).`); }
    else if (s.target === 'aoe') { for (const e of alive().filter((x) => ringOf(x) <= (s.reach || 0))) applyHit(e, roll(eff.min, eff.max), false); }
    else {
      const t = pickTarget(s); if (!t) { state.hero.mana += s.cost; return { ok: false, reason: 'no target in reach' }; }
      if (s.type === 'breakthrough') { applyHit(t, roll(eff.min, eff.max), true); state.hero.exposed = true; state.log.push('You break through — and drop your guard.'); }
      else if (s.scale === 'hits') { for (let h = 0; h < eff.hits && t.hp > 0; h++) applyHit(t, roll(eff.min, eff.max), false); }
      else applyHit(t, roll(eff.min, eff.max), false);
    }
    state.log.push(`Cast ${s.name}.`);
    if (!alive().length) finish('win');
    return { ok: true };
  }

  function summonsPhase() {
    if (!state.hero.summons.length || !alive().length) return;
    const focus = byUid(state.hero.focusUid);
    for (const sk of state.hero.summons) {
      if (!alive().length) break;
      const t = (focus && focus.hp > 0) ? focus : alive().find((e) => e.role === 'caster') || alive()[0];
      const d = roll(sk.min, sk.max); applyHit(t, d, true);
      state.log.push(`Skeleton strikes ${t.name} for ${d}.`);
    }
    if (!alive().length) finish('win');
  }

  function endTurn() {
    if (state.over) return;
    summonsPhase(); if (state.over) return;
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
    if (learn && !state.abilities.includes(id)) state.abilities.push(id);
    state.log.push(`${learn ? 'Learn' : 'Improve'} ${SKILLS[id].name} (Lv ${skillLevel(state.hero, id)}).`);
    return { ok: true };
  }
  function addPlusSkills(n) { state.hero.plusSkills = Math.max(0, state.hero.plusSkills + n); }
  function finish(r) { state.over = true; state.result = r; state.log.push(r === 'win' ? 'The ring breaks.' : 'You have died.'); }

  function getState() {
    return {
      hero: { ...state.hero, hard: { ...state.hero.hard }, summons: state.hero.summons.map((s) => ({ ...s })) },
      enemies: state.enemies.map((e) => ({ ...e, ring: ringOf(e), guarded: isGuarded(e), guardianCount: livingGuardians(e).length })),
      abilities: state.abilities.map((id) => ({ id, ...SKILLS[id], eff: skillEffect(state.hero, id) })),
      knownSkills: [...state.abilities],
      turn: state.turn, over: state.over, result: state.result, log: state.log.slice(),
    };
  }

  startTurn();
  return { playCard, endTurn, setFocus, spendSkillPoint, addPlusSkills, getState };
}
