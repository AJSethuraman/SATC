// Engine tests: the SURROUNDED model — guarded targets, breakthrough + exposed,
// surround pressure, caster mend, and per-skill scaling.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFight, skillEffect, skillLevel, GUARD_MITIGATION } from './engine.js';

const HERO = { maxLife: 60, maxMana: 12, handSize: 5, plusSkills: 0, hard: {} };
function fight(deck, pack, over = {}) { return createFight({ deck, hero: { ...HERO, ...over }, pack, seed: 'p' }); }
function playById(c, cid, tgt) { const i = c.getState().hand.findIndex((x) => x.id === cid); return i >= 0 && c.playCard(i, tgt).ok; }

// ---- scaling (unchanged, still the win from the detour) ----
test('Zeal scales HITS; damage skills scale DAMAGE; +Skills raises the level', () => {
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'zeal').hits, 2);
  assert.equal(skillEffect({ hard: { zeal: 2 }, plusSkills: 0 }, 'zeal').hits, 4);
  assert.equal(skillEffect({ hard: {}, plusSkills: 0 }, 'strike').damage, 6);
  assert.equal(skillEffect({ hard: { strike: 2 }, plusSkills: 0 }, 'strike').damage, 10);
  assert.equal(skillLevel({ hard: {}, plusSkills: 3 }, 'strike'), 4);
});

// ---- the guard: a reason NOT to just snipe the caster ----
test('a guarded caster takes heavily reduced damage while a guardian lives', () => {
  const c = fight(['strike', 'strike', 'strike', 'strike', 'strike'],
    [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }]);
  const before = c.getState().enemies[0].hp; // 16
  c.playCard(0, 0); // Strike the shaman — but it's guarded
  const dealt = before - c.getState().enemies[0].hp;
  assert.ok(dealt < 6, `guarded hit should be reduced (got ${dealt} of 6)`);
  assert.equal(dealt, Math.max(1, Math.round(6 * (1 - GUARD_MITIGATION)))); // 2
});

test('kill the escorts and the caster is exposed to full damage', () => {
  const c = fight(['smite', 'smite', 'smite', 'smite', 'smite'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  c.playCard(0, 1); c.playCard(0, 1); // smite (9) x2 kills the guardian (15 hp)
  assert.equal(c.getState().enemies[1].hp, 0);
  const before = c.getState().enemies[0].hp;
  c.playCard(0, 0); // now the shaman takes full damage
  assert.equal(c.getState().enemies[0].hp, before - 9);
});

// ---- breakthrough: reach it now, at a price ----
test('Charge breaks through the guard for full damage but leaves you Exposed', () => {
  const c = fight(['charge', 'charge', 'charge', 'charge', 'charge'], [{ id: 'shaman' }, { id: 'guardian', guards: 0 }]);
  const before = c.getState().enemies[0].hp;
  c.playCard(0, 0); // Charge the guarded shaman
  assert.equal(c.getState().enemies[0].hp, before - 7); // full, ignores guard
  assert.equal(c.getState().hero.exposed, true);
});

test('while Exposed, your Block does not hold', () => {
  const c = fight(['guard', 'charge', 'guard', 'charge', 'guard'], [{ id: 'fallen' }]); // fallen hits 3
  assert.ok(playById(c, 'guard'));           // gain Block
  assert.ok(c.getState().hero.block > 0);
  assert.ok(playById(c, 'charge', 0));        // break through -> Exposed
  c.endTurn();                                // fallen attacks; Block is ignored
  assert.equal(c.getState().hero.life, 60 - 3);
});

// ---- surround + caster behaviour ----
test('every living enemy attacks each turn (the surround)', () => {
  const c = fight(['guard', 'guard', 'guard', 'guard', 'guard'], [{ id: 'fallen' }, { id: 'fallen' }, { id: 'goatman' }]);
  c.endTurn(); // 3 + 3 + 6 = 12 incoming, no block
  assert.equal(c.getState().hero.life, 60 - 12);
});

test('a caster mends its wounded allies (telegraphed a turn ahead)', () => {
  const c = fight(['strike', 'strike', 'strike', 'strike', 'strike'], [{ id: 'shaman' }, { id: 'fallen' }]);
  c.playCard(0, 1); // wound the fallen
  c.endTurn();
  assert.equal(c.getState().enemies[0].intent.type, 'mend');
});

// ---- skill tree + determinism ----
test('learning a skill adds its card to the deck', () => {
  const c = fight(['guard', 'guard'], [{ id: 'fallen' }], { skillPoints: 1 });
  const before = c.getState().drawCount + c.getState().hand.length + c.getState().discardCount;
  c.spendSkillPoint('cleave', { learn: true });
  assert.equal(c.getState().drawCount + c.getState().hand.length + c.getState().discardCount, before + 1);
});

test('same seed + actions => identical state (determinism)', () => {
  const p = [{ id: 'shaman' }, { id: 'guardian', guards: 0 }, { id: 'fallen' }, { id: 'goatman' }];
  const a = fight(['cleave', 'strike', 'guard', 'zeal', 'charge'], p);
  const b = fight(['cleave', 'strike', 'guard', 'zeal', 'charge'], p);
  a.playCard(0); b.playCard(0); a.endTurn(); b.endTurn();
  assert.deepEqual(a.getState(), b.getState());
});
