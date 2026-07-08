// Run orchestration: a full descent through a seeded map. You commit to one of
// three directions each step (no backtracking), fight swarms/elites, loot
// randomized gear, level up (build-crafting), and face the act boss. Life
// carries between fights (camps heal). Permadeath ends the run. Pure engine.

import { CLASSES, ITEMS, SLOTS, LEVELUP_OPTIONS, ELITE_AFFIXES, BOSS_PACK } from './content.js';
import { makeRng } from './rng.js';
import { createCombat } from './combat.js';
import { generateEncounter } from './encounters.js';
import { makeMap, nextChoices, NODE_TYPES } from './map.js';
import { rollItem } from './loot.js';

export function deriveDeck(cls, equipment, bonusCards = []) {
  const deck = [...cls.baseCards, ...bonusCards];
  for (const slot of SLOTS) {
    const item = equipment[slot];
    if (item && item.grants && item.grants.cards) deck.push(...item.grants.cards);
  }
  return deck;
}

export function deriveStats(cls, equipment, bonusStats = {}) {
  const stats = {
    maxLife: cls.maxLife, maxMana: cls.maxMana, startBlock: cls.startBlock || 0,
    plusSkills: 0, accuracy: cls.accuracy != null ? cls.accuracy : 100,
    evasion: cls.evasion || 0, handSize: cls.handSize,
  };
  const add = (mods) => { for (const [k, v] of Object.entries(mods)) stats[k] = (stats[k] || 0) + v; };
  for (const slot of SLOTS) { const it = equipment[slot]; if (it && it.passive) add(it.passive); }
  add(bonusStats);
  return stats;
}

const xpForLevel = (level) => 14 + level * 8; // xp needed to reach the next level

