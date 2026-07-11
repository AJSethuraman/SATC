// Engine tests: ACTIVE SKILL SLOTS. Instead of every learned skill auto-firing, the
// player slots up to 3 to auto-cast; the rest stay idle. 'attack' always swings and
// is never a slot. Deterministic: seeded rng + fixed DT ticks. We exercise the game's
// active-set API (createGame) and the arena's disabled seam (createArena/setDisabled).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';
import { createArena } from '../engine/arena.js';
import { makeRng } from '../engine/rng.js';

// Drive a survival run, greedily spending points across distinct skills so the roster
// grows past the 3-slot cap (needed to test the cap). Mirrors run.test's autopilot.
function survive(g, max, prefs) {
  const cb = g.getCombat(); let t = 0;
  while (!cb.getState().over && t++ < max) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.4) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
    const sy = g.syncArena();
    if (sy.leveled) { let spent = true;
      while (spent) { spent = false; const r = g.getRun();
        for (const p of prefs) { const w = r.tree.find((x) => x.id === p && x.canInvest); if (w) { g.investSkill(p); spent = true; break; } } } }
  }
  return cb.getState();
}

test('a fresh run auto-slots a sensible few (attack always fires, never a slot)', () => {
  const g = createGame('slots-fresh', { classId: 'barbarian' });
  const active = g.getActiveSkills();
  assert.ok(active.length <= 3, 'never more than the cap');
  assert.ok(!active.includes('attack'), 'attack is the basic swing, not a slot');
  // barbarian starts with 2 slottable skills (guard + weapon Cleave) — both auto-slot.
  assert.deepEqual([...active].sort(), ['cleave', 'guard'].sort());
});

test('descending pushes the disabled set into combat: only slotted skills + attack fire', () => {
  const g = createGame('slots-wire', { classId: 'barbarian' });
  g.descend();
  const cb = g.getCombat();
  const off = Object.fromEntries(cb.getState().hero.abilities.map((a) => [a.id, a.off]));
  assert.equal(off.attack, false, 'attack always fires');
  assert.equal(off.cleave, false, 'a slotted skill fires');
  assert.equal(off.guard, false, 'a slotted skill fires');
  // unslot Cleave -> it goes idle in combat, attack still swings
  g.setActiveSkill('cleave', false);
  const off2 = Object.fromEntries(cb.getState().hero.abilities.map((a) => [a.id, a.off]));
  assert.equal(off2.cleave, true, 'unslotted skill is now idle');
  assert.equal(off2.attack, false, 'attack keeps firing');
});

test('the active set caps at 3 and rejects a 4th; unslotting frees a slot', () => {
  const g = createGame('slots-nec', { classId: 'necromancer' });
  g.descend();
  survive(g, 30 * 160, ['teeth', 'bone_armor', 'bone_spear', 'raise_golem']);
  const r = g.getRun();
  const roster = r.abilities.filter((a) => a !== 'attack');
  assert.ok(roster.length >= 4, `need >3 slottable skills to test the cap (got ${roster.length})`);
  const active = g.getActiveSkills();
  assert.equal(active.length, 3, 'auto-slot fills exactly the cap');
  assert.ok(active.every((id) => roster.includes(id)) && !active.includes('attack'));
  const spare = roster.find((id) => !active.includes(id));
  assert.equal(g.setActiveSkill(spare, true).ok, false, 'a 4th is rejected while 3 are active');
  assert.equal(g.getActiveSkills().length, 3, 'rejection left the set untouched');
  // free a slot, then the 4th slots in
  assert.equal(g.setActiveSkill(active[0], false).ok, true);
  const now = g.setActiveSkill(spare, true);
  assert.equal(now.ok, true, 'with room, the skill slots in');
  assert.ok(now.active.includes(spare) && now.active.length <= 3);
});

test('unslotting sticks (auto-fill never re-adds a deliberately idled skill) and persists across descents', () => {
  const g = createGame('slots-stick', { classId: 'barbarian' });
  g.descend();
  assert.deepEqual([...g.getActiveSkills()].sort(), ['cleave', 'guard'].sort());
  g.setActiveSkill('guard', false);
  assert.deepEqual(g.getActiveSkills(), ['cleave'], 'guard stays idle despite an open slot');
  g.flee(); assert.equal(g.getRun().phase, 'town');
  g.descend();
  assert.deepEqual(g.getActiveSkills(), ['cleave'], 'the slot choice carried into the next descent');
});

// ---- arena seam: only the enabled skills deal damage; disabled ones never fire ----
function meleeHero(over = {}) {
  return { name: 'T', glyph: '🪓', maxLife: 600, life: 600, maxMana: 40, mana: 40, manaRegen: 5,
    accuracy: 12, evade: 0, actions: 3, weapon: { dmg: [6, 10], wtype: 'melee' }, hard: {}, plusSkills: 0,
    abilities: ['attack', 'cleave', 'whirlwind'], ...over };
}

test('a fully-disabled kit deals no damage; enabling one AoE makes only it fire', () => {
  const pack = [{ id: 'zombie' }, { id: 'zombie' }, { id: 'zombie' }];
  const off = createArena({ hero: meleeHero(), pack, rng: makeRng('iso') });
  off.setDisabled(['attack', 'cleave', 'whirlwind', 'guard']); // nothing slotted
  for (let i = 0; i < 200 && !off.getState().over; i++) off.tick({ x: 0, y: 0 });
  assert.equal(off.getState().tally.dmgDealt, 0, 'disabled skills never fire — no damage');

  const on = createArena({ hero: meleeHero(), pack, rng: makeRng('iso') });
  on.setDisabled(['attack', 'whirlwind', 'guard']); // only Cleave active
  for (let i = 0; i < 200 && !on.getState().over; i++) on.tick({ x: 0, y: 0 });
  const s = on.getState();
  assert.ok(s.tally.dmgDealt > 0, 'the one active AoE dealt the damage');
  assert.ok(!s.hero.cd.whirlwind, 'the disabled skill never went on cooldown (never fired)');
});

test('a disabled summon never raises a minion; enabling it makes minions appear', () => {
  const necro = { name: 'N', glyph: '💀', maxLife: 600, life: 600, maxMana: 60, mana: 60, manaRegen: 6,
    accuracy: 10, evade: 0, actions: 3, weapon: { dmg: null, wtype: 'focus' }, hard: {}, plusSkills: 0,
    abilities: ['attack', 'raise_skeleton'] };
  const pack = [{ id: 'fallen' }, { id: 'fallen' }];
  const idle = createArena({ hero: { ...necro }, pack, rng: makeRng('m') });
  idle.setDisabled(['attack', 'raise_skeleton', 'guard']);
  let seen = 0; for (let i = 0; i < 150 && !idle.getState().over; i++) { idle.tick({ x: 0, y: 0 }); seen = Math.max(seen, idle.getState().minions.length); }
  assert.equal(seen, 0, 'a disabled summon never fires');

  const cast = createArena({ hero: { ...necro }, pack, rng: makeRng('m') });
  cast.setDisabled(['attack', 'guard']); // raise_skeleton active
  let raised = 0; for (let i = 0; i < 150 && !cast.getState().over; i++) { cast.tick({ x: 0, y: 0 }); raised = Math.max(raised, cast.getState().minions.length); }
  assert.ok(raised > 0, 'the active summon raised minions');
});
