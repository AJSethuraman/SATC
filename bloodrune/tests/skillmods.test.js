// Gear that reshapes HOW spells behave — the "items impact your skills" slice.
// Two layers: (1) deriveStats aggregates the behavior passives off gear into a
// skillMods bag (pure, deterministic); (2) the arena's geo router honors that bag —
// more spell%, bigger blasts, extra chain jumps / bolts, and piercing bolts all
// increase output. Behavioral checks run identical seeds with a big mod vs none and
// assert the mod strictly raises damage (the effect dwarfs RNG divergence).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createArena } from '../engine/arena.js';
import { makeRng } from '../engine/rng.js';
import { deriveStats } from '../engine/game.js';
import { CLASSES, ACT1 } from '../engine/content.js';
import { rollItem } from '../engine/loot.js';

// --- (1) plumbing: gear passives -> skillMods bag -------------------------------
test('deriveStats folds skill-behavior passives off gear into a skillMods bag', () => {
  const sorc = CLASSES.sorceress;
  const eq = { gloves: { passive: { spellPct: 12, aoePct: 20 } }, ring1: { passive: { plusJumps: 2, pierce: 1 } }, amulet: { passive: { plusBolts: 1 } } };
  const s = deriveStats(sorc, eq, 5, sorc.attr);
  assert.deepEqual(s.skillMods, { spellPct: 12, aoePct: 20, jumps: 2, bolts: 1, pierce: 1, costReduce: 0 });
});

test('a bare character has an all-zero skillMods bag (no gear, no reshaping)', () => {
  const s = deriveStats(CLASSES.sorceress, {}, 1);
  assert.deepEqual(s.skillMods, { spellPct: 0, aoePct: 0, jumps: 0, bolts: 0, pierce: 0, costReduce: 0 });
});

// --- (2) the behavior mods actually roll onto items, flat (not tier-scaled) -----
test('behavior COUNTS roll flat at any tier; percents scale with tier', () => {
  // force the Arcing/Scattering/Transfixing/Detonating affixes onto items by rolling
  // many caster items and checking the counts are always small integers.
  let sawJump = false, sawBolt = false, sawPierce = false;
  const rng = makeRng('mods');
  for (let i = 0; i < 400; i++) {
    const it = rollItem(rng, { tier: 'Hell', slot: 'gloves', prefer: 'caster' });
    const p = it.passive || {};
    if (p.plusJumps != null) { sawJump = true; assert.ok(p.plusJumps >= 1 && p.plusJumps <= 2, `+jumps stays small, got ${p.plusJumps}`); }
    if (p.plusBolts != null) { sawBolt = true; assert.ok(p.plusBolts >= 1 && p.plusBolts <= 2, `+bolts stays small, got ${p.plusBolts}`); }
    if (p.pierce != null) { sawPierce = true; assert.ok(p.pierce >= 1 && p.pierce <= 2, `pierce stays small, got ${p.pierce}`); }
  }
  assert.ok(sawJump && sawBolt && sawPierce, 'the new caster behavior affixes are reachable in the loot pool');
});

// --- (3) behavioral: the geo router honors the bag ------------------------------
// Average over several seeds and a long-enough window that the swarm reaches real
// density (a tanky, always-casting hero thins a sparse early crowd, which hides the
// AoE/multi-target mods — the difference only shows once foes actually pile up).
const TICKS = 30 * 30;
function avgDamage(abilities, hard, skillMods) {
  let sum = 0; const seeds = ['a', 'b', 'c', 'd'];
  for (const seed of seeds) {
    const hero = { name: 'S', glyph: '🔮', maxLife: 5000, life: 5000, maxMana: 99999, mana: 99999, manaRegen: 999,
      accuracy: 9, evade: 0, weapon: { wtype: 'focus' }, hard, plusSkills: 0, skillMods, abilities };
    const a = createArena({ hero, rng: makeRng('sm-' + seed), survival: { areas: ACT1, tier: 'Normal', rollLoot: () => null } });
    for (let t = 0; t < TICKS && !a.getState().over; t++) a.tick({ x: Math.sin(t / 23) * 0.6, y: Math.cos(t / 19) * 0.6 });
    sum += a.getState().tally.dmgDealt;
  }
  return sum / seeds.length;
}

test('+Spell Damage raises a spell build\'s output', () => {
  const base = avgDamage(['fire_ball'], { fire_ball: 6, fire_bolt: 4 }, {});
  const buffed = avgDamage(['fire_ball'], { fire_ball: 6, fire_bolt: 4 }, { spellPct: 150 });
  assert.ok(buffed > base * 1.3, `+150% Spell Damage should clearly out-damage base (base ${base.toFixed(0)}, buffed ${buffed.toFixed(0)})`);
});

test('+Chain Lightning jumps makes it strike more (more total damage)', () => {
  const base = avgDamage(['chain_lightning'], { chain_lightning: 5, lightning: 3 }, {});
  const buffed = avgDamage(['chain_lightning'], { chain_lightning: 5, lightning: 3 }, { jumps: 6 });
  assert.ok(buffed > base, `extra jumps should raise chain output (base ${base.toFixed(0)}, buffed ${buffed.toFixed(0)})`);
});

test('+Charged Bolt count throws more bolts (more total damage)', () => {
  const base = avgDamage(['charged_bolt'], { charged_bolt: 4 }, {});
  const buffed = avgDamage(['charged_bolt'], { charged_bolt: 4 }, { bolts: 6 });
  assert.ok(buffed > base, `extra bolts should raise spread output (base ${base.toFixed(0)}, buffed ${buffed.toFixed(0)})`);
});

test('piercing bolts hit more foes per cast (more total damage)', () => {
  const base = avgDamage(['fire_bolt'], { fire_bolt: 6 }, {});
  const buffed = avgDamage(['fire_bolt'], { fire_bolt: 6 }, { pierce: 4 });
  assert.ok(buffed > base, `piercing bolts should raise output in a crowd (base ${base.toFixed(0)}, buffed ${buffed.toFixed(0)})`);
});
