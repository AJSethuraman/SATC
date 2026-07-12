// Engine tests: ABILITIES (always available, Mana-gated — no draw) with DAMAGE
// RANGES, on the surrounded/reach/summon model.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFight, skillEffect, skillLevel, GUARD_MITIGATION } from './engine.js';

const HERO = { maxLife: 60, maxMana: 12, plusSkills: 0, hard: {} };
function fight(deck, pack, over = {}) { return createFight({ deck, hero: { ...HERO, ...over }, pack, seed: 'p' }); }
const idx = (c, id) => c.getState().abilities.findIndex((a) => a.id === id);

test('skills scale their own way and carry damage RANGES', () => {
  const e = skillEffect({ hard: {}, plusSkills: 0 }, 'strike');
  assert.deepEqual([e.min, e.max], [5, 8]);
  const e2 = skillEffect({ hard: { strike: 2 }, plusSkills: 0 }, 'strike'); // +2 levels, grow 2
  assert.deepEqual([e2.min, e2.max], [9, 12]);
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { raise_skeleton: 4 }, plusSkills: 0 }, 'raise_skeleton').count, 3);
  assert.equal(skillLevel({ hard: {}, plusSkills: 3 }, 'strike'), 4);
});

test('abilities are ALWAYS available (no draw) — only Mana gates them', () => {
  const c = fight(['strike', 'guard'], [{ id: 'goatman' }]);
  assert.equal(c.getState().abilities.length, 2);
  const si = idx(c, 'strike');
  assert.ok(c.playCard(si).ok);       // cast Strike
  assert.ok(c.playCard(si).ok);       // cast it AGAIN this turn (still available)
  assert.equal(c.getState().abilities.length, 2); // nothing consumed
});

test('damage lands within its range', () => {
  const c = fight(['strike'], [{ id: 'goatman' }]); // Strike 5-8
  const before = c.getState().enemies[0].hp;
  c.playCard(idx(c, 'strike'), 0);
  const dealt = before - c.getState().enemies[0].hp;
  assert.ok(dealt >= 5 && dealt <= 8, `dealt ${dealt} out of 5-8`);
});

test('melee cannot reach the outer ring — it hits the inner bodies instead', () => {
  const c = fight(['smite'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.playCard(idx(c, 'smite'), 0); // focus outer shaman, but Smite is melee
  assert.equal(c.getState().enemies[0].hp, 16);
  assert.ok(c.getState().enemies[1].hp < 15);
});

test('a ranged skill reaches the outer caster (still guard-reduced)', () => {
  const c = fight(['shoot'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.playCard(idx(c, 'shoot'), 0);
  const dealt = before - c.getState().enemies[0].hp;
  // Arrow 4-7, guarded => round(x*0.4) => 2..3
  assert.ok(dealt >= 1 && dealt <= 3, `guarded hit ${dealt}`);
});

test('clear the escorts and the caster takes full ranged damage', () => {
  const c = fight(['smite', 'shoot'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const si = idx(c, 'smite');
  c.playCard(si, 1); c.playCard(si, 1); // Smite 8-12 x2 kills the 15hp Champion
  assert.equal(c.getState().enemies[1].hp, 0);
  const before = c.getState().enemies[0].hp;
  c.playCard(idx(c, 'shoot'), 0);
  assert.ok(before - c.getState().enemies[0].hp >= 4); // full 4-7
});

test('Charge reaches + pierces the guard, but Exposes you', () => {
  const c = fight(['charge'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.playCard(idx(c, 'charge'), 0);
  assert.ok(before - c.getState().enemies[0].hp >= 6); // 6-10 full
  assert.equal(c.getState().hero.exposed, true);
});

test('while Exposed your Block does not hold', () => {
  const c = fight(['guard', 'charge'], [{ id: 'goatman' }]); // goatman hp18 atk6 survives a Charge
  c.playCard(idx(c, 'guard'));
  assert.ok(c.getState().hero.block > 0);
  c.playCard(idx(c, 'charge'), 0);
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 6);
});

test('summons strike your focus each turn — even the guarded outer caster', () => {
  const c = fight(['raise_skeleton', 'guard'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.playCard(idx(c, 'raise_skeleton'));
  c.setFocus(0);
  const before = c.getState().enemies[0].hp;
  c.endTurn();
  const dealt = before - c.getState().enemies[0].hp;
  assert.ok(dealt >= 2 && dealt <= 4, `skeleton flanked for ${dealt} (2-4)`); // full, not guard-reduced
});

test('every living enemy hits you each turn (the surround)', () => {
  const c = fight(['guard'], [{ id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }]);
  c.endTurn();
  assert.equal(c.getState().hero.life, 60 - 12);
});

test('a caster mends its wounded allies (telegraphed a turn ahead)', () => {
  const c = fight(['shoot'], [{ id: 'shaman' }, { id: 'fallen' }]);
  c.playCard(idx(c, 'shoot'), 1);
  c.endTurn();
  assert.equal(c.getState().enemies[0].intent.type, 'mend');
});

test('learning a skill adds it to your always-available abilities', () => {
  const c = fight(['guard'], [{ id: 'fallen' }], { skillPoints: 1 });
  const before = c.getState().abilities.length;
  c.spendSkillPoint('raise_skeleton', { learn: true });
  assert.equal(c.getState().abilities.length, before + 1);
});

test('same seed + actions => identical state (determinism)', () => {
  const p = [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }];
  const a = fight(['raise_skeleton', 'cleave', 'shoot', 'charge'], p);
  const b = fight(['raise_skeleton', 'cleave', 'shoot', 'charge'], p);
  a.playCard(0); b.playCard(0); a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
