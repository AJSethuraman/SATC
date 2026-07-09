// Run orchestration — SURVIVORS model. You drop into ONE big arena and survive
// escalating waves; MOVEMENT is the only control and your skills auto-fire. You
// start NAKED (a weapon that grants one skill + a universal Guard) and SCALE the
// same way as ever: XP -> levels -> skill points (spent in the class skill tree)
// and LOOT that monsters drop for you to grab. A boss lands at bossTime — kill it
// to clear the tier. Permadeath ends the run. The moment-to-moment sim is in
// engine/arena.js (survival mode); this file owns the meta/progression.

import { CLASSES, ITEMS, SLOTS, WEAPON_DROPS, SKILLS, ACT1 } from './content.js';
import { makeRng } from './rng.js';
import { skillEffect } from './combat.js';
import { createArena } from './arena.js';
import { rollItem } from './loot.js';

// Quadratic curve: fast to ~15 (core skills online), then each point is precious —
// so the swarm's huge kill-count can't rocket you to level 60 and max the whole tree.
// You land ~level 25 by Andariel; the tree stays a real CHOICE.
const xpForLevel = (lvl) => 10 + 3 * lvl * lvl;

// Stats scale with LEVEL (Life/Mana growth) + gear passive mods.
export function deriveStats(cls, equipment, level, bonus = {}) {
  const stats = { maxLife: cls.maxLife + (level - 1) * 5, maxMana: cls.maxMana + (level - 1),
    manaRegen: (cls.manaRegen || 4) + Math.floor((level - 1) / 4), startBlock: cls.startBlock || 0,
    accuracy: (cls.acc || 6) + (level - 1), evade: cls.eva || 0, actions: cls.actions || 3, plusSkills: 0,
    fcr: 0, ias: 0, penetration: 0 }; // Faster Cast Rate (spells) / Increased Attack Speed (physical) — from gear
  const add = (m) => { for (const [k, v] of Object.entries(m)) stats[k] = (stats[k] || 0) + v; };
  for (const s of SLOTS) { const it = equipment[s]; if (it && it.passive) add(it.passive); }
  add(bonus);
  return stats;
}

// Your abilities = a universal Guard + the skill your weapon grants + everything learned.
export function deriveAbilities(equipment, skillHard) {
  const list = ['attack', 'guard'];
  for (const s of SLOTS) { const it = equipment[s]; if (it && it.grants && it.grants.skill) list.push(it.grants.skill); }
  for (const id of Object.keys(skillHard)) if (skillHard[id] > 0) list.push(id);
  return [...new Set(list)].filter((id) => !(SKILLS[id] && SKILLS[id].type === 'passive')); // passives don't auto-fire
}


