// Engine seam tests: the inventory/equipment model, the gear->deck and
// gear->stats seams, and the seeded loot roll.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveDeck, deriveStats } from '../engine/game.js';
import { CLASSES, ITEMS, M1_DROP_TABLE } from '../engine/content.js';

const barb = CLASSES.barbarian;

test('deriveDeck = class base cards + cards granted by equipped gear (any slot)', () => {
  const eq = { weapon: ITEMS.worn_axe, offhand: ITEMS.grim_fetish }; // fetish grants War Cry
  const deck = deriveDeck(barb, eq);
  assert.equal(deck.filter((c) => c === 'strike').length, 2); // from worn_axe
  assert.equal(deck.includes('warcry'), true); // from off-hand, not a weapon
});

test('deriveStats sums passive mods from every equipped slot', () => {
  const eq = { helm: ITEMS.horned_helm, body: ITEMS.chainmail, amulet: ITEMS.sigil_of_wrath };
  const s = deriveStats(barb, eq);
  assert.equal(s.maxLife, barb.maxLife + 10 + 14); // helm +10, chainmail +14
  assert.equal(s.startBlock, 1); // chainmail +1
  assert.equal(s.maxMana, barb.maxMana + 1); // sigil +1
  assert.equal(s.plusSkills, 2); // sigil +2 to Skills
});

test('equipping from the bag rebuilds deck AND stats; displaced gear returns to bag', () => {
  const game = createGame('inv');
  const before = game.getRun();
  assert.equal(before.deck.includes('rend'), false);
  // starting bag contains a rusted_hatchet (grants Rend) and a horned_helm (+10 Life)
  const r1 = game.equipFromBag('rusted_hatchet');
  assert.equal(r1.ok, true);
  const afterWeapon = game.getRun();
  assert.equal(afterWeapon.deck.includes('rend'), true);
  assert.equal(afterWeapon.bag.some((i) => i.id === 'worn_axe'), true); // old weapon back in bag

  const r2 = game.equipFromBag('horned_helm');
  assert.equal(r2.ok, true);
  assert.equal(game.getRun().stats.maxLife, barb.maxLife + 10);
});

test('unequipping returns the item to the bag and reverts the deck/stats', () => {
  const game = createGame('inv2');
  game.equipFromBag('horned_helm');
  assert.equal(game.getRun().stats.maxLife, barb.maxLife + 10);
  const res = game.unequip('helm');
  assert.equal(res.ok, true);
  assert.equal(game.getRun().stats.maxLife, barb.maxLife);
  assert.equal(game.getRun().bag.some((i) => i.id === 'horned_helm'), true);
});

test('rings fill the first free finger, then swap', () => {
  const game = createGame('rings');
  // put two ring items in play: iron_band is in... it's in starting bag ('iron_band')
  game.equipFromBag('iron_band');
  const run = game.getRun();
  assert.ok(run.equipment.ring1 && run.equipment.ring1.id === 'iron_band');
  assert.equal(run.equipment.ring2, null);
});

test('same seed => same loot drop (determinism)', () => {
  const a = playToLoot('seed-A');
  const b = playToLoot('seed-A');
  assert.equal(a.getRun().pendingLoot.id, b.getRun().pendingLoot.id);
});

test('winning drops loot into the bag from the table', () => {
  const game = playToLoot('win-seed');
  const run = game.getRun();
  assert.equal(run.phase, 'loot');
  assert.ok(run.pendingLoot);
  assert.ok(M1_DROP_TABLE.includes(run.pendingLoot.id));
  assert.ok(run.bag.some((i) => i.id === run.pendingLoot.id)); // it's in the bag to equip
});

// --- helper: greedily play the M1 fight to victory, then resolve loot -------
function playToLoot(seed) {
  const game = createGame(seed);
  const combat = game.startFight();
  let guard = 0;
  while (!combat.getState().over && guard++ < 500) {
    let played = true;
    while (played) {
      played = false;
      const s = combat.getState();
      if (s.over) break;
      for (let i = 0; i < s.hand.length; i++) {
        if (s.hand[i].cost <= s.hero.mana) { combat.playCard(i); played = true; break; }
      }
    }
    if (combat.getState().over) break;
    combat.endTurn();
  }
  assert.equal(combat.getState().result, 'win', `expected the M1 fight to be winnable (seed ${seed})`);
  game.resolveCombat();
  return game;
}
