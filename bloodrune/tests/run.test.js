// Engine tests: the SURVIVORS run — start naked, drop into one big arena, XP ->
// levels -> skill points, monsters DROP loot you collect (auto-equip upgrades), and
// the run ends in victory (boss) or death. Also gear/ability derivation + economy.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveStats, deriveAbilities } from '../engine/game.js';
import { rollItem } from '../engine/loot.js';
import { makeRng } from '../engine/rng.js';
import { CLASSES, ITEMS } from '../engine/content.js';

test('you start NAKED: one weapon-granted skill + a universal Guard', () => {
  const g = createGame('naked', { classId: 'barbarian' });
  const run = g.getRun();
  assert.deepEqual(run.abilities.sort(), ['attack', 'guard', 'cleave'].sort());
  assert.equal(run.level, 1); assert.equal(run.skillPoints, 0);
});

test('deriveStats grows Life/Mana with level and sums gear mods', () => {
  const barb = CLASSES.barbarian;
  const base = deriveStats(barb, { weapon: ITEMS.worn_axe }, 1);
  const lvl3 = deriveStats(barb, { weapon: ITEMS.worn_axe }, 3);
  assert.ok(lvl3.maxLife > base.maxLife);
  const geared = deriveStats(barb, { weapon: ITEMS.great_axe }, 1);
  assert.equal(geared.plusSkills, 1);
});

test('deriveAbilities = Auto-Attack + Guard + weapon skill + learned skills', () => {
  const ab = deriveAbilities({ weapon: ITEMS.short_bow }, { strafe: 1 });
  assert.ok(ab.includes('attack') && ab.includes('guard') && ab.includes('power_shot') && ab.includes('strafe'));
});

test('rollItem drops armor/jewelry with rolled affixes (never a weapon)', () => {
  for (let s = 0; s < 30; s++) { const it = rollItem(makeRng('r' + s), {}); assert.notEqual(it.slot, 'weapon'); }
});

// Drive a survival run with the movement autopilot; auto-quaff, greedily spend points.
function survive(g, maxTicks) {
  const cb = g.getCombat(); let t = 0; let collected = 0, levels = 0;
  while (!cb.getState().over && t++ < maxTicks) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.4) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
    const sync = g.syncArena(); collected += sync.loot.length; levels += sync.leveled;
    if (sync.leveled) { const r = g.getRun(); const w = r.tree.find((x) => x.canInvest); if (w) g.investSkill(w.id); }
  }
  return { s: cb.getState(), collected, levels };
}

// Play the whole ACT: descend from town into each quest, survive the segment,
// bank + return to town between quests, until the act is won or the hero dies.
function playAct(g, perSegmentTicks) {
  for (let guard = 0; guard < 40; guard++) {
    const p = g.getRun().phase;
    if (p === 'victory' || p === 'dead') break;
    if (p === 'town') { g.bankAll(); if (!g.descend().ok) break; }
    survive(g, perSegmentTicks);
  }
  return g.getRun().phase;
}

test('a survival run terminates in victory or death (across the town loop)', () => {
  const g = createGame('sv-term', { classId: 'amazon', difficulty: 'Normal' });
  const phase = playAct(g, 30 * 90); // per-quest hard cap; enrage guarantees each gate resolves
  assert.ok(['victory', 'dead'].includes(phase), `ended ${phase}`);
});

test('monsters drop loot the hero collects — into gear or the bag', () => {
  // an Amazon farms reliably (ranged: kills while kiting, the magnet vacuums the
  // drops) — we're testing the drop->collect->bag pipeline, not a class's survival.
  let evidence = 0;
  for (const seed of ['loot-a', 'loot-b', 'loot-c']) {
    const g = createGame(seed, { classId: 'amazon', difficulty: 'Normal' }); g.startRun();
    const before = Object.values(g.getRun().equipment).filter(Boolean).length;
    const { collected } = survive(g, 30 * 200);
    const r = g.getRun();
    evidence += collected + Math.max(0, Object.values(r.equipment).filter(Boolean).length - before) + r.bag.length;
  }
  assert.ok(evidence > 0, 'monster drops were collected — into gear or the bag');
});

test('leveling during a run grants skill points; investing raises a skill', () => {
  const g = createGame('sv-lvl', { classId: 'necromancer', difficulty: 'Normal' });
  g.startRun();
  const { levels } = survive(g, 30 * 90);
  assert.ok(g.getRun().level > 1 && levels > 0, 'leveled up while surviving');
  // if a point remains, spending it raises a skill's level
  const r = g.getRun();
  const spendable = r.tree.find((t) => t.canInvest);
  if (spendable) { const before = spendable.level; g.investSkill(spendable.id);
    assert.equal(g.getRun().tree.find((t) => t.id === spendable.id).level, before + 1); }
});

test('Mana persists and Mana potions restore it (no free refill)', () => {
  const g = createGame('sv-mana', { classId: 'necromancer', difficulty: 'Normal' });
  g.startRun();
  const cb = g.getCombat(); const maxMana = cb.getState().hero.maxMana;
  // tick until the first wave arrives and an auto-fired skill spends Mana
  let guard = 0; while (cb.getState().hero.mana >= maxMana && !cb.getState().over && guard++ < 300) cb.tick(cb.autoInput());
  const low = cb.getState().hero.mana;
  assert.ok(low < maxMana, 'casting spent Mana');
  const potsBefore = g.getRun().potions.mana;
  const r = g.quaff('mana');
  assert.equal(r.ok, true); assert.equal(g.getRun().potions.mana, potsBefore - 1);
  assert.ok(cb.getState().hero.mana > low, 'potion restored Mana');
});

test('the skill tree gates by level and prerequisite — you cannot learn everything at once', () => {
  const g = createGame('gate', { classId: 'barbarian' });
  const run0 = g.getRun();
  const whirl = run0.tree.find((t) => t.id === 'whirlwind');
  assert.equal(whirl.req, 8); assert.ok(!whirl.canInvest, 'Whirlwind locked at level 1');
  assert.equal(g.investSkill('whirlwind').ok, false);
  assert.equal(g.investSkill('charge').ok, false);
  assert.equal(run0.tree.find((t) => t.id === 'cleave').req, 1);
});

test('bag economy: DROP frees a slot for nothing; SELL frees it for gold; gold buys potions', () => {
  const g = createGame('sv-econ', { classId: 'amazon', difficulty: 'Normal' });
  g.startRun();
  survive(g, 30 * 150); // collect some spoils
  const r = g.getRun();
  assert.equal(r.bagCap, 12); assert.ok(r.bag.length <= r.bagCap);
  if (r.bag.length > 0) { const n = r.bag.length, gold = r.gold;
    assert.equal(g.dropFromBag(r.bag[0].id).ok, true);
    assert.equal(g.getRun().bag.length, n - 1); assert.equal(g.getRun().gold, gold, 'dropping gives no gold'); }
  if (g.getRun().bag.length > 0) { const n = g.getRun().bag.length, gold = g.getRun().gold;
    assert.equal(g.sellFromBag(g.getRun().bag[0].id).ok, true);
    assert.ok(g.getRun().gold > gold); assert.equal(g.getRun().bag.length, n - 1); }
  while (g.getRun().bag.length > 0) g.sellFromBag(g.getRun().bag[0].id);
  if (g.getRun().gold >= 12) { const pm = g.getRun().potions.mana, gd = g.getRun().gold;
    assert.equal(g.buyPotion('mana').ok, true);
    assert.equal(g.getRun().potions.mana, pm + 1); assert.equal(g.getRun().gold, gd - 12); }
});
