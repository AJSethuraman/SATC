// Run orchestration for the ABILITIES model. You start NAKED (a weapon that
// grants one skill + a basic Guard), descend a blind branching map, fight
// SURROUNDED packs, and SCALE via XP -> levels -> skill points (spend in the
// class skill tree) + loot. Life carries between fights; permadeath ends the run.

import { CLASSES, ITEMS, SLOTS, WEAPON_DROPS, ELITE_AFFIXES, BOSS_PACK, SKILLS, SUPERUNIQUES, SUPERUNIQUE_IDS } from './content.js';
import { makeRng } from './rng.js';
import { createCombat, skillEffect } from './combat.js';
import { makeMap, nextChoices, NODE_TYPES } from './map.js';
import { rollItem } from './loot.js';

const xpForLevel = (lvl) => 6 + lvl * 4;

// Stats scale with LEVEL (Life/Mana growth) + gear passive mods.
export function deriveStats(cls, equipment, level, bonus = {}) {
  const stats = { maxLife: cls.maxLife + (level - 1) * 5, maxMana: cls.maxMana + (level - 1),
    manaRegen: (cls.manaRegen || 4) + Math.floor((level - 1) / 4), startBlock: cls.startBlock || 0,
    accuracy: (cls.acc || 6) + (level - 1), evade: cls.eva || 0, plusSkills: 0 };
  const add = (m) => { for (const [k, v] of Object.entries(m)) stats[k] = (stats[k] || 0) + v; };
  for (const s of SLOTS) { const it = equipment[s]; if (it && it.passive) add(it.passive); }
  add(bonus);
  return stats;
}

// Your abilities = a universal Guard + the skill your weapon grants + everything
// you've LEARNED in the tree (skillHard[id] > 0).
export function deriveAbilities(equipment, skillHard) {
  const list = ['guard'];
  for (const s of SLOTS) { const it = equipment[s]; if (it && it.grants && it.grants.skill) list.push(it.grants.skill); }
  for (const id of Object.keys(skillHard)) if (skillHard[id] > 0) list.push(id);
  return [...new Set(list)];
}

