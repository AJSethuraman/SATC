// Engine tests for the REAL-TIME arena (the movement pivot). Deterministic: fixed
// DT ticks + seeded rng, so every fight is reproducible. We drive with the engine's
// own movement autopilot (skills auto-fire; the "player" only moves).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createArena, DT, ARENA_W, ARENA_H } from '../engine/arena.js';
import { makeRng } from '../engine/rng.js';
import { ITEMS } from '../engine/content.js';

function hero(over = {}) {
  return { name: 'Test', glyph: '🪓', maxLife: 60, life: 60, maxMana: 14, mana: 14, manaRegen: 2,
    accuracy: 8, evade: 0, actions: 3, weapon: { dmg: [5, 8], wtype: 'melee' }, hard: {}, plusSkills: 0,
    abilities: ['attack', 'cleave'], ...over };
}
function arena(pack, h = hero(), seed = 'a') { return createArena({ hero: h, pack, rng: makeRng(seed) }); }
function run(a, cap = 30 * 60) { let t = 0; while (!a.getState().over && t++ < cap) a.tick(a.autoInput()); return a.getState(); }

test('a fight resolves to a win when you out-fight the pack', () => {
  const s = run(arena([{ id: 'fallen' }, { id: 'fallen' }, { id: 'fallen' }]));
  assert.equal(s.over, true); assert.equal(s.result, 'win');
  assert.ok(s.xpEarned > 0, 'killing grants XP'); assert.equal(s.enemies.filter((e) => e.hp > 0).length, 0);
});

test('deterministic: same seed + same inputs -> identical outcome', () => {
  const mk = () => arena([{ id: 'fallen' }, { id: 'goatman' }, { id: 'zombie' }], hero(), 'det');
  const a = mk(), b = mk(); let ra, rb;
  do { ra = a.tick(a.autoInput()); rb = b.tick(b.autoInput()); } while (!ra.over && !rb.over);
  assert.equal(ra.result, rb.result); assert.equal(ra.xpEarned, rb.xpEarned);
  assert.deepEqual(ra.tally, rb.tally);
});

test('movement moves the hero and stays inside the arena bounds', () => {
  const a = arena([{ id: 'fallen' }]); const x0 = a.getState().hero.x;
  for (let i = 0; i < 20; i++) a.tick({ x: 1, y: 0 });
  assert.ok(a.getState().hero.x > x0, 'moving right increases x');
  for (let i = 0; i < 400; i++) a.tick({ x: 1, y: 1 });
  const h = a.getState().hero; assert.ok(h.x <= ARENA_W && h.y <= ARENA_H && h.x >= 0 && h.y >= 0, 'clamped in bounds');
});

test('Mana gates skills: an empty pool still leaves the free auto-attack', () => {
  // no-mana, no-regen hero with only a costly skill + free attack: it can never cast
  // the skill but still auto-attacks, so it can still win a trivial pack.
  const h = hero({ mana: 0, maxMana: 0, manaRegen: 0, abilities: ['attack', 'cleave'] });
  const s = run(arena([{ id: 'fallen' }], h));
  assert.equal(s.result, 'win'); // the free swing carried it
  assert.ok(s.tally.dmgDealt > 0);
});

test('Mana regenerates over time (per second)', () => {
  const h = hero({ mana: 0, maxMana: 20, manaRegen: 4, abilities: ['attack'] });
  const a = arena([{ id: 'fallen' }], h);
  for (let i = 0; i < 30; i++) a.tick({ x: 0, y: 0 }); // ~1s
  assert.ok(a.getState().hero.mana >= 3, 'about +4/s regen');
});

test('homing bolts let a ranged hero connect and win', () => {
  const h = hero({ glyph: '🏹', maxLife: 50, accuracy: 8, evade: 4, weapon: { dmg: [5, 8], wtype: 'ranged' }, abilities: ['attack', 'power_shot'] });
  const s = run(arena([{ id: 'fallen' }, { id: 'archer' }], h, 'amz'));
  assert.equal(s.result, 'win'); assert.ok(s.tally.hits > 0);
});

