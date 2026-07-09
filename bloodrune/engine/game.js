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
import { rollItem, itemScore } from './loot.js';

// Quadratic curve: fast to ~15 (core skills online), then each point is precious —
// so the swarm's huge kill-count can't rocket you to level 60 and max the whole tree.
// You land ~level 25 by Andariel; the tree stays a real CHOICE.
const xpForLevel = (lvl) => 10 + 3 * lvl * lvl;

// Attribute points earned per level (D2 gives 5). Spent on Str/Dex/Vit/Energy.
const ATTR_PER_LEVEL = 5;

// Each Vitality point adds Life; each Energy point adds Mana (and a trickle of
// regen). Str/Dex are mostly equip gates but toss in a small Block/Accuracy nudge.
export const VIT_LIFE = 4, ENERGY_MANA = 2;

// Stats scale with LEVEL (Life/Mana growth) + ATTRIBUTES (Vit/Energy) + gear mods.
// `attr` = the Str/Dex/Vit/Energy the run has invested (defaults to the class base
// so callers that don't track a run still get sane numbers).
export function deriveStats(cls, equipment, level, attr = null, bonus = {}) {
  const a = attr || cls.attr || { str: 0, dex: 0, vit: 0, energy: 0 };
  // sum every gear passive (and the caller's bonus) into one mod bag first
  const gear = {};
  const add = (m) => { for (const [k, v] of Object.entries(m)) gear[k] = (gear[k] || 0) + v; };
  for (const s of SLOTS) { const it = equipment[s]; if (it && it.passive) add(it.passive); }
  add(bonus);
  // total attributes = invested + whatever gear grants (so +Vit/+Energy gear counts)
  const str = (a.str || 0) + (gear.str || 0), dex = (a.dex || 0) + (gear.dex || 0);
  const vit = (a.vit || 0) + (gear.vit || 0), energy = (a.energy || 0) + (gear.energy || 0);
  return {
    maxLife: cls.maxLife + (level - 1) * 5 + vit * VIT_LIFE + (gear.maxLife || 0),
    maxMana: cls.maxMana + (level - 1) + energy * ENERGY_MANA + (gear.maxMana || 0),
    manaRegen: (cls.manaRegen || 4) + Math.floor((level - 1) / 4) + Math.floor(energy / 12) + (gear.manaRegen || 0),
    startBlock: (cls.startBlock || 0) + Math.floor(str / 30) + (gear.startBlock || 0),
    accuracy: (cls.acc || 6) + (level - 1) + Math.floor(dex / 6) + (gear.accuracy || 0),
    evade: (cls.eva || 0) + (gear.evade || 0), actions: cls.actions || 3,
    plusSkills: gear.plusSkills || 0, fcr: gear.fcr || 0, ias: gear.ias || 0, penetration: gear.penetration || 0,
    str, dex, vit, energy,
  };
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
    // Attributes reset every run: start at the class base, earn ~5 to spend per level.
    attr: { ...(cls.attr || { str: 0, dex: 0, vit: 0, energy: 0 }) }, attrPoints: 0,
    // Town / checkpoint loop: an ACT is an ordered list of quests (ACT1 areas). You
    // clear one quest per field descent, then return to TOWN to bank/turn-in/respec
    // before the next. `stash` PERSISTS across runs (injected by the UI from storage);
    // `bag` is the at-risk run inventory — forfeited on death, safe once banked.
    act: 1, questIdx: 0, quests: ACT1.map((a) => ({ name: a.name, quest: a.quest, questText: a.questText, done: false })),
    stash: (opts.stash || []).map((it) => ({ ...it })), respecUsedThisAct: false,
    lastResult: null, gained: null, life: 0, mana: 0, potions: { life: 3, mana: 3 }, gold: 0, phase: 'town',
  };
  run.equipment.weapon = ITEMS[cls.startWeapon];
  const STASH_CAP = 40, POTION_CAP = 6, BAG_CAP = 12, POTION_PRICE = 12;
  const itemValue = (it) => it.grants ? 12 : ({ common: 2, magic: 8, rare: 20, unique: 60 }[it.rarity] || 3);
  let combat = null, lastXp = 0, equipSeq = 0;
  if (opts.loadout) applyLoadout(opts.loadout); // start equipped with chosen stash gear
  run.life = statsNow().maxLife;
  run.mana = statsNow().maxMana;

  function emptyEquipment() { const e = {}; for (const s of SLOTS) e[s] = null; return e; }
  function statsNow() { const st = deriveStats(cls, run.equipment, run.level, run.attr); st.manaRegen += (run.skillHard.warmth || 0); return st; } // Warmth: +Mana regen
  function abilitiesNow() { return deriveAbilities(run.equipment, run.skillHard); }
  function weaponNow() { const w = run.equipment.weapon; return w ? { dmg: w.dmg, wtype: w.wtype } : null; }
  function heroForFight() { const s = statsNow(); return { name: cls.name, glyph: cls.glyph, maxLife: s.maxLife, life: run.life,
    maxMana: s.maxMana, mana: Math.min(run.mana, s.maxMana), manaRegen: s.manaRegen, startBlock: s.startBlock, plusSkills: s.plusSkills,
    accuracy: s.accuracy, evade: s.evade, actions: s.actions, fcr: s.fcr, ias: s.ias, penetration: s.penetration, weapon: weaponNow(), hard: { ...run.skillHard }, abilities: abilitiesNow() }; }

  // ---- gear ----
  function slotFor(it) { if (it.slot === 'ring') return run.equipment.ring1 ? (run.equipment.ring2 ? 'ring1' : 'ring2') : 'ring1'; return it.slot; }
  // Equip GATE: an item's Str/Dex/level requirement is checked against your INVESTED
  // attributes (gear +stats don't count toward wearing OTHER gear) — greed is punished.
  function canEquip(it) {
    const r = (it && it.req) || {};
    if ((r.str || 0) > run.attr.str) return { ok: false, reason: `Req ${r.str} Str` };
    if ((r.dex || 0) > run.attr.dex) return { ok: false, reason: `Req ${r.dex} Dex` };
    if ((r.level || 0) > run.level) return { ok: false, reason: `Req Lv ${r.level}` };
    return { ok: true };
  }
  function equipFromBag(id) { const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false };
    const it = run.bag[i]; const gate = canEquip(it); if (!gate.ok) return gate;
    const slot = slotFor(it); run.bag.splice(i, 1); if (run.equipment[slot]) run.bag.push(run.equipment[slot]); run.equipment[slot] = it; clampLife(); pushHeroStats(); return { ok: true }; }
  function unequip(slot) { const it = run.equipment[slot]; if (!it) return { ok: false }; if (slot === 'weapon') return { ok: false, reason: 'need a weapon' }; run.bag.push(it); run.equipment[slot] = null; clampLife(); pushHeroStats(); return { ok: true }; }
  function clampLife() { const s = statsNow(); run.life = Math.min(run.life, s.maxLife); run.mana = Math.min(run.mana, s.maxMana); }

  // Auto-equip a dropped item ONLY when it's a clear upgrade — fill an empty slot,
  // or beat the score of what's there. NEVER auto-swap the weapon TYPE (that would
  // brick a build); a wrong-type weapon goes to the bag for you to decide.
  const weaponScore = (w) => (w && w.dmg ? (w.dmg[0] + w.dmg[1]) / 2 : 0) + ((w && w.passive && w.passive.plusSkills) || 0) * 4 + (w && w.grants ? 2 : 0);
  const armorScore = (it) => { const p = it.passive || {}; return (p.maxLife || 0) + (p.maxMana || 0) * 3 + (p.plusSkills || 0) * 10 + (p.startBlock || 0) * 3 + (p.accuracy || 0) * 2 + (p.evade || 0) * 2; };
  function autoEquipIfUpgrade(it) {
    if (!canEquip(it).ok) return false;                               // can't wear it -> stays in the bag
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
  // Spend an attribute point (str/dex/vit/energy). Vit/Energy retune Life/Mana live.
  function investAttr(key) { if (run.attrPoints <= 0) return { ok: false, reason: 'no points' };
    if (!['str', 'dex', 'vit', 'energy'].includes(key)) return { ok: false, reason: 'bad attr' };
    run.attrPoints -= 1; run.attr[key] += 1;
    if (key === 'vit') { const s = statsNow(); run.life += VIT_LIFE; run.life = Math.min(run.life, s.maxLife); } // new Life is usable now
    if (key === 'energy') { const s = statsNow(); run.mana += ENERGY_MANA; run.mana = Math.min(run.mana, s.maxMana); }
    pushHeroStats(); return { ok: true }; }

  // ---- town / checkpoint loop ----
  // A DESCENT plays exactly ONE quest (the current ACT1 area) as a survival segment.
  // Clear its gate -> back to TOWN (bank/turn-in/respec) for the next; the final
  // quest (Andariel) wins the act. You can only descend FROM town.
  let lastCleared = 0;
  function descend() {
    if (run.phase !== 'town') return { ok: false, reason: 'not in town' };
    lastXp = 0; lastCleared = 0;
    combat = createArena({ hero: heroForFight(), rng, survival: { areas: [ACT1[run.questIdx]], tier: run.difficulty, rollLoot: rollGroundItem } });
    run.phase = 'arena'; return { ok: true };
  }
  const startRun = descend; const beginDescent = descend; // (the town's "descend" button)

  // BANK the at-risk run inventory into the persistent stash — town only. This is
  // the ONLY way loot survives the run; anything unbanked is lost on death.
  function bank(id) {
    if (run.phase !== 'town') return { ok: false, reason: 'bank only in town' };
    const i = run.bag.findIndex((x) => x.id === id); if (i < 0) return { ok: false, reason: 'not in bag' };
    const [it] = run.bag.splice(i, 1); pushToStash(it); return { ok: true, stash: run.stash.length };
  }
  function bankAll() {
    if (run.phase !== 'town') return { ok: false, reason: 'bank only in town' };
    const n = run.bag.length; for (const it of run.bag) pushToStash(it); run.bag = []; return { ok: true, banked: n };
  }
  // Keep the stash under its cap by evicting the LEAST build-valuable item when full.
  function pushToStash(it) {
    run.stash.push(it);
    if (run.stash.length > STASH_CAP) {
      let worst = 0; for (let i = 1; i < run.stash.length; i++) if (stashScore(run.stash[i]) < stashScore(run.stash[worst])) worst = i;
      run.stash.splice(worst, 1);
    }
  }
  const stashScore = (it) => it.grants ? 50 : itemScore(it, cls.id) + ({ unique: 40, rare: 12, magic: 4 }[it.rarity] || 0);

  // Draw a COPY of a stash item onto the character (town only). The stash keeps the
  // original — it's your permanent gear library — so equipping never risks it.
  function equipFromStash(id) {
    if (run.phase !== 'town') return { ok: false, reason: 'town only' };
    const src = run.stash.find((x) => x.id === id); if (!src) return { ok: false, reason: 'not in stash' };
    const copy = { ...src, id: src.id + '_eq' + (equipSeq++) };
    const gate = canEquip(copy); if (!gate.ok) return gate;
    const slot = slotFor(copy); if (run.equipment[slot]) run.bag.push(run.equipment[slot]);
    run.equipment[slot] = copy; clampLife(); pushHeroStats(); return { ok: true };
  }

  // Start a run equipped with chosen stash gear (a COPY of each; stash retained).
  // Silently skips anything you can't wear yet (level/str/dex gates still apply).
  function applyLoadout(picks) {
    for (const p of picks) {
      const src = (p && p.slot) ? p : run.stash.find((x) => x.id === p);
      if (!src) continue;
      const copy = { ...src, id: (src.id || 'load') + '_ld' + (equipSeq++) };
      if (!canEquip(copy).ok) continue;
      const slot = slotFor(copy); if (run.equipment[slot] && slot !== 'weapon') run.bag.push(run.equipment[slot]);
      run.equipment[slot] = copy;
    }
  }

  // One FREE full respec (skills + attributes) per act — refund every spent point.
  function respec() {
    if (run.phase !== 'town') return { ok: false, reason: 'town only' };
    if (run.respecUsedThisAct) return { ok: false, reason: 'respec already used this act' };
    for (const v of Object.values(run.skillHard)) run.skillPoints += v; run.skillHard = {};
    const base = cls.attr || { str: 0, dex: 0, vit: 0, energy: 0 };
    for (const k of ['str', 'dex', 'vit', 'energy']) { run.attrPoints += (run.attr[k] - base[k]); run.attr[k] = base[k]; }
    run.respecUsedThisAct = true; clampLife(); pushHeroStats(); return { ok: true };
  }

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
      while (run.xp >= xpForLevel(run.level)) { run.xp -= xpForLevel(run.level); run.level += 1; run.skillPoints += 1; run.attrPoints += ATTR_PER_LEVEL; leveled += 1; } }
    const got = combat.takeCollected(); const equipped = [];
    for (const it of got) { if (autoEquipIfUpgrade(it)) equipped.push(it); else if (run.bag.length < BAG_CAP) run.bag.push(it); }
    // clearing an area completes its QUEST — reward skill points, a heal, and a restock
    let cleared = 0;
    if (s.areaCleared > lastCleared) { cleared = s.areaCleared - lastCleared; lastCleared = s.areaCleared;
      for (let k = 0; k < cleared; k++) { run.skillPoints += 2; combat.heal(Math.round(statsNow().maxLife * 0.5)); addPotions(1, 1); } }
    if (leveled || equipped.length) pushHeroStats();
    run.life = s.hero.life; run.mana = s.hero.mana;
    if (s.over) resolveArena();
    return { leveled, loot: got, equipped, cleared, phase: run.phase };
  }

  // A segment ended: WIN clears the quest (turn it in -> town, or the act is won on
  // the last quest); LOSE is death (forfeit the unbanked run inventory; stash is
  // safe); FLEE is a safe retreat back to town (quest not cleared, loot kept).
  function resolveArena() {
    if (!combat) return run.phase; const s = combat.getState(); if (!s.over) return run.phase;
    run.life = s.hero.life; run.mana = s.hero.mana; run.lastResult = s.result;
    if (s.result === 'win') {
      run.quests[run.questIdx].done = true;
      if (run.questIdx >= ACT1.length - 1) { run.phase = 'victory'; }
      else { run.questIdx += 1; toTown(); }
    } else if (s.result === 'fled') {
      toTown(); // retreated — the current quest still stands, but the loot came home
    } else {
      run.phase = 'dead'; run.bag = []; // death forfeits everything unbanked; the stash persists
    }
    combat = null; return run.phase;
  }
  // Arrive in town: rest to full and top the belt. (Banking/turn-in are your calls.)
  function toTown() { run.phase = 'town'; const st = statsNow(); run.life = st.maxLife; run.mana = st.maxMana; addPotions(1, 1); }
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
      gold: run.gold, bagCap: BAG_CAP, stashCap: STASH_CAP,
      level: run.level, xp: run.xp, xpToNext: xpForLevel(run.level), skillPoints: run.skillPoints,
      attr: { ...run.attr }, attrPoints: run.attrPoints,
      act: run.act, questIdx: run.questIdx, quests: run.quests.map((q) => ({ ...q })),
      quest: run.quests[run.questIdx] ? { ...run.quests[run.questIdx] } : null,
      respecUsedThisAct: run.respecUsedThisAct, canRespec: run.phase === 'town' && !run.respecUsedThisAct,
      abilities: abilitiesNow(), tree, tabs: cls.tabs || null,
      equipment: Object.fromEntries(SLOTS.map((sl) => [sl, run.equipment[sl] ? { ...run.equipment[sl] } : null])),
      bag: run.bag.map((i) => ({ ...i })), stash: run.stash.map((i) => ({ ...i })),
      lastResult: run.lastResult, gained: run.gained };
  }
  function skName(id) { return SKILLS[id] ? SKILLS[id].name : id; }
  function getStash() { return run.stash.map((i) => ({ ...i })); } // for the UI to persist to storage

  return { beginDescent, startRun, descend, syncArena, resolveArena, flee, toTown, bank, bankAll, equipFromStash, respec, getStash,
    equipFromBag, unequip, canEquip, investSkill, investAttr, quaff, sellFromBag, buyPotion, dropFromBag,
    getRun, getCombat: () => combat, deriveStats: () => statsNow(), deriveAbilities: () => abilitiesNow() };
}
