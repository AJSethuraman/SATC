// Engine seam tests: deterministic combat resolution. No DOM, no browser.
// Run with:  node --test   (from bloodrune/)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRng } from '../engine/rng.js';
import { createCombat } from '../engine/combat.js';

const HERO = { name: 'Barbarian', glyph: '🪓', maxLife: 60, maxMana: 3, handSize: 5 };

function combat(deck, pack, seed = 42, hero = HERO) {
  return createCombat({ deck, hero, pack, rng: makeRng(seed) });
}

test('same seed + same actions => identical state (determinism)', () => {
  const deck = ['strike', 'guard', 'bash', 'cleave', 'strike', 'guard'];
  const a = combat(deck, ['fallen', 'skeleton', 'ghoul'], 1234);
  const b = combat(deck, ['fallen', 'skeleton', 'ghoul'], 1234);
  a.playCard(0); b.playCard(0);
  a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});

test('different seeds diverge (rng is actually used)', () => {
  const deck = ['strike', 'guard', 'bash', 'cleave', 'strike', 'guard'];
  const a = combat(deck, ['fallen', 'skeleton', 'ghoul'], 1);
  const b = combat(deck, ['fallen', 'skeleton', 'ghoul'], 2);
  // Opening hands are shuffled by seed; at least the hand order should differ
  // for these two seeds (documents that draw is seed-driven).
  assert.notDeepEqual(a.getState().hand, b.getState().hand);
});

test('front-target attack damages the front living monster only', () => {
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['fallen', 'skeleton']);
  const before = c.getState().lane.map((m) => m.hp);
  // find a Strike in hand (deck is all strikes, so hand[0] is one)
  const res = c.playCard(0);
  assert.equal(res.ok, true);
  const after = c.getState().lane.map((m) => m.hp);
  assert.equal(after[0], before[0] - 6); // Strike deals 6 to front
  assert.equal(after[1], before[1]); // second monster untouched
});

test('AoE attack hits every living monster', () => {
  const c = combat(['cleave', 'cleave', 'cleave', 'cleave', 'cleave'], ['fallen', 'skeleton', 'ghoul']);
  const before = c.getState().lane.map((m) => m.hp);
  c.playCard(0); // Cleave: 5 to all
  const after = c.getState().lane.map((m) => m.hp);
  for (let i = 0; i < after.length; i++) assert.equal(after[i], before[i] - 5);
});

test('no Block => Hero takes the full telegraphed damage', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'skeleton', 'ghoul']);
  // end turn without playing anything: intents are 4 + 6 + 8 = 18
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 18);
});

test('Block absorbs telegraphed damage exactly (shared pool, in order)', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'skeleton', 'ghoul']);
  c.playCard(0); // +6 block
  c.playCard(0); // +6 block => 12 block
  assert.equal(c.getState().hero.block, 12);
  c.endTurn(); // 18 incoming, 12 absorbed => 6 to Hero
  assert.equal(c.getState().hero.life, 60 - 6);
});

test('killing every monster ends the fight as a win', () => {
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['fallen']); // fallen hp 10
  c.playCard(0); // 6
  c.playCard(0); // 6 => 12 >= 10, dead
  const s = c.getState();
  assert.equal(s.over, true);
  assert.equal(s.result, 'win');
});

test('Hero Life reaching 0 ends the fight as a loss', () => {
  const frail = { ...HERO, maxLife: 5 };
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['ghoul'], 7, frail); // ghoul hits 8
  c.endTurn(); // 8 dmg to a 5-life hero
  const s = c.getState();
  assert.equal(s.hero.life, 0);
  assert.equal(s.over, true);
  assert.equal(s.result, 'lose');
});

test('a killed monster cannot act on its telegraphed intent', () => {
  // Two fallen (hp10, atk4). Kill the front one, then end turn: only 1 attack lands.
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'fallen']); // Rend = 10
  c.playCard(0); // front fallen dies (10 >= 10)
  assert.equal(c.getState().lane[0].hp, 0);
  c.endTurn(); // only the surviving fallen hits for 4
  assert.equal(c.getState().hero.life, 60 - 4);
});
