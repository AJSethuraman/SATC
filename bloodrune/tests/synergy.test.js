// S1 — the synergy engine. Synergy IS the damage: a capstone scales with HARD
// points in its named same-tree siblings (+ the tree's Mastery). Gear +skills feed
// synergy PARTIALLY (~40% of a hard point — enough that a "+3 Fire" find is a real
// spike), and cross-tree points add ZERO. Committing to one tree still dominates.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { skillEffect } from '../engine/combat.js';

const orb = { wtype: 'focus' };
const eff = (hard, plusSkills = 0) => skillEffect({ hard, plusSkills, weapon: orb }, 'fire_ball');
const avg = (e) => (e.min + e.max) / 2;

test('synergy web + mastery make a fed capstone ~3x an unfed one at the SAME level', () => {
  const level = { fire_ball: 8 };
  const fed = eff({ fire_ball: 8, fire_bolt: 8, meteor: 8, inferno: 6, fire_mastery: 8 });
  const unfed = eff({ ...level }); // same fire_ball level, no siblings, no mastery
  const ratio = avg(fed) / avg(unfed);
  assert.ok(ratio >= 2.5 && ratio <= 5, `fed/unfed capstone ratio ${ratio.toFixed(2)} should be ~3x`);
  assert.ok(fed.syn > 1 && fed.mas > 1, 'fed capstone reports synergy + mastery multipliers');
  assert.equal(unfed.syn, 1); assert.equal(unfed.mas, 1);
});

test('gear +skills feed synergy PARTIALLY (~40% of a hard point) — a spike, not a rounding error', () => {
  const hard = { fire_ball: 8, fire_bolt: 8, meteor: 8 };
  const bare = eff(hard, 0), geared = eff(hard, 6);
  assert.ok(geared.syn > bare.syn, '+skills now raises the synergy multiplier');
  assert.equal(geared.mas, bare.mas, 'mastery multiplier is still HARD-points only');
  // but each +skill is worth only a FRACTION of a hard point: +6 skills < +6 hard sibling points
  const hardier = eff({ fire_ball: 8, fire_bolt: 14, meteor: 14 }, 0);
  assert.ok(geared.syn < hardier.syn, 'gear +skills is weaker than the same count of HARD points');
  assert.ok(avg(geared) > avg(bare), '+skills also raises raw damage (via skill level)');
});

test('cross-tree points add ZERO synergy to a capstone', () => {
  const base = eff({ fire_ball: 8, fire_bolt: 8 });
  const withCold = eff({ fire_ball: 8, fire_bolt: 8, ice_bolt: 10, glacial_spike: 10, cold_mastery: 8 });
  assert.equal(withCold.syn, base.syn, 'cold points do not feed a fire capstone');
  assert.equal(withCold.mas, base.mas, 'cold mastery does not multiply fire damage');
});

test('committing one tree beats spreading the same points across three', () => {
  const BUDGET = 33;
  // committed: everything into fire
  const committed = skillEffect({ hard: { fire_ball: 9, fire_bolt: 8, meteor: 8, inferno: 4, fire_mastery: 4 }, weapon: orb }, 'fire_ball');
  // spread: ~11 points per tree, so fire_ball's web is thin
  const spread = skillEffect({ hard: { fire_ball: 5, fire_bolt: 3, fire_mastery: 3, ice_bolt: 6, glacial_spike: 5, charged_bolt: 6, nova: 5 }, weapon: orb }, 'fire_ball');
  const ratio = avg(committed) / avg(spread);
  assert.ok(ratio >= 2.5, `committed capstone should be >=2.5x the spread build's (was ${ratio.toFixed(2)})`);
});

test('masteries no longer add flat damage to OTHER trees (old masteryBonus is gone)', () => {
  // a fire capstone gains nothing from cold/lightning mastery points
  const noMast = eff({ fire_ball: 6 });
  const otherMast = eff({ fire_ball: 6, cold_mastery: 10, light_mastery: 10 });
  assert.equal(avg(otherMast), avg(noMast), 'other-tree masteries do not touch fire damage');
});
