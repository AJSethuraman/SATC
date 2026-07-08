// Engine tests for the de-clunked positional prototype: per-skill scaling, melee
// hits the front band (no reach-gate), ranged absorbed by the front, Backstep.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFight, skillEffect, skillLevel } from './engine.js';

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, hard: {} };
function fight(deck, pack, heroOverrides = {}) {
  return createFight({ deck, hero: { ...HERO, ...heroOverrides }, pack, seed: 'p' });
}

// ---- scaling ----
test('Zeal scales HITS with level (D2: +1 hit/level, capped at 5)', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { zeal: 2 }, plusSkills: 0 }, 'zeal').hits, 4);
  assert.equal(skillEffect({ hard: { zeal: 9 }, plusSkills: 0 }, 'zeal').hits, 5);
});
test('Charged Bolt scales BOLTS with level (D2: +1 bolt/level)', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'charged_bolt').bolts, 1);
  assert.equal(skillEffect({ hard: { charged_bolt: 3 }, plusSkills: 0 }, 'charged_bolt').bolts, 4);
});
test('damage skills scale DAMAGE with level', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'cleave').damage, 5);
  assert.equal(skillEffect({ hard: { cleave: 2 }, plusSkills: 0 }, 'cleave').damage, 9);
});
test('+to Skills raises the LEVEL (soft points), scaling each skill its own way', () => {
  assert.equal(skillLevel({ hard: {}, plusSkills: 2 }, 'zeal'), 3);
  assert.equal(skillEffect({ hard: {}, plusSkills: 2 }, 'zeal').hits, 4);
  assert.equal(skillEffect({ hard: {}, plusSkills: 2 }, 'charged_bolt').bolts, 3);
});
test('Zeal actually strikes multiple times in combat', () => {
  const c = fight(['zeal', 'zeal', 'zeal', 'zeal', 'zeal'], [{ id: 'brute', pos: 2 }], { hard: { zeal: 2 } });
  const before = c.getState().enemies[0].hp;
  c.playCard(0);
  assert.equal(c.getState().enemies[0].hp, before - 16); // 4 hits x4
});

// ---- de-clunk: no reach gate, front-band targeting, absorb, backstep ----
test('melee always hits the front band — no reach-gating, no move needed', () => {
  const c = fight(['cleave', 'cleave', 'cleave', 'cleave', 'cleave'], [{ id: 'grunt', pos: 4 }]);
  const before = c.getState().enemies[0].hp;
  assert.equal(c.playCard(0).ok, true); // playable even at distance 4
  assert.ok(c.getState().enemies[0].hp < before);
});
test('a ranged shot aimed past the front is absorbed by the front mob', () => {
  // front grunt at pos 2, target the archer behind at pos 5
  const c = fight(['shoot', 'shoot', 'shoot', 'shoot', 'shoot'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 5 }]);
  const before = c.getState().enemies.map((e) => e.hp);
  const archerUid = c.getState().enemies[1].uid;
  c.playCard(0, archerUid); // aim at the back — front soaks it
  const after = c.getState().enemies.map((e) => e.hp);
  assert.ok(after[0] < before[0], 'front took the shot');
  assert.equal(after[1], before[1], 'back archer shielded by the front');
});
test('once the front is cleared, ranged reaches the next band', () => {
  const c = fight(['fireball', 'shoot', 'shoot', 'shoot', 'shoot'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 5 }]);
  c.playCard(0); // Fireball clears the front grunt (6 >= grunt 10? no) -> ensure kill
  // grunt hp 10, fireball 6 -> not dead; hit again with shoot(5) -> dead
  c.playCard(0); // shoot front grunt
  // now front should be the archer
  const s = c.getState();
  const archerAlive = s.enemies.find((e) => e.id === 'archer');
  assert.equal(s.frontPos, archerAlive.pos); // archer is now the front band
});
test('Backstep shoves the swarm back one band, once per turn', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'grunt', pos: 2 }]);
  assert.equal(c.backstep().ok, true);
  assert.equal(c.getState().enemies[0].pos, 3); // pushed back
  assert.equal(c.backstep().ok, false); // only once
});
test('enemies advance toward you and then attack when adjacent', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'grunt', pos: 3 }]);
  c.endTurn(); assert.equal(c.getState().enemies[0].pos, 2);
  c.endTurn(); assert.equal(c.getState().enemies[0].pos, 1); // now adjacent -> will attack
});
test('spending a skill point can learn a new skill into the deck', () => {
  const c = fight(['guard', 'guard'], [{ id: 'grunt', pos: 3 }], { skillPoints: 1 });
  const before = c.getState().drawCount + c.getState().hand.length + c.getState().discardCount;
  c.spendSkillPoint('fireball', { learn: true });
  assert.equal(c.getState().drawCount + c.getState().hand.length + c.getState().discardCount, before + 1);
});
test('same seed + actions => identical state (determinism)', () => {
  const a = fight(['cleave', 'shoot', 'guard', 'zeal', 'bash'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 4 }]);
  const b = fight(['cleave', 'shoot', 'guard', 'zeal', 'bash'], [{ id: 'grunt', pos: 2 }, { id: 'archer', pos: 4 }]);
  a.backstep(); b.backstep(); a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
