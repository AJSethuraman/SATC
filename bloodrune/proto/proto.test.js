// Engine tests: reach (melee=inner, ranged/charge=outer), summons that reach the
// outer ring and flank the guard, guard mitigation, breakthrough+exposed, scaling.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFight, skillEffect, skillLevel, GUARD_MITIGATION } from './engine.js';

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, hard: {} };
function fight(deck, pack, over = {}) { return createFight({ deck, hero: { ...HERO, ...over }, pack, seed: 'p' }); }
function playById(c, cid, focus) { const i = c.getState().hand.findIndex((x) => x.id === cid); return i >= 0 && c.playCard(i, focus).ok; }

// ---- scaling, incl. summon count ----
test('skills scale their own way; Raise Skeleton scales its army', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { strike: 2 }, plusSkills: 0 }, 'strike').damage, 10);
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'raise_skeleton').count, 1);
  assert.equal(skillEffect({ hard: { raise_skeleton: 4 }, plusSkills: 0 }, 'raise_skeleton').count, 3); // 1 + floor(4/2)
  assert.equal(skillLevel({ hard: {}, plusSkills: 3 }, 'strike'), 4);
});

// ---- reach: melee = inner ring only ----
test('melee cannot reach the outer ring — it hits the inner bodies instead', () => {
  const c = fight(['smite', 'smite', 'smite', 'smite', 'smite'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.playCard(0, 0); // focus the outer shaman, but Smite is melee (reach 0)
  assert.equal(c.getState().enemies[0].hp, 16); // shaman untouched
  assert.ok(c.getState().enemies[1].hp < 15);   // the inner Champion took it
});

test('a ranged skill reaches the outer ring (but the caster is still guarded)', () => {
  const c = fight(['shoot', 'shoot', 'shoot', 'shoot', 'shoot'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.playCard(0, 0); // Arrow reaches the shaman; guard reduces it
  const dealt = before - c.getState().enemies[0].hp;
  assert.equal(dealt, Math.max(1, Math.round(5 * (1 - GUARD_MITIGATION)))); // 2
});

test('clear the escorts and the outer caster takes full ranged damage', () => {
  const c = fight(['smite', 'smite', 'shoot', 'shoot', 'shoot'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  playById(c, 'smite', 1); playById(c, 'smite', 1); // melee kills the inner Champion (15 hp, 9+9)
  assert.equal(c.getState().enemies[1].hp, 0);
  const before = c.getState().enemies[0].hp;
  playById(c, 'shoot', 0); // now full
  assert.equal(c.getState().enemies[0].hp, before - 5);
});

// ---- breakthrough ----
test('Charge reaches + ignores the guard for full damage, but Exposes you', () => {
  const c = fight(['charge', 'charge', 'charge', 'charge', 'charge'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.playCard(0, 0);
  assert.equal(c.getState().enemies[0].hp, before - 7);
  assert.equal(c.getState().hero.exposed, true);
});

test('while Exposed your Block does not hold', () => {
  const c = fight(['guard', 'charge', 'guard', 'charge', 'guard'], [{ id: 'fallen' }]);
  assert.ok(playById(c, 'guard'));
  assert.ok(c.getState().hero.block > 0);
  assert.ok(playById(c, 'charge', 0));
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 3);
});

// ---- summons: attack out of your immediate circle, flanking the guard ----
test('summons strike your focus each turn — even the guarded outer caster', () => {
  const c = fight(['raise_skeleton', 'guard', 'guard', 'guard', 'guard'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  playById(c, 'raise_skeleton'); // 1 skeleton, atk 3
  c.setFocus(0); // focus the guarded shaman
  const before = c.getState().enemies[0].hp;
  c.endTurn(); // summons phase: skeleton flanks the guard and hits the shaman full
  assert.equal(c.getState().enemies[0].hp, before - 3);
});

// ---- surround + caster ----
test('every living enemy hits you each turn (the surround)', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }]);
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 12);
});

test('a caster mends its wounded allies (telegraphed a turn ahead)', () => {
  const c = fight(['shoot', 'shoot', 'shoot', 'shoot', 'shoot'], [{ id: 'shaman' }, { id: 'fallen' }]);
  playById(c, 'shoot', 1); // wound the fallen
  c.endTurn();
  assert.equal(c.getState().enemies[0].intent.type, 'mend');
});

// ---- tree + determinism ----
test('learning a skill adds its card to the deck', () => {
  const c = fight(['guard', 'guard'], [{ id: 'fallen' }], { skillPoints: 1 });
  const before = c.getState().drawCount + c.getState().hand.length + c.getState().discardCount;
  c.spendSkillPoint('raise_skeleton', { learn: true });
  assert.equal(c.getState().drawCount + c.getState().hand.length + c.getState().discardCount, before + 1);
});

test('same seed + actions => identical state (determinism)', () => {
  const p = [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }];
  const a = fight(['raise_skeleton', 'cleave', 'guard', 'shoot', 'charge'], p);
  const b = fight(['raise_skeleton', 'cleave', 'guard', 'shoot', 'charge'], p);
  playById(a, 'raise_skeleton'); playById(b, 'raise_skeleton'); a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
