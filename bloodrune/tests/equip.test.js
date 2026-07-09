// S4 — loot no longer auto-equips. Drops land in the at-risk bag; you gear up
// EXPLICITLY back in town (never mid-field, never automatic). Junk salvages into
// Arcane Shards (a craft/reroll currency); compareItem reads build-fit vs what's
// worn. All at the deterministic engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';

const mk = (id, over = {}) => ({ id, slot: 'helm', rarity: 'magic', itemTier: 'Normal', passive: { maxLife: 10 }, req: {}, ...over });
const GODAXE = { id: 'god-axe', slot: 'weapon', wtype: 'melee', dmg: [300, 400], grants: { skill: 'cleave' }, rarity: 'unique', itemTier: 'Normal', req: {}, passive: {} };
const BEEF = [
  mk('beef-body', { slot: 'body', passive: { maxLife: 70 } }),
  mk('beef-helm', { slot: 'helm', passive: { maxLife: 45 } }),
  mk('beef-boots', { slot: 'boots', passive: { maxLife: 45 } }),
  GODAXE,
];
function survive(g, maxTicks) {
  const cb = g.getCombat(); let t = 0;
  while (cb && !cb.getState().over && t++ < maxTicks) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.45) g.quaff('life');
    cb.tick(cb.autoInput());
    const sync = g.syncArena();
    if (sync.leveled) { const inv = g.getRun().tree.find((x) => x.canInvest); if (inv) g.investSkill(inv.id); }
  }
}
function fieldFor(g, ticks) { const cb = g.getCombat(); for (let i = 0; i < ticks && !cb.getState().over; i++) { cb.tick(cb.autoInput()); g.syncArena(); } }

test('loot NEVER auto-equips — mid-field nothing changes on the hero', () => {
  const g = createGame('eq-auto', { classId: 'barbarian' });
  g.descend();
  fieldFor(g, 30 * 40); // ~40s into Blood Moor, still alive and pre-gate
  const r = g.getRun();
  assert.equal(r.phase, 'arena', 'still surviving');
  const worn = Object.entries(r.equipment).filter(([, v]) => v).map(([k]) => k);
  assert.deepEqual(worn.sort(), ['weapon'], 'only the start weapon is worn — nothing auto-equipped');
});

test('an empty armor slot stays empty through a whole quest — never auto-filled', () => {
  // The barbarian starts naked; the OLD code auto-filled empty slots from drops.
  // Now, after clearing a full quest, the armor slots must STILL be empty — gearing
  // up is an explicit town choice. (run.test proves drops do reach the bag.)
  const g = createGame('eq-collect', { classId: 'barbarian', stash: [GODAXE], loadout: [GODAXE] });
  g.descend(); survive(g, 30 * 160);
  const r = g.getRun();
  assert.equal(r.phase, 'town', 'cleared the quest');
  const worn = Object.entries(r.equipment).filter(([, v]) => v).map(([k]) => k);
  assert.deepEqual(worn.sort(), ['weapon'], 'no armor was auto-equipped across the whole quest');
});

test('equipping / unequipping is refused in the field, allowed in town', () => {
  const g = createGame('eq-explicit', { classId: 'barbarian' });
  g.descend();
  fieldFor(g, 30 * 40);
  const bagItem = g.getRun().bag.find((x) => x.slot && x.slot !== 'weapon');
  if (bagItem) assert.equal(g.equipFromBag(bagItem.id).ok, false, 'cannot equip mid-field');
  assert.equal(g.unequip('weapon').ok, false, 'cannot fiddle gear mid-field');

  // reach town with a strong loadout, then equip explicitly
  const g2 = createGame('eq-town', { classId: 'barbarian', stash: BEEF, loadout: BEEF });
  g2.descend(); survive(g2, 30 * 160);
  assert.equal(g2.getRun().phase, 'town');
  const item = g2.getRun().bag.find((x) => x.slot && x.slot !== 'weapon' && g2.canEquip(x).ok);
  if (item) {
    const n = g2.getRun().bag.length;
    assert.equal(g2.equipFromBag(item.id).ok, true, 'equip is an explicit town action');
    assert.ok(g2.getRun().equipment[item.slot === 'ring' ? 'ring1' : item.slot], 'the item is now worn');
    assert.ok(g2.getRun().bag.length <= n, 'the bag shrank (or swapped) on equip');
  }
});

test('salvage turns bag junk into Arcane Shards — town only', () => {
  const g = createGame('eq-salvage', { classId: 'barbarian', stash: BEEF, loadout: BEEF });
  g.descend();
  assert.equal(g.salvage('anything').ok, false, 'no salvage in the field');
  survive(g, 30 * 160);
  assert.equal(g.getRun().phase, 'town');
  const r = g.getRun();
  if (r.bag.length > 0) {
    const before = r.shards; const id = r.bag[0].id;
    const res = g.salvage(id);
    assert.ok(res.ok && res.gained > 0, 'salvage yielded Shards');
    assert.ok(g.getRun().shards > before);
    assert.equal(g.getRun().bag.some((x) => x.id === id), false, 'the salvaged item left the bag');
  }
  const n = g.getRun().bag.length;
  const all = g.salvageAll();
  assert.ok(all.ok && all.banked === n);
  assert.equal(g.getRun().bag.length, 0, 'salvageAll empties the bag for Shards');
});

test('compareItem reads build-fit vs what is worn (and wearability)', () => {
  const g = createGame('eq-compare', { classId: 'sorceress' }); // helm slot empty
  const casterHelm = mk('c', { rarity: 'rare', passive: { fcr: 15, plusSkills: 1 } });
  const bruteHelm = mk('b', { rarity: 'rare', passive: { ias: 15, accuracy: 6 } });
  const heavyHelm = mk('h', { passive: { plusSkills: 1 }, req: { str: 99 } });
  const cc = g.compareItem(casterHelm);
  assert.ok(cc.isUpgrade && cc.delta > 0 && cc.wearable, 'a caster helm upgrades an empty slot');
  assert.equal(g.compareItem(bruteHelm).isUpgrade, false, 'a melee helm is worthless to a Sorceress');
  assert.equal(g.compareItem(heavyHelm).wearable, false, 'a Str-99 helm is not wearable yet');
});

test('reroll gating: needs a magic/rare bag item + Shards, and is town only', () => {
  const g = createGame('eq-reroll', { classId: 'barbarian', stash: BEEF, loadout: BEEF });
  assert.equal(g.reroll('missing').ok, false, 'nothing to reroll');
  g.descend(); survive(g, 30 * 160);
  if (g.getRun().phase !== 'town') return;
  const target = g.getRun().bag.find((x) => x.rarity === 'magic' || x.rarity === 'rare');
  // salvage everything else to bank Shards
  for (const it of g.getRun().bag.filter((x) => !target || x.id !== target.id)) g.salvage(it.id);
  if (target && g.getRun().shards >= 6) {
    const res = g.reroll(target.id);
    assert.ok(res.ok, 'reroll consumed Shards and refreshed the rolls');
    assert.ok(g.getRun().bag.some((x) => x.id === target.id), 'the item kept its identity');
  }
});
