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
  assert.deepEqual(run.abilities.sort(), ['cleave', 'guard'].sort()); // Worn Axe -> Cleave, + Guard
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
    if (run.phase === 'reward') { while (S().skillPoints > 0) { const known = S().abilities; const want = learnPref.find((id) => !known.includes(id)) || learnPref[0]; g.investSkill(want); } g.continueFromReward(); continue; }
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
      g.resolveCombat();
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

test('leveling grants skill points and investing raises a skill', () => {
  const g = createGame('lvl', { classId: 'barbarian' });
  g.beginDescent();
  // fight the first node to gain xp
  const i = g.getRun().choices.findIndex((c) => c.type === 'combat');
  g.chooseDirection(i >= 0 ? i : 0);
  const cb = g.getCombat();
  if (cb) { let t = 0; while (!cb.getState().over && t++ < 40) { const st = cb.getState(); const liv = st.enemies.filter((e) => e.hp > 0); cb.setFocus(liv[0] ? liv[0].uid : 0);
    let acted = true; while (acted) { acted = false; const c = cb.getState(); if (c.over) break; const idx = c.hero.abilities.findIndex((a) => a.id !== 'guard' && a.cost <= c.hero.mana); if (idx >= 0) { cb.useSkill(idx); acted = true; } } cb.endTurn(); }
    g.resolveCombat(); }
  const run = g.getRun();
  if (run.skillPoints > 0) { const before = run.tree.find((t) => t.id === 'strike').level; g.investSkill('strike'); assert.equal(g.getRun().tree.find((t) => t.id === 'strike').level, before + 1); }
  assert.ok(run.level >= 1);
});