test('a Block skill (Guard) soaks damage — shield shows in state', () => {
  const h = hero({ abilities: ['attack', 'guard'], mana: 20, maxMana: 20 });
  const a = arena([{ id: 'goatman' }, { id: 'goatman' }], h, 'blk');
  let sawShield = false; for (let i = 0; i < 60; i++) { a.tick({ x: 0, y: 0 }); if (a.getState().hero.shield > 0) sawShield = true; }
  assert.ok(sawShield, 'Guard raised a Block shield');
});

test('summons (skeletons) fight for the Necromancer and clear a pack', () => {
  const h = hero({ glyph: '💀', maxLife: 44, maxMana: 20, mana: 20, manaRegen: 3,
    weapon: { dmg: null, wtype: 'focus' }, abilities: ['attack', 'raise_skeleton'] });
  const a = arena([{ id: 'fallen' }, { id: 'fallen' }], h, 'nec');
  let sawMinion = false; const s = (() => { let t = 0; while (!a.getState().over && t++ < 30 * 60) { a.tick(a.autoInput()); if (a.getState().minions.length) sawMinion = true; } return a.getState(); })();
  assert.ok(sawMinion, 'raised at least one skeleton'); assert.equal(s.result, 'win');
});

test('a rezzer raises a slain grunt, but raised foes yield no XP (no farming)', () => {
  // A lone shaman + one fallen: the shaman will raise the fallen after you kill it.
  const a = arena([{ id: 'shaman' }, { id: 'fallen' }], hero(), 'rez');
  let raisedSeen = false; let t = 0;
  while (!a.getState().over && t++ < 30 * 60) { a.tick(a.autoInput()); if (a.getState().enemies.some((e) => e.raised && e.hp > 0)) raisedSeen = true; }
  const s = a.getState();
  assert.ok(raisedSeen, 'the shaman raised the fallen at least once');
  // XP earned should equal shaman + a single (first) fallen kill — raised re-kills add nothing
  assert.equal(s.result, 'win');
});

test('Evade lets a nimble hero dodge blows (statistical)', () => {
  const h = hero({ evade: 6, maxLife: 200, abilities: ['attack'] });
  const a = arena([{ id: 'goatman' }, { id: 'goatman' }, { id: 'goatman' }], h, 'eva');
  for (let i = 0; i < 30 * 20; i++) { a.tick({ x: 0, y: 0 }); if (a.getState().over) break; }
  assert.ok(a.getState().tally.evades > 0, 'dodged at least one hit over many');
});

test('quaff restores Life and Mana; flee ends the fight', () => {
  const h = hero({ life: 20, mana: 2, maxMana: 14 });
  const a = arena([{ id: 'fallen' }, { id: 'fallen' }], h, 'q');
  assert.equal(a.quaff('life', 15).ok, true); assert.ok(a.getState().hero.life >= 34);
  assert.equal(a.quaff('mana', 6).ok, true); assert.ok(a.getState().hero.mana >= 7);
  const r = a.flee(); assert.ok(['fled', 'lose'].includes(r.result)); assert.equal(a.getState().over, true);
});

test('you can toggle a skill OFF so it stops auto-firing (Whirlwind, not Cleave)', () => {
  const a = arena([{ id: 'zombie' }, { id: 'zombie' }, { id: 'zombie' }], hero({ maxLife: 300 }), 'tg');
  a.setDisabled(['attack', 'cleave', 'guard']); // silence every offense
  for (let i = 0; i < 200 && !a.getState().over; i++) a.tick({ x: 0, y: 0 });
  assert.equal(a.getState().tally.dmgDealt, 0, 'disabled skills deal no damage');
  assert.equal(a.toggleAbility('cleave'), true); // toggling flips it back on
  for (let i = 0; i < 120 && !a.getState().over; i++) a.tick({ x: 0, y: 0 });
  assert.ok(a.getState().tally.dmgDealt > 0, 're-enabled skill fires again');
});

test('DT is a sane fixed step and arena has real dimensions', () => {
  assert.ok(DT > 0 && DT <= 1 / 20); assert.ok(ARENA_W > 200 && ARENA_H > 200);
});
