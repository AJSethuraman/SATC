// S6 — town / checkpoint loop. An ACT is ordered quests; you clear ONE quest per
// field descent then return to TOWN to bank/turn-in/respec before the next. The
// `stash` PERSISTS across runs; the run inventory (`bag`) is at-risk — banked in
// town it survives, unbanked it is forfeited on death. All at the engine seam.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame } from '../engine/game.js';
import { CLASSES } from '../engine/content.js';

const mk = (id, over = {}) => ({ id, slot: 'helm', rarity: 'magic', itemTier: 'Normal', passive: { maxLife: 10 }, req: {}, ...over });
// A tanky + hard-hitting starting loadout so a survival segment reliably CLEARS its
// gate and reaches the next town (survivability/clear-speed shouldn't be the thing
// under test in the town-loop suite — that's the balance harness's job).
const BEEF = [
  mk('beef-body', { slot: 'body', passive: { maxLife: 70 } }),
  mk('beef-helm', { slot: 'helm', passive: { maxLife: 45 } }),
  mk('beef-boots', { slot: 'boots', passive: { maxLife: 45 } }),
  mk('beef-gloves', { slot: 'gloves', passive: { maxLife: 45 } }),
  { id: 'god-axe', slot: 'weapon', wtype: 'melee', dmg: [300, 400], grants: { skill: 'cleave' }, rarity: 'unique', itemTier: 'Normal', req: {}, passive: {} },
];

// Drive one field segment: move (autopilot), auto-quaff, greedily invest.
function survive(g, maxTicks) {
  const cb = g.getCombat(); let t = 0;
  while (cb && !cb.getState().over && t++ < maxTicks) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.45) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
    const sync = g.syncArena();
    if (sync.leveled) { const inv = g.getRun().tree.find((x) => x.canInvest); if (inv) g.investSkill(inv.id); }
  }
}

test('a fresh game starts in TOWN at the first quest; descend needs town', () => {
  const g = createGame('town-start', { classId: 'barbarian' });
  const r = g.getRun();
  assert.equal(r.phase, 'town');
  assert.equal(r.questIdx, 0);
  assert.equal(r.quests.length, 8, 'Act 1 = 8 quests');
  assert.ok(g.descend().ok, 'can descend from town');
  assert.equal(g.getRun().phase, 'arena');
  assert.equal(g.descend().ok, false, 'cannot descend again mid-field');
});

test('clearing a quest turns it in and returns to TOWN at the next quest', () => {
  const g = createGame('town-quest', { classId: 'barbarian' });
  g.descend();
  survive(g, 30 * 160);
  const r = g.getRun();
  assert.equal(r.phase, 'town', `expected town, got ${r.phase}`);
  assert.equal(r.questIdx, 1, 'advanced to quest 2');
  assert.ok(r.quests[0].done, 'quest 1 turned in');
});

test('banking moves the run inventory into the stash — and ONLY in town', () => {
  const g = createGame('town-bank', { classId: 'barbarian', stash: BEEF, loadout: BEEF });
  g.descend();
  assert.equal(g.bankAll().ok, false, 'cannot bank mid-field');
  survive(g, 30 * 160);
  assert.equal(g.getRun().phase, 'town');
  const bagN = g.getRun().bag.length, stashN = g.getRun().stash.length;
  const res = g.bankAll();
  assert.ok(res.ok);
  assert.equal(g.getRun().bag.length, 0, 'bag emptied into the stash');
  assert.equal(g.getRun().stash.length, stashN + bagN, 'every banked item landed in the stash');
});

test('death forfeits the unbanked run inventory; the persistent stash survives', () => {
  const g = createGame('town-death', { classId: 'sorceress', stash: [mk('s1'), mk('s2')] });
  g.descend();
  const cb = g.getCombat();
  // stand still, do not quaff: a level-1 Sorceress is overwhelmed and dies
  for (let i = 0; i < 30 * 90 && g.getRun().phase === 'arena'; i++) { cb.tick({ x: 0, y: 0 }); g.syncArena(); }
  const r = g.getRun();
  assert.equal(r.phase, 'dead', 'standing still got her killed');
  assert.equal(r.bag.length, 0, 'unbanked loot was forfeited');
  assert.equal(r.stash.length, 2, 'the stash persisted through death');
});

test('one free respec per act refunds skills + attributes, then refuses', () => {
  const g = createGame('town-respec', { classId: 'barbarian', stash: BEEF, loadout: BEEF });
  g.descend();
  survive(g, 30 * 160);
  assert.equal(g.getRun().phase, 'town');
  // spend some points
  const inv = g.getRun().tree.find((t) => t.canInvest); if (inv) g.investSkill(inv.id);
  while (g.getRun().attrPoints > 0) if (!g.investAttr('str').ok) break;
  const spentSkills = Object.values(g.getRun().tree).filter((t) => t.level > 1 && !t.passive).length;
  assert.ok(g.getRun().canRespec, 'respec available in town this act');
  const res = g.respec();
  assert.ok(res.ok);
  assert.deepEqual(g.getRun().attr, CLASSES.barbarian.attr, 'attributes reset to the class base');
  assert.ok(g.getRun().attrPoints > 0 || spentSkills === 0, 'attribute points were refunded');
  assert.equal(g.respec().ok, false, 'only one respec per act');
  assert.equal(g.getRun().canRespec, false);
});

test('starting loadout equips chosen stash gear (a copy); the stash is retained', () => {
  const helm = mk('load-helm', { passive: { maxLife: 14 } });
  const g = createGame('town-load', { classId: 'sorceress', stash: [helm], loadout: [helm] });
  const r = g.getRun();
  assert.ok(r.equipment.helm && r.equipment.helm.passive.maxLife === 14, 'started wearing the loadout helm');
  assert.equal(r.stash.length, 1, 'the stash kept the original (loadout is a copy)');
  // gear you cannot meet the requirement for is silently skipped
  const g2 = createGame('town-load2', { classId: 'sorceress', loadout: [mk('heavy', { slot: 'body', req: { str: 99 } })] });
  assert.equal(g2.getRun().equipment.body, null, 'a too-heavy loadout item is not force-equipped');
});

test('equipFromStash draws a COPY onto the character (town only), stash unchanged', () => {
  const ring = mk('r1', { slot: 'ring', rarity: 'rare', passive: { maxLife: 20 }, req: {} });
  const g = createGame('town-eq', { classId: 'sorceress', stash: [ring] });
  const res = g.equipFromStash('r1');
  assert.ok(res.ok);
  assert.ok(g.getRun().equipment.ring1, 'ring is now worn');
  assert.equal(g.getRun().stash.length, 1, 'stash still holds the original');
  // not allowed once you have descended into the field
  g.descend();
  assert.equal(g.equipFromStash('r1').ok, false, 'no stash access in the field');
});

test('the stash is injected + read back — the UI persistence seam', () => {
  const carried = [mk('keep1', { slot: 'ring', rarity: 'rare' }), mk('keep2')];
  const g = createGame('persist', { classId: 'necromancer', stash: carried });
  assert.equal(g.getRun().stash.length, 2);
  assert.deepEqual(g.getStash().map((i) => i.id).sort(), ['keep1', 'keep2']);
});