export function createGame(seed = 'bloodrune', opts = {}) {
  const rng = makeRng(seed);
  const cls = CLASSES[opts.classId || 'barbarian'];
  const run = {
    seed, difficulty: opts.difficulty || 'Normal', className: cls.name, glyph: cls.glyph,
    equipment: emptyEquipment(), bag: [],
    skillHard: {}, skillPoints: 0, level: 1, xp: 0,
    lastResult: null, gained: null, life: 0, mana: 0, potions: { life: 3, mana: 3 }, gold: 0, phase: 'prep',
  };
  run.equipment.weapon = ITEMS[cls.startWeapon];
  run.life = statsNow().maxLife;
  run.mana = statsNow().maxMana;
  const POTION_CAP = 6, BAG_CAP = 12, POTION_PRICE = 12;
  const itemValue = (it) => it.grants ? 12 : ({ common: 2, magic: 8, rare: 20, unique: 60 }[it.rarity] || 3);
  let combat = null, lastXp = 0;

  function emptyEquipment() { const e = {}; for (const s of SLOTS) e[s] = null; return e; }
  function statsNow() { const st = deriveStats(cls, run.equipment, run.level); st.manaRegen += (run.skillHard.warmth || 0); return st; } // Warmth: +Mana regen
  function abilitiesNow() { return deriveAbilities(run.equipment, run.skillHard); }
  function weaponNow() { const w = run.equipment.weapon; return w ? { dmg: w.dmg, wtype: w.wtype } : null; }
  function heroForFight() { const s = statsNow(); return { name: cls.name, glyph: cls.glyph, maxLife: s.maxLife, life: run.life,
    maxMana: s.maxMana, mana: Math.min(run.mana, s.maxMana), manaRegen: s.manaRegen, startBlock: s.startBlock, plusSkills: s.plusSkills,
    accuracy: s.accuracy, evade: s.evade, actions: s.actions, fcr: s.fcr, ias: s.ias, penetration: s.penetration, weapon: weaponNow(), hard: { ...run.skillHard }, abilities: abilitiesNow() }; }

  // ---- gear ----
  function slotFor(it) { if (it.slot === 'ring') return run.equipment.ring1 ? (run.equipment.ring2 ? 'ring1' : 'ring2') : 'ring1'; return it.slot; }
  function equipFromBag(id) { const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false };
    const it = run.bag[i]; const slot = slotFor(it); run.bag.splice(i, 1); if (run.equipment[slot]) run.bag.push(run.equipment[slot]); run.equipment[slot] = it; clampLife(); pushHeroStats(); return { ok: true }; }
  function unequip(slot) { const it = run.equipment[slot]; if (!it) return { ok: false }; if (slot === 'weapon') return { ok: false, reason: 'need a weapon' }; run.bag.push(it); run.equipment[slot] = null; clampLife(); pushHeroStats(); return { ok: true }; }
  function clampLife() { const s = statsNow(); run.life = Math.min(run.life, s.maxLife); run.mana = Math.min(run.mana, s.maxMana); }

  // Auto-equip a dropped item ONLY when it's a clear upgrade — fill an empty slot,
  // or beat the score of what's there. NEVER auto-swap the weapon TYPE (that would
  // brick a build); a wrong-type weapon goes to the bag for you to decide.
  const weaponScore = (w) => (w && w.dmg ? (w.dmg[0] + w.dmg[1]) / 2 : 0) + ((w && w.passive && w.passive.plusSkills) || 0) * 4 + (w && w.grants ? 2 : 0);
  const armorScore = (it) => { const p = it.passive || {}; return (p.maxLife || 0) + (p.maxMana || 0) * 3 + (p.plusSkills || 0) * 10 + (p.startBlock || 0) * 3 + (p.accuracy || 0) * 2 + (p.evade || 0) * 2; };
  function autoEquipIfUpgrade(it) {
    if (it.slot === 'weapon') { const cur = run.equipment.weapon;
      if (cur && cur.wtype !== it.wtype) return false;               // never auto-swap weapon type
      if (cur && weaponScore(cur) >= weaponScore(it)) return false;
      if (cur && run.bag.length < BAG_CAP) run.bag.push(cur); run.equipment.weapon = it; clampLife(); return true; }
    const slot = slotFor(it); const cur = run.equipment[slot];
    if (!cur) { run.equipment[slot] = it; clampLife(); return true; } // fill an empty slot
    if (armorScore(it) > armorScore(cur)) { if (run.bag.length < BAG_CAP) run.bag.push(cur); run.equipment[slot] = it; clampLife(); return true; }
    return false;
  }

  // ---- potions (the belt persists across the run) ----
  function quaff(type) { if (!combat || (type !== 'life' && type !== 'mana')) return { ok: false };
    if (run.potions[type] <= 0) return { ok: false, reason: 'none left' };
    const s = statsNow(); const amt = type === 'life' ? Math.round(s.maxLife * 0.4) : Math.round(s.maxMana * 0.5);
    const r = combat.quaff(type, amt); if (!r.ok) return r; run.potions[type] -= 1;
    run.life = combat.getState().hero.life; run.mana = combat.getState().hero.mana; return { ok: true }; }
  function addPotions(life, mana) { run.potions.life = Math.min(POTION_CAP, run.potions.life + life); run.potions.mana = Math.min(POTION_CAP, run.potions.mana + mana); }

  // ---- economy: sell/drop bag items ----
  function sellFromBag(id) { const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false };
    run.gold += itemValue(run.bag[i]); run.bag.splice(i, 1); return { ok: true, gold: run.gold }; }
  function buyPotion(type) { if (type !== 'life' && type !== 'mana') return { ok: false };
    if (run.gold < POTION_PRICE) return { ok: false, reason: 'not enough gold' };
    if (run.potions[type] >= POTION_CAP) return { ok: false, reason: 'belt full' };
    run.gold -= POTION_PRICE; run.potions[type] += 1; return { ok: true }; }
  function dropFromBag(id) { const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false }; run.bag.splice(i, 1); return { ok: true }; }

  // ---- skill tree (D2-style gates: tier level-req, prerequisites, per-point gate) ----
  function hasPoint(id) { return (run.skillHard[id] || 0) > 0 || (run.equipment.weapon && run.equipment.weapon.grants && run.equipment.weapon.grants.skill === id); }
  function skillGate(id) {
    const s = SKILLS[id]; if (!s) return { ok: false, reason: 'unknown' };
    if (!cls.tree.includes(id) && id !== 'guard') return { ok: false, reason: 'not in your tree' };
    const cur = run.skillHard[id] || 0; const need = (s.req || 1) + cur;
    if (run.level < need) return { ok: false, reason: `Lv ${need}`, needLevel: need };
    const missing = (s.pre || []).filter((p) => !hasPoint(p));
    if (missing.length) return { ok: false, reason: `needs ${missing.map((p) => skName(p)).join(', ')}`, missing };
    return { ok: true };
  }
  function investSkill(id) { if (run.skillPoints <= 0) return { ok: false, reason: 'no points' };
    const gate = skillGate(id); if (!gate.ok) return gate;
    run.skillPoints -= 1; run.skillHard[id] = (run.skillHard[id] || 0) + 1; pushHeroStats(); return { ok: true }; }

  // ---- the Act 1 gauntlet run ----
  let lastCleared = 0;
  function startRun() {
    run.life = statsNow().maxLife; run.mana = statsNow().maxMana; lastXp = 0; lastCleared = 0;
    combat = createArena({ hero: heroForFight(), rng, survival: { areas: ACT1, tier: run.difficulty, rollLoot: rollGroundItem } });
    run.phase = 'arena'; return { ok: true };
  }
  const beginDescent = startRun; // (the prep screen's "descend" button)

  // What a monster drops — usually armor/jewelry (useful to any class), sometimes a
  // weapon that MATCHES your type (a Sorceress won't be buried in Great Axes).
  // Magic-find scales with the kill's tier (elite/unique/boss).
  const WEAP_BY_TYPE = { melee: 'great_axe', ranged: 'war_bow', focus: 'bone_staff' };
  function rollGroundItem(mf) {
    if (rng.next() < 0.06) { const wt = (run.equipment.weapon && run.equipment.weapon.wtype) || 'melee';
      const w = { ...ITEMS[WEAP_BY_TYPE[wt] || rng.pick(WEAPON_DROPS)] }; return { ...w, id: w.id + '_' + Math.floor(rng.next() * 1e6) }; }
    return rollItem(rng, { tier: run.difficulty, magicFind: 4 + mf * 6 });
  }

  // Push live progression (level-ups, gear) into the in-flight survival hero.
  function pushHeroStats() { if (!combat) return; const s = statsNow();
    combat.setHero({ maxLife: s.maxLife, maxMana: s.maxMana, accuracy: s.accuracy, evade: s.evade,
      manaRegen: s.manaRegen, plusSkills: s.plusSkills, fcr: s.fcr, ias: s.ias, penetration: s.penetration, hard: { ...run.skillHard }, weapon: weaponNow(), abilities: abilitiesNow() }); }

  // Called each frame by the UI while surviving: fold the engine's earned XP into
  // levels/points, and its collected drops into the bag (auto-equipping upgrades).
  function syncArena() {
    if (!combat) return { leveled: 0, loot: [], equipped: [], cleared: 0 };
    const s = combat.getState();
    let leveled = 0; const delta = s.xpEarned - lastXp; lastXp = s.xpEarned;
    if (delta > 0) { run.xp += delta;
      while (run.xp >= xpForLevel(run.level)) { run.xp -= xpForLevel(run.level); run.level += 1; run.skillPoints += 1; leveled += 1; } }
    const got = combat.takeCollected(); const equipped = [];
    for (const it of got) { if (autoEquipIfUpgrade(it)) equipped.push(it); else if (run.bag.length < BAG_CAP) run.bag.push(it); }
    // clearing an area completes its QUEST — reward skill points, a heal, and a restock
    let cleared = 0;
    if (s.areaCleared > lastCleared) { cleared = s.areaCleared - lastCleared; lastCleared = s.areaCleared;
      for (let k = 0; k < cleared; k++) { run.skillPoints += 2; combat.heal(Math.round(statsNow().maxLife * 0.5)); addPotions(1, 1); } }
    if (leveled || equipped.length) pushHeroStats();
    run.life = s.hero.life; run.mana = s.hero.mana;
    return { leveled, loot: got, equipped, cleared };
  }

  function resolveArena() { if (!combat) return run.phase; const s = combat.getState(); if (!s.over) return run.phase;
    run.life = s.hero.life; run.mana = s.hero.mana; run.lastResult = s.result;
    run.phase = s.result === 'win' ? 'victory' : 'dead'; return run.phase; }
  function flee() { if (!combat) return run.phase; combat.flee(); return resolveArena(); }

  function getRun() {
    const s = statsNow();
    const treeIds = cls.tabs ? cls.tree.slice() : ['guard', ...cls.tree.filter((t) => t !== 'guard')]; // Sorceress builds tabs, others prepend Guard
    const tree = treeIds.map((id) => { const sk = SKILLS[id] || {}; const gate = skillGate(id);
      return { id, level: 1 + (run.skillHard[id] || 0), req: sk.req || 1, pre: sk.pre || [], tab: sk.tab || null, passive: sk.type === 'passive',
        learned: hasPoint(id) || id === 'guard',
        canInvest: run.skillPoints > 0 && gate.ok, gateReason: gate.ok ? null : gate.reason,
        eff: skillEffect({ hard: run.skillHard, plusSkills: s.plusSkills, weapon: weaponNow() }, id), name: skName(id) }; });
    return { seed: run.seed, difficulty: run.difficulty, className: run.className, glyph: run.glyph, phase: run.phase,
      stats: s, life: run.life, maxLife: s.maxLife, mana: run.mana, maxMana: s.maxMana, potions: { ...run.potions },
      gold: run.gold, bagCap: BAG_CAP,
      level: run.level, xp: run.xp, xpToNext: xpForLevel(run.level), skillPoints: run.skillPoints,
      abilities: abilitiesNow(), tree, tabs: cls.tabs || null,
      equipment: Object.fromEntries(SLOTS.map((sl) => [sl, run.equipment[sl] ? { ...run.equipment[sl] } : null])),
      bag: run.bag.map((i) => ({ ...i })), lastResult: run.lastResult, gained: run.gained };
  }
  function skName(id) { return SKILLS[id] ? SKILLS[id].name : id; }

  return { beginDescent, startRun, syncArena, resolveArena, flee, equipFromBag, unequip, investSkill, quaff, sellFromBag, buyPotion, dropFromBag,
    getRun, getCombat: () => combat, deriveStats: () => statsNow(), deriveAbilities: () => abilitiesNow() };
}
