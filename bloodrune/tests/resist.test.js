// S2 — elements, resistances, immunities, penetration. Difficulty is a BUILD
// problem: resistances cut damage, Hell immunities zero an element (swap or die),
// and gear penetration lowers resist but can't crack a true immunity.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resistedDamage, createArena } from '../engine/arena.js';
import { skillEffect } from '../engine/combat.js';
import { makeRng } from '../engine/rng.js';

test('resistance reduces elemental damage; wrong/absent element is unaffected', () => {
  assert.equal(resistedDamage(100, { fire: 0.5 }, null, 'fire', 0), 50);
  assert.equal(resistedDamage(100, { fire: 0.5 }, null, 'cold', 0), 100); // cold not resisted
  assert.equal(resistedDamage(100, null, null, 'fire', 0), 100);          // no resist table
  assert.equal(resistedDamage(100, { fire: 0.25 }, null, 'fire', 0), 75);
});

test('immunity zeroes that element and penetration cannot crack it', () => {
  assert.equal(resistedDamage(999, { fire: 1 }, 'fire', 'fire', 0), 0);
  assert.equal(resistedDamage(999, { fire: 1 }, 'fire', 'fire', 0.9), 0, 'penetration cannot break immunity');
  assert.ok(resistedDamage(100, { fire: 1 }, 'fire', 'cold', 0) > 0, 'a different element still hits an immune-to-fire foe');
});

test('penetration lowers effective resistance', () => {
  assert.equal(resistedDamage(100, { fire: 0.6 }, null, 'fire', 0.6), 100, 'full penetration cancels resist');
  assert.equal(resistedDamage(100, { fire: 0.6 }, null, 'fire', 0.3), 70, '-30% resist -> 30% effective');
});

test('Sorceress damage skills carry an element', () => {
  const orb = { hard: { fire_bolt: 1 }, weapon: { wtype: 'focus' } };
  assert.equal(skillEffect(orb, 'fire_bolt').element, 'fire');
  assert.equal(skillEffect({ hard: { ice_bolt: 1 }, weapon: { wtype: 'focus' } }, 'ice_bolt').element, 'cold');
  assert.equal(skillEffect({ hard: { nova: 1 }, weapon: { wtype: 'focus' } }, 'nova').element, 'lightning');
});

test('a fire spell cannot damage a fire-immune foe in the live sim (must swap element)', () => {
  const hero = { name: 'S', glyph: '🔮', maxLife: 900, life: 900, maxMana: 60, mana: 60, manaRegen: 10,
    accuracy: 8, evade: 0, weapon: { wtype: 'focus' }, hard: { fire_ball: 6 }, plusSkills: 0, abilities: ['fire_ball'] };
  // one fire-IMMUNE zombie + one normal zombie, both very tanky so neither dies.
  // Stand still; both walk to the hero and Fire Ball's burst splashes them both.
  const a = createArena({ hero, pack: [{ id: 'zombie', hpMul: 80, immune: 'fire' }, { id: 'zombie', hpMul: 80 }], rng: makeRng('imm') });
  for (let i = 0; i < 30 * 20 && !a.getState().over; i++) a.tick({ x: 0, y: 0 });
  const s = a.getState(); const im = s.enemies.find((e) => e.immune === 'fire'); const norm = s.enemies.find((e) => !e.immune);
  assert.ok(im && im.hp === im.maxHp, 'the fire-immune foe took ZERO fire damage');
  assert.ok(norm && norm.hp < norm.maxHp, 'the non-immune foe was burned');
});
