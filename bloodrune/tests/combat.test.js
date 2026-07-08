// Engine tests: the surrounded ABILITIES combat — ranges, reach, guard,
// breakthrough/exposed, summons, surround, XP, flee.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeRng } from '../engine/rng.js';
import { createCombat, skillEffect, skillLevel } from '../engine/combat.js';

const HERO = { name: 'Hero', glyph: '🪓', maxLife: 60, maxMana: 14, startBlock: 0, plusSkills: 0, hard: {},
  abilities: ['strike', 'guard', 'arrow', 'charge', 'raise_skeleton', 'cleave', 'zeal'] };
function fight(pack, over = {}) { return createCombat({ hero: { ...HERO, ...over }, pack, rng: makeRng('p') }); }
const ai = (c, id) => c.getState().hero.abilities.findIndex((a) => a.id === id);

test('skills scale their own way, with damage ranges', () => {
  assert.deepEqual([skillEffect({ hard: {}, plusSkills: 0 }, 'strike').min, skillEffect({ hard: {}, plusSkills: 0 }, 'strike').max], [5, 8]);
  assert.deepEqual([skillEffect({ hard: { strike: 2 }, plusSkills: 0 }, 'strike').min, skillEffect({ hard: { strike: 2 }, plusSkills: 0 }, 'strike').max], [9, 12]);
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { raise_skeleton: 4 }, plusSkills: 0 }, 'raise_skeleton').count, 3);
  assert.equal(skillLevel({ hard: {}, plusSkills: 3 }, 'strike'), 4);
});

test('melee reaches only the inner ring; a ranged skill reaches the outer', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const gBefore = c.getState().enemies[1].hp;
  c.useSkill(ai(c, 'strike'), 0); // focus outer shaman, melee -> hits inner instead
  assert.equal(c.getState().enemies[0].hp, 16); // shaman (outer) untouched by melee
  assert.ok(c.getState().enemies[1].hp < gBefore); // inner guardian took the Strike
  const c2 = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c2.getState().enemies[0].hp;
  c2.useSkill(ai(c2, 'arrow'), 0); // Arrow reaches the shaman (guard-reduced)
  const dealt = before - c2.getState().enemies[0].hp;
  assert.ok(dealt >= 1 && dealt <= 3, `guarded arrow ${dealt}`);
});

test('Charge pierces the guard for full damage but Exposes you', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.useSkill(ai(c, 'charge'), 0);
  assert.ok(before - c.getState().enemies[0].hp >= 6);
  assert.equal(c.getState().hero.exposed, true);
});

test('while Exposed, Block does not hold', () => {
  const c = fight([{ id: 'goatman' }]); // hp18 atk6
  c.useSkill(ai(c, 'guard'));
  assert.ok(c.getState().hero.block > 0);
  c.useSkill(ai(c, 'charge'), 0);
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 5); // goatman atk 5, Block dropped while Exposed
});

test('summons strike your focus each turn, flanking the guard', () => {
  const c = fight([{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.useSkill(ai(c, 'raise_skeleton'));
  c.setFocus(0);
  const before = c.getState().enemies[0].hp;
  c.endTurn();
  const dealt = before - c.getState().enemies[0].hp;
  assert.ok(dealt >= 3 && dealt <= 5, `skeleton flanked ${dealt}`);
});

test('every living enemy hits you each turn (the surround) and kills grant XP', () => {
  const c = fight([{ id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }]);
  c.endTurn(); assert.equal(c.getState().hero.life, 60 - (2 + 2 + 5)); // fallen 2 + fallen 2 + goatman 5
  const c2 = fight([{ id: 'fallen' }]);
  c2.useSkill(ai(c2, 'strike'), 0); // kill it (strike 5-8 >= 8? maybe; use zeal? fallen hp8)
  // strike may not one-shot; cast again
  if (c2.getState().enemies[0].hp > 0) c2.useSkill(ai(c2, 'strike'), 0);
  assert.equal(c2.getState().enemies[0].hp, 0);
  assert.ok(c2.getState().xpEarned >= 3);
});

test('summons body-block the surround (the skeleton wall) and can shatter', () => {
  // one goatman (atk 5); a lone skeleton (4 HP) soaks the blow so the hero is untouched.
  const c = fight([{ id: 'goatman' }]);
  c.useSkill(ai(c, 'raise_skeleton'));
  const lifeBefore = c.getState().hero.life;
  c.endTurn();
  assert.equal(c.getState().hero.life, lifeBefore); // the wall took the hit, not you
  assert.equal(c.getState().hero.summons.length, 0); // 4-HP skeleton shattered on a 5 hit
});

test('a caster mends its wounded allies (telegraphed a turn ahead)', () => {
  const c = fight([{ id: 'shaman' }, { id: 'fallen' }]);
  c.useSkill(ai(c, 'arrow'), 1); // wound the fallen (reaches, unguarded)
  c.endTurn();
  assert.equal(c.getState().enemies[0].intent.type, 'mend');
});

test('flee ends the fight without a win; parting blows can kill', () => {
  const c = fight([{ id: 'fallen' }, { id: 'goatman' }]);
  const r = c.flee();
  assert.ok(['fled', 'lose'].includes(r.result));
  assert.equal(c.getState().over, true);
});

test('same seed + actions => identical state (determinism)', () => {
  const p = [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }];
  const a = fight(p); const b = fight(p);
  a.useSkill(ai(a, 'raise_skeleton')); b.useSkill(ai(b, 'raise_skeleton'));
  a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
