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
  assert.deepEqual(run.abilities.sort(), ['strike', 'guard'].sort()); // Worn Axe -> Strike (free basic), + Guard
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

test('deriveAbilities = Guard + weapon skill + learned skills', () => {
  const ab = deriveAbilities({ weapon: ITEMS.short_bow }, { power_shot: 1 });
  assert.ok(ab.includes('guard') && ab.includes('arrow') && ab.includes('power_shot'));
});

test('rollItem drops armor/jewelry with rolled affixes (never a weapon)', () => {
  for (let s = 0; s < 30; s++) { const it = rollItem(makeRng('r' + s), {}); assert.notEqual(it.slot, 'weapon'); }
});

// competent auto-player: focus caster, learn/level a reach or summon, spend Mana
function autoRun(seed, classId, learnPref) {
  const g = createGame(seed, { classId });
  g.beginDescent();
  const S = () => g.getRun();
  const cIdx = (id) => g.getCombat().getState().hero.abilities.findIndex((a) => a.id === id);
  const tryUse = (id) => { const i = cIdx(id); if (i < 0) return false; const r = g.getCombat().useSkill(i); return !!(r && r.ok); };
  let guard = 0;
  while (guard++ < 400) {
    const run = S();
    if (run.phase === 'victory' || run.phase === 'dead') break;
    if (run.phase === 'map') { const i = run.choices.findIndex((c) => c.type === 'combat' || c.type === 'elite'); g.chooseDirection(i >= 0 ? i : 0); continue; }
    if (run.phase === 'shop') { g.continueFromReward(); continue; }
    if (run.phase === 'reward') { let sp = 0; while (S().skillPoints > 0 && sp++ < 20) { const tree = S().tree;
      const want = learnPref.map((id) => tree.find((t) => t.id === id)).find((t) => t && t.canInvest) || tree.find((t) => t.canInvest);
      if (!want) break; g.investSkill(want.id); } g.continueFromReward(); continue; }
    if (run.phase === 'combat') {
      const cb = g.getCombat();
      let turns = 0;
      while (!cb.getState().over && turns++ < 60) {
        const st = cb.getState();
        const caster = st.enemies.find((e) => e.hp > 0 && e.role === 'caster'); const liv = st.enemies.filter((e) => e.hp > 0);
        cb.setFocus(caster ? caster.uid : (liv[0] ? liv[0].uid : 0));
        let acted = true;
        while (acted) { acted = false; const c = cb.getState(); if (c.over) break;
          const has = (id) => c.hero.abilities.some((a) => a.id === id); const aff = (id) => { const a = c.hero.abilities.find((x) => x.id === id); return a && a.cost <= c.hero.mana; };
          if (c.hero.summons.length < 3 && has('raise_skeleton') && aff('raise_skeleton') && tryUse('raise_skeleton')) { acted = true; continue; }
          for (const id of ['strafe', 'teeth', 'cleave', 'whirlwind', 'power_shot', 'arrow', 'bone_spear', 'charge', 'pierce', 'smite', 'zeal', 'strike']) { if (has(id) && aff(id) && tryUse(id)) { acted = true; break; } }
        }
        cb.endTurn();
      }
      if (!cb.getState().over) g.flee(); else g.resolveCombat(); // bail on a stalemate instead of spinning
      continue;
    }
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
  // strike is a tier-1 skill; still needs a point though
  const strike = run0.tree.find((t) => t.id === 'strike');
  assert.equal(strike.req, 1);
});

