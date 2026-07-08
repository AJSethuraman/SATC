// Engine tests for the Option-B positional prototype: unique per-skill scaling,
// melee reach, ranged front-blocking, movement, determinism.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFight, skillEffect, skillLevel } from './engine.js';

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, hard: {} };
function fight(deck, pack, heroOverrides = {}) {
  return createFight({ deck, hero: { ...HERO, ...heroOverrides }, pack, seed: 'p' });
}

// ---- scaling: each skill scales in its OWN way ----
test('Zeal scales HITS with level (D2: +1 hit/level, capped)', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2); // level 1
  assert.equal(skillEffect({ hard: { zeal: 2 }, plusSkills: 0 }, 'zeal').hits, 4); // level 3
  assert.equal(skillEffect({ hard: { zeal: 9 }, plusSkills: 0 }, 'zeal').hits, 5); // capped at 5
});

test('Charged Bolt scales BOLTS with level (D2: +1 bolt/level)', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'charged_bolt').bolts, 1);
  assert.equal(skillEffect({ hard: { charged_bolt: 3 }, plusSkills: 0 }, 'charged_bolt').bolts, 4);
});

test('damage skills scale DAMAGE with level', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'cleave').damage, 5);
  assert.equal(skillEffect({ hard: { cleave: 2 }, plusSkills: 0 }, 'cleave').damage, 9); // 5 + 2*2
});

test('+to Skills raises the LEVEL (soft points), scaling each skill its own way', () => {
  assert.equal(skillLevel({ hard: {}, plusSkills: 2 }, 'zeal'), 3);
  assert.equal(skillEffect({ hard: {}, plusSkills: 2 }, 'zeal').hits, 4);          // +skills => more hits
  assert.equal(skillEffect({ hard: {}, plusSkills: 2 }, 'charged_bolt').bolts, 3); // +skills => more bolts
});

test('Zeal actually strikes multiple times in combat', () => {
  const c = fight(['zeal', 'zeal', 'zeal', 'zeal', 'zeal'], [{ id: 'brute', pos: 1 }], { hard: { zeal: 2 } }); // lvl3 => 4 hits x4 = 16
  const before = c.getState().enemies[0].hp;
  c.playCard(0);
  assert.equal(c.getState().enemies[0].hp, before - 16);
});

// ---- positioning ----
test('melee is out of reach until you move into range', () => {
  const c = fight(['cleave', 'cleave', 'cleave', 'cleave', 'cleave'], [{ id: 'grunt', pos: 2 }]);
  assert.equal(c.playCard(0).ok, false); // dist 2 > reach 1
  c.move('advance'); // pos 0 -> 1, dist -> 1
  assert.equal(c.playCard(0).ok, true);
});

test('ranged fire is absorbed by the nearest band (a mob on the way blocks it)', () => {
  const c = fight(['shoot', 'shoot', 'shoot', 'shoot', 'shoot'], [{ id: 'grunt', pos: 2 }, { id: 'grunt', pos: 4 }]);
  const before = c.getState().enemies.map((e) => e.hp);
  c.playCard(0); // Arrow -> nearest band (pos 2) only
  const after = c.getState().enemies.map((e) => e.hp);
  assert.ok(after[0] < before[0], 'front enemy hit');
  assert.equal(after[1], before[1], 'back enemy shielded by the front');
});

test('Charged Bolt spreads its bolts across the front band', () => {
  const c = fight(['charged_bolt', 'charged_bolt', 'charged_bolt', 'charged_bolt', 'charged_bolt'],
    [{ id: 'grunt', pos: 2 }, { id: 'grunt', pos: 2 }, { id: 'grunt', pos: 2 }], { plusSkills: 2 }); // lvl3 => 3 bolts
  const before = c.getState().enemies.map((e) => e.hp);
  c.playCard(0);
  const after = c.getState().enemies.map((e) => e.hp);
  const hitCount = after.filter((hp, i) => hp < before[i]).length;
  assert.equal(hitCount, 3, 'all three front enemies took a bolt');
});

test('only one Move per turn', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'grunt', pos: 3 }]);
  assert.equal(c.move('advance').ok, true);
  assert.equal(c.move('advance').ok, false); // already moved
});

test('enemies advance toward you and then attack', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'grunt', pos: 3 }]);
  c.endTurn(); // grunt advances 3 -> 2
  assert.equal(c.getState().enemies[0].pos, 2);
});

// ---- skill tree: learn a skill -> it enters the deck ----
test('spending a skill point can learn a new skill into the deck', () => {
  const c = fight(['guard', 'guard'], [{ id: 'grunt', pos: 3 }], { skillPoints: 1 });
  const before = c.getState().drawCount + c.getState().hand.length + c.getState().discardCount;
  c.spendSkillPoint('fireball', { learn: true });
  const after = c.getState().drawCount + c.getState().hand.length + c.getState().discardCount;
  assert.equal(after, before + 1); // Fireball card added to the deck
});

test('same seed + actions => identical state (determinism)', () => {
  const a = fight(['cleave', 'shoot', 'guard', 'zeal', 'bash'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 4 }]);
  const b = fight(['cleave', 'shoot', 'guard', 'zeal', 'bash'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 4 }]);
  a.move('advance'); b.move('advance');
  a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
