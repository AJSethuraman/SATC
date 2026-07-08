// Engine seam tests: deterministic combat + M1.5 mechanics (Mana pool,
// targeting, standing Block, +to Skills). No DOM, no browser.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRng } from '../engine/rng.js';
import { createCombat } from '../engine/combat.js';
import { generateEncounter } from '../engine/encounters.js';

const HERO = { name: 'Barbarian', glyph: '🪓', maxLife: 64, maxMana: 10, handSize: 5,
  startBlock: 0, plusSkills: 0 };

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
  assert.notDeepEqual(a.getState().hand, b.getState().hand);
});

test('single-target attack hits the FRONT monster by default', () => {
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['fallen', 'skeleton']);
  const before = c.getState().lane.map((m) => m.hp);
  c.playCard(0); // Strike = 7 to front
  const after = c.getState().lane.map((m) => m.hp);
  assert.equal(after[0], before[0] - 7);
  assert.equal(after[1], before[1]);
});

test('single-target attack can be aimed at a chosen target', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'skeleton', 'ghoul']);
  const before = c.getState().lane.map((m) => m.hp);
  c.playCard(0, 2); // Rend = 12 aimed at the ghoul (index 2)
  const after = c.getState().lane.map((m) => m.hp);
  assert.equal(after[0], before[0]); // front untouched
  assert.equal(after[2], before[2] - 12); // ghoul hit
});

test('aiming at a dead target falls back to the front', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'skeleton']);
  c.playCard(0, 0); // kill front fallen (12 >= 12)
  assert.equal(c.getState().lane[0].hp, 0);
  const skelBefore = c.getState().lane[1].hp;
  c.playCard(0, 0); // aim at the now-dead front -> falls back to front living (skeleton)
  assert.equal(c.getState().lane[1].hp, skelBefore - 12);
});

test('AoE attack hits every living monster', () => {
  const c = combat(['cleave', 'cleave', 'cleave', 'cleave', 'cleave'], ['fallen', 'skeleton', 'ghoul']);
  const before = c.getState().lane.map((m) => m.hp);
  c.playCard(0); // Cleave: 6 to all
  const after = c.getState().lane.map((m) => m.hp);
  for (let i = 0; i < after.length; i++) assert.equal(after[i], before[i] - 6);
});

test('+to Skills adds flat damage to cards', () => {
  const buff = { ...HERO, plusSkills: 3 };
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['ghoul'], 42, buff);
  const before = c.getState().lane[0].hp;
  c.playCard(0); // Strike 7 + 3 = 10
  assert.equal(c.getState().lane[0].hp, before - 10);
});

test('Mana is a pool: multiple cards per turn until it runs out', () => {
  const c = combat(['strike', 'strike', 'strike', 'strike', 'guard'], ['ghoul']);
  assert.equal(c.getState().hero.mana, 10);
  c.playCard(0); // -3 => 7
  c.playCard(0); // -3 => 4
  c.playCard(0); // -3 => 1
  assert.equal(c.getState().hero.mana, 1);
  const res = c.playCard(0); // Strike costs 3, only 1 left
  assert.equal(res.ok, false);
});

test('Mana refund gives Mana back (pool feel)', () => {
  const c = combat(['frenzy', 'frenzy', 'frenzy', 'frenzy', 'frenzy'], ['ghoul']);
  c.playCard(0); // Frenzy cost 3, refund 2 => net -1
  assert.equal(c.getState().hero.mana, 9);
});

test('standing Block is granted at the start of each turn', () => {
  const armored = { ...HERO, startBlock: 4 };
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen'], 42, armored);
  assert.equal(c.getState().hero.block, 4);
});

test('no Block => Hero takes the full telegraphed damage', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'skeleton', 'ghoul']);
  c.endTurn(); // intents 3 + 5 + 7 = 15
  assert.equal(c.getState().hero.life, 64 - 15);
});

test('Block absorbs telegraphed damage exactly (shared pool, in order)', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'skeleton', 'ghoul']);
  c.playCard(0); // +8 Block
  assert.equal(c.getState().hero.block, 8);
  c.endTurn(); // 15 incoming, 8 absorbed => 7 to Hero
  assert.equal(c.getState().hero.life, 64 - 7);
});

test('a Fallen Shaman mends its most-wounded ally instead of attacking', () => {
  // front Fallen (idx0), Shaman at back (idx1). Intents telegraph a turn ahead,
  // so the shaman commits to attack THIS turn; the mend comes next turn once the
  // wound persists (this documents the telegraph timing).
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['fallen', 'fallen_shaman']);
  c.playCard(0, 0); // Strike 7 vs Fallen 8 => hp 1 (shaman already telegraphed attack)
  c.endTurn();      // enemy phase, then re-telegraph for the next turn
  const shaman = c.getState().lane[1];
  assert.equal(shaman.intent.type, 'mend'); // now it sees the wounded ally
  c.endTurn();      // shaman mends the fallen +4 (1 -> 5)
  assert.equal(c.getState().lane[0].hp, 5);
});

test('a Shaman with no wounded ally just attacks', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'fallen_shaman']);
  // no damage dealt; both at full => shaman should telegraph an attack
  assert.equal(c.getState().lane[1].intent.type, 'attack');
});

test('killing every monster ends the fight as a win', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen']); // fallen hp 12
  c.playCard(0); // Rend 12 >= 12 -> dead
  const s = c.getState();
  assert.equal(s.over, true);
  assert.equal(s.result, 'win');
});

test('Hero Life reaching 0 ends the fight as a loss', () => {
  const frail = { ...HERO, maxLife: 5 };
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['ghoul'], 7, frail); // ghoul hits 9
  c.endTurn();
  const s = c.getState();
  assert.equal(s.hero.life, 0);
  assert.equal(s.over, true);
  assert.equal(s.result, 'lose');
});

test('a killed monster cannot act on its telegraphed intent', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'fallen']); // Rend 12, fallen hp 8
  c.playCard(0); // front fallen dies
  assert.equal(c.getState().lane[0].hp, 0);
  c.endTurn(); // only the surviving fallen hits for 3
  assert.equal(c.getState().hero.life, 64 - 3);
});

test('encounter generation is deterministic and capped, with real packs', () => {
  const a = generateEncounter(makeRng('enc-1'));
  const b = generateEncounter(makeRng('enc-1'));
  assert.deepEqual(a, b); // same seed => same pack
  assert.ok(a.length >= 1 && a.length <= 5);
  const c = generateEncounter(makeRng('enc-2'));
  // different seed likely differs (documents rng use); at minimum it's valid
  assert.ok(c.length >= 1 && c.length <= 5);
});
