// Engine seam tests: deterministic combat + Swarm mechanics (Mana pool,
// targeting, Accuracy hit/miss, the Evasion hook, shaman mend, encounters).
// No DOM, no browser.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRng } from '../engine/rng.js';
import { createCombat } from '../engine/combat.js';
import { generateEncounter } from '../engine/encounters.js';

// accuracy 120 => every player attack lands (clamped to 100), so damage/Block
// tests are exact and independent of the hit RNG. Miss behaviour is covered by
// its own tests with a low-accuracy hero.
const HERO = { name: 'Barbarian', glyph: '🪓', maxLife: 64, maxMana: 10, handSize: 5,
  startBlock: 0, plusSkills: 0, accuracy: 120, evasion: 0 };

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
  assert.equal(after[0], before[0]);
  assert.equal(after[2], before[2] - 12);
});

test('aiming at a dead target falls back to the front', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'skeleton']);
  c.playCard(0, 0); // kill front fallen (12 >= 8)
  assert.equal(c.getState().lane[0].hp, 0);
  const skelBefore = c.getState().lane[1].hp;
  c.playCard(0, 0); // aim at dead front -> falls back to living front (skeleton)
  assert.equal(c.getState().lane[1].hp, skelBefore - 12);
});

test('AoE attack hits every living monster', () => {
  const c = combat(['cleave', 'cleave', 'cleave', 'cleave', 'cleave'], ['fallen', 'skeleton', 'ghoul']);
  const before = c.getState().lane.map((m) => m.hp);
  c.playCard(0); // Cleave: 6 to all (hero acc 120 => all land)
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
  c.playCard(0); c.playCard(0); c.playCard(0); // 3x Strike @3 => 1 left
  assert.equal(c.getState().hero.mana, 1);
  assert.equal(c.playCard(0).ok, false); // can't afford a 4th
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

// --- Accuracy: attacker-driven avoidance ----------------------------------

test('a low-accuracy attacker sometimes misses (your attacks can whiff)', () => {
  let hits = 0, misses = 0;
  for (let s = 0; s < 60; s++) {
    const c = createCombat({ deck: ['strike'], hero: { ...HERO, accuracy: 50 }, pack: ['ghoul'], rng: makeRng(s) });
    const before = c.getState().lane[0].hp;
    c.playCard(0);
    if (c.getState().lane[0].hp < before) hits++; else misses++;
  }
  assert.ok(hits > 0 && misses > 0, `acc 50 should mix hits and misses: hits=${hits} misses=${misses}`);
});

test('high accuracy never misses (non-punitive at the top end)', () => {
  let misses = 0;
  for (let s = 0; s < 60; s++) {
    const c = createCombat({ deck: ['strike'], hero: { ...HERO, accuracy: 100 }, pack: ['ghoul'], rng: makeRng(s) });
    const before = c.getState().lane[0].hp;
    c.playCard(0);
    if (c.getState().lane[0].hp === before) misses++;
  }
  assert.equal(misses, 0);
});

test('a low-accuracy monster sometimes misses YOU (attacker-driven avoidance)', () => {
  let took = 0, dodged = 0;
  for (let s = 0; s < 60; s++) {
    const c = createCombat({ deck: ['guard'], hero: { ...HERO }, pack: ['zombie'], rng: makeRng(s) }); // zombie acc 65
    const before = c.getState().hero.life;
    c.endTurn();
    if (c.getState().hero.life < before) took++; else dodged++;
  }
  assert.ok(took > 0 && dodged > 0, `zombie acc 65 should mix: took=${took} dodged=${dodged}`);
});

test('Evasion hook: a defender with high Evasion dodges landed blows', () => {
  // skeleton has 100 accuracy, but hero Evasion 100 dodges every landed hit.
  const dodgy = { ...HERO, evasion: 100 };
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['skeleton'], 3, dodgy);
  c.endTurn();
  assert.equal(c.getState().hero.life, dodgy.maxLife); // took nothing
});

// --- exact enemy damage (using 100%-accuracy monsters: skeleton, ghoul) ----

test('no Block => Hero takes the full telegraphed damage', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['skeleton', 'ghoul']);
  c.endTurn(); // intents 5 + 7 = 12 (both acc 100)
  assert.equal(c.getState().hero.life, 64 - 12);
});

test('Block absorbs telegraphed damage exactly (shared pool, in order)', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['skeleton', 'ghoul']);
  c.playCard(0); // +8 Block
  assert.equal(c.getState().hero.block, 8);
  c.endTurn(); // 12 incoming, skeleton 5 absorbed, ghoul 7 -> 3 absorbed + 4 dmg
  assert.equal(c.getState().hero.life, 64 - 4);
});

test('killing every monster ends the fight as a win', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen']); // fallen hp 8
  c.playCard(0);
  const s = c.getState();
  assert.equal(s.over, true);
  assert.equal(s.result, 'win');
});

test('Hero Life reaching 0 ends the fight as a loss', () => {
  const frail = { ...HERO, maxLife: 5 };
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['ghoul'], 7, frail); // ghoul acc 100 hits 7
  c.endTurn();
  const s = c.getState();
  assert.equal(s.hero.life, 0);
  assert.equal(s.result, 'lose');
});

test('a killed monster cannot act on its telegraphed intent', () => {
  const c = combat(['rend', 'rend', 'rend', 'rend', 'rend'], ['fallen', 'skeleton']); // fallen hp 8, skeleton acc 100
  c.playCard(0, 0); // kill front fallen
  assert.equal(c.getState().lane[0].hp, 0);
  c.endTurn(); // only the surviving skeleton hits for 5
  assert.equal(c.getState().hero.life, 64 - 5);
});

// --- shaman support --------------------------------------------------------

test('a Fallen Shaman mends its most-wounded ally instead of attacking', () => {
  // intents telegraph a turn ahead: shaman commits to attack this turn; the
  // mend comes next turn once the wound persists.
  const c = combat(['strike', 'strike', 'strike', 'strike', 'strike'], ['fallen', 'fallen_shaman']);
  c.playCard(0, 0); // Strike 7 vs Fallen 8 => hp 1
  c.endTurn();
  assert.equal(c.getState().lane[1].intent.type, 'mend');
  c.endTurn(); // shaman mends the fallen +4 (1 -> 5)
  assert.equal(c.getState().lane[0].hp, 5);
});

test('a Shaman with no wounded ally just attacks', () => {
  const c = combat(['guard', 'guard', 'guard', 'guard', 'guard'], ['fallen', 'fallen_shaman']);
  assert.equal(c.getState().lane[1].intent.type, 'attack');
});

// --- encounters ------------------------------------------------------------

test('encounter generation is deterministic and capped, with real packs', () => {
  const a = generateEncounter(makeRng('enc-1'));
  const b = generateEncounter(makeRng('enc-1'));
  assert.deepEqual(a, b);
  assert.ok(a.length >= 1 && a.length <= 8);
  const big = generateEncounter(makeRng('enc-2'), { maxMonsters: 9 });
  assert.ok(big.length >= 1 && big.length <= 9);
});
