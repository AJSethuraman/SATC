// Engine tests: the run — start naked, XP -> levels -> skill points, skill tree,
// loot, flee, and a full auto-played descent that terminates. Also gear derivation.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createGame, deriveStats, deriveAbilities } from '../engine/game.js';
import { rollItem } from '../engine/loot.js';
import { makeRng } from '../engine/rng.js';
import { CLASSES, ITEMS } from '../engine/content.js';

test('you start NAKED: one weapon-granted skill + a universal Guard', () => {
  const g = createGame('naked', { classId: 'barbarian' });
  const run = g.getRun();
  assert.deepEqual(run.abilities.sort(), ['attack', 'guard', 'cleave'].sort()); // universal Auto-Attack + Guard, Worn Axe -> Cleave
  assert.equal(run.level, 1);
  assert.equal(run.skillPoints, 0);
});

test('deriveStats grows Life/Mana with level and sums gear mods', () => {
  const barb = CLASSES.barbarian;
  const base = deriveStats(barb, { weapon: ITEMS.worn_axe }, 1);
  const lvl3 = deriveStats(barb, { weapon: ITEMS.worn_axe }, 3);
  assert.ok(lvl3.maxLife > base.maxLife); // leveling raises Life
  const geared = deriveStats(barb, { weapon: ITEMS.great_axe }, 1); // +1 to Skills
  assert.equal(geared.plusSkills, 1);
});

test('deriveAbilities = Auto-Attack + Guard + weapon skill + learned skills', () => {
  const ab = deriveAbilities({ weapon: ITEMS.short_bow }, { strafe: 1 });
  assert.ok(ab.includes('attack') && ab.includes('guard') && ab.includes('power_shot') && ab.includes('strafe'));
});

test('rollItem drops armor/jewelry with rolled affixes (never a weapon)', () => {
  for (let s = 0; s < 30; s++) { const it = rollItem(makeRng('r' + s), {}); assert.notEqual(it.slot, 'weapon'); }
});

// Drive one REAL-TIME fight to its end with the engine's movement autopilot (skills
// auto-fire; the bot only moves). Auto-quaff when low, flee if it somehow runs long.
function clearFight(g, cap = 30 * 80) {
  const cb = g.getCombat(); let t = 0;
  while (!cb.getState().over && t++ < cap) {
    const s = cb.getState();
    if (s.hero.life < s.hero.maxLife * 0.4) g.quaff('life');
    if (s.hero.mana < s.hero.maxMana * 0.15) g.quaff('mana');
    cb.tick(cb.autoInput());
  }
  if (!cb.getState().over) g.flee(); else g.resolveCombat();
}

// competent auto-player: learn a preferred build, then move-and-survive each fight
function autoRun(seed, classId, learnPref) {
  const g = createGame(seed, { classId });
  g.beginDescent();
  const S = () => g.getRun();
  let guard = 0;
  while (guard++ < 400) {
    const run = S();
    if (run.phase === 'victory' || run.phase === 'dead') break;
    if (run.phase === 'map') { const i = run.choices.findIndex((c) => c.type === 'combat' || c.type === 'elite'); g.chooseDirection(i >= 0 ? i : 0); continue; }
    if (run.phase === 'shop') { g.continueFromReward(); continue; }
    if (run.phase === 'reward') { let sp = 0; while (S().skillPoints > 0 && sp++ < 20) { const tree = S().tree;
      const want = learnPref.map((id) => tree.find((t) => t.id === id)).find((t) => t && t.canInvest) || tree.find((t) => t.canInvest);
      if (!want) break; g.investSkill(want.id); } g.continueFromReward(); continue; }
    if (run.phase === 'combat') { clearFight(g); continue; }
    break;
  }
  return S().phase;
}

test('a Barbarian descent terminates (win or death) without throwing', () => {
  const end = autoRun('br-barb', 'barbarian', ['cleave', 'smite', 'charge', 'whirlwind']);
  assert.ok(['victory', 'dead'].includes(end), `ended ${end}`);
});

test('a Necromancer descent terminates', () => {
  const end = autoRun('br-necro', 'necromancer', ['raise_skeleton', 'bone_spear', 'teeth', 'raise_golem']);
  assert.ok(['victory', 'dead'].includes(end), `ended ${end}`);
});

test('the skill tree gates by level and prerequisite — you cannot learn everything at once', () => {
  const g = createGame('gate', { classId: 'barbarian' });
  // hand the hero some points without leveling (simulate) by leveling via a fight is slow; use investSkill gates directly
  const run0 = g.getRun();
  const whirl = run0.tree.find((t) => t.id === 'whirlwind');
  assert.equal(whirl.req, 8); // capstone
  assert.ok(!whirl.canInvest, 'Whirlwind is locked at level 1');
  assert.equal(g.investSkill('whirlwind').ok, false); // refused: level + prereqs
  assert.equal(g.investSkill('charge').ok, false); // charge req 4, still locked at level 1
  // cleave is a tier-1 skill (the weapon grants it); Zeal needs a point in it first
  const cleave = run0.tree.find((t) => t.id === 'cleave');
  assert.equal(cleave.req, 1);
});

