// Engine seam tests: the gear->deck seam and the seeded loot roll.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveDeck } from '../engine/game.js';
import { CLASSES, ITEMS, M1_DROP_TABLE } from '../engine/content.js';

test('deriveDeck = class base cards + cards granted by equipped gear', () => {
  const barb = CLASSES.barbarian;
  const withAxe = deriveDeck(barb, { weapon: ITEMS.worn_axe });
  // base (bash, guard, guard, cleave) + worn_axe (strike, strike)
  assert.equal(withAxe.length, barb.baseCards.length + 2);
  assert.equal(withAxe.filter((c) => c === 'strike').length, 2);
  assert.equal(withAxe.includes('rend'), false);
});

test('swapping the weapon changes the deck (equip is load-bearing)', () => {
  const barb = CLASSES.barbarian;
  const before = deriveDeck(barb, { weapon: ITEMS.worn_axe });
  const after = deriveDeck(barb, { weapon: ITEMS.rusted_hatchet }); // grants strike + rend
  assert.equal(before.includes('rend'), false);
  assert.equal(after.includes('rend'), true);
});

test('same seed => same loot drop (determinism)', () => {
  const a = playToLoot('seed-A');
  const b = playToLoot('seed-A');
  assert.equal(a.getRun().pendingLoot.id, b.getRun().pendingLoot.id);
});

test('winning the M1 fight offers a gear drop from the table', () => {
  const game = playToLoot('deterministic-win');
  const run = game.getRun();
  assert.equal(run.phase, 'loot');
  assert.ok(run.pendingLoot, 'a drop should be offered');
  assert.ok(M1_DROP_TABLE.includes(run.pendingLoot.id));
});

test('equipping the drop grants its cards into the deck', () => {
  const game = playToLoot('deterministic-win');
  const drop = game.getRun().pendingLoot;
  const deckBefore = game.getRun().deck.slice();
  const res = game.equipPendingLoot();
  assert.equal(res.ok, true);
  const deckAfter = game.getRun().deck;
  // The equipped weapon replaces the old one; its granted cards must appear.
  for (const cardId of drop.grants.cards) assert.ok(deckAfter.includes(cardId));
  assert.notDeepEqual(deckAfter, deckBefore);
  assert.equal(game.getRun().phase, 'won');
});

// --- helper: greedily play the M1 fight to victory, then resolve loot -------
function playToLoot(seed) {
  const game = createGame(seed);
  const combat = game.startFight();
  let guard = 0;
  while (!combat.getState().over && guard++ < 500) {
    // play every affordable card each turn (attacks + block), then end turn
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
  const s = combat.getState();
  assert.equal(s.result, 'win', `expected the M1 fight to be winnable (seed ${seed})`);
  game.resolveCombat();
  return game;
}
