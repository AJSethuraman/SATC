// Run/game orchestration (M1.5): a Diablo-style character with a full equipment
// slot set and a bag of found items. Equipping rebuilds BOTH the deck (cards
// granted by gear) and the hero's stats (passive mods). On victory, loot drops
// into the bag; the player opens the inventory to equip it. Pure engine, seeded
// rng only.

import { CLASSES, ITEMS, SLOTS, M1_DROP_TABLE } from './content.js';
import { makeRng } from './rng.js';
import { createCombat } from './combat.js';
import { generateEncounter } from './encounters.js';

// Deck = class base cards + every card granted by equipped gear (any slot).
export function deriveDeck(cls, equipment) {
  const deck = [...cls.baseCards];
  for (const slot of SLOTS) {
    const item = equipment[slot];
    if (item && item.grants && item.grants.cards) deck.push(...item.grants.cards);
  }
  return deck;
}

// Stats = class base + summed passive mods from equipped gear.
// Mod vocabulary (extensible): maxLife, maxMana, startBlock, plusSkills.
// (Resists / faster-cast / attack-speed / leech land here in the M3/M4 slices.)
export function deriveStats(cls, equipment) {
  const stats = {
    maxLife: cls.maxLife,
    maxMana: cls.maxMana,
    startBlock: cls.startBlock || 0,
    plusSkills: 0,
    accuracy: cls.accuracy != null ? cls.accuracy : 100,
    evasion: cls.evasion || 0, // Amazon-style dodge; 0 for the Barbarian
    handSize: cls.handSize,
  };
  for (const slot of SLOTS) {
    const item = equipment[slot];
    if (!item || !item.passive) continue;
    for (const [k, v] of Object.entries(item.passive)) {
      stats[k] = (stats[k] || 0) + v;
    }
  }
  return stats;
}

export function createGame(seed = 'bloodrune') {
  const rng = makeRng(seed);
  const cls = CLASSES.barbarian;

  const run = {
    seed,
    className: cls.name,
    equipment: emptyEquipment(),
    bag: [...(cls.startingBag || [])],
    pendingLoot: null,
    phase: 'ready', // 'ready' | 'combat' | 'loot' | 'won' | 'dead'
  };
  run.equipment.weapon = ITEMS[cls.startingWeapon];

  let combat = null;

  function emptyEquipment() {
    const eq = {};
    for (const s of SLOTS) eq[s] = null;
    return eq;
  }

  // Which equipment slot an item can go into. Rings resolve to the first free
  // ring finger (or ring1 if both are full — the swap is handled by equip()).
  function slotFor(item) {
    if (item.slot === 'ring') return run.equipment.ring1 ? (run.equipment.ring2 ? 'ring1' : 'ring2') : 'ring1';
    return item.slot;
  }

  function hero() {
    const s = deriveStats(cls, run.equipment);
    return { name: cls.name, glyph: cls.glyph, maxLife: s.maxLife, maxMana: s.maxMana,
      handSize: s.handSize, startBlock: s.startBlock, plusSkills: s.plusSkills,
      accuracy: s.accuracy, evasion: s.evasion };
  }

  function deck() { return deriveDeck(cls, run.equipment); }
  function stats() { return deriveStats(cls, run.equipment); }

  // Equip an item from the bag into its slot; any displaced item returns to bag.
  function equipFromBag(itemId) {
    const idx = run.bag.indexOf(itemId);
    if (idx < 0) return { ok: false, reason: 'not in bag' };
    const item = ITEMS[itemId];
    const slot = slotFor(item);
    run.bag.splice(idx, 1);
    if (run.equipment[slot]) run.bag.push(run.equipment[slot].id);
    run.equipment[slot] = item;
    return { ok: true, deck: deck(), stats: stats() };
  }

  function unequip(slot) {
    const item = run.equipment[slot];
    if (!item) return { ok: false };
    run.bag.push(item.id);
    run.equipment[slot] = null;
    return { ok: true, deck: deck(), stats: stats() };
  }

  function startFight() {
    const pack = generateEncounter(rng, { maxMonsters: 9 });
    combat = createCombat({ deck: deck(), hero: hero(), pack, rng });
    run.phase = 'combat';
    return combat;
  }

  function resolveCombat() {
    const s = combat.getState();
    if (!s.over) return run.phase;
    if (s.result === 'win') {
      const dropId = rng.pick(M1_DROP_TABLE);
      run.pendingLoot = ITEMS[dropId];
      run.bag.push(dropId); // loot goes to the bag; equip it from the inventory
      run.phase = 'loot';
    } else {
      run.phase = 'dead';
    }
    return run.phase;
  }

  function ackLoot() { run.pendingLoot = null; run.phase = 'won'; }

  function getRun() {
    return {
      seed: run.seed,
      className: run.className,
      equipment: Object.fromEntries(SLOTS.map((s) => [s, run.equipment[s] ? { ...run.equipment[s] } : null])),
      bag: run.bag.map((id) => ({ ...ITEMS[id] })),
      deck: deck(),
      stats: stats(),
      pendingLoot: run.pendingLoot ? { ...run.pendingLoot } : null,
      phase: run.phase,
    };
  }

  return {
    startFight, resolveCombat, ackLoot,
    equipFromBag, unequip,
    getRun, getCombat: () => combat,
    deriveDeck: () => deck(), deriveStats: () => stats(),
  };
}