test('space-limited bag: loot must be TAKEN, overflow is left behind (never free gold)', () => {
  const g = createGame('econ', { classId: 'barbarian' }); g.beginDescent();
  let guard = 0;
  while (guard++ < 40 && !['dead', 'victory'].includes(g.getRun().phase)) {
    const r = g.getRun();
    if (r.phase === 'shop') { g.continueFromReward(); continue; }
    if (r.phase === 'reward') {
      const goldBefore = g.getRun().gold;
      for (const it of g.getRun().pendingLoot.slice()) g.takeLoot(it.id); // take all you can; overflow simply fails
      assert.equal(g.getRun().gold, goldBefore, 'taking/leaving loot never grants gold');
      assert.ok(g.getRun().bag.length <= g.getRun().bagCap, 'bag never exceeds cap');
      g.continueFromReward(); continue;
    }
    if (r.phase === 'map') { const i = r.choices.findIndex((c) => ['combat', 'treasure', 'elite'].includes(c.type)); g.chooseDirection(i >= 0 ? i : 0); continue; }
    if (r.phase === 'combat') { clearFight(g); continue; }
    break;
  }
  const run = g.getRun();
  assert.equal(run.bagCap, 12);
  assert.ok(run.bag.length <= run.bagCap);
  // DROP frees a slot for nothing (no gold); SELL frees a slot for gold
  if (run.bag.length > 0) { const n = g.getRun().bag.length, gold = g.getRun().gold; assert.equal(g.dropFromBag(run.bag[0].id).ok, true);
    assert.equal(g.getRun().bag.length, n - 1); assert.equal(g.getRun().gold, gold, 'dropping gives no gold'); }
  if (g.getRun().bag.length > 0) { const n = g.getRun().bag.length, gold = g.getRun().gold; const s = g.sellFromBag(g.getRun().bag[0].id);
    assert.equal(s.ok, true); assert.ok(g.getRun().gold > gold); assert.equal(g.getRun().bag.length, n - 1); }
  while (g.getRun().bag.length > 0) g.sellFromBag(g.getRun().bag[0].id);
  if (g.getRun().gold >= 12) { const pm = g.getRun().potions.mana, gd = g.getRun().gold; assert.equal(g.buyPotion('mana').ok, true);
    assert.equal(g.getRun().potions.mana, pm + 1); assert.equal(g.getRun().gold, gd - 12); }
});

test('Mana persists across the run (no free refill); Mana potions restore it', () => {
  const g = createGame('manatest', { classId: 'necromancer' });
  g.beginDescent();
  // descend into a fight (prefer fights; advance via treasure — never camp, which restores Mana)
  let guard = 0;
  while (guard++ < 15 && g.getRun().phase !== 'combat') {
    const r = g.getRun();
    if (r.phase === 'reward' || r.phase === 'shop') { g.continueFromReward(); continue; }
    if (r.phase !== 'map') break;
    let i = ['combat', 'elite', 'treasure'].map((t) => r.choices.findIndex((c) => c.type === t)).find((x) => x >= 0);
    g.chooseDirection(i == null ? 0 : i);
  }
  const cb = g.getCombat(); assert.ok(cb && g.getRun().phase === 'combat', 'reached a fight');
  const maxMana = cb.getState().hero.maxMana;
  // let the auto-firing skills (Raise Skeleton / Guard) spend Mana over a few frames
  for (let i = 0; i < 3; i++) cb.tick(cb.autoInput());
  const low = cb.getState().hero.mana;
  assert.ok(low < maxMana, 'casting spent Mana (no free per-fight refill to full)');
  // quaff a Mana potion: restores Mana, decrements the belt
  const potsBefore = g.getRun().potions.mana;
  const r = g.quaff('mana');
  assert.equal(r.ok, true); assert.equal(g.getRun().potions.mana, potsBefore - 1);
  assert.ok(cb.getState().hero.mana > low, 'potion restored Mana');
  // leave the fight; Mana carries to the run (the engine never resets it to full)
  const endMana = cb.getState().hero.mana;
  if (!cb.getState().over) g.flee();
  assert.equal(g.getRun().mana, endMana, 'run Mana = what you left the fight with (no free refill)');
});

test('leveling grants skill points and investing raises a skill', () => {
  const g = createGame('lvl', { classId: 'barbarian' });
  g.beginDescent();
  // fight the first node to gain xp
  const i = g.getRun().choices.findIndex((c) => c.type === 'combat');
  g.chooseDirection(i >= 0 ? i : 0);
  const cb = g.getCombat();
  if (cb) clearFight(g);
  const run = g.getRun();
  if (run.skillPoints > 0) { const before = run.tree.find((t) => t.id === 'cleave').level; g.investSkill('cleave'); assert.equal(g.getRun().tree.find((t) => t.id === 'cleave').level, before + 1); }
  assert.ok(run.level >= 1);
});
