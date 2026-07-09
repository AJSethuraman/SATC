// S5 — Str/Dex/Vit/Energy attribute economy + equip requirement gates. Attributes
// reset every run, you earn ~5 points/level, Vit->Life and Energy->Mana, and
// Str/Dex GATE what gear you can wear — so a greedy all-Energy caster is locked out
// of heavy Str/Dex gear until they invest. All at the deterministic engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveStats } from '../engine/game.js';
import { CLASSES } from '../engine/content.js';

const SORC = CLASSES.sorceress;
const BASE = { str: 10, dex: 25, vit: 10, energy: 35 };

test('Vitality raises max Life; Energy raises max Mana + regen', () => {
  const base = deriveStats(SORC, {}, 1, BASE);
  const hiVit = deriveStats(SORC, {}, 1, { ...BASE, vit: 40 });
  const hiEnergy = deriveStats(SORC, {}, 1, { ...BASE, energy: 80 });
  assert.ok(hiVit.maxLife > base.maxLife, 'more Vit -> more Life');
  assert.ok(hiEnergy.maxMana > base.maxMana, 'more Energy -> more Mana');
  assert.ok(hiEnergy.manaRegen >= base.manaRegen, 'more Energy -> at least as much regen');
  // exact: each Vit point is worth a fixed slab of Life
  assert.equal(hiVit.maxLife - base.maxLife, (40 - 10) * 4);
});

test('gear +Vit / +Energy also feed Life / Mana (not just invested points)', () => {
  const bare = deriveStats(SORC, {}, 1, BASE);
  const geared = deriveStats(SORC, { helm: { passive: { vit: 10, energy: 10 } } }, 1, BASE);
  assert.ok(geared.maxLife > bare.maxLife && geared.maxMana > bare.maxMana);
});

test('equip is REFUSED under a Str / Dex / level requirement, allowed when met', () => {
  const g = createGame('attr-gate', { classId: 'sorceress' }); // base Str 10, Dex 25, level 1
  // a greedy caster cannot wear a Plate (Str 40) or a War Bow (Dex 36) yet
  assert.equal(g.canEquip({ req: { str: 40 } }).ok, false);
  assert.equal(g.canEquip({ req: { dex: 36 } }).ok, false);
  assert.equal(g.canEquip({ req: { level: 6 } }).ok, false);
  // within her means, it's allowed
  assert.equal(g.canEquip({ req: { str: 10, dex: 25, level: 1 } }).ok, true);
  assert.equal(g.canEquip({ req: {} }).ok, true);
  assert.equal(g.canEquip({}).ok, true, 'no req = wearable');
  // the refusal carries a visible reason (not a silent ignore)
  assert.match(g.canEquip({ req: { str: 40 } }).reason, /Str/);
});

test('attributes reset to the class base every run; no points pre-spent', () => {
  const g = createGame('attr-reset', { classId: 'sorceress' });
  const r = g.getRun();
  assert.deepEqual(r.attr, SORC.attr);
  assert.equal(r.attrPoints, 0);
});

// Drive a survival run far enough to level up (the autopilot moves + auto-quaffs).
function survive(g, maxTicks) {
  const cb = g.getCombat(); let t = 0;
  while (!cb.getState().over && t++ < maxTicks) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.4) g.quaff('life');
    cb.tick(cb.autoInput());
    g.syncArena();
  }
}

test('leveling grants attribute points; investing spends them and unlocks gear', () => {
  const g = createGame('attr-invest', { classId: 'sorceress', difficulty: 'Normal' });
  g.startRun();
  survive(g, 30 * 120);
  const r = g.getRun();
  assert.ok(r.level > 1, 'leveled up while surviving');
  assert.ok(r.attrPoints >= 5, `earned ~5 attr points per level (got ${r.attrPoints} at level ${r.level})`);
  // pour points into Str until a Str-40 Plate becomes wearable
  const before = g.getRun().attrPoints;
  const need = 40 - g.getRun().attr.str;
  let spent = 0;
  for (let i = 0; i < need && g.getRun().attrPoints > 0; i++) { if (g.investAttr('str').ok) spent++; }
  assert.equal(g.getRun().attr.str, SORC.attr.str + spent, 'invested points raised Str');
  assert.equal(g.getRun().attrPoints, before - spent, 'points were consumed');
  if (spent === need) assert.equal(g.canEquip({ req: { str: 40 } }).ok, true, 'enough Str now wears the Plate');
});

test('investing Vitality raises current usable Life immediately', () => {
  const g = createGame('attr-vit', { classId: 'sorceress', difficulty: 'Normal' });
  g.startRun();
  survive(g, 30 * 120);
  if (g.getRun().attrPoints > 0) {
    const beforeMax = g.getRun().maxLife;
    g.investAttr('vit');
    assert.ok(g.getRun().maxLife > beforeMax, 'max Life rose with the Vitality point');
  }
});

test('investAttr with no points, or a bad key, is refused', () => {
  const g = createGame('attr-nopts', { classId: 'sorceress' });
  assert.equal(g.investAttr('str').ok, false, 'no points at level 1');
  assert.equal(g.investAttr('luck').ok, false, 'unknown attribute rejected');
});
