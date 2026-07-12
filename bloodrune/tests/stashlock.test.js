// STASH DEPOSIT LOCK — banking an item during a town visit COMMITS it to storage:
// it can't be equipped/withdrawn again THIS visit, only after you START the next
// descent. The stash still persists across runs and survives death. Engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';

const mk = (id, over = {}) => ({ id, slot: 'helm', rarity: 'magic', itemTier: 'Normal', passive: { maxLife: 10 }, req: {}, ...over });

// A tanky loadout so a segment reliably clears its gate and returns to town.
const BEEF = [
  mk('beef-body', { slot: 'body', passive: { maxLife: 70 } }),
  mk('beef-helm', { slot: 'helm', passive: { maxLife: 45 } }),
  mk('beef-boots', { slot: 'boots', passive: { maxLife: 45 } }),
  mk('beef-gloves', { slot: 'gloves', passive: { maxLife: 45 } }),
  { id: 'god-axe', slot: 'weapon', wtype: 'melee', dmg: [300, 400], grants: { skill: 'cleave' }, rarity: 'unique', itemTier: 'Normal', req: {}, passive: {} },
];
function survive(g, maxTicks) {
  const cb = g.getCombat(); let t = 0;
  while (cb && !cb.getState().over && t++ < maxTicks) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.45) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
    g.syncArena();
  }
}

test('an item banked THIS visit is locked: equipFromStash refuses it', () => {
  const g = createGame('lock-bank', { classId: 'sorceress', bag: [mk('loot', { slot: 'ring', rarity: 'rare' })] });
  assert.ok(g.bank('loot').ok, 'banked from bag into stash');
  const stashItem = g.getRun().stash.find((x) => x.id === 'loot');
  assert.equal(stashItem.locked, true, 'freshly banked item is flagged locked');
  const res = g.equipFromStash('loot');
  assert.equal(res.ok, false);
  assert.equal(res.reason, 'locked until next descent');
  assert.ok(!g.getRun().equipment.ring1, 'nothing got equipped');
});

test('prior-visit stash stays usable; only freshly-banked-this-visit locks', () => {
  // 'old' arrives via opts.stash (a prior visit) — usable now. 'fresh' is banked this
  // visit — locked. Equipping the old one still works.
  const g = createGame('lock-mix', { classId: 'sorceress',
    stash: [mk('old', { slot: 'ring', rarity: 'rare' })],
    bag: [mk('fresh', { slot: 'body', rarity: 'rare', passive: { maxLife: 20 } })] });
  assert.ok(g.bank('fresh').ok);
  assert.equal(g.equipFromStash('fresh').ok, false, 'this-visit deposit is locked');
  assert.ok(g.equipFromStash('old').ok, 'a prior-visit stash item is still usable');
  assert.ok(g.getRun().equipment.ring1, 'the old ring got equipped');
});

test('descend UNLOCKS banked gear; back in town it is usable, stash survives death', () => {
  const g = createGame('lock-descend', { classId: 'barbarian', stash: BEEF, loadout: BEEF,
    bag: [mk('spoil', { slot: 'ring', rarity: 'rare', passive: { maxLife: 20 } })] });
  assert.ok(g.bank('spoil').ok);
  assert.equal(g.equipFromStash('spoil').ok, false, 'locked before the next descent');

  g.descend(); // starting the next descent frees the deposit
  assert.equal(g.getRun().stash.find((x) => x.id === 'spoil').locked, undefined, 'descend cleared the lock');
  survive(g, 30 * 320);
  assert.equal(g.getRun().phase, 'town', 'returned to town');

  const res = g.equipFromStash('spoil');
  assert.ok(res.ok, 'now usable after the descent');
  assert.ok(g.getRun().equipment.ring1, 'the once-locked ring is equipped');
  assert.equal(g.getRun().stash.length, BEEF.length + 1, 'stash kept the original (equip drew a copy)');
});

test('a locked deposit is refused by a loadout too; the stash persists across runs', () => {
  // Bank an item this visit -> it locks. Persisted via getStash, the lock is dropped
  // (a committed store), so a NEW run built from that stash starts fully usable.
  const g = createGame('lock-persist', { classId: 'sorceress',
    bag: [mk('keep', { slot: 'ring', rarity: 'rare' })] });
  g.bank('keep');
  const persisted = g.getStash();
  assert.equal(persisted.find((x) => x.id === 'keep').locked, undefined, 'persistence strips the within-visit lock');

  // a fresh run seeded from the persisted stash can equip it immediately
  const g2 = createGame('lock-persist2', { classId: 'sorceress', stash: persisted, loadout: ['keep'] });
  assert.ok(g2.getRun().equipment.ring1, 'reloaded stash item equipped via loadout');
});

test('a stash item locked THIS visit is skipped by a mid-visit loadout draw', () => {
  const g = createGame('lock-load', { classId: 'sorceress',
    bag: [mk('banked', { slot: 'ring', rarity: 'rare' })] });
  g.bank('banked');
  // applyLoadout runs at construction, but we can prove the guard via equipFromStash;
  // for the loadout path, a fresh game whose stash carries a still-locked item skips it.
  const lockedStash = g.getRun().stash.map((i) => ({ ...i })); // keeps locked:true
  const g2 = createGame('lock-load2', { classId: 'sorceress', stash: lockedStash, loadout: ['banked'] });
  assert.ok(!g2.getRun().equipment.ring1, 'a locked stash item is not force-drawn into a loadout');
});