export function createGame(seed = 'bloodrune', opts = {}) {
  const rng = makeRng(seed);
  const cls = CLASSES[opts.classId || 'barbarian'];
  const run = {
    seed, difficulty: opts.difficulty || 'Normal', className: cls.name, glyph: cls.glyph,
    equipment: emptyEquipment(), bag: [],
    skillHard: {}, skillPoints: 0, level: 1, xp: 0,
    map: makeMap({ length: 9 }), choices: null, node: null,
    pendingLoot: [], lastResult: null, gained: null, life: 0, phase: 'prep',
  };
  run.equipment.weapon = ITEMS[cls.startWeapon];
  run.life = statsNow().maxLife;
  let combat = null;

  function emptyEquipment() { const e = {}; for (const s of SLOTS) e[s] = null; return e; }
  function statsNow() { return deriveStats(cls, run.equipment, run.level); }
  function abilitiesNow() { return deriveAbilities(run.equipment, run.skillHard); }
  function weaponNow() { const w = run.equipment.weapon; return w ? { dmg: w.dmg, wtype: w.wtype } : null; }
  function heroForFight() { const s = statsNow(); return { name: cls.name, glyph: cls.glyph, maxLife: s.maxLife, life: run.life,
    maxMana: s.maxMana, manaRegen: s.manaRegen, startBlock: s.startBlock, plusSkills: s.plusSkills,
    accuracy: s.accuracy, evade: s.evade, weapon: weaponNow(), hard: { ...run.skillHard }, abilities: abilitiesNow() }; }

  // ---- gear ----
  function slotFor(it) { if (it.slot === 'ring') return run.equipment.ring1 ? (run.equipment.ring2 ? 'ring1' : 'ring2') : 'ring1'; return it.slot; }
  function equipFromBag(id) { const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false };
    const it = run.bag[i]; const slot = slotFor(it); run.bag.splice(i, 1); if (run.equipment[slot]) run.bag.push(run.equipment[slot]); run.equipment[slot] = it; clampLife(); return { ok: true }; }
  function unequip(slot) { const it = run.equipment[slot]; if (!it) return { ok: false }; if (slot === 'weapon') return { ok: false, reason: 'need a weapon' }; run.bag.push(it); run.equipment[slot] = null; clampLife(); return { ok: true }; }
  function clampLife() { run.life = Math.min(run.life, statsNow().maxLife); }

  // ---- skill tree (D2-style gates: tier level-req, prerequisites, per-point gate) ----
  function hasPoint(id) { return (run.skillHard[id] || 0) > 0 || (run.equipment.weapon && run.equipment.weapon.grants && run.equipment.weapon.grants.skill === id); }
  function skillGate(id) {
    const s = SKILLS[id]; if (!s) return { ok: false, reason: 'unknown' };
    if (!cls.tree.includes(id) && id !== 'guard') return { ok: false, reason: 'not in your tree' };
    const cur = run.skillHard[id] || 0; const need = (s.req || 1) + cur; // point (cur+1) needs level req + cur
    if (run.level < need) return { ok: false, reason: `Lv ${need}`, needLevel: need };
    const missing = (s.pre || []).filter((p) => !hasPoint(p));
    if (missing.length) return { ok: false, reason: `needs ${missing.map((p) => skName(p)).join(', ')}`, missing };
    return { ok: true };
  }
  function investSkill(id) { if (run.skillPoints <= 0) return { ok: false, reason: 'no points' };
    const gate = skillGate(id); if (!gate.ok) return gate;
    run.skillPoints -= 1; run.skillHard[id] = (run.skillHard[id] || 0) + 1; return { ok: true }; }

  // ---- map / nodes ----
  function beginDescent() { run.choices = nextChoices(rng, run.map); run.phase = 'map'; }
  function rint(lo, hi) { return lo + rng.int(hi - lo + 1); }

  // size is the TOTAL pack (a support caster + its guard + an archer are counted
  // within it, not stacked on top) — a surround you chew through over a few turns,
  // not a wall that deletes you now that AoE only catches a couple foes at a time.
  function genEncounter(depth) {
    const pack = []; const size = Math.min(4 + Math.floor(depth / 1.5), 8);
    if (depth >= 2 && rng.next() < 0.65) { pack.push({ id: 'shaman' }); if (depth >= 3) pack.push({ id: 'guardian', guards: 0 }); }
    if (depth >= 3 && rng.next() < 0.45) pack.push({ id: 'archer' });
    while (pack.length < size) { const r = rng.next(); pack.push({ id: r < 0.6 ? 'fallen' : r < 0.82 ? 'goatman' : 'zombie' }); }
    return pack;
  }
  function genSuperUnique(depth) {
    const sid = rng.pick(SUPERUNIQUE_IDS); const su = SUPERUNIQUES[sid];
    const pack = [{ sid }];
    for (const m of su.minions) pack.push({ id: m });
    if (depth >= 5) pack.push({ id: su.minions[0] }); // deeper terrors bring an extra thrall
    return pack;
  }
  function genElite(depth) {
    const pack = genEncounter(Math.max(1, depth - 1));
    const keys = Object.keys(ELITE_AFFIXES); const n = 1 + rng.int(2); const affixes = [];
    while (affixes.length < n) { const a = rng.pick(keys); if (!affixes.includes(a)) affixes.push(a); }
    pack.push({ id: rng.pick(['goatman', 'zombie']), affixes });
    return pack;
  }

  function chooseDirection(i) { if (run.phase !== 'map' || !run.choices || !run.choices[i]) return { ok: false };
    const node = run.choices[i]; run.node = node; const depth = run.map.step + 1;
    if (node.type === 'combat') return startFight(genEncounter(depth));
    if (node.type === 'superunique') return startFight(genSuperUnique(depth));
    if (node.type === 'elite') return startFight(genElite(depth));
    if (node.type === 'boss') return startFight(BOSS_PACK.map((e) => ({ ...e })));
    if (node.type === 'treasure') { grantLoot(2, 15); run.lastResult = 'treasure'; run.gained = null; run.phase = 'reward'; advance(); return { ok: true }; }
    if (node.type === 'camp') { const s = statsNow(); run.life = Math.min(s.maxLife, run.life + Math.round(s.maxLife * 0.4)); run.skillPoints += 1; run.gained = { levels: 0, points: 1, heal: true }; run.lastResult = 'camp'; run.pendingLoot = []; run.phase = 'reward'; advance(); return { ok: true }; }
    return { ok: false };
  }
  function startFight(pack) { combat = createCombat({ hero: heroForFight(), pack, rng }); run.phase = 'combat'; return { ok: true }; }
  function advance() { run.map.step += 1; run.choices = nextChoices(rng, run.map); }

  function resolveCombat() {
    const s = combat.getState(); if (!s.over) return run.phase;
    run.life = s.hero.life;
    if (s.result === 'lose') { run.phase = 'dead'; return run.phase; }
    const boss = run.node && run.node.type === 'boss';
    if (s.result === 'win') {
      const beforeLvl = run.level; run.xp += s.xpEarned;
      while (run.xp >= xpForLevel(run.level)) { run.xp -= xpForLevel(run.level); run.level += 1; run.skillPoints += 1; }
      run.life = Math.min(statsNow().maxLife, run.life); // level-up may raise max; keep current
      const elite = run.node && run.node.type === 'elite';
      const su = run.node && run.node.type === 'superunique';
      grantLoot(su ? 3 : elite ? 2 : boss ? 3 : 1, su ? 30 : elite ? 20 : boss ? 45 : 5);
      run.gained = { levels: run.level - beforeLvl, points: run.level - beforeLvl };
      run.lastResult = 'win';
      if (boss) { run.phase = 'victory'; return run.phase; }
      advance();
    } else { run.lastResult = 'fled'; run.pendingLoot = []; run.gained = null; advance(); }
    run.phase = 'reward'; return run.phase;
  }
  function flee() { if (!combat) return; combat.flee(); return resolveCombat(); }

  function grantLoot(count, mf) {
    run.pendingLoot = [];
    for (let n = 0; n < count; n++) {
      let item; if (rng.next() < 0.28) { item = { ...ITEMS[rng.pick(WEAPON_DROPS)] }; item = { ...item, id: item.id + '_' + Math.floor(rng.next() * 1e6) }; }
      else item = rollItem(rng, { magicFind: mf });
      run.bag.push(item); run.pendingLoot.push(item);
    }
  }
  function continueFromReward() { run.phase = 'map'; }

  function getRun() {
    const s = statsNow();
    const tree = ['guard', ...cls.tree.filter((t) => t !== 'guard')].map((id) => { const sk = SKILLS[id] || {}; const gate = skillGate(id);
      return { id, level: 1 + (run.skillHard[id] || 0), req: sk.req || 1, pre: sk.pre || [],
        learned: hasPoint(id) || id === 'guard',
        canInvest: run.skillPoints > 0 && gate.ok, gateReason: gate.ok ? null : gate.reason,
        eff: skillEffect({ hard: run.skillHard, plusSkills: s.plusSkills, weapon: weaponNow() }, id), name: skName(id) }; });
    return { seed: run.seed, difficulty: run.difficulty, className: run.className, glyph: run.glyph, phase: run.phase,
      stats: s, life: run.life, maxLife: s.maxLife, level: run.level, xp: run.xp, xpToNext: xpForLevel(run.level), skillPoints: run.skillPoints,
      abilities: abilitiesNow(), tree,
      equipment: Object.fromEntries(SLOTS.map((sl) => [sl, run.equipment[sl] ? { ...run.equipment[sl] } : null])),
      bag: run.bag.map((i) => ({ ...i })), pendingLoot: run.pendingLoot.map((i) => ({ ...i })), lastResult: run.lastResult, gained: run.gained,
      choices: run.choices ? run.choices.map((c) => ({ type: c.type, ...NODE_TYPES[c.type] })) : null,
      node: run.node ? { type: run.node.type, ...NODE_TYPES[run.node.type] } : null, mapStep: run.map.step, mapLength: run.map.length };
  }
  function skName(id) { return SKILLS[id] ? SKILLS[id].name : id; }

  return { beginDescent, chooseDirection, resolveCombat, flee, equipFromBag, unequip, investSkill, continueFromReward,
    getRun, getCombat: () => combat, deriveStats: () => statsNow(), deriveAbilities: () => abilitiesNow() };
}