export function createGame(seed = 'bloodrune', opts = {}) {
  const rng = makeRng(seed);
  const cls = CLASSES[opts.classId || 'barbarian'];
  const difficulty = opts.difficulty || 'Normal'; // Normal | Nightmare | Hell

  const run = {
    seed, difficulty,
    className: cls.name,
    equipment: emptyEquipment(),
    bag: [...(cls.startingBag || [])].map((id) => ITEMS[id]),
    bonusCards: [],
    bonusStats: {},
    level: 1, xp: 0,
    pendingLevels: 0,
    levelupOptions: null,
    map: makeMap({ length: 9 }),
    choices: null,
    node: null,       // the node currently being resolved
    pendingLoot: [],  // items shown on the reward screen (already in bag)
    lastResult: null, // 'win' | 'fled'
    life: 0,
    phase: 'prep',    // prep|map|combat|reward|levelup|camp|treasure|dead|victory
  };
  run.equipment.weapon = ITEMS[cls.startingWeapon];
  run.life = statsNow().maxLife;

  let combat = null;

  function emptyEquipment() { const e = {}; for (const s of SLOTS) e[s] = null; return e; }
  function statsNow() { return deriveStats(cls, run.equipment, run.bonusStats); }
  function deckNow() { return deriveDeck(cls, run.equipment, run.bonusCards); }

  function slotFor(item) {
    if (item.slot === 'ring') return run.equipment.ring1 ? (run.equipment.ring2 ? 'ring1' : 'ring2') : 'ring1';
    return item.slot;
  }
  function equipFromBag(itemId) {
    const idx = run.bag.findIndex((i) => i.id === itemId);
    if (idx < 0) return { ok: false };
    const item = run.bag[idx];
    const slot = slotFor(item);
    run.bag.splice(idx, 1);
    if (run.equipment[slot]) run.bag.push(run.equipment[slot]);
    run.equipment[slot] = item;
    clampLife();
    return { ok: true };
  }
  function unequip(slot) {
    const item = run.equipment[slot];
    if (!item) return { ok: false };
    run.bag.push(item);
    run.equipment[slot] = null;
    clampLife();
    return { ok: true };
  }
  function clampLife() { run.life = Math.min(run.life, statsNow().maxLife); }

  function heroForFight() {
    const s = statsNow();
    return { name: cls.name, glyph: cls.glyph, maxLife: s.maxLife, life: run.life,
      maxMana: s.maxMana, handSize: s.handSize, startBlock: s.startBlock,
      plusSkills: s.plusSkills, accuracy: s.accuracy, evasion: s.evasion };
  }

  // ---- map / node flow ----
  function beginDescent() {
    run.choices = nextChoices(rng, run.map);
    run.phase = 'map';
  }

  function eliteEncounter() {
    const pack = generateEncounter(rng, { maxMonsters: 4, mixChance: 0.15 });
    const eliteId = rng.pick(['ghoul', 'goatman', 'skeleton_archer']);
    const affixKeys = Object.keys(ELITE_AFFIXES);
    const n = 1 + rng.int(2); // 1-2 affixes
    const affixes = [];
    while (affixes.length < n) { const a = rng.pick(affixKeys); if (!affixes.includes(a)) affixes.push(a); }
    pack.push({ id: eliteId, affixes });
    return pack;
  }

  function chooseDirection(i) {
    if (run.phase !== 'map' || !run.choices || !run.choices[i]) return { ok: false };
    const node = run.choices[i];
    run.node = node;
    if (node.type === 'combat') return startFight(generateEncounter(rng, { maxMonsters: 9 }));
    if (node.type === 'elite') return startFight(eliteEncounter());
    if (node.type === 'boss') return startFight([...BOSS_PACK]);
    if (node.type === 'treasure') { grantLoot(2, 15); run.lastResult = 'treasure'; run.phase = 'reward'; advanceStep(); return { ok: true }; }
    if (node.type === 'camp') { const s = statsNow(); run.life = Math.min(s.maxLife, run.life + Math.round(s.maxLife * 0.4)); queueLevels(1); run.phase = 'camp'; advanceStep(); return { ok: true }; }
    return { ok: false };
  }

  function startFight(pack) {
    combat = createCombat({ deck: deckNow(), hero: heroForFight(), pack, rng });
    run.phase = 'combat';
    return { ok: true };
  }

  function advanceStep() { run.map.step += 1; run.choices = nextChoices(rng, run.map); }

  // Called by UI after a combat resolves.
  function resolveCombat() {
    const s = combat.getState();
    if (!s.over) return run.phase;
    run.life = s.hero.life;
    if (s.result === 'lose') { run.phase = 'dead'; return run.phase; }

    const wasBoss = run.node && run.node.type === 'boss';
    if (s.result === 'win') {
      run.xp += s.xpEarned;
      grantXpLevels();
      const isElite = run.node && run.node.type === 'elite';
      grantLoot(isElite ? 2 : wasBoss ? 3 : 1, isElite ? 20 : wasBoss ? 45 : 5);
      run.lastResult = 'win';
      if (wasBoss) { run.phase = 'victory'; return run.phase; }
      advanceStep();
    } else { // fled — no xp, no loot
      run.lastResult = 'fled';
      run.pendingLoot = [];
      advanceStep();
    }
    run.phase = run.pendingLevels > 0 ? beginLevelup() : 'reward';
    return run.phase;
  }

  function flee() {
    if (!combat) return;
    combat.flee();
    return resolveCombat();
  }

  // ---- loot / xp / leveling ----
  function grantLoot(count, magicFind) {
    run.pendingLoot = [];
    for (let n = 0; n < count; n++) {
      const item = rollItem(rng, { magicFind });
      run.bag.push(item);
      run.pendingLoot.push(item);
    }
  }

  function grantXpLevels() {
    while (run.xp >= xpForLevel(run.level)) { run.xp -= xpForLevel(run.level); run.level += 1; run.pendingLevels += 1; }
  }
  function queueLevels(n) { run.pendingLevels += n; }

  function beginLevelup() {
    // offer 3 distinct options; cards already known are filtered out
    const known = new Set(run.bonusCards);
    const pool = LEVELUP_OPTIONS.filter((o) => !(o.kind === 'card' && known.has(o.card)));
    const opts = [];
    const copy = pool.slice();
    while (opts.length < 3 && copy.length) opts.push(copy.splice(rng.int(copy.length), 1)[0]);
    run.levelupOptions = opts;
    run.phase = 'levelup';
    return 'levelup';
  }

  function pickLevelup(id) {
    const opt = (run.levelupOptions || []).find((o) => o.id === id);
    if (!opt) return { ok: false };
    if (opt.kind === 'card') run.bonusCards.push(opt.card);
    else { for (const [k, v] of Object.entries(opt.mod)) run.bonusStats[k] = (run.bonusStats[k] || 0) + v; if (opt.mod.maxLife) run.life += opt.mod.maxLife; }
    run.pendingLevels -= 1;
    run.levelupOptions = null;
    if (run.pendingLevels > 0) beginLevelup();
    else run.phase = 'reward';
    return { ok: true, phase: run.phase };
  }

  function continueFromReward() { run.phase = 'map'; }

  function getRun() {
    const s = statsNow();
    return {
      seed: run.seed, difficulty: run.difficulty, className: run.className, glyph: cls.glyph,
      phase: run.phase,
      stats: s, deck: deckNow(),
      life: run.life, maxLife: s.maxLife,
      level: run.level, xp: run.xp, xpToNext: xpForLevel(run.level), pendingLevels: run.pendingLevels,
      levelupOptions: run.levelupOptions,
      equipment: Object.fromEntries(SLOTS.map((sl) => [sl, run.equipment[sl] ? { ...run.equipment[sl] } : null])),
      bag: run.bag.map((i) => ({ ...i })),
      pendingLoot: run.pendingLoot.map((i) => ({ ...i })),
      lastResult: run.lastResult,
      choices: run.choices ? run.choices.map((c) => ({ type: c.type, ...NODE_TYPES[c.type] })) : null,
      node: run.node ? { type: run.node.type, ...NODE_TYPES[run.node.type] } : null,
      mapStep: run.map.step, mapLength: run.map.length,
    };
  }

  return {
    beginDescent, chooseDirection, resolveCombat, flee,
    equipFromBag, unequip, pickLevelup, continueFromReward,
    getRun, getCombat: () => combat,
    deriveDeck: () => deckNow(), deriveStats: () => statsNow(),
  };
}