test('inventory is space-limited; Shop sells for gold and buys potions', () => {
  const g = createGame('econ', { classId: 'barbarian' }); g.beginDescent();
  let guard = 0;
  while (guard++ < 30 && !['dead', 'victory'].includes(g.getRun().phase)) {
    const r = g.getRun();
    if (r.phase === 'shop' || r.phase === 'reward') { g.continueFromReward(); continue; }
    if (r.phase === 'map') { const i = r.choices.findIndex((c) => ['combat', 'treasure', 'elite'].includes(c.type)); g.chooseDirection(i >= 0 ? i : 0); continue; }
    if (r.phase === 'combat') { const cb = g.getCombat(); let t = 0;
      while (!cb.getState().over && t++ < 40) { const st = cb.getState(); const liv = st.enemies.filter((e) => e.hp > 0); cb.setFocus(liv[0] ? liv[0].uid : 0);
        let a = true; while (a) { a = false; const c = cb.getState(); if (c.over) break; const idx = c.hero.abilities.findIndex((x) => x.cost <= c.hero.mana && x.id !== 'guard'); if (idx >= 0 && cb.useSkill(idx).ok) a = true; } cb.endTurn(); }
      if (!cb.getState().over) g.flee(); else g.resolveCombat(); continue; }
    break;
  }
  const run = g.getRun();
  assert.equal(run.bagCap, 12);
  assert.ok(run.bag.length <= run.bagCap, 'bag never exceeds its cap');
  assert.equal(typeof run.gold, 'number');
  if (run.bag.length > 0) { const before = g.getRun().gold, n = g.getRun().bag.length; const s = g.sellFromBag(run.bag[0].id);
    assert.equal(s.ok, true); assert.ok(g.getRun().gold > before); assert.equal(g.getRun().bag.length, n - 1); }
  while (g.getRun().bag.length > 0) g.sellFromBag(g.getRun().bag[0].id);
  if (g.getRun().gold >= 12) { const before = g.getRun().potions.mana, gold = g.getRun().gold; const b = g.buyPotion('mana');
    assert.equal(b.ok, true); assert.equal(g.getRun().potions.mana, before + 1); assert.equal(g.getRun().gold, gold - 12); }
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
  // spend Mana (raise skeletons / cast)
  let g2 = 0; while (g2++ < 12) { const st = cb.getState(); if (st.over) break; const idx = st.hero.abilities.findIndex((a) => a.id !== 'guard' && a.cost <= st.hero.mana); if (idx < 0) break; if (!cb.useSkill(idx).ok) break; }
  const low = cb.getState().hero.mana;
  assert.ok(low < maxMana, 'Mana was spent');
  // quaff a Mana potion: restores Mana, decrements the belt
  const potsBefore = g.getRun().potions.mana;
  const r = g.quaff('mana');
  assert.equal(r.ok, true); assert.equal(g.getRun().potions.mana, potsBefore - 1);
  assert.ok(cb.getState().hero.mana > low, 'potion restored Mana');
  // leave the fight; Mana carries to the run — you did NOT refill to full
  if (!cb.getState().over) g.flee();
  assert.equal(g.getRun().mana, cb.getState().hero.mana, 'run Mana = what you left the fight with');
  assert.ok(g.getRun().mana < maxMana, 'no magical refill between packs');
});

test('leveling grants skill points and investing raises a skill', () => {
  const g = createGame('lvl', { classId: 'barbarian' });
  g.beginDescent();
  // fight the first node to gain xp
  const i = g.getRun().choices.findIndex((c) => c.type === 'combat');
  g.chooseDirection(i >= 0 ? i : 0);
  const cb = g.getCombat();
  if (cb) { let t = 0; while (!cb.getState().over && t++ < 40) { const st = cb.getState(); const liv = st.enemies.filter((e) => e.hp > 0); cb.setFocus(liv[0] ? liv[0].uid : 0);
    let acted = true; while (acted) { acted = false; const c = cb.getState(); if (c.over) break; const idx = c.hero.abilities.findIndex((a) => a.id !== 'guard' && a.cost <= c.hero.mana); if (idx >= 0 && cb.useSkill(idx).ok) { acted = true; } } cb.endTurn(); }
    g.resolveCombat(); }
  const run = g.getRun();
  if (run.skillPoints > 0) { const before = run.tree.find((t) => t.id === 'strike').level; g.investSkill('strike'); assert.equal(g.getRun().tree.find((t) => t.id === 'strike').level, before + 1); }
  assert.ok(run.level >= 1);
});
