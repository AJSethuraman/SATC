// Run/game orchestration for the M1 tracer bullet: build the Barbarian's deck
// from equipped gear, start the fight, and — on victory — roll a gear drop the
// player can equip to visibly change the deck (the gear->deck seam in miniature).
// Pure engine, seeded rng only.

import { CLASSES, ITEMS, M1_PACK, M1_DROP_TABLE } from './content.js';
import { makeRng } from './rng.js';
import { createCombat } from './combat.js';

// Deck = class base cards + every card granted by equipped gear.
// (Slice 4 splits weapon=cards vs armor=passives; M1 has weapon grants only.)
export function deriveDeck(cls, equipment) {
  const deck = [...cls.baseCards];
  for (const slot of Object.keys(equipment)) {
    const item = equipment[slot];
    if (item && item.grants && item.grants.cards) deck.push(...item.grants.cards);
  }
  return deck;
}

export function createGame(seed = 'bloodrune') {
  const rng = makeRng(seed);
  const cls = CLASSES.barbarian;

  const run = {
    seed,
    className: cls.name,
    equipment: { weapon: ITEMS[cls.startingWeapon] },
    pendingLoot: null, // an item offered after a win, until equipped/skipped
    phase: 'ready', // 'ready' | 'combat' | 'loot' | 'won' | 'dead'
  };

  let combat = null;

  function hero() {
    return {
      name: cls.name, glyph: cls.glyph,
      maxLife: cls.maxLife, maxMana: cls.maxMana, handSize: cls.handSize,
    };
  }

  function deck() {
    return deriveDeck(cls, run.equipment);
  }

  function startFight() {
    combat = createCombat({ deck: deck(), hero: hero(), pack: [...M1_PACK], rng });
    run.phase = 'combat';
    return combat;
  }

  // Called by the UI/tests after a combat resolves, to advance run phase and
  // roll loot on a win.
  function resolveCombat() {
    const s = combat.getState();
    if (!s.over) return run.phase;
    if (s.result === 'win') {
      const dropId = rng.pick(M1_DROP_TABLE);
      run.pendingLoot = ITEMS[dropId];
      run.phase = 'loot';
    } else {
      run.phase = 'dead';
    }
    return run.phase;
  }

  function equipPendingLoot() {
    if (!run.pendingLoot) return { ok: false };
    run.equipment[run.pendingLoot.slot] = run.pendingLoot;
    run.pendingLoot = null;
    run.phase = 'won';
    return { ok: true, deck: deck() };
  }

  function skipLoot() {
    run.pendingLoot = null;
    run.phase = 'won';
    return { deck: deck() };
  }

  function getRun() {
    return {
      seed: run.seed,
      className: run.className,
      equipment: Object.fromEntries(
        Object.entries(run.equipment).map(([k, v]) => [k, v ? { ...v } : null])),
      deck: deck(),
      pendingLoot: run.pendingLoot ? { ...run.pendingLoot } : null,
      phase: run.phase,
    };
  }

  return {
    startFight,
    resolveCombat,
    equipPendingLoot,
    skipLoot,
    getRun,
    getCombat: () => combat,
    deriveDeck: () => deck(),
  };
}
